"""
Файл: at_window_utils.py
Путь: windows/at_window_utils.py

Описание:
Модуль с утилитами для главного окна AT-CAD.
Содержит функции для работы с позицией окна, всплывающими окнами, шрифтами и стилизацией интерфейса.
Все настройки (FONT_NAME, FONT_TYPE, FONT_SIZE, BACKGROUND_COLOR и т.д.) читаются из user_settings.json
через get_setting. Локализация текстов осуществляется через loc.get с использованием словаря translations.
"""
import logging
import os
import json
import wx
from typing import Tuple, Dict, Optional, List
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_input import at_point_input
from windows.at_style import style_textctrl, style_combobox, style_radiobutton, style_staticbox, style_label
from config.at_config import load_user_settings, DEFAULT_SETTINGS, get_setting, ICON_PATH, RESOURCE_DIR
from config.at_last_input import save_last_input

# -----------------------------
# Кастомные события
# -----------------------------
LANGUAGE_CHANGE_EVT_TYPE = wx.NewEventType()
LANGUAGE_CHANGE_EVT = wx.PyEventBinder(LANGUAGE_CHANGE_EVT_TYPE, 1)

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "en": "Error",
        "de": "Fehler"
    },
    "info": {
        "ru": "Информация",
        "en": "Information",
        "de": "Information"
    },
    "point_not_selected": {
        "ru": "Точка не выбрана",
        "en": "Point not selected",
        "de": "Punkt nicht ausgewählt"
    },
    "point_selected": {
        "ru": "Точка выбрана: x={0}, y={1}",
        "en": "Point selected: x={0}, y={1}",
        "de": "Punkt ausgewählt: x={0}, y={1}"
    },
    "point_selection_error": {
        "ru": "Ошибка выбора точки: {0}",
        "en": "Point selection error: {0}",
        "de": "Fehler bei der Punktauswahl: {0}"
    },
    "copyright": {
        "ru": "Дизайн и разработка: А.Тутубалин © 2025",
        "en": "Design and development: A.Tutubalin © 2025",
        "de": "Design und Entwicklung: A.Tutubalin © 2025"
    },
    "ok_button": {
        "ru": "ОК",
        "en": "OK",
        "de": "OK"
    },
    "cancel_button": {
        "ru": "Отмена",
        "en": "Cancel",
        "de": "Abbrechen"
    },
    "clear_button": {
        "ru": "Очистить",
        "en": "Clear",
        "de": "Löschen"
    },
    "image_not_found": {
        "ru": "Изображение не найдено",
        "en": "Image not found",
        "de": "Bild nicht gefunden"
    },
    "image_error": {
        "ru": "Ошибка изображения",
        "en": "Image error",
        "de": "Bildfehler"
    },
    "invalid_size": {
        "ru": "Недопустимый размер панели",
        "en": "Invalid panel size",
        "de": "Ungültige Panelgröße"
    },
    "test_label": {
        "ru": "Тестовый текст",
        "de": "Beispieltext",
        "en": "Test text"
    },
    "test_window": {
        "ru": "Тестовое окно",
        "de": "Beispielfenster",
        "en": "Test window"
    }
}
loc.register_translations(TRANSLATIONS)

# Настройка логирования (только критические ошибки)
logging.basicConfig(
    level=logging.ERROR,
    filename="logs/at_window_utils.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Кэш для данных из JSON-файлов
_common_data_cache = None


class BaseContentPanel(wx.Panel):
    """
    Базовый класс для панелей контента: AppsContentPanel, ConeContentPanel, RingsContentPanel, PlateContentPanel, HeadContentPanel.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = load_user_settings()
        background_color = self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
        self.SetBackgroundColour(wx.Colour(background_color))
        self.last_input_file = ""  # Для панелей ввода данных, устанавливается в дочерних классах
        self.insert_point = None  # Для панелей с выбором точки
        self.buttons = []  # Для панелей с кнопками

    def switch_content_panel(self, content_name: str) -> None:
        """
        Переключает содержимое главного окна на указанную панель.

        Args:
            content_name: Имя модуля контента для переключения.
        """
        try:
            main_window = wx.GetTopLevelParent(self)
            if hasattr(main_window, "switch_content"):
                main_window.switch_content(content_name)
            else:
                show_popup(loc.get("error", "Ошибка: невозможно переключить контент"), popup_type="error")
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка переключения контента: {str(e)}"), popup_type="error")

    def on_ok(self, event: wx.Event, close_window: bool = False) -> None:
        """
        Обрабатывает нажатие кнопки OK: собирает данные, проверяет их валидность, обрабатывает данные.

        Args:
            event: Событие wxPython.
            close_window: Если True, переключает на content_apps после успешной обработки.
        """
        try:
            data = self.collect_input_data()
            if not self.validate_input(data):
                show_popup(loc.get("error", "Некорректные входные данные"), popup_type="error")
                return
            if not self.process_input(data):
                show_popup(loc.get("error", "Ошибка обработки данных"), popup_type="error")
                return
            if self.last_input_file:
                save_last_input(self.last_input_file, data)
            if close_window:
                self.switch_content_panel("content_apps")
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка ввода: {str(e)}"), popup_type="error")

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода и сбрасывает статусную строку.

        Args:
            event: Событие wxPython.
        """
        try:
            self.clear_input_fields()
            update_status_bar_point_selected(self, None)
            if self.last_input_file:
                save_last_input(self.last_input_file, self.collect_input_data())
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при очистке полей: {str(e)}"), popup_type="error")

    def on_cancel(self, event: wx.Event, switch_content: Optional[str] = "content_apps") -> None:
        """
        Переключает контент на указанную панель (по умолчанию content_apps).

        Args:
            event: Событие wxPython.
            switch_content: Имя контента для переключения.
        """
        self.switch_content_panel(switch_content)

    def collect_input_data(self) -> Dict:
        """
        Собирает данные из полей ввода панели.

        Returns:
            Dict: Словарь с данными из полей ввода.
        """
        return {}

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введённых данных.

        Args:
            data: Словарь с данными из полей ввода.

        Returns:
            bool: True, если данные валидны, иначе False.
        """
        return True

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает собранные данные (например, выполняет расчёты или построение).

        Args:
            data: Словарь с данными из полей ввода.

        Returns:
            bool: True, если обработка успешна, иначе False.
        """
        return True

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода панели.
        """
        pass

    def update_ui_language(self) -> None:
        """
        Обновляет текст элементов интерфейса при смене языка.
        """
        pass


def load_common_data() -> Dict:
    """
    Загружает данные о материалах, толщинах и конфигурации днищ из файлов 'config/common_data.json' и 'config/config.json'
    с кэшированием.

    Returns:
        Dict: Словарь с ключами 'material', 'thicknesses', 'h1_table', 'head_types', 'fields'.
    """
    global _common_data_cache
    if _common_data_cache is not None:
        return _common_data_cache

    _common_data_cache = {
        "material": [],
        "thicknesses": [],
        "h1_table": {},
        "head_types": {},
        "fields": [{}]
    }

    # Загрузка common_data.json
    common_data_path = RESOURCE_DIR / "common_data.json"
    try:
        with common_data_path.open("r", encoding='utf-8') as f:
            data = json.load(f)
            dimensions = data.get("dimensions", {})
            _common_data_cache["material"] = dimensions.get("material", [])
            _common_data_cache["thicknesses"] = dimensions.get("thicknesses", [])
            _common_data_cache["diameters"] = dimensions.get("diameters", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {common_data_path}: {e}")

    # Загрузка config.json
    config_path = RESOURCE_DIR / "config.json"
    try:
        with config_path.open("r", encoding='utf-8') as f:
            config = json.load(f)
            _common_data_cache["h1_table"] = config.get("h1_table", {})
            _common_data_cache["head_types"] = config.get("head_types", {})
            _common_data_cache["fields"] = config.get("fields", [{}])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {config_path}: {e}")

    return _common_data_cache


def reset_common_data_cache() -> None:
    """
    Сбрасывает кэш данных из common_data.json и config.json.
    """
    global _common_data_cache
    _common_data_cache = None


def save_last_position(x: int, y: int) -> None:
    """
    Сохраняет координаты позиции окна в файл 'config/last_position.json'.

    Args:
        x: Координата x окна.
        y: Координата y окна.
    """
    config_path = RESOURCE_DIR / "last_position.json"
    try:
        with config_path.open("w", encoding='utf-8') as f:
            json.dump({"x": x, "y": y}, f, indent=2, ensure_ascii=False)
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {config_path}: {e}")

def load_last_position() -> Tuple[int, int]:
    """
    Загружает координаты последней позиции окна из файла 'config/last_position.json'.

    Returns:
        Tuple[int, int]: Координаты окна (x, y) или (-1, -1) при ошибке или отсутствии файла.
    """
    config_path = RESOURCE_DIR / "last_position.json"
    try:
        with config_path.open("r", encoding='utf-8') as f:
            data = json.load(f)
            return (data.get("x", -1), data.get("y", -1))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {config_path}: {e}")
        return (-1, -1)

def load_last_input(filename: str) -> Dict:
    """
    Загружает последние введённые данные из указанного файла.

    Args:
        filename (str): Имя файла для загрузки (например, 'last_cone_input.json').

    Returns:
        Dict: Словарь с данными или пустой словарь при ошибке.
    """
    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {filename}: {e}")
        return {}


def save_last_input(filename: str, data: Dict) -> None:
    """
    Сохраняет введённые данные в указанный файл.

    Args:
        filename (str): Имя файла для сохранения.
        data (Dict): Словарь с данными.
    """
    try:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename))
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {abs_path}: {e}")


def show_popup(message: str, popup_type: str = "info") -> None:
    """
    Отображает всплывающее окно с сообщением.

    Args:
        message (str): Текст сообщения.
        popup_type (str): Тип сообщения ("info" для информационного, "error" для ошибки).
    """
    title = loc.get(popup_type, popup_type.capitalize())
    style = wx.OK | (wx.ICON_INFORMATION if popup_type == "info" else wx.ICON_ERROR)
    wx.MessageBox(message, title, style)


def get_standard_font() -> wx.Font:
    """
    Возвращает стандартный шрифт на основе конфигурации из user_settings.json.

    Returns:
        wx.Font: Объект шрифта с заданным размером, стилем и именем.
    """
    font_name = get_setting("FONT_NAME") or DEFAULT_SETTINGS["FONT_NAME"]
    font_styles = {
        "normal": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
        "italic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL),
        "bold": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
        "bolditalic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD),
    }
    style, weight = font_styles.get(get_setting("FONT_TYPE").lower(), (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    font_size = int(get_setting("FONT_SIZE") or DEFAULT_SETTINGS["FONT_SIZE"])
    return wx.Font(font_size, wx.FONTFAMILY_DEFAULT, style, weight, faceName=font_name)


def get_button_font() -> wx.Font:
    """
    Возвращает шрифт для кнопок (на 2 пункта больше стандартного).

    Returns:
        wx.Font: Объект шрифта для кнопок.
    """
    font = get_standard_font()
    font_size = int(get_setting("FONT_SIZE") or DEFAULT_SETTINGS["FONT_SIZE"]) + 2
    font.SetPointSize(font_size)
    return font


def get_link_font() -> wx.Font:
    """
    Возвращает шрифт для текстовых ссылок на основе параметров из user_settings.json.

    Returns:
        wx.Font: Шрифт для ссылок.
    """
    style_map = {
        "normal": wx.FONTSTYLE_NORMAL,
        "italic": wx.FONTSTYLE_ITALIC,
        "slant": wx.FONTSTYLE_SLANT
    }
    weight_map = {
        "normal": wx.FONTWEIGHT_NORMAL,
        "bold": wx.FONTWEIGHT_BOLD,
        "light": wx.FONTWEIGHT_LIGHT
    }
    font_style = style_map.get(get_setting("LABEL_FONT_TYPE").lower(), wx.FONTSTYLE_NORMAL)
    font_weight = weight_map.get(get_setting("LABEL_FONT_WEIGHT").lower(), wx.FONTWEIGHT_NORMAL)
    font_size = int(get_setting("LABEL_FONT_SIZE") or DEFAULT_SETTINGS["LABEL_FONT_SIZE"])
    font_name = get_setting("LABEL_FONT_NAME") or DEFAULT_SETTINGS["LABEL_FONT_NAME"]
    return wx.Font(font_size, wx.FONTFAMILY_ROMAN, font_style, font_weight, faceName=font_name)


def fit_text_to_height(ctrl, text: str, max_width: int, max_height: int, font_name: str, style_flags: Dict) -> int:
    """
    Подбирает наибольший размер шрифта, при котором текст помещается по высоте.

    Args:
        ctrl: Виджет для отображения текста.
        text: Текст для измерения.
        max_width: Максимальная ширина текста.
        max_height: Максимальная высота текста.
        font_name: Имя шрифта.
        style_flags: Словарь с параметрами стиля шрифта (style, weight).

    Returns:
        int: Оптимальный размер шрифта.
    """
    font_size = 48
    min_size = 8
    while font_size >= min_size:
        font = wx.Font(
            font_size,
            wx.FONTFAMILY_DEFAULT,
            style_flags.get("style", wx.FONTSTYLE_NORMAL),
            style_flags.get("weight", wx.FONTWEIGHT_NORMAL),
            faceName=font_name,
        )
        ctrl.SetFont(font)
        ctrl.SetLabel(text)
        ctrl.Wrap(max_width)
        dc = wx.ClientDC(ctrl)
        dc.SetFont(font)
        _, text_height = dc.GetMultiLineTextExtent(ctrl.GetLabel())
        if text_height <= max_height:
            return font_size
        font_size -= 1
    return min_size


def parse_float(value: str) -> Optional[float]:
    """Преобразует строку в число, заменяя запятую на точку."""
    try:
        cleaned_value = value.strip().replace(',', '.')
        return float(cleaned_value) if cleaned_value else None
    except ValueError:
        return None


class CanvasPanel(wx.Panel):
    """
    Панель для отображения изображения с поддержкой масштабирования.

    Attributes:
        image: Объект wx.Image или None при ошибке загрузки.
        scaled_bitmap: Кэшированное масштабированное изображение.
    """
    def __init__(self, parent: wx.Window, image_file: str, size: Tuple[int, int] = (600, 400)):
        """
        Инициализирует панель с заданным изображением и размером.

        Args:
            parent: Родительский элемент.
            image_file: Путь к файлу изображения (например, 'shell_image.png').
            size: Размер панели (ширина, высота).
        """
        super().__init__(parent, size=size)
        self.SetBackgroundColour(wx.WHITE)
        self.image = None
        self.scaled_bitmap = None
        if os.path.exists(image_file):
            try:
                self.image = wx.Image(image_file, wx.BITMAP_TYPE_PNG)
                if not self.image.IsOk():
                    raise ValueError("Некорректное изображение")
            except Exception as e:
                logging.error(f"Ошибка загрузки изображения {image_file}: {e}")
                self.image = None
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def on_paint(self, event: wx.Event) -> None:
        """
        Отрисовывает изображение или сообщение об ошибке, если изображение недоступно.

        Args:
            event: Событие отрисовки (wx.EVT_PAINT).
        """
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        width, height = self.GetSize()
        if width <= 0 or height <= 0:
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(loc.get("invalid_size", "Недопустимый размер панели"), width // 2 - 50, height // 2)
            return
        if not self.image or not self.image.IsOk():
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(loc.get("image_not_found", "Изображение не найдено"), width // 2 - 50, height // 2)
            return
        img_width, img_height = self.image.GetWidth(), self.image.GetHeight()
        if img_width <= 0 or img_height <= 0:
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(loc.get("image_not_found", "Изображение не найдено"), width // 2 - 50, height // 2)
            return
        scale = min(width / img_width, height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        if new_width > 0 and new_height > 0:
            try:
                scaled_image = self.image.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
                self.scaled_bitmap = wx.Bitmap(scaled_image)
                x = (width - self.scaled_bitmap.GetWidth()) // 2
                y = (height - self.scaled_bitmap.GetHeight()) // 2
                dc.DrawBitmap(self.scaled_bitmap, x, y)
            except Exception as e:
                logging.error(f"Ошибка масштабирования изображения: {e}")
                dc.SetTextForeground(wx.BLACK)
                dc.DrawText(loc.get("image_error", "Ошибка изображения"), width // 2 - 50, height // 2)

    def on_resize(self, event: wx.Event) -> None:
        """
        Обновляет отображение при изменении размера панели.

        Args:
            event: Событие изменения размера (wx.EVT_SIZE).
        """
        self.Refresh()
        event.Skip()


class BaseInputWindow(wx.Frame):
    """
    Базовый класс для диалоговых окон ввода параметров.

    Обеспечивает унифицированную инициализацию, работу с AutoCAD, обработку событий и сохранение данных.
    """
    def __init__(self, title_key: str, last_input_file: str, window_size: Tuple[int, int] = (1200, 650), parent=None):
        """
        Инициализирует окно с заданным заголовком, файлом данных, размером и родительским окном.

        Args:
            title_key: Ключ локализации для заголовка окна.
            last_input_file: Имя файла для сохранения последних введённых данных.
            window_size: Размер окна (ширина, высота).
            parent: Родительское окно (по умолчанию None).
        """
        title = loc.get(title_key, title_key)
        super().__init__(parent, title=title, style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.common_data = load_common_data()
        self.last_input = load_last_input(last_input_file)
        self.panel = wx.Panel(self)
        background_color = get_setting("BACKGROUND_COLOR") or DEFAULT_SETTINGS["BACKGROUND_COLOR"]
        self.panel.SetBackgroundColour(wx.Colour(background_color))
        self.insert_point = None
        self.adoc = None
        self.model = None
        self.selected_layer = "0"
        self.result = None
        self.buttons = []

        self.CreateStatusBar()
        self.GetStatusBar().SetFieldsCount(2)
        self.GetStatusBar().SetStatusWidths([-1, 250])
        self.GetStatusBar().SetFont(get_standard_font())
        status_text_color = get_setting("STATUS_TEXT_COLOR") or DEFAULT_SETTINGS["STATUS_TEXT_COLOR"]
        self.GetStatusBar().SetForegroundColour(wx.Colour(status_text_color))
        self.SetStatusText(loc.get("point_not_selected", "Точка не выбрана"), 0)
        self.SetStatusText(loc.get("copyright", "Дизайн и разработка: А.Тутубалин © 2025"), 1)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetSize(window_size)
        x, y = load_last_position()
        if x != -1 and y != -1:
            self.SetPosition((x, y))
        else:
            self.Centre()

        cad = ATCadInit()
        self.adoc = cad.document
        self.model = cad.model_space

    def on_cancel(self, event: wx.Event) -> None:
        """
        Отменяет ввод, закрывает окно и восстанавливает родительское окно.

        Args:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        self.result = None
        if self.GetParent():
            self.GetParent().Iconize(False)
            self.GetParent().Raise()
            self.GetParent().SetFocus()
        self.Close()

    def on_close(self, event: wx.Event) -> None:
        """
        Сохраняет позицию окна, закрывает его и восстанавливает родительское окно.

        Args:
            event: Событие закрытия (wx.EVT_CLOSE).
        """
        x, y = self.GetPosition()
        save_last_position(x, y)
        if self.GetParent():
            self.GetParent().Iconize(False)
            self.GetParent().Raise()
            self.GetParent().SetFocus()
        self.Destroy()

    def adjust_button_widths(self) -> None:
        """
        Устанавливает одинаковую ширину для кнопок с учётом локализации текста.
        """
        if not self.buttons:
            return
        button_font = get_button_font()
        max_width = 0
        languages = ['ru', 'de', 'en']
        for button in self.buttons:
            for lang in languages:
                temp_loc = loc.__class__(lang)
                label = temp_loc.get(button.GetLabel(), button.GetLabel())
                dc = wx.ClientDC(button)
                dc.SetFont(button_font)
                width, _ = dc.GetTextExtent(label)
                max_width = max(max_width, width + 20)
        for button in self.buttons:
            _, height = button.GetMinSize()
            button.SetMinSize((max_width, height))

    def on_key_down(self, event: wx.Event) -> None:
        """
        Обрабатывает нажатие клавиши Esc для отмены.

        Args:
            event: Событие клавиатуры (wx.EVT_KEY_DOWN).
        """
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.on_cancel(event)
        event.Skip()

    def on_select_point(self, event: wx.Event) -> None:
        """
        Запрашивает выбор точки вставки в AutoCAD, минимизируя окно на время выбора.

        Args:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        try:
            self.Iconize(True)
            self.insert_point = at_point_input(self.adoc)
            update_status_bar_point_selected(self, self.insert_point)
        except Exception as e:
            show_popup(loc.get("point_selection_error", str(e)), popup_type="error")
            logging.error(f"Ошибка выбора точки: {e}")
        finally:
            self.Iconize(False)
            self.Raise()
            self.SetFocus()

    def update_ui_language(self) -> None:
        """
        Обновляет язык и стили интерфейса окна на основе настроек из user_settings.json.
        """
        title = loc.get(self.GetTitle(), self.GetTitle())
        self.SetTitle(title)
        background_color = get_setting("BACKGROUND_COLOR") or DEFAULT_SETTINGS["BACKGROUND_COLOR"]
        self.panel.SetBackgroundColour(wx.Colour(background_color))
        self.GetStatusBar().SetFont(get_standard_font())
        status_text_color = get_setting("STATUS_TEXT_COLOR") or DEFAULT_SETTINGS["STATUS_TEXT_COLOR"]
        self.GetStatusBar().SetForegroundColour(wx.Colour(status_text_color))
        self.SetStatusText(loc.get("point_not_selected", "Точка не выбрана"), 0)
        self.SetStatusText(loc.get("copyright", "Дизайн и разработка: А.Тутубалин © 2025"), 1)
        apply_styles_to_panel(self.panel)
        self.adjust_button_widths()
        self.Layout()
        self.Refresh()


def create_window(window_class, parent=None) -> Optional[Dict]:
    """
    Создаёт и отображает диалоговое окно для ввода параметров.

    Args:
        window_class: Класс окна (например, ConeInputWindow, ShellInputWindow и т.д.).
        parent: Родительское окно (например, MainWindow).

    Returns:
        Optional[Dict]: Данные из диалога или None при отмене.
    """
    window = window_class(parent=parent)
    window.Show()
    window.Iconize(False)
    window.Raise()
    return window.result


def apply_styles_recursively(widget: wx.Window) -> None:
    """
    Рекурсивно применяет стили к виджету и его дочерним элементам.
    Поддерживает wx.StaticText, wx.TextCtrl, wx.ComboBox, wx.RadioButton, wx.StaticBox.

    Args:
        widget: Виджет для стилизации.
    """
    if isinstance(widget, wx.StaticText):
        style_label(widget)
    elif isinstance(widget, wx.TextCtrl):
        style_textctrl(widget)
    elif isinstance(widget, wx.ComboBox):
        style_combobox(widget)
    elif isinstance(widget, wx.RadioButton):
        style_radiobutton(widget)
    elif isinstance(widget, wx.StaticBox):
        style_staticbox(widget)
    for child in widget.GetChildren():
        apply_styles_recursively(child)


def apply_styles_to_panel(panel: wx.Window) -> None:
    """
    Применяет стили ко всем элементам внутри заданной панели.

    Args:
        panel: Панель для стилизации.
    """
    apply_styles_recursively(panel)


def create_standard_buttons(parent: wx.Window, on_ok, on_cancel, on_clear=None) -> List[wx.Button]:
    """
    Создаёт стандартные кнопки (OK, Cancel, Clear) с привязкой событий.

    Args:
        parent: Родительский элемент.
        on_ok: Обработчик для кнопки OK.
        on_cancel: Обработчик для кнопки Cancel.
        on_clear: Обработчик для кнопки Clear (опционально, если None, кнопка не создаётся).

    Returns:
        List[wx.Button]: Список кнопок [ok_button, cancel_button, clear_button] (clear_button опционально).
    """
    button_font = get_button_font()
    button_color = get_setting("BUTTON_FONT_COLOR") or DEFAULT_SETTINGS["BUTTON_FONT_COLOR"]

    ok_button = wx.Button(parent, label=loc.get("ok_button"))
    ok_button.SetFont(button_font)
    ok_button.SetBackgroundColour(wx.Colour(0, 128, 0))
    ok_button.SetForegroundColour(wx.Colour(button_color))
    ok_button.Bind(wx.EVT_BUTTON, on_ok)

    clear_button = None
    if on_clear:
        clear_button = wx.Button(parent, label=loc.get("clear_button"))
        clear_button.SetFont(button_font)
        clear_button.SetBackgroundColour(wx.Colour(64, 64, 64))
        clear_button.SetForegroundColour(wx.Colour(button_color))
        clear_button.Bind(wx.EVT_BUTTON, on_clear)

    cancel_button = wx.Button(parent, label=loc.get("cancel_button"))
    cancel_button.SetFont(button_font)
    cancel_button.SetBackgroundColour(wx.Colour(255, 0, 0))
    cancel_button.SetForegroundColour(wx.Colour(button_color))
    cancel_button.Bind(wx.EVT_BUTTON, on_cancel)

    buttons = [ok_button, cancel_button]
    if clear_button:
        buttons.insert(1, clear_button)
    return buttons


def adjust_button_widths(buttons: List[wx.Button]) -> None:
    """
    Устанавливает одинаковую ширину для переданных кнопок с учётом локализации текста.

    Args:
        buttons: Список кнопок для стилизации.
    """
    if not buttons:
        return
    button_font = get_button_font()
    max_width = 0
    languages = ['ru', 'de', 'en']
    for button in buttons:
        for lang in languages:
            temp_loc = loc.__class__(lang)
            label = temp_loc.get(button.GetLabel(), button.GetLabel())
            dc = wx.ClientDC(button)
            dc.SetFont(button_font)
            width, _ = dc.GetTextExtent(label)
            max_width = max(max_width, width + 20)
    for button in buttons:
        _, height = button.GetMinSize()
        button.SetMinSize((max_width, height))


def update_status_bar_point_selected(window: wx.Window, insert_point: Optional[object] = None) -> None:
    """
    Обновляет статусную строку окна с координатами выбранной точки.

    Args:
        window: Окно или панель, содержащее строку состояния.
        insert_point: Объект точки с атрибутами x, y (например, APoint).
    """
    main_window = wx.GetTopLevelParent(window)
    if hasattr(main_window, "GetStatusBar") and main_window.GetStatusBar():
        if insert_point and hasattr(insert_point, "x") and hasattr(insert_point, "y"):
            try:
                point_text = loc.get("point_selected", "Точка выбрана: x={0}, y={1}").format(insert_point.x, insert_point.y)
                main_window.GetStatusBar().SetStatusText(point_text, 0)
            except Exception as e:
                main_window.GetStatusBar().SetStatusText(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), 0)
                logging.error(f"Ошибка при обновлении строки состояния: {e}")
        else:
            main_window.GetStatusBar().SetStatusText(loc.get("point_not_selected", "Точка не выбрана"), 0)


if __name__ == "__main__":
    """
    Тестовый блок для проверки работоспособности модуля.
    Создаёт окно на основе BaseInputWindow с панелью, кнопками и проверяет локализацию, шрифты и сохранение позиции.
    """
    from config.at_config import LAST_CONE_INPUT_FILE  # Добавьте импорт LAST_CONE_INPUT_FILE

    app = wx.App()

    # Используем BaseInputWindow для тестового окна
    frame = BaseInputWindow(
        title_key="test_window",
        last_input_file=str(LAST_CONE_INPUT_FILE),  # Используем существующий файл из at_config.py
        window_size=(800, 600)
    )
    panel = BaseContentPanel(frame.panel)
    sizer = wx.BoxSizer(wx.VERTICAL)

    # Тест шрифтов и стилизации
    label = wx.StaticText(panel, label=loc.get("test_label", "Тестовый текст"))
    style_label(label)
    sizer.Add(label, 0, wx.ALL, 10)


    # Тест кнопок
    def on_ok(event):
        show_popup(loc.get("info", "Кнопка ОК нажата"), popup_type="info")


    def on_cancel(event):
        frame.on_cancel(event)


    buttons = create_standard_buttons(panel, on_ok, on_cancel)
    frame.buttons = buttons  # Сохраняем кнопки для adjust_button_widths
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    for button in buttons:
        button_sizer.Add(button, 0, wx.ALL, 5)
    adjust_button_widths(buttons)
    sizer.Add(button_sizer, 0, wx.ALL | wx.CENTER, 10)

    # Тест панели с изображением
    test_image = str(ICON_PATH)
    canvas = CanvasPanel(panel, test_image, size=(200, 150))
    sizer.Add(canvas, 0, wx.ALL | wx.CENTER, 10)

    panel.SetSizer(sizer)
    # Исправляем создание сайзера для frame.panel
    main_sizer = wx.BoxSizer(wx.VERTICAL)
    main_sizer.Add(panel, 1, wx.EXPAND)
    frame.panel.SetSizer(main_sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
