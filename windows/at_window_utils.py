"""
Файл: at_window_utils.py
Путь: windows\at_window_utils.py

Описание:
Модуль с утилитами для главного окна AT-CAD.
Содержит функции для работы с позицией окна, всплывающими окнами, шрифтами и стилизацией интерфейса.
Все настройки (FONT_NAME, FONT_TYPE, FONT_SIZE, BACKGROUND_COLOR и т.д.) читаются из user_settings.json
через get_setting.
"""

import os
import json
import logging
import time
from typing import Tuple, Dict, Optional, List
import wx
from config.at_config import get_setting, DEFAULT_SETTINGS
from locales.at_localization_class import loc
from programms.at_base import init_autocad
from programms.at_input import at_point_input
from windows.at_style import style_textctrl, style_combobox, style_radiobutton, style_staticbox, style_label

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Изменено на INFO для более подробного логирования
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Кэш для данных из JSON-файлов
_common_data_cache = None

def load_common_data() -> Dict:
    """
    Загружает данные о материалах, толщинах и конфигурации днищ из файлов 'config/common_data.json' и 'config/config.json'
    с кэшированием.

    Возвращает:
        Dict: Словарь с ключами 'material', 'thicknesses', 'h1_table', 'head_types', 'fields'.

    Исключения:
        FileNotFoundError: Если файлы 'config/common_data.json' или 'config/config.json' отсутствуют.
        json.JSONDecodeError: Если файлы содержат некорректный JSON.
        ValueError: Если структура JSON некорректна (например, отсутствует ключ 'dimensions').
    """
    global _common_data_cache
    if _common_data_cache is not None:
        logging.debug("Использование кэшированных данных из common_data.json и config.json")
        return _common_data_cache

    _common_data_cache = {
        "material": [],
        "thicknesses": [],
        "h1_table": {},
        "head_types": {},
        "fields": [{}]
    }

    # Загрузка common_data.json
    common_data_path = os.path.join("config", "common_data.json")
    try:
        with open(common_data_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            logging.info(f"Сырые данные из {common_data_path}: {data}")
            if not isinstance(data.get("dimensions"), dict):
                raise ValueError("Некорректная структура common_data.json: отсутствует ключ 'dimensions'")
            dimensions = data.get("dimensions", {})
            _common_data_cache["material"] = dimensions.get("material", []) if isinstance(
                dimensions.get("material"), list) else []
            _common_data_cache["thicknesses"] = dimensions.get("thicknesses", []) if isinstance(
                dimensions.get("thicknesses"), list) else []
            # Валидация толщин
            for t in _common_data_cache["thicknesses"]:
                try:
                    float(t)
                except ValueError:
                    logging.error(f"Недопустимое значение толщины в common_data.json: {t}")
                    show_popup(loc.get("invalid_thickness", f"Недопустимое значение толщины: {t}"), popup_type="error")
                    _common_data_cache["thicknesses"] = []
                    break
        logging.info(f"Данные успешно загружены из {common_data_path}: материалы={_common_data_cache['material']}, "
                     f"толщины={_common_data_cache['thicknesses']}")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error(f"Ошибка загрузки {common_data_path}: {e}")
        _common_data_cache["material"] = []
        _common_data_cache["thicknesses"] = []

    # Загрузка config.json
    config_path = os.path.join("config", "config.json")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            config = json.load(f)
            logging.info(f"Сырые данные из {config_path}: {config}")
            _common_data_cache["h1_table"] = config.get("h1_table", {}) if isinstance(
                config.get("h1_table"), dict) else {}
            _common_data_cache["head_types"] = config.get("head_types", {}) if isinstance(
                config.get("head_types"), dict) else {}
            _common_data_cache["fields"] = config.get("fields", [{}]) if isinstance(
                config.get("fields"), list) else [{}]
        logging.info(f"Данные успешно загружены из {config_path}: h1_table={_common_data_cache['h1_table']}, "
                     f"head_types={_common_data_cache['head_types']}, fields={_common_data_cache['fields']}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {config_path}: {e}")
        _common_data_cache["h1_table"] = {}
        _common_data_cache["head_types"] = {}
        _common_data_cache["fields"] = [{}]

    return _common_data_cache

def reset_common_data_cache() -> None:
    """
    Сбрасывает кэш данных из common_data.json и config.json.
    """
    global _common_data_cache
    _common_data_cache = None
    logging.info("Кэш common_data.json и config.json сброшен")

def load_last_position() -> Tuple[int, int]:
    """
    Загружает координаты последней позиции окна из файла 'config/last_position.json'.

    Возвращает:
        Tuple[int, int]: Координаты окна (x, y) или (-1, -1) при ошибке или отсутствии файла.
    """
    config_path = os.path.join("config", "last_position.json")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            return (data.get("x", -1), data.get("y", -1))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {config_path}: {e}")
        return (-1, -1)

def save_last_position(x: int, y: int) -> None:
    """
    Сохраняет координаты позиции окна в файл 'config/last_position.json'.

    Аргументы:
        x: Координата x окна.
        y: Координата y окна.
    """
    config_path = os.path.join("config", "last_position.json")
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump({"x": x, "y": y}, f, indent=2, ensure_ascii=False)
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {config_path}: {e}")

def load_last_input(filename: str) -> Dict:
    """
    Загружает последние введённые данные из указанного файла.

    Аргументы:
        filename: Имя файла для загрузки (например, 'last_cone_input.json').

    Возвращает:
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

    Аргументы:
        filename: Имя файла для сохранения.
        data: Словарь с данными.
    """
    try:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename))
        logging.info(f"Попытка сохранить данные в абсолютный путь: {abs_path}")
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"Данные успешно сохранены в {abs_path}: {data}")
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {abs_path}: {e}")

def show_popup(message: str, popup_type: str = "info") -> None:
    """
    Отображает всплывающее окно с сообщением.

    Аргументы:
        message: Текст сообщения.
        popup_type: Тип сообщения ("info" для информационного, "error" для ошибки).
    """
    style = wx.OK | (wx.ICON_INFORMATION if popup_type == "info" else wx.ICON_ERROR)
    wx.MessageBox(message, loc.get("error" if popup_type == "error" else "info"), style)

def get_standard_font() -> wx.Font:
    """
    Возвращает стандартный шрифт на основе конфигурации из user_settings.json.

    Возвращает:
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
    return wx.Font(
        int(get_setting("FONT_SIZE") or DEFAULT_SETTINGS["FONT_SIZE"]),
        wx.FONTFAMILY_DEFAULT,
        style,
        weight,
        faceName=font_name
    )

def get_button_font() -> wx.Font:
    """
    Возвращает шрифт для кнопок (на 2 пункта больше стандартного).

    Возвращает:
        wx.Font: Объект шрифта для кнопок.
    """
    font = get_standard_font()
    font.SetPointSize(int(get_setting("FONT_SIZE") or DEFAULT_SETTINGS["FONT_SIZE"]) + 2)
    return font

def get_link_font() -> wx.Font:
    """
    Возвращает шрифт для текстовых ссылок на основе параметров из user_settings.json.

    Возвращает:
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

    return wx.Font(
        pointSize=int(get_setting("LABEL_FONT_SIZE") or DEFAULT_SETTINGS["LABEL_FONT_SIZE"]),
        family=wx.FONTFAMILY_ROMAN,
        style=font_style,
        weight=font_weight,
        faceName=get_setting("LABEL_FONT_NAME") or DEFAULT_SETTINGS["LABEL_FONT_NAME"]
    )

def fit_text_to_height(ctrl, text, max_width, max_height, font_name, style_flags):
    """
    Подбирает наибольший размер шрифта, при котором текст помещается по высоте.

    Аргументы:
        ctrl: Виджет для отображения текста.
        text: Текст для измерения.
        max_width: Максимальная ширина текста.
        max_height: Максимальная высота текста.
        font_name: Имя шрифта.
        style_flags: Словарь с параметрами стиля шрифта (style, weight).

    Возвращает:
        int: Оптимальный размер шрифта.
    """
    font_size = 48  # начнем с большого размера
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
            return font_size  # нашли подходящий размер

        font_size -= 1  # уменьшаем и пробуем снова

    return min_size  # минимально допустимый

class CanvasPanel(wx.Panel):
    """
    Панель для отображения изображения с поддержкой масштабирования.

    Атрибуты:
        image: Объект wx.Image или None при ошибке загрузки.
        scaled_bitmap: Кэшированное масштабированное изображение.
    """

    def __init__(self, parent: wx.Window, image_file: str, size: Tuple[int, int] = (600, 400)):
        """
        Инициализирует панель с заданным изображением и размером.

        Аргументы:
            parent: Родительский элемент (wx.Window).
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
        else:
            logging.error(f"Файл изображения {image_file} не найден")
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def on_paint(self, event: wx.Event) -> None:
        """
        Отрисовывает изображение или сообщение об ошибке, если изображение недоступно.

        Аргументы:
            event: Событие отрисовки (wx.EVT_PAINT).
        """
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.WHITE_BRUSH)
        dc.Clear()
        width, height = self.GetSize()
        if self.image and self.image.IsOk():
            if not self.scaled_bitmap or self.scaled_bitmap.GetSize() != (width, height):
                img_width, img_height = self.image.GetWidth(), self.image.GetHeight()
                scale = min(width / img_width, height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                scaled_image = self.image.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
                self.scaled_bitmap = wx.Bitmap(scaled_image)
            x = (width - self.scaled_bitmap.GetWidth()) // 2
            y = (height - self.scaled_bitmap.GetHeight()) // 2
            dc.DrawBitmap(self.scaled_bitmap, x, y)
        else:
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText(loc.get("image_not_found"), width // 2 - 50, height // 2)

    def on_resize(self, event: wx.Event) -> None:
        """
        Обновляет отображение при изменении размера панели.

        Аргументы:
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

        Аргументы:
            title_key: Ключ локализации для заголовка окна.
            last_input_file: Имя файла для сохранения последних введённых данных.
            window_size: Размер окна (ширина, высота).
            parent: Родительское окно (по умолчанию None).

        Исключения:
            RuntimeError: Если инициализация AutoCAD не удалась.
        """
        super().__init__(parent, title=loc.get(title_key),
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.common_data = load_common_data()
        self.last_input = load_last_input(last_input_file)
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(get_setting("BACKGROUND_COLOR") or DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        self.insert_point = None
        self.adoc = None
        self.model = None
        self.selected_layer = "0"
        self.result = None
        self.buttons = []

        self.CreateStatusBar()
        self.GetStatusBar().SetFieldsCount(2)
        self.GetStatusBar().SetStatusWidths([-1, 250])
        self.SetStatusText(loc.get("point_not_selected"), 0)
        self.SetStatusText(loc.get("copyright"), 1)
        font = get_standard_font()
        self.GetStatusBar().SetFont(font)
        self.GetStatusBar().SetForegroundColour(wx.Colour(get_setting("STATUS_TEXT_COLOR") or DEFAULT_SETTINGS["STATUS_TEXT_COLOR"]))
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetSize(window_size)
        self.SetMinSize(window_size)
        self.SetMaxSize(window_size)

        x, y = load_last_position()
        if x != -1 and y != -1:
            self.SetPosition((x, y))
        else:
            self.Centre()

        try:
            init_result = init_autocad()
            if not init_result:
                show_popup(loc.get("cad_init_error_short"), popup_type="error")
                logging.error("Не удалось инициализировать AutoCAD")
                self.Destroy()
                return
            self.adoc, self.model, _ = init_result
        except Exception as e:
            show_popup(loc.get("cad_init_error_short"), popup_type="error")
            logging.error(f"Ошибка инициализации AutoCAD: {e}")
            self.Destroy()

    def on_cancel(self, event: wx.Event) -> None:
        """
        Отменяет ввод, закрывает окно и восстанавливает родительское окно.

        Аргументы:
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

        Аргументы:
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
                label = temp_loc.get(button.GetLabel())
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

        Аргументы:
            event: Событие клавиатуры (wx.EVT_KEY_DOWN).
        """
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.on_cancel(event)
        event.Skip()

    def on_select_point(self, event: wx.Event) -> None:
        """
        Запрашивает выбор точки вставки в AutoCAD, минимизируя окно на время выбора.

        Аргументы:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        try:
            self.Iconize(True)
            self.insert_point = at_point_input(self.adoc)
            update_status_bar_point_selected(self, self.insert_point)
        except Exception as e:
            show_popup(loc.get("point_selection_error", str(e)), popup_type="error")
            logging.error(f"Ошибка выбора точки: {e}")
            update_status_bar_point_selected(self, None)
        finally:
            self.Iconize(False)
            self.Raise()
            self.SetFocus()
            wx.Yield()
            time.sleep(0.1)

    def update_ui_language(self) -> None:
        """
        Обновляет язык и стили интерфейса окна на основе настроек из user_settings.json.
        """
        self.SetTitle(loc.get(self.GetTitle()))  # Обновляем заголовок
        self.panel.SetBackgroundColour(wx.Colour(get_setting("BACKGROUND_COLOR") or DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        font = get_standard_font()
        self.GetStatusBar().SetFont(font)
        self.GetStatusBar().SetForegroundColour(wx.Colour(get_setting("STATUS_TEXT_COLOR") or DEFAULT_SETTINGS["STATUS_TEXT_COLOR"]))
        self.SetStatusText(loc.get("point_not_selected"), 0)
        self.SetStatusText(loc.get("copyright"), 1)
        apply_styles_to_panel(self.panel)
        self.adjust_button_widths()
        self.Layout()
        self.Refresh()

def create_window(window_class, parent=None) -> Optional[Dict]:
    """
    Создаёт и отображает диалоговое окно для ввода параметров.

    Аргументы:
        window_class: Класс окна (например, ConeInputWindow, ShellInputWindow и т.д.).
        parent: Родительское окно (например, MainWindow).

    Возвращает:
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

    Аргументы:
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

    Аргументы:
        panel: Панель для стилизации.
    """
    apply_styles_recursively(panel)

def create_standard_buttons(parent: wx.Window, on_ok, on_cancel, on_clear=None) -> List[wx.Button]:
    """
    Создаёт стандартные кнопки (OK, Cancel, Clear) с привязкой событий.

    Аргументы:
        parent: Родительский элемент (wx.Window).
        on_ok: Обработчик для кнопки OK.
        on_cancel: Обработчик для кнопки Cancel.
        on_clear: Обработчик для кнопки Clear (опционально, если None, кнопка не создаётся).

    Возвращает:
        List[wx.Button]: Список кнопок [ok_button, cancel_button, clear_button] (clear_button опционально).
    """
    button_font = get_button_font()

    ok_button = wx.Button(parent, label=loc.get("ok_button"))
    ok_button.SetFont(button_font)
    ok_button.SetBackgroundColour(wx.Colour(0, 128, 0))
    ok_button.SetForegroundColour(wx.Colour(get_setting("BUTTON_FONT_COLOR") or DEFAULT_SETTINGS["BUTTON_FONT_COLOR"]))
    ok_button.Bind(wx.EVT_BUTTON, on_ok)

    clear_button = None
    if on_clear:
        clear_button = wx.Button(parent, label=loc.get("clear_button"))
        clear_button.SetFont(button_font)
        clear_button.SetBackgroundColour(wx.Colour(64, 64, 64))  # Тёмно-серый цвет
        clear_button.SetForegroundColour(wx.Colour(get_setting("BUTTON_FONT_COLOR") or DEFAULT_SETTINGS["BUTTON_FONT_COLOR"]))
        clear_button.Bind(wx.EVT_BUTTON, on_clear)

    cancel_button = wx.Button(parent, label=loc.get("cancel_button"))
    cancel_button.SetFont(button_font)
    cancel_button.SetBackgroundColour(wx.Colour(255, 0, 0))
    cancel_button.SetForegroundColour(wx.Colour(get_setting("BUTTON_FONT_COLOR") or DEFAULT_SETTINGS["BUTTON_FONT_COLOR"]))
    cancel_button.Bind(wx.EVT_BUTTON, on_cancel)

    buttons = [ok_button, cancel_button]
    if clear_button:
        buttons.insert(1, clear_button)

    return buttons

def adjust_button_widths(buttons: List[wx.Button]) -> None:
    """
    Устанавливает одинаковую ширину для переданных кнопок с учётом локализации текста.

    Аргументы:
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
            label = temp_loc.get(button.GetLabel())
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

    Аргументы:
        window: Окно или панель, содержащее строку состояния.
        insert_point: Объект точки с атрибутами x, y (например, APoint).
    """
    main_window = wx.GetTopLevelParent(window)
    if hasattr(main_window, "status_text"):
        if insert_point and hasattr(insert_point, "x") and hasattr(insert_point, "y"):
            try:
                main_window.status_text.SetLabel(
                    loc.get("point_selected").format(insert_point.x, insert_point.y)
                )
            except Exception as e:
                logging.error(f"Ошибка при обновлении строки состояния: {e}")
                main_window.status_text.SetLabel(
                    loc.get("point_selection_error", "Ошибка выбора точки")
                )
        else:
            main_window.status_text.SetLabel(
                loc.get("point_not_selected",
                        "Точка не определена, выберите точку или нажмите Отмена для выхода в главное окно")
            )
    else:
        logging.warning("Строка состояния (status_text) не доступна в главном окне")
