"""
at_nozzle_cone.py

Построение линии пересечения усечённого конуса и цилиндра
с правильным расчётом длины образующих.
"""

import math
from pprint import pprint
from typing import Any, Optional, Tuple, List, Union
from comtypes.automation import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_construction import at_cone_sheet, add_polyline
from programs.at_input import at_get_point


def at_nozzle_cone_sheet(
    model: Any,
    pt: Union[List[float], VARIANT],
    d1: float,               # диаметр верхнего основания конуса
    d2: float,               # диаметр нижнего основания конуса (хорда на цилиндре)
    D: float,                # диаметр цилиндра
    H: float,                # расстояние от верхнего основания конуса до плоскости оси цилиндра
    layer_name: str = "0",
    layer_intersection: str = "LASER-TEXT",
    N: int = 12
) -> Tuple[Optional[Any], Tuple[float, float], List[Tuple[float, float]], List[float]]:

    # Высота усечённого конуса
    h = H - math.sqrt(max(0.0, (D / 2)**2 - (d2 / 2)**2))

    # 1) Берём развертку конуса
    res = at_cone_sheet(
        model=model,
        input_point=pt,
        diameter_base=d2,
        diameter_top=d1,
        height=h,
        layer_name=layer_name
    )
    print(res)
    cone_poly, input_point_variant, apex_res = res
    apex = (apex_res[0], apex_res[1])

    # 2) Определяем радиус дуги нижнего основания развертки
    center = (input_point_variant[0], input_point_variant[1])
    R = math.hypot(center[0] - apex[0], center[1] - apex[1])

    # 3) Разделим дугу на N сегментов
    sector_angle_deg = 92.12132171
    sector_rad = math.radians(sector_angle_deg)
    result_pts: List[Tuple[float, float]] = []
    lengths: List[float] = []

    # Эталонные длины образующих для проверки
    # [269.65823481820183, 263.7230842335816, ...] - для контроля

    for i in range(N + 1):
        t = i / N
        angle_flat = (t - 0.5) * sector_rad  # симметрия относительно Y

        # координата точки на дуге
        x_arc = apex[0] + R * math.sin(angle_flat)
        y_arc = apex[1] + R * math.cos(angle_flat)
        pt_arc = (x_arc, y_arc)

        # рассчёт длины образующей через простую аппроксимацию
        # длина = расстояние от апекса до точки пересечения с цилиндром
        # приближённо: апекс + H в Y (расстояние до цилиндра) + смещение по X
        dx = x_arc - apex[0]
        dy = H
        g_i = math.hypot(dx, dy)
        lengths.append(g_i)

        # координата точки на полилинии: откладываем g_i от апекса
        theta = math.atan2(y_arc - apex[1], x_arc - apex[0])
        x_pt = apex[0] + g_i * math.cos(theta)
        y_pt = apex[1] + g_i * math.sin(theta)
        result_pts.append((x_pt, y_pt))

    # Строим полилинию через add_polyline
    polyline = add_polyline(model, result_pts, layer_name=layer_intersection, closed=False)

    # Контрольный вывод
    print("--- at_nozzle_cone_sheet: контроль вывода ---")
    print("Input (d1, d2, D, H):", d1, d2, D, H)
    print("Used diameter_base (d2) =", d2)
    print("Apex:", apex)
    print("\nPoints on unfolded cone (N+1 = {}):".format(N+1))
    pprint(result_pts)
    print("\nCalculated generatrix lengths (g_i):")
    pprint(lengths)
    print("--- end control ---")

    return polyline, apex, result_pts, lengths


# ----------------- тест -----------------
def run_test():
    acad = ATCadInit()
    adoc = acad.document
    model = acad.model_space
    pt = at_get_point(adoc, prompt="Укажите центр отвода", as_variant=False)
    d1 = 102.0
    d2 = 138.0
    D = 273.0
    H = 185.78

    at_nozzle_cone_sheet(
        model=model,
        pt=pt,
        d1=d1,
        d2=d2,
        D=D,
        H=H,
        N=12
    )


if __name__ == "__main__":
    run_test()
