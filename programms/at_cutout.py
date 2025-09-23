"""
File: programms/at_cutout.py
Назначение: Построение выреза в трубе для штуцера
           (версия: offset — угол поворота в радианах, т.е. вращение вокруг оси)
"""

import math
from typing import Dict, Any, List, Tuple
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_text, add_polyline, add_dimension
from programms.at_geometry import ensure_point_variant, convert_to_variant_points
from windows.at_gui_utils import show_popup
from config.at_config import TEXT_HEIGHT_SMALL, DEFAULT_DIM_OFFSET

# -----------------------------
# Локальные переводы модуля
# -----------------------------
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
}
loc.register_translations(TRANSLATIONS)


# -----------------------------
# Построение контура (LISP-подобно), с вращением на угол offset (в радианах)
# -----------------------------
def build_cutout_contour_rotated(
    radius_main: float,
    radius_branch: float,
    offset_rad: float = 0.0,
    steps_quarter: int = 45
) -> List[Tuple[float, float]]:
    """
    Построение 2D-контура выреза (список пар (x,y)) по схеме LISP:
      - theta ∈ [0, pi/2] — параметр по окружности штуцера
      - alpha = asin((r / R) * sin(theta))
      - для правой стороны: x = R*(+alpha + offset_rad)
        для левой стороны:  x = R*(-alpha + offset_rad)
      - y = ± r * cos(theta)

    offset_rad интерпретируется как угол поворота штуцера вокруг продольной оси трубы (радианы).
    steps_quarter — число шагов на квартал (рекомендуется >= 8).
    """
    if steps_quarter < 4:
        steps_quarter = 4

    # Если branch больше main, как в старой LISP версии — ограничим r = R
    if radius_branch > radius_main:
        radius_branch = radius_main

    points: List[Tuple[float, float]] = []

    # theta в квартале 0..pi/2
    theta_list = [i * (0.5 * math.pi) / steps_quarter for i in range(0, steps_quarter + 1)]

    # Правый верх (theta 0..pi/2), x = R*(+alpha + offset)
    for theta in theta_list:
        s = math.sin(theta)
        arg = (radius_branch / radius_main) * s
        # защита asin
        if arg > 1.0:
            if arg - 1.0 < 1e-9:
                arg = 1.0
            else:
                continue
        alpha = math.asin(arg)
        x = radius_main * ( alpha + offset_rad )
        y = radius_branch * math.cos(theta)
        points.append((x, y))

    # Правый низ (theta pi/2..0)
    for theta in reversed(theta_list):
        s = math.sin(theta)
        arg = (radius_branch / radius_main) * s
        if arg > 1.0:
            if arg - 1.0 < 1e-9:
                arg = 1.0
            else:
                continue
        alpha = math.asin(arg)
        x = radius_main * ( alpha + offset_rad )
        y = - (radius_branch * math.cos(theta))
        points.append((x, y))

    # Левый низ (theta 0..pi/2), x = R*(-alpha + offset)
    for theta in theta_list:
        s = math.sin(theta)
        arg = (radius_branch / radius_main) * s
        if arg > 1.0:
            if arg - 1.0 < 1e-9:
                arg = 1.0
            else:
                continue
        alpha = math.asin(arg)
        x = radius_main * ( -alpha + offset_rad )
        y = - (radius_branch * math.cos(theta))
        points.append((x, y))

    # Левый верх (theta pi/2..0)
    for theta in reversed(theta_list):
        s = math.sin(theta)
        arg = (radius_branch / radius_main) * s
        if arg > 1.0:
            if arg - 1.0 < 1e-9:
                arg = 1.0
            else:
                continue
        alpha = math.asin(arg)
        x = radius_main * ( -alpha + offset_rad )
        y = radius_branch * math.cos(theta)
        points.append((x, y))

    # Убираем подряд идущие дубликаты (численная точность)
    cleaned: List[Tuple[float, float]] = []
    last = None
    for p in points:
        if last is None or (abs(p[0] - last[0]) > 1e-9 or abs(p[1] - last[1]) > 1e-9):
            cleaned.append(p)
            last = p

    return cleaned


# -----------------------------
# Основная функция
# -----------------------------
def at_cutout(data: Dict[str, Any]) -> bool:
    """
    Основная функция построения выреза штуцера.

    Параметры (в data):
      insert_point: [x, y, z] — точка вставки, центр развертки (обяз.)
      diameter: диаметр отвода (r*2)
      diameter_main: диаметр основной трубы (R*2)
      offset: угол поворота штуцера вокруг продольной оси трубы (в радианах, опционально, default=0.0)
      steps: общее число делений полного круга (опционально; по умолчанию 180).
      layer_name, order_number, detail_number, material, thickness — опционально
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return None

        insert_point = data.get("insert_point", [0.0, 0.0, 0.0])
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) < 2:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return None

        diameter = float(data.get("diameter", 0.0))
        diameter_main = float(data.get("diameter_main", 0.0))
        offset = float(data.get("offset", 0.0))  # интерпретируем как радианы
        steps = int(data.get("steps", 180))
        layer_name = data.get("layer_name", "0")
        material = data.get("material", "")
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")

        if diameter <= 0 or diameter_main <= 0:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return None

        r = diameter / 2.0
        R = diameter_main / 2.0

        # LISP-поведение: если r > R — приводим r = R
        if r > R:
            r = R

        # шаги: переводим в steps_quarter
        steps_quarter = max(4, int(round(steps / 4.0)))

        # строим контур (offset в радианах)
        contour_pairs = build_cutout_contour_rotated(R, r, offset_rad=offset, steps_quarter=steps_quarter)
        if not contour_pairs:
            show_popup(loc.get("contour_not_built"), popup_type="error")
            return None

        # сдвигаем контур так, чтобы insert_point был центром развёртки:
        ipx, ipy = float(insert_point[0]), float(insert_point[1])
        contour_global_pairs = [(ipx + x, ipy + y) for (x, y) in contour_pairs]

        # Преобразуем в VARIANT и рисуем полилинию
        var_pts = convert_to_variant_points(contour_global_pairs)
        poly = add_polyline(model, var_pts, layer_name=layer_name, closed=True)
        if poly is None:
            show_popup(loc.get("build_error").format("Не удалось создать полилинию"), popup_type="error")
            return None

        # вертикальный размер (диаметр отвода) и тексты
        # центр штуцера в развёртке — x = ipx + R * offset (alpha=0 => x=R*offset)
        center_x = ipx + R * offset
        center_y = ipy

        p_top = ensure_point_variant([center_x, center_y + r, 0.0])
        p_bottom = ensure_point_variant([center_x, center_y - r, 0.0])
        # add_dimension(adoc, "V", p_bottom, p_top, offset=DEFAULT_DIM_OFFSET)

        k_text = f"{order_number}"
        f_text = k_text if not detail_number else f"{k_text}-{detail_number}"
        text_point = ensure_point_variant([center_x, center_y - (r + 30), 0.0])
        try:
            add_text(model, text_point, f_text, layer_name="schrift", text_height=TEXT_HEIGHT_SMALL, text_alignment=12)
        except Exception as e:
            show_popup(loc.get("build_error").format(f"Ошибка при добавлении текста: {str(e)}"), popup_type="error")
            return None

        thickness = data.get("thickness", "")
        if thickness != "":
            mat_text = loc.get("material_text").format(thickness, material)
            mat_point = ensure_point_variant([center_x, center_y + (r + 20), 0.0])
            add_text(model, mat_point, mat_text, layer_name="AM_5", text_height=TEXT_HEIGHT_SMALL, text_alignment=0)

        regen(adoc)
        return True

    except Exception as e:
        show_popup(loc.get("build_error").format(str(e)), popup_type="error")
        return None


if __name__ == "__main__":
    # Примеры для тестирования (offset — радианы):
    tests = [
        {"insert_point": [0.0, 0.0, 0.0], "diameter": 150, "diameter_main": 300, "offset": 0.0, "steps": 90},
        {"insert_point": [0.0, 0.0, 0.0], "diameter": 150, "diameter_main": 300, "offset": 0.5, "steps": 90},
        {"insert_point": [0.0, 0.0, 0.0], "diameter": 300, "diameter_main": 300, "offset": 0, "steps": 90},
    ]
    for t in tests:
        at_cutout(t)
