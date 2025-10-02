"""
Модуль содержит панель CutoutContentPanel для настройки параметров выреза
в приложении AT-CAD. Панель собирает данные в словарь и передает их через callback.

Функциональность:
- UI по образцу окна отвода (NozzleContentPanel)
- Сбор данных в словарь:
    {
        "insert_point": PointVariant | None,
        "diameter": float,
        "diameter_main": float,
        "offset": float,
        "steps": int,
        "mode": str,
        "text": str
    }
- Тестовый запуск в конце файла (аналогично nozzle_content_panel.py)
- Поддержка динамической смены языка через update_ui_language()
- Минимальная валидация полей
- Возможность ввода пользовательского значения steps (editable ComboBox)
"""

import wx
from typing import Optional, Dict, List
from pathlib import Path

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_input import at_point_input
from windows.at_window_utils import (
    CanvasPanel, show_popup, get_standard_font, apply_styles_to_panel,
    create_standard_buttons, adjust_button_widths, BaseContentPanel,
    parse_float, style_label, style_textctrl, style_combobox, style_staticbox,
    update_status_bar_point_selected
)
from config.at_config import CUTOUT_IMAGE_PATH

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "cutout_data_label": {"ru": "Данные выреза", "de": "Ausschnittdaten", "en": "Cutout Data"},
    "diameter_label": {"ru": "Диаметр, d", "de": "Durchmesser, d", "en": "Diameter, d"},
    "diameter_main_label": {"ru": "Диаметр магистрали, D", "de": "Hauptdurchmesser, D", "en": "Main Diameter, D"},
    "offset_label": {"ru": "Смещение, O", "de": "Versatz, O", "en": "Offset, O"},
    "text_label": {"ru": "Сопроводительный текст", "de": "Begleittext", "en": "Accompanying Text"},
    "additional_params_label": {"ru": "Дополнительные параметры", "de": "Zusatzparameter", "en": "Additional Parameters"},
    "mode_label": {"ru": "Режим построения", "de": "Konstruktionsmodus", "en": "Build Mode"},
    "mode_bulge": {"ru": "Дуги", "de": "Bogen", "en": "Bulge"},
    "mode_polyline": {"ru": "Полилиния", "de": "Polylinie", "en": "Polyline"},
    "mode_spline": {"ru": "Сплайн", "de": "Spline", "en": "Spline"},
    "steps_label": {"ru": "Точность (точек)", "de": "Genauigkeit (Punkte)", "en": "Steps (points)"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "point_prompt": {"ru": "Укажите центр выреза", "de": "Geben Sie das Zentrum des Ausschnitts an", "en": "Select cutout center"},
    "point_selection_error": {"ru": "Точка не выбрана", "de": "Punkt nicht gewählt", "en": "Point not selected"},
    "invalid_input": {"ru": "Некорректный ввод: {0}", "de": "Ungültige Eingabe: {0}", "en": "Invalid input: {0}"},
}
loc.register_translations(TRANSLATIONS)

# Значения по умолчанию
default_modes = ["mode_bulge", "mode_polyline", "mode_spline"]
default_steps = ["180", "360", "720"]  # Значения для steps по умолчанию

# Рекомендуемые наборы значений steps по режимам
STEPS_OPTIONS = {
    "bulge": ["90", "180", "360"],          # Баланс точности/производительности
    "polyline": ["360", "720", "1080"],     # Поли-линия — больше точек
    "spline": ["90", "180", "360"],         # Сплайн — умеренно
}

# Фабричная функция для создания панели
def create_window(parent: wx.Window) -> wx.Panel:
    return CutoutContentPanel(parent)


class CutoutContentPanel(BaseContentPanel):
    """
    Панель для настройки параметров выреза.
    """
    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.on_submit_callback = callback
        self.parent = parent
        self.labels = {}
        self.static_boxes = {}
        self.buttons = []
        self.insert_point = None

        # Виджеты
        self.diameter_input: Optional[wx.TextCtrl] = None
        self.diameter_main_input: Optional[wx.TextCtrl] = None
        self.offset_input: Optional[wx.TextCtrl] = None
        self.text_input: Optional[wx.TextCtrl] = None
        self.mode_combo: Optional[wx.ComboBox] = None
        self.steps_combo: Optional[wx.ComboBox] = None

        self.setup_ui()
        self.diameter_input.SetFocus()

    def setup_ui(self):
        if self.GetSizer():
            self.GetSizer().Clear(True)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)

        # Левый блок (изображение и кнопки)
        image_path = str(CUTOUT_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = create_standard_buttons(self, self.on_ok, self.on_cancel, self.on_clear)
        for button in self.buttons:
            button_sizer.Add(button, 0, wx.RIGHT, 5)
        adjust_button_widths(self.buttons)
        self.left_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # Правый блок (поля ввода)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()
        field_size = (120, -1)  # Ширина 120, высота автоматическая

        # --- Данные выреза ---
        cutout_data_box = wx.StaticBox(self, label=loc.get("cutout_data_label", "Данные выреза"))
        style_staticbox(cutout_data_box)
        self.static_boxes["cutout_data"] = cutout_data_box
        cutout_data_sizer = wx.StaticBoxSizer(cutout_data_box, wx.VERTICAL)

        # Диаметр выреза
        row_d = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter"] = wx.StaticText(cutout_data_box, label=loc.get("diameter_label", "Диаметр, d"))
        style_label(self.labels["diameter"])
        self.diameter_input = wx.TextCtrl(cutout_data_box, value="", size=field_size)
        style_textctrl(self.diameter_input)
        row_d.Add(self.labels["diameter"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_d.AddStretchSpacer()
        row_d.Add(self.diameter_input, 0)
        cutout_data_sizer.Add(row_d, 0, wx.EXPAND | wx.ALL, 5)

        # Диаметр магистрали
        row_dm = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["diameter_main"] = wx.StaticText(cutout_data_box, label=loc.get("diameter_main_label", "Диаметр магистрали, D"))
        style_label(self.labels["diameter_main"])
        self.diameter_main_input = wx.TextCtrl(cutout_data_box, value="", size=field_size)
        style_textctrl(self.diameter_main_input)
        row_dm.Add(self.labels["diameter_main"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_dm.AddStretchSpacer()
        row_dm.Add(self.diameter_main_input, 0)
        cutout_data_sizer.Add(row_dm, 0, wx.EXPAND | wx.ALL, 5)

        # Смещение
        row_off = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["offset"] = wx.StaticText(cutout_data_box, label=loc.get("offset_label", "Смещение, O"))
        style_label(self.labels["offset"])
        self.offset_input = wx.TextCtrl(cutout_data_box, value="0", size=field_size)
        style_textctrl(self.offset_input)
        row_off.Add(self.labels["offset"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_off.AddStretchSpacer()
        row_off.Add(self.offset_input, 0)
        cutout_data_sizer.Add(row_off, 0, wx.EXPAND | wx.ALL, 5)

        # Сопроводительный текст
        row_text = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["text"] = wx.StaticText(cutout_data_box, label=loc.get("text_label", "Сопроводительный текст"))
        style_label(self.labels["text"])
        self.text_input = wx.TextCtrl(cutout_data_box, value="N1", size=field_size)
        style_textctrl(self.text_input)
        row_text.Add(self.labels["text"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_text.AddStretchSpacer()
        row_text.Add(self.text_input, 0)
        cutout_data_sizer.Add(row_text, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(cutout_data_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        # --- Дополнительные параметры ---
        additional_params_box = wx.StaticBox(self, label=loc.get("additional_params_label", "Дополнительные параметры"))
        style_staticbox(additional_params_box)
        self.static_boxes["additional_params"] = additional_params_box
        additional_params_sizer = wx.StaticBoxSizer(additional_params_box, wx.VERTICAL)

        # Режим построения
        row_mode = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["mode"] = wx.StaticText(additional_params_box, label=loc.get("mode_label", "Режим построения"))
        style_label(self.labels["mode"])
        self.mode_combo = wx.ComboBox(
            additional_params_box,
            choices=[loc.get(mode, mode) for mode in default_modes],
            value=loc.get("mode_bulge", "Bulge"),
            style=wx.CB_READONLY,
            size=field_size
        )
        style_combobox(self.mode_combo)
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_change)
        row_mode.Add(self.labels["mode"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_mode.AddStretchSpacer()
        row_mode.Add(self.mode_combo, 0)
        additional_params_sizer.Add(row_mode, 0, wx.EXPAND | wx.ALL, 5)

        # Точность (steps)
        row_steps = wx.BoxSizer(wx.HORIZONTAL)
        self.labels["steps"] = wx.StaticText(additional_params_box, label=loc.get("steps_label", "Точность (точек)"))
        style_label(self.labels["steps"])
        self.steps_combo = wx.ComboBox(
            additional_params_box,
            choices=STEPS_OPTIONS["bulge"],
            value="180",
            style=wx.CB_DROPDOWN,
            size=field_size
        )
        style_combobox(self.steps_combo)
        row_steps.Add(self.labels["steps"], 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        row_steps.AddStretchSpacer()
        row_steps.Add(self.steps_combo, 0)
        additional_params_sizer.Add(row_steps, 0, wx.EXPAND | wx.ALL, 5)

        self.right_sizer.Add(additional_params_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        main_sizer.Add(self.left_sizer, 1, wx.EXPAND)
        main_sizer.Add(self.right_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

    # ----------------------------------------------------------------
    # Обработчики событий
    # ----------------------------------------------------------------

    def on_mode_change(self, event):
        """Меняет список значений steps при смене режима построения."""
        mode_map = {
            loc.get("mode_bulge", "Bulge"): "bulge",
            loc.get("mode_polyline", "Polyline"): "polyline",
            loc.get("mode_spline", "Spline"): "spline",
        }
        selected_mode = mode_map.get(self.mode_combo.GetValue(), "bulge")
        options = STEPS_OPTIONS.get(selected_mode, STEPS_OPTIONS["bulge"])
        self.steps_combo.SetItems(options)
        self.steps_combo.SetValue(options[0])

    def on_ok(self, event: wx.Event):
        """
        Обрабатывает нажатие кнопки "ОК": собирает данные в словарь, добавляет точку вставки
        и выводит словарь на экран в тестовом режиме. В реальном режиме передает данные через callback.

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

            # Инициализация CAD и выбор точки (гарантированно возвращает точку)
            cad = ATCadInit()
            pt = at_point_input(
                cad.document,
                prompt=loc.get("point_prompt", "Укажите центр выреза"),
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
            update_status_bar_point_selected(self, pt)

            # Вывод словаря в консоль для тестового режима
            # print("Сформированный словарь данных выреза:")
            # print(data)

            # Передаем данные через callback, если он задан (реальный режим)
            if self.on_submit_callback:
                self.on_submit_callback(data)

        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")

    def on_cancel(self, event):
        parent = wx.GetTopLevelParent(self)
        if hasattr(parent, "switch_content"):
            parent.switch_content("content_apps")

    def on_clear(self, event):
        self.diameter_input.SetValue("")
        self.diameter_main_input.SetValue("")
        self.offset_input.SetValue("0")
        self.text_input.SetValue("N1")
        self.mode_combo.SetValue(loc.get("mode_bulge", "Bulge"))
        self.steps_combo.SetValue("180")

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
            # Парсинг числовых полей
            diameter = parse_float(self.diameter_input.GetValue())
            if diameter is None or diameter <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_label", "Диаметр, d")), popup_type="error")
                return None

            diameter_main = parse_float(self.diameter_main_input.GetValue())
            if diameter_main is None or diameter_main <= 0:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("diameter_main_label", "Диаметр магистрали, D")), popup_type="error")
                return None

            offset = parse_float(self.offset_input.GetValue()) or 0.0

            steps = parse_float(self.steps_combo.GetValue())
            if steps is None or steps < 4:
                show_popup(loc.get("invalid_input", "Некорректный ввод: {0}").format(
                    loc.get("steps_label", "Точность (точек)")), popup_type="error")
                return None

            mode_map = {
                loc.get("mode_bulge", "Bulge"): "bulge",
                loc.get("mode_polyline", "Polyline"): "polyline",
                loc.get("mode_spline", "Spline"): "spline",
            }

            return {
                "insert_point": self.insert_point,
                "diameter": diameter,
                "diameter_main": diameter_main,
                "offset": offset,
                "steps": int(steps),
                "mode": mode_map.get(self.mode_combo.GetValue(), "bulge"),
                "text": self.text_input.GetValue()
            }
        except Exception as e:
            show_popup(f"{loc.get('error', 'Ошибка')}: {e}", popup_type="error")
            return None

    def update_ui_language(self):
        """Переводит все подписи при смене языка."""
        self.static_boxes["cutout_data"].SetLabel(loc.get("cutout_data_label", "Данные выреза"))
        self.static_boxes["additional_params"].SetLabel(loc.get("additional_params_label", "Дополнительные параметры"))

        self.labels["diameter"].SetLabel(loc.get("diameter_label", "Диаметр, d"))
        self.labels["diameter_main"].SetLabel(loc.get("diameter_main_label", "Диаметр магистрали, D"))
        self.labels["offset"].SetLabel(loc.get("offset_label", "Смещение, O"))
        self.labels["text"].SetLabel(loc.get("text_label", "Сопроводительный текст"))
        self.labels["mode"].SetLabel(loc.get("mode_label", "Режим построения"))
        self.labels["steps"].SetLabel(loc.get("steps_label", "Точность (точек)"))

        # Обновление списка режимов построения
        self.mode_combo.SetItems([loc.get(mode, mode) for mode in default_modes])
        self.mode_combo.SetValue(loc.get("mode_bulge", "Bulge"))

        self.Layout()
        self.Refresh()

# ----------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title="Test CutoutContentPanel", size=(1000, 600))
    panel = CutoutContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()

