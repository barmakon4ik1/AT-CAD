# windows/content_head.py
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
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel, create_standard_buttons, adjust_button_widths,
    update_status_bar_point_selected
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
    logging.debug("Создание панели HeadContentPanel")
    try:
        panel = HeadContentPanel(parent)
        logging.info("Панель HeadContentPanel успешно создана")
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


class HeadContentPanel(wx.Panel):
    """
    Панель для ввода параметров днища.
    """

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
        """
        logging.debug("Инициализация HeadContentPanel")
        super().__init__(parent)
        self.settings = load_user_settings()  # Загружаем настройки
        background_color = self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
        self.SetBackgroundColour(background_color)
        self.parent = parent
        self.labels = {}  # Для хранения текстовых меток
        self.static_boxes = {}  # Для хранения StaticBox
        self.insert_point = None  # Точка вставки
        self.config = config_manager.data  # Загружаем config.json
        self.update_status_bar_no_point()
        self.setup_ui()
        self.D_combo.SetFocus()  # Фокус на поле диаметра

    def update_status_bar_no_point(self):
        """
        Обновляет статусную строку, если точка не выбрана.
        """
        update_status_bar_point_selected(self, None)
        logging.debug("Статусная строка обновлена: точка не выбрана")

    def update_status_bar_point_selected(self):
        """
        Обновляет статусную строку с координатами выбранной точки.
        """
        update_status_bar_point_selected(self, self.insert_point)
        logging.debug(f"Статусная строка обновлена: точка {self.insert_point}")

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями.
        """
        logging.debug("Настройка UI для HeadContentPanel")
        try:
            if self.GetSizer():
                self.GetSizer().Clear(True)
                self.SetSizer(None)  # Очистка текущего sizer'а
            self.labels.clear()
            self.static_boxes.clear()

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)

            # Проверка существования изображения
            image_path = os.path.abspath("images/head_image.png")
            if not os.path.exists(image_path):
                logging.warning(f"Файл изображения днища '{image_path}' не найден, продолжаем без изображения")

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
            # Извлечение data_source как строки
            fields = self.config.get("fields", [{}])
            D_data_source = fields[1].get("data_source", "dimensions.diameters") if len(fields) > 1 and isinstance(
                fields[1], dict) else "dimensions.diameters"
            if not isinstance(D_data_source, str):
                logging.error(
                    f"Некорректный data_source для диаметра: тип={type(D_data_source)}, значение={D_data_source}")
                D_data_source = "dimensions.diameters"
            D_options = common_data_manager.get_data(D_data_source)
            if not isinstance(D_options, list):
                logging.error(f"Некорректные данные диаметров: тип={type(D_options)}, значение={D_options}")
                D_options = []
            default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
            self.D_combo = wx.ComboBox(params_box, choices=D_options, value=default_D, style=wx.CB_DROPDOWN,
                                       size=INPUT_FIELD_SIZE)
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
            s_data_source = fields[2].get("data_source", "dimensions.thicknesses") if len(fields) > 2 and isinstance(
                fields[2], dict) else "dimensions.thicknesses"
            if not isinstance(s_data_source, str):
                logging.error(
                    f"Некорректный data_source для толщины: тип={type(s_data_source)}, значение={s_data_source}")
                s_data_source = "dimensions.thicknesses"
            s_options = common_data_manager.get_data(s_data_source)
            if not isinstance(s_options, list):
                logging.error(f"Некорректные данные толщин: тип={type(s_options)}, значение={s_options}")
                s_options = []
            default_s = "5" if "5" in s_options else s_options[0] if s_options else ""
            self.s_combo = wx.ComboBox(params_box, choices=s_options, value=default_s, style=wx.CB_DROPDOWN,
                                       size=INPUT_FIELD_SIZE)
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
            head_type_options = fields[0].get("options",
                                              ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103", "Custom"]) if len(
                fields) > 0 and isinstance(fields[0], dict) else ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103",
                                                                  "Custom"]
            if not isinstance(head_type_options, list):
                logging.error(
                    f"Некорректные данные типов головы: тип={type(head_type_options)}, значение={head_type_options}")
                head_type_options = ["DIN 28011", "DIN 28013", "ASME VB-1", "NFE 81-103", "Custom"]
            self.head_type_combo = wx.ComboBox(params_box, choices=head_type_options, value="DIN 28011",
                                               style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
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
            self.h1_combo = wx.ComboBox(params_box, choices=get_h1_values("DIN 28011", default_s, self.config),
                                        value="20", style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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
            layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text",
                             loc.get("add_custom_layer", "Добавить пользовательский слой")]
            self.layer_combo = wx.ComboBox(params_box, choices=layer_options, value="0",
                                           style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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
            self.on_head_type_change(None)  # Инициализация полей R, r и h1
            logging.info("Интерфейс панели HeadContentPanel успешно настроен")

            # Устанавливаем фокус на D_combo
            self.D_combo.SetFocus()

        except Exception as e:
            logging.error(f"Ошибка настройки UI для HeadContentPanel: {e}")
            show_popup(loc.get("error", f"Ошибка настройки интерфейса: {str(e)}"), popup_type="error")
            raise

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        logging.debug("Обновление языка UI для HeadContentPanel")
        try:
            self.static_boxes["params"].SetLabel(loc.get("head_params_label", "Параметры"))
            self.labels["D"].SetLabel(loc.get("diameter_label", "Диаметр (D), мм"))
            self.labels["s"].SetLabel(loc.get("thickness_label", "Толщина (s)"))
            self.labels["head_type"].SetLabel(loc.get("head_type_label", "Тип Heads"))
            self.labels["h1"].SetLabel(loc.get("height_h1_label", "Высота (h1)"))
            self.labels["R"].SetLabel(loc.get("radius_R_label", "Радиус (R)"))
            self.labels["r"].SetLabel(loc.get("radius_r_label", "Радиус (r)"))
            self.labels["layer"].SetLabel(loc.get("layer_label", "Слой"))

            # Обновление текста кнопок
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
            self.buttons[2].SetLabel(loc.get("cancel_button", "Отмена"))
            adjust_button_widths(self.buttons)

            # Обновление списка слоёв
            layer_options = ["0", "AM_0", "AM_3", "AM_5", "AM_7", "AM_CL", "LASER-TEXT", "schrift", "text",
                             loc.get("add_custom_layer", "Добавить пользовательский слой")]
            current_layer = self.layer_combo.GetValue()
            self.layer_combo.SetItems(layer_options)
            self.layer_combo.SetValue(current_layer if current_layer in layer_options else "0")
            self.selected_layer = self.layer_combo.GetValue()

            self.update_status_bar_no_point()
            self.Layout()
            logging.info("Язык UI HeadContentPanel успешно обновлён")
        except Exception as e:
            logging.error(f"Ошибка обновления языка UI: {e}")
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")

    def on_layer_change(self, event: wx.Event) -> None:
        """
        Обрабатывает выбор слоя в выпадающем списке.

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
        Обновляет параметры при изменении типа головы.

        Args:
            event: Событие выбора типа (может быть None).
        """
        logging.debug("Обновление параметров при изменении типа головы")
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
                    show_popup(loc.get("error_in_function", f"Ошибка расчёта радиусов: {str(e)}"), popup_type="error")
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
        logging.debug("Обновление параметров при изменении толщины")
        self.on_head_type_change(None)

    def get_input_data(self) -> Optional[Dict]:
        """
        Возвращает введённые данные в виде словаря.

        Returns:
            dict: Словарь с данными (D, s, h1, head_type, insert_point, layer, R, r) или None при ошибке.
        """
        try:
            D = self.D_combo.GetValue().strip()
            s = self.s_combo.GetValue().strip()
            h1 = self.h1_combo.GetValue().strip()
            head_type = self.head_type_combo.GetValue()
            layer = self.selected_layer if self.selected_layer.strip() else "0"

            if not D or not s or not h1:
                logging.error("Не все обязательные поля заполнены (D, s, h1)")
                return None

            data = {
                "D": float(D.replace(',', '.')),
                "s": float(s.replace(',', '.')),
                "h1": float(h1.replace(',', '.')),
                "head_type": head_type,
                "insert_point": self.insert_point,
                "layer": layer
            }

            if head_type == "Custom":
                R = self.R_input.GetValue().strip()
                r = self.r_input.GetValue().strip()
                if not R or not r:
                    logging.error("Для типа 'Custom' требуются значения R и r")
                    return None
                data["R"] = float(R.replace(',', '.'))
                data["r"] = float(r.replace(',', '.'))
            else:
                head_config = self.config.get("head_types", {})
                try:
                    R_expr = head_config.get(head_type, {}).get("R")
                    r_expr = head_config.get(head_type, {}).get("r")
                    data["R"] = eval(R_expr, {"D": data["D"], "s": data["s"]}) if R_expr else 0
                    data["r"] = eval(r_expr, {"D": data["D"], "s": data["s"]}) if r_expr else 0
                except Exception as e:
                    logging.error(f"Ошибка расчёта R/r для head_type={head_type}: {e}")
                    data["R"] = 0
                    data["r"] = 0

            if data["D"] <= 0:
                logging.error("Диаметр (D) должен быть положительным")
                return None
            if data["s"] <= 0:
                logging.error("Толщина (s) должна быть положительной")
                return None
            if data["h1"] <= 0:
                logging.error("Высота (h1) должна быть положительной")
                return None
            if head_type == "Custom":
                if data["R"] <= 0 or data["r"] <= 0:
                    logging.error("Радиусы R и r должны быть положительными для типа 'Custom'")
                    return None

            return data
        except Exception as e:
            logging.error(f"Ошибка получения данных из HeadContentPanel: {e}")
            return None

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет данные, запрашивает точку вставки в AutoCAD и вызывает at_add_head для построения головы.
        Очищает поля и оставляет окно для нового ввода.

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки OK в HeadContentPanel")
        try:
            # Минимизируем окно для выбора точки
            main_window = self.GetTopLevelParent()
            main_window.Iconize(True)
            from programms.at_input import at_point_input
            point = at_point_input()
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            if point and hasattr(point, "x") and hasattr(point, "y"):
                self.insert_point = point
                self.update_status_bar_point_selected()
                logging.info(f"Точка вставки выбрана: x={point.x}, y={point.y}")
            else:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                logging.error(f"Точка вставки не выбрана или некорректна: {point}")
                self.update_status_bar_no_point()
                return

            # Получаем данные
            head_data = self.get_input_data()
            if not head_data:
                show_popup(loc.get("no_data_error", "Необходимо заполнить все обязательные поля"), popup_type="error")
                logging.error("Данные не введены или некорректны")
                return

            logging.debug(f"Данные для головы: {head_data}")

            # Инициализация AutoCAD
            cad = ATCadInit()
            if not cad.is_initialized():
                show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
                logging.error("Не удалось инициализировать AutoCAD")
                return

            # Вызов обработки головы
            success = at_add_head(
                D=head_data["D"],
                s=head_data["s"],
                R=head_data["R"],
                r=head_data["r"],
                h1=head_data["h1"],
                insert_point=head_data["insert_point"],
                layer=head_data["layer"],
                adoc=cad.adoc
            )
            if success:
                cad.adoc.Regen(0)  # Обновление активного видового экрана
                logging.info("Голова успешно построена")
                # Очищаем поля
                D_options = common_data_manager.get_data("dimensions.diameters")
                default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
                s_options = common_data_manager.get_data("dimensions.thicknesses")
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
            else:
                show_popup(loc.get("heads_error", "Построение головы отменено или завершилось с ошибкой"), popup_type="error")
                logging.error("Ошибка построения головы")

        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")
            show_popup(loc.get("heads_error", f"Ошибка построения головы: {str(e)}"), popup_type="error")
            self.update_status_bar_no_point()

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Очистить в HeadContentPanel")
        D_options = common_data_manager.get_data("dimensions.diameters")
        default_D = "1000" if "1000" in D_options else D_options[0] if D_options else ""
        s_options = common_data_manager.get_data("dimensions.thicknesses")
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
        self.on_head_type_change(None)  # Обновляем зависимые поля
        logging.info("Поля ввода очищены")

    def on_cancel(self, event: wx.Event) -> None:
        """
        Переключает контент на начальную страницу (content_apps) при нажатии кнопки "Отмена".

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Отмена в HeadContentPanel")
        try:
            main_window = wx.GetTopLevelParent(self)
            if hasattr(main_window, "switch_content"):
                main_window.switch_content("content_apps")
                logging.info("Переключение на content_apps по нажатию кнопки 'Отмена'")
            else:
                logging.error("Главное окно не имеет метода switch_content")
                show_popup(loc.get("error_switch_content", "Ошибка: невозможно переключить контент"), popup_type="error")
        except Exception as e:
            logging.error(f"Ошибка при переключении на content_apps: {e}")
            show_popup(loc.get("error", f"Ошибка переключения контента: {str(e)}"), popup_type="error")
