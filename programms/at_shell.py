"""
programms/at_shell.py
Программа отрисовки развертки цилиндра с нанесением осей, текста и размеров
"""

import math
from typing import Dict

from django.template.defaultfilters import length

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
        axis = data.get("axis", True)
        axis_marks = data.get("axis_marks", 0.0)
        layer_name = data.get("layer_name", "0")
        weld_allowance_top = data.get("weld_allowance_top", 0.0)
        weld_allowance_bottom = data.get("weld_allowance_bottom", 0.0)

        # Проверяем insert_point
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"), popup_type="error")
            return None
        insert_point = list(map(float, insert_point[:3]))  # Берём [x, y, z]
        data["insert_point"] = insert_point  # Обновляем в data
        
        width = math.pi * diameter
        length_full = length + weld_allowance_top + weld_allowance_bottom
       
        # Нарисовать прямоугольник развертки
        add_rectangle(model, insert_point, width, length_full, layer_name=layer_name)

        # Точки для размерных линий
        rect_top_right = offset_point(insert_point, width, length_full)
        rect_top_left = offset_point(insert_point, 0, length_full)
        rect_bottom_left = ensure_point_variant(insert_point)

        # Размеры габаритные
        add_dimension(adoc, "H", rect_top_left, rect_top_right, offset=DEFAULT_DIM_OFFSET * 2 + 20)
        add_dimension(adoc, "V", rect_bottom_left, rect_top_left, offset=DEFAULT_DIM_OFFSET)

        if axis:
            drawn_x = set()  # будем помнить, какие линии уже проведены

            # Получить точки для углов осей на развертке цилиндра
            points = get_unwrapped_points(D=diameter, L=length, A_deg=a_deg, clockwise=clockwise)

            # Массив для верхних точек осей (для размеров типа H)
            top_axis_points = []

            # заранее вычисляем X-координаты краёв рамки
            rect_top_left_v = ensure_point_variant(rect_top_left)
            rect_top_right_v = ensure_point_variant(rect_top_right)
            left_edge_x = float(rect_top_left_v.value[0])
            right_edge_x = float(rect_top_right_v.value[0])
            edge_tol = 1e-6

            # Отрисовка осей и меток в одном цикле
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
                point2 = [base_x, base_y + length_full]
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

                    # собираем верхние точки для размеров
                    top_axis_points.append(point2)

                # --- Метки (только если задано axis_marks и это не граница прямоугольника) ---
                if axis_marks > 0 and not (
                        math.isclose(base_x, left_edge_x, abs_tol=edge_tol) or
                        math.isclose(base_x, right_edge_x, abs_tol=edge_tol)
                ):
                    # снизу
                    add_line(model, [base_x, base_y], [base_x, base_y + axis_marks], layer_name="LASER-TEXT")
                    # сверху
                    top_y = base_y + length_full
                    add_line(model, [base_x, top_y], [base_x, top_y - axis_marks], layer_name="LASER-TEXT")

            # --- Теперь проставляем размеры H между верхними точками осей ---
            if len(top_axis_points) >= 1:
                top_axis_points.sort(key=lambda p: p[0])

                # --- крайний размер: от левого угла прямоугольника до первой оси ---
                left_top_corner = ensure_point_variant(rect_top_left)
                first_axis = ensure_point_variant(top_axis_points[0])
                add_dimension(adoc, "H", left_top_corner, first_axis, offset=DEFAULT_DIM_OFFSET)

                # --- промежуточные размеры ---
                for i in range(len(top_axis_points) - 1):
                    p1 = ensure_point_variant(top_axis_points[i])
                    p2 = ensure_point_variant(top_axis_points[i + 1])
                    add_dimension(adoc, "H", p1, p2, offset=DEFAULT_DIM_OFFSET)

                # --- крайний размер: от последней оси до правого угла прямоугольника ---
                right_top_corner = ensure_point_variant(rect_top_right)
                last_axis = ensure_point_variant(top_axis_points[-1])
                add_dimension(adoc, "H", last_axis, right_top_corner, offset=DEFAULT_DIM_OFFSET)

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
        "insert_point": [-2000.0, 0.0, 0.0],
        "diameter": 846,
        "length": 900,
        "angle": 270,
        "clockwise": True,
        "axis": True,
        "axis_marks": 10.0,
        "layer_name": "0",
        "thickness": "4.0",
        "order_number": "K20196",
        "detail_number": "2-1",
        "weld_allowance_top": 0.0,
        "weld_allowance_bottom": 0.0
    }
    at_shell(input_data)
