"""
Файл: windows/content_cone.py
Описание:
Модуль для создания панели ввода параметров развертки конуса.
Обеспечивает интерфейс для ввода данных конуса с валидацией, вызовом функции выбора точки
и возвратом словаря с данными через callback. Локализация через словарь TRANSLATIONS,
регистрируемый в loc. Настройки из user_settings.json. Сохраняет указанные данные
(order_number, material, thickness, weld_allowance) в last_cone_input.json для использования
в качестве начальных значений. Изображение конуса отображается с помощью CanvasPanel слева,
кнопки под изображением, поля ввода справа. Поддерживает автоматический пересчёт параметров
высоты, наклона и угла с использованием debounce.

Особенности:
- Выход из окна конуса происходит только по кнопке "Возврат" (переключение на content_apps).
- При нажатии "ОК" данные передаются через callback, после чего очищаются поля, не сохраняемые
  в last_cone_input.json, и окно остаётся открытым.
- Исправлена ошибка "wrapped C/C++ object of type TextCtrl has been deleted" путём проверки
  состояния окна перед очисткой полей и отложенного вызова clear_input_fields.
"""

import logging
import math
import os
import json
from typing import Optional, Dict

import wx
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from config.at_config import *
from config.at_last_input import save_last_input
from locales.at_translations import loc
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from programms.at_input import at_point_input
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, parse_float
)

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "main_data_label": {
        "ru": "Основные данные",
        "de": "Hauptdaten",
        "en": "Main Data"
    },
    "diameter_label": {
        "ru": "Диаметры",
        "de": "Durchmesser",
        "en": "Diameters"
    },
    "height_label": {
        "ru": "Высота",
        "de": "Höhe",
        "en": "Height"
    },
    "order_label": {
        "ru": "К-№",
        "de": "Auftragsnummer",
        "en": "Order No."
    },
    "material_label": {
        "ru": "Материал",
        "de": "Material",
        "en": "Material"
    },
    "thickness_label": {
        "ru": "Толщина",
        "de": "Dicke",
        "en": "Thickness"
    },
    "d_label": {
        "ru": "d, мм",
        "de": "d, mm",
        "en": "d, mm"
    },
    "D_label": {
        "ru": "D, мм",
        "de": "D, mm",
        "en": "D, mm"
    },
    "inner_label": {
        "ru": "Внутренний",
        "de": "Innen",
        "en": "Inner"
    },
    "middle_label": {
        "ru": "Средний",
        "de": "Mittel",
        "en": "Middle"
    },
    "outer_label": {
        "ru": "Внешний",
        "de": "Außen",
        "en": "Outer"
    },
    "height_label_mm": {
        "ru": "H, мм",
        "de": "H, mm",
        "en": "H, mm"
    },
    "steigung_label": {
        "ru": "Наклон",
        "de": "Neigung",
        "en": "Slope"
    },
    "angle_label": {
        "ru": "α°",
        "de": "α°",
        "en": "α°"
    },
    "weld_allowance_label": {
        "ru": "Припуск на сварку, мм",
        "de": "Schweißnahtzugabe, mm",
        "en": "Weld Allowance, mm"
    },
    "ok_button": {
        "ru": "ОК",
        "de": "OK",
        "en": "OK"
    },
    "clear_button": {
        "ru": "Очистить",
        "de": "Zurücksetzen",
        "en": "Clear"
    },
    "cancel_button": {
        "ru": "Возврат",
        "de": "Zurück",
        "en": "Return"
    },
    "no_data_error": {
        "ru": "Необходимо заполнить все обязательные поля",
        "de": "Alle Pflichtfelder müssen ausgefüllt werden",
        "en": "All mandatory fields must be filled"
    },
    "invalid_number_format_error": {
        "ru": "Неверный формат числа",
        "de": "Ungültiges Zahlenformat",
        "en": "Invalid number format"
    },
    "diameter_positive_error": {
        "ru": "Диаметры должны быть положительными",
        "de": "Durchmesser müssen positiv sein",
        "en": "Diameters must be positive"
    },
    "thickness_positive_error": {
        "ru": "Толщина должна быть положительной",
        "de": "Dicke muss positiv sein",
        "en": "Thickness must be positive"
    },
    "height_positive_error": {
        "ru": "Высота должна быть положительной",
        "de": "Höhe muss positiv sein",
        "en": "Height must be positive"
    },
    "weld_allowance_non_negative_error": {
        "ru": "Припуск на сварку не может быть отрицательным",
        "de": "Schweißnahtzugabe darf nicht negativ sein",
        "en": "Weld allowance cannot be negative"
    },
    "angle_range_error": {
        "ru": "Угол должен быть в диапазоне 0–180°",
        "de": "Winkel muss im Bereich 0–180° liegen",
        "en": "Angle must be in the range 0–180°"
    },
    "steigung_positive_error": {
        "ru": "Наклон должен быть положительным",
        "de": "Neigung muss positiv sein",
        "en": "Slope must be positive"
    },
    "point_selection_error": {
        "ru": "Ошибка выбора точки",
        "de": "Fehler bei der Punktauswahl",
        "en": "Point selection error"
    },
    "cad_init_error": {
        "ru": "Ошибка инициализации AutoCAD",
        "de": "Fehler bei der Initialisierung von AutoCAD",
        "en": "AutoCAD initialization error"
    },
    "diameter_adjusted_negative_error": {
        "ru": "Скорректированный диаметр не может быть отрицательным",
        "de": "Der angepasste Durchmesser darf nicht negativ sein",
        "en": "Adjusted diameter cannot be negative"
    },
    "window_destroyed_error": {
        "ru": "Окно было закрыто во время обработки",
        "de": "Das Fenster wurde während der Verarbeitung geschlossen",
        "en": "The window was closed during processing"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Изменено на INFO для более подробной отладки
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров конуса.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров конуса или None при ошибке.
    """
    try:
        panel = ConeContentPanel(parent)
        logging.info("Панель ConeContentPanel создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания ConeContentPanel: {e}")
        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        return None


class ConeContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров развертки конуса.
    """

    def __init__(self, parent, callback=None):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
            callback: Функция обратного вызова для передачи данных.
        """
        super().__init__(parent)
        self.last_input_file = str(LAST_CONE_INPUT_FILE)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None
        self._updating = False
        self._debounce_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)
        self.setup_ui()
        self.load_last_input()
        self.order_input.SetFocus()
        logging.info("ConeContentPanel инициализирована")

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.labels.clear()
        self.static_boxes.clear()
        self.buttons.clear()

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Проверка изображения
        image_path = str(CONE_IMAGE_PATH)
        if not image_path:
            show_popup(
                loc.get("error", "Ошибка") + f": Путь к изображению не указан",
                popup_type="error"
            )

        # Изображение конуса
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

        # Загрузка данных
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[
            0] if thickness_options else ""

        # Группа "Основные данные"
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        self.static_boxes["main_data"] = main_data_box

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        order_label.SetFont(font)
        self.labels["order"] = order_label
        self.order_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
        self.order_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
        self.detail_input.SetFont(font)
        order_sizer.Add(self.detail_input, 0, wx.RIGHT, 5)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Материал
        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        material_label.SetFont(font)
        self.labels["material"] = material_label
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                         value=material_options[0] if material_options else "", style=wx.CB_DROPDOWN,
                                         size=INPUT_FIELD_SIZE)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        material_sizer.Add(self.material_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина"))
        thickness_label.SetFont(font)
        self.labels["thickness"] = thickness_label
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options, value=default_thickness,
                                          style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.thickness_combo.SetFont(font)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Диаметры"
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("diameter_label", "Диаметры"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)
        self.static_boxes["diameter"] = diameter_box

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label=loc.get("d_label", "d, мм"))
        d_label.SetFont(font)
        self.labels["d"] = d_label
        self.d_input = wx.TextCtrl(diameter_box, value="", size=INPUT_FIELD_SIZE)
        self.d_input.SetFont(font)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_input, 0, wx.ALL, 5)
        diameter_sizer.Add(d_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Радиокнопки для диаметра вершины
        d_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.d_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.d_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        for rb in [self.d_inner, self.d_middle, self.d_outer]:
            rb.SetFont(font)
        self.d_inner.SetValue(True)
        self.labels["d_inner"] = self.d_inner
        self.labels["d_middle"] = self.d_middle
        self.labels["d_outer"] = self.d_outer
        d_radio_sizer.AddStretchSpacer()
        d_radio_sizer.Add(self.d_inner, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_middle, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(d_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр основания (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(diameter_box, label=loc.get("D_label", "D, мм"))
        D_label.SetFont(font)
        self.labels["D"] = D_label
        self.D_input = wx.TextCtrl(diameter_box, value="", size=INPUT_FIELD_SIZE)
        self.D_input.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_input, 0, wx.ALL, 5)
        diameter_sizer.Add(D_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Радиокнопки для диаметра основания
        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.D_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        for rb in [self.D_inner, self.D_middle, self.D_outer]:
            rb.SetFont(font)
        self.D_inner.SetValue(True)
        self.labels["D_inner"] = self.D_inner
        self.labels["D_middle"] = self.D_middle
        self.labels["D_outer"] = self.D_outer
        D_radio_sizer.AddStretchSpacer()
        D_radio_sizer.Add(self.D_inner, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_middle, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(D_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(diameter_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Высота"
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("height_label", "Высота"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        self.static_boxes["height"] = height_box

        # Высота (H)
        height_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        height_label = wx.StaticText(height_box, label=loc.get("height_label_mm", "H, мм"))
        height_label.SetFont(font)
        self.labels["height"] = height_label
        self.height_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.height_input.SetFont(font)
        height_input_sizer.AddStretchSpacer()
        height_input_sizer.Add(height_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        height_input_sizer.Add(self.height_input, 0, wx.ALL, 5)
        height_sizer.Add(height_input_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Наклон
        steigung_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steigung_label = wx.StaticText(height_box, label=loc.get("steigung_label", "Наклон"))
        steigung_label.SetFont(font)
        self.labels["steigung"] = steigung_label
        self.steigung_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.steigung_input.SetFont(font)
        steigung_sizer.AddStretchSpacer()
        steigung_sizer.Add(steigung_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        steigung_sizer.Add(self.steigung_input, 0, wx.ALL, 5)
        height_sizer.Add(steigung_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Угол
        angle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        angle_label = wx.StaticText(height_box, label=loc.get("angle_label", "α°"))
        angle_label.SetFont(font)
        self.labels["angle"] = angle_label
        self.angle_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.angle_input.SetFont(font)
        angle_sizer.AddStretchSpacer()
        angle_sizer.Add(angle_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        angle_sizer.Add(self.angle_input, 0, wx.ALL, 5)
        height_sizer.Add(angle_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.height_input.Bind(wx.EVT_TEXT, self.on_height_text)
        self.steigung_input.Bind(wx.EVT_TEXT, self.on_steigung_text)
        self.angle_input.Bind(wx.EVT_TEXT, self.on_angle_text)
        self.right_sizer.Add(height_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Припуск на сварку
        allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        allowance_label = wx.StaticText(self, label=loc.get("weld_allowance_label", "Припуск на сварку, мм"))
        allowance_label.SetFont(font)
        self.labels["allowance"] = allowance_label
        self.allowance_combo = wx.ComboBox(self, choices=[str(i) for i in range(11)], value="3", style=wx.CB_READONLY,
                                          size=INPUT_FIELD_SIZE)
        self.allowance_combo.SetFont(font)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALL, 5)
        self.right_sizer.Add(allowance_sizer, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()
        logging.info("Интерфейс ConeContentPanel настроен")

    def load_last_input(self) -> None:
        """
        Загружает последние введённые данные из last_cone_input.json.
        """
        try:
            if os.path.exists(self.last_input_file):
                with open(self.last_input_file, "r", encoding='utf-8') as f:
                    last_input = json.load(f)
                if not self.order_input.IsBeingDeleted():
                    self.order_input.SetValue(last_input.get("order_number", ""))
                if not self.material_combo.IsBeingDeleted():
                    self.material_combo.SetValue(last_input.get("material", self.material_combo.GetValue()))
                if not self.thickness_combo.IsBeingDeleted():
                    self.thickness_combo.SetValue(str(last_input.get("thickness", self.thickness_combo.GetValue())))
                if not self.allowance_combo.IsBeingDeleted():
                    self.allowance_combo.SetValue(str(last_input.get("weld_allowance", "3")))
                logging.info(f"Последние данные загружены из {self.last_input_file}")
            else:
                logging.info(f"Файл {self.last_input_file} не найден, используются значения по умолчанию")
        except Exception as e:
            logging.error(f"Ошибка загрузки {self.last_input_file}: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")

    def clear_input_fields(self) -> None:
        """
        Очищает поля ввода, не сохраняемые в last_cone_input.json.
        Проверяет, что элементы не были уничтожены перед очисткой.
        """
        try:
            if self.IsBeingDeleted():
                logging.warning("Попытка очистки полей в уничтожаемом окне")
                logging.getLogger().handlers[0].flush()
                return
            if not self.detail_input.IsBeingDeleted():
                self.detail_input.SetValue("")
            if not self.d_input.IsBeingDeleted():
                self.d_input.SetValue("")
            if not self.D_input.IsBeingDeleted():
                self.D_input.SetValue("")
            if not self.d_inner.IsBeingDeleted():
                self.d_inner.SetValue(True)
            if not self.D_inner.IsBeingDeleted():
                self.D_inner.SetValue(True)
            if not self.height_input.IsBeingDeleted():
                self.height_input.SetValue("")
            if not self.steigung_input.IsBeingDeleted():
                self.steigung_input.SetValue("")
            if not self.angle_input.IsBeingDeleted():
                self.angle_input.SetValue("")
            self.insert_point = None
            update_status_bar_point_selected(self, None)
            if not self.height_input.IsBeingDeleted():
                self.height_input.Enable(True)
            if not self.steigung_input.IsBeingDeleted():
                self.steigung_input.Enable(True)
            if not self.angle_input.IsBeingDeleted():
                self.angle_input.Enable(True)
            if not self.order_input.IsBeingDeleted():
                self.order_input.SetFocus()
            logging.info(
                "Очищены поля: detail_number, diameter_top, diameter_base, height, steigung, angle, insert_point, d_type, D_type")
            logging.getLogger().handlers[0].flush()
        except Exception as e:
            logging.error(f"Ошибка при очистке полей: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            logging.getLogger().handlers[0].flush()

    def update_ui_language(self) -> None:
        """
        Обновляет текст меток и групп при смене языка.
        Проверяет, что элементы не уничтожены.
        """
        try:
            if self.IsBeingDeleted():
                logging.warning("Попытка обновления языка в уничтожаемом окне")
                return
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["diameter"].SetLabel(loc.get("diameter_label", "Диаметры"))
            self.static_boxes["height"].SetLabel(loc.get("height_label", "Высота"))
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
            self.labels["d"].SetLabel(loc.get("d_label", "d, мм"))
            self.labels["D"].SetLabel(loc.get("D_label", "D, мм"))
            self.labels["d_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
            self.labels["d_middle"].SetLabel(loc.get("middle_label", "Средний"))
            self.labels["d_outer"].SetLabel(loc.get("outer_label", "Внешний"))
            self.labels["D_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
            self.labels["D_middle"].SetLabel(loc.get("middle_label", "Средний"))
            self.labels["D_outer"].SetLabel(loc.get("outer_label", "Внешний"))
            self.labels["height"].SetLabel(loc.get("height_label_mm", "H, мм"))
            self.labels["steigung"].SetLabel(loc.get("steigung_label", "Наклон"))
            self.labels["angle"].SetLabel(loc.get("angle_label", "α°"))
            self.labels["allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку, мм"))

            for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
                if not self.buttons[i].IsBeingDeleted():
                    self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Возврат"][i]))
            adjust_button_widths(self.buttons)

            update_status_bar_point_selected(self, self.insert_point)
            self.Layout()
            logging.info("Язык UI обновлён")
        except Exception as e:
            logging.error(f"Ошибка при обновлении языка UI: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")

    def on_height_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода высоты с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки.

        Args:
            event: Событие wxPython.
        """
        if self._updating or self.IsBeingDeleted():
            return
        self._updating = True
        try:
            height_str = self.height_input.GetValue().strip().replace(',', '.')
            steigung_str = self.steigung_input.GetValue().strip().replace(',', '.')
            angle_str = self.angle_input.GetValue().strip().replace(',', '.')
            d_str = self.d_input.GetValue().strip().replace(',', '.')
            D_str = self.D_input.GetValue().strip().replace(',', '.')

            d = float(d_str) if d_str else 0
            D = float(D_str) if D_str else 1000

            if height_str:
                self.steigung_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    height = float(height_str)
                    if height <= 0:
                        show_popup(loc.get("height_positive_error", "Высота должна быть положительной"),
                                   popup_type="error")
                        return
                    steigung = at_steigung(height, D, d)
                    angle = math.degrees(math.atan2(abs(D - d) / 2, height)) * 2
                    self.steigung_input.SetValue(f"{steigung:.2f}" if steigung is not None else "")
                    self.angle_input.SetValue(f"{angle:.2f}" if angle is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для высоты"),
                               popup_type="error")
            elif steigung_str:
                self.height_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    steigung = float(steigung_str)
                    if steigung <= 0:
                        show_popup(loc.get("steigung_positive_error", "Наклон должен быть положительным"),
                                   popup_type="error")
                        return
                    height = at_cone_height(D, d, steigung=steigung)
                    angle = math.degrees(math.atan2(abs(D - d) / 2, height)) * 2 if height else 0
                    self.height_input.SetValue(f"{height:.2f}" if height is not None else "")
                    self.angle_input.SetValue(f"{angle:.2f}" if angle is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для наклона"),
                               popup_type="error")
            elif angle_str:
                self.height_input.Enable(False)
                self.steigung_input.Enable(False)
                try:
                    angle = float(angle_str)
                    if not 0 < angle < 180:
                        show_popup(loc.get("angle_range_error", "Угол должен быть в диапазоне 0–180°"),
                                   popup_type="error")
                        return
                    height = at_cone_height(D, d, angle=angle)
                    steigung = at_steigung(height, D, d)
                    self.height_input.SetValue(f"{height:.2f}" if height is not None else "")
                    self.steigung_input.SetValue(f"{steigung:.2f}" if steigung is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для угла"),
                               popup_type="error")
            else:
                self.height_input.Enable(True)
                self.steigung_input.Enable(True)
                self.angle_input.Enable(True)
                self.height_input.SetValue("")
                self.steigung_input.SetValue("")
                self.angle_input.SetValue("")
        except Exception as e:
            logging.error(f"Ошибка в расчётах параметров конуса: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        finally:
            self._updating = False

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода, корректируя диаметры и высоту.

        Диаметры:
        - Если диаметр равен 0, заменяется на значение толщины.
        - Если тип диаметра 'outer', вычитается толщина.
        - Если тип диаметра 'inner', прибавляется толщина.
        - Если тип диаметра 'middle', диаметр остаётся без изменений.
        Высота:
        - К высоте прибавляется припуск на сварку.

        Returns:
            Optional[Dict]: Словарь с данными (order_number, detail_number, material, thickness, diameter_top,
            diameter_base, d_type, D_type, height, steigung, angle, weld_allowance, insert_point, thickness_text)
            или None при ошибке.
        """
        try:
            data = {
                "order_number": self.order_input.GetValue().strip(),
                "detail_number": self.detail_input.GetValue().strip(),
                "material": self.material_combo.GetValue().strip(),
                "thickness": parse_float(self.thickness_combo.GetValue()),
                "diameter_top": parse_float(self.d_input.GetValue()) or 0,
                "diameter_base": parse_float(self.D_input.GetValue()) or 0,
                "d_type": "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer",
                "D_type": "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer",
                "height": parse_float(self.height_input.GetValue()),
                "steigung": parse_float(self.steigung_input.GetValue()),
                "angle": parse_float(self.angle_input.GetValue()),
                "weld_allowance": parse_float(self.allowance_combo.GetValue()),
                "insert_point": self.insert_point,
                "thickness_text": f"{parse_float(self.thickness_combo.GetValue()):.2f} {loc.get('mm', 'мм')}" if parse_float(
                    self.thickness_combo.GetValue()) is not None else None
            }

            # Проверка на наличие всех обязательных полей
            if any(data[key] is None for key in ["thickness", "diameter_top", "diameter_base", "height", "weld_allowance"]):
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                return None

            # Замена нулевых диаметров на толщину
            if data["diameter_top"] == 0:
                data["diameter_top"] = data["thickness"]
            if data["diameter_base"] == 0:
                data["diameter_base"] = data["thickness"]

            # Корректировка диаметров с использованием at_diameter
            try:
                data["diameter_top"] = at_diameter(data["diameter_top"], data["thickness"], data["d_type"])
                data["diameter_base"] = at_diameter(data["diameter_base"], data["thickness"], data["D_type"])
            except ValueError as e:
                logging.error(f"Ошибка корректировки диаметров: {str(e)}")
                show_popup(str(e), popup_type="error")
                return None

            # Проверка скорректированных диаметров
            if data["diameter_top"] <= 0 or data["diameter_base"] <= 0:
                show_popup(loc.get("diameter_adjusted_negative_error", "Скорректированный диаметр не может быть отрицательным"), popup_type="error")
                return None

            # Корректировка высоты с учётом припуска на сварку
            data["height"] += data["weld_allowance"]

            return data
        except ValueError as e:
            logging.error(f"Ошибка получения данных: {e}")
            show_popup(loc.get("invalid_number_format_error", "Неверный формат числа"), popup_type="error")
            return None
        except Exception as e:
            logging.error(f"Ошибка в collect_input_data: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            return None

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введённых данных.

        Args:
            data: Словарь с данными из полей ввода (после корректировки).

        Returns:
            bool: True, если данные валидны, иначе False.
        """
        try:
            if not data or any(data[key] is None for key in ["thickness", "diameter_top", "diameter_base", "height"]):
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                return False

            if data["thickness"] <= 0:
                show_popup(loc.get("thickness_positive_error", "Толщина должна быть положительной"), popup_type="error")
                self.thickness_combo.SetFocus()
                return False

            if data["diameter_top"] <= 0 or data["diameter_base"] <= 0:
                show_popup(loc.get("diameter_positive_error", "Диаметры должны быть положительными"), popup_type="error")
                self.d_input.SetFocus() if data["diameter_top"] <= 0 else self.D_input.SetFocus()
                return False

            if data["height"] <= 0:
                show_popup(loc.get("height_positive_error", "Высота должна быть положительной"), popup_type="error")
                self.height_input.SetFocus()
                return False

            if data["weld_allowance"] < 0:
                show_popup(loc.get("weld_allowance_non_negative_error", "Припуск на сварку не может быть отрицательным"), popup_type="error")
                self.allowance_combo.SetFocus()
                return False

            if data["angle"] is not None and (data["angle"] <= 0 or data["angle"] >= 180):
                show_popup(loc.get("angle_range_error", "Угол должен быть в диапазоне 0–180°"), popup_type="error")
                self.angle_input.SetFocus()
                return False

            if data["steigung"] is not None and data["steigung"] <= 0:
                show_popup(loc.get("steigung_positive_error", "Наклон должен быть положительным"), popup_type="error")
                self.steigung_input.SetFocus()
                return False

            if not data["insert_point"]:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                return False

            return True
        except Exception as e:
            logging.error(f"Ошибка валидации данных: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            return False

    def on_ok(self, event: wx.Event) -> None:
        """
        Обрабатывает нажатие кнопки "ОК", запрашивает точку, передаёт данные через callback
        и очищает поля, не сохраняемые в last_cone_input.json, если окно не уничтожено.

        Args:
            event: Событие нажатия кнопки "ОК".
        """
        try:
            if self.IsBeingDeleted():
                logging.warning("Попытка обработки ОК в уничтожаемом окне")
                show_popup(loc.get("window_destroyed_error", "Окно было закрыто во время обработки"),
                           popup_type="error")
                logging.getLogger().handlers[0].flush()  # Принудительная запись лога
                return

            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            cad = ATCadInit()

            if cad.adoc is None:
                logging.error("Не удалось инициализировать AutoCAD")
                show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()
                logging.getLogger().handlers[0].flush()
                return

            point = None
            try:
                point = at_point_input(cad.adoc, as_variant=False,
                                       prompt=loc.get("point_prompt", "Введите точку вставки конуса"))
                if point is None or not (isinstance(point, list) and len(point) == 3):
                    logging.error("Ошибка выбора точки")
                    show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                    main_window.Iconize(False)
                    main_window.Raise()
                    main_window.SetFocus()
                    logging.getLogger().handlers[0].flush()
                    return
            except Exception as e:
                logging.error(f"Ошибка при выборе точки: {e}")
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки") + f": {str(e)}", popup_type="error")
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()
                logging.getLogger().handlers[0].flush()
                return

            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()

            self.insert_point = point
            update_status_bar_point_selected(self, point)

            data = self.collect_input_data()
            if data and self.validate_input(data):
                # Сохраняем указанные поля в last_cone_input.json
                last_input_data = {
                    "order_number": data["order_number"],
                    "material": data["material"],
                    "thickness": data["thickness"],
                    "weld_allowance": data["weld_allowance"]
                }
                save_last_input(self.last_input_file, last_input_data)
                logging.info(f"Данные сохранены в {self.last_input_file}: {last_input_data}")
                logging.getLogger().handlers[0].flush()

                # Проверяем, что окно всё ещё существует перед вызовом callback
                if self.IsBeingDeleted():
                    logging.warning("Окно уничтожено перед вызовом on_submit_callback")
                    show_popup(loc.get("window_destroyed_error", "Окно было закрыто во время обработки"),
                               popup_type="error")
                    logging.getLogger().handlers[0].flush()
                    return

                # Вызываем callback в безопасном контексте
                if self.on_submit_callback:
                    logging.info("Перед вызовом on_submit_callback")
                    try:
                        wx.CallAfter(self.on_submit_callback, data)  # Отложенный вызов callback
                        logging.info("on_submit_callback вызван отложенно")
                    except Exception as e:
                        logging.error(f"Ошибка при вызове on_submit_callback: {e}")
                        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
                        logging.getLogger().handlers[0].flush()
                        return

                # Отложенная очистка полей
                if not self.IsBeingDeleted():
                    wx.CallAfter(self.clear_input_fields)
                    logging.info("Окно конуса остаётся открытым, несохранённые поля будут очищены отложенно")
                else:
                    logging.warning("Окно уничтожено перед очисткой полей")
                logging.getLogger().handlers[0].flush()
            else:
                logging.info("Данные не прошли валидацию, очистка полей не выполняется")
                logging.getLogger().handlers[0].flush()
        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            logging.getLogger().handlers[0].flush()
        finally:
            if not main_window.IsBeingDeleted():
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()
            logging.getLogger().handlers[0].flush()

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает поля ввода, не сохраняемые в last_cone_input.json.

        Args:
            event: Событие нажатия кнопки.
        """
        try:
            self.clear_input_fields()
            logging.info("Поля ввода очищены")
        except Exception as e:
            logging.error(f"Ошибка при очистке полей: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")

    def on_cancel(self, event: wx.Event, switch_content: Optional[str] = "content_apps") -> None:
        """
        Переключает контент на указанную панель (по умолчанию content_apps).

        Args:
            event: Событие нажатия кнопки.
            switch_content: Имя контента для переключения.
        """
        try:
            self.switch_content_panel(switch_content)
            logging.info(f"Переключение на панель {switch_content}")
        except Exception as e:
            logging.error(f"Ошибка при отмене: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и поведения кнопок.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ConeContentPanel", size=(800, 600))
    panel = ConeContentPanel(frame)

    def on_ok_test(data):
        """
        Тестовая функция для обработки callback.
        Симулирует обработку данных и проверяет состояние окна.
        """
        try:
            print("Собранные данные:", data)
            logging.info("Тестовый callback вызван с данными")
            # Симулируем задержку, как в реальной отрисовке
            wx.MilliSleep(100)
            if panel.IsBeingDeleted():
                logging.warning("Окно уничтожено в тестовом callback")
            else:
                logging.info("Окно всё ещё существует после тестового callback")
        except Exception as e:
            print(f"Ошибка в тестовом callback: {e}")
            logging.error(f"Ошибка в тестовом callback: {e}")

    def on_ok_event(event):
        """
        Тестовая функция для обработки нажатия "ОК".
        Проверяет, что данные передаются, поля очищаются, а окно остаётся открытым.
        """
        try:
            panel.on_submit_callback = on_ok_test
            panel.on_ok(event)
            if not panel.IsBeingDeleted():
                print("Поля после нажатия ОК:")
                print(f"detail_number: {panel.detail_input.GetValue()}")
                print(f"diameter_top: {panel.d_input.GetValue()}")
                print(f"diameter_base: {panel.D_input.GetValue()}")
                print(f"height: {panel.height_input.GetValue()}")
                print(f"steigung: {panel.steigung_input.GetValue()}")
                print(f"angle: {panel.angle_input.GetValue()}")
                print(f"insert_point: {panel.insert_point}")
                print(f"d_type: {'inner' if panel.d_inner.GetValue() else 'middle' if panel.d_middle.GetValue() else 'outer'}")
                print(f"D_type: {'inner' if panel.D_inner.GetValue() else 'middle' if panel.D_middle.GetValue() else 'outer'}")
                print("Окно должно остаться открытым")
            else:
                print("Окно уничтожено после нажатия ОК")
                logging.warning("Окно уничтожено в тестовом режиме")
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")
            logging.error(f"Ошибка в тестовом запуске: {e}")

    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_event)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
