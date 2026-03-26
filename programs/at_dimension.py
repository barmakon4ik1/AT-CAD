"""
Файл: programs/add_dimension.py
Описание:
    Добавление размеров в AutoCAD через COM API.
    Поддерживаются типы размеров:
        - H : Горизонтальный  (Rotated Dimension)
        - V : Вертикальный    (Rotated Dimension)
        - L : Линейный под углом верх/низ (Aligned Dimension)
        - R : Радиусный       (Radial Dimension)
        - D : Диаметральный   (Diametric Dimension)
        - A : Угловой         (Angular Dimension)

Зависимости:
    - config.at_cad_init.ATCadInit — инициализация AutoCAD COM API
    - programs.at_base.regen — регенерация чертежа
    - programs.at_input.at_get_point — запрос точки у пользователя
    - config.at_config — значения по умолчанию (масштаб, отступ, стиль, слой)
    - locales.at_localization_class.loc — локализация

Примечания по COM:
    - AddDimRotated(xline1Point, xline2Point, dimLinePoint, rotationRadians)
    - AddDimAligned(xline1Point, xline2Point, dimLinePoint)
    - AddDimRadial(center, chordPoint, leaderLength)
    - AddDimDiametric(chordPoint1, chordPoint2, leaderLength)
    - AddDimAngular(angleVertex, firstEndPoint, secondEndPoint, textPoint)
"""

# ============================== programs/add_dimension.py ==============================

import math
import pythoncom
from typing import Optional, Union
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from errors.at_errors import DataError
from programs.at_base import regen
from programs.at_geometry import ensure_point_variant
from programs.at_input import at_get_point
from config.at_config import (
    DEFAULT_DIM_SCALE,
    DEFAULT_DIM_OFFSET,
    DEFAULT_DIM_STYLE,
    DEFAULT_DIM_LAYER,
)
from locales.at_localization_class import loc

# --------------------------------------------------------------------------------------
# Константы подсказок
# --------------------------------------------------------------------------------------

PROMPTS = {
    "H_start": "Укажите первую точку горизонтального размера",
    "H_end": "Укажите вторую точку горизонтального размера",
    "V_start": "Укажите первую точку вертикального размера",
    "V_end": "Укажите вторую точку вертикального размера",
    "L_start": "Укажите первую точку линейного размера",
    "L_end": "Укажите вторую точку линейного размера",
    "R_center": "Укажите центр окружности или дуги",
    "R_start": "Укажите центр окружности или дуги",
    "R_point": "Укажите точку на окружности или дуге",
    "R_end": "Укажите точку на окружности или дуге",
    "D_start": "Укажите первую точку на окружности",
    "D_end": "Укажите противоположную точку на окружности",
    "A_vertex": "Укажите вершину угла",
    "A_side1": "Укажите точку на первой стороне угла",
    "A_side2": "Укажите точку на второй стороне угла",
    "A_arc": "Укажите точку на дуге размерной линии",
}


# --------------------------------------------------------------------------------------
# Вспомогательные функции
# --------------------------------------------------------------------------------------

def _xyz_from_variant(p: Union[VARIANT, list, tuple]) -> list[float]:
    """
    Преобразует точку AutoCAD в список [x, y, z].
    Если приходит (x, y), дополняем z=0.0.
    """
    if isinstance(p, VARIANT):
        coords = list(p.value)
    else:
        coords = list(p)
    if len(coords) == 2:
        coords.append(0.0)
    return coords[:3]


def _dim_mid_offset(dim_type: str, point1: VARIANT, point2: VARIANT, offset: float) -> VARIANT:
    """
    Вычисляет точку для размерной линии, смещённую на offset. Для V смещение влево от минимальной x,
    если point1 нижняя, или вправо от максимальной x, если point1 верхняя.

    Args:
        dim_type: Тип размера ("H" - горизонтальный, "V" - вертикальный, "L" - линейный).
        point1: Первая точка (VARIANT, [x, y, 0]).
        point2: Вторая точка (VARIANT, [x, y, 0]).
        offset: Расстояние смещения.

    Returns:
        VARIANT: Смещённая точка в формате [x, y, 0].
    """
    # Преобразуем VARIANT в списки [x, y, z]
    p1 = _xyz_from_variant(point1)
    p2 = _xyz_from_variant(point2)

    # Средняя y-координата
    mid_y = (p1[1] + p2[1]) / 2.0

    # Вектор p1->p2 (XY)
    vx, vy = p2[0] - p1[0], p2[1] - p1[1]

    # Инициализация результирующей точки
    result = [0.0, mid_y, 0.0]

    # Определяем нормаль и смещение
    nx, ny = 0.0, 0.0
    if dim_type == "H":
        # Для горизонтального размера: ближайшая точка с большей y
        base_point = p2 if p2[1] > p1[1] else p1
        # Нормаль перпендикулярна линии p1->p2
        nx, ny = -vy, vx
        nlen = math.hypot(nx, ny)
        if nlen > 0:
            nx /= nlen
            ny /= nlen
            # Смещение от base_point
            result[0] = base_point[0] + nx * offset
            result[1] = base_point[1] + ny * offset
    elif dim_type == "V":
        # Для вертикального размера: направление зависит от y point1
        if p1[1] < p2[1]:  # point1 нижняя
            # Выбираем точку с минимальной x
            base_point = p1 if p1[0] <= p2[0] else p2
            result[0] = base_point[0] - offset  # Влево
        else:  # point1 верхняя или y равны
            # Выбираем точку с максимальной x
            base_point = p1 if p1[0] >= p2[0] else p2
            result[0] = base_point[0] + offset  # Вправо
        result[1] = mid_y  # Средняя y
    elif dim_type == "L":
        # Для линейного размера: смещение от середины
        result[0] = (p1[0] + p2[0]) / 2.0
        nx, ny = -vy, vx
        nlen = math.hypot(nx, ny)
        if nlen > 0:
            nx /= nlen
            ny /= nlen
            result[0] += nx * offset
            result[1] += ny * offset

    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, result)

def _safe_leader_len(leader_len: Optional[float]) -> float:
    """
    Возвращает безопасную длину выносной линии (> 0).
    """
    return max(1.0, float(leader_len) if leader_len is not None else 1.0)


# --------------------------------------------------------------------------------------
# Валидация размеров
# --------------------------------------------------------------------------------------

def _distance_xy(p1: VARIANT, p2: VARIANT) -> float:
    """
    Вычисляет расстояние между двумя точками в плоскости XY.
    Используется для проверки нулевой длины размера.
    """
    a = _xyz_from_variant(p1)
    b = _xyz_from_variant(p2)
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _validate_linear_dim(p1: VARIANT, p2: VARIANT, offset: float) -> bool:
    """
    Проверяет корректность линейного/горизонтального/вертикального размера.

    Условия:
        - точки не совпадают
        - расстояние больше допуска
        - offset не нулевой
    """
    if p1 is None or p2 is None:
        return False

    if _distance_xy(p1, p2) < 1e-6:
        return False

    if abs(offset) < 1e-6:
        return False

    return True


def _ensure_layer_exists(adoc, layer_name: str):
    """
    Гарантирует существование слоя.
    Если слой отсутствует — создаётся.
    """
    try:
        adoc.Layers.Item(layer_name)
    except (DataError, IndexError):
        adoc.Layers.Add(layer_name)


def _ensure_dimstyle_exists(adoc, style_name: str):
    """
    Проверяет существование размерного стиля.
    Если отсутствует — используется текущий активный.
    """
    try:
        adoc.DimStyles.Item(style_name)
        adoc.ActiveDimStyle = adoc.DimStyles.Item(style_name)
    except Exception:
        # если стиль отсутствует — не падаем
        pass


# --------------------------------------------------------------------------------------
# Основная функция
# --------------------------------------------------------------------------------------

def add_dimension(
    adoc,
    dim_type: str = None,
    start_point = None,
    end_point: VARIANT = None,
    leader_len: float = None,
    point3: VARIANT = None,
    point4: VARIANT = None,
    offset: float = DEFAULT_DIM_OFFSET
):
    """
    Добавляет размер в AutoCAD, запрашивая недостающие параметры у пользователя.

    :param adoc: COM-объект ActiveDocument AutoCAD
    :param dim_type: Тип размера (H/V/L/R/D/A)
    :param start_point: Первая точка (VARIANT). Для A — вершина угла.
    :param end_point: Вторая точка (VARIANT). Для A — точка на первой стороне.
    :param leader_len: Длина выносной (для R/D)
    :param point3: Для A — точка на второй стороне
    :param point4: Для A — точка на дуге размерной линии
    :param offset: Отступ размерной линии от контура
    :return: COM-объект созданного размера или None
    """

    # --- Гарантия ModelSpace ---
    adoc.ActiveSpace = 1
    model = adoc.ModelSpace

    # --- Обеспечение слоя и стиля ---
    _ensure_layer_exists(adoc, DEFAULT_DIM_LAYER)
    _ensure_dimstyle_exists(adoc, DEFAULT_DIM_STYLE)

    # --- Определение типа размера ---
    if dim_type:
        dim_type = dim_type.upper()
    else:
        dim_type = str(adoc.Utility.GetString(
            True,
            "Введите тип размера (H/V/L/R/D/A): "
        )).strip().upper()

    if not dim_type:
        return None

    # берём только первый символ
    dim_type = dim_type[0]

    valid_types = {"H", "V", "L", "R", "D", "A"}

    if dim_type not in valid_types:
        print(f"Неверный тип размера: {dim_type}")
        return None

    # --- Преобразование точек ---
    if start_point is None:
        start_point = at_get_point(adoc, as_variant=True, prompt=PROMPTS[f"{dim_type}_start"])

    if end_point is None:
        end_point = at_get_point(adoc, as_variant=True, prompt=PROMPTS[f"{dim_type}_end"])

    start_point = ensure_point_variant(start_point)
    end_point = ensure_point_variant(end_point)

    try:
        # ------------------------------------------------------------------
        # Горизонтальный / Вертикальный / Линейный
        # ------------------------------------------------------------------
        if dim_type in ("H", "V", "L"):

            if not _validate_linear_dim(start_point, end_point, offset):
                return None

            dim_pt = _dim_mid_offset(dim_type, start_point, end_point, offset)

            if dim_type == "L":
                dim_ent = model.AddDimAligned(start_point, end_point, dim_pt)
            else:
                rot = 0 if dim_type == "H" else math.pi / 2
                dim_ent = model.AddDimRotated(start_point, end_point, dim_pt, rot)

        # ------------------------------------------------------------------
        # Радиус
        # ------------------------------------------------------------------
        elif dim_type == "R":

            center = start_point
            chord = end_point

            dim_ent = model.AddDimRadial(
                center,
                chord,
                _safe_leader_len(leader_len)
            )

        # ------------------------------------------------------------------
        # Диаметр
        # ------------------------------------------------------------------
        elif dim_type == "D":

            # # Сдвигаем start_point диаметрально относительно end_point
            # x0, y0, z0 = _xyz_from_variant(start_point)
            # x1, y1, z1 = _xyz_from_variant(end_point)

            start_diam = start_point
            end_diam = end_point

            dim_ent = model.AddDimDiametric(
                start_diam,
                end_diam,
                _safe_leader_len(leader_len)
            )

        # ------------------------------------------------------------------
        # Угловой
        # ------------------------------------------------------------------
        elif dim_type == "A":

            if point3:
                point3 = ensure_point_variant(point3)

            if point4:
                point4 = ensure_point_variant(point4)

            p1 = start_point
            p2 = end_point
            p3 = point3
            p4 = point4

            dim_ent = model.AddDimAngular(
                p1, p2, p3, p4
            )

        else:
            return None

        # --- Установка свойств ---
        dim_ent.Layer = DEFAULT_DIM_LAYER
        dim_ent.ScaleFactor = DEFAULT_DIM_SCALE

        return dim_ent

    except pythoncom.com_error as e:
        # Отладочная информация при падении COM
        print("COM error while creating dimension:")
        print("Type:", dim_type)
        print("Start:", start_point)
        print("End:", end_point)
        print("Offset:", offset)
        print(e)
        return None


# --------------------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    cad = ATCadInit()
    if cad.is_initialized():
        add_dimension(cad.document)
