import wx
from pathlib import Path

from config.at_config import ARROWS_IMAGE_PATH

# ============================================================
# CONFIG / STYLE
# Позже можно заменить значениями из конфига
# ============================================================

DEFAULT_CORNER_VALUE = 0

CELL_SIZE = (76, 58)
CELL_GAP = 4
WINDOW_PADDING = 12

NORMAL_FONT_SIZE = 12
OUTPUT_FONT_SIZE = 10

COLOR_FREE_BG = wx.Colour(245, 245, 245)
COLOR_FREE_FG = wx.Colour(30, 30, 30)

COLOR_ACTIVE_BG = wx.Colour(210, 235, 255)
COLOR_ACTIVE_FG = wx.Colour(0, 0, 0)

COLOR_BLOCKED_BG = wx.Colour(215, 215, 215)
COLOR_BLOCKED_FG = wx.Colour(120, 120, 120)

COLOR_ERROR_BG = wx.Colour(255, 220, 220)

BLOCKED_TEXT = "×"

BUTTON_LABEL_GET_VALUES = "Получить значения углов"
BUTTON_LABEL_CLEAR = "Сбросить всё"

# ============================================================
# IMAGE CONFIG
# ============================================================

# Относительный путь от текущей рабочей папки запуска.
# Потом можно заменить путём из конфига.
IMAGE_DIR = ARROWS_IMAGE_PATH

ICON_DRAW_SIZE = (32, 32)

ICON_FILES = {
    "00": "lt.png",
    "01": "lt+rt.png",
    "02": "rt.png",

    "10": "lt+lb.png",
    "11": "all.png",
    "12": "rt+rb.png",

    "20": "lb.png",
    "21": "lb+rb.png",
    "22": "rb.png",
}


# ============================================================
# CORNER LOGIC
# ============================================================

CELL_MASKS = {
    "00": {"lt"},
    "01": {"lt", "rt"},
    "02": {"rt"},

    "10": {"lt", "lb"},
    "11": {"lt", "rt", "lb", "rb"},
    "12": {"rt", "rb"},

    "20": {"lb"},
    "21": {"lb", "rb"},
    "22": {"rb"},
}

CELL_ORDER = [
    ["00", "01", "02"],
    ["10", "11", "12"],
    ["20", "21", "22"],
]

CORNER_NAMES = {
    "lt": "левый верхний",
    "rt": "правый верхний",
    "lb": "левый нижний",
    "rb": "правый нижний",
}


# ============================================================
# IMAGE HELPERS
# ============================================================

def load_bitmap(path: Path, size: tuple[int, int]) -> wx.Bitmap:
    if not path.exists():
        raise FileNotFoundError(f"Не найдена иконка: {path}")

    image = wx.Image(str(path), wx.BITMAP_TYPE_ANY)

    if not image.IsOk():
        raise ValueError(f"Не удалось загрузить изображение: {path}")

    image = image.Rescale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
    return wx.Bitmap(image)


def load_cell_bitmaps() -> dict[str, wx.Bitmap]:
    bitmaps = {}

    for code, filename in ICON_FILES.items():
        path = IMAGE_DIR / filename
        bitmaps[code] = load_bitmap(path, ICON_DRAW_SIZE)

    return bitmaps


# ============================================================
# CELL WIDGET
# ============================================================

class CornerCell(wx.Panel):
    def __init__(self, parent, code: str, bitmap: wx.Bitmap):
        super().__init__(
            parent,
            size=CELL_SIZE,
            style=wx.BORDER_SIMPLE,
        )

        self.code = code
        self.bitmap = bitmap

        self.bitmap_ctrl = wx.StaticBitmap(self, bitmap=self.bitmap)

        self.text_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_CENTER | wx.BORDER_NONE,
        )

        self.text_ctrl.Hide()

        self._build_ui()

    # --------------------------------------------------------

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.AddStretchSpacer()
        sizer.Add(self.bitmap_ctrl, 0, wx.ALIGN_CENTER)
        sizer.Add(self.text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        sizer.AddStretchSpacer()

        self.SetSizer(sizer)

    # --------------------------------------------------------

    def show_icon(self):
        self.text_ctrl.Hide()
        self.bitmap_ctrl.Show()
        self.Layout()

    # --------------------------------------------------------

    def show_text(self, value: str, editable: bool):
        self.bitmap_ctrl.Hide()
        self.text_ctrl.Show()

        if self.text_ctrl.GetValue() != value:
            self.text_ctrl.ChangeValue(value)

        self.text_ctrl.SetEditable(editable)
        self.Layout()

    # --------------------------------------------------------

    def set_state_colors(self, bg: wx.Colour, fg: wx.Colour):
        self.SetBackgroundColour(bg)

        self.text_ctrl.SetBackgroundColour(bg)
        self.text_ctrl.SetForegroundColour(fg)

        self.bitmap_ctrl.SetBackgroundColour(bg)

        self.Refresh()
        self.text_ctrl.Refresh()
        self.bitmap_ctrl.Refresh()

    # --------------------------------------------------------

    def set_text_font(self, font: wx.Font):
        self.text_ctrl.SetFont(font)


# ============================================================
# MAIN PANEL
# ============================================================

class CornerPlatePanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.values: dict[str, str] = {}
        self.cells: dict[str, CornerCell] = {}

        self.normal_font = wx.Font(
            NORMAL_FONT_SIZE,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )

        self.output_font = wx.Font(
            OUTPUT_FONT_SIZE,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        )

        self.bitmaps = load_cell_bitmaps()

        self._build_ui()
        self.refresh_cells()
        self.print_current_values()

    # --------------------------------------------------------

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        grid = wx.GridSizer(
            rows=3,
            cols=3,
            vgap=CELL_GAP,
            hgap=CELL_GAP,
        )

        for row in CELL_ORDER:
            for code in row:
                cell = CornerCell(
                    self,
                    code=code,
                    bitmap=self.bitmaps[code],
                )

                cell.SetMinSize(CELL_SIZE)
                cell.SetToolTip(self._get_tooltip(code))
                cell.set_text_font(self.normal_font)

                cell.Bind(wx.EVT_LEFT_DOWN, lambda evt, c=code: self.on_cell_click(evt, c))
                cell.bitmap_ctrl.Bind(wx.EVT_LEFT_DOWN, lambda evt, c=code: self.on_cell_click(evt, c))
                cell.text_ctrl.Bind(wx.EVT_LEFT_DOWN, lambda evt, c=code: self.on_cell_click(evt, c))

                cell.Bind(wx.EVT_LEFT_DCLICK, lambda evt, c=code: self.clear_cell(c))
                cell.bitmap_ctrl.Bind(wx.EVT_LEFT_DCLICK, lambda evt, c=code: self.clear_cell(c))
                cell.text_ctrl.Bind(wx.EVT_LEFT_DCLICK, lambda evt, c=code: self.clear_cell(c))

                cell.text_ctrl.Bind(wx.EVT_TEXT, lambda evt, c=code: self.on_text_changed(evt, c))
                cell.text_ctrl.Bind(wx.EVT_KEY_DOWN, lambda evt, c=code: self.on_key_down(evt, c))

                self.cells[code] = cell
                grid.Add(cell, 0, wx.EXPAND)

        root.Add(grid, 0, wx.ALL, WINDOW_PADDING)

        buttons = wx.BoxSizer(wx.HORIZONTAL)

        btn_get = wx.Button(self, label=BUTTON_LABEL_GET_VALUES)
        btn_clear = wx.Button(self, label=BUTTON_LABEL_CLEAR)

        btn_get.Bind(wx.EVT_BUTTON, self.on_get_values)
        btn_clear.Bind(wx.EVT_BUTTON, self.on_clear_all)

        buttons.Add(btn_get, 0, wx.RIGHT, 8)
        buttons.Add(btn_clear, 0)

        root.Add(buttons, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, WINDOW_PADDING)

        self.output = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(340, 105),
        )
        self.output.SetFont(self.output_font)

        root.Add(
            self.output,
            0,
            wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND,
            WINDOW_PADDING,
        )

        self.SetSizer(root)

    # --------------------------------------------------------

    def _get_tooltip(self, code: str) -> str:
        corners = ", ".join(CORNER_NAMES[c] for c in CELL_MASKS[code])
        return f"{code}: {corners}"

    # --------------------------------------------------------

    def get_occupied_corners(self) -> set[str]:
        occupied = set()

        for code in self.values:
            occupied |= CELL_MASKS[code]

        return occupied

    # --------------------------------------------------------

    def is_blocked(self, code: str) -> bool:
        if code in self.values:
            return False

        occupied = self.get_occupied_corners()
        return bool(occupied & CELL_MASKS[code])

    # --------------------------------------------------------

    def is_single_corner(self, code: str) -> bool:
        return len(CELL_MASKS[code]) == 1

    # --------------------------------------------------------

    def activate_cell(self, code: str):
        if self.is_blocked(code):
            return

        if code not in self.values:
            self.values[code] = ""

        self.refresh_cells()

        cell = self.cells[code]
        cell.text_ctrl.SetFocus()
        cell.text_ctrl.SelectAll()

    # --------------------------------------------------------

    def clear_cell(self, code: str):
        if code in self.values:
            del self.values[code]

        self.refresh_cells()
        self.print_current_values()

    # --------------------------------------------------------

    def clear_all(self):
        self.values.clear()
        self.refresh_cells()
        self.print_current_values()

    # --------------------------------------------------------

    def refresh_cells(self):
        for code, cell in self.cells.items():
            active = code in self.values
            blocked = self.is_blocked(code)

            cell.Freeze()

            if active:
                value = str(self.values[code])

                cell.Enable(True)
                cell.show_text(value, editable=True)
                cell.set_state_colors(COLOR_ACTIVE_BG, COLOR_ACTIVE_FG)

            elif blocked:
                cell.Enable(False)
                cell.show_text(BLOCKED_TEXT, editable=False)
                cell.set_state_colors(COLOR_BLOCKED_BG, COLOR_BLOCKED_FG)

            else:
                cell.Enable(True)

                if self.is_single_corner(code):
                    cell.show_text(str(DEFAULT_CORNER_VALUE), editable=False)
                else:
                    cell.show_icon()

                cell.set_state_colors(COLOR_FREE_BG, COLOR_FREE_FG)

            cell.Thaw()
            cell.Refresh()

    # --------------------------------------------------------

    def on_cell_click(self, event, code: str):
        if code in self.values:
            event.Skip()
            return

        self.activate_cell(code)

    # --------------------------------------------------------

    def on_text_changed(self, event, code: str):
        if code in self.values:
            self.values[code] = self.cells[code].text_ctrl.GetValue()
            self.print_current_values()

        event.Skip()

    # --------------------------------------------------------

    def on_key_down(self, event, code: str):
        key = event.GetKeyCode()

        if key == wx.WXK_ESCAPE:
            self.clear_cell(code)
            return

        if key == wx.WXK_RETURN:
            self.print_current_values()
            return

        event.Skip()

    # --------------------------------------------------------

    def on_get_values(self, event):
        self.print_current_values()

    # --------------------------------------------------------

    def on_clear_all(self, event):
        self.clear_all()

    # --------------------------------------------------------

    def get_corner_values(self) -> dict[str, str | int]:
        result = {
            "lt": DEFAULT_CORNER_VALUE,
            "rt": DEFAULT_CORNER_VALUE,
            "lb": DEFAULT_CORNER_VALUE,
            "rb": DEFAULT_CORNER_VALUE,
        }

        for code, value in self.values.items():
            if value == "":
                continue

            for corner in CELL_MASKS[code]:
                result[corner] = value

        return result

    # --------------------------------------------------------

    def print_current_values(self):
        values = self.get_corner_values()

        text = (
            "Итоговые значения углов:\n"
            f"lt = {values['lt']}\n"
            f"rt = {values['rt']}\n"
            f"lb = {values['lb']}\n"
            f"rb = {values['rb']}\n\n"
            f"Активные ячейки: {self.values}"
        )

        self.output.SetValue(text)


# ============================================================
# TEST WINDOW
# ============================================================

class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(
            None,
            title="Тест ввода значений углов",
            size=wx.Size(400, 405),
            style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER,
        )

        panel = CornerPlatePanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.Centre()


class TestApp(wx.App):
    def OnInit(self):
        frame = TestFrame()
        frame.Show()
        return True


if __name__ == "__main__":
    app = TestApp(False)
    app.MainLoop()