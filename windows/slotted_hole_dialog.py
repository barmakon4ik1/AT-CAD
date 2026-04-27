"""
windows/slotted_hole_dialog.py

Диалоговое окно продолговатого отверстия
"""
from pprint import pprint

import wx
from typing import Optional
from config.at_config import SLOTTED_HOLE_IMAGE_PATH
from locales.at_translations import loc
from windows.at_fields_builder import FieldBuilder, FormBuilder, normalize_input
from windows.at_gui_utils import show_popup
from windows.at_window_utils import (
    CanvasPanel,
    BaseContentPanel,
    apply_styles_to_panel,
)

# ----------------------------------------------------------------------
# Локализация
# ----------------------------------------------------------------------

TRANSLATIONS = {
    "dimensions_label": {"ru": "Размеры", "de": "Abmessungen", "en": "Dimensions"},
    "length_label": {"ru": "Длина, мм", "de": "Länge, mm", "en": "Length, mm"},
    "diameter_label": {"ru": "Диаметр D, мм", "de": "Durchmesser D, mm", "en": "Diameter D, mm"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},
    "clear_button": {"ru": "Очистить", "de": "Zurücksetzen", "en": "Clear"},
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "list_label": {"ru": "Продолговатое отверстие", "de": "Langloch", "en": "Slotted hole"},
    "angle_label": {"ru": "Угол поворота A°", "de": "Drehwinkel A°", "en": "Angle of rotation A°"},
    "direction_label": {"ru": "Положение базовой точки", "de": "Lage des Basispunktes", "en": "Location of the base point"},
    "center": {"ru": "по центру, C", "de": "mitte, C", "en": "center, C"},
    "top": {"ru": "сверху, T", "de": "oben, T", "en": "top, T"},
    "bottom": {"ru": "снизу, B", "de": "unten, B", "en": "bottom, B"},
    "left": {"ru": "слева, L", "de": "links, L", "en": "left, L"},
    "right": {"ru": "справа, R", "de": "rechts, R", "en": "right, R"},
    "invalid_number_format_error": {
        "ru": "Введено неверное число.\nПроверьте вводимые числа.\n (W1 должен быть > D)",
        "de": "Ungültige Zahl eingegeben.\nBitte überprüfen Sie die eingegebenen Zahlen.\n (W1 muss > D sein)",
        "en": "Invalid number entered.\nPlease check the numbers you entered.\n (W1 must be > D)"
    }
}
loc.register_translations(TRANSLATIONS)

# ----------------------------------------------------------------------
# Основная панель
# ----------------------------------------------------------------------
class SlottedHoleDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(
            parent,
            title=loc.get("list_label"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1000, 600),
        )

        self.selected_code: Optional[str] = None

        self.panel = SlottedHoleContentPanel(self, width=170)

        box_sizer = wx.BoxSizer(wx.VERTICAL)
        box_sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(box_sizer)

        self.CentreOnParent()


class SlottedHoleContentPanel(BaseContentPanel):
    """
    Панель продолговатого отверстия
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
        self.Freeze()
        try:
            # Очистка предыдущего интерфейса
            if self.GetSizer():
                self.GetSizer().Clear(True)

            self.form = FormBuilder(self)

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer = wx.BoxSizer(wx.VERTICAL)

            #--- Левая часть (картинка)
            FieldBuilder(self, self.left_sizer, form=self.form)

            image_path = str(SLOTTED_HOLE_IMAGE_PATH)
            self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
            self.left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

            # --- Правая часть
            self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

            # =============================
            # Основные параметры отверстия
            # =============================
            main_data_sizer = self.fb.static_box("dimensions_label")
            fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

            fb_main.universal_row(
                "diameter_label",
                [
                    {"type": "text",
                     "name": "diameter",
                     "value": "",
                     "required": True,
                     "default": ""
                     },
                ]
            )

            length_option = ["W", "W1"]
            fb_main.universal_row(
                loc.get("length_label"),
                [
                    {"type": "combo",
                     "name": "length_offset_option",
                     "value": length_option[0],
                     "choices": length_option,
                     "required": True,
                     "default": length_option[0],
                     "readonly": True,
                     "size": (100, -1)
                     },
                    {"type": "text",
                     "name": "length",
                     "value": "",
                     "required": True,
                     "default": ""
                     }
                ]
            )
            fb_main.universal_row(
                "angle_label",
                [
                    {"type": "text",
                     "name": "angle",
                     "value": "0",
                     "required": True,
                     "default": "0"
                     },
                ]
            )

            # =============================
            # Положение бвзовой точки отверстия
            # =============================
            main_data_sizer = self.fb.static_box("direction_label")
            fb_dir = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

            direction_option = [
                loc.get("center"),
                loc.get("left"),
                loc.get("right"),
                loc.get("top"),
                loc.get("bottom"),
            ]
            fb_dir.universal_row(
                "",
                [
                    {"type": "combo",
                     "name": "direction",
                     "value": direction_option[0],
                     "choices": direction_option,
                     "required": True,
                     "default": direction_option[0],
                     "readonly": True
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
        finally:
            self.Layout()
            self.Thaw()

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
    def on_ok(self, event: wx.Event, close_window: bool = True) -> None:
        try:
            # 1. Получаем данные формы
            raw = self.form.collect()

            pprint(raw) # Debug

            # 2. Преобразование чисел
            diameter = normalize_input(raw, "diameter", 0.0)
            length = normalize_input(raw, "length", 0.0)
            angle = normalize_input(raw, "angle", 0.0)

            # 3. Строковые параметры
            length_mode = raw.get("length_offset_option")  # W / W1
            if length_mode == "W1":
                length -= diameter

            direction_raw = raw.get("direction")

            if direction_raw == loc.get("left"):
                direction = "left"
            elif direction_raw == loc.get("right"):
                direction = "right"
            elif direction_raw == loc.get("top"):
                direction = "top"
            elif direction_raw == loc.get("bottom"):
                direction = "bottom"
            else:
                direction = "center"

            #  Формирование результата
            self.result = {
                "diameter": diameter,
                "length": length,
                "angle": angle,
                "direction": direction,
            }
            pprint(self.result) # Debug

            #  Закрытие окна
            if close_window:
                parent = self.GetParent()
                if isinstance(parent, wx.Dialog):
                    parent.EndModal(wx.ID_OK)
                else:
                    parent.Close()

        except ValueError:
            show_popup(loc.get("invalid_number_format_error"), popup_type="error")

    def on_cancel(self, event) -> None:
        parent = self.GetParent()
        if isinstance(parent, wx.Dialog):
            parent.EndModal(wx.ID_CANCEL)
        else:
            parent.Close()

    def on_clear(self, event: wx.Event) -> None:
        self.clear_input_fields()


def open_dialog(parent: wx.Window) -> dict | None:
    """
    Открывает диалог, возвращает словарь с данными или None при отмене.
    """
    dlg = SlottedHoleDialog(parent)
    result = None
    if dlg.ShowModal() == wx.ID_OK:
        result = dlg.panel.result
    dlg.Destroy()
    return result


if __name__ == "__main__":

    app = wx.App(False)
    frame = wx.Frame(None, title="test_slotted_hole_window", size=wx.Size(1000, 400))
    panel = SlottedHoleContentPanel(frame, 170)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
