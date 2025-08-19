# programms/at_run_plate.py
"""
Модуль для построения листа для лазерной резки в AutoCAD с использованием Win32com (COM).

Создаёт внешнюю и внутреннюю замкнутые полилинии, проставляет размеры и добавляет текст.
Совместим с функциями построения из programms.at_construction (add_polyline, add_text).

Правила размеров (список вершин против часовой):
- Базовые 4 точки: 0 (ЛЛ), 1 (ПН), 2 (ПВ), 3 (ЛВ).
- Если точек >4: далее 4-5-6-7 (последняя) и замыкание на 0.

Порядок размеров:
Горизонтальные: (1,0), если >4 то (3,2), если ≥6 то (5,2).
Вертикальные:   (2,1), если >4 то (0,5), если ≥8 то (0,7).

Меньший размер — меньший offset.
"""

from typing import Dict, Any, List, Tuple
import logging
import sys

import pythoncom
import win32com.client  # COM

from config.at_cad_init import ATCadInit
from programms.at_calculation import at_plate_weight, at_density
from programms.at_construction import add_polyline, add_text
from programms.at_dimension import add_dimension
from programms.at_base import regen
from programms.at_offset import at_offset
from programms.at_geometry import ensure_point_variant
from windows.at_gui_utils import show_popup
from config.at_config import (
    DEFAULT_DIM_OFFSET,  # базовый отступ для размеров
    TEXT_HEIGHT_BIG
)
from locales.at_translations import loc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


def _points_to_variant_list(points_xy: List[Tuple[float, float]]) -> List:
    """[(x,y), ...] -> список VARIANT-точек [x,y,z] для add_polyline()."""
    return [ensure_point_variant([float(x), float(y), 0.0]) for x, y in points_xy]


def _build_dimension_pairs(points_xy: List[Tuple[float, float]]):
    """
    Формирует пары для размеров по заданным правилам.
    Возвращает два списка: pairs_h, pairs_v, где каждая пара — индексы вершин (i, j).
    """
    n = len(points_xy)
    pairs_h: List[Tuple[int, int]] = []
    pairs_v: List[Tuple[int, int]] = []

    if n >= 2:
        pairs_h.append((1, 0))  # базовый H
    if n >= 3:
        pairs_v.append((2, 1))  # базовый V
    if n > 4:
        # дополнительные при >4
        if n >= 4:
            pairs_h.append((3, 2))
        if n >= 6:
            pairs_h.append((5, 2))
            pairs_v.append((0, 5))
        if n >= 8:
            pairs_v.append((0, 7))

    # фильтр на валидные индексы
    pairs_h = [(i, j) for (i, j) in pairs_h if i < n and j < n]
    pairs_v = [(i, j) for (i, j) in pairs_v if i < n and j < n]
    return pairs_h, pairs_v


def _dim_length(points_xy: List[Tuple[float, float]], pair: Tuple[int, int], orient: str) -> float:
    """Длина размера для сортировки (H — по Δx, V — по Δy)."""
    (i, j) = pair
    (x1, y1), (x2, y2) = points_xy[i], points_xy[j]
    if orient == "H":
        return abs(x2 - x1)
    return abs(y2 - y1)


def _apply_dimensions_with_offsets(
    adoc,
    points_xy: List[Tuple[float, float]],
    pairs_h: List[Tuple[int, int]],
    pairs_v: List[Tuple[int, int]],
    thickness: float
) -> float:
    """
    Ставит размеры с возрастающими offset внутри каждой группы (H и V)
    так, чтобы более короткие имели меньший offset.
    Возвращает Y максимальной горизонтальной размерной линии (для расчёта высоты текста).
    """
    # базовый и шаг (можно при желании сделать параметрами)
    base = DEFAULT_DIM_OFFSET + max(0.0, float(thickness)) * 2.0
    step = max(60.0, float(thickness) * 5.0)  # разнос между линиями

    max_y_line = max(y for _, y in points_xy)  # на случай отсутствия H-замеров

    # Горизонтальные: сортируем по длине по возрастанию (короче — ближе)
    pairs_h_sorted = sorted(pairs_h, key=lambda pr: _dim_length(points_xy, pr, "H"))
    for rank, (i, j) in enumerate(pairs_h_sorted):
        p1 = ensure_point_variant([points_xy[i][0], points_xy[i][1], 0.0])
        p2 = ensure_point_variant([points_xy[j][0], points_xy[j][1], 0.0])
        offset = base + rank * step
        add_dimension(adoc, "H", p1, p2, offset=offset)
        # горизонтальная размерная линия идёт выше верхней из точек пары
        y_line = max(points_xy[i][1], points_xy[j][1]) + offset
        if y_line > max_y_line:
            max_y_line = y_line

    # Вертикальные: сортируем по длине по возрастанию (короче — ближе)
    pairs_v_sorted = sorted(pairs_v, key=lambda pr: _dim_length(points_xy, pr, "V"))
    for rank, (i, j) in enumerate(pairs_v_sorted):
        p1 = ensure_point_variant([points_xy[i][0], points_xy[i][1], 0.0])
        p2 = ensure_point_variant([points_xy[j][0], points_xy[j][1], 0.0])
        offset = base + rank * step
        add_dimension(adoc, "V", p1, p2, offset=offset)
        # вертикальная размерная линия уходит вправо; по Y она ограничена самими точками
        # (на высоту текста это не влияет), но на всякий держим максимум по Y точек
        # уже учтён max_y_line выше.

    return max_y_line


def run_plate(adoc: Any, plate_data: Dict[str, Any]) -> bool:
    """
    Построение листа: внешняя и внутренняя полилинии, размеры и текст.
    """
    pythoncom.CoInitialize()
    try:
        model = adoc.ModelSpace

        insert_point = plate_data.get("insert_point", (0.0, 0.0))
        polyline_points: List[Tuple[float, float]] = plate_data.get("polyline_points", [])
        allowance = float(plate_data.get("allowance", 0.0))

        # --- внешняя полилиния ---
        points_variant_list = _points_to_variant_list(polyline_points)
        poly = add_polyline(model, points_variant_list, layer_name="SF-TEXT", closed=True)

        # --- площадь для массы ---
        area = float(poly.Area)

        # --- свойства материала ---
        material = plate_data.get("material", "")
        thickness = float(plate_data.get("thickness", 0.0))
        melt_no = plate_data.get("melt_no", "")

        density = at_density(material)
        weight = at_plate_weight(thickness, density, area)

        # --- пары размеров по правилам ---
        pairs_h, pairs_v = _build_dimension_pairs(polyline_points)

        # --- постановка размеров с корректной иерархией offset ---
        max_y_dim_line = _apply_dimensions_with_offsets(adoc, polyline_points, pairs_h, pairs_v, thickness)

        # --- текст над самым верхним размером + 60 мм ---
        text_point = (insert_point[0], max_y_dim_line + 60.0, 0.0)
        text_str = f"{thickness:g} mm {material}, {weight:g} kg, Ch. {melt_no}"
        add_text(model, point=text_point, text=text_str, layer_name="AM_5",
                 text_height=TEXT_HEIGHT_BIG, text_angle=0, text_alignment=0)

        # --- внутренний контур ---
        at_offset(poly, allowance, adoc, model)

        regen(adoc)
        logging.info("Полилиния, размеры и текст успешно созданы")
        return True

    except Exception as e:
        show_popup(f"Ошибка: {str(e)}", popup_type="error")
        logging.error(f"Ошибка в run_plate: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    cad = ATCadInit()
    if not cad.is_initialized():
        sys.exit(0)

    adoc = cad.adoc

    # Пример: 8 точек (0..7), против часовой
    input_data = {
        "insert_point": (0, 0),
        "polyline_points": [
            (0, 0),     # 0: ЛЛ
            (3000, 0),  # 1: ПН
            (3000, 1500),  # 2: ПВ
            (2000, 1500),  # 3: ЛВ наружного участка
            (2000, 1000),  # 4
            (1000, 1000),  # 5
            (1000, 500),   # 6
            (0, 500)       # 7
        ],
        "material": "1.4301",
        "thickness": 4.0,
        "melt_no": "123456-789",
        "allowance": 10.0
    }

    ok = run_plate(adoc, input_data)
    logging.info("Готово" if ok else "Выполнено с ошибками")
