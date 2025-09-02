# programms/at_run_plate.py
"""
Модуль для построения листа для лазерной резки в AutoCAD с использованием Win32com (COM).

"""
from typing import Dict, Optional, List

import win32com
from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, TEXT_HEIGHT_BIG, DEFAULT_DIM_OFFSET
from locales.at_translations import loc
from programms.at_calculation import at_density, at_plate_weight
from programms.at_construction import add_circle, add_text, add_polyline
from programms.at_base import layer_context, regen
from programms.at_dimension import add_dimension
from programms.at_geometry import ensure_point_variant, polar_point, offset_point, build_polyline_list, \
    convert_to_variant_points
from programms.at_offset import at_offset
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "to_small_points": {
        "ru": "Мало точек",
        "de": "Zu wenig Punkten",
        "en": "To small points"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

from typing import Dict, List, Optional
from windows.at_window_utils import show_popup
from locales.at_translations import loc



def main(plate_data: dict = None) -> bool:
    """
    Основная функция для построения листа для лазерной резки в AutoCAD.

    Args:
        plate_data: Словарь с данными листа, полученными из окна

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    # Инициализация AutoCAD
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    # Проверка данных
    if not plate_data:
        show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
        return None

    # Извлекаем данные
    insert_point = plate_data.get("insert_point")
    material = plate_data.get("material", "")
    thickness = float(plate_data.get("thickness", 0.0))
    melt_no = plate_data.get("melt_no", "")
    allowance = plate_data.get("allowance")
    point_list = plate_data.get("point_list")
    l, h = point_list[0][0], point_list[0][1]

    # Проверяем insert_point
    if not isinstance(insert_point, (list, tuple)) or len(insert_point) < 2:
        show_popup(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"), popup_type="error")
        return None
    insert_point = list(map(float, insert_point[:2]))  # Берём только [x, y]
    plate_data["insert_point"] = insert_point  # Обновляем в plate_data

    polyline_list = build_polyline_list(plate_data)
    variant_points = convert_to_variant_points(polyline_list)

    # --- внешняя полилиния ---
    poly = add_polyline(model, variant_points, layer_name="SF-TEXT", closed=True)

    # Вызов функции at_offset
    at_offset(poly, allowance, adoc, model)

    # --- площадь для массы ---
    area = float(poly.Area)

    # --- свойства материала ---
    density = at_density(material)
    weight = at_plate_weight(thickness, density, area)

    # -----------------------------
    # Простановка размеров
    # -----------------------------
    # Базовые точки для размеров
    p1 = ensure_point_variant(polyline_list[1])
    p0 = ensure_point_variant(polyline_list[0])
    p2 = ensure_point_variant(polyline_list[2])

    # Простановка начальных размеров
    add_dimension(adoc, "H", p1, p0, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "V", p2, p1, offset=DEFAULT_DIM_OFFSET)

    default_offset = 60 # Базовое смещение для размеров

    # text_offset = 60
    # if len(polyline_list) > 2:
    #     offset = DEFAULT_DIM_OFFSET
    #     text_offset += offset
    #     p3 = ensure_point_variant(polyline_list[3])
    #     add_dimension(adoc, "H", p3, p2, offset=offset)
    #     if len(polyline_list) > 4:
    #         offset = 2 * DEFAULT_DIM_OFFSET
    #         text_offset += offset
    #         p5 = ensure_point_variant(polyline_list[5])
    #         add_dimension(adoc, "H", p5, p2, offset=offset)
    #         if len(polyline_list) > 6:
    #             offset = 3 * DEFAULT_DIM_OFFSET
    #             text_offset += offset
    #             p7 = ensure_point_variant(polyline_list[7])
    #             add_dimension(adoc, "H", p7, p2, offset=offset)
    #             if len(polyline_list) > 8:
    #                 offset = 4 * DEFAULT_DIM_OFFSET
    #                 text_offset += offset
    #                 p9 = ensure_point_variant(polyline_list[9])
    #                 add_dimension(adoc, "H", p9, p2, offset=offset)
    #
    # offset = DEFAULT_DIM_OFFSET
    # if len(polyline_list) > 10:
    #     p11 = ensure_point_variant(polyline_list[11])
    #     add_dimension(adoc, "V", p0, p11, offset=offset)
    #     offset += DEFAULT_DIM_OFFSET
    #
    # if len(polyline_list) > 8:
    #     p9 = ensure_point_variant(polyline_list[9])
    #     add_dimension(adoc, "V", p0, p9, offset=offset)
    #     offset += DEFAULT_DIM_OFFSET
    #
    # if len(polyline_list) > 6:
    #     p7 = ensure_point_variant(polyline_list[7])
    #     add_dimension(adoc, "V", p0, p7, offset=offset)
    #     offset += DEFAULT_DIM_OFFSET
    #
    # if len(polyline_list) > 4:
    #     p5 = ensure_point_variant(polyline_list[5])
    #     add_dimension(adoc, "V", p0, p5, offset=offset)


    # текст h + 60 мм

    # Список индексов для горизонтальных размеров (p3, p5, p7, p9)
    h_indices = [4, 6, 8, 10]
    offset = default_offset
    text_offset = default_offset + 60

    # Горизонтальные размеры
    for idx in h_indices:
        if len(polyline_list) > idx:
            offset += default_offset
            text_offset += default_offset
            p_idx = ensure_point_variant(polyline_list[idx])
            add_dimension(adoc, "H", p_idx, p2, offset=offset)

    # Список индексов для вертикальных размеров (p5, p7, p9, p11) в обратном порядке
    v_indices = [11, 9, 7, 5]
    offset = default_offset

    # Вертикальные размеры
    for idx in v_indices:
        if len(polyline_list) > idx:
            p_idx = ensure_point_variant(polyline_list[idx])
            add_dimension(adoc, "V", p0, p_idx, offset=offset)
            offset += default_offset

    text_point = polar_point(insert_point, h + text_offset, 90, as_variant=False)
    text_str = f"{thickness:g} mm {material}, {weight:g} kg, Ch. {melt_no}"
    add_text(model, point=text_point, text=text_str, layer_name="AM_5",
             text_height=TEXT_HEIGHT_BIG, text_angle=0, text_alignment=0)

    regen(adoc)
    return True


if __name__ == '__main__':
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    input_data = {
        'insert_point': [0.0, 0.0, 0.0],  # Формат [x, y, 0]
        'point_list': [
            [3000.0, 1500.0],
            [1000.0, 1250.0],
            [1500.0, 1000.0],
            [2000.0, 750.0],
            [2500.0, 500.0]
        ],
        'material': '1.4301',
        'thickness': 4.0,
        'melt_no': '123654',
        'allowance': 10.0
    }

    main(input_data)