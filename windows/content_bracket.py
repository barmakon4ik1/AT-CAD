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
"""
import math
from pprint import pprint
from typing import Optional, Dict, cast
from docutils.nodes import ValidationError
from wx.lib.buttons import GenButton
from config.at_cad_init import ATCadInit
from config.at_config import *
from config.name_plates.nameplate_storage import load_nameplates
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_geometry import diameter_cone_offset
from programs.at_name_plate import BridgeConfig, BridgeBuilder, NamePlate
from windows.at_fields_builder import FormBuilder, FieldBuilder
from windows.at_window_utils import (
    CanvasPanel, show_popup, apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel, load_user_settings, load_common_data, get_wx_color_from_value, get_standard_font,
    get_textctrl_font, apply_radio_group, parse_float
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
    "chamber": {"ru": "Фаска 45°", "de": "Fase 45°", "en": "Chamfer 45°"},
    "special_parameters": {"ru": "Специальные параметры", "de": "Spezielle Parameter", "en": "Special parameters"},
    "add_detail_number": {"ru": "Номер детали перемычки", "de": "Steg Teilenummer", "en": "Web part number"},
    "corner_label": {"ru": "Форма R", "de": "Form R", "en": "Form R"},
    "web_height": {"ru": "Высота H1, мм", "de": "Höhe H1, mm", "en": "Height H1, mm"},
    "shell_diameter": {"ru": "Диаметр D, мм", "de": "Durchmesser D, mm", "en": "Diameter D, mm"},
    "shell_diameter1": {"ru": "Диаметр D1, мм", "de": "Durchmesser D1, mm", "en": "Diameter D1, mm"},
    "shell_diameter2": {"ru": "Диаметр D2, мм", "de": "Durchmesser D2, mm", "en": "Diameter D2, mm"},
    "length": {"ru": "Длина, мм", "de": "Länge, mm", "en": "Length, mm"},
    "length1": {"ru": "Длина L1, мм", "de": "Länge L1, mm", "en": "Length L1, mm"},
    "calculate": {"ru": "Рассчитать", "de": "Berechnen", "en": "Calculate"},
    "edge_angle_label": {"ru": "Угол A°", "de": "Winkel A°", "en": "Angle A°"},
    "no": {"ru": "Неизвестно", "de": "Unbekannt", "en": "Unknown"},
    "auto": {"ru": "автоматически", "de": "automatisch", "en": "automatically"},
    "select": {"ru": "Выбрать", "de": "Auswählen", "en": "Select"},
    "bridge_type_not_selected": {
        "ru": "Не выбран тип мостика",
        "de": "Brückentyp nicht ausgewählt",
        "en": "Bridge type not selected"
    },
    "validation_error": {
        "ru": "Ошибка проверки данных",
        "de": "Validierungsfehler",
        "en": "Validation error"
    },
    "length_positive_error": {
        "ru": "Длина должна быть больше 0",
        "de": "Länge muss größer als 0 sein",
        "en": "Length must be greater than 0"
    },
    "diameter_positive_error": {
        "ru": "Диаметр должен быть больше 0",
        "de": "Durchmesser muss größer als 0 sein",
        "en": "Diameter must be greater than 0"
    },
    "invalid_width_error": {
        "ru": "Некорректная ширина мостика",
        "de": "Ungültige Brückenbreite",
        "en": "Invalid bridge width"
    },
    "width_exceeds_diameter": {
        "ru": "Ширина или высота мостика больше диаметра. Выберите тип 3 или 5.",
        "de": "Brückenbreite oder Brückenhöhe größer als Durchmesser. Typ 3 oder 5 wählen.",
        "en": "Bridge width or height exceeds diameter. Choose type 3 or 5."
    },
    "geometry_compensation_error": {
        "ru": "Геометрическая ошибка вычисления компенсации",
        "de": "Geometrischer Fehler bei Kompensation",
        "en": "Geometric compensation error"
    },
    "invalid_length_option": {
        "ru": "Неверный параметр длины",
        "de": "Ungültige Längenoption",
        "en": "Invalid length option"
    },
    "invalid_angle_error": {
        "ru": "Недопустимое значение угла",
        "de": "Ungültiger Winkel",
        "en": "Invalid angle"
    },
    "name_plates": {"ru": "Таблички", "de": "Schilder", "en": "Name plates"},
    "name_plate": {"ru": "Табличка", "de": "Schilder", "en": "Name plate"},
    "point_prompt": {
        "ru": "Укажите центр вставки развертки мостика",
        "de": "Geben Sie die Mitte der Schilderbrücken Abwicklung an",
        "en": "Specify the center of the bridge scan insertion"
    },
    "plates_gap_label": {
        "ru": "Интервал табличек Hz, мм",
        "de": "Schildabstand Hz, mm",
        "en": "Plate Spacing Hz, mm"
    },
    "offset_top_label": {
        "ru": "Верхний отступ Ho, мм",
        "de": "Oberer Randabstand Ho, mm",
        "en": "Top Offset Ho, mm"
    },
    "diameter_dialog_title": {
        "ru": "Диаметры конуса",
        "de": "Kegeldurchmesser",
        "en": "Cone Diameters"
    },

    "diameter_type_inner": {
        "ru": "Внутренний",
        "de": "Innendurchmesser",
        "en": "Inner"
    },
    "diameter_type_middle": {
        "ru": "Средний",
        "de": "Mittlerer Durchmesser",
        "en": "Middle"
    },
    "diameter_type_outer": {
        "ru": "Наружный",
        "de": "Außendurchmesser",
        "en": "Outer"
    }
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
        bridge_type = self.bridge_type_choice.GetValue()
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

        self.form = FormBuilder(self)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # -----------------------------
        # Левая часть
        # -----------------------------
        fb_left = FieldBuilder(self, self.left_sizer, form=self.form)

        created = fb_left.universal_row(
            label_key="select_bridge_type",
            elements=[
                {
                    "type": "combo",
                    "name": "type",
                    "choices": ["1", "2", "3", "4", "5"],
                    "value": "1",
                    "required": True,
                    "parser": lambda v: f"type{v}",
                    "default": "1",
                    "align_right": False,
                }
            ],
            element_proportion=0,
        )

        # universal_row возвращает список созданных контролов
        self.bridge_type_choice = created[0]

        # Canvas с изображением мостика
        default_image = BRIDGE_TYPE_IMAGES.get("1", "")
        self.canvas = CanvasPanel(self, image_file=str(default_image), size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Событие
        self.bridge_type_choice.Bind(wx.EVT_COMBOBOX, self.on_bridge_type_changed)

        # -----------------------------
        # Загрузка общих данных
        # -----------------------------
        common_data = load_common_data()
        material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
        thickness_options = common_data.get("thicknesses", [])

        # -----------------------------
        # ПРАВАЯ ЧАСТЬ
        # -----------------------------
        self.fb = FieldBuilder(
            parent=self,
            target_sizer=self.right_sizer,
            form=self.form
        )

        # =============================
        # Основные данные
        # =============================
        main_data_sizer = self.fb.static_box("main_data")
        fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        # Номер заказа и номер детали
        fb_main.universal_row(
            "order_label",
            [
                {"type": "text", "name": "order_number", "value": "", "required": False, "default": ""},
                {"type": "text", "name": "detail_number", "value": "", "required": False, "default": ""},
            ]
        )

        # Материал
        fb_main.universal_row(
            "material_label",
            [
                {"type": "combo",
                 "name": "material",
                 "choices": material_options,
                 "value": "",
                 "required": True,
                 "default": "1.4301",
                 "size": (310, -1),}
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

        wx.CallAfter(self.on_bridge_type_changed)
        wx.CallAfter(self.clear_input_fields)

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
        # Сохраняем текущий тип
        current_type = self.bridge_type_choice.GetStringSelection()

        # Очищаем форму
        self.form.clear()

        # Восстанавливаем тип
        if current_type:
            self.bridge_type_choice.SetStringSelection(current_type)
            self.on_bridge_type_changed(None)

    # ------------------------------------------------------------------
    # Доступ к данным
    # ------------------------------------------------------------------
    def on_ok(self, *args, **kwargs):
        """
        Формирует строго структурированный словарь bridge_data
        и передаёт его в callback.
        """

        raw = self.form.collect()
        if not raw:
            return

        bridge_type = raw.get("type")

        geometry = {
            "center_point": raw.get("center_point"),
            "width": parse_float(raw.get("width")),
            "height": parse_float(raw.get("height")),
        }

        bridge_data = {
            "type": bridge_type,
            "order_number": raw.get("order_number"),
            "detail_number": raw.get("detail_number"),
            "material": raw.get("material"),
            "thickness": raw.get("thickness"),
            "geometry": geometry,
        }

        # Specific
        specific_data = self.specific_panel.get_specific_data(geometry)
        if specific_data is None:
            return
        bridge_data.update(specific_data)

        # Cutout
        if self.cutout_panel:
            cutout_data = self.cutout_panel.get_data()
            if cutout_data:
                bridge_data["cutout"] = cutout_data["cutout"]

        # Nameplates
        if self.nameplate_panel:
            nameplate_data = self.nameplate_panel.get_data()
            if nameplate_data:
                bridge_data.update(nameplate_data)

        # ======================================================
        # Debug
        # ======================================================
        # pprint(bridge_data)

        # ======================================================
        # Обработка
        # ======================================================
        try:
            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            adoc = cad.document
            model_space = cad.model_space

            if not cad.is_initialized():
                show_popup(loc.get("cad_not_ready"), popup_type="error")
                return

            if not model_space:
                show_popup(loc.get("cad_not_ready"), popup_type="error")
                return

            # Сворачиваем окно перед выбором точки
            main_window.Hide()

            pt = at_get_point(
                cad.document,
                prompt=loc.get("point_prompt", "Укажите центр мостика"),
                as_variant=False
            )

            if not pt:
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            # Разворачиваем окно обратно
            main_window.Show()
            main_window.Raise()
            main_window.SetFocus()

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            bridge_data["geometry"]["center_point"] = pt

            np = NamePlate()

            pprint(bridge_data) # Debug

            # # Передаем данные дальше через callback
            # if self.on_submit_callback:
            #     self.on_submit_callback(bridge_data)

            config = BridgeConfig(adoc, bridge_data)
            builder = BridgeBuilder(config, np.plates)
            builder.build(model_space)
            cad.regen_doc()

        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")

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
    Панель выбора до MAX_PLATES табличек и управления их расположением.

    Логика работы:
    --------------
    1. Доступна первая табличка.
    2. Вторая становится доступной только если выбрана первая.
    3. Третья становится доступной только если выбрана вторая.
    4. Поле plates_gap активно только если выбрано более одной таблички (>1).
    5. Поле offset_top относится только к первой табличке и активно,
       если выбрана первая табличка.
    6. Выбор таблички возможен:
       - из выпадающего списка
       - через диалог выбора (NamePlateDialog)

    Возвращаемая структура данных:
    -------------------------------
    {
        "plates": [
            {"name": "B+H_Ustamp_1Room", "offset_top": 7.0},
            {"name": "GEA_gross"}
        ],
        "plates_gap": 6.0
    }
    """

    MAX_PLATES = 3

    def __init__(self, parent, form: FormBuilder):
        super().__init__(parent)

        self.form = form
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        # Список словарей вида:
        # [{"combo": wx.ComboBox, "button": wx.Button}, ...]
        self.plates: list[dict] = []

        self.plates_gap_ctrl: wx.TextCtrl | None = None
        self.offset_top_ctrl: wx.TextCtrl | None = None

        self._build_ui()
        self._update_enable_state()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self):
        """
        Создаёт интерфейс панели:
        - строки выбора табличек
        - поле межтабличного расстояния
        - поле верхнего отступа
        """

        nameplates_list = load_nameplates()
        codes = [rec["name"] for rec in nameplates_list]

        fb = FieldBuilder(parent=self, target_sizer=self.sizer, form=self.form)
        box_sizer = fb.static_box(loc.get("name_plates"))
        fb_box = FieldBuilder(parent=self, target_sizer=box_sizer, form=self.form)

        # --- Строки выбора табличек ---
        for i in range(self.MAX_PLATES):
            controls = fb_box.universal_row(
                f"{i+1}:",
                [
                    {
                        "type": "combo",
                        "name": f"name_plate_{i+1}",
                        "choices": codes,
                        "value": "",
                        "size": (210, -1)
                    },
                    {
                        "type": "button",
                        "label": loc.get("select") if loc.get("select") else "Выбрать",
                        "callback": lambda evt, idx=i: self._on_select_dialog(idx),
                        "bg_color": "#00BFFF",
                        "toggle": False
                    },
                ]
            )

            combo, button = controls

            combo.Bind(wx.EVT_COMBOBOX,
                       lambda evt, idx=i: self._on_combo_changed(idx))

            self.plates.append({
                "combo": combo,
                "button": button
            })

        # --- Расстояние между табличками ---
        gap_ctrl = fb_box.universal_row(
            loc.get("plates_gap_label"),
            [{
                "type": "text",
                "name": "plates_gap",
                "value": "5"
            }]
        )
        self.plates_gap_ctrl = gap_ctrl[0]

        # --- Отступ верхнего края ---
        offset_ctrl = fb_box.universal_row(
            loc.get("offset_top_label"),
            [{
                "type": "text",
                "name": "offset_top",
                "value": loc.get("auto")
            }]
        )
        self.offset_top_ctrl = offset_ctrl[0]

    # ------------------------------------------------------------------
    # Логика выбора
    # ------------------------------------------------------------------

    def _on_combo_changed(self, idx: int):
        """Обработчик изменения выбора в ComboBox."""
        self._update_enable_state()

    def _on_select_dialog(self, idx: int):
        """
        Открывает диалог выбора таблички.
        Возвращённый код записывается в соответствующий ComboBox.
        """
        from windows.nameplate_dialog import create_window

        code = create_window(self)
        if code:
            self.plates[idx]["combo"].SetValue(code)
            self._update_enable_state()

    # ------------------------------------------------------------------
    # Управление доступностью элементов
    # ------------------------------------------------------------------

    def _update_enable_state(self):
        """
        Централизованная логика включения/отключения элементов.
        """

        selected_count = 0

        for i, plate in enumerate(self.plates):
            combo = plate["combo"]
            button = plate["button"]

            if i == 0:
                combo.Enable()
                button.Enable()
            else:
                prev_selected = bool(self.plates[i - 1]["combo"].GetValue())
                combo.Enable(prev_selected)
                button.Enable(prev_selected)

                if not prev_selected:
                    combo.SetValue("")

            if combo.GetValue():
                selected_count += 1

        # plates_gap активен только если выбрано > 1
        self.plates_gap_ctrl.Enable(selected_count > 1)

        # offset_top активен только если выбрана первая
        self.offset_top_ctrl.Enable(
            bool(self.plates[0]["combo"].GetValue())
        )

    # ------------------------------------------------------------------
    # Получение данных
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        """
        Формирует итоговую структуру данных.

        Возвращает:
        ----------
        dict — структура для дальнейшей обработки
        """

        plates_data = []

        for i, plate in enumerate(self.plates):
            name = plate["combo"].GetValue()
            if not name:
                continue

            entry = {"name": name}

            # offset_top только для первой таблички
            if i == 0 and self.offset_top_ctrl.IsEnabled():
                offset_value = self.offset_top_ctrl.GetValue()
                if offset_value and offset_value != loc.get("auto"):
                    try:
                        entry["offset_top"] = parse_float(offset_value)
                    except ValueError:
                        show_popup(
                            loc.get("invalid_number_format_error"),
                            popup_type="error"
                        )
                        return {}

            plates_data.append(entry)

        if not plates_data:
            return {}

        result = {"plates": plates_data}

        # plates_gap только если >1
        if len(plates_data) > 1:
            gap_value = self.plates_gap_ctrl.GetValue()
            if gap_value:
                try:
                    result["plates_gap"] = parse_float(gap_value)
                except ValueError:
                    show_popup(
                        loc.get("invalid_number_format_error"),
                        popup_type="error"
                    )
                    return {}

        return result


class CutoutPanel(wx.Panel):
    """
    Панель для ввода параметров выреза в мостике.

    Поля:
        - height_cut: высота выреза
        - length_cut: длина выреза
        - radius_cut: радиус/скос выреза
        - cutout_label: тип выреза (cut/round/chamber)
    """

    def __init__(self, parent, form: FormBuilder):
        super().__init__(parent)
        self.form = form
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self._build_ui()

    def _build_ui(self):
        """
        Строит интерфейс панели с тремя полями: высота, длина, радиус
        и комбобоксом типа выреза.
        Контролы сразу регистрируются в FormBuilder.
        """
        fb = FieldBuilder(parent=self, target_sizer=self.sizer, form=self.form)
        box_sizer = fb.static_box(loc.get("cutout_parameters"))
        fb_box = FieldBuilder(parent=self, target_sizer=box_sizer, form=self.form)

        # ------------------------
        # Поля height и length
        # ------------------------
        fb_box.universal_row(
            loc.get("height_cut"),
            [{"type": "text", "name": "height_cut", "value": "", "required": True, "default": ""}]
        )
        fb_box.universal_row(
            loc.get("length_cut"),
            [{"type": "text", "name": "length_cut", "value": "", "required": True, "default": ""}]
        )

        # ------------------------
        # ComboBox для выбора типа выреза + поле radius
        # ------------------------
        cut_options = [loc.get("round"), loc.get("chamber")]

        controls = fb_box.universal_row(
            loc.get("cut_angle"),
            [
                {
                    "type": "combo",
                    "name": "cutout_label",
                    "value": cut_options[0],
                    "choices": cut_options,
                    "required": True,
                    "default": cut_options[0]
                },
                {
                    "type": "text",
                    "name": "radius_cut",
                    "value": "",
                    "required": True,
                    "default": ""
                }
            ]
        )

        # Приводим элементы к конкретным типам для IDE и mypy
        from typing import cast
        combo_ctrl = cast(wx.ComboBox, controls[0])
        radius_ctrl = cast(wx.TextCtrl, controls[1])

        # ------------------------
        # Функция безопасного получения значения ComboBox
        # ------------------------
        def get_combo_value(ctrl: wx.ComboBox) -> str:
            idx = ctrl.GetSelection()
            return ctrl.GetString(idx) if idx != wx.NOT_FOUND else ""

        # Вызываем один раз на старте, чтобы корректно выставить состояние
        combo_ctrl.SetSelection(cut_options.index(loc.get("round")))
        wx.CallAfter(self.clear_fields)

        self.Layout()

    def clear_fields(self):
        """Сброс всех полей панели выреза к значениям по умолчанию."""
        for name in ["height_cut", "length_cut", "radius_cut", "cutout_label"]:
            field = self.form.fields.get(name)
            if field:
                field.set_value(field.default)


    def get_data(self) -> dict | None:
        """
        Возвращает словарь параметров выреза в формате:
            {"cutout": {"height_cut": float, "length_cut": float, "radius_cut": float}}

        radius корректируется в зависимости от выбранного типа выреза:
            cut: 0
            round: >0
            chamfer: <0 (отрицательное значение)

        Если высота или длина некорректны (0, None, пустая строка) — возвращается None.
        """
        if not self:
            return None

        def safe_float(ctrl_name):
            field = self.form.fields.get(ctrl_name)
            if not field:
                return None
            try:
                return float(field.get_value() or 0)
            except (TypeError, ValueError):
                return None

        height = safe_float("height_cut")
        length = safe_float("length_cut")
        radius = safe_float("radius_cut")

        cut_type_ctrl = self.form.fields.get("cutout_label")
        cut_type = cut_type_ctrl.get_value().lower() if cut_type_ctrl else ""

        round_str = loc.get("round").lower()
        chamber_str = loc.get("chamber").lower()

        if cut_type == round_str:
            radius = abs(radius) if radius is not None else 0
        elif cut_type == chamber_str:
            radius = -abs(radius) if radius is not None else 0
        else:
            radius = 0

        if height is None or length is None:
            return None

        return {
            "cutout": {
                "height_cut": height,
                "length_cut": length,
                "radius_cut": radius
            }
        }


class BracketSpecificPanel(wx.Panel):
    """
    Панель специфических параметров мостика.
    Управляет доступностью полей и собирает сырые данные для дальнейшей обработки.
    """

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
        Создает контролы с учётом специфик каждого типа.
        """
        self.bridge_type = bridge_type
        self.fields_sizer.Clear(True)
        self.controls.clear()

        fb = FieldBuilder(parent=self, target_sizer=self.fields_sizer, form=self.form)
        box_sizer = fb.static_box(loc.get("special_parameters"))
        fb_box = FieldBuilder(parent=self, target_sizer=box_sizer, form=self.form)

        # --- Type 1 ---
        if bridge_type == "type1":
            fb_box.universal_row(
                loc.get("add_detail_number"),
                [{"type": "text", "name": "add_detail_number", "value": "", "required": True, "default": ""}]
            )
            fb_box.universal_row(
                loc.get("length"),
                [{"type": "text", "name": "length", "value": "", "required": True, "default": ""}]
            )
            fb_box.universal_row(
                loc.get("web_height"),
                [{"type": "text", "name": "web_height", "value": "", "required": True, "default": ""}]
            )

            corner_options = [loc.get("round"), loc.get("chamber")]
            fb_box.universal_row(
                loc.get("corner_label"),
                [
                    {"type": "combo", "name": "corner_options", "value": "", "choices": corner_options, "required": True, "default": corner_options[0]},
                    {"type": "text", "name": "corner_radius", "value": "", "required": True, "default": ""}
                ]
            )

        # --- Type 2 / 4 ---
        elif bridge_type in ("type2", "type4"):
            fb_box.universal_row(
                loc.get("shell_diameter"),
                [{"type": "text", "name": "shell_diameter1", "value": "", "required": True, "default": ""}]
            )
            length_option = ["L", "L0"]

            fb_box.universal_row(
                loc.get("length"),
                [
                    {
                        "type": "combo",
                        "name": "length_option",
                        "value": length_option[0],
                        "choices": length_option,
                        "required": True,
                        "default": length_option[0],
                        "style": wx.CB_READONLY  # запрет ручного ввода
                    },
                    {
                        "type": "text",
                        "name": "length",
                        "value": "",
                        "required": True,
                        "default": ""
                    }
                ]
            )

        # --- Type 3 ---
        elif bridge_type == "type3":
            fb_box.universal_row(
                loc.get("shell_diameter"),
                [{"type": "text", "name": "shell_diameter1", "value": "", "required": True, "default": ""}]
            )
            fb_box.universal_row(
                loc.get("length_label"),
                [{"type": "text", "name": "length", "value": "", "required": True, "default": ""}]
            )
            fb_box.universal_row(
                loc.get("length1"),
                [{"type": "combo", "name": "l1", "value": "", "choices": [loc.get("no")], "required": True, "default": loc.get("no")}]
            )
            fb_box.universal_row(
                loc.get("edge_angle_label"),
                [{"type": "combo", "name": "edge_angle", "value": "", "choices": ["90", "120"], "required": True, "default": "90"}]
            )

        # --- Type 5 ---
        elif bridge_type == "type5":
            fb_box.universal_row(
                loc.get("shell_diameter1"),
                [{"type": "text", "name": "shell_diameter1", "value": "", "required": True, "default": ""},
                    {
                        "type": "button",
                        "label": loc.get("calculate"),
                        "callback": self.on_calculate_cone_forward,
                        "bg_color": "#008080",
                        "toggle": False
                    },
                ]
            )
            fb_box.universal_row(
                loc.get("shell_diameter2"),
                [{"type": "text", "name": "shell_diameter2", "value": "", "required": True, "default": ""},
                     {
                         "type": "button",
                         "label": loc.get("calculate"),
                         "callback": self.on_calculate_cone_reverse,
                         "bg_color": "#008080",
                         "toggle": False
                     },
                 ]
            )

            length_option1 = ["L", "L2"]
            fb_box.universal_row(
                loc.get("length"),
                [
                    {"type": "combo", "name": "length_option", "value": length_option1[0], "choices": length_option1, "required": True, "default": length_option1[0]},
                    {"type": "text", "name": "length", "value": "", "required": True, "default": ""}
                ]
            )
            length_option2 = ["L1", loc.get("no")]
            fb_box.universal_row(
                loc.get("length"),
                [
                    {"type": "combo", "name": "length_option1", "value": length_option2[0], "choices": length_option2, "required": True, "default": length_option2[0]},
                    {"type": "text", "name": "l1", "value": "", "required": True, "default": ""}
                ]
            )
            fb_box.universal_row(
                loc.get("edge_angle_label"),
                [{"type": "combo", "name": "edge_angle", "value": "", "choices": ["90", "120"], "required": True, "default": "90"}]
            )

        apply_styles_to_panel(self)
        self.Layout()

    def on_calculate_cone_forward(self, event):
        self._open_cone_dialog(mode="forward")

    def on_calculate_cone_reverse(self, event):
        self._open_cone_dialog(mode="reverse")

    def on_select_diameter(self, event):

        dlg = ConeOffsetDialog(self, self.form)

        if dlg.ShowModal() == wx.ID_OK:
            d_outer = dlg.get_result()
            if d_outer:
                self.form.set_value("shell_diameter1", f"{d_outer:.3f}")

        dlg.Destroy()

    def _open_cone_dialog(self, mode: str):

        raw = self.form.collect()

        try:
            width = parse_float(raw.get("width"))
            thickness = parse_float(raw.get("thickness"))
        except (TypeError, ValueError):
            show_popup(
                message=loc.get("invalid_number_format_error"),
                popup_type="error"
            )
            return

        dlg = ConeOffsetDialog(
            parent=self,
            width=width,
            thickness=thickness
        )

        if dlg.ShowModal() == wx.ID_OK:
            d1, d2 = dlg.get_result()

            if mode == "forward":
                self.form.set_value("shell_diameter1", f"{d1:.3f}")
                self.form.set_value("shell_diameter2", f"{d2:.3f}")
            else:
                self.form.set_value("shell_diameter2", f"{d1:.3f}")
                self.form.set_value("shell_diameter1", f"{d2:.3f}")

        dlg.Destroy()

    def get_specific_data(self, geometry: dict) -> dict | None:
        """
        Формирует единый словарь 'specific' с ключами для всех типов мостиков.
        Поля, не актуальные для данного типа, остаются пустыми или 0.

        Args:
            geometry (dict): {"width": float, "height": float} — размеры мостика.

        Returns:
            dict | None: {"specific": {...}} или None при ошибке валидации.

        Ключи словаря:
            length (float) — общая длина площадки мостика (отступ L), для всех типов.
            corner_radius (float) — радиус скругления углов мостика, только type1.
            add_detail_number (str) — дополнительный номер детали, type1.
            web_height (float) — высота перемычки (type1), если отличается от geometry["height"].
            shell_diameter1 (float) — основной диаметр обечайки, type2/3/4/5.
            shell_diameter2 (float) — второй диаметр (если требуется), type5.
            edge_angle (float) — угол раскрытия/скоса боковин, type3 и type5.
            variant (int) — вариант набора исходных данных, type3 и type5.
            l1 (float) — дополнительная длина L1, type3 и type5.
            l2 (float) — дополнительная длина L2, type5.
            Будущее развитие (закомментировано): cone_top_offset, cone_length, cone_diameter_top, cone_diameter_bottom.
        """
        if not self.bridge_type:
            show_popup(
                message=loc.get("bridge_type_not_selected"),
                popup_type="error"
            )
            return None

        raw = self.form.collect()

        specific = {
            "length": 0.0,
            "corner_radius": 0.0,
            "add_detail_number": "",
            "web_height": 0.0,
            "shell_diameter1": 0.0,
            "shell_diameter2": 0.0,
            "edge_angle": 0.0,
            "variant": 0,
            "l1": 0.0,
            "l2": 0.0,
        }

        try:
            # --- Тип 1 ---
            if self.bridge_type == "type1":
                specific["add_detail_number"] = raw.get("add_detail_number", "").strip()
                specific["length"] = parse_float(raw.get("length"))
                specific["web_height"] = self._require_positive_float(raw, "web_height", "Высота перемычки должна быть > 0")
                corner_type = raw.get("corner_options")
                try:
                    corner_radius = parse_float(raw.get("corner_radius"))
                except (TypeError, ValueError):
                    raise ValidationError(loc.get("invalid_number_format_error"))
                specific["corner_radius"] = corner_radius
                if corner_type == loc.get("round"):
                    specific["corner_radius"] = abs(corner_radius)
                elif corner_type == loc.get("chamber"):
                    specific["corner_radius"] = -abs(corner_radius)
                else:
                    raise ValidationError("Неверный тип угла для мостика")

            # --- Тип 2 / 4 ---
            elif self.bridge_type in ("type2", "type4"):

                diameter = self._require_positive_float(
                    raw,
                    "shell_diameter1",
                    loc.get("diameter_positive_error")
                )

                length_input = self._require_positive_float(
                    raw,
                    "length",
                    loc.get("length_positive_error")
                )

                length_option = raw.get("length_option")

                try:
                    width = parse_float(geometry.get("width"))
                except (TypeError, ValueError):
                    raise ValidationError(loc.get("invalid_width_error"))

                radius = diameter / 2.0

                if width > diameter:
                    raise ValidationError(loc.get("width_exceeds_diameter"))

                if length_option == "L":
                    specific["length"] = length_input

                elif length_option == "L0":
                    under_root = math.sqrt(radius ** 2 - (width ** 2) / 4.0)

                    if under_root < 0:
                        raise ValidationError(loc.get("geometry_compensation_error"))

                    delta = radius - (under_root ** 0.5)
                    specific["length"] = length_input + delta

                else:
                    raise ValidationError(loc.get("invalid_length_option"))

                specific["shell_diameter1"] = diameter

            # --- Тип 3 ---
            elif self.bridge_type == "type3":
                specific["shell_diameter1"] = self._require_positive_float(raw, "shell_diameter1", "Диаметр > 0")
                specific["edge_angle"] = parse_float(raw.get("edge_angle"))
                if specific["edge_angle"] not in (90.0, 120.0):
                    raise ValidationError(loc.get("invalid_angle_error"))
                if specific["l1"] == "no":
                    specific["l1"] = 0.0
                else:
                    specific["l1"] = parse_float(raw.get("l1"))
                # specific["variant"] = 1 if specific["l1"] > 0 else 0

            # --- Тип 5 ---
            elif self.bridge_type == "type5":
                specific["shell_diameter1"] = self._require_positive_float(raw, "shell_diameter1", "Диаметр1 > 0")
                d2_raw = raw.get("shell_diameter2")
                if d2_raw:
                    d2 = parse_float(d2_raw)
                    if d2 > 0:
                        specific["shell_diameter2"] = d2
                specific["edge_angle"] = parse_float(raw.get("edge_angle"))
                if specific["edge_angle"] not in (90.0, 120.0):
                    raise ValidationError(loc.get("invalid_angle_error"))

                L = parse_float(raw.get("length"))
                L1 = parse_float(raw.get("l1"))
                length_option = raw.get("length_option")
                length_option1 = raw.get("length_option1")

                if length_option == "L" and length_option1 == "L1":
                    specific["variant"] = 1
                    specific["length"] = L
                    specific["l1"] = L1
                elif length_option == "L" and length_option1 == loc.get("no"):
                    specific["variant"] = 2
                    specific["length"] = L
                elif length_option == "L2":
                    L2 = parse_float(raw.get("length"))
                    specific["variant"] = 3
                    specific["l2"] = L2
                    specific["l1"] = L1

                if specific["l1"] is None:
                    specific["l1"] = 0.0
                if specific["l2"] is None:
                    specific["l2"] = 0.0

        except ValidationError as e:
            show_popup(
                message=str(e),
                title=loc.get("validation_error"),
                popup_type="error"
            )

            return None

        return {"specific": specific}

    @staticmethod
    def _require_positive_float(raw, key, message):
        """
        Преобразует значение из raw в положительное float, иначе выбрасывает ValidationError.
        """
        value_raw = raw.get(key)

        try:
            value = parse_float(value_raw)
        except ValueError:
            raise ValidationError(loc.get("invalid_number_format_error"))

        if value is None or value <= 0:
            raise ValidationError(message)

        return value
#---------------------------------------------------------
# TODO ConeOffsetDialog
# Класс совсем недоделан!
# --------------------------------------------------------

class ConeOffsetDialog(wx.Dialog):

    def __init__(self, parent, width: float, thickness: float):
        super().__init__(parent, title=loc.get("diameter_dialog_title"))

        self.width = width
        self.thickness = thickness
        self.result = None

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # --- Левая часть (картинка)
        # bmp = wx.Bitmap(BRACKET5_IMAGE_PATH, wx.BITMAP_TYPE_ANY)
        # left = wx.StaticBitmap(self, bitmap=bmp)
        left = wx.StaticBitmap(self)
        main_sizer.Add(left, 0, wx.ALL, 10)

        # --- Правая часть
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # D1
        self.d1 = wx.TextCtrl(self)
        self.d1_type = wx.ComboBox(
            self,
            choices=[
                loc.get("diameter_type_inner"),
                loc.get("diameter_type_middle"),
                loc.get("diameter_type_outer"),
            ],
            style=wx.CB_READONLY
        )
        self.d1_type.SetSelection(0)

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        row1.Add(wx.StaticText(self, label=loc.get("shell_diameter1")), 0, wx.RIGHT, 5)
        row1.Add(self.d1, 1, wx.RIGHT, 5)
        row1.Add(self.d1_type, 0)
        right_sizer.Add(row1, 0, wx.ALL | wx.EXPAND, 5)

        # D2
        self.d2 = wx.TextCtrl(self)
        self.d2_type = wx.ComboBox(
            self,
            choices=[
                loc.get("diameter_type_inner"),
                loc.get("diameter_type_middle"),
                loc.get("diameter_type_outer"),
            ],
            style=wx.CB_READONLY
        )
        self.d2_type.SetSelection(0)

        row2 = wx.BoxSizer(wx.HORIZONTAL)
        row2.Add(wx.StaticText(self, label=loc.get("shell_diameter2")), 0, wx.RIGHT, 5)
        row2.Add(self.d2, 1, wx.RIGHT, 5)
        row2.Add(self.d2_type, 0)
        right_sizer.Add(row2, 0, wx.ALL | wx.EXPAND, 5)

        # L
        self.length = wx.TextCtrl(self)
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        row3.Add(wx.StaticText(self, label=loc.get("length")), 0, wx.RIGHT, 5)
        row3.Add(self.length, 1)
        right_sizer.Add(row3, 0, wx.ALL | wx.EXPAND, 5)

        # L1
        self.length1 = wx.TextCtrl(self)
        row4 = wx.BoxSizer(wx.HORIZONTAL)
        row4.Add(wx.StaticText(self, label=loc.get("length1")), 0, wx.RIGHT, 5)
        row4.Add(self.length1, 1)
        right_sizer.Add(row4, 0, wx.ALL | wx.EXPAND, 5)

        # Кнопки
        btn_sizer = wx.StdDialogButtonSizer()

        ok_btn = wx.Button(self, wx.ID_OK, loc.get("ok_button"))
        clear_btn = wx.Button(self, wx.ID_CLEAR, loc.get("clear_button"))
        cancel_btn = wx.Button(self, wx.ID_CANCEL, loc.get("cancel_button"))

        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(clear_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()

        right_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        main_sizer.Add(right_sizer, 1, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(main_sizer)
        self.Fit()

        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)

    def on_clear(self, event):
        self.d1.SetValue("")
        self.d2.SetValue("")
        self.length.SetValue("")
        self.length1.SetValue("")

    def on_ok(self, event):
        try:
            d1 = float(self.d1.GetValue())
            d2 = float(self.d2.GetValue())
            L = float(self.length.GetValue())
            L1 = float(self.length1.GetValue())
        except ValueError:
            show_popup(loc.get("invalid_number_format_error"), popup_type="error")
            return

        d1_new, d2_new = diameter_cone_offset(
            length=L,
            length1=L1,
            diameter1=d1,
            diameter2=d2
        )

        self.result = (d1_new, d2_new)
        self.EndModal(wx.ID_OK)


# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------
if __name__ == "__main__":

    app = wx.App(False)
    frame = wx.Frame(None, title="test_bracket_window", size=wx.Size(1500, 800))
    panel = BracketContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()