import logging
import pythoncom
from pyautocad import APoint
from programms.at_construction import add_LWpolyline
from typing import Dict, Any, List
from locales.at_localization_class import loc
from config.at_config import LANGUAGE
from windows.at_gui_utils import show_popup
from programms.at_base import ensure_layer, regen, init_autocad

loc.language = LANGUAGE

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def run_plate(plate_data: Dict[str, Any]) -> bool:
    """
    Выполняет построение листа для лазерной резки на основе предоставленных данных.

    Args:
        plate_data: Словарь с параметрами листа (insert_point, point_list, material, thickness_text, melt_no, allowance).

    Returns:
        bool: True если выполнено успешно, False если ошибка.
    """
    try:
        # Инициализация AutoCAD
        cad_objects = init_autocad()
        if cad_objects is None:
            show_popup(loc.get("cad_init_error_short", "Ошибка инициализации AutoCAD"), popup_type="error")
            logging.error("Не удалось инициализировать AutoCAD")
            return False
        adoc, model, original_layer = cad_objects

        # Проверка данных
        if not plate_data:
            show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
            logging.error("Данные не предоставлены")
            return False

        # Извлекаем данные
        insert_point = plate_data.get("insert_point")
        point_list = plate_data.get("point_list", [])
        if not point_list:
            show_popup(loc.get("no_input_data"), popup_type="error")
            logging.error("Не заданы координаты точек")
            return False
        if not insert_point or not model:
            show_popup(loc.get("invalid_point"), popup_type="error")
            logging.error("Не указана точка вставки или модель")
            return False

        # Точки для полилинии
        x0, y0 = insert_point[0], insert_point[1]

        # Подготовка списка точек для полилинии с учетом точки вставки
        polyline_points = []
        for point in point_list:
            if len(point) != 2:
                show_popup(loc.get("invalid_point_format", "Неверный формат точки"), popup_type="error")
                logging.error(f"Неверный формат точки: {point}")
                return False
            # Смещаем точки относительно точки вставки
            polyline_points.extend([x0 + point[0], y0 + point[1]])

        # Создание слоя, если не существует
        ensure_layer(adoc, "SF-TEXT")

        # Построение замкнутой полилинии
        polyline = add_LWpolyline(model, polyline_points, layer_name="SF-TEXT")
        if polyline is None:
            show_popup(loc.get("polyline_creation_error", "Ошибка создания полилинии"), popup_type="error")
            logging.error("Не удалось создать полилинию")
            return False

        # Регенерация чертежа
        regen(model)

        logging.info("Полилиния успешно создана")
        return True

    except Exception as e:
        show_popup(loc.get("general_error", f"Ошибка: {str(e)}"), popup_type="error")
        logging.error(f"Ошибка в run_plate: {str(e)}")
        return False


if __name__ == "__main__":
    # Тестовые данные
    test_plate_data = {
        "insert_point": [0, 0],  # Точка вставки (x0, y0)
        "point_list": [
            [0, 0],    # Точка 1
            [3000, 0],   # Точка 2
            [3000, 500],  # Точка 3
            [1500, 500],    # Точка 4
            [1500, 1500],    # Точка 5
            [0, 1500]    # Точка 6
        ],
        "material": "1.4571",
        "thickness_text": "3 mm",
        "melt_no": "12345",
        "allowance": 10
    }

    # Запуск функции с тестовыми данными
    result = run_plate(test_plate_data)
    if result:
        print("Тестовый запуск успешен: полилиния создана")
    else:
        print("Тестовый запуск не удался: проверьте лог at_cad.log")