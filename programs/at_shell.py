"""
File: programs/at_shell.py
Назначение: Построение развертки цилиндра (оболочки)
с нанесением осей, текстов и размеров в AutoCAD
"""

# ============================================================
# Пример схемы развертки цилиндра (вид сверху):
#
#   ^ длина (L)
#   |
#   |
#   +------------------------------------------+
#   |                                          |
#   |   |      |      |      |      |      |   |  <- оси (углы)
#   |                                          |
#   +------------------------------------------+  -> ширина = π*D
#
#   * Сверху и снизу могут быть припуски на сварку
#   * Вдоль ширины ставятся подписи углов (0°, 45°, 90° ... A°)
#   * Добавляются габаритные размеры H (по горизонтали) и V (по вертикали)
#   * Снизу выводятся гравировка (LASER-TEXT) и маркировка (schrift)
#
# ============================================================


import math
from typing import Dict
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_construction import add_text
from programs.at_geometry import ensure_point_variant, get_unwrapped_points, offset_point, polar_point
from programs.at_construction import add_rectangle, add_line, add_dimension
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
# Регистрируем переводы при загрузке модуля
loc.register_translations(TRANSLATIONS)

def main(data):
    return at_shell(data)

def at_shell(data: Dict[str, any]) -> bool:
    """
    Основная функция для построения развертки цилиндра (оболочки).

    Параметры:
        data (dict): словарь исходных данных, содержащий:
            - insert_point (list/tuple): точка вставки [x, y, z]
            - diameter (float): диаметр цилиндра
            - length (float): длина цилиндра
            - angle (float): угол развертки в градусах
            - clockwise (bool): направление развертки
            - axis (bool): рисовать ли оси
            - axis_marks (float): длина меток осей
            - layer_name (str): имя слоя для отрисовки
            - thickness (float|str): толщина детали
            - order_number (str): номер заказа
            - detail_number (str): номер детали
            - weld_allowance_top (float): припуск сварки сверху
            - weld_allowance_bottom (float): припуск сварки снизу

    Возвращает:
        bool: True при успешном построении, иначе None.
    """
    try:
        # --- Инициализация AutoCAD ---
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        # --- Проверка входных данных ---
        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return None

        # Проверяем наличие обязательных ключей
        required_keys = ["insert_point", "diameter", "length", "angle", "clockwise"]
        for key in required_keys:
            if key not in data or data[key] is None:
                show_popup(
                    loc.get("no_data_error", f"Missing or None value for key: {key}"),
                    popup_type="error"
                )
                return None

        # --- Извлечение параметров ---
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

        # --- Проверяем точку вставки ---
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return None
        insert_point = list(map(float, insert_point[:3]))
        data["insert_point"] = insert_point  # обновляем

        # --- Расчёт габаритов ---
        width = math.pi * diameter  # длина окружности
        length_full = length + weld_allowance_top + weld_allowance_bottom

        # --- Построение прямоугольника развертки ---
        add_rectangle(model, insert_point, width, length_full, layer_name=layer_name)

        # --- Точки для размеров ---
        rect_top_right = offset_point(insert_point, width, length_full)
        rect_top_left = offset_point(insert_point, 0, length_full)
        rect_bottom_left = ensure_point_variant(insert_point)

        # --- Габаритные размеры ---
        add_dimension(adoc, "H", rect_top_left, rect_top_right, offset=DEFAULT_DIM_OFFSET * 2 + 20)
        add_dimension(adoc, "V", rect_bottom_left, rect_top_left, offset=DEFAULT_DIM_OFFSET)

        # --- Отрисовка осей ---
        if axis:
            drawn_x = set()
            points = get_unwrapped_points(D=diameter, L=length, A_deg=a_deg, clockwise=clockwise)
            top_axis_points = []

            # координаты краёв рамки
            left_edge_x = float(ensure_point_variant(rect_top_left).value[0])
            right_edge_x = float(ensure_point_variant(rect_top_right).value[0])
            edge_tol = 1e-6

            for angle, x, y in points:
                if angle == 360:
                    continue  # избегаем дублирования 0°

                base_x = insert_point[0] + x
                base_y = insert_point[1] + y

                # если по этому X линия уже нарисована
                if round(base_x, 6) in drawn_x:
                    continue
                drawn_x.add(round(base_x, 6))

                point1 = [base_x, base_y]
                point2 = [base_x, base_y + length_full]
                point_text = [base_x, base_y - 60]
                point_text2 = [base_x + width, base_y - 60]

                # текст угла
                angle_text = f"{int(angle)}°" if angle.is_integer() else f"{angle:.1f}°"

                if angle == a_deg:
                    # правая граница
                    add_text(model, point_text, angle_text, layer_name="AM_5")
                    add_text(model, point_text2, angle_text, layer_name="AM_5")
                else:
                    # ось
                    add_line(model, point1, point2, layer_name="AM_5")
                    add_text(model, point_text, angle_text, layer_name="AM_5")
                    top_axis_points.append(point2)

                # --- Метки на оси ---
                if axis_marks > 0 and not (
                        math.isclose(base_x, left_edge_x, abs_tol=edge_tol) or
                        math.isclose(base_x, right_edge_x, abs_tol=edge_tol)
                ):
                    # снизу
                    add_line(model, [base_x, base_y], [base_x, base_y + axis_marks], layer_name="LASER-TEXT")
                    # сверху
                    top_y = base_y + length_full
                    add_line(model, [base_x, top_y], [base_x, top_y - axis_marks], layer_name="LASER-TEXT")

            # --- Размеры между осями ---
            if len(top_axis_points) >= 1:
                top_axis_points.sort(key=lambda p: p[0])

                # от левого края до первой оси
                add_dimension(adoc, "H", ensure_point_variant(rect_top_left),
                              ensure_point_variant(top_axis_points[0]), offset=DEFAULT_DIM_OFFSET)

                # промежуточные
                for i in range(len(top_axis_points) - 1):
                    add_dimension(adoc, "H",
                                  ensure_point_variant(top_axis_points[i]),
                                  ensure_point_variant(top_axis_points[i + 1]),
                                  offset=DEFAULT_DIM_OFFSET)

                # от последней оси до правого края
                add_dimension(adoc, "H", ensure_point_variant(top_axis_points[-1]),
                              ensure_point_variant(rect_top_right), offset=DEFAULT_DIM_OFFSET)

        # --- Формирование текста ---
        k_text = f"{order_number}"
        f_text = k_text if not detail_number else f"{k_text}-{detail_number}"

        text_point = polar_point(insert_point, 20, 45, as_variant=False)

        text_configs = [
            # Гравировка
            {
                "point": ensure_point_variant(text_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 12
            },
            # Маркировка
            {
                "point": ensure_point_variant(polar_point(text_point, distance=30, alpha=90, as_variant=False)),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": TEXT_HEIGHT_SMALL,
                "text_angle": 0,
                "text_alignment": 12
            }
        ]

        # --- Добавление текстов ---
        for i, config in enumerate(text_configs):
            try:
                add_text(model, **config)
            except Exception as e:
                show_popup(
                    loc.get(
                        "text_error_details",
                        f"Ошибка добавления текста {i + 1} ({config['text']}): {str(e)}"
                    ).format(i + 1, config['text'], str(e)),
                    popup_type="error"
                )
                return None

        # --- Обновляем документ ---
        regen(adoc)
        return {
            "success": True,
            "outline": [
                [insert_point[0], insert_point[1]],
                [insert_point[0] + width, insert_point[1]],
                [insert_point[0] + width, insert_point[1] + length_full],
                [insert_point[0], insert_point[1] + length_full],
                [insert_point[0], insert_point[1]],
            ],
            "metadata": {
                "insert_point": insert_point,
                "diameter": diameter,
                "length": length,
                "width": width,                  # развернутая окружность (π·D)
                "height": length_full,           # с учётом припусков
                "angle_ref": a_deg,              # угол разреза (где нулевая точка развёртки)
                "unroll_dir": "CW" if clockwise else "CCW",  # направление развёртки
                "weld_allowance_top": weld_allowance_top,
                "weld_allowance_bottom": weld_allowance_bottom,
                "order_number": order_number,
                "detail_number": detail_number,
                "material": material,
                "thickness": thickness
            }
        }


    except Exception as e:
        show_popup(
            loc.get("build_error", f"Ошибка построения: {str(e)}").format(str(e)),
            popup_type="error"
        )
        return None


if __name__ == "__main__":
    # Пример данных для тестирования
    input_data = {
        "insert_point": [-3000.0, 0.0, 0.0],
        "diameter": 790,
        "length": 1700,
        "angle": 340,
        "clockwise": True,
        "axis": True,
        "axis_marks": 0.0,
        "layer_name": "0",
        "thickness": "10.0",
        "order_number": "K20202",
        "detail_number": "1",
        "weld_allowance_top": 0.0,
        "weld_allowance_bottom": 0.0
    }
    at_shell(input_data)
