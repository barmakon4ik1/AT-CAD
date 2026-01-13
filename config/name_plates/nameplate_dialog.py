# nameplate_dialog.py
"""
Файл: nameplate_dialog.py
Путь: config/name_plates/nameplate_dialog.py

Панель CRUD-обслуживания конфигураций табличек (Name Plates)
в составе интерфейса AT-CAD.
"""

import os
import wx
from typing import Dict, Optional

from wx.lib.buttons import GenButton

from locales.at_translations import loc
from windows.at_gui_utils import show_popup
from windows.at_window_utils import (
    CanvasPanel,
    BaseContentPanel,
    apply_styles_to_panel,
    style_label,
    style_textctrl,
    style_staticbox, style_gen_button,
)

from config.name_plates.nameplate_storage import load_nameplates, save_nameplates
from config.name_plates.nameplate_validation import validate_record


# ----------------------------------------------------------------------
# Локализация
# ----------------------------------------------------------------------

TRANSLATIONS = {
    "list_label": {"ru": "Таблички", "en": "Name Plates", "de": "Typenschilder"},
    "data_label": {"ru": "Параметры таблички, мм", "en": "Name Plate Data, mm", "de": "Typenschilddaten, mm"},
    "add": {"ru": "Добавить", "en": "Add", "de": "Hinzufügen"},
    "clear": {"ru": "Очистить", "en": "Clear", "de": "Leeren"},
    "delete": {"ru": "Удалить", "en": "Delete", "de": "Löschen"},
    "ok": {"ru": "Возврат", "en": "Return", "de": "Zurück"},
    "confirm_delete": {
        "ru": "Удалить выбранную табличку?",
        "en": "Delete selected name plate?",
        "de": "Ausgewähltes Typenschild löschen?",
    },
    "error": {"ru": "Ошибка", "en": "Error", "de": "Fehler"},
    "field_name": {
        "ru": "Код",
        "en": "Code",
        "de": "Code",
    },
    "field_remark": {
        "ru": "Примечание.",
        "en": "Remark",
        "de": "Bemerkung",
    },
}
loc.register_translations(TRANSLATIONS)


# ----------------------------------------------------------------------
# Фабрика панели (как в рабочих окнах)
# ----------------------------------------------------------------------

def create_window(parent: wx.Window) -> wx.Panel:
    return NamePlateContentPanel(parent)


# ----------------------------------------------------------------------
# Основная панель
# ----------------------------------------------------------------------

class NamePlateContentPanel(BaseContentPanel):
    """
    Панель обслуживания конфигураций табличек.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.data = load_nameplates()
        self.current_index: Optional[int] = None
        self.fields: Dict[str, wx.TextCtrl] = {}

        self._build_ui()
        self._update_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):

        FIELD_LABELS = {
            "name": "field_name",
            "a1": "a1",
            "b1": "b1",
            "a": "a",
            "b": "b",
            "d": "d",
            "r": "r",
            "s": "s",
            "remark": "field_remark",
        }

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # ================= Левая часть =================
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        image_path = os.path.join(
            os.path.dirname(__file__),
            "name_plate_image.png",
        )

        self.canvas = CanvasPanel(
            self,
            image_file=image_path,
            size=(600, 400),
        )
        left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        self.btn_ok = GenButton(self, label=loc.get("ok"), size=(140, 30))
        style_gen_button(self.btn_ok, "#2980b9", font_size=14, button_height=30)

        # ================= Правая часть =================
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Список ---
        self.list_box = wx.StaticBox(self, label=loc.get("list_label"))
        style_staticbox(self.list_box)
        list_sizer = wx.StaticBoxSizer(self.list_box, wx.VERTICAL)

        self.listbox = wx.ListBox(self.list_box)
        list_sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 5)

        right_sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 5)

        # --- Данные ---
        self.data_box = wx.StaticBox(self, label=loc.get("data_label"))
        style_staticbox(self.data_box)
        data_sizer = wx.StaticBoxSizer(self.data_box, wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 6, 10)
        grid.AddGrowableCol(1, 1)

        self.labels: Dict[str, wx.StaticText] = {}

        for key, label_key in FIELD_LABELS.items():
            lbl = wx.StaticText(
                self.data_box,
                label=loc.get(label_key, label_key),
            )
            style_label(lbl)

            self.labels[key] = lbl

            txt = wx.TextCtrl(self.data_box)
            style_textctrl(txt)

            self.fields[key] = txt

            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(txt, 1, wx.EXPAND)

        data_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        right_sizer.Add(data_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Кнопки действий ---
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_add = GenButton(self, label=loc.get("add"), size=(120, 30))
        style_gen_button(self.btn_add, "#27ae60", font_size=14, button_height=30)

        self.btn_clear = GenButton(self, label=loc.get("clear"), size=(120, 30))
        style_gen_button(self.btn_clear, "#e67e22", font_size=14, button_height=30)

        self.btn_delete = GenButton(self, label=loc.get("delete"), size=(120, 30))
        style_gen_button(self.btn_delete, "#c0392b", font_size=14, button_height=30)

        # action_sizer.Add(self.btn_add, 0, wx.RIGHT, 8)
        # action_sizer.Add(self.btn_clear, 0, wx.RIGHT, 8)
        # action_sizer.Add(self.btn_delete, 0)

        right_sizer.Add(action_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        bottom_sizer.AddStretchSpacer()

        bottom_sizer.Add(self.btn_ok, 0, wx.RIGHT, 50)
        bottom_sizer.Add(self.btn_add, 0, wx.RIGHT, 5)
        bottom_sizer.Add(self.btn_clear, 0, wx.RIGHT, 2)
        bottom_sizer.Add(self.btn_delete, 0, wx.RIGHT, 0)

        # ================= Сборка =================
        # main_sizer.Add(left_sizer, 2, wx.EXPAND)
        # main_sizer.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 10)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        content_sizer.Add(left_sizer, 2, wx.EXPAND)
        content_sizer.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 10)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(content_sizer, 1, wx.EXPAND)
        main_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)
        self.Layout()

        # Bind
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.listbox.Bind(wx.EVT_LISTBOX, self.on_select)
        self.btn_add.Bind(wx.EVT_BUTTON, self.on_add)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------

    def _update_list(self):
        self.listbox.Clear()
        for item in self.data:
            self.listbox.Append(item.get("name", ""))

    def _collect_fields(self) -> Dict[str, str]:
        return {k: v.GetValue() for k, v in self.fields.items()}

    def _fill_fields(self, record: Dict):
        for k, ctrl in self.fields.items():
            ctrl.SetValue(str(record.get(k, "")))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_select(self, event):
        idx = event.GetSelection()
        if 0 <= idx < len(self.data):
            self.current_index = idx
            self._fill_fields(self.data[idx])

    def on_add(self, event):
        record = self._collect_fields()
        errors = validate_record(record)
        if errors:
            show_popup("\n".join(errors), popup_type="error")
            return

        self.data.append(record)
        save_nameplates(self.data)
        self._update_list()

    def on_clear(self, event):
        for ctrl in self.fields.values():
            ctrl.SetValue("")
        self.current_index = None

    def on_delete(self, event):
        idx = self.current_index
        if idx is None or idx < 0 or idx >= len(self.data):
            return

        res = show_popup(
            loc.get("confirm_delete"),
            popup_type="question",
            buttons=("OK", "Cancel"),
        )
        if res != "OK":
            return

        del self.data[idx]
        save_nameplates(self.data)

        self.current_index = None
        self._update_list()
        self.on_clear(None)

    def on_ok(self, event):
        parent = wx.GetTopLevelParent(self)
        if hasattr(parent, "switch_content"):
            parent.switch_content("content_apps")

    def update_ui_language(self):
        """
        Обновляет все текстовые элементы интерфейса
        при смене языка на лету.
        """

        # Заголовки блоков
        self.list_box.SetLabel(loc.get("list_label"))
        self.data_box.SetLabel(loc.get("data_label"))

        # Подписи полей
        FIELD_LABELS = {
            "name": "field_name",
            "a": "a",
            "b": "b",
            "a1": "a1",
            "b1": "b1",
            "d": "d",
            "r": "r",
            "s": "s",
            "remark": "field_remark",
        }

        for key, label_key in FIELD_LABELS.items():
            if key in self.labels:
                self.labels[key].SetLabel(
                    loc.get(label_key, label_key)
                )

        # Кнопки действий
        self.btn_add.SetLabel(loc.get("add"))
        self.btn_clear.SetLabel(loc.get("clear"))
        self.btn_delete.SetLabel(loc.get("delete"))
        self.btn_ok.SetLabel(loc.get("ok"))

        # Обновление layout
        self.Layout()
        self.Refresh()


# ----------------------------------------------------------------------
# Тестовый запуск
# ----------------------------------------------------------------------

if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title=loc.get("list_label"), size=(1200, 700))
    panel = NamePlateContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Show()
    app.MainLoop()
