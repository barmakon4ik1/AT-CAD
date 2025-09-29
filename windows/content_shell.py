# Filename: shell_content_panel.py
"""
Модуль содержит панель ShellContentPanel для настройки параметров оболочки
в приложении AT-CAD. Панель собирает данные и передает их через callback в at_shell.
"""

import wx
from typing import Optional, Dict

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
from config.at_config import SHELL_IMAGE_PATH
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
    "shell_params_label": {"ru": "Параметры оболочки", "de": "Schalendaten", "en": "Shell Params"},
    "diameter_label": {"ru": "Диаметр, D", "de": "Durchmesser, D", "en": "Diameter, D"},
    "inner_label": {"ru": "Внутренний", "de": "Innen", "en": "Inner"},
    "middle_label": {"ru": "Средний", "de": "Mittel", "en": "Middle"},
    "outer_label": {"ru": "Внешний", "de": "Außen", "en": "Outer"},
    "length_label": {"ru": "Длина L", "de": "Länge L", "en": "Length L"},
    "angle_label": {"ru": "Положение шва (°)", "de": "Nahtposition (°)", "en": "Seam angle (°)"},
    "clockwise_label": {"ru": "Развертка по часовой стрелке", "de": "Abwicklung im Uhrzeigersinn", "en": "Clockwise development"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "axis_checkbox": {"ru": "Отрисовка осей", "de": "Achsen zeichnen", "en": "Draw axes"},
    "axis_marks_label": {"ru": "Метки осей", "de": "Achsenmarken", "en": "Axis marks"},
    "weld_allowance_label": {"ru": "Припуск на сварку", "de": "Schweißnahtzugabe", "en": "Weld Allowance"},
    "allowance_top_label": {"ru": "Сверху Lt", "de": "Oben Lt", "en": "Top Lt"},
    "allowance_bottom_label": {"ru": "Снизу Lb", "de": "Unten Lb", "en": "Bottom Lb"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "branch_button": {"ru": "Наличие отвода", "de": "Abzweig", "en": "Branch"},
}

loc.register_translations(TRANSLATIONS)

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    """
    Фабричная функция для создания панели ShellContentPanel.

    Args:
        parent (wx.Window): Родительская панель (обычно content_panel в ATMainWindow).

    Returns:
        wx.Panel: Инициализированный экземпляр ShellContentPanel.
    """
    return ShellContentPanel(parent)

# Значения по умолчанию
default_allowances = ["0", "1", "2", "3", "4", "5", "10", "20"]
default_axis_marks = ["0", "10", "20"]

class ShellContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров оболочки в приложении AT-CAD.
    Наследуется от BaseContentPanel, предоставляя интерфейс для ввода данных об оболочке,
    таких как заказ, материал, размеры, припуски и дополнительные параметры.
    Данные собираются в словарь и передаются через callback в другую программу.
    """
    def __init__(self, parent, callback=None):
        """
        Инициализация панели ShellContentPanel.

        Аргументы:
            parent: Родительское окно или панель wxPython.
            callback: Опциональная функция обратного вызова для передачи собранных данных.
        """
        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None

        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self):
        """
        Настраивает пользовательский интерфейс панели ShellContentPanel.
        Создает левый сайзер с изображением и кнопками и правый сайзер с полями ввода.
        Все поля ввода (TextCtrl, ComboBox) имеют одинаковую ширину и выровнены по правому краю
        с использованием wx.StretchSpacer(). Стилизация выполняется через функции из at_window_utils.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок: изображение и кнопки
        image_path = str(SHELL_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.branch_button = wx.Button(self, label=loc.get("branch_button", "Наличие отвода"))
        self.branch_button.SetBackgroundColour(wx.Colour(0, 102, 204))
        self.branch_button.SetForegroundColour(wx.Colour(255, 255, 255))
        self.branch_button.SetFont(get_standard_font())
        self.left_sizer.Add(self.branch_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правый блок
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        font_big = get_standard_font().Bold()
        field_size = (150, -1)  # Единая ширина для всех полей ввода

        # --- Основные данные ---
        main_data_box = wx.StaticBox(self, label=loc.get("main_data_label", "Основные данные"))
        style_staticbox(main_data_box)
        self.static_boxes["main_data"] = main_data_box
        main_data_sizer = wx.StaticBoxSizer(main_data_box, wx.VERTICAL)

        # Первая строка: К-№ и Деталь
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
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else (thickness_options[0] if thickness_options else "")

        # Вторая строка: Материал
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

        # Третья строка: Толщина
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

        # --- Параметры оболочки ---
        shell_box = wx.StaticBox(self, label=loc.get("shell_params_label", "Параметры оболочки"))
        style_staticbox(shell_box)
        self.static_boxes["shell_params"] = shell_box
        shell_sizer = wx.StaticBoxSizer(shell_box, wx.VERTICAL)

        # Диаметр
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter"] = wx.StaticText(shell_box, label=loc.get("diameter_label", "Диаметр, D"))
        style_label(self.labels["diameter"])
        self.diameter_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        row4.Add(self.labels["diameter"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row4.AddStretchSpacer()
        row4.Add(self.diameter_input, 0)
        shell_sizer.Add(row4, 0, wx.EXPAND | wx.ALL, 5)

        # Радиокнопки
        rb_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.d_inner = wx.RadioButton(shell_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(shell_box, label=loc.get("middle_label", "Средний"))
        self.d_outer = wx.RadioButton(shell_box, label=loc.get("outer_label", "Внешний"))
        self.d_outer.SetValue(True)
        for rb in [self.d_inner, self.d_middle, self.d_outer]:
            rb.SetFont(font)
            style_radiobutton(rb)
        rb_sizer.AddStretchSpacer()
        rb_sizer.Add(self.d_inner, 0, wx.RIGHT, 10)
        rb_sizer.Add(self.d_middle, 0, wx.RIGHT, 10)
        rb_sizer.Add(self.d_outer, 0)
        shell_sizer.Add(rb_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Длина
        row5 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["length"] = wx.StaticText(shell_box, label=loc.get("length_label", "Длина, L"))
        style_label(self.labels["length"])
        self.length_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.length_input)
        row5.Add(self.labels["length"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row5.AddStretchSpacer()
        row5.Add(self.length_input, 0)
        shell_sizer.Add(row5, 0, wx.EXPAND | wx.ALL, 5)

        # Угол шва
        row6 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["angle"] = wx.StaticText(shell_box, label=loc.get("angle_label", "Положение шва (°)"))
        style_label(self.labels["angle"])
        self.angle_input = wx.TextCtrl(shell_box, value="", size=field_size)
        style_textctrl(self.angle_input)
        row6.Add(self.labels["angle"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row6.AddStretchSpacer()
        row6.Add(self.angle_input, 0)
        shell_sizer.Add(row6, 0, wx.EXPAND | wx.ALL, 5)

        # Чекбокс развертки
        self.clockwise_checkbox = wx.CheckBox(shell_box, label=loc.get("clockwise_label", "Развертка по часовой"))
        self.clockwise_checkbox.SetFont(font_big)
        shell_sizer.Add(self.clockwise_checkbox, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        self.right_sizer.Add(shell_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Дополнительные условия ---
        additional_box = wx.StaticBox(self, label=loc.get("additional_label", "Доп. условия"))
        style_staticbox(additional_box)
        self.static_boxes["additional"] = additional_box
        additional_sizer = wx.StaticBoxSizer(additional_box, wx.VERTICAL)

        self.axis_checkbox = wx.CheckBox(
            additional_box,
            label=loc.get("axis_checkbox", "Маркировать оси гравировкой?")
        )
        self.axis_checkbox.SetFont(font_big)
        self.axis_checkbox.SetValue(True)
        additional_sizer.Add(self.axis_checkbox, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        # Метки осей
        row7 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["axis_marks"] = wx.StaticText(
            additional_box, label=loc.get("axis_marks_label", "Шаг меток (мм)")
        )
        style_label(self.labels["axis_marks"])
        self.axis_marks_combo = wx.ComboBox(
            additional_box,
            choices=default_axis_marks,
            value="10",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.axis_marks_combo)
        row7.Add(self.labels["axis_marks"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row7.AddStretchSpacer()
        row7.Add(self.axis_marks_combo, 0)
        additional_sizer.Add(row7, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(additional_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # --- Припуск на сварку ---
        allowance_box = wx.StaticBox(self, label=loc.get("weld_allowance_label", "Припуск на сварку"))
        style_staticbox(allowance_box)
        self.static_boxes["allowance"] = allowance_box
        allowance_sizer = wx.StaticBoxSizer(allowance_box, wx.VERTICAL)

        # Припуски сверху и снизу
        row8 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["allowance_top"] = wx.StaticText(allowance_box, label=loc.get("allowance_top_label", "Сверху Lt"))
        style_label(self.labels["allowance_top"])
        self.allowance_top = wx.ComboBox(allowance_box, choices=default_allowances, value="0", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.allowance_top)
        self.labels["allowance_bottom"] = wx.StaticText(allowance_box, label=loc.get("allowance_bottom_label", "Снизу Lb"))
        style_label(self.labels["allowance_bottom"])
        self.allowance_bottom = wx.ComboBox(allowance_box, choices=default_allowances, value="0", style=wx.CB_DROPDOWN, size=field_size)
        style_combobox(self.allowance_bottom)
        row8.Add(self.labels["allowance_top"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row8.Add(self.allowance_top, 0, wx.RIGHT, 10)
        row8.AddStretchSpacer()
        row8.Add(self.labels["allowance_bottom"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row8.Add(self.allowance_bottom, 0)
        allowance_sizer.Add(row8, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(allowance_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Собираем общий макет
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)  # Применяем стили ко всем элементам
        self.Layout()

    def collect_input_data(self) -> Dict:
        """
        Собирает данные из полей ввода панели в словарь для передачи в другую программу.

        Возвращает:
            Dict: Словарь с данными из полей ввода.
        """
        try:
            diameter = parse_float(self.diameter_input.GetValue())
            thickness = parse_float(self.thickness_combo.GetValue())
            diameter_type = "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer"
            diameter = at_diameter(diameter, thickness, diameter_type)

            data = {
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness": self.thickness_combo.GetValue(),
                "diameter": diameter,
                "length": parse_float(self.length_input.GetValue()),
                "angle": parse_float(self.angle_input.GetValue()) or 0.0,
                "clockwise": self.clockwise_checkbox.GetValue(),
                "axis": self.axis_checkbox.GetValue(),
                "axis_marks": parse_float(self.axis_marks_combo.GetValue()) or 0,
                "weld_allowance_top": parse_float(self.allowance_top.GetValue()) or 0,
                "weld_allowance_bottom": parse_float(self.allowance_bottom.GetValue()) or 0,
                "layer_name": "0",
                "insert_point": self.insert_point
            }
            return data
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка сбора данных: {str(e)}"), popup_type="error")
            return {}

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введенных данных.

        Аргументы:
            data: Словарь с данными из полей ввода.

        Возвращает:
            bool: True, если данные валидны, иначе False.
        """
        if data.get("diameter") is None or data.get("diameter") <= 0:
            show_popup(loc.get("error", "Некорректный диаметр"), popup_type="error")
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
        return True

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает введенные данные, передавая их в callback-функцию.

        Аргументы:
            data: Словарь с данными из полей ввода.

        Возвращает:
            bool: True, если обработка успешна, иначе False.
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
        Очищает все поля ввода и сбрасывает значения на начальные.
        """
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetSelection(wx.NOT_FOUND)
        self.thickness_combo.SetSelection(wx.NOT_FOUND)
        self.diameter_input.SetValue("")
        self.d_inner.SetValue(False)
        self.d_middle.SetValue(False)
        self.d_outer.SetValue(True)
        self.length_input.SetValue("")
        self.angle_input.SetValue("")
        self.clockwise_checkbox.SetValue(True)
        self.axis_checkbox.SetValue(True)
        self.axis_marks_combo.SetValue("10")
        self.allowance_top.SetValue("0")
        self.allowance_bottom.SetValue("0")
        self.insert_point = None

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": запрашивает точку вставки и передает данные в callback.

        Аргументы:
            event: Событие wxPython.
        """
        try:
            # Собираем данные из полей (без проверок)
            data = self.collect_input_data()

            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Сворачиваем окно перед выбором точки
            main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = at_point_input(
                cad.document,
                prompt=loc.get("point_prompt", "Введите точку вставки оболочки"),
                as_variant=False
            )

            # Разворачиваем окно обратно
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()

            if not pt:
                logging.warning("Точка не выбрана")
                return

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            data["insert_point"] = pt
            print(data)
            # Передаем данные дальше через callback
            if self.on_submit_callback:
                wx.CallAfter(self.process_input, data)

        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")

    def update_ui_language(self):
        """
        Обновляет язык интерфейса, применяя переводы ко всем элементам.
        """
        try:
            # Заголовки групп
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["shell_params"].SetLabel(loc.get("shell_params_label", "Параметры оболочки"))
            self.static_boxes["additional"].SetLabel(loc.get("additional_label", "Доп. условия"))
            self.static_boxes["allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку"))

            # Метки полей
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина, S"))
            self.labels["diameter"].SetLabel(loc.get("diameter_label", "Диаметр, D"))
            self.labels["length"].SetLabel(loc.get("length_label", "Длина, L"))
            self.labels["angle"].SetLabel(loc.get("angle_label", "Положение шва (°)"))
            self.labels["allowance_top"].SetLabel(loc.get("allowance_top_label", "Сверху Lt"))
            self.labels["allowance_bottom"].SetLabel(loc.get("allowance_bottom_label", "Снизу Lb"))

            # Радиокнопки
            self.d_inner.SetLabel(loc.get("inner_label", "Внутренний"))
            self.d_middle.SetLabel(loc.get("middle_label", "Средний"))
            self.d_outer.SetLabel(loc.get("outer_label", "Внешний"))

            # Чекбоксы
            self.clockwise_checkbox.SetLabel(loc.get("clockwise_label", "Развертка по часовой стрелке"))
            self.axis_checkbox.SetLabel(loc.get("axis_checkbox", "Маркировать оси гравировкой?"))

            # Кнопки
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            if len(self.buttons) > 2:
                self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
                self.buttons[2].SetLabel(loc.get("cancel_button", "Возврат"))
            else:
                self.buttons[1].SetLabel(loc.get("cancel_button", "Возврат"))
            self.branch_button.SetLabel(loc.get("branch_button", "Наличие отвода"))

            apply_styles_to_panel(self)  # Обновляем стили после смены языка
            self.Layout()  # Перестраиваем макет для корректного отображения
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")

if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса, поведения кнопок и формирования словаря данных.
    Выполняет явный вызов at_point_input для выбора точки в AutoCAD и выводит словарь данных в исходном виде.
    """
    import logging
    logging.basicConfig(
        level=logging.INFO,
        filename="at_cad.log",
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ShellContentPanel", size=(1000, 700))
    panel = ShellContentPanel(frame)

    def on_ok_test(data):
        """
        Тестовая функция для обработки callback.
        Выводит собранные данные в консоль в виде словаря.
        """
        try:
            print("Собранные данные:", data)
            logging.info(f"Тестовый callback вызван с данными: {data}")
            # Симулируем задержку, как в реальной обработке
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
        Тестовая функция для обработки нажатия 'ОК'.
        Выполняет выбор точки через at_point_input, проверяет валидацию данных,
        вызывает callback и выводит словарь данных.
        """
        try:
            if panel.IsBeingDeleted():
                print("Окно уничтожено перед обработкой ОК")
                logging.warning("Окно уничтожено перед обработкой ОК")
                return

            from programs.at_input import at_point_input
            from config.at_cad_init import ATCadInit
            from windows.at_window_utils import update_status_bar_point_selected

            # Собираем данные
            data = panel.collect_input_data()

            # Запрашиваем точку вставки
            cad = ATCadInit()
            frame.Iconize(True)
            try:
                pt = at_point_input(cad.document, prompt=loc.get("point_prompt", "Введите точку вставки оболочки"), as_variant=False)
            except Exception as e:
                logging.error(f"Ошибка при вызове at_point_input: {str(e)}")
                show_popup(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), popup_type="error")
                pt = None

            frame.Iconize(False)
            frame.Raise()
            frame.SetFocus()

            if not pt:
                logging.error("Точка не выбрана")
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            # Обновляем точку в данных
            panel.insert_point = pt
            data["insert_point"] = pt
            update_status_bar_point_selected(panel, pt)

            # Проверяем валидность данных
            if not panel.validate_input(data):
                print("Валидация не пройдена")
                logging.info("Валидация данных не пройдена")
                return

            # Передаем данные в callback
            panel.on_submit_callback = on_ok_test
            if not panel.IsBeingDeleted():
                wx.CallAfter(panel.process_input, data)  # Отложенный вызов callback
                logging.info("Данные переданы в callback отложенно")
            else:
                print("Окно уничтожено после нажатия ОК")
                logging.warning("Окно уничтожено в тестовом режиме")
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")
            logging.error(f"Ошибка в тестовом запуске: {e}")
        finally:
            if not frame.IsBeingDeleted():
                frame.Iconize(False)
                frame.Raise()
                frame.SetFocus()
            logging.getLogger().handlers[0].flush()

    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_event)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()

