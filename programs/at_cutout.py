# -*- coding: utf-8 -*-
"""
File: programs/at_cutout.py
Назначение: Построение выреза в трубе для штуцера.
Возвращает согласованный словарь результата (всегда).
"""

import math
from typing import Dict, Any, List, Tuple
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_construction import (
    add_polyline,
    add_dimension,
    add_line,
    add_spline,
    add_text,
)
from programs.at_geometry import (
    ensure_point_variant,
    convert_to_variant_points,
    circle_center_from_points,
    offset_point,
)
from programs.at_input import at_point_input
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
    steps: int = 180,
    eps: float = 1e-12
) -> List[List[Tuple[float, float, float]]]:
    """
    Возвращает список полилиний развёртки пересечения (может быть одна).
    Формат: [ [(s, z, bulge), ...] ] или [] если нет пересечения.
    (Эта функция почти неизменна — аккуратно защищена от краевых случаев.)
    """
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
    phi_max = math.asin(offset / R) if abs(offset / R) <= 1 else 0.0

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
    top_pts = []
    bottom_pts = []
    tol_z = 1e-12
    for s, z in zip(s_list, z_list):
        if abs(z) <= tol_z:
            top_pts.append((s, 0.0))
            bottom_pts.append((s, 0.0))
        else:
            top_pts.append((s, z))
            bottom_pts.append((s, -z))

    # Собираем контур: верхняя ветвь + нижняя перевёрнутая без дубликатов концов
    contour_xy = top_pts + list(reversed(bottom_pts))[1:]

    # Удаляем дубликаты
    dedup_tol = 1e-6
    dedup = [contour_xy[0]]
    for pt in contour_xy[1:]:
        last = dedup[-1]
        if abs(pt[0] - last[0]) > dedup_tol or abs(pt[1] - last[1]) > dedup_tol:
            dedup.append(pt)
    contour_xy = dedup

    # Закрываем контур
    if len(contour_xy) > 1:
        tol = 1e-6
        if abs(contour_xy[-1][0] - contour_xy[0][0]) > tol or abs(contour_xy[-1][1] - contour_xy[0][1]) > tol:
            contour_xy.append(contour_xy[0])

    if len(contour_xy) < 3:
        return []

    # --- вычисление bulges ---
    bulges_contour = []
    extended_pts = [contour_xy[-1]] + contour_xy + [contour_xy[0]]

    for i in range(1, len(contour_xy) + 1):
        p0 = extended_pts[i - 1]
        p1 = extended_pts[i]
        p2 = extended_pts[i + 1]
        center = circle_center_from_points(p0, p1, p2)
        if center is None:
            bulges_contour.append(0.0)
            continue
        cx, cy = center
        ang1 = math.atan2(p1[1] - cy, p1[0] - cx)
        ang2 = math.atan2(p2[1] - cy, p2[0] - cx)
        sweep = ang2 - ang1
        sweep = (sweep + math.pi) % (2 * math.pi) - math.pi
        if abs(sweep) < 1e-12:
            bulges_contour.append(0.0)
        else:
            bulges_contour.append(math.tan(sweep / 4.0))

    if len(bulges_contour) >= 2:
        bulges_contour[0] = bulges_contour[-2]

    contour_with_bulge = [(s, z, b) for (s, z), b in zip(contour_xy, bulges_contour)]
    return [contour_with_bulge]


def at_cutout(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Интеграция с AutoCAD: строит контур выреза и возвращает словарь результата.
    Ожидаемые ключи в data:
      - insert_point: [x, y, z]
      - diameter: диаметр отвода (r*2)
      - diameter_main: диаметр основной трубы (R*2)
      - offset: смещение (по смыслу функции) — если не задано, 0
      - steps: число шагов дискретизации
      - layer_name: имя слоя
      - mode: 'polyline'|'bulge'|'spline'
      - text: подпись
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        insert_point = data.get("insert_point")
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) < 3:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return {"success": False, "error": loc.get("invalid_point_format")}

        # Читаем параметры (fallbacks)
        diameter = float(data.get("diameter", 0.0))
        diameter_main = float(data.get("diameter_main", 0.0))
        offset = float(data.get("offset", 0.0))
        steps = int(data.get("steps", 2048))
        mode = data.get("mode", "bulge").lower()
        text = data.get("text", "")

        # Минимальная валидация
        if diameter <= 0 or diameter_main <= 0:
            err = "diameter and diameter_main must be > 0"
            show_popup(err, popup_type="error")
            return {"success": False, "error": err}

        r = diameter / 2.0
        R = diameter_main / 2.0
        x0, y0 = insert_point[0], insert_point[1]

        # Контрольные линии (для наглядности в CAD)
        center_s = R * math.asin(offset / R) if abs(offset / R) <= 1 else offset
        p_top = ensure_point_variant([x0 + center_s, y0 + r, 0.0])
        p_bottom = ensure_point_variant([x0 + center_s, y0 - r, 0.0])
        p_left = ensure_point_variant([x0 + center_s - 1.3 * r, y0, 0.0])
        p_right = ensure_point_variant([x0 + center_s + 1.3 * r, y0, 0.0])
        try:
            add_dimension(adoc, "V", p_bottom, p_top, offset=r + 100)
            add_line(model, p_bottom, p_top, layer_name="AM_7")
            add_line(model, p_left, p_right, layer_name="AM_7")
        except Exception:
            # не критично: если у пользователя нет интерфейса размеров — продолжаем
            pass

        # Сопроводительный текст
        try:
            point_text = ensure_point_variant(offset_point(insert_point, 20, 20))
            add_text(model, point_text, text, layer_name="AM_5", text_height=30)
        except Exception:
            pass

        # Основная геометрия
        polylines = compute_cyl_cyl_intersection_unwrap(R, r, offset, steps)
        if not polylines:
            show_popup(loc.get("contour_not_built"), popup_type="error")
            return {"success": False, "error": loc.get("contour_not_built")}

        # Рисуем и формируем outline в единообразном формате
        outlines = []
        for poly in polylines:
            if mode == "polyline":
                points_xy = [[x0 + s, y0 + z] for s, z, _ in poly]
                pts_variant = convert_to_variant_points(points_xy)
                add_polyline(model, pts_variant, layer_name="0", closed=True)
                outlines.extend([{"x": px, "y": py} for px, py in points_xy])
            elif mode == "bulge":
                pts = [(x0 + s, y0 + z, b) for s, z, b in poly]
                add_polyline(model, pts, layer_name="0", closed=True)
                outlines.extend([{"x": px, "y": py, "bulge": b} for px, py, b in pts])
            elif mode == "spline":
                points_xy = [[x0 + s, y0 + z] for s, z, _ in poly]
                pts_variant = convert_to_variant_points(points_xy)
                add_spline(model, pts_variant, layer_name="0", closed=True)
                outlines.extend([{"x": px, "y": py} for px, py in points_xy])
            else:
                msg = loc.get("unknown_mode").format(mode)
                show_popup(msg, popup_type="info")
                return {"success": False, "error": msg}

        regen(adoc)
        return {
            "success": True,
            "outline": outlines,
            "metadata": {
                "insert_point": insert_point,
                "diameter": diameter,
                "diameter_main": diameter_main,
                "offset": offset,
                "steps": steps,
                "mode": mode,
                "text": text
            }
        }

    except Exception as e:
        show_popup(loc.get("build_error").format(str(e)), popup_type="error")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    data = {
        "insert_point": at_point_input(adoc, prompt=loc.get("select_point", "Укажите центр отвода"), as_variant=False),
        "diameter": 35,
        "diameter_main": 794,
        "offset": 300,
        "steps": 360,
        "mode": "polyline",
        "text": ""
    }
    print(at_cutout(data))
