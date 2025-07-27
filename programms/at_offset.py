"""
Файл: programms/at_offset.py
"""
import win32com.client
import pythoncom
from typing import List, Any
from config.at_cad_init import ATCadInit
from programms.at_construction import add_LWpolyline, at_addText
from programms.at_create_layer import at_create_layer


def at_offset(polyline: Any, offset_distance: float, doc: Any, model: Any) -> List[Any]:
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
        pass

if __name__ == "__main__":
    try:
        cad = ATCadInit()
        adoc, model, original_layer = cad.adoc, cad.model, cad.original_layer
        at_create_layer(adoc)

        # Тестовые данные
        polyline_points = [
            (0, 0),
            (1500, 0),
            (1500, 1500),
            (1000, 1500),
            (1000, 750),
            (0, 750)
        ]
        offset_distance = 10.0
        text_content = "Test Text"

        # Создание тестовой полилинии
        flat_points = [float(coord) for point in polyline_points for coord in point]
        polyline = add_LWpolyline(model, flat_points, "SF-TEXT")
        coords = polyline.Coordinates
        text_point = [coords[0], coords[5], 0]
        # vertices = list(zip(coords[::2], coords[1::2]))

        # Вызов функции at_offset
        offset_polylines = at_offset(polyline, offset_distance, adoc, model)

        # Создание тестового текста
        text_obj = at_addText(model, text_point, text_content, "schrift", text_height=60, text_angle=0, text_alignment=0)

        # Регенерация чертежа
        adoc.Regen(1)  # acAllViewports

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
