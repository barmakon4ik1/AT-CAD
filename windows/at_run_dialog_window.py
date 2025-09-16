"""
Файл: at_run_dialog_window.py
Путь: windows/at_run_dialog_window.py

Описание:
Модуль для управления динамической загрузкой контента в приложении AT-CAD.
Предоставляет функции для загрузки панелей контента и создания списка пунктов меню
с локализованными метками, используя ключи из CONTENT_REGISTRY и переводы из locales.at_localization.
"""

import wx
import logging
import importlib
from typing import Union, List, Tuple  # Добавляем импорт Union, List, Tuple
from windows.at_content_registry import CONTENT_REGISTRY

# # Настройка логирования в консоль
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler()]
# )

def load_content(content_name: str, parent: wx.Window) -> Union[List[Tuple[str, str]], wx.Window, None]:
    """
    Загружает контент по его имени.

    Args:
        content_name: Имя контента (например, 'content_apps', 'cone' или 'get_content_menu').
        parent: Родительский элемент (обычно content_panel).

    Returns:
        Union[List[Tuple[str, str]], wx.Window, None]: Список программ для меню или панель контента.
    """
    logging.info(f"load_content: Попытка загрузки {content_name}")
    if content_name == "get_content_menu":
        result = [(name, info.get("label", name)) for name, info in CONTENT_REGISTRY.items()]
        logging.info(f"load_content: Возвращён список программ: {result}")
        return result

    content_info = CONTENT_REGISTRY.get(content_name)
    if not content_info:
        logging.error(f"Контент {content_name} не найден в CONTENT_REGISTRY")
        return None

    try:
        module = importlib.import_module(content_info.get("module", ""))
        create_window = getattr(module, "create_window")
        panel = create_window(parent)
        logging.info(f"load_content: Успешно загружен контент {content_name}, тип: {panel.__class__.__name__}")
        return panel
    except Exception as e:
        logging.error(f"Ошибка загрузки контента {content_name}: {e}")
        return None

def at_load_content(content_name: str, parent: wx.Window) -> wx.Window | None:
    """
    Вспомогательная функция для загрузки контента.

    Args:
        content_name: Имя контента.
        parent: Родительский элемент.

    Returns:
        wx.Window | None: Панель контента или None при ошибке.
    """
    return load_content(content_name, parent)
