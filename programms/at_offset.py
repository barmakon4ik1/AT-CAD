"""
Файл: programms/at_offset.py
"""
import win32com.client
import pythoncom
from typing import List, Any

from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from programms.at_base import regen
from programms.at_dimension import add_dimension
from programms.at_construction import add_LWpolyline, at_addText
from programms.at_geometry import polar_point
from programms.at_input import at_point_input


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
        coords = polyline.Coordinates
        vertices = list(zip(coords[::2], coords[1::2]))

        # Смещение внутрь
        offset_distance = -abs(float(offset_distance))
        offset_objects = polyline.Offset(offset_distance)
        result = list(offset_objects) if offset_objects else []
        return result

    except Exception as e:
        print(f"Ошибка создания смещенной полилинии: {e}")
        return None


if __name__ == "__main__":
    try:
        cad = ATCadInit()
        adoc, model, original_layer = cad.adoc, cad.model, cad.original_layer
        # Запрашиваем точку у пользователя (at_point_input уже возвращает готовый VARIANT)
        input_point = at_point_input(cad.adoc, prompt="Укажите левый нижний угол")

        # Вычисляем дополнительные точки с помощью полярных координат
        point2 = polar_point(input_point, distance=3000, alpha=0)
        point3 = polar_point(point2, distance=1500, alpha=90)
        point4 = polar_point(input_point, distance=1500, alpha=90)

        # Тестовые данные
        polyline_points = [input_point, point2, point3, point4]
        offset_distance = 10.0
        text_content = "Test Text"

        # Создание тестовой полилинии
        polyline = add_LWpolyline(model, polyline_points, "SF-TEXT")

        # Вызов функции at_offset
        offset_polylines = at_offset(polyline, offset_distance, adoc, model)

        # Размеры
        offset_h = 100
        add_dimension(adoc, "H", point4, point3, offset=offset_h)
        add_dimension(adoc, "V", input_point, point4, offset=80)

        # Создание тестового текста
        text_point = polar_point(point4, distance=offset_h+100, alpha=90)
        text_obj = at_addText(model, text_point, text_content, "schrift", text_height=60, text_angle=0, text_alignment=0)

        # Регенерация чертежа
        regen(adoc)

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
