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
import math
import sys
from typing import Optional, Any, List, Union, Tuple
import os
import logging
from win32com.client import VARIANT
import pythoncom

from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_TEXT_LAYER, DEFAULT_DIM_OFFSET
from programms.at_base import regen
from programms.at_dimension import add_dimension
from programms.at_geometry import add_rectangle_points, offset_point, polar_point, ensure_point_variant
from programms.at_input import at_point_input
from windows.at_gui_utils import show_popup
from locales.at_translations import loc

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


# -----------------------------
# Вспомогательные методы
# -----------------------------
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
    except ValueError as e:
        logger.error(f"at_diameter failed: {str(e)}")
        show_popup(str(e), popup_type="error")
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
    except Exception as e:
        show_popup(loc.get("math_error", f"Ошибка математических вычислений: {str(e)}"), popup_type="error")
        logger.error(f"at_steigung failed: {str(e)}")
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
    except Exception as e:
        show_popup(loc.get("math_error", f"Ошибка математических вычислений: {str(e)}"), popup_type="error")
        logger.error(f"at_cone_height failed: {str(e)}")
        return None


def at_cone_sheet(model: Any, input_point: Union[List[float], VARIANT], diameter_base: float,
                  diameter_top: float = 0, height: float = 0, layer_name: str = "0") -> Optional[tuple]:
    """
    Создаёт развертку конуса в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        input_point: Координаты базовой точки (список, кортеж или VARIANT).
        diameter_base: Диаметр основания конуса.
        diameter_top: Диаметр вершины конуса (по умолчанию 0).
        height: Высота конуса.
        layer_name: Имя слоя для полилинии.

    Returns:
        Optional[tuple]: Кортеж (объект полилинии, точка вставки) или None при ошибке.
    """
    try:
        if not all(isinstance(x, (int, float)) for x in [diameter_base, diameter_top, height]):
            show_popup(loc.get("invalid_number", "Неверный формат числа."), popup_type="error")
            logger.error("at_cone_sheet failed: Invalid number format")
            return None
        if not isinstance(input_point, (list, tuple, VARIANT)) or (isinstance(input_point, (list, tuple)) and len(input_point) < 2):
            show_popup(loc.get("invalid_point", "Некорректная точка вставки."), popup_type="error")
            logger.error("at_cone_sheet failed: Invalid insertion point")
            return None
        if diameter_base <= 0:
            show_popup(loc.get("diameter_base_positive", "Диаметр основания должен быть положительным."), popup_type="error")
            logger.error("at_cone_sheet failed: Base diameter must be positive")
            return None
        if diameter_top < 0:
            show_popup(loc.get("diameter_top_non_negative", "Диаметр вершины не может быть отрицательным."), popup_type="error")
            logger.error("at_cone_sheet failed: Top diameter cannot be negative")
            return None
        if height <= 0:
            show_popup(loc.get("height_positive", "Высота должна быть положительной."), popup_type="error")
            logger.error("at_cone_sheet failed: Height must be positive")
            return None
        if diameter_top > diameter_base:
            diameter_top, diameter_base = diameter_base, diameter_top
        k = 0.5 * math.sqrt(1 + height ** 2 * 4 / ((diameter_base - diameter_top) ** 2))
        R1 = diameter_base * k
        R2 = diameter_top * k
        theta = math.pi * diameter_base / R1
        if math.isinf(theta) or math.isnan(theta):
            show_popup(loc.get("invalid_result", "Недопустимый результат вычислений."), popup_type="error")
            logger.error("at_cone_sheet failed: Invalid calculation result")
            return None
        if R1 <= 0 or R2 < 0 or math.isinf(R1) or math.isnan(R1) or math.isinf(R2) or math.isnan(R2):
            show_popup(loc.get("invalid_geometry", "Недопустимая геометрия конуса."), popup_type="error")
            logger.error("at_cone_sheet failed: Invalid cone geometry")
            return None
        half_theta = theta / 2
        sin_half_theta = math.sin(half_theta)
        cos_half_theta = math.cos(half_theta)
        drs1 = R1 * sin_half_theta
        drs2 = R2 * sin_half_theta
        drc1 = R1 * cos_half_theta
        drc2 = R2 * cos_half_theta
        center = [input_point[0], input_point[1] - (R1 - (R1 - R2) * 0.5), 0.0] if isinstance(input_point, (list, tuple)) else [input_point.value[0], input_point.value[1] - (R1 - (R1 - R2) * 0.5), 0.0]
        p1 = [center[0] + drs2, center[1] + drc2, 0.0]
        p2 = [center[0] + drs1, center[1] + drc1, 0.0]
        p3 = [center[0] - drs1, center[1] + drc1, 0.0]
        p4 = [center[0] - drs2, center[1] + drc2, 0.0]
        bulge = math.tan(0.25 * theta)
        if math.isinf(bulge) or math.isnan(bulge):
            show_popup(loc.get("invalid_bulge", "Недопустимое значение выпуклости."), popup_type="error")
            logger.error("at_cone_sheet failed: Invalid bulge value")
            return None
        points_list = [p1, p2, p3, p4]
        points_variant = [ensure_point_variant(p) for p in points_list]
        polyline = add_polyline(model, points_variant, layer_name, closed=True)
        if polyline is None:
            show_popup(loc.get("polyline_error", "Ошибка при создании полилинии."), popup_type="error")
            logger.error("at_cone_sheet failed: Failed to create polyline")
            return None
        polyline.SetBulge(1, bulge)
        polyline.SetBulge(3, -bulge)
        input_point_variant = ensure_point_variant(input_point)
        return polyline, input_point_variant
    except Exception as e:
        show_popup(loc.get("cone_sheet_error", f"Ошибка построения развертки конуса: {str(e)}"), popup_type="error")
        logger.error(f"at_cone_sheet failed: {str(e)}")
        return None


# -----------------------------
# Основные методы
# -----------------------------
def add_circle(model: Any, center: Union[List[float], VARIANT], radius: float,
               layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт окружность в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        center: Координаты центра окружности (список, кортеж или VARIANT).
        radius: Радиус окружности.
        layer_name: Имя слоя для окружности.

    Returns:
        Optional[Any]: Объект окружности или None при ошибке.
    """
    try:
        circle = model.AddCircle(ensure_point_variant(center), radius)
        circle.Layer = layer_name
        return circle
    except Exception as e:
        logger.error(f"add_circle failed: {str(e)}")
        show_popup(loc.get("circle_error", f"Ошибка при создании окружности: {str(e)}"), popup_type="error")
        return None


def add_line(model: Any, point1: Union[List[float], VARIANT],
             point2: Union[List[float], VARIANT],
             layer_name: str = "0") -> Optional[Any]:
    """
    Создаёт линию в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point1: Начальная точка линии (список, кортеж или VARIANT).
        point2: Конечная точка линии (список, кортеж или VARIANT).
        layer_name: Имя слоя для линии.

    Returns:
        Optional[Any]: Объект линии или None при ошибке.
    """
    try:
        line = model.AddLine(ensure_point_variant(point1), ensure_point_variant(point2))
        line.Layer = layer_name
        return line
    except Exception as e:
        logger.error(f"add_line failed: {str(e)}")
        show_popup(loc.get("line_error", f"Ошибка при создании линии: {str(e)}"), popup_type="error")
        return None


def add_polyline(model: Any, points: Union[VARIANT, List[VARIANT]],
                 layer_name: str = "0", closed: bool = True) -> Optional[Any]:
    """
    Создаёт легковесную полилинию в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        points: COM VARIANT с координатами вершин (x1, y1, x2, y2, ...) или список VARIANT-объектов с точками [x, y, z].
        layer_name: Имя слоя для полилинии.
        closed: Закрывать полилинию или нет (по умолчанию True).

    Returns:
        Optional[Any]: Объект полилинии или None при ошибке.
    """
    try:
        if isinstance(points, list) and all(isinstance(p, VARIANT) for p in points):
            flat_points = []
            for point in points:
                coords = point.value
                if len(coords) < 2 or any(c is None or not isinstance(c, (int, float)) for c in coords[:2]):
                    raise ValueError("Неправильные координаты точки")
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
        logger.error(f"add_polyline failed: {str(e)}")
        show_popup(loc.get("polyline_error", f"Ошибка при создании полилинии: {str(e)}"), popup_type="error")
        return None

def add_polyline_with_bilge(
        model: Any,
        points: List[Union[List[float], VARIANT, tuple]],
        mode: str = "bulge",  # "polyline", "bulge", "spline"
        layer_name: str = "0",
        closed: bool = True
) -> Optional[Any]:
    """
    Создаёт полилинию в AutoCAD:
      - polyline: обычная полилиния
      - bulge: полилиния с вычислением кривизны (bulge) для каждого сегмента
      - spline: создаёт SplineEntity через все точки

    Args:
        model: ModelSpace документа
        points: Список точек [x, y] или VARIANT
        mode: "polyline", "bulge", "spline"
        layer_name: имя слоя
        closed: закрывать полилинию или нет

    Returns:
        COM объект полилинии или None
    """
    try:
        if len(points) < 2:
            show_popup(loc.get("to_small_points", "Мало точек"), popup_type="error")
            return None

        # Преобразуем все точки в формат [x, y]
        pts: List[List[float]] = []
        for p in points:
            if isinstance(p, VARIANT):
                pts.append(list(p.value[:2]))
            elif isinstance(p, (list, tuple)):
                pts.append([float(p[0]), float(p[1])])
            else:
                raise TypeError("Точки должны быть списком, кортежем или VARIANT")

        # ------------------------------
        # Режим Spline
        # ------------------------------
        if mode == "spline":
            # Spline через все точки
            spline = model.AddSpline(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                             [coord for pt in pts for coord in pt]))
            spline.Closed = closed
            spline.Layer = layer_name
            return spline

        # ------------------------------
        # Режим polyline или bulge
        # ------------------------------
        # Формируем плоский массив координат
        flat_points = [coord for pt in pts for coord in pt]
        polyline = model.AddLightWeightPolyline(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_points))
        polyline.Closed = closed
        polyline.Layer = layer_name

        if mode == "bulge":
            # вычисляем bulge для каждого сегмента по трём точкам
            n = len(pts)
            for i in range(n):
                p0 = pts[i - 1 if i > 0 else (0 if closed else 0)]
                p1 = pts[i]
                p2 = pts[(i + 1) % n] if (i + 1 < n) else (pts[0] if closed else pts[-1])
                # вычисляем центр окружности
                d = 2.0 * (p0[0] * (p1[1] - p2[1]) + p1[0] * (p2[1] - p0[1]) + p2[0] * (p0[1] - p1[1]))
                if abs(d) < 1e-12:
                    bulge = 0.0
                else:
                    a2 = p0[0] ** 2 + p0[1] ** 2
                    b2 = p1[0] ** 2 + p1[1] ** 2
                    c2 = p2[0] ** 2 + p2[1] ** 2
                    ux = (a2 * (p1[1] - p2[1]) + b2 * (p2[1] - p0[1]) + c2 * (p0[1] - p1[1])) / d
                    uy = (a2 * (p2[0] - p1[0]) + b2 * (p0[0] - p2[0]) + c2 * (p1[0] - p0[0])) / d
                    ang1 = math.atan2(p1[1] - uy, p1[0] - ux)
                    ang2 = math.atan2(p2[1] - uy, p2[0] - ux)
                    sweep = (ang2 - ang1 + math.pi) % (2 * math.pi) - math.pi
                    bulge = math.tan(sweep / 4.0)
                try:
                    polyline.SetBulge(i, float(bulge))
                except Exception as ex:
                    logger.warning(f"SetBulge failed at index {i}: {ex}")
        return polyline

    except Exception as e:
        logger.error(f"add_polyline_with_bilge failed: {e}")
        show_popup(loc.get("polyline_error", f"Ошибка при создании полилинии: {str(e)}"), popup_type="error")
        return None


def add_spline(
        model: Any,
        points: List[Union[List[float], tuple, VARIANT]],
        layer_name: str = "0",
        closed: bool = False
) -> Any:
    """
    Создаёт сплайн в AutoCAD через заданные точки.

    Args:
        model: ModelSpace документа AutoCAD.
        points: Список точек [x, y] или VARIANT.
        layer_name: Имя слоя для сплайна.
        closed: Замкнуть сплайн или нет.

    Returns:
        COM объект сплайна или None при ошибке.
    """
    try:
        if len(points) < 2:
            show_popup(loc.get("to_small_points", "Мало точек"), popup_type="error")
            return None

        # Преобразуем точки в плоский список координат [x1, y1, x2, y2, ...]
        flat_points = []
        for p in points:
            if isinstance(p, VARIANT):
                flat_points.extend(list(p.value[:2]))
            elif isinstance(p, (list, tuple)):
                flat_points.extend([float(p[0]), float(p[1])])
            else:
                raise TypeError("Точки должны быть списком, кортежем или VARIANT")

        # Создаём сплайн
        spline = model.AddSpline(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_points))
        spline.Closed = closed
        spline.Layer = layer_name

        return spline

    except Exception as e:
        logger.error(f"add_spline failed: {e}")
        show_popup(loc.get("polyline_error", f"Ошибка при создании сплайна: {str(e)}"), popup_type="error")
        return None

def add_rectangle(model: Any, point: Union[List[float], VARIANT],
                  width: float, height: float,
                  layer_name: str = "0",
                  point_direction: str = "left_bottom") -> Optional[Any]:
    """
    Создаёт прямоугольник в модельном пространстве.

    Args:
        model: Объект ModelSpace активного документа AutoCAD.
        point: Координаты базовой точки прямоугольника (список, кортеж или VARIANT).
        width: Ширина прямоугольника.
        height: Высота прямоугольника.
        layer_name: Имя слоя для прямоугольника.
        point_direction: Положение базовой точки ("left_bottom", "center", и др.).

    Returns:
        Optional[Any]: Объект полилинии-прямоугольника или None при ошибке.
    """
    try:
        points_variant = add_rectangle_points(point, width, height, point_direction)
        polyline = add_polyline(model, points_variant, layer_name=layer_name, closed=True)
        return polyline
    except Exception as e:
        logger.error(f"add_rectangle failed: {str(e)}")
        show_popup(loc.get("rectangle_error", f"Ошибка при создании прямоугольника: {str(e)}"), popup_type="error")
        return None


def add_text(
        model: Any,
        point: Union[List[float], VARIANT],
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
    except Exception as e:
        logger.error(f"add_text failed: {str(e)}")
        show_popup(loc.get("text_error", f"Ошибка при создании текста: {str(e)}"), popup_type="error")
        return None


if __name__ == "__main__":
    """
    Тестирование создания текста, окружности, линии, полилинии и прямоугольника
    с использованием точки, полученной через at_point_input().

    Порядок:
      1) Проверяется инициализация AutoCAD (должен быть уже запущен).
      2) Запрашивается базовая точка у пользователя.
      3) Создаются объекты: текст, окружность, линия, полилиния (3 точки), прямоугольник.
      4) Ставится размер (add_dimension) и выполняется regen().
    """
    cad = ATCadInit()

    if cad.is_initialized():
        adoc = cad.document
        model = cad.model_space

        # Запрашиваем точку у пользователя
        input_point = at_point_input(adoc, prompt=loc.get("select_point", "Укажите центр окружности"))

        if input_point:
            try:
                # Вычисляем дополнительные точки с помощью полярных координат
                point2 = polar_point(input_point, distance=400, alpha=90, as_variant=True)
                point3 = polar_point(input_point, distance=400, alpha=60, as_variant=True)
                point4 = polar_point(input_point, distance=400, alpha=120, as_variant=True)

                # Создание текста
                add_text(model, polar_point(input_point, distance=500, alpha=90, as_variant=True),
                         loc.get("test_text", "Тестовый текст"))

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
                add_dimension(adoc, "H", input_point, end_point, offset=DEFAULT_DIM_OFFSET)

                # Обновляем экран
                regen(adoc)

            except Exception as e:
                logger.error(f"__main__ test scenario failed: {str(e)}")
                show_popup(loc.get("test_error", f"Ошибка тестового сценария: {str(e)}"), popup_type="error")
        else:
            print(loc.get("point_selection_cancelled", "Выбор точки отменён."))
    else:
        logger.error("AutoCAD initialization failed")
        show_popup(loc.get("autocad_not_running", "AutoCAD не запущен. Сначала откройте AutoCAD."), popup_type="error")
        sys.exit(1)
