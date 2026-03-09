# windows/at_entity_inspector.py

# -*- coding: utf-8 -*-
import wx


class EntityInspectorFrame(wx.Frame):
    """
    Простое окно просмотра свойств COM-объекта AutoCAD.
    Никаких JSON, состояния или зависимостей от BaseInputWindow.
    """

    def __init__(self, entity, parent=None):
        super().__init__(
            parent,
            title="Свойства объекта AutoCAD",
            size=wx.Size(900, 700),
            style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP
        )

        self.entity = entity

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Большое поле просмотра
        self.text_ctrl = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE |
                  wx.TE_READONLY |
                  wx.HSCROLL |
                  wx.TE_RICH2
        )

        font = wx.Font(
            14,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        )
        self.text_ctrl.SetFont(font)

        main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопка закрытия
        btn_close = wx.Button(panel, label="Закрыть")
        btn_close.Bind(wx.EVT_BUTTON, self.on_close)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(btn_close, 0, wx.ALL, 10)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND)

        panel.SetSizer(main_sizer)

        self.fill_data()
        self.Centre()
        self.Raise()
        self.SetFocus()

    # ---------------------------------------------------------
    # Заполнение данных
    # ---------------------------------------------------------

    def fill_data(self):

        obj = self.entity
        lines = []

        lines.append("=== ОСНОВНЫЕ СВОЙСТВА ===\n")

        base_props = [
            "ObjectName",
            "Layer",
            "Linetype",
            "LinetypeScale",
            "Lineweight",
            "Color",
            "Handle",
            "Visible"
        ]

        for p in base_props:
            try:
                lines.append(f"{p}: {getattr(obj, p)}")
            except Exception:
                pass

        lines.append("\n=== ГЕОМЕТРИЯ ===\n")

        try:
            name = obj.ObjectName

            if name == "AcDbPolyline":
                coords = list(obj.Coordinates)
                vertex_count = len(coords) // 2

                lines.append(f"VertexCount: {vertex_count}")
                lines.append(f"Length: {round(obj.Length, 3)}")
                lines.append(f"Area: {round(getattr(obj,'Area',0) / 1000000, 3)} м²")
                lines.append(f"Closed: {obj.Closed}")

                lines.append("\n=== ВЕРШИНЫ ===\n")
                lines.append(self.format_polyline_table(obj))

            elif name == "AcDbLine":
                lines.append(f"StartPoint: {list(obj.StartPoint)}")
                lines.append(f"EndPoint: {list(obj.EndPoint)}")
                lines.append(f"Length: {obj.Length}")

            elif name == "AcDbCircle":
                lines.append(f"Center: {list(obj.Center)}")
                lines.append(f"Radius: {obj.Radius}")
                lines.append(f"Area: {obj.Area / 1000000} м²")

            elif name == "AcDbArc":
                lines.append(f"Center: {list(obj.Center)}")
                lines.append(f"Radius: {obj.Radius}")
                lines.append(f"StartAngle: {obj.StartAngle}")
                lines.append(f"EndAngle: {obj.EndAngle}")
                lines.append(f"ArcLength: {obj.ArcLength}")

        except Exception as e:
            lines.append(f"Ошибка чтения геометрии: {e}")

        lines.append("\n=== ВСЕ ДОСТУПНЫЕ COM-СВОЙСТВА ===\n")

        exclude_props = {"Coordinates"}

        for attr in dir(obj):
            if attr.startswith("_") or attr in exclude_props:
                continue
            try:
                value = getattr(obj, attr)
                if not callable(value):
                    lines.append(f"{attr}: {value}")
            except Exception:
                pass

        self.text_ctrl.SetValue("\n".join(lines))

    # ---------------------------------------------------------
    # Закрытие
    # ---------------------------------------------------------

    def on_close(self, event):
        self.Destroy()

    def format_polyline_table(self, obj):
        """
        Формирует таблицу вершин полилинии:
        Idx | X | Y | Bulge
        """

        coords = list(obj.Coordinates)
        vertex_count = len(coords) // 2

        # Получаем bulge
        bulges = []
        for i in range(vertex_count):
            try:
                bulges.append(obj.GetBulge(i))
            except Exception:
                bulges.append(0.0)

        header = (
            "Idx |      X        |      Y        |   Bulge\n"
            "----+---------------+---------------+----------"
        )

        rows = []

        for i in range(vertex_count):
            x = round(coords[2 * i], 3)
            y = round(coords[2 * i + 1], 3)
            b = round(bulges[i], 3)

            rows.append(
                f"{i:>3} | "
                f"{x:>13.3f} | "
                f"{y:>13.3f} | "
                f"{b:>8.3f}"
            )

        return header + "\n" + "\n".join(rows)