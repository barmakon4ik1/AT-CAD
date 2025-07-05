# windows/at_run_dialog_window.py
"""
Модуль для управления динамической загрузкой контента в AT-CAD.
"""

import wx
import logging
import importlib
from windows.at_content_registry import CONTENT_REGISTRY

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def at_load_content(content_name: str, parent: wx.Window, cad) -> wx.Window:
    """
    Загружает контент по его имени из CONTENT_REGISTRY.
    Используется в switch_content для динамической загрузки панелей.

    Args:
        content_name: Имя контента (ключ в CONTENT_REGISTRY).
        parent: Родительский wx.Window для создаваемого контента.
        cad: Экземпляр ATCadInit для работы с AutoCAD.

    Returns:
        wx.Window: Созданная панель контента или None в случае ошибки.
    """
    content_info = CONTENT_REGISTRY.get(content_name)
    if not content_info:
        logging.error(f"Контент с ключом '{content_name}' не найден в CONTENT_REGISTRY")
        return None

    try:
        # Динамически импортируем модуль
        module_path = content_info["module"]
        module = importlib.import_module(module_path)
        create_window = getattr(module, "create_window")
        content = create_window(parent, cad=cad)
        if not isinstance(content, wx.Window):
            logging.error(f"Некорректный контент возвращён для {content_name}")
            return None
        logging.info(f"Контент {content_name} успешно загружен")
        return content
    except Exception as e:
        logging.error(f"Ошибка загрузки контента {content_name}: {e}")
        return None


def load_content(content_key: str, parent: wx.Window, cad=None) -> list | wx.Window:
    """
    Возвращает список элементов меню контента для create_menu или загружает панель контента.

    Args:
        content_key: Ключ контента или 'get_content_menu' для получения списка меню.
        parent: Родительский wx.Window (для загрузки контента).
        cad: Экземпляр ATCadInit для работы с AutoCAD (опционально).

    Returns:
        list | wx.Window: Список кортежей (content_name, label) для меню или панель контента.
    """
    if content_key == "get_content_menu":
        # Возвращаем список доступных программ для меню
        return [(name, info["label"]) for name, info in CONTENT_REGISTRY.items() if name != "content_apps"]
    else:
        # Перенаправляем на at_load_content для загрузки панели
        logging.warning(f"load_content вызван с content_key='{content_key}', перенаправление на at_load_content")
        return at_load_content(content_key, parent, cad=cad)
