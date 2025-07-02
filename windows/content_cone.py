"""
Модуль для создания панели ввода параметров развертки конуса.
Предоставляет интерфейс для ввода данных о заказе, материале, диаметрах, высоте и припуске,
возвращая данные для функции at_cone_sheet через вызов at_run_cone.run_application.
"""

import math
import logging
import os
from typing import Optional, Dict

import wx
from config.at_config import (
    FONT_NAME, FONT_SIZE, FONT_TYPE, BACKGROUND_COLOR, FOREGROUND_COLOR,
    CONE_IMAGE_PATH, LAST_CONE_INPUT_FILE, INPUT_FIELD_SIZE
)
from config.at_cad_init import ATCadInit
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from programms.at_input import at_point_input
from locales.at_localization import loc
from windows.at_window_utils import (
    CanvasPanel, save_last_input, show_popup,
    get_standard_font, apply_styles_to_panel, create_standard_buttons
)
from programms.at_run_cone import run_application

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров конуса.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров конуса.
    """
    return ConeContentPanel(parent)


class ConeContentPanel(wx.Panel):
    """
    Панель для ввода параметров развертки конуса.
    """

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
        """
        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.parent = parent
        self._updating = False
        self._debounce_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)

        # Инициализация AutoCAD
        self.cad = ATCadInit()
        if not self.cad.is_initialized():
            show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
            logging.error("AutoCAD не инициализирован")

        # Загрузка последних введённых данных
        self.last_input = wx.GetApp().GetTopWindow().last_input if hasattr(wx.GetApp().GetTopWindow(),
                                                                           'last_input') else {}
        self.setup_ui()
        self.order_input.SetFocus()
        logging.info("ConeContentPanel успешно инициализировано")

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями.
        """
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Проверка существования изображения
        image_path = os.path.abspath(CONE_IMAGE_PATH)
        if not os.path.exists(image_path):
            logging.error(f"Файл изображения конуса '{image_path}' не найден")
            show_popup(loc.get("image_not_found", f"Изображение не найдено: {image_path}"), popup_type="error")

        # Изображение конуса
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_select_point, self.on_ok, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        self.adjust_button_widths()
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Единый размер для всех полей ввода и выпадающих списков
        font = get_standard_font()

        # Данные для выпадающих списков
        material_options = ["Сталь", "Алюминий", "Нержавейка"]
        thickness_options = ["1", "1.5", "2", "3", "4", "5", "6", "8", "10", "12", "14", "15"]

        # Группа "Основные данные"
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        main_data_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label="К-№")
        order_label.SetFont(font)
        self.order_input = wx.TextCtrl(main_data_box, value=self.last_input.get("order_number", ""),
                                       size=INPUT_FIELD_SIZE)
        self.order_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        self.detail_input = wx.TextCtrl(main_data_box, value=self.last_input.get("detail_number", ""),
                                        size=INPUT_FIELD_SIZE)
        self.detail_input.SetFont(font)
        order_sizer.Add(self.detail_input, 0, wx.RIGHT, 5)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Материал
        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        material_label.SetFont(font)
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                          value=self.last_input.get("material", material_options[0]),
                                          style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        material_sizer.Add(self.material_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина"))
        thickness_label.SetFont(font)
        last_thickness = str(self.last_input.get("thickness", "")).replace(',', '.')
        try:
            last_thickness_float = float(last_thickness)
            last_thickness = str(int(last_thickness_float)) if last_thickness_float.is_integer() else str(
                last_thickness_float)
        except ValueError:
            last_thickness = ""
        thickness_value = last_thickness if last_thickness in thickness_options else thickness_options[0]
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options,
                                           value=thickness_value,
                                           style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.thickness_combo.SetFont(font)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Диаметр"
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("diameter", "Диаметр"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)
        diameter_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label="d, мм")
        d_label.SetFont(font)
        self.d_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_top", "")),
                                   size=INPUT_FIELD_SIZE)
        self.d_input.SetFont(font)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_input, 0, wx.ALL, 5)

        d_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.d_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.d_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        self.d_inner.SetFont(font)
        self.d_middle.SetFont(font)
        self.d_outer.SetFont(font)
        self.d_inner.SetValue(self.last_input.get("d_type", "inner") == "inner")
        self.d_middle.SetValue(self.last_input.get("d_type", "inner") == "middle")
        self.d_outer.SetValue(self.last_input.get("d_type", "inner") == "outer")
        d_radio_sizer.AddStretchSpacer()
        d_radio_sizer.Add(self.d_inner, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_middle, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(d_sizer, 0, wx.EXPAND | wx.ALL, 5)
        diameter_sizer.Add(d_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр основания (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(diameter_box, label="D, мм")
        D_label.SetFont(font)
        self.D_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_base", "")),
                                   size=INPUT_FIELD_SIZE)
        self.D_input.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_input, 0, wx.ALL, 5)

        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.D_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        self.D_inner.SetFont(font)
        self.D_middle.SetFont(font)
        self.D_outer.SetFont(font)
        self.D_inner.SetValue(self.last_input.get("D_type", "inner") == "inner")
        self.D_middle.SetValue(self.last_input.get("D_type", "inner") == "middle")
        self.D_outer.SetValue(self.last_input.get("D_type", "inner") == "outer")
        D_radio_sizer.AddStretchSpacer()
        D_radio_sizer.Add(self.D_inner, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_middle, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(D_sizer, 0, wx.EXPAND | wx.ALL, 5)
        diameter_sizer.Add(D_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(diameter_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Высота"
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("height_label", "Высота"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        height_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        self.height_input = wx.TextCtrl(height_box, value=str(self.last_input.get("height", "")), size=INPUT_FIELD_SIZE)
        self.steigung_input = wx.TextCtrl(height_box, value=str(self.last_input.get("steigung", "")),
                                          size=INPUT_FIELD_SIZE)
        self.angle_input = wx.TextCtrl(height_box, value=str(self.last_input.get("angle", "")), size=INPUT_FIELD_SIZE)
        self.height_input.SetFont(font)
        self.steigung_input.SetFont(font)
        self.angle_input.SetFont(font)

        height_label = wx.StaticText(height_box, label="H, мм")
        steigung_label = wx.StaticText(height_box, label=loc.get("steigung_label", "Наклон"))
        angle_label = wx.StaticText(height_box, label="α°")
        height_label.SetFont(font)
        steigung_label.SetFont(font)
        angle_label.SetFont(font)

        height_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        height_input_sizer.AddStretchSpacer()
        height_input_sizer.Add(height_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        height_input_sizer.Add(self.height_input, 0, wx.ALL, 5)
        height_sizer.Add(height_input_sizer, 0, wx.ALL | wx.EXPAND, 5)

        steigung_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steigung_sizer.AddStretchSpacer()
        steigung_sizer.Add(steigung_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        steigung_sizer.Add(self.steigung_input, 0, wx.ALL, 5)
        height_sizer.Add(steigung_sizer, 0, wx.ALL | wx.EXPAND, 5)

        angle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        angle_sizer.AddStretchSpacer()
        angle_sizer.Add(angle_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        angle_sizer.Add(self.angle_input, 0, wx.ALL, 5)
        height_sizer.Add(angle_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.height_input.Bind(wx.EVT_TEXT, self.on_height_text)
        self.steigung_input.Bind(wx.EVT_TEXT, self.on_steigung_text)
        self.angle_input.Bind(wx.EVT_TEXT, self.on_angle_text)
        self.right_sizer.Add(height_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Припуск на сварку
        allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        allowance_label = wx.StaticText(self, label=loc.get("weld_allowance_label", "Припуск на сварку"))
        allowance_label.SetFont(font)
        allowance_options = [str(i) for i in range(11)]
        self.allowance_combo = wx.ComboBox(self, choices=allowance_options,
                                           value=self.last_input.get("weld_allowance", "0"),
                                           style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.allowance_combo.SetFont(font)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALL, 5)
        self.right_sizer.Add(allowance_sizer, 0, wx.ALL | wx.EXPAND, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()
        logging.info("Интерфейс панели ConeContentPanel успешно настроен")

    def adjust_button_widths(self):
        """Устанавливает одинаковую ширину для всех кнопок."""
        max_width = 0
        for button in self.buttons:
            dc = wx.ClientDC(button)
            width, _ = dc.GetTextExtent(button.GetLabel())
            max_width = max(max_width, width + 20)
        for button in self.buttons:
            button.SetMinSize((max_width, 30))

    def _clear_height_fields(self) -> None:
        """
        Очищает поля ввода высоты, наклона и угла.
        """
        wx.CallAfter(self.height_input.SetValue, "")
        wx.CallAfter(self.steigung_input.SetValue, "")
        wx.CallAfter(self.angle_input.SetValue, "")

    def on_height_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода высоты с задержкой (debounce).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки.
        """
        if self._updating:
            return
        self._updating = True
        try:
            height_str = self.height_input.GetValue().strip()
            steigung_str = self.steigung_input.GetValue().strip()
            angle_str = self.angle_input.GetValue().strip()

            try:
                d = float(self.d_input.GetValue().replace(',', '.')) if self.d_input.GetValue().strip() else 0
                D = float(self.D_input.GetValue().replace(',', '.')) if self.D_input.GetValue().strip() else 1000
            except ValueError:
                d = 0
                D = 1000

            if height_str:
                self.steigung_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    height = float(height_str.replace(',', '.'))
                    if height <= 0:
                        logging.warning(f"Недопустимое значение высоты: {height}")
                        self._clear_height_fields()
                        return
                    steigung = at_steigung(height, D, d)
                    delta_d = abs(D - d) / 2
                    angle = math.degrees(math.atan2(delta_d, height)) * 2
                    wx.CallAfter(self.steigung_input.SetValue, f"{steigung:.2f}" if steigung is not None else "")
                    wx.CallAfter(self.angle_input.SetValue, f"{angle:.2f}" if angle is not None else "")
                except (ValueError, TypeError) as e:
                    logging.error(f"Ошибка расчёта по высоте: {e}")
                    self._clear_height_fields()
            elif steigung_str:
                self.height_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    steigung = float(steigung_str.replace(',', '.'))
                    if steigung <= 0:
                        logging.warning(f"Недопустимое значение наклона: {steigung}")
                        self._clear_height_fields()
                        return
                    height = at_cone_height(D, d, steigung=steigung)
                    delta_d = abs(D - d) / 2
                    angle = math.degrees(math.atan2(delta_d, height)) * 2 if height != 0 else 0
                    wx.CallAfter(self.height_input.SetValue, f"{height:.2f}" if height is not None else "")
                    wx.CallAfter(self.angle_input.SetValue, f"{angle:.2f}" if angle is not None else "")
                except (ValueError, TypeError) as e:
                    logging.error(f"Ошибка расчёта по наклону: {e}")
                    self._clear_height_fields()
            elif angle_str:
                self.height_input.Enable(False)
                self.steigung_input.Enable(False)
                try:
                    angle = float(angle_str.replace(',', '.'))
                    if not (0 < angle < 180):
                        logging.warning(f"Недопустимое значение угла: {angle}")
                        self._clear_height_fields()
                        return
                    height = at_cone_height(D, d, angle=angle)
                    steigung = at_steigung(height, D, d)
                    wx.CallAfter(self.height_input.SetValue, f"{height:.2f}" if height is not None else "")
                    wx.CallAfter(self.steigung_input.SetValue, f"{steigung:.2f}" if steigung is not None else "")
                except (ValueError, TypeError) as e:
                    logging.error(f"Ошибка расчёта по углу: {e}")
                    self._clear_height_fields()
            else:
                self.height_input.Enable(True)
                self.steigung_input.Enable(True)
                self.angle_input.Enable(True)
                self._clear_height_fields()
        except Exception as e:
            logging.error(f"Ошибка в on_debounce_timeout: {e}")
            self._clear_height_fields()
        finally:
            self._updating = False

    def on_select_point(self, event: wx.Event) -> None:
        """
        Запрашивает точку вставки в AutoCAD.
        """
        if not self.cad.is_initialized():
            show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
            return
        point = at_point_input(self.cad.adoc)
        if point:
            self.insert_point = point
            show_popup(loc.get("point_selected", "Точка вставки выбрана"), popup_type="info")
            logging.info(f"Точка вставки выбрана: {point}")
        else:
            show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
            logging.error("Точка вставки не выбрана")

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет данные и вызывает run_application для построения развертки.
        """
        if not self.cad.is_initialized():
            show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
            logging.error("AutoCAD не инициализирован")
            return
        if not hasattr(self, "insert_point") or not self.insert_point:
            show_popup(loc.get("point_not_selected", "Точка вставки не выбрана"), popup_type="error")
            logging.error("Точка вставки не выбрана")
            return

        try:
            d = float(self.d_input.GetValue().replace(',', '.')) if self.d_input.GetValue().strip() else None
            D = float(self.D_input.GetValue().replace(',', '.')) if self.D_input.GetValue().strip() else None
            if d is None or D is None:
                show_popup(loc.get("error_diameter_required", "Требуется ввести диаметры"), popup_type="error")
                logging.error("Диаметр вершины или основания не введён")
                return
            if d > D:
                d, D = D, d
            thickness = float(
                self.thickness_combo.GetValue().replace(',', '.')) if self.thickness_combo.GetValue().strip() else None
            allowance = float(
                self.allowance_combo.GetValue().replace(',', '.')) if self.allowance_combo.GetValue().strip() else 0

            if thickness is None:
                show_popup(loc.get("error_thickness_required", "Требуется выбрать толщину"), popup_type="error")
                logging.error("Толщина не выбрана")
                return
            if D <= 0:
                show_popup(loc.get("error_base_diameter_positive", "Диаметр основания должен быть положительным"),
                           popup_type="error")
                logging.error("Диаметр основания должен быть положительным")
                return
            if d < 0:
                show_popup(loc.get("error_top_diameter_non_negative", "Диаметр вершины не может быть отрицательным"),
                           popup_type="error")
                logging.error("Диаметр вершины не может быть отрицательным")
                return
            if allowance < 0:
                show_popup(
                    loc.get("error_weld_allowance_non_negative", "Припуск на сварку не может быть отрицательным"),
                    popup_type="error")
                logging.error("Припуск на сварку не может быть отрицательным")
                return
            if thickness <= 0:
                show_popup(loc.get("error_thickness_positive", "Толщина должна быть положительной"), popup_type="error")
                logging.error("Толщина должна быть положительной")
                return

            d_type = "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer"
            D_type = "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer"

            try:
                diameter_top = at_diameter(d, thickness, d_type)
                diameter_base = at_diameter(D, thickness, D_type)
            except Exception as e:
                show_popup(loc.get("error_diameter_calculation", f"Ошибка расчёта диаметра: {str(e)}"),
                           popup_type="error")
                logging.error(f"Ошибка расчёта диаметра: {e}")
                return

            if diameter_base <= 0:
                show_popup(loc.get("error_base_diameter_positive", "Диаметр основания должен быть положительным"),
                           popup_type="error")
                logging.error("Средний диаметр основания должен быть положительным")
                return
            if diameter_top < 0:
                show_popup(loc.get("error_top_diameter_non_negative", "Диаметр вершины не должен быть отрицательным"),
                           popup_type="error")
                logging.error("Средний диаметр вершины не должен быть отрицательным")
                return

            height = None
            if self.height_input.GetValue().strip():
                height = float(self.height_input.GetValue().replace(',', '.'))
                if height <= 0:
                    show_popup(loc.get("error_height_positive", "Высота должна быть положительной"), popup_type="error")
                    logging.error("Высота должна быть положительной")
                    return
            elif self.steigung_input.GetValue().strip():
                steigung = float(self.steigung_input.GetValue().replace(',', '.'))
                if steigung <= 0:
                    show_popup(loc.get("error_steigung_positive", "Наклон должен быть положительным"),
                               popup_type="error")
                    logging.error("Наклон должен быть положительным")
                    return
                height = at_cone_height(D, d, steigung=steigung)
            elif self.angle_input.GetValue().strip():
                angle = float(self.angle_input.GetValue().replace(',', '.'))
                if angle <= 0 or angle >= 180:
                    show_popup(loc.get("error_angle_range", "Угол должен быть в диапазоне от 0 до 180 градусов"),
                               popup_type="error")
                    logging.error("Угол должен быть в диапазоне от 0 до 180 градусов")
                    return
                height = at_cone_height(D, d, angle=angle)
            else:
                show_popup(loc.get("error_height_steigung_angle_required", "Необходимо ввести высоту, наклон или угол"),
                           popup_type="error")
                logging.error("Необходимо ввести высоту, наклон или угол")
                return

            if height is None or height <= 0:
                show_popup(loc.get("error_height_positive", "Высота должна быть положительной"), popup_type="error")
                logging.error("Высота должна быть положительной")
                return

            height += allowance

            thickness_text = f"{thickness:.2f} {loc.get('mm', 'мм')}"

            data = {
                "model": self.cad.model,
                "input_point": self.insert_point,
                "diameter_base": diameter_base,
                "diameter_top": diameter_top,
                "height": height,
                "layer_name": "0",
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness_text": thickness_text
            }

            save_last_input(LAST_CONE_INPUT_FILE, {
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "thickness": str(thickness),
                "weld_allowance": str(allowance),
                "diameter_top": self.d_input.GetValue(),
                "diameter_base": self.D_input.GetValue(),
                "d_type": d_type,
                "D_type": D_type,
                "height": self.height_input.GetValue(),
                "steigung": self.steigung_input.GetValue(),
                "angle": self.angle_input.GetValue()
            })

            # Вызов run_application
            try:
                success = run_application(data)
                if success:
                    show_popup(loc.get("cone_build_success", "Развертка конуса успешно построена"), popup_type="info")
                    self.on_clear(None)
                else:
                    show_popup(loc.get("cone_build_failed", "Построение отменено или завершилось с ошибкой"),
                               popup_type="error")
            except Exception as e:
                show_popup(loc.get("cone_build_error", f"Ошибка построения: {str(e)}"), popup_type="error")
                logging.error(f"Ошибка в run_application: {e}")

        except (ValueError, TypeError) as e:
            show_popup(loc.get("error_invalid_number_format", "Неверный формат числа"), popup_type="error")
            logging.error(f"Ошибка формата числа в on_ok: {e}")

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода.
        """
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetValue(self.material_combo.GetString(0))
        self.thickness_combo.SetValue(self.thickness_combo.GetString(0))
        self.d_input.SetValue("")
        self.D_input.SetValue("")
        self.d_inner.SetValue(True)
        self.D_inner.SetValue(True)
        self.height_input.SetValue("")
        self.steigung_input.SetValue("")
        self.angle_input.SetValue("")
        self.allowance_combo.SetValue("0")
        if hasattr(self, "insert_point"):
            del self.insert_point
        logging.info("Поля ввода очищены")
