# Filename: content_cone_pipe.py
"""
Модуль построения линии пересечения конусного отвода на трубе
"""

import wx
from typing import Optional, Dict, List
from pathlib import Path

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_input import at_get_point
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, BaseContentPanel,
    parse_float, load_common_data, style_label, style_textctrl,
    style_combobox, style_radiobutton, style_staticbox, update_status_bar_point_selected
)
from config.at_config import CONE_PIPE_IMAGE_PATH
from windows.at_content_registry import run_build

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main Data"},
    "order_label": {"ru": "К-№", "de": "Auftrags-Nr.", "en": "Order No."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина, S", "de": "Dicke, S", "en": "Thickness, S"},
    "nozzle_params_label": {"ru": "Параметры отвода", "de": "Stutzenparameter", "en": "Nozzle Params"},
    "diameter_label": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "diameter": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "chorda_label": {"ru": "Длина хорды, db", "de": "Chorda Länge, db", "en": "Chord length, db"},
    "diameter_main_label": {"ru": "Диаметр магистрали, D", "de": "Main Durchmesser, D", "en": "Main Diameter, D"},
    "height_label": {"ru": "Высота, H", "de": "Höhe, H", "en": "Height, H"},
    "weld_allowance_label": {"ru": "Припуск на сварку", "de": "Schweißnahtzugabe", "en": "Weld Allowance"},
    "accuracy_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Accuracy (points)"},
    "additional_label": {"ru": "Доп. условия", "de": "Zusatzbedingungen", "en": "Additional"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "point_prompt": {"ru": "Укажите точку вставки", "de": "Geben Sie ein Punkt für Abwicklung", "en": "Select nozzle point"},
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

# Рекомендуемые наборы значений accuracy по режимам
ACCURACY_OPTIONS = {
    "polyline": ["360", "480", "600", "720"]   # полилиния — много точек
}

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    return ConePipeContentPanel(parent)


class ConePipeContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров конусного отвода
    """
    def __init__(self, parent, callback=None):

        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = {}
        self.insert_point = None

        # Виджеты
        self.accuracy_combo: Optional[wx.ComboBox] = None
        self.diameter_main_input: Optional[wx.TextCtrl] = None
        self.weld_allowance_input: Optional[wx.ComboBox] = None
        self.diameter_type_choice: Optional[wx.Choice] = None

        self.setup_ui()
        self.order_input.SetFocus()

    def setup_ui(self):
        if self.GetSizer():
            self.GetSizer().Clear(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок (изображение и кнопки)
        image_path = str(CONE_PIPE_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Правый блок (поля ввода)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        field_size = (120, -1)  # ширина 150, высота автоматическая

        # --- Основные данные ---
        main_data_box = wx.StaticBox(self, label=loc.get("main_data_label", "Основные данные"))
        style_staticbox(main_data_box)
        self.static_boxes["main_data"] = main_data_box
        main_data_sizer = wx.StaticBoxSizer(main_data_box, wx.VERTICAL)

        # строка: К-№ и Деталь
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["order"] = wx.StaticText(main_data_box, label=loc.get("order_label", "К-№"))
        style_label(self.labels["order"])
        self.order_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.order_input)
        self.detail_input = wx.TextCtrl(main_data_box, value="", size=field_size)
        style_textctrl(self.detail_input)
        row1.Add(self.labels["order"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row1.AddStretchSpacer()
        row1.Add(self.order_input, 0, wx.RIGHT, 10)
        row1.Add(self.detail_input, 0)
        main_data_sizer.Add(row1, 0, wx.EXPAND | wx.ALL, 5)

        # Загрузка общих данных
        common_data = load_common_data()
        material_options = [mat["name"] for mat in common_data.get("material", []) if mat.get("name")]
        thickness_options = common_data.get("thicknesses", [])
        default_thickness = "5" if "5" in thickness_options or "5.0" in thickness_options else (thickness_options[0] if thickness_options else "")

        # строка: Материал
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["material"] = wx.StaticText(main_data_box, label=loc.get("material_label", "Материал"))
        style_label(self.labels["material"])
        self.material_combo = wx.ComboBox(
            main_data_box,
            choices=material_options,
            value=material_options[0] if material_options else "",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.material_combo)
        row2.Add(self.labels["material"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row2.AddStretchSpacer()
        row2.Add(self.material_combo, 0)
        main_data_sizer.Add(row2, 0, wx.EXPAND | wx.ALL, 5)

        # строка: Толщина
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["thickness"] = wx.StaticText(main_data_box, label=loc.get("thickness_label", "Толщина, S"))
        style_label(self.labels["thickness"])
        self.thickness_combo = wx.ComboBox(
            main_data_box,
            choices=thickness_options,
            value=default_thickness,
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.thickness_combo)
        row3.Add(self.labels["thickness"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row3.AddStretchSpacer()
        row3.Add(self.thickness_combo, 0)
        main_data_sizer.Add(row3, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(main_data_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        # --- Параметры отвода ---
        nozzle_box = wx.StaticBox(self, label=loc.get("nozzle_params_label", "Параметры отвода"))
        style_staticbox(nozzle_box)
        self.static_boxes["nozzle_params"] = nozzle_box
        nozzle_sizer = wx.StaticBoxSizer(nozzle_box, wx.VERTICAL)

        # Диаметр верхнего основания отвода
        row_d = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter_top"] = wx.StaticText(nozzle_box, label=loc.get("diameter_label", "Диаметр, d"))
        style_label(self.labels["diameter_top"])
        self.diameter_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        row_d.Add(self.labels["diameter_top"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_d.Add(self.diameter_input, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Тип диаметра
        self.diameter_type_choice = wx.Choice(
            nozzle_box,
            choices=[
                loc.get("external_diameter_label", "Внешний"),
                loc.get("middle_diameter_label", "Средний"),
                loc.get("internal_diameter_label", "Внутренний"),
            ]
        )
        self.diameter_type_choice.SetMinSize(field_size)
        self.diameter_type_choice.SetInitialSize(field_size)
        self.diameter_type_choice.SetSelection(0)
        row_d.Add(self.diameter_type_choice, 1, wx.EXPAND)
        nozzle_sizer.Add(row_d, 0, wx.EXPAND | wx.ALL, 5)

        # Хорда пересечения db
        row_ch = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["chorda"] = wx.StaticText(nozzle_box, label=loc.get("chorda_label", "Длина хорды, db"))
        style_label(self.labels["chorda"])
        self.chorda_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.chorda_input)
        row_ch.Add(self.labels["chorda"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_ch.AddStretchSpacer()
        row_ch.Add(self.chorda_input, 0)
        nozzle_sizer.Add(row_ch, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр магистрали
        row_dm = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter_main"] = wx.StaticText(nozzle_box, label=loc.get("diameter_main_label", "Диаметр магистрали, D"))
        style_label(self.labels["diameter_main"])
        self.diameter_main_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.diameter_main_input)
        row_dm.Add(self.labels["diameter_main"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_dm.AddStretchSpacer()
        row_dm.Add(self.diameter_main_input, 0)
        nozzle_sizer.Add(row_dm, 0, wx.EXPAND | wx.ALL, 5)

        # Высота отвода
        row_h = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["height"] = wx.StaticText(nozzle_box, label=loc.get("height_label", "Высота, H"))
        style_label(self.labels["height"])
        self.height_input = wx.TextCtrl(nozzle_box, value="", size=field_size)
        style_textctrl(self.height_input)
        row_h.Add(self.labels["height"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_h.AddStretchSpacer()
        row_h.Add(self.height_input, 0)
        nozzle_sizer.Add(row_h, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(nozzle_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        # --- Условия построения ---
        build_box = wx.StaticBox(self, label=loc.get("build_conditions_label", "Условия построения"))
        style_staticbox(build_box)
        self.static_boxes["build_conditions"] = build_box
        build_sizer = wx.StaticBoxSizer(build_box, wx.VERTICAL)

        # Точность
        row_acc = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["accuracy"] = wx.StaticText(build_box, label=loc.get("accuracy_label", "Точность"))
        style_label(self.labels["accuracy"])
        self.accuracy_combo = wx.ComboBox(
            build_box,
            choices=ACCURACY_OPTIONS["polyline"],
            value="360",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.accuracy_combo)
        row_acc.Add(self.labels["accuracy"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_acc.AddStretchSpacer()
        row_acc.Add(self.accuracy_combo, 0)
        build_sizer.Add(row_acc, 0, wx.EXPAND | wx.ALL, 5)

        # Припуск на сварку
        row_weld = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["weld_allowance"] = wx.StaticText(build_box,
                                                      label=loc.get("weld_allowance_label", "Припуск на сварку"))
        style_label(self.labels["weld_allowance"])
        self.weld_allowance_input = wx.ComboBox(
            build_box,
            choices=default_allowances,
            value="0",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.weld_allowance_input)
        row_weld.Add(self.labels["weld_allowance"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_weld.AddStretchSpacer()
        row_weld.Add(self.weld_allowance_input, 0)
        build_sizer.Add(row_weld, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(build_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        self.right_sizer.AddStretchSpacer()
        self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND) # Левый блок растягивается, чтобы занять больше пространства
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10) # Правый блок фиксированного размера с отступами

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

    # ----------------------------------------------------------------
    # Обработчики событий
    # ----------------------------------------------------------------

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": запрашивает точку вставки и передает данные в callback.

        Аргументы:
            event: Событие wxPython.
        """
        try:
            # Собираем данные из полей
            data = self.get_data()
            if not data:
                return

            # Получаем главное окно
            main_window = wx.GetTopLevelParent(self)

            # Сворачиваем окно перед выбором точки
            main_window.Iconize(True)

            # Инициализация CAD и выбор точки
            cad = ATCadInit()
            pt = at_get_point(
                cad.document,
                prompt=loc.get("point_prompt", "Укажите точку вставки"),
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
        self.order_input.SetValue("")
        self.detail_input.SetValue("")
        self.diameter_input.SetValue("")
        self.diameter_main_input.SetValue("")
        self.height_input.SetValue("")
        self.material_combo.SetSelection(0 if self.material_combo.GetCount() > 0 else -1)
        self.thickness_combo.SetSelection(0 if self.thickness_combo.GetCount() > 0 else -1)
        self.weld_allowance_input.SetValue("0")
        self.accuracy_combo.SetValue("360")

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
            # Проверка комбобоксов
            if not self.material_combo.GetValue():
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("material_label", "Материал")),
                    popup_type="error")
                return None
            if not self.thickness_combo.GetValue():
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("thickness_label", "Толщина, S")),
                    popup_type="error")
                return None

            # Парсинг числовых полей
            diameter_top = parse_float(self.diameter_input.GetValue())
            if diameter_top is None or diameter_top <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр, d")), popup_type="error")
                return None

            thickness = parse_float(self.thickness_combo.GetValue())
            if thickness is None or thickness < 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("thickness_label", "Толщина, S")),
                    popup_type="error")
                return None

            chorda = parse_float(self.chorda_input.GetValue())
            if chorda is None or chorda < 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("chorda_label")), popup_type="error")
                return None

            diameter_main = parse_float(self.diameter_main_input.GetValue())
            if diameter_main is None or diameter_main <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_main_label", "Диаметр магистрали, D")), popup_type="error")
                return None

            height = parse_float(self.height_input.GetValue())
            if height is None or height <= 0:
                show_popup(
                    loc.get("invalid_input", "Некорректный ввод: {0}").format(loc.get("height_label", "Длина, L")),
                    popup_type="error")
                return None

            weld_allowance = parse_float(self.weld_allowance_input.GetValue()) or 0.0
            height += weld_allowance

            accuracy = parse_float(self.accuracy_combo.GetValue())
            if accuracy is None or accuracy < 4:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("accuracy_label", "Точность (точек)")), popup_type="error")
                return None


            # Маппинг типа диаметра
            diameter_type_map = {
                0: "outer",
                1: "middle",
                2: "inner"
            }
            flag = diameter_type_map.get(self.diameter_type_choice.GetSelection(), "outer")

            # Вычисление наружного диаметра через at_diameter
            try:
                diameter_top = at_diameter(diameter_top, thickness, flag) + thickness
            except ValueError as e:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр, d")), popup_type="error")
                return None


            return {
                "insert_point": self.insert_point,
                "diameter_base": chorda,
                "diameter_pipe": diameter_main,
                "diameter_top": diameter_top,
                "height_full": height,
                "thickness": thickness,
                "order_number": self.order_input.GetValue(),
                "detail_number": self.detail_input.GetValue(),
                "material": self.material_combo.GetValue(),
                "N": int(accuracy),
                "layer_name": "LASER-TEXT"
            }
        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")
            return None

    def update_ui_language(self):
        """Переводит все подписи при смене языка."""
        self.static_boxes["main_data"].SetLabel(loc.get("main_data_label", "Основные данные"))
        self.static_boxes["nozzle_params"].SetLabel(loc.get("nozzle_params_label", "Параметры отвода"))
        self.static_boxes["build_conditions"].SetLabel(loc.get("build_conditions_label", "Условия построения"))

        self.labels["order"].SetLabel(loc.get("order_label", "К-№"))
        self.labels["material"].SetLabel(loc.get("material_label", "Материал"))
        self.labels["thickness"].SetLabel(loc.get("thickness_label", "Толщина, S"))
        self.labels["diameter_top"].SetLabel(loc.get("diameter_label", "Диаметр, d"))
        self.labels["chorda"].SetLabel(loc.get("chorda_label", "Длина хорды, db"))
        self.labels["diameter_main"].SetLabel(loc.get("diameter_main_label", "Диаметр магистрали, D"))
        self.labels["height"].SetLabel(loc.get("height_label", "Высота, H"))
        self.labels["accuracy"].SetLabel(loc.get("accuracy_label", "Точность"))
        self.labels["weld_allowance"].SetLabel(loc.get("weld_allowance_label", "Припуск на сварку"))

        # Обновление списка типов диаметра
        self.diameter_type_choice.SetItems([
            loc.get("external_diameter_label", "Внешний"),
            loc.get("middle_diameter_label", "Средний"),
            loc.get("internal_diameter_label", "Внутренний"),
        ])
        self.diameter_type_choice.SetSelection(0)

        self.Layout()
        self.Refresh()

# ----------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title="Test ConePipeContentPanel", size=(1000, 600))
    panel = ConePipeContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()























