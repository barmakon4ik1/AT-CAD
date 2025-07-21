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
from windows.at_content_registry import CONTENT_REGISTRY
from locales.at_localization_class import loc  # Импортируем loc для локализации

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,  # Основной уровень логирования для ошибок
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def at_load_content(content_name: str, parent: wx.Window) -> wx.Window | None:
    """
    Загружает панель контента по имени из CONTENT_REGISTRY.

    Args:
        content_name (str): Ключ контента в CONTENT_REGISTRY (например, 'cone', 'content_apps').
        parent (wx.Window): Родительский wx.Window для создаваемой панели.

    Returns:
        wx.Window | None: Созданная панель контента или None, если загрузка не удалась.
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
        content = create_window(parent)
        if not isinstance(content, wx.Window):
            logging.error(f"Некорректный контент возвращён для {content_name}: ожидался wx.Window")
            return None
        logging.info(f"Контент {content_name} успешно загружен из модуля {module_path}")
        return content
    except Exception as e:
        logging.error(f"Ошибка загрузки контента {content_name}: {e}")
        return None


def load_content(content_key: str, parent: wx.Window) -> list[tuple[str, str]] | wx.Window | None:
    """
    Возвращает список пунктов меню контента с локализованными метками или загружает панель контента.

    Args:
        content_key (str): Ключ контента (например, 'cone', 'content_apps') или 'get_content_menu' для получения списка меню.
        parent (wx.Window): Родительский wx.Window для загрузки контента.

    Returns:
        list[tuple[str, str]] | wx.Window | None: Список кортежей (content_name, translated_label) для меню
        или панель контента (wx.Window) при загрузке контента, или None в случае ошибки.
    """
    if content_key == "get_content_menu":
        # Формируем список пунктов меню с локализованными метками
        menu_items = []
        for name, info in CONTENT_REGISTRY.items():
            if name != "content_apps":  # Исключаем content_apps из меню
                label_key = info.get("label", name)  # Используем ключ локализации или имя как запасной вариант
                # Проверяем, является ли label_key словарем, и извлекаем строку, если возможно
                if isinstance(label_key, dict):
                    logging.warning(f"Получен словарь вместо строки для label_key в CONTENT_REGISTRY для {name}: {label_key}")
                    label_key = label_key.get('key', name)  # Извлекаем строковый ключ или используем имя
                translated_label = loc.get(label_key, name)  # Получаем переведённую метку, возвращаем имя, если перевод отсутствует
                if translated_label == label_key:
                    logging.warning(f"Перевод для ключа '{label_key}' не найден в translations, использовано имя контента: {name}")
                else:
                    logging.info(f"Локализованная метка для {name}: {translated_label}")
                menu_items.append((name, translated_label))
        return menu_items
    else:
        # Перенаправляем на at_load_content для загрузки панели
        logging.warning(f"load_content вызван с content_key='{content_key}', перенаправление на at_load_content")
        return at_load_content(content_key, parent)
