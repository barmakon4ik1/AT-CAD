# config/at_config.py
"""
Файл: at_config.py
Путь: config/at_config.py

Описание:
Конфигурационный файл для проекта AT-CAD. Содержит:
- Пути к ресурсам проекта (иконки, конфиги, изображения)
- Настройки интерфейса и слоёв AutoCAD
- Функции для загрузки/сохранения пользовательских настроек
"""

import json
import logging
from pathlib import Path
from typing import TypedDict, Optional

import wx

logger = logging.getLogger("at_config")

# ============================================================
# БАЗОВЫЕ ПУТИ
# ============================================================

BASE_DIR: Path = Path(__file__).resolve().parent.parent
IMAGES_DIR: Path = BASE_DIR / "images"
RESOURCE_DIR: Path = BASE_DIR / "config"

# ============================================================
# ПУТИ К КОНФИГАМ ПОЛЬЗОВАТЕЛЯ
# ============================================================

USER_CONFIG_PATH: Path = RESOURCE_DIR / "user_settings.json"
USER_LANGUAGE_PATH: Path = RESOURCE_DIR / "user_language.json"
LAST_CONE_INPUT_FILE: Path = RESOURCE_DIR / "last_input.json"
NAME_PLATES_FILE: Path = RESOURCE_DIR / "name_plates/name_plates.json"

# ============================================================
# ИКОНКИ ПРИЛОЖЕНИЯ
# ============================================================

ICON_PATH: Path = IMAGES_DIR / "AT-CAD_8.png"

# ============================================================
# ПУТИ К ИЗОБРАЖЕНИЯМ ОБЪЕКТОВ
# ============================================================

RING_IMAGE_PATH: Path = IMAGES_DIR / "ring_image.png"
HEAD_IMAGE_PATH: Path = IMAGES_DIR / "head_image.png"
PLATE_IMAGE_PATH: Path = IMAGES_DIR / "plate_image.png"
CONE_IMAGE_PATH: Path = IMAGES_DIR / "cone_image.png"
DONE_ICON_PATH: Path = IMAGES_DIR / "done-icon.png"
SHELL_IMAGE_PATH: Path = IMAGES_DIR / "shell_image.png"
NOZZLE_IMAGE_PATH: Path = IMAGES_DIR / "nozzle_image.png"
CUTOUT_IMAGE_PATH: Path = IMAGES_DIR / "cutout_image.png"
UNWRAPPER_PATH: Path = IMAGES_DIR / "unwrapper_image.png"
ECCENTRIC_REDUCER_PATH: Path = IMAGES_DIR / "eccentric_reducer_image.png"
CONE_PIPE_IMAGE_PATH: Path = IMAGES_DIR / "cone-pipe_image.png"
NAME_PLATE_IMAGE_PATH: Path = IMAGES_DIR / "name_plate_image.png"
BRACKET1_IMAGE_PATH: Path = IMAGES_DIR / "SB1.png"
BRACKET2_IMAGE_PATH: Path = IMAGES_DIR / "SB2.png"
BRACKET3_IMAGE_PATH: Path = IMAGES_DIR / "SB3.png"
BRACKET4_IMAGE_PATH: Path = IMAGES_DIR / "SB4.png"
BRACKET5_IMAGE_PATH: Path = IMAGES_DIR / "SB5.png"
BRACKET5_CONE_IMAGE_PATH: Path = IMAGES_DIR / "SB_cone.png"
SLOTTED_HOLE_IMAGE_PATH: Path = IMAGES_DIR / "slotted_hole.png"
ARROWS_IMAGE_PATH: Path = IMAGES_DIR / "arrows/"

# ============================================================
# ИКОНКИ ЯЗЫКОВ И МЕНЮ
# ============================================================

LANGUAGE_ICONS: dict[str, Path] = {
    "ru": IMAGES_DIR / "ru.png",
    "de": IMAGES_DIR / "de.png",
    "en": IMAGES_DIR / "en.png",
}

MENU_ICONS: dict[str, Path] = {
    "exit":     IMAGES_DIR / "exit_icon.png",
    "about":    IMAGES_DIR / "about_icon.png",
    "settings": IMAGES_DIR / "settings_icon.png",
    "lang_ru":  IMAGES_DIR / "lang_ru_icon.png",
    "lang_de":  IMAGES_DIR / "lang_de_icon.png",
    "lang_en":  IMAGES_DIR / "lang_en_icon.png",
}

# ============================================================
# ПАРАМЕТРЫ ИНТЕРФЕЙСА
# FIX: wx.Size вместо tuple[int, int] — устраняет предупреждение
#      "Expected type 'Size', got 'tuple[int, int]' instead"
#      в местах, где wxPython ожидает wx.Size.
# ============================================================

INPUT_FIELD_SIZE: wx.Size = wx.Size(150, -1)
BUTTON_SIZE: wx.Size = wx.Size(150, -1)
BANNER_HIGH: int = 100
LOGO_SIZE: wx.Size = wx.Size(BANNER_HIGH - 10, BANNER_HIGH - 10)
WINDOW_SIZE: wx.Size = wx.Size(1280, 980)

FORM_CONFIG: dict[str, object] = {
    "input_size":        INPUT_FIELD_SIZE,
    "row_border":        5,
    "label_padding":     10,
    "label_proportion":  0,
    "field_proportion":  0,
    "field_bg_color":    (255, 255, 255),
}

# ============================================================
# НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ
# FIX: TypedDict key must be a string literal — PyCharm требует,
#      чтобы TypedDict описывал ровно те ключи, которые используются
#      в DEFAULT_SETTINGS. Любое несовпадение (лишний ключ, опечатка)
#      даёт предупреждение. Здесь ключи выверены и совпадают 1-в-1.
# ============================================================

class DefaultSettings(TypedDict):
    TITLE_FONT_NAME:   str
    TITLE_FONT_TYPE:   str
    TITLE_FONT_SIZE:   int
    TITLE_FONT_WEIGHT: int
    TITLE_FONT_COLOR:  str
    FONT_NAME:         str
    FONT_TYPE:         str
    FONT_SIZE:         int
    STATUS_FONT_SIZE:  int
    STATUS_TEXT_COLOR: str
    BANNER_FONT_SIZE:  int
    LABEL_FONT_SIZE:   int
    LABEL_FONT_NAME:   str
    LABEL_FONT_TYPE:   str
    LABEL_FONT_WEIGHT: str
    BACKGROUND_COLOR:  str
    FOREGROUND_COLOR:  str
    BANNER_COLOR:      str
    BANNER_TEXT_COLOR: str
    EXIT_BUTTON_COLOR: str
    LABEL_FONT_COLOR:  str
    BUTTON_FONT_COLOR: str

DEFAULT_SETTINGS: DefaultSettings = {
    "TITLE_FONT_NAME":   "BUSE letters 16x8",
    "TITLE_FONT_TYPE":   "normal",
    "TITLE_FONT_SIZE":   48,
    "TITLE_FONT_WEIGHT": 30,
    "TITLE_FONT_COLOR":  "(0, 0, 0)",
    "FONT_NAME":         "Times New Roman",
    "FONT_TYPE":         "normal",
    "FONT_SIZE":         16,
    "STATUS_FONT_SIZE":  8,
    "STATUS_TEXT_COLOR": "white",
    "BANNER_FONT_SIZE":  24,
    "LABEL_FONT_SIZE":   24,
    "LABEL_FONT_NAME":   "Times New Roman",
    "LABEL_FONT_TYPE":   "normal",
    "LABEL_FONT_WEIGHT": "bold",
    "BACKGROUND_COLOR":  "#508050",
    "FOREGROUND_COLOR":  "white",
    "BANNER_COLOR":      "light blue",
    "BANNER_TEXT_COLOR": "black",
    "EXIT_BUTTON_COLOR": "dark grey",
    "LABEL_FONT_COLOR":  "blue",
    "BUTTON_FONT_COLOR": "white",
}

# ============================================================
# СЛОИ AutoCAD
# FIX: LayerDef(TypedDict) вместо dict[str, object] —
#      устраняет предупреждения "Expected type 'str'/'int', got 'object'"
#      в at_cad_init.py при обращении к полям слоя.
#      total=False: не все слои имеют lineweight и plot.
# ============================================================

class LayerDef(TypedDict, total=False):
    name:       str
    color:      int
    linetype:   str
    lineweight: float
    plot:       bool

LAYER_DATA: list[LayerDef] = [
    {"name": "0",          "color": 7,   "linetype": "CONTINUOUS", "lineweight": 0.25},
    {"name": "AM_0",       "color": 7,   "linetype": "CONTINUOUS", "lineweight": 1.0},
    {"name": "SF-ARE",     "color": 233, "linetype": "PHANTOM2",   "plot": False},
    {"name": "AM_5",       "color": 110, "linetype": "CONTINUOUS", "lineweight": 0.05},
    {"name": "AM_7",       "color": 4,   "linetype": "AMISO8W050", "lineweight": 0.05},
    {"name": "LASER-TEXT", "color": 2,   "linetype": "CONTINUOUS"},
    {"name": "schrift",    "color": 4,   "linetype": "CONTINUOUS"},
    {"name": "SF-RAHMEN",  "color": 140, "linetype": "CONTINUOUS"},
    {"name": "SF-TEXT",    "color": 82,  "linetype": "CONTINUOUS"},
    {"name": "TEXT",       "color": 2,   "linetype": "CONTINUOUS"},
]

# ============================================================
# СЛОИ ПО УМОЛЧАНИЮ ДЛЯ ОБЪЕКТОВ AutoCAD
# ============================================================

DEFAULT_CUTOUT_LAYER: str = "0"
RECTANGLE_LAYER: str = "0"
DEFAULT_CIRCLE_LAYER: str = "0"
HEADS_LAYER: str = "AM_0"
DEFAULT_TEXT_LAYER: str = "schrift"
DEFAULT_LASER_LAYER: str = "LASER-TEXT"
DEFAULT_ACCOMPANY_TEXT_LAYER: str = "AM_5"

# ============================================================
# НАСТРОЙКИ РАЗМЕРОВ
# ============================================================

DEFAULT_DIM_LAYER: str = "AM_5"
DEFAULT_DIM_STYLE: str = "AM_ISO"
DEFAULT_DIM_OFFSET: float = 60.0
DEFAULT_DIM_SCALE: float = 10.0

# ============================================================
# ТЕКСТОВЫЕ ПАРАМЕТРЫ
# ============================================================

TEXT_FONT: str = "ISOCPEUR"
TEXT_BOLD: bool = False
TEXT_ITAL: bool = True
TEXT_HEIGHT_BIG: int = 60
TEXT_HEIGHT_SMALL: int = 30
TEXT_HEIGHT_LASER: int = 7
TEXT_DISTANCE: int = 80
MAIN_TEXT_OFFSET: int = 10

# ============================================================
# СИМВОЛЫ СТАТУСОВ
# ============================================================

CHECK_MARK: str = "✅"
ERROR_MARK: str = "⚠️"

# ============================================================
# ЗАГРУЗКА / СОХРАНЕНИЕ НАСТРОЕК
# ============================================================

_cached_settings: Optional[dict[str, object]] = None


def load_user_settings() -> dict[str, object]:
    """
    Загружает пользовательские настройки из USER_CONFIG_PATH.
    Если файл отсутствует или повреждён — возвращает DEFAULT_SETTINGS.
    Результат кэшируется до следующего вызова save_user_settings().
    """
    global _cached_settings
    if _cached_settings is not None:
        return _cached_settings

    if USER_CONFIG_PATH.exists():
        try:
            with USER_CONFIG_PATH.open("r", encoding="utf-8") as f:
                user_settings: dict[str, object] = json.load(f)
            for key in DEFAULT_SETTINGS:
                user_settings.setdefault(key, DEFAULT_SETTINGS[key])  # type: ignore[literal-required]
            _cached_settings = user_settings
            return _cached_settings
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"load_user_settings: не удалось прочитать {USER_CONFIG_PATH}: {e}")

    _cached_settings = dict(DEFAULT_SETTINGS)
    return _cached_settings


def save_user_settings(settings: dict[str, object]) -> None:
    """
    Сохраняет настройки в USER_CONFIG_PATH.
    Автоматически дополняет недостающие ключи из DEFAULT_SETTINGS.
    """
    global _cached_settings
    for key in DEFAULT_SETTINGS:
        settings.setdefault(key, DEFAULT_SETTINGS[key])  # type: ignore[literal-required]
    try:
        with USER_CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        _cached_settings = settings.copy()
    except OSError as e:
        logger.error(f"save_user_settings: не удалось сохранить {USER_CONFIG_PATH}: {e}")


def get_setting(key: str) -> object:
    """
    Возвращает значение настройки по ключу.
    Если ключ отсутствует — возвращает значение из DEFAULT_SETTINGS.
    """
    settings = load_user_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))  # type: ignore[literal-required]


# ============================================================
# ОКНО КОНФИГУРАЦИИ (диагностика путей и настроек)
# ============================================================

def show_config_window() -> None:
    """Открывает окно со списком всех путей и настроек (с подсветкой отсутствующих файлов)."""

    class ConfigFrame(wx.Frame):
        def __init__(self) -> None:
            total_items = 3 + len(LANGUAGE_ICONS) + len(MENU_ICONS) + len(load_user_settings()) + 3
            height = min(800, 100 + total_items * 25)
            super().__init__(None, title="Конфигурация AT-CAD", size=wx.Size(800, height))

            panel = wx.Panel(self)
            self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
            self.list_ctrl.InsertColumn(0, "Название",    width=220)
            self.list_ctrl.InsertColumn(1, "Путь / Значение", width=480)
            self.list_ctrl.InsertColumn(2, "Статус",      width=80)

            btn_refresh = wx.Button(panel, label="Обновить")
            btn_close   = wx.Button(panel, label="Закрыть")
            btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
            btn_close.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            btn_sizer.AddStretchSpacer()
            btn_sizer.Add(btn_refresh, 0, wx.ALL, 5)
            btn_sizer.Add(btn_close,   0, wx.ALL, 5)

            sizer.Add(btn_sizer, 0, wx.EXPAND | wx.RIGHT, 10)
            panel.SetSizer(sizer)
            self.populate()

        def _add_item(self, label: str, display_value: str, exists: bool = True) -> None:
            """
            FIX: переименованы параметры label/display_value вместо name/value —
                 устраняет "Shadows name 'name'/'value' from outer scope".
            FIX: Path передаётся уже как str через display_value —
                 устраняет "Expected type 'str', got 'Path' instead".
            """
            idx = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), label)
            self.list_ctrl.SetItem(idx, 1, display_value)
            self.list_ctrl.SetItem(idx, 2, CHECK_MARK if exists else ERROR_MARK)
            if not exists:
                self.list_ctrl.SetItemBackgroundColour(idx, wx.Colour(255, 200, 200))

        def populate(self) -> None:
            self.list_ctrl.DeleteAllItems()

            # Базовые пути
            self._add_item("BASE_DIR",        str(BASE_DIR),        BASE_DIR.exists())
            self._add_item("ICON_PATH",       str(ICON_PATH),       ICON_PATH.exists())
            self._add_item("USER_CONFIG_PATH", str(USER_CONFIG_PATH), USER_CONFIG_PATH.exists())

            # Иконки языков
            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Иконки языков ---")
            for lang, path in LANGUAGE_ICONS.items():
                self._add_item(f"  {lang}", str(path), path.exists())

            # Иконки меню
            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Иконки меню ---")
            for icon_key, path in MENU_ICONS.items():
                self._add_item(f"  {icon_key}", str(path), path.exists())

            # Текущие настройки
            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Настройки ---")
            for setting_key, setting_val in load_user_settings().items():
                self._add_item(f"  {setting_key}", str(setting_val))

        def on_refresh(self, _event: wx.CommandEvent) -> None:
            self.populate()

    app = wx.App(False)
    frame = ConfigFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    show_config_window()