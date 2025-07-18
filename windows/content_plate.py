"""
Модуль для создания панели для ввода параметров листа.
"""

import logging
import os
from typing import Optional, Dict, List
import wx
from pyautocad import APoint

from config.at_cad_init import ATCadInit
from config.at_config import BACKGROUND_COLOR, PLATE_IMAGE_PATH, INPUT_FIELD_SIZE
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    load_common_data
)
from programms.at_run_plate import run_plate

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров листа.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров листа.
    """
    logging.debug("Создание панели PlateContentPanel")
    try:
        panel = PlateContentPanel(parent)
        logging.info("Панель PlateContentPanel успешно создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания PlateContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели листа: {str(e)}"), popup_type="error")
        return None


class PlateContentPanel(wx.Panel):
    """
    Панель для ввода параметров листа.
    """

    def __init__(self, parent):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
        """
        logging.debug("Инициализация PlateContentPanel")
        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.parent = parent
        self.labels = {}  # Для хранения текстовых меток
        self.static_boxes = {}  # Для хранения StaticBox
        self.insert_point = None  # Точка вставки
        self.size_inputs = []  # Список полей ввода для таблицы размеров
        self.update_status_bar_no_point()
        self.setup_ui()
        self.melt_no_input.SetFocus()

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
        logging.debug("Настройка UI для PlateContentPanel")
        try:
            if self.GetSizer():
                self.GetSizer().Clear(True)
            self.labels.clear()
            self.static_boxes.clear()
            self.size_inputs.clear()

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)

            # Проверка существования изображения
            image_path = os.path.abspath(PLATE_IMAGE_PATH)
            if not os.path.exists(image_path):
                logging.warning(f"Файл изображения листа '{image_path}' не найден")
                show_popup(loc.get("image_not_found", f"Изображение не найдено: {image_path}"), popup_type="error")

            # Изображение листа
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

            # Загрузка данных из common_data.json
            common_data = load_common_data()
            material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
            thickness_options = common_data.get("thicknesses", [])
            logging.info(f"Загружены материалы: {material_options}")
            logging.info(f"Загружены толщины: {thickness_options}")

            # Установка толщины по умолчанию
            default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0]
            if default_thickness != "4" and default_thickness != "4.0":
                logging.warning(
                    f"Толщина '4' не найдена в списке толщин, выбрано значение по умолчанию: {default_thickness}")

            # Группа "Основные данные"
            main_data_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("main_data_label", "Основные данные"))
            main_data_box = main_data_sizer.GetStaticBox()
            main_data_box.SetFont(font)
            self.static_boxes["main_data"] = main_data_box

            # Материал
            material_sizer = wx.BoxSizer(wx.HORIZONTAL)
            material_label = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
            material_label.SetFont(font)
            self.labels["material"] = material_label
            self.material_combo = wx.ComboBox(main_data_box, choices=material_options, value=material_options[0],
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
            self.labels["thickness"] = thickness_label
            self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options, value=default_thickness,
                                               style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
            self.thickness_combo.SetFont(font)
            thickness_sizer.AddStretchSpacer()
            thickness_sizer.Add(thickness_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            thickness_sizer.Add(self.thickness_combo, 0, wx.ALL, 5)
            main_data_sizer.Add(thickness_sizer, 0, wx.ALL | wx.EXPAND, 5)

            # Номер плавки
            melt_no_sizer = wx.BoxSizer(wx.HORIZONTAL)
            melt_no_label = wx.StaticText(main_data_box, label=loc.get("melt_no_label", "Номер плавки"))
            melt_no_label.SetFont(font)
            self.labels["melt_no"] = melt_no_label
            self.melt_no_input = wx.TextCtrl(main_data_box, value="", size=INPUT_FIELD_SIZE)
            self.melt_no_input.SetFont(font)
            melt_no_sizer.AddStretchSpacer()
            melt_no_sizer.Add(melt_no_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            melt_no_sizer.Add(self.melt_no_input, 0, wx.ALL, 5)
            main_data_sizer.Add(melt_no_sizer, 0, wx.ALL | wx.EXPAND, 5)

            self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.ALL, 10)

            # Группа "Размеры"
            dimensions_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, loc.get("dimensions_label", "Размеры"))
            dimensions_box = dimensions_sizer.GetStaticBox()
            dimensions_box.SetFont(font)
            self.static_boxes["dimensions"] = dimensions_box

            # Выпадающий список размеров (отсортирован по убыванию площади)
            size_options = [
                "SF - 4000x2000",  # 8000000
                "XF - 3000x2000",  # 6000000
                "GF - 3000x1500",  # 4500000
                "MF - 2500x1250",  # 3125000
                "NF - 2000x1000",  # 2000000
                loc.get("manual_input_label", "Ручной ввод")
            ]
            size_sizer = wx.BoxSizer(wx.HORIZONTAL)
            size_label = wx.StaticText(dimensions_box, label=loc.get("size_label", "Размер"))
            size_label.SetFont(font)
            self.labels["size"] = size_label
            self.size_combo = wx.ComboBox(dimensions_box, choices=size_options,
                                          value=loc.get("manual_input_label", "Ручной ввод"),
                                          style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
            self.size_combo.SetFont(font)
            size_sizer.AddStretchSpacer()
            size_sizer.Add(size_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            size_sizer.Add(self.size_combo, 0, wx.ALL, 5)
            dimensions_sizer.Add(size_sizer, 0, wx.ALL | wx.EXPAND, 5)

            # Заголовки для таблицы размеров
            header_sizer = wx.BoxSizer(wx.HORIZONTAL)
            header_sizer.AddStretchSpacer()
            length_label = wx.StaticText(dimensions_box, label=loc.get("length_label", "Длина L, мм"))
            length_label.SetFont(font)
            self.labels["length"] = length_label
            header_sizer.Add(length_label, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 20)
            height_label = wx.StaticText(dimensions_box, label=loc.get("height_label", "Высота H, мм"))
            height_label.SetFont(font)
            self.labels["height"] = height_label
            header_sizer.Add(height_label, 0, wx.ALIGN_CENTER | wx.LEFT | wx.RIGHT, 20)
            header_sizer.AddStretchSpacer()
            dimensions_sizer.Add(header_sizer, 0, wx.EXPAND | wx.ALL, 5)

            # Таблица для ручного ввода размеров (L, H)
            self.size_grid_sizer = wx.GridSizer(rows=5, cols=2, vgap=5, hgap=1)
            for i in range(5):
                l_input = wx.TextCtrl(dimensions_box, value="", size=(200, -1))
                h_input = wx.TextCtrl(dimensions_box, value="", size=(200, -1))
                l_input.SetFont(font)
                h_input.SetFont(font)
                l_input.Enable(False)
                h_input.Enable(False)
                self.size_inputs.append((l_input, h_input))
                self.size_grid_sizer.Add(l_input, 0, wx.ALL, 5)
                self.size_grid_sizer.Add(h_input, 0, wx.ALL, 5)
            dimensions_sizer.Add(self.size_grid_sizer, 0, wx.ALL | wx.EXPAND, 5)

            # Поле для отступа
            allowance_sizer = wx.BoxSizer(wx.HORIZONTAL)
            allowance_label = wx.StaticText(dimensions_box, label=loc.get("allowance_label", "Отступ от края, мм"))
            allowance_label.SetFont(font)
            self.labels["allowance"] = allowance_label
            self.allowance_input = wx.TextCtrl(dimensions_box, value="10", size=INPUT_FIELD_SIZE)
            self.allowance_input.SetFont(font)
            allowance_sizer.AddStretchSpacer()
            allowance_sizer.Add(allowance_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            allowance_sizer.Add(self.allowance_input, 0, wx.ALL, 5)
            dimensions_sizer.Add(allowance_sizer, 0, wx.ALL | wx.EXPAND, 5)

            self.right_sizer.Add(dimensions_sizer, 0, wx.EXPAND | wx.ALL, 10)

            main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(self.right_sizer, 0, wx.ALL | wx.EXPAND, 10)
            self.SetSizer(main_sizer)
            apply_styles_to_panel(self)
            self.Layout()
            logging.info("Интерфейс панели PlateContentPanel успешно настроен")

            # Привязка события для активации/деактивации таблицы
            self.size_combo.Bind(wx.EVT_COMBOBOX, self.on_size_combo_change)
            # Активация таблицы для "Ручной ввод" при инициализации
            self.on_size_combo_change(None)

        except Exception as e:
            logging.error(f"Ошибка настройки UI для PlateContentPanel: {e}")
            show_popup(loc.get("error", f"Ошибка настройки интерфейса: {str(e)}"), popup_type="error")
            raise

    def on_size_combo_change(self, event: wx.Event) -> None:
        """
        Обработчик изменения выбора в выпадающем списке размеров.
        """
        logging.debug("Обработка изменения выбора размера")
        try:
            size_selection = self.size_combo.GetValue()
            is_manual = size_selection == loc.get("manual_input_label", "Ручной ввод")
            for l_input, h_input in self.size_inputs:
                l_input.Enable(is_manual)
                h_input.Enable(is_manual)
            logging.info(f"Ручной ввод {'включён' if is_manual else 'выключен'}")
        except Exception as e:
            logging.error(f"Ошибка в on_size_combo_change: {e}")
            show_popup(loc.get("error", f"Ошибка при изменении размера: {str(e)}"), popup_type="error")

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        logging.debug("Обновление языка UI для PlateContentPanel")
        try:
            self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
            self.static_boxes["dimensions"].SetLabel(loc.get("dimensions_label", "Размеры"))
            self.labels["melt_no"].SetLabel(loc.get("melt_no_label", "Номер плавки"))
            self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
            self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
            self.labels["size"].SetLabel(loc.get("size_label", "Размер"))
            self.labels["allowance"].SetLabel(loc.get("allowance_label", "Отступ от края, мм"))
            self.labels["length"].SetLabel(loc.get("length_label", "Длина L, мм"))
            self.labels["height"].SetLabel(loc.get("height_label", "Высота H, мм"))

            # Обновление текста кнопок
            self.buttons[0].SetLabel(loc.get("ok_button", "ОК"))
            self.buttons[1].SetLabel(loc.get("clear_button", "Очистить"))
            self.buttons[2].SetLabel(loc.get("cancel_button", "Отмена"))
            adjust_button_widths(self.buttons)

            # Обновление выпадающего списка размеров
            size_options = [
                "SF - 4000x2000",
                "XF - 3000x2000",
                "GF - 3000x1500",
                "MF - 2500x1250",
                "NF - 2000x1000",
                loc.get("manual_input_label", "Ручной ввод")
            ]
            current_value = self.size_combo.GetValue()
            self.size_combo.SetItems(size_options)
            self.size_combo.SetValue(
                current_value if current_value in size_options else loc.get("manual_input_label", "Ручной ввод"))

            # Обновление толщины по умолчанию
            thickness_options = load_common_data().get("thicknesses", [])
            default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0]
            self.thickness_combo.SetItems(thickness_options)
            self.thickness_combo.SetValue(default_thickness)

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
            dict: Словарь с данными (insert_point, point_list, material, thickness_text, melt_no, allowance)
                  или None при ошибке.
        """
        try:
            point_list = []
            size_selection = self.size_combo.GetValue()

            # Обработка размеров
            if size_selection == "SF - 4000x2000":
                point_list = [[4000, 2000]]  # Только точка с максимальными координатами
            elif size_selection == "XF - 3000x2000":
                point_list = [[3000, 2000]]
            elif size_selection == "GF - 3000x1500":
                point_list = [[3000, 1500]]
            elif size_selection == "MF - 2500x1250":
                point_list = [[2500, 1250]]
            elif size_selection == "NF - 2000x1000":
                point_list = [[2000, 1000]]
            elif size_selection == loc.get("manual_input_label", "Ручной ввод"):
                for l_input, h_input in self.size_inputs:
                    l_str = l_input.GetValue().strip().replace(',', '.')
                    h_str = h_input.GetValue().strip().replace(',', '.')
                    if l_str and h_str:
                        try:
                            l = float(l_str)
                            h = float(h_str)
                            if l <= 0 or h <= 0:
                                show_popup(loc.get("size_positive_error", "Размеры должны быть положительными"),
                                           popup_type="error")
                                logging.error(f"Недопустимые размеры: L={l}, H={h}")
                                return None
                            point_list.append([l, h])
                        except ValueError:
                            show_popup(loc.get("invalid_number_format_error", "Неверный формат числа"),
                                       popup_type="error")
                            logging.error(f"Некорректный формат размеров: L={l_str}, H={h_str}")
                            return None
                if not point_list:
                    show_popup(loc.get("no_size_error", "Необходимо ввести хотя бы один размер"),
                               popup_type="error")
                    logging.error("Не введены размеры в ручном режиме")
                    return None

            # Проверка, что количество точек не превышает 5
            if len(point_list) > 5:
                show_popup(loc.get("max_points_error", "Максимальное количество точек - 5"),
                           popup_type="error")
                logging.error(f"Слишком много точек: {len(point_list)}")
                return None

            # Проверка отступа
            allowance_str = self.allowance_input.GetValue().strip().replace(',', '.')
            try:
                allowance = float(allowance_str)
                if allowance < 0:
                    show_popup(loc.get("offset_non_negative_error", "Отступ не может быть отрицательным"),
                               popup_type="error")
                    logging.error(f"Недопустимое значение отступа: {allowance}")
                    return None
            except ValueError:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для отступа"),
                           popup_type="error")
                logging.error(f"Некорректный формат отступа: {allowance_str}")
                return None

            # Проверка толщины
            thickness_str = self.thickness_combo.GetValue().strip().replace(',', '.')
            try:
                thickness = float(thickness_str)
            except ValueError:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для толщины"),
                           popup_type="error")
                logging.error(f"Некорректный формат толщины: {thickness_str}")
                return None

            return {
                "insert_point": self.insert_point,
                "point_list": point_list,
                "material": self.material_combo.GetValue(),
                "thickness_text": f"{thickness:.2f} {loc.get('mm', 'мм')}",
                "melt_no": self.melt_no_input.GetValue().strip(),
                "allowance": allowance
            }
        except Exception as e:
            logging.error(f"Ошибка получения данных из PlateContentPanel: {e}")
            show_popup(loc.get("error", f"Ошибка получения данных: {str(e)}"), popup_type="error")
            return None

    def create_polyline_points(self, data: Dict) -> List[tuple]:
        """
        Преобразует входные данные в список точек для полилинии.

        Args:
            data: Словарь с данными, содержащий 'insert_point' (APoint) и 'point_list' (список [x, y]).

        Returns:
            List[tuple]: Список кортежей с координатами точек полилинии.
        """
        logging.debug("Создание списка точек для полилинии")
        try:
            # Извлекаем начальную точку
            insert_point = data['insert_point']
            x0, y0 = insert_point.x, insert_point.y  # Используем .x и .y для APoint

            # Получаем список точек
            point_list = data['point_list']

            # Проверяем, что количество точек не превышает 5
            if len(point_list) > 5:
                raise ValueError("Максимальное количество точек - 5")

            # Создаем список точек полилинии
            polyline_points = [(x0, y0)]  # Начальная точка
            max_x = point_list[0][0]

            # Проходим по всем точкам из point_list
            for i, point in enumerate(point_list):
                x, y = point
                # Прибавляем относительные координаты к начальной точке
                abs_x = x0 + x
                abs_y = y0 + y

                # Добавляем промежуточные точки
                if i == 0:
                    # Для первой точки добавляем (x1, y0)
                    polyline_points.append((abs_x, y0))
                else:
                    # Для последующих точек добавляем (xi, y(i-1)) и (xi, yi)
                    prev_y = y0 + point_list[i - 1][1]
                    polyline_points.append((abs_x, prev_y))

                polyline_points.append((abs_x, abs_y))

            # Добавляем последнюю точку (x0, yn)
            if point_list:
                polyline_points.append((x0, y0 + point_list[-1][1]))

            # Замыкаем полилинию
            polyline_points.append((x0, y0))

            logging.debug(f"Созданы точки полилинии: {polyline_points}")
            return polyline_points

        except Exception as e:
            logging.error(f"Ошибка создания точек полилинии: {e}")
            show_popup(loc.get("error", f"Ошибка создания полилинии: {str(e)}"), popup_type="error")
            return []

    def on_ok(self, event: wx.Event) -> None:
        """
        Обработчик нажатия кнопки OK.
        """
        logging.debug("Обработка нажатия кнопки OK в PlateContentPanel")
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
            plate_data = self.get_input_data()
            if not plate_data or not plate_data["point_list"]:
                show_popup(loc.get("no_data_error", "Необходимо ввести хотя бы один размер"), popup_type="error")
                logging.error("Данные не введены или отсутствуют размеры")
                return

            # Создаём точки полилинии
            polyline_points = self.create_polyline_points(plate_data)
            if not polyline_points:
                logging.error("Не удалось создать точки полилинии")
                return

            # Обновляем plate_data, добавляя точки полилинии
            plate_data["polyline_points"] = polyline_points

            # Для отладки
            print("Входные данные:", plate_data)
            print("Точки полилинии:", polyline_points)

            # Вызываем run_plate с обновлёнными данными
            success = run_plate(plate_data)
            if success:
                logging.info("Лист успешно построен")
            else:
                show_popup(loc.get("plate_build_error", "Ошибка построения листа"), popup_type="error")
                logging.error("Ошибка построения листа")

            # Очищаем поля
            self.melt_no_input.SetValue("")
            self.material_combo.SetValue(self.material_combo.GetItems()[0])
            self.thickness_combo.SetValue(self.thickness_combo.GetItems()[0])
            self.size_combo.SetValue(loc.get("manual_input_label", "Ручной ввод"))
            for l_input, h_input in self.size_inputs:
                l_input.SetValue("")
                h_input.SetValue("")
                l_input.Enable(False)
                h_input.Enable(False)
            self.allowance_input.SetValue("10")
            if hasattr(self, "insert_point"):
                del self.insert_point
            self.update_status_bar_no_point()
            self.melt_no_input.SetFocus()

        except Exception as e:
            logging.error(f"Ошибка в on_ok: {e}")
            show_popup(loc.get("plate_build_error", f"Ошибка построения листа: {str(e)}"), popup_type="error")
            self.update_status_bar_no_point()

    def on_clear(self, event: wx.Event) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Очистить в PlateContentPanel")
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
        thickness_options = common_data.get("thicknesses", [])
        self.melt_no_input.SetValue("")
        self.material_combo.SetValue(material_options[0])
        self.thickness_combo.SetValue(thickness_options[0])
        self.size_combo.SetValue(self.size_combo.GetItems()[0])
        for l_input, h_input in self.size_inputs:
            l_input.SetValue("")
            h_input.SetValue("")
            l_input.Enable(False)
            h_input.Enable(False)
        self.allowance_input.SetValue("0")
        if hasattr(self, "insert_point"):
            del self.insert_point
        self.update_status_bar_no_point()
        self.melt_no_input.SetFocus()
        logging.info("Поля ввода очищены")

    def on_cancel(self, event: wx.Event) -> None:
        """
        Переключает контент на начальную страницу (content_apps) при нажатии кнопки "Отмена".

        Args:
            event: Событие нажатия кнопки.
        """
        logging.debug("Обработка нажатия кнопки Отмена в PlateContentPanel")
        try:
            main_window = wx.GetTopLevelParent(self)
            if hasattr(main_window, "switch_content"):
                main_window.switch_content("content_apps")
                logging.info("Переключение на content_apps по нажатию кнопки 'Отмена'")
            else:
                logging.error("Главное окно не имеет метода switch_content")
                show_popup(loc.get("error_switch_content", "Ошибка: невозможно переключить контент"),
                           popup_type="error")
        except Exception as e:
            logging.error(f"Ошибка при переключении на content_apps: {e}")
            show_popup(loc.get("error", f"Ошибка переключения контента: {str(e)}"), popup_type="error")
