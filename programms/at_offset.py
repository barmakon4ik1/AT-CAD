"""
Файл: programms/at_offset.py
"""
import sys
import pythoncom
from pyautocad import APoint
from programms.at_construction import add_LWpolyline

def at_offset(polyline, allowance, adoc=None, model=None):
    """
    Создаёт внутреннюю полилинию путём масштабирования внешней полилинии и смещения.

    Args:
        polyline: Объект полилинии (AcadLWPolyline).
        allowance: Расстояние смещения (положительное, в единицах чертежа).
        adoc: Объект ActiveDocument AutoCAD (не используется).
        model: Объект ModelSpace (для создания полилинии).

    Returns:
        Список объектов полилиний или None в случае ошибки.
    """
    try:
        pythoncom.CoInitialize()
        print(f"[{sys._getframe().f_code.co_name}] Шаг 1: Начало создания внутренней полилинии")
        print(f"[{sys._getframe().f_code.co_name}] Шаг 2: Расстояние смещения: {allowance}")

        # Получение координат полилинии
        print(f"[{sys._getframe().f_code.co_name}] Шаг 3: Вычисление координат")
        coordinates = polyline.Coordinates
        polyline_points = [(coordinates[i], coordinates[i+1]) for i in range(0, len(coordinates), 2)]
        if len(polyline_points) > 1 and polyline_points[-1] == polyline_points[0]:
            polyline_points = polyline_points[:-1]
        print(f"[{sys._getframe().f_code.co_name}] Шаг 3.1: Исходные точки: {polyline_points}")

        # Определение размеров внешней полилинии
        min_x = min(x for x, y in polyline_points)
        max_x = max(x for x, y in polyline_points)
        min_y = min(y for x, y in polyline_points)
        max_y = max(y for x, y in polyline_points)
        width = max_x - min_x
        height = max_y - min_y
        print(f"[{sys._getframe().f_code.co_name}] Шаг 3.2: Размеры внешней полилинии: ширина={width}, высота={height}")

        # Коэффициенты масштабирования
        scale_x = (width - 2 * allowance) / width if width > 0 else 1.0
        scale_y = (height - 2 * allowance) / height if height > 0 else 1.0
        print(f"[{sys._getframe().f_code.co_name}] Шаг 3.3: Коэффициенты масштабирования: scale_x={scale_x}, scale_y={scale_y}")

        # Масштабирование относительно (0, 0)
        scaled_points = [(x * scale_x, y * scale_y) for x, y in polyline_points]
        print(f"[{sys._getframe().f_code.co_name}] Шаг 3.4: Масштабированные точки: {scaled_points}")

        # Смещение на (10, 10)
        offset_points = [(x + allowance, y + allowance) for x, y in scaled_points]
        print(f"[{sys._getframe().f_code.co_name}] Шаг 4: Смещённые координаты: {offset_points}")

        # Добавляем замыкающую точку
        if offset_points and offset_points[0] != offset_points[-1]:
            offset_points.append(offset_points[0])
        flat_offset_points = [coord for pt in offset_points for coord in pt]

        # Создание полилинии
        offset_poly = add_LWpolyline(model, flat_offset_points, layer_name="SF-TEXT")
        if offset_poly:
            offset_poly.Closed = True
            print(f"[{sys._getframe().f_code.co_name}] Шаг 5: Полилиния создана: Handle={offset_poly.Handle}, Площадь={offset_poly.Area}")
            return [offset_poly]
        else:
            print(f"[{sys._getframe().f_code.co_name}] Шаг 5.1: Не удалось создать полилинию")
            return None

    except Exception as e:
        print(f"[{sys._getframe().f_code.co_name}] Шаг 6: Ошибка: {e}, Type: {type(e)}, Args: {e.args}")
        return None
    finally:
        pythoncom.CoUninitialize()
