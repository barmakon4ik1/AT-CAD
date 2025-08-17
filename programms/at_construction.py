# programms/at_construction.py
"""
Файл: at_construction.py
Путь: programms/at_construction.py

Описание:
Модуль для создания геометрических объектов в AutoCAD через COM-интерфейс.
Переданный слой должен быть установлен как активный в системе.

Дополнено:
- Добавлена универсальная функция ensure_point_variant() для гарантированного преобразования любых входных данных точки
  (список, кортеж, генератор, готовый VARIANT) в COM-тип VARIANT(VT_ARRAY | VT_R8) с координатами [x, y, z].
- Это исключает необходимость ручного преобразования точек в каждой функции.
"""

from typing import Optional, Any, List, Tuple, Union
import math
import array
import pythoncom
from win32com.client import VARIANT

from programms.at_base import regen
from programms.at_dimension import add_dimension
from programms.at_geometry import add_rectangle_points, offset_point
from programms.at_input import at_point_input
from windows.at_gui_utils import show_popup
from config.at_config import DEFAULT_TEXT_LAYER
from locales.at_localization_class import loc
from programms.at_geometry import ensure_point_variant


def add_circle(model: Any, center: Union[List[float], VARIANT], radius: float,
               layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт окружность в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        center: Координаты центра окружности (список, кортеж или готовый VARIANT).
        radius: Радиус окружности.
        layer_name: Имя слоя для окружности.

    Returns:
        Объект окружности или None при ошибке.
    """
    try:
        circle = model.AddCircle(ensure_point_variant(center), radius)
        circle.Layer = layer_name
        return circle
    except:
        return None


def add_line(model: Any, point1: Union[List[float], VARIANT],
             point2: Union[List[float], VARIANT],
             layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт линию в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point1: Начальная точка линии.
        point2: Конечная точка линии.
        layer_name: Имя слоя для линии.

    Returns:
        Объект линии или None при ошибке.
    """
    try:
        line = model.AddLine(ensure_point_variant(point1), ensure_point_variant(point2))
        line.Layer = layer_name
        return line
    except:
        return None


def add_LWpolyline(model: Any, points: Union[VARIANT, List[VARIANT]], layer_name: str = "0", closed: bool = True) -> Optional[Any]:
    """
    Создаёт легковесную полилинию в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        points: COM VARIANT с координатами вершин (x1, y1, x2, y2, ...) или список VARIANT-объектов с точками [x, y, z].
        layer_name: Имя слоя для полилинии.
        closed: Закрывать полилинию или нет (по умолчанию True).

    Returns:
        Объект полилинии или None при ошибке.
    """
    try:
        # Если передан список VARIANT-объектов, преобразуем в плоский VARIANT
        if isinstance(points, list) and all(isinstance(p, VARIANT) for p in points):
            flat_points = []
            for point in points:
                coords = point.value
                if len(coords) < 2 or any(c is None or not isinstance(c, (int, float)) for c in coords[:2]):
                    raise ValueError(f"Неправильные координаты точки: {coords}")
                flat_points.extend([float(coords[0]), float(coords[1])])
            points_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_points)
        elif isinstance(points, VARIANT):
            points_variant = points
        else:
            raise TypeError("Точки должны быть типа либо VARIANT, либо list или объектом VARIANT")

        # Создаём полилинию
        polyline = model.AddLightWeightPolyline(points_variant)
        polyline.Closed = closed
        polyline.Layer = layer_name
        return polyline
    except Exception as e:
        print(f"Ошибка в функции add_LWpolyline: {e}")
        return None


def add_rectangle(model: Any, point: Union[List[float], VARIANT],
                  width: float, height: float,
                  layer_name: str = "0",
                  point_direction: str = "left_bottom") -> Optional[Any]:
    """
    Создаёт прямоугольник в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point: Координаты базовой точки прямоугольника.
        width: Ширина прямоугольника.
        height: Высота прямоугольника.
        layer_name: Имя слоя для прямоугольника.
        point_direction: Положение базовой точки ("left_bottom", "center", и др.).

    Returns:
        Объект полилинии-прямоугольника или None при ошибке.
    """
    try:
        # Вычисляем координаты прямоугольника
        points_variant = add_rectangle_points(point, width, height, point_direction)

        # Создаём полилинию
        polyline = add_LWpolyline(model, points_variant, layer_name=layer_name, closed=True)
        return polyline
    except Exception as e:
        print(f"Error in add_rectangle: {e}")
        return None


def at_addText(model: Any, point: Union[List[float], VARIANT],
               text: str = "",
               layer_name: str = DEFAULT_TEXT_LAYER,
               text_height: float = 30,
               text_angle: float = 0,
               text_alignment: int = 4) -> Optional[Any]:
    """
    Создаёт текст в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point: Координаты базовой точки текста.
        text: Содержимое текста.
        layer_name: Имя слоя для текста.
        text_height: Высота текста.
        text_angle: Угол поворота текста (в радианах).
        text_alignment: Код выравнивания текста (0 - по умолчанию, 4 - центр и т.д.).

    Returns:
        Объект текста или None при ошибке.

    Notes:
    Значения выравнивания text_alignment:
    0: acAlignmentLeft, 1: acAlignmentCenter, 2: acAlignmentRight,
    3: acAlignmentAligned, 4: acAlignmentMiddle, 5: acAlignmentFit,
    6: acAlignmentTopLeft, 7: acAlignmentTopCenter, 8: acAlignmentTopRight,
    9: acAlignmentMiddleLeft, 10: acAlignmentMiddleCenter, 11: acAlignmentMiddleRight,
    12: acAlignmentBottomLeft, 13: acAlignmentBottomCenter, 14: acAlignmentBottomRight.
    """
    try:
        point_variant = ensure_point_variant(point)
        text_object = model.AddText(text, point_variant, text_height)
        text_object.Layer = layer_name
        text_object.Alignment = text_alignment
        if text_alignment not in [0, 1, 2]:
            text_object.TextAlignmentPoint = point_variant
        text_object.Rotation = text_angle
        return text_object
    except:
        return None


if __name__ == "__main__":
    """
    Тестирование создания текста, окружности, линии, полилинии и прямоугольника
    с использованием точки, полученной через at_point_input().
    """
    from config.at_cad_init import ATCadInit
    from programms.at_geometry import polar_point

    cad = ATCadInit()

    # Запрашиваем точку у пользователя (at_point_input уже возвращает готовый VARIANT)
    input_point = at_point_input(cad.adoc, prompt="Укажите центр окружности")

    if input_point:
        # Вычисляем дополнительные точки с помощью полярных координат
        point2 = polar_point(input_point, distance=400, alpha=90)
        point3 = polar_point(input_point, distance=400, alpha=60)
        point4 = polar_point(input_point, distance=400, alpha=120)

        # Создание текста
        at_addText(cad.model, polar_point(input_point, distance=500, alpha=90), "Тестовый текст")

        # Создание окружности
        add_circle(cad.model, input_point, 200, layer_name="AM_0")

        # Создание линии
        add_line(cad.model, input_point, point2, layer_name="AM_7")

        # Создание полилинии
        polyline_points = [input_point, point3, point4]
        add_LWpolyline(cad.model, polyline_points, layer_name="LASER-TEXT")

        # Создание прямоугольника
        width, height = 500, 300
        add_rectangle(cad.model, input_point, width, height, layer_name="SF-TEXT")
        end_point = offset_point(input_point, width, height)
        add_dimension(cad.adoc, "H", input_point, end_point)

        # Обновляем экран
        regen(cad.adoc)
    else:
        print(loc.get("point_selection_cancelled", "Выбор точки отменён."))
