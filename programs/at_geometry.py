# -*- coding: utf-8 -*-
"""
Модуль: at_geometry.py
Путь: programs\at_geometry.py

Модуль для геометрических вычислений.

Содержит функции для вычисления углов треугольника, конвертации углов,
вычисления коэффициента bulge дуги, нахождения точек пересечения окружностей,
вычисления точек прямоугольника и функцию для вычисления координат точки
по полярным координатам с возвратом COM VARIANT для AutoCAD.

Автор: Alexander Tutubalin
Дата создания: 13.08.2025
"""

import math
from pprint import pprint
from typing import Optional, List, Tuple, Union, Dict
from win32com.client import VARIANT
import pythoncom
from locales.at_translations import loc
from windows.at_gui_utils import show_popup
from errors.at_errors import DataError, GeometryError

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


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """
    Безопасное деление, чтобы избежать ZeroDivisionError.
    Возвращает default, если делитель близок к нулю.
    """
    try:
        if abs(b) < 1e-12:
            return default
        return a / b
    except ZeroDivisionError:
        return default


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


def calculate_angles(angle: int, unit: int, A: Tuple[float, float], B: Tuple[float, float],
                    C: Tuple[float, float]) -> Union[float, Tuple[float, float, float]]:
    """
    Вычисляет углы треугольника по трём точкам.

    Args:
        C: координата вершины треугольника.
        B: координата вершины треугольника.
        A: координата вершины треугольника.
        angle: 0 для возврата всех углов, 1–3 для возврата одного из углов.
        unit: 0 — результат в градусах, 1 — в радианах.

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

    denom_A = vector_length(AB) * vector_length(AC)
    denom_B = vector_length(BA) * vector_length(BC)
    denom_C = vector_length(CA) * vector_length(CB)

    cos_A = safe_div(dot_product(AB, AC), denom_A, 0.0)
    cos_B = safe_div(dot_product(BA, BC), denom_B, 0.0)
    cos_C = safe_div(dot_product(CA, CB), denom_C, 0.0)

    # clamp to [-1,1]
    cos_A = max(min(cos_A, 1.0), -1.0)
    cos_B = max(min(cos_B, 1.0), -1.0)
    cos_C = max(min(cos_C, 1.0), -1.0)

    angle_A = math.acos(cos_A)
    angle_B = math.acos(cos_B)
    angle_C = math.acos(cos_C)
    if unit == 0:
        angle_A, angle_B, angle_C = map(math.degrees, [angle_A, angle_B, angle_C])
    return (angle_A, angle_B, angle_C) if angle == 0 else [angle_A, angle_B, angle_C][angle - 1]


# def deg_to_rad(angle: float) -> Optional[float]:
#     """
#     Конвертирует угол из градусов в радианы.
#
#     Args:
#         angle: Угол в градусах.
#
#     Returns:
#         Угол в радианах.
#     """
#     return math.radians(angle)
#
# def rad_to_deg(angle: float) -> Optional[float]:
#     """
#     Конвертирует угол из радиан в градусы.
#
#     Args:
#         angle: Угол в радианах.
#
#     Returns:
#         Угол в градусах.
#     """
#     return math.degrees(angle)


def circle_center_from_points(A: Tuple[float, float],
                              B: Tuple[float, float],
                              C: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """
    Находит центр окружности, проходящей через три точки.

    Args:
        A, B, C: Три точки (x, y).

    Returns:
        (cx, cy): Координаты центра окружности или None, если точки на одной прямой.
    """
    (x1, y1), (x2, y2), (x3, y3) = A, B, C

    # Определяем знаменатель
    d = 2 * (x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))
    if abs(d) < 1e-12:
        return None  # точки на одной прямой

    ux = ((x1**2 + y1**2)*(y2 - y3) +
          (x2**2 + y2**2)*(y3 - y1) +
          (x3**2 + y3**2)*(y1 - y2)) / d
    uy = ((x1**2 + y1**2)*(x3 - x2) +
          (x2**2 + y2**2)*(x1 - x3) +
          (x3**2 + y3**2)*(x2 - x1)) / d

    return (ux, uy)


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


def bulge_from_center(start: Tuple[float, float],
                      end: Tuple[float, float],
                      center: Tuple[float, float],
                      clockwise: bool = False) -> Optional[float]:
    """
    Вычисляет bulge (коэффициент выпуклости) для дуги заданной начальной и
    конечной точками и центром окружности.

    Bulge = tan(sweep / 4), где sweep — угол дуги (в радианах).
    sweep выбирается так, чтобы направление дуги соответствовало параметру clockwise:
      - clockwise=False -> выбираем положительный (CCW) sweep (0..2π)
      - clockwise=True  -> выбираем отрицательный (CW) sweep (0..-2π)

    Args:
        start: (x, y) — начальная точка дуги.
        end: (x, y) — конечная точка дуги.
        center: (x, y) — центр окружности, которой принадлежит дуга.
        clockwise: направление обхода дуги (False — CCW, True — CW).

    Returns:
        float: значение bulge (может быть отрицательным для CW-дуг).
    """
    # углы радианы относительно центра
    ang1 = math.atan2(start[1] - center[1], start[0] - center[0])
    ang2 = math.atan2(end[1] - center[1], end[0] - center[0])

    sweep = ang2 - ang1
    if not clockwise:
        # хотим положительный обход (CCW)
        if sweep <= 0:
            sweep += 2.0 * math.pi
    else:
        # хотим отрицательный обход (CW)
        if sweep >= 0:
            sweep -= 2.0 * math.pi

    # защищаемся от нулевого угла
    if abs(sweep) < 1e-12:
        return 0.0

    return math.tan(sweep / 4.0)


def bulge_from_three_points(start: Tuple[float, float],
                            mid: Tuple[float, float],
                            end: Tuple[float, float]) -> Optional[float]:
    """
    Вычисляет bulge для дуги, проходящей через три точки (start, mid, end).
    Точка `mid` должна лежать на самой дуге (не на хорде).

    Алгоритм:
      1. Находит центр описанной окружности (circumcenter) по трём точкам.
      2. Определяет, лежит ли средняя точка между start->end по направлению CCW.
         Если да — считаем направление CCW, иначе — CW.
      3. Вызывает bulge_from_center для вычисления bulge.

    Args:
        start: (x, y) — начало дуги.
        mid: (x, y) — точка на дуге (не на хорде).
        end: (x, y) — конец дуги.

    Returns:
        float: bulge (или None при ошибке / вырожденных точках).
    """
    ax, ay = start
    bx, by = mid
    cx, cy = end

    # Вычисление центра описанной окружности (формула через определитель)
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        # Точки почти коллинеарны — вернём 0.0 как безопасный bulge
        return 0.0

    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy

    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    center = (ux, uy)

    # углы относительно центра
    ang_start = math.atan2(start[1] - center[1], start[0] - center[0])
    ang_mid = math.atan2(mid[1] - center[1], mid[0] - center[0])
    ang_end = math.atan2(end[1] - center[1], end[0] - center[0])

    # нормализуем в [0, 2pi)
    def _norm(a: float) -> float:
        v = a % (2.0 * math.pi)
        if v < 0:
            v += 2.0 * math.pi
        return v

    s = _norm(ang_start)
    m = _norm(ang_mid)
    e = _norm(ang_end)

    # проверка, лежит ли m между s->e в CCW направлении
    def _between_ccw(a: float, b: float, t: float) -> bool:
        # возвращает True если t лежит на дуге CCW от a до b (включая границы)
        if a <= b:
            return a <= t <= b
        # обёрнутый случай
        return t >= a or t <= b

    ccw_contains = _between_ccw(s, e, m)
    clockwise = not ccw_contains  # если mid не в CCW промежутке, значит нужная дуга — в CW направлении

    return bulge_from_center(start, end, center, clockwise=clockwise)



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
    x = safe_div((d ** 2 + r1 ** 2 - r2 ** 2), (2 * d), 0.0)
    discriminant = r1 ** 2 - x ** 2
    if discriminant < 0:
        return None
    y = math.sqrt(discriminant)
    cos_theta = safe_div((x2 - x1), d, 1.0)
    sin_theta = safe_div((y2 - y1), d, 0.0)
    if abs(discriminant) < 1e-10:
        px = x1 + x * cos_theta
        py = y1 + x * sin_theta
        return [(px, py)]
    px1 = x1 + x * cos_theta - y * sin_theta
    py1 = y1 + x * sin_theta + y * cos_theta
    px2 = x1 + x * cos_theta + y * sin_theta
    py2 = y1 + x * sin_theta - y * cos_theta
    return [(px1, py1), (px2, py2)]


def add_rectangle_points(point:Union[List[float], Tuple[float, ...], VARIANT], width: float, height: float, point_direction: str = "left_bottom") -> VARIANT | None:
    """
    Вычисляет координаты точек прямоугольника и возвращает COM VARIANT.

    Args:
        point: Начальная точка (VARIANT).
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

def build_polyline_list(data: Dict) -> Optional[List[List[float]]]:
    """
    Создаёт список точек для полилинии на основе данных листа.

    Args:
        data: Словарь с данными (insert_point, point_list, material, thickness, melt_no, allowance).

    Returns:
        List[List[float]]: Список точек в формате [[x1, y1], [x2, y2], ...] или None при ошибке.
    """
    try:
        # Инициализация списка полилинии
        polyline_list = []

        # Извлекаем данные
        insert_point = data.get("insert_point")
        point_list = data.get("point_list")

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


def get_unwrapped_points(D, L, A_deg, clockwise=True):
    """
    Возвращает список (угол, x, y) вдоль развертки цилиндра.

    D  - диаметр цилиндра
    L  - высота цилиндра (не используется, но для совместимости)
    A_deg - угол разреза в градусах
    clockwise - направление обхода:
                False = против часовой стрелки (по умолчанию)
                True  = по часовой стрелке
    """
    unwrapped_length = math.pi * D
    deg_to_len = lambda angle: (angle % 360) / 360 * unwrapped_length
    y = 0  # Все точки на нижней линии развёртки

    # Базовые углы
    base_angles = [0, 90, 180, 270, 360]

    # Нормализуем A
    A = A_deg % 360

    # Выбор правил в зависимости от направления
    distance = (lambda a1, a2: (a1 - a2) % 360) if clockwise else (lambda a1, a2: (a2 - a1) % 360)
    shift    = (lambda ang: (A - ang) % 360)    if clockwise else (lambda ang: (ang - A) % 360)

    # Определить набор углов
    marked_angles = sorted(set(base_angles + [A]), key=lambda ang: distance(A, ang))

    # Замкнуть на A
    if marked_angles[0] != A:
        marked_angles = [A] + marked_angles
    if marked_angles[-1] != A:
        marked_angles.append(A)

    # Преобразовать углы в координаты
    points = []
    for ang in marked_angles:
        x = deg_to_len(shift(ang))
        points.append((ang % 360, x, y))

    return points

def get_insert_point_on_shell(
    insert_point: Tuple[float, float, float],
    diameter: float,
    length: float,
    angle_deg: float,
    offset_axial: float = 0.0,
    axial_shift: float = 0.0,
    weld_allowance_top: float = 0.0,
    weld_allowance_bottom: float = 0.0
) -> Tuple[float, float, float]:
    """
    Возвращает точку вставки выреза на развертке цилиндра.

    :param insert_point: Базовая точка вставки прямоугольника оболочки [x, y, z]
    :param diameter: диаметр цилиндра (D)
    :param length: длина цилиндра (L)
    :param angle_deg: угол поворота (0° = X=0 на развёртке)
    :param offset_axial: осевой отступ (мм) от нижнего края цилиндра
    :param axial_shift: дополнительное смещение вдоль оси (мм)
    :param weld_allowance_top: припуск сверху (мм)
    :param weld_allowance_bottom: припуск снизу (мм)
    :return: координаты точки вставки [X, Y, Z]
    """
    # базовая точка развёртки
    x0, y0, z0 = insert_point

    # ширина развёртки (длина окружности)
    width = math.pi * diameter

    # координата по окружности (X)
    X = (angle_deg % 360.0) / 360.0 * width

    # координата по оси (Y)
    Y = weld_allowance_bottom + offset_axial + axial_shift

    return x0 + X, y0 + Y, z0


def angle_to_unroll_x(angle_deg, diameter, cut_angle_ref=0.0, unroll_dir="CW"):
    """
    Перевод угла окружности цилиндра в координату X на развёртке.

    :param angle_deg: Исходный угол (в системе цилиндра)
    :param diameter: диаметр цилиндра
    :param cut_angle_ref: угол, по которому сделан разрез (левый край развёртки)
    :param unroll_dir: направление разворота: "CW" или "CCW"
    :return: координата X (мм)
    """
    W = math.pi * diameter

    # 1. относительный угол
    alpha_rel = (angle_deg - cut_angle_ref) % 360

    # 2. направление
    if unroll_dir.upper() == "CCW":
        alpha_rel = (360 - alpha_rel) % 360

    # 3. преобразуем в мм
    X = alpha_rel / 360.0 * W
    return X

def distance_2points(p1, p2):
    """
    Находит расстояние между двумя точками.
    Поддерживаем форматы:
      (x, y), [x, y], (x, y, z), [x, y, z]

    Если z отсутствует — используется z=0.
    """

    # Приводим к списку
    p1 = normalize_point(p1)
    p2 = normalize_point(p2)

    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    dz = p1[2] - p2[2]
    return math.hypot(dx, dy, dz)  # sqrt(dx*dx + dy*dy + dz*dz)

def bulge_chord(radius: float, chord: float) -> float:
    return math.tan(0.5 * math.asin(chord / (2 * radius)))

def normalize_point(p):
    """
    Превращает p в точку (x, y, z), даже если p имеет лишние вложения.
    Поддерживает форматы:
    [x, y], (x, y), (x, y, z), [ [x, y] ], ( [x, y, z], ), etc.
    """
    # Распаковка вложенных структур пока не доберёмся до списка/кортежа из чисел
    while isinstance(p, (list, tuple)) and len(p) == 1 and isinstance(p[0], (list, tuple)):
        p = p[0]

    # Теперь p должен быть списком или кортежем чисел
    if len(p) == 2:
        return (p[0], p[1], 0.0)
    if len(p) == 3:
        return (p[0], p[1], p[2])

    raise ValueError(f"Bad point format: {p}")

def make_cone_arc_points(
    apex: Tuple[float, float],
    R: float,
    theta_rad: float,
    N: int
) -> List[Tuple[float, float]]:
    """
    Создаёт N+1 точек внешней дуги развертки конуса.

    Дуга располагается так:
        - апекс в точке (apex_x, apex_y)
        - дуга симметрична относительно вертикальной оси, проходящей через апекс
        - крайние точки: углы -theta_rad/2 и +theta_rad/2

    Параметры:
        apex       - координаты апекса (x, y)
        R          - радиус внешней дуги (первая образующая)
        theta_rad  - центральный угол развертки (в радианах)
        N          - количество делений дуги

    Возвращает:
        Список из N+1 точек [(x0,y0), (x1,y1), ... , (xN, yN)]
    """

    ax, ay = apex

    # начальный угол (левая точка)
    angle_start = -theta_rad / 2

    # шаг угла
    angle_step = theta_rad / N

    pts = []

    for i in range(N + 1):
        angle = angle_start + i * angle_step
        # x = apex.x + R * sin(angle)
        # y = apex.y + R * cos(angle)
        x = ax + R * math.sin(angle)
        y = ay + R * math.cos(angle)
        pts.append((x, y))

    return pts


def fillet_points(A, B, C, r):
    """
    Возвращает точки касания дуги радиуса r
    для угла ABC (90°)
    """
    BA = (A[0] - B[0], A[1] - B[1])
    BC = (C[0] - B[0], C[1] - B[1])

    len_BA = math.hypot(*BA)
    len_BC = math.hypot(*BC)

    uBA = (BA[0] / len_BA, BA[1] / len_BA)
    uBC = (BC[0] / len_BC, BC[1] / len_BC)

    t1 = (B[0] + uBA[0] * r, B[1] + uBA[1] * r)
    t2 = (B[0] + uBC[0] * r, B[1] + uBC[1] * r)

    return t1, t2


Point = Tuple[float, float]
Vertex = Tuple[float, float, float]

def _unit_vector(a: Point, b: Point) -> Point:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    l = math.hypot(dx, dy)
    return (dx / l, dy / l)

def _bulge_for_90(p1: Point, p2: Point, p3: Point) -> float:
    """
    Возвращает bulge со знаком,
    соответствующим направлению поворота.
    """
    cross = (
            (p2[0] - p1[0]) * (p3[1] - p2[1])
            - (p2[1] - p1[1]) * (p3[0] - p2[0])
    )
    sign = -1.0 if cross > 0 else 1.0
    return sign * math.tan(math.radians(22.5))


class PolylineBuilder:
    """
    Builder для LWPolyline с поддержкой:
    - прямых сегментов
    - скруглений (r > 0)
    - фасок (r < 0)
    """

    def __init__(self, start: Point):
        self._vertices: List[Vertex] = [(start[0], start[1], 0.0)]
        self._last_point: Point = start

    # --------------------------------------------------
    # Прямой сегмент
    # --------------------------------------------------
    def line_to(self, p: Point):
        self._vertices.append((p[0], p[1], 0.0))
        self._last_point = p
        return self

    # --------------------------------------------------
    # Угол: прямой / скругление / фаска
    # --------------------------------------------------
    def corner(self, vertex: Point, next_point: Point, r: float):
        """
        Обрабатывает угол в точке vertex между последним сегментом и сегментом к next_point.

        r = 0  → прямой угол
        r > 0  → скругление радиусом r
        r < 0  → фаска длиной |r|
        """
        prev = self._last_point
        curr = vertex
        nextp = next_point

        # --- прямой угол ---
        if r == 0:
            self.line_to(curr)
            return self

        # --- фаска или скругление ---
        t1, t2 = fillet_points(prev, curr, nextp, abs(r))

        if r > 0:
            # скругление — ставим bulge на первый сегмент
            BULGE_90 = -math.tan(math.radians(22.5))  # для 90° угла
            self._vertices.append((t1[0], t1[1], BULGE_90))
        else:
            # фаска — просто прямая, bulge=0
            self._vertices.append((t1[0], t1[1], 0.0))

        # вторая точка касания — всегда обычная вершина
        self._vertices.append((t2[0], t2[1], 0.0))
        self._last_point = t2
        return self

    def arc_to(self, pt, bulge):
        self._vertices.append((pt[0], pt[1], float(bulge)))


    # --------------------------------------------------
    def close(self):
        if self._vertices[0][:2] != self._vertices[-1][:2]:
            x0, y0, _ = self._vertices[0]
            self._vertices.append((x0, y0, 0.0))
        return self

    def vertices(self) -> List[Vertex]:
        return self._vertices

def circle_line_intersection(p01, C, D, A):
        """
        Функция нахождения точки пересечения окружности с наклонной линией
        (точка p1 на развертке мостика типа 5)
        p01 = (x01, y01)  координаты точки начала наклонной прямой
        C   = (xc, yc)    координаты центра окружности
        D   = диаметр окружности
        A   = угол наклона прямой к горизонтали в радианах

        Returns:
            p1 (x1, y1),
            (H  = yc - y1,
            Lx = xc - x1,
            Ld = abs(xc - x1)) - включить, если надо
        """
        x0, y0 = p01
        xc, yc = C
        R = D / 2.0

        t = math.tan(A)

        # квадратное уравнение: (1+t^2)x^2 - 2*(xc + t^2*x0 + t*(yc - y0))*x + (...) = 0
        under_sqrt = R * R * (1 + t * t) - (yc - y0 - t * (xc - x0)) ** 2

        if under_sqrt < 0:
            raise ValueError("Нет допустимого пересечения")

        sqrt_val = math.sqrt(under_sqrt)

        # два решения для x
        x1 = (xc + t * t * x0 + t * (yc - y0)) + sqrt_val
        x2 = (xc + t * t * x0 + t * (yc - y0)) - sqrt_val

        x1 /= (1 + t * t)
        x2 /= (1 + t * t)

        # соответствующие y
        y1 = y0 + t * (x1 - x0)
        y2 = y0 + t * (x2 - x0)

        # выбираем точку, ближайшую к исходной точке
        d1 = math.hypot(x1 - x0, y1 - y0)
        d2 = math.hypot(x2 - x0, y2 - y0)

        if d1 < d2:
            x, y = x1, y1
        else:
            x, y = x2, y2

        H = yc - y
        # ld = xc - x
        # Lx = R - Ld

        return x, y


def triangle(data: dict) -> dict:
    """
    Универсальный метод решения плоского треугольника.

    ---------------------------
    Геометрические обозначения
    ---------------------------

    Используется каноническая схема:

                 γ
                /|
               / |
            b /  | a
             /   |
            /____|
           α  c  β

    Соответствие сторон и углов:
        • a  ↔  α (alpha) — угол, противолежащий стороне a
        • b  ↔  β (beta)  — угол, противолежащий стороне b
        • c  ↔  γ (gamma) — угол, противолежащий стороне c

    ---------------------------
    Входные данные
    ---------------------------

    Входной словарь может содержать любые из следующих ключей:
        a, b, c            - длины сторон
        alpha, beta, gamma - углы в ГРАДУСАХ

    Неизвестные величины должны иметь значение None.

    ---------------------------
    Правила решения
    ---------------------------

    • Для решения необходимо минимум 3 независимые величины
    • Комбинация AAA (три угла) недопустима — отсутствует масштаб
    • Комбинации SSA допускаются только при однозначности решения
    • При задании более 3 величин выполняется проверка согласованности

    ---------------------------
    Результат
    ---------------------------

    Возвращается словарь со ВСЕМИ величинами:
        a, b, c,
        alpha, beta, gamma (в градусах),
        ha, hb, hc — высоты, опущенные на стороны a, b, c

    В случае ошибки возбуждается DataError или GeometryError.
    """

    module = __name__
    eps = 1e-6
    pi = math.pi

    # ------------------------------------------------------------
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ------------------------------------------------------------

    def rad(x): return math.radians(x)
    def deg(x): return math.degrees(x)

    def solve_SSS(a, b, c):
        if a + b <= c or a + c <= b or b + c <= a:
            raise GeometryError(module, ValueError("Нарушено неравенство треугольника"))
        alpha = math.acos((b*b + c*c - a*a) / (2*b*c))
        beta  = math.acos((a*a + c*c - b*b) / (2*a*c))
        gamma = pi - alpha - beta
        return a, b, c, alpha, beta, gamma

    def side_by_cos(s1, s2, angle):
        return math.sqrt(s1*s1 + s2*s2 - 2*s1*s2*math.cos(angle))

    def side_by_sin(known_side, known_angle, target_angle):
        return known_side * math.sin(target_angle) / math.sin(known_angle)

    def canonical_SSA(b, c, beta):
        """
        Канонический SSA:
            известны b, c и beta (напротив b)
        """
        x = c * math.sin(beta) / b
        if x > 1 + eps:
            raise GeometryError(module, ValueError("Треугольник не существует"))

        gamma1 = math.asin(min(1.0, x))  # острый

        # Проверка однозначности
        if b < c:
            raise GeometryError(
                module,
                ValueError("Двусмысленный случай SSA (два возможных треугольника)")
            )

        gamma = gamma1
        alpha = pi - beta - gamma
        if alpha <= 0:
            raise GeometryError(module, ValueError("Невозможная конфигурация углов"))

        a = side_by_sin(b, beta, alpha)
        return a, b, c, alpha, beta, gamma

    # ------------------------------------------------------------
    # ИЗВЛЕЧЕНИЕ И НОРМАЛИЗАЦИЯ ДАННЫХ
    # ------------------------------------------------------------

    a = data.get('a')
    b = data.get('b')
    c = data.get('c')

    alpha = rad(data['alpha']) if data.get('alpha') is not None else None
    beta  = rad(data['beta'])  if data.get('beta')  is not None else None
    gamma = rad(data['gamma']) if data.get('gamma') is not None else None

    given = {k for k, v in {
        'a': a, 'b': b, 'c': c,
        'alpha': alpha, 'beta': beta, 'gamma': gamma
    }.items() if v is not None}

    n = len(given)

    # ------------------------------------------------------------
    # ПРОВЕРКИ КОЛИЧЕСТВА ДАННЫХ
    # ------------------------------------------------------------

    if n < 3:
        raise DataError(module, ValueError("Недостаточно данных для решения треугольника"))

    if given == {'alpha', 'beta', 'gamma'}:
        raise DataError(module, ValueError("Комбинация AAA не определяет масштаб"))

    # ------------------------------------------------------------
    # ВОССТАНОВЛЕНИЕ УГЛОВ (если возможно)
    # ------------------------------------------------------------

    if alpha and beta and not gamma:
        gamma = pi - alpha - beta
    elif alpha and gamma and not beta:
        beta = pi - alpha - gamma
    elif beta and gamma and not alpha:
        alpha = pi - beta - gamma

    if alpha and beta and gamma:
        if abs(alpha + beta + gamma - pi) > eps:
            raise DataError(module, ValueError("Сумма углов не равна 180°"))

    # ------------------------------------------------------------
    # ОСНОВНОЕ РЕШЕНИЕ
    # ------------------------------------------------------------

    solved = False

    # --- SSS
    if a and b and c:
        a, b, c, alpha, beta, gamma = solve_SSS(a, b, c)
        solved = True

    # --- SAS
    elif a and b and gamma:
        c = side_by_cos(a, b, gamma)
        a, b, c, alpha, beta, gamma = solve_SSS(a, b, c)
        solved = True

    elif a and c and beta:
        b = side_by_cos(a, c, beta)
        a, b, c, alpha, beta, gamma = solve_SSS(a, b, c)
        solved = True

    elif b and c and alpha:
        a = side_by_cos(b, c, alpha)
        a, b, c, alpha, beta, gamma = solve_SSS(a, b, c)
        solved = True

    # --- ASA / AAS
    elif alpha and beta and a:
        b = side_by_sin(a, alpha, beta)
        c = side_by_sin(a, alpha, gamma)
        solved = True

    elif alpha and gamma and a:
        b = side_by_sin(a, alpha, beta)
        c = side_by_sin(a, alpha, gamma)
        solved = True

    elif beta and gamma and b:
        a = side_by_sin(b, beta, alpha)
        c = side_by_sin(b, beta, gamma)
        solved = True

    # --- SSA (с канонизацией)
    else:
        # пробуем все циклические перестановки
        perms = [
            ('a', 'b', 'c', 'alpha', 'beta', 'gamma'),
            ('b', 'c', 'a', 'beta', 'gamma', 'alpha'),
            ('c', 'a', 'b', 'gamma', 'alpha', 'beta'),
        ]

        for sa, sb, sc, aa, ab, ag in perms:
            if data.get(sb) and data.get(sc) and data.get(ab):
                b0 = data[sb]
                c0 = data[sc]
                beta0 = rad(data[ab])

                a0, b0, c0, alpha0, beta0, gamma0 = canonical_SSA(b0, c0, beta0)

                # обратная подстановка
                mapping = {
                    sa: a0, sb: b0, sc: c0,
                    aa: alpha0, ab: beta0, ag: gamma0
                }

                a = mapping['a']
                b = mapping['b']
                c = mapping['c']
                alpha = mapping['alpha']
                beta = mapping['beta']
                gamma = mapping['gamma']

                solved = True
                break

    if not solved:
        raise DataError(
            module,
            ValueError("Недопустимая или неоднозначная комбинация исходных данных")
        )

    # ------------------------------------------------------------
    # ПРОВЕРКА СОГЛАСОВАННОСТИ (>3 заданных)
    # ------------------------------------------------------------

    for key, val in data.items():
        if val is None:
            continue

        if key in ('alpha', 'beta', 'gamma'):
            if abs(rad(val) - locals()[key]) > eps:
                raise DataError(
                    module,
                    ValueError(f"Противоречивое значение {key}")
                )
        else:
            if abs(val - locals()[key]) > eps:
                raise DataError(
                    module,
                    ValueError(f"Противоречивое значение {key}")
                )

    # ------------------------------------------------------------
    # ВЫСОТЫ
    # ------------------------------------------------------------

    ha = b * math.sin(gamma)
    hb = a * math.sin(gamma)
    hc = a * math.sin(beta)

    return {
        'a': a,
        'b': b,
        'c': c,
        'alpha': deg(alpha),
        'beta':  deg(beta),
        'gamma': deg(gamma),
        'ha': ha,
        'hb': hb,
        'hc': hc,
    }


# Конец модуля

if __name__ == '__main__':
    data = {
        'a': None,
        'b': 3.0,
        'c': None,
        'alpha': None,
        'beta': 45,
        'gamma': 90.0,
    }
    pprint(triangle(data))