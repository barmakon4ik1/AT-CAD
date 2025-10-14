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
    - programs.at_input.at_point_input — запрос точки у пользователя
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
from programs.at_base import regen
from programs.at_input import at_point_input
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
    "R_point": "Укажите точку на окружности или дуге",
    "D_p1": "Укажите первую точку на окружности",
    "D_p2": "Укажите противоположную точку на окружности",
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
# Основная функция
# --------------------------------------------------------------------------------------

def add_dimension(
    adoc,
    dim_type: str = None,
    start_point: VARIANT = None,
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
    model = adoc.ModelSpace

    # --- Определение типа размера ---
    if dim_type is None:
        dim_type = str(adoc.Utility.GetString(True, "Введите тип размера (H/V/L/R/D/A): ")).strip().upper()
        if dim_type not in ("H", "V", "L", "R", "D", "A"):
            return None

    # --- Горизонтальный, вертикальный, линейный ---
    if dim_type in ("H", "V", "L"):
        if start_point is None:
            start_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS[f"{dim_type}_start"])
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS[f"{dim_type}_end"])
        dim_pt = _dim_mid_offset(dim_type, start_point, end_point, offset)
        if dim_type == "L":
            dim_ent = model.AddDimAligned(start_point, end_point, dim_pt)
        else:
            rot = 0 if dim_type == "H" else math.pi / 2
            dim_ent = model.AddDimRotated(start_point, end_point, dim_pt, rot)

    # --- Радиус ---
    elif dim_type == "R":
        if start_point is None:
            start_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["R_center"])
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["R_point"])
        dim_ent = model.AddDimRadial(start_point, end_point, _safe_leader_len(leader_len))

    # --- Диаметр ---
    elif dim_type == "D":
        if start_point is None:
            start_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["D_p1"])
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["D_p2"])
        dim_ent = model.AddDimDiametric(start_point, end_point, _safe_leader_len(leader_len))

    # --- Угловой ---
    elif dim_type == "A":
        if start_point is None:
            start_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["A_vertex"])
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True, prompt=PROMPTS["A_side1"])
        if point3 is None:
            point3 = at_point_input(adoc, as_variant=True, prompt=PROMPTS["A_side2"])
        if point4 is None:
            point4 = at_point_input(adoc, as_variant=True, prompt=PROMPTS["A_arc"])
        dim_ent = model.AddDimAngular(start_point, end_point, point3, point4)

    else:
        return None

    # --- Установка свойств ---
    dim_ent.StyleName = DEFAULT_DIM_STYLE
    dim_ent.ScaleFactor = DEFAULT_DIM_SCALE
    dim_ent.Layer = DEFAULT_DIM_LAYER

    regen(adoc)
    return dim_ent


# --------------------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    cad = ATCadInit()
    if cad.is_initialized():
        add_dimension(cad.document)
