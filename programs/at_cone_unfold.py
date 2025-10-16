# -*- coding: utf-8 -*-
"""
Модуль: at_cone_unfold.py
Путь: programs/at_cone_unfold.pyПостроение развертки усечённого конуса с одной вертикальной образующей.
Поддерживаются линии, дуги (bulge) и сплайны.Использует функции из at_geometry.py для расчёта координат и bulge дуг.Автор: Alexander Tutubalin
Дата: 16.10.2025
"""

import math
import matplotlib.pyplot as plt
from typing import List, Tuple, Any
from config.at_cad_init import ATCadInit
from programs.at_base import regen
from programs.at_construction import add_polyline, add_spline
from programs.at_geometry import find_intersection_points, bulge_from_center
from programs.at_input import at_point_input
from locales.at_translations import loc# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "autocad_not_running": {
        "ru": "AutoCAD не запущен. Сначала откройте AutoCAD.",
        "en": "AutoCAD is not running. Please start AutoCAD first.",
        "de": "AutoCAD läuft nicht. Bitte starten Sie zuerst AutoCAD."
    },
    "point_selection_cancelled": {
        "ru": "Выбор точки отменён.",
        "en": "Point selection cancelled.",
        "de": "Punktauswahl abgebrochen."
    },
    "invalid_dimensions": {
        "ru": "Нижний диаметр должен быть больше верхнего.",
        "en": "Bottom diameter must be greater than top diameter.",
        "de": "Der untere Durchmesser muss größer als der obere sein."
    }
}
loc.register_translations(TRANSLATIONS)# -------------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------------
def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Безопасное деление для предотвращения деления на ноль."""
    return a / b if abs(b) > 1e-12 else default# -------------------------------------------------------------
# Построение половины развертки (одна сторона вертикальна)
# -------------------------------------------------------------
def build_half_cone_unfold(D: float, H: float, n: int) -> List[Tuple[float, float]]:
    """
    Строит половину развертки конуса (одна сторона вертикальна).Args:
    D: Диаметр основания половины конуса.
    H: Высота конуса.
    n: Количество точек разбиения дуги.

Returns:
    Список точек [(x, y), ...] для одной половины.
"""
    points = []
    apex = (0.0, 0.0)  # вершина конуса
    first_length = math.sqrt(D ** 2 + H ** 2)
    base_point = (0.0, -first_length)
    points.append(base_point)

    arc_len = math.pi * D / n
    prev_point = base_point

    for i in range(1, n // 2 + 1):
        angle_deg = i * 180.0 / n
        L = math.sqrt((D * math.cos(math.radians(angle_deg))) ** 2 + H ** 2)
        intersections = find_intersection_points(apex, L, prev_point, arc_len)
        if not intersections:
            break
        p1, p2 = intersections
        new_point = p1 if p1[0] > p2[0] else p2
        points.append(new_point)
        prev_point = new_point
    return points

# -------------------------------------------------------------
# Построение полной развертки усечённого конуса
# -------------------------------------------------------------
def build_truncated_cone_from_halves(
    d1: float,
    d2: float,
    h: float,
    n: int,
    curve_mode: str = "lines"
):
    if d2 <= d1:
        raise ValueError(loc.get("invalid_dimensions"))

    h_full = h * d2 / (d2 - d1)

    # --- Верхний и нижний сегменты
    upper_half = build_half_cone_unfold(d1, h_full - h, n)
    upper_mirror = [(-x, y) for x, y in upper_half[::-1]]
    upper_curve = upper_mirror + upper_half

    lower_half = build_half_cone_unfold(d2, h_full, n)
    lower_mirror = [(-x, y) for x, y in lower_half[::-1]]
    lower_curve = lower_mirror + lower_half

    # --- Краевые точки
    upper_left = min(upper_curve, key=lambda p: p[0])
    upper_right = max(upper_curve, key=lambda p: p[0])
    lower_left = min(lower_curve, key=lambda p: p[0])
    lower_right = max(lower_curve, key=lambda p: p[0])

    upper_path = upper_curve
    lower_path = lower_curve

    # --- Bulge (для дуг)
    apex = (0.0, 0.0)
    bulge_lower = [0.0] * (len(lower_path) - 1)
    bulge_upper = [0.0] * (len(upper_path) - 1)

    if curve_mode == "bulge":
        for i in range(len(lower_path) - 1):
            bulge_lower[i] = bulge_from_center(lower_path[i], lower_path[i + 1], apex, clockwise=False)
        for i in range(len(upper_path) - 1):
            bulge_upper[i] = bulge_from_center(upper_path[i], upper_path[i + 1], apex, clockwise=False)

    # --- Концевые точки (прямые образующие)
    left_line = [lower_left, upper_left]
    right_line = [lower_right, upper_right]

    # --- Общий контур
    contour = (
        lower_path[:-1]
        + [lower_right, upper_right]
        + list(reversed(upper_path))[1:-1]
        + [upper_left, lower_left]
    )
    bulge_list = [0.0] * (len(contour) - 1)

    return contour, bulge_list, lower_path, upper_path, bulge_lower, bulge_upper


# -------------------------------------------------------------
# Основная точка входа
# -------------------------------------------------------------
if __name__ == "__main__":
    d2 = 794.0
    d1 = 267.0
    h = 918.0
    n = 72
    curve_mode = "spline"  # "lines", "bulge", "spline"

    acad = ATCadInit()
    adoc, model = acad.document, acad.model_space

    contour_local, bulge_list, lower_path, upper_path, bulge_lower, bulge_upper = \
        build_truncated_cone_from_halves(d1, d2, h, n, curve_mode)

    input_point = at_point_input(adoc, prompt="Укажите вершину развертки", as_variant=False)
    X0, Y0 = input_point[0], input_point[1]

    shift = lambda path: [(x + X0, y + Y0) for x, y in path]
    lower_path = shift(lower_path)
    upper_path = shift(upper_path)

    if curve_mode == "spline":
        # Две кривые отдельно, без замыкания
        add_spline(model, lower_path, layer_name="0")
        add_spline(model, upper_path, layer_name="0")
        # Прямые образующие
        add_polyline(model, [lower_path[0], upper_path[0]], layer_name="0")
        add_polyline(model, [lower_path[-1], upper_path[-1]], layer_name="0")

    elif curve_mode == "bulge":
        # Исправление направления bulge: у зеркальных половин нужно инвертировать знак
        bulge_lower_corr = [b if not math.isnan(b) else 0.0 for b in bulge_lower]
        bulge_upper_corr = [-b if not math.isnan(b) else 0.0 for b in bulge_upper]

        # Нижняя дуга
        if len(bulge_lower_corr) == len(lower_path) - 1:
            add_polyline(model, lower_path, layer_name="0", bulges=bulge_lower_corr)
        else:
            add_polyline(model, lower_path, layer_name="0")

        # Верхняя дуга
        if len(bulge_upper_corr) == len(upper_path) - 1:
            add_polyline(model, upper_path, layer_name="0", bulges=bulge_upper_corr)
        else:
            add_polyline(model, upper_path, layer_name="0")

        # Прямые образующие
        add_polyline(model, [lower_path[0], upper_path[0]], layer_name="0")
        add_polyline(model, [lower_path[-1], upper_path[-1]], layer_name="0")

    else:
        # Линейный режим
        contour = shift(contour_local)
        add_polyline(model, contour, layer_name="0")

    regen(adoc)



    # --- графический вывод (опционально)
    # xs, ys = zip(*contour_local)
    # plt.figure(figsize=(9, 7))
    # plt.plot(xs, ys, "-o", lw=1.2)
    # for i, (x, y) in enumerate(contour_local):
    #     plt.text(x, y, f"{i}", fontsize=8, color="blue")
    # plt.axis("equal")
    # plt.title("Развёртка усечённого конуса (одна сторона вертикальна)")
    # plt.xlabel("X")
    # plt.ylabel("Y")
    # plt.grid(True)
    # plt.show()

