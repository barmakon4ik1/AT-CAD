"""
windows/content_plate.py
Модуль для создания панели для ввода параметров листа.
"""

from typing import Optional, Dict, cast
from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_translations import loc
from windows.at_fields_builder import FormBuilder, FieldBuilder
from windows.at_window_utils import (
    CanvasPanel, show_popup, apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, get_wx_color_from_value
)
from programs.at_input import at_get_point

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "dimensions_label": {"ru": "Размеры", "de": "Abmessungen", "en": "Dimensions"},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},
    "melt_no_label": {"ru": "Номер плавки", "de": "Schmelznummer", "en": "Melt Number"},
    "size_label": {"ru": "Размер", "de": "Größe", "en": "Size"},
    "length_label": {"ru": "Длина L, мм", "de": "Länge L, mm", "en": "Length L, mm"},
    "height_label": {"ru": "Высота H, мм", "de": "Höhe H, mm", "en": "Height H, mm"},
    "allowance_label": {"ru": "Отступ от края, мм", "de": "Randabstand, mm", "en": "Edge Allowance, mm"},
    "manual_input_label": {"ru": "Ручной ввод", "de": "Manuelle Eingabe", "en": "Manual Input"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "no_data_error": {"ru": "Необходимо ввести хотя бы один размер", "de": "Mindestens eine Größe muss eingegeben werden", "en": "At least one size must be entered"},
    "max_points_error": {"ru": "Максимальное количество точек - 5", "de": "Maximale Anzahl von Punkten - 5", "en": "Maximum number of points - 5"},
    "size_positive_error": {"ru": "Размеры должны быть положительными", "de": "Größen müssen positiv sein", "en": "Sizes must be positive"},
    "invalid_number_format_error": {"ru": "Неверный формат числа", "de": "Ungültiges Zahlenformat", "en": "Invalid number format"},
    "offset_non_negative_error": {"ru": "Отступ не может быть отрицательным", "de": "Randabstand darf nicht negativ sein", "en": "Allowance cannot be negative"},
    "point_selection_error": {"ru": "Ошибка выбора точки", "de": "Fehler bei der Punktauswahl", "en": "Point selection error"}
}
loc.register_translations(TRANSLATIONS)


def create_window(parent: wx.Window) -> Optional[wx.Panel]:
    """
    Создаёт панель контента для ввода параметров листа.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel или None: Панель с интерфейсом для ввода параметров листа или None при ошибке.
    """
    try:
        return PlateContentPanel(parent)
    except Exception as e:
        show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
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
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.size_inputs = []
        self.insert_point = None
        self.setup_ui()

        self.SetBackgroundColour(
            get_wx_color_from_value(
                self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
            )
        )

        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None
        self.canvas: Optional[CanvasPanel] = None
        self.form: Optional[FormBuilder] = None
        self.fb: Optional[FieldBuilder] = None
        self.material_ctrl: Optional[wx.Choice] = None
        self.thickness_ctrl: Optional[wx.ComboBox] = None
        self.melt_no_ctrl: Optional[wx.TextCtrl] = None
        self.size_combo: Optional[wx.ComboBox] = None
        self.size_grid_sizer: Optional[wx.GridSizer] = None
        self.allowance_input: Optional[wx.TextCtrl] = None

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса панели ввода параметров листа.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)

        self.size_inputs.clear()

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # ------------------------------------------------------------
        # Левая часть — изображение
        # ------------------------------------------------------------
        image_path = str(PLATE_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------
        # Данные
        # ------------------------------------------------------------
        common_data = load_common_data()
        material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
        thickness_options = common_data.get("thicknesses", [])

        # ------------------------------------------------------------
        # Форма и фабрики полей
        # ------------------------------------------------------------
        self.form = FormBuilder(self)

        self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

        # ------------------------------------------------------------
        # Основные данные
        # ------------------------------------------------------------
        main_data_sizer = self.fb.static_box("main_data")
        self.static_boxes["main_data"] = main_data_sizer.GetStaticBox()

        main_fb = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        self.material_ctrl = main_fb.choice(
            name="material",
            label_key="material_label",
            choices=material_options,
            required=True
        )

        self.thickness_ctrl = main_fb.combo(
            name="thickness",
            label_key="thickness_label",
            choices=thickness_options,
            required=True
        )

        self.melt_no_ctrl = main_fb.text(
            name="melt_no",
            label_key="melt_no_label"
        )

        # ------------------------------------------------------------
        # Размеры
        # ------------------------------------------------------------
        dimensions_box = wx.StaticBox(self, label=loc.get("dimensions_label"))
        dimensions_sizer = wx.StaticBoxSizer(dimensions_box, wx.VERTICAL)

        # Размер (combo)
        row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_size = wx.StaticText(dimensions_box, label=loc.get("size_label"))
        self.size_combo = wx.ComboBox(
            dimensions_box,
            choices=[
                "SF - 4000x2000",
                "XF - 3000x2000",
                "GF - 3000x1500",
                "MF - 2500x1250",
                "NF - 2000x1000",
                loc.get("manual_input_label")
            ],
            value=loc.get("manual_input_label"),
            style=wx.CB_READONLY,
            size=wx.Size(*INPUT_FIELD_SIZE)
        )
        row.Add(lbl_size, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row.AddStretchSpacer()
        row.Add(self.size_combo, 0)
        dimensions_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 5)

        # Заголовки таблицы
        header = wx.BoxSizer(wx.HORIZONTAL)
        lbl_l = wx.StaticText(dimensions_box, label=loc.get("length_label"))
        lbl_h = wx.StaticText(dimensions_box, label=loc.get("height_label"))
        header.Add(lbl_l, 1, wx.ALIGN_CENTER)
        header.Add(lbl_h, 1, wx.ALIGN_CENTER)
        dimensions_sizer.Add(header, 0, wx.EXPAND | wx.ALL, 5)

        # Таблица
        self.size_grid_sizer = wx.GridSizer(5, 2, 5, 5)
        for _ in range(5):
            l = wx.TextCtrl(dimensions_box, size=wx.Size(200, -1))
            h = wx.TextCtrl(dimensions_box, size=wx.Size(200, -1))
            l.Enable(False)
            h.Enable(False)
            self.size_inputs.append((l, h))
            self.size_grid_sizer.Add(l)
            self.size_grid_sizer.Add(h)
        dimensions_sizer.Add(self.size_grid_sizer, 0, wx.ALL, 5)

        # Allowance
        allowance_row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_allowance = wx.StaticText(dimensions_box, label=loc.get("allowance_label"))
        self.allowance_input = wx.TextCtrl(dimensions_box, value="10", size=wx.Size(*INPUT_FIELD_SIZE))
        allowance_row.Add(lbl_allowance, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        allowance_row.AddStretchSpacer()
        allowance_row.Add(self.allowance_input, 0)
        dimensions_sizer.Add(allowance_row, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(dimensions_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------
        # Кнопки
        # ------------------------------------------------------------
        self.right_sizer.AddStretchSpacer()
        self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # ------------------------------------------------------------
        # Финал
        # ------------------------------------------------------------
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

        self.size_combo.Bind(wx.EVT_COMBOBOX, self.on_size_combo_change)
        self.on_size_combo_change()

    def on_size_combo_change(self) -> None:
        """
        Обрабатывает изменение выбора в выпадающем списке размеров.
        """
        size_selection = self.size_combo.GetValue()
        is_manual = size_selection == loc.get("manual_input_label")
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
        default_thickness = "4" if "4" in thickness_options or "4.0" in thickness_options else thickness_options[0] if thickness_options else ""

        self.melt_no_ctrl.SetValue("")
        if material_options:
            self.material_ctrl.SetStringSelection(material_options[0])
        if default_thickness:
            self.thickness_ctrl.SetValue(str(default_thickness))
        self.size_combo.SetValue(loc.get("manual_input_label"))
        for l_input, h_input in self.size_inputs:
            l_input.SetValue("")
            h_input.SetValue("")
            l_input.Enable(False)
            h_input.Enable(False)
        self.allowance_input.SetValue("10")
        self.insert_point = None
        self.melt_no_ctrl.SetFocus()

    def collect_input_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода панели PlateContentPanel.
        """
        try:
            point_list = []

            # Выбор размера
            size_selection = self.size_combo.GetValue()
            preset_sizes = {
                "SF - 4000x2000": [4000, 2000],
                "XF - 3000x2000": [3000, 2000],
                "GF - 3000x1500": [3000, 1500],
                "MF - 2500x1250": [2500, 1250],
                "NF - 2000x1000": [2000, 1000]
            }

            if size_selection in preset_sizes:
                point_list.append(preset_sizes[size_selection])
            else:
                # Ручной ввод
                for l_input, h_input in self.size_inputs:
                    l_val = l_input.GetValue().strip().replace(",", ".")
                    h_val = h_input.GetValue().strip().replace(",", ".")
                    if l_val and h_val:
                        try:
                            point_list.append([float(l_val), float(h_val)])
                        except ValueError:
                            show_popup(loc.get("invalid_number_format_error"), popup_type="error")
                            return None

            # Отступ
            allowance_text = self.allowance_input.GetValue().strip().replace(",", ".")
            try:
                allowance = float(allowance_text) if allowance_text else 0.0
            except ValueError:
                show_popup(loc.get("invalid_number_format_error"), popup_type="error")
                return None

            # Материал
            material = self.material_ctrl.GetStringSelection() if self.material_ctrl else ""

            # Толщина
            try:
                thickness = float(self.thickness_ctrl.GetValue()) if self.thickness_ctrl else 0.0
            except ValueError:
                show_popup(loc.get("invalid_number_format_error"), popup_type="error")
                return None

            # Номер плавки
            melt_no = self.melt_no_ctrl.GetValue().strip() if self.melt_no_ctrl else ""

            return {
                "insert_point": self.insert_point,
                "point_list": point_list,
                "material": material,
                "thickness": thickness,
                "melt_no": melt_no,
                "allowance": allowance
            }

        except Exception as e:
            show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
            return None

    def validate_input(self, data: Dict) -> bool:
        """
        Проверяет валидность введённых данных.
        """
        try:
            if not data or not data.get("point_list"):
                show_popup(loc.get("no_data_error"), popup_type="error")
                return False

            if len(data["point_list"]) > 5:
                show_popup(loc.get("max_points_error"), popup_type="error")
                return False

            for l, h in data["point_list"]:
                if l <= 0 or h <= 0:
                    show_popup(loc.get("size_positive_error"), popup_type="error")
                    return False

            allowance = data.get("allowance")
            if allowance is None or allowance < 0:
                show_popup(loc.get("offset_non_negative_error"), popup_type="error")
                return False

            thickness = data.get("thickness")
            if thickness is None or thickness <= 0:
                show_popup(loc.get("invalid_number_format_error"), popup_type="error")
                return False

            if not data.get("insert_point"):
                show_popup(loc.get("point_selection_error"), popup_type="error")
                return False

            return True
        except Exception as e:
            show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
            return False

    def on_ok(self, *args, **kwargs) -> None:
        """
        Обрабатывает нажатие кнопки "ОК", запрашивает точку и вызывает callback.
        """
        event = kwargs.get('event', None)  # если нужно использовать event
        try:
            main_window = wx.GetTopLevelParent(self)
            cast(wx.Frame, main_window).Iconize(True)
            cad = ATCadInit()
            point = at_get_point(cad.document, as_variant=False, prompt="Введите левый нижний угол листа")
            cast(wx.Frame, main_window).Iconize(False)
            main_window.Raise()
            main_window.SetFocus()
            wx.Yield()

            if not isinstance(point, list) or len(point) != 3:
                show_popup(loc.get("point_selection_error"), popup_type="error")
                return

            self.insert_point = point
            update_status_bar_point_selected(self, point)

            data = self.collect_input_data()
            if data and self.validate_input(data):
                if self.on_submit_callback:
                    self.on_submit_callback(data)
        except Exception as e:
            _ = event  # чтобы event считался использованным
            show_popup(loc.get("error") + f": {str(e)}", popup_type="error")


if __name__ == "__main__":
    """
    Тестовый вызов окна для проверки интерфейса и вывода данных, введённых пользователем.
    """
    from programs.at_run_plate import main

    app = wx.App(False)
    frame = wx.Frame(None, title="Тест PlateContentPanel", size=wx.Size(1500, 700))
    panel = PlateContentPanel(frame)

    # Функция для вывода данных при нажатии "ОК"
    def on_ok_test():
        try:
            # Тестовая точка для имитации ввода
            cad = ATCadInit()
            point = at_get_point(cad.document, as_variant=False, prompt="Введите левый нижний угол листа")
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

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()