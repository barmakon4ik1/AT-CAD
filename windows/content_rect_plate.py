"""
windows/content_rect_plate.py

Панель ввода параметров прямоугольной пластины AT-CAD.

Назначение
----------
Модуль отвечает только за GUI-ввод, предпросмотр и формирование чистого словаря
``plate_data`` для ``programs/at_rect_plate.py``. Построение в AutoCAD здесь
намеренно не выполняется.

Компоновка
----------
Слева расположен интерактивный предпросмотр, справа — панель ввода. Пропорция
левой и правой частей 2:1. В правой части всегда видны:

    1. Основные данные: заказ/деталь, материал, толщина.
    2. Внешний контур: ширина, высота.
    3. Три переключающие кнопки секций:
       - углы;
       - симметричные отверстия;
       - произвольные отверстия.
    4. Стандартная нижняя панель кнопок ОК / Очистить / Возврат.

Секции углов и отверстий показываются взаимоисключающе, как в модуле мостиков:
это не перегружает правую панель и сохраняет рабочий размер окна.

Соглашение по углам
-------------------
Формат значений совпадает с ``programs.at_rect_plate.RectPlate``:

    0       -> острый угол;
    r > 0   -> скругление радиусом r;
    r < 0   -> симметричная фаска abs(r) x abs(r);
    a;b     -> асимметричная фаска (a, b).

Соглашение по отверстиям
------------------------
На выходе все отверстия приводятся к обычному списку:

    circle: {"type": "circle", "cx": x, "cy": y, "r": d / 2}
    slot:   {"type": "slot", "cx": x, "cy": y, "length": L, "diameter": D, "angle": A}

Симметрия разворачивается в этом окне. Модуль построения получает уже готовые
координаты отверстий и ничего не знает о режиме ввода.

Режимы запуска
--------------
Встроенный режим:
    create_window(parent)

Тестовый режим:
    python windows/content_rect_plate.py
"""

from __future__ import annotations

import math
from pathlib import Path
from pprint import pprint
from typing import Any, Callable, Optional

import wx
import wx.grid as gridlib

# ----------------------------------------------------------------------
# Проектные импорты
# ----------------------------------------------------------------------
from config.at_config import (
    ARROWS_IMAGE_PATH,
    BUTTON_SIZE,
    DEFAULT_SETTINGS,
)
from locales.at_translations import loc
from windows.at_fields_builder import FieldBuilder, FormBuilder, parse_float
from windows.at_gui_utils import show_popup
from windows.at_window_utils import (
    BaseContentPanel,
    apply_styles_to_panel,
    get_wx_color_from_value,
    load_common_data,
    load_user_settings,
)

try:
    from windows.slotted_hole_dialog import open_dialog as open_slotted_hole_dialog
except Exception:
    open_slotted_hole_dialog = None


# ----------------------------------------------------------------------
# Локальные переводы
# ----------------------------------------------------------------------
TRANSLATIONS = {
    "cancel_button": {"ru": "Возврат", "de": "Zurück", "en": "Return"},
    "clear_button": {"ru": "Очистить", "de": "Löschen", "en": "Clear"},
    "ok_button": {"ru": "ОК", "de": "OK", "en": "OK"},

    "error": {"ru": "Ошибка", "de": "Fehler", "en": "Error"},
    "main_data": {"ru": "Основные данные", "de": "Hauptdaten", "en": "Main data"},
    "order_label": {"ru": "К-№", "de": "K-Nr.", "en": "Order no."},
    "material_label": {"ru": "Материал", "de": "Material", "en": "Material"},
    "thickness_label": {"ru": "Толщина S, мм", "de": "Dicke S, mm", "en": "Thickness S, mm"},

    "outer_contour": {"ru": "Внешний контур", "de": "Außenkontur", "en": "Outer contour"},
    "width_label": {"ru": "Ширина W, мм", "de": "Breite W, mm", "en": "Width W, mm"},
    "height_label": {"ru": "Высота H, мм", "de": "Höhe H, mm", "en": "Height H, mm"},

    "corners_label": {"ru": "Углы", "de": "Ecken", "en": "Corners"},
    "symmetric_holes": {"ru": "Симметричные отверстия", "de": "Symmetrische Bohrungen", "en": "Symmetric holes"},
    "free_holes": {"ru": "Произвольные отверстия", "de": "Freie Bohrungen", "en": "Free holes"},

    "corner_help": {
        "ru": "0 — острый; 25 — R25; -10 — фаска 10x10; 10;20 — асимметричная фаска.",
        "de": "0 — scharf; 25 — R25; -10 — Fase 10x10; 10;20 — asymmetrische Fase.",
        "en": "0 — sharp; 25 — R25; -10 — chamfer 10x10; 10;20 — asymmetric chamfer.",
    },

    "hole_type": {"ru": "Тип отверстия", "de": "Bohrungstyp", "en": "Hole type"},
    "circle": {"ru": "Круглое", "de": "Rund", "en": "Circle"},
    "slot": {"ru": "Продолговатое", "de": "Langloch", "en": "Slot"},
    "holes_count": {"ru": "Количество", "de": "Anzahl", "en": "Count"},
    "symmetry_axis": {"ru": "Симметрия", "de": "Symmetrie", "en": "Symmetry"},
    "symmetry_none": {"ru": "без симметрии", "de": "ohne Symmetrie", "en": "none"},
    "symmetry_x": {"ru": "относительно X", "de": "zur X-Achse", "en": "about X"},
    "symmetry_y": {"ru": "относительно Y", "de": "zur Y-Achse", "en": "about Y"},
    "symmetry_xy": {"ru": "относительно X и Y", "de": "zur X- und Y-Achse", "en": "about X and Y"},

    "diameter_label": {"ru": "Диаметр D, мм", "de": "Durchmesser D, mm", "en": "Diameter D, mm"},
    "offset_x_label": {"ru": "X от центра, мм", "de": "X von Mitte, mm", "en": "X from center, mm"},
    "offset_y_label": {"ru": "Y от центра, мм", "de": "Y von Mitte, mm", "en": "Y from center, mm"},
    "slot_params": {"ru": "Параметры паза...", "de": "Langlochparameter...", "en": "Slot params..."},
    "slot_params_short": {"ru": "Паз", "de": "Langloch", "en": "Slot"},

    "axis_legend": {
        "ru": "Оси предпросмотра: X — горизонтально, Y — вертикально. Координаты отверстий задаются от центра.",
        "de": "Vorschauachsen: X horizontal, Y vertikal. Koordinaten ab Plattenmitte.",
        "en": "Preview axes: X horizontal, Y vertical. Coordinates are from plate center.",
    },
    "free_holes_hint": {
        "ru": "Каждая строка — отдельное отверстие. circle: D. slot: D, L и A°.",
        "de": "Jede Zeile ist eine Bohrung. circle: D. slot: D, L und A°.",
        "en": "Each row is one hole. circle: D. slot: D, L and A°.",
    },

    "col_type": {"ru": "Тип", "de": "Typ", "en": "Type"},
    "col_x": {"ru": "X", "de": "X", "en": "X"},
    "col_y": {"ru": "Y", "de": "Y", "en": "Y"},
    "col_d": {"ru": "D", "de": "D", "en": "D"},
    "col_l": {"ru": "L", "de": "L", "en": "L"},
    "col_angle": {"ru": "A°", "de": "A°", "en": "A°"},

    "no_data_error": {
        "ru": "Необходимо ввести ширину и высоту пластины",
        "de": "Breite und Höhe der Platte müssen eingegeben werden",
        "en": "Plate width and height are required",
    },
    "invalid_dimensions": {
        "ru": "Ширина и высота должны быть больше 0",
        "de": "Breite und Höhe müssen größer 0 sein",
        "en": "Width and height must be greater than 0",
    },
    "invalid_number_format_error": {"ru": "Неверный формат числа", "de": "Ungültiges Zahlenformat", "en": "Invalid number format"},
    "corner_too_large": {
        "ru": "Размер угла больше допустимого для этой пластины",
        "de": "Eckgröße ist für diese Platte zu groß",
        "en": "Corner value is too large for this plate",
    },
    "hole_error": {"ru": "Проверьте параметры отверстий", "de": "Bohrungsparameter prüfen", "en": "Check hole parameters"},
    "slot_dialog_unavailable": {
        "ru": "Диалог продолговатого отверстия недоступен",
        "de": "Langlochdialog ist nicht verfügbar",
        "en": "Slotted-hole dialog is unavailable",
    },
    "slot_params_missing": {
        "ru": "Не заданы параметры продолговатого отверстия",
        "de": "Langlochparameter fehlen",
        "en": "Slot parameters are missing",
    },
    "result_debug": {"ru": "Данные пластины", "de": "Plattendaten", "en": "Plate data"},
}
loc.register_translations(TRANSLATIONS)


# ----------------------------------------------------------------------
# Централизованные настройки оформления
# ----------------------------------------------------------------------
DEFAULT_CORNER_VALUE = 0

PREVIEW_SIZE = (760, 560)
RIGHT_PANEL_MIN_WIDTH = 390

CELL_SIZE = (72, 54)
CELL_GAP = 4
WINDOW_PADDING = 10
SECTION_BUTTON_SIZE = wx.Size(120, -1)
SUBPANEL_INPUT_SIZE = (130, -1)

NORMAL_FONT_SIZE = int(DEFAULT_SETTINGS.get("FONT_SIZE", 10))

COLOR_FREE_BG = wx.Colour(245, 245, 245)
COLOR_FREE_FG = wx.Colour(30, 30, 30)
COLOR_ACTIVE_BG = wx.Colour(210, 235, 255)
COLOR_ACTIVE_FG = wx.Colour(0, 0, 0)
COLOR_BLOCKED_BG = wx.Colour(215, 215, 215)
COLOR_BLOCKED_FG = wx.Colour(120, 120, 120)
COLOR_PREVIEW_BG = wx.Colour(255, 255, 255)
COLOR_PREVIEW_FG = wx.Colour(30, 30, 30)
COLOR_PREVIEW_AUX = wx.Colour(150, 150, 150)

BLOCKED_TEXT = "×"

IMAGE_DIR = Path(ARROWS_IMAGE_PATH)
ICON_DRAW_SIZE = (30, 30)

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

CORNER_ORDER = ("rb", "rt", "lt", "lb")
CORNER_NAMES = {"lt": "LT", "rt": "RT", "lb": "LB", "rb": "RB"}


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def create_window(parent: wx.Window) -> Optional[wx.Panel]:
    """Создаёт панель прямоугольной пластины для главного окна проекта."""
    try:
        return RectPlateContentPanel(parent)
    except Exception as e:
        show_popup(loc.get("error") + f": {e}", popup_type="error")
        return None


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------
def _to_float(value: Any, allow_empty: bool = False, default: float = 0.0) -> float:
    """Парсит число с поддержкой запятой как десятичного разделителя."""
    if value is None or str(value).strip() == "":
        if allow_empty:
            return default
        raise ValueError(loc.get("invalid_number_format_error"))
    return parse_float(value)


def _create_static_text(parent: wx.Window, text: str) -> wx.StaticText:
    label = wx.StaticText(parent, label=text)
    label.SetFont(wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    return label


def load_bitmap(path: Path, size: tuple[int, int]) -> wx.Bitmap:
    """Загружает PNG-иконку и масштабирует её под ячейку."""
    if not path.exists():
        # В тестовом режиме без ресурсов возвращаем пустой bitmap.
        bmp = wx.Bitmap(size[0], size[1])
        dc = wx.MemoryDC(bmp)
        dc.SetBackground(wx.Brush(wx.Colour(245, 245, 245)))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bmp

    image = wx.Image(str(path), wx.BITMAP_TYPE_ANY)
    if not image.IsOk():
        raise ValueError(f"Не удалось загрузить изображение: {path}")
    image = image.Rescale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
    return wx.Bitmap(image)


def load_cell_bitmaps() -> dict[str, wx.Bitmap]:
    """Загружает все иконки матрицы углов."""
    return {code: load_bitmap(IMAGE_DIR / filename, ICON_DRAW_SIZE) for code, filename in ICON_FILES.items()}


def parse_corner_value(value: Any) -> float | tuple[float, float] | int:
    """Преобразует текст ячейки угла в формат ``programs.at_rect_plate``."""
    text = str(value).strip().replace(",", ".")
    if text == "":
        return DEFAULT_CORNER_VALUE

    if ";" in text:
        a_str, b_str = text.split(";", 1)
        a = float(a_str.strip())
        b = float(b_str.strip())
        if a <= 0 or b <= 0:
            raise ValueError(loc.get("invalid_number_format_error"))
        return (a, b)

    value_float = float(text)
    if abs(value_float) < 1e-12:
        return 0
    return value_float


def corner_abs_limit_value(value: float | tuple[float, float] | int) -> float:
    """Возвращает максимальный линейный размер угла для быстрой проверки."""
    if isinstance(value, tuple):
        return max(abs(float(value[0])), abs(float(value[1])))
    return abs(float(value))


# ----------------------------------------------------------------------
# Панель предпросмотра
# ----------------------------------------------------------------------
class RectPlatePreviewPanel(wx.Panel):
    """
    Интерактивный предпросмотр пластины.

    Панель не выполняет точные CAD-расчёты. Её задача — быстро показать общую
    форму: прямоугольник, скругления/фаски и отверстия. Подписи размеров в
    предпросмотре не выводятся, чтобы не съедать рабочую область.
    """

    def __init__(self, parent: wx.Window):
        super().__init__(parent, size=PREVIEW_SIZE, style=wx.BORDER_SIMPLE)
        self.width_value = 300.0
        self.height_value = 180.0
        self.corners: dict[str, float | tuple[float, float] | int] = {k: 0 for k in CORNER_ORDER}
        self.holes: list[dict[str, Any]] = []
        self.SetBackgroundColour(COLOR_PREVIEW_BG)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def update_preview(
        self,
        width_value: Optional[float],
        height_value: Optional[float],
        corners: Optional[dict[str, Any]] = None,
        holes: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        if width_value and width_value > 0:
            self.width_value = float(width_value)
        if height_value and height_value > 0:
            self.height_value = float(height_value)
        if corners is not None:
            self.corners = corners
        if holes is not None:
            self.holes = holes
        self.Refresh()

    def on_paint(self, _event: wx.PaintEvent):
        dc = wx.PaintDC(self)
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if gc:
            self._draw(gc)

    def _draw(self, gc: wx.GraphicsContext) -> None:
        client_w, client_h = self.GetClientSize()
        margin = 36

        w = max(self.width_value, 1.0)
        h = max(self.height_value, 1.0)

        scale = min((client_w - 2 * margin) / w, (client_h - 2 * margin) / h)
        draw_w = w * scale
        draw_h = h * scale
        x = (client_w - draw_w) / 2
        y = (client_h - draw_h) / 2

        gc.SetPen(wx.Pen(COLOR_PREVIEW_FG, 2))
        gc.SetBrush(wx.Brush(wx.Colour(245, 250, 255), wx.BRUSHSTYLE_TRANSPARENT))
        gc.StrokePath(self._build_preview_path(gc, x, y, draw_w, draw_h, scale))

        # Оси X/Y. Только легенда осей, без размерных надписей.
        gc.SetPen(wx.Pen(COLOR_PREVIEW_AUX, 1, wx.PENSTYLE_DOT))
        cx = x + draw_w / 2
        cy = y + draw_h / 2
        gc.StrokeLine(x, cy, x + draw_w, cy)
        gc.StrokeLine(cx, y, cx, y + draw_h)

        gc.SetFont(
            wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
            COLOR_PREVIEW_AUX,
        )
        gc.DrawText("X", x + draw_w - 16, cy + 4)
        gc.DrawText("Y", cx + 4, y + 4)

        self._draw_holes(gc, x, y, draw_w, draw_h, scale)

    def _corner_size_px(self, key: str, scale: float) -> float:
        value = self.corners.get(key, 0)
        return min(corner_abs_limit_value(value) * scale, 80.0)

    def _build_preview_path(self, gc: wx.GraphicsContext, x: float, y: float, w: float, h: float, scale: float):
        r_lt = self._corner_size_px("lt", scale)
        r_rt = self._corner_size_px("rt", scale)
        r_rb = self._corner_size_px("rb", scale)
        r_lb = self._corner_size_px("lb", scale)

        path = gc.CreatePath()
        path.MoveToPoint(x + r_lt, y)
        path.AddLineToPoint(x + w - r_rt, y)
        self._add_corner(path, "rt", x + w, y, r_rt, "top_right")
        path.AddLineToPoint(x + w, y + h - r_rb)
        self._add_corner(path, "rb", x + w, y + h, r_rb, "bottom_right")
        path.AddLineToPoint(x + r_lb, y + h)
        self._add_corner(path, "lb", x, y + h, r_lb, "bottom_left")
        path.AddLineToPoint(x, y + r_lt)
        self._add_corner(path, "lt", x, y, r_lt, "top_left")
        path.CloseSubpath()
        return path

    def _add_corner(self, path, key: str, cx: float, cy: float, r: float, pos: str) -> None:
        value = self.corners.get(key, 0)
        is_round = isinstance(value, (int, float)) and float(value) > 0

        if r <= 0:
            path.AddLineToPoint(cx, cy)
            return

        if pos == "top_right":
            end = (cx, cy + r)
            ctrl = (cx, cy)
        elif pos == "bottom_right":
            end = (cx - r, cy)
            ctrl = (cx, cy)
        elif pos == "bottom_left":
            end = (cx, cy - r)
            ctrl = (cx, cy)
        else:
            end = (cx + r, cy)
            ctrl = (cx, cy)

        if is_round:
            path.AddQuadCurveToPoint(ctrl[0], ctrl[1], end[0], end[1])
        else:
            path.AddLineToPoint(end[0], end[1])

    def _draw_holes(self, gc: wx.GraphicsContext, x: float, y: float, w: float, h: float, scale: float) -> None:
        if not self.holes:
            return

        gc.SetPen(wx.Pen(wx.Colour(80, 80, 80), 1))
        gc.SetBrush(wx.Brush(wx.Colour(255, 255, 255), wx.BRUSHSTYLE_TRANSPARENT))

        center_x = x + w / 2
        center_y = y + h / 2

        for hole in self.holes:
            hx = center_x + float(hole.get("cx", 0)) * scale
            hy = center_y - float(hole.get("cy", 0)) * scale

            if hole.get("type") == "slot":
                diameter = float(hole.get("diameter", 0)) * scale
                length = float(hole.get("length", 0)) * scale
                angle = math.radians(float(hole.get("angle", 0)))
                self._draw_slot(gc, hx, hy, max(length, diameter), diameter, angle)
            else:
                radius = float(hole.get("r", 0)) * scale
                if radius > 0:
                    gc.DrawEllipse(hx - radius, hy - radius, 2 * radius, 2 * radius)

    def _draw_slot(self, gc: wx.GraphicsContext, cx: float, cy: float, length: float, diameter: float, angle: float) -> None:
        radius = diameter / 2
        half = max((length - diameter) / 2, 0)
        dx = math.cos(angle) * half
        dy = -math.sin(angle) * half
        x1, y1 = cx - dx, cy - dy
        x2, y2 = cx + dx, cy + dy

        gc.DrawEllipse(x1 - radius, y1 - radius, diameter, diameter)
        gc.DrawEllipse(x2 - radius, y2 - radius, diameter, diameter)
        gc.StrokeLine(x1, y1, x2, y2)


# ----------------------------------------------------------------------
# Ячейка матрицы углов
# ----------------------------------------------------------------------
class CornerCell(wx.Panel):
    """Составная ячейка: иконка для свободной группы или TextCtrl для значения."""

    def __init__(self, parent: wx.Window, code: str, bitmap: wx.Bitmap):
        super().__init__(parent, size=CELL_SIZE, style=wx.BORDER_SIMPLE)
        self.code = code
        self.bitmap_ctrl = wx.StaticBitmap(self, bitmap=bitmap)
        self.text_ctrl = wx.TextCtrl(self, style=wx.TE_CENTER | wx.BORDER_NONE)
        self.text_ctrl.Hide()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddStretchSpacer()
        sizer.Add(self.bitmap_ctrl, 0, wx.ALIGN_CENTER)
        sizer.Add(self.text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        sizer.AddStretchSpacer()
        self.SetSizer(sizer)

    def show_icon(self):
        self.text_ctrl.Hide()
        self.bitmap_ctrl.Show()
        self.Layout()

    def show_text(self, value: str, editable: bool):
        self.bitmap_ctrl.Hide()
        self.text_ctrl.Show()
        if self.text_ctrl.GetValue() != value:
            self.text_ctrl.ChangeValue(value)
        self.text_ctrl.SetEditable(editable)
        self.Layout()

    def set_state_colors(self, bg: wx.Colour, fg: wx.Colour):
        self.SetBackgroundColour(bg)
        self.text_ctrl.SetBackgroundColour(bg)
        self.text_ctrl.SetForegroundColour(fg)
        self.bitmap_ctrl.SetBackgroundColour(bg)
        self.Refresh()

    def set_text_font(self, font: wx.Font):
        self.text_ctrl.SetFont(font)


# ----------------------------------------------------------------------
# Панель ввода углов
# ----------------------------------------------------------------------
class CornerInputPanel(wx.Panel):
    """Матрица 3x3 для ввода значений углов с блокировкой пересечений."""

    def __init__(self, parent: wx.Window, on_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.values: dict[str, str] = {}
        self.cells: dict[str, CornerCell] = {}
        self.on_change = on_change
        self.bitmaps = load_cell_bitmaps()
        self.normal_font = wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self._build_ui()
        self.refresh_cells()

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(_create_static_text(self, loc.get("corner_help")), 0, wx.EXPAND | wx.BOTTOM, 6)

        grid = wx.GridSizer(rows=3, cols=3, vgap=CELL_GAP, hgap=CELL_GAP)
        for row in CELL_ORDER:
            for code in row:
                cell = CornerCell(self, code, self.bitmaps[code])
                cell.SetMinSize(CELL_SIZE)
                cell.set_text_font(self.normal_font)
                cell.SetToolTip(self._get_tooltip(code))

                for ctrl in (cell, cell.bitmap_ctrl, cell.text_ctrl):
                    ctrl.Bind(wx.EVT_LEFT_DOWN, lambda evt, c=code: self.on_cell_click(evt, c))
                    ctrl.Bind(wx.EVT_LEFT_DCLICK, lambda evt, c=code: self.clear_cell(c))

                cell.text_ctrl.Bind(wx.EVT_TEXT, lambda evt, c=code: self.on_text_changed(evt, c))
                cell.text_ctrl.Bind(wx.EVT_KEY_DOWN, lambda evt, c=code: self.on_key_down(evt, c))

                self.cells[code] = cell
                grid.Add(cell, 0, wx.EXPAND)

        root.Add(grid, 0, wx.ALIGN_LEFT | wx.TOP, 4)
        self.SetSizer(root)

    def _get_tooltip(self, code: str) -> str:
        corners = ", ".join(CORNER_NAMES[c] for c in CELL_MASKS[code])
        return f"{code}: {corners}"

    def get_occupied_corners(self) -> set[str]:
        occupied: set[str] = set()
        for code in self.values:
            occupied |= CELL_MASKS[code]
        return occupied

    def is_blocked(self, code: str) -> bool:
        if code in self.values:
            return False
        return bool(self.get_occupied_corners() & CELL_MASKS[code])

    def is_single_corner(self, code: str) -> bool:
        return len(CELL_MASKS[code]) == 1

    def activate_cell(self, code: str):
        if self.is_blocked(code):
            return
        if code not in self.values:
            self.values[code] = ""
        self.refresh_cells()
        self.cells[code].text_ctrl.SetFocus()
        self.cells[code].text_ctrl.SelectAll()

    def clear_cell(self, code: str):
        if code in self.values:
            del self.values[code]
        self.refresh_cells()
        self._emit_change()

    def clear_all(self):
        self.values.clear()
        self.refresh_cells()
        self._emit_change()

    def refresh_cells(self):
        for code, cell in self.cells.items():
            active = code in self.values
            blocked = self.is_blocked(code)

            cell.Freeze()
            if active:
                cell.Enable(True)
                cell.show_text(str(self.values[code]), editable=True)
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

    def on_cell_click(self, event: wx.Event, code: str):
        if code in self.values:
            event.Skip()
            return
        self.activate_cell(code)
        self._emit_change()

    def on_text_changed(self, event: wx.Event, code: str):
        if code in self.values:
            self.values[code] = self.cells[code].text_ctrl.GetValue()
            self._emit_change()
        event.Skip()

    def on_key_down(self, event: wx.KeyEvent, code: str):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.clear_cell(code)
            return
        event.Skip()

    def get_corner_values(self) -> dict[str, float | tuple[float, float] | int]:
        result: dict[str, float | tuple[float, float] | int] = {"lt": 0, "rt": 0, "lb": 0, "rb": 0}
        for code, value in self.values.items():
            parsed = parse_corner_value(value)
            for corner in CELL_MASKS[code]:
                result[corner] = parsed
        return result

    def _emit_change(self):
        if self.on_change:
            self.on_change()


# ----------------------------------------------------------------------
# Симметричные отверстия
# ----------------------------------------------------------------------
class SymmetricHolesPanel(wx.Panel):
    """
    Компактная панель основного сценария: симметричные отверстия.

    Используется FieldBuilder/universal_row, чтобы подписи, поля и кнопки имели
    тот же стиль, что и в остальных окнах проекта.
    """

    def __init__(self, parent: wx.Window, on_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_change = on_change
        self.slot_data: Optional[dict[str, Any]] = None
        self.local_form = FormBuilder(self)
        self._build_ui()
        self._update_slot_button_state()

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(root)

        fb = FieldBuilder(parent=self, target_sizer=root, form=self.local_form)

        fb.universal_row(
            None,
            [{"type": "info", "value": loc.get("axis_legend"), "wrap": 360}],
            align_right=False,
        )

        self.type_choice = fb.universal_row(
            "hole_type",
            [{
                "type": "combo",
                "name": "sym_hole_type",
                "choices": [loc.get("circle"), loc.get("slot")],
                "value": loc.get("circle"),
                "default": loc.get("circle"),
                "readonly": True,
                "size": SUBPANEL_INPUT_SIZE,
            }],
        )[0]

        self.count_choice = fb.universal_row(
            "holes_count",
            [{
                "type": "combo",
                "name": "sym_hole_count",
                "choices": ["0", "1", "2", "4"],
                "value": "0",
                "default": "0",
                "readonly": True,
                "size": SUBPANEL_INPUT_SIZE,
            }],
        )[0]

        self.axis_choice = fb.universal_row(
            "symmetry_axis",
            [{
                "type": "combo",
                "name": "symmetry_axis_value",
                "choices": [
                    loc.get("symmetry_none"),
                    loc.get("symmetry_x"),
                    loc.get("symmetry_y"),
                    loc.get("symmetry_xy"),
                ],
                "value": loc.get("symmetry_none"),
                "default": loc.get("symmetry_none"),
                "readonly": True,
                "size": (190, -1),
            }],
        )[0]

        self.x_ctrl = fb.universal_row(
            "offset_x_label",
            [{"type": "float", "name": "sym_dx", "value": "0", "default": "0", "size": SUBPANEL_INPUT_SIZE}],
        )[0]
        self.y_ctrl = fb.universal_row(
            "offset_y_label",
            [{"type": "float", "name": "sym_dy", "value": "0", "default": "0", "size": SUBPANEL_INPUT_SIZE}],
        )[0]
        self.d_ctrl = fb.universal_row(
            "diameter_label",
            [{"type": "float", "name": "sym_diameter", "value": "", "default": "", "size": SUBPANEL_INPUT_SIZE}],
        )[0]

        self.slot_button = fb.universal_row(
            "slot_params_short",
            [{
                "type": "button",
                "label": loc.get("slot_params"),
                "callback": self.on_slot_params,
                "bg_color": "#2980b9",
                "size": (150, -1),
            }],
        )[0]

        self.slot_summary = wx.StaticText(self, label="")
        root.Add(self.slot_summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        for ctrl in (self.type_choice, self.count_choice, self.axis_choice):
            ctrl.Bind(wx.EVT_COMBOBOX, self.on_any_change)
        for ctrl in (self.x_ctrl, self.y_ctrl, self.d_ctrl):
            ctrl.Bind(wx.EVT_TEXT, self.on_any_change)

    def on_any_change(self, event: wx.Event):
        self._update_slot_button_state()
        self._emit_change()
        event.Skip()

    def _is_slot(self) -> bool:
        return self.type_choice.GetSelection() == 1

    def _update_slot_button_state(self):
        is_slot = self._is_slot()
        self.slot_button.Enable(is_slot)
        self.d_ctrl.Enable(not is_slot)

        if not is_slot:
            self.slot_summary.SetLabel("")
        elif self.slot_data:
            self.slot_summary.SetLabel(
                f"D={self.slot_data.get('diameter')}, L={self.slot_data.get('length')}, A={self.slot_data.get('angle')}°"
            )
        else:
            self.slot_summary.SetLabel(loc.get("slot_params_missing"))
        self.Layout()

    def on_slot_params(self, _event: wx.Event):
        if open_slotted_hole_dialog is None:
            show_popup(loc.get("slot_dialog_unavailable"), popup_type="error")
            return

        result = open_slotted_hole_dialog(self)
        if result:
            self.slot_data = result
            self._update_slot_button_state()
            self._emit_change()

    def clear(self):
        self.type_choice.SetSelection(0)
        self.count_choice.SetSelection(0)
        self.axis_choice.SetSelection(0)
        self.x_ctrl.SetValue("0")
        self.y_ctrl.SetValue("0")
        self.d_ctrl.SetValue("")
        self.slot_data = None
        self._update_slot_button_state()
        self._emit_change()

    def get_holes(self) -> list[dict[str, Any]]:
        count = int(self.count_choice.GetValue() or "0")
        if count == 0:
            return []

        x = _to_float(self.x_ctrl.GetValue(), allow_empty=True, default=0.0)
        y = _to_float(self.y_ctrl.GetValue(), allow_empty=True, default=0.0)
        points = self._make_points(count, x, y)

        if self._is_slot():
            if not self.slot_data:
                raise ValueError(loc.get("slot_params_missing"))

            return [
                {
                    "type": "slot",
                    "cx": px,
                    "cy": py,
                    "length": float(self.slot_data.get("length", 0)),
                    "diameter": float(self.slot_data.get("diameter", 0)),
                    "angle": float(self.slot_data.get("angle", 0)),
                }
                for px, py in points
            ]

        d = _to_float(self.d_ctrl.GetValue())
        if d <= 0:
            raise ValueError(loc.get("hole_error"))

        return [{"type": "circle", "cx": px, "cy": py, "r": d / 2.0} for px, py in points]

    def _make_points(self, count: int, x: float, y: float) -> list[tuple[float, float]]:
        axis = self.axis_choice.GetSelection()

        if count == 1:
            return [(x, y)]

        if count == 2:
            # "относительно X" -> зеркалим координату Y.
            if axis == 1:
                return [(x, y), (x, -y)]
            # Для "без симметрии" и "относительно Y" берём зеркалирование по X.
            return [(x, y), (-x, y)]

        if count == 4:
            return [(x, y), (-x, y), (-x, -y), (x, -y)]

        return []

    def _emit_change(self):
        if self.on_change:
            self.on_change()


# ----------------------------------------------------------------------
# Произвольные отверстия
# ----------------------------------------------------------------------
class FreeHolesPanel(wx.Panel):
    """Табличный ввод произвольного количества отверстий."""

    COL_TYPE = 0
    COL_X = 1
    COL_Y = 2
    COL_D = 3
    COL_L = 4
    COL_A = 5

    def __init__(self, parent: wx.Window, on_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_change = on_change
        self._build_ui()

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(_create_static_text(self, loc.get("free_holes_hint")), 0, wx.EXPAND | wx.BOTTOM, 6)

        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(4, 6)
        self.grid.SetRowLabelSize(0)

        labels = [
            loc.get("col_type"),
            loc.get("col_x"),
            loc.get("col_y"),
            loc.get("col_d"),
            loc.get("col_l"),
            loc.get("col_angle"),
        ]
        for col, label in enumerate(labels):
            self.grid.SetColLabelValue(col, label)

        widths = [86, 58, 58, 58, 58, 58]
        for col, width in enumerate(widths):
            self.grid.SetColSize(col, width)

        font = wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.grid.SetDefaultCellFont(font)
        self.grid.SetLabelFont(font)

        for row in range(self.grid.GetNumberRows()):
            self._init_row(row)

        self.grid.Bind(gridlib.EVT_GRID_CELL_CHANGED, self.on_cell_changed)

        root.Add(self.grid, 1, wx.EXPAND)
        self.SetSizer(root)

    def _init_row(self, row: int):
        self.grid.SetCellValue(row, self.COL_TYPE, "circle")
        self.grid.SetCellValue(row, self.COL_X, "0")
        self.grid.SetCellValue(row, self.COL_Y, "0")
        self.grid.SetCellValue(row, self.COL_D, "")
        self.grid.SetCellValue(row, self.COL_L, "")
        self.grid.SetCellValue(row, self.COL_A, "0")

        for col in range(self.grid.GetNumberCols()):
            self.grid.SetCellAlignment(row, col, wx.ALIGN_CENTER, wx.ALIGN_CENTER_VERTICAL)

    def on_cell_changed(self, event: gridlib.GridEvent):
        row = event.GetRow()
        if row == self.grid.GetNumberRows() - 1 and self._row_has_data(row):
            self.grid.AppendRows(1)
            self._init_row(self.grid.GetNumberRows() - 1)
        self._emit_change()
        event.Skip()

    def _row_has_data(self, row: int) -> bool:
        return any(self.grid.GetCellValue(row, col).strip() for col in range(self.grid.GetNumberCols()))

    def clear(self):
        self.grid.ClearGrid()
        while self.grid.GetNumberRows() > 4:
            self.grid.DeleteRows(4, 1)
        for row in range(self.grid.GetNumberRows()):
            self._init_row(row)
        self._emit_change()

    def get_holes(self) -> list[dict[str, Any]]:
        holes: list[dict[str, Any]] = []

        for row in range(self.grid.GetNumberRows()):
            if not self._row_has_data(row):
                continue

            htype = self.grid.GetCellValue(row, self.COL_TYPE).strip().lower() or "circle"
            d_text = self.grid.GetCellValue(row, self.COL_D).strip()
            l_text = self.grid.GetCellValue(row, self.COL_L).strip()

            # Пустая строка с дефолтами circle/0/0 не должна создавать отверстие.
            if not d_text and not l_text:
                continue

            x = _to_float(self.grid.GetCellValue(row, self.COL_X), allow_empty=True, default=0.0)
            y = _to_float(self.grid.GetCellValue(row, self.COL_Y), allow_empty=True, default=0.0)
            d = _to_float(d_text)

            if d <= 0:
                raise ValueError(loc.get("hole_error"))

            if htype in ("slot", "langloch", "паз", "продолговатое"):
                length = _to_float(l_text)
                angle = _to_float(self.grid.GetCellValue(row, self.COL_A), allow_empty=True, default=0.0)
                holes.append({"type": "slot", "cx": x, "cy": y, "length": length, "diameter": d, "angle": angle})
            else:
                holes.append({"type": "circle", "cx": x, "cy": y, "r": d / 2.0})

        return holes

    def _emit_change(self):
        if self.on_change:
            self.on_change()


# ----------------------------------------------------------------------
# Главная панель окна
# ----------------------------------------------------------------------
class RectPlateContentPanel(BaseContentPanel):
    """Основная панель ввода прямоугольной пластины."""

    def __init__(self, parent: wx.Window, callback: Optional[Callable[[dict[str, Any]], None]] = None):
        super().__init__(parent)

        self.parent = parent
        self.on_submit_callback = callback
        self.settings = load_user_settings()

        self.form: Optional[FormBuilder] = None
        self.fb: Optional[FieldBuilder] = None

        self.left_sizer: Optional[wx.BoxSizer] = None
        self.right_sizer: Optional[wx.BoxSizer] = None

        self.preview: Optional[RectPlatePreviewPanel] = None
        self.corner_panel: Optional[CornerInputPanel] = None
        self.symmetric_holes_panel: Optional[SymmetricHolesPanel] = None
        self.free_holes_panel: Optional[FreeHolesPanel] = None

        self.section_buttons: dict[str, wx.Button] = {}
        self.active_section: Optional[wx.Panel] = None

        self.insert_point = None
        self.width_ctrl: Optional[wx.TextCtrl] = None
        self.height_ctrl: Optional[wx.TextCtrl] = None

        self.SetBackgroundColour(
            get_wx_color_from_value(
                self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])
            )
        )

        self.setup_ui()

    def setup_ui(self) -> None:
        self.Freeze()
        try:
            if self.GetSizer():
                self.GetSizer().Clear(True)

            self.form = FormBuilder(self)

            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.left_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer = wx.BoxSizer(wx.VERTICAL)
            self.right_sizer.SetMinSize(wx.Size(RIGHT_PANEL_MIN_WIDTH, -1))

            # Левая часть — интерактивный предпросмотр.
            self.preview = RectPlatePreviewPanel(self)
            self.left_sizer.Add(self.preview, 1, wx.EXPAND | wx.ALL, 10)

            # Правая часть — ввод.
            self.fb = FieldBuilder(parent=self, target_sizer=self.right_sizer, form=self.form)

            common_data = load_common_data()
            material_options = [m["name"] for m in common_data.get("material", []) if m.get("name")]
            thickness_options = common_data.get("thicknesses", [])

            self._build_main_data(material_options, thickness_options)
            self._build_outer_geometry()
            self._build_switch_buttons()
            self._build_switch_sections()

            self.right_sizer.AddStretchSpacer()
            self.right_sizer.Add(self.create_button_bar(), 0, wx.ALIGN_RIGHT | wx.ALL, 5)

            # Пропорция 2:1.
            main_sizer.Add(self.left_sizer, 2, wx.EXPAND | wx.ALL, 10)
            main_sizer.Add(self.right_sizer, 1, wx.EXPAND | wx.ALL, 10)

            self.SetSizer(main_sizer)
            self.SetMinSize(wx.Size(1180, 680))

            apply_styles_to_panel(self)

            wx.CallAfter(self._show_section, self.corner_panel)
            wx.CallAfter(self.update_preview)
        finally:
            self.Layout()
            self.Thaw()

    # ------------------------------------------------------------------
    # Построение UI-блоков
    # ------------------------------------------------------------------
    def _build_main_data(self, material_options: list[str], thickness_options: list[str]):
        main_data_sizer = self.fb.static_box("main_data")
        fb_main = FieldBuilder(parent=self, target_sizer=main_data_sizer, form=self.form)

        fb_main.universal_row(
            "order_label",
            [
                {"type": "text", "name": "order", "value": "", "required": False, "default": ""},
                {"type": "text", "name": "detail", "value": "", "required": False, "default": ""},
            ],
        )

        fb_main.universal_row(
            "material_label",
            [{
                "type": "combo",
                "name": "material",
                "choices": material_options,
                "value": "",
                "required": True,
                "default": "1.4301",
                "size": (230, -1),
            }],
        )

        fb_main.universal_row(
            "thickness_label",
            [{
                "type": "combo",
                "name": "thickness",
                "choices": thickness_options,
                "value": "",
                "required": True,
                "default": "3",
                "size": SUBPANEL_INPUT_SIZE,
            }],
        )

    def _build_outer_geometry(self):
        geom_sizer = self.fb.static_box("outer_contour")
        fb_geom = FieldBuilder(parent=self, target_sizer=geom_sizer, form=self.form)

        created_w = fb_geom.universal_row(
            "width_label",
            [{"type": "float", "name": "width", "value": "", "required": True, "default": "", "size": SUBPANEL_INPUT_SIZE}],
        )
        created_h = fb_geom.universal_row(
            "height_label",
            [{"type": "float", "name": "height", "value": "", "required": True, "default": "", "size": SUBPANEL_INPUT_SIZE}],
        )

        self.width_ctrl = created_w[0]
        self.height_ctrl = created_h[0]

        self.width_ctrl.Bind(wx.EVT_TEXT, self._on_geometry_changed)
        self.height_ctrl.Bind(wx.EVT_TEXT, self._on_geometry_changed)

    def _build_switch_buttons(self):
        # Кнопки как в модуле мостиков: три переключателя, показывающие одну секцию.
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fb_button = FieldBuilder(parent=self, target_sizer=button_sizer, form=self.form)

        controls = fb_button.universal_row(
            "",
            [
                {
                    "type": "button",
                    "label": loc.get("corners_label"),
                    "callback": self.on_toggle_corners,
                    "bg_color": "#27ae60",
                    "toggle": True,
                    "size": SECTION_BUTTON_SIZE,
                },
                {
                    "type": "button",
                    "label": loc.get("symmetric_holes"),
                    "callback": self.on_toggle_symmetric_holes,
                    "bg_color": "#2980b9",
                    "toggle": True,
                    "size": SECTION_BUTTON_SIZE,
                },
                {
                    "type": "button",
                    "label": loc.get("free_holes"),
                    "callback": self.on_toggle_free_holes,
                    "bg_color": "#8e44ad",
                    "toggle": True,
                    "size": SECTION_BUTTON_SIZE,
                },
            ],
            align_right=False,
        )

        self.section_buttons = {
            "corners": controls[0],
            "symmetric": controls[1],
            "free": controls[2],
        }

        self.right_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)

    def _build_switch_sections(self):
        self.corner_panel = CornerInputPanel(self, on_change=self.update_preview)
        self.symmetric_holes_panel = SymmetricHolesPanel(self, on_change=self.update_preview)
        self.free_holes_panel = FreeHolesPanel(self, on_change=self.update_preview)

        for panel in (self.corner_panel, self.symmetric_holes_panel, self.free_holes_panel):
            panel.Hide()
            self.right_sizer.Add(panel, 0, wx.EXPAND | wx.ALL, 5)

    # ------------------------------------------------------------------
    # Переключение секций
    # ------------------------------------------------------------------
    def on_toggle_corners(self, _event: Optional[wx.Event] = None):
        self._show_section(self.corner_panel)

    def on_toggle_symmetric_holes(self, _event: Optional[wx.Event] = None):
        self._show_section(self.symmetric_holes_panel)

    def on_toggle_free_holes(self, _event: Optional[wx.Event] = None):
        self._show_section(self.free_holes_panel)

    def _show_section(self, section: Optional[wx.Panel]):
        if section is None:
            return

        self.Freeze()
        try:
            for panel in (self.corner_panel, self.symmetric_holes_panel, self.free_holes_panel):
                if panel:
                    panel.Show(panel is section)
            self.active_section = section
            self._set_section_buttons_active(section)
            self.Layout()
        finally:
            self.Thaw()

    def _set_section_buttons_active(self, section: wx.Panel):
        """Синхронизирует визуальное состояние трёх toggle-кнопок секций."""
        mapping = {
            "corners": self.corner_panel,
            "symmetric": self.symmetric_holes_panel,
            "free": self.free_holes_panel,
        }

        for key, panel in mapping.items():
            button = self.section_buttons.get(key)
            if button and hasattr(button, "set_active"):
                button.set_active(panel is section)

    # ------------------------------------------------------------------
    # Сбор и проверка данных
    # ------------------------------------------------------------------
    def _collect_raw_form(self) -> dict[str, Any]:
        raw = self.form.collect()
        return raw or {}

    def _read_dimensions(self) -> tuple[float, float]:
        width = _to_float(self.width_ctrl.GetValue())
        height = _to_float(self.height_ctrl.GetValue())

        if width <= 0 or height <= 0:
            raise ValueError(loc.get("invalid_dimensions"))

        return width, height

    def _read_corners(self, width: float, height: float) -> dict[str, float | tuple[float, float] | int]:
        corners = self.corner_panel.get_corner_values() if self.corner_panel else {"lt": 0, "rt": 0, "lb": 0, "rb": 0}
        limit = min(width, height) / 2.0

        for value in corners.values():
            if corner_abs_limit_value(value) > limit:
                raise ValueError(loc.get("corner_too_large"))

        # Порядок ключей совпадает с at_rect_plate.py.
        return {
            "rb": corners["rb"],
            "rt": corners["rt"],
            "lt": corners["lt"],
            "lb": corners["lb"],
        }

    def _read_holes(self) -> list[dict[str, Any]]:
        holes: list[dict[str, Any]] = []

        if self.symmetric_holes_panel:
            holes.extend(self.symmetric_holes_panel.get_holes())

        if self.free_holes_panel:
            holes.extend(self.free_holes_panel.get_holes())

        return holes

    def build_plate_data(self) -> dict[str, Any]:
        raw = self._collect_raw_form()
        width, height = self._read_dimensions()
        corners = self._read_corners(width, height)
        holes = self._read_holes()

        return {
            "width": width,
            "height": height,
            "corners": corners,
            "holes": holes,
            "order": raw.get("order", ""),
            "detail": raw.get("detail", ""),
            "material": raw.get("material", ""),
            "thickness": raw.get("thickness", ""),
        }

    # ------------------------------------------------------------------
    # Предпросмотр
    # ------------------------------------------------------------------
    def _on_geometry_changed(self, event: wx.Event):
        self.update_preview()
        event.Skip()

    def update_preview(self):
        try:
            width = _to_float(self.width_ctrl.GetValue(), allow_empty=True, default=300.0)
            height = _to_float(self.height_ctrl.GetValue(), allow_empty=True, default=180.0)
        except Exception:
            width, height = 300.0, 180.0

        try:
            corners = self.corner_panel.get_corner_values() if self.corner_panel else {"lt": 0, "rt": 0, "lb": 0, "rb": 0}
        except Exception:
            corners = {"lt": 0, "rt": 0, "lb": 0, "rb": 0}

        try:
            holes = self._read_holes()
        except Exception:
            holes = []

        if self.preview:
            self.preview.update_preview(width, height, corners, holes)

    # ------------------------------------------------------------------
    # Кнопки
    # ------------------------------------------------------------------
    def clear_input_fields(self):
        if self.form:
            self.form.clear()

        if self.corner_panel:
            self.corner_panel.clear_all()

        if self.symmetric_holes_panel:
            self.symmetric_holes_panel.clear()

        if self.free_holes_panel:
            self.free_holes_panel.clear()

        self.insert_point = None
        self.update_preview()

    def on_ok(self, event: Optional[wx.Event] = None, close_window: bool = False):
        try:
            plate_data = self.build_plate_data()
        except Exception as e:
            show_popup(f"{loc.get('error')}: {e}", popup_type="error")
            return

        pprint({loc.get("result_debug"): plate_data})

        if self.on_submit_callback:
            self.on_submit_callback(plate_data)
        else:
            show_popup(str(plate_data), popup_type="info")

    def on_clear(self, event: Optional[wx.Event] = None):
        self.clear_input_fields()

    def on_cancel(self, event: Optional[wx.Event] = None, switch_content: str = "content_apps"):
        try:
            self.switch_content_panel(switch_content)
        except Exception:
            frame = wx.GetTopLevelParent(self)
            if frame:
                frame.Close()


# ----------------------------------------------------------------------
# Standalone test window
# ----------------------------------------------------------------------
class RectPlateTestFrame(wx.Frame):
    """Отдельное окно для тестирования панели без главного окна проекта."""

    def __init__(self):
        super().__init__(None, title="test_rect_plate_window", size=wx.Size(1250, 740))
        panel = RectPlateContentPanel(self, callback=lambda data: print("Collected plate data:", data))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Centre()


if __name__ == "__main__":
    app = wx.App(False)
    frame = RectPlateTestFrame()
    frame.Show()
    app.MainLoop()
