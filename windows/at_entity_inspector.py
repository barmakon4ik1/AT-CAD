# -*- coding: utf-8 -*-
import math
from typing import Optional

import wx
import wx.propgrid as pg
import pythoncom
import pywintypes
import time

from locales.at_translations import loc
from windows.at_window_utils import (
    apply_styles_to_panel,
    show_popup,
    load_user_settings,
    get_wx_color_from_value
)
from windows.at_fields_builder import FieldBuilder, FormBuilder
from config.at_cad_init import ATCadInit


# =========================================================
# Локализация
# =========================================================

TRANSLATIONS = {
    "title": {"ru": "Свойства объекта AutoCAD", "de": "Objekteigenschaften", "en": "Object properties"},
    "select_button": {"ru": "Выбрать примитив", "de": "Objekt wählen", "en": "Select entity"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "cancel_button": {"ru": "Закрыть", "de": "Close", "en": "Exit"},
    "no_object": {"ru": "Объект не выбран", "de": "Kein Objekt gewählt", "en": "No object selected"},
    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "types": {"ru": "Типы объектов", "de": "Objekttypen", "en": "Object types"},
    "geometry": {"ru": "ГЕОМЕТРИЯ", "de": "GEOMETRIE", "en": "GEOMETRY"},
    "vertices": {"ru": "ВЕРШИНЫ", "de": "PUNKTE", "en": "VERTICES"},
    "totals": {"ru": "ИТОГИ", "de": "SUMMEN", "en": "TOTALS"},
    "objects": {"ru": "Объекты", "de": "Objekte", "en": "Objects"},
    "total_length": {"ru": "Суммарная длина", "de": "Gesamtlänge", "en": "Total length"},
    "total_area": {"ru": "Суммарная площадь", "de": "Gesamtfläche", "en": "Total area"},
}

loc.register_translations(TRANSLATIONS)

ALLOWED_TYPES = {
    "AcDbLine",
    "AcDbPolyline",
    "AcDbCircle",
    "AcDbArc"
}

# =========================================================
# Диалог
# =========================================================

class EntityInspectorDialog(wx.Dialog):

    def __init__(self, parent=None):

        super().__init__(
            parent,
            title=loc.get("title"),
            size=wx.Size(500, 800),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP
        )

        self.pg = None
        self.text = None
        settings = load_user_settings()
        self.SetBackgroundColour(
            get_wx_color_from_value(settings.get("BACKGROUND_COLOR"))
        )
        self.objects = []
        self.entity = None

        self.setup_ui()

    # -----------------------------------------------------

    def setup_ui(self):

        main = wx.BoxSizer(wx.VERTICAL)

        # ===== Верх: PropertyGrid =====
        self.pg = pg.PropertyGrid(
            self,
            style=pg.PG_SPLITTER_AUTO_CENTER
        )

        main.Add(self.pg, 1, wx.EXPAND | wx.ALL, 8)

        # ===== Низ: текстовый вывод =====
        self.text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE |
                  wx.TE_READONLY |
                  wx.HSCROLL
        )

        font = wx.Font(
            14,
            wx.FONTFAMILY_MODERN,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
            faceName="Consolas"
        )
        self.text.SetFont(font)

        main.Add(self.text, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ===== Кнопки через FieldBuilder =====

        btn_panel = wx.Panel(self)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        form = FormBuilder(btn_panel)
        fb = FieldBuilder(btn_panel, btn_sizer, form=form)

        fb.universal_row(
            None,
            [
                {
                    "type": "button",
                    "label": loc.get("select_button"),
                    "callback": self.on_select,
                    "size": (200, 45)
                },
                {
                    "type": "button",
                    "label": loc.get("clear_button"),
                    "callback": self.on_clear,
                    "size": (150, 45)
                },
                {
                    "type": "button",
                    "label": loc.get("cancel_button"),
                    "callback": self.on_cancel,
                    "size": (150, 45)
                },
            ],
            align_right=True
        )

        btn_panel.SetSizer(btn_sizer)
        main.Add(btn_panel, 0, wx.EXPAND | wx.ALL, 6)

        self.SetSizer(main)

        apply_styles_to_panel(self)

    # =====================================================
    # КНОПКИ
    # =====================================================

    def on_select(self, _):

        try:
            pythoncom.CoInitialize()

            cad = ATCadInit()
            doc = cad.document

            new_objs = self.select_objects(doc)

            if not new_objs:
                show_popup(loc.get("no_object"))
                return

            # --- накопление без дублей ---
            existing = {o.Handle for o in self.objects}

            for obj in new_objs:
                if obj.Handle not in existing:
                    self.objects.append(obj)

            self.inspect_objects(self.objects)

        except Exception as e:
            show_popup(f"{loc.get('error')}: {e}", popup_type="error")

    # -----------------------------------------------------

    def on_clear(self, event):

        self.objects = []

        self.pg.Clear()
        self.text.Clear()

    # -----------------------------------------------------

    def on_cancel(self, _):
        self.EndModal(wx.ID_CANCEL)

    # =====================================================
    # ВЫБОР ОБЪЕКТА
    # =====================================================

    def select_objects(self, doc):

        sel_name = "PY_TMP_SEL"

        try:
            doc.SelectionSets.Item(sel_name).Delete()
        except:
            pass

        sel = doc.SelectionSets.Add(sel_name)

        self.Enable(False)
        sel.SelectOnScreen()
        self.Enable(True)
        self.Raise()

        def com_retry(func):
            for _ in range(10):
                try:
                    return func()
                except pywintypes.com_error as e:
                    if e.args[0] == -2147418111:
                        time.sleep(0.1)
                        continue
                    raise
            return None

        count = com_retry(lambda: sel.Count)

        if not count:
            return []

        result = []

        for i in range(count):

            obj = com_retry(lambda i=i: sel.Item(i))

            try:
                if obj.ObjectName in ALLOWED_TYPES:
                    result.append(obj)
            except:
                pass

        return result

    # =====================================================
    # ИНСПЕКТОР
    # =====================================================

    @staticmethod
    def get_common_property(objs, prop):

        values = set()

        for obj in objs:
            try:
                values.add(getattr(obj, prop))
            except:
                pass

        if len(values) == 1:
            return values.pop()

        return "<разные>"

    def inspect_objects(self, objs):

        self.pg.Clear()
        self.text.Clear()

        first = objs[0]
        single_mode = len(objs) == 1

        # ---------- Общие свойства ----------
        self.pg.Append(pg.PropertyCategory("Group"))

        group_props = ["Layer", "Color", "Linetype"]

        for p in group_props:
            val = self.get_common_property(objs, p)
            self.pg.Append(pg.StringProperty(p, value=str(val)))

        # ---------- Суммарные данные ----------
        total_length = 0.0
        total_area = 0.0

        lines = []

        lines.append(f"=== {loc.get('totals')} ===")
        lines.append(f"{loc.get('objects')}: {len(objs)}")

        for obj in objs:

            try:
                name = obj.ObjectName

                if name in ("AcDbLine",):
                    total_length += obj.Length

                elif name == "AcDbPolyline":
                    total_length += obj.Length
                    total_area += getattr(obj, "Area", 0)

                elif name == "AcDbArc":
                    total_length += obj.ArcLength

                elif name == "AcDbCircle":
                    total_area += obj.Area
                    total_length += 2 * math.pi * obj.Radius

            except:
                pass

        lines.append(f"{loc.get('total_length')}: {round(total_length, 3)} мм")

        if total_area:
            lines.append(
                f"{loc.get('total_area')}: "
                f"{round(total_area / 1_000_000, 3)} м²"
            )

        # ---------- Распределение по типам ----------
        type_counts = {}

        for obj in objs:
            try:
                name = obj.ObjectName
                type_counts[name] = type_counts.get(name, 0) + 1
            except:
                pass

        lines.append("")
        lines.append(loc.get("types") + ":")

        for k, v in type_counts.items():
            lines.append(f"  {k}: {v}")

        # ---------- Геометрия (только для одного объекта) ----------
        if single_mode:

            lines.append("")
            lines.append(f"=== {loc.get('geometry')} ===")

            try:
                name = first.ObjectName

                if name == "AcDbPolyline":

                    coords = list(first.Coordinates)
                    vc = len(coords) // 2

                    lines.append(f"VertexCount: {vc}")
                    lines.append(f"Length: {round(first.Length, 3)}")
                    lines.append(
                        f"Area: {round(getattr(first, 'Area', 0) / 1_000_000, 3)} м²"
                    )
                    lines.append(f"Closed: {first.Closed}")

                    lines.append("")
                    lines.append(f"=== {loc.get('vertices')} ===")
                    lines.append(self.format_polyline_table(first))

                elif name == "AcDbLine":

                    lines.append(f"StartPoint: {list(first.StartPoint)}")
                    lines.append(f"EndPoint: {list(first.EndPoint)}")
                    lines.append(f"Length: {round(first.Length, 3)}")

                elif name == "AcDbCircle":

                    lines.append(f"Center: {list(first.Center)}")
                    lines.append(f"Radius: {first.Radius}")
                    lines.append(
                        f"Area: {round(first.Area / 1_000_000, 3)} м²"
                    )

                elif name == "AcDbArc":

                    lines.append(f"Center: {list(first.Center)}")
                    lines.append(f"Radius: {first.Radius}")
                    lines.append(f"StartAngle: {first.StartAngle}")
                    lines.append(f"EndAngle: {first.EndAngle}")
                    lines.append(f"ArcLength: {round(first.ArcLength, 3)}")

            except Exception as e:
                lines.append(f"Ошибка геометрии: {e}")

        # ---------- Все свойства первого ----------
        if single_mode:

            self.pg.Append(pg.PropertyCategory("All Properties"))

            for attr in dir(first):

                if attr.startswith("_") or attr == "Coordinates":
                    continue

                try:
                    val = getattr(first, attr)

                    if callable(val):
                        continue

                    self.pg.Append(pg.StringProperty(attr, value=str(val)))

                except:
                    pass

        self.text.SetValue("\n".join(lines))

    # =====================================================
    # ТАБЛИЦА ВЕРШИН
    # =====================================================

    def format_polyline_table(self, obj):

        coords = list(obj.Coordinates)
        count = len(coords) // 2

        bulges = []
        for i in range(count):
            try:
                bulges.append(obj.GetBulge(i))
            except:
                bulges.append(0.0)

        header = (
            "Idx |           X         |           Y         |   Bulge\n"
            "----+---------------+---------------+----------"
        )

        rows = []

        for i in range(count):
            x = coords[2 * i]
            y = coords[2 * i + 1]
            b = bulges[i]

            rows.append(
                f"{i:>3} | "
                f"{x:>13.3f} | "
                f"{y:>13.3f} | "
                f"{b:>8.3f}"
            )

        return header + "\n" + "\n".join(rows)


# =========================================================
# Вызов
# =========================================================

def show_entity_inspector(parent=None):
    dlg = EntityInspectorDialog(parent)
    dlg.ShowModal()
    dlg.Destroy()


# =========================================================
# Вызов диалога из главного окна
# =========================================================
def open_dialog(parent=None, data=None) -> int | None:
    dlg = EntityInspectorDialog(parent)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result



# =========================================================
# Тест
# =========================================================

if __name__ == "__main__":
    app = wx.App(False)
    show_entity_inspector()
    app.MainLoop()