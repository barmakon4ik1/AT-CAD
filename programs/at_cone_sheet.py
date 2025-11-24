# -*- coding: utf-8 -*-
"""
at_cone_sheet.py

Построение развёртки усечённого конуса и линии пересечения с цилиндром.
Линия пересечения строится с точным совмещением апекса, и поворот вычисляется автоматически
из геометрии конуса и цилиндра.
"""
from typing import List, Optional, Tuple
import math

from programs.at_construction import add_polyline
from programs.at_input import at_get_point
import programs.at_run_cone as run_cone

Pt2 = Tuple[float, float]


def cone_geometry_from_chord(d_top: float, d_base: float, H: float):
    r_top = d_top / 2.0
    r_base = d_base / 2.0
    if r_base <= r_top:
        raise ValueError("Base diameter must be > top diameter")
    alpha = math.atan((r_base - r_top) / H)
    x_top = r_top / math.tan(alpha)
    s_top = math.hypot(x_top, r_top)
    s_chord = math.hypot(x_top + H, r_base)
    return alpha, x_top, r_top, r_base, H, s_top, s_chord


def _solve_for_xrel(tan_a: float, Xc: float, Yc: float, R: float, cos_psi: float) -> List[float]:
    t = tan_a * cos_psi
    A = 1.0 + t * t
    B = -2.0 * (Xc + t * Yc)
    C = Xc * Xc + Yc * Yc - R * R
    disc = B * B - 4.0 * A * C
    if disc < 0.0:
        return []
    sqrt_disc = math.sqrt(disc)
    x1 = (-B + sqrt_disc) / (2.0 * A)
    x2 = (-B - sqrt_disc) / (2.0 * A)
    if abs(x1 - x2) < 1e-12:
        return [x1]
    return [x1, x2]


def compute_intersection_points_on_development(
    d_top: float,
    d_base: float,
    H: float,
    D_cyl: float,
    ix: float,
    iy: float,
    N_psi: int = 720,
    debug: bool = True
) -> List[Pt2]:
    alpha, x_top, r_top, r_base, H_loc, s_top, s_chord = cone_geometry_from_chord(d_top, d_base, H)
    tan_a = math.tan(alpha)
    R = D_cyl / 2.0

    # Апекс развертки (минимальная Y)
    apex_y = iy - (s_top + s_chord) / 2.0
    apex_x = ix  # апекс по X совпадает с вертикальной осью развертки

    # Горизонтальный полуразмер пересечения с цилиндром
    d_hor = math.sqrt(max(0.0, R * R - r_base * r_base))
    X_plane_bottom = x_top + H_loc
    Yc = 0.0

    candidates = [
        ("bottom_hor_left", X_plane_bottom - d_hor),
        ("bottom_hor_right", X_plane_bottom + d_hor),
        ("mid_apex_bottom", (0.0 + X_plane_bottom) / 2.0)
    ]

    chosen_raw = None
    best_count = -1
    chosen_Xc = None
    for name, Xc in candidates:
        raw = []
        for i in range(N_psi):
            psi = 2.0 * math.pi * i / (N_psi - 1)
            roots = _solve_for_xrel(tan_a, Xc, Yc, R, math.cos(psi))
            for xr in roots:
                if x_top <= xr <= x_top + H_loc:
                    r = xr * tan_a
                    if r_top <= r <= r_base:
                        raw.append((psi, xr, r))
        if len(raw) > best_count:
            best_count = len(raw)
            chosen_raw = raw
            chosen_Xc = Xc

    if not chosen_raw:
        if debug:
            print("Не удалось построить точки пересечения")
        return []

    # сортировка по psi
    chosen_raw.sort(key=lambda t: t[0])

    # Определяем угол поворота линии, чтобы левая и правая точки нижнего основания совпадали
    # Левая точка нижнего основания на развертке
    left_x = ix - d_hor
    right_x = ix + d_hor
    y_base = apex_y + s_chord
    theta = math.atan2(y_base - apex_y, left_x - apex_x)  # угол наклона линии относительно апекса

    res_pts: List[Pt2] = []
    for psi, xr, r in chosen_raw:
        s = math.hypot(xr, r)
        phi = psi * math.sin(alpha)
        x0 = apex_x + s * math.cos(phi)
        y0 = apex_y + s * math.sin(phi)

        # поворот относительно апекса
        dx = x0 - apex_x
        dy = y0 - apex_y
        xr_rot = dx * math.cos(theta) - dy * math.sin(theta)
        yr_rot = dx * math.sin(theta) + dy * math.cos(theta)
        x_dev = apex_x + xr_rot
        y_dev = apex_y + yr_rot

        # ограничение по Y верхней точки
        if y_dev > y_base:
            y_dev = y_base
        res_pts.append((x_dev, y_dev))

    # убираем дубли
    eps = 1e-9
    cleaned: List[Pt2] = []
    for p in res_pts:
        if not cleaned or abs(cleaned[-1][0] - p[0]) > eps or abs(cleaned[-1][1] - p[1]) > eps:
            cleaned.append(p)
    res_pts = cleaned

    if debug:
        print(f"Точек линии пересечения: {len(res_pts)}")
        if res_pts:
            print("Начало:", res_pts[0], "Конец:", res_pts[-1])
            print("Апекс Y:", apex_y, "Максимальная Y:", y_base)
            print("Угол поворота (deg):", math.degrees(theta))

    return res_pts


def at_cone_sheet(
    model,
    input_point: List[float],
    d_top: float = 102.0,
    d_base: float = 138.0,
    h: float = 68.0,
    D_cylinder: float = 273.0,
    debug: bool = True
) -> Optional[bool]:
    try:
        ix, iy = float(input_point[0]), float(input_point[1])

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

        pts = compute_intersection_points_on_development(
            d_top=d_top,
            d_base=d_base,
            H=h,
            D_cyl=D_cylinder,
            ix=ix,
            iy=iy,
            N_psi=720,
            debug=debug
        )

        if not pts or len(pts) < 2:
            print("Недостаточно точек для линии пересечения")
            return True

        add_polyline(model, pts, layer_name="LASER-TEXT", closed=False)
        print(f"Линия пересечения добавлена на слой LASER-TEXT (точек: {len(pts)})")
        return True

    except Exception as e:
        print("Ошибка:", e)
        return None


if __name__ == "__main__":
    from config.at_cad_init import ATCadInit
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    pt = at_get_point(adoc, prompt="Укажите точку вставки (центр развертки)", as_variant=False)
    at_cone_sheet(model, pt, debug=True)
