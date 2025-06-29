"""
Модуль для построения колец в AutoCAD на основе данных из диалогового окна.

Создаёт окружности с заданными диаметрами и добавляет текстовые метки с номером работы.
"""

import pythoncom

from at_text_input import ATTextInput
import at_ringe_window
from at_gui_utils import show_popup
import at_utils as utils
from at_config import DEFAULT_CIRCLE_LAYER
from at_localization import loc
from pyautocad import APoint
from at_construction import add_circle


def main():
    """
    Основная функция для построения колец в AutoCAD.

    Получает данные из диалогового окна, создаёт окружности и добавляет текстовые метки.

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    # Инициализация AutoCAD (на случай, если окно не инициализировало)
    cad_objects = utils.init_autocad()
    if cad_objects is None:
        show_popup(loc.get("cad_init_error_short"), popup_type="error")
        return None
    adoc, _, original_layer = cad_objects

    # Получаем данные из окна
    ring_data = at_ringe_window.create_window()
    if ring_data is None:
        return None # Тихое завершение при отмене

    # Извлекаем данные
    work_number = ring_data.get("work_number", "")
    diameters = ring_data.get("diameters", {})
    center = ring_data.get("insert_point")
    model = ring_data.get("model")
    if not diameters:
        show_popup(loc.get("no_diameters"), popup_type="error")
        return None
    if not center or not model:
        show_popup(loc.get("no_center"), popup_type="error")
        return None

    # Построение окружностей
    try:
        with utils.layer_context(adoc, DEFAULT_CIRCLE_LAYER):
            for diameter_value in diameters.values():
                add_circle(model, APoint(center[0], center[1]), diameter_value / 2.0, DEFAULT_CIRCLE_LAYER)
    except Exception:
        show_popup(loc.get("circle_error"), popup_type="error")
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

            ATTextInput(ptm=p1, text=work_number, layout="LASER-TEXT", high=7).at_text_input()
            ATTextInput(ptm=p2, text=work_number, layout="schrift", high=30).at_text_input()
        except Exception:
            show_popup(loc.get("text_error"), popup_type="error")
            return None

    # Обновляем вид
    try:
        utils.regen(adoc)
    except Exception:
        show_popup(loc.get("regen_error"), popup_type="error")
        return None

    return True  # Успешное выполнение, продолжаем цикл


if __name__ == "__main__":
    """
    Точка входа в приложение. Повторяет выполнение до нажатия "Отмена".
    """
    try:
        pythoncom.CoInitialize()  # Инициализация COM один раз
        while True:
            if not main():  # Прерываем цикл, если main() вернул None или False
                break
    except Exception as e:
        show_popup(loc.get("error_in_main", str(e)), popup_type="error")
    finally:
        try:
            pythoncom.CoUninitialize()  # Освобождение COM в конце
        except Exception as e:
            show_popup(loc.get("com_release_error", str(e)), popup_type="error")
