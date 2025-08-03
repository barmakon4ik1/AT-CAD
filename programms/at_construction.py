# programms/at_construction.py
"""
Модуль для создания геометрических объектов в AutoCAD.
"""
import array

from pyautocad import APoint, Autocad

from programms.at_base import *
from programms.at_geometry import *
from programms.at_input import at_point_input
import win32com.client
import pythoncom
import array
from typing import List, Any, Optional
from win32com.client import VARIANT
from typing import Union, Tuple
import math
from windows.at_gui_utils import show_popup
from locales.at_localization_class import loc



@handle_errors
def add_circle(model: object, center: APoint, radius: float, layer_name: str = "0") -> Optional[object]:
    """
    Создает окружность в модельном пространстве.
    """
    circle = model.AddCircle(center, radius)
    circle.Layer = layer_name
    return circle


@handle_errors
def add_line(model: object, point1: APoint, point2: APoint, layer_name: str = "0") -> Optional[object]:
    """
    Создает линию в модельном пространстве.
    """
    line = model.AddLine(point1, point2)
    line.Layer = layer_name
    return line


@handle_errors
# def add_LWpolyline(model: object, points_list: List[float], layer_name: str = "0") -> Optional[object]:
#     """
#     Создает легковесную полилинию в модельном пространстве.
#     """
#     if not isinstance(points_list, (list, tuple)) or len(points_list) % 2 != 0:
#         raise ValueError("Invalid points list")
#     flat_points = [float(coord) for coord in points_list]
#     points_double = array.array("d", flat_points)
#     adoc = model.Document
#     ensure_layer(adoc, layer_name)
#     layer = adoc.Layers.Item(layer_name)
#     if layer.Lock:
#         layer.Lock = False
#     polyline = model.AddLightWeightPolyline(points_double)
#     polyline.Closed = True
#     polyline.Layer = layer_name
#     return polyline
def add_LWpolyline(model: Any, points_list: List[float], layer_name: str = "0") -> Any:
    """
        Создает легковесную полилинию в модельном пространстве.
    """
    try:
        if not isinstance(points_list, (list, tuple)) or len(points_list) % 2 != 0:
            raise ValueError("Invalid points list")
        flat_points = [float(coord) for coord in points_list]

        adoc = model.Document
        layer = adoc.Layers.Item(layer_name)
        if layer.Lock:
            layer.Lock = False

        arr = array.array('d', flat_points)
        variant_array = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, arr)
        polyline = model.AddLightWeightPolyline(variant_array)
        polyline.Closed = True
        polyline.Layer = layer_name

        return polyline
    except Exception as e:
        print(f"Ошибка в add_LWpolyline: {e}")
        return None

@handle_errors
def add_rectangle(model: object, point: APoint, width: float, height: float, layer_name: str = "0",
                 point_direction: str = "left_bottom") -> Optional[object]:
    """
    Создает прямоугольник в модельном пространстве.
    """
    from at_geometry import add_rectangle_points
    points_list = add_rectangle_points(point, width, height, point_direction)
    return add_LWpolyline(model, points_list, layer_name)


def at_diameter(diameter: float, thickness: float, flag: str = "outer") -> float:
    """
    Вычисляет средний диаметр с учетом толщины.

    Args:
        diameter: Диаметр (внешний, внутренний или средний).
        thickness: Толщина материала.
        flag: Тип диаметра ("inner", "middle", "outer").

    Returns:
        Средний диаметр.

    Raises:
        ValueError: Если входные данные некорректны.
    """
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
    raise ValueError(loc.get('dia_error', "Неверный тип диаметра."))


@handle_errors
def at_steigung(height: float, diameter_base: float, diameter_top: float = 0) -> Optional[float]:
    """
    Вычисляет наклон конуса.
    """
    if not all(isinstance(x, (int, float)) for x in [height, diameter_base, diameter_top]):
        show_popup(loc.get('invalid_number'), popup_type="error")
        return None
    if diameter_base <= 0 or diameter_top < 0 or height <= 0:
        show_popup(loc.get('diameter_base_positive') if diameter_base <= 0 else
                   loc.get('diameter_top_non_negative') if diameter_top < 0 else
                   loc.get('height_positive'), popup_type="error")
        return None
    if diameter_top > diameter_base:
        diameter_top, diameter_base = diameter_base, diameter_top
    try:
        steigung = (diameter_base - diameter_top) / height
        return steigung if not (math.isinf(steigung) or math.isnan(steigung)) else None
    except Exception:
        show_popup(loc.get('invalid_result'), popup_type="error")
        return None


@handle_errors
def at_cone_height(diameter_base: float, diameter_top: float = 0, steigung: Optional[float] = None,
                   angle: Optional[float] = None) -> Optional[float]:
    """
    Вычисляет высоту конуса по заданным параметрам.
    """
    if not all(isinstance(x, (int, float)) for x in [diameter_base, diameter_top]):
        show_popup(loc.get('invalid_number'), popup_type="error")
        return None
    if diameter_base <= 0 or diameter_top < 0:
        show_popup(loc.get('diameter_base_positive') if diameter_base <= 0 else
                   loc.get('diameter_top_non_negative'), popup_type="error")
        return None
    if diameter_top > diameter_base:
        diameter_top, diameter_base = diameter_base, diameter_top
    if steigung is None and angle is None:
        show_popup(loc.get('missing_data'), popup_type="error")
        return None
    if steigung is not None and angle is not None:
        show_popup(loc.get('both_parameters_error'), popup_type="error")
        return None
    if steigung is not None:
        if not isinstance(steigung, (int, float)) or steigung <= 0:
            show_popup(loc.get('invalid_gradient') if not isinstance(steigung, (int, float)) else
                       loc.get('gradient_positive'), popup_type="error")
            return None
        return (diameter_base - diameter_top) / steigung
    if not isinstance(angle, (int, float)) or angle <= 0 or angle >= 180:
        show_popup(loc.get('invalid_angle') if not isinstance(angle, (int, float)) else
                   loc.get('angle_range_error'), popup_type="error")
        return None
    try:
        return (diameter_base - diameter_top) / (2 * math.tan(math.radians(angle) / 2))
    except Exception:
        show_popup(loc.get('math_error'), popup_type="error")
        return None


@handle_errors
def at_cone_sheet(model: object, input_point: APoint, diameter_base: float, diameter_top: float = 0,
                  height: float = 0, layer_name: str = "0") -> Optional[Tuple[object, APoint]]:
    """
    Создает развертку конуса в модельном пространстве.
    """
    if not all(isinstance(x, (int, float)) for x in [diameter_base, diameter_top, height]):
        show_popup(loc.get('invalid_number'), popup_type="error")
        return None, None
    if not isinstance(input_point, (APoint, list, tuple)) or len(input_point) < 2:
        show_popup(loc.get('invalid_point'), popup_type="error")
        return None, None
    if diameter_base <= 0 or diameter_top < 0 or height <= 0:
        show_popup(loc.get('diameter_base_positive') if diameter_base <= 0 else
                   loc.get('diameter_top_non_negative') if diameter_top < 0 else
                   loc.get('height_positive'), popup_type="error")
        return None, None
    if diameter_top > diameter_base:
        diameter_base, diameter_top = diameter_top, diameter_base
    try:
        k = 0.5 * math.sqrt(1 + height ** 2 * 4 / ((diameter_base - diameter_top) ** 2))
        R1 = diameter_base * k
        R2 = diameter_top * k
        theta = math.pi * diameter_base / R1
        if math.isinf(theta) or math.isnan(theta):
            show_popup(loc.get('invalid_result'), popup_type="error")
            return None, None
        if R1 <= 0 or R2 < 0 or math.isinf(R1) or math.isinf(R2) or math.isnan(R1) or math.isnan(R2):
            show_popup(loc.get('invalid_geometry'), popup_type="error")
            return None, None
        half_theta = theta / 2
        sin_half_theta = math.sin(half_theta)
        cos_half_theta = math.cos(half_theta)
        drs1 = R1 * sin_half_theta
        drs2 = R2 * sin_half_theta
        drc1 = R1 * cos_half_theta
        drc2 = R2 * cos_half_theta
        center = (input_point[0], input_point[1] - (R1 - (R1 - R2) * 0.5))
        p1 = APoint(center[0] + drs2, center[1] + drc2)
        p2 = APoint(center[0] + drs1, center[1] + drc1)
        p3 = APoint(center[0] - drs1, center[1] + drc1)
        p4 = APoint(center[0] - drs2, center[1] + drc2)
        bulge = math.tan(0.25 * theta)
        if math.isinf(bulge) or math.isnan(bulge):
            show_popup(loc.get('invalid_bulge'), popup_type="error")
            return None, None
        points_list = [p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1]]
        adoc = model.Document
        ensure_layer(adoc, layer_name)
        polyline = add_LWpolyline(model, points_list, layer_name)
        polyline.SetBulge(1, bulge)
        polyline.SetBulge(3, -bulge)
        return polyline, input_point
    except Exception:
        show_popup(loc.get('cone_sheet_error', ''), popup_type="error")
        return None, None


def polar_point(point: Union[APoint, Tuple[float, float]], distance: float, alpha: float = 0) -> Tuple[float, float]:
    """
    Находит точку в полярных координатах относительно начальной точки.

    Args:
        point: Начальная точка (объект APoint или кортеж (x, y)).
        distance: Расстояние от начальной точки.
        alpha: Угол в градусах (по умолчанию 0).

    Returns:
        Tuple[float, float]: Координаты новой точки (x, y).

    Notes:
        Если входные параметры некорректны, функция показывает всплывающее окно с запросом на исправление.
        При нажатии "Cancel" возвращается (0, 0).
        Сообщения выводятся на языке, установленном в объекте loc.
    """
    # Проверка параметра point
    while True:
        if point is None:
            result = show_popup(
                message=loc.get("invalid_point", "Точка должна быть определена. Введите корректную точку"),
                title=loc.get("error", "Ошибка"),
                popup_type="error",
                buttons=[loc.get("ok_button", "OK"), loc.get("cancel", "Отмена")]
            )
            if result == 0:  # Cancel
                return (0, 0)
            point = (0, 0)  # Установка значения по умолчанию для продолжения
            continue

        if isinstance(point, APoint):
            x0, y0 = point.x, point.y
            break
        elif isinstance(point, (tuple, list)) and len(point) == 2 and all(isinstance(coord, (int, float)) for coord in point):
            x0, y0 = point
            break
        else:
            result = show_popup(
                message=loc.get(
                    "invalid_points_type",
                    f"Точка должна быть типа APoint или кортеж (x, y), получено же: {type(point)}. Пожалуйста исправьте."
                ).format(type(point)),
                title=loc.get("error", "Ошибка"),
                popup_type="error",
                buttons=[loc.get("ok_button", "OK"), loc.get("cancel", "Отмена")]
            )
            if result == 0:  # Cancel
                return (0, 0)
            point = (0, 0)  # Установка значения по умолчанию для продолжения

    # Проверка distance
    while not isinstance(distance, (int, float)) or distance < 0:
        result = show_popup(
            message=loc.get(
                "length_positive_error",
                f"Расстояние должно быть положительным числом, получено: {distance}. Пожалуйста исправьте."
            ).format(distance),
            title=loc.get("error", "Ошибка"),
            popup_type="error",
            buttons=[loc.get("ok_button", "OK"), loc.get("cancel", "Отмена")]
        )
        if result == 0:  # Cancel
            return (0, 0)
        distance = 0  # Установка значения по умолчанию для продолжения

    # Проверка alpha
    while not isinstance(alpha, (int, float)):
        result = show_popup(
            message=loc.get(
                "invalid_angle",
                f"Угол должен быть числом, получено: {alpha}. Пожалуйста исправьте."
            ).format(alpha),
            title=loc.get("error", "Ошибка"),
            popup_type="error",
            buttons=[loc.get("ok_button", "OK"), loc.get("cancel", "Отмена")]
        )
        if result == 0:  # Cancel
            return (0, 0)
        alpha = 0  # Установка значения по умолчанию для продолжения

    # Вычисление новой точки
    alpha_rad = math.radians(alpha)
    x1 = x0 + distance * math.cos(alpha_rad)
    y1 = y0 + distance * math.sin(alpha_rad)

    return (x1, y1)

def at_addText(model: object, point: List[float | int], text: str = "", layer_name: str = "schrift",
               text_height: float = 30, text_angle: float = 0, text_alignment: int = 4) -> Optional[object]:
    """
    Создает текст в модельном пространстве в указанной точке.
    Параметры выравнивания:
        0: acAlignmentLeft
        1: acAlignmentCenter
        2: acAlignmentRight
        3: acAlignmentAligned
        4: acAlignmentMiddle
        5: acAlignmentFit
        6: acAlignmentTopLeft
        7: acAlignmentTopCenter
        8: acAlignmentTopRight
        9: acAlignmentMiddleLeft
        10: acAlignmentMiddleCenter
        11: acAlignmentMiddleRight
        12: acAlignmentBottomLeft
        13: acAlignmentBottomCenter
        14: acAlignmentBottomRight
    """
    try:
        # Проверка point
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            raise ValueError("Point must be a list or tuple with 3 coordinates [x, y, z]")
        point_array = [float(coord) for coord in point]
        print(f"at_addText: point_array: {point_array}, text: {text}, layer: {layer_name}")

        # Проверка слоя
        adoc = model.Document
        layer = adoc.Layers.Item(layer_name)
        if layer.Lock:
            print(f"Слой {layer_name} заблокирован, разблокировка...")
            layer.Lock = False

        # Создание текста
        point_variant = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point_array)
        text_obj = model.AddText(text, point_variant, text_height)

        # Проверка, что text_obj является объектом AutoCAD
        if isinstance(text_obj, str):
            raise RuntimeError(f"AddText вернул строку вместо объекта: {text_obj}")

        text_obj.Layer = layer_name
        text_obj.Alignment = text_alignment

        # Устанавливаем TextAlignmentPoint только для выравниваний, где это необходимо
        if text_alignment not in [0, 1, 2]:  # acAlignmentLeft, acAlignmentCenter, acAlignmentRight
            text_obj.TextAlignmentPoint = point_variant
        text_obj.Rotation = text_angle
        return text_obj

    except Exception as e:
        print(f"Ошибка в at_addText: {str(e)}")
        return None


if __name__ == "__main__":
    """
    Тест добавления текста
    """
    cad = ATCadInit()
    adoc, model = cad.adoc, cad.model
    input_point = at_point_input(adoc)
    # at_addText(model, input_point, "text", text_height=60, text_alignment=0)
    # cad.adoc.Regen(0)
    point2 = polar_point(APoint(input_point), distance=360, alpha=30)
    print(point2)
    add_line(adoc, APoint(input_point), point2)







