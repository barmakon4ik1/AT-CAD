# -*- coding: utf-8 -*-
"""
File: programs/at_nozzle.py
Назначение: Построение развертки патрубка
прямоугольного простого переходного тройника
с сопутствующими данными (текстами, размерами и т.п.)
Поддерживает три режима:
    - polyline (отрезки)
    - bulge (полилиния с дугами: верхняя часть криволинейная, левая/нижняя/правая стороны прямые)
    - spline (сплайн для верхней части, полилиния для боковых и нижней сторон)
"""

import math
from typing import Dict, Any, List, Tuple
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs.at_base import regen
from programs.at_construction import add_text, add_polyline, add_spline
from programs.at_geometry import ensure_point_variant, polar_point, convert_to_variant_points, circle_center_from_points
from programs.at_construction import add_line, add_dimension
from programs.at_input import at_point_input
from windows.at_gui_utils import show_popup
from config.at_config import TEXT_HEIGHT_SMALL, DEFAULT_DIM_OFFSET

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "invalid_point_format": {
        "ru": "Точка вставки должна быть [x, y, 0]",
        "de": "Einfügepunkt muss [x, y, 0] sein",
        "en": "Insertion point must be [x, y, 0]"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "de": "Baufehler: {0}",
        "en": "Build error: {0}"
    },
    "text_error_details": {
        "ru": "Ошибка добавления текста {0} ({1}): {2}",
        "de": "Fehler beim Hinzufügen von Text {0} ({1}): {2}",
        "en": "Error adding text {0} ({1}): {2}"
    },
    "material_text": {
        "ru": "{0} мм {1}",
        "de": "{0} mm {1}",
        "en": "{0} mm {1}"
    },
    "contour_not_built": {
        "ru": "Контур выреза не построен (нет допустимых точек)",
        "de": "Schnittkontur nicht erstellt (keine gültigen Punkte)",
        "en": "Cutout contour not built (no valid points)"
    },
    "unknown_mode": {
        "ru": "Неизвестный режим: {0}",
        "de": "Unbekannter Modus: {0}",
        "en": "Unknown mode: {0}"
    },
}
loc.register_translations(TRANSLATIONS)


# -----------------------------
# Вспомогательные функции
# -----------------------------
def build_unwrapped_contour(
    insert_point: List[float],
    diameter: float,
    diameter_main: float,
    length: float,
    weld_allowance: float,
    accuracy: int,
    offset: float,
    thickness: float,
    thk_correction: bool,
    mode: str
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float, float]], List[float], float]:
    """
    Строит контур развёртки.

    Args:
        insert_point: Точка вставки [x, y, z].
        diameter: Диаметр отвода.
        diameter_main: Диаметр основной трубы.
        length: Длина патрубка.
        weld_allowance: Припуск на сварку.
        accuracy: Количество делений развертки.
        offset: Смещение центра.
        thickness: Толщина материала.
        thk_correction: Признак корректировки толщины.
        mode: "polyline", "bulge" или "spline" (режим построения контура).

    Returns:
        contour_upper: Список координат верхней криволинейной части [(x, y, bulge), ...].
        contour_rect: Список координат прямоугольной части (правая, нижняя, левая стороны) [(x, y, bulge), ...].
        generatrix_length: Список длин образующих.
        width: Полная ширина развертки.
    """
    length_full = length + weld_allowance
    radius = (diameter - thickness) / 2.0 if thk_correction else diameter / 2.0
    width = 2 * math.pi * radius

    angle_list = [2 * math.pi - i * (math.pi / (0.5 * accuracy)) for i in range(accuracy + 1)]

    generatrix_length = [
        length_full - math.sqrt((0.5 * diameter_main) ** 2.0 - (math.sin(w) * radius + offset) ** 2.0)
        for w in angle_list
    ]

    # Формируем точки верхней части (криволинейной)
    point_list = [
        (
            insert_point[0] + x * (width / accuracy),
            insert_point[1] + y
        )
        for x, y in zip(range(accuracy + 1), generatrix_length)
    ]

    # Удаляем дубликаты в верхней части
    dedup_tol = 1e-6
    dedup: List[Tuple[float, float]] = [point_list[0]]
    for pt in point_list[1:]:
        last = dedup[-1]
        if abs(pt[0] - last[0]) > dedup_tol or abs(pt[1] - last[1]) > dedup_tol:
            dedup.append(pt)
    point_list = dedup

    n_upper = len(point_list)
    if n_upper < 2:
        return [], [], generatrix_length, width

    # Вычисление bulges для верхней части (для режима bulge или spline)
    bulges_contour = []
    extended_pts = [point_list[-1]] + point_list + [point_list[0]]  # Замкнутость для верхней части

    for i in range(1, n_upper + 1):
        prev_i = i - 1
        next_i = i + 1
        p0 = extended_pts[prev_i]
        p1 = extended_pts[i]
        p2 = extended_pts[next_i]
        if mode == "polyline" or i == n_upper:  # Устанавливаем bulge=0 для последней точки
            bulges_contour.append(0.0)
            continue
        center = circle_center_from_points(p0, p1, p2)
        if center is None:
            bulges_contour.append(0.0)
            continue
        cx, cy = center
        ang1 = math.atan2(p1[1] - cy, p1[0] - cx)
        ang2 = math.atan2(p2[1] - cy, p2[0] - cx)
        sweep = ang2 - ang1
        sweep = (sweep + math.pi) % (2 * math.pi) - math.pi
        bulges_contour.append(math.tan(sweep / 4.0))

    # Подмена bulge для первого сегмента
    if len(bulges_contour) >= 2 and mode != "polyline":
        bulges_contour[0] = bulges_contour[-2]  # Симметрия относительно предпоследнего сегмента

    # Формируем верхний контур с bulges
    contour_upper: List[Tuple[float, float, float]] = [
        (x, y, b) for (x, y), b in zip(point_list, bulges_contour)
    ]

    # Формируем прямоугольную часть (правая, нижняя, левая стороны)
    contour_rect: List[Tuple[float, float, float]] = [
        (insert_point[0] + width, insert_point[1] + generatrix_length[-1], 0.0),  # правая верхняя
        (insert_point[0] + width, insert_point[1], 0.0),  # правая нижняя
        (insert_point[0], insert_point[1], 0.0),  # левая нижняя
        (insert_point[0], insert_point[1] + generatrix_length[0], 0.0)  # левая верхняя
    ]

    return contour_upper, contour_rect, generatrix_length, width


def get_profile_point(
    insert_point: List[float],
    width: float,
    generatrix_length: List[float],
    accuracy: int,
    frac: float
):
    """
    Возвращает координаты точки на профиле.

    Args:
        insert_point: Точка вставки [x, y, z].
        width: Общая ширина развертки.
        generatrix_length: Массив длин образующих.
        accuracy: Количество делений развертки.
        frac: Доля по ширине (0.0 ... 1.0).

    Returns:
        p_bottom_variant: Точка на нижней линии (variant).
        p_top_variant: Точка на верхней линии (variant).
        (x, y): Числовые координаты верхней точки.
    """
    idx = min(int(frac * accuracy), accuracy)
    x = insert_point[0] + idx * (width / accuracy)
    y = insert_point[1] + generatrix_length[idx]
    p_top = ensure_point_variant([x, y, 0])
    p_bottom = ensure_point_variant([x, insert_point[1], 0])
    return p_bottom, p_top, (x, y)


def build_axes(model, insert_point, width, generatrix_length, accuracy):
    """
    Строит вертикальные оси в долях 1/4, 1/2, 3/4 ширины.
    """
    axis_fracs = [1/4, 1/2, 3/4]
    axis_layer = "AM_5"
    for frac in axis_fracs:
        p_bottom, p_top, _ = get_profile_point(insert_point, width, generatrix_length, accuracy, frac)
        add_line(model, p_bottom, p_top, layer_name=axis_layer)


def build_axis_marks(model, insert_point, width, generatrix_length, accuracy, axis_marks):
    """
    Рисует метки на осях сверху и снизу.

    Args:
        model: Пространство модели.
        insert_point: Точка вставки.
        width: Ширина развертки.
        generatrix_length: Список длин образующих.
        accuracy: Количество делений.
        axis_marks: Длина метки (если 0 - не строим).
    """
    if axis_marks <= 0:
        return

    axis_fracs = [1/4, 1/2, 3/4]
    mark_layer = "LASER-TEXT"

    for frac in axis_fracs:
        p_bottom, p_top, (x, y_top) = get_profile_point(insert_point, width, generatrix_length, accuracy, frac)
        y_bottom = insert_point[1]

        # метка снизу
        mark_bottom_start = ensure_point_variant([x, y_bottom, 0])
        mark_bottom_end = ensure_point_variant([x, y_bottom + axis_marks, 0])
        add_line(model, mark_bottom_start, mark_bottom_end, layer_name=mark_layer)

        # метка сверху
        mark_top_start = ensure_point_variant([x, y_top, 0])
        mark_top_end = ensure_point_variant([x, y_top - axis_marks, 0])
        add_line(model, mark_top_start, mark_top_end, layer_name=mark_layer)


def build_dimensions(adoc, insert_point, width, generatrix_length, accuracy, rights_bottom_point):
    """
    Добавляет размеры H и V.

    Args:
        adoc: Документ AutoCAD.
        insert_point: Точка вставки.
        width: Ширина развертки.
        generatrix_length: Список длин образующих.
        accuracy: Количество делений.
        rights_bottom_point: Правая нижняя точка.
    """
    bottom_left_point = ensure_point_variant(insert_point)
    rights_bottom_point = ensure_point_variant(rights_bottom_point)

    add_dimension(adoc, "H", rights_bottom_point, bottom_left_point, offset=DEFAULT_DIM_OFFSET)

    _, top_left_point, _ = get_profile_point(insert_point, width, generatrix_length, accuracy, 0)
    add_dimension(adoc, "V", bottom_left_point, top_left_point, offset=DEFAULT_DIM_OFFSET)

    bottom_quarter, top_quarter, _ = get_profile_point(insert_point, width, generatrix_length, accuracy, 1/4)
    add_dimension(adoc, "V", bottom_quarter, top_quarter, offset=2 * DEFAULT_DIM_OFFSET + width / 4.0)


# -----------------------------
# Основная функция
# -----------------------------
def main(data):
    """
    Чтобы функция корректно работала в связке с остальными программами в основном окне.
    """
    return at_nozzle(data)

def at_nozzle(data: Dict[str, Any]) -> bool:
    """
    Основная функция построения развертки патрубка.

    Args:
        data: Словарь параметров, содержит:
            insert_point: [x, y, z] точка вставки.
            diameter: Диаметр отвода.
            diameter_main: Диаметр основной трубы.
            length: Длина патрубка.
            axis: Флаг построения осей.
            axis_marks: Длина меток на осях.
            layer_name: Имя слоя для контура.
            thickness: Толщина материала.
            order_number: Номер заказа.
            detail_number: Номер детали.
            material: Марка материала.
            weld_allowance: Припуск на сварку.
            accuracy: Количество делений.
            offset: Смещение центра.
            thk_correction: Корректировка толщины отвода равнопроходного тройника.
            mode: "polyline", "bulge" или "spline" (режим построения контура).

    Returns:
        bool: True при успешном построении, False при ошибке.
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return False

        insert_point = data.get("insert_point")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")
        diameter = float(data.get("diameter", 0.0))
        diameter_main = float(data.get("diameter_main", 0.0))
        length = float(data.get("length", 0.0))
        axis = data.get("axis", True)
        axis_marks = float(data.get("axis_marks", 0.0))
        layer_name = data.get("layer_name", "0")
        weld_allowance = float(data.get("weld_allowance", 0.0))
        accuracy = int(data.get("accuracy", 180))
        offset = float(data.get("offset", 0.0))
        thk_correction = data.get("thk_correction", False)
        mode = data.get("mode", "polyline").lower()

        insert_point = list(map(float, insert_point[:3]))
        data["insert_point"] = insert_point

        # Вызов функции build_unwrapped_contour
        contour_upper, contour_rect, generatrix_length, width = build_unwrapped_contour(
            insert_point, diameter, diameter_main, length, weld_allowance, accuracy, offset, thickness, thk_correction, mode
        )
        rights_bottom_point = (insert_point[0] + width, insert_point[1])

        if not contour_upper or not contour_rect:
            show_popup(loc.get("contour_not_built"), popup_type="error")
            return False

        # Построение контура в зависимости от режима
        if mode == "polyline" or mode == "bulge":
            # Объединяем верхнюю и прямоугольную части в единый контур
            contour_with_bulge = contour_upper + contour_rect[1:]  # Пропускаем первую точку contour_rect
            add_polyline(model, contour_with_bulge, layer_name=layer_name, closed=True)
        elif mode == "spline":
            # Верхняя часть как сплайн
            points_xy = [[x, y] for x, y, _ in contour_upper]
            add_spline(model, points_xy, layer_name=layer_name, closed=False)
            # Прямоугольная часть как полилиния
            add_polyline(model, contour_rect, layer_name=layer_name, closed=False)
            # Соединяем концы сплайна и полилинии для замыкания
            add_line(model,
                     ensure_point_variant([contour_upper[-1][0], contour_upper[-1][1], 0]),
                     ensure_point_variant([contour_rect[0][0], contour_rect[0][1], 0]),
                     layer_name=layer_name)
            add_line(model,
                     ensure_point_variant([contour_rect[-1][0], contour_rect[-1][1], 0]),
                     ensure_point_variant([contour_upper[0][0], contour_upper[0][1], 0]),
                     layer_name=layer_name)
        else:
            show_popup(loc.get("unknown_mode").format(mode), popup_type="info")
            return False

        if axis:
            build_axes(model, insert_point, width, generatrix_length, accuracy)
        if axis_marks > 0:
            build_axis_marks(model, insert_point, width, generatrix_length, accuracy, axis_marks)

        build_dimensions(adoc, insert_point, width, generatrix_length, accuracy, rights_bottom_point)

        k_text = f"{order_number}"
        f_text = k_text if not detail_number else f"{k_text}-{detail_number}"

        text_point = polar_point(insert_point, 20, 45, as_variant=False)

        text_configs = [
            {
                "point": ensure_point_variant(text_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 12
            },
            {
                "point": ensure_point_variant(
                    polar_point(text_point, distance=10, alpha=90, as_variant=False)
                ),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": TEXT_HEIGHT_SMALL,
                "text_angle": 0,
                "text_alignment": 12
            }
        ]

        for i, config in enumerate(text_configs):
            try:
                add_text(model, **config)
            except Exception as e:
                show_popup(
                    loc.get("text_error_details").format(i + 1, config['text'], str(e)),
                    popup_type="error"
                )
                return False

        _, top_quarter_variant, (x_quarter, y_quarter) = get_profile_point(
            insert_point, width, generatrix_length, accuracy, 1 / 4
        )
        mat_point = polar_point(insert_point, distance=(y_quarter + 30), alpha=90, as_variant=False)
        mat_point = ensure_point_variant(mat_point)
        mat_text = loc.get("material_text").format(thickness, material)
        add_text(model, mat_point, mat_text, layer_name="AM_5", text_alignment=0)


        regen(adoc)
        return True

    except Exception as e:
        show_popup(
            loc.get("build_error").format(str(e)),
            popup_type="error"
        )
        return False


if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    input_data = {
        "insert_point": at_point_input(adoc, prompt=loc.get("select_point", "Укажите центр отвода"), as_variant=False),
        "diameter": 163.3,
        "diameter_main": 800.0,
        "length": 495.0,
        "axis": False,
        "axis_marks": 0.0,
        "layer_name": "0",
        "thickness": 5.0,
        "order_number": "20202",
        "detail_number": "17",
        "material": "1.4301",
        "weld_allowance": 3.0,
        "accuracy": 16,
        "offset": 0.0,
        "thk_correction": False,
        "mode": "bulge"
    }
    at_nozzle(input_data)
