# programms/at_ringe.py
"""
Модуль для построения колец в AutoCAD на основе данных из диалогового окна.

Создаёт окружности с заданными диаметрами и добавляет текстовые метки с номером работы.
"""

import pythoncom
import logging
from pyautocad import APoint
from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, DEFAULT_TEXT_LAYER
from locales.at_localization_class import loc
from programms.at_construction import add_circle
from programms.at_text_input import ATTextInput
from programms.at_base import layer_context, init_autocad, regen
from windows.at_gui_utils import show_popup

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main(ring_data: dict = None) -> bool:
    """
    Основная функция для построения колец в AutoCAD.

    Args:
        ring_data: Словарь с данными колец (work_number, diameters, insert_point, model).

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    logging.debug("Запуск функции main в at_ringe")
    # Инициализация AutoCAD
    cad_objects = init_autocad()
    if cad_objects is None:
        show_popup(loc.get("cad_init_error_short", "Ошибка инициализации AutoCAD"), popup_type="error")
        logging.error("Не удалось инициализировать AutoCAD")
        return None
    adoc, model, original_layer = cad_objects

    # Проверка данных
    if not ring_data:
        show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
        logging.error("Данные не предоставлены")
        return None

    # Извлекаем данные
    work_number = ring_data.get("work_number", "")
    diameters = ring_data.get("diameters", {})
    center = ring_data.get("insert_point")
    if not diameters:
        show_popup(loc.get("no_diameters"), popup_type="error")
        logging.error("Не указаны диаметры")
        return None
    if not center or not model:
        show_popup(loc.get("no_center"), popup_type="error")
        logging.error("Не указана центральная точка или модель")
        return None

    # Построение окружностей
    try:
        with layer_context(adoc, DEFAULT_CIRCLE_LAYER):
            for diameter_value in diameters.values():
                add_circle(model, APoint(center[0], center[1]), diameter_value / 2.0, DEFAULT_CIRCLE_LAYER)
                logging.info(f"Построена окружность с диаметром {diameter_value} мм")
    except Exception as e:
        show_popup(loc.get("circle_error"), popup_type="error")
        logging.error(f"Ошибка построения окружностей: {e}")
        return None

    # Добавление текста
    if work_number:  # Добавляем текст только если work_number не пустой
        try:
            # Вычисление позиций текста на основе диаметров
            sorted_radii = sorted([d / 2.0 for d in diameters.values()], reverse=True)
            max_radius = sorted_radii[0]
            second_radius = sorted_radii[1] if len(sorted_radii) > 1 else 0
            y_offset = max_radius - (max_radius - second_radius) * 0.5
            p1 = APoint(center[0], center[1] + y_offset)
            p2 = APoint(center[0], center[1] - y_offset)

            # Добавление текста с использованием ATTextInput
            text1 = ATTextInput(p1, work_number, "LASER-TEXT", 7)
            text2 = ATTextInput(p2, work_number, "schrift", 30)
            if not text1.at_text_input() or not text2.at_text_input():
                show_popup(loc.get("text_error"), popup_type="error")
                logging.error("Ошибка добавления текста")
                return None
            logging.info(f"Текст '{work_number}' добавлен на слои 'LASER-TEXT' и 'schrift'")
        except Exception as e:
            show_popup(loc.get("text_error"), popup_type="error")
            logging.error(f"Ошибка добавления текста: {e}")
            return None

    # Обновляем вид
    try:
        regen(adoc)
        logging.info("Вид успешно обновлён")
    except Exception as e:
        show_popup(loc.get("regen_error"), popup_type="error")
        logging.error(f"Ошибка обновления вида: {e}")
        return None

    return True  # Успешное выполнение


if __name__ == "__main__":
    """
    Точка входа в приложение. Для тестирования напрямую (не рекомендуется).
    """
    logging.debug("Запуск at_ringe как основного модуля")
    try:
        pythoncom.CoInitialize()  # Инициализация COM один раз
        # Для тестирования можно передать тестовые данные
        test_data = {
            "work_number": "TEST123",
            "diameters": {"1": 100, "2": 200},
            "insert_point": (0, 0),
            "model": None  # Требуется инициализация AutoCAD
        }
        main(test_data)
    except Exception as e:
        show_popup(loc.get("error_in_main", str(e)), popup_type="error")
        logging.error(f"Ошибка в главном цикле: {e}")
    finally:
        try:
            pythoncom.CoUninitialize()  # Освобождение COM в конце
            logging.debug("COM успешно освобождён")
        except Exception as e:
            show_popup(loc.get("com_release_error", str(e)), popup_type="error")
            logging.error(f"Ошибка освобождения COM: {e}")
