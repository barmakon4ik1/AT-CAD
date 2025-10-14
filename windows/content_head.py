"""
windows/content_head.py
Модуль для создания панели для ввода параметров днища.
"""

import wx
import logging
import os
from typing import Optional, Dict, List
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_translations import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data
)
from programs.at_input import at_point_input

# Настройка логирования только для критических ошибок
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
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
    "head_params_label": {
        "ru": "Параметры днища",
        "de": "Kopfparameter",
        "en": "Head Parameters"
    },
    "diameter_label": {
        "ru": "Диаметр (D), мм",
        "de": "Durchmesser (D), mm",
        "en": "Diameter (D), mm"
    },
    "thickness_label": {
        "ru": "Толщина (s), мм",
        "de": "Dicke (s), mm",
        "en": "Thickness (s), mm"
    },
    "head_type_label": {
        "ru": "Тип днища",
        "de": "Kopftyp",
        "en": "Head Type"
    },
    "height_h1_label": {
        "ru": "Высота (h1), мм",
        "de": "Höhe (h1), mm",
        "en": "Height (h1), mm"
    },
    "radius_R_label": {
        "ru": "Радиус (R), мм",
        "de": "Radius (R), mm",
        "en": "Radius (R), mm"
    },
    "radius_r_label": {
        "ru": "Радиус (r), мм",
        "de": "Radius (r), mm",
        "en": "Radius (r), mm"
    },
    "layer_label": {
        "ru": "Слой",
        "de": "Layer",
        "en": "Layer"
    },
    "add_custom_layer": {
        "ru": "Добавить пользовательский слой",
        "de": "Benutzerdefiniertes Layer hinzufügen",
        "en": "Add Custom Layer"
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
    "error_diameter_positive": {
        "ru": "Диаметр (D) должен быть положительным",
        "de": "Durchmesser (D) muss positiv sein",
        "en": "Diameter (D) must be positive"
    },
    "error_thickness_positive": {
        "ru": "Толщина (s) должна быть положительной",
        "de": "Dicke (s) muss positiv sein",
        "en": "Thickness (s) must be positive"
    },
    "error_height_positive": {
        "ru": "Высота (h1) должна быть положительной",
        "de": "Höhe (h1) muss positiv sein",
        "en": "Height (h1) must be positive"
    },
    "error_radii_required": {
        "ru": "Для типа 'Custom' требуются значения R и r",
        "de": "Für Typ 'Custom' sind Werte für R und r erforderlich",
        "en": "For 'Custom' type, R and r values are required"
    },
    "error_radii_positive": {
        "ru": "Радиусы R и r должны быть положительными",
        "de": "Radien R und r müssen positiv sein",
        "en": "Radii R and r must be positive"
    },
    "invalid_number_format_error": {
        "ru": "Неверный формат числа",
        "de": "Ungültiges Zahlenformat",
        "en": "Invalid number format"
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
    "heads_error": {
        "ru": "Ошибка построения днища",
        "de": "Fehler beim Erstellen des Kopfes",
        "en": "Error building head"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров днища.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров днища или None при ошибке.
    """
    try:
        panel = HeadContentPanel(parent)
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания HeadContentPanel: {e}")
        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        return None


def get_h1_values(head_type: str, s: str, config: Dict) -> List[str]:
    """
    Возвращает допустимые значения высоты h1 для типа днища и толщины.

    Args:
        head_type: Тип днища (например, 'DIN 28011').
        s: Толщина материала (строка, например, '5').
        config: Данные конфигурации из config.json.

    Returns:
        list: Список строковых значений h1.
    """
    try:
        h1_table = config.get("h1_table", {}).get(head_type, [])
        s_val = float(s.replace(',', '.')) if s.strip() else 5.0
        for entry in h1_table:
            min_s = entry.get("min_s", float("-inf"))
            max_s = entry.get("max_s", float("inf"))
            if min_s <= s_val <= max_s:
                return [str(entry["h1"])]
        return ["20"]
    except Exception as e:
        logging.error(f"Ошибка получения значений h1 для head_type={head_type}, s={s}: {e}")
        return ["20"]


class HeadContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров днища.
    """

    def __init__(self, parent, callback=None):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
            callback: Функция обратного вызова для передачи данных.
        """
        super().__init__(parent)
        self.settings = load_user_settings()
        self.SetBackgroundColour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None
        self.config = load_common_data()
        self.selected_layer = "0"
        self.setup_ui()
        self.D_combo.SetFocus()

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

        # Изображение днища
        self.canvas = CanvasPanel(self, image_file=str(HEAD_IMAGE_PATH), size=(600, 400))
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

        # Загрузка common_data
        common_data = load_common_data()

        # Группа "Параметры днища"
        params_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("head_params_label", "Параметры днища"))
        params_box = params_sizer.GetStaticBox()
        params_box.SetFont(font)
        self.static_boxes["params"] = params_box

        # Диаметр (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(params_box, label=loc.get("diameter_label", "Диаметр (D), мм"))
        D_label.SetFont(font)
        self.labels["D"] = D_label
        D_options = common_data.get("diameters", []) or []
        default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
        self.D_combo = wx.ComboBox(params_box, choices=D_options, value=default_D, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.D_combo.SetFont(font)
        self.D_combo.Bind(wx.EVT_COMBOBOX, self.on_D_change)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_combo, 0, wx.ALL, 5)
        params_sizer.Add(D_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина (s)
        s_sizer = wx.BoxSizer(wx.HORIZONTAL)
        s_label = wx.StaticText(params_box, label=loc.get("thickness_label", "Толщина (s), мм"))
        s_label.SetFont(font)
        self.labels["s"] = s_label
        s_options = common_data.get("thicknesses", []) or []
        default_s = "5" if "5" in s_options or "5.0" in s_options else s_options[0] if s_options else ""
        self.s_combo = wx.ComboBox(params_box, choices=s_options, value=default_s, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.s_combo.SetFont(font)
        self.s_combo.Bind(wx.EVT_COMBOBOX, self.on_s_change)
        s_sizer.AddStretchSpacer()
        s_sizer.Add(s_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        s_sizer.Add(self.s_combo, 0, wx.ALL, 5)
        params_sizer.Add(s_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Тип днища
        head_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        head_type_label = wx.StaticText(params_box, label=loc.get("head_type_label", "Тип днища"))
        head_type_label.SetFont(font)
        self.labels["head_type"] = head_type_label
        head_type_options = list(self.config.get("head_types", {}).keys()) or ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103", "Custom"]
        self.head_type_combo = wx.ComboBox(params_box, choices=head_type_options, value="DIN 28011", style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
        self.head_type_combo.SetFont(font)
        self.head_type_combo.Bind(wx.EVT_COMBOBOX, self.on_head_type_change)
        head_type_sizer.AddStretchSpacer()
        head_type_sizer.Add(head_type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        head_type_sizer.Add(self.head_type_combo, 0, wx.ALL, 5)
        params_sizer.Add(head_type_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Высота (h1)
        h1_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h1_label = wx.StaticText(params_box, label=loc.get("height_h1_label", "Высота (h1), мм"))
        h1_label.SetFont(font)
        self.labels["h1"] = h1_label
        self.h1_combo = wx.ComboBox(params_box, choices=get_h1_values("DIN 28011", default_s, self.config), value="20", style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.h1_combo.SetFont(font)
        h1_sizer.AddStretchSpacer()
        h1_sizer.Add(h1_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        h1_sizer.Add(self.h1_combo, 0, wx.ALL, 5)
        params_sizer.Add(h1_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Радиус R
        R_sizer = wx.BoxSizer(wx.HORIZONTAL)
        R_label = wx.StaticText(params_box, label=loc.get("radius_R_label", "Радиус (R), мм"))
        R_label.SetFont(font)
        self.labels["R"] = R_label
        self.R_input = wx.TextCtrl(params_box, value="", size=INPUT_FIELD_SIZE)
        self.R_input.SetFont(font)
        self.R_input.Enable(False)
        R_sizer.AddStretchSpacer()
        R_sizer.Add(R_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        R_sizer.Add(self.R_input, 0, wx.ALL, 5)
        params_sizer.Add(R_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Радиус r
        r_sizer = wx.BoxSizer(wx.HORIZONTAL)
        r_label = wx.StaticText(params_box, label=loc.get("radius_r_label", "Радиус (r), мм"))
        r_label.SetFont(font)
        self.labels["r"] = r_label
        self.r_input = wx.TextCtrl(params_box, value="", size=INPUT_FIELD_SIZE)
        self.r_input.SetFont(font)
        self.r_input.Enable(False)
        r_sizer.AddStretchSpacer()
        r_sizer.Add(r_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        r_sizer.Add(self.r_input, 0, wx.ALL, 5)
        params_sizer.Add(r_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Слой
        layer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        layer_label = wx.StaticText(params_box, label=loc.get("layer_label", "Слой"))
        layer_label.SetFont(font)
        self.labels["layer"] = layer_label
        layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text", loc.get("add_custom_layer", "Добавить пользовательский слой")]
        self.layer_combo = wx.ComboBox(params_box, choices=layer_options, value="0", style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.layer_combo.SetFont(font)
        self.layer_combo.Bind(wx.EVT_COMBOBOX, self.on_layer_change)
        self.layer_combo.Bind(wx.EVT_TEXT, self.on_layer_text_change)
        layer_sizer.AddStretchSpacer()
        layer_sizer.Add(layer_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        layer_sizer.Add(self.layer_combo, 0, wx.ALL, 5)
        params_sizer.Add(layer_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(params_sizer, 0, wx.EXPAND | wx.ALL, 10)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()
        self.on_head_type_change(None)

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода без обновления строки состояния и сохранения данных.

        Args:
            event: Событие нажатия кнопки.
        """
        try:
            self.clear_input_fields()
        except Exception as e:
            show_popup(loc.get("error", f"Ошибка при очистке полей: {str(e)}"), popup_type="error")

    def on_D_change(self, event: wx.Event) -> None:
        """
        Обновляет параметры при изменении диаметра.

        Args:
            event: Событие выбора диаметра.
        """
        self.on_head_type_change(None)

    def on_s_change(self, event: wx.Event) -> None:
        """
        Обновляет параметры при изменении толщины.

        Args:
            event: Событие выбора толщины.
        """
        self.on_head_type_change(None)

    def on_head_type_change(self, event: Optional[wx.Event]) -> None:
        """
        Обновляет параметры при изменении типа днища.

        Args:
            event: Событие выбора типа (может быть None).
        """
        try:
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
                    D_val = float(D.replace(',', '.')) if D else 1000.0
                    s_val = float(s.replace(',', '.')) if s else 5.0
                    R_expr = head_config.get(head_type, {}).get("R")
                    r_expr = head_config.get(head_type, {}).get("r")
                    R = eval(R_expr, {"D": D_val, "s": s_val}) if R_expr else ""
                    r = eval(r_expr, {"D": D_val, "s": s_val}) if r_expr else ""
                    self.R_input.SetValue(str(round(R, 2)) if R != "" else "")
                    self.r_input.SetValue(str(round(r, 2)) if r != "" else "")
                except Exception as e:
                    logging.error(f"Ошибка расчёта R/r для head_type={head_type}: {e}")
                    self.R_input.SetValue("")
                    self.r_input.SetValue("")
            else:
                self.R_input.SetValue("")
                self.r_input.SetValue("")
        except Exception as e:
            logging.error(f"Ошибка в on_head_type_change: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")

    def on_layer_change(self, event: wx.Event) -> None:
        """
        Обрабатывает выбор слоя.

        Args:
            event: Событие выбора.
        """
        selected = self.layer_combo.GetValue()
        if selected == loc.get("add_custom_layer", "Добавить пользовательский слой"):
            self.layer_combo.SetValue("")
        self.selected_layer = self.layer_combo.GetValue()

    def on_layer_text_change(self, event: wx.Event) -> None:
        """
        Обрабатывает ввод текста в поле слоя.

        Args:
            event: Событие ввода текста.
        """
        self.selected_layer = self.layer_combo.GetValue()

    def on_ok(self, event: wx.Event) -> Optional[Dict]:
        """
        Собирает данные из полей ввода и возвращает словарь с параметрами.

        Args:
            event: Событие нажатия кнопки "ОК".

        Returns:
            dict: Словарь с данными (D, s, h1, head_type, insert_point, layer, R, r) или None, если данные не собраны.
        """
        try:
            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            cad = ATCadInit()

            # Запрашиваем точку вставки, повторяя, пока не получим корректную
            point = None
            while not (isinstance(point, list) and len(point) == 3):
                point = at_point_input(cad.document, as_variant=False, prompt=loc.get("point_prompt", "Введите точку вставки днища"))

            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            self.insert_point = point
            data = self.collect_input_data()
            if data and self.on_submit_callback:
                self.on_submit_callback(data)
            return data
        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")
            return None

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.
        """
        common_data = load_common_data()
        D_options = common_data.get("diameters", []) or []
        default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
        s_options = common_data.get("thicknesses", []) or []
        default_s = "5" if "5" in s_options or "5.0" in s_options else s_options[0] if s_options else ""
        self.D_combo.SetValue(default_D)
        self.s_combo.SetValue(default_s)
        self.head_type_combo.SetValue("DIN 28011")
        self.h1_combo.SetValue("20")
        self.R_input.SetValue("")
        self.r_input.SetValue("")
        self.layer_combo.SetValue("0")
        self.selected_layer = "0"
        self.insert_point = None
        self.D_combo.SetFocus()

    def update_ui_language(self) -> None:
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["params"].SetLabel(loc.get("head_params_label", "Параметры днища"))
        self.labels["D"].SetLabel(loc.get("diameter_label", "Диаметр (D), мм"))
        self.labels["s"].SetLabel(loc.get("thickness_label", "Толщина (s), мм"))
        self.labels["head_type"].SetLabel(loc.get("head_type_label", "Тип днища"))
        self.labels["h1"].SetLabel(loc.get("height_h1_label", "Высота (h1), мм"))
        self.labels["R"].SetLabel(loc.get("radius_R_label", "Радиус (R), мм"))
        self.labels["r"].SetLabel(loc.get("radius_r_label", "Радиус (r), мм"))
        self.labels["layer"].SetLabel(loc.get("layer_label", "Слой"))

        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Возврат"][i]))
        adjust_button_widths(self.buttons)

        layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text", loc.get("add_custom_layer", "Добавить пользовательский слой")]
        current_layer = self.layer_combo.GetValue()
        self.layer_combo.SetItems(layer_options)
        self.layer_combo.SetValue(current_layer if current_layer in layer_options else "0")
        self.selected_layer = self.layer_combo.GetValue()

        update_status_bar_point_selected(self, self.insert_point)
        self.Layout()

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.

        Returns:
            dict: Словарь с данными (D, s, h1, head_type, insert_point, layer, R, r) или None при ошибке.
        """
        try:
            D = self.D_combo.GetValue().strip().replace(',', '.')
            s = self.s_combo.GetValue().strip().replace(',', '.')
            h1 = self.h1_combo.GetValue().strip().replace(',', '.')
            head_type = self.head_type_combo.GetValue()
            layer = self.selected_layer.strip() if self.selected_layer.strip() else "0"

            data = {
                "D": float(D) if D else None,
                "s": float(s) if s else None,
                "h1": float(h1) if h1 else None,
                "head_type": head_type,
                "insert_point": self.insert_point,
                "layer": layer
            }

            if head_type == "Custom":
                R = self.R_input.GetValue().strip().replace(',', '.')
                r = self.r_input.GetValue().strip().replace(',', '.')
                data["R"] = float(R) if R else None
                data["r"] = float(r) if r else None
            else:
                head_config = self.config.get("head_types", {})
                try:
                    R_expr = head_config.get(head_type, {}).get("R")
                    r_expr = head_config.get(head_type, {}).get("r")
                    data["R"] = eval(R_expr, {"D": data["D"], "s": data["s"]}) if R_expr and data["D"] and data["s"] else 0
                    data["r"] = eval(r_expr, {"D": data["D"], "s": data["s"]}) if r_expr and data["D"] and data["s"] else 0
                except Exception as e:
                    logging.error(f"Ошибка расчёта R/r для head_type={head_type}: {e}")
                    data["R"] = 0
                    data["r"] = 0

            return data
        except Exception as e:
            logging.error(f"Ошибка получения данных: {e}")
            return None

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введённых данных.

        Args:
            data: Словарь с данными из полей ввода.

        Returns:
            bool: True, если данные валидны, иначе False.
        """
        try:
            if not data or any(data[key] is None for key in ["D", "s", "h1", "insert_point"]):
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                logging.error("Не все обязательные поля заполнены (D, s, h1, insert_point)")
                return False

            if data["D"] <= 0:
                show_popup(loc.get("error_diameter_positive", "Диаметр (D) должен быть положительным"), popup_type="error")
                logging.error("Диаметр (D) должен быть положительным")
                return False
            if data["s"] <= 0:
                show_popup(loc.get("error_thickness_positive", "Толщина (s) должна быть положительной"), popup_type="error")
                logging.error("Толщина (s) должна быть положительной")
                return False
            if data["h1"] <= 0:
                show_popup(loc.get("error_height_positive", "Высота (h1) должна быть положительной"), popup_type="error")
                logging.error("Высота (h1) должна быть положительной")
                return False
            if data["head_type"] == "Custom":
                if data["R"] is None or data["r"] is None:
                    show_popup(loc.get("error_radii_required", "Для типа 'Custom' требуются значения R и r"), popup_type="error")
                    logging.error("Для типа 'Custom' требуются значения R и r")
                    return False
                if data["R"] <= 0 or data["r"] <= 0:
                    show_popup(loc.get("error_radii_positive", "Радиусы R и r должны быть положительными"), popup_type="error")
                    logging.error("Радиусы R и r должны быть положительными")
                    return False

            return True
        except Exception as e:
            logging.error(f"Ошибка валидации данных: {e}")
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            return False


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и вывода данных.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест HeadContentPanel", size=(800, 600))
    panel = HeadContentPanel(frame)

    def on_ok_test(event):
        """
        Тестовая функция для обработки нажатия "ОК".
        """
        try:
            data = panel.on_ok(event)
            if data:
                print("Собранные данные:", data)
            else:
                print("Ошибка: данные не собраны")
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")
            logging.error(f"Ошибка в тестовом запуске: {e}")

    # Привязываем тестовую функцию к кнопке "ОК"
    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_test)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
