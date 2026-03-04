# Filename: content_nozzle.py
"""
Модуль содержит панель NozzleContentPanel для настройки параметров одиночного отвода
в приложении AT-CAD. Панель собирает данные и передает их через callback в вызывающую
часть приложения (например, в программу построения отвода).

Функциональность:
- UI по образцу окна обечайки (ShellContentPanel)
- Сбор данных в словарь:
    {
        "insert_point": PointVariant | None,
        "diameter": float,
        "diameter_main": float,
        "length": float,
        "axis": bool,
        "axis_marks": float,
        "layer_name": "0",
        "thickness": float,
        "order_number": str,
        "detail_number": str,
        "material": str,
        "weld_allowance": float,
        "accuracy": int,
        "offset": float,
        "thk_correction": bool,
        "mode": str
    }
- Тестовый запуск в конце файла (аналогично shell_content_panel.py)
- Поддержка динамической смены языка через update_ui_language()
- Минимальная валидация полей
- Возможность ввода пользовательского значения accuracy (editable ComboBox)
"""
from pprint import pprint

import wx
from typing import Optional, Dict, List
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_input import at_get_point
from windows.at_fields_builder import FormBuilder, FieldBuilder
from windows.at_window_utils import (
    CanvasPanel, show_popup, apply_styles_to_panel, BaseContentPanel,
    parse_float, load_common_data, update_status_bar_point_selected
)
from config.at_config import NOZZLE_IMAGE_PATH
from windows.at_content_registry import run_build

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "order_label": {"ru": "К-№", "de": "Auftrags-Nr.", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},
    "nozzle_params_label": {"ru": "Параметры отвода, мм", "de": "Stutzenparameter, mm", "en": "Nozzle Parameters, mm"},
    "diameter_label": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "diameter": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "diameter_main_label": {"ru": "Диаметр магистрали, D", "de": "Main Durchmesser, D", "en": "Main Diameter, D"},
    "length_label": {"ru": "Длина, L", "de": "Länge, L", "en": "Length, L"},
    "weld_allowance_label": {"ru": "Припуск на сварку, мм", "de": "Schweißnahtzugabe, mm", "en": "Weld Allowance, mm"},
    "offset_label": {"ru": "Смещение, O", "de": "Versatz, O", "en": "Offset, O"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "mode_bulge": {"ru": "Дуги", "de": "Bogen", "en": "Bulge"},
    "mode_polyline": {"ru": "Полилиния", "de": "Polylinie", "en": "Polyline"},
    "mode_spline": {"ru": "Сплайн", "de": "Spline", "en": "Spline"},
    "accuracy_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Accuracy (points)"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "axis_checkbox": {"ru": "Показать оси на чертеже", "de": "Achsen zeichnen", "en": "Draw axes"},
    "axis_marks_label": {"ru": "Метки осей, мм", "de": "Achsenmarken, mm", "en": "Axis marks, mm"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "point_prompt": {"ru": "Укажите точку вставки развертки отвода", "de": "Geben Sie einen Punkt der Abwicklung an", "en": "Select the point"},
    "point_selection_error": {"ru": "Точка не выбрана", "de": "Punkt nicht gewählt", "en": "Point not selected"},
    "yes_label": {"ru": "Да", "de": "Ja", "en": "Yes"},
    "no_label": {"ru": "Нет", "de": "Nein", "en": "No"},
    "external_diameter_label": {"ru": "Внешний", "de": "Außen", "en": "External"},
    "middle_diameter_label": {"ru": "Средний", "de": "Mitte", "en": "Middle"},
    "internal_diameter_label": {"ru": "Внутренний", "de": "Innen", "en": "Internal"},
    "build_conditions_label": {"ru": "Условия построения", "de": "Bau-Bedingungen", "en": "Build Conditions"},
}
loc.register_translations(TRANSLATIONS)

# Значения по умолчанию
default_allowances = ["0", "1", "2", "3", "4", "5", "10", "20"]
default_axis_marks = ["0", "10", "20"]
default_modes = ["mode_bulge", "mode_polyline", "mode_spline"]

# Рекомендуемые наборы значений accuracy по режимам
ACCURACY_OPTIONS: Dict[str, List[str]] = {
    "bulge": ["18", "24", "30", "36"],          # баланс точности/производительности
    "polyline": ["360", "480", "600", "720"],   # полилиния — много точек
    "spline": ["24", "36", "48", "72"],         # сплайн — умеренно
}

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    return NozzleContentPanel(parent)


class NozzleContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров одиночного отвода.
    """
    def __init__(self, parent, callback=None):

        super().__init__(parent)
        self.fb = None
        self.canvas = None
        self.right_sizer = None
        self.left_sizer = None
        self.form = None
        self.diameter_input = None
        self.thickness_combo = None
        self.material_combo = None
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None

        # Виджеты
        self.mode_combo: Optional[wx.ComboBox] = None
        self.accuracy_combo: Optional[wx.ComboBox] = None
        self.diameter_main_input: Optional[wx.TextCtrl] = None
        self.weld_allowance_input: Optional[wx.ComboBox] = None
        self.offset_input: Optional[wx.TextCtrl] = None
        self.diameter_type_choice: Optional[wx.Choice] = None
        self.axis_combo: Optional[wx.ComboBox] = None

        self.setup_ui()

    def setup_ui(self):
        self.Freeze()
        try:
            if self.GetSizer():
                self.GetSizer().Clear(True)

            self.form = FormBuilder(self)

            # -----------------------------
            # Загрузка общих данных
            # -----------------------------
            common_data = load_common_data()
            material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
            thickness_options = common_data.get("thicknesses", [])

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer = wx.BoxSizer(wx.VERTICAL)

            # Левый блок (изображение и кнопки)
            image_path = str(NOZZLE_IMAGE_PATH)
            self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
            self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

            # Правый блок (поля ввода)
            self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

            # =============================
            # Основные данные
            # =============================
            main_data_sizer = self.fb.static_box(loc.get("main_data_label", "Основные данные"))
            fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

            # Номер заказа и номер детали
            fb_main.universal_row(
                "order_label",
                [
                    {"type": "text", "name": "order_input", "value": "", "required": False, "default": ""},
                    {"type": "text", "name": "detail_input", "value": "", "required": False, "default": ""},
                ]
            )
            # Материал
            fb_main.universal_row(
                "material_label",
                [
                    {"type": "combo",
                     "name": "material_combo",
                     "choices": material_options,
                     "value": material_options[0],
                     "required": True,
                     "default": material_options[0],
                     "size": (310, -1),
                     "readonly": False
                     }
                ]
            )

            # Толщина
            fb_main.universal_row(
                "thickness_label",
                [
                    {"type": "combo", "name": "thickness_combo", "choices": thickness_options, "value": "", "required": True, "default": "3"}
                ]
            )

            # --- Параметры отвода ---
            nozzle_sizer = self.fb.static_box(loc.get("nozzle_params_label", "Параметры отвода"))
            fb_nozzle = FieldBuilder(parent=self, target_sizer=nozzle_sizer, form=self.form)

            # Диаметр отвода
            choices = [
                        loc.get("external_diameter_label", "Внешний"),
                        loc.get("middle_diameter_label", "Средний"),
                        loc.get("internal_diameter_label", "Внутренний"),
                    ]

            fb_nozzle.universal_row(
                "diameter_label",
                [
                    {"type": "text", "name": "diameter", "value": "", "required": False, "default": "" },
                    {"type": "combo",
                     "name": "diameter_type_choice",
                     "choices": choices,
                     "value": choices[0],
                     "required": True,
                     "default": choices[0],
                     "readonly": True
                     }
                ]
            )

            # Диаметр магистрали
            fb_nozzle.universal_row(
                "diameter_main_label",
                [
                    {
                        "type": "text",
                        "name": "diameter_main_input",
                        "value": "",
                        "required": True,
                        "default": ""
                    }
                ]
            )

            # Длина
            fb_nozzle.universal_row(
                "length_label",
                [
                    {
                        "type": "text",
                        "name": "length_input",
                        "value": "",
                        "required": True,
                        "default": ""
                    }
                ]
            )

            # Смещение
            fb_nozzle.universal_row(
                "offset_label",
                [
                    {
                        "type": "text",
                        "name": "offset_input",
                        "value": "0",
                        "required": False,
                        "default": "0"
                    }
                ]
            )

            # --- Условия построения ---
            build_sizer = self.fb.static_box(loc.get("build_conditions_label", "Условия построения"))
            fb_build = FieldBuilder(parent=self, target_sizer=build_sizer, form=self.form)

            # Режим построения
            fb_build.universal_row(
                "mode_label",
                [
                    {
                        "type": "combo",
                        "name": "mode_combo",
                        "choices": [loc.get(mode, mode) for mode in default_modes],
                        "value": loc.get("mode_bulge", "Bulge"),
                        "required": True,
                        "default": loc.get("mode_bulge", "Bulge"),
                        "readonly": True,
                        "bind": {
                            "event": wx.EVT_COMBOBOX,
                            "handler": self.on_mode_change
                        }
                    }
                ]
            )

            # Точность
            fb_build.universal_row(
                "accuracy_label",
                [
                    {
                        "type": "combo",
                        "name": "accuracy_combo",
                        "choices": ACCURACY_OPTIONS["bulge"],
                        "value": "24",
                        "required": True,
                        "default": "24",
                        "readonly": False,
                    }
                ]
            )

            # Припуск на сварку
            fb_build.universal_row(
                "weld_allowance_label",
                [
                    {
                        "type": "combo",
                        "name": "weld_allowance_input",
                        "choices": default_allowances,
                        "value": "0",
                        "required": False,
                        "default": "0",
                        "readonly": False,
                    }
                ]
            )

            # Показать оси (замена CheckBox на ComboBox)
            fb_build.universal_row(
                "axis_checkbox",
                [
                    {
                        "type": "combo",
                        "name": "axis_combo",
                        "choices": [
                            loc.get("yes_label", "Да"),
                            loc.get("no_label", "Нет")
                        ],
                        "value": loc.get("yes_label", "Да"),
                        "required": True,
                        "default": loc.get("yes_label", "Да"),
                        "readonly": True
                    }
                ]
            )

            # Метки осей
            fb_build.universal_row(
                "axis_marks_label",
                [
                    {
                        "type": "combo",
                        "name": "axis_marks_input",
                        "choices": default_axis_marks,
                        "value": "0",
                        "required": False,
                        "default": "0",
                        "readonly": False,
                    }
                ]
            )

            self.right_sizer.AddStretchSpacer()
            self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

            main_sizer.Add(self.left_sizer, 1, wx.EXPAND) # Левый блок растягивается, чтобы занять больше пространства
            main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10) # Правый блок фиксированного размера с отступами

            self.SetSizer(main_sizer)
            apply_styles_to_panel(self)

            self.form.clear()
            self.on_mode_change()
            self.Layout()
        finally:
            self.Thaw()



    # ----------------------------------------------------------------
    # Обработчики событий
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    # Обработчик смены режима построения
    # ----------------------------------------------------------------
    def on_mode_change(self, _event: Optional[wx.Event] = None) -> None:
        """
        Обновляет список значений точности (accuracy_combo)
        в зависимости от выбранного режима построения.

        Логика:
        0 -> bulge
        1 -> polyline
        2 -> spline

        Используется индекс выбора, а не текст,
        чтобы исключить ошибки локализации.
        """

        # Получаем поля из FormBuilder
        mode_field = self.form.fields.get("mode_combo")
        acc_field = self.form.fields.get("accuracy_combo")

        if mode_field is None or acc_field is None:
            return

        mode_ctrl = mode_field.ctrl
        accuracy_ctrl = acc_field.ctrl

        # Проверка типов контролов
        if not isinstance(mode_ctrl, wx.ComboBox):
            return

        if not isinstance(accuracy_ctrl, wx.ComboBox):
              return

        # Получаем индекс выбранного режима
        selection_index: int = mode_ctrl.GetSelection()

        # Маппинг по индексу (жёстко и надёжно)
        index_mode_map: Dict[int, str] = {
            0: "bulge",
            1: "polyline",
            2: "spline",
        }

        # Если индекс некорректный — выходим
        if selection_index not in index_mode_map:
            return

        selected_mode: str = index_mode_map[selection_index]

        # Получаем набор точностей для режима
        options: List[str] = ACCURACY_OPTIONS[selected_mode]

        # Сохраняем текущее значение, если оно ещё допустимо
        current_value: str = accuracy_ctrl.GetValue()

        # Обновляем список значений
        accuracy_ctrl.Set(options)

        # Если текущее значение допустимо — оставить
        if current_value in options:
            accuracy_ctrl.SetValue(current_value)
        else:
            # иначе выставить первое значение
            accuracy_ctrl.SetValue(options[0])

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": запрашивает точку вставки и передает данные в callback.

        Аргументы:
            event: Событие wxPython.
        """
        try:
            # Собираем данные из полей
            data = self.get_data()

            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Сворачиваем окно перед выбором точки
            main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = at_get_point(
                cad.document,
                prompt=loc.get("point_prompt", "Укажите точку вставки развертки отвода"),
                as_variant=False
            )

            # Разворачиваем окно обратно
            main_window.Iconize(False)
            main_window.Raise()
            main_window.SetFocus()

            if not pt:
                show_popup(loc.get("point_selection_error", "Точка не выбрана"), popup_type="error")
                return

            # Сохраняем точку и обновляем словарь
            self.insert_point = pt
            data["insert_point"] = pt

            # Debug
            pprint(data)

            # Передаем данные дальше через callback или run_build
            if self.on_submit_callback:
                self.on_submit_callback(data)
            else:
                run_build("nozzle", data)

        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")

    def on_cancel(self, event):
        parent = wx.GetTopLevelParent(self)
        if hasattr(parent, "switch_content"):
            parent.switch_content("content_apps")

    def on_clear(self, event):
        self.form.clear()
        self.insert_point = None
        update_status_bar_point_selected(self, None)

    # ----------------------------------------------------------------
    # Сбор данных
    # ----------------------------------------------------------------

    def get_data(self) -> Optional[Dict]:
        """
        Собирает данные из полей ввода в словарь.

        Returns:
            Словарь с данными или None в случае ошибки.
        """
        try:
            data = self.form.collect()

            if not data:
                show_popup(loc.get("no_data_error"), popup_type="error")
                return None

            # Маппинг типа диаметра
            diameter_type_map = {
                0: "outer",
                1: "middle",
                2: "inner"
            }
            flag = diameter_type_map.get(data["diameter_type_choice"], "outer")

            # Парсинг числовых полей
            diameter = parse_float(data["diameter"])
            if diameter is None or diameter <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр отвода, d")), popup_type="error")
                return None

            thickness = parse_float(data["thickness_combo"])
            if thickness is None or thickness < 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("thickness_label", "Толщина, S")),
                    popup_type="error")
                return None

            # Вычисление среднего диаметра через at_diameter
            middle_diameter = at_diameter(diameter, thickness, flag)

            diameter_main = parse_float(data["diameter_main_input"])
            if diameter_main is None or diameter_main <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_main_label", "Диаметр магистрали, D")), popup_type="error")
                return None

            length = parse_float(data["length_input"])
            if length is None or length <= 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("length_label", "Длина, L")),
                    popup_type="error")
                return None

            axis_marks = parse_float(data["axis_marks_input"]) or 0.0
            weld_allowance = parse_float(data["weld_allowance_input"]) or 0.0
            accuracy = parse_float(data["accuracy_combo"])
            if accuracy is None or accuracy < 4:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("accuracy_label", "Точность (точек)")), popup_type="error")
                return None
            offset = parse_float(data["offset_input"]) or 0.0

            mode_map = {
                loc.get("mode_bulge", "Bulge"): "bulge",
                loc.get("mode_polyline", "Polyline"): "polyline",
                loc.get("mode_spline", "Spline"): "spline",
            }

            # Маппинг значения axis_combo
            axis_value = data["axis_combo"] == loc.get("yes_label", "Да")

            return {
                "insert_point": self.insert_point,
                "diameter": middle_diameter,
                "diameter_main": diameter_main,
                "length": length,
                "axis": axis_value,
                "axis_marks": axis_marks,
                "layer_name": "0",
                "thickness": thickness,
                "order_number": data["order_input"],
                "detail_number": data["detail_input"],
                "material": data["material_combo"],
                "weld_allowance": weld_allowance,
                "accuracy": int(accuracy),
                "offset": offset,
                "thk_correction": False,
                "mode": mode_map.get(data["mode_combo"], "bulge")
            }
        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")
            return None

# ----------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title="Test NozzleContentPanel", size=wx.Size(1000, 800))
    panel = NozzleContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()