"""
programs/at_rect_plate.py

Модуль для построения разверток плоских прямоугольных пластин в AutoCAD:
проушин, усилительных накладок, опорных плит и аналогичных деталей.

Особенности геометрии:
  - Всегда прямоугольник (противоположные стороны параллельны, смежные перпендикулярны)
  - Углы: острые (0), скруглённые (r > 0) или фаски (r < 0 → 45°; (a, b) → произвольная)
  - Отверстия: круглые и продолговатые (слоты), произвольное количество

Соглашение по углам (corner value):
  0              → острый угол
  float > 0      → скругление радиусом r
  float < 0      → симметричная фаска: катеты abs(r) × abs(r)
  (a, b)         → асимметричная фаска: a по первой стороне, b по второй

Обход контура: CCW (против часовой стрелки), начиная с правого нижнего угла.
Порядок углов в словаре: "rb", "rt", "lt", "lb"
  rb = right-bottom (правый нижний)
  rt = right-top    (правый верхний)
  lt = left-top     (левый верхний)
  lb = left-bottom  (левый нижний)

Пример входного словаря:
    {
        "width": 300.0,
        "height": 200.0,
        "corners": {
            "rb": 0,
            "rt": 30.0,
            "lt": 30.0,
            "lb": -15.0,
        },
        "holes": [
            {"type": "circle", "cx": 0, "cy": 50, "r": 12.0},
            {"type": "slot",   "cx": 80, "cy": 0, "length": 40, "diameter": 16, "angle": 0},
        ],
        "order":     "W2025-001",
        "detail":    "3",
        "material":  "S235JR",
        "thickness": 10,
    }
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, DEFAULT_DIM_OFFSET
from errors.at_errors import ATError, DataError, GeometryError, TextError
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_construction import (
    AccompanyText,
    MainText,
    add_circle,
    add_polyline,
    add_slotted_hole,
)
from programs.at_geometry import (
    ensure_point_variant,
    fillet_points,
    offset_point,
)
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup

# ---------------------------------------------------------------------------
# Локальные переводы
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные пластины не переданы",
        "de": "Keine Plattendaten übergeben",
        "en": "No plate data provided",
    },
    "invalid_dimensions": {
        "ru": "Ширина и высота должны быть положительными числами",
        "de": "Breite und Höhe müssen positive Zahlen sein",
        "en": "Width and height must be positive numbers",
    },
    "invalid_corner_value": {
        "ru": "Недопустимое значение угла: {0}",
        "de": "Ungültiger Eckwert: {0}",
        "en": "Invalid corner value: {0}",
    },
    "corner_too_large": {
        "ru": "Размер угла {0} превышает допустимое значение для данной геометрии",
        "de": "Eckgröße {0} überschreitet den zulässigen Wert für diese Geometrie",
        "en": "Corner size {0} exceeds allowable value for this geometry",
    },
    "invalid_hole": {
        "ru": "Неверный формат данных отверстия: {0}",
        "de": "Ungültiges Format der Lochd​aten: {0}",
        "en": "Invalid hole data format: {0}",
    },
    "point_error": {
        "ru": "Ошибка преобразования точки вставки",
        "de": "Fehler bei der Umwandlung des Einfügepunkts",
        "en": "Insert point conversion error",
    },
    "build_contour_error": {
        "ru": "Ошибка построения контура: {0}",
        "de": "Fehler beim Aufbau der Kontur: {0}",
        "en": "Contour build error: {0}",
    },
    "build_holes_error": {
        "ru": "Ошибка построения отверстий: {0}",
        "de": "Fehler beim Erstellen der Löcher: {0}",
        "en": "Holes build error: {0}",
    },
    "build_text_error": {
        "ru": "Ошибка добавления текста: {0}",
        "de": "Fehler beim Hinzufügen des Texts: {0}",
        "en": "Text build error: {0}",
    },
    "unknown_hole_type": {
        "ru": "Неизвестный тип отверстия: {0}",
        "de": "Unbekannter Lochtyp: {0}",
        "en": "Unknown hole type: {0}",
    },
}
loc.register_translations(TRANSLATIONS)

# ---------------------------------------------------------------------------
# Константа bulge для дуги 90°
# ---------------------------------------------------------------------------
_BULGE_90_CCW = math.tan(math.radians(22.5))   # ≈ 0.4142  — дуга CCW (скругление)

# ---------------------------------------------------------------------------
# Вспомогательные типы
# ---------------------------------------------------------------------------

# Значение угла после нормализации:
# (mode, a, b)
#   mode = "sharp"  → острый
#   mode = "round"  → скругление, a = радиус
#   mode = "chamfer"→ фаска,      a = катет по первой стороне, b = по второй
@dataclass
class _CornerSpec:
    mode: str        # "sharp" | "round" | "chamfer"
    a: float = 0.0   # радиус скругления ИЛИ первый катет фаски
    b: float = 0.0   # второй катет фаски (для "chamfer")


# ---------------------------------------------------------------------------
# Класс RectPlate
# ---------------------------------------------------------------------------

class RectPlate:
    """
    Вычисляет и строит развертку прямоугольной пластины в AutoCAD.

    Использование:
        plate = RectPlate(data)
        plate.draw(model, center_point)
    """

    # Порядок обхода углов CCW начиная с rb
    _CORNER_ORDER = ("rb", "rt", "lt", "lb")

    def __init__(self, data: Dict[str, Any]):
        """
        Парсит и валидирует входные данные.

        Args:
            data: словарь с параметрами пластины.

        Raises:
            DataError: при некорректных размерах или данных углов.
        """
        if not data:
            raise DataError(__name__, ValueError(loc.get("no_data_error")))

        # --- Размеры ---
        width = data.get("width")
        height = data.get("height")
        if not isinstance(width, (int, float)) or width <= 0:
            raise DataError(__name__, ValueError(loc.get("invalid_dimensions")))
        if not isinstance(height, (int, float)) or height <= 0:
            raise DataError(__name__, ValueError(loc.get("invalid_dimensions")))

        self.width: float = float(width)
        self.height: float = float(height)

        # --- Углы ---
        raw_corners: Dict = data.get("corners", {})
        self.corners: Dict[str, _CornerSpec] = {
            key: self._parse_corner(raw_corners.get(key, 0), key)
            for key in self._CORNER_ORDER
        }

        # --- Отверстия ---
        self.holes: List[Dict] = self._validate_holes(data.get("holes", []))

        # --- Текст ---
        self.order: str = str(data.get("order", ""))
        self.detail: str = str(data.get("detail", ""))
        self.material: str = str(data.get("material", ""))
        self.thickness: Any = data.get("thickness", "")

    # ------------------------------------------------------------------
    # Парсинг и валидация
    # ------------------------------------------------------------------

    def _parse_corner(self, val: Any, key: str) -> _CornerSpec:
        """
        Нормализует значение угла к _CornerSpec.

        Args:
            val: 0, float, или (a, b) кортеж
            key: имя угла ("rb"/"rt"/"lt"/"lb") — для сообщений об ошибках

        Returns:
            _CornerSpec
        """
        # Острый угол
        if val == 0 or val is None:
            return _CornerSpec(mode="sharp")

        # Скругление или симметричная фаска
        if isinstance(val, (int, float)):
            v = float(val)
            if v > 0:
                self._check_corner_size(v, v, key)
                return _CornerSpec(mode="round", a=v)
            else:
                cat = abs(v)
                self._check_corner_size(cat, cat, key)
                return _CornerSpec(mode="chamfer", a=cat, b=cat)

        # Асимметричная фаска: кортеж/список (a, b)
        if isinstance(val, (tuple, list)) and len(val) == 2:
            a, b = float(val[0]), float(val[1])
            if a <= 0 or b <= 0:
                raise DataError(
                    __name__,
                    ValueError(loc.get("invalid_corner_value").format(val))
                )
            self._check_corner_size(a, b, key)
            return _CornerSpec(mode="chamfer", a=a, b=b)

        raise DataError(
            __name__,
            ValueError(loc.get("invalid_corner_value").format(val))
        )

    def _check_corner_size(self, a: float, b: float, key: str) -> None:
        """
        Проверяет, что катеты фаски/радиус скругления не превышают
        половину соответствующей стороны.
        """
        half_w = self.width / 2
        half_h = self.height / 2
        # rb и lt — смежные со сторонами width и height
        # Радиус (или катет) не должен превышать min(half_w, half_h)
        limit = min(half_w, half_h)
        if max(a, b) > limit:
            raise DataError(
                __name__,
                ValueError(loc.get("corner_too_large").format(f"{key}: max({a},{b}) > {limit}"))
            )

    def _validate_holes(self, holes: Any) -> List[Dict]:
        """
        Проверяет список отверстий. Отсеивает некорректные записи.
        """
        if not isinstance(holes, (list, tuple)):
            return []

        valid = []
        for i, h in enumerate(holes):
            if not isinstance(h, dict):
                continue
            hole_type = h.get("type", "circle")

            if hole_type == "circle":
                r = h.get("r", 0)
                if not isinstance(r, (int, float)) or r <= 0:
                    continue
                valid.append({
                    "type": "circle",
                    "cx": float(h.get("cx", 0)),
                    "cy": float(h.get("cy", 0)),
                    "r": float(r),
                })

            elif hole_type == "slot":
                length = h.get("length", 0)
                diameter = h.get("diameter", 0)
                if not isinstance(length, (int, float)) or length < 0:
                    continue
                if not isinstance(diameter, (int, float)) or diameter <= 0:
                    continue
                valid.append({
                    "type":     "slot",
                    "cx":       float(h.get("cx", 0)),
                    "cy":       float(h.get("cy", 0)),
                    "length":   float(length),
                    "diameter": float(diameter),
                    "angle":    float(h.get("angle", 0)),
                })

            # Сюда будущие типы (например, "rect_hole")

        return valid

    # ------------------------------------------------------------------
    # Расчёт контура
    # ------------------------------------------------------------------

    def _build_contour_vertices(
        self, cx: float, cy: float
    ) -> Tuple[List[Tuple[float, float, float]], bool]:
        """
        Рассчитывает вершины контура пластины как список (x, y, bulge).

        Обход: CCW от правого нижнего угла.
        Вершины углов прямоугольника:
            rb = (cx + hw, cy - hh)
            rt = (cx + hw, cy + hh)
            lt = (cx - hw, cy + hh)
            lb = (cx - hw, cy - hh)

        Для каждого угла:
          - острый → одна вершина, bulge=0
          - скругление → две точки касания + bulge на первой
          - фаска → две точки касания, bulge=0 (прямой срез)

        Args:
            cx, cy: координаты центра пластины

        Returns:
            vertices — список (x, y, bulge)
            needs_close — True (контур всегда замкнут)
        """
        hw = self.width / 2
        hh = self.height / 2

        # Вершины прямоугольника CCW от rb
        raw: List[Tuple[float, float]] = [
            (cx + hw, cy - hh),  # rb
            (cx + hw, cy + hh),  # rt
            (cx - hw, cy + hh),  # lt
            (cx - hw, cy - hh),  # lb
        ]

        n = len(raw)
        vertices: List[Tuple[float, float, float]] = []  # (x, y, bulge)

        for i, key in enumerate(self._CORNER_ORDER):
            spec = self.corners[key]
            prev_pt = raw[(i - 1) % n]
            curr_pt = raw[i]
            next_pt = raw[(i + 1) % n]

            if spec.mode == "sharp":
                vertices.append((curr_pt[0], curr_pt[1], 0.0))

            elif spec.mode == "round":
                # Точки касания
                t1, t2 = fillet_points(prev_pt, curr_pt, next_pt, spec.a)
                # Bulge: для прямоугольника угол всегда 90°, CCW обход
                # Скругление изнутри → bulge отрицательный (дуга выпуклая наружу)
                bulge = _BULGE_90_CCW
                vertices.append((t1[0], t1[1], bulge))
                vertices.append((t2[0], t2[1], 0.0))

            elif spec.mode == "chamfer":
                # Направляющие векторы от curr к prev и к next
                def _unit(p_from, p_to):
                    dx = p_to[0] - p_from[0]
                    dy = p_to[1] - p_from[1]
                    length = math.hypot(dx, dy)
                    return (dx / length, dy / length) if length > 1e-12 else (0.0, 0.0)

                u_prev = _unit(curr_pt, prev_pt)
                u_next = _unit(curr_pt, next_pt)

                # t1 — точка на стороне к prev, t2 — на стороне к next
                t1 = (curr_pt[0] + u_prev[0] * spec.a, curr_pt[1] + u_prev[1] * spec.a)
                t2 = (curr_pt[0] + u_next[0] * spec.b, curr_pt[1] + u_next[1] * spec.b)

                vertices.append((t1[0], t1[1], 0.0))
                vertices.append((t2[0], t2[1], 0.0))

        return vertices, True

    # ------------------------------------------------------------------
    # Построение в AutoCAD
    # ------------------------------------------------------------------

    def draw(self, model: Any, center: Any) -> None:
        """
        Строит пластину в пространстве модели AutoCAD.

        Args:
            model:  ModelSpace AutoCAD
            center: точка центра пластины (список [x,y,z] или VARIANT)
        """
        # --- Нормализуем центр ---
        try:
            center_v = ensure_point_variant(center)
            cx = center_v.value[0]
            cy = center_v.value[1]
        except Exception as err:
            raise GeometryError(__name__, err)

        # --- Контур ---
        # Слой "0" — жёстко закреплён для лазерной резки, не изменяется.
        try:
            vertices, _ = self._build_contour_vertices(cx, cy)
            points = [(v[0], v[1]) for v in vertices]
            bulges = [v[2] for v in vertices]

            add_polyline(
                model,
                points,
                layer_name="0",
                closed=True,
                bulges=bulges,
            )
        except Exception as err:
            raise GeometryError(
                __name__,
                Exception(loc.get("build_contour_error").format(str(err)))
            )

        # --- Отверстия ---
        try:
            self._draw_holes(model, cx, cy)
        except Exception as err:
            raise GeometryError(
                __name__,
                Exception(loc.get("build_holes_error").format(str(err)))
            )

        # --- Текст ---
        if self.order:
            try:
                self._draw_text(model, cx, cy)
            except Exception as err:
                raise TextError(
                    __name__,
                    Exception(loc.get("build_text_error").format(str(err)))
                )

    def _draw_holes(self, model: Any, cx: float, cy: float) -> None:
        """
        Строит все отверстия относительно центра пластины.
        cx, cy передаются уже рассчитанными GUI как центр каждого отверстия.
        """
        for hole in self.holes:
            hole_center = offset_point(
                ensure_point_variant([cx, cy, 0.0]),
                hole["cx"],
                hole["cy"],
                as_variant=False,
            )

            if hole["type"] == "circle":
                add_circle(
                    model,
                    ensure_point_variant(hole_center),
                    hole["r"],
                    DEFAULT_CIRCLE_LAYER,
                )

            elif hole["type"] == "slot":
                # Центр слота уже рассчитан в GUI — direction всегда "center"
                add_slotted_hole(
                    model,
                    hole_center,
                    innen_length=hole["length"],
                    height=hole["diameter"],
                    angle=hole["angle"],
                    direction="center",
                )

            else:
                show_popup(
                    loc.get("unknown_hole_type").format(hole["type"]),
                    popup_type="warning",
                )

    def _draw_text(self, model: Any, cx: float, cy: float) -> None:
        """
        Добавляет текстовые метки над пластиной.
        """
        hh = self.height / 2

        # Основной текст — внутри пластины (по центру)
        p_main = ensure_point_variant([cx, cy, 0.0])

        # Сопроводительный текст — выше контура
        p_accomp = offset_point(
            ensure_point_variant([cx, cy, 0.0]),
            0,
            hh + DEFAULT_DIM_OFFSET + 20,
        )

        MainText(
            {"work_number": self.order, "detail": self.detail}
        ).draw(model, p_main, text_alignment=4, laser=True)

        AccompanyText(
            {"thickness": self.thickness, "material": self.material}
        ).draw(model, p_accomp, text_alignment=4)


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main(plate_data: Optional[Dict] = None) -> bool:
    """
    Основная функция: инициализирует AutoCAD, запрашивает точку вставки,
    строит пластину.

    Args:
        plate_data: словарь с параметрами пластины (из UI)

    Returns:
        True при успехе, False при ошибке
    """
    try:
        # --- Инициализация AutoCAD ---
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        # --- Проверка данных ---
        if not plate_data:
            raise DataError(__name__, ValueError(loc.get("no_data_error")))

        # --- Создание объекта пластины (валидация) ---
        plate = RectPlate(plate_data)

        # --- Запрос точки вставки ---
        center = at_get_point(
            adoc,
            as_variant=False,
            prompt="Укажите центр пластины",
        )
        if center is None:
            return False

        plate_data["insert_point"] = center

        # --- Построение ---
        plate.draw(model, center)

        regen(adoc)
        return True

    except ATError as err:
        err.show()
        return False


# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_data = {
        "width": 170.0,
        "height": 170.0,
        "corners": {
            "rb": 20,         # острый
            "rt": 20.0,      # скругление R30
            "lt": 20.0,      # скругление R30
            "lb": 20.0,     # фаска 20×20
        },
        "holes": [
            {"type": "circle", "cx": 0,   "cy": -70,  "r": 2.75},
            #{"type": "circle", "cx": 100, "cy": -60, "r": 11.0},
            #{"type": "slot",   "cx": -80, "cy": -30,   "length": 60, "diameter": 22, "angle": 0},
        ],
        "order":     "20387-1",
        "detail":    "17-4",
        "material":  "1.4301",
        "thickness": 4,
    }
    main(test_data)
