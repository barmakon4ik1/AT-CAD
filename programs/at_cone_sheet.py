# -*- coding: utf-8 -*-
"""
at_cone_sheet.py

Построение развёртки усечённого конуса и линии пересечения с цилиндром.
Использует модуль at_run_cone для построения развёртки конуса.
Линия пересечения строится на слое "LASER-TEXT".
"""

from typing import List, Optional
from programs.at_construction import add_polyline
from programs.at_input import at_get_point
import programs.at_run_cone as run_cone
import math

Pt2 = tuple[float, float]

# ---------------- Геометрия конуса ----------------
def cone_geometry(d_top: float, d_base: float, h: float):
    """Возвращает полуугол конуса, расстояние до верхнего основания и s_base"""
    r_top = d_top / 2
    r_base = d_base / 2
    if r_base <= r_top:
        raise ValueError("Base diameter must be > top diameter")
    alpha = math.atan((r_base - r_top) / h)
    x_top = r_top / math.tan(alpha)
    s_base = math.hypot(x_top + h, r_base)
    return alpha, x_top, r_top, r_base, h

# ---------------- Проекция точки на развёртку ----------------
def map_point_to_development(x_from_top, y, z, alpha, x_top):
    """Проекция 3D точки на развёртку конуса"""
    s = (x_from_top + x_top) / math.cos(alpha)
    psi = math.atan2(z, y)
    phi = psi * math.sin(alpha)
    return s * math.cos(phi), s * math.sin(phi)

# ---------------- Линия пересечения ----------------
def compute_intersection(d_top, d_base, h, D_cyl, ix, iy, N_theta=360):
    """
    Строим линию пересечения конуса с цилиндром.
    Конус вдавлен в цилиндр сбоку, нижнее основание уходит внутрь цилиндра.
    """
    alpha, x_top, r_top, r_base, H = cone_geometry(d_top, d_base, h)
    R_cyl = D_cyl / 2

    dev_pts: List[Pt2] = []

    for i in range(N_theta):
        theta = 2 * math.pi * i / (N_theta - 1)
        y_cyl = R_cyl * math.cos(theta)
        z_cyl = R_cyl * math.sin(theta)
        r_cyl = math.hypot(y_cyl, z_cyl)

        # Найдём x_from_top для точки пересечения конуса с цилиндром
        if r_cyl < r_top or r_cyl > r_base:
            continue  # не пересекает конус
        x_from_top = H * (r_cyl - r_top) / (r_base - r_top)

        xdev, ydev = map_point_to_development(x_from_top, y_cyl, z_cyl, alpha, x_top)
        dev_pts.append((ix + xdev, iy + ydev))

    # Сортировка по углу вокруг точки вставки
    dev_pts = sorted(dev_pts, key=lambda t: math.atan2(t[1]-iy, t[0]-ix))

    # Удаление дублей
    res: List[Pt2] = []
    eps = 1e-9
    for x, y in dev_pts:
        if not res or abs(x - res[-1][0]) > eps or abs(y - res[-1][1]) > eps:
            res.append((x, y))
    return res

# ---------------- Основная функция ----------------
def at_cone_sheet(
    model,
    input_point: List[float],
    d_top: float = 102.0,
    d_base: float = 138.0,
    h: float = 68.0,
    D_cylinder: float = 273.0
) -> Optional[bool]:
    """
    Построение развёртки конуса и линии пересечения с цилиндром
    """
    try:
        ix, iy = float(input_point[0]), float(input_point[1])

        # ---------------- Развёртка конуса ----------------
        data = {
            "insert_point": [ix, iy, 0.0],
            "diameter_top": d_top,
            "diameter_base": d_base,
            "height": h,
            "material": "",
            "thickness": 0.0,
            "thickness_text": "0",
            "order_number": "",
            "detail_number": ""
        }
        run_cone.main(data)

        # ---------------- Линия пересечения ----------------
        line_pts = compute_intersection(d_top, d_base, h, D_cylinder, ix, iy)

        if not line_pts or len(line_pts) < 2:
            print("Недостаточно точек для линии пересечения")
            return True

        add_polyline(model, line_pts, layer_name="LASER-TEXT", closed=False)
        print("Линия пересечения построена на слой LASER-TEXT")
        return True

    except Exception as e:
        print("Ошибка:", e)
        return None

# ---------------- Тестовый запуск ----------------
if __name__ == "__main__":
    from config.at_cad_init import ATCadInit
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    pt = at_get_point(adoc, prompt="Укажите точку вставки (центр развёртки)", as_variant=False)
    at_cone_sheet(model, pt)
