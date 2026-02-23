# utils/cad_transaction.py
import uuid
from win32com.client import CDispatch

from programs.at_construction import add_polyline, add_line, add_circle, add_rectangle, add_text

class CadTransaction:
    """
    Контекст для надёжного построения блока примитивов в AutoCAD.
    Все элементы рисуются во временном блоке.
    Если всё прошло успешно — блок распаковывается в модельное пространство.
    При ошибке — блок удаляется, ошибки собираются.
    """

    def __init__(self, doc: CDispatch):
        self.doc = doc
        self.errors: list[str] = []
        self.entities: list[CDispatch] = []
        self.block_name = f"_trx_block_{uuid.uuid4().hex}"  # уникальное имя блока
        self.block = None

    def __enter__(self):
        ms = self.doc.ModelSpace

        # Создаём временный блок в модели
        self.block = self.doc.Blocks.Add((0, 0, 0), self.block_name)
        return self

    def add_entity(self, func, *args, **kwargs):
        """
        Добавляет примитив в блок. func — любая функция рисования,
        например add_line, add_circle, add_rectangle, add_text.
        """
        try:
            entity = func(self.block, *args, **kwargs)
            if entity:
                self.entities.append(entity)
            return entity
        except Exception as ex:
            self.errors.append(f"{func.__name__} failed: {ex}")
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        ms = self.doc.ModelSpace

        if exc_type or self.errors:
            # Что-то пошло не так — удаляем временный блок
            try:
                self.block.Delete()
            except Exception:
                pass  # игнорируем ошибки удаления
            return False  # проброс исключения наружу

        # Всё успешно — распаковываем блок в модельное пространство
        try:
            ins = ms.InsertBlock((0, 0, 0), self.block_name, 1, 1, 1, 0)
            self.block.Delete()  # временный блок больше не нужен
        except Exception as ex:
            self.errors.append(f"Block insert failed: {ex}")
            return False