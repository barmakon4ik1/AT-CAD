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
    "order_label": {"ru": "К-№", "de": "Auftragsnummer", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина", "de": "Dicke", "en": "Thickness"},
    "nozzle_params_label": {"ru": "Параметры отвода", "de": "Abzweigparameter", "en": "Nozzle Params"},
    "diameter_label": {"ru": "Диаметр отвода, d", "de": "Abzweigdurchmesser, d", "en": "Nozzle Diameter, d"},
    "diameter_main_label": {"ru": "Диаметр магистрали, D", "de": "Hauptdurchmesser, D", "en": "Main Diameter, D"},
    "length_label": {"ru": "Длина L", "de": "Länge L", "en": "Length L"},
    "weld_allowance_label": {"ru": "Припуск на сварку", "de": "Schweißnahtzugabe", "en": "Weld Allowance"},
    "offset_label": {"ru": "Смещение", "de": "Versatz", "en": "Offset"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "accuracy_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Accuracy (points)"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "axis_checkbox": {"ru": "Отрисовка осей", "de": "Achsen zeichnen", "en": "Draw axes"},
    "axis_marks_label": {"ru": "Метки осей", "de": "Achsenmarken", "en": "Axis marks"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "point_prompt": {"ru": "Укажите центр отвода", "de": "Geben Sie das Zentrum des Abzweigs an", "en": "Select nozzle center"},
    "point_selection_error": {"ru": "Точка не выбрана", "de": "Punkt nicht gewählt", "en": "Point not selected"},
}
loc.register_translations(TRANSLATIONS)

# Значения по умолчанию
default_allowances = ["0", "1", "2", "3", "4", "5", "10", "20"]
default_axis_marks = ["0", "10", "20"]
default_modes = ["bulge", "polyline", "spline"]

# Рекомендуемые наборы значений accuracy по режимам
ACCURACY_OPTIONS = {
    "bulge": ["18", "24", "30", "36"],          # баланс точности/производительности
    "polyline": ["360", "480", "600", "720"],   # поли-линия — много точек
    "spline": ["24", "36", "48", "72"],         # сплайн — умеренно
}

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    """
    Фабричная функция для создания панели NozzleContentPanel.

    Args:
        parent (wx.Window): Родительская панель.

    Returns:
        wx.Panel: Инициализированный экземпляр NozzleContentPanel.
    """
    return NozzleContentPanel(parent)


class NozzleContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров одиночного отвода.

    По функционалу и расположению виджетов максимально унифицирована с ShellContentPanel.
    """
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None

        # Состояние/виджеты специфичные для отвода
        self.mode_combo: Optional[wx.ComboBox] = None
        self.accuracy_combo: Optional[wx.ComboBox] = None
        self.diameter_main_input: Optional[wx.TextCtrl] = None
        self.weld_allowance_input: Optional[wx.ComboBox] = None
        self.offset_input: Optional[wx.TextCtrl] = None

        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self):
        """
        Создает и располагает все элементы управления.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок: изображение и кнопки
        image_path = str(NOZZLE_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Стандартные кнопки: OK, Clear, Return
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правый блок: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        font_big = get_standard_font().Bold()
        field_size = (150, -1)

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
        row1.Add(self.order_input, 0, wx.RIGHT, 10)
        row1.AddStretchSpacer()
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

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Параметры отвода ---
        nozzle_box = wx.StaticBox(self, label=loc.get("nozzle_params_label", "Параметры отвода"))
        style_staticbox(nozzle_box)
        self.static_boxes["nozzle_params"] = nozzle_box
        nozzle_sizer = wx.StaticBoxSizer(nozzle_box, wx.VERTICAL)

        # Диаметр отвода
        row_d = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter"] = wx.StaticText(nozzle_box, label=loc.get("diameter_label", "Диаметр отвода, d"))
        style_label(self.labels["diameter"])
        self.diameter_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        row_d.Add(self.labels["diameter"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_d.AddStretchSpacer()
        row_d.Add(self.diameter_input, 0)
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

        # Режим и Точность (accuracy)
        row_mode = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["mode"] = wx.StaticText(nozzle_box, label=loc.get("mode_label", "Режим построения"))
        style_label(self.labels["mode"])
        self.mode_combo = wx.ComboBox(nozzle_box, choices=default_modes, value="bulge", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.mode_combo)
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_changed)
        self.mode_combo.Bind(wx.EVT_TEXT, self.on_mode_changed)

        row_mode.Add(self.labels["mode"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_mode.AddStretchSpacer()
        row_mode.Add(self.mode_combo, 0)
        nozzle_sizer.Add(row_mode, 0, wx.EXPAND | wx.ALL, 5)

        row_acc = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["accuracy"] = wx.StaticText(nozzle_box, label=loc.get("accuracy_label", "Точность (точек)"))
        style_label(self.labels["accuracy"])
        # editable combobox: пользователь может ввести своё число
        self.accuracy_combo = wx.ComboBox(nozzle_box, choices=ACCURACY_OPTIONS["bulge"], value=ACCURACY_OPTIONS["bulge"][1], style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.accuracy_combo)
        row_acc.Add(self.labels["accuracy"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_acc.AddStretchSpacer()
        row_acc.Add(self.accuracy_combo, 0)
        nozzle_sizer.Add(row_acc, 0, wx.EXPAND | wx.ALL, 5)

        # Припуск на сварку
        row_weld = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["weld_allowance"] = wx.StaticText(nozzle_box, label=loc.get("weld_allowance_label", "Припуск на сварку"))
        style_label(self.labels["weld_allowance"])
        self.weld_allowance_input = wx.ComboBox(nozzle_box, choices=default_allowances, value="0", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.weld_allowance_input)
        row_weld.Add(self.labels["weld_allowance"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_weld.AddStretchSpacer()
        row_weld.Add(self.weld_allowance_input, 0)
        nozzle_sizer.Add(row_weld, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(nozzle_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Дополнительные условия ---
        additional_box = wx.StaticBox(self, label=loc.get("additional_label", "Доп. условия"))
        style_staticbox(additional_box)
        self.static_boxes["additional"] = additional_box
        additional_sizer = wx.StaticBoxSizer(additional_box, wx.VERTICAL)

        self.axis_checkbox = wx.CheckBox(additional_box, label=loc.get("axis_checkbox", "Отрисовка осей"))
        self.axis_checkbox.SetFont(font_big)
        self.axis_checkbox.SetValue(True)
        additional_sizer.Add(self.axis_checkbox, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        # Метки осей
        row_am = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis_marks"] = wx.StaticText(additional_box, label=loc.get("axis_marks_label", "Шаг меток (мм)"))
        style_label(self.labels["axis_marks"])
        self.axis_marks_combo = wx.ComboBox(additional_box, choices=default_axis_marks, value="10", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.axis_marks_combo)
        row_am.Add(self.labels["axis_marks"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_am.AddStretchSpacer()
        row_am.Add(self.axis_marks_combo, 0)
        additional_sizer.Add(row_am, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(additional_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Собираем общий макет
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

    # --- Работа с режимом и accuracy ---
    def on_mode_changed(self, event=None):
        """
        Обновляет список опций accuracy в зависимости от выбранного режима.
        Значение accuracy остаётся, если оно подходит; иначе выбирается значение по умолчанию из списка.
        """
        try:
            mode = self.mode_combo.GetValue() if self.mode_combo else "bulge"
            if mode not in ACCURACY_OPTIONS:
                mode = "bulge"
            current = self.accuracy_combo.GetValue() if self.accuracy_combo else ""
            options = ACCURACY_OPTIONS.get(mode, ACCURACY_OPTIONS["bulge"])
            # Обновляем список сохраня при этом пользовательский ввод если он числовой
            self.accuracy_combo.Clear()
            for v in options:
                self.accuracy_combo.Append(v)
            # Попытка сохранить текущее значение, иначе выбрать среднее/предустановленное
            if current and current.strip().isdigit():
                self.accuracy_combo.SetValue(current.strip())
            else:
                self.accuracy_combo.SetValue(options[1])  # второй элемент как разумный дефолт
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при смене режима: {str(e)}"), popup_type="error")

    def collect_input_data(self) -> Dict:
        """
        Собирает данные из полей ввода в словарь.
        """
        try:
            # Преобразования числовых полей
            diameter = parse_float(self.diameter_input.GetValue())
            diameter_main = parse_float(self.diameter_main_input.GetValue())
            thickness = parse_float(self.thickness_combo.GetValue())
            length = parse_float(self.length_input.GetValue())
            offset = parse_float(self.offset_input.GetValue()) or 0.0
            weld_allowance = parse_float(self.weld_allowance_input.GetValue()) or 0.0
            axis_marks = parse_float(self.axis_marks_combo.GetValue()) or 0.0

            # Обработка диаметра с учетом типа (аналогично оболочке, используем at_diameter если нужно)
            # Тут предположим, что пользователь задаёт наружный диаметр отвода,
            # если потребуется, можно добавить выбор типа диаметра.
            diameter_calc = at_diameter(diameter, thickness, "outer") if diameter and thickness else diameter

            # accuracy: попытка получить целое число из ComboBox (включая пользовательский ввод)
            acc_raw = self.accuracy_combo.GetValue() if self.accuracy_combo else ""
            try:
                accuracy = int(float(acc_raw))
            except Exception:
                accuracy = None

            data = {
                "insert_point": self.insert_point,
                "diameter": diameter_calc,
                "diameter_main": diameter_main,
                "length": length,
                "axis": self.axis_checkbox.GetValue(),
                "axis_marks": axis_marks,
                "layer_name": "0",  # берётся из конфига, не спрашиваем у пользователя
                "thickness": thickness,
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "weld_allowance": weld_allowance,
                "accuracy": accuracy,
                "offset": offset,
                "thk_correction": False,  # вычисляется ниже
                "mode": self.mode_combo.GetValue() if self.mode_combo else "bulge"
            }

            # thk_correction — True если диаметр отвода равен диаметру магистрали (с допустимой погрешностью)
            try:
                if data.get("diameter") is not None and data.get("diameter_main") is not None:
                    if abs(float(data["diameter"]) - float(data["diameter_main"])) < 1e-6:
                        data["thk_correction"] = True
                    else:
                        data["thk_correction"] = False
            except Exception:
                data["thk_correction"] = False

            return data
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка сбора данных: {str(e)}"), popup_type="error")
            return {}

    def validate_input(self, data: Dict) -> bool:
        """
        Минимальная валидация полей.
        """
        # Проверка числовых значений и обязательных полей
        if data.get("diameter") is None or data.get("diameter") <= 0:
            show_popup(loc.get("error", "Некорректный диаметр отвода"), popup_type="error")
            return False
        if data.get("diameter_main") is None or data.get("diameter_main") <= 0:
            show_popup(loc.get("error", "Некорректный диаметр магистрали"), popup_type="error")
            return False
        if data.get("length") is None or data.get("length") <= 0:
            show_popup(loc.get("error", "Некорректная длина"), popup_type="error")
            return False
        if not data.get("material"):
            show_popup(loc.get("error", "Материал не выбран"), popup_type="error")
            return False
        if not data.get("thickness"):
            show_popup(loc.get("error", "Толщина не выбрана"), popup_type="error")
            return False
        if not data.get("insert_point"):
            show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
            return False
        # accuracy как целое положительное число
        acc = data.get("accuracy")
        if acc is None:
            show_popup(loc.get("error", "Некорректная точность (accuracy)"), popup_type="error")
            return False
        try:
            acc_i = int(acc)
            if acc_i <= 0:
                show_popup(loc.get("error", "Точность должна быть положительным числом"), popup_type="error")
                return False
            # Не навязываем строгие пределы, но предупреждаем при экстремальных значениях
            # (оставляем успешную валидацию)
        except Exception:
            show_popup(loc.get("error", "Точность должна быть целым числом"), popup_type="error")
            return False

        return True

    def process_input(self, data: Dict) -> bool:
        """
        Передаёт данные через callback.
        """
        try:
            if self.on_submit_callback:
                self.on_submit_callback(data)
            return True
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка обработки данных: {str(e)}"), popup_type="error")
            return False

    def clear_input_fields(self):
        """
        Сброс всех полей в значения по умолчанию.
        """
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetSelection(wx.NOT_FOUND)
        self.thickness_combo.SetSelection(wx.NOT_FOUND)
        self.diameter_input.SetValue("")
        self.diameter_main_input.SetValue("")
        self.length_input.SetValue("")
        self.offset_input.SetValue("0")
        self.mode_combo.SetValue("bulge")
        # обновим accuracy под bulge
        self.on_mode_changed()
        self.weld_allowance_input.SetValue("0")
        self.axis_checkbox.SetValue(True)
        self.axis_marks_combo.SetValue("10")
        self.insert_point = None

    def on_ok(self, event: wx.Event):
        """
        Обработка кнопки ОК: запрос точки через AutoCAD и передача данных.
        """
        try:
            # Собираем предварительные данные
            data = self.collect_input_data()

            # Свернем главное окно перед выбором точки
            main_window = wx.GetTopLevelParent(self)
            if main_window:
                main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = None
            try:
                pt = at_point_input(
                    cad.document,
                    prompt=loc.get("point_prompt", "Укажите центр отвода"),
                    as_variant=False
                )
            except Exception as e:
                # Показываем ошибку выбора точки, но не падаем
                show_popup(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), popup_type="error")
                pt = None

            # Разворачиваем окно обратно
            if main_window:
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()

            if not pt:
                # Если точка не выбрана — выходим (пользователь мог отменить)
                print("Точка не выбрана")
                return

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            data["insert_point"] = pt

            # Валидация
            if not self.validate_input(data):
                return

            # Передаём данные в callback
            if self.on_submit_callback:
                wx.CallAfter(self.process_input, data)

        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при обработке ОК: {str(e)}"), popup_type="error")

    def on_clear(self, event=None):
        """
        Обработка кнопки Очистить.
        """
        try:
            self.clear_input_fields()
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при очистке: {str(e)}"), popup_type="error")

    def on_cancel(self, event=None):
        """
        Обработка кнопки возврат/закрыть: просто скрываем/уничтожаем родительское диалоговое окно,
        но реализация зависит от того, как окно интегрировано в основное приложение.
        Здесь просто пытаемся закрыть родительский фрейм если это отдельное окно.
        """
        try:
            top = wx.GetTopLevelParent(self)
            if top and isinstance(top, wx.Frame):
                top.Close()
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при закрытии окна: {str(e)}"), popup_type="error")

    def update_ui_language(self):
        """
        Обновляет метки и надписи при смене языка.
        """
        try:
            # Групповые заголовки
            if "main_data" in self.static_boxes:
                self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            if "nozzle_params" in self.static_boxes:
                self.static_boxes["nozzle_params"].SetLabel(loc.get("nozzle_params_label", "Параметры отвода"))
            if "additional" in self.static_boxes:
                self.static_boxes["additional"].SetLabel(loc.get("additional_label", "Доп. условия"))

            # Метки полей
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина, S"))
            self.labels["diameter"].SetLabel(loc.get("diameter_label", "Диаметр отвода, d"))
            self.labels["diameter_main"].SetLabel(loc.get("diameter_main_label", "Диаметр магистрали, D"))
            self.labels["length"].SetLabel(loc.get("length_label", "Длина L"))
            self.labels["offset"].SetLabel(loc.get("offset_label", "Смещение"))
            self.labels["mode"].SetLabel(loc.get("mode_label", "Режим построения"))
            self.labels["accuracy"].SetLabel(loc.get("accuracy_label", "Точность (точек)"))
            self.labels["weld_allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку"))
            self.labels["axis_marks"].SetLabel(loc.get("axis_marks_label", "Шаг меток (мм)"))

            # Чекбоксы и кнопки
            self.axis_checkbox.SetLabel(loc.get("axis_checkbox", "Отрисовка осей"))
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            if len(self.buttons) > 2:
                self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
                self.buttons[2].SetLabel(loc.get("cancel_button", "Возврат"))
            else:
                self.buttons[1].SetLabel(loc.get("cancel_button", "Возврат"))

            apply_styles_to_panel(self)
            self.Layout()
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")


if __name__ == "__main__":
    """
    Тестовый запуск панели NozzleContentPanel.
    Выводит собранный словарь в консоль через тестовый callback.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест NozzleContentPanel", size=(1000, 700))
    panel = NozzleContentPanel(frame)

    def on_ok_test(data):
        try:
            print("Собранные данные:", data)
            # простая симуляция обработки
            wx.MilliSleep(100)
        except Exception as e:
            print(f"Ошибка в тестовом callback: {e}")

    def on_ok_event(event):
        try:
            # Собираем данные, просим точку и выполняем валидацию (аналогично реальной on_ok)
            data = panel.collect_input_data()
            cad = ATCadInit()
            frame.Iconize(True)
            try:
                pt = at_point_input(cad.document, prompt=loc.get("point_prompt", "Укажите центр отвода"), as_variant=False)
            except Exception as e:
                show_popup(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), popup_type="error")
                pt = None
            frame.Iconize(False)
            frame.Raise()
            frame.SetFocus()

            if not pt:
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            panel.insert_point = pt
            data["insert_point"] = pt

            if not panel.validate_input(data):
                return

            panel.on_submit_callback = on_ok_test
            wx.CallAfter(panel.process_input, data)
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")

    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_event)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
