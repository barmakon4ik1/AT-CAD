"""
windows/cone_offset_dialog.py

Диалоговое окно мостика таблички, посаженного на конус
"""

from pprint import pprint

import wx
from typing import Optional
from config.at_config import BRACKET5_CONE_IMAGE_PATH
from locales.at_translations import loc
from programs.at_construction import at_diameter
from programs.at_geometry import diameter_cone_offset
from windows.at_fields_builder import FieldBuilder, FormBuilder
from windows.at_gui_utils import show_popup
from windows.at_window_utils import (
    CanvasPanel,
    BaseContentPanel,
    apply_styles_to_panel,
    load_common_data, parse_float,
)

# ----------------------------------------------------------------------
# Локализация
# ----------------------------------------------------------------------

TRANSLATIONS = {
    "main_data_cone": {"ru": "Основные данные конуса", "de": "Hauptdaten des Kegels", "en": "Main Data of cone"},
    "dimensions_label": {"ru": "Размеры", "de": "Abmessungen", "en": "Dimensions"},
    "thickness_cone_label": {"ru": "Толщина Sk, мм", "de": "Dicke Sk, mm", "en": "Thickness Sk, mm"},
    "length_cone_label": {"ru": "Длина Lk, мм", "de": "Länge Lk, mm", "en": "Length Lk, mm"},
    "length_offset_label": {"ru": "Длина смещения, мм", "de": "Versatzlänge, mm", "en": "Offset length, mm"},
    "diameter_base_label": {"ru": "Диаметр Db, мм", "de": "Durchmesser Db, mm", "en": "Diameter Db, mm"},
    "diameter_top_label": {"ru": "Диаметр Dv, мм", "de": "Durchmesser Dv, mm", "en": "Diameter Dv, mm"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "list_label": {"ru": "Посадка на конус", "de": "Lage auf dem Kegel", "en": "Location on the cone"},
    "bracket_offset": {"ru": "Длина смещения мостика", "de": "Brückenversatzlänge", "en": "Bracket offset length"},
    "inner": {
        "ru": "Внутренний",
        "de": "Innendurchmesser",
        "en": "Inner"
    },
    "middle": {
        "ru": "Средний",
        "de": "Mittlerer Durchmesser",
        "en": "Middle"
    },
    "outer": {
        "ru": "Наружный",
        "de": "Außendurchmesser",
        "en": "Outer"
    }
}
loc.register_translations(TRANSLATIONS)

# ----------------------------------------------------------------------
# Основная панель
# ----------------------------------------------------------------------
class ConeOffsetDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(
            parent,
            title=loc.get("list_label"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1000, 400),
        )

        self.selected_code: Optional[str] = None

        self.panel = ConeOffsetContentPanel(self, width=170)

        box_sizer = wx.BoxSizer(wx.VERTICAL)
        box_sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(box_sizer)

        self.CentreOnParent()


class ConeOffsetContentPanel(BaseContentPanel):
    """
    Панель обслуживания таблички, посаженной на конус
    """

    def __init__(self, parent: wx.Window, width:float) -> None:
        super().__init__(parent)

        self.width = width
        self.result = None
        self.dialog = parent

        # Построение интерфейса
        self.setup_ui()

    # ----------------------------
    #  UI
    # ----------------------------
    def setup_ui(self):
        """Метод, вызываемый базовым классом для построения интерфейса и обновления языка."""
        self._build_ui()

    def _build_ui(self):

        # Очистка предыдущего интерфейса
        if self.GetSizer():
            self.GetSizer().Clear(True)

        self.form = FormBuilder(self)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_sizer = wx.BoxSizer(wx.VERTICAL)

        #--- Левая часть (картинка)
        FieldBuilder(self, self.left_sizer, form=self.form)

        image_path = str(BRACKET5_CONE_IMAGE_PATH)
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        # -----------------------------
        # Загрузка общих данных
        # -----------------------------
        common_data = load_common_data()
        thickness_options = common_data.get("thicknesses", [])

        # --- Правая часть
        self.fb = FieldBuilder(
            parent=self,
            target_sizer=self.right_sizer,
            form=self.form
        )

        # =============================
        # Основные данные конуса
        # =============================
        main_data_sizer = self.fb.static_box("main_data_cone")
        fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        # Толщина
        fb_main.universal_row(
            "thickness_cone_label",
            [
                {"type": "combo",
                 "name": "thickness_cone",
                 "choices": thickness_options,
                 "value": "",
                 "required": True,
                 "default": "3"}
            ]
        )

        choices = [
            loc.get("inner"),
            loc.get("middle"),
            loc.get("outer"),
            ]

        fb_main.universal_row(
            "diameter_base_label",
            [
                {"type": "combo",
                 "name": "diameter_db_type",
                 "choices": choices,
                 "value": choices[0],
                 "required": True,
                 "default": choices[0],
                 "readonly": True
                 },
                {"type": "text",
                 "name": "diameter_db",
                 "value": "",
                 "required": True,
                 "default": ""},
            ]
        )

        fb_main.universal_row(
            "diameter_top_label",
            [
                {"type": "combo",
                 "name": "diameter_dv_type",
                 "choices": choices,
                 "value": choices[0],
                 "required": True,
                 "default": choices[0],
                 "readonly": True
                 },
                {"type": "text",
                 "name": "diameter_dv",
                 "value": "",
                 "required": True,
                 "default": ""},
            ]
        )

        fb_main.universal_row(
            "length_cone_label",
            [
                {"type": "text",
                 "name": "length_cone",
                 "value": "",
                 "required": True,
                 "default": ""
                 },
            ]
        )

        # =============================
        # Отступ мостика
        # =============================
        bracket_offset_sizer = self.fb.static_box("bracket_offset")
        fb_offset = FieldBuilder(parent=self, target_sizer=bracket_offset_sizer, form=self.form)

        length_offset_option = ["La", "Lb"]
        fb_offset.universal_row(
            loc.get("length_offset_label"),
            [
                {"type": "combo",
                 "name": "length_offset_option",
                 "value": length_offset_option[0],
                 "choices": length_offset_option,
                 "required": True,
                 "default": length_offset_option[0],
                 "readonly": True
                 },
                {"type": "text",
                 "name": "length_offset",
                 "value": "",
                 "required": True,
                 "default": ""
                 }
            ]
        )


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

        wx.CallAfter(self.clear_input_fields)

    # ------------------------------------------------------------------
    # Сервисные функции
    # ------------------------------------------------------------------
    def clear_input_fields(self):
        """
        Очистка всех полей формы и сброс точки вставки.
        """
        # Очищаем форму
        self.form.clear()

    # ------------------------------------------------------------------
    # Доступ к данным
    # ------------------------------------------------------------------
    def on_ok(self, event: wx.Event, close_window: bool = False) -> None:
        try:
            w = self.width
            raw = self.form.collect()
            pprint(raw) # Debug

            LOCALIZED_TO_FLAG = {
                loc.get("inner"): "inner",
                loc.get("middle"): "middle",
                loc.get("outer"): "outer",
            }

            dv = parse_float(raw.get("diameter_dv"))
            db = parse_float(raw.get("diameter_db"))
            sk = parse_float(raw.get("thickness_cone"))
            lk = parse_float(raw.get("length_cone"))
            l_type = raw.get("length_offset_option")
            l_offset = parse_float(raw.get("length_offset"))

            dv_type_local = raw.get("diameter_dv_type")
            db_type_local = raw.get("diameter_db_type")

            dv_type = LOCALIZED_TO_FLAG.get(dv_type_local)
            db_type = LOCALIZED_TO_FLAG.get(db_type_local)

            if dv_type is None or db_type is None:
                raise ValueError("Invalid diameter type")

            dvs = at_diameter(dv, sk, flag=dv_type)
            dbs = at_diameter(db, sk, flag=db_type)

            di = diameter_cone_offset(lk, l_offset, dvs, dbs)

            if l_type == "La":
                d1 = di
                d2 = diameter_cone_offset(lk, l_offset + w, dvs, dbs)
            else:
                d2 = di
                d1 = diameter_cone_offset(lk, l_offset - w, dvs, dbs)

            self.result = (d1, d2)
            # print(self.result)

            parent = self.GetParent()
            if isinstance(parent, wx.Dialog):
                parent.EndModal(wx.ID_OK)
            else:
                parent.Close()

        except ValueError:
            show_popup(loc.get("invalid_number_format_error"), popup_type="error")
            return

    def on_cancel(self, event) -> None:
        parent = self.GetParent()
        if isinstance(parent, wx.Dialog):
            parent.EndModal(wx.ID_CANCEL)
        else:
            parent.Close()

    def on_clear(self, event: wx.Event) -> None:
        self.clear_input_fields()


if __name__ == "__main__":

    app = wx.App(False)
    frame = wx.Frame(None, title="test_bracket_window", size=wx.Size(1000, 400))
    panel = ConeOffsetContentPanel(frame, 170)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
