"""
Файл: windows/content_cone.py
Описание:
Модуль для создания панели ввода параметров развертки конуса.
Обеспечивает интерфейс для ввода данных конуса с валидацией, вызовом функции выбора точки
и возвратом словаря с данными в main_window.last_input. Локализация через loc.get, настройки из user_settings.json.
Сохраняет указанные данные в last_input.json для использования в качестве начальных значений.
Изображение конуса отображается с помощью CanvasPanel слева, кнопки под изображением, поля ввода справа.
"""

import logging
import math
import os
import json
from typing import Optional, Dict

import wx

from config.at_config import *
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_common_data
)
from config.at_last_input import save_last_input

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
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
    try:
        panel = ConeContentPanel(parent)
        logging.info("Панель ConeContentPanel создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания ConeContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели конуса: {str(e)}"), popup_type="error")
        return wx.Panel(parent)


class ConeContentPanel(BaseContentPanel):
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
        self.last_input_file = os.path.join(RESOURCE_DIR, "last_cone_input.json")
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None
        self._updating = False
        self._debounce_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)
        self.update_status_bar_no_point()
        self.setup_ui()
        self.load_last_input()
        self.order_input.SetFocus()
        logging.info("ConeContentPanel инициализирована")

    def update_status_bar_no_point(self):
        """
        Обновляет статусную строку, если точка не выбрана.
        """
        self.update_status_bar_point_selected(None)

    def update_status_bar_point_selected(self, point):
        """
        Обновляет статусную строку с координатами выбранной точки.

        Args:
            point: Координаты точки вставки ([x, y, z]) или None.
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
        image_path = os.path.abspath(CONE_IMAGE_PATH)
        if not os.path.exists(image_path):
            logging.warning(f"Файл изображения конуса '{image_path}' не найден")
            image_path = None  # Устанавливаем None, чтобы CanvasPanel обработал отсутствие изображения

        # Изображение конуса
        try:
            self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
            self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)
        except Exception as e:
            logging.error(f"Ошибка создания CanvasPanel: {e}")
            show_popup(loc.get("error", f"Ошибка загрузки изображения: {str(e)}"), popup_type="error")
            self.canvas = wx.Panel(self, size=(600, 400))
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

        # Загрузка данных
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[
            0] if thickness_options else ""

        # Группа "Основные данные"
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        self.static_boxes["main_data"] = main_data_box

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        order_label.SetFont(font)
        self.labels["order"] = order_label
        self.order_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
        self.order_input.SetFont(font)
        order_sizer.AddStretchSpacer()
        order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
        self.detail_input.SetFont(font)
        order_sizer.Add(self.detail_input, 0, wx.RIGHT, 5)
        main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Материал
        material_sizer = wx.BoxSizer(wx.HORIZONTAL)
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        material_label.SetFont(font)
        self.labels["material"] = material_label
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                          value=material_options[0] if material_options else "", style=wx.CB_DROPDOWN,
                                          size=INPUT_FIELD_SIZE)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        material_sizer.Add(self.material_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина"))
        thickness_label.SetFont(font)
        self.labels["thickness"] = thickness_label
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options, value=default_thickness,
                                           style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.thickness_combo.SetFont(font)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Диаметры"
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("diameter", "Диаметры"))
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)
        self.static_boxes["diameter"] = diameter_box

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label=loc.get("d_label", "d, мм"))
        d_label.SetFont(font)
        self.labels["d"] = d_label
        self.d_input = wx.TextCtrl(diameter_box, value="", size=INPUT_FIELD_SIZE)
        self.d_input.SetFont(font)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_input, 0, wx.ALL, 5)
        diameter_sizer.Add(d_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Радиокнопки для диаметра вершины
        d_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.d_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.d_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        for rb in [self.d_inner, self.d_middle, self.d_outer]:
            rb.SetFont(font)
        self.d_inner.SetValue(True)
        self.labels["d_inner"] = self.d_inner
        self.labels["d_middle"] = self.d_middle
        self.labels["d_outer"] = self.d_outer
        d_radio_sizer.AddStretchSpacer()
        d_radio_sizer.Add(self.d_inner, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_middle, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(d_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр основания (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(diameter_box, label=loc.get("D_label", "D, мм"))
        D_label.SetFont(font)
        self.labels["D"] = D_label
        self.D_input = wx.TextCtrl(diameter_box, value="", size=INPUT_FIELD_SIZE)
        self.D_input.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_input, 0, wx.ALL, 5)
        diameter_sizer.Add(D_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Радиокнопки для диаметра основания
        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=loc.get("inner_label", "Внутренний"), style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=loc.get("middle_label", "Средний"))
        self.D_outer = wx.RadioButton(diameter_box, label=loc.get("outer_label", "Внешний"))
        for rb in [self.D_inner, self.D_middle, self.D_outer]:
            rb.SetFont(font)
        self.D_inner.SetValue(True)
        self.labels["D_inner"] = self.D_inner
        self.labels["D_middle"] = self.D_middle
        self.labels["D_outer"] = self.D_outer
        D_radio_sizer.AddStretchSpacer()
        D_radio_sizer.Add(self.D_inner, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_middle, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(D_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(diameter_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Высота"
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("height_label", "Высота"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        self.static_boxes["height"] = height_box

        # Высота (H)
        height_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        height_label = wx.StaticText(height_box, label=loc.get("height_label_mm", "H, мм"))
        height_label.SetFont(font)
        self.labels["height"] = height_label
        self.height_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.height_input.SetFont(font)
        height_input_sizer.AddStretchSpacer()
        height_input_sizer.Add(height_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        height_input_sizer.Add(self.height_input, 0, wx.ALL, 5)
        height_sizer.Add(height_input_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Наклон
        steigung_sizer = wx.BoxSizer(wx.HORIZONTAL)
        steigung_label = wx.StaticText(height_box, label=loc.get("steigung_label", "Наклон"))
        steigung_label.SetFont(font)
        self.labels["steigung"] = steigung_label
        self.steigung_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.steigung_input.SetFont(font)
        steigung_sizer.AddStretchSpacer()
        steigung_sizer.Add(steigung_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        steigung_sizer.Add(self.steigung_input, 0, wx.ALL, 5)
        height_sizer.Add(steigung_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Угол
        angle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        angle_label = wx.StaticText(height_box, label=loc.get("angle_label", "α°"))
        angle_label.SetFont(font)
        self.labels["angle"] = angle_label
        self.angle_input = wx.TextCtrl(height_box, value="", size=INPUT_FIELD_SIZE)
        self.angle_input.SetFont(font)
        angle_sizer.AddStretchSpacer()
        angle_sizer.Add(angle_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        angle_sizer.Add(self.angle_input, 0, wx.ALL, 5)
        height_sizer.Add(angle_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.height_input.Bind(wx.EVT_TEXT, self.on_height_text)
        self.steigung_input.Bind(wx.EVT_TEXT, self.on_steigung_text)
        self.angle_input.Bind(wx.EVT_TEXT, self.on_angle_text)
        self.right_sizer.Add(height_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Припуск на сварку
        allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        allowance_label = wx.StaticText(self, label=loc.get("weld_allowance_label", "Припуск на сварку, мм"))
        allowance_label.SetFont(font)
        self.labels["allowance"] = allowance_label
        self.allowance_combo = wx.ComboBox(self, choices=[str(i) for i in range(11)], value="3", style=wx.CB_READONLY,
                                           size=INPUT_FIELD_SIZE)
        self.allowance_combo.SetFont(font)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALL, 5)
        self.right_sizer.Add(allowance_sizer, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()
        logging.info("Интерфейс ConeContentPanel настроен")

    def load_last_input(self) -> None:
        """
        Загружает последние введённые данные из last_input.json.
        """
        try:
            file_path = self.last_input_file
            if os.path.exists(file_path):
                with open(file_path, "r", encoding='utf-8') as f:
                    last_input = json.load(f)
                self.order_input.SetValue(last_input.get("order_number", ""))
                self.material_combo.SetValue(last_input.get("material", self.material_combo.GetValue()))
                self.thickness_combo.SetValue(str(last_input.get("thickness", self.thickness_combo.GetValue())))
                self.allowance_combo.SetValue(str(last_input.get("weld_allowance", "3")))
                logging.info(f"Последние данные загружены из {file_path}")
            else:
                logging.info(f"Файл {file_path} не найден, используются значения по умолчанию")
        except Exception as e:
            logging.error(f"Ошибка загрузки {file_path}: {e}")
            show_popup(loc.get("error", f"Ошибка загрузки данных: {str(e)}"), popup_type="error")

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["diameter"].SetLabel(loc.get("diameter", "Диаметры"))
        self.static_boxes["height"].SetLabel(loc.get("height_label", "Высота"))
        self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
        self.labels["d"].SetLabel(loc.get("d_label", "d, мм"))
        self.labels["D"].SetLabel(loc.get("D_label", "D, мм"))
        self.labels["d_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
        self.labels["d_middle"].SetLabel(loc.get("middle_label", "Средний"))
        self.labels["d_outer"].SetLabel(loc.get("outer_label", "Внешний"))
        self.labels["D_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
        self.labels["D_middle"].SetLabel(loc.get("middle_label", "Средний"))
        self.labels["D_outer"].SetLabel(loc.get("outer_label", "Внешний"))
        self.labels["height"].SetLabel(loc.get("height_label_mm", "H, мм"))
        self.labels["steigung"].SetLabel(loc.get("steigung_label", "Наклон"))
        self.labels["angle"].SetLabel(loc.get("angle_label", "α°"))
        self.labels["allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку, мм"))

        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Отмена"][i]))
        adjust_button_widths(self.buttons)

        self.canvas.Refresh()
        self.Layout()
        self.Refresh()
        self.Update()
        logging.info("Язык UI обновлён")

    def on_height_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода высоты с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).

        Args:
            event: Событие wxPython.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки.

        Args:
            event: Событие wxPython.
        """
        if self._updating:
            return
        self._updating = True
        try:
            height_str = self.height_input.GetValue().strip().replace(',', '.')
            steigung_str = self.steigung_input.GetValue().strip().replace(',', '.')
            angle_str = self.angle_input.GetValue().strip().replace(',', '.')
            d_str = self.d_input.GetValue().strip().replace(',', '.')
            D_str = self.D_input.GetValue().strip().replace(',', '.')

            d = float(d_str) if d_str else 0
            D = float(D_str) if D_str else 1000

            if height_str:
                self.steigung_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    height = float(height_str)
                    if height <= 0:
                        show_popup(loc.get("error_height_positive", "Высота должна быть положительной"),
                                   popup_type="error")
                        return
                    steigung = at_steigung(height, D, d)
                    angle = math.degrees(math.atan2(abs(D - d) / 2, height)) * 2
                    self.steigung_input.SetValue(f"{steigung:.2f}" if steigung is not None else "")
                    self.angle_input.SetValue(f"{angle:.2f}" if angle is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для высоты"),
                               popup_type="error")
            elif steigung_str:
                self.height_input.Enable(False)
                self.angle_input.Enable(False)
                try:
                    steigung = float(steigung_str)
                    if steigung <= 0:
                        show_popup(loc.get("error_steigung_positive", "Наклон должен быть положительным"),
                                   popup_type="error")
                        return
                    height = at_cone_height(D, d, steigung=steigung)
                    angle = math.degrees(math.atan2(abs(D - d) / 2, height)) * 2 if height else 0
                    self.height_input.SetValue(f"{height:.2f}" if height is not None else "")
                    self.angle_input.SetValue(f"{angle:.2f}" if angle is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для наклона"),
                               popup_type="error")
            elif angle_str:
                self.height_input.Enable(False)
                self.steigung_input.Enable(False)
                try:
                    angle = float(angle_str)
                    if not 0 < angle < 180:
                        show_popup(loc.get("error_angle_range", "Угол должен быть в диапазоне 0–180°"),
                                   popup_type="error")
                        return
                    height = at_cone_height(D, d, angle=angle)
                    steigung = at_steigung(height, D, d)
                    self.height_input.SetValue(f"{height:.2f}" if height is not None else "")
                    self.steigung_input.SetValue(f"{steigung:.2f}" if steigung is not None else "")
                except ValueError:
                    show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для угла"),
                               popup_type="error")
            else:
                self.height_input.Enable(True)
                self.steigung_input.Enable(True)
                self.angle_input.Enable(True)
                self.height_input.SetValue("")
                self.steigung_input.SetValue("")
                self.angle_input.SetValue("")
        except Exception as e:
            logging.error(f"Ошибка в расчётах параметров конуса: {e}")
            show_popup(loc.get("error", f"Ошибка расчёта: {str(e)}"), popup_type="error")
        finally:
            self._updating = False

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.

        Returns:
            Optional[Dict]: Словарь с данными или None при ошибке.
        """
        try:
            data = {
                "order_number": self.order_input.GetValue().strip(),
                "detail_number": self.detail_input.GetValue().strip(),
                "material": self.material_combo.GetValue().strip(),
                "thickness": float(self.thickness_combo.GetValue().replace(',',
                                                                           '.')) if self.thickness_combo.GetValue().strip() else 0,
                "diameter_top": float(
                    self.d_input.GetValue().replace(',', '.')) if self.d_input.GetValue().strip() else 0,
                "diameter_base": float(
                    self.D_input.GetValue().replace(',', '.')) if self.D_input.GetValue().strip() else 0,
                "d_type": "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer",
                "D_type": "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer",
                "height": float(
                    self.height_input.GetValue().replace(',', '.')) if self.height_input.GetValue().strip() else 0,
                "steigung": float(
                    self.steigung_input.GetValue().replace(',', '.')) if self.steigung_input.GetValue().strip() else 0,
                "angle": float(
                    self.angle_input.GetValue().replace(',', '.')) if self.angle_input.GetValue().strip() else 0,
                "weld_allowance": float(self.allowance_combo.GetValue().replace(',',
                                                                                '.')) if self.allowance_combo.GetValue().strip() else 0,
                "insert_point": self.insert_point,
                "thickness_text": f"{float(self.thickness_combo.GetValue()):.2f} {loc.get('mm', 'мм')}" if self.thickness_combo.GetValue().strip() else "0.00 мм"
            }
            return data
        except ValueError as e:
            logging.error(f"Ошибка получения данных: {e}")
            show_popup(loc.get("invalid_number_format_error", "Неверный формат числа"), popup_type="error")
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
            if not data:
                show_popup(loc.get("error_data_missing", "Необходимо ввести данные"), popup_type="error")
                return False

            # Проверка материала
            if not data["material"]:
                show_popup(loc.get("error_material_required", "Выберите материал"), popup_type="error")
                self.material_combo.SetFocus()
                return False

            # Проверка числовых значений
            for field, label, input_ctrl in [
                ("thickness", loc.get("thickness_label", "Толщина"), self.thickness_combo),
                ("diameter_top", loc.get("d_label", "d, мм"), self.d_input),
                ("diameter_base", loc.get("D_label", "D, мм"), self.D_input),
                ("height", loc.get("height_label_mm", "H, мм"), self.height_input),
                ("weld_allowance", loc.get("weld_allowance_label", "Припуск на сварку, мм"), self.allowance_combo)
            ]:
                if data[field] < 0:
                    show_popup(loc.get(f"error_{field}_non_negative", f"{label} не может быть отрицательным"),
                               popup_type="error")
                    input_ctrl.SetFocus()
                    return False
                if field != "weld_allowance" and data[field] == 0:
                    show_popup(loc.get(f"error_{field}_positive", f"{label} должен быть положительным"),
                               popup_type="error")
                    input_ctrl.SetFocus()
                    return False

            # Проверка угла
            if data["angle"] != 0 and (data["angle"] <= 0 or data["angle"] >= 180):
                show_popup(loc.get("error_angle_range", "Угол должен быть в диапазоне 0–180°"), popup_type="error")
                self.angle_input.SetFocus()
                return False

            # Проверка наклона
            if data["steigung"] != 0 and data["steigung"] <= 0:
                show_popup(loc.get("error_steigung_positive", "Наклон должен быть положительным"), popup_type="error")
                self.steigung_input.SetFocus()
                return False

            return True
        except Exception as e:
            logging.error(f"Ошибка валидации данных: {e}")
            show_popup(loc.get("error", f"Ошибка валидации: {str(e)}"), popup_type="error")
            return False

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает собранные данные, запрашивает точку вставки и сохраняет данные в main_window.last_input.

        Args:
            data: Словарь с данными из полей ввода.

        Returns:
            bool: True, если обработка успешна, иначе False.
        """
        try:
            if not data or not self.validate_input(data):
                logging.error("Данные отсутствуют или невалидны в process_input")
                show_popup(loc.get("error_data_missing", "Некорректные данные"), popup_type="error")
                return False

            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            try:
                logging.info("Вызов at_point_input для выбора точки")
                point = at_point_input()
                logging.info(f"Получена точка: {point}")
            except Exception as e:
                logging.error(f"Ошибка вызова at_point_input: {e}")
                show_popup(loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}"), popup_type="error")
                return False
            finally:
                main_window.Iconize(False)
                main_window.Raise()
                main_window.SetFocus()
                wx.Yield()

            if point and isinstance(point, (list, tuple)) and len(point) == 3:
                self.insert_point = list(point)
                data["insert_point"] = self.insert_point
                self.update_status_bar_point_selected(self.insert_point)
                main_window.last_input = data  # Сохраняем полный словарь в main_window
                # Сохраняем только указанные поля в last_input.json
                last_input_data = {
                    "order_number": data["order_number"],
                    "material": data["material"],
                    "thickness": data["thickness"],
                    "weld_allowance": data["weld_allowance"]
                }
                save_last_input(self.last_input_file, last_input_data)
                logging.info(f"Точка вставки выбрана: {self.insert_point}, данные сохранены в main_window.last_input")
                main_window.switch_content("content_apps")  # Переключение на content_apps
                return True
            else:
                logging.warning(f"Некорректная точка вставки: {point}")
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                return False
        except Exception as e:
            logging.error(f"Ошибка обработки данных: {e}")
            show_popup(loc.get("error", f"Ошибка обработки: {str(e)}"), popup_type="error")
            return False
        finally:
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода, кроме загружаемых из common_data.json и last_input.json.
        """
        self.detail_input.SetValue("")
        self.d_input.SetValue("")
        self.D_input.SetValue("")
        self.d_inner.SetValue(True)
        self.D_inner.SetValue(True)
        self.height_input.SetValue("")
        self.steigung_input.SetValue("")
        self.angle_input.SetValue("")
        self.insert_point = None
        self.update_status_bar_no_point()
        self.height_input.Enable(True)
        self.steigung_input.Enable(True)
        self.angle_input.Enable(True)
        self.order_input.SetFocus()
        logging.info("Поля ввода очищены, кроме данных из common_data.json и last_input.json")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ConeContentPanel", size=(800, 600))
    panel = ConeContentPanel(frame)
    frame.Show()
    app.MainLoop()
