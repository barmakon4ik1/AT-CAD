# -*- coding: utf-8 -*-
"""
programs/at_nozzle_cone.py

Построение развертки линии пересечения усечённого конуса и цилиндра (патрубок/врезка).
Модуль разработан в стиле и API, совместимом с programs/at_nozzle.py.

Автор: A.Tutubalin
Дата: 2025
"""

from __future__ import annotations

import math
import logging
from typing import Any, Dict, List, Tuple

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_construction import at_cone_sheet, add_polyline, add_text
from programs.at_geometry import ensure_point_variant, rad_to_deg, polar_point
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup
from config.at_config import TEXT_HEIGHT_SMALL, TEXT_DISTANCE, TEXT_HEIGHT_BIG

# Локальные переводы (если нужно, можно расширить)
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "en": "No data provided"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "en": "Build error: {0}"
    },
    "unknown_mode": {
        "ru": "Режим не поддерживается (используется polyline): {0}",
        "en": "Mode not supported (using polyline): {0}"
    },
}
loc.register_translations(TRANSLATIONS)


# ---------------------------------------------------------------------------
# Вспомогательные геометрические функции (версия без классов)
# ---------------------------------------------------------------------------

def diameter_at_height(z: float, diameter_base: float, diameter_top: float,
                       height_cone: float) -> float:
    """Линейный диаметр сечения конуса на высоте z от нижнего основания."""
    r2 = diameter_base / 2.0
    r1 = diameter_top / 2.0
    return 2.0 * (r2 - z * (r2 - r1) / height_cone)


def generatrix_by_diameter(d: float, diameter_base: float, L_full: float) -> float:
    """Длина образующей, пропорциональная диаметру сечения."""
    return L_full * (d / diameter_base)


def finder_z(alpha: float, diameter_pipe: float, diameter_base: float,
             height_lower: float) -> float:
    """
    Высота z от нижнего основания конуса до линии пересечения с цилиндром
    для угла alpha (в радианах) вдоль полу-хорды.
    """
    cos_a = math.cos(alpha)
    # радиус цилиндра
    R = diameter_pipe / 2.0
    # половина хорды в данном направлении = (diameter_base * cos_a) / 2
    half_chord = (diameter_base * cos_a) / 2.0
    # расстояние от оси цилиндра до точки пересечения (по Z):
    # из x^2 + z'^2 = R^2 => z' = sqrt(R^2 - x^2)
    # потом смещаем на height_lower, чтобы получить z от нижнего основания
    z_from_base = math.sqrt(max(0.0, R * R - half_chord * half_chord)) - height_lower
    return z_from_base


# ---------------------------------------------------------------------------
# Построение полилинии пересечения на развертке
# ---------------------------------------------------------------------------

def build_intersection_points_on_flat(apex: Tuple[float, float, float],
                                      theta_rad: float,
                                      generatrix_list: List[float]) -> List[List[float]]:
    """
    Возвращает список точек [x,y] для полилинии линии пересечения на развертке.
    apex: (x,y,z) из at_cone_sheet
    theta_rad: полный угол сектора развертки (в радианах)
    generatrix_list: список длин образующих (N+1)
    """
    Ax, Ay, _ = apex
    n = len(generatrix_list) - 1
    if n <= 0:
        return []

    step = theta_rad / n
    pts: List[List[float]] = []
    for i, g in enumerate(generatrix_list):
        phi = i * step
        x = Ax + g * math.cos(phi)
        y = Ay + g * math.sin(phi)
        pts.append([x, y])
    return pts


def rotate_points(points: List[List[float]], angle_deg: float,
                  origin: Tuple[float, float, float]) -> List[List[float]]:
    """Поворачивает список точек на angle_deg вокруг origin (ox,oy)."""
    ox, oy, _ = origin
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    out: List[List[float]] = []
    for x, y in points:
        tx, ty = x - ox, y - oy
        rx = tx * ca - ty * sa
        ry = tx * sa + ty * ca
        out.append([rx + ox, ry + oy])
    return out

# -----------------------------
# Основная функция
# -----------------------------
def main(data):
    """
    Чтобы функция корректно работала в связке с остальными программами в основном окне.
    """
    return at_nozzle_cone(data)

# ---------------------------------------------------------------------------
# Основная логика: парсер входного словаря -> геометрия -> развертка
# ---------------------------------------------------------------------------

def at_nozzle_cone(data: Dict[str, Any], params=None) -> bool:
    """
    Основная функция построения развертки патрубка-конуса.

    Поддерживает входной словарь в стиле at_nozzle.py. Выполняет:
        - чтение и маппинг параметров
        - вычисление геометрии (высоты, L_full и т.п.)
        - формирование списка длин образующих (N+1)
        - получение развертки конуса через at_cone_sheet
        - построение полилинии на развертке и добавление её в модель

    Возвращает True при успехе, False при ошибке.
    """
    try:
        # --- cad init
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return False

        # --- чтение и маппинг параметров
        insert_point = data.get("insert_point")
        if insert_point is None:
            at_get_point(adoc, prompt=loc.get("select_point", "Укажите точку вставки"), as_variant=False)

        diameter_base = float(data.get("diameter_base", 0.0))
        diameter_pipe = float(data.get("diameter_pipe", 0.0))
        height_full = float(data.get("height_full", 0.0))
        diameter_top = float(data.get("diameter_top", 0.0))

        # остальное — дополнительный набор (по умолчанию)
        N = int(data.get("N", 360))
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")

        # ensure insert_point is 3-length list
        insert_point = list(map(float, insert_point[:3]))
        data["insert_point"] = insert_point

        # Проверки
        if diameter_base <= 0 or diameter_pipe <= 0 or diameter_top <= 0:
            show_popup("Invalid diameters", popup_type="error")
            return False

        if N <= 2:
            show_popup("Invalid accuracy (N)", popup_type="error")
            return False

        # ---------------------------------------------------------------------
        # Геометрические вычисления
        # ---------------------------------------------------------------------
        # высота усеченного участка конуса (от нижнего основания до "верхней грани" пересечения)
        height_cone = height_full - math.sqrt(max(0.0, (diameter_pipe / 2.0) ** 2 - (diameter_base / 2.0) ** 2))

        # высота от плоскости цилиндра до нижнего основания конуса
        height_lower = height_full - height_cone

        # высота от верхнего основания до апекса (полная у вершины)
        # (для усечённого конуса при подобии)
        height_top = height_cone / (diameter_base / diameter_top - 1.0)

        # полная образующая от вершины до нижнего основания конуса
        L_full = math.hypot(height_cone + height_top, diameter_base / 2.0)

        # ---------------------------------------------------------------------
        # Формирование списка образующих (N+1)
        # алгоритм:
        #  1) делим полу-хорду на угловые шаги в радианах (0..pi)
        #  2) для каждого alpha находим z = finder_z(alpha)
        #  3) по z находим диаметр сечения D(z)
        #  4) по D(z) — образующую
        # ---------------------------------------------------------------------
        gens: List[float] = []
        # Нам нужен полуинтервал 0..pi (полуокружность) — но мы в итоге возьмём 0..2pi
        # В реализации на развертке мы берём равномерную сетку по углу вокруг оси
        # Используем шаг по полу-хорде: угловой шаг на полуокружности diameter_base/2
        # Практически мы берем N равномерных углов на окружности (0..2pi)
        angle_step = 2.0 * math.pi / float(N)

        for i in range(N + 1):
            alpha = i * angle_step
            z = finder_z(alpha, diameter_pipe, diameter_base, height_lower)
            # z может выйти за [0, height_cone] — обрежем
            z_clamped = max(0.0, min(z, height_cone))
            d_at_z = diameter_at_height(z_clamped, diameter_base, diameter_top, height_cone)
            g = generatrix_by_diameter(d_at_z, diameter_base, L_full)
            gens.append(g)

        # ---------------------------------------------------------------------
        # Получаем развертку конуса (используем at_cone_sheet как у тебя)
        # at_cone_sheet(model, input_point, diameter_base, diameter_top, height_cone, layer_name)
        # возвращает: polyline, input_point_variant, apex_variant, theta_rad
        # ---------------------------------------------------------------------
        cone_res = at_cone_sheet(model, insert_point, diameter_base, diameter_top, height_cone, layer_name="0")
        if not cone_res:
            show_popup(loc.get("build_error").format("at_cone_sheet returned None"), popup_type="error")
            return False

        cone_points_list, input_pt_variant, apex_variant, theta_rad = cone_res
        # apex_variant может быть VARIANT; предполагаем, что апекс можно взять как [x,y,z] или tuple
        # приведение к кортежу:
        try:
            # apex_variant может быть VARIANT; ensure it is sequence
            apex = tuple(apex_variant if not hasattr(apex_variant, 'value') else apex_variant.value
                         for apex_variant in (apex_variant,))  # will be tuple of one element... safer to process below
        except Exception:
            # попытка разобрать как простой список/кортеж
            if isinstance(apex_variant, (list, tuple)):
                apex = tuple(apex_variant)
            else:
                # если неожиданный формат — попытаемся взять первые 3 чисел
                try:
                    apex = (float(apex_variant[0]), float(apex_variant[1]), float(apex_variant[2]))
                except Exception:
                    apex = (0.0, 0.0, 0.0)

        # many at_cone_sheet return apex as [x,y,z] directly; handle that:
        if isinstance(apex_variant, (list, tuple)):
            apex = tuple(apex_variant)
        # if apex still wrapped (e.g. VARIANT) try to read .value
        else:
            try:
                val = getattr(apex_variant, "value", None)
                if isinstance(val, (list, tuple)):
                    apex = tuple(val)
            except Exception:
                pass

        # Ensure apex is 3-tuple
        if len(apex) == 2:
            apex = (apex[0], apex[1], 0.0)
        elif len(apex) > 3:
            apex = (float(apex[0]), float(apex[1]), float(apex[2]))

        # ---------------------------------------------------------------------
        # Строим точки полилинии на развертке
        # ---------------------------------------------------------------------
        pts_flat = build_intersection_points_on_flat(apex, theta_rad, gens)

        # Поворот: чтобы апекс оказался внизу
        rotate_angle = 90.0 - rad_to_deg(theta_rad) / 2.0
        pts_rot = rotate_points(pts_flat, rotate_angle, origin=apex)

        # Добавляем полилинию в модель
        add_polyline(model, pts_rot, layer_name=data.get("layer_name", "LASER-TEXT"), closed=False)

        # -------------------------------------------------------------------------
        #                С Л У Ж Е Б Н Ы Е   Д А Н Н Ы Е   Д Л Я   Т Е К С Т А
        # -------------------------------------------------------------------------
        # Формирование текста для меток
        k_text = f"{order_number}"
        f_text = k_text
        if detail_number:
            f_text += f"-{detail_number}"
        text_ab = TEXT_DISTANCE
        text_h = TEXT_HEIGHT_BIG
        text_s = TEXT_HEIGHT_SMALL
        text_point = polar_point(insert_point, 300, 0, as_variant=False)

        # Список текстов для добавления
        text_configs = [
            {
                "point": ensure_point_variant(insert_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 4
            },  # Гравировка
            {
                "point": ensure_point_variant(polar_point(insert_point, distance=20, alpha=-90, as_variant=False)),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": text_s,
                "text_angle": 0,
                "text_alignment": 4
            },  # Маркировка
            {
                "point": ensure_point_variant(text_point),
                "text": f"Komm.Nr. {f_text}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },  # Строка К-№
            {
                "point": ensure_point_variant(polar_point(text_point, distance=text_ab, alpha=-90, as_variant=False)),
                "text": f"D = {diameter_base} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(
                    polar_point(text_point, distance=2 * text_ab, alpha=-90, as_variant=False)),
                "text": f"d = {diameter_top} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(
                    polar_point(text_point, distance=3 * text_ab, alpha=-90, as_variant=False)),
                "text": f"H = {height_full} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(
                    polar_point(text_point, distance=4 * text_ab, alpha=-90, as_variant=False)),
                "text": f"Dicke = {thickness}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(
                    polar_point(text_point, distance=5 * text_ab, alpha=-90, as_variant=False)),
                "text": f"Wst: {material}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            }
        ]

        # Добавление текстов
        for i, config in enumerate(text_configs):
            try:
                add_text(
                    model=model,
                    point=config["point"],
                    text=config["text"],
                    layer_name=config["layer_name"],
                    text_height=config["text_height"],
                    text_angle=config["text_angle"],
                    text_alignment=config["text_alignment"]
                )
            except Exception as e:
                show_popup(
                    loc.get("text_error_details",
                            f"Ошибка добавления текста {i + 1} ({config['text']}): {str(e)}").format(i + 1,
                                                                                                     config['text'],
                                                                                                     str(e)),
                    popup_type="error"
                )
                logging.error(f"Ошибка добавления текста {i + 1}: {e}")
                return None

        regen(adoc)
        return True

    except Exception as exc:
        logging.exception("at_nozzle_cone failed")
        show_popup(loc.get("build_error").format(str(exc)), popup_type="error")
        return False


# ---------------------------------------------------------------------------
# Простой запуск для тестирования
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    insert = at_get_point(adoc, prompt=loc.get("select_point", "Укажите точку вставки"), as_variant=False)

    sample = {
        "insert_point": insert,
        "diameter_base": 138.0,
        "diameter_pipe": 273.0,
        "diameter_top": 102.0,
        "height_full": 185.78,
        "N": 360,
        "material": "1.4301",
        "thickness": 0.0,
        "order_number": "20310",
        "detail_number": "7",
        "layer_name": "LASER-TEXT"
    }
    at_nozzle_cone(sample)
