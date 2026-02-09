"""
windows/content_bracket.py

Панель ввода параметров мостиков для табличек (AT-CAD).

Назначение:
    Формирование входных данных для построения мостиков табличек
    различных типов (Type 1 … Type 5) с последующей передачей
    в расчётно-геометрический модуль.

Область ответственности:
    - ввод технологических данных (заказ, деталь, материал)
    - ввод базовой геометрии мостика
    - выбор типа мостика
    - выбор и привязка табличек
    - формирование итогового словаря bridge_data

НЕ выполняет:
    - геометрические расчёты
    - построение в AutoCAD
    - проверку технологических ограничений

Архитектурные принципы:
    - наличие параметра = параметр задан
    - отсутствие параметра = параметр не используется
    - никакие "нулевые значения" по умолчанию не применяются

Связанные модули:
    programs.at_name_plate        — построение табличек
    windows.nameplate_dialog      — выбор табличек
    windows.bracket_specific_*    — дочерние окна специфических параметров

TODO:
    - реализация дочерних окон специфики по типам
    - валидация входных данных
    - привязка выбора точки вставки (AutoCAD)
"""

from typing import Optional, Dict, cast
from config.at_cad_init import ATCadInit
from config.at_config import *
from locales.at_translations import loc
from windows.at_fields_builder import FormBuilder, FieldBuilder
from windows.at_window_utils import (
    CanvasPanel, show_popup, apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, get_wx_color_from_value, get_standard_font,
    get_textctrl_font
)
from programs.at_input import at_get_point

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "dimensions_label": {"ru": "Размеры", "de": "Abmessungen", "en": "Dimensions"},
    "select_bridge_type": {"ru": "Выберите тип мостика", "de": "Wählen Sie den Brückentyp aus", "en": "Select the type of bracket"},
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


BRIDGE_TYPE_IMAGES = {
    "1": BRACKET1_IMAGE_PATH,
    "2": BRACKET2_IMAGE_PATH,
    "3": BRACKET3_IMAGE_PATH,
    "4": BRACKET4_IMAGE_PATH,
    "5": BRACKET5_IMAGE_PATH,
}


def create_window(parent: wx.Window) -> Optional[wx.Panel]:
    """
    Создаёт панель контента для ввода параметров мостиков табличек.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel или None: Панель с интерфейсом для ввода параметров мостиков или None при ошибке.
    """
    try:
        return BracketContentPanel(parent)
    except Exception as e:
        show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
        return None


class BracketContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров мостиков табличек
    """

    def __init__(self, parent: wx.Window, callback=None):
        """
        Инициализирует панель, создаёт элементы управления.

        Args:
            parent: Родительский wx.Window (content_panel).
            callback: Функция обратного вызова для передачи данных.
        """
        super().__init__(parent)
        self.bridge_type_choice = None
        self.settings = load_user_settings()
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.size_inputs = []
        self.insert_point = None
        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None
        self.canvas: Optional[CanvasPanel] = None
        self.form: Optional[FormBuilder] = None
        self.fb: Optional[FieldBuilder] = None
        self.material_ctrl: Optional[wx.Choice] = None
        self.thickness_ctrl: Optional[wx.ComboBox] = None
        self.size_combo: Optional[wx.ComboBox] = None
        self.size_grid_sizer: Optional[wx.GridSizer] = None
        self.setup_ui()

        self.SetBackgroundColour(
            get_wx_color_from_value(
                self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
            )
        )

    def on_bridge_type_changed(self, event: Optional[wx.Event] = None):
        bridge_type = self.bridge_type_choice.GetStringSelection()
        if not bridge_type:
            return

        image_path = BRIDGE_TYPE_IMAGES.get(bridge_type)
        if not image_path:
            return

        # Ключевое: используем метод CanvasPanel
        self.canvas.set_image(image_path)

    def setup_ui(self) -> None:
        """
        Настраивает элементы интерфейса панели ввода параметров мостика таблички.
        Все выборы реализованы через ComboBox (только выбор, ручной ввод запрещен).
        """
        # Очистка старого слайзера
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.size_inputs.clear()

        # Основной горизонтальный слайзер: слева — картинка, справа — данные
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # -----------------------------
        # Тип мостика (ComboBox)
        # -----------------------------
        type_row = wx.BoxSizer(wx.HORIZONTAL)
        type_label = wx.StaticText(self, label=loc.get("select_bridge_type"))
        self.bridge_type_choice = wx.ComboBox(
            self,
            choices=["1", "2", "3", "4", "5"],
            style=wx.CB_READONLY,
            size=wx.Size(60, -1)
        )
        font = get_textctrl_font(self)
        type_label.SetFont(font)
        self.bridge_type_choice.SetFont(font)
        type_row.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        type_row.Add(self.bridge_type_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        self.left_sizer.Add(type_row, 0, wx.ALL, 10)

        # -----------------------------
        # Canvas для картинки
        # -----------------------------
        default_image = BRIDGE_TYPE_IMAGES.get("1", "")
        self.canvas = CanvasPanel(self, image_file=str(default_image), size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Привязка события выбора типа мостика
        self.bridge_type_choice.Bind(wx.EVT_COMBOBOX, self.on_bridge_type_changed)

        # -----------------------------
        # Данные: материалы, толщины
        # -----------------------------
        common_data = load_common_data()
        material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
        thickness_options = common_data.get("thicknesses", [])

        # -----------------------------
        # Форма и фабрики полей
        # -----------------------------
        self.form = FormBuilder(self)
        self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

        # =============================
        # Основные данные
        # =============================
        main_data_sizer = self.fb.static_box("main_data")
        self.static_boxes["main_data"] = main_data_sizer.GetStaticBox()
        fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_order = fb_main.create_label("order_label")
        order_ctrl = wx.TextCtrl(self, size=wx.Size(150, -1))
        detail_ctrl = wx.TextCtrl(self, size=wx.Size(150, -1))
        self.form.register("order", order_ctrl)
        self.form.register("detail", detail_ctrl)
        row.Add(lbl_order, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row.Add(order_ctrl, 0, wx.RIGHT, 10)
        row.Add(detail_ctrl, 1)
        main_data_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 5)

        # Материал и Толщина через ComboBox
        fb_main.combo(name="material", label_key="material_label", choices=material_options, required=True)
        fb_main.combo(name="thickness", label_key="thickness_label", choices=thickness_options, required=True)

        # =============================
        # Данные мостика (базовая геометрия)
        # =============================
        bridge_geom_sizer = self.fb.static_box("bridge_geometry")
        fb_geom = FieldBuilder(parent=self, target_sizer=bridge_geom_sizer, form=self.form)
        fb_geom.combo(name="width", label_key="bridge_width", choices=[], required=True)
        fb_geom.combo(name="height", label_key="bridge_height", choices=[], required=True)
        fb_geom.combo(name="variant", label_key="geometry_variant",
                      choices=["Variant 1", "Variant 2", "Variant 3"], required=True)

        # =============================
        # Специфические параметры, вырез, таблички
        # =============================
        # TODO: дочерние окна и кнопки для специфики и табличек

        # -----------------------------
        # Кнопки
        # -----------------------------
        self.right_sizer.AddStretchSpacer()
        self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # -----------------------------
        # Финальная сборка
        # -----------------------------
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

        # -----------------------------
        # Инициализация: дефолтный тип мостика
        # -----------------------------
        self.bridge_type_choice.SetSelection(0)  # индекс 0 = тип "1"
        wx.CallAfter(self.on_bridge_type_changed)


    # ------------------------------------------------------------------
    # Сервис
    # ------------------------------------------------------------------
    def clear_input_fields(self):
        self.form.clear()
        self.insert_point = None
        update_status_bar_point_selected(self, None)

    # ------------------------------------------------------------------
    # Кнопки-
    # ------------------------------------------------------------------
    def on_ok(self, *args, **kwargs):
        """
        Формирует словарь bridge_data на основе введённых данных.

        TODO:
            - выбор точки вставки
            - валидация
            - вызов расчётного модуля
        """
        pass

    def on_clear(self, event: Optional[wx.Event] = None):
        _ = event
        self.clear_input_fields()

    def on_cancel(self, event: Optional[wx.Event] = None, switch_content="content_apps"):
        _ = event
        self.switch_content_panel(switch_content)


# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------
if __name__ == "__main__":

    app = wx.App(False)
    frame = wx.Frame(None, title="test_rings_window", size=wx.Size(1500, 700))
    panel = BracketContentPanel(frame)



    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()







