"""
File: programms/at_nozzle.py
Назначение: Построение развертки патрубка
прямоугольного простого переходного тройника
с сопутствующими данными (текстами, размерами и т.п.)
"""

import math
from typing import Dict, Any, List, Tuple
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_text, add_polyline
from programms.at_geometry import ensure_point_variant, polar_point, convert_to_variant_points
from at_construction import add_line, add_dimension
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
    }
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
    thickness_correction: bool
) -> Tuple[List[Tuple[float, float]], List[float], float]:
    """
    Строит контур развертки.

    Args:
        insert_point: Точка вставки [x, y, z].
        diameter: Диаметр отвода.
        diameter_main: Диаметр основной трубы.
        length: Длина патрубка.
        weld_allowance: Припуск на сварку.
        accuracy: Количество делений развертки.
        offset: Смещение центра.
        thickness: Толщина материала.
        thickness_correction: Признак корректировки толщины.

    Returns:
        point_list: Список координат контура.
        generatrix_length: Список длин образующих.
        width: Полная ширина развертки.
    """
    length_full = length + weld_allowance
    radius = (diameter - thickness) / 2.0 if thickness_correction else diameter / 2.0
    width = 2 * math.pi * radius

    angle_list = [2 * math.pi - i * (math.pi / (0.5 * accuracy)) for i in range(accuracy + 1)]

    generatrix_length = [
        length_full - math.sqrt((0.5 * diameter_main) ** 2.0 - (math.sin(w) * radius + offset) ** 2.0)
        for w in angle_list
    ]

    point_list = [
        (
            insert_point[0] + x * (width / accuracy),
            insert_point[1] + y
        )
        for x, y in zip(range(accuracy + 1), generatrix_length)
    ]

    point_list.append((insert_point[0] + width, insert_point[1]))
    point_list.append((insert_point[0], insert_point[1]))

    return point_list, generatrix_length, width


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

    Returns:
        True при успешном построении, иначе None.
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return None

        insert_point = data.get("insert_point")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")
        diameter = data.get("diameter", 0.0)
        diameter_main = float(data.get("diameter_main", 0.0))
        length = data.get("length", 0.0)
        axis = data.get("axis", True)
        axis_marks = data.get("axis_marks", 0.0)
        layer_name = data.get("layer_name", "0")
        weld_allowance = data.get("weld_allowance", 0.0)
        accuracy = data.get("accuracy", 180)
        offset = data.get("offset", 0.0)
        thickness_correction = True if diameter == diameter_main else False

        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format"), popup_type="error")
            return None
        insert_point = list(map(float, insert_point[:3]))
        data["insert_point"] = insert_point

        point_list, generatrix_length, width = build_unwrapped_contour(
            insert_point, diameter, diameter_main, length,
            weld_allowance, accuracy, offset, thickness, thickness_correction
        )
        rights_bottom_point = (insert_point[0] + width, insert_point[1])

        variant_points = convert_to_variant_points(point_list)
        add_polyline(model, variant_points, layer_name=layer_name)

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
                return None

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
    return None


if __name__ == "__main__":
    input_data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter": 150,
        "diameter_main": 300,
        "length": 250,
        "axis": False,
        "axis_marks": 10,
        "layer_name": "0",
        "thickness": "4.0",
        "order_number": "20196",
        "detail_number": "2-1",
        "material": "1.4301",
        "weld_allowance": 0.0,
        "accuracy": 180,
        "offset": 0.0,
    }
    at_nozzle(input_data)
