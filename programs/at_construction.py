"""
Файл: at_construction.py
Путь: programs/at_construction.py

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
import math
import sys
from typing import Optional, Any, List, Union, Sequence, Tuple
import os
import logging
from win32com.client import VARIANT
import pythoncom
from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_TEXT_LAYER, DEFAULT_DIM_OFFSET, TEXT_HEIGHT_BIG, TEXT_HEIGHT_SMALL, \
    TEXT_HEIGHT_LASER, DEFAULT_LASER_LAYER, MAIN_TEXT_OFFSET
from programs.at_base import regen
from programs.at_dimension import add_dimension
from programs.at_geometry import add_rectangle_points, offset_point, polar_point, ensure_point_variant, PolylineBuilder
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup
from locales.at_translations import loc
from contextlib import contextmanager

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
    "dia_error": {
        "ru": "Неверный тип диаметра.",
        "en": "Invalid diameter type",
        "de": "Ungültiger Durchmessertyp"
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
    },
    "invalid_number": {
        "ru": "Неверный формат числа.",
        "en": "Invalid number format.",
        "de": "Ungültiges Zahlenformat."
    },
    "diameter_base_positive": {
        "ru": "Диаметр основания должен быть положительным.",
        "en": "Base diameter must be positive.",
        "de": "Basisdurchmesser muss positiv sein."
    },
    "diameter_top_non_negative": {
        "ru": "Диаметр вершины не может быть отрицательным.",
        "en": "Top diameter cannot be negative.",
        "de": "Spitzendurchmesser darf nicht negativ sein."
    },
    "height_positive": {
        "ru": "Высота должна быть положительной.",
        "en": "Height must be positive.",
        "de": "Höhe muss positiv sein."
    },
    "invalid_result": {
        "ru": "Недопустимый результат вычислений.",
        "en": "Invalid calculation result.",
        "de": "Ungültiges Berechnungsergebnis."
    },
    "invalid_geometry": {
        "ru": "Недопустимая геометрия конуса.",
        "en": "Invalid cone geometry.",
        "de": "Ungültige Kegelgeometrie."
    },
    "invalid_bulge": {
        "ru": "Недопустимое значение выпуклости.",
        "en": "Invalid bulge value.",
        "de": "Ungültiger Wölbungswert."
    },
    "missing_data": {
        "ru": "Отсутствуют данные для вычислений.",
        "en": "Missing data for calculations.",
        "de": "Fehlende Daten für Berechnungen."
    },
    "both_parameters_error": {
        "ru": "Нельзя указывать одновременно наклон и угол.",
        "en": "Cannot specify both slope and angle.",
        "de": "Neigung und Winkel können nicht gleichzeitig angegeben werden."
    },
    "invalid_gradient": {
        "ru": "Неверный формат наклона.",
        "en": "Invalid slope format.",
        "de": "Ungültiges Neigungsformat."
    },
    "gradient_positive": {
        "ru": "Наклон должен быть положительным.",
        "en": "Slope must be positive.",
        "de": "Neigung muss positiv sein."
    },
    "invalid_angle": {
        "ru": "Неверный формат угла.",
        "en": "Invalid angle format.",
        "de": "Ungültiges Winkelformat."
    },
    "angle_range_error": {
        "ru": "Угол должен быть в диапазоне 0–180°.",
        "en": "Angle must be in the range 0–180°.",
        "de": "Winkel muss im Bereich 0–180° liegen."
    },
    "math_error": {
        "ru": "Ошибка математических вычислений.",
        "en": "Mathematical calculation error.",
        "de": "Fehler bei der mathematischen Berechnung."
    },
    "invalid_point": {
        "ru": "Некорректная точка вставки.",
        "en": "Invalid insertion point.",
        "de": "Ungültiger Einfügepunkt."
    },
    "cone_sheet_error": {
        "ru": "Ошибка построения развертки конуса: {0}",
        "en": "Error building cone sheet: {0}",
        "de": "Fehler beim Erstellen der Kegelabwicklung: {0}"
    },
    "spline_error": {
        "ru": "Ошибка при создании сплайна: {0}",
        "en": "Error creating spline: {0}",
        "de": "Fehler beim Erstellen der Spline: {0}"
    },
    "mm": {
        "ru": "мм",
        "de": "mm",
        "en": "mm"
    },
    "thickness_positive_error": {
        "ru": "Толщина должна быть положительной",
        "de": "Die Dicke muss positiv sein",
        "en": "The thickness must be positive"
    },
    "diameter_positive_error": {
        "ru": "Диаметр не может быть отрицательным",
        "de": "Der Durchmesser kann nicht negativ sein",
        "en": "The diameter cannot be negative"
    },
    "invalid_type": {
        "ru": "Неподдерживаемый тип данных.",
        "en": "Unsupported data type.",
        "de": "Nicht unterstützter Datentyp."
    },
    "point_normalization_error": {
        "ru": "Ошибка нормализации точки.",
        "en": "Point normalization error.",
        "de": "Fehler bei der Punktnormalisierung."
    },
    "invalid_points_format": {
        "ru": "Неверный формат списка точек.",
        "en": "Invalid points format.",
        "de": "Ungültiges Punkteformat."
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# -----------------------------
# Логирование (только ошибки)
# -----------------------------
_LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, "at_construction.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == _LOG_FILE for h in logger.handlers):
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
logger.propagate = False

PointLike = Union[Sequence[float], VARIANT]

# Вспомогательные методы
# -----------------------------
# Нормализация геометрии (ЕДИНЫЙ СТАНДАРТ)
# -----------------------------

def _normalize_point_2d(point: PointLike) -> Tuple[float, float]:
    """
    Приводит точку к формату (x, y).

    Поддерживает:
    - VARIANT([x, y, z])
    - list/tuple [x, y, ...]

    Returns:
        (x, y)
    """
    if isinstance(point, VARIANT):
        coords = list(point.value)
        if len(coords) < 2:
            raise ValueError("VARIANT точка содержит менее 2 координат")
        return float(coords[0]), float(coords[1])

    if isinstance(point, (list, tuple)):
        if len(point) < 2:
            raise ValueError("Точка должна содержать минимум x, y")
        return float(point[0]), float(point[1])

    raise TypeError(f"Неподдерживаемый тип точки: {type(point)}")


def _normalize_point_3d(point: PointLike) -> Tuple[float, float, float]:
    """
    Приводит точку к формату (x, y, z).

    Если z отсутствует → z = 0.0
    """
    if isinstance(point, VARIANT):
        coords = list(point.value)
        if len(coords) < 2:
            raise ValueError("VARIANT точка содержит менее 2 координат")
        z = float(coords[2]) if len(coords) > 2 else 0.0
        return float(coords[0]), float(coords[1]), z

    if isinstance(point, (list, tuple)):
        if len(point) < 2:
            raise ValueError("Точка должна содержать минимум x, y")
        z = float(point[2]) if len(point) > 2 else 0.0
        return float(point[0]), float(point[1]), z

    raise TypeError(f"Неподдерживаемый тип точки: {type(point)}")


def _normalize_points(points) -> List[Tuple[float, float, float]]:
    """
    Универсальная нормализация точек полилинии.

    Всегда возвращает:
        [(x, y, bulge), ...]

    Поддерживает:
    - VARIANT (плоский массив [x1, y1, x2, y2, ...])
    - список VARIANT
    - список (x, y)
    - список (x, y, bulge)
    - смешанные типы

    Это ГЛАВНАЯ точка входа для всех полилиний.
    """

    result = []

    # --- VARIANT (плоский массив) ---
    if isinstance(points, VARIANT):
        data = list(points.value)
        if len(data) % 2 != 0:
            raise ValueError("VARIANT массив должен содержать чётное число координат")

        for i in range(0, len(data), 2):
            result.append((float(data[i]), float(data[i + 1]), 0.0))

        return result

    # --- список ---
    if isinstance(points, (list, tuple)):
        for p in points:

            # VARIANT внутри списка
            if isinstance(p, VARIANT):
                x, y, _ = _normalize_point_3d(p)
                result.append((x, y, 0.0))
                continue

            # tuple/list
            if isinstance(p, (list, tuple)):
                if len(p) < 2:
                    raise ValueError("Точка должна содержать минимум x, y")

                x = float(p[0])
                y = float(p[1])
                bulge = float(p[2]) if len(p) > 2 else 0.0

                result.append((x, y, bulge))
                continue

            raise TypeError(f"Неподдерживаемый тип точки: {type(p)}")

        return result

    raise TypeError("Неподдерживаемый формат points")


def at_diameter(diameter: float, thickness: float, flag: str = "outer") -> float:
    """
    Вычисляет средний диаметр с учётом толщины.

    Args:
        diameter: Диаметр (внешний, внутренний или средний).
        thickness: Толщина материала.
        flag: Тип диаметра ("inner", "middle", "outer").

    Returns:
        float: Средний диаметр.

    Raises:
        ValueError: Если входные данные некорректны.
    """
    try:
        if not isinstance(diameter, (int, float)) or not isinstance(thickness, (int, float)):
            raise ValueError(loc.get("invalid_number", "Неверный формат числа."))
        if thickness < 0:
            raise ValueError(loc.get("thickness_positive_error", "Толщина должна быть положительной."))
        if diameter < 0:
            raise ValueError(loc.get("diameter_positive_error", "Диаметр не может быть отрицательным."))
        if flag == "middle":
            return float(diameter)
        elif flag == "outer":
            if diameter < thickness:
                raise ValueError(loc.get("diameter_positive_error", "Внешний диаметр не может быть меньше толщины."))
            return float(diameter - thickness)
        elif flag == "inner":
            return float(diameter + thickness)
        raise ValueError(loc.get("dia_error", "Неверный тип диаметра."))
    except ValueError as err:
        logger.error(f"at_diameter failed: {str(err)}")
        show_popup(str(err), popup_type="error")
        raise


def at_steigung(height: float, diameter_base: float, diameter_top: float = 0) -> Optional[float]:
    """
    Вычисляет наклон конуса.

    Args:
        height: Высота конуса.
        diameter_base: Диаметр основания.
        diameter_top: Диаметр вершины (по умолчанию 0).

    Returns:
        Optional[float]: Наклон конуса или None при ошибке.
    """
    try:
        if not all(isinstance(x, (int, float)) for x in [height, diameter_base, diameter_top]):
            show_popup(loc.get("invalid_number", "Неверный формат числа."), popup_type="error")
            logger.error("at_steigung failed: Invalid number format")
            return None
        if diameter_base <= 0:
            show_popup(loc.get("diameter_base_positive", "Диаметр основания должен быть положительным."), popup_type="error")
            logger.error("at_steigung failed: Base diameter must be positive")
            return None
        if diameter_top < 0:
            show_popup(loc.get("diameter_top_non_negative", "Диаметр вершины не может быть отрицательным."), popup_type="error")
            logger.error("at_steigung failed: Top diameter cannot be negative")
            return None
        if height <= 0:
            show_popup(loc.get("height_positive", "Высота должна быть положительной."), popup_type="error")
            logger.error("at_steigung failed: Height must be positive")
            return None
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top
        steigung = (diameter_base - diameter_top) / height
        if math.isinf(steigung) or math.isnan(steigung):
            show_popup(loc.get("invalid_result", "Недопустимый результат вычислений."), popup_type="error")
            logger.error("at_steigung failed: Invalid calculation result")
            return None
        return steigung
    except Exception as err:
        show_popup(loc.get("math_error", f"Ошибка математических вычислений: {str(err)}"), popup_type="error")
        logger.error(f"at_steigung failed: {str(err)}")
        return None


def at_cone_height(diameter_base: float, diameter_top: float = 0, steigung: Optional[float] = None,
                   angle: Optional[float] = None) -> Optional[float]:
    """
    Вычисляет высоту конуса по заданным параметрам.

    Args:
        diameter_base: Диаметр основания.
        diameter_top: Диаметр вершины (по умолчанию 0).
        steigung: Наклон конуса (опционально).
        angle: Угол конуса в градусах (опционально).

    Returns:
        Optional[float]: Высота конуса или None при ошибке.
    """
    try:
        if not all(isinstance(x, (int, float)) for x in [diameter_base, diameter_top]):
            show_popup(loc.get("invalid_number", "Неверный формат числа."), popup_type="error")
            logger.error("at_cone_height failed: Invalid number format")
            return None
        if diameter_base <= 0:
            show_popup(loc.get("diameter_base_positive", "Диаметр основания должен быть положительным."), popup_type="error")
            logger.error("at_cone_height failed: Base diameter must be positive")
            return None
        if diameter_top < 0:
            show_popup(loc.get("diameter_top_non_negative", "Диаметр вершины не может быть отрицательным."), popup_type="error")
            logger.error("at_cone_height failed: Top diameter cannot be negative")
            return None
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top
        if steigung is None and angle is None:
            show_popup(loc.get("missing_data", "Отсутствуют данные для вычислений."), popup_type="error")
            logger.error("at_cone_height failed: Missing data for calculations")
            return None
        if steigung is not None and angle is not None:
            show_popup(loc.get("both_parameters_error", "Нельзя указывать одновременно наклон и угол."), popup_type="error")
            logger.error("at_cone_height failed: Cannot specify both slope and angle")
            return None
        if steigung is not None:
            if not isinstance(steigung, (int, float)):
                show_popup(loc.get("invalid_gradient", "Неверный формат наклона."), popup_type="error")
                logger.error("at_cone_height failed: Invalid slope format")
                return None
            if steigung <= 0:
                show_popup(loc.get("gradient_positive", "Наклон должен быть положительным."), popup_type="error")
                logger.error("at_cone_height failed: Slope must be positive")
                return None
            return (diameter_base - diameter_top) / steigung
        if not isinstance(angle, (int, float)):
            show_popup(loc.get("invalid_angle", "Неверный формат угла."), popup_type="error")
            logger.error("at_cone_height failed: Invalid angle format")
            return None
        if angle <= 0 or angle >= 180:
            show_popup(loc.get("angle_range_error", "Угол должен быть в диапазоне 0–180°."), popup_type="error")
            logger.error("at_cone_height failed: Angle must be in range 0–180°")
            return None
        height = (diameter_base - diameter_top) / (2 * math.tan(math.radians(angle) / 2))
        if math.isinf(height) or math.isnan(height):
            show_popup(loc.get("invalid_result", "Недопустимый результат вычислений."), popup_type="error")
            logger.error("at_cone_height failed: Invalid calculation result")
            return None
        return height
    except Exception as err:
        show_popup(loc.get("math_error", f"Ошибка математических вычислений: {str(err)}"), popup_type="error")
        logger.error(f"at_cone_height failed: {str(err)}")
        return None


def at_cone_sheet(
    model: Any,
    input_point: PointLike,
    diameter_base: float,
    diameter_top: float = 0,
    height: float = 0,
    layer_name: str = "0"
) -> Optional[tuple]:
    """
    Создаёт развертку конуса в модельном пространстве.
    Изменена только нормализация входных данных.
    Returns:
        (points_list, input_point, center, theta)
    """
    try:
        # --- проверки ---
        if not all(isinstance(x, (int, float)) for x in [diameter_base, diameter_top, height]):
            show_popup(loc.get("invalid_number"), popup_type="error")
            return None

        if diameter_base <= 0:
            show_popup(loc.get("diameter_base_positive"), popup_type="error")
            return None

        if diameter_top < 0:
            show_popup(loc.get("diameter_top_non_negative"), popup_type="error")
            return None

        if height <= 0:
            show_popup(loc.get("height_positive"), popup_type="error")
            return None

        # --- нормализация точки (КЛЮЧЕВОЕ ИЗМЕНЕНИЕ) ---
        x0, y0 = _normalize_point_2d(input_point)

        # --- упорядочивание диаметров ---
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top

        # --- геометрия (НЕ ТРОГАЕМ) ---
        k = 0.5 * math.sqrt(1 + height ** 2 * 4 / ((diameter_base - diameter_top) ** 2))
        R1 = diameter_base * k
        R2 = diameter_top * k

        theta = math.pi * diameter_base / R1

        if any(map(lambda v: math.isinf(v) or math.isnan(v), [R1, R2, theta])):
            show_popup(loc.get("invalid_result"), popup_type="error")
            return None

        if R1 <= 0 or R2 < 0:
            show_popup(loc.get("invalid_geometry"), popup_type="error")
            return None

        half_theta = theta / 2
        sin_half = math.sin(half_theta)
        cos_half = math.cos(half_theta)

        drs1 = R1 * sin_half
        drs2 = R2 * sin_half
        drc1 = R1 * cos_half
        drc2 = R2 * cos_half

        # --- центр (переписан, но формула та же) ---
        center = [
            x0,
            y0 - (R1 - (R1 - R2) / 2.0),
            0.0
        ]

        # --- точки (БЕЗ изменений) ---
        p1 = [center[0] + drs2, center[1] + drc2, 0.0]
        p2 = [center[0] + drs1, center[1] + drc1, 0.0]
        p3 = [center[0] - drs1, center[1] + drc1, 0.0]
        p4 = [center[0] - drs2, center[1] + drc2, 0.0]

        # --- bulge ---
        bulge = math.tan(0.25 * theta)

        if math.isinf(bulge) or math.isnan(bulge):
            show_popup(loc.get("invalid_bulge"), popup_type="error")
            return None

        # --- ВАЖНО: убрали VARIANT ---
        points_list = [p1, p2, p3, p4]

        # теперь напрямую (через normalize внутри)
        polyline = add_polyline(model, points_list, layer_name, closed=True)

        if polyline is None:
            return None

        # --- bulge (как было) ---
        polyline.SetBulge(1, bulge)
        polyline.SetBulge(3, -bulge)

        return points_list, input_point, center, theta

    except Exception as err:
        print(f"at_cone_sheet error: {err}")
        show_popup(loc.get("cone_sheet_error", f"Ошибка: {err}"), popup_type="error")
        return None


# -----------------------------
# Основные методы
# -----------------------------
def _add_circle(
    model: Any,
    center: PointLike,
    radius: float,
    layer_name: str = "0"
) -> Optional[Any]:
    """
    Создаёт окружность в модельном пространстве.

    Центр может быть:
    - VARIANT
    - list/tuple (x, y) или (x, y, z)

    Args:
        model: Объект ModelSpace.
        center: Центр окружности.
        radius: Радиус.
        layer_name: Имя слоя.

    Returns:
        Объект окружности или None при ошибке.
    """
    try:
        # --- нормализация ---
        x, y, z = _normalize_point_3d(center)

        # --- COM ---
        center_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

        circle = model.AddCircle(center_variant, float(radius))
        circle.Layer = layer_name

        return circle

    except Exception as err:
        print(f"_add_circle error: {err}")
        show_popup(loc.get("circle_error", f"Ошибка при создании окружности: {err}"), popup_type="error")
        return None


def _add_line(
    model: Any,
    point1: PointLike,
    point2: PointLike,
    layer_name: str = "0"
) -> Optional[Any]:
    """
    Создаёт линию в модельном пространстве.

    Входные точки могут быть:
    - VARIANT
    - list/tuple (x, y) или (x, y, z)

    Все точки нормализуются в (x, y, z), затем конвертируются в COM VARIANT.

    Args:
        model: Объект ModelSpace.
        point1: Начальная точка.
        point2: Конечная точка.
        layer_name: Имя слоя.

    Returns:
        Объект линии или None при ошибке.
    """
    try:
        # --- нормализация ---
        x1, y1, z1 = _normalize_point_3d(point1)
        x2, y2, z2 = _normalize_point_3d(point2)

        # --- COM ---
        p1 = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x1, y1, z1])
        p2 = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x2, y2, z2])

        line = model.AddLine(p1, p2)
        line.Layer = layer_name

        return line

    except Exception as err:
        print(f"_add_line error: {err}")
        show_popup(loc.get("line_error", f"Ошибка при создании линии: {err}"), popup_type="error")
        return None


def _add_polyline(
    model: Any,
    points,
    layer_name: str = "0",
    closed: bool = True,
    bulges: Optional[list] = None
) -> Optional[Any]:
    """
    СТАБИЛЬНЫЙ вариант LWPOLYLINE для AutoCAD COM.

    ВАЖНО:
        - AddLightWeightPolyline принимает FLAT ARRAY
        - bulge задаётся отдельно через SetBulge
    """

    try:
        norm_pts = _normalize_points(points)

        if len(norm_pts) < 2:
            raise ValueError("Polyline requires at least 2 points")

        n = len(norm_pts)

        # 1. FLAT координаты (ОБЯЗАТЕЛЬНО)
        flat = []
        for x, y, *_ in norm_pts:
            flat.extend([float(x), float(y)])

        variant_points = VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            flat
        )

        # 2. создаём LWPOLYLINE
        pl = model.AddLightWeightPolyline(variant_points)

        pl.Layer = layer_name
        pl.Closed = closed

        # 3. bulge (если есть)
        if bulges:
            for i, b in enumerate(bulges):
                if i < n and abs(b) > 1e-12:
                    pl.SetBulge(i, float(b))

        # 4. закрытие: последняя дуга → первая
        # (AutoCAD сам замыкает, но bulge нужно явно задать)
        if closed and bulges and len(bulges) >= n:
            pl.SetBulge(n - 1, float(bulges[n - 1]))

        return pl

    except Exception as err:
        print(f"_add_polyline ERROR: {err}")

        # ❗ ВАЖНО: не вызываем wx здесь
        # иначе ты скрываешь реальную ошибку COM
        return None


def _add_spline(
    model: Any,
    points,
    layer_name: str = "0",
    closed: bool = False
) -> Optional[Any]:
    """
    Создаёт сплайн в AutoCAD через заданные точки.

    Вход:
        points — любые:
            - VARIANT (плоский массив x,y,z,...)
            - список VARIANT
            - список (x, y) или (x, y, z)
            - смешанные типы

    Все точки приводятся к:
        [(x, y, z), ...]

    Args:
        model: ModelSpace
        points: точки сплайна
        layer_name: слой
        closed: замкнуть сплайн

    Returns:
        Объект сплайна или None
    """
    try:
        norm: List[Tuple[float, float, float]] = []

        # --- VARIANT (плоский массив) ---
        if isinstance(points, VARIANT):
            data = list(points.value)

            if len(data) % 3 != 0:
                raise ValueError("VARIANT массив должен быть кратен 3 (x,y,z)")

            for i in range(0, len(data), 3):
                norm.append((
                    float(data[i]),
                    float(data[i + 1]),
                    float(data[i + 2])
                ))

        # --- список ---
        elif isinstance(points, (list, tuple)):
            for p in points:
                x, y, z = _normalize_point_3d(p)
                norm.append((x, y, z))

        else:
            raise TypeError("Неподдерживаемый формат points")

        # --- проверка ---
        if len(norm) < 2:
            raise ValueError("Для сплайна требуется минимум 2 точки")

        # --- замыкание ---
        if closed:
            p0 = norm[0]
            plast = norm[-1]

            tol = 1e-6
            if not (
                abs(p0[0] - plast[0]) < tol and
                abs(p0[1] - plast[1]) < tol and
                abs(p0[2] - plast[2]) < tol
            ):
                norm.append(p0)

        # --- flat массив ---
        flat = []
        for x, y, z in norm:
            flat.extend([x, y, z])

        # --- COM ---
        points_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat)

        # касательные (нулевые = AutoCAD сам рассчитает)
        zero_vec = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0.0, 0.0, 0.0])

        spline = model.AddSpline(points_variant, zero_vec, zero_vec)
        spline.Layer = layer_name

        # --- попытка закрытия ---
        if closed:
            try:
                spline.Closed = True
            except RuntimeError:
                # иногда AutoCAD не даёт установить — это нормально
                pass

        return spline

    except Exception as err:
        print(f"_add_spline error: {err}")
        show_popup(
            loc.get("spline_error", f"Ошибка при создании сплайна: {err}"),
            popup_type="error"
        )
        return None


def _add_rectangle(
    model: Any,
    point: PointLike,
    width: float,
    height: float,
    layer_name: str = "0",
    point_direction: str = "left_bottom",
    radius: float = 0.0
) -> Optional[Any]:
    """
    Создаёт прямоугольник (обычный / со скруглением / с фасками).

    Логика radius:
        = 0   → обычный
        > 0   → скругление (bulge)
        < 0   → фаска 45° (длина = abs(radius))

    Args:
        model: ModelSpace
        point: базовая точка
        width: ширина
        height: высота
        layer_name: слой
        point_direction: положение базовой точки
        radius: радиус или фаска

    Returns:
        Polyline или None
    """
    try:
        # --- базовые точки (через существующую функцию) ---
        rect_variant = add_rectangle_points(point, width, height, point_direction)

        # нормализуем → [(x, y, 0)...]
        norm = _normalize_points(rect_variant)

        # извлекаем 4 угла
        if len(norm) != 4:
            raise ValueError("Ожидалось 4 точки прямоугольника")

        p1, p2, p3, p4 = [(x, y) for x, y, _ in norm]

        # ----------------------------------------
        # 1. ОБЫЧНЫЙ ПРЯМОУГОЛЬНИК
        # ----------------------------------------
        if radius == 0:
            return add_polyline(
                model,
                [p1, p2, p3, p4],
                layer_name=layer_name,
                closed=True
            )

        # ----------------------------------------
        # 2. СКРУГЛЕНИЕ (radius > 0)
        # ----------------------------------------
        if radius > 0:
            r = float(radius)

            if r * 2 >= min(width, height):
                raise ValueError(f"Радиус {r} слишком велик")

            # bulge для 90°
            bulge = math.tan(math.radians(90 / 4))

            pts = [
                (p1[0] + r, p1[1]),
                (p2[0] - r, p2[1]),
                (p2[0], p2[1] + r),
                (p3[0], p3[1] - r),
                (p3[0] - r, p3[1]),
                (p4[0] + r, p4[1]),
                (p4[0], p4[1] - r),
                (p1[0], p1[1] + r),
            ]

            bulges = [0.0, bulge, 0.0, bulge, 0.0, bulge, 0.0, bulge]

            return add_polyline(
                model,
                pts,
                layer_name=layer_name,
                closed=True,
                bulges=bulges
            )

        # ----------------------------------------
        # 3. ФАСКА (radius < 0)
        # ----------------------------------------
        d = abs(radius)

        if d * 2 >= min(width, height):
            raise ValueError(f"Фаска {d} слишком велика")

        # формируем 8 точек (по 2 на угол)
        pts = [
            (p1[0] + d, p1[1]),     # нижний левый → вправо
            (p2[0] - d, p2[1]),     # нижний правый → влево
            (p2[0], p2[1] + d),     # вверх
            (p3[0], p3[1] - d),
            (p3[0] - d, p3[1]),
            (p4[0] + d, p4[1]),
            (p4[0], p4[1] - d),
            (p1[0], p1[1] + d),
        ]

        # фаска — это просто прямые сегменты → bulge = 0
        bulges = [0.0] * 8

        return add_polyline(
            model,
            pts,
            layer_name=layer_name,
            closed=True,
            bulges=bulges
        )

    except Exception as err:
        print(f"_add_rectangle error: {err}")
        show_popup(
            loc.get("rectangle_error", f"Ошибка при создании прямоугольника: {err}"),
            popup_type="error"
        )
        return None


def _add_text(
        model: Any,
        point: PointLike,
        text: str = "",
        layer_name: str = DEFAULT_TEXT_LAYER,
        text_height: float = 30,
        text_angle: float = 0,
        text_alignment: int = 4
) -> Optional[Any]:
    """
    Создаёт текст в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point: Координаты базовой точки текста (список, кортеж или VARIANT).
        text: Содержимое текста.
        layer_name: Имя слоя для текста.
        text_height: Высота текста.
        text_angle: Угол поворота текста (в радианах).
        text_alignment: Код выравнивания текста (0 - по умолчанию, 4 - центр и т.д.).

    Returns:
        Optional[Any]: Объект текста или None при ошибке.

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
    except Exception as err:
        logger.error(f"add_text failed: {str(err)}")
        show_popup(loc.get("text_error", f"Ошибка при создании текста: {str(err)}"), popup_type="error")
        return None


def rotate(obj, base, angle_deg):
    """
    Поворот объекта на заданный угол
    Args:
        obj: объект
        base: точка поворота (вариант)
        angle_deg: угол поворота в градусах
    """
    obj.Rotate(base, math.radians(angle_deg))


def _add_slotted_hole(innen_length: float, height: float):
    """
    Геометрия продолговатого отверстия (slot)

    Возвращает:
        points, bulges
    """

    if innen_length <= 0 or height <= 0:
        raise ValueError("Invalid slotted hole parameters")

    r = height / 2.0
    half = innen_length / 2.0

    # точки (строго по часовой стрелке)
    points = [
        (-half, -r),  # 0
        (-half,  r),  # 1 ← левая дуга
        ( half,  r),  # 2
        ( half, -r),  # 3 ← правая дуга
    ]

    # bulge на сегменты:
    # 0→1 = дуга
    # 1→2 = линия
    # 2→3 = дуга
    # 3→0 = линия
    bulges = [
        -1.0,  # 0→1 (левая полуокружность)
        0.0,  # 1→2
        -1.0,  # 2→3 (правая полуокружность)
        0.0   # 3→0
    ]

    return points, bulges


class AccompanyText:
    """
    Сопроводительный текст с толщиной и маркой материала
    """

    def __init__(self, data: dict):
        self.data = data

    def draw(self, ms, text_insert_point, text_alignment=0):
        """
        Отображение текста
        """
        thickness = self.data["thickness"]
        material = self.data["material"]
        text = f'{thickness}{loc.get("mm", "mm")} {material}'

        add_text(
            model=ms,
            point=ensure_point_variant(text_insert_point),
            text=text,
            layer_name=DEFAULT_TEXT_LAYER,
            text_height=TEXT_HEIGHT_BIG,
            text_angle=0,
            text_alignment=text_alignment,
        )


class MainText:
    """
    Добавление текста Order+Detail  на развертку, с возможностью гравировки
    """
    def __init__(self, data: dict):
        self.data = data

    def draw(self, ms, text_insert_point, text_alignment=0, laser=True) -> None:
        """
        Отображение текстов на развертке
        Args:
            ms: пространство модели
            text_insert_point: точка вставки текста (в виде списка или варианта)
            text_alignment: выравнивание текста (см. add_text)
            laser: лазерная гравировка на развертке - да/нет (True/False)
        """
        work_number = self.data["work_number"]
        detail = self.data["detail"]
        if detail == "":
            detail = None

        # Добавление текста
        if work_number:  # Добавляем текст только если work_number не пустой
            try:
                full_text = f'{work_number}-{detail}' if detail else f'{work_number}'

                if laser:
                    # точка для гравировки
                    point = polar_point(text_insert_point, MAIN_TEXT_OFFSET, 90, as_variant=True) # точка  основного текста
                    laser_text = f'{work_number}'
                    add_text(
                        ms,
                        text_insert_point,
                        text=laser_text,
                        layer_name=DEFAULT_LASER_LAYER,
                        text_height=TEXT_HEIGHT_LASER,
                        text_alignment=text_alignment
                        )
                else:
                    point = text_insert_point

                add_text(
                    ms,
                    point,
                    text=full_text,
                    layer_name=DEFAULT_TEXT_LAYER,
                    text_height=TEXT_HEIGHT_SMALL,
                    text_alignment=text_alignment
                    )
            except KeyError as err:
                show_popup(loc.get("text_error", f"Отсутствует ключ: {err}"), popup_type="error")
                raise
            except Exception as err:
                show_popup(loc.get("text_error", f"Ошибка создания текста: {err}"), popup_type="error")
                raise


class _ConstructionContext:
    def __init__(self):
        self.batch_mode = False
        self.suppress_regen = False
        self.objects_created = 0

CTX = _ConstructionContext()


@contextmanager
def construction_batch(do_regen: bool = False):
    """
    Контекст пакетного построения.

    Args:
        do_regen: выполнить regen после завершения
    """
    prev_batch = CTX.batch_mode
    prev_regen = CTX.suppress_regen

    CTX.batch_mode = True
    CTX.suppress_regen = True

    try:
        yield
    finally:
        CTX.batch_mode = prev_batch
        CTX.suppress_regen = prev_regen

        if do_regen:
            try:
                cad = ATCadInit()
                if cad.is_initialized():
                    regen(cad.document)
            except RuntimeError:
                pass


def maybe_regen(document):
    if not CTX.batch_mode and not CTX.suppress_regen:
        try:
            regen(document)
        except RuntimeError:
            pass


def _execute_construction(
    func,
    *args,
    **kwargs
) -> Any:
    """
    Единая точка выполнения всех CAD-конструкций.

    Контракт:
        - функция должна либо вернуть объект
        - либо выбросить исключение
        - возврат None считается ошибкой

    Args:
        func: функция построения (line, polyline, spline и т.д.)
        *args, **kwargs: параметры

    Returns:
        Результат выполнения func

    Raises:
        RuntimeError если результат None
    """
    try:
        result = func(*args, **kwargs)

        # --- ЖЁСТКАЯ ПРОВЕРКА ---
        if result is None:
            raise RuntimeError(
                f"{func.__name__} returned None (construction failed silently)"
            )

        return result

    except Exception as err:
        # единый UX-вывод
        print(f"[EXECUTION ERROR] {func.__name__}: {err}")

        show_popup(
            loc.get(
                "execution_error",
                f"Ошибка выполнения операции {func.__name__}: {err}"
            ),
            popup_type="error"
        )

        return None

# ------------------------------------------
# Публичные обертки без изменения сигнатуры
# ------------------------------------------
def add_line(model: Any, point1: PointLike,
             point2: PointLike,
             layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт линию в модельном пространстве.
    (Поддерживает batch-режим и оптимизацию regen)
    """
    return _execute_construction(_add_line, model, point1, point2, layer_name=layer_name)

def add_circle(model: Any, center: PointLike, radius: float,
               layer_name: str = "0") -> Optional[Any]:
    return _execute_construction(_add_circle, model, center, radius, layer_name=layer_name)

def add_polyline(
    model: Any,
    points: Union[
        VARIANT,
        List[VARIANT],
        Sequence[Sequence[float]]
    ],
    layer_name: str = "0",
    closed: bool = True,
    bulges: Optional[List[float]] = None
    ) -> Optional[Any]:
    return _execute_construction(_add_polyline, model, points, layer_name=layer_name, closed=closed, bulges=bulges)

def add_spline(
    model: Any,
    points: Union[VARIANT, Sequence[Sequence[float]]],
    layer_name: str = "0",
    closed: bool = True
) -> Optional[Any]:
    return _execute_construction(_add_spline, model, points, layer_name=layer_name, closed=closed)


def add_rectangle(
    model: Any,
    point: Union[List[float], tuple, VARIANT],
    width: float,
    height: float,
    layer_name: str = "0",
    point_direction: str = "left_bottom",
    radius: float = 0.0
) -> Optional[Any]:
    return _execute_construction(_add_rectangle, model, point, width, height, layer_name=layer_name, point_direction=point_direction, radius=radius)


def add_slotted_hole(
    model,
    input_point,
    innen_length: float,
    height: float,
    angle: float = 0.0,
    direction: str = "center"
):
    """
    Создание продолговатого отверстия в модели AutoCAD.

    Этот слой отвечает за:
        - позиционирование в модели
        - поворот
        - создание CAD-объекта
        - вызов execution pipeline

    Геометрия создаётся в локальной системе координат (_add_slotted_hole).

    Args:
        model: пространство модели AutoCAD
        input_point: точка вставки (центр слота)
        innen_length: внутренняя длина слота
        height: диаметр отверстия
        angle: угол поворота (в градусах)
        direction: смещение относительно центра ("center", "left", "right")

    Returns:
        CAD объект полилинии или None
    """

    # -----------------------------
    # 1. НОРМАЛИЗАЦИЯ ПОЛОЖЕНИЯ
    # -----------------------------
    x, y, *_ = input_point[0], input_point[1]

    half_length = innen_length / 2.0

    if direction == "left":
        x += half_length
    elif direction == "right":
        x -= half_length
    elif direction == "top":
        y -= half_length
    elif direction == "bottom":
        y += half_length
    elif direction != "center":
        raise ValueError(f"Unknown direction: {direction}")

    base_point = (x, y)

    # -----------------------------
    # 2. СОЗДАНИЕ ГЕОМЕТРИИ
    # -----------------------------
    points, bulges = _add_slotted_hole(innen_length, height)

    # --- трансформация ---
    transformed_points = [
        (px + base_point[0], py + base_point[1])
        for px, py in points
    ]

    # -----------------------------
    # 3. СОЗДАНИЕ ОБЪЕКТА
    # -----------------------------
    obj = _execute_construction(
        add_polyline,
        model,
        transformed_points,
        closed=True,
        bulges=bulges
    )

    if obj is None:
        return None

    # -----------------------------
    # 4. ПОВОРОТ
    # -----------------------------
    if angle:
        base = VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            [base_point[0], base_point[1], 0.0]
        )

        obj.Rotate(base, math.radians(angle))

    return obj


def add_text(
        model: Any,
        point: PointLike,
        text: str = "",
        layer_name: str = DEFAULT_TEXT_LAYER,
        text_height: float = 30,
        text_angle: float = 0,
        text_alignment: int = 4
) -> Optional[Any]:
    return _execute_construction(_add_text, model, point, text, layer_name=layer_name, text_height=text_height, text_angle=text_angle, text_alignment=text_alignment)


if __name__ == "__main__":
    """
    Тестирование создания текста, окружности, линии, полилинии и прямоугольника
    с использованием точки, полученной через at_get_point().

    Порядок:
      1) Проверяется инициализация AutoCAD (должен быть уже запущен).
      2) Запрашивается базовая точка у пользователя.
      3) Создаются объекты: текст, окружность, линия, полилиния (3 точки), прямоугольник.
      4) Ставится размер (add_dimension) и выполняется regen().
    """
    autocad = ATCadInit()

    if autocad.is_initialized():
        autocad_document = autocad.document
        autocad_model = autocad.model_space

        # Запрашиваем точку у пользователя
        test_input_point = at_get_point(autocad_document, prompt=loc.get("select_point", "Укажите центр окружности"))

        if test_input_point:
            try:
                # Вычисляем дополнительные точки с помощью полярных координат
                test_point2 = polar_point(test_input_point, distance=400, alpha=90, as_variant=True)
                test_point3 = polar_point(test_input_point, distance=400, alpha=60, as_variant=True)
                test_point4 = polar_point(test_input_point, distance=400, alpha=120, as_variant=True)

                # Создание текста
                # add_text(autocad_model, polar_point(test_input_point, distance=500, alpha=90, as_variant=True),
                #          loc.get("test_text", "Тестовый текст"))

                # Создание окружности
                add_circle(autocad_model, test_input_point, 200, layer_name="AM_0")

                # Создание линии
                # add_line(autocad_model, test_input_point, test_point2, layer_name="AM_7")

                # Создание полилинии
                # test_pts = [test_input_point, test_point3, test_point4]
                # add_polyline(autocad_model, test_pts, layer_name="LASER-TEXT")


                # Создание прямоугольника
                # rec_width, rec_height = 500, 300
                # add_rectangle(autocad_model, test_input_point, rec_width, rec_height, layer_name="SF-TEXT")
                # end_point = offset_point(test_input_point, rec_width, rec_height)

                # Продолговатое отверстие
                il = float(input("Длина между осями отверстий\n"))
                d = float(input("Диаметр отверстия\n"))
                a = float(input("Угол поворота в градусах\n"))
                direct = str(input("Направление (center/left/right/top/bottom)\n"))
                add_slotted_hole(autocad_model, test_input_point, il, d, a, direction=direct)

                # Размер
                # add_dimension(autocad_document, "H", test_input_point, end_point, offset=DEFAULT_DIM_OFFSET)

                # Обновляем экран
                regen(autocad_document)

            except Exception as e:
                logger.error(f"__main__ test scenario failed: {str(e)}")
                show_popup(loc.get("test_error", f"Ошибка тестового сценария: {str(e)}"), popup_type="error")
        else:
            print(loc.get("point_selection_cancelled", "Выбор точки отменён."))
    else:
        logger.error("AutoCAD initialization failed")
        show_popup(loc.get("autocad_not_running", "AutoCAD не запущен. Сначала откройте AutoCAD."), popup_type="error")
        sys.exit(1)
