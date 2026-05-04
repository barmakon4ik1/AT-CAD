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
Формат значений совпадает с ``programs.at_rect_plate. RectPlate``:

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


# ----------------------------------------------------------------------
# Проектные импорты
# ----------------------------------------------------------------------
from config.at_config import (
    ARROWS_IMAGE_PATH,
    DEFAULT_SETTINGS, BUTTON_SIZE,
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
    "symmetric_holes": {"ru": "Сим.отв.", "de": "Symm.Bohr.", "en": "Symm.holes"},
    "free_holes": {"ru": "Отверстия", "de": "Bohrungen", "en": "Holes"},

    "corner_help_btn":   {"ru": "Справка", "de": "Hilfe", "en": "Help"},
    "corner_help_title": {"ru": "Формат ввода углов и сторон", "de": "Eingabeformat", "en": "Input format"},
    "corner_help": {
        "ru": "0 — без обработки, острый угол 90°;\n25 — скругление радиусом R25;\n-10 — фаска 10x45°;\n10;20 — асимметричная фаска 10x20\n"
              "*100 - выпуклая сторона с радиусом R100;\n*-100 - вогнутая сторона с радиусом R100",
        "de": "0 — keine Bearbeitung, spitzer Winkel 90°;\n25 — Abrundung mit Radius R25;\n-10 — Fase 10x45°;\n10;20 — asymmetrische Fase 10x20\n"
              "*100 ist die konvexe Seite mit Radius R100;\n*-100 ist die konkave Seite mit Radius R100.",
        "en": "0 — no processing, angle 90°;\n25 — rounding with radius R25;\n-10 — chamfer 10x45°;\n10;20 — asymmetric chamfer 10x20\n"
              "*100 is the convex side with radius R100;\n*-100 is the concave side with radius R100.",
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
    "sym_from_edge": {"ru": "от края", "de": "vom Rand", "en": "from edge"},
    "sym_step": {"ru": "  шаг", "de": "  Schritt", "en": "  step"},
}
loc.register_translations(TRANSLATIONS)


# ----------------------------------------------------------------------
# Централизованные настройки оформления
# ----------------------------------------------------------------------
DEFAULT_CORNER_VALUE = 0

PREVIEW_SIZE        = (760, 560)
RIGHT_PANEL_MIN_WIDTH = 420

CELL_SIZE           = wx.Size(72, 54)     # wx.Size, не tuple
CELL_GAP            = 4
WINDOW_PADDING      = 10

SUBPANEL_INPUT_SIZE = wx.Size(130, -1)    # wx.Size, не tuple

HOLE_ICON_SIZE      = (24, 24)            # для circle.png / slot.png
SYM_ICON_SIZE       = (26, 26)            # для sym_*.png
BTN_ICON_SIZE       = (22, 22)            # для кнопок управления

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


def _load_bmp(filename: str, size: tuple[int, int]) -> wx.Bitmap:
    """Загружает PNG из ARROWS_IMAGE_PATH; при ошибке — серый placeholder."""
    return load_bitmap(IMAGE_DIR / filename, size)


def _load_hole_bmp(filename: str) -> wx.Bitmap:
    """Загружает иконку типа отверстия (circle.png / slot.png)."""
    return _load_bmp(filename, HOLE_ICON_SIZE)


def _bmp_to_bundle(bmp: wx.Bitmap) -> wx.BitmapBundle:
    """Конвертирует wx.Bitmap → wx.BitmapBundle для BitmapButton."""
    return wx.BitmapBundle.FromBitmap(bmp)


def load_cell_bitmaps() -> dict[str, wx.Bitmap]:
    """Загружает все иконки матрицы углов."""
    return {code: load_bitmap(IMAGE_DIR / filename, ICON_DRAW_SIZE) for code, filename in ICON_FILES.items()}


def parse_corner_value(value: Any) -> float | tuple[float, float] | int:
    """
    Преобразует текст ячейки угла в формат ``programs.at_rect_plate``.

    Если текст начинается с '*', это обозначение дуги (bulge) для
    соседней стороны — возвращается 0 (угол без обработки).
    Значение bulge извлекается отдельно через parse_edge_bulge().
    """
    text = str(value).strip().replace(",", ".")
    if text == "" or text.startswith("*"):
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


def parse_edge_bulge(value: Any) -> float:
    """
    Извлекает значение bulge из ячейки стороны (ячейки 01, 10, 12, 21).

    Формат: '*<число>', например '*0.5' или '*-0.3'.
    Если префикса '*' нет или строка пустая — возвращает 0.0 (дуга не нужна).
    """
    text = str(value).strip().replace(",", ".")
    if not text.startswith("*"):
        return 0.0
    tail = text[1:].strip()
    if not tail:
        return 0.0
    return float(tail)


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

    @staticmethod
    def _draw_slot(gc: wx.GraphicsContext, cx: float, cy: float, length: float, diameter: float, angle: float) -> None:
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

        # Кнопка «?» — справка по вводу углов
        info_btn = wx.Button(self, label="?  " + loc.get("corner_help_btn", "Справка"), size=BUTTON_SIZE)
        info_btn.SetFont(wx.Font(NORMAL_FONT_SIZE - 1, wx.FONTFAMILY_DEFAULT,
                                  wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        info_btn.SetBackgroundColour(wx.Colour(52, 152, 219))
        info_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        info_btn.Bind(wx.EVT_BUTTON, self._on_show_help)
        root.Add(info_btn, 0, wx.TOP | wx.ALIGN_LEFT, 6)

        self.SetSizer(root)

    def _on_show_help(self, _evt):
        msg = loc.get("corner_help")
        dlg = wx.MessageDialog(self, msg, loc.get("corner_help_title", "Формат ввода"),
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def _get_tooltip(code: str) -> str:
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

    @staticmethod
    def is_single_corner(code: str) -> bool:
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

    def get_corner_values(self) -> dict[str, Any]:
        """
        Возвращает словарь для at_rect_plate с угловыми значениями
        и опциональными bulge-значениями для сторон.

        Ключи углов:  rb, rt, lt, lb  (float | tuple | int)
        Ключи сторон: edge_top, edge_bottom, edge_left, edge_right  (float, bulge)

        Ячейки матрицы → стороны:
            "01" → верхняя  → edge_top
            "21" → нижняя   → edge_bottom
            "10" → левая    → edge_left
            "12" → правая   → edge_right
        """
        result: dict[str, Any] = {
            "lt": 0, "rt": 0, "lb": 0, "rb": 0,
            # Bulge сторон; 0.0 = не используется (прямая линия)
            "edge_top":    0.0,
            "edge_bottom": 0.0,
            "edge_left":   0.0,
            "edge_right":  0.0,
        }

        # Ячейки с одиночными углами и группами
        _CORNER_CELLS  = {"00", "02", "20", "22", "11"}
        # Ячейки, определяющие форму стороны (дуга)
        _EDGE_MAP = {
            "01": "edge_top",
            "21": "edge_bottom",
            "10": "edge_left",
            "12": "edge_right",
        }

        for code, value in self.values.items():
            if code in _EDGE_MAP:
                # Это ячейка стороны — пишем bulge, угол = 0 (сторона не угол)
                result[_EDGE_MAP[code]] = parse_edge_bulge(value)
            else:
                # Обычная угловая ячейка
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
    Симметричные отверстия.

    При N=2 активная ось определяется тем, в какое поле «шаг» пользователь
    ввёл значение первым. Поля «от края» блокируются кнопкой симметрии.
    """

    _FIELD_W   = 80
    _BTN_W     = 34
    _ROW_H     = -1
    _BTN_ICON  = (22, 22)

    def __init__(self, parent: wx.Window, on_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_change    = on_change
        self.slot_data: Optional[dict[str, Any]] = None

        self._sym_x = True    # True = симм. ↔, False = от левого края →
        self._sym_y = True    # True = симм. ↕, False = от нижнего края ↑
        self._type_is_slot = False
        self._holes: list[dict[str, Any]] = []

        # Какая ось была введена первой при N=2 (None = ещё не определено)
        self._first_axis: Optional[str] = None   # "x" | "y"

        self.status_text: str = ""
        self._build_ui()
        self._refresh_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        fnt = wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT,
                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        hdr_fnt = wx.Font(NORMAL_FONT_SIZE - 1, wx.FONTFAMILY_DEFAULT,
                          wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        root = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(root)

        # ── Строка 1: тип / кол-во / Ø ────────────────────────────────
        row1 = wx.BoxSizer(wx.HORIZONTAL)

        self._type_btn = wx.BitmapButton(
            self,
            bitmap=_bmp_to_bundle(_load_hole_bmp("circle.png")),
            size=wx.Size(self._BTN_W, self._BTN_W))
        self._type_btn.SetToolTip(loc.get("hole_type"))
        row1.Add(self._type_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self._count_ctrl = wx.Choice(self, choices=["2", "4"])
        self._count_ctrl.SetSelection(1)
        self._count_ctrl.SetFont(fnt)
        row1.Add(self._count_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)

        lbl_xd = wx.StaticText(self, label=" × Ø")
        lbl_xd.SetFont(fnt)
        row1.Add(lbl_xd, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)

        self._d_ctrl = wx.TextCtrl(self, size=wx.Size(self._FIELD_W, self._ROW_H))
        self._d_ctrl.SetFont(fnt)
        row1.Add(self._d_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(row1, 0, wx.EXPAND | wx.ALL, 5)

        # ── Grid X / Y: заголовок + 2 строки ──────────────────────────
        #   Колонки: [ось 20] [btn 36] [от края FIELD_W] [шаг FIELD_W]
        pad = 4

        hdr_row = wx.BoxSizer(wx.HORIZONTAL)
        hdr_row.Add(wx.Size(20 + self._BTN_W + pad * 2, 1))
        for label in (loc.get("sym_from_edge"), loc.get("sym_step")):
            s = wx.StaticText(self, label=label)
            s.SetFont(hdr_fnt)
            s.SetForegroundColour(wx.Colour(110, 110, 110))
            hdr_row.Add(s, 0, wx.RIGHT, self._FIELD_W - s.GetBestSize().width + pad)
        root.Add(hdr_row, 0, wx.LEFT | wx.RIGHT, 5)

        def make_axis_row(axis_label: str) -> tuple:
            row = wx.BoxSizer(wx.HORIZONTAL)
            lbl = wx.StaticText(self, label=axis_label)
            lbl.SetFont(fnt)
            row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, pad)

            sym_btn = wx.BitmapButton(
                self,
                bitmap=_bmp_to_bundle(_load_bmp("sym_xy.png", SYM_ICON_SIZE)),
                size=wx.Size(self._BTN_W, self._BTN_W))
            row.Add(sym_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, pad)

            edge_ctrl = wx.TextCtrl(self, size=wx.Size(self._FIELD_W, self._ROW_H))
            edge_ctrl.SetFont(fnt)
            row.Add(edge_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, pad)

            step_ctrl = wx.TextCtrl(self, size=wx.Size(self._FIELD_W, self._ROW_H))
            step_ctrl.SetFont(fnt)
            row.Add(step_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)

            return row, sym_btn, edge_ctrl, step_ctrl

        row_x, self._sym_x_btn, self._x_edge_ctrl, self._x_step_ctrl = make_axis_row("X:")
        row_y, self._sym_y_btn, self._y_edge_ctrl, self._y_step_ctrl = make_axis_row("Y:")

        root.Add(row_x, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        root.Add(row_y, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # ── Список добавленных отверстий ──────────────────────────────
        # Ширина колонок ~5 символов × ~7px = 36px + заголовок
        self._holes_list = wx.ListCtrl(
            self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=wx.Size(-1, 85))
        self._holes_list.SetFont(wx.Font(NORMAL_FONT_SIZE - 1, wx.FONTFAMILY_DEFAULT,
                                         wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        col_defs = [("N", 28), ("Тип", 40), ("Ø", 48), ("L", 42),
                    ("X от кр.", 58), ("шаг X", 48), ("Y от кр.", 58), ("шаг Y", 48)]
        for i, (h, w) in enumerate(col_defs):
            self._holes_list.InsertColumn(i, h, width=w)
        root.Add(self._holes_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # ── Кнопки с иконками ─────────────────────────────────────────
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        icons = [
            ("ok.png",    self._on_add),
            ("clear.png",      self._on_clear_list)
        ]
        for fname, handler in icons:
            bmp = _load_bmp(fname, self._BTN_ICON)
            btn = wx.BitmapButton(self, bitmap=_bmp_to_bundle(bmp),
                                  size=wx.Size(self._BTN_ICON[0] + 8, self._BTN_ICON[1] + 8))
            btn.Bind(wx.EVT_BUTTON, handler)
            btn_sizer.Add(btn, 0, wx.RIGHT, 3)
        root.Add(btn_sizer, 0, wx.LEFT | wx.BOTTOM, 5)

        # ── События ───────────────────────────────────────────────────
        self._type_btn.Bind(wx.EVT_BUTTON,   self._on_type_toggle)
        self._count_ctrl.Bind(wx.EVT_CHOICE, self._on_count_changed)
        self._sym_x_btn.Bind(wx.EVT_BUTTON,  self._on_sym_x_toggle)
        self._sym_y_btn.Bind(wx.EVT_BUTTON,  self._on_sym_y_toggle)
        self._d_ctrl.Bind(wx.EVT_TEXT, lambda e: self._emit_change())

        # Отслеживаем «первое нажатие» в полях шага для N=2
        self._x_step_ctrl.Bind(wx.EVT_TEXT, self._on_x_step_text)
        self._y_step_ctrl.Bind(wx.EVT_TEXT, self._on_y_step_text)
        for ctrl in (self._x_edge_ctrl, self._y_edge_ctrl):
            ctrl.Bind(wx.EVT_TEXT, lambda e: self._emit_change())

    # ------------------------------------------------------------------
    # Отслеживание первого введённого шага (для N=2)
    # ------------------------------------------------------------------
    def _on_x_step_text(self, evt):
        val = self._x_step_ctrl.GetValue().strip()
        if val:
            # Если ось Y ещё не зафиксирована — фиксируем X
            if self._first_axis is None:
                self._first_axis = "x"
                self._refresh_ui()
        else:
            # Поле X очищено — сбрасываем фиксацию, если была по X
            if self._first_axis == "x":
                self._first_axis = None
                self._refresh_ui()
        self._emit_change()
        evt.Skip()

    def _on_y_step_text(self, evt):
        val = self._y_step_ctrl.GetValue().strip()
        if val:
            # Если ось X ещё не зафиксирована — фиксируем Y
            if self._first_axis is None:
                self._first_axis = "y"
                self._refresh_ui()
        else:
            # Поле Y очищено — сбрасываем фиксацию, если была по Y
            if self._first_axis == "y":
                self._first_axis = None
                self._refresh_ui()
        self._emit_change()
        evt.Skip()

    # ------------------------------------------------------------------
    # Обновление иконок и блокировок
    # ------------------------------------------------------------------
    def _refresh_ui(self):
        # Иконка типа
        self._type_btn.SetBitmap(
            _bmp_to_bundle(_load_hole_bmp("slot.png" if self._type_is_slot else "circle.png")))
        self._d_ctrl.Enable(not self._type_is_slot)

        # Иконки симметрии
        self._update_sym_icon(self._sym_x_btn, self._sym_x, "x")
        self._update_sym_icon(self._sym_y_btn, self._sym_y, "y")

        # Блокировка «от края»
        self._x_edge_ctrl.Enable(not self._sym_x)
        self._y_edge_ctrl.Enable(not self._sym_y)

        # При N=2: пока ни одна ось не введена — обе доступны;
        # как только введена одна — вторая блокируется целиком.
        count = self._get_count()
        if count == 2:
            if self._first_axis is None:
                # Обе оси свободны — разрешаем всё
                self._x_step_ctrl.Enable(True)
                self._x_edge_ctrl.Enable(not self._sym_x)
                self._sym_x_btn.Enable(True)
                self._y_step_ctrl.Enable(True)
                self._y_edge_ctrl.Enable(not self._sym_y)
                self._sym_y_btn.Enable(True)
            else:
                x_active = (self._first_axis == "x")
                y_active = (self._first_axis == "y")
                self._x_step_ctrl.Enable(x_active)
                self._x_edge_ctrl.Enable(x_active and not self._sym_x)
                self._sym_x_btn.Enable(x_active)
                self._y_step_ctrl.Enable(y_active)
                self._y_edge_ctrl.Enable(y_active and not self._sym_y)
                self._sym_y_btn.Enable(y_active)
        else:
            for ctrl in (self._x_step_ctrl, self._y_step_ctrl,
                         self._sym_x_btn, self._sym_y_btn):
                ctrl.Enable(True)
            self._x_edge_ctrl.Enable(not self._sym_x)
            self._y_edge_ctrl.Enable(not self._sym_y)

        self.Layout()

    @staticmethod
    def _update_sym_icon(btn: wx.BitmapButton, is_sym: bool, axis: str) -> None:
        if is_sym:
            fname = "sym_xy.png" if axis == "x" else "sym_yx.png"
            tip = loc.get("sym_tooltip_sym_x" if axis == "x" else "sym_tooltip_sym_y")
        else:
            fname = "sym_right.png" if axis == "x" else "sym_up.png"
            tip = loc.get("sym_tooltip_edge_x" if axis == "x" else "sym_tooltip_edge_y")
        btn.SetBitmap(_bmp_to_bundle(_load_bmp(fname, SYM_ICON_SIZE)))
        btn.SetToolTip(tip)

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _on_type_toggle(self, _evt):
        self._type_is_slot = not self._type_is_slot
        if self._type_is_slot:
            self._open_slot_dialog()
        else:
            self.slot_data = None
        self._refresh_ui()

    def _on_count_changed(self, _evt):
        self._first_axis = None   # сброс при смене количества
        self._refresh_ui()
        self._emit_change()

    def _on_sym_x_toggle(self, _evt):
        self._sym_x = not self._sym_x
        self._refresh_ui()
        self._emit_change()

    def _on_sym_y_toggle(self, _evt):
        self._sym_y = not self._sym_y
        self._refresh_ui()
        self._emit_change()

    def _open_slot_dialog(self):
        if open_slotted_hole_dialog is None:
            show_popup(loc.get("slot_dialog_unavailable"), popup_type="error")
            self._type_is_slot = False
            return
        result = open_slotted_hole_dialog(self)
        if result:
            self.slot_data = result
        else:
            self._type_is_slot = False

    def _on_add(self, _evt):
        try:
            holes = self._calc_current_holes()
        except ValueError as e:
            show_popup(str(e), popup_type="error")
            return
        self._holes.extend(holes)
        self._refresh_list()
        self._emit_change()

    def _on_delete(self, _evt):
        idx = self._holes_list.GetFirstSelected()
        if 0 <= idx < len(self._holes):
            del self._holes[idx]
            self._refresh_list()
            self._emit_change()

    def _on_clear_list(self, _evt):
        self._holes.clear()
        self._refresh_list()
        self._emit_change()

    def _on_apply(self, _evt):
        self._emit_change()

    # ------------------------------------------------------------------
    def _get_count(self) -> int:
        return [2, 4][self._count_ctrl.GetSelection()]

    def _calc_current_holes(self) -> list[dict[str, Any]]:
        count = self._get_count()
        x_step = _to_float(self._x_step_ctrl.GetValue(), allow_empty=True, default=0.0)
        y_step = _to_float(self._y_step_ctrl.GetValue(), allow_empty=True, default=0.0)
        x_edge = _to_float(self._x_edge_ctrl.GetValue(), allow_empty=True, default=0.0)
        y_edge = _to_float(self._y_edge_ctrl.GetValue(), allow_empty=True, default=0.0)

        px = x_step / 2.0 if self._sym_x else x_edge
        py = y_step / 2.0 if self._sym_y else y_edge

        if count == 2:
            active = self._first_axis or "x"
            if active == "x":
                points = [(px, py), (-px, py)]
            else:
                points = [(px, py), (px, -py)]
        else:
            points = [(px, py), (-px, py), (-px, -py), (px, -py)]

        if self._type_is_slot:
            if not self.slot_data:
                raise ValueError(loc.get("slot_params_missing"))
            return [{"type": "slot", "cx": p[0], "cy": p[1],
                     "length": float(self.slot_data.get("length", 0)),
                     "diameter": float(self.slot_data.get("diameter", 0)),
                     "angle": float(self.slot_data.get("angle", 0)),
                     "_xe": x_edge, "_xs": x_step,
                     "_ye": y_edge, "_ys": y_step,
                     "_sx": self._sym_x, "_sy": self._sym_y} for p in points]

        d = _to_float(self._d_ctrl.GetValue())
        if d <= 0:
            raise ValueError(loc.get("hole_error"))
        return [{"type": "circle", "cx": p[0], "cy": p[1], "r": d / 2.0,
                 "_xe": x_edge, "_xs": x_step,
                 "_ye": y_edge, "_ys": y_step,
                 "_sx": self._sym_x, "_sy": self._sym_y} for p in points]

    def _refresh_list(self):
        self._holes_list.DeleteAllItems()
        # Показываем группами (уникальные наборы параметров)
        seen: set = set()
        groups: list[dict] = []
        for h in self._holes:
            key = (h["type"], h.get("r", h.get("diameter")),
                   h.get("_xs"), h.get("_ys"), h.get("_xe"), h.get("_ye"))
            if key not in seen:
                seen.add(key)
                groups.append(h)

        for i, h in enumerate(groups):
            n = sum(1 for hh in self._holes if
                    hh["type"] == h["type"] and
                    abs(hh.get("r", hh.get("diameter", 0)) -
                        h.get("r", h.get("diameter", 0))) < 1e-6)
            d_str = (f"{h.get('r',0)*2:.1f}" if h["type"] == "circle"
                     else f"{h.get('diameter',0):.1f}")
            l_str = f"{h.get('length','')}" if h["type"] == "slot" else ""
            xe = ("sym" if h.get("_sx") else f"{h.get('_xe',0):.1f}")
            xs = f"{h.get('_xs',0):.1f}"
            ye = ("sym" if h.get("_sy") else f"{h.get('_ye',0):.1f}")
            ys = f"{h.get('_ys',0):.1f}"

            idx = self._holes_list.InsertItem(i, str(n))
            for col, val in enumerate([h["type"], d_str, l_str, xe, xs, ye, ys], start=1):
                self._holes_list.SetItem(idx, col, val)

    def get_holes(self) -> list[dict[str, Any]]:
        return [{k: v for k, v in h.items() if not k.startswith("_")}
                for h in self._holes]

    def clear(self):
        self._type_is_slot = False
        self._count_ctrl.SetSelection(1)
        self._d_ctrl.SetValue("")
        self._x_edge_ctrl.SetValue("")
        self._x_step_ctrl.SetValue("")
        self._y_edge_ctrl.SetValue("")
        self._y_step_ctrl.SetValue("")
        self._sym_x = True
        self._sym_y = True
        self._first_axis = None
        self.slot_data = None
        self._holes.clear()
        self._refresh_list()
        self._refresh_ui()
        self._emit_change()

    def _emit_change(self):
        if self.on_change:
            self.on_change()


# ----------------------------------------------------------------------
# Произвольные отверстия
# ----------------------------------------------------------------------
class FreeHolesPanel(wx.Panel):
    """Табличный ввод произвольного количества отверстий с иконками типа."""

    COL_TYPE = 0
    COL_X    = 1
    COL_Y    = 2
    COL_D    = 3
    COL_L    = 4
    COL_A    = 5

    _INIT_ROWS = 4
    # Ширины колонок: тип (кнопка), X, Y, D, L, A
    _COL_W = [30, 60, 60, 60, 60, 50]
    _ROW_H = 26
    _BTN_ICON_SZ = (22, 22)

    def __init__(self, parent: wx.Window, on_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_change = on_change
        self._bmp_circle = _load_hole_bmp("circle.png")
        self._bmp_slot   = _load_hole_bmp("slot.png")
        self._rows: list[dict] = []
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(root)

        # ── Строка заголовков ─────────────────────────────────────────
        hdr = wx.BoxSizer(wx.HORIZONTAL)
        hdr_labels = ["", "X", "Y", "Ø D", "L", "A°"]
        hdr_fnt = wx.Font(NORMAL_FONT_SIZE - 1, wx.FONTFAMILY_DEFAULT,
                          wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        for label, col_w in zip(hdr_labels, self._COL_W):
            st = wx.StaticText(self, label=label)
            st.SetFont(hdr_fnt)
            st.SetForegroundColour(wx.Colour(100, 100, 100))
            hdr.Add(st, 0, wx.LEFT, max(0, (col_w + 2 - st.GetBestSize().width) // 2))
            hdr.Add(wx.Size(col_w + 2 - st.GetBestSize().width -
                            max(0, (col_w + 2 - st.GetBestSize().width) // 2), 1))
        root.Add(hdr, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 2)

        # ── Прокручиваемая область со строками ─────────────────────────
        self._scroll = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self._scroll.SetScrollRate(0, 10)
        self._rows_sizer = wx.BoxSizer(wx.VERTICAL)
        self._scroll.SetSizer(self._rows_sizer)
        self._scroll.SetMinSize(wx.Size(-1, self._ROW_H * self._INIT_ROWS + 8))

        for _ in range(self._INIT_ROWS):
            self._append_row()

        root.Add(self._scroll, 1, wx.EXPAND | wx.TOP, 2)

        # ── Кнопки управления с иконками ─────────────────────────────
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        icons = [
            ("add_row.png",    self._on_add_row),
            ("remove_row.png", self._on_del_row),
            ("clear.png",      self._on_clear),
            ("ok.png",         self._on_apply),
        ]
        for fname, handler in icons:
            bmp = _load_bmp(fname, self._BTN_ICON_SZ)
            btn = wx.BitmapButton(self, bitmap=_bmp_to_bundle(bmp),
                                  size=wx.Size(self._BTN_ICON_SZ[0] + 8, self._BTN_ICON_SZ[1] + 8))
            btn.Bind(wx.EVT_BUTTON, handler)
            btn_sizer.Add(btn, 0, wx.RIGHT, 3)
        root.Add(btn_sizer, 0, wx.TOP, 4)

    # ------------------------------------------------------------------
    def _append_row(self, is_slot: bool = False):
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fnt = wx.Font(NORMAL_FONT_SIZE, wx.FONTFAMILY_DEFAULT,
                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        # Кнопка-иконка типа
        bmp = self._bmp_slot if is_slot else self._bmp_circle
        type_btn = wx.BitmapButton(self._scroll, bitmap=_bmp_to_bundle(bmp),
                                   size=wx.Size(self._COL_W[0], self._ROW_H))
        type_btn.SetToolTip("slot" if is_slot else "circle")
        row_idx = len(self._rows)
        type_btn.Bind(wx.EVT_BUTTON, lambda e, i=row_idx: self._on_type_toggle(i))
        row_sizer.Add(type_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 2)

        # Поля X, Y, D, L, A
        ctrls = []
        defaults = ["0", "0", "", "", "0"]
        for w, default in zip(self._COL_W[1:], defaults):
            ctrl = wx.TextCtrl(self._scroll, value=default,
                               size=wx.Size(w, self._ROW_H))
            ctrl.SetFont(fnt)
            ctrl.Bind(wx.EVT_TEXT, lambda e: self._emit_change())
            row_sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 2)
            ctrls.append(ctrl)

        self._rows_sizer.Add(row_sizer, 0, wx.EXPAND | wx.BOTTOM, 2)
        self._rows.append({"type_btn": type_btn, "ctrls": ctrls, "is_slot": is_slot})
        self._update_row_locks(len(self._rows) - 1)

    def _update_row_locks(self, i: int):
        row = self._rows[i]
        row["ctrls"][3].Enable(row["is_slot"])   # L
        row["ctrls"][4].Enable(row["is_slot"])   # A

    def _on_type_toggle(self, row_idx: int):
        if row_idx >= len(self._rows):
            return
        row = self._rows[row_idx]
        row["is_slot"] = not row["is_slot"]
        bmp = self._bmp_slot if row["is_slot"] else self._bmp_circle
        row["type_btn"].SetBitmap(_bmp_to_bundle(bmp))
        row["type_btn"].SetToolTip("slot" if row["is_slot"] else "circle")
        if not row["is_slot"]:
            row["ctrls"][3].SetValue("")
            row["ctrls"][4].SetValue("0")
        self._update_row_locks(row_idx)
        self._emit_change()

    def _on_add_row(self, _evt):
        self._append_row()
        self._scroll.SetMinSize(wx.Size(-1, min(self._ROW_H * len(self._rows) + 8, 160)))
        self._scroll.FitInside()
        self._scroll.Scroll(0, 9999)
        self.Layout()
        self._emit_change()

    def _on_del_row(self, _evt):
        if len(self._rows) <= 1:
            return
        row = self._rows.pop()
        row["type_btn"].Destroy()
        for c in row["ctrls"]:
            c.Destroy()
        n = self._rows_sizer.GetItemCount()
        if n > 0:
            self._rows_sizer.Remove(n - 1)
        self._scroll.FitInside()
        self.Layout()
        self._emit_change()

    def _on_clear(self, _evt):
        self.clear()

    def _on_apply(self, _evt):
        self._emit_change()

    def clear(self):
        while len(self._rows) > self._INIT_ROWS:
            row = self._rows.pop()
            row["type_btn"].Destroy()
            for c in row["ctrls"]:
                c.Destroy()
            n = self._rows_sizer.GetItemCount()
            if n > 0:
                self._rows_sizer.Remove(n - 1)

        for i, row in enumerate(self._rows):
            row["is_slot"] = False
            row["type_btn"].SetBitmap(_bmp_to_bundle(self._bmp_circle))
            row["type_btn"].SetToolTip("circle")
            for ctrl, val in zip(row["ctrls"], ["0", "0", "", "", "0"]):
                ctrl.SetValue(val)
            self._update_row_locks(i)

        self._scroll.FitInside()
        self.Layout()
        self._emit_change()

    def get_holes(self) -> list[dict[str, Any]]:
        holes = []
        for row in self._rows:
            ctrls = row["ctrls"]
            d_val = ctrls[2].GetValue().strip()
            if not d_val:
                continue
            x = _to_float(ctrls[0].GetValue(), allow_empty=True, default=0.0)
            y = _to_float(ctrls[1].GetValue(), allow_empty=True, default=0.0)
            d = _to_float(d_val)
            if d <= 0:
                raise ValueError(loc.get("hole_error"))
            if row["is_slot"]:
                l_val = ctrls[3].GetValue().strip()
                if not l_val:
                    continue
                length = _to_float(l_val)
                angle  = _to_float(ctrls[4].GetValue(), allow_empty=True, default=0.0)
                holes.append({"type": "slot", "cx": x, "cy": y,
                               "length": length, "diameter": d, "angle": angle})
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
            self.SetMinSize(wx.Size(1220, 700))

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
        """Три кнопки-переключателя секций — одинаковой ширины, всегда видимы."""
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        btn_specs = [
            (loc.get("corners_label"),   "#27ae60", self.on_toggle_corners),
            (loc.get("free_holes"),      "#8e44ad", self.on_toggle_free_holes),
            (loc.get("symmetric_holes"), "#2980b9", self.on_toggle_symmetric_holes),
        ]
        keys = ["corners", "free", "symmetric"]

        fb_tmp = FieldBuilder(parent=self, target_sizer=btn_sizer, form=self.form)
        controls = fb_tmp.universal_row(
            None,
            [
                {
                    "type": "button",
                    "label": label,
                    "callback": cb,
                    "bg_color": color,
                    "toggle": True,
                    "rows": 2,
                    # size=-1 → растянется через proportion=1 ниже
                    "size": wx.Size(-1, -1),
                }
                for label, color, cb in btn_specs
            ],
            align_right=False,
            element_proportion=1,    # каждый элемент тянется равномерно
        )

        self.section_buttons = dict(zip(keys, controls))
        self.right_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

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
        mapping = {
            "corners":   self.corner_panel,
            "free":      self.free_holes_panel,
            "symmetric": self.symmetric_holes_panel,
        }
        for key, panel in mapping.items():
            btn = self.section_buttons.get(key)
            if btn and hasattr(btn, "set_active"):
                btn.set_active(panel is section)

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

    def _read_corners(self, width: float, height: float) -> dict[str, Any]:
        """
        Считывает значения углов и дуговых сторон из CornerInputPanel.

        Угловые ключи:  rb, rt, lt, lb  — проходят валидацию по min(W,H)/2.
        Edge-ключи: edge_top, edge_bottom, edge_left, edge_right — радиус
        кривизны (знак = направление выпуклости); валидация не применяется,
        т.к. ограничение иное (R >= длина_стороны / 2) и проверяется в
        модуле построения.
        """
        all_values = (
            self.corner_panel.get_corner_values()
            if self.corner_panel
            else {
                "lt": 0, "rt": 0, "lb": 0, "rb": 0,
                "edge_top": 0.0, "edge_bottom": 0.0,
                "edge_left": 0.0, "edge_right": 0.0,
            }
        )

        # Валидируем ТОЛЬКО угловые ключи
        corner_keys = {"lt", "rt", "lb", "rb"}
        limit = min(width, height) / 2.0
        for key in corner_keys:
            value = all_values.get(key, 0)
            if corner_abs_limit_value(value) > limit:
                raise ValueError(loc.get("corner_too_large"))

        return {
            # Углы
            "rb": all_values.get("rb", 0),
            "rt": all_values.get("rt", 0),
            "lt": all_values.get("lt", 0),
            "lb": all_values.get("lb", 0),
            # Дуговые стороны (bulge-радиус; 0.0 = прямая линия)
            "edge_top":    all_values.get("edge_top",    0.0),
            "edge_bottom": all_values.get("edge_bottom", 0.0),
            "edge_left":   all_values.get("edge_left",   0.0),
            "edge_right":  all_values.get("edge_right",  0.0),
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
            "width":    width,
            "height":   height,
            "corners":  {
                "rb": corners["rb"],
                "rt": corners["rt"],
                "lt": corners["lt"],
                "lb": corners["lb"],
            },
            # Дуговые стороны вынесены отдельным ключом верхнего уровня,
            # чтобы модуль построения мог использовать их независимо.
            "edges": {
                "top":    corners["edge_top"],
                "bottom": corners["edge_bottom"],
                "left":   corners["edge_left"],
                "right":  corners["edge_right"],
            },
            "holes":     holes,
            "order":     raw.get("order", ""),
            "detail":    raw.get("detail", ""),
            "material":  raw.get("material", ""),
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
            top_frame = wx.GetTopLevelParent(self)
            if top_frame:
                top_frame.Close()


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