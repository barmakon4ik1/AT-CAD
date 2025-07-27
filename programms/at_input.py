# programms/at_input.py
"""
Модуль для обработки пользовательского ввода в AutoCAD.
"""
import win32com.client
from typing import Optional, List
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
from programms.at_utils import handle_errors

@handle_errors
def at_point_input(adoc: object = None) -> Optional[List[float]]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument). Если None, инициализируется автоматически.

    Returns:
        Optional[List[float]]: Выбранная точка в виде списка [x, y, z] или None в случае ошибки или отмены.
    """
    try:
        adoc.Utility.Prompt("Укажите точку: ")
        point_data = adoc.Utility.GetPoint()
        point_list = [float(point_data[0]), float(point_data[1]), float(point_data[2])]
        return point_list
    except Exception as e:
        show_popup(loc.get('point_selection_error', 'No point selected'), popup_type="error")
        return None


if __name__ == "__main__":
    """
    Тест получения точки
    """
    cad = ATCadInit()
    adoc, model = cad.adoc, cad.model
    input_point = at_point_input(adoc)
    print(f"at_point_input: {input_point}")
