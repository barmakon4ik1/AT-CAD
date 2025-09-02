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
from typing import Optional, List, Tuple, Union, Dict
from pyautocad import APoint
from programms.at_utils import handle_errors
from win32com.client import VARIANT
import pythoncom
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "max_points_error": {
        "ru": "Максимальное количество точек - 5",
        "de": "Maximale Punktzahl - 5",
        "en": "Maximum number of points - 5"
    },
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "to_small_points": {
        "ru": "Мало точек",
        "de": "Zu wenig Punkten",
        "en": "To small points"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

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


def offset_point(input_point: Union[List[float], Tuple[float, ...], VARIANT],
                offset_x: float,
                offset_y: float,
                as_variant: bool = True) -> Union[List[float], VARIANT]:
    """
    Вычисляет координаты точки, смещенной от исходной на заданные значения по осям X и Y,
    с фиксированной координатой Z=0, и возвращает готовый COM VARIANT для AutoCAD или список [x, y].

    Args:
        input_point: Исходная точка (список, кортеж или готовый VARIANT).
        offset_x: Смещение по оси X.
        offset_y: Смещение по оси Y.
        as_variant: Если True, возвращает VARIANT [x, y, 0]; если False, возвращает [x, y].

    Returns:
        Union[List[float], VARIANT]: Список [x, y] или COM-массив double [x, y, 0].
    """
    # Если input_point — VARIANT, извлекаем значения через .value
    point_list = list(input_point.value) if isinstance(input_point, VARIANT) else list(input_point)

    # Используем только x, y (игнорируем z, если есть)
    x, y = point_list[0], point_list[1] if len(point_list) > 1 else point_list[0]

    # Вычисляем новые координаты
    new_x = x + offset_x
    new_y = y + offset_y

    # Возвращаем результат
    if as_variant:
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [new_x, new_y, 0.0])
    return [new_x, new_y]

def polar_point(base_point: Union[List[float], Tuple[float, ...], VARIANT],
                distance: float,
                alpha: float,
                as_variant: bool = True) -> Union[List[float], VARIANT]:
    """
    Вычисляет координаты точки, расположенной на заданном расстоянии и под углом от базовой точки,
    и возвращает готовый COM VARIANT для AutoCAD или список [x, y].

    Args:
        base_point: Базовая точка (список, кортеж или готовый VARIANT).
        distance: Расстояние до новой точки.
        alpha: Угол в градусах (0° = по оси X, 90° = по оси Y).
        as_variant: Если True, возвращает VARIANT [x, y, 0]; если False, возвращает [x, y].

    Returns:
        Union[List[float], VARIANT]: Список [x, y] или COM-массив double [x, y, 0].
    """
    # Если base_point — VARIANT, извлекаем значения через .value
    bp_list = list(base_point.value) if isinstance(base_point, VARIANT) else list(base_point)

    # Используем только x, y (игнорируем z, если есть)
    x, y = bp_list[0], bp_list[1] if len(bp_list) > 1 else bp_list[0]

    # Переводим угол в радианы
    rad = math.radians(alpha)

    # Вычисляем новые координаты
    new_x = x + distance * math.cos(rad)
    new_y = y + distance * math.sin(rad)

    # Возвращаем результат
    if as_variant:
        return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [new_x, new_y, 0.0])
    return [new_x, new_y]

def build_polyline_list(plate_data: Dict) -> Optional[List[List[float]]]:
    """
    Создаёт список точек для полилинии на основе данных листа.

    Args:
        plate_data: Словарь с данными (insert_point, point_list, material, thickness, melt_no, allowance).

    Returns:
        List[List[float]]: Список точек в формате [[x1, y1], [x2, y2], ...] или None при ошибке.
    """
    try:
        # Инициализация списка полилинии
        polyline_list = []

        # Извлекаем данные
        insert_point = plate_data.get("insert_point")
        point_list = plate_data.get("point_list")

        # Проверка наличия точек
        if not point_list:
            show_popup(loc.get("to_small_points", "Мало точек"), popup_type="error")
            return None

        # Начальная точка (p0) из insert_point
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) < 2:
            show_popup(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"), popup_type="error")
            return None
        p0x, p0y = map(float, insert_point[:2])  # Берём только x, y
        p0 = [p0x, p0y]
        polyline_list.append(p0)

        # Первая пара размеров (обязательная)
        l, h = point_list[0][0], point_list[0][1]
        p1 = offset_point(p0, l, 0, as_variant=False)  # Двигаемся вправо на l
        p2 = polar_point(p1, h, 90, as_variant=False)  # Двигаемся вверх на h
        polyline_list.append(p1)
        polyline_list.append(p2)

        # Обработка дополнительных пар размеров
        prev_h = h  # Высота предыдущей пары
        for i in range(1, len(point_list)):
            if i >= 5:  # Ограничение на максимум 5 пар точек
                show_popup(loc.get("max_points_error", "Максимальное количество точек - 5"), popup_type="error")
                return None
            l_i, h_i = point_list[i][0], point_list[i][1]
            # Точка на уровне prev_h
            p_next = offset_point(p0, l - l_i, prev_h, as_variant=False)
            polyline_list.append(p_next)
            # Точка на уровне h_i
            p_next = offset_point(p0, l - l_i, h_i, as_variant=False)
            polyline_list.append(p_next)
            prev_h = h_i  # Обновляем prev_h для следующей итерации

        # Закрытие полилинии: возвращаемся к точке на уровне h_i от p0
        if len(point_list) > 1:
            last_h = point_list[-1][1]  # Высота последней пары
            p_close = polar_point(p0, last_h, 90, as_variant=False)
            polyline_list.append(p_close)
        else:
            p_close = polar_point(p0, h, 90, as_variant=False)
            polyline_list.append(p_close)

        return polyline_list

    except Exception as e:
        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        return None

def convert_to_variant_points(polyline_list: List[List[float]]) -> List:
    """
    Преобразует список точек [[x, y], ...] в список VARIANT для AutoCAD.

    Args:
        polyline_list: Список точек в формате [[x1, y1], [x2, y2], ...].

    Returns:
        List: Список точек в формате VARIANT.
    """
    if polyline_list is None:
        print("Error: polyline_list is None")  # Отладка
        return []
    return [ensure_point_variant([x, y, 0.0]) for x, y in polyline_list]