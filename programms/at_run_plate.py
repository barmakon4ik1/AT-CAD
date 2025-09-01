# programms/at_run_plate.py
"""
Модуль для построения листа для лазерной резки в AutoCAD с использованием Win32com (COM).

"""
from typing import Dict, Optional, List

import win32com
from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, TEXT_HEIGHT_BIG
from locales.at_translations import loc
from programms.at_calculation import at_density, at_plate_weight
from programms.at_construction import add_circle, add_text, add_polyline
from programms.at_base import layer_context, regen
from programms.at_geometry import ensure_point_variant, polar_point, offset_point
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

def build_polyline_list(plate_data: Dict) -> Optional[List]:
    """
    Создаёт список точек для полилинии на основе данных листа.

    Args:
        plate_data: Словарь с данными (insert_point, point_list, material, thickness, melt_no, allowance).

    Returns:
        List: Список точек для полилинии или None при ошибке.
    """
    try:
        # Инициализация списка полилинии
        # список для полилинии
        polyline_list = []  # Извлекаем данные
        insert_point = plate_data.get("insert_point")

        point_list = plate_data.get("point_list")
        l, h = point_list[0][0], point_list[0][1]
        p0x, p0y = insert_point[0], insert_point[1]
        p0 = [p0x, p0y]
        polyline_list.append(p0)
        if len(point_list) > 0:
            p1 = offset_point(p0, l, 0, as_variant=False)
            p2 = polar_point(p1, h, 90, as_variant=False)
            polyline_list.append(p1)
            polyline_list.append(p2)
            if len(point_list) > 1:
                l1, h1 = point_list[1][0], point_list[1][1]
                p3 = offset_point(p0, l - l1, h, as_variant=False)
                p4 = offset_point(p0, l - l1, h1, as_variant=False)
                polyline_list.append(p3)
                polyline_list.append(p4)
                if len(point_list) > 2:
                    l2, h2 = point_list[2][0], point_list[2][1]
                    p5 = offset_point(p0, l - l2, h1, as_variant=False)
                    p6 = offset_point(p0, l - l2, h2, as_variant=False)
                    polyline_list.append(p5)
                    polyline_list.append(p6)
                    if len(point_list) > 3:
                        l3, h3 = point_list[3][0], point_list[3][1]
                        p7 = offset_point(p0, l - l3, h2, as_variant=False)
                        p8 = offset_point(p0, l - l3, h3, as_variant=False)
                        polyline_list.append(p7)
                        polyline_list.append(p8)
                        if len(point_list) > 4:
                            l4, h4 = point_list[4][0], point_list[4][1]
                            p9 = offset_point(p0, l - l4, h3, as_variant=False)
                            p10 = offset_point(p0, l - l4, h4, as_variant=False)
                            p11 = polar_point(p0, h4, 90, as_variant=False)
                            polyline_list.append(p9)
                            polyline_list.append(p10)
                            polyline_list.append(p11)
                        else:
                            p9 = polar_point(p0, h3, 90, as_variant=False)
                            polyline_list.append(p9)
                    else:
                        p7 = polar_point(p0, h2, 90, as_variant=False)
                        polyline_list.append(p7)
                else:
                    p5 = polar_point(p0, h1, 90, as_variant=False)
                    polyline_list.append(p5)
            else:
                p3 = polar_point(p0, h, 90, as_variant=False)
                polyline_list.append(p3)
        else:
            show_popup(loc.get("to_small_points", "Мало точек"), popup_type="error")
            return None
        return polyline_list
    except Exception as e:
        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        return None

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

    polyline_list = build_polyline_list(plate_data)

    # --- внешняя полилиния ---
    poly = add_polyline(model, polyline_list, layer_name="SF-TEXT", closed=True)

    # Вызов функции at_offset
    at_offset(poly, allowance, adoc, model)

    # --- площадь для массы ---
    area = float(poly.Area)

    # --- свойства материала ---

    density = at_density(material)
    weight = at_plate_weight(thickness, density, area)

    # текст h + 60 мм
    text_point = polar_point(insert_point, h + 60, 90)
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
        'insert_point': [0, 0],
        'point_list': [
            [3000.0, 1500.0],
            # [1000, 1250.0],
            # [1500, 1000.0],
            [2000, 750.0],
            [2500, 500.0]
        ],
        'material': '1.4301',
        'thickness': 4.0,
        'melt_no': '123654',
        'allowance': 10.0
    }

    main(input_data)
