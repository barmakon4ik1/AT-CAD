"""
Конфигурационный файл для проекта AT-CAD.
Содержит настройки языка, шрифта, интерфейса и параметров черчения.
"""

import os
import logging


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Путь к папке с ресурсами (иконки, изображения и т.д.)
IMAGES_DIR: str = "images"
RESOURCE_DIR: str = "config"

# Путь к иконке приложения
ICON_PATH: str = os.path.join(IMAGES_DIR, "AT-CAD_8.png")

# Путь к изображению конуса
CONE_IMAGE_PATH: str = os.path.join(IMAGES_DIR, "cone.png")

# Путь к файлу с последними введёнными данными для конуса
LAST_CONE_INPUT_FILE: str = os.path.join(RESOURCE_DIR, "last_cone_input.json")

# Иконки для языков
LANGUAGE_ICONS: dict = {
    "ru": os.path.join(IMAGES_DIR, "ru.png"),
    "de": os.path.join(IMAGES_DIR, "de.png"),
    "en": os.path.join(IMAGES_DIR, "en.png"),
}

# Размер полей ввода и выпадающих списков
INPUT_FIELD_SIZE: tuple[int, int] = (200, -1)

# Настройка высоты баннера
BANNER_HIGH: int = 100  # Высота баннера в пикселях

# Размер логотипа в баннере
LOGO_SIZE: tuple[int, int] = (BANNER_HIGH - 10, BANNER_HIGH - 10)  # Ширина и высота логотипа в пикселях

# Настройка окна
WINDOW_SIZE: tuple[int, int] = (1280, 1024)

# Язык локализации
LANGUAGE: str = "ru"  # Устанавливает язык интерфейса и сообщений ('ru', 'de', 'en')

# Настройки шрифта
FONT_NAME: str = "Times New Roman"  # Название шрифта для интерфейса
FONT_TYPE: str = "normal"  # Стиль шрифта ('italic', 'normal', 'bold', 'bolditalic')
FONT_SIZE: int = 16  # Размер шрифта в интерфейсе
STATUS_FONT_SIZE: int = 8  # Размер шрифта для статусной строки
STATUS_TEXT_COLOR: str = "white"  # Цвет текста статусной строки
BANNER_FONT_SIZE: int = 24  # (для баннера)

# Настройки цвета
BACKGROUND_COLOR: str = "#508050"  # Цвет фона (зеленый, как на ДНЦ-пульте Нева)
FOREGROUND_COLOR: str = "white"  # Цвет текста (для элементов, кроме баннера и статусной строки)
BANNER_COLOR: str = "light blue"  # Цвет баннера
BANNER_TEXT_COLOR: str = "black"  # Цвет текста баннера
EXIT_BUTTON_COLOR: str = "#FF0000"  # Цвет кнопки выхода

# Слои по умолчанию для объектов AutoCAD
RECTANGLE_LAYER: str = "0"  # Слой для прямоугольников
DEFAULT_CIRCLE_LAYER: str = "0"  # Слой для окружностей
HEADS_LAYER: str = "0"  # Слой для построения днищ

# Текстовые параметры для черчения
TEXT_HEIGHT_BIG: int = 60  # Высота большого текста
TEXT_HEIGHT_SMALL: int = 30  # Высота малого текста
TEXT_DISTANCE: int = 80  # Расстояние между текстами
