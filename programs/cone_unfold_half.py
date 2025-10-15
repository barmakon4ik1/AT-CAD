import math
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional

from config.at_cad_init import ATCadInit
from programs.at_base import regen
from programs.at_construction import add_polyline
from programs.at_geometry import find_intersection_points
from programs.at_input import at_point_input
from locales.at_translations import loc

# -----------------------------
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
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# -------------------------------------------------------------
# Вспомогательная функция безопасного деления
def safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if abs(b) > 1e-12 else default


# -------------------------------------------------------------
# Функция пересечения двух окружностей
# def find_intersection_points(pt1: Tuple[float, float], r1: float,
#                              pt2: Tuple[float, float], r2: float) -> Optional[List[Tuple[float, float]]]:
#     x1, y1 = pt1
#     x2, y2 = pt2
#     d = math.hypot(x2 - x1, y2 - y1)
#
#     # Проверки существования решения
#     if d > r1 + r2 or d < abs(r1 - r2) or (d == 0 and r1 == r2):
#         return None
#
#     x = safe_div(d**2 + r1**2 - r2**2, 2 * d, 0.0)
#     discriminant = r1**2 - x**2
#     if discriminant < 0:
#         return None
#
#     y = math.sqrt(discriminant)
#     cos_theta = safe_div((x2 - x1), d, 1.0)
#     sin_theta = safe_div((y2 - y1), d, 0.0)
#
#     if abs(discriminant) < 1e-10:
#         px = x1 + x * cos_theta
#         py = y1 + x * sin_theta
#         return [(px, py)]
#
#     # Две возможные точки пересечения
#     px1 = x1 + x * cos_theta - y * sin_theta
#     py1 = y1 + x * sin_theta + y * cos_theta
#     px2 = x1 + x * cos_theta + y * sin_theta
#     py2 = y1 + x * sin_theta - y * cos_theta
#
#     return [(px1, py1), (px2, py2)]


# -------------------------------------------------------------
# Основная функция построения развертки половины конуса
def build_half_cone_unfold(D: float, H: float, n: int) -> List[Tuple[float, float]]:
    """
    Строит координаты точек половины развертки усечённого конуса (пирамиды),
    где одна сторона вертикальна.

    Args:
        D: диаметр основания
        H: высота конуса
        n: число сегментов половины окружности

    Returns:
        Список координат точек [(x, y), ...] для полилинии
    """

    # --- Инициализация
    points = []

    # Вершина конуса — начало координат
    apex = (0.0, 0.0)
    # Первая образующая (вертикальная) — вниз по оси Y
    first_length = math.sqrt((D * math.cos(0))**2 + H**2)
    base_point = (0.0, -first_length)
    points.append(base_point)

    # Длина дуги деления основания (в полукруге)
    arc_len = math.pi * D / n

    prev_point = base_point
    prev_len = first_length

    # Строим только до вертикальной образующей (90 градусов)
    for i in range(1, n // 2 + 1):
        angle_deg = i * 180.0 / n
        L = math.sqrt((D * math.cos(math.radians(angle_deg)))**2 + H**2)

        # Центры окружностей — вершина и предыдущая точка
        intersections = find_intersection_points(apex, L, prev_point, arc_len)

        if not intersections:
            print(f"[!] Нет пересечения для i={i}, L={L:.3f}")
            break

        # Берем точку с большим X (правая половина развертки)
        p1, p2 = intersections
        new_point = p1 if p1[0] > p2[0] else p2

        points.append(new_point)
        prev_point = new_point
        prev_len = L

    return points


# -------------------------------------------------------------
# Визуализация для проверки
# -------------------------------------------------------------
# Визуализация и построение в AutoCAD
if __name__ == "__main__":
    D = 794.0   # диаметр основания
    H = 1378.58    # высота
    n = 72      # количество сегментов половины окружности

    cad = ATCadInit()

    if not cad.is_initialized():
        print(loc.get("autocad_not_running"))
    else:
        adoc = cad.document
        model = cad.model_space

        # Точка вставки (вершина конуса)
        input_point = at_point_input(adoc, prompt=loc.get("select_point", "Укажите вершину развертки"), as_variant=False)
        if not input_point:
            print(loc.get("point_selection_cancelled"))
        else:
            X0, Y0 = input_point[0], input_point[1]

            # Правая половина (включая вершину)
            pts_right = build_half_cone_unfold(D, H, n)
            pts_right.insert(0, (0.0, 0.0))  # вершина в начале

            # Левая половина (зеркально, включая вершину)
            pts_left = [(-x, y) for x, y in pts_right[::-1]]

            # Полная развёртка:
            # левая половина (всё, кроме последней вершины) + правая половина (всё, кроме первой вершины)
            # и в конце добавляем вершину для замыкания
            pts_local = pts_left[:-1] + pts_right[1:] + [(0.0, 0.0)]

            # Смещаем все точки относительно точки вставки
            pts = [(x + X0, y + Y0) for x, y in pts_local]

            # Создание полилинии в AutoCAD
            add_polyline(model, pts, layer_name="LASER-TEXT")

            print(f"Развёртка построена корректно. Точка вставки: ({X0:.3f}, {Y0:.3f})")

            regen(adoc)

    # # Вывод координат
    # print("Координаты точек развертки:")
    # for i, (x, y) in enumerate(pts):
    #     print(f"{i:2d}: ({x:.3f}, {y:.3f})")
    #
    # # Построение графика
    # xs, ys = zip(*([(0, 0)] + pts))  # включая вершину
    # plt.figure(figsize=(8, 6))
    # plt.plot(xs, ys, marker='o')
    # plt.axis('equal')
    # plt.title("Развертка половины конуса (одна сторона вертикальна)")
    # plt.xlabel("X")
    # plt.ylabel("Y")
    # plt.grid(True)
    # plt.show()
