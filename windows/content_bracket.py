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
    windows.content_bracket       — панель ввода и специфики мостиков

TODO:
    - реализация дочерних окон специфики по типам
    - валидация входных данных
    - привязка выбора точки вставки (AutoCAD)
"""

from typing import Optional, Dict, cast

from wx.lib.buttons import GenButton

from config.at_cad_init import ATCadInit
from config.at_config import *
from config.name_plates.nameplate_storage import load_nameplates
from locales.at_translations import loc
from windows.at_fields_builder import FormBuilder, FieldBuilder
from windows.at_window_utils import (
    CanvasPanel, show_popup, apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, get_wx_color_from_value, get_standard_font,
    get_textctrl_font, apply_radio_group
)
from programs.at_input import at_get_point

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "order_label": {
        "ru": "Номер заказа",
        "de": "Auftragsnummer",
        "en": "Order Number"
    },
    "detail_label": {
        "ru": "Номер детали",
        "de": "Teilenummer",
        "en": "Part Number"
    },
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "dimensions_label": {"ru": "Размеры", "de": "Abmessungen", "en": "Dimensions"},
    "select_bridge_type": {"ru": "Выберите тип мостика", "de": "Wählen Sie den Brückentyp aus", "en": "Select the type of bracket"},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},
    "bridge_geometry": {"ru": "Геометрия мостика", "de": "Schilderbrücke Geometry", "en": "Bracket geometry"},
    "size_label": {"ru": "Размер", "de": "Größe", "en": "Size"},
    "length_label": {"ru": "Длина L, мм", "de": "Länge L, mm", "en": "Length L, mm"},
    "width_label": {"ru": "Ширина W, мм", "de": "Breite W, mm", "en": "Width W, mm"},
    "height_label": {"ru": "Высота H, мм", "de": "Höhe H, mm", "en": "Height H, mm"},
    "cutout_label": {"ru": "Вырез", "de": "Ausschnitt", "en": "Cut out"},
    "manual_input_label": {"ru": "Ручной ввод", "de": "Manuelle Eingabe", "en": "Manual Input"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "no_data_error": {"ru": "Необходимо ввести хотя бы один размер", "de": "Mindestens eine Größe muss eingegeben werden", "en": "At least one size must be entered"},
    "max_points_error": {"ru": "Максимальное количество точек - 5", "de": "Maximale Anzahl von Punkten - 5", "en": "Maximum number of points - 5"},
    "size_positive_error": {"ru": "Размеры должны быть положительными", "de": "Größen müssen positiv sein", "en": "Sizes must be positive"},
    "invalid_number_format_error": {"ru": "Неверный формат числа", "de": "Ungültiges Zahlenformat", "en": "Invalid number format"},
    "offset_non_negative_error": {"ru": "Отступ не может быть отрицательным", "de": "Randabstand darf nicht negativ sein", "en": "Allowance cannot be negative"},
    "vessel_label": {"ru": "Таблички", "de": "Schilder", "en": "Vessel names"},
    "point_selection_error": {"ru": "Ошибка выбора точки", "de": "Fehler bei der Punktauswahl", "en": "Point selection error"},
    "height_cut": {"ru": "Высота выреза Hc", "de": "Ausschnitthöhe Hc", "en": "Cutout height Hc"},
    "length_cut": {"ru": "Глубина выреза Lc", "de": "Ausschnitttiefe Lc", "en": "Cutout length Lc"},
    "cutout_parameters": {"ru": "Параметры выреза, мм", "de": "Ausschnittparameter, mm", "en": "Cutout parameters, mm"},
    "cut_angle": {"ru": "Форма Rc", "de": "Form Rc", "en": "Form Rc"},
    "cut": {"ru": "Срез (R=0)", "de": "Schnitt (R=0)", "en": "Cut (R=0)"},
    "round": {"ru": "Скругление", "de": "Abrundung", "en": "Round"},
    "chamber": {"ru": "Фаска 45°", "de": "Fase 45°", "en": "Chamfer 45°"}
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

# ==========================================================
# Специализированные окна
# ==========================================================
class BracketSpecificPanel(wx.Panel):
    """
    Панель специфических параметров мостика.
    Управляет доступностью полей и собирает сырые данные для дальнейшей обработки.
    """

    # Схема полей по типам
    BRIDGE_SPEC_FIELDS = {
        "type1": ["add_detail_number", "length", "web_height", "corner_radius"],
        "type2": ["shell_diameter1", "length"],  # L или L0, в словарь length
        "type3": ["shell_diameter1", "length", "l1", "edge_angle"],
        "type4": ["shell_diameter1", "length"],  # L или L0
        "type5": ["shell_diameter1", "shell_diameter2", "length", "l1", "l2", "edge_angle"]
    }

    def __init__(self, parent, form: FormBuilder):
        super().__init__(parent)
        self.form = form
        self.bridge_type: Optional[str] = None

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.fields_sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.fields_sizer, 1, wx.EXPAND | wx.ALL, 5)

        self.controls: dict[str, wx.Control] = {}

    def rebuild(self, bridge_type: str):
        """
        Перестройка панели под указанный тип мостика.
        """
        self.bridge_type = bridge_type
        self.fields_sizer.Clear(True)
        self.controls.clear()

        fb = FieldBuilder(parent=self, target_sizer=self.fields_sizer, form=self.form)

        # --- список полей для текущего типа ---
        fields = self.BRIDGE_SPEC_FIELDS.get(bridge_type, [])

        for name in fields:
            # Особый комбобокс для corner_radius
            if bridge_type == "type1" and name == "corner_radius":
                row_sizer = wx.BoxSizer(wx.HORIZONTAL)
                label = wx.StaticText(self, label="Оформление краёв")
                row_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

                # Комбобокс
                combo = wx.ComboBox(
                    self,
                    choices=["Угол", "Скругление", "Фаска 45°"],
                    style=wx.CB_READONLY,
                )
                row_sizer.Add(combo, 0, wx.RIGHT, 5)

                # Поле для ввода величины
                value_ctrl = wx.TextCtrl(self)
                row_sizer.Add(value_ctrl, 0)

                # Регистрация контролов в form.fields
                self.form.register("corner_radius_type", combo)
                self.form.register("corner_radius_value", value_ctrl)

                # Блокировка ввода, если выбран угол
                def on_combo_change(event):
                    selection = combo.GetStringSelection()
                    if selection == "Угол":
                        value_ctrl.Disable()
                        value_ctrl.SetValue("0")
                    else:
                        value_ctrl.Enable()

                combo.Bind(wx.EVT_COMBOBOX, on_combo_change)

                self.fields_sizer.Add(row_sizer, 0, wx.ALL, 2)

            # Для типов 2 и 4 обрабатываем L и L0
            elif bridge_type in ("type2", "type4") and name in ("length", "l0"):
                ctrl = fb.text(
                    name=name,
                    label_key=name,
                    parser=float,
                    required=True
                )
                # блокировка взаимозависимого поля через form.fields
                other_name = "l0" if name == "length" else "length"
                other_value = self.form.fields.get(other_name)
                if other_value and other_value.get_value() is not None:
                    ctrl.Disable()
            else:
                ctrl = fb.text(
                    name=name,
                    label_key=name,
                    parser=float if "diameter" in name or "length" in name or "height" in name or "l" in name or "edge_angle" in name else str,
                    required=name in ["shell_diameter1", "length", "edge_angle"]
                )

            self.controls[name] = ctrl

        if bridge_type == "type5":
            length_ctrl = self.controls.get("length")
            l2_ctrl = self.controls.get("l2")
            length_val = self.form.fields.get("length")
            l2_val = self.form.fields.get("l2")
            if l2_val and l2_val.get_value() is not None:
                if length_ctrl:
                    length_ctrl.Disable()
            else:
                if l2_ctrl:
                    l2_ctrl.Disable()

        # Обязательно перерисовываем Layout
        self.Layout()

    def get_raw_data(self) -> dict:
        """
        Возвращает все введенные значения. Для пустых полей возвращает None или 0.
        """
        data = {}
        for name, ctrl in self.controls.items():
            if ctrl is None:
                continue

            value = ctrl.get_value()
            if value is None:
                # для числовых полей возвращаем 0, для строковых None
                if isinstance(ctrl, wx.TextCtrl):
                    try:
                        value = float(ctrl.GetValue())
                    except ValueError:
                        value = 0.0
                else:
                    value = None

            # Преобразование corner_radius из комбобокса в число
            if name == "corner_radius" and isinstance(ctrl, wx.ComboBox):
                val_str = ctrl.GetValue()
                if val_str == "угол":
                    value = 0.0
                elif val_str == "скругление":
                    value = 5.0  # пример радиуса, можно задавать конкретно
                elif val_str == "фаска 45°":
                    value = -45.0

            data[name] = value

        # Для type5 вычисляем variant автоматически
        if self.bridge_type == "type5":
            length, l2 = data.get("length"), data.get("l2")
            if l2 and l2 > 0:
                data["variant"] = 3
                data["length"] = 0  # length недоступен
            elif length and length > 0:
                data["variant"] = 1
            else:
                data["variant"] = 2
                data["length"] = 0
            if "l1" not in data:
                data["l1"] = 0

        # Для type3, если l1 не задан, ставим 0
        if self.bridge_type == "type3" and "l1" not in data:
            data["l1"] = 0

        return data


# ==========================================================
# Главная панель
# ==========================================================
class BracketContentPanel(BaseContentPanel):
    """
    Панель для ввода параметров мостиков и табличек.

    Основные функции:
    -----------------
    - Выбор типа мостика
    - Ввод технологических параметров (номер заказа, деталь, материал, толщина)
    - Ввод базовой геометрии (ширина, высота)
    - Панель специфики для отдельных типов мостиков (corner_radius, shell_diameter и др.)
    - Панель табличек (до 3 табличек, расстояния, отступ от верхнего края)
    - Панель выреза в мостике (если требуется)
    - Формирование словаря `bridge_data` для дальнейшей обработки
    """

    def __init__(self, parent: wx.Window, callback=None):
        """
        Инициализация панели.

        Args:
            parent: Родительский wx.Window.
            callback: Функция обратного вызова для передачи словаря bridge_data.
        """
        super().__init__(parent)
        self.parent = parent
        self.on_submit_callback = callback

        # --------------------------------------------------
        # UI элементы и вспомогательные поля
        # --------------------------------------------------
        self.bridge_type_choice: Optional[wx.ComboBox] = None
        self.canvas: Optional[CanvasPanel] = None
        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None
        self.form: Optional[FormBuilder] = None
        self.fb: Optional[FieldBuilder] = None
        self.specific_panel: Optional[BracketSpecificPanel] = None
        self.nameplate_panel: Optional[NamePlateSelectionPanel] = None
        self.cutout_panel: Optional[CutoutPanel] = None

        # Загружаем пользовательские настройки для фона
        self.settings = load_user_settings()
        self.SetBackgroundColour(
            get_wx_color_from_value(
                self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
            )
        )

        # Построение интерфейса
        self.setup_ui()

    # ------------------------------------------------------------------
    # Обновление изображения мостика при выборе типа
    # ------------------------------------------------------------------

    def on_bridge_type_changed(self, event: Optional[wx.Event] = None):
        """
        Обновляет картинку мостика в CanvasPanel при изменении типа мостика.
        """
        bridge_type = self.bridge_type_choice.GetStringSelection()
        if not bridge_type:
            return

        # обновляем картинку
        image_path = BRIDGE_TYPE_IMAGES.get(bridge_type)
        if image_path:
            self.canvas.set_image(image_path)

        # --- перестройка секции специфики даже если она открыта ---
        if self.specific_panel:
            self.specific_panel.rebuild(f"type{bridge_type}")
            # показываем секцию, если она была открыта
            if self.specific_panel.IsShown():
                self._show_section(self.specific_panel)

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:
        """
        Строит интерфейс панели: левый блок с Canvas, правый блок с данными.
        Добавляет три кнопки для управления спецификой, табличками и вырезом.
        """
        # Очистка предыдущего интерфейса
        if self.GetSizer():
            self.GetSizer().Clear(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # -----------------------------
        # Выбор типа мостика
        # -----------------------------
        self.form = FormBuilder(self)
        fb_left = FieldBuilder(self, self.left_sizer, form=self.form)
        self.bridge_type_choice = wx.ComboBox(
            self,
            choices=["1", "2", "3", "4", "5"],
            style=wx.CB_READONLY,
            size=wx.Size(60, -1)
        )
        # Регистрируем с преобразованием
        self.form.register(
            name="type",
            ctrl=self.bridge_type_choice,
            required=True,
            parser=lambda v: f"type{v}"
        )

        fb_left.row(
            label_key="select_bridge_type",
            controls=[self.bridge_type_choice],
            spacing=8,
            align_right=False
        )

        # Canvas с изображением мостика
        default_image = BRIDGE_TYPE_IMAGES.get("1", "")
        self.canvas = CanvasPanel(self, image_file=str(default_image), size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)
        self.bridge_type_choice.Bind(wx.EVT_COMBOBOX, self.on_bridge_type_changed)

        # -----------------------------
        # Загрузка общих данных
        # -----------------------------
        common_data = load_common_data()
        material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
        thickness_options = common_data.get("thicknesses", [])

        # -----------------------------
        # Форма и фабрика полей
        # -----------------------------
        self.form = FormBuilder(self)
        self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

        # =============================
        # Основные данные
        # =============================
        main_data_sizer = self.fb.static_box("main_data")
        fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        # Номер заказа и номер детали
        fb_main.universal_row(
            "order_label",
            [
                {"type": "text", "name": "order", "value": "", "required": False, "default": ""},
                {"type": "text", "name": "detail", "value": "", "required": False, "default": ""},
            ]
        )

        # Материал
        fb_main.universal_row(
            "material_label",
            [
                {"type": "combo", "name": "material", "choices": material_options, "value": "", "required": True, "default": "1.4301"}
            ]
        )

        # Толщина
        fb_main.universal_row(
            "thickness_label",
            [
                {"type": "combo", "name": "thickness", "choices": thickness_options, "value": "", "required": True, "default": "3"}
            ]
        )

        # =============================
        # Базовая геометрия мостика
        # =============================
        bridge_geom_sizer = self.fb.static_box("bridge_geometry")
        fb_geom = FieldBuilder(parent=self, target_sizer=bridge_geom_sizer, form=self.form)

        fb_geom.universal_row(
            "width_label",
            [
                {"type": "text", "name": "width", "value": "", "required": True, "default": ""},
            ]
        )
        fb_geom.universal_row(
            "height_label",
            [
                {"type": "text", "name": "height", "value": "", "required": True, "default": ""},
            ]
        )

        # -----------------------------
        # Панели специфики
        # -----------------------------
        self.specific_panel = BracketSpecificPanel(self, form=self.form)
        bridge_geom_sizer.Add(self.specific_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Панель табличек
        self.nameplate_panel = NamePlateSelectionPanel(self, form=self.form)
        self.nameplate_panel.Hide()
        bridge_geom_sizer.Add(self.nameplate_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Панель выреза
        self.cutout_panel = CutoutPanel(self, form=self.form)
        self.cutout_panel.Hide()
        bridge_geom_sizer.Add(self.cutout_panel, 0, wx.EXPAND | wx.ALL, 5)

        # -----------------------------
        # Кнопки управления
        # -----------------------------
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fb_button = FieldBuilder(parent=self, target_sizer=button_sizer, form=self.form)

        fb_button.universal_row(
            "",
            [
                {
                    "type": "button",
                    "label": loc.get("dimensions_label"),
                    "callback": self.on_toggle_specific,
                    "bg_color": "#27ae60",
                    "toggle": True,
                    "size": BUTTON_SIZE
                },
                {
                    "type": "button",
                    "label": loc.get("vessel_label"),
                    "callback": self.on_toggle_nameplates,
                    "bg_color": "#2980b9",
                    "toggle": True,
                    "size": BUTTON_SIZE
                },
                {
                    "type": "button",
                    "label": loc.get("cutout_label"),
                    "callback": self.on_toggle_cutout,
                    "bg_color": "#8e44ad",
                    "toggle": True,
                    "size": BUTTON_SIZE
                }
            ]
        )

        self.right_sizer.Add(button_sizer, 0, wx.ALL, 5)

        # -----------------------------
        # Кнопки действия (ОК/Отмена)
        # -----------------------------
        self.right_sizer.AddStretchSpacer()
        self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Финальная сборка
        main_sizer.Add(self.left_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

        # Инициализация дефолтного типа мостика
        self.bridge_type_choice.SetSelection(0)
        wx.CallAfter(self.on_bridge_type_changed)

    # ------------------------------------------------------------------
    # Сохранение/восстановление значений контролов панели
    # ------------------------------------------------------------------
    def _hide_panel(self, panel: wx.Panel):
        """Сохраняет значения всех контролов панели и скрывает её."""
        if not panel:
            return
        for attr_name in dir(panel):
            ctrl = getattr(panel, attr_name)
            if isinstance(ctrl, (wx.TextCtrl, wx.ComboBox)):
                try:
                    ctrl._saved_value = ctrl.GetValue()
                except RuntimeError:
                    # Если контрол уже удалён (защита от ошибок)
                    continue
        panel.Hide()

    def _show_panel(self, panel: wx.Panel):
        """Показывает панель и восстанавливает сохранённые значения контролов."""
        if not panel:
            return
        panel.Show()
        for attr_name in dir(panel):
            ctrl = getattr(panel, attr_name)
            if isinstance(ctrl, (wx.TextCtrl, wx.ComboBox)):
                if hasattr(ctrl, "_saved_value"):
                    try:
                        ctrl.SetValue(ctrl._saved_value)
                    except RuntimeError:
                        continue


    # ------------------------------------------------------------------
    # Сервисные функции
    # ------------------------------------------------------------------
    def clear_input_fields(self):
        """
        Очистка всех полей формы и сброс точки вставки.
        """
        self.form.clear()
        self.insert_point = None
        update_status_bar_point_selected(self, None)

    # ------------------------------------------------------------------
    # Доступ к данным
    # ------------------------------------------------------------------
    def on_ok(self, *args, **kwargs):
        """
        Формирует словарь bridge_data на основе введённых данных
        и передаёт его в callback.
        """
        # Собираем базовые данные
        bridge_data = self.form.collect()

        # --------------------------------------------------
        # Пример: geometry уже есть в форме или задаём явно
        # --------------------------------------------------
        geometry = {
            "center_point": bridge_data.get("center_point", (0, 0, 0)),
            "width": bridge_data.get("width", 170.0),
            "height": bridge_data.get("height", 160.0),
            "length": bridge_data.get("length", 70.0),
        }

        # --------------------------------------------------
        # Вырез (cutout)
        # --------------------------------------------------
        cutout_data = self.cutout_panel.get_data(
            max_height=geometry["height"],
            max_length=geometry["length"]
        )

        if cutout_data:
            bridge_data.update(cutout_data)
        # если cutout_data is None — секция выреза просто не добавляется

        # --------------------------------------------------
        # Передача в callback
        # --------------------------------------------------
        print(bridge_data)  # Debug
        if self.on_submit_callback:
            self.on_submit_callback(bridge_data)

    def on_clear(self, event: Optional[wx.Event] = None):
        """Очистка полей по кнопке Clear."""
        _ = event
        self.clear_input_fields()

    def on_cancel(self, event: Optional[wx.Event] = None, switch_content="content_apps"):
        """Закрытие панели и возврат к предыдущему контенту."""
        _ = event
        self.switch_content_panel(switch_content)

    # ------------------------------------------------------------------
    # Переключение видимости панелей
    # ------------------------------------------------------------------
    def on_toggle_specific(self, event):
        self._show_section(self.specific_panel)

    def on_toggle_nameplates(self, event):
        self._show_section(self.nameplate_panel)

    def on_toggle_cutout(self, event):
        self._show_section(self.cutout_panel)

    def _hide_all_optional_panels(self):
        for panel in (self.specific_panel, self.nameplate_panel, self.cutout_panel):
            self._hide_panel(panel)

    def _show_section(self, section: Optional[wx.Panel]):
        # Сначала скрываем все остальные панели
        for panel in (self.specific_panel, self.nameplate_panel, self.cutout_panel):
            if panel and panel != section:
                self._hide_panel(panel)

        # Показываем нужную панель
        self._show_panel(section)
        self.Layout()


class NamePlateSelectionPanel(wx.Panel):
    """
    Панель выбора до 3 табличек и управления отступами.
    """
    MAX_PLATES = 3

    def __init__(self, parent, form: FormBuilder):
        super().__init__(parent)
        self.form = form
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.plate_choices: list[wx.ComboBox] = []
        self.spacing_ctrl: Optional[wx.TextCtrl] = None
        self.offset_top_ctrl: Optional[wx.TextCtrl] = None

        self._build_ui()

    def _build_ui(self):
        # Загружаем список табличек
        nameplates_list = load_nameplates()
        codes = [rec["name"] for rec in nameplates_list]

        for i in range(self.MAX_PLATES):
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl = wx.StaticText(self, label=f"Табличка {i+1}")
            ctrl = wx.ComboBox(
                self,
                choices=codes,
                style=wx.CB_READONLY,
                size=wx.Size(200, -1)
            )
            row_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            row_sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
            self.sizer.Add(row_sizer, 0, wx.ALL, 2)

            ctrl.Bind(wx.EVT_COMBOBOX, self._on_plate_changed)
            self.plate_choices.append(ctrl)

            # Скрываем все кроме первой
            if i != 0:
                ctrl.Disable()

        # Поле для расстояния между табличками
        row_spacing = wx.BoxSizer(wx.HORIZONTAL)
        lbl_spacing = wx.StaticText(self, label="Расстояние между табличками, мм")
        self.spacing_ctrl = wx.TextCtrl(self, size=(100, -1))
        row_spacing.Add(lbl_spacing, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row_spacing.Add(self.spacing_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(row_spacing, 0, wx.ALL, 5)

        # Поле отступа от верхнего края мостика
        row_offset = wx.BoxSizer(wx.HORIZONTAL)
        lbl_offset = wx.StaticText(self, label="Отступ от верхнего края мостика, мм")
        self.offset_top_ctrl = wx.TextCtrl(self, size=(100, -1))
        row_offset.Add(lbl_offset, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        row_offset.Add(self.offset_top_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(row_offset, 0, wx.ALL, 5)

        # Скрываем поле отступа пока нет первой таблички
        self.offset_top_ctrl.Disable()

    def _on_plate_changed(self, event):
        # Активируем следующий комбобокс, если есть
        for i, ctrl in enumerate(self.plate_choices):
            if ctrl.GetValue() == "" or i < len(self.plate_choices) - 1 and self.plate_choices[i+1].IsEnabled():
                continue
            if i < len(self.plate_choices) - 1:
                self.plate_choices[i+1].Enable()

        # Активируем поле отступа только если выбрана первая табличка
        if self.plate_choices[0].GetValue():
            self.offset_top_ctrl.Enable()
        else:
            self.offset_top_ctrl.Disable()
            self.offset_top_ctrl.SetValue("")

    def get_data(self) -> dict:
        """
        Возвращает словарь с выбранными табличками и отступами.
        """
        data = {}
        for i, ctrl in enumerate(self.plate_choices, start=1):
            key = f"nameplate_{i}"
            value = ctrl.GetValue()
            if value:
                data[key] = value
        spacing = self.spacing_ctrl.GetValue()
        offset = self.offset_top_ctrl.GetValue()
        if spacing:
            data["nameplate_spacing"] = spacing
        if offset:
            data["nameplate_offset_top"] = offset
        return data


class CutoutPanel(wx.Panel):
    """
    Панель для ввода параметров выреза в мостике.

    Поля:
        - height: высота выреза
        - length: длина выреза
        - radius: радиус/скос выреза
    """

    def __init__(self, parent, form: FormBuilder):
        super().__init__(parent)
        self.form = form
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self._build_ui()

    def _build_ui(self):
        """
        Строит интерфейс панели с тремя полями: высота, длина, радиус.
        Контролы регистрируются сразу в FormBuilder.
        """
        fb = FieldBuilder(parent=self, target_sizer=self.sizer, form=self.form)
        box_sizer = fb.static_box(loc.get("cutout_parameters"))
        fb_box = FieldBuilder(parent=self, target_sizer=box_sizer, form=self.form)

        fb_box.universal_row(
            loc.get("height_cut"),
            [
                {
                    "type": "text",
                    "name": "height",
                    "value": "",
                    "required": True,
                    "default": ""
                },
            ]
        )
        fb_box.universal_row(
            loc.get("length_cut"),
            [
                {
                    "type": "text",
                    "name": "length",
                    "value": "",
                    "required": True,
                    "default": ""
                },
            ]
        )

        # Список вариантов для комбо
        cut_options = [
            loc.get("cut"),
            loc.get("round"),
            loc.get("chamber")
        ]

        # Создаём строку через universal_row
        controls = fb_box.universal_row(
            loc.get("cut_angle"),
            [
                {
                    "type": "combo",
                    "name": "cutout_label",
                    "value": "",
                    "choices": cut_options,
                    "required": True,
                    "default": cut_options[0]
                },
                {
                    "type": "text",
                    "name": "r_cut",
                    "value": "",
                    "required": True,
                    "default": ""
                }
            ]
        )

        def update_r_cut(dependent, master):
            if master.GetStringSelection() == loc.get("cut_angle"):
                dependent.Disable()
                dependent.SetValue("0")
            else:
                dependent.Enable()

        controls[0].Bind(wx.EVT_COMBOBOX, lambda evt: update_r_cut(controls[1], controls[0]))

        # Один раз вызываем, чтобы установить начальное состояние
        update_r_cut(controls[1], controls[0])

        self.Layout()

    def get_data(self, max_height: float, max_length: float) -> dict | None:
        """
        Возвращает словарь параметров выреза в формате:
            {"cutout": {"height": float, "length": float, "radius": float}}
            radius корректируется в зависимости от выбранного типа выреза:
                cut: 0
                round: >0
                chamfer: <0 (отрицательное значение)

        Если высота или длина некорректны (0, None, пустая строка) — возвращается None.

        :param max_height: ограничение по высоте выреза (от geometry)
        :param max_length: ограничение по длине выреза (от geometry)
        """
        data_raw = self.form.collect()

        # Попытка конвертировать в float
        try:
            height = float(data_raw.get("height", 0.0))
        except (ValueError, TypeError):
            height = 0.0

        try:
            length = float(data_raw.get("length", 0.0))
        except (ValueError, TypeError):
            length = 0.0

        try:
            radius = float(data_raw.get("radius", 0.0))
        except (ValueError, TypeError):
            radius = 0.0

        # Приводим max_height и max_length к float
        try:
            max_height = float(max_height)
        except (ValueError, TypeError):
            max_height = float("inf")

        try:
            max_length = float(max_length)
        except (ValueError, TypeError):
            max_length = float("inf")

        # Проверка на валидность и границы
        if height <= 0 or length <= 0 or height > max_height or length > max_length:
            return None  # секция выреза не добавляется

        return {
            "cutout": {
                "height": height,
                "length": length,
                "radius": radius
            }
        }


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