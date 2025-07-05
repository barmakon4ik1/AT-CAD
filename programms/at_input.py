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
def at_point_input(adoc: object) -> Optional[APoint]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD.
    """
    try:
        point_data = adoc.Utility.GetPoint()
        return APoint(point_data) if point_data else None
    except Exception:
        show_popup(loc.get('point_selection_error', 'No point selected'), popup_type="error")
        return None
