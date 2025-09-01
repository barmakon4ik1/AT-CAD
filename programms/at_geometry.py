# -*- coding: utf-8 -*-
"""
Модуль: at_geometry.py
Путь: programms\at_geometry.py

Модуль для геометрических вычислений.

Содержит функции для вычисления углов треугольника, конвертации углов,
вычисления коэффициента bulge дуги, нахождения точек пересечения окружностей,
вычисления точек прямоугольника и функцию для вычисления координат точки
по полярным координатам с возвратом COM VARIANT для AutoCAD.

Автор: Alexander Tutubalin
Дата создания: 13.08.2025
"""

import math
from typing import Optional, List, Tuple, Union
from pyautocad import APoint
from programms.at_utils import handle_errors
from win32com.client import VARIANT
import pythoncom


def ensure_point_variant(point: Union[List[float], Tuple[float, ...], VARIANT]) -> VARIANT:
    """
    Приводит любую точку к COM VARIANT (VT_ARRAY | VT_R8) в формате [x, y, z].

    Args:
        point: Может быть готовым VARIANT или любым итерируемым с координатами (список, кортеж, генератор).

    Returns:
        VARIANT: COM-массив double [x, y, z].

    Примечания:
        - Если передан готовый VARIANT, он возвращается без изменений.
        - Если координат меньше трёх, недостающие заполняются нулями.
        - Если координат больше трёх, лишние отбрасываются.
        - Все значения преобразуются в float.
    """
    if isinstance(point, VARIANT):
        return point
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(map(float, (list(point) + [0, 0, 0])[:3])))


@handle_errors
def calculate_angles(angle: int, unit: int, A: Tuple[float, float], B: Tuple[float, float],
                    C: Tuple[float, float]) -> Union[float, Tuple[float, float, float]]:
    """
    Вычисляет углы треугольника по трём точкам.

    Args:
        angle: 0 для возврата всех углов, 1–3 для возврата одного из углов.
        unit: 0 — результат в градусах, 1 — в радианах.
        A, B, C: координаты вершин треугольника.

    Returns:
        Угол или кортеж углов в зависимости от параметра angle.
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

    Args:
        angle: Угол в градусах.

    Returns:
        Угол в радианах.
    """
    return math.radians(angle)


@handle_errors
def at_bulge(start_point: Tuple[float, float], end_point: Tuple[float, float],
             center: Tuple[float, float]) -> Optional[float]:
    """
    Вычисляет коэффициент выпуклости (bulge) для дуги.

    Args:
        start_point: Начальная точка дуги (x, y).
        end_point: Конечная точка дуги (x, y).
        center: Точка центра окружности (x, y).

    Returns:
        Коэффициент выпуклости (float).
    """
    angle = calculate_angles(3, 1, start_point, end_point, center)
    return math.tan(angle / 4)


@handle_errors
def find_intersection_points(pt1: Tuple[float, float], r1: float,
                             pt2: Tuple[float, float], r2: float) -> Optional[List[Tuple[float, float]]]:
    """
    Находит точки пересечения двух окружностей.

    Args:
        pt1: Центр первой окружности (x, y).
        r1: Радиус первой окружности.
        pt2: Центр второй окружности (x, y).
        r2: Радиус второй окружности.

    Returns:
        Список точек пересечения [(x1, y1), (x2, y2)] или None.
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


def add_rectangle_points(point: APoint, width: float, height: float, point_direction: str = "left_bottom") -> VARIANT:
    """
    Вычисляет координаты точек прямоугольника и возвращает COM VARIANT.

    Args:
        point: Начальная точка (APoint или VARIANT).
        width: Ширина прямоугольника.
        height: Высота прямоугольника.
        point_direction: Позиция точки относительно прямоугольника
                         ("left_bottom", "right_bottom", "center", "left_top", "right_top").

    Returns:
        VARIANT: COM-массив double [x0, y0, x1, y1, x2, y2, x3, y3].
    """
    try:
        # Если point — VARIANT, извлекаем координаты
        if isinstance(point, VARIANT):
            x, y = point.value[0], point.value[1]
        else:
            x, y = float(point[0]), float(point[1])

        # Вычисляем координаты вершин
        if point_direction == "right_bottom":
            x0, y0 = x - width, y
        elif point_direction == "center":
            x0, y0 = x - width / 2.0, y - height / 2.0
        elif point_direction == "left_top":
            x0, y0 = x, y - height
        elif point_direction == "right_top":
            x0, y0 = x - width, y - height
        else:  # left_bottom
            x0, y0 = x, y
        x1, y1 = x0 + width, y0
        x2, y2 = x1, y0 + height
        x3, y3 = x0, y0 + height
        points = [float(x0), float(y0), float(x1), float(y1), float(x2), float(y2), float(x3), float(y3)]

        # Возвращаем VARIANT
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, points)
    except Exception as e:
        print(f"Error in add_rectangle_points: {e}")
        return None


def polar_point(base_point: Union[List[float], Tuple[float, ...], VARIANT],
                distance: float,
                alpha: float,
                as_variant=True) -> list | VARIANT:
    """
    Вычисляет координаты точки, расположенной на заданном расстоянии и под углом от базовой точки,
    и возвращает готовый COM VARIANT для AutoCAD.

    Args:
        base_point: Базовая точка (список, кортеж или готовый VARIANT).
        distance: Расстояние до новой точки.
        alpha: Угол в градусах (0° = по оси X, 90° = по оси Y).
        as_variant: True или False
    Returns:
        VARIANT: COM-массив double [x, y, z], готовый для передачи в AutoCAD API.

    Примечания:
        - Угол alpha интерпретируется в градусах, внутри функции переводится в радианы.
        - Если base_point содержит менее трёх координат, недостающие будут заполнены нулями.

    """
    # Если base_point — VARIANT, извлекаем значения через .value
    bp_list = list(base_point.value) if isinstance(base_point, VARIANT) else list(base_point)

    # Дополняем координаты до [x, y, z]
    while len(bp_list) < 3:
        bp_list.append(0.0)

    # Переводим угол в радианы
    rad = math.radians(alpha)

    # Вычисляем новые координаты
    new_x = bp_list[0] + distance * math.cos(rad)
    new_y = bp_list[1] + distance * math.sin(rad)
    new_z = bp_list[2]

    # Возвращаем готовый COM VARIANT
    if as_variant:
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [new_x, new_y, new_z])
    else:
        return [new_x, new_y, new_z]

def offset_point(input_point: Union[List[float], Tuple[float, ...], VARIANT],
                offset_x: float,
                offset_y: float,
                as_variant=True) -> list | VARIANT:
    """
    Вычисляет координаты точки, смещенной от исходной на заданные значения по осям X и Y,
    с фиксированной координатой Z=0, и возвращает готовый COM VARIANT для AutoCAD.

    Args:
        input_point: Исходная точка (список, кортеж или готовый VARIANT).
        offset_x: Смещение по оси X.
        offset_y: Смещение по оси Y.
        as_variant: True или False
    Returns:
        VARIANT: COM-массив double [x, y, z], готовый для передачи в AutoCAD API.

    Примечания:
        - Если input_point содержит менее трёх координат, недостающие будут заполнены нулями.
        - Координата Z новой точки всегда равна 0.
    """
    # Если input_point — VARIANT, извлекаем значения через .value
    point_list = list(input_point.value) if isinstance(input_point, VARIANT) else list(input_point)

    # Дополняем координаты до [x, y, z]
    while len(point_list) < 3:
        point_list.append(0.0)

    # Вычисляем новые координаты
    new_x = point_list[0] + offset_x
    new_y = point_list[1] + offset_y
    new_z = 0.0

    # Возвращаем готовый COM VARIANT
    if as_variant:
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [new_x, new_y, new_z])
    else:
        return [new_x, new_y, new_z]