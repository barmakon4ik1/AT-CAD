"""
windows/content_rings.py

Панель ввода параметров колец.
"""

import wx
from typing import Optional
from config.at_config import (
    RING_IMAGE_PATH,
    DEFAULT_SETTINGS,
)
from locales.at_translations import loc
from windows.at_fields_builder import FieldBuilder, FormBuilder
from windows.at_window_utils import (
    CanvasPanel,
    show_popup,
    load_common_data,
    apply_styles_to_panel,
    update_status_bar_point_selected,
    BaseContentPanel,
    load_user_settings,
    get_wx_color_from_value,
)

# ----------------------------------------------------------------------
# Локальные переводы
# ----------------------------------------------------------------------
TRANSLATIONS = {
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main data"},
    "order_label": {"ru": "К-№", "de": "K-Nr.", "en": "K-no."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},
    "diameter": {"ru": "Диаметры", "de": "Durchmesser", "en": "Diameters"},
    "diameters": {"ru": "Диаметр", "de": "Durchmesser", "en": "Diameter"},
    "no_data_error": {"ru": "Необходимо ввести хотя бы один размер", "de": "Mindestens eine Abmessung muss eingegeben werden", "en": "At least one dimension must be entered"},
    "point_selection_error": {"ru": "Ошибка выбора точки", "de": "Fehler bei der Punktauswahl", "en": "Point selection error"},
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
}
loc.register_translations(TRANSLATIONS)

# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def create_window(parent: wx.Window) -> Optional[wx.Panel]:
    try:
        return RingsContentPanel(parent)
    except Exception as e:
        show_popup(loc.get("error") + f": {str(e)}", popup_type="error")
        return None

# ----------------------------------------------------------------------
# Панель
# ----------------------------------------------------------------------
class RingsContentPanel(BaseContentPanel):
    """
    Панель ввода параметров колец.
    Левая часть: изображение колец.
    Правая часть: поля main_data + таблица диаметров + кнопки.
    """

    def __init__(self, parent: wx.Window, on_submit_callback=None):
        super().__init__(parent)
        self.settings = load_user_settings()
        self.on_submit_callback = on_submit_callback
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

        # UI элементы
        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None
        self.canvas: Optional[CanvasPanel] = None
        self.form = None
        self.fb = None
        self.diameter_inputs = []

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def setup_ui(self) -> None:
        if self.GetSizer():
            self.GetSizer().Clear(True)

        # ------------------------------------------------------------
        # Главный сайзер
        # ------------------------------------------------------------
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        # ------------------------------------------------------------
        # Левая часть — изображение
        # ------------------------------------------------------------
        image_path = str(RING_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------
        # Данные
        # ------------------------------------------------------------
        common_data = load_common_data()
        material_options = [m["name"] for m in common_data.get("material", []) if m["name"]]
        thickness_options = common_data.get("thicknesses", [])

        # ------------------------------------------------------------
        # Форма
        # ------------------------------------------------------------
        self.form = FormBuilder(self)
        self.fb = FieldBuilder(
            parent=self,
            target_sizer=self.right_sizer,
            form=self.form
        )

        # ============================================================
        # ГРУППА: Основные данные
        # ============================================================
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

        # ============================================================
        # ГРУППА: Диаметры
        # ============================================================
        diam_sizer = self.fb.static_box("diameters")
        self.static_boxes["diameters"] = diam_sizer.GetStaticBox()

        fb_diam = FieldBuilder(
            parent=self,
            target_sizer=diam_sizer,
            form=self.form
        )

        fb_diam.text_column(
            [f"diameter_{i + 1}" for i in range(5)],
            width=200,
            default=""
        )

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
    def on_ok(self, *args, **kwargs) -> None:
        try:
            data = self.form.collect()
            if not data:
                show_popup(loc.get("no_data_error"), popup_type="error")
                return

            # диаметры
            diameters = {
                k.replace("diameter_", ""): v
                for k, v in data.items()
                if k.startswith("diameter_") and v not in ("", None)
            }

            if not diameters:
                show_popup(loc.get("no_data_error"), popup_type="error")
                return

            data["diameters"] = diameters

            if not self.validate_input(data):
                return

            if self.on_submit_callback:
                self.on_submit_callback(data)

        except ValueError as e:
            show_popup(str(e), popup_type="error")
        except Exception as e:
            show_popup(loc.get("error") + f": {str(e)}", popup_type="error")

    # def on_clear(self, event: Optional[wx.Event] = None):
    #     _ = event
    #     self.clear_input_fields()
    #
    # def on_cancel(self, event: Optional[wx.Event] = None, switch_content="content_apps"):
    #     _ = event
    #     self.switch_content_panel(switch_content)

# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------
if __name__ == "__main__":

    from programs.at_ringe import main

    app = wx.App(False)
    frame = wx.Frame(None, title="test_rings_window", size=wx.Size(1500, 700))
    panel = RingsContentPanel(frame)

    def on_ok_test():
        data = panel.form.collect()
        if data:
            print("FORM DATA:", data)
            main(data)


    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
