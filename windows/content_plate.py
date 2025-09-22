"""
windows/content_plate.py
Модуль для создания панели для ввода параметров листа.
"""

import wx
from typing import Optional, Dict
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_translations import loc
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data
)
from programms.at_input import at_point_input

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "main_data_label": {
        "ru": "Основные данные",
        "de": "Hauptdaten",
        "en": "Main Data"
    },
    "dimensions_label": {
        "ru": "Размеры",
        "de": "Abmessungen",
        "en": "Dimensions"
    },
    "material_label": {
        "ru": "Материал",
        "de": "Material",
        "en": "Material"
    },
    "thickness_label": {
        "ru": "Толщина",
        "de": "Dicke",
        "en": "Thickness"
    },
    "melt_no_label": {
        "ru": "Номер плавки",
        "de": "Schmelznummer",
        "en": "Melt Number"
    },
    "size_label": {
        "ru": "Размер",
        "de": "Größe",
        "en": "Size"
    },
    "length_label": {
        "ru": "Длина L, мм",
        "de": "Länge L, mm",
        "en": "Length L, mm"
    },
    "height_label": {
        "ru": "Высота H, мм",
        "de": "Höhe H, mm",
        "en": "Height H, mm"
    },
    "allowance_label": {
        "ru": "Отступ от края, мм",
        "de": "Randabstand, mm",
        "en": "Edge Allowance, mm"
    },
    "manual_input_label": {
        "ru": "Ручной ввод",
        "de": "Manuelle Eingabe",
        "en": "Manual Input"
    },
    "ok_button": {
        "ru": "ОК",
        "de": "OK",
        "en": "OK"
    },
    "clear_button": {
        "ru": "Очистить",
        "de": "Zurücksetzen",
        "en": "Clear"
    },
    "cancel_button": {
        "ru": "Возврат",
        "de": "Zurück",
        "en": "Return"
    },
    "no_data_error": {
        "ru": "Необходимо ввести хотя бы один размер",
        "de": "Mindestens eine Größe muss eingegeben werden",
        "en": "At least one size must be entered"
    },
    "max_points_error": {
        "ru": "Максимальное количество точек - 5",
        "de": "Maximale Anzahl von Punkten - 5",
        "en": "Maximum number of points - 5"
    },
    "size_positive_error": {
        "ru": "Размеры должны быть положительными",
        "de": "Größen müssen positiv sein",
        "en": "Sizes must be positive"
    },
    "invalid_number_format_error": {
        "ru": "Неверный формат числа",
        "de": "Ungültiges Zahlenformat",
        "en": "Invalid number format"
    },
    "offset_non_negative_error": {
        "ru": "Отступ не может быть отрицательным",
        "de": "Randabstand darf nicht negativ sein",
        "en": "Allowance cannot be negative"
    },
    "point_selection_error": {
        "ru": "Ошибка выбора точки",
        "de": "Fehler bei der Punktauswahl",
        "en": "Point selection error"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель контента для ввода параметров листа.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель с интерфейсом для ввода параметров листа или None при ошибке.
    """
    try:
        panel = PlateContentPanel(parent)
        return panel
    except Exception as e:
        show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
        return None


class PlateContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров листа.
    """

    def __init__(self, parent, callback=None):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
            callback: Функция обратного вызова для передачи данных.
        """
        super().__init__(parent)
        self.settings = load_user_settings()
        self.SetBackgroundColour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"]))
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.size_inputs = []
        self.insert_point = None
        self.setup_ui()
        self.melt_no_input.SetFocus()

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
        image_path = str(PLATE_IMAGE_PATH)
        if not str(image_path):
            show_popup(
                loc.get("error", "Ошибка") + f": Путь к изображению не указан",
                popup_type="error"
            )

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

    def on_size_combo_change(self, event: wx.Event) -> None:
        """
        Обрабатывает изменение выбора в выпадающем списке размеров.
        """
        size_selection = self.size_combo.GetValue()
        is_manual = size_selection == loc.get("manual_input_label", "Ручной ввод")
        for l_input, h_input in self.size_inputs:
            l_input.Enable(is_manual)
            h_input.Enable(is_manual)

    def clear_input_fields(self) -> None:
        """
        Очищает все поля ввода панели.
        """
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat["name"]]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[
            0] if thickness_options else ""
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
        self.insert_point = None
        self.melt_no_input.SetFocus()

    def update_ui_language(self):
        """
        Обновляет текст меток и групп при смене языка.
        """
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["dimensions"].SetLabel(loc.get("dimensions_label", "Размеры"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина"))
        self.labels["melt_no"].SetLabel(loc.get("melt_no_label", "Номер плавки"))
        self.labels["size"].SetLabel(loc.get("size_label", "Размер"))
        self.labels["length"].SetLabel(loc.get("length_label", "Длина L, мм"))
        self.labels["height"].SetLabel(loc.get("height_label", "Высота H, мм"))
        self.labels["allowance"].SetLabel(loc.get("allowance_label", "Отступ от края, мм"))

        # Обновляем метки кнопок: ОК, Отмена, Очистить
        for i, key in enumerate(["ok_button", "clear_button", "cancel_button"]):
            self.buttons[i].SetLabel(loc.get(key, ["ОК", "Возврат", "Очистить"][i]))
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
        self.size_combo.SetValue(
            current_value if current_value in size_options else loc.get("manual_input_label", "Ручной ввод"))

        thickness_options = load_common_data().get("thicknesses", [])
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[
            0] if thickness_options else ""
        self.thickness_combo.SetItems(thickness_options)
        self.thickness_combo.SetValue(default_thickness)

        update_status_bar_point_selected(self, None)
        self.Layout()

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
                            show_popup(
                                loc.get("invalid_number_format_error", "Неверный формат числа"),
                                popup_type="error"
                            )
                            return None

            allowance_str = self.allowance_input.GetValue().strip().replace(',', '.')
            thickness_str = self.thickness_combo.GetValue().strip().replace(',', '.')

            try:
                allowance = float(allowance_str) if allowance_str else None
                thickness = float(thickness_str) if thickness_str else None
            except ValueError:
                show_popup(
                    loc.get("invalid_number_format_error", "Неверный формат числа"),
                    popup_type="error"
                )
                return None

            # Преобразуем insert_point в список [x, z, y], если он существует
            insert_point = self.insert_point if self.insert_point else None

            return {
                "insert_point": insert_point,
                "point_list": point_list,
                "material": self.material_combo.GetValue(),
                "thickness": thickness,
                "melt_no": self.melt_no_input.GetValue().strip(),
                "allowance": allowance
            }
        except Exception as e:
            show_popup(
                loc.get("error", "Ошибка") + f": {str(e)}",
                popup_type="error"
            )
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
                return False

            if len(data["point_list"]) > 5:
                show_popup(loc.get("max_points_error", "Максимальное количество точек - 5"), popup_type="error")
                return False

            for l, h in data["point_list"]:
                if l <= 0 or h <= 0:
                    show_popup(loc.get("size_positive_error", "Размеры должны быть положительными"), popup_type="error")
                    return False

            if data["allowance"] is None:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для отступа"),
                           popup_type="error")
                return False
            if data["allowance"] < 0:
                show_popup(loc.get("offset_non_negative_error", "Отступ не может быть отрицательным"),
                           popup_type="error")
                return False

            if data["thickness"] is None:
                show_popup(loc.get("invalid_number_format_error", "Неверный формат числа для толщины"),
                           popup_type="error")
                return False

            if not data["insert_point"]:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                return False

            return True
        except Exception as e:
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")
            return False

    def on_ok(self, event: wx.Event) -> None:
        """
        Обрабатывает нажатие кнопки "ОК", запрашивает точку и вызывает callback.
        """
        try:
            main_window = wx.GetTopLevelParent(self)
            main_window.Iconize(True)
            cad = ATCadInit()
            point = at_point_input(cad.adoc, as_variant=False, prompt="Введите левый нижний угол листа")
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            if not isinstance(point, list) or len(point) != 3:
                show_popup(loc.get("point_selection_error", "Ошибка выбора точки"), popup_type="error")
                return

            self.insert_point = point  # Сохраняем точку как список [x, z, y]
            update_status_bar_point_selected(self, point)

            data = self.collect_input_data()
            if data and self.validate_input(data):
                if self.on_submit_callback:
                    self.on_submit_callback(data)
        except Exception as e:
            show_popup(loc.get("error", "Ошибка") + f": {str(e)}", popup_type="error")



if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и вывода данных, введённых пользователем.
    """
    from programms.at_run_plate import main

    app = wx.App(False)
    frame = wx.Frame(None, title="Тест PlateContentPanel", size=(800, 600))
    panel = PlateContentPanel(frame)

    # Функция для вывода данных при нажатии "ОК"
    def on_ok_test(event):
        try:
            # Тестовая точка для имитации ввода
            cad = ATCadInit()
            point = at_point_input(cad.adoc, as_variant=False, prompt="Введите левый нижний угол листа")
            panel.insert_point = point  # Сохраняем точку как список [x, z, y]
            update_status_bar_point_selected(panel, point)

            # Собираем данные, введённые пользователем
            data = panel.collect_input_data()
            if data:
                print("Собранные данные:", data)
                main(data)
            else:
                print("Ошибка: данные не собраны")
        except Exception as e:
            print(f"Ошибка в тестовом запуске: {e}")

    # Привязываем тестовую функцию к кнопке "ОК"
    panel.buttons[0].Bind(wx.EVT_BUTTON, on_ok_test)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()


