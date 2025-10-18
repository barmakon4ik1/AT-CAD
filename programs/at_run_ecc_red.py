# -*- coding: utf-8 -*-
"""
Модуль: at_run_ecc_red.py
Путь: programs/at_run_ecc_red.py
Построение развертки усечённого конуса с одной вертикальной образующей.
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
loc.register_translations(TRANSLATIONS)

# -------------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------------
def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Безопасное деление для предотвращения деления на ноль."""
    return a / b if abs(b) > 1e-12 else default

# -------------------------------------------------------------
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
) -> Tuple[
    List[Tuple[float, float]],   # contour (общий)
    List[float],                 # bulge_list (общий)
    List[Tuple[float, float]],   # lower_path
    List[Tuple[float, float]],   # upper_path
    List[float],                 # bulge_lower
    List[float]                  # bulge_upper
]:
    if d2 <= d1:
        raise ValueError(loc.get("invalid_dimensions"))

    # Полная высота гипотетического конуса
    h_full = h * d2 / (d2 - d1)

    # --- Верхний сегмент
    upper_half = build_half_cone_unfold(d1, h_full - h, n)
    upper_mirror = [(-x, y) for x, y in upper_half[::-1]]
    # убираем дублированные крайние точки
    upper_curve = upper_mirror[:-1] + upper_half

    # --- Нижний сегмент
    lower_half = build_half_cone_unfold(d2, h_full, n)
    lower_mirror = [(-x, y) for x, y in lower_half[::-1]]
    lower_curve = lower_mirror[:-1] + lower_half

    # --- Краевые точки
    upper_left = min(upper_curve, key=lambda p: p[0])
    upper_right = max(upper_curve, key=lambda p: p[0])
    lower_left = min(lower_curve, key=lambda p: p[0])
    lower_right = max(lower_curve, key=lambda p: p[0])

    # --- Bulge (реальные дуги)
    apex = (0.0, 0.0)
    bulge_lower = []
    bulge_upper = []

    if curve_mode == "bulge":
        # нижний и верхний радиусы (длины образующих)
        R_lower = math.sqrt(h_full ** 2 + (d2 / 2) ** 2)
        R_upper = math.sqrt((h_full - h) ** 2 + (d1 / 2) ** 2)

        # шаг по углу для половины развёртки
        phi_step_lower = math.pi / (len(lower_half) - 1)
        phi_step_upper = math.pi / (len(upper_half) - 1)

        bulge_lower = [math.tan(phi_step_lower / 4.0)] * len(lower_curve)
        bulge_upper = [math.tan(phi_step_upper / 4.0)] * len(upper_curve)

    # --- Общий контур: низ → правая образующая → верх → левая образующая
    contour = (
        lower_curve +
        [lower_right, upper_right] +
        list(reversed(upper_curve)) +
        [upper_left, lower_left]
    )
    bulge_list = [0.0] * (len(contour) - 1)

    return contour, bulge_list, lower_curve, upper_curve, bulge_lower, bulge_upper


# -------------------------------------------------------------
# Основная точка входа
# -------------------------------------------------------------
def main(data):
    return at_eccentric_reducer(data)


def at_eccentric_reducer(data: Dict[str, any]) -> bool:
    """
    Основная функция для построения развертки конуса в AutoCAD.

    Args:
        data: Словарь с данными конуса, полученными из окна content_cone.py
              (order_number, detail_number, material, thickness, diameter_top,
              diameter_base, d_type, D_type, height, steigung, angle, weld_allowance,
              insert_point, thickness_text).

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    # --- параметры конуса
    d2 = 794.0
    d1 = 267.0
    h = 918.0
    n = 36
    curve_mode = "bulge"  # "lines", "bulge", "spline"

    # --- подключение к AutoCAD
    acad = ATCadInit()
    adoc, model = acad.document, acad.model_space

    # --- построение контура
    contour_local, bulge_list, lower_path, upper_path, bulge_lower, bulge_upper = \
        build_truncated_cone_from_halves(d1, d2, h, n, curve_mode)

    # --- ввод точки вставки
    input_point = at_point_input(adoc, prompt="Укажите вершину развертки", as_variant=False)
    X0, Y0 = input_point[0], input_point[1]

    # --- сдвиг координат
    shift = lambda path: [(x + X0, y + Y0) for x, y in path]
    lower_path = shift(lower_path)
    upper_path = shift(upper_path)
    contour = shift(contour_local)

    # --- построение в AutoCAD
    if curve_mode == "spline":
        # Верхняя и нижняя кривые – отдельные открытые сплайны
        add_spline(model, lower_path, layer_name="0", closed=False)
        add_spline(model, upper_path, layer_name="0", closed=False)
        # Образующие
        add_polyline(model, [lower_path[0], upper_path[0]], layer_name="0")
        add_polyline(model, [lower_path[-1], upper_path[-1]], layer_name="0")

    elif curve_mode == "bulge":
        # --- проверяем bulge на всякий случай
        if len(bulge_lower) != len(lower_path):
            bulge_lower = [0.0] * len(lower_path)
        if len(bulge_upper) != len(upper_path):
            bulge_upper = [0.0] * len(upper_path)

        # --- точки и bulge для замкнутой полилинии
        # порядок обхода: нижняя -> правая образующая -> верхняя (обратная) -> левая образующая
        all_points = (
                lower_path +  # нижняя
                [lower_path[-1], upper_path[-1]] +  # правая вертикальная
                upper_path[::-1] +  # верхняя в обратном порядке
                [upper_path[0], lower_path[0]]  # левая вертикальная
        )

        # --- bulge: нижняя + 0 для вертикали + верхняя обратная + 0 для вертикали
        all_bulges = (
                bulge_lower +
                [0.0, 0.0] +
                list(reversed(bulge_upper)) +
                [0.0, 0.0]
        )

        # --- строим замкнутую полилинию
        add_polyline(model, all_points, layer_name="0", bulges=all_bulges, closed=True)

    else:
        # Прямая полилиния (для режима lines)
        add_polyline(model, contour, layer_name="0", closed=True)

        # --- объединение в замкнутый контур (join) после построения
        if curve_mode in ["bulge", "spline"]:
            try:
                # Получаем последние 4 созданные объекта (нижняя, верхняя, левая, правая)
                # В ModelSpace Count - общее, Item(Count - 1) - последний
                entities_to_join = []
                for i in range(1, 5):
                    ent = model.Item(model.Count - i)
                    entities_to_join.append(ent)

                # JoinEntities требует массива объектов и базового (первого в массиве)
                # Выберем нижнюю как базу (или любую)
                base_ent = entities_to_join[0]
                others = entities_to_join[1:]
                base_ent.JoinEntities(others)
                base_ent.Closed = True
            except Exception as e:
                print(f"Join failed: {e}")

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


if __name__ == "__main__":
    # Пример данных для тестирования
    input_data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter_base": 1000.0,
        "diameter_top": 500.0,
        "height": 800.0,
        "material": "1.4301",
        "thickness": 4.0,
        "order_number": "12345",
        "detail_number": "01",
        "layer_name": "0",
        "weld_allowance": 3.0
    }
    at_eccentric_reducer(input_data)