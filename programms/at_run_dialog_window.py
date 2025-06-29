# at_run_dialog_window.py
"""
Модуль для запуска диалогового окна и возврата введенных данных.
"""

import importlib
import wx
from at_localization import loc
from at_gui_utils import show_popup
from typing import Optional, Dict, Any


def at_run_dialog_window(window_name: str) -> Optional[Dict[str, Any]]:
    """
    Запускает диалоговое окно и возвращает введенные пользователем данные.

    Args:
        window_name: Имя модуля диалогового окна (например, 'at_head_input_window').

    Returns:
        dict: Данные из диалога или None при ошибке/отмене.
    """
    try:
        module_name = window_name.lower()
        module = importlib.import_module(module_name)
        if hasattr(module, 'create_window'):
            # Запуск диалогового окна и получение данных
            dialog_data = module.create_window()
            return dialog_data
        show_popup(loc.get("module_error", module_name), popup_type="error")
        return None
    except ImportError:
        show_popup(loc.get("module_import_error", module_name), popup_type="error")
        return None
    except Exception:
        show_popup(loc.get("dialog_error", ""), popup_type="error")
        return None
