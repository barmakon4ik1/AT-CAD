# windows/at_head_input_window.py
"""
Модуль для создания диалогового окна ввода параметров днища.
Позволяет выбрать точку вставки и параметры, возвращая данные для построения.
"""

import wx
from typing import Optional, Dict, List
from config.at_config import BACKGROUND_COLOR, LANGUAGE
from locales.at_localization_class import loc, Localization
from programms.at_data_manager import data_manager
from windows.at_window_utils import BaseInputWindow, CanvasPanel, show_popup, get_standard_font, create_standard_buttons, create_window

loc.language = LANGUAGE


def get_h1_values(head_type: str, s: str, config: Dict) -> List[str]:
    """
    Возвращает допустимые значения высоты h1 для типа днища и толщины.

    Args:
        head_type: Тип днища (например, 'DIN 28011').
        s: Толщина материала.
        config: Данные конфигурации.

    Returns:
        list: Список строковых значений h1.
    """
    try:
        h1_table = config.get("h1_table", {}).get(head_type, [])
        s_val = float(s) if s.strip() else 5.0
        for entry in h1_table:
            min_s = entry.get("min_s", float("-inf"))
            max_s = entry.get("max_s", float("inf"))
            if min_s <= s_val <= max_s:
                return [str(entry["h1"])]
        return ["20"]
    except Exception:
        return ["20"]


class HeadInputWindow(BaseInputWindow):
    """
    Диалоговое окно для ввода параметров днища.
    """

    def __init__(self, parent=None):
        """
        Инициализирует окно и элементы управления.

        Args:
            parent: Родительское окно (например, MainWindow).
        """
        super().__init__(title_key="window_title_head", last_input_file="last_head_input.json", window_size=(1200, 650),
                         parent=parent)
        self.config = self.common_data  # Используем common_data из BaseInputWindow
        self.setup_ui()
        self.panel.Layout()
        self.Fit()
        right_sizer_size = self.right_sizer.GetMinSize()
        left_sizer_size = self.left_sizer.GetMinSize()
        status_bar_height = self.GetStatusBar().GetSize()[1] if self.GetStatusBar() else 20
        window_width = 1200
        window_height = max(right_sizer_size[1], left_sizer_size[1]) + 60 + status_bar_height
        self.SetSize((window_width, window_height))
        self.SetMinSize((window_width, window_height))
        self.SetMaxSize((window_width, window_height))
        self.Centre()

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса.
        """
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.canvas = CanvasPanel(self.panel, "head_image.png", size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self.panel, self.on_select_point, self.on_ok, self.on_cancel)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        self.adjust_button_widths()
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()

        D_label = wx.StaticText(self.panel, label=loc.get("diameter_label"))
        D_label.SetFont(font)
        D_label.SetForegroundColour(wx.Colour("white"))
        D_data_source = self.config.get("fields", [{}])[1].get("data_source", "")
        D_options = data_manager.get_data(D_data_source)
        self.D_combo = wx.ComboBox(self.panel, choices=D_options, value="1000",
                                   style=wx.CB_DROPDOWN, size=(200, -1))
        self.D_combo.SetFont(font)
        self.right_sizer.Add(D_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.D_combo, 0, wx.ALL, 5)

        s_label = wx.StaticText(self.panel, label=loc.get("thickness_label"))
        s_label.SetFont(font)
        s_data_source = self.config.get("fields", [{}])[2].get("data_source", "")
        s_options = data_manager.get_data(s_data_source)
        self.s_combo = wx.ComboBox(self.panel, choices=s_options, value="5",
                                   style=wx.CB_DROPDOWN, size=(200, -1))
        self.s_combo.SetFont(font)
        self.s_combo.Bind(wx.EVT_COMBOBOX, self.on_s_change)
        self.right_sizer.Add(s_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.s_combo, 0, wx.ALL, 5)

        head_type_label = wx.StaticText(self.panel, label=loc.get("head_type_label"))
        head_type_label.SetFont(font)
        head_type_options = self.config.get("fields", [{}])[0].get("options", [])
        self.head_type_combo = wx.ComboBox(self.panel, choices=head_type_options, value="DIN 28011",
                                           style=wx.CB_READONLY, size=(200, -1))
        self.head_type_combo.SetFont(font)
        self.head_type_combo.Bind(wx.EVT_COMBOBOX, self.on_head_type_change)
        self.right_sizer.Add(head_type_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.head_type_combo, 0, wx.ALL, 5)

        h1_label = wx.StaticText(self.panel, label=loc.get("height_h1_label"))
        h1_label.SetFont(font)
        self.h1_combo = wx.ComboBox(self.panel, choices=get_h1_values("DIN 28011", "5", self.config),
                                    value="20", style=wx.CB_DROPDOWN, size=(200, -1))
        self.h1_combo.SetFont(font)
        self.right_sizer.Add(h1_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.h1_combo, 0, wx.ALL, 5)

        R_label = wx.StaticText(self.panel, label=loc.get("radius_R_label"))
        R_label.SetFont(font)
        self.R_input = wx.TextCtrl(self.panel, value="", size=(200, -1))
        self.R_input.SetFont(font)
        self.R_input.Enable(False)
        self.right_sizer.Add(R_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.R_input, 0, wx.ALL, 5)

        r_label = wx.StaticText(self.panel, label=loc.get("radius_r_label"))
        r_label.SetFont(font)
        self.r_input = wx.TextCtrl(self.panel, value="", size=(200, -1))
        self.r_input.SetFont(font)
        self.r_input.Enable(False)
        self.right_sizer.Add(r_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.r_input, 0, wx.ALL, 5)

        layer_label = wx.StaticText(self.panel, label=loc.get("layer_label"))
        layer_label.SetFont(font)
        layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text",
                         loc.get("add_custom_layer")]
        self.layer_combo = wx.ComboBox(self.panel, choices=layer_options, value="0",
                                       style=wx.CB_DROPDOWN, size=(200, -1))
        self.layer_combo.SetFont(font)
        self.layer_combo.Bind(wx.EVT_COMBOBOX, self.on_layer_change)
        self.layer_combo.Bind(wx.EVT_TEXT, self.on_layer_text_change)
        self.right_sizer.Add(layer_label, 0, wx.ALL, 5)
        self.right_sizer.Add(self.layer_combo, 0, wx.ALL, 5)
        self.selected_layer = self.layer_combo.GetValue()

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.panel.SetSizer(main_sizer)
        self.on_head_type_change(None)

    def on_layer_change(self, event: wx.Event) -> None:
        """
        Обрабатывает выбор слоя в выпадающем списке.

        Args:
            event: Событие выбора.
        """
        selected = self.layer_combo.GetValue()
        if selected == loc.get("add_custom_layer"):
            self.layer_combo.SetValue("")
        self.selected_layer = self.layer_combo.GetValue()

    def on_layer_text_change(self, event: wx.Event) -> None:
        """
        Обрабатывает ввод текста в поле слоя.

        Args:
            event: Событие ввода текста.
        """
        self.selected_layer = self.layer_combo.GetValue()

    def on_head_type_change(self, event: Optional[wx.Event]) -> None:
        """
        Обновляет параметры при изменении типа днища.

        Args:
            event: Событие выбора типа (может быть None).
        """
        head_type = self.head_type_combo.GetValue()
        s = self.s_combo.GetValue() or "5"
        D = self.D_combo.GetValue() or "1000"
        self.h1_combo.SetItems(get_h1_values(head_type, s, self.config))
        self.h1_combo.SetValue(self.h1_combo.GetItems()[0] if self.h1_combo.GetItems() else "20")
        self.R_input.Enable(head_type == "Custom")
        self.r_input.Enable(head_type == "Custom")
        if head_type != "Custom":
            try:
                head_config = self.config.get("head_types", {})
                D_val = float(D.replace(',', '.'))
                s_val = float(s.replace(',', '.'))
                R_expr = head_config.get(head_type, {}).get("R")
                r_expr = head_config.get(head_type, {}).get("r")
                R = eval(R_expr, {"D": D_val, "s": s_val}) if R_expr else ""
                r = eval(r_expr, {"D": D_val, "s": s_val}) if r_expr else ""
                self.R_input.SetValue(str(R) if R != "" else "")
                self.r_input.SetValue(str(r) if r != "" else "")
            except Exception:
                self.R_input.SetValue("")
                self.r_input.SetValue("")
                show_popup(loc.get("error_in_function", "on_head_type_change", ""), popup_type="error")
        else:
            self.R_input.SetValue("")
            self.r_input.SetValue("")

    def on_s_change(self, event: wx.Event) -> None:
        """
        Обновляет параметры при изменении толщины.

        Args:
            event: Событие выбора толщины.
        """
        head_type = self.head_type_combo.GetValue()
        s = self.s_combo.GetValue() or "5"
        D = self.D_combo.GetValue() or "1000"
        self.h1_combo.SetItems(get_h1_values(head_type, s, self.config))
        self.h1_combo.SetValue(self.h1_combo.GetItems()[0] if self.h1_combo.GetItems() else "20")
        if head_type != "Custom":
            try:
                head_config = self.config.get("head_types", {})
                D_val = float(D.replace(',', '.'))
                s_val = float(s.replace(',', '.'))
                R_expr = head_config.get(head_type, {}).get("R")
                r_expr = head_config.get(head_type, {}).get("r")
                R = eval(R_expr, {"D": D_val, "s": s_val}) if R_expr else ""
                r = eval(r_expr, {"D": D_val, "s": s_val}) if r_expr else ""
                self.R_input.SetValue(str(R) if R != "" else "")
                self.r_input.SetValue(str(r) if r != "" else "")
            except Exception:
                self.R_input.SetValue("")
                self.r_input.SetValue("")
                show_popup(loc.get("error_in_function", "on_s_change", ""), popup_type="error")

    def on_ok(self, event: wx.Event) -> None:
        """
        Сохраняет введённые данные и закрывает окно.

        Args:
            event: Событие нажатия кнопки OK.
        """
        if not self.insert_point:
            show_popup(loc.get("insert_point_not_selected"), popup_type="error")
            return
        try:
            self.result = {
                "D": float(self.D_combo.GetValue().replace(',', '.')),
                "s": float(self.s_combo.GetValue().replace(',', '.')),
                "h1": float(self.h1_combo.GetValue().replace(',', '.')),
                "head_type": self.head_type_combo.GetValue(),
                "insert_point": self.insert_point,
                "layer": self.selected_layer if self.selected_layer.strip() else "0",
                "adoc": self.adoc
            }
            if self.result["head_type"] == "Custom":
                self.result["R"] = float(self.R_input.GetValue().replace(',', '.'))
                self.result["r"] = float(self.r_input.GetValue().replace(',', '.'))
            else:
                head_config = self.config.get("head_types", {})
                try:
                    R_expr = head_config.get(self.result["head_type"], {}).get("R")
                    r_expr = head_config.get(self.result["head_type"], {}).get("r")
                    self.result["R"] = eval(R_expr, {"D": self.result["D"], "s": self.result["s"]}) if R_expr else 0
                    self.result["r"] = eval(r_expr, {"D": self.result["D"], "s": self.result["s"]}) if r_expr else 0
                except Exception:
                    self.result["R"] = 0
                    self.result["r"] = 0
            if self.GetParent():
                self.GetParent().Iconize(False)
                self.GetParent().Raise()
                self.GetParent().SetFocus()
            self.Close()
        except Exception:
            show_popup(loc.get("build_error", ""), popup_type="error")
