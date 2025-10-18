"""
Файл: windows/content_eccentric.py
Описание:
Модуль для создания панели ввода параметров развертки усечённого конуса с одной вертикальной образующей.
Обеспечивает интерфейс для ввода данных конуса с валидацией, вызовом функции выбора точки
и возвратом словаря с данными через callback. Локализация через словарь TRANSLATIONS,
регистрируемый в loc. Настройки из user_settings.json.
Изображение конуса отображается с помощью CanvasPanel слева, кнопки под изображением, поля ввода справа.

Особенности:
- Выход из окна конуса происходит только по кнопке "Возврат" (переключение на content_apps).
- При нажатии "ОК" данные передаются через callback, после чего очищаются поля и окно остаётся открытым.
"""

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
from programs.at_construction import at_diameter, at_cone_height, at_steigung
from programs.at_input import at_point_input
from windows.at_style import style_staticbox, style_combobox, style_label
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, parse_float
)

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "diameter_label": {"ru": "Диаметры", "de": "Durchmesser", "en": "Diameters"},
    "height_label": {"ru": "Высота", "de": "Höhe", "en": "Height"},
    "order_label": {"ru": "К-№", "de": "Auftragsnummer", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина, S", "de": "Dicke, S", "en": "Thickness, S"},
    "d_label": {"ru": "d, мм", "de": "d, mm", "en": "d, mm"},
    "D_label": {"ru": "D, мм", "de": "D, mm", "en": "D, mm"},
    "inner_label": {"ru": "Внутренний", "de": "Innen", "en": "Inner"},
    "middle_label": {"ru": "Средний", "de": "Mittel", "en": "Middle"},
    "outer_label": {"ru": "Внешний", "de": "Außen", "en": "Outer"},
    "height_label_mm": {"ru": "H, мм", "de": "H, mm", "en": "H, mm"},
    "weld_allowance_label": {"ru": "Припуск на сварку, мм", "de": "Schweißnahtzugabe, mm", "en": "Weld Allowance, mm"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "no_data_error": {"ru": "Необходимо заполнить все обязательные поля", "de": "Alle Pflichtfelder müssen ausgefüllt werden", "en": "All mandatory fields must be filled"},
    "invalid_number_format_error": {"ru": "Неверный формат числа", "de": "Ungültiges Zahlenformat", "en": "Invalid number format"},
    "diameter_positive_error": {"ru": "Диаметры должны быть положительными", "de": "Durchmesser müssen positiv sein", "en": "Diameters must be positive"},
    "thickness_positive_error": {"ru": "Толщина должна быть положительной", "de": "Dicke muss positiv sein", "en": "Thickness must be positive"},
    "height_positive_error": {"ru": "Высота должна быть положительной", "de": "Höhe muss positiv sein", "en": "Height must be positive"},
    "weld_allowance_non_negative_error": {"ru": "Припуск на сварку не может быть отрицательным", "de": "Schweißnahtzugabe darf nicht negativ sein", "en": "Weld allowance cannot be negative"},
    "point_selection_error": {"ru": "Ошибка выбора точки", "de": "Fehler bei der Punktauswahl", "en": "Point selection error"},
    "cad_init_error": {"ru": "Ошибка инициализации AutoCAD", "de": "Fehler bei der Initialisierung von AutoCAD", "en": "AutoCAD initialization error"},
    "window_destroyed_error": {"ru": "Окно было закрыто во время обработки", "de": "Das Fenster wurde während der Verarbeitung geschlossen", "en": "The window was closed during processing"},
    "point_prompt": {"ru": "Введите точку вставки конуса", "de": "Geben Sie den Einfügepunkt des Kegels ein", "en": "Enter the cone insertion point"},
    "mm": {"ru": "мм", "de": "mm", "en": "mm"},
   "axis_yes": {"ru": "Да", "de": "Ja", "en": "Yes"},
    "axis_no": {"ru": "Нет", "de": "Nein", "en": "No"},
    "axis_marks_label": {"ru": "Метки осей, мм", "de": "Achsenmarken, mm", "en": "Axis marks, mm"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "mode_bulge": {"ru": "Дуги", "de": "Bogen", "en": "Bulge"},
    "mode_polyline": {"ru": "Полилиния", "de": "Polylinie", "en": "Polyline"},
    "mode_spline": {"ru": "Сплайн", "de": "Spline", "en": "Spline"},
    "accuracy_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Accuracy (points)"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "build_conditions_label": {"ru": "Условия построения", "de": "Bau-Bedingungen", "en": "Build Conditions"},
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# Значения по умолчанию
default_allowances = ["0", "1", "2", "3", "4", "5", "10", "20"]
default_axis_marks = ["0", "10", "20"]
default_modes = ["mode_bulge", "mode_polyline", "mode_spline"]

# Рекомендуемые наборы значений accuracy по режимам
ACCURACY_OPTIONS = {
    "bulge": ["18", "24", "30", "36"],          # баланс точности/производительности
    "polyline": ["360", "480", "600", "720"],   # полилиния — много точек
    "spline": ["24", "36", "48", "72"],         # сплайн — умеренно
}

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров конуса.
    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).
    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров конуса.
    """
    return ReducerContentPanel(parent)


class ReducerContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров развертки усечённого конуса с одной вертикальной образующей.
    Данные собираются в словарь и передаются через callback в другую программу.
    """
    def __init__(self, parent, callback=None):
        """
        Инициализирует панель, создаёт элементы управления.
        Args:
            parent: Родительский wx.Window (content_panel).
            callback: Функция обратного вызова для передачи данных.
        """
        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []

        # Виджеты
        self.order_input: Optional[wx.TextCtrl] = None
        self.detail_input: Optional[wx.TextCtrl] = None
        self.material_combo: Optional[wx.ComboBox] = None
        self.thickness_combo: Optional[wx.ComboBox] = None
        self.d_input: Optional[wx.TextCtrl] = None
        self.D_input: Optional[wx.TextCtrl] = None
        self.d_type_choice: Optional[wx.Choice] = None
        self.D_type_choice: Optional[wx.Choice] = None
        self.D_adjustment_input: Optional[wx.TextCtrl] = None
        self.height_input: Optional[wx.TextCtrl] = None
        self.allowance_combo: Optional[wx.ComboBox] = None
        self.accuracy_combo: Optional[wx.ComboBox] = None
        self.mode_combo: Optional[wx.ComboBox] = None

        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями. Все поля ввода (TextCtrl, ComboBox, Choice) имеют
        одинаковую ширину и выровнены по правому краю с использованием wx.StretchSpacer()
        между метками и полями.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)

        self.labels.clear()
        self.static_boxes.clear()
        self.buttons.clear()

        field_size = (150, -1)  # Единая ширина для всех полей ввода
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Изображение конуса
        image_path = str(ECCENTRIC_REDUCER_PATH)
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
        self.order_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        self.order_input.SetFont(font)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        self.detail_input.SetFont(font)
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(self.order_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        order_sizer.Add(self.detail_input, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(order_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Материал
        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        material_label.SetFont(font)
        self.labels["material"] = material_label
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                          value=material_options[0] if material_options else "", style=wx.CB_DROPDOWN,
                                          size=field_size)
        self.material_combo.SetFont(font)
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(self.material_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(material_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина"))
        thickness_label.SetFont(font)
        self.labels["thickness"] = thickness_label
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options, value=default_thickness,
                                           style=wx.CB_DROPDOWN, size=field_size)
        self.thickness_combo.SetFont(font)
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        main_data_sizer.Add(thickness_sizer, 0, wx.EXPAND | wx.ALL, 5)

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
        self.d_input = wx.TextCtrl(diameter_box, value="", size=field_size)
        self.d_input.SetFont(font)
        self.d_type_choice = wx.Choice(
            diameter_box,
            choices=[
                loc.get("outer_label", "Внешний"),
                loc.get("middle_label", "Средний"),
                loc.get("inner_label", "Внутренний")
            ],
            size=field_size
        )
        self.d_type_choice.SetFont(font)
        self.d_type_choice.SetSelection(0)  # Внутренний по умолчанию
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(self.d_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_type_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        diameter_sizer.Add(d_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр основания (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(diameter_box, label=loc.get("D_label", "D, мм"))
        D_label.SetFont(font)
        self.labels["D"] = D_label
        self.D_input = wx.TextCtrl(diameter_box, value="", size=field_size)
        self.D_input.SetFont(font)
        self.D_type_choice = wx.Choice(
            diameter_box,
            choices=[
                loc.get("outer_label", "Внешний"),
                loc.get("middle_label", "Средний"),
                loc.get("inner_label", "Внутренний")
            ],
            size=field_size
        )
        self.D_type_choice.SetFont(font)
        self.D_type_choice.SetSelection(0)  # Внутренний по умолчанию
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(self.D_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_type_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        diameter_sizer.Add(D_sizer, 0, wx.EXPAND | wx.ALL, 5)

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
        self.height_input = wx.TextCtrl(height_box, value="", size=field_size)
        self.height_input.SetFont(font)
        height_input_sizer.Add(height_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        height_input_sizer.AddStretchSpacer()
        height_input_sizer.Add(self.height_input, 0, wx.ALIGN_CENTER_VERTICAL)
        height_sizer.Add(height_input_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Припуск на сварку
        allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        allowance_label = wx.StaticText(height_box, label=loc.get("weld_allowance_label", "Припуск на сварку, мм"))
        allowance_label.SetFont(font)
        self.labels["allowance"] = allowance_label
        self.allowance_combo = wx.ComboBox(height_box, choices=[str(i) for i in range(11)], value="3",
                                           style=wx.CB_READONLY,
                                           size=field_size)
        self.allowance_combo.SetFont(font)
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        height_sizer.Add(allowance_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(height_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Условия построения ---
        build_box = wx.StaticBox(self, label=loc.get("build_conditions_label", "Условия построения"))
        style_staticbox(build_box)
        self.static_boxes["build_conditions"] = build_box
        build_sizer = wx.StaticBoxSizer(build_box, wx.VERTICAL)

        # Режим построения
        row_mode = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["mode"] = wx.StaticText(build_box, label=loc.get("mode_label", "Режим"))
        style_label(self.labels["mode"])
        self.mode_combo = wx.ComboBox(
            build_box,
            choices=[loc.get(mode, mode) for mode in default_modes],
            value=loc.get("mode_bulge", "Bulge"),
            style=wx.CB_READONLY,
            size=field_size
        )
        style_combobox(self.mode_combo)
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_change)
        row_mode.Add(self.labels["mode"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_mode.AddStretchSpacer()
        row_mode.Add(self.mode_combo, 0)
        build_sizer.Add(row_mode, 0, wx.EXPAND | wx.ALL, 5)

        # Точность
        row_acc = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["accuracy"] = wx.StaticText(build_box, label=loc.get("accuracy_label", "Точность"))
        style_label(self.labels["accuracy"])
        self.accuracy_combo = wx.ComboBox(
            build_box,
            choices=ACCURACY_OPTIONS["bulge"],
            value="24",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.accuracy_combo)
        row_acc.Add(self.labels["accuracy"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_acc.AddStretchSpacer()
        row_acc.Add(self.accuracy_combo, 0)
        build_sizer.Add(row_acc, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(build_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

    # ----------------------------------------------------------------
    # Обработчики событий
    # ----------------------------------------------------------------

    def on_mode_change(self, event):
        """Меняет список значений accuracy при смене режима построения."""
        mode_map = {
            loc.get("mode_bulge", "Bulge"): "bulge",
            loc.get("mode_polyline", "Polyline"): "polyline",
            loc.get("mode_spline", "Spline"): "spline",
        }
        selected_mode = mode_map.get(self.mode_combo.GetValue(), "bulge")
        options = ACCURACY_OPTIONS.get(selected_mode, ACCURACY_OPTIONS["bulge"])
        self.accuracy_combo.SetItems(options)
        self.accuracy_combo.SetValue(options[0])

    def on_ok(self, event: wx.Event) -> None:
        """
        Обрабатывает нажатие кнопки "ОК", запрашивает точку, передаёт данные через callback
        и очищает поля, не сохраняемые в last_cone_input.json, если окно не уничтожено.

        Args:
            event: Событие нажатия кнопки "ОК".
        """
        try:
            # 1️⃣ Передаем фокус AutoCAD (если окно активно)
            main_window = wx.GetTopLevelParent(self)
            if main_window:
                main_window.Iconize(True)
                main_window.Update()

            cad = ATCadInit()

            # 2️⃣ Запрос точки в AutoCAD
            point = at_point_input(
                cad.document,
                as_variant=False,
                prompt=loc.get("point_prompt", "Укажите точку вставки детали")
            )
            if not point:
                show_popup("Ошибка выбора точки", popup_type="error")
                return

            # 3️⃣ Сохраняем точку
            self.insert_point = point
            update_status_bar_point_selected(self, point)

            # 4️⃣ Возвращаем фокус окну
            if main_window:
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()

            # 5️⃣ Собираем данные формы
            data = self.get_data()
            if data is None:
                return

            # 6️⃣ Передаём собранные данные через callback
            if self.on_submit_callback:
                wx.CallAfter(self.on_submit_callback, data)

        except Exception as e:
            show_popup(f"Ошибка: {e}", popup_type="error")


    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает поля ввода.

        Args:
            event: Событие нажатия кнопки.
        """
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.thickness_combo.SetValue("4")
        self.material_combo.SetValue("1.4301")
        self.d_input.SetValue("")
        self.D_input.SetValue("")
        self.d_type_choice.SetSelection(0)
        self.D_type_choice.SetSelection(0)
        self.height_input.SetValue("")
        self.height_input.Enable(True)
        self.mode_combo.SetValue(loc.get("mode_bulge", "Bulge"))
        self.accuracy_combo.SetValue("24")

    def on_cancel(self, event: wx.Event, switch_content: Optional[str] = "content_apps") -> None:
        """
        Переключает контент на указанную панель (по умолчанию content_apps).

        Args:
            event: Событие нажатия кнопки.
            switch_content: Имя контента для переключения.
        """
        try:
            self.switch_content_panel(switch_content)
        except Exception as e:
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")

    # ----------------------------------------------------------------
    # Сбор данных
    # ----------------------------------------------------------------

    def get_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода, выполняет валидацию и вычисляет
        фактические (средние) диаметры и высоту с учётом припуска на сварку.
        Returns:
            dict | None: словарь с данными или None в случае ошибки.
        """
        try:
            # --- Чтение данных из элементов управления ---
            material = self.material_combo.GetValue().strip()
            thickness_str = self.thickness_combo.GetValue().strip()
            d_str = self.d_input.GetValue().strip()
            D_str = self.D_input.GetValue().strip()
            H_str = self.height_input.GetValue().strip()

            if not material or not thickness_str or not d_str or not D_str or not H_str:
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                return None

            # --- Преобразование строк в числа ---
            d_val = parse_float(d_str)
            D_val = parse_float(D_str)
            H_val = parse_float(H_str)
            thickness = parse_float(thickness_str)
            weld_allowance = parse_float(self.allowance_combo.GetValue()) or 0.0
            accuracy = parse_float(self.accuracy_combo.GetValue()) or 24

            # --- Проверка числовых значений ---
            if any(v is None for v in [d_val, D_val, H_val, thickness]):
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа"), popup_type="error")
                return None
            if d_val <= 0 or D_val <= 0:
                show_popup(loc.get("diameter_positive_error", "Диаметры должны быть положительными"), popup_type="error")
                return None
            if thickness <= 0:
                show_popup(loc.get("thickness_positive_error", "Толщина должна быть положительной"), popup_type="error")
                return None
            if H_val <= 0:
                show_popup(loc.get("height_positive_error", "Высота должна быть положительной"), popup_type="error")
                return None
            if weld_allowance < 0:
                show_popup(loc.get("weld_allowance_non_negative_error", "Припуск на сварку не может быть отрицательным"), popup_type="error")
                return None

            # --- Определение типов диаметров из комбобоксов ---
            type_map = {0: "inner", 1: "middle", 2: "outer"}
            d_type = type_map.get(self.d_type_choice.GetSelection(), "outer")
            D_type = type_map.get(self.D_type_choice.GetSelection(), "outer")

            # --- Пересчёт в средние диаметры ---
            try:
                d_mid = at_diameter(d_val, thickness, d_type)
                D_mid = at_diameter(D_val, thickness, D_type)
            except Exception as e:
                show_popup(loc.get("invalid_number_format_error", "Ошибка при вычислении диаметра") + f": {e}", popup_type="error")
                return None

            # --- Проверка и перестановка, если верхний диаметр больше нижнего ---
            if d_mid > D_mid:
                d_mid, D_mid = D_mid, d_mid

            # --- Высота с учётом припуска на сварку ---
            H_total = H_val + weld_allowance

            # --- Определение режима построения ---
            mode_map = {
                loc.get("mode_bulge", "Bulge"): "bulge",
                loc.get("mode_polyline", "Polyline"): "polyline",
                loc.get("mode_spline", "Spline"): "spline",
            }
            mode = mode_map.get(self.mode_combo.GetValue(), "bulge")

            # --- Формирование итогового словаря ---
            return {
                "insert_point": self.insert_point,
                "order_number": self.order_input.GetValue().strip(),
                "detail_number": self.detail_input.GetValue().strip(),
                "material": material,
                "thickness": thickness,
                "diameter_top": d_mid,
                "diameter_base": D_mid,
                "height": H_total,
                "mode": mode,
                "accuracy": int(accuracy),
            }

        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")
            return None

    def update_ui_language(self) -> None:
        """
        Обновляет текст меток и групп при смене языка.
        Проверяет, что элементы не уничтожены.
        """
        try:
            if self.IsBeingDeleted():
                return

            # StaticBox labels
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["diameter"].SetLabel(loc.get("diameter_label", "Диаметры"))
            self.static_boxes["height"].SetLabel(loc.get("height_label", "Высота"))

            # Прочие метки
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
            self.labels["d"].SetLabel(loc.get("d_label", "d, мм"))
            self.labels["D"].SetLabel(loc.get("D_label", "D, мм"))
            self.labels["height"].SetLabel(loc.get("height_label_mm", "H, мм"))
            self.labels["allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку, мм"))

            # Обновление списков типов диаметров
            self.d_type_choice.SetItems([
                loc.get("inner_label", "Внутренний"),
                loc.get("middle_label", "Средний"),
                loc.get("outer_label", "Внешний")
            ])
            self.d_type_choice.SetSelection(0)

            self.D_type_choice.SetItems([
                loc.get("inner_label", "Внутренний"),
                loc.get("middle_label", "Средний"),
                loc.get("outer_label", "Внешний")
            ])
            self.D_type_choice.SetSelection(0)

            # Кнопки
            for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
                if i < len(self.buttons) and not self.buttons[i].IsBeingDeleted():
                    self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Возврат"][i]))
            adjust_button_widths(self.buttons)

            # Форсируем перерисовку staticbox'ов и панели
            for sb in self.static_boxes.values():
                try:
                    sb.Refresh()
                    parent = sb.GetParent()
                    if parent:
                        parent.Layout()
                        parent.Refresh()
                except Exception:
                    pass

            self.Layout()
            self.Refresh()
            self.Update()
        except Exception as e:
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и поведения кнопок.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Test NozzleContentPanel", size=(1000, 700))
    panel = ReducerContentPanel(frame)


    def on_ok_test(data):
        """
Тестовая функция для обработки callback.
        Симулирует обработку данных и проверяет состояние окна.
        """
        try:
            print("Собранные данные:", data)
            # Симулируем задержку, как в реальной отрисовке
            wx.MilliSleep(100)
        except Exception as e:
            print(f"Ошибка в тестовом callback: {e}")

    def on_ok_event(event):
        """
        Тестовая функция для обработки нажатия "ОК".
        Проверяет, что данные передаются, поля очищаются, а окно остаётся открытым.
        """
        try:
            panel.on_submit_callback = on_ok_test
            panel.on_ok(event)
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")

    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_event)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()


