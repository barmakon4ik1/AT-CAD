import time
import pythoncom
from contextlib import ContextDecorator

from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_DIM_OFFSET
from programs.at_base import regen
from programs.at_construction import add_rectangle, add_circle
from programs.at_dimension import add_dimension
from programs.at_geometry import ensure_point_variant


class CadTransaction(ContextDecorator):
    """
    Транзакция через временный блок.

    - Автоматический commit при успешном выходе
    - Автоматический rollback при исключении
    - Результат доступен после выхода из with
    """

    def __init__(self, doc, base_point):
        self.doc = doc
        self.base_point = base_point
        self.block = None
        self.block_name = None
        self.result_entities = []
        self.errors = []
        self._committed = False

    # ---------------- ENTER ----------------

    def __enter__(self):
        ts = str(int(time.time() * 1000))
        self.block_name = f"TMP_TRX_{ts}"

        try:
            self.block = self.doc.Blocks.Add(self.base_point, self.block_name)
        except pythoncom.com_error as e:
            self.errors.append(f"Block create error: {e}")

        return self

    # ---------------- EXIT ----------------

    def __exit__(self, exc_type, exc_val, exc_tb):

        # если внутри with было исключение
        if exc_type is not None:
            self.rollback()
            return False  # пробрасываем исключение дальше

        # если блок не создан
        if self.block is None:
            return False

        # автоматический commit
        self._auto_commit()

        return False

    # ---------------- MODEL ----------------

    @property
    def model(self):
        return self.block

    # ---------------- COMMIT ----------------

    def _auto_commit(self):

        if self.errors:
            self.rollback()
            return

        try:
            ms = self.doc.ModelSpace

            block_ref = ms.InsertBlock(
                self.base_point,
                self.block_name,
                1, 1, 1,
                0
            )

            exploded = block_ref.Explode()

            for ent in exploded:
                self.result_entities.append(ent)

            block_ref.Delete()
            self.doc.Blocks.Item(self.block_name).Delete()

            self._committed = True

        except pythoncom.com_error as e:
            self.errors.append(f"Commit error: {e}")
            self.rollback()

    # ---------------- ROLLBACK ----------------

    def rollback(self):
        try:
            if self.block_name:
                self.doc.Blocks.Item(self.block_name).Delete()
        except:
            pass


def run_in_transaction(doc, base_point, build_func, *args, **kwargs):
    """
    Выполняет функцию построения внутри транзакции.
    build_func должен принимать model первым аргументом.
    """

    base_variant = ensure_point_variant(base_point)

    with CadTransaction(doc, base_variant) as trx:

        if trx.block is None:
            return None, trx.errors

        result = build_func(trx.model, *args, **kwargs)

    return result, trx.errors


def transactional(func):

    def wrapper(base_point, *args, **kwargs):
        from programs.at_geometry import ensure_point_variant

        base_variant = ensure_point_variant(base_point)

        with CadTransaction(doc, base_variant) as trx:

            if trx.block is None:
                return None, trx.errors

            result = func(*args, **kwargs)

        return result, trx.errors

    return wrapper


# ------------------------------
#  Для примера
# ------------------------------
@transactional
def build_plate(width, height):
    add_rectangle(model, (0,0,0), width, height)
    add_circle(model, (width/2, height/2, 0), 50, layer_name="schrift")
    p0 = ensure_point_variant((0, 0, 0))
    p1 = ensure_point_variant((400, 200, 0))
    p2 = ensure_point_variant((0, 200, 0))
    add_dimension(doc, "H", p2, p1, offset=DEFAULT_DIM_OFFSET)
    add_dimension(doc, "V", p0, p1, offset=DEFAULT_DIM_OFFSET)


if __name__ == '__main__':
    acad = ATCadInit()
    doc, model = acad.document, acad.model_space
    user_point = ensure_point_variant((0, 0, 0))
    build_plate(user_point, 400, 200)
    regen(doc)

# if __name__ == "__main__":
#
#     from config.at_cad_init import ATCadInit
#     from programs.at_construction import add_line, add_circle, add_rectangle
#     from programs.at_base import regen
#
#     cad = ATCadInit()
#     doc = cad.document
#
#     print("AutoCAD подключён")
#
#     with CadTransaction(doc, base_point=ensure_point_variant([0, 0, 0])) as trx:
#
#         model = trx.model
#
#         p0 = ensure_point_variant((0, 0, 0))
#         p1 = ensure_point_variant((300, 100, 0))
#
#         add_line(model, (0, 0, 0), (300, 100, 0), layer_name="AM_7")
#         add_circle(model, (150, 0, 0), 80, layer_name="AM_0")
#         add_rectangle(model, (0, 0, 0), 400, 200, layer_name="SF-TEXT")
#         add_dimension(doc, "H", p0, p1, offset=DEFAULT_DIM_OFFSET)
#
#     # ← здесь уже выполнен commit
#
#     if trx.errors:
#         print("Ошибки транзакции:")
#         for e in trx.errors:
#             print("  ", e)
#     else:
#         print("Создано объектов:", len(trx.result_entities))
#         regen(doc)

