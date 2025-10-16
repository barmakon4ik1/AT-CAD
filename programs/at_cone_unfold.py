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
) -> Tuple[List[Tuple[float, float]], List[float]]:
    """
    Строит развертку с правильным соединением краев (min/max x).
    """
    if d2 <= d1:
        raise ValueError(loc.get("invalid_dimensions"))

    h_full = h * d2 / (d2 - d1)

    # --- Верхний сегмент
    upper_half = build_half_cone_unfold(d1, h_full - h, n)
    upper_mirror = [(-x, y) for x, y in upper_half[::-1]]
    upper_curve = upper_mirror + upper_half  # min_x (left) -> ... -> max_x (right)

    # --- Нижний сегмент
    lower_half = build_half_cone_unfold(d2, h_full, n)
    lower_mirror = [(-x, y) for x, y in lower_half[::-1]]
    lower_curve = lower_mirror + lower_half  # min_x -> ... -> max_x

    # --- Находим края по x (левая: min x, правая: max x)
    upper_left = min(upper_curve, key=lambda p: p[0])
    upper_right = max(upper_curve, key=lambda p: p[0])
    lower_left = min(lower_curve, key=lambda p: p[0])
    lower_right = max(lower_curve, key=lambda p: p[0])

    # Индексы для слайсинга (чтобы пройти along curve от left to right)
    idx_upper_left = upper_curve.index(upper_left)
    idx_upper_right = upper_curve.index(upper_right)
    idx_lower_left = lower_curve.index(lower_left)
    idx_lower_right = lower_curve.index(lower_right)

    # Путь по upper от left to right (может быть не 0 to -1 если асимметрия, но в строении да)
    upper_path = upper_curve[idx_upper_left : idx_upper_right + 1] if idx_upper_left < idx_upper_right else list(reversed(upper_curve))[::-1]  # На всякий

    lower_path = lower_curve[idx_lower_left : idx_lower_right + 1]

    # --- Bulge для полных кривых
    apex = (0.0, 0.0)
    upper_bulge_full = [0.0] * (len(upper_curve) - 1)
    lower_bulge_full = [0.0] * (len(lower_curve) - 1)
    if curve_mode == "bulge":
        for i in range(len(upper_curve) - 1):
            upper_bulge_full[i] = bulge_from_center(upper_curve[i], upper_curve[i + 1], apex, clockwise=False)
        for i in range(len(lower_curve) - 1):
            lower_bulge_full[i] = bulge_from_center(lower_curve[i], lower_curve[i + 1], apex, clockwise=False)

    # Bulge для путей (слайс от left to right)
    bulge_lower = lower_bulge_full[idx_lower_left : idx_lower_right]
    bulge_upper = upper_bulge_full[idx_upper_left : idx_upper_right]
    bulge_upper_reversed = [-b for b in reversed(bulge_upper)]  # Реверс пути + смена знака bulge

    # --- Финальный контур: lower_left -> lower_path to lower_right -> upper_right -> reversed upper_path to upper_left -> lower_left
    # Чтобы избежать дублирования краев в пути:
    contour = (
        lower_path[:-1] +  # lower_left -> ... (без right)
        [lower_right, upper_right] +  # right_connect
        list(reversed(upper_path))[1:-1] +  # reversed от right к left, без дублирования краев
        [upper_left, lower_left]   # left_connect (замыкает к старту)
    )

    # Bulge соответственно: для lower_path (без последней), 0 для right_connect, для reversed upper (без краев), 0 для left_connect
    bulge_list = (
        bulge_lower[:-1 if len(bulge_lower) > 0 else 0] +
        [0.0] +  # right
        bulge_upper_reversed[1:-1 if len(bulge_upper_reversed) > 1 else 0] +
        [0.0]   # left
    )

    # Корректировка длины bulge к кол-ву сегментов в contour
    num_segments = len(contour) - 1
    if len(bulge_list) < num_segments:
        bulge_list += [0.0] * (num_segments - len(bulge_list))
    elif len(bulge_list) > num_segments:
        bulge_list = bulge_list[:num_segments]

    return contour, bulge_list


# -------------------------------------------------------------
# Основная точка входа
# -------------------------------------------------------------
if __name__ == "__main__":
    # --- параметры конуса
    d2 = 794.0  # нижний диаметр
    d1 = 267.0  # верхний диаметр
    h = 918.0   # высота
    n = 72      # сегменты дуги
    curve_mode = "lines"  # "lines", "bulge", "spline"# --- подключение к AutoCAD
    acad = ATCadInit()
    adoc, model = acad.document, acad.model_space

    # --- построение контура
    contour_local, bulge_list = build_truncated_cone_from_halves(d1, d2, h, n, curve_mode)

    # --- ввод точки вставки
    input_point = at_point_input(adoc, prompt="Укажите вершину развертки", as_variant=False)
    X0, Y0 = input_point[0], input_point[1]
    contour = [(x + X0, y + Y0) for x, y in contour_local]

    # --- построение в AutoCAD
    if curve_mode == "spline":
        add_spline(model, contour, layer_name="0")
    elif curve_mode == "bulge":
        add_polyline(model, contour, layer_name="0", bulges=bulge_list)
    else:
        add_polyline(model, contour, layer_name="0")

    # --- обновление документа
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

