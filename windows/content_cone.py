"""
Файл: windows/content_cone.py
Описание:
Модуль для создания панели для ввода параметров развертки конуса.
Обеспечивает интерфейс для ввода данных конуса, обработку расчётов и вызов построения развертки.
Локализация осуществляется через loc.get с использованием словаря translations.
Настройки (шрифты, цвета) читаются из user_settings.json через load_user_settings.
"""

import math
import logging
import os
import time
from typing import Optional, Dict, List

import wx

from config.at_cad_init import ATCadInit
from config.at_config import *
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup,
    get_standard_font, apply_styles_to_panel, create_standard_buttons, load_common_data, adjust_button_widths,
    update_status_bar_point_selected, save_last_input
)
from programms.at_run_cone import run_application

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,  # Основной уровень для ошибок, INFO и WARNING для локализации и стилизации
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров конуса.

    Args:
        parent (wx.Window): Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров конуса.
    """
    return ConeContentPanel(parent)


class ConeContentPanel(wx.Panel):
    """
    Панель для ввода параметров развертки конуса.

    Attributes:
        settings (Dict): Настройки из user_settings.json.
        insert_point: Точка вставки в AutoCAD ([x, y, z]).
        last_input (Dict): Последние введённые данные.
        labels (Dict): Словарь текстовых меток для локализации.
        static_boxes (Dict): Словарь StaticBox для групп.
    """

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent (wx.Window): Родительский wx.Window (content_panel).
        """
        super().__init__(parent)
        self.settings = load_user_settings()  # Загружаем настройки
        background_color = self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
        self.SetBackgroundColour(wx.Colour(background_color))
        logging.info(f"Установлен цвет фона панели: {background_color}")
        self.parent = parent
        self._updating = False
        self._debounce_timer = wx.Timer(self)
        self.labels = {}  # Для хранения текстовых меток
        self.static_boxes = {}  # Для хранения StaticBox
        self.insert_point = None  # Точка вставки
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)

        # Загрузка последних введённых данных
        main_window = wx.GetTopLevelParent(self)
        self.last_input = getattr(main_window, 'last_input', {}) if hasattr(main_window, 'last_input') else {}
        logging.info(f"Загружены последние введённые данные: {self.last_input}")
        self.update_status_bar_no_point()

        self.setup_ui()
        self.order_input.SetFocus()

    def update_status_bar_no_point(self):
        """
        Обновляет статусную строку, если точка не выбрана.
        """
        update_status_bar_point_selected(self, None)

    def update_status_bar_point_selected(self):
        """
        Обновляет статусную строку с координатами выбранной точки.
        """
        update_status_bar_point_selected(self, self.insert_point)

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса, создавая компоновку с левой (изображение, кнопки)
        и правой (поля ввода) частями.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.labels.clear()
        self.static_boxes.clear()

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
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Единый размер для всех полей ввода и выпадающих списков
        font = get_standard_font()
        logging.info(f"Применён стандартный шрифт: {font.GetFaceName()}, размер={font.GetPointSize()}")

        # Загрузка данных из common_data.json
        common_data = load_common_data()
        logging.info(f"Сырые данные common_data в setup_ui: {common_data}")
        material_options = [mat["name"] for mat in common_data.get("material", [])]
        thickness_options = common_data.get("thicknesses", [])
        logging.info(f"Загружены материалы: {material_options}")
        logging.info(f"Загружены толщины: {thickness_options}")

        # Группа "Основные данные"
        main_data_label = loc.get("main_data_label", "Основные данные")
        if main_data_label == "main_data_label":
            logging.warning(f"Перевод для ключа 'main_data_label' не найден, использовано значение: {main_data_label}")
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, main_data_label)
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        main_data_box.SetForegroundColour(wx.Colour(self.settings.get("FOREGROUND_COLOR", DEFAULT_SETTINGS["FOREGROUND_COLOR"])))
        self.static_boxes["main_data"] = main_data_box

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        if order_label.GetLabel() == "order_label":
            logging.warning(f"Перевод для ключа 'order_label' не найден, использовано значение: К-№")
        order_label.SetFont(font)
        self.labels["order"] = order_label
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
        material_label_text = loc.get("material_label", "Материал")
        if material_label_text == "material_label":
            logging.warning(f"Перевод для ключа 'material_label' не найден, использовано значение: {material_label_text}")
        material_label = wx.StaticText(main_data_box, label=material_label_text)
        material_label.SetFont(font)
        self.labels["material"] = material_label
        last_material = self.last_input.get("material", "")
        material_value = last_material if last_material in material_options else (material_options[0] if material_options else "")
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                         value=material_value, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.material_combo.SetFont(font)
        material_sizer.AddStretchSpacer()
        material_sizer.Add(material_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        material_sizer.Add(self.material_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(material_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Толщина
        thickness_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thickness_label_text = loc.get("thickness_label", "Толщина")
        if thickness_label_text == "thickness_label":
            logging.warning(f"Перевод для ключа 'thickness_label' не найден, использовано значение: {thickness_label_text}")
        thickness_label = wx.StaticText(main_data_box, label=thickness_label_text)
        thickness_label.SetFont(font)
        self.labels["thickness"] = thickness_label
        last_thickness = str(self.last_input.get("thickness", "")).replace(',', '.')
        try:
            last_thickness_float = float(last_thickness)
            last_thickness = str(int(last_thickness_float)) if last_thickness_float.is_integer() else str(last_thickness_float)
        except ValueError:
            last_thickness = ""
        thickness_value = last_thickness if last_thickness in thickness_options else (thickness_options[4] if len(thickness_options) > 4 else "")
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options,
                                          value=thickness_value, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
        self.thickness_combo.SetFont(font)
        thickness_sizer.AddStretchSpacer()
        thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, 5)
        main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Диаметр"
        diameter_label = loc.get("diameter", "Диаметр")
        if diameter_label == "diameter":
            logging.warning(f"Перевод для ключа 'diameter' не найден, использовано значение: {diameter_label}")
        diameter_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, diameter_label)
        diameter_box = diameter_sizer.GetStaticBox()
        diameter_box.SetFont(font)
        diameter_box.SetForegroundColour(wx.Colour(self.settings.get("FOREGROUND_COLOR", DEFAULT_SETTINGS["FOREGROUND_COLOR"])))
        self.static_boxes["diameter"] = diameter_box

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label=loc.get("d_label", "d, мм"))
        if d_label.GetLabel() == "d_label":
            logging.warning(f"Перевод для ключа 'd_label' не найден, использовано значение: d, мм")
        d_label.SetFont(font)
        self.labels["d"] = d_label
        self.d_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_top", "")),
                                   size=INPUT_FIELD_SIZE)
        self.d_input.SetFont(font)
        d_sizer.AddStretchSpacer()
        d_sizer.Add(d_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        d_sizer.Add(self.d_input, 0, wx.ALL, 5)

        d_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        inner_label = loc.get("inner_label", "Внутренний")
        middle_label = loc.get("middle_label", "Средний")
        outer_label = loc.get("outer_label", "Внешний")
        if inner_label == "inner_label":
            logging.warning(f"Перевод для ключа 'inner_label' не найден, использовано значение: {inner_label}")
        if middle_label == "middle_label":
            logging.warning(f"Перевод для ключа 'middle_label' не найден, использовано значение: {middle_label}")
        if outer_label == "outer_label":
            logging.warning(f"Перевод для ключа 'outer_label' не найден, использовано значение: {outer_label}")
        self.d_inner = wx.RadioButton(diameter_box, label=inner_label, style=wx.RB_GROUP)
        self.d_middle = wx.RadioButton(diameter_box, label=middle_label)
        self.d_outer = wx.RadioButton(diameter_box, label=outer_label)
        self.d_inner.SetFont(font)
        self.d_middle.SetFont(font)
        self.d_outer.SetFont(font)
        self.d_inner.SetValue(self.last_input.get("d_type", "inner") == "inner")
        self.d_middle.SetValue(self.last_input.get("d_type", "inner") == "middle")
        self.d_outer.SetValue(self.last_input.get("d_type", "inner") == "outer")
        self.labels["d_inner"] = self.d_inner
        self.labels["d_middle"] = self.d_middle
        self.labels["d_outer"] = self.d_outer
        d_radio_sizer.AddStretchSpacer()
        d_radio_sizer.Add(self.d_inner, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_middle, 0, wx.RIGHT, 5)
        d_radio_sizer.Add(self.d_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(d_sizer, 0, wx.EXPAND | wx.ALL, 5)
        diameter_sizer.Add(d_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр основания (D)
        D_sizer = wx.BoxSizer(wx.HORIZONTAL)
        D_label = wx.StaticText(diameter_box, label=loc.get("D_label", "D, мм"))
        if D_label.GetLabel() == "D_label":
            logging.warning(f"Перевод для ключа 'D_label' не найден, использовано значение: D, мм")
        D_label.SetFont(font)
        self.labels["D"] = D_label
        self.D_input = wx.TextCtrl(diameter_box, value=str(self.last_input.get("diameter_base", "")),
                                   size=INPUT_FIELD_SIZE)
        self.D_input.SetFont(font)
        D_sizer.AddStretchSpacer()
        D_sizer.Add(D_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        D_sizer.Add(self.D_input, 0, wx.ALL, 5)

        D_radio_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.D_inner = wx.RadioButton(diameter_box, label=inner_label, style=wx.RB_GROUP)
        self.D_middle = wx.RadioButton(diameter_box, label=middle_label)
        self.D_outer = wx.RadioButton(diameter_box, label=outer_label)
        self.D_inner.SetFont(font)
        self.D_middle.SetFont(font)
        self.D_outer.SetFont(font)
        self.D_inner.SetValue(self.last_input.get("D_type", "inner") == "inner")
        self.D_middle.SetValue(self.last_input.get("D_type", "inner") == "middle")
        self.D_outer.SetValue(self.last_input.get("D_type", "inner") == "outer")
        self.labels["D_inner"] = self.D_inner
        self.labels["D_middle"] = self.D_middle
        self.labels["D_outer"] = self.D_outer
        D_radio_sizer.AddStretchSpacer()
        D_radio_sizer.Add(self.D_inner, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_middle, 0, wx.RIGHT, 5)
        D_radio_sizer.Add(self.D_outer, 0, wx.RIGHT, 5)
        diameter_sizer.Add(D_sizer, 0, wx.EXPAND | wx.ALL, 5)
        diameter_sizer.Add(D_radio_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(diameter_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Группа "Высота"
        height_label = loc.get("height_label", "Высота")
        if height_label == "height_label":
            logging.warning(f"Перевод для ключа 'height_label' не найден, использовано значение: {height_label}")
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, height_label)
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        height_box.SetForegroundColour(wx.Colour(self.settings.get("FOREGROUND_COLOR", DEFAULT_SETTINGS["FOREGROUND_COLOR"])))
        self.static_boxes["height"] = height_box

        self.height_input = wx.TextCtrl(height_box, value=str(self.last_input.get("height", "")), size=INPUT_FIELD_SIZE)
        self.steigung_input = wx.TextCtrl(height_box, value=str(self.last_input.get("steigung", "")),
                                          size=INPUT_FIELD_SIZE)
        self.angle_input = wx.TextCtrl(height_box, value=str(self.last_input.get("angle", "")), size=INPUT_FIELD_SIZE)
        self.height_input.SetFont(font)
        self.steigung_input.SetFont(font)
        self.angle_input.SetFont(font)

        height_label_text = loc.get("height_label_mm", "H, мм")
        if height_label_text == "height_label_mm":
            logging.warning(f"Перевод для ключа 'height_label_mm' не найден, использовано значение: H, мм")
        height_label = wx.StaticText(height_box, label=height_label_text)
        steigung_label_text = loc.get("steigung_label", "Наклон")
        if steigung_label_text == "steigung_label":
            logging.warning(f"Перевод для ключа 'steigung_label' не найден, использовано значение: {steigung_label_text}")
        steigung_label = wx.StaticText(height_box, label=steigung_label_text)
        angle_label_text = loc.get("angle_label", "α°")
        if angle_label_text == "angle_label":
            logging.warning(f"Перевод для ключа 'angle_label' не найден, использовано значение: α°")
        angle_label = wx.StaticText(height_box, label=angle_label_text)
        height_label.SetFont(font)
        steigung_label.SetFont(font)
        angle_label.SetFont(font)
        self.labels["height"] = height_label
        self.labels["steigung"] = steigung_label
        self.labels["angle"] = angle_label

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
        allowance_label_text = loc.get("weld_allowance_label", "Припуск на сварку")
        if allowance_label_text == "weld_allowance_label":
            logging.warning(f"Перевод для ключа 'weld_allowance_label' не найден, использовано значение: {allowance_label_text}")
        allowance_label = wx.StaticText(self, label=allowance_label_text)
        allowance_label.SetFont(font)
        self.labels["allowance"] = allowance_label
        allowance_options = [str(i) for i in range(11)]
        self.allowance_combo = wx.ComboBox(self, choices=allowance_options,
                                          value=self.last_input.get("weld_allowance", "3"),
                                          style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
        self.allowance_combo.SetFont(font)
        allowance_sizer.AddStretchSpacer()
        allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_sizer.Add(self.allowance_combo, 0, wx.ALL, 5)
        self.right_sizer.Add(allowance_sizer, 0, wx.ALL | wx.EXPAND, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        logging.info("Стили применены к панели ConeContentPanel")
        self.Layout()
        logging.info("Интерфейс панели ConeContentPanel успешно настроен")

        # Устанавливаем фокус на order_input после создания интерфейса
        self.order_input.SetFocus()

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        main_data_label = loc.get("main_data_label", "Основные данные")
        if main_data_label == "main_data_label":
            logging.warning(f"Перевод для ключа 'main_data_label' не найден, использовано значение: {main_data_label}")
        self.static_boxes["main_data"].SetLabel(main_data_label)

        diameter_label = loc.get("diameter", "Диаметр")
        if diameter_label == "diameter":
            logging.warning(f"Перевод для ключа 'diameter' не найден, использовано значение: {diameter_label}")
        self.static_boxes["diameter"].SetLabel(diameter_label)

        height_label = loc.get("height_label", "Высота")
        if height_label == "height_label":
            logging.warning(f"Перевод для ключа 'height_label' не найден, использовано значение: {height_label}")
        self.static_boxes["height"].SetLabel(height_label)

        material_label = loc.get("material_label", "Материал")
        if material_label == "material_label":
            logging.warning(f"Перевод для ключа 'material_label' не найден, использовано значение: {material_label}")
        self.labels["material"].SetLabel(material_label)

        thickness_label = loc.get("thickness_label", "Толщина")
        if thickness_label == "thickness_label":
            logging.warning(f"Перевод для ключа 'thickness_label' не найден, использовано значение: {thickness_label}")
        self.labels["thickness"].SetLabel(thickness_label)

        inner_label = loc.get("inner_label", "Внутренний")
        if inner_label == "inner_label":
            logging.warning(f"Перевод для ключа 'inner_label' не найден, использовано значение: {inner_label}")
        self.labels["d_inner"].SetLabel(inner_label)
        self.labels["D_inner"].SetLabel(inner_label)

        middle_label = loc.get("middle_label", "Средний")
        if middle_label == "middle_label":
            logging.warning(f"Перевод для ключа 'middle_label' не найден, использовано значение: {middle_label}")
        self.labels["d_middle"].SetLabel(middle_label)
        self.labels["D_middle"].SetLabel(middle_label)

        outer_label = loc.get("outer_label", "Внешний")
        if outer_label == "outer_label":
            logging.warning(f"Перевод для ключа 'outer_label' не найден, использовано значение: {outer_label}")
        self.labels["d_outer"].SetLabel(outer_label)
        self.labels["D_outer"].SetLabel(outer_label)

        steigung_label = loc.get("steigung_label", "Наклон")
        if steigung_label == "steigung_label":
            logging.warning(f"Перевод для ключа 'steigung_label' не найден, использовано значение: {steigung_label}")
        self.labels["steigung"].SetLabel(steigung_label)

        allowance_label = loc.get("weld_allowance_label", "Припуск на сварку")
        if allowance_label == "weld_allowance_label":
            logging.warning(f"Перевод для ключа 'weld_allowance_label' не найден, использовано значение: {allowance_label}")
        self.labels["allowance"].SetLabel(allowance_label)

        order_label = loc.get("order_label", "К-№")
        if order_label == "order_label":
            logging.warning(f"Перевод для ключа 'order_label' не найден, использовано значение: {order_label}")
        self.labels["order"].SetLabel(order_label)

        d_label = loc.get("d_label", "d, мм")
        if d_label == "d_label":
            logging.warning(f"Перевод для ключа 'd_label' не найден, использовано значение: {d_label}")
        self.labels["d"].SetLabel(d_label)

        D_label = loc.get("D_label", "D, мм")
        if D_label == "D_label":
            logging.warning(f"Перевод для ключа 'D_label' не найден, использовано значение: {D_label}")
        self.labels["D"].SetLabel(D_label)

        height_label_mm = loc.get("height_label_mm", "H, мм")
        if height_label_mm == "height_label_mm":
            logging.warning(f"Перевод для ключа 'height_label_mm' не найден, использовано значение: {height_label_mm}")
        self.labels["height"].SetLabel(height_label_mm)

        angle_label = loc.get("angle_label", "α°")
        if angle_label == "angle_label":
            logging.warning(f"Перевод для ключа 'angle_label' не найден, использовано значение: {angle_label}")
        self.labels["angle"].SetLabel(angle_label)

        # Обновление текста кнопок
        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            button_label = loc.get(key, ["ОК", "Очистить", "Отмена"][i])
            if button_label == key:
                logging.warning(f"Перевод для ключа '{key}' не найден, использовано значение: {button_label}")
            self.buttons[i].SetLabel(button_label)

        adjust_button_widths(self.buttons)
        self.update_status_bar_no_point()
        self.Layout()
        logging.info("Язык интерфейса ConeContentPanel успешно обновлён")

    def _clear_height_fields(self) -> None:
        """
        Очищает поля ввода высоты, наклона и угла.
        """
        wx.CallAfter(self.height_input.SetValue, "")
        wx.CallAfter(self.steigung_input.SetValue, "")
        wx.CallAfter(self.angle_input.SetValue, "")
        logging.info("Поля высоты, наклона и угла очищены")

    def on_height_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода высоты с задержкой (debounce).

        Args:
            event (wx.Event): Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).

        Args:
            event (wx.Event): Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).

        Args:
            event (wx.Event): Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки.

        Args:
            event (wx.Event): Событие таймера.
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

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет данные, запрашивает точку вставки в AutoCAD и вызывает run_application для построения развертки.
        Очищает поля, не указанные в last_input.json, и оставляет окно content_cone для нового ввода.

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        try:
            # Минимизируем окно для выбора точки
            main_window = self.GetTopLevelParent()
            main_window.Iconize(True)
            cad = ATCadInit()
            if not cad.is_initialized():
                error_msg = loc.get('cad_init_error', 'Ошибка инициализации AutoCAD')
                show_popup(error_msg, popup_type="error")
                logging.error(error_msg)
                return
            adoc = cad.adoc
            point = at_point_input(adoc)  # Передаём adoc для корректной инициализации
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()
            time.sleep(0.1)

            if point and isinstance(point, (list, tuple)) and len(point) == 3:
                self.insert_point = list(point)  # Сохраняем как список [x, y, z]
                self.update_status_bar_point_selected()
                logging.info(f"Точка вставки выбрана: {self.insert_point}, type={type(self.insert_point)}")
            else:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                logging.error(f"Точка вставки не выбрана или некорректна: {point}")
                self.update_status_bar_no_point()
                return

            # Проверка и обработка остальных данных
            try:
                d = float(self.d_input.GetValue().replace(',', '.')) if self.d_input.GetValue().strip() else None
                D = float(self.D_input.GetValue().replace(',', '.')) if self.D_input.GetValue().strip() else None
                if d is None or D is None:
                    error_msg = loc.get("error_diameter_required", "Требуется ввести диаметры")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if d > D:
                    d, D = D, d
                thickness = float(
                    self.thickness_combo.GetValue().replace(',', '.')) if self.thickness_combo.GetValue().strip() else None
                allowance = float(
                    self.allowance_combo.GetValue().replace(',', '.')) if self.allowance_combo.GetValue().strip() else 0

                if thickness is None:
                    error_msg = loc.get("error_thickness_required", "Требуется выбрать толщину")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if D <= 0:
                    error_msg = loc.get("error_base_diameter_positive", "Диаметр основания должен быть положительным")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if d < 0:
                    error_msg = loc.get("error_top_diameter_non_negative", "Диаметр вершины не может быть отрицательным")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if allowance < 0:
                    error_msg = loc.get("error_weld_allowance_non_negative", "Припуск на сварку не может быть отрицательным")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if thickness < 0:
                    error_msg = loc.get("error_thickness_positive", "Толщина должна быть положительной")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return

                d_type = "inner" if self.d_inner.GetValue() else "middle" if self.d_middle.GetValue() else "outer"
                D_type = "inner" if self.D_inner.GetValue() else "middle" if self.D_middle.GetValue() else "outer"

                try:
                    diameter_top = at_diameter(d, thickness, d_type)
                    diameter_base = at_diameter(D, thickness, D_type)
                except Exception as e:
                    error_msg = loc.get("error_diameter_calculation", f"Ошибка расчёта диаметра: {str(e)}")
                    show_popup(error_msg, popup_type="error")
                    logging.error(f"Ошибка расчёта диаметра: {e}")
                    return

                if diameter_base <= 0:
                    error_msg = loc.get("error_base_diameter_positive", "Диаметр основания должен быть положительным")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return
                if diameter_top < 0:
                    error_msg = loc.get("error_top_diameter_non_negative", "Диаметр вершины не должен быть отрицательным")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return

                height = None
                if self.height_input.GetValue().strip():
                    height = float(self.height_input.GetValue().replace(',', '.'))
                    if height <= 0:
                        error_msg = loc.get("error_height_positive", "Высота должна быть положительной")
                        show_popup(error_msg, popup_type="error")
                        logging.error(error_msg)
                        return
                elif self.steigung_input.GetValue().strip():
                    steigung = float(self.steigung_input.GetValue().replace(',', '.'))
                    if steigung <= 0:
                        error_msg = loc.get("error_steigung_positive", "Наклон должен быть положительным")
                        show_popup(error_msg, popup_type="error")
                        logging.error(error_msg)
                        return
                    height = at_cone_height(D, d, steigung=steigung)
                elif self.angle_input.GetValue().strip():
                    angle = float(self.angle_input.GetValue().replace(',', '.'))
                    if angle <= 0 or angle >= 180:
                        error_msg = loc.get("error_angle_range", "Угол должен быть в диапазоне от 0 до 180 градусов")
                        show_popup(error_msg, popup_type="error")
                        logging.error(error_msg)
                        return
                    height = at_cone_height(D, d, angle=angle)
                else:
                    error_msg = loc.get("error_height_steigung_angle_required", "Необходимо ввести высоту, наклон или угол")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return

                if height is None or height <= 0:
                    error_msg = loc.get("error_height_positive", "Высота должна быть положительной")
                    show_popup(error_msg, popup_type="error")
                    logging.error(error_msg)
                    return

                height += allowance

                thickness_text = f"{thickness:.2f} {loc.get('mm', 'мм')}"
                if thickness_text == f"{thickness:.2f} mm":
                    logging.warning(f"Перевод для ключа 'mm' не найден, использовано значение: мм")

                # Инициализация AutoCAD для получения model
                model = cad.model

                data = {
                    "model": model,
                    "input_point": self.insert_point,  # Передаём точку как список [x, y, z]
                    "diameter_base": diameter_base,
                    "diameter_top": diameter_top,
                    "height": height,
                    "layer_name": "0",
                    "order_number": self.order_input.GetValue(),
                    "detail_number": self.detail_input.GetValue(),
                    "material": self.material_combo.GetValue(),
                    "thickness_text": thickness_text
                }

                # Сохраняем только необходимые данные в last_input.json
                last_input_data = {
                    "order_number": str(self.order_input.GetValue()),
                    "material": str(self.material_combo.GetValue()),
                    "thickness": str(self.thickness_combo.GetValue()),
                    "weld_allowance": str(self.allowance_combo.GetValue())
                }
                main_window = wx.GetTopLevelParent(self)
                main_window.last_input = last_input_data
                save_last_input(LAST_CONE_INPUT_FILE, last_input_data)
                logging.info(f"Данные сохранены в {LAST_CONE_INPUT_FILE}: {last_input_data}")

                # Вызов run_application
                try:
                    success = run_application(data)
                    if success:
                        cad.adoc.Regen(1)  # Обновление всех видовых экранов
                        # Очищаем только поля, связанные с геометрией
                        self.detail_input.SetValue("")
                        self.d_input.SetValue("")
                        self.D_input.SetValue("")
                        self.d_inner.SetValue(True)
                        self.D_inner.SetValue(True)
                        self.height_input.SetValue("")
                        self.steigung_input.SetValue("")
                        self.angle_input.SetValue("")
                        if hasattr(self, "insert_point"):
                            del self.insert_point
                        self.update_status_bar_no_point()
                        logging.info("Поля геометрии очищены после успешного построения")
                    else:
                        error_msg = loc.get("cone_build_failed", "Построение отменено или завершилось с ошибкой")
                        show_popup(error_msg, popup_type="error")
                        logging.error(error_msg)
                except Exception as e:
                    error_msg = loc.get("cone_build_error", f"Ошибка построения: {str(e)}")
                    show_popup(error_msg, popup_type="error")
                    logging.error(f"Ошибка в run_application: {e}")

            except (ValueError, TypeError) as e:
                error_msg = loc.get("error_invalid_number_format", "Неверный формат числа")
                show_popup(error_msg, popup_type="error")
                logging.error(f"Ошибка формата числа в on_ok: {e}")
        except Exception as e:
            error_msg = loc.get("point_selection_error", f"Ошибка выбора точки: {str(e)}")
            show_popup(error_msg, popup_type="error")
            logging.error(f"Ошибка выбора точки: {e}")
            self.update_status_bar_no_point()

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода и сбрасывает значения комбобоксов на значения по умолчанию из common_data.json.
        Сохраняет очищенные данные в last_input.json.

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        # Загружаем данные из common_data.json
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", [])]
        thickness_options = common_data.get("thicknesses", ["1", "1.5", "2", "3", "4", "5", "6", "8", "10", "12", "14", "15"])
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetValue(material_options[0] if material_options else "")
        self.thickness_combo.SetValue(thickness_options[0] if thickness_options else "")
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
        self.update_status_bar_no_point()
        logging.info("Все поля ввода очищены, комбобоксы сброшены на значения по умолчанию")

    def on_cancel(self, event: wx.Event) -> None:
        """
        Переключает контент на начальную страницу (content_apps) при нажатии кнопки "Отмена".

        Args:
            event (wx.Event): Событие нажатия кнопки.
        """
        main_window = wx.GetTopLevelParent(self)
        if hasattr(main_window, "switch_content"):
            main_window.switch_content("content_apps")
            logging.info("Переключение на content_apps по нажатию кнопки 'Отмена'")
        else:
            error_msg = loc.get("error_switch_content", "Ошибка: невозможно переключить контент")
            show_popup(error_msg, popup_type="error")
            logging.error(error_msg)

if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и построения развертки конуса.
    """
    import wx
    from config.at_cad_init import ATCadInit
    from programms.at_input import at_point_input

    app = wx.App(False)
    frame = wx.Frame(None, title="Тест ConeContentPanel", size=(800, 600))
    panel = ConeContentPanel(frame)

    # Установка тестовых данных
    panel.order_input.SetValue("TestOrder")
    panel.detail_input.SetValue("TestDetail")
    panel.material_combo.SetValue("Сталь")
    panel.thickness_combo.SetValue("2")
    panel.d_input.SetValue("100")
    panel.D_input.SetValue("500")
    panel.d_inner.SetValue(True)
    panel.D_inner.SetValue(True)
    panel.height_input.SetValue("300")
    panel.allowance_combo.SetValue("3")

    # Тест выбора точки и построения
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            logging.error("Не удалось инициализировать AutoCAD")
            print("Ошибка: Не удалось инициализировать AutoCAD")
        else:
            adoc, model = cad.adoc, cad.model
            print(f"AutoCAD Version: {adoc.Application.Version}")
            print(f"Active Document: {adoc.Name}")

            # Тест с фиксированной точкой
            test_point = [0.0, 0.0, 0.0]
            panel.insert_point = test_point
            panel.update_status_bar_point_selected()
            print(f"Тест с фиксированной точкой: {test_point}")

            data = {
                "model": model,
                "input_point": test_point,
                "diameter_base": 500.0,
                "diameter_top": 100.0,
                "height": 303.0,  # 300 + 3 (припуск)
                "layer_name": "0",
                "order_number": "TestOrder",
                "detail_number": "TestDetail",
                "material": "Сталь",
                "thickness_text": "2.00 мм"
            }
            success = run_application(data)
            if success:
                print("Развертка конуса построена успешно")
                adoc.Regen(1)
            else:
                print("Ошибка построения развертки")

            # Тест с точкой от пользователя
            print("Получение точки от пользователя...")
            user_point = at_point_input(adoc)
            if user_point is None:
                print("Точка не выбрана, используется точка по умолчанию [500.0, 375.0, 0.0]")
                user_point = [500.0, 375.0, 0.0]
            panel.insert_point = user_point
            panel.update_status_bar_point_selected()
            print(f"Тест с пользовательской точкой: {user_point}")

            data["input_point"] = user_point
            success = run_application(data)
            if success:
                print("Развертка конуса построена успешно")
                adoc.Regen(1)
            else:
                print("Ошибка построения развертки")

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
        logging.error(f"Ошибка в тестовом запуске: {e}")

    frame.Show()
    app.MainLoop()
