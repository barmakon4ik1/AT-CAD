"""
Модуль для создания панели для ввода параметров днища.
"""

import wx
import logging
import os
from typing import Optional, Dict, List
from pyautocad import APoint

from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel, 
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings
)
from programms.at_data_manager import config_manager, common_data_manager
from programms.at_addhead import at_add_head

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров днища.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров днища.
    """
    try:
        panel = HeadContentPanel(parent)
        logging.info("Панель HeadContentPanel создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания HeadContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели днища: {str(e)}"), popup_type="error")
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

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
        """
        super().__init__(parent)
        self.settings = load_user_settings()
        self.SetBackgroundColour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None
        self.config = config_manager.data
        self.update_status_bar_no_point()
        self.setup_ui()
        self.D_combo.SetFocus()

    def update_status_bar_no_point(self):
        """
        Обновляет статусную строку, если точка не выбрана.
        """
        self.update_status_bar_point_selected(None)

    def update_status_bar_point_selected(self, point):
        """
        Обновляет статусную строку с координатами выбранной точки.

        Args:
            point: Координаты точки вставки (APoint или None).
        """
        update_status_bar_point_selected(self, point)
        logging.debug(f"Статусная строка обновлена: точка {point}")

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
        image_path = os.path.abspath(HEAD_IMAGE_PATH)
        if not os.path.exists(image_path):
            logging.warning(f"Файл изображения днища '{image_path}' не найден")

        # Изображение днища
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()

        # Группа "Параметры днища"
        params_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("head_params_label", "Параметры"))
        params_box = params_sizer.GetStaticBox()
        params_box.SetFont(font)
        self.static_boxes["params"] = params_box

        # Диаметр (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(params_box, label=loc.get("diameter_label", "Диаметр (D), мм"))
        D_label.SetFont(font)
        self.labels["D"] = D_label
        fields = self.config.get("fields", [{}])
        D_data_source = fields[1].get("data_source", "dimensions.diameters") if len(fields) > 1 else "dimensions.diameters"
        D_options = common_data_manager.get_data(D_data_source) or []
        default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
        self.D_combo = wx.ComboBox(params_box, choices=D_options, value=default_D, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.D_combo.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_combo, 0, wx.ALL, 5)
        params_sizer.Add(D_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина (s)
        s_sizer = wx.BoxSizer(wx.HORIZONTAL)
        s_label = wx.StaticText(params_box, label=loc.get("thickness_label", "Толщина (s)"))
        s_label.SetFont(font)
        self.labels["s"] = s_label
        s_data_source = fields[2].get("data_source", "dimensions.thicknesses") if len(fields) > 2 else "dimensions.thicknesses"
        s_options = common_data_manager.get_data(s_data_source) or []
        default_s = "5" if "5" in s_options else s_options[0] if s_options else ""
        self.s_combo = wx.ComboBox(params_box, choices=s_options, value=default_s, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.s_combo.SetFont(font)
        self.s_combo.Bind(wx.EVT_COMBOBOX, self.on_s_change)
        s_sizer.AddStretchSpacer()
        s_sizer.Add(s_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        s_sizer.Add(self.s_combo, 0, wx.ALL, 5)
        params_sizer.Add(s_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Тип головы
        head_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        head_type_label = wx.StaticText(params_box, label=loc.get("head_type_label", "Тип Heads"))
        head_type_label.SetFont(font)
        self.labels["head_type"] = head_type_label
        head_type_options = fields[0].get("options", ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103", "Custom"]) if len(fields) > 0 else ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103", "Custom"]
        self.head_type_combo = wx.ComboBox(params_box, choices=head_type_options, value="DIN 28011", style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
        self.head_type_combo.SetFont(font)
        self.head_type_combo.Bind(wx.EVT_COMBOBOX, self.on_head_type_change)
        head_type_sizer.AddStretchSpacer()
        head_type_sizer.Add(head_type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        head_type_sizer.Add(self.head_type_combo, 0, wx.ALL, 5)
        params_sizer.Add(head_type_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Высота (h1)
        h1_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h1_label = wx.StaticText(params_box, label=loc.get("height_h1_label", "Высота (h1)"))
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
        R_label = wx.StaticText(params_box, label=loc.get("radius_R_label", "Радиус (R)"))
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
        r_label = wx.StaticText(params_box, label=loc.get("radius_r_label", "Радиус (r)"))
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
        self.selected_layer = self.layer_combo.GetValue()
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
        logging.info("Интерфейс HeadContentPanel настроен")

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["params"].SetLabel(loc.get("head_params_label", "Параметры"))
        self.labels["D"].SetLabel(loc.get("diameter_label", "Диаметр (D), мм"))
        self.labels["s"].SetLabel(loc.get("thickness_label", "Толщина (s)"))
        self.labels["head_type"].SetLabel(loc.get("head_type_label", "Тип Heads"))
        self.labels["h1"].SetLabel(loc.get("height_h1_label", "Высота (h1)"))
        self.labels["R"].SetLabel(loc.get("radius_R_label", "Радиус (R)"))
        self.labels["r"].SetLabel(loc.get("radius_r_label", "Радиус (r)"))
        self.labels["layer"].SetLabel(loc.get("layer_label", "Слой"))

        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Отмена"][i]))
        adjust_button_widths(self.buttons)

        layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text", loc.get("add_custom_layer", "Добавить пользовательский слой")]
        current_layer = self.layer_combo.GetValue()
        self.layer_combo.SetItems(layer_options)
        self.layer_combo.SetValue(current_layer if current_layer in layer_options else "0")
        self.selected_layer = self.layer_combo.GetValue()

        self.update_status_bar_no_point()
        self.Layout()
        logging.info("Язык UI обновлён")

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
        logging.debug(f"Выбран слой: {self.selected_layer}")

    def on_layer_text_change(self, event: wx.Event) -> None:
        """
        Обрабатывает ввод текста в поле слоя.

        Args:
            event: Событие ввода текста.
        """
        self.selected_layer = self.layer_combo.GetValue()
        logging.debug(f"Введён пользовательский слой: {self.selected_layer}")

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
                    D_val = float(D.replace(',', '.'))
                    s_val = float(s.replace(',', '.'))
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
            show_popup(loc.get("error", f"Ошибка обновления параметров: {str(e)}"), popup_type="error")

    def on_s_change(self, event: wx.Event) -> None:
        """
        Обновляет параметры при изменении толщины.

        Args:
            event: Событие выбора толщины.
        """
        self.on_head_type_change(None)

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.

        Returns:
            dict: Словарь с данными (D, s, h1, head_type, insert_point, layer, R, r) или None при ошибке.
        """
        try:
            D = self.D_combo.GetValue().strip()
            s = self.s_combo.GetValue().strip()
            h1 = self.h1_combo.GetValue().strip()
            head_type = self.head_type_combo.GetValue()
            layer = self.selected_layer if self.selected_layer.strip() else "0"

            data = {
                "D": float(D.replace(',', '.')) if D else None,
                "s": float(s.replace(',', '.')) if s else None,
                "h1": float(h1.replace(',', '.')) if h1 else None,
                "head_type": head_type,
                "insert_point": self.insert_point,
                "layer": layer
            }

            if head_type == "Custom":
                R = self.R_input.GetValue().strip()
                r = self.r_input.GetValue().strip()
                data["R"] = float(R.replace(',', '.')) if R else None
                data["r"] = float(r.replace(',', '.')) if r else None
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
            if not data or any(data[key] is None for key in ["D", "s", "h1"]):
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                logging.error("Не все обязательные поля заполнены (D, s, h1)")
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
            show_popup(loc.get("error", f"Неверный формат данных: {str(e)}"), popup_type="error")
            return False

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает данные для построения днища.

        Args:
            data: Словарь с данными из полей ввода.

        Returns:
            bool: True, если построение успешно, иначе False.
        """
        try:
            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            from programms.at_input import at_point_input
            point = at_point_input()
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            if point and hasattr(point, "x") and hasattr(point, "y"):
                self.insert_point = point
                self.update_status_bar_point_selected(point)
                data["insert_point"] = self.insert_point
                logging.info(f"Точка вставки выбрана: x={point.x}, y={point.y}")
            else:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                logging.error(f"Точка вставки не выбрана: {point}")
                return False

            cad = ATCadInit()
            if not cad.is_initialized():
                show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
                logging.error("Не удалось инициализировать AutoCAD")
                return False

            success = at_add_head(
                D=data["D"],
                s=data["s"],
                R=data["R"],
                r=data["r"],
                h1=data["h1"],
                insert_point=data["insert_point"],
                layer=data["layer"],
                adoc=cad.adoc
            )
            if success:
                cad.adoc.Regen(0)
                logging.info("Днище успешно построено")
                self.clear_input_fields()
            else:
                show_popup(loc.get("heads_error", "Ошибка построения днища"), popup_type="error")
                logging.error("Ошибка построения днища")
            return success
        except Exception as e:
            logging.error(f"Ошибка в process_input: {e}")
            show_popup(loc.get("heads_error", f"Ошибка построения днища: {str(e)}"), popup_type="error")
            return False

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.
        """
        D_options = common_data_manager.get_data("dimensions.diameters") or []
        default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
        s_options = common_data_manager.get_data("dimensions.thicknesses") or []
        default_s = "5" if "5" in s_options else s_options[0] if s_options else ""
        self.D_combo.SetValue(default_D)
        self.s_combo.SetValue(default_s)
        self.head_type_combo.SetValue("DIN 28011")
        self.h1_combo.SetValue("20")
        self.R_input.SetValue("")
        self.r_input.SetValue("")
        self.layer_combo.SetValue("0")
        self.selected_layer = "0"
        if hasattr(self, "insert_point"):
            del self.insert_point
        self.update_status_bar_no_point()
        self.D_combo.SetFocus()
        self.on_head_type_change(None)
        logging.info("Поля ввода очищены")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и построения днища.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест HeadContentPanel", size=(800, 600))
    panel = HeadContentPanel(frame)

    # Установка тестовых данных
    panel.D_combo.SetValue("1000")
    panel.s_combo.SetValue("5")
    panel.head_type_combo.SetValue("DIN 28011")
    panel.h1_combo.SetValue("20")
    panel.layer_combo.SetValue("0")

    # Тест выбора точки и построения
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            logging.error("Не удалось инициализировать AutoCAD")
            print("Ошибка: Не удалось инициализировать AutoCAD")
        else:
            adoc = cad.adoc
            print(f"AutoCAD Version: {adoc.Application.Version}")
            print(f"Active Document: {adoc.Name}")

            test_point = APoint(0.0, 0.0)
            panel.insert_point = test_point
            panel.update_status_bar_point_selected(test_point)
            print(f"Тест с фиксированной точкой: {test_point}")

            data = {
                "D": 1000.0,
                "s": 5.0,
                "h1": 20.0,
                "R": 1000.0,
                "r": 100.0,
                "head_type": "DIN 28011",
                "insert_point": test_point,
                "layer": "0"
            }
            success = at_add_head(
                D=data["D"],
                s=data["s"],
                R=data["R"],
                r=data["r"],
                h1=data["h1"],
                insert_point=data["insert_point"],
                layer=data["layer"],
                adoc=adoc
            )
            if success:
                print("Днище построено успешно")
                adoc.Regen(0)
            else:
                print("Ошибка построения днища")

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
        logging.error(f"Ошибка в тестовом запуске: {e}")

    frame.Show()
    app.MainLoop()
