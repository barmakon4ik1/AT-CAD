"""
programs/at_nozzle_cone.py

Модуль строит линию пересечения усечённого конуса и цилиндра
и наносит её на развертку боковой поверхности конуса.

Автор: A.Tutubalin
Дата: 2025

Основные функции:
    - main(params) — основной вход, принимает словарь данных как из GUI
    - вычисление образующих на пересечении
    - построение развертки конуса (через at_cone_sheet)
    - генерация точек линии пересечения на развертке
    - корректный поворот полилинии так, чтобы апекс был внизу

Использование:
    import programs.at_nozzle_cone as nozzle
    nozzle.main(params)
"""

import math
import logging
from typing import Any, Dict, Tuple, List

from config.at_cad_init import ATCadInit
from programs.at_base import regen
from programs.at_construction import at_cone_sheet, add_polyline
from programs.at_geometry import rad_to_deg
from programs.at_input import at_get_point


# -----------------------------------------------------------------------------
#                     G E O M E Т Р И Ч Е С К И Е   Ф У Н К Ц И И
# -----------------------------------------------------------------------------


def diameter_at_height(z: float, diameter_base: float, diameter_top: float, height: float) -> float:
    """
    Линейная интерполяция диаметра конуса на высоте z от нижнего основания.
    """
    r2 = diameter_base / 2
    r1 = diameter_top / 2
    return 2 * (r2 - z * (r2 - r1) / height)


def generatrix_by_diameter(d: float, diameter_base: float, L_full: float) -> float:
    """
    Возвращает длину образующей для сечения с диаметром d.
    d пропорционален общей высоте конуса, поэтому образующая масштабируется линейно.
    """
    return L_full * d / diameter_base


def finder_z(alpha: float, diameter_pipe: float, diameter_base: float, height_lower: float) -> float:
    """
    Высота пересечения конуса с цилиндром относительно нижнего основания конуса.
    Аргумент alpha — угол в радианах.
    """
    angle = math.cos(alpha)
    z = math.sqrt((diameter_pipe / 2) ** 2 - (diameter_base * angle / 2) ** 2) - height_lower
    return z


# -----------------------------------------------------------------------------
#                          П О Л И Л И Н И И  /  Р А З В О Р О Т
# -----------------------------------------------------------------------------


def build_intersection_polyline(
        apex: Tuple[float, float],
        theta_rad: float,
        generatrix_list: List[float]
) -> List[List[float]]:
    """
    Формирует точки линии пересечения на развертке конуса.

    apex — точка вершины развертки
    theta_rad — полный угол развертки
    generatrix_list — список длин образующих (N+1 элементов)
    """
    Ax, Ay, Az = apex
    N = len(generatrix_list) - 1
    angle_step = theta_rad / N

    points = []
    for i, g in enumerate(generatrix_list):
        phi = i * angle_step
        x = Ax + g * math.cos(phi)
        y = Ay + g * math.sin(phi)
        points.append([x, y])

    return points


def rotate_points(
        points: List[List[float]],
        angle_deg: float,
        origin: Tuple[float, float]
) -> List[List[float]]:
    """
    Поворот списка точек на угол angle_deg вокруг origin.
    """
    ox, oy, oz = origin
    angle = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    rotated = []
    for x, y in points:
        tx = x - ox
        ty = y - oy

        rx = tx * cos_a - ty * sin_a
        ry = tx * sin_a + ty * cos_a

        rotated.append([rx + ox, ry + oy])

    return rotated


# -----------------------------------------------------------------------------
#                               O C Н O В H A Я   Ф У Н К Ц И Я
# -----------------------------------------------------------------------------


def main(params: Dict[str, Any]):
    """
    Основная функция построения развертки линии пересечения цилиндра и усечённого конуса.
    """

    # --- Проверка параметров -------------------------------------------------
    required_keys = ["model", "input_point", "diameter_top",
                     "diameter_base", "diameter_pipe", "height_full"]

    for k in required_keys:
        if k not in params:
            logging.error(f"Не указан обязательный параметр: {k}")
            raise KeyError(f"Отсутствует '{k}'")

    try:
        model = params["model"]
        input_point = params["input_point"]
        diameter_top = float(params["diameter_top"])
        diameter_base = float(params["diameter_base"])
        diameter_pipe = float(params["diameter_pipe"])
        height_full = float(params["height_full"])
    except Exception as e:
        logging.error("Неверные типы параметров")
        raise

    layout = params.get("layout", "LASER-TEXT")
    N = int(params.get("N", 360))

    # --- Геометрия конуса ----------------------------------------------------
    # Высота усечённой части: пересечение цилиндра с конусом
    height = height_full - math.sqrt((diameter_pipe / 2) ** 2 -
                                     (diameter_base / 2) ** 2)

    # Высота от плоскости цилиндра до нижнего основания
    height_lower = height_full - height

    # Высота от верхнего основания до вершины конуса
    height_top = height / (diameter_base / diameter_top - 1)

    # Полная образующая конуса
    L_full = math.hypot(height + height_top, diameter_base / 2)

    # --- Список образующих пересечения --------------------------------------
    angle_step = 2 * math.pi / N

    generatrix_list = []
    for i in range(N + 1):
        z = finder_z(i * angle_step, diameter_pipe, diameter_base, height_lower)
        d = diameter_at_height(z, diameter_base, diameter_top, height)
        g = generatrix_by_diameter(d, diameter_base, L_full)
        generatrix_list.append(g)

    # --- Построение развертки конуса ----------------------------------------
    # at_cone_sheet возвращает: (points_list, input_point, apex, theta_rad)
    cone_points, _, apex, theta_rad = at_cone_sheet(
        model, input_point, diameter_base, diameter_top, height, layer_name="0"
    )

    # --- Формирование линии пересечения в развертке --------------------------
    polyline_pts = build_intersection_polyline(apex, theta_rad, generatrix_list)

    # --- Поворот полилинии для ориентации апекса вниз ------------------------
    rotate_angle = 90 - rad_to_deg(theta_rad) / 2
    rotated_poly = rotate_points(polyline_pts, rotate_angle, origin=apex)

    # --- Добавление полилинии в AutoCAD --------------------------------------
    add_polyline(model, rotated_poly, layer_name=layout, closed=False)


# -----------------------------------------------------------------------------
#                                Т Е С Т
# -----------------------------------------------------------------------------

def run_test():
    """
    Локальная проверка без GUI.
    """
    acad = ATCadInit()
    adoc, model = acad.document, acad.model_space
    input_point = at_get_point(adoc, prompt="Укажите точку вставки")

    params = {
        "model": model,
        "input_point": input_point,
        "diameter_top": 102.0,
        "diameter_base": 138.0,
        "diameter_pipe": 273.0,
        "height_full": 185.78,
        "layout": "LASER-TEXT",
        "N": 360,
    }

    main(params)
    regen(adoc)


if __name__ == "__main__":
    run_test()
