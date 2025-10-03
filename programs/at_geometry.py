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
from typing import Optional, List, Tuple, Union, Dict

from config.at_cad_init import ATCadInit
from programs.at_input import at_point_input
from programs.at_utils import handle_errors
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


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """
    Безопасное деление, чтобы избежать ZeroDivisionError.
    Возвращает default, если делитель близок к нулю.
    """
    try:
        if abs(b) < 1e-12:
            return default
        return a / b
    except Exception:
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


def deg_to_rad(angle: float) -> Optional[float]:
    """
    Конвертирует угол из градусов в радианы.

    Args:
        angle: Угол в градусах.

    Returns:
        Угол в радианах.
    """
    return math.radians(angle)


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


def add_rectangle_points(point:Union[List[float], Tuple[float, ...], VARIANT], width: float, height: float, point_direction: str = "left_bottom") -> VARIANT:
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

    :param insert_point: базовая точка вставки прямоугольника оболочки [x, y, z]
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

    return [x0 + X, y0 + Y, z0]


def angle_to_unroll_x(angle_deg, diameter, cut_angle_ref=0.0, unroll_dir="CW"):
    """
    Перевод угла окружности цилиндра в координату X на развёртке.

    :param angle_deg: исходный угол (в системе цилиндра)
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


# Конец модуля
