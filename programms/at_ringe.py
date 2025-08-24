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
from programms.at_construction import add_circle, add_text
from programms.at_base import layer_context, regen
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
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

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
    except:
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

            # Добавление текста с использованием add_text
            add_text(model, p1, text=work_number, layer_name="LASER-TEXT", text_height=7)
            add_text(model, p2, text=work_number, layer_name="schrift", text_height=30)
        except:
            return None

    # Обновляем вид
    regen(adoc)
    return True  # Успешное выполнение


if __name__ == "__main__":
    """
    Точка входа в приложение. Для тестирования напрямую (не рекомендуется).
    """
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
        print(f"Ошибка в главном цикле: {e}")
    finally:
        try:
            pythoncom.CoUninitialize()  # Освобождение COM в конце
        except Exception as e:
            show_popup(loc.get("com_release_error", str(e)), popup_type="error")

