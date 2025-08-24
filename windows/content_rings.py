"""
windows/content_rings.py
Модуль для создания панели для ввода параметров колец.
Работает с AutoCAD через win32com.client.
"""

import logging
from typing import Optional, Dict

import wx
import win32com.client

from config.at_config import *
from locales.at_translations import loc
from programms.at_input import at_point_input
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, BaseInputWindow, load_user_settings
)

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "diameter": {"ru": "Диаметр", "de": "Durchmesser", "en": "Diameter"},
    "diameters": {"ru": "Диаметры", "de": "Durchmesser", "en": "Diameters"},
    "diameter_label": {"ru": "Диаметры", "de": "Durchmesser", "en": "Diameters"},
    "diameters_label": {
        "ru": "Диаметры (через запятую)",
        "de": "Durchmesser (durch Kommas getrennt)",
        "en": "Diameters (separated by commas)",
    },
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main data"},
    "no_data_error": {
        "ru": "Необходимо ввести хотя бы один размер",
        "de": "Mindestens eine Abmessung muss eingegeben werden",
        "en": "At least one dimension must be entered",
    },
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "order_label": {"ru": "К-№", "de": "K-Nr.", "en": "K-no."},
    "point_selection_error": {
        "ru": "Ошибка выбора точки: {}. Пожалуйста, повторите ввод или отмените.",
        "de": "Fehler bei der Punktauswahl: {}. Bitte wiederholen Sie die Eingabe oder brechen Sie ab.",
        "en": "Point selection error: {}. Please retry or cancel.",
    },
    "prompt_select_point": {"ru": "Укажите точку: ", "de": "Punkt auswählen: ", "en": "Select point: "},
    "point_selected": {
        "ru": "Точка выбрана: x={0}, y={1}",
        "en": "Point selected: x={0}, y={1}",
        "de": "Punkt ausgewählt: x={0}, y={1}"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# Настройка логирования (только критические ошибки)
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров колец.

    Args:
        parent: Родительский wx.Window (например, content_panel).

    Returns:
        wx.Panel: Панель RingsContentPanel или None при ошибке.
    """
    try:
        return RingsContentPanel(parent)
    except Exception as e:
        logging.error(f"Ошибка создания RingsContentPanel: {e}")
        return None


class RingsContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров колец.
    """

    def __init__(self, parent, on_submit_callback=None):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
            on_submit_callback: Функция обратного вызова для обработки данных (опционально).
        """
        super().__init__(parent)
        self.settings = load_user_settings()
        self.SetBackgroundColour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        self.parent = parent
        self.on_submit_callback = on_submit_callback
        self.labels: Dict[str, wx.StaticText] = {}
        self.static_boxes: Dict[str, wx.StaticBox] = {}
        self.buttons: list[wx.Button] = []
        self.input_point = None  # Единый стиль имени точки
        self._build_ui()
        self.order_input.SetFocus()

    def _build_ui(self) -> None:
        """
        Создаёт компоновку: слева изображение и кнопки, справа поля ввода.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.labels.clear()
        self.static_boxes.clear()
        self.buttons.clear()

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Изображение (из конфига: Path -> str)
        image_path = str(RING_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()

        # Группа "Основные данные"
        main_box = wx.StaticBox(self, label=loc.get("main_data_label", "Основные данные"))
        main_box.SetFont(font)
        self.static_boxes["main_data"] = main_box
        main_data_sizer = wx.StaticBoxSizer(main_box, wx.VERTICAL)

        # К-№
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_box, label=loc.get("order_label", "К-№"))
        order_label.SetFont(font)
        self.labels["order"] = order_label
        self.order_input = wx.TextCtrl(main_box, value="", size=INPUT_FIELD_SIZE)
        self.order_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Диаметры"
        diam_box = wx.StaticBox(self, label=loc.get("diameter_label", "Диаметры"))
        diam_box.SetFont(font)
        self.static_boxes["diameters"] = diam_box
        diameters_sizer = wx.StaticBoxSizer(diam_box, wx.VERTICAL)

        # Ввод диаметров
        di_inp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        di_label = wx.StaticText(diam_box, label=loc.get("diameters_label", "Диаметры (через запятую)"))
        di_label.SetFont(font)
        self.labels["diameters"] = di_label
        self.diameters_input = wx.TextCtrl(diam_box, value="", style=wx.TE_MULTILINE, size=(INPUT_FIELD_SIZE[0], 100))
        self.diameters_input.SetFont(font)
        di_inp_sizer.AddStretchSpacer()
        di_inp_sizer.Add(di_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        di_inp_sizer.Add(self.diameters_input, 0, wx.ALL, 5)
        diameters_sizer.Add(di_inp_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(diameters_sizer, 0, wx.EXPAND | wx.ALL, 10)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()
        self._status_clear()

    def _status_clear(self):
        """Сбрасывает статусную строку (точка не выбрана)."""
        update_status_bar_point_selected(self, None)

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["diameters"].SetLabel(loc.get("diameter_label", "Диаметры"))
        self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
        self.labels["diameters"].SetLabel(loc.get("diameters_label", "Диаметры (через запятую)"))
        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Возврат"][i]))
        adjust_button_widths(self.buttons)
        self._status_clear()
        self.Layout()

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.
        Возвращает словарь с данными: work_number, diameters, input_point.

        Returns:
            Optional[Dict]: Словарь с данными или None при ошибке.
        """
        try:
            diameters_text = self.diameters_input.GetValue().strip()
            diameters: Dict[str, float] = {}
            if diameters_text:
                for i, value in enumerate(diameters_text.split(",")):
                    val = float(value.strip().replace(",", "."))
                    diameters[str(i + 1)] = val

            return {
                "work_number": self.order_input.GetValue().strip(),
                "diameters": diameters,
                "input_point": self.input_point
            }
        except Exception as e:
            logging.error(f"Ошибка получения данных: {e}")
            show_popup(loc.get("error", f"Ошибка: {e}"), popup_type="error")
            return None

    def validate_input(self, data: Dict) -> bool:
        """
        Минимальная проверка UI-уровня: наличие хотя бы одного диаметра и точки.

        Args:
            data: Словарь с данными ввода.

        Returns:
            bool: True, если данные валидны, иначе False.
        """
        if not data or not data.get("diameters"):
            show_popup(loc.get("no_data_error", "Необходимо ввести хотя бы один размер"), popup_type="error")
            return False
        if not data.get("input_point"):
            show_popup(loc.get("point_selection_error", "Ошибка выбора точки").format("None"), popup_type="error")
            return False
        return True

    def on_ok(self, event: wx.Event, close_window: bool = False) -> None:
        """
        Обрабатывает нажатие кнопки OK: запрашивает точку, собирает данные, проверяет и передаёт их через callback.

        Args:
            event: Событие wxPython.
            close_window: Если True, переключает на content_apps после успешной обработки.
        """
        try:
            # Запрос точки через AutoCAD
            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            self.input_point = at_point_input(as_variant=False)  # Возвращаем список [x, y, z]
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            # Собираем данные
            data = self.collect_input_data()
            if not data:
                return

            # Проверяем данные (включая точку)
            if not self.validate_input(data):
                return

            # Вызываем callback, если он есть
            if self.on_submit_callback:
                self.on_submit_callback(data)

            # Переключаем на content_apps, если нужно
            if close_window:
                self.switch_content_panel("content_apps")

        except Exception as e:
            logging.error(f"Ошибка при обработке ввода: {e}")
            show_popup(loc.get("error", f"Ошибка: {e}"), popup_type="error")

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает поля ввода и сбрасывает статусную строку.

        Args:
            event: Событие wxPython.
        """
        self.clear_input_fields()

    def clear_input_fields(self) -> None:
        """
        Очищает поля ввода и сбрасывает выбранную точку.
        """
        self.order_input.SetValue("")
        self.diameters_input.SetValue("")
        self.input_point = None
        self._status_clear()
        self.order_input.SetFocus()

    def on_cancel(self, event: wx.Event, switch_content: Optional[str] = "content_apps") -> None:
        """
        Переключает контент на указанную панель (по умолчанию content_apps).

        Args:
            event: Событие wxPython.
            switch_content: Имя контента для переключения.
        """
        self.switch_content_panel(switch_content)


# -----------------------------
# Тестовый запуск окна
# -----------------------------
if __name__ == "__main__":
    def on_submit(data: Dict):
        """Выводит полученные данные в консоль для проверки."""
        print("Полученные данные:")
        for k, v in data.items():
            print(f"{k}: {v}")

    app = wx.App(False)
    frame = BaseInputWindow(
        title_key="test_rings_window",
        last_input_file=str(LAST_CONE_INPUT_FILE),
        window_size=(900, 600)
    )
    panel = RingsContentPanel(frame.panel, on_submit_callback=on_submit)
    main_sizer = wx.BoxSizer(wx.VERTICAL)
    main_sizer.Add(panel, 1, wx.EXPAND)
    frame.panel.SetSizer(main_sizer)
    frame.Show()
    app.MainLoop()
