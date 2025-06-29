# at_cone_input_window.py
"""
Модуль для создания диалогового окна ввода параметров развертки конуса.
Предоставляет интерфейс для ввода данных о заказе, материале, диаметрах, высоте и припуске,
возвращая словарь с параметрами для функции at_cone_sheet и текстовыми данными.
"""

import math
import logging
import os
from typing import Optional, Dict, Tuple

import wx

from config.at_config import (
    FONT_NAME, FONT_SIZE, FONT_TYPE, BACKGROUND_COLOR, FOREGROUND_COLOR,
    CONE_IMAGE_PATH, LAST_CONE_INPUT_FILE, INPUT_FIELD_SIZE
)
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from locales.at_localization import loc
from windows.at_window_utils import (
    BaseInputWindow, CanvasPanel, save_last_input, show_popup,
    get_standard_font, create_standard_buttons, apply_styles_to_panel
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename="at_cad.log",
                    format="%(asctime)s - %(levelname)s - %(message)s")


class ConeInputWindow(BaseInputWindow):
    """
    Диалоговое окно для ввода параметров развертки конуса.
    Наследуется от BaseInputWindow для общей логики и интерфейса.
    """

    def __init__(self, parent=None):
        """
        Инициализирует окно, создаёт элементы управления и настраивает AutoCAD.

        Args:
            parent: Родительское окно (например, MainWindow).
        """
        super().__init__(title_key="window_title_cone", last_input_file=LAST_CONE_INPUT_FILE,
                         window_size=(1200, 750), parent=parent)
        self.parent = parent
        self._updating = False
        self._debounce_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)
        self.setup_ui()
        self.order_input.SetFocus()
        logging.info("ConeInputWindow успешно инициализировано")

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями. Все поля ввода и выпадающие списки имеют одинаковый
        размер и выровнены по правому краю.
        """
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Проверка существования изображения
        if not os.path.exists(CONE_IMAGE_PATH):
            logging.error(f"Файл изображения конуса '{CONE_IMAGE_PATH}' не найден")
            show_popup(loc.get("image_not_found", CONE_IMAGE_PATH), popup_type="error")

        # Изображение конуса
        self.canvas = CanvasPanel(self.panel, image_file=CONE_IMAGE_PATH, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self.panel, self.on_select_point, self.on_ok, self.on_cancel)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        self.adjust_button_widths()
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Единый размер для всех полей ввода и выпадающих списков
        font = get_standard_font()

        # Проверка корректности данных common_data
        material_options = self.common_data.get("material", ["Сталь", "Алюминий", "Нержавейка"])
        thickness_options = self.common_data.get("thicknesses", ["1", "1.5", "2", "3", "4", "5", "6", "8", "10", "12", "14", "15"])
        if not material_options or not thickness_options:
            logging.warning("Некорректные данные common_data: material или thicknesses пусты")
            show_popup(loc.get("invalid_common_data"), popup_type="error")

        # Группа "Основные данные"
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, loc.get("main_data_label"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        main_data_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label="К-№")
        order_label.SetFont(font)
        self.order_input = wx.TextCtrl(main_data_box, value=self.last_input.get("order_number", ""), size=INPUT_FIELD_SIZE)
        self.order_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        self.detail_input = wx.TextCtrl(main_data_box, value=self.last_input.get("detail_number", ""), size=INPUT_FIELD_SIZE)
        self.detail_input.SetFont(font)
        order_sizer.Add(self.detail_input, 0, wx.RIGHT, 5)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Материал
        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label"))
        material_label.SetFont(font)
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                         value=self.last_input.get("material", material_options[0] if material_options else ""),
                                         style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        material_sizer.Add(self.material_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label"))
        thickness_label.SetFont(font)
        last_thickness = str(self.last_input.get("thickness", "")).replace(',', '.')
        try:
            last_thickness_float = float(last_thickness)
            last_thickness = str(int(last_thickness_float)) if last_thickness_float.is_integer() else str(last_thickness_float)
        except ValueError:
            last_thickness = ""
        thickness_value = last_thickness if last_thickness in thickness_options else (thickness_options[0] if thickness_options else "")
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
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, loc.get("diameter"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)
        diameter_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label="d, мм")
        d_label.SetFont(font)
        self.d_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_top", "")), size=INPUT_FIELD_SIZE)
        self.d_input.SetFont(font)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_input, 0, wx.ALL, 5)

        d_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.d_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label"), style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label"))
        self.d_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label"))
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
        self.D_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_base", "")), size=INPUT_FIELD_SIZE)
        self.D_input.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_input, 0, wx.ALL, 5)

        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label"), style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label"))
        self.D_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label"))
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
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self.panel, loc.get("height_label"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        height_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))

        self.height_input = wx.TextCtrl(height_box, value=str(self.last_input.get("height", "")), size=INPUT_FIELD_SIZE)
        self.steigung_input = wx.TextCtrl(height_box, value=str(self.last_input.get("steigung", "")), size=INPUT_FIELD_SIZE)
        self.angle_input = wx.TextCtrl(height_box, value=str(self.last_input.get("angle", "")), size=INPUT_FIELD_SIZE)
        self.height_input.SetFont(font)
        self.steigung_input.SetFont(font)
        self.angle_input.SetFont(font)

        height_label = wx.StaticText(height_box, label="H, мм")
        steigung_label = wx.StaticText(height_box, label=loc.get("steigung_label"))
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
        allowance_label = wx.StaticText(self.panel, label=loc.get("weld_allowance_label"))
        allowance_label.SetFont(font)
        allowance_options = [str(i) for i in range(11)]
        self.allowance_combo = wx.ComboBox(self.panel, choices=allowance_options,
                                          value=self.last_input.get("weld_allowance", "0"),
                                          style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.allowance_combo.SetFont(font)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALL, 5)
        self.right_sizer.Add(allowance_sizer, 0, wx.ALL | wx.EXPAND, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.panel.SetSizer(main_sizer)
        apply_styles_to_panel(self.panel)
        self.panel.Layout()
        logging.info("Интерфейс окна ConeInputWindow успешно настроен")

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

        Args:
            event: Событие ввода текста (wx.EVT_TEXT).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).

        Args:
            event: Событие ввода текста (wx.EVT_TEXT).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).

        Args:
            event: Событие ввода текста (wx.EVT_TEXT).
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки (debounce).
        Угол интерпретируется как полный угол при вершине конуса.

        Args:
            event: Событие таймера (wx.EVT_TIMER).
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
        except (ValueError, TypeError) as e:
            logging.error(f"Ошибка в on_debounce_timeout: {e}")
            self._clear_height_fields()
        finally:
            self._updating = False

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет и сохраняет введённые данные, формирует результат и закрывает окно.

        Args:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        if not self.insert_point or not self.model:
            show_popup(loc.get("cad_not_initialized_or_point_not_selected"), popup_type="error")
            logging.error("AutoCAD не инициализирован или точка вставки не выбрана")
            return
        try:
            d = float(self.d_input.GetValue().replace(',', '.')) if self.d_input.GetValue().strip() else None
            D = float(self.D_input.GetValue().replace(',', '.')) if self.D_input.GetValue().strip() else None
            if d is None or D is None:
                show_popup(loc.get("error_diameter_required"), popup_type="error")
                logging.error("Диаметр вершины или основания не введён")
                return
            if d > D:
                d, D = D, d
            thickness = float(self.thickness_combo.GetValue().replace(',', '.')) if self.thickness_combo.GetValue().strip() else None
            allowance = float(self.allowance_combo.GetValue().replace(',', '.')) if self.allowance_combo.GetValue().strip() else 0

            if thickness is None:
                show_popup(loc.get("error_thickness_required"), popup_type="error")
                logging.error("Толщина не выбрана")
                return
            if D <= 0:
                show_popup(loc.get("error_base_diameter_positive"), popup_type="error")
                logging.error("Диаметр основания должен быть положительным")
                return
            if d < 0:
                show_popup(loc.get("error_top_diameter_non_negative"), popup_type="error")
                logging.error("Диаметр вершины не может быть отрицательным")
                return
            if allowance < 0:
                show_popup(loc.get("error_weld_allowance_non_negative"), popup_type="error")
                logging.error("Припуск на сварку не может быть отрицательным")
                return
            if thickness <= 0:
                show_popup(loc.get("error_thickness_positive"), popup_type="error")
                logging.error("Толщина должна быть положительной")
                return

            d_type = "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer" if self.d_outer.GetValue() else None
            D_type = "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer" if self.D_outer.GetValue() else None
            if d_type is None or D_type is None:
                show_popup(loc.get("error_diameter_type_required"), popup_type="error")
                logging.error("Тип диаметра не выбран")
                return

            try:
                diameter_top = at_diameter(d, thickness, d_type)
                diameter_base = at_diameter(D, thickness, D_type)
            except Exception as e:
                show_popup(loc.get("error_diameter_calculation", str(e)), popup_type="error")
                logging.error(f"Ошибка расчёта диаметра: {e}")
                return

            if diameter_base <= 0:
                show_popup(loc.get("error_base_diameter_positive"), popup_type="error")
                logging.error("Средний диаметр основания должен быть положительным")
                return
            if diameter_top < 0:
                show_popup(loc.get("error_top_diameter_non_negative"), popup_type="error")
                logging.error("Средний диаметр вершины не должен быть отрицательным")
                return

            height = None
            if self.height_input.GetValue().strip():
                height = float(self.height_input.GetValue().replace(',', '.'))
                if height <= 0:
                    show_popup(loc.get("error_height_positive"), popup_type="error")
                    logging.error("Высота должна быть положительной")
                    return
            elif self.steigung_input.GetValue().strip():
                steigung = float(self.steigung_input.GetValue().replace(',', '.'))
                if steigung <= 0:
                    show_popup(loc.get("error_steigung_positive"), popup_type="error")
                    logging.error("Наклон должен быть положительным")
                    return
                height = at_cone_height(D, d, steigung=steigung)
            elif self.angle_input.GetValue().strip():
                angle = float(self.angle_input.GetValue().replace(',', '.'))
                if angle <= 0 or angle >= 180:
                    show_popup(loc.get("error_angle_range"), popup_type="error")
                    logging.error("Угол должен быть в диапазоне от 0 до 180 градусов")
                    return
                height = at_cone_height(D, d, angle=angle)
            else:
                show_popup(loc.get("error_height_steigung_angle_required"), popup_type="error")
                logging.error("Необходимо ввести высоту, наклон или угол")
                return

            if height is None or height <= 0:
                show_popup(loc.get("error_height_positive"), popup_type="error")
                logging.error("Высота должна быть положительной")
                return

            height += allowance

            thickness_text = f"{thickness:.2f} {loc.get('mm')}"

            self.result = {
                "model": self.model,
                "input_point": self.insert_point,
                "diameter_base": diameter_base,
                "diameter_top": diameter_top,
                "height": height,
                "layer_name": self.selected_layer if self.selected_layer.strip() else "0",
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

            self.Close()
        except (ValueError, TypeError) as e:
            show_popup(loc.get("error_invalid_number_format"), popup_type="error")
            logging.error(f"Ошибка формата числа в on_ok: {e}")

    def on_cancel(self, event: wx.Event) -> None:
        """
        Закрывает окно без сохранения данных.

        Args:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        logging.info("Закрытие окна ConeInputWindow через кнопку 'Отмена'")
        try:
            self._debounce_timer.Stop()  # Остановка таймера
            self.Close()
            if self.parent:
                self.parent.Raise()  # Восстановить фокус родительского окна
        except Exception as e:
            logging.error(f"Ошибка при закрытии окна ConeInputWindow: {e}")
            show_popup(loc.get("error_window_close", str(e)), popup_type="error")


if __name__ == "__main__":
    """
    Тестовый блок для отладки вызова окна ConeInputWindow и проверки словаря результата.
    """


    def on_window_close(event: wx.CloseEvent) -> None:
        """
        Обработчик события закрытия окна для вывода результата.
        """
        if window.result:
            print("Полученный словарь результата:")
            for key, value in window.result.items():
                print(f"{key}: {value}")
        else:
            print("Окно закрыто без результата (нажата 'Отмена' или ошибка)")
        event.Skip()  # Продолжить стандартную обработку закрытия


    # Создание приложения wxPython
    app = wx.App(False)

    # Инициализация окна
    window = ConeInputWindow(parent=None)

    # Привязка обработчика закрытия окна
    window.Bind(wx.EVT_CLOSE, on_window_close)

    # Отображение окна
    window.Show()

    # Запуск главного цикла приложения
    logging.info("Запуск тестового приложения для ConeInputWindow")
    app.MainLoop()