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
        diameters = ring_data.get("diameters", {})

        if not diameters:
            raise DataError(__name__, ValueError(loc.get("no_diameters")))

        # ------------------------------------------------------------------
        # Преобразование точки центра
        # ------------------------------------------------------------------
        try:
            center_variant = ensure_point_variant(center)
        except Exception as err:
            raise GeometryError(__name__, err)

        # ------------------------------------------------------------------
        # Построение окружностей с учётом смещений
        # ------------------------------------------------------------------
        try:
            with layer_context(adoc, DEFAULT_CIRCLE_LAYER):
                for i, values in enumerate(diameters.values(), start=1):  # start=1 для нумерации
                    # if not (isinstance(values, (list, tuple)) and len(values) == 3):
                    #     raise ValueError(loc.get("no_diameters"))

                    diameter, offset_x, offset_y = values

                    # if not isinstance(diameter, (int, float)) or diameter <= 0:
                    #     raise ValueError(loc.get("no_diameters"))

                    radius = diameter / 2.0
                    # точка с учётом смещений
                    circle_center = offset_point(center_variant, offset_x, offset_y)

                    add_circle(model, circle_center, radius, DEFAULT_CIRCLE_LAYER)
                    # построение радиуса
                    # chord_point = polar_point(circle_center, radius, 20 * i)
                    # add_dimension(adoc, "R", circle_center, chord_point, radius)

        except Exception as err:
            raise GeometryError(__name__, err)

        # ------------------------------------------------------------------
        # Добавление текста
        # ------------------------------------------------------------------
        if work_number:
            try:
                # # вытаскиваем радиусы из списка [D, X, Y]
                # sorted_radii = sorted(
                #     [values[0] / 2.0 for values in diameters.values()], reverse=True
                # )
                # max_radius = sorted_radii[0]
                # second_radius = sorted_radii[1] if len(sorted_radii) > 1 else 0
                #
                # # вычисляем смещение текста
                # y_offset = max_radius - (max_radius - second_radius) * 0.5
                #
                # p1 = [center[0], center[1] + y_offset, 0]
                # p2 = [
                #     center[0],
                #     center[1] + max_radius + DEFAULT_DIM_OFFSET + 20,
                #     0,
                # ]

                # DEBUG
                p1 = polar_point(center, radius / 2.0, 90)
                p2 = polar_point(center, radius + 50, 90)

                # основной текст
                MainText(
                    {
                        "work_number": work_number,
                        "detail": detail,
                    }
                ).draw(model, p1, text_alignment=4, laser=True)

                # дополнительный текст
                AccompanyText(
                    {
                        "thickness": thickness,
                        "material": material,
                    }
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
