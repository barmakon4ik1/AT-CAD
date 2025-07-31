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
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings
)
from programms.at_ringe import main as run_rings

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
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
    try:
        panel = RingsContentPanel(parent)
        logging.info("Панель RingsContentPanel создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания RingsContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели колец: {str(e)}"), popup_type="error")
        return None


class RingsContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров колец.
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
        self.update_status_bar_no_point()
        self.setup_ui()
        self.order_input.SetFocus()

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
        image_path = os.path.abspath(RING_IMAGE_PATH)
        if not os.path.exists(image_path):
            logging.warning(f"Файл изображения колец '{image_path}' не найден")

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
        logging.info("Интерфейс RingsContentPanel настроен")

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["diameters"].SetLabel(loc.get("diameter_label", "Диаметры"))
        self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
        self.labels["diameters"].SetLabel(loc.get("diameters_label", "Диаметры (через запятую)"))

        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Отмена"][i]))
        adjust_button_widths(self.buttons)

        self.update_status_bar_no_point()
        self.Layout()
        logging.info("Язык UI обновлён")

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.

        Returns:
            dict: Словарь с данными (work_number, diameters, insert_point) или None при ошибке.
        """
        try:
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
            if not data or not data["diameters"]:
                show_popup(loc.get("no_data_error", "Необходимо ввести хотя бы один диаметр"), popup_type="error")
                logging.error("Данные не введены или отсутствуют диаметры")
                return False
            return True
        except Exception as e:
            logging.error(f"Ошибка валидации данных: {e}")
            show_popup(loc.get("error", f"Неверный формат данных: {str(e)}"), popup_type="error")
            return False

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает данные для построения колец.

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

            data["model"] = cad.model
            success = run_rings(ring_data=data)
            if success:
                cad.adoc.Regen(0)
                logging.info("Кольца успешно построены")
                self.clear_input_fields()
            else:
                show_popup(loc.get("ring_build_failed", "Ошибка построения колец"), popup_type="error")
                logging.error("Ошибка построения колец")
            return success
        except Exception as e:
            show_popup(loc.get("ring_build_error", f"Ошибка построения колец: {str(e)}"), popup_type="error")
            logging.error(f"Ошибка в process_input: {e}")
            return False

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.
        """
        self.order_input.SetValue("")
        self.diameters_input.SetValue("")
        if hasattr(self, "insert_point"):
            del self.insert_point
        self.update_status_bar_no_point()
        self.order_input.SetFocus()
        logging.info("Поля ввода очищены")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и построения колец.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест RingsContentPanel", size=(800, 600))
    panel = RingsContentPanel(frame)

    # Установка тестовых данных
    panel.order_input.SetValue("TestOrder")
    panel.diameters_input.SetValue("100, 200, 300")

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

            test_point = APoint(0.0, 0.0)
            panel.insert_point = test_point
            panel.update_status_bar_point_selected(test_point)
            print(f"Тест с фиксированной точкой: {test_point}")

            data = {
                "model": model,
                "input_point": test_point,
                "work_number": "TestOrder",
                "diameters": {"1": 100.0, "2": 200.0, "3": 300.0}
            }
            success = run_rings(ring_data=data)
            if success:
                print("Кольца построены успешно")
                adoc.Regen(0)
            else:
                print("Ошибка построения колец")

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
        logging.error(f"Ошибка в тестовом запуске: {e}")

    frame.Show()
    app.MainLoop()
