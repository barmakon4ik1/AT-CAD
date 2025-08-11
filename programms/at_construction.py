# programms/at_construction.py
"""
Файл: at_construction.py
Путь: programms/at_construction.py

Описание:
Модуль для создания геометрических объектов в AutoCAD через COM-интерфейс.
Переданный слой должен быть установлен как активный в системе.
"""

from typing import Optional, Any, List, Tuple
import math
import array
import pythoncom
from win32com.client import VARIANT

from programms.at_base import regen
from programms.at_geometry import add_rectangle_points
from programms.at_input import at_point_input
from windows.at_gui_utils import show_popup
from config.at_config import DEFAULT_TEXT_LAYER
from locales.at_localization_class import loc


def add_circle(model: Any, center: List[float], radius: float, layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт окружность в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        center: Центр окружности в формате [x, y, z].
        radius: Радиус окружности.
        layer_name: Название слоя (по умолчанию "0", должен быть активным).

    Returns:
        Optional[Any]: Объект окружности или None в случае ошибки.
    """
    try:
        center_array = [float(coord) for coord in center]
        center_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, center_array)
        circle = model.AddCircle(center_variant, radius)
        circle.Layer = layer_name
        return circle
    except:
        return None


def add_line(model: Any, point1: List[float], point2: List[float], layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт линию в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        point1: Начальная точка линии в формате [x, y, z].
        point2: Конечная точка линии в формате [x, y, z].
        layer_name: Название слоя (по умолчанию "0", должен быть активным).

    Returns:
        Optional[Any]: Объект линии или None в случае ошибки.
    """
    try:
        point1_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point1)
        point2_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point2)
        line = model.AddLine(point1_variant, point2_variant)
        line.Layer = layer_name
        return line
    except:
        return None


def add_LWpolyline(model: Any, points_list: List[float], layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт легковесную полилинию в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        points_list: Список координат [x1, y1, x2, y2, ...].
        layer_name: Название слоя (по умолчанию "0", должен быть активным).

    Returns:
        Optional[Any]: Объект полилинии или None в случае ошибки.
    """
    try:
        flat_points = [float(coord) for coord in points_list]
        arr = array.array('d', flat_points)
        variant_array = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, arr)
        polyline = model.AddLightWeightPolyline(variant_array)
        polyline.Closed = True
        polyline.Layer = layer_name
        return polyline
    except:
        return None


def add_rectangle(model: Any, point: List[float], width: float, height: float, layer_name: str = "0",
                  point_direction: str = "left_bottom") -> Optional[Any]:
    """
    Создаёт прямоугольник в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        point: Начальная точка в формате [x, y, z].
        width: Ширина прямоугольника.
        height: Высота прямоугольника.
        layer_name: Название слоя (по умолчанию "0", должен быть активным).
        point_direction: Направление начальной точки (по умолчанию "left_bottom").

    Returns:
        Optional[Any]: Объект полилинии (прямоугольник) или None в случае ошибки.
    """
    try:
        points_list = add_rectangle_points(point, width, height, point_direction)
        return add_LWpolyline(model, points_list, layer_name)
    except:
        return None


def at_diameter(diameter: float, thickness: float, flag: str = "outer") -> float:
    """
    Вычисляет средний диаметр с учётом толщины.

    Args:
        diameter: Диаметр (внешний, внутренний или средний).
        thickness: Толщина материала.
        flag: Тип диаметра ("inner", "middle", "outer").

    Returns:
        float: Средний диаметр.

    Raises:
        ValueError: Если входные данные некорректны.
    """
    try:
        if thickness < 0:
            raise ValueError("Толщина материала не может быть отрицательной.")
        if diameter < 0:
            raise ValueError("Диаметр не может быть отрицательным.")
        if flag == "middle":
            return float(diameter)
        elif flag == "outer":
            if diameter < thickness:
                raise ValueError("Внешний диаметр не может быть меньше толщины.")
            return float(diameter - thickness)
        elif flag == "inner":
            return float(diameter + thickness)
        raise ValueError(loc.get("dia_error", "Неверный тип диаметра."))
    except Exception as e:
        show_popup(
            loc.get("diameter_error_details", f"Ошибка при вычислении диаметра: {str(e)}"),
            popup_type="error"
        )
        return 0.0


def at_steigung(height: float, diameter_base: float, diameter_top: float = 0) -> Optional[float]:
    """
    Вычисляет наклон конуса.

    Args:
        height: Высота конуса.
        diameter_base: Диаметр основания.
        diameter_top: Диаметр вершины (по умолчанию 0).

    Returns:
        Optional[float]: Наклон конуса или None в случае ошибки.
    """
    try:
        if not all(isinstance(x, (int, float)) for x in [height, diameter_base, diameter_top]):
            raise ValueError("All inputs must be numbers")
        if diameter_base <= 0 or diameter_top < 0 or height <= 0:
            raise ValueError(
                loc.get("diameter_base_positive",
                        "Диаметр основания должен быть положительным.") if diameter_base <= 0 else
                loc.get("diameter_top_non_negative",
                        "Диаметр вершины не может быть отрицательным.") if diameter_top < 0 else
                loc.get("height_positive", "Высота должна быть положительной.")
            )
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top
        steigung = (diameter_base - diameter_top) / height
        if math.isinf(steigung) or math.isnan(steigung):
            raise ValueError("Invalid steigung result")
        return steigung
    except Exception as e:
        show_popup(
            loc.get("steigung_error_details", f"Ошибка при вычислении наклона: {str(e)}"),
            popup_type="error"
        )
        return None


def at_cone_height(diameter_base: float, diameter_top: float = 0, steigung: Optional[float] = None,
                   angle: Optional[float] = None) -> Optional[float]:
    """
    Вычисляет высоту конуса по заданным параметрам.

    Args:
        diameter_base: Диаметр основания.
        diameter_top: Диаметр вершины (по умолчанию 0).
        steigung: Наклон конуса (опционально).
        angle: Угол наклона в градусах (опционально).

    Returns:
        Optional[float]: Высота конуса или None в случае ошибки.
    """
    try:
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top
        if steigung is None and angle is None:
            raise ValueError(loc.get("missing_data", "Необходимо указать наклон или угол."))
        if steigung is not None and angle is not None:
            raise ValueError(loc.get("both_parameters_error", "Нельзя указывать одновременно наклон и угол."))
        if steigung is not None:
            if not isinstance(steigung, (int, float)) or steigung <= 0:
                raise ValueError(
                    loc.get("invalid_gradient", "Наклон должен быть числом.") if not isinstance(steigung,
                                                                                                (int, float)) else
                    loc.get("gradient_positive", "Наклон должен быть положительным.")
                )
            return (diameter_base - diameter_top) / steigung
        if not isinstance(angle, (int, float)) or angle <= 0 or angle >= 180:
            raise ValueError(
                loc.get("invalid_angle", "Угол должен быть числом.") if not isinstance(angle, (int, float)) else
                loc.get("angle_range_error", "Угол должен быть в диапазоне (0, 180).")
            )
        return (diameter_base - diameter_top) / (2 * math.tan(math.radians(angle) / 2))
    except Exception as e:
        show_popup(
            loc.get("cone_height_error_details", f"Ошибка при вычислении высоты конуса: {str(e)}"),
            popup_type="error"
        )
        return None


def at_cone_sheet(model: Any, input_point: List[float], diameter_base: float, diameter_top: float = 0,
                  height: float = 0, layer_name: str = "0") -> Optional[Tuple[Any, List[float]]]:
    """
    Создаёт развертку конуса в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        input_point: Точка вставки в формате [x, y, z].
        diameter_base: Диаметр основания.
        diameter_top: Диаметр вершины (по умолчанию 0).
        height: Высота конуса.
        layer_name: Название слоя (по умолчанию "0", должен быть активным).

    Returns:
        Optional[Tuple[Any, List[float]]]: Объект полилинии и точка вставки или (None, None) в случае ошибки.
    """
    try:
        if diameter_top > diameter_base:
            diameter_base, diameter_top = diameter_top, diameter_base
        k = 0.5 * math.sqrt(1 + height ** 2 * 4 / ((diameter_base - diameter_top) ** 2))
        R1 = diameter_base * k
        R2 = diameter_top * k
        theta = math.pi * diameter_base / R1
        if math.isinf(theta) or math.isnan(theta):
            raise ValueError("Invalid theta result")
        if R1 <= 0 or R2 < 0 or math.isinf(R1) or math.isinf(R2) or math.isnan(R1) or math.isnan(R2):
            raise ValueError("Invalid geometry parameters")
        half_theta = theta / 2
        sin_half_theta = math.sin(half_theta)
        cos_half_theta = math.cos(half_theta)
        drs1 = R1 * sin_half_theta
        drs2 = R2 * sin_half_theta
        drc1 = R1 * cos_half_theta
        drc2 = R2 * cos_half_theta
        center = [input_point[0], input_point[1] - (R1 - (R1 - R2) * 0.5), 0]
        p1 = [center[0] + drs2, center[1] + drc2]
        p2 = [center[0] + drs1, center[1] + drc1]
        p3 = [center[0] - drs1, center[1] + drc1]
        p4 = [center[0] - drs2, center[1] + drc2]
        bulge = math.tan(0.25 * theta)
        if math.isinf(bulge) or math.isnan(bulge):
            raise ValueError("Invalid bulge result")
        points_list = [p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1]]
        polyline = add_LWpolyline(model, points_list, layer_name)
        if polyline:
            polyline.SetBulge(1, bulge)
            polyline.SetBulge(3, -bulge)
        return polyline, input_point
    except Exception as e:
        if hasattr(e, 'hresult') and e.hresult == -2147417848:
            return None, None
        show_popup(
            loc.get("cone_sheet_error_details", f"Ошибка при создании развертки конуса: {str(e)}"),
            popup_type="error"
        )
        return None, None


def polar_point(point: List[float], distance: float, alpha: float = 0) -> list[float | int] | None:
    """
    Находит точку в полярных координатах относительно начальной точки.

    Args:
        point: Начальная точка в формате [x, y] или [x, y, z].
        distance: Расстояние от начальной точки.
        alpha: Угол в градусах (по умолчанию 0).

    Returns:
        Tuple[float, float]: Координаты новой точки (x, y).

    Notes:
        Если входные параметры некорректны, возвращается None.
    """
    try:
        x0, y0 = float(point[0]), float(point[1])
        alpha_rad = math.radians(alpha)
        x1 = x0 + distance * math.cos(alpha_rad)
        y1 = y0 + distance * math.sin(alpha_rad)
        return [x1, y1, 0]
    except:
        return None


def at_addText(model: Any, point: List[float], text: str = "", layer_name: str = DEFAULT_TEXT_LAYER,
               text_height: float = 30, text_angle: float = 0, text_alignment: int = 4) -> Optional[Any]:
    """
    Создаёт текст в модельном пространстве.

    Args:
        model: Объект модельного пространства AutoCAD (ModelSpace).
        point: Точка вставки текста в формате [x, y, z].
        text: Строка текста.
        layer_name: Название слоя (по умолчанию DEFAULT_TEXT_LAYER, должен быть активным).
        text_height: Высота текста (по умолчанию 30).
        text_angle: Угол поворота текста в радианах (по умолчанию 0).
        text_alignment: Выравнивание текста (по умолчанию 4, acAlignmentMiddle).

    Returns:
        Optional[Any]: Объект текста или None в случае ошибки.

    Notes:
        Значения выравнивания:
        0: acAlignmentLeft, 1: acAlignmentCenter, 2: acAlignmentRight,
        3: acAlignmentAligned, 4: acAlignmentMiddle, 5: acAlignmentFit,
        6: acAlignmentTopLeft, 7: acAlignmentTopCenter, 8: acAlignmentTopRight,
        9: acAlignmentMiddleLeft, 10: acAlignmentMiddleCenter, 11: acAlignmentMiddleRight,
        12: acAlignmentBottomLeft, 13: acAlignmentBottomCenter, 14: acAlignmentBottomRight.
    """
    try:
        point_array = [float(coord) for coord in point]
        point_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point_array)
        text_obj = model.AddText(text, point_variant, text_height)
        text_obj.Layer = layer_name
        text_obj.Alignment = text_alignment
        if text_alignment not in [0, 1, 2]:
            text_obj.TextAlignmentPoint = point_variant
        text_obj.Rotation = text_angle
        return text_obj
    except:
        return None


if __name__ == "__main__":
    """
    Тестирование создания текста, окружности, линий, полилинии и прямоугольника с использованием точки из at_input.
    """
    from config.at_cad_init import ATCadInit

    cad = ATCadInit()

    # Точки
    input_point = at_point_input(cad.adoc)
    point2 = polar_point(input_point, distance=400, alpha=90)
    point3 = polar_point(input_point, distance=400, alpha=60)
    point4 = polar_point(input_point, distance=400, alpha=120)

    # Создание текста
    text_obj = at_addText(cad.model, input_point, "Тестовый текст")

    # Создание окружности
    radius = 200
    circle_obj = add_circle(cad.model, input_point, radius, layer_name="SF-ARE")

    # Создание линии
    line_obj = add_line(cad.model, input_point, point2, layer_name="AM_7")

    # Создание полилинии (треугольник)
    polyline_points = [input_point[0], input_point[1], point3[0], point3[1], point4[0], point4[1]]
    polyline_obj = add_LWpolyline(cad.model, polyline_points, layer_name="LASER-TEXT")

    # Создание прямоугольника
    width, height = 300, 200
    rectangle_obj = add_rectangle(cad.model, input_point, width, height, layer_name="SF-TEXT")

    regen(cad.adoc)
