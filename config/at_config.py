"""
Файл: at_config.py
Путь: config/at_config.py

Описание:
Конфигурационный файл для проекта AT-CAD. Содержит пути к ресурсам, настройки по умолчанию
и функции для загрузки/сохранения пользовательских настроек из user_settings.json.
"""

import os
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Базовая директория проекта
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Путь к папке с ресурсами
IMAGES_DIR: str = "images"
RESOURCE_DIR: str = "config"

# Путь к файлу пользовательских настроек
USER_CONFIG_PATH: str = os.path.join(RESOURCE_DIR, "user_settings.json")
USER_LANGUAGE_PATH: str = os.path.join(RESOURCE_DIR, "user_language.json")

# Путь к иконке приложения
ICON_PATH: str = os.path.join(IMAGES_DIR, "AT-CAD_8.png")

# Пути к изображениям для различных объектов
RING_IMAGE_PATH: str = os.path.join(IMAGES_DIR, "ring_image.png")
HEAD_IMAGE_PATH: str = os.path.join(IMAGES_DIR, "head_image.png")
PLATE_IMAGE_PATH: str = os.path.join(IMAGES_DIR, "plate_image.png")
CONE_IMAGE_PATH: str = os.path.join(IMAGES_DIR, "cone.png")
DONE_ICON_PATH: str = os.path.join(IMAGES_DIR, "done-icon.png")

# Путь к файлу с последними введёнными данными для конуса
LAST_CONE_INPUT_FILE: str = os.path.join(RESOURCE_DIR, "last_input.json")

# Иконки для языков
LANGUAGE_ICONS: dict = {
    "ru": os.path.join(IMAGES_DIR, "ru.png"),
    "de": os.path.join(IMAGES_DIR, "de.png"),
    "en": os.path.join(IMAGES_DIR, "en.png"),
}

# Иконки для пунктов меню
MENU_ICONS: dict = {
    "exit": os.path.join(IMAGES_DIR, "exit_icon.png"),
    "about": os.path.join(IMAGES_DIR, "about_icon.png"),
    "settings": os.path.join(IMAGES_DIR, "settings_icon.png"),
    "lang_ru": os.path.join(IMAGES_DIR, "lang_ru_icon.png"),
    "lang_de": os.path.join(IMAGES_DIR, "lang_de_icon.png"),
    "lang_en": os.path.join(IMAGES_DIR, "lang_en_icon.png"),
}

# Размер полей ввода и выпадающих списков
INPUT_FIELD_SIZE: tuple[int, int] = (200, -1)

# Высота баннера в пикселях
BANNER_HIGH: int = 100

# Размер логотипа в баннере
LOGO_SIZE: tuple[int, int] = (BANNER_HIGH - 10, BANNER_HIGH - 10)

# Размер главного окна приложения
WINDOW_SIZE: tuple[int, int] = (1280, 980)

# Словарь настроек по умолчанию
DEFAULT_SETTINGS: dict = {
    "FONT_NAME": "Times New Roman",
    "FONT_TYPE": "normal",
    "FONT_SIZE": 16,
    "STATUS_FONT_SIZE": 8,
    "STATUS_TEXT_COLOR": "white",
    "BANNER_FONT_SIZE": 24,
    "LABEL_FONT_SIZE": 24,
    "LABEL_FONT_NAME": "Times New Roman",
    "LABEL_FONT_TYPE": "normal",
    "LABEL_FONT_WEIGHT": "bold",
    "BACKGROUND_COLOR": "#508050",
    "FOREGROUND_COLOR": "white",
    "BANNER_COLOR": "light blue",
    "BANNER_TEXT_COLOR": "black",
    "EXIT_BUTTON_COLOR": "dark grey",
    "LABEL_FONT_COLOR": "blue",
    "BUTTON_FONT_COLOR": "white",
}

# Слои по умолчанию для объектов AutoCAD
RECTANGLE_LAYER: str = "0"
DEFAULT_CIRCLE_LAYER: str = "0"
HEADS_LAYER: str = "0"
DEFAULT_TEXT_LAYER: str = "schrift"

# Текстовые параметры для черчения
TEXT_HEIGHT_BIG: int = 60
TEXT_HEIGHT_SMALL: int = 30
TEXT_DISTANCE: int = 80
CHECK_MARK: str = "✅"
ERROR_MARK: str = "⚠️"

# Кэш для пользовательских настроек
_cached_settings = None


def load_user_settings() -> dict:
    """
    Загружает пользовательские настройки из файла user_settings.json.
    Если файл не существует или содержит ошибки, возвращает настройки по умолчанию.

    Возвращает:
        dict: Словарь с пользовательскими настройками.
    """
    global _cached_settings
    if _cached_settings is not None:
        return _cached_settings
    try:
        if os.path.exists(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                # Проверяем, что все ключи из DEFAULT_SETTINGS присутствуют
                for key in DEFAULT_SETTINGS:
                    if key not in user_settings:
                        user_settings[key] = DEFAULT_SETTINGS[key]
                logging.info(f"Пользовательские настройки загружены: {user_settings}")
                _cached_settings = user_settings
                return user_settings
        else:
            logging.info("Файл пользовательских настроек не найден, используются настройки по умолчанию")
            _cached_settings = DEFAULT_SETTINGS.copy()
            return _cached_settings
    except Exception as e:
        logging.error(f"Ошибка загрузки пользовательских настроек: {e}")
        _cached_settings = DEFAULT_SETTINGS.copy()
        return _cached_settings


def save_user_settings(settings: dict) -> None:
    """
    Сохраняет настройки в файл user_settings.json.

    Аргументы:
        settings (dict): Словарь с настройками.
    """
    global _cached_settings
    try:
        # Проверяем, что все ключи из DEFAULT_SETTINGS присутствуют
        for key in DEFAULT_SETTINGS:
            if key not in settings:
                settings[key] = DEFAULT_SETTINGS[key]
        with open(USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        _cached_settings = settings.copy()
        logging.info(f"Пользовательские настройки сохранены: {settings}")
    except Exception as e:
        logging.error(f"Ошибка сохранения пользовательских настроек: {e}")


def get_setting(key: str) -> any:
    """
    Возвращает значение настройки по ключу из user_settings.json.

    Аргументы:
        key (str): Ключ настройки (например, "FONT_NAME").

    Возвращает:
        Значение настройки или значение по умолчанию из DEFAULT_SETTINGS.
    """
    settings = load_user_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))
