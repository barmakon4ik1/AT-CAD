"""
Файл: programs/at_offset.py
"""
import win32com.client
import pythoncom
from typing import List, Any

from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_base import regen
from programs.at_dimension import add_dimension
from programs.at_construction import add_text, add_polyline
from programs.at_geometry import polar_point, offset_point
from programs.at_input import at_get_point


def at_offset(polyline: Any, offset_distance: float, doc: Any, model: Any) -> list[Any] | None:
    """
    Создает смещенную полилинию с использованием win32com.

    Args:
        polyline: Объект полилинии (AcadLWPolyline).
        offset_distance: Расстояние смещения (float).
        doc: ActiveDocument AutoCAD.
        model: ModelSpace AutoCAD.

    Returns:
        Список смещенных полилиний или None в случае ошибки.
    """
    try:
        # Смещение внутрь
        offset_dist = -abs(float(offset_distance))
        offset_objects = polyline.Offset(offset_dist)
        result = list(offset_objects) if offset_objects else []
        return result

    except Exception as e:
        print(f"Ошибка создания смещенной полилинии: {e}")
        return None


if __name__ == "__main__":
    try:
        cad = ATCadInit()
        adoc, model, original_layer = cad.document, cad.model_space, cad.original_layer
        # # # Запрашиваем точку у пользователя (at_get_point уже возвращает готовый VARIANT)
        # input_point = at_get_point(cad.document, prompt="Укажите левый нижний угол", as_variant=False)
        #
        # # Вычисляем дополнительные точки с помощью полярных координат
        # input_point = (0, 0)
        # point2 = polar_point(input_point, distance=3000, alpha=0)
        # point3 = polar_point(point2, distance=1500, alpha=90)
        # point4 = polar_point(point3, distance=1000, alpha=180)
        # point5 = polar_point(point4, distance=500, alpha=-90)
        # point6 = polar_point(point5, distance=1000, alpha=180)
        # point7 = polar_point(point6, distance=500, alpha=-90)
        # point8 = polar_point(input_point, distance=500, alpha=90)

        # Тестовые данные
        polyline_points: list = [[0, 0], [3000, 0], [3000, 1500], [1500, 1500], [1500, 1000], [0, 1000]]
        offset_distance = 10.0
        text_content = "Попытка полной ломанной полилинии и ее смещение"

        print(polyline_points)

        # Создание тестовой полилинии
        polyline = add_polyline(model, polyline_points, "SF-TEXT")

        print(type(polyline))

        # Вызов функции at_offset
        offset_polylines = at_offset(polyline, offset_distance, adoc, model)

        # Размеры
        # offset_h, offset_v = 100, 80
        # add_dimension(adoc, "H", point4, point3, offset=offset_h)
        # add_dimension(adoc, "H", point6, point3, offset=offset_h + 360)
        # add_dimension(adoc, "H", point2, input_point, offset=offset_h)
        # add_dimension(adoc, "V", input_point, point8, offset=offset_v)
        # add_dimension(adoc, "V", input_point, point6, offset=offset_v + 900)
        # add_dimension(adoc, "V", point3, point2, offset=80)

        # Создание текста
        # text_point = offset_point(input_point, 0, 1800)
        # text_obj = add_text(model, text_point, text_content, "schrift", text_height=60, text_angle=0, text_alignment=0)

        # Регенерация чертежа
        regen(adoc)

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
