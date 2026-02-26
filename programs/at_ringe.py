"""
programs/at_ringe.py
Модуль для построения колец в AutoCAD на основе данных из диалогового окна.
Создаёт окружности с заданными диаметрами и добавляет текстовые метки с номером работы.
"""

from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, DEFAULT_DIM_OFFSET
from engineering_handbook.engineering_handbook.settings import DEBUG
from locales.at_translations import loc
from programs.at_construction import add_circle, AccompanyText, MainText
from programs.at_base import layer_context, regen
from programs.at_dimension import add_dimension
from programs.at_geometry import ensure_point_variant, polar_point, offset_point
from programs.at_input import at_get_point

from errors.at_errors import ATError, GeometryError, DataError, TextError
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided",
    },
    "no_diameters": {
        "ru": "Не указаны диаметры",
        "de": "Keine Durchmesser angegeben",
        "en": "No diameters specified",
    },
    "point_conversion_error": {
        "ru": "Ошибка преобразования точки",
        "de": "Fehler bei der Punktkonvertierung",
        "en": "Point conversion error",
    },
    "mm": {
        "ru": "мм",
        "de": "mm",
        "en": "mm",
    },
}

loc.register_translations(TRANSLATIONS)


def get_valid_diameters(diameters: dict) -> list[tuple[float, float, float]]:
    """
    Возвращает список корректных (D, X, Y).

    Фильтрует:
    - None
    - пустые строки
    - некорректные типы
    - отрицательные и нулевые диаметры
    """

    if not isinstance(diameters, dict):
        return []

    valid = []

    for values in diameters.values():

        if not isinstance(values, (list, tuple)) or len(values) != 3:
            continue

        diameter, offset_x, offset_y = values

        # Проверка диаметра
        if not isinstance(diameter, (int, float)) or diameter <= 0:
            continue

        # Проверка смещений
        if not isinstance(offset_x, (int, float)):
            offset_x = 0.0

        if not isinstance(offset_y, (int, float)):
            offset_y = 0.0

        valid.append((float(diameter), float(offset_x), float(offset_y)))

    return valid


def main(ring_data: dict | None = None) -> bool:
    """
    Основная функция для построения колец в AutoCAD.
    """

    try:
        # ------------------------------------------------------------------
        # Инициализация AutoCAD
        # ------------------------------------------------------------------
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        center = at_get_point(
            adoc,
            as_variant=False,
            prompt="Выберите точку вставки",
        )

        # ------------------------------------------------------------------
        # Проверка входных данных
        # ------------------------------------------------------------------
        if not ring_data:
            raise DataError(__name__, ValueError(loc.get("no_data_error")))

        ring_data["insert_point"] = center

        work_number = ring_data.get("order", "")
        detail = ring_data.get("detail", "")
        material = ring_data.get("material", "")
        thickness = ring_data.get("thickness", "")
        raw_diameters = ring_data.get("diameters", {})
        diameters = get_valid_diameters(raw_diameters)

        if not diameters:
            raise DataError(__name__, ValueError(loc.get("no_diameters")))

        if not diameters:
            raise DataError(__name__, ValueError(loc.get("no_diameters")))

        # ------------------------------------------------------------------
        # Преобразование точки центра
        # ------------------------------------------------------------------
        try:
            center_variant = ensure_point_variant(center)
        except Exception as err:
            raise GeometryError(__name__, err)

        # Нахожление окружности с максимальным диаметром
        max_diameter, max_offset_x, max_offset_y = max(
            diameters,
            key=lambda v: v[0]  # сортировка по диаметру
        )

        max_radius = max_diameter / 2.0
        max_center = offset_point(center_variant, max_offset_x, max_offset_y)

        # ------------------------------------------------------------------
        # Построение окружностей с учётом смещений
        # ------------------------------------------------------------------
        try:
            with layer_context(adoc, DEFAULT_CIRCLE_LAYER):
                for i, (diameter, offset_x, offset_y) in enumerate(diameters, start=1):
                    radius = diameter / 2.0
                    circle_center = offset_point(center_variant, offset_x, offset_y)

                    add_circle(model, circle_center, radius, DEFAULT_CIRCLE_LAYER)

        except Exception as err:
            raise GeometryError(__name__, err)

        # ------------------------------------------------------------------
        # Добавление текста
        # ------------------------------------------------------------------
        if work_number:
            try:
                p1 = offset_point(max_center, 0, max_radius / 2)
                p2 = offset_point(max_center, 0, max_radius + DEFAULT_DIM_OFFSET + 20)

                # основной текст
                MainText(
                    {"work_number": work_number, "detail": detail}
                ).draw(model, p1, text_alignment=4, laser=True)

                # дополнительный текст
                AccompanyText(
                    {"thickness": thickness, "material": material}
                ).draw(model, p2, text_alignment=4)

            except Exception as err:
                raise TextError(__name__, err)

        # ------------------------------------------------------------------
        # Обновление экрана
        # ------------------------------------------------------------------
        regen(adoc)
        return True

    except ATError as err:
        err.show()
        return False


if __name__ == "__main__":
    """
    Точка входа в приложение. Для тестирования напрямую (не рекомендуется).
    """
    try:
        # Для тестирования можно передать тестовые данные
        test_data = {
            "order": "TEST123",
            "detail": "1",
            "material": "1.4301",
            "thickness": 3,
            "diameters": {"1": [500, 0, 0], "2": [200, 0, 0], "3": [22, 150, -150]},
            "input_point": (0, 0, 0)  # Изменено с insert_point на input_point
        }
        main(test_data)
    except Exception as main_err:
        show_popup(loc.get("build_error", "Ошибка построения колец: {}").format(str(main_err)), popup_type="error")
