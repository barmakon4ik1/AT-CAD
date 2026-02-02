# nameplate_dialog.py
"""
Панель CRUD-обслуживания конфигураций табличек (Name Plates)
в составе интерфейса AT-CAD.Функциональность:Добавление / редактирование / удаление записей
Проверка уникальности поля "name"
Undo удаления (Ctrl+Z)
Корректное управление состояниями ADD / EDIT
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
    style_staticbox,
    style_gen_button,
)
from config.name_plates.nameplate_storage import load_nameplates, save_nameplates
from config.name_plates.nameplate_validation import validate_record# ----------------------------------------------------------------------
# Локализация
# ----------------------------------------------------------------------

TRANSLATIONS = {
    "list_label": {"ru": "Таблички", "en": "Name Plates", "de": "Typenschilder"},
    "data_label": {"ru": "Параметры таблички, мм", "en": "Name Plate Data, mm", "de": "Typenschilddaten, mm"},
    "add": {"ru": "Добавить", "en": "Add", "de": "Hinzufügen"},
    "edit": {"ru": "Изменить", "en": "Edit", "de": "Ändern"},
    "clear": {"ru": "Очистить", "en": "Clear", "de": "Leeren"},
    "delete": {"ru": "Удалить", "en": "Delete", "de": "Löschen"},
    "ok": {"ru": "Возврат", "en": "Return", "de": "Zurück"},
    "confirm_delete": {
        "ru": "Удалить выбранную табличку?",
        "en": "Delete selected name plate?",
        "de": "Ausgewähltes Typenschild löschen?",
    },
    "field_name": {"ru": "Код", "en": "Code", "de": "Code"},
    "field_remark": {"ru": "Примечание", "en": "Remark", "de": "Bemerkung"},
    "name_not_unique": {
        "ru": "Код уже существует",
        "en": "Code already exists",
        "de": "Code existiert bereits",
    },
}
loc.register_translations(TRANSLATIONS)# ----------------------------------------------------------------------
# Фабрика панели
# ----------------------------------------------------------------------

# def create_window(parent: wx.Window) -> wx.Panel:
#     return NamePlateContentPanel(parent)

def create_window(parent: wx.Window) -> Optional[str]:
    dlg = NamePlateDialog(parent)
    result = dlg.ShowModal()

    code = dlg.selected_code if result == wx.ID_OK else None
    dlg.Destroy()
    return code


# ----------------------------------------------------------------------
# Основная панель
# ----------------------------------------------------------------------
class NamePlateDialog(wx.Dialog):
    def __init__(self, parent: wx.Window):
        super().__init__(
            parent,
            title=loc.get("list_label"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1200, 900),
        )

        self.selected_code: Optional[str] = None

        self.panel = NamePlateContentPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.CentreOnParent()


class NamePlateContentPanel(BaseContentPanel):
    """
    Панель обслуживания конфигураций табличек.
    """
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)

        self.current_index: Optional[int] = None
        self.fields: Dict[str, wx.TextCtrl] = {}
        self.labels: Dict[str, wx.StaticText] = {}
        self.data: list[dict] = load_nameplates()
        self._last_deleted: Optional[tuple[int, dict]] = None

        self._build_ui()
        self.btn_delete.Disable()
        self._update_list()

        wx.CallAfter(self._force_refresh_list)

    def _force_refresh_list(self):
        self.listbox.Clear()  # на всякий случай
        for item in self.data:
            self.listbox.Append(item.get("name", ""))
        self.listbox.Refresh()
        self.listbox.Update()
        self.Refresh()  # иногда помогает

        # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def setup_ui(self):
        """Метод, вызываемый базовым классом для построения интерфейса и обновления языка."""
        self._build_ui()

    def _build_ui(self):
        field_labels = {
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

        # # ===== Левая часть =====
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        image_path = os.path.join(os.path.dirname(__file__), "name_plate_image.png")
        self.canvas = CanvasPanel(self, image_file=image_path, size=(600, 400))
        left_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 10)

        self.btn_ok = GenButton(self, label=loc.get("ok"), size=(140, 30))
        style_gen_button(self.btn_ok, "#2980b9", font_size=14)

        # ===== Правая часть =====
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

        for key, label_key in field_labels.items():
            lbl = wx.StaticText(self.data_box, label=loc.get(label_key, label_key))
            style_label(lbl)
            self.labels[key] = lbl

            txt = wx.TextCtrl(self.data_box)
            style_textctrl(txt)
            self.fields[key] = txt

            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(txt, 1, wx.EXPAND)

        data_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        right_sizer.Add(data_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- Кнопки ---
        self.btn_add = GenButton(self, label=loc.get("add"), size=(120, 30))
        self.btn_clear = GenButton(self, label=loc.get("clear"), size=(120, 30))
        self.btn_delete = GenButton(self, label=loc.get("delete"), size=(120, 30))

        style_gen_button(self.btn_add, "#27ae60", font_size=14)
        style_gen_button(self.btn_clear, "#e67e22", font_size=14)
        style_gen_button(self.btn_delete, "#c0392b", font_size=14)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        bottom.AddStretchSpacer()
        bottom.Add(self.btn_ok, 0, wx.RIGHT, 40)
        bottom.Add(self.btn_add, 0, wx.RIGHT, 5)
        bottom.Add(self.btn_clear, 0, wx.RIGHT, 5)
        bottom.Add(self.btn_delete, 0)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        content = wx.BoxSizer(wx.HORIZONTAL)
        content.Add(left_sizer, 2, wx.EXPAND)
        content.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 10)

        main_sizer.Add(content, 1, wx.EXPAND)
        main_sizer.Add(bottom, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)
        apply_styles_to_panel(self)

        # Bind
        self.listbox.Bind(wx.EVT_LISTBOX, self.on_select)
        self.btn_add.Bind(wx.EVT_BUTTON, self.on_add)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
    # ------------------------------------------------------------------
    # Вспомогательная логика
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

    def _is_name_unique(self, name: str) -> bool:
        for idx, item in enumerate(self.data):
            if item.get("name") == name:
                if self.current_index is None or idx != self.current_index:
                    return False
        return True

    # ------------------------------------------------------------------
    # Режимы
    # ------------------------------------------------------------------

    def _set_mode_add(self):
        self.current_index = None
        self.listbox.SetSelection(wx.NOT_FOUND)
        self.btn_add.SetLabel(loc.get("add"))
        self.btn_delete.Disable()

        self.Layout()
        self.Refresh()

    def _set_mode_edit(self, index: int):
        self.current_index = index
        self.btn_add.SetLabel(loc.get("edit"))
        self.btn_delete.Enable()

        self.Layout()
        self.Refresh()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_select(self, event):
        idx = event.GetSelection()
        if idx == wx.NOT_FOUND:
            return

        self._fill_fields(self.data[idx])
        self._set_mode_edit(idx)

    def on_add(self, _):
        record = self._collect_fields()
        errors = validate_record(record)
        if errors:
            show_popup("\n".join(errors), popup_type="error")
            return

        if not self._is_name_unique(record.get("name", "")):
            show_popup(loc.get("name_not_unique"), popup_type="error")
            return

        if self.current_index is None:
            self.data.append(record)
        else:
            self.data[self.current_index] = record

        save_nameplates(self.data)
        self._update_list()
        self.on_clear(None)

    def on_clear(self, _):
        for ctrl in self.fields.values():
            ctrl.SetValue("")
        self._set_mode_add()

    def on_delete(self, _):
        if self.current_index is None:
            return

        dlg = wx.MessageDialog(
            self,
            loc.get("confirm_delete"),
            loc.get("delete"),
            style=wx.YES_NO | wx.ICON_QUESTION,
        )

        if dlg.ShowModal() != wx.ID_YES:
            dlg.Destroy()
            return
        dlg.Destroy()

        self._last_deleted = (self.current_index, self.data[self.current_index])
        del self.data[self.current_index]

        save_nameplates(self.data)
        self._update_list()
        self.on_clear(None)

    def undo_delete(self):
        if not self._last_deleted:
            return

        idx, record = self._last_deleted
        self.data.insert(min(idx, len(self.data)), record)
        self._last_deleted = None

        save_nameplates(self.data)
        self._update_list()

    def _on_key(self, event):
        if event.ControlDown() and event.GetKeyCode() == ord("Z"):
            self.undo_delete()
        else:
            event.Skip()

    def on_ok(self, event=None, close_window: bool = True):
        parent = wx.GetTopLevelParent(self)

        if self.current_index is not None:
            # Передаём результат
            parent.selected_code = self.data[self.current_index].get("name", "")

        if hasattr(parent, "switch_content"):
            print("switch_content", parent.selected_code) # Debug
            parent.switch_content("content_apps")
        elif isinstance(parent, wx.Dialog):
            print("dialog", parent.selected_code) # Debug
            parent.EndModal(wx.ID_OK)
        else:
            # запасной вариант — просто закрыть фрейм, если ничего не подошло
            print("запасной вариант — просто закрыть фрейм, если ничего не подошло") # Debug
            parent.Close()


if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title=loc.get("list_label"), size=wx.Size(1200, 900))
    panel = NamePlateContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Show()
    app.MainLoop()


"""
plate_code = create_window(parent)

if plate_code:
    output_data["nameplate_code"] = plate_code
"""