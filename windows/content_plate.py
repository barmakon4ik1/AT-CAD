"""
window/content_plate.py
Модуль для создания панели для ввода параметров листа.
"""

import wx
from typing import Optional, Dict, List
from pyautocad import APoint

from config.at_config import *
from locales.at_localization_class import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data
)
from programms.at_run_plate import run_plate

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
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
    try:
        panel = PlateContentPanel(parent)
        logging.info("Панель PlateContentPanel создана")
        return panel
    except Exception as e:
        logging.error(f"Ошибка создания PlateContentPanel: {e}")
        show_popup(loc.get("error", f"Ошибка создания панели листа: {str(e)}"), popup_type="error")
        return None


class PlateContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров листа.
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
        self.size_inputs = []
        self.insert_point = None
        self.update_status_bar_no_point()
        self.setup_ui()
        self.melt_no_input.SetFocus()

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
        self.size_inputs.clear()

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Проверка изображения
        image_path = os.path.abspath(PLATE_IMAGE_PATH)
        if not os.path.exists(image_path):
            logging.warning(f"Файл изображения листа '{image_path}' не найден")

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
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0] if thickness_options else ""

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
        self.material_combo = wx.ComboBox(main_data_box, choices=material_options, value=material_options[0] if material_options else "", style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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
        self.thickness_combo = wx.ComboBox(main_data_box, choices=thickness_options, value=default_thickness, style=wx.CB_DROPDOWN, size=INPUT_FIELD_SIZE)
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

        # Выпадающий список размеров
        size_options = [
            "SF - 4000x2000",
            "XF - 3000x2000",
            "GF - 3000x1500",
            "MF - 2500x1250",
            "NF - 2000x1000",
            loc.get("manual_input_label", "Ручной ввод")
        ]
        size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        size_label = wx.StaticText(dimensions_box, label=loc.get("size_label", "Размер"))
        size_label.SetFont(font)
        self.labels["size"] = size_label
        self.size_combo = wx.ComboBox(dimensions_box, choices=size_options, value=loc.get("manual_input_label", "Ручной ввод"), style=wx.CB_READONLY, size=INPUT_FIELD_SIZE)
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

        # Таблица для ручного ввода размеров
        self.size_grid_sizer = wx.GridSizer(rows=5, cols=2, vgap=5, hgap=1)
        for _ in range(5):
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
        self.size_combo.Bind(wx.EVT_COMBOBOX, self.on_size_combo_change)
        self.on_size_combo_change(None)
        logging.info("Интерфейс PlateContentPanel настроен")

    def on_size_combo_change(self, event: wx.Event) -> None:
        """
        Обрабатывает изменение выбора в выпадающем списке размеров.
        """
        size_selection = self.size_combo.GetValue()
        is_manual = size_selection == loc.get("manual_input_label", "Ручной ввод")
        for l_input, h_input in self.size_inputs:
            l_input.Enable(is_manual)
            h_input.Enable(is_manual)
        logging.debug(f"Ручной ввод {'включён' if is_manual else 'выключен'}")

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["dimensions"].SetLabel(loc.get("dimensions_label", "Размеры"))
        self.labels["melt_no"].SetLabel(loc.get("melt_no_label", "Номер плавки"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
        self.labels["size"].SetLabel(loc.get("size_label", "Размер"))
        self.labels["allowance"].SetLabel(loc.get("allowance_label", "Отступ от края, мм"))
        self.labels["length"].SetLabel(loc.get("length_label", "Длина L, мм"))
        self.labels["height"].SetLabel(loc.get("height_label", "Высота H, мм"))

        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Очистить", "Отмена"][i]))
        adjust_button_widths(self.buttons)

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
        self.size_combo.SetValue(current_value if current_value in size_options else loc.get("manual_input_label", "Ручной ввод"))

        thickness_options = load_common_data().get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0] if thickness_options else ""
        self.thickness_combo.SetItems(thickness_options)
        self.thickness_combo.SetValue(default_thickness)

        self.update_status_bar_no_point()
        self.Layout()
        logging.info("Язык UI обновлён")

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода.

        Returns:
            dict: Словарь с данными (insert_point, point_list, material, thickness, melt_no, allowance)
                  или None при ошибке.
        """
        try:
            point_list = []
            size_selection = self.size_combo.GetValue()

            if size_selection == "SF - 4000x2000":
                point_list = [[4000, 2000]]
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
                            point_list.append([l, h])
                        except ValueError:
                            return None

            allowance_str = self.allowance_input.GetValue().strip().replace(',', '.')
            thickness_str = self.thickness_combo.GetValue().strip().replace(',', '.')

            try:
                allowance = float(allowance_str) if allowance_str else None
                thickness = float(thickness_str) if thickness_str else None
            except ValueError:
                return None

            return {
                "insert_point": self.insert_point,
                "point_list": point_list,
                "material": self.material_combo.GetValue(),
                "thickness": thickness,
                "melt_no": self.melt_no_input.GetValue().strip(),
                "allowance": allowance
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
            if not data or not data["point_list"]:
                show_popup(loc.get("no_data_error", "Необходимо ввести хотя бы один размер"), popup_type="error")
                logging.error("Отсутствуют размеры")
                return False

            if len(data["point_list"]) > 5:
                show_popup(loc.get("max_points_error", "Максимальное количество точек - 5"), popup_type="error")
                logging.error(f"Слишком много точек: {len(data['point_list'])}")
                return False

            for l, h in data["point_list"]:
                if l <= 0 or h <= 0:
                    show_popup(loc.get("size_positive_error", "Размеры должны быть положительными"), popup_type="error")
                    logging.error(f"Недопустимые размеры: L={l}, H={h}")
                    return False

            if data["allowance"] is None:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для отступа"), popup_type="error")
                logging.error(f"Некорректный формат отступа: {data['allowance']}")
                return False
            if data["allowance"] < 0:
                show_popup(loc.get("offset_non_negative_error", "Отступ не может быть отрицательным"), popup_type="error")
                logging.error(f"Недопустимое значение отступа: {data['allowance']}")
                return False

            if data["thickness"] is None:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для толщины"), popup_type="error")
                logging.error(f"Некорректный формат толщины: {data['thickness']}")
                return False

            return True
        except Exception as e:
            logging.error(f"Ошибка валидации данных: {e}")
            show_popup(loc.get("error", f"Неверный формат данных: {str(e)}"), popup_type="error")
            return False

    def create_polyline_points(self, data: Dict) -> List[tuple]:
        """
        Преобразует входные данные в список точек для полилинии.

        Args:
            data: Словарь с данными, содержащий 'insert_point' (APoint) и 'point_list' (список [x, y]).

        Returns:
            List[tuple]: Список кортежей с координатами точек полилинии.
        """
        try:
            insert_point = data['insert_point']
            x0, y0 = insert_point.x, insert_point.y if insert_point else (0, 0)
            point_list = data['point_list']

            if len(point_list) > 5:
                logging.error("Максимальное количество точек - 5")
                return []

            polyline_points = [(0, 0)]
            if point_list:
                x = point_list[0][0]
                y = point_list[0][1]
                polyline_points.append((x, 0))
                polyline_points.append((x, y))
                x1 = x
                prev_y = y
                for dx, dy in point_list[1:]:
                    x, y = x1 - dx, dy
                    polyline_points.extend([(x, prev_y), (x, y)])
                    prev_y = y
                polyline_points.append((0, y))
            polyline_points.append((0, 0))
            polyline_points = [(x + x0, y + y0) for x, y in polyline_points]
            logging.debug(f"Созданы точки полилинии: {polyline_points}")
            return polyline_points
        except Exception as e:
            logging.error(f"Ошибка создания точек полилинии: {e}")
            return []

    def process_input(self, data: Dict) -> bool:
        """
        Обрабатывает данные для построения листа.

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

            polyline_points = self.create_polyline_points(data)
            if not polyline_points:
                logging.error("Не удалось создать точки полилинии")
                return False

            data["polyline_points"] = polyline_points
            success = run_plate(data)
            if success:
                logging.info("Лист успешно построен")
                self.clear_input_fields()
            else:
                show_popup(loc.get("plate_build_error", "Ошибка построения листа"), popup_type="error")
                logging.error("Ошибка построения листа")
            return success
        except Exception as e:
            logging.error(f"Ошибка в process_input: {e}")
            show_popup(loc.get("plate_build_error", f"Ошибка построения листа: {str(e)}"), popup_type="error")
            return False

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода и сбрасывает точку вставки.
        """
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0] if thickness_options else ""
        self.melt_no_input.SetValue("")
        self.material_combo.SetValue(material_options[0] if material_options else "")
        self.thickness_combo.SetValue(default_thickness)
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
        logging.info("Поля ввода очищены")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и построения листа.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Тест PlateContentPanel", size=(800, 600))
    panel = PlateContentPanel(frame)

    # Установка тестовых данных
    panel.melt_no_input.SetValue("TestMelt")
    panel.material_combo.SetValue("1ю4301")
    panel.thickness_combo.SetValue("4")
    panel.size_combo.SetValue("SF - 4000x2000")
    panel.allowance_input.SetValue("10")

    # Тест выбора точки и построения
    try:
        from config.at_cad_init import ATCadInit
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
                "insert_point": test_point,
                "point_list": [[4000, 2000]],
                "material": "Steel",
                "thickness": 4.0,
                "melt_no": "TestMelt",
                "allowance": 10.0,
                "polyline_points": [(0, 0), (4000, 0), (4000, 2000), (0, 2000), (0, 0)]
            }
            success = run_plate(data)
            if success:
                print("Лист построен успешно")
                adoc.Regen(0)
            else:
                print("Ошибка построения листа")

    except Exception as e:
        print(f"Ошибка в тестовом запуске: {e}")
        logging.error(f"Ошибка в тестовом запуске: {e}")

    frame.Show()
    app.MainLoop()
