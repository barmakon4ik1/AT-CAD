"""
windows/content_rings.py

Панель ввода параметров колец.

Поддерживает:
- динамическую смену языка
- централизованный UI через FieldBuilder
- сбор и валидацию данных через FormBuilder
"""

from typing import Optional, Dict
from config.at_config import *
from locales.at_translations import loc
from programs.at_input import at_get_point

from windows.at_fields_builder import FieldBuilder, FormBuilder, LocalizableStaticBox, LocalizableButton
from windows.at_window_utils import (
    CanvasPanel,
    show_popup,
    get_standard_font,
    apply_styles_to_panel,
    adjust_button_widths,
    update_status_bar_point_selected,
    BaseContentPanel,
    BaseInputWindow,
    load_user_settings,
)

# ----------------------------------------------------------------------
# Локальные переводы
# ----------------------------------------------------------------------

TRANSLATIONS = {
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},

    "main_data_label": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main data"},
    "order_label": {"ru": "К-№", "de": "K-Nr.", "en": "K-no."},

    "diameter_label": {"ru": "Диаметры", "de": "Durchmesser", "en": "Diameters"},
    "diameters_label": {
        "ru": "Диаметры (через запятую)",
        "de": "Durchmesser (durch Kommas getrennt)",
        "en": "Diameters (separated by commas)",
    },

    "no_data_error": {
        "ru": "Необходимо ввести хотя бы один размер",
        "de": "Mindestens eine Abmessung muss eingegeben werden",
        "en": "At least one dimension must be entered",
    },

    "point_selection_error": {
        "ru": "Ошибка выбора точки: {}",
        "de": "Fehler bei der Punktauswahl: {}",
        "en": "Point selection error: {}",
    },

    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
}

loc.register_translations(TRANSLATIONS)

# ----------------------------------------------------------------------
# Парсер диаметров
# ----------------------------------------------------------------------

def parse_diameters(text: str) -> Dict[str, float]:
    items = [s.strip() for s in text.split(",") if s.strip()]
    if not items:
        raise ValueError(loc.get("no_data_error"))

    result: Dict[str, float] = {}
    for i, value in enumerate(items, start=1):
        result[str(i)] = float(value.replace(",", "."))
    return result


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------

def create_window(parent: wx.Window) -> wx.Panel | None:
    try:
        return RingsContentPanel(parent)
    except Exception as e:
        show_popup(f"{loc.get('error')}: {e}", popup_type="error")
        return None


# ----------------------------------------------------------------------
# Панель
# ----------------------------------------------------------------------

class RingsContentPanel(BaseContentPanel):
    """
    Встраиваемая панель ввода параметров колец
    с поддержкой динамической локализации.
    """

    def __init__(self, parent: wx.Window, on_submit_callback=None):
        super().__init__(parent)

        self.settings = load_user_settings()
        self.SetBackgroundColour(
            self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
        )

        self.on_submit_callback = on_submit_callback
        self.form = FormBuilder(self)
        self.input_point = None

        # ссылки для обновления языка
        self._field_builders: list[FieldBuilder] = []
        self._static_boxes: Dict[str, wx.StaticBox] = {}
        self._buttons: list[wx.Button] = []

        self._build_ui()
        self._status_clear()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        if self.GetSizer():
            self.GetSizer().Clear(True)

        self._field_builders.clear()
        self._static_boxes.clear()
        self._buttons.clear()

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Левая часть
        left = wx.BoxSizer(wx.VERTICAL)
        self.canvas = CanvasPanel(self, str(RING_IMAGE_PATH), size=(600, 400))
        left.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Правая часть
        right = wx.BoxSizer(wx.VERTICAL)
        font = get_standard_font()

        # -------------------- Основные данные --------------------
        main_box = wx.StaticBox(self, label=loc.get("main_data_label"))
        main_box.SetFont(font)
        self._static_boxes["main_data"] = main_box

        main_sizer_box = wx.StaticBoxSizer(main_box, wx.VERTICAL)

        fb_main = FieldBuilder(
            parent=main_box,
            target_sizer=main_sizer_box,
            form=self.form,
            default_size=INPUT_FIELD_SIZE,
        )
        self._field_builders.append(fb_main)

        fb_main.text(
            name="work_number",
            label_key="order_label",
        )

        right.Add(main_sizer_box, 0, wx.EXPAND | wx.ALL, 10)

        # -------------------- Диаметры --------------------
        diam_box = wx.StaticBox(self, label=loc.get("diameter_label"))
        diam_box.SetFont(font)
        self._static_boxes["diameters"] = diam_box

        diam_sizer_box = wx.StaticBoxSizer(diam_box, wx.VERTICAL)

        fb_diam = FieldBuilder(
            parent=diam_box,
            target_sizer=diam_sizer_box,
            form=self.form,
            default_size=(INPUT_FIELD_SIZE[0], 100),
        )
        self._field_builders.append(fb_diam)

        fb_diam.multiline_text(
            name="diameters",
            label_key="diameters_label",
            required=True,
            parser=parse_diameters,
            size=(INPUT_FIELD_SIZE[0], 100),
        )

        right.Add(diam_sizer_box, 0, wx.EXPAND | wx.ALL, 10)
        right.AddStretchSpacer()

        # -------------------- Кнопки --------------------
        button_bar_sizer = self.create_button_bar()
        self._buttons = self.buttons  # сохраняем ссылки на кнопки

        right.Add(button_bar_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        # -------------------- Добавляем всё в главный сайзер --------------------
        main_sizer.Add(left, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(right, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

        # группы
        for key, box in self._static_boxes.items():
            self.register_localizable(LocalizableStaticBox(box, f"{key}_label"))

        # кнопки
        for btn, key in zip(self._buttons, ["ok_button", "clear_button", "cancel_button"]):
            if btn:
                self.register_localizable(LocalizableButton(btn, key))

    # ------------------------------------------------------------------
    # Сервис
    # ------------------------------------------------------------------

    def _status_clear(self):
        update_status_bar_point_selected(self, None)

    def clear_input_fields(self):
        self.form.clear()
        self.input_point = None
        self._status_clear()

    # ------------------------------------------------------------------
    # Данные
    # ------------------------------------------------------------------

    def collect_input_data(self) -> Optional[Dict]:
        try:
            data = self.form.collect()
            data["input_point"] = self.input_point
            return data
        except Exception as e:
            show_popup(str(e), popup_type="error")
            return None

    # ------------------------------------------------------------------
    # Кнопки
    # ------------------------------------------------------------------

    def on_ok(self, event: wx.Event, close_window: bool = False):
        try:
            top = wx.GetTopLevelParent(self)
            top.Iconize(True)

            self.input_point = at_get_point(as_variant=False)

            top.Iconize(False)
            top.Raise()
            wx.Yield()

            data = self.collect_input_data()
            if not data:
                return

            if not data["input_point"]:
                show_popup(
                    loc.get("point_selection_error").format("None"),
                    popup_type="error",
                )
                return

            if self.on_submit_callback:
                self.on_submit_callback(data)

            if close_window:
                self.switch_content_panel("content_apps")

        except Exception as e:
            show_popup(str(e), popup_type="error")

    def on_clear(self, event: wx.Event):
        self.clear_input_fields()

    def on_cancel(self, event: wx.Event, switch_content="content_apps"):
        self.switch_content_panel(switch_content)


# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------

if __name__ == "__main__":

    def on_submit(data: Dict):
        print("Полученные данные:")
        for k, v in data.items():
            print(f"{k}: {v}")

    app = wx.App(False)
    frame = BaseInputWindow(
        title_key="test_rings_window",
        last_input_file=str(LAST_CONE_INPUT_FILE),
        window_size=(900, 600),
    )

    panel = RingsContentPanel(frame.panel, on_submit_callback=on_submit)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.panel.SetSizer(sizer)

    frame.Show()
    app.MainLoop()
