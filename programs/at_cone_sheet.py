# -*- coding: utf-8 -*-
"""
programs/at_construction/at_cone_sheet.py

Построение развертки усечённого конуса (закрытая полилиния).
Поддерживает режимы: "polyline", "bulge", "spline".
Боковые образующие всегда прямые (bulge=0).
Функция возвращает True при успехе, None при ошибке.
"""

import math
from typing import List, Tuple, Optional

from config.at_cad_init import ATCadInit
from programs.at_geometry import ensure_point_variant, convert_to_variant_points, circle_center_from_points, polar_point
from programs.at_construction import add_polyline, add_spline, add_line, add_text
from programs.at_base import regen

# helper type
Pt = Tuple[float, float]

def _arc_points(center_x: float, center_y: float, radius: float, start_ang: float, end_ang: float, n: int) -> List[Pt]:
    """Возвращает n точек вдоль дуги радиуса radius от start_ang до end_ang (в радианах)."""
    pts: List[Pt] = []
    if n < 2:
        n = 2
    for i in range(n):
        a = start_ang + (end_ang - start_ang) * (i / (n - 1))
        x = center_x + radius * math.cos(a)
        y = center_y + radius * math.sin(a)
        pts.append((x, y))
    return pts

def _compute_bulges(points: List[Pt], mode: str) -> List[float]:
    """
    Для последовательности точек вычисляет bulge для каждого сегмента, используя круговое приближение.
    Возвращает список bulge длиной len(points) (последний bulge ставится 0).
    Если mode == "polyline" — все bulge = 0.
    """
    n = len(points)
    if n < 2:
        return [0.0] * n
    if mode == "polyline":
        return [0.0] * n

    bulges: List[float] = []
    # Для вычисления центра круга используем три соседних точки
    # Расширяем список (wrap) чтобы покрыть циклические триады (но здесь дуга не замкнута)
    extended = [points[0]] + points + [points[-1]]
    for i in range(1, n + 1):
        p0 = extended[i - 1]
        p1 = extended[i]
        p2 = extended[i + 1]
        # если точки коллинеарны или нет центра — bulge = 0
        center = circle_center_from_points(p0, p1, p2)
        if center is None:
            bulges.append(0.0)
            continue
        cx, cy = center
        ang1 = math.atan2(p1[1] - cy, p1[0] - cx)
        ang2 = math.atan2(p2[1] - cy, p2[0] - cx)
        sweep = ang2 - ang1
        # нормализуем sweep в (-pi, pi)
        sweep = (sweep + math.pi) % (2 * math.pi) - math.pi
        # bulge = tan(sweep/4)
        bulges.append(math.tan(sweep / 4.0))
    # последний bulge (для завершения списка) — 0 (мы будем ставить для n точек, polylines ожидают булги на каждом узле)
    # Однако у нас n элементов и мы сопоставляем bulge с сегментами; для простоты вернём длину n и последним 0
    if len(bulges) < n:
        bulges += [0.0] * (n - len(bulges))
    bulges[-1] = 0.0
    return bulges

def at_cone_sheet(
    model,
    input_point,
    diameter_base: float,
    diameter_top: float,
    height: float,
    layer_name: str = "0",
    accuracy: int = 180,
    mode: str = "polyline"
) -> Optional[bool]:
    """
    Построение развертки усечённого конуса.
    - model: AutoCAD model space (win32com object)
    - input_point: точка вставки [x,y,z] или Variant
    - diameter_base: D (нижний/большой диаметр)
    - diameter_top: d (верхний/малый диаметр)
    - height: H (высота вдоль оси между кругами)
    - accuracy: число точек на дугу (рекомендуется >= 36)
    - mode: "polyline", "bulge", "spline"

    Возвращает True при успехе, None при ошибке.
    """
    try:
        # Нормализация входной точки
        insert = ensure_point_variant(input_point)
        ix = float(insert[0])
        iy = float(insert[1])
        # iz = float(insert[2])  # не используем Z для развертки в текущей плоскости

        # Проверки
        if diameter_base <= 0 or diameter_top <= 0 or height <= 0:
            return None

        # Радиусы по средней линии
        r1 = diameter_top / 2.0    # малый радиус (верхний)
        r2 = diameter_base / 2.0   # большой радиус (нижний)

        if abs(r2 - r1) < 1e-12:
            # почти цилиндр — можно использовать приближение: сектор с радиусом s = любое и theta = 2*pi
            s_frag = height  # образующая почти равна высоте
            s1 = s2 = s_frag
            theta = 2.0 * math.pi
        else:
            # образующая между кругами
            s_frag = math.hypot(height, r2 - r1)
            # расстояния от апекса до кругов (по образующей)
            s1 = r1 * s_frag / (r2 - r1)
            s2 = s1 + s_frag
            # центральный угол сектора (радианы)
            theta = 2.0 * math.pi * r2 / s2

        # Дискретизация дуг
        # Нижняя дуга: радиус s2, угол от 0 до theta (по часовой/против? — возьмём 0..theta)
        # Верхняя дуга: радиус s1, чтобы замкнуть контур идёт в обратном направлении (theta..0)
        n = max(6, int(accuracy))
        # делаем n точек на дугу (включая концевые)
        angles_bottom = [0.0 + (theta) * (i / (n - 1)) for i in range(n)]
        angles_top = [theta - (theta) * (i / (n - 1)) for i in range(n)]  # обратное направление

        bottom_pts: List[Pt] = [(ix + s2 * math.cos(a), iy + s2 * math.sin(a)) for a in angles_bottom]
        top_pts: List[Pt] = [(ix + s1 * math.cos(a), iy + s1 * math.sin(a)) for a in angles_top]

        # Формирование замкнутого контура
        # Порядок: нижняя дуга (0..θ), правая образующая (последняя нижней -> первая верхней),
        # верхняя дуга (θ..0), левая образующая (последняя верхней -> первая нижней)
        # Для polyline/bulge нужно передать список точек с bulge значениями (x,y,bulge)
        mode = (mode or "polyline").lower()
        if mode not in ("polyline", "bulge", "spline"):
            mode = "polyline"

        if mode == "spline":
            # Для spline: рисуем верхнюю и нижнюю дуги сплайнами, и два прямых сегмента между их концами.
            # Создаём сплайн нижней дуги (в прямом порядке)
            add_spline(model, [[x, y] for x, y in bottom_pts], layer_name=layer_name, closed=False)
            # Сплайн верхней дуги
            add_spline(model, [[x, y] for x, y in top_pts], layer_name=layer_name, closed=False)
            # Соединительные прямые (образующие)
            # правая: от last bottom -> first top
            last_bottom = bottom_pts[-1]
            first_top = top_pts[0]
            add_line(model, ensure_point_variant([last_bottom[0], last_bottom[1], 0.0]),
                          ensure_point_variant([first_top[0], first_top[1], 0.0]), layer_name=layer_name)
            # левая: от last top -> first bottom
            last_top = top_pts[-1]
            first_bottom = bottom_pts[0]
            add_line(model, ensure_point_variant([last_top[0], last_top[1], 0.0]),
                          ensure_point_variant([first_bottom[0], first_bottom[1], 0.0]), layer_name=layer_name)
            # В spline-режиме возвращаем True (контур составлен из двух сплайнов и двух линий)
            return True

        # Для polyline и bulge: подготовим список точек (x,y,bulge)
        # Сначала делаем только верхнюю и нижнюю дуги, затем боковые (bulge=0)
        # Вычислим bulge для дуг, если mode == "bulge", иначе оставим 0
        bottom_bulges = _compute_bulges(bottom_pts, mode)
        top_bulges = _compute_bulges(top_pts, mode)

        # Составляем contour как список (x,y,bulge)
        contour: List[Tuple[float, float, float]] = []

        # нижняя дуга (включая все точки кроме последней, потому что следующий сегмент пойдёт между последней нижней и первой верхней)
        for i, (x, y) in enumerate(bottom_pts[:-1]):
            contour.append((x, y, bottom_bulges[i]))

        # правая образующая: from last bottom to first top -> прямой (bulge=0)
        last_bottom = bottom_pts[-1]
        first_top = top_pts[0]
        contour.append((last_bottom[0], last_bottom[1], 0.0))
        contour.append((first_top[0], first_top[1], 0.0))

        # верхняя дуга (включая все точки кроме последней)
        for i, (x, y) in enumerate(top_pts[:-1]):
            contour.append((x, y, top_bulges[i]))

        # левая образующая: from last top to first bottom -> прямой
        last_top = top_pts[-1]
        first_bottom = bottom_pts[0]
        contour.append((last_top[0], last_top[1], 0.0))
        contour.append((first_bottom[0], first_bottom[1], 0.0))

        # Удалим возможные подряд повторяющиеся точки (чтобы не ломало add_polyline)
        cleaned: List[Tuple[float, float, float]] = []
        eps = 1e-9
        for p in contour:
            if not cleaned:
                cleaned.append(p)
            else:
                lp = cleaned[-1]
                if abs(p[0] - lp[0]) > eps or abs(p[1] - lp[1]) > eps:
                    cleaned.append(p)

        if len(cleaned) < 3:
            return None

        # Добавляем полилинию в модель
        add_polyline(model, cleaned, layer_name=layer_name, closed=True)

        return True

    except Exception as e:
        # не поднимаем исключение — вызывающая сторона покажет popup/log
        # Можно логировать здесь при необходимости
        return None
