# Filename: content_nozzle.py
"""
Модуль содержит панель NozzleContentPanel для настройки параметров одиночного отвода
в приложении AT-CAD. Панель собирает данные и передает их через callback в вызывающую
часть приложения (например, в программу построения отвода).

Функциональность:
- UI по образцу окна обечайки (ShellContentPanel)
- Сбор данных в словарь:
    {
        "insert_point": PointVariant | None,
        "diameter": float,
        "diameter_main": float,
        "length": float,
        "axis": bool,
        "axis_marks": float,
        "layer_name": "0",
        "thickness": float,
        "order_number": str,
        "detail_number": str,
        "material": str,
        "weld_allowance": float,
        "accuracy": int,
        "offset": float,
        "thk_correction": bool,
        "mode": str
    }
- Тестовый запуск в конце файла (аналогично shell_content_panel.py)
- Поддержка динамической смены языка через update_ui_language()
- Минимальная валидация полей
- Возможность ввода пользовательского значения accuracy (editable ComboBox)
"""

import wx
from typing import Optional, Dict, List
from pathlib import Path

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_input import at_point_input
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, BaseContentPanel,
    parse_float, load_common_data, style_label, style_textctrl,
    style_combobox, style_radiobutton, style_staticbox, update_status_bar_point_selected
)
from config.at_config import NOZZLE_IMAGE_PATH
from windows.at_content_registry import run_build

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "order_label": {"ru": "К-№", "de": "Auftrags-Nr.", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина, S", "de": "Dicke, S", "en": "Thickness, S"},
    "nozzle_params_label": {"ru": "Параметры отвода", "de": "Stutzenparameter", "en": "Nozzle Params"},
    "diameter_label": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "diameter_main_label": {"ru": "Диаметр магистрали, D", "de": "Main Durchmesser, D", "en": "Main Diameter, D"},
    "length_label": {"ru": "Длина, L", "de": "Länge, L", "en": "Length, L"},
    "weld_allowance_label": {"ru": "Припуск на сварку", "de": "Schweißnahtzugabe", "en": "Weld Allowance"},
    "offset_label": {"ru": "Смещение, O", "de": "Versatz, O", "en": "Offset, O"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "mode_bulge": {"ru": "Дуги", "de": "Bogen", "en": "Bulge"},
    "mode_polyline": {"ru": "Полилиния", "de": "Polylinie", "en": "Polyline"},
    "mode_spline": {"ru": "Сплайн", "de": "Spline", "en": "Spline"},
    "accuracy_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Accuracy (points)"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "axis_checkbox": {"ru": "Показать оси на чертеже", "de": "Achsen zeichnen", "en": "Draw axes"},
    "axis_marks_label": {"ru": "Метки осей, мм", "de": "Achsenmarken, mm", "en": "Axis marks, mm"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "point_prompt": {"ru": "Укажите центр отвода", "de": "Geben Sie das Zentrum des Abzweigs an", "en": "Select nozzle center"},
    "point_selection_error": {"ru": "Точка не выбрана", "de": "Punkt nicht gewählt", "en": "Point not selected"},
    "yes_label": {"ru": "Да", "de": "Ja", "en": "Yes"},
    "no_label": {"ru": "Нет", "de": "Nein", "en": "No"},
    "external_diameter_label": {"ru": "Внешний", "de": "Außen", "en": "External"},
    "middle_diameter_label": {"ru": "Средний", "de": "Mitte", "en": "Middle"},
    "internal_diameter_label": {"ru": "Внутренний", "de": "Innen", "en": "Internal"},
    "build_conditions_label": {"ru": "Условия построения", "de": "Bau-Bedingungen", "en": "Build Conditions"},
}
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
    return NozzleContentPanel(parent)


class NozzleContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров одиночного отвода.
    """
    def __init__(self, parent, callback=None):

        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None

        # Виджеты
        self.mode_combo: Optional[wx.ComboBox] = None
        self.accuracy_combo: Optional[wx.ComboBox] = None
        self.diameter_main_input: Optional[wx.TextCtrl] = None
        self.weld_allowance_input: Optional[wx.ComboBox] = None
        self.offset_input: Optional[wx.TextCtrl] = None
        self.diameter_type_choice: Optional[wx.Choice] = None
        self.axis_combo: Optional[wx.ComboBox] = None

        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self):
        if self.GetSizer():
            self.GetSizer().Clear(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок (изображение и кнопки)
        image_path = str(NOZZLE_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правый блок (поля ввода)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        field_size = (120, -1) # ширина 150, высота автоматическая

        # --- Основные данные ---
        main_data_box = wx.StaticBox(self, label=loc.get("main_data_label", "Основные данные"))
        style_staticbox(main_data_box)
        self.static_boxes["main_data"] = main_data_box
        main_data_sizer = wx.StaticBoxSizer(main_data_box, wx.VERTICAL)

        # строка: К-№ и Деталь
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["order"] = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        style_label(self.labels["order"])
        self.order_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.order_input)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.detail_input)
        row1.Add(self.labels["order"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row1.AddStretchSpacer()
        row1.Add(self.order_input, 0, wx.RIGHT, 10)
        row1.Add(self.detail_input, 0)
        main_data_sizer.Add(row1, 0, wx.EXPAND | wx.ALL, 5)

        # Загрузка общих данных
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat.get("name")]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "5" if "5" in thickness_options or "5.0" in thickness_options else (thickness_options[0] if thickness_options else "")

        # строка: Материал
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["material"] = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        style_label(self.labels["material"])
        self.material_combo = wx.ComboBox(
            main_data_box,
            choices=material_options,
            value=material_options[0] if material_options else "",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.material_combo)
        row2.Add(self.labels["material"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row2.AddStretchSpacer()
        row2.Add(self.material_combo, 0)
        main_data_sizer.Add(row2, 0, wx.EXPAND | wx.ALL, 5)

        # строка: Толщина
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["thickness"] = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина, S"))
        style_label(self.labels["thickness"])
        self.thickness_combo = wx.ComboBox(
            main_data_box,
            choices=thickness_options,
            value=default_thickness,
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.thickness_combo)
        row3.Add(self.labels["thickness"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row3.AddStretchSpacer()
        row3.Add(self.thickness_combo, 0)
        main_data_sizer.Add(row3, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        # --- Параметры отвода ---
        nozzle_box = wx.StaticBox(self, label=loc.get("nozzle_params_label", "Параметры отвода"))
        style_staticbox(nozzle_box)
        self.static_boxes["nozzle_params"] = nozzle_box
        nozzle_sizer = wx.StaticBoxSizer(nozzle_box, wx.VERTICAL)

        # Диаметр отвода
        row_d = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter"] = wx.StaticText(nozzle_box, label=loc.get("diameter_label", "Диаметр, d"))
        style_label(self.labels["diameter"])
        self.diameter_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        row_d.Add(self.labels["diameter"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_d.Add(self.diameter_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Тип диаметра
        self.diameter_type_choice = wx.Choice(
            nozzle_box,
            choices=[
                loc.get("external_diameter_label", "Внешний"),
                loc.get("middle_diameter_label", "Средний"),
                loc.get("internal_diameter_label", "Внутренний"),
            ]
        )
        self.diameter_type_choice.SetMinSize(field_size)
        self.diameter_type_choice.SetInitialSize(field_size)
        self.diameter_type_choice.SetSelection(0)
        row_d.Add(self.diameter_type_choice, 1, wx.EXPAND)
        nozzle_sizer.Add(row_d, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр магистрали
        row_dm = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter_main"] = wx.StaticText(nozzle_box, label=loc.get("diameter_main_label", "Диаметр магистрали, D"))
        style_label(self.labels["diameter_main"])
        self.diameter_main_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.diameter_main_input)
        row_dm.Add(self.labels["diameter_main"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_dm.AddStretchSpacer()
        row_dm.Add(self.diameter_main_input, 0)
        nozzle_sizer.Add(row_dm, 0, wx.EXPAND | wx.ALL, 5)

        # Длина
        row_l = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["length"] = wx.StaticText(nozzle_box, label=loc.get("length_label", "Длина L"))
        style_label(self.labels["length"])
        self.length_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.length_input)
        row_l.Add(self.labels["length"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_l.AddStretchSpacer()
        row_l.Add(self.length_input, 0)
        nozzle_sizer.Add(row_l, 0, wx.EXPAND | wx.ALL, 5)

        # Смещение
        row_off = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["offset"] = wx.StaticText(nozzle_box, label=loc.get("offset_label", "Смещение"))
        style_label(self.labels["offset"])
        self.offset_input = wx.TextCtrl(nozzle_box, value="0", size=field_size)
        style_textctrl(self.offset_input)
        row_off.Add(self.labels["offset"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_off.AddStretchSpacer()
        row_off.Add(self.offset_input, 0)
        nozzle_sizer.Add(row_off, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(nozzle_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

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

        # Припуск на сварку
        row_weld = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["weld_allowance"] = wx.StaticText(build_box,
                                                      label=loc.get("weld_allowance_label", "Припуск на сварку"))
        style_label(self.labels["weld_allowance"])
        self.weld_allowance_input = wx.ComboBox(
            build_box,
            choices=default_allowances,
            value="0",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.weld_allowance_input)
        row_weld.Add(self.labels["weld_allowance"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_weld.AddStretchSpacer()
        row_weld.Add(self.weld_allowance_input, 0)
        build_sizer.Add(row_weld, 0, wx.EXPAND | wx.ALL, 5)

        # Показать оси (замена CheckBox на ComboBox)
        row_axis = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis"] = wx.StaticText(build_box, label=loc.get("axis_checkbox", "Показать оси"))
        style_label(self.labels["axis"])
        self.axis_combo = wx.ComboBox(
            build_box,
            choices=[loc.get("yes_label", "Да"), loc.get("no_label", "Нет")],
            value=loc.get("yes_label", "Да"),
            style=wx.CB_READONLY,
            size=field_size
        )
        style_combobox(self.axis_combo)
        row_axis.Add(self.labels["axis"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_axis.AddStretchSpacer()
        row_axis.Add(self.axis_combo, 0)
        build_sizer.Add(row_axis, 0, wx.EXPAND | wx.ALL, 5)


        # Метки осей
        row_marks = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis_marks"] = wx.StaticText(build_box, label=loc.get("axis_marks_label", "Метки осей"))
        style_label(self.labels["axis_marks"])
        self.axis_marks_input = wx.ComboBox(
            build_box,
            choices=default_axis_marks,
            value="0",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.axis_marks_input)
        row_marks.Add(self.labels["axis_marks"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_marks.AddStretchSpacer()
        row_marks.Add(self.axis_marks_input, 0)
        build_sizer.Add(row_marks, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(build_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND) # Левый блок растягивается, чтобы занять больше пространства
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10) # Правый блок фиксированного размера с отступами

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

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": запрашивает точку вставки и передает данные в callback.

        Аргументы:
            event: Событие wxPython.
        """
        try:
            # Собираем данные из полей
            data = self.get_data()
            if not data:
                return

            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Сворачиваем окно перед выбором точки
            main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = at_point_input(
                cad.document,
                prompt=loc.get("point_prompt", "Укажите центр отвода"),
                as_variant=False
            )

            # Разворачиваем окно обратно
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()

            if not pt:
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            data["insert_point"] = pt

            # Передаем данные дальше через callback или run_build
            if self.on_submit_callback:
                self.on_submit_callback(data)
            else:
                run_build("nozzle", data)

        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")

    def on_cancel(self, event):
        parent = wx.GetTopLevelParent(self)
        if hasattr(parent, "switch_content"):
            parent.switch_content("content_apps")

    def on_clear(self, event):
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.diameter_input.SetValue("")
        self.diameter_main_input.SetValue("")
        self.length_input.SetValue("")
        self.offset_input.SetValue("0")
        self.material_combo.SetSelection(0 if self.material_combo.GetCount() > 0 else -1)
        self.thickness_combo.SetSelection(0 if self.thickness_combo.GetCount() > 0 else -1)
        self.weld_allowance_input.SetValue("0")
        self.axis_combo.SetValue(loc.get("yes_label", "Да"))
        self.axis_marks_input.SetValue("0")
        self.mode_combo.SetValue(loc.get("mode_bulge", "Bulge"))
        self.accuracy_combo.SetValue("24")

    # ----------------------------------------------------------------
    # Сбор данных
    # ----------------------------------------------------------------

    def get_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода в словарь.

        Returns:
            Словарь с данными или None в случае ошибки.
        """
        try:
            # Проверка комбобоксов
            if not self.material_combo.GetValue():
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("material_label", "Материал")),
                    popup_type="error")
                return None
            if not self.thickness_combo.GetValue():
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("thickness_label", "Толщина, S")),
                    popup_type="error")
                return None

            # Парсинг числовых полей
            diameter = parse_float(self.diameter_input.GetValue())
            if diameter is None or diameter <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр отвода, d")), popup_type="error")
                return None

            thickness = parse_float(self.thickness_combo.GetValue())
            if thickness is None or thickness <= 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("thickness_label", "Толщина, S")),
                    popup_type="error")
                return None

            diameter_main = parse_float(self.diameter_main_input.GetValue())
            if diameter_main is None or diameter_main <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_main_label", "Диаметр магистрали, D")), popup_type="error")
                return None

            length = parse_float(self.length_input.GetValue())
            if length is None or length <= 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("length_label", "Длина, L")),
                    popup_type="error")
                return None

            axis_marks = parse_float(self.axis_marks_input.GetValue()) or 0.0
            weld_allowance = parse_float(self.weld_allowance_input.GetValue()) or 0.0
            accuracy = parse_float(self.accuracy_combo.GetValue())
            if accuracy is None or accuracy < 4:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("accuracy_label", "Точность (точек)")), popup_type="error")
                return None
            offset = parse_float(self.offset_input.GetValue()) or 0.0

            # Маппинг типа диаметра
            diameter_type_map = {
                0: "outer",
                1: "middle",
                2: "inner"
            }
            flag = diameter_type_map.get(self.diameter_type_choice.GetSelection(), "outer")

            # Вычисление среднего диаметра через at_diameter
            try:
                diameter = at_diameter(diameter, thickness, flag)
            except ValueError as e:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр отвода, d")), popup_type="error")
                return None

            mode_map = {
                loc.get("mode_bulge", "Bulge"): "bulge",
                loc.get("mode_polyline", "Polyline"): "polyline",
                loc.get("mode_spline", "Spline"): "spline",
            }

            # Маппинг значения axis_combo
            axis_value = self.axis_combo.GetValue() == loc.get("yes_label", "Да")

            return {
                "insert_point": self.insert_point,
                "diameter": diameter,
                "diameter_main": diameter_main,
                "length": length,
                "axis": axis_value,
                "axis_marks": axis_marks,
                "layer_name": "0",
                "thickness": thickness,
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "weld_allowance": weld_allowance,
                "accuracy": int(accuracy),
                "offset": offset,
                "thk_correction": False,
                "mode": mode_map.get(self.mode_combo.GetValue(), "bulge")
            }
        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")
            return None

    def update_ui_language(self):
        """Переводит все подписи при смене языка."""
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["nozzle_params"].SetLabel(loc.get("nozzle_params_label", "Параметры отвода"))
        self.static_boxes["build_conditions"].SetLabel(loc.get("build_conditions_label", "Условия построения"))

        self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина, S"))
        self.labels["diameter"].SetLabel(loc.get("diameter_label", "Диаметр отвода, d"))
        self.labels["diameter_main"].SetLabel(loc.get("diameter_main_label", "Диаметр магистрали, D"))
        self.labels["length"].SetLabel(loc.get("length_label", "Длина, L"))
        self.labels["offset"].SetLabel(loc.get("offset_label", "Смещение, O"))
        self.labels["mode"].SetLabel(loc.get("mode_label", "Режим"))
        self.labels["accuracy"].SetLabel(loc.get("accuracy_label", "Точность"))
        self.labels["weld_allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку"))
        self.labels["axis"].SetLabel(loc.get("axis_checkbox", "Показать оси"))
        self.labels["axis_marks"].SetLabel(loc.get("axis_marks_label", "Метки осей"))

        # Обновление списка режимов построения
        self.mode_combo.SetItems([loc.get(mode, mode) for mode in default_modes])
        self.mode_combo.SetValue(loc.get("mode_bulge", "Bulge"))

        # Обновление списка типов диаметра
        self.diameter_type_choice.SetItems([
            loc.get("external_diameter_label", "Внешний"),
            loc.get("middle_diameter_label", "Средний"),
            loc.get("internal_diameter_label", "Внутренний"),
        ])
        self.diameter_type_choice.SetSelection(0)

        # Обновление списка для axis_combo
        self.axis_combo.SetItems([
            loc.get("yes_label", "Да"),
            loc.get("no_label", "Нет")
        ])
        self.axis_combo.SetValue(loc.get("yes_label", "Да"))

        self.Layout()
        self.Refresh()

# ----------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title="Test NozzleContentPanel", size=(1000, 600))
    panel = NozzleContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()

