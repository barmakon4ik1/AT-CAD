# windows/content_rings.py
"""
Модуль для создания панели для ввода параметров колец.
"""

import logging
import os
from typing import Optional, Dict

import wx
from pyautocad import APoint

from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel, create_standard_buttons, adjust_button_widths,
    update_status_bar_point_selected
)
from programms.at_ringe import main as run_rings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров колец.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров колец.
    """
    logging.debug("Создание панели RingsContentPanel")
    try:
        panel = RingsContentPanel(parent)
        logging.info("Панель RingsContentPanel успешно создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания RingsContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели колец: {str(e)}"), popup_type="error")
        return None


class RingsContentPanel(wx.Panel):
    """
    Панель для ввода параметров колец.
    """

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
        """
        logging.debug("Инициализация RingsContentPanel")
        super().__init__(parent)
        self.settings = load_user_settings()  # Загружаем настройки
        background_color = self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
        self.SetBackgroundColour(background_color)
        self.parent = parent
        self.labels = {}  # Для хранения текстовых меток
        self.static_boxes = {}  # Для хранения StaticBox
        self.insert_point = None  # Точка вставки
        self.update_status_bar_no_point()
        self.setup_ui()
        self.order_input.SetFocus()

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
        logging.debug("Настройка UI для RingsContentPanel")
        try:
            if self.GetSizer():
                self.GetSizer().Clear(True)
                self.SetSizer(None)  # Очистка текущего sizer'а
            self.labels.clear()
            self.static_boxes.clear()

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)

            # Проверка существования изображения (необязательно)
            image_path = os.path.abspath(RING_IMAGE_PATH)
            if not os.path.exists(image_path):
                logging.warning(f"Файл изображения колец '{image_path}' не найден, продолжаем без изображения")

            # Изображение колец
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
            font = get_standard_font()

            # Группа "Основные данные"
            main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
            main_data_box = main_data_sizer.GetStaticBox()
            main_data_box.SetFont(font)
            self.static_boxes["main_data"] = main_data_box

            # Номер заказа
            order_sizer = wx.BoxSizer(wx.HORIZONTAL)
            order_label = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
            order_label.SetFont(font)
            self.labels["order"] = order_label
            self.order_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
            self.order_input.SetFont(font)
            order_sizer.AddStretchSpacer()
            order_sizer.Add(order_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            order_sizer.Add(self.order_input, 0, wx.RIGHT, 10)
            main_data_sizer.Add(order_sizer, 0, wx.ALL | wx.EXPAND, 5)

            self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

            # Группа "Диаметры"
            diameters_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("diameter_label", "Диаметры"))
            diameters_box = diameters_sizer.GetStaticBox()
            diameters_box.SetFont(font)
            self.static_boxes["diameters"] = diameters_box

            # Диаметры (многострочный ввод)
            diameters_input_sizer = wx.BoxSizer(wx.HORIZONTAL)
            diameters_label = wx.StaticText(diameters_box, label=loc.get("diameters_label", "Диаметры (через запятую)"))
            diameters_label.SetFont(font)
            self.labels["diameters"] = diameters_label
            self.diameters_input = wx.TextCtrl(diameters_box, value="", style=wx.TE_MULTILINE, size=(INPUT_FIELD_SIZE[0], 100))
            self.diameters_input.SetFont(font)
            diameters_input_sizer.AddStretchSpacer()
            diameters_input_sizer.Add(diameters_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            diameters_input_sizer.Add(self.diameters_input, 0, wx.ALL, 5)
            diameters_sizer.Add(diameters_input_sizer, 0, wx.ALL | wx.EXPAND, 5)

            self.right_sizer.Add(diameters_sizer, 0, wx.EXPAND | wx.ALL, 10)

            main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
            self.SetSizer(main_sizer)
            apply_styles_to_panel(self)
            self.Layout()
            logging.info("Интерфейс панели RingsContentPanel успешно настроен")

            # Устанавливаем фокус на order_input
            self.order_input.SetFocus()

        except Exception as e:
            logging.error(f"Ошибка настройки UI для RingsContentPanel: {e}")
            show_popup(loc.get("error", f"Ошибка настройки интерфейса: {str(e)}"), popup_type="error")
            raise

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        logging.debug("Обновление языка UI для RingsContentPanel")
        try:
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["diameters"].SetLabel(loc.get("diameter_label", "Диаметры"))
            self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
            self.labels["diameters"].SetLabel(loc.get("diameters_label", "Диаметры (через запятую)"))

            # Обновление текста кнопок
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
            self.buttons[2].SetLabel(loc.get("cancel_button", "Отмена"))
            adjust_button_widths(self.buttons)

            self.update_status_bar_no_point()
            self.Layout()
            logging.info("Язык UI успешно обновлён")
        except Exception as e:
            logging.error(f"Ошибка обновления языка UI: {e}")
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")

    def get_input_data(self) -> Optional[Dict]:
        """
        Возвращает введённые данные в виде словаря.

        Returns:
            dict: Словарь с данными (work_number, diameters, insert_point) или None при ошибке.
        """
        try:
            # Парсинг диаметров
            diameters_text = self.diameters_input.GetValue().strip()
            diameters = {}
            if diameters_text:
                for i, value in enumerate(diameters_text.split(",")):
                    try:
                        diameter = float(value.strip().replace(',', '.'))
                        if diameter <= 0:
                            logging.error(f"Недопустимое значение диаметра: {diameter}")
                            return None
                        diameters[str(i + 1)] = diameter
                    except ValueError:
                        logging.error(f"Некорректный диаметр: {value}")
                        return None

            return {
                "work_number": self.order_input.GetValue().strip(),
                "diameters": diameters,
                "insert_point": self.insert_point
            }
        except Exception as e:
            logging.error(f"Ошибка получения данных из RingsContentPanel: {e}")
            return None

    def on_ok(self, event: wx.Event) -> None:
        """
        Проверяет данные, запрашивает точку вставки в AutoCAD и вызывает run_rings для построения колец.
        Очищает поля и оставляет окно для нового ввода.

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки OK в RingsContentPanel")
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
            ring_data = self.get_input_data()
            if not ring_data or not ring_data["diameters"]:
                show_popup(loc.get("no_data_error", "Необходимо ввести хотя бы один диаметр"), popup_type="error")
                logging.error("Данные не введены или отсутствуют диаметры")
                return

            logging.debug(f"Данные для колец: {ring_data}")

            # Инициализация AutoCAD
            cad = ATCadInit()
            if not cad.is_initialized():
                show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
                logging.error("Не удалось инициализировать AutoCAD")
                return
            ring_data["model"] = cad.model

            # Вызов обработки колец
            success = run_rings(ring_data=ring_data)
            if success:
                cad.adoc.Regen(0)  # Обновление активного видового экрана
                logging.info("Кольца успешно построены")
                # Очищаем поля
                self.order_input.SetValue("")
                self.diameters_input.SetValue("")
                if hasattr(self, "insert_point"):
                    del self.insert_point
                self.update_status_bar_no_point()
                self.order_input.SetFocus()
            else:
                show_popup(loc.get("ring_build_failed", "Построение колец отменено или завершилось с ошибкой"), popup_type="error")
                logging.error("Ошибка построения колец")

        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")
            show_popup(loc.get("ring_build_error", f"Ошибка построения колец: {str(e)}"), popup_type="error")
            self.update_status_bar_no_point()

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Очистить в RingsContentPanel")
        self.order_input.SetValue("")
        self.diameters_input.SetValue("")
        if hasattr(self, "insert_point"):
            del self.insert_point
        self.update_status_bar_no_point()
        self.order_input.SetFocus()
        logging.info("Поля ввода очищены")

    def on_cancel(self, event: wx.Event) -> None:
        """
        Переключает контент на начальную страницу (content_apps) при нажатии кнопки "Отмена".

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Отмена в RingsContentPanel")
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
