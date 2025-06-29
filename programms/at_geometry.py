"""
Модуль для геометрических вычислений.
"""

import math
from typing import Optional, List, Tuple, Union

from pyautocad import APoint

from programms.at_utils import handle_errors


@handle_errors
def calculate_angles(angle: int, unit: int, A: Tuple[float, float], B: Tuple[float, float],
                    C: Tuple[float, float]) -> Union[float, Tuple[float, float, float]]:
    """
    Вычисляет углы треугольника по трем точкам.
    """
    x0, y0 = A
    x1, y1 = B
    x2, y2 = C
    AB = (x1 - x0, y1 - y0)
    AC = (x2 - x0, y2 - y0)
    BA = (x0 - x1, y0 - y1)
    BC = (x2 - x1, y2 - y1)
    CA = (x0 - x2, y0 - y2)
    CB = (x1 - x2, y1 - y2)

    def dot_product(v1, v2):
        return v1[0] * v2[0] + v1[1] * v2[1]

    def vector_length(v):
        return math.sqrt(v[0] ** 2 + v[1] ** 2)

    cos_A = dot_product(AB, AC) / (vector_length(AB) * vector_length(AC))
    cos_B = dot_product(BA, BC) / (vector_length(BA) * vector_length(BC))
    cos_C = dot_product(CA, CB) / (vector_length(CA) * vector_length(CB))
    angle_A = math.acos(max(min(cos_A, 1), -1))
    angle_B = math.acos(max(min(cos_B, 1), -1))
    angle_C = math.acos(max(min(cos_C, 1), -1))
    if unit == 0:
        angle_A, angle_B, angle_C = map(math.degrees, [angle_A, angle_B, angle_C])
    return (angle_A, angle_B, angle_C) if angle == 0 else [angle_A, angle_B, angle_C][angle - 1]


@handle_errors
def deg_to_rad(angle: float) -> Optional[float]:
    """
    Конвертирует угол из градусов в радианы.
    """
    return math.radians(angle)


@handle_errors
def at_bulge(start_point: Tuple[float, float], end_point: Tuple[float, float],
             center: Tuple[float, float]) -> Optional[float]:
    """
    Вычисляет коэффициент выпуклости (bulge) для дуги.
    """
    angle = calculate_angles(3, 1, start_point, end_point, center)
    return math.tan(angle / 4)


@handle_errors
def find_intersection_points(pt1: Tuple[float, float], r1: float, pt2: Tuple[float, float], r2: float) -> Optional[
    List[Tuple[float, float]]]:
    """
    Находит точки пересечения двух окружностей.
    """
    x1, y1 = pt1
    x2, y2 = pt2
    d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if d > r1 + r2 or d < abs(r1 - r2) or (d == 0 and r1 == r2):
        return None
    x = (d ** 2 + r1 ** 2 - r2 ** 2) / (2 * d)
    discriminant = r1 ** 2 - x ** 2
    if discriminant < 0:
        return None
    y = math.sqrt(discriminant)
    cos_theta = (x2 - x1) / d if d != 0 else 1
    sin_theta = (y2 - y1) / d if d != 0 else 0
    if abs(discriminant) < 1e-10:
        px = x1 + x * cos_theta
        py = y1 + x * sin_theta
        return [(px, py)]
    px1 = x1 + x * cos_theta - y * sin_theta
    py1 = y1 + x * sin_theta + y * cos_theta
    px2 = x1 + x * cos_theta + y * sin_theta
    py2 = y1 + x * sin_theta - y * cos_theta
    return [(px1, py1), (px2, py2)]


@handle_errors
def add_rectangle_points(point: APoint, width: float, height: float, point_direction: str = "left_bottom") -> List[float]:
    """
    Вычисляет координаты точек прямоугольника.
    """
    x, y = float(point[0]), float(point[1])
    if point_direction == "right_bottom":
        x0, y0 = x - width, y
    elif point_direction == "center":
        x0, y0 = x - width / 2.0, y - height / 2.0
    elif point_direction == "left_top":
        x0, y0 = x, y - height
    elif point_direction == "right_top":
        x0, y0 = x - width, y - height
    else:
        x0, y0 = x, y
    x1, y1 = x0 + width, y0
    x2, y2 = x1, y0 + height
    x3, y3 = x0, y0 + height
    return [float(x0), float(y0), float(x1), float(y1), float(x2), float(y2), float(x3), float(y3)]
