"""
Модуль для создания диалогового окна ввода параметров развертки обечайки.
Предоставляет интерфейс для ввода данных о заказе, материале, диаметре, высоте, расположении сварного шва
и припуске на сварку. Возвращает словарь с параметрами для построения развертки обечайки в AutoCAD и текстовыми данными.
"""

import wx
from typing import Optional, Dict
from config.at_config import BACKGROUND_COLOR, LANGUAGE
from programs.at_construction import at_diameter
from locales.at_localization_class import loc
from windows.at_window_utils import BaseInputWindow, CanvasPanel, save_last_input, show_popup, get_standard_font, create_standard_buttons, create_window

loc.language = LANGUAGE


class ShellInputWindow(BaseInputWindow):
    """
    Диалоговое окно для ввода параметров развертки обечайки.
    """
    def __init__(self, parent=None):
        """
        Инициализирует окно, наследуя базовый класс BaseInputWindow.
        Настраивает интерфейс и устанавливает фокус на поле ввода номера заказа.
        """
        super().__init__(title_key="window_title_shell", last_input_file="last_shell_input.json", window_size=(1200, 750), parent=parent)
        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая wx.Notebook с двумя вкладками.
        """
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)
        self.notebook.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))

        shell_panel = wx.Panel(self.notebook)
        shell_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.notebook.AddPage(shell_panel, loc.get("shell_tab_label"))
        self.setup_shell_tab(shell_panel)

        fittings_panel = wx.Panel(self.notebook)
        fittings_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.notebook.AddPage(fittings_panel, loc.get("fittings_tab_label"))
        wx.StaticText(fittings_panel, label=loc.get("fittings_placeholder_label"),
                      pos=(10, 10)).SetFont(get_standard_font())

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.panel.SetSizer(main_sizer)
        self.panel.Layout()

    def setup_shell_tab(self, panel: wx.Panel) -> None:
        """
        Настраивает вкладку для ввода параметров обечайки.
        Создаёт левую часть (изображение и кнопки) и правую часть (поля ввода) без прокрутки.

        Args:
            panel: Родительская панель вкладки (wx.Panel).
        """
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левая часть: изображение
        self.canvas = CanvasPanel(panel, "shell_image.png", size=(600, 400))
        left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(panel, self.on_select_point, self.on_ok, self.on_cancel)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        self.adjust_button_widths()
        left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правая часть: поля ввода
        font = get_standard_font()
        input_size = (200, -1)
        spacing = 2

        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, loc.get("main_data_label"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)

        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label="К-№")
        order_label.SetFont(font)
        self.order_input = wx.TextCtrl(main_data_box, value=self.last_input.get("order_number", ""), size=input_size)
        self.order_input.SetFont(font)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=input_size)
        self.detail_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        order_sizer.Add(self.detail_input, 0)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, spacing)

        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label"))
        material_label.SetFont(font)
        material_options = self.common_data.get("material", ["Сталь", "Алюминий", "Нержавейка"])
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                         value=self.last_input.get("material", material_options[0] if material_options else ""),
                                         style=wx.CB_DROPDOWN, size=input_size)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        material_sizer.Add(self.material_combo, 0, wx.ALL, spacing)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, spacing)

        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label"))
        thickness_label.SetFont(font)
        thickness_options = self.common_data.get("thicknesses", ["1", "1.5", "2", "3", "4", "5", "6", "8", "10", "12", "14", "15"])
        last_thickness = str(self.last_input.get("thickness", "")).replace(',', '.')
        try:
            last_thickness_float = float(last_thickness)
            last_thickness = str(int(last_thickness_float)) if last_thickness_float.is_integer() else str(last_thickness_float)
        except ValueError:
            last_thickness = ""
        thickness_value = last_thickness if last_thickness in thickness_options else thickness_options[0] if thickness_options else ""
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options,
                                          value=thickness_value, style=wx.CB_DROPDOWN, size=input_size)
        self.thickness_combo.SetFont(font)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, spacing)
        main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, spacing)
        right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 5)

        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, loc.get("diameter"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)

        D_sizer = wx.BoxSizer(wx.VERTICAL)
        D_label = wx.StaticText(diameter_box, label="D, мм")
        D_label.SetFont(font)
        self.D_input = wx.TextCtrl(diameter_box, value="", size=input_size)
        self.D_input.SetFont(font)
        D_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_input_sizer.AddStretchSpacer()
        D_input_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        D_input_sizer.Add(self.D_input, 0, wx.ALL, spacing)
        D_sizer.Add(D_input_sizer, 0, wx.EXPAND)
        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label"), style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label"))
        self.D_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label"))
        self.D_inner.SetFont(font)
        self.D_middle.SetFont(font)
        self.D_outer.SetFont(font)
        self.D_inner.SetValue(True)
        D_radio_sizer.AddStretchSpacer()
        D_radio_sizer.Add(self.D_inner, 0, wx.RIGHT, spacing)
        D_radio_sizer.Add(self.D_middle, 0, wx.RIGHT, spacing)
        D_radio_sizer.Add(self.D_outer, 0, wx.RIGHT, spacing)
        D_sizer.Add(D_radio_sizer, 0, wx.EXPAND | wx.LEFT, 30)
        diameter_sizer.Add(D_sizer, 0, wx.ALL | wx.EXPAND, spacing)
        right_sizer.Add(diameter_sizer, 0, wx.EXPAND | wx.ALL, 5)

        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, loc.get("height_label"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)

        length_label = wx.StaticText(height_box, label="L, мм")
        offset_label = wx.StaticText(height_box, label="La, мм")
        length_label.SetFont(font)
        offset_label.SetFont(font)
        self.length_input = wx.TextCtrl(height_box, value="", size=input_size)
        self.offset_input = wx.TextCtrl(height_box, value="0", size=input_size)
        self.length_input.SetFont(font)
        self.offset_input.SetFont(font)

        length_sizer = wx.BoxSizer(wx.HORIZONTAL)
        length_sizer.AddStretchSpacer()
        length_sizer.Add(length_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        length_sizer.Add(self.length_input, 0, wx.ALL, spacing)
        height_sizer.Add(length_sizer, 0, wx.ALL | wx.EXPAND, spacing)

        offset_sizer = wx.BoxSizer(wx.HORIZONTAL)
        offset_sizer.AddStretchSpacer()
        offset_sizer.Add(offset_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        offset_sizer.Add(self.offset_input, 0, wx.ALL, spacing)
        height_sizer.Add(offset_sizer, 0, wx.ALL | wx.EXPAND, spacing)
        right_sizer.Add(height_sizer, 0, wx.EXPAND | wx.ALL, 5)

        seam_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, loc.get("seam_angle_label"))
        seam_box = seam_sizer.GetStaticBox()
        seam_box.SetFont(font)

        seam_angle_label = wx.StaticText(seam_box, label="a°")
        seam_angle_label.SetFont(font)
        self.seam_angle_input = wx.TextCtrl(seam_box, value="0", size=input_size)
        self.seam_angle_input.SetFont(font)

        seam_angle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        seam_angle_sizer.AddStretchSpacer()
        seam_angle_sizer.Add(seam_angle_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        seam_angle_sizer.Add(self.seam_angle_input, 0, wx.ALL, spacing)
        seam_sizer.Add(seam_angle_sizer, 0, wx.ALL | wx.EXPAND, spacing)

        seam_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.seam_clockwise = wx.RadioButton(seam_box, label=loc.get("clockwise_label"), style=wx.RB_GROUP)
        self.seam_counterclockwise = wx.RadioButton(seam_box, label=loc.get("counterclockwise_label"))
        self.seam_clockwise.SetFont(font)
        self.seam_counterclockwise.SetFont(font)
        self.seam_clockwise.SetValue(True)
        seam_radio_sizer.AddStretchSpacer()
        seam_radio_sizer.Add(self.seam_clockwise, 0, wx.RIGHT, spacing)
        seam_radio_sizer.Add(self.seam_counterclockwise, 0, wx.RIGHT, spacing)
        seam_sizer.Add(seam_radio_sizer, 0, wx.EXPAND | wx.LEFT, 30)
        right_sizer.Add(seam_sizer, 0, wx.EXPAND | wx.ALL, 5)

        allowance_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, loc.get("weld_allowance_label"))
        allowance_box = allowance_sizer.GetStaticBox()
        allowance_box.SetFont(font)

        top_allowance_label = wx.StaticText(allowance_box, label=loc.get("top_allowance_label"))
        bottom_allowance_label = wx.StaticText(allowance_box, label=loc.get("bottom_allowance_label"))
        top_allowance_label.SetFont(font)
        bottom_allowance_label.SetFont(font)
        allowance_options = [str(i) for i in range(11)]
        self.top_allowance_combo = wx.ComboBox(allowance_box, choices=allowance_options,
                                              value=self.last_input.get("top_allowance", "0"),
                                              style=wx.CB_DROPDOWN, size=input_size)
        self.bottom_allowance_combo = wx.ComboBox(allowance_box, choices=allowance_options,
                                                 value=self.last_input.get("bottom_allowance", "0"),
                                                 style=wx.CB_DROPDOWN, size=input_size)
        self.top_allowance_combo.SetFont(font)
        self.bottom_allowance_combo.SetFont(font)

        top_allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_allowance_sizer.AddStretchSpacer()
        top_allowance_sizer.Add(top_allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        top_allowance_sizer.Add(self.top_allowance_combo, 0, wx.ALL, spacing)
        allowance_sizer.Add(top_allowance_sizer, 0, wx.ALL | wx.EXPAND, spacing)

        bottom_allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_allowance_sizer.AddStretchSpacer()
        bottom_allowance_sizer.Add(bottom_allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, spacing)
        bottom_allowance_sizer.Add(self.bottom_allowance_combo, 0, wx.ALL, spacing)
        allowance_sizer.Add(bottom_allowance_sizer, 0, wx.ALL | wx.EXPAND, spacing)
        right_sizer.Add(allowance_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel_sizer.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 5)
        panel_sizer.Add(right_sizer, 0, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(panel_sizer)
        panel.Layout()

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет и сохраняет введённые данные, формирует результат и закрывает окно.
        """
        if not self.insert_point or not self.model:
            show_popup(loc.get("point_not_selected_error"), popup_type="error")
            return
        try:
            D = float(self.D_input.GetValue().replace(',', '.'))
            thickness = float(self.thickness_combo.GetValue().replace(',', '.'))
            length = float(self.length_input.GetValue().replace(',', '.'))
            offset = float(self.offset_input.GetValue().replace(',', '.'))
            seam_angle = float(self.seam_angle_input.GetValue().replace(',', '.'))
            top_allowance = float(self.top_allowance_combo.GetValue().replace(',', '.'))
            bottom_allowance = float(self.bottom_allowance_combo.GetValue().replace(',', '.'))

            if D <= 0:
                show_popup(loc.get("diameter_positive_error"), popup_type="error")
                return
            if thickness <= 0:
                show_popup(loc.get("thickness_positive_error"), popup_type="error")
                return
            if length <= 0:
                show_popup(loc.get("length_positive_error"), popup_type="error")
                return
            if offset < 0:
                show_popup(loc.get("offset_non_negative_error"), popup_type="error")
                return
            if seam_angle < 0 or seam_angle > 360:
                show_popup(loc.get("seam_angle_range_error"), popup_type="error")
                return
            if top_allowance < 0 or bottom_allowance < 0:
                show_popup(loc.get("allowance_non_negative_error"), popup_type="error")
                return

            D_type = "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer"
            diameter = at_diameter(D, thickness, D_type)
            if diameter <= 0:
                show_popup(loc.get("diameter_result_positive_error"), popup_type="error")
                return

            seam_direction = "clockwise" if self.seam_clockwise.GetValue() else "counterclockwise"
            thickness_text = f"{thickness:.2f} {loc.get('mm')}"

            self.result = {
                "model": self.model,
                "input_point": self.insert_point,
                "diameter": diameter,
                "length": length,
                "offset": offset,
                "seam_angle": seam_angle,
                "seam_direction": seam_direction,
                "top_allowance": top_allowance,
                "bottom_allowance": bottom_allowance,
                "layer_name": self.selected_layer if self.selected_layer.strip() else "0",
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness_text": thickness_text
            }

            save_last_input("last_shell_input.json", {
                "order_number": self.order_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness": str(thickness),
                "top_allowance": self.top_allowance_combo.GetValue(),
                "bottom_allowance": self.bottom_allowance_combo.GetValue()
            })

            self.EndModal(wx.ID_OK)
        except ValueError:
            show_popup(loc.get("invalid_number_format_error"), popup_type="error")
