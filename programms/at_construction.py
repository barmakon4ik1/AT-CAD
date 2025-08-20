# programms/at_construction.py
"""
Файл: at_construction.py
Путь: programms/at_construction.py

Описание:
Модуль для создания геометрических объектов в AutoCAD через COM-интерфейс.
Переданный слой должен быть установлен как активный в системе.

Дополнено:
- Используется локальная регистрация переводов через locales.at_translations.loc.
- Убраны все успешные всплывающие сообщения — построения выполняются тихо.
- Логирование ведётся ТОЛЬКО по ошибкам (без info).
- Сохранены все исходные функции построения и тестовый блок запуска.

Примечание:
Для работы модуль ожидает, что AutoCAD уже запущен и инициализирован через ATCadInit.
"""

from typing import Optional, Any, List, Union
import os
import sys
import logging
import pythoncom
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from programms.at_base import regen
from programms.at_dimension import add_dimension
from programms.at_geometry import add_rectangle_points, offset_point, polar_point
from programms.at_input import at_point_input
from windows.at_gui_utils import show_popup
from config.at_config import DEFAULT_TEXT_LAYER
from locales.at_translations import loc
from programms.at_geometry import ensure_point_variant

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "autocad_not_running": {
        "ru": "AutoCAD не запущен. Сначала откройте AutoCAD.",
        "en": "AutoCAD is not running. Please start AutoCAD first.",
        "de": "AutoCAD läuft nicht. Bitte starten Sie zuerst AutoCAD."
    },
    "point_selection_cancelled": {
        "ru": "Выбор точки отменён.",
        "en": "Point selection cancelled.",
        "de": "Punktauswahl abgebrochen."
    },
    "circle_error": {
        "ru": "Ошибка при создании окружности: {0}",
        "en": "Error creating circle: {0}",
        "de": "Fehler beim Erstellen des Kreises: {0}"
    },
    "line_error": {
        "ru": "Ошибка при создании линии: {0}",
        "en": "Error creating line: {0}",
        "de": "Fehler beim Erstellen der Linie: {0}"
    },
    "polyline_error": {
        "ru": "Ошибка при создании полилинии: {0}",
        "en": "Error creating lightweight polyline: {0}",
        "de": "Fehler beim Erstellen der Leichtpolylinie: {0}"
    },
    "rectangle_error": {
        "ru": "Ошибка при создании прямоугольника: {0}",
        "en": "Error creating rectangle: {0}",
        "de": "Fehler beim Erstellen des Rechtecks: {0}"
    },
    "text_error": {
        "ru": "Ошибка при создании текста: {0}",
        "en": "Error creating text: {0}",
        "de": "Fehler beim Erstellen des Textes: {0}"
    }
}
# Регистрируем переводы сразу при загрузке модуля (до любых вызовов loc.get)
loc.register_translations(TRANSLATIONS)

# -----------------------------
# Логирование (только ошибки)
# -----------------------------
_LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "at_construction.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
# не трогаем глобальную конфигурацию — свой файловый handler
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == _LOG_FILE for h in logger.handlers):
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
logger.propagate = False


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
    except Exception as e:
        logger.error("add_circle failed: %s", e)
        show_popup(loc.get("circle_error", "Ошибка при создании окружности: {0}", str(e)), popup_type="error")
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
    except Exception as e:
        logger.error("add_line failed: %s", e)
        show_popup(loc.get("line_error", "Ошибка при создании линии: {0}", str(e)), popup_type="error")
        return None


def add_polyline(model: Any, points: Union[VARIANT, List[VARIANT]],
                   layer_name: str = "0", closed: bool = True) -> Optional[Any]:
    """
    Создаёт легковесную полилинию в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        points: COM VARIANT с координатами вершин (x1, y1, x2, y2, ...)
                или список VARIANT-объектов с точками [x, y, z].
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
            raise TypeError("Точки должны быть типа VARIANT либо списком объектов VARIANT")

        polyline = model.AddLightWeightPolyline(points_variant)
        polyline.Closed = closed
        polyline.Layer = layer_name
        return polyline
    except Exception as e:
        logger.error("add_polyline failed: %s", e)
        show_popup(loc.get("polyline_error", "Ошибка при создании полилинии: {0}", str(e)), popup_type="error")
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
        # Вычисляем координаты прямоугольника (возвращается VARIANT плоских координат)
        points_variant = add_rectangle_points(point, width, height, point_direction)

        # Создаём полилинию
        polyline = add_polyline(model, points_variant, layer_name=layer_name, closed=True)
        return polyline
    except Exception as e:
        logger.error("add_rectangle failed: %s", e)
        show_popup(loc.get("rectangle_error", "Ошибка при создании прямоугольника: {0}", str(e)), popup_type="error")
        return None


def add_text(model: Any, point: Union[List[float], VARIANT],
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
    except Exception as e:
        logger.error("at_addText failed: %s", e)
        show_popup(loc.get("text_error", "Ошибка при создании текста: {0}", str(e)), popup_type="error")
        return None


if __name__ == "__main__":
    """
    Тестирование создания текста, окружности, линии, полилинии и прямоугольника
    с использованием точки, полученной через at_point_input().

    Порядок:
      1) Проверяется инициализация AutoCAD (должен быть уже запущен).
      2) Запрашивается базовая точка у пользователя.
      3) Создаются объекты: текст, окружность, линия, полилиния (3 точки), прямоугольник.
      4) Ставит размер (add_dimension) и выполняет regen().
    """
    cad = ATCadInit()

    if cad.is_initialized():
        logging.info("AutoCAD initialized successfully")
        loc.register_translations(TRANSLATIONS)

        adoc = cad.document
        model = cad.model_space

        # Запрашиваем точку у пользователя (at_point_input уже возвращает готовый VARIANT)
        input_point = at_point_input(adoc, prompt="Укажите центр окружности")

        if input_point:
            try:
                # Вычисляем дополнительные точки с помощью полярных координат
                point2 = polar_point(input_point, distance=400, alpha=90)
                point3 = polar_point(input_point, distance=400, alpha=60)
                point4 = polar_point(input_point, distance=400, alpha=120)

                # Создание текста
                add_text(model, polar_point(input_point, distance=500, alpha=90), "Тестовый текст")

                # Создание окружности
                add_circle(model, input_point, 200, layer_name="AM_0")

                # Создание линии
                add_line(model, input_point, point2, layer_name="AM_7")

                # Создание полилинии
                polyline_points = [input_point, point3, point4]
                add_polyline(model, polyline_points, layer_name="LASER-TEXT")

                # Создание прямоугольника
                width, height = 500, 300
                add_rectangle(model, input_point, width, height, layer_name="SF-TEXT")
                end_point = offset_point(input_point, width, height)

                # Размер
                add_dimension(adoc, "H", input_point, end_point)

                # Обновляем экран
                regen(adoc)

            except Exception as e:
                # На случай ошибки в сценарии теста (в т.ч. COM-ошибок)
                logger.error("__main__ test scenario failed: %s", e)
                show_popup(str(e), popup_type="error")
        else:
            print(loc.get("point_selection_cancelled", "Выбор точки отменён."))
    else:
        sys.exit(1)
