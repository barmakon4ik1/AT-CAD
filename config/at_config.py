# at_config.py
"""
Конфигурационный файл для проекта AT-CAD.
Содержит настройки языка, шрифта, интерфейса и параметров черчения.
"""

import os
from locales.at_localization import loc

# Путь к папке с ресурсами (иконки, изображения и т.д.)
RESOURCE_DIR: str = "images"

# Путь к иконке приложения
ICON_PATH: str = os.path.join(RESOURCE_DIR, "AT-CAD_8.png")

# Путь к изображению конуса
CONE_IMAGE_PATH: str = os.path.join(RESOURCE_DIR, "cone_image.png")

# Путь к файлу с последними введёнными данными для конуса
LAST_CONE_INPUT_FILE: str = os.path.join(RESOURCE_DIR, "last_cone_input.json")

# Иконки для языков
LANGUAGE_ICONS: dict = {
    "ru": os.path.join(RESOURCE_DIR, "ru.png"),
    "de": os.path.join(RESOURCE_DIR, "de.png"),
    "en": os.path.join(RESOURCE_DIR, "en.png")
}

# Размер полей ввода и выпадающих списков
INPUT_FIELD_SIZE: tuple[int, int] = (200, -1)

# Язык локализации
LANGUAGE: str = "ru"  # Устанавливает язык интерфейса и сообщений ('ru', 'de', 'en')

# Настройки шрифта
FONT_NAME: str = "Times New Roman"  # Название шрифта для интерфейса
FONT_TYPE: str = "normal"  # Стиль шрифта ('italic', 'normal', 'bold', 'bolditalic')
FONT_SIZE: int = 14  # Размер шрифта в интерфейсе

# Настройки цвета
BACKGROUND_COLOR: str = "#508050"  # Цвет фона (зеленый, как на ДНЦ-пульте Нева)
FOREGROUND_COLOR: str = "white"  # Цвет текста
BANNER_COLOR: str = "light blue"  # Цвет баннера
BANNER_TEXT_COLOR: str = "blue"  # Цвет текста баннера
EXIT_BUTTON_COLOR: str = "#FF0000"  # Цвет кнопки выхода

# Слои по умолчанию для объектов AutoCAD
RECTANGLE_LAYER: str = "0"  # Слой для прямоугольников
DEFAULT_CIRCLE_LAYER: str = "0"  # Слой для окружностей
HEADS_LAYER: str = "0"  # Слой для построения днищ

# Текстовые параметры для черчения
TEXT_HEIGHT_BIG: int = 60  # Высота большого текста
TEXT_HEIGHT_SMALL: int = 30  # Высота малого текста
TEXT_DISTANCE: int = 80  # Расстояние между текстами


def set_language(lang: str) -> None:
    """
    Устанавливает язык интерфейса и обновляет локализацию.

    Args:
        lang: Код языка ('ru', 'de', 'en').

    Raises:
        ValueError: Если передан неподдерживаемый код языка.
    """
    global LANGUAGE
    valid_languages = ["ru", "de", "en"]
    if lang not in valid_languages:
        lang = "ru"  # Язык по умолчанию
        print(f"Предупреждение: Указан неверный язык '{lang}'. Установлен язык по умолчанию: 'ru'.")
    LANGUAGE = lang
    loc.language = lang
    print(f"set_language: LANGUAGE обновлён на {LANGUAGE}, loc.language = {loc.language}")
