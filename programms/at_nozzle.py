"""
File: programms/at_nozzle.py
Назначение: Построение развертки патрубка
прямоугольного простого переходного тройника
с сопутствующими данными (текстами, размерами и т.п.)
"""

import math
from typing import Dict
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_text, add_polyline
from programms.at_geometry import ensure_point_variant, get_unwrapped_points, offset_point, polar_point, \
    convert_to_variant_points
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
# Регистрируем переводы при загрузке модуля
loc.register_translations(TRANSLATIONS)

def at_nozzle(data: Dict[str, any]) -> bool:
    """
    Основная функция для построения развертки патрубка отвода
    прямоугольного простого переходного тройника.

    Параметры:
        data (dict): словарь исходных данных, содержащий:
            - insert_point (list/tuple): точка вставки [x, y, z] - левый нижний угол
            - diameter_main (float): диаметр основной трубы, мм
            - diameter (float): диаметр отвода, мм
            - length (float): длина отвода от оси основной трубы, мм
            - axis (bool): рисовать ли оси на развертке
            - axis_marks (float): длина меток осей
            - layer_name (str): имя слоя для отрисовки
            - thickness (float|str): толщина отвода, мм
            - order_number (str): номер заказа, опционально, для сопроводительного текста
            - detail_number (str): номер детали, опционально, для сопроводительного текста
            - material (str): материал детали, опционально, для сопроводительного текста
            - weld_allowance (float): припуск сварки общий
            - accuracy (int): число делений длины отвода (точность), по умолчанию 180
            - offset (float): отступ оси отвода от продольной оси трубы в поперечной проекции, по умолчанию 0
            - thickness_correction (bool): корректура толщины патрубка равнопроходного отвода

    Возвращает:
        bool: True при успешном построении, иначе None.
    """
    try:
        # --- Инициализация AutoCAD ---
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        # --- Проверка входных данных ---
        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return None

        # --- Извлечение параметров ---
        insert_point = data.get("insert_point")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")
        diameter = data.get("diameter", 0.0)
        diameter_main = float(data.get("diameter_main", 0.0))
        length = data.get("length", 0.0)
        axis = data.get("axis", True)
        axis_marks = data.get("axis_marks", 0.0)
        layer_name = data.get("layer_name", "0")
        weld_allowance = data.get("weld_allowance", 0.0)
        accuracy = data.get("accuracy", 180)
        offset = data.get("offset", 0.0)
        thickness_correction =data.get("thickness_correction", False)

        # --- Проверяем точку вставки ---
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return None
        insert_point = list(map(float, insert_point[:3]))
        data["insert_point"] = insert_point  # обновляем

        # --- Расчёт габаритов ---
        length_full = length + weld_allowance
        radius = (diameter - thickness) / 2.0 if thickness > 0.0 else diameter / 2.0
        width = math.pi * diameter  # Длина развертки отвода

        # Генерация массива точек
        # создаём список делений (0, 1, 2, ..., accuracy)
        a = list(range(accuracy + 1))

        # список углов (с шагом pi/(0.5*accuracy))
        angle_list = []
        angle = 2 * math.pi
        angle_list.append(0) # добавляем нулевой угол в начало списка
        # добавляем остальные углы
        for _ in range(accuracy):
            angle -= math.pi / (0.5 * accuracy)
            angle_list.append(angle)

        # вычисляем координаты Y через синусы углов
        generatrix_length = [
            length_full - math.sqrt(
                (0.5 * diameter_main) ** 2.0 - (m * radius + offset) ** 2.0
            )
            for m in [math.sin(w) for w in angle_list]
        ]

        # формируем список точек (x, y)
        point_list = [
            (
                insert_point[0] + x * (width / accuracy),
                insert_point[1] + y
            )
            for x, y in zip(a, generatrix_length)
        ]

        # добавляем правый нижний угол
        pt2 = (insert_point[0] + width, insert_point[1])
        point_list.append(pt2)

        # добавляем исходную точку
        point_list.append((insert_point[0], insert_point[1]))

        # преобразовываем список точек в список вариантов точек
        variant_points = convert_to_variant_points(point_list)

        # создание полилинии
        nozzle_polylinie = add_polyline(model, variant_points, layer_name=layer_name)

        # очистка переменных
        a = None
        angle = None


        # --- Обновляем документ ---
        regen(adoc)
        return True


    except Exception as e:
        show_popup(
            loc.get("build_error", f"Ошибка построения: {str(e)}").format(str(e)),
            popup_type="error"
        )
    return None

if __name__ == "__main__":
    # Пример данных для тестирования
    input_data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter": 200,
        "diameter_main": 300,
        "length": 250,
        "axis": True,
        "axis_marks": 10.0,
        "layer_name": "0",
        "thickness": "0.0",
        "order_number": "K20196",
        "detail_number": "2-1",
        "material": "1.4301",
        "weld_allowance": 0.0,
        "accuracy": 180,
        "offset": 0.0,
        "thickness_correction": False
    }
    at_nozzle(input_data)

