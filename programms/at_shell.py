"""
programms/at_shell.py
Программа отрисовки развертки цилиндра с нанесением осей, текста и размеров
"""

import math
from typing import Dict

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_text
from programms.at_geometry import ensure_point_variant, get_unwrapped_points, offset_point, polar_point
from at_construction import add_rectangle, add_line, add_dimension
from windows.at_gui_utils import show_popup
from config.at_config import TEXT_HEIGHT_BIG, TEXT_HEIGHT_SMALL, TEXT_DISTANCE, DEFAULT_DIM_OFFSET

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
    "text_error_details": {
        "ru": "Ошибка добавления текста {0} ({1}): {2}",
        "de": "Fehler beim Hinzufügen von Text {0} ({1}): {2}",
        "en": "Error adding text {0} ({1}): {2}"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


def at_shell(data: Dict[str, any]) -> bool:
    """
    Функция построения развертки оболочки/цилиндра
    :return: 
    """
    try:     
        # Инициализация AutoCAD
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model
        
        # Проверка данных
        if not data:
            show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
            return None
        
        # Извлекаем данные
        required_keys = ["insert_point", "diameter", "length", "angle", "clockwise"]
        for key in required_keys:
            if key not in data or data[key] is None:
                show_popup(loc.get("no_data_error", f"Missing or None value for key: {key}"), popup_type="error")
                return None
        
        insert_point = data.get("insert_point")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")       
        diameter = data.get("diameter", 0.0)
        length = data.get("length", 0.0)
        a_deg = data.get("angle", 0.0)
        clockwise = data.get("clockwise", False)
        layer_name = data.get("layer_name", "0")
        weld_allowance_top = data.get("weld_allowance_top", False)
        weld_allowance_bottom = data.get("weld_allowance_bottom", False)

        # Проверяем insert_point
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"), popup_type="error")
            return None
        insert_point = list(map(float, insert_point[:3]))  # Берём [x, y, z]
        data["insert_point"] = insert_point  # Обновляем в data
        
        width = math.pi * diameter
       
        # Нарисовать прямоугольник развертки
        add_rectangle(model, insert_point, width, length, layer_name=layer_name)
    
        # Получить точки для углов на развертке цилиндра
        points = get_unwrapped_points(D=diameter, L=length, A_deg=a_deg, clockwise=clockwise)
    
        # Точки для размерных линий
        end_point = offset_point(insert_point, width, length)
        top_point = offset_point(insert_point, 0, length)
        left_bottom = ensure_point_variant(insert_point)

        # Размеры
        add_dimension(adoc, "H", top_point, end_point, offset=DEFAULT_DIM_OFFSET * 2)
        add_dimension(adoc, "V", left_bottom, top_point, offset=DEFAULT_DIM_OFFSET)

        drawn_x = set()  # будем помнить, какие линии уже проведены
        # Отрисовка осей
        for angle, x, y in points:
            # пропускаем 360°, чтобы не дублировать 0°
            if angle == 360:
                continue
    
            base_x = insert_point[0] + x
            base_y = insert_point[1] + y
    
            # если по этому X линия уже нарисована – пропускаем
            if round(base_x, 6) in drawn_x:
                continue
            drawn_x.add(round(base_x, 6))
    
            point1 = [base_x, base_y]
            point2 = [base_x, base_y + length]
            point_text = [base_x, base_y - 60]
            point_text2 = [base_x + width, base_y - 60]

            # Форматируем угол: если целое — без дробной части, иначе с одной
            angle_text = f"{int(angle)}°" if angle.is_integer() else f"{angle:.1f}°"
    
            if angle == a_deg:
                # правая граница: только подпись (слева и справа)
                add_text(model, point_text, angle_text, layer_name="AM_5")
                add_text(model, point_text2, angle_text, layer_name="AM_5")
    
            else:
                # остальные углы: линия + подпись
                add_line(model, point1, point2, layer_name="AM_5")
                add_text(model, point_text, angle_text, layer_name="AM_5")
    
            # print(f"Угол: {angle:.1f}°, X: {base_x:>7.2f}, Y: {base_y}")

        # Формирование текста для меток
        k_text = f"{order_number}"
        f_text = k_text
        if detail_number:
            f_text += f"-{detail_number}"
        text_ab = TEXT_DISTANCE
        text_h = TEXT_HEIGHT_BIG
        text_s = TEXT_HEIGHT_SMALL
        text_point = polar_point(insert_point, 100, 45, as_variant=False)

        # Список текстов для добавления
        text_configs = [
            {
                "point": ensure_point_variant(text_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 12
            },  # Гравировка
            {
                "point": ensure_point_variant(polar_point(text_point, distance=60, alpha=90, as_variant=False)),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": text_s,
                "text_angle": 0,
                "text_alignment": 12
            }  # Маркировка
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
                    loc.get("text_error_details", f"Ошибка добавления текста {i + 1} ({config['text']}): {str(e)}").format(i + 1, config['text'], str(e)),
                    popup_type="error"
                )
                return None
    
        regen(adoc)
        return True
    except Exception as e:
        show_popup(loc.get("build_error", f"Ошибка построения: {str(e)}").format(str(e)), popup_type="error")
        return None


if __name__ == "__main__":
    input_data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter": 500,
        "length": 1000,
        "angle": 30,
        "clockwise": False,
        "layer_name": "0",
        "thickness": "4.0",
        "order_number": "12345",
        "detail_number": "1",
        "weld_allowance_top": 1.0,
        "weld_allowance_bottom": 1.0
    }
    at_shell(input_data)
