# windows/content_cone.py
"""
Модуль для создания панели для ввода параметров развертки конуса.
"""

import math
import logging
import os
from typing import Optional, Dict

import wx
from config.at_config import (
    FONT_NAME, FONT_SIZE, FONT_TYPE, BACKGROUND_COLOR, FOREGROUND_COLOR,
    CONE_IMAGE_PATH, INPUT_FIELD_SIZE, LAST_CONE_INPUT_FILE
)
from programms.at_construction import at_diameter, at_cone_height, at_steigung
from programms.at_input import at_point_input
from locales.at_localization import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup,
    get_standard_font, apply_styles_to_panel, create_standard_buttons, load_common_data, adjust_button_widths,
    update_status_bar_point_selected, save_last_input
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
        self.labels = {}  # Для хранения текстовых меток
        self.static_boxes = {}  # Для хранения StaticBox
        self.Bind(wx.EVT_TIMER, self.on_debounce_timeout, self._debounce_timer)

        # Загрузка последних введённых данных
        self.last_input = wx.GetApp().GetTopWindow().last_input if hasattr(wx.GetApp().GetTopWindow(),
                                                                           'last_input') else {}
        # Точка вставки не загружается из JSON
        self.insert_point = None
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
        self.buttons = create_standard_buttons(self, self.on_select_point, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        # Правая часть: поля ввода
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Единый размер для всех полей ввода и выпадающих списков
        font = get_standard_font()

        # Загрузка данных из common_data.json
        common_data = load_common_data()
        logging.info(f"Сырые данные common_data в setup_ui: {common_data}")
        material_options = common_data.get("material", [])
        thickness_options = common_data.get("thicknesses", [])
        logging.info(f"Загружены материалы: {material_options}")
        logging.info(f"Загружены толщины: {thickness_options}")

        # Группа "Основные данные"
        main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
        main_data_box = main_data_sizer.GetStaticBox()
        main_data_box.SetFont(font)
        main_data_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))
        self.static_boxes["main_data"] = main_data_box

        # Номер заказа и детали
        order_sizer = wx.BoxSizer(wx.HORIZONTAL)
        order_label = wx.StaticText(main_data_box, label="К-№")
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
        material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        material_label.SetFont(font)
        self.labels["material"] = material_label
        last_material = self.last_input.get("material", "")
        material_value = last_material if last_material in material_options else material_options[0]
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options,
                                          value=material_value, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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
        last_thickness = str(self.last_input.get("thickness", "")).replace(',', '.')
        try:
            last_thickness_float = float(last_thickness)
            last_thickness = str(int(last_thickness_float)) if last_thickness_float.is_integer() else str(
                last_thickness_float)
        except ValueError:
            last_thickness = ""
        thickness_value = last_thickness if last_thickness in thickness_options else thickness_options[0]
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options,
                                           value=thickness_value, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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
        self.static_boxes["diameter"] = diameter_box

        # Диаметр вершины (d)
        d_sizer = wx.BoxSizer(wx.HORIZONTAL)
        d_label = wx.StaticText(diameter_box, label="d, мм")
        d_label.SetFont(font)
        self.labels["d"] = d_label
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
        D_label = wx.StaticText(diameter_box, label="D, мм")
        D_label.SetFont(font)
        self.labels["D"] = D_label
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
        height_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("height_label", "Высота"))
        height_box = height_sizer.GetStaticBox()
        height_box.SetFont(font)
        height_box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))
        self.static_boxes["height"] = height_box

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
        allowance_label = wx.StaticText(self, label=loc.get("weld_allowance_label", "Припуск на сварку"))
        allowance_label.SetFont(font)
        self.labels["allowance"] = allowance_label
        allowance_options = [str(i) for i in range(11)]
        self.allowance_combo = wx.ComboBox(self, choices=allowance_options,
                                           value=self.last_input.get("weld_allowance", "0"),
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
        self.Layout()
        logging.info("Интерфейс панели ConeContentPanel успешно настроен")

        # Устанавливаем фокус на order_input после создания интерфейса
        self.order_input.SetFocus()

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["diameter"].SetLabel(loc.get("diameter", "Диаметр"))
        self.static_boxes["height"].SetLabel(loc.get("height_label", "Высота"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
        self.labels["d_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
        self.labels["d_middle"].SetLabel(loc.get("middle_label", "Средний"))
        self.labels["d_outer"].SetLabel(loc.get("outer_label", "Внешний"))
        self.labels["D_inner"].SetLabel(loc.get("inner_label", "Внутренний"))
        self.labels["D_middle"].SetLabel(loc.get("middle_label", "Средний"))
        self.labels["D_outer"].SetLabel(loc.get("outer_label", "Внешний"))
        self.labels["steigung"].SetLabel(loc.get("steigung_label", "Наклон"))
        self.labels["allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку"))

        # Обновление текста кнопок
        self.buttons[0].SetLabel(loc.get("insert_point_label", "Точка вставки"))
        self.buttons[1].SetLabel(loc.get("ok_button", "ОК"))
        self.buttons[2].SetLabel(loc.get("clear_button", "Очистить"))
        self.buttons[3].SetLabel(loc.get("cancel_button", "Отмена"))
        self.adjust_button_widths()

        self.Layout()

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
            event: Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_steigung_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода наклона с задержкой (debounce).

        Args:
            event: Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_angle_text(self, event: wx.Event) -> None:
        """
        Запускает обработку ввода угла с задержкой (debounce).

        Args:
            event: Событие ввода текста.
        """
        self._debounce_timer.Stop()
        self._debounce_timer.Start(500, oneShot=True)
        event.Skip()

    def on_debounce_timeout(self, event: wx.Event) -> None:
        """
        Выполняет расчёты высоты, наклона или угла после задержки.

        Args:
            event: Событие таймера.
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
        Запрашивает точку вставки в AutoCAD и сохраняет её в переменной.

        Args:
            event: Событие нажатия кнопки.
        """
        try:
            point = at_point_input(self.cad.adoc)
            if point and hasattr(point, "x") and hasattr(point, "y"):
                self.insert_point = point
                update_status_bar_point_selected(self, self.insert_point)
                show_popup(
                    loc.get("point_selected").format(point.x, point.y),
                    popup_type="info"
                )
                logging.info(f"Точка вставки выбрана: x={point.x}, y={point.y}, type={type(point)}")
            else:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                logging.error(f"Точка вставки не выбрана или некорректна: {point}")
                update_status_bar_point_selected(self, None)
        except Exception as e:
            show_popup(loc.get("point_selection_error", "Ошибка выбора точки: {}").format(str(e)), popup_type="error")
            logging.error(f"Ошибка выбора точки: {e}")
            update_status_bar_point_selected(self, None)

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет данные и вызывает run_application для построения развертки.

        Args:
            event: Событие нажатия кнопки.
        """
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
                    self.cad.adoc.Regen(0)  # Обновление активного видового экрана
                    # show_popup(loc.get("cone_build_success", "Развертка конуса успешно построена"), popup_type="info")
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
        Очищает все поля ввода и сбрасывает значения комбобоксов на значения по умолчанию из common_data.json.
        Сохраняет очищенные данные в last_input.json.

        Args:
            event: Событие нажатия кнопки.
        """
        # Загружаем данные из common_data.json
        common_data = load_common_data()
        material_options = common_data.get("material", ["1.4301", "1.4404", "1.4571"])
        thickness_options = common_data.get("thicknesses",
                                            ["1", "1.5", "2", "3", "4", "5", "6", "8", "10", "12", "14", "15"])
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.material_combo.SetValue(material_options[0])
        self.thickness_combo.SetValue(thickness_options[0])
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

    def on_cancel(self, event: wx.Event) -> None:
        """
        Переключает контент на начальную страницу (content_apps) при нажатии кнопки "Отмена".

        Args:
            event: Событие нажатия кнопки.
        """
        main_window = wx.GetTopLevelParent(self)
        if hasattr(main_window, "switch_content"):
            main_window.switch_content("content_apps")
            logging.info("Переключение на content_apps по нажатию кнопки 'Отмена'")
        else:
            logging.error("Главное окно не имеет метода switch_content")
            show_popup(loc.get("error_switch_content", "Ошибка: невозможно переключить контент"), popup_type="error")
