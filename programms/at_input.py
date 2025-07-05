# programms/at_input.py
"""
Модуль для обработки пользовательского ввода в AutoCAD.
"""

from pyautocad import APoint

from config.at_cad_init import ATCadInit
from locales.at_localization import loc
from windows.at_gui_utils import show_popup
from typing import Optional
from programms.at_utils import handle_errors


@handle_errors
def at_point_input(adoc: object = None) -> Optional[APoint]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument). Если None, инициализируется автоматически.

    Returns:
        Optional[APoint]: Выбранная точка в виде APoint или None в случае ошибки или отмены.
    """
    # Инициализация AutoCAD, если adoc не передан
    if adoc is None:
        cad = ATCadInit()
        if not cad.is_initialized():
            show_popup(loc.get('cad_init_error', 'Ошибка инициализации AutoCAD'), popup_type="error")
            return None
        adoc = cad.adoc

    try:
        point_data = adoc.Utility.GetPoint()
        return APoint(point_data) if point_data else None
    except Exception:
        show_popup(loc.get('point_selection_error', 'No point selected'), popup_type="error")
        return None
