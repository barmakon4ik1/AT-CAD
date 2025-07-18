# programms/at_run_plate
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
        plate_data: Словарь с параметрами листа, включая:
            - insert_point: Точка вставки (APoint).
            - polyline_points: Список точек полилинии [(x0, y0), (x1, y0), ...].
            - material: Материал.
            - thickness_text: Толщина.
            - melt_no: Номер плавки.
            - allowance: Отступ.

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
        polyline_points = plate_data.get("polyline_points", [])
        if not polyline_points:
            show_popup(loc.get("no_input_data", "Не заданы координаты точек полилинии"), popup_type="error")
            logging.error("Не заданы точки полилинии")
            return False
        if not insert_point or not model:
            show_popup(loc.get("invalid_point", "Не указана точка вставки или модель"), popup_type="error")
            logging.error("Не указана точка вставки или модель")
            return False

        # Преобразуем точки в плоский список для add_LWpolyline
        flat_points = []
        for x, y in polyline_points:
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                show_popup(loc.get("invalid_point_format", "Неверный формат точки"), popup_type="error")
                logging.error(f"Неверный формат точки: ({x}, {y})")
                return False
            flat_points.extend([x, y])

        # Создание слоя, если не существует
        ensure_layer(adoc, "SF-TEXT")

        # Построение замкнутой полилинии
        polyline = add_LWpolyline(model, flat_points, layer_name="SF-TEXT")
        if polyline is None:
            show_popup(loc.get("polyline_creation_error", "Ошибка создания полилинии"), popup_type="error")
            logging.error("Не удалось создать полилинию")
            return False

        # Регенерация чертежа
        regen(adoc)

        logging.info("Полилиния успешно создана")
        return True

    except Exception as e:
        show_popup(loc.get("general_error", f"Ошибка: {str(e)}"), popup_type="error")
        logging.error(f"Ошибка в run_plate: {str(e)}")
        return False

