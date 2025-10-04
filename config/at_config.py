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
from pathlib import Path
import wx

# --- Базовые пути ---
BASE_DIR: Path = Path(__file__).resolve().parent.parent
IMAGES_DIR: Path = BASE_DIR / "images"
RESOURCE_DIR: Path = BASE_DIR / "config"

# --- Пути к конфигам пользователя ---
USER_CONFIG_PATH: Path = RESOURCE_DIR / "user_settings.json"
USER_LANGUAGE_PATH: Path = RESOURCE_DIR / "user_language.json"
LAST_CONE_INPUT_FILE: Path = RESOURCE_DIR / "last_input.json"

# --- Иконки приложения ---
ICON_PATH: Path = IMAGES_DIR / "AT-CAD_8.png"

# --- Пути к изображениям объектов ---
RING_IMAGE_PATH: Path = IMAGES_DIR / "ring_image.png"
HEAD_IMAGE_PATH: Path = IMAGES_DIR / "head_image.png"
PLATE_IMAGE_PATH: Path = IMAGES_DIR / "plate_image.png"
CONE_IMAGE_PATH: Path = IMAGES_DIR / "cone_image.png"
DONE_ICON_PATH: Path = IMAGES_DIR / "done-icon.png"
SHELL_IMAGE_PATH: Path = IMAGES_DIR / "shell_image.png"
NOZZLE_IMAGE_PATH: Path = IMAGES_DIR / "nozzle_image.png"
CUTOUT_IMAGE_PATH: Path = IMAGES_DIR / "cutout_image.png"
UNWRAPPER_PATH: Path = IMAGES_DIR / "unwrapper_image.png"

# --- Иконки языков ---
LANGUAGE_ICONS: dict[str, Path] = {
    "ru": IMAGES_DIR / "ru.png",
    "de": IMAGES_DIR / "de.png",
    "en": IMAGES_DIR / "en.png",
}

# --- Иконки меню ---
MENU_ICONS: dict[str, Path] = {
    "exit": IMAGES_DIR / "exit_icon.png",
    "about": IMAGES_DIR / "about_icon.png",
    "settings": IMAGES_DIR / "settings_icon.png",
    "lang_ru": IMAGES_DIR / "lang_ru_icon.png",
    "lang_de": IMAGES_DIR / "lang_de_icon.png",
    "lang_en": IMAGES_DIR / "lang_en_icon.png",
}

# --- Параметры интерфейса ---
INPUT_FIELD_SIZE: tuple[int, int] = (200, -1)
BANNER_HIGH: int = 100
LOGO_SIZE: tuple[int, int] = (BANNER_HIGH - 10, BANNER_HIGH - 10)
WINDOW_SIZE: tuple[int, int] = (1280, 980)

# --- Настройки по умолчанию ---
DEFAULT_SETTINGS: dict[str, object] = {
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

# --- Предопределённые слои AutoCAD ---
LAYER_DATA: list[dict[str, object]] = [
    {"name": "0", "color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
    {"name": "AM_0", "color": 7, "linetype": "CONTINUOUS", "lineweight": 1},
    {"name": "SF-ARE", "color": 233, "linetype": "PHANTOM2", "plot": False},
    {"name": "AM_5", "color": 110, "linetype": "CONTINUOUS", "lineweight": 0.05},
    {"name": "LASER-TEXT", "color": 2, "linetype": "CONTINUOUS"},
    {"name": "schrift", "color": 4, "linetype": "CONTINUOUS"},
    {"name": "SF-RAHMEN", "color": 140, "linetype": "CONTINUOUS"},
    {"name": "SF-TEXT", "color": 82, "linetype": "CONTINUOUS"},
    {"name": "TEXT", "color": 2, "linetype": "CONTINUOUS"},
    {"name": "AM_7", "color": 4, "linetype": "AM_ISO08W050", "lineweight": 0.05},
]

# --- Слои по умолчанию для объектов AutoCAD ---
RECTANGLE_LAYER: str = "0"
DEFAULT_CIRCLE_LAYER: str = "0"
HEADS_LAYER: str = "AM_0"
DEFAULT_TEXT_LAYER: str = "schrift"

# --- Настройки размеров ---
DEFAULT_DIM_LAYER: str = "AM_5"
DEFAULT_DIM_STYLE: str = "AM_ISO"
DEFAULT_DIM_OFFSET: float = 60.0
DEFAULT_DIM_SCALE: float = 10.0

# --- Текстовые параметры ---
TEXT_FONT: str = "ISOCPEUR"
TEXT_BOLD: bool = False
TEXT_ITAL: bool = True
TEXT_HEIGHT_BIG: int = 60
TEXT_HEIGHT_SMALL: int = 30
TEXT_DISTANCE: int = 80

# --- Символы статусов ---
CHECK_MARK: str = "✅"
ERROR_MARK: str = "⚠️"

# --- Кэш настроек пользователя ---
_cached_settings: dict[str, object] | None = None


def load_user_settings() -> dict[str, object]:
    """
    Загружает пользовательские настройки из USER_CONFIG_PATH.
    Если файл отсутствует или повреждён — возвращает DEFAULT_SETTINGS.
    """
    global _cached_settings
    if _cached_settings is not None:
        return _cached_settings

    try:
        if USER_CONFIG_PATH.exists():
            with USER_CONFIG_PATH.open('r', encoding='utf-8') as f:
                user_settings = json.load(f)
            for key in DEFAULT_SETTINGS:
                user_settings.setdefault(key, DEFAULT_SETTINGS[key])
            _cached_settings = user_settings
        else:
            _cached_settings = DEFAULT_SETTINGS.copy()
    except Exception:
        _cached_settings = DEFAULT_SETTINGS.copy()

    return _cached_settings


def save_user_settings(settings: dict[str, object]) -> None:
    """
    Сохраняет настройки в USER_CONFIG_PATH.
    Автоматически дополняет недостающие ключи из DEFAULT_SETTINGS.
    """
    global _cached_settings
    try:
        for key in DEFAULT_SETTINGS:
            settings.setdefault(key, DEFAULT_SETTINGS[key])
        with USER_CONFIG_PATH.open('w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        _cached_settings = settings.copy()
    except Exception:
        pass


def get_setting(key: str):
    """
    Возвращает значение настройки по ключу из USER_CONFIG_PATH.
    Если ключ отсутствует — возвращает значение из DEFAULT_SETTINGS.
    """
    settings = load_user_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))


def show_config_window():
    """Открывает окно со списком всех путей и настроек (с подсветкой отсутствующих файлов)."""

    class ConfigFrame(wx.Frame):
        def __init__(self):
            total_items = 3 + len(LANGUAGE_ICONS) + len(MENU_ICONS) + len(load_user_settings()) + 3
            height = min(800, 100 + total_items * 25)
            wx.Frame.__init__(self, None, title="Конфигурация AT-CAD", size=(800, height))

            panel = wx.Panel(self)
            self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
            self.list_ctrl.InsertColumn(0, "Название", width=220)
            self.list_ctrl.InsertColumn(1, "Путь / Значение", width=480)
            self.list_ctrl.InsertColumn(2, "Статус", width=80)

            btn_refresh = wx.Button(panel, label="Обновить")
            btn_close = wx.Button(panel, label="Закрыть")
            btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
            btn_close.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            btn_sizer.AddStretchSpacer()
            btn_sizer.Add(btn_refresh, 0, wx.ALL, 5)
            btn_sizer.Add(btn_close, 0, wx.ALL, 5)

            sizer.Add(btn_sizer, 0, wx.EXPAND | wx.RIGHT, 10)
            panel.SetSizer(sizer)

            self.populate()

        def populate(self):
            self.list_ctrl.DeleteAllItems()

            def add_item(name: str, value: str, exists: bool = True):
                index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), name)
                self.list_ctrl.SetItem(index, 1, str(value))
                self.list_ctrl.SetItem(index, 2, "✅" if exists else "⚠️")
                # Подсветка отсутствующих файлов красным
                if not exists:
                    self.list_ctrl.SetItemBackgroundColour(index, wx.Colour(255, 200, 200))

            add_item("BASE_DIR", BASE_DIR, BASE_DIR.exists())
            add_item("ICON_PATH", ICON_PATH, ICON_PATH.exists())
            add_item("USER_CONFIG_PATH", USER_CONFIG_PATH, USER_CONFIG_PATH.exists())

            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Иконки языков ---")
            for lang, path in LANGUAGE_ICONS.items():
                add_item(f"  {lang}", path, path.exists())

            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Иконки меню ---")
            for name, path in MENU_ICONS.items():
                add_item(f"  {name}", path, path.exists())

            self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), "--- Настройки ---")
            for key, value in load_user_settings().items():
                add_item(f"  {key}", value, True)

        def on_refresh(self, event):
            self.populate()

    app = wx.App(False)
    frame = ConfigFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    show_config_window()