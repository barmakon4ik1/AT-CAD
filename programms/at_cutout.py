# -*- coding: utf-8 -*-
"""
File: programms/at_cutout.py
Назначение: Построение выреза в трубе для штуцера.
Поддерживает три режима:
    - polyline (отрезки)
    - bulge (полилиния с дугами)
    - spline (сплайн)
Принцип работы:
1. Аналитически находим φ-границы пересечения (|R sin φ - o| = r)
2. Выбираем интервал, содержащий phi_max = asin(offset / R)
3. Дискретизируем интервал φ: s = R * φ (радианы), z = ± sqrt(r² - (R sin φ - o)²)
4. Формируем верхнюю и нижнюю ветви
5. Вычисляем bulges локально по трём точкам с добавлением фиктивных точек для скругления концов
6. Собираем контур: верхняя ветвь + нижняя перевёрнутая без дубликатов концов
"""

import math
from typing import Dict, Any, List, Tuple

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import (
    add_polyline,
    add_dimension,
    add_line,
    add_polyline_with_bilge,
    add_spline,
)
from programms.at_geometry import (
    ensure_point_variant,
    convert_to_variant_points,
    circle_center_from_points,
)
from windows.at_gui_utils import show_popup

# Переводы сообщений
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "invalid_point_format": {
        "ru": "Точка вставки должна быть [x, y, 0]",
        "de": "Einfügepunkt muss [x, y, 0] sein",
        "en": "Insertion point must be [x, y, 0]"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "de": "Baufehler: {0}",
        "en": "Build error: {0}"
    },
    "contour_not_built": {
        "ru": "Контур выреза не построен (нет допустимых точек)",
        "de": "Schnittkontur nicht erstellt (keine gültigen Punkte)",
        "en": "Cutout contour not built (no valid points)"
    },
    "unknown_mode": {
        "ru": "Неизвестный режим: {0}",
        "de": "Unbekannter Modus: {0}",
        "en": "Unknown mode: {0}"
    },
}
loc.register_translations(TRANSLATIONS)


def compute_cyl_cyl_intersection_unwrap(
    R: float,
    r: float,
    offset: float,
    steps: int = 2048,
    eps: float = 1e-12
) -> List[List[Tuple[float, float, float]]]:
    """
    Возвращает одну полилинию (замкнутый контур) развёртки пересечения.
    Формат: [ [(s, z, bulge), ...] ] или [] если нет пересечения.

    Принцип:
    - аналитически находим φ-границы пересечения (|R sin φ - o| = r),
    - выбираем интервал, содержащий asin(o/R),
    - дискретизируем интервал φ, s = R * φ (радианы), z = ± sqrt(r² - (R sin φ - o)²),
    - формируем upper и lower ветви,
    - собираем контур: upper forward + lower reversed без дубликатов концов,
    - вычисляем bulges локально по трём точкам (prev, current, next).
    """
    import math
    from programms.at_geometry import circle_center_from_points

    two_pi = 2.0 * math.pi

    if R <= 0 or r < 0:
        return []

    # --- границы пересечения ---
    s_low = (offset - r) / R
    s_high = (offset + r) / R
    if s_low > 1.0 or s_high < -1.0:
        return []

    s_low_clamped = max(-1.0, min(1.0, s_low))
    s_high_clamped = max(-1.0, min(1.0, s_high))
    phi_a = math.asin(s_low_clamped)
    phi_b = math.asin(s_high_clamped)
    if phi_a > phi_b:
        phi_a, phi_b = phi_b, phi_a

    I1 = (phi_a, phi_b)
    I2 = (math.pi - phi_b, math.pi - phi_a)

    # Выбираем интервал, содержащий phi_max
    phi_max = math.asin(offset / R) if abs(offset / R) <= 1 else 0
    def contains_phi(interval, target):
        s, e = interval
        if s <= e:
            return s <= target <= e
        else:
            return target >= s or target <= e

    chosen_interval = I1 if contains_phi(I1, phi_max) else I2
    start_phi, end_phi = chosen_interval
    if end_phi <= start_phi:
        end_phi += two_pi

    segment_length = end_phi - start_phi
    if segment_length <= 0:
        return []

    # --- дискретизация ---
    n_pts = max(3, int(math.ceil(steps * (segment_length / two_pi))))
    phis = [start_phi + (i / (n_pts - 1)) * segment_length for i in range(n_pts)]

    s_list: List[float] = []
    z_list: List[float] = []
    for ph in phis:
        y = R * math.sin(ph)
        dy = y - offset
        val = r * r - dy * dy
        if val < -eps:
            continue
        z_abs = math.sqrt(max(0.0, val))
        s = R * ph
        s_list.append(s)
        z_list.append(z_abs)

    if not s_list:
        return []

    # --- формируем контур верх/низ ---
    top_pts: List[Tuple[float, float]] = []
    bottom_pts: List[Tuple[float, float]] = []
    tol_z = 1e-12
    for s, z in zip(s_list, z_list):
        if abs(z) <= tol_z:
            top_pts.append((s, 0.0))
            bottom_pts.append((s, 0.0))
        else:
            top_pts.append((s, z))
            bottom_pts.append((s, -z))

    contour_xy: List[Tuple[float, float]] = top_pts + list(reversed(bottom_pts))[1:]

    # --- удаляем дубликаты ---
    dedup_tol = 1e-9
    dedup: List[Tuple[float, float]] = [contour_xy[0]]
    for pt in contour_xy[1:]:
        last = dedup[-1]
        if abs(pt[0] - last[0]) > dedup_tol or abs(pt[1] - last[1]) > dedup_tol:
            dedup.append(pt)
    contour_xy = dedup

    n = len(contour_xy)
    if n < 3:
        return []

    # --- вычисление bulges ---
    bulges_contour = []

    # Подменяем фиктивные точки реальными: -2 и 1
    extended_pts = [contour_xy[-2]] + contour_xy + [contour_xy[1]]

    for i in range(1, n+1):
        prev_i = i - 1
        next_i = i + 1
        p0 = extended_pts[prev_i]
        p1 = extended_pts[i]
        p2 = extended_pts[next_i]
        center = circle_center_from_points(p0, p1, p2)
        if center is None:
            bulges_contour.append(0.0)
            continue
        cx, cy = center
        ang1 = math.atan2(p1[1] - cy, p1[0] - cx)
        ang2 = math.atan2(p2[1] - cy, p2[0] - cx)
        sweep = ang2 - ang1
        sweep = (sweep + math.pi) % (2*math.pi) - math.pi
        bulges_contour.append(math.tan(sweep / 4.0))

    contour_with_bulge: List[Tuple[float, float, float]] = [
        (s, z, b) for (s, z), b in zip(contour_xy, bulges_contour)
    ]

    return [contour_with_bulge]




def at_cutout(data: Dict[str, Any]) -> bool:
    """
    Интеграция с AutoCAD: строит контур выреза.
    Поддерживает режимы: polyline, bulge, spline.
    Ожидаемые ключи в data:
      - insert_point: [x, y, z]
      - diameter: диаметр отвода
      - diameter_main: диаметр основной трубы
      - offset: отступ осей
      - steps: число шагов дискретизации
      - layer_name: имя слоя
      - mode: "polyline", "bulge" или "spline"
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        insert_point = data.get("insert_point")
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) < 3:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return False

        diameter = float(data.get("diameter", 0.0))
        diameter_main = float(data.get("diameter_main", 0.0))
        offset = float(data.get("offset", 0.0))
        steps = int(data.get("steps", 2048))
        layer_name = data.get("layer_name", "0")
        mode = data.get("mode", "bulge").lower()

        r = diameter / 2.0
        R = diameter_main / 2.0
        x0, y0 = insert_point[0], insert_point[1]

        # Контрольные линии
        center_s = R * math.asin(offset / R) if abs(offset / R) <= 1 else offset
        p_top = ensure_point_variant([x0 + center_s, y0 + r, 0.0])
        p_bottom = ensure_point_variant([x0 + center_s, y0 - r, 0.0])
        p_left = ensure_point_variant([x0 + center_s - 1.3 * r, y0, 0.0])
        p_right = ensure_point_variant([x0 + center_s + 1.3 * r, y0, 0.0])
        add_dimension(adoc, "V", p_bottom, p_top, offset=r + 100)
        add_line(model, p_bottom, p_top, layer_name="AM_7")
        add_line(model, p_left, p_right, layer_name="AM_7")

        polylines = compute_cyl_cyl_intersection_unwrap(R, r, offset, steps)
        if not polylines:
            show_popup(loc.get("contour_not_built"), popup_type="error")
            return False

        # Переносим точки в систему координат вставки
        for poly in polylines:
            if mode == "polyline":
                points_xy = [[x0 + s, y0 + z] for s, z, _ in poly]
                pts_variant = convert_to_variant_points(points_xy)
                add_polyline(model, pts_variant, closed=True, layer_name=layer_name)
            elif mode == "bulge":
                pts = [(x0 + s, y0 + z, b) for s, z, b in poly]
                add_polyline_with_bilge(model, pts, layer_name=layer_name, closed=True)
            elif mode == "spline":
                points_xy = [[x0 + s, y0 + z] for s, z, _ in poly]
                add_spline(model, points_xy, layer_name=layer_name, closed=True)
            else:
                show_popup(loc.get("unknown_mode").format(mode), popup_type="info")
                return False

        regen(adoc)
        return True

    except Exception as e:
        show_popup(loc.get("build_error").format(str(e)), popup_type="error")
        return False


if __name__ == "__main__":
    data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter": 200.0,
        "diameter_main": 300.0,
        "offset": 0,
        "steps": 60,
        "layer_name": "0",
        "mode": "bulge"
    }
    at_cutout(data)
