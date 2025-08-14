"""
Файл: add_dimension.py
Описание: Добавление размеров в AutoCAD через COM API.
Поддерживаются: линейные (H/V/L), радиусные (R), диаметральные (D) и угловые (A) размеры.
"""
import time

from config import at_config as cfg
from config.at_cad_init import ATCadInit
from programms.at_com_utils import safe_utility_call
from locales.at_localization_class import loc
from programms.at_input import at_point_input
from windows.at_gui_utils import show_popup
import pythoncom
from win32com.client import Dispatch


def add_dimension(
    adoc,
    dim_type: str = None,
    start_point: list = None,
    end_point: list = None,
    second_point_for_angle: list = None,
    dim_layer: str = None,
    dim_style: str = None,
    scale_factor: float = None,
    dim_offset: float = None
):
    """
    Добавляет размер в AutoCAD с безопасным запросом типа и точек у пользователя.
    Параметры:
        adoc: COM объект ActiveDocument AutoCAD
        model: ModelSpace документа
        dim_type: Тип размера ('H','V','L','R','D','A')
        start_point: первая точка
        end_point: вторая точка
        second_point_for_angle: для угловых размеров третья точка
        dim_layer: слой размера
        dim_style: стиль размера
        scale_factor: масштаб размера
        dim_offset: смещение линии размера
    Если параметры не заданы, используются значения по умолчанию и запрос у пользователя.
    """
    # --- Значения по умолчанию ---
    dim_layer = dim_layer or cfg.DEFAULT_DIM_LAYER
    dim_style = dim_style or cfg.DEFAULT_DIM_STYLE
    model = cad.model
    # Проверяем и преобразуем scale_factor
    try:
        scale_factor = float(scale_factor if scale_factor is not None else cfg.DEFAULT_DIM_SCALE)
    except (ValueError, TypeError) as e:
        show_popup(
            loc.get("invalid_value", "Неверное значение scale_factor: {}").format(scale_factor or cfg.DEFAULT_DIM_SCALE),
            popup_type="error"
        )
        return
    # Проверяем и преобразуем dim_offset
    try:
        dim_offset = float(dim_offset if dim_offset is not None else cfg.DEFAULT_DIM_OFFSET)
    except (ValueError, TypeError) as e:
        show_popup(
            loc.get("invalid_value", "Неверное значение dim_offset: {}").format(dim_offset or cfg.DEFAULT_DIM_OFFSET),
            popup_type="error"
        )
        return

    # --- Запрос типа размера, если не задан ---
    if dim_type is None:
        raw = adoc.Utility.GetString(True, "Введите тип размера (H/V/L/R/D/A): ")
        if raw is None or not str(raw).strip():
            show_popup(
                loc.get("input_error", "Ошибка ввода типа размера или пустой ввод"),
                popup_type="error"
            )
            return
        dim_type = str(raw).strip().upper()  # Приводим к строке и верхнему регистру
        if dim_type not in ("H", "V", "L", "R", "D", "A"):
            return

    # --- Запрос первой точки, если не задана ---
    if start_point is None:
        start_point = at_point_input(adoc, as_variant=True)

    # --- Запрос остальных точек в зависимости от типа ---
    if dim_type in ("H", "V", "L"):
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True)

    elif dim_type == "R":
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True)

    elif dim_type == "D":
        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True)

    elif dim_type == "A":
        if second_point_for_angle is None:
            second_point_for_angle = at_point_input(adoc, as_variant=True)

        if end_point is None:
            end_point = at_point_input(adoc, as_variant=True)

    # --- Создание размера ---
    dim_ent = None
    if dim_type in ("H", "V"):
        angle = 0 if dim_type == "H" else 90  # 0 для H/L, 90 для V
        dim_ent = model.AddDimRotated(start_point, end_point, angle, None)
    elif dim_type == "L":
        dim_ent = model.AddDimRotated(start_point, end_point, None, None)
    elif dim_type == "R":
        dim_ent = model.AddDimRadial(start_point, end_point)
    elif dim_type == "D":
        dim_ent = model.AddDimDiametric(start_point, end_point, 0)
    elif dim_type == "A":
        dim_ent = model.AddDimAngular(start_point, second_point_for_angle, end_point, None)

    # --- Применяем параметры ---
    dim_ent.ScaleFactor = scale_factor
    dim_ent.Layer = dim_layer
    dim_ent.StyleName = dim_style
    if hasattr(dim_ent, "DimLineOffset"):
        dim_ent.DimLineOffset = dim_offset

    adoc.Regen()  # Обновляем чертеж

    return dim_ent


# --- Точка входа ---
if __name__ == "__main__":

    cad = ATCadInit()
    add_dimension(cad.adoc)


"""
Рабочий вариант с sendcommand
# programms/at_dimension.py

Постановка размеров H/V/L/D/R/A в AutoCAD (Mechanical 2026) из Python.
Масштаб применяется только к созданному размеру (не глобально).

Типы размеров:
    H — горизонтальный (DIMROTATED 0)
    V — вертикальный   (DIMROTATED 90)
    L — линейный       (DIMLINEAR)
    D — диаметр        (DIMDIAMETER)
    R — радиус         (DIMRADIUS)
    A — угол           (DIMANGULAR)


from __future__ import annotations
import time
from typing import Optional

from config.at_cad_init import ATCadInit
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from programms.at_base import regen
from config.at_config import DEFAULT_DIM_STYLE, DEFAULT_DIM_SCALE, DEFAULT_DIM_LAYER, DEFAULT_DIM_OFFSET


# ---------- Вспомогательные функции ----------

def _fmt_xy(pt) -> str:
Формат 'x,y' с точкой как десятичным разделителем.
    return f"{float(pt[0]):.8f},{float(pt[1]):.8f}"


def _set_active_layer_and_style(adoc, layer_name: str, dimstyle_name: str) -> None:
Активируем слой и стиль размеров.
    try:
        adoc.ActiveLayer = adoc.Layers.Item(layer_name)
    except Exception:
        # слой гарантированно есть, так что ошибок быть не должно
        pass
    try:
        adoc.ActiveDimStyle = adoc.DimStyles.Item(dimstyle_name)
    except Exception:
        pass


def _ucs_world(adoc) -> None:
Привязка к WCS для предсказуемого смещения размерных линий.
    adoc.SendCommand("._UCS _W\n")
    time.sleep(0.05)


def _wait_new_entity(ms, count_before: int, timeout: float = 5.0) -> bool:
Ждем появления нового объекта в ModelSpace после SendCommand.
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if ms.Count > count_before:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return False


def _is_dimension(ent) -> bool:
Эвристика для определения объекта как размера.
    name = ""
    try:
        name = getattr(ent, "ObjectName", "") or getattr(ent, "EntityName", "")
    except Exception:
        name = ""
    if isinstance(name, str) and ("Dim" in name or "DIM" in name):
        return True
    # запасной признак — наличие типичных свойств размера
    for prop in ("DimScale", "ScaleFactor", "TextPosition"):
        try:
            getattr(ent, prop)
            return True
        except Exception:
            continue
    return False


def _find_last_dimension(ms, count_before: int) -> Optional[object]:
    Находим последний созданный размер после count_before.
    try:
        i = ms.Count - 1
        low = max(count_before, 0)
        steps = 0
        while i >= low and steps < 20:
            try:
                ent = ms.Item(i)
                if _is_dimension(ent):
                    return ent
            except Exception:
                pass
            i -= 1
            steps += 1
    except Exception:
        pass
    return None


def _apply_per_entity_scale(dim_ent, scale: float) -> bool:

    Применяем масштаб только к созданному размеру.
    Используем DimScale / ScaleFactor, если доступно.

    for prop in ("DimScale", "ScaleFactor"):
        try:
            setattr(dim_ent, prop, float(scale))
            try:
                dim_ent.Update()
            except Exception:
                pass
            return True
        except Exception:
            continue
    return False


# ---------- Основная функция ----------

def add_dimension(adoc, model, dim_type: str, start_point, end_point, offset: float = DEFAULT_DIM_OFFSET,
                  per_entity_scale: float = DEFAULT_DIM_SCALE) -> bool:

    Ставит размер в AutoCAD по типу:
        H — горизонтальный
        V — вертикальный
        L — линейный
        D — диаметр
        R — радиус
        A — угол
    Масштаб применяется только к созданному размеру.

    Args:
        dim_type: 'H'|'V'|'L'|'D'|'R'|'A'
        start_point: [x,y,z]
        end_point:   [x,y,z]
        offset:      смещение размерной линии
        per_entity_scale: масштаб для нового размера

    _ucs_world(adoc)
    _set_active_layer_and_style(adoc, DEFAULT_DIM_LAYER, DEFAULT_DIM_STYLE)

    x1, y1 = float(start_point[0]), float(start_point[1])
    x2, y2 = float(end_point[0]), float(end_point[1])

    dim_type = (dim_type or "").upper().strip()

    # Вычисление точки размещения размерной линии
    if dim_type == "H":
        pd = ((x1 + x2) / 2.0, y1 + float(offset))
        cmd = f"_.DIMROTATED 0 {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))} {_fmt_xy(pd)}\n"
    elif dim_type == "V":
        pd = (max(x1, x2) + float(offset), (y1 + y2) / 2.0)
        cmd = f"_.DIMROTATED 90 {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))} {_fmt_xy(pd)}\n"
    elif dim_type == "L":
        # Линейный размер параллельно линии с смещением offset
        import math
        dx, dy = x2 - x1, y2 - y1
        angle = math.degrees(math.atan2(dy, dx))
        length = math.hypot(dx, dy)
        # нормаль к линии (перпендикуляр)
        nx, ny = -dy / length, dx / length
        pd = ((x1 + x2) / 2 + nx * offset, (y1 + y2) / 2 + ny * offset)
        cmd = f"_.DIMROTATED {angle} {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))} {_fmt_xy(pd)}\n"
    elif dim_type == "D":
        cmd = f"_.DIMDIAMETER {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))}\n"
    elif dim_type == "R":
        cmd = f"_.DIMRADIUS {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))}\n"
    elif dim_type == "A":
        # угол между точками, pd = средняя точка между p1 и p2
        pd = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        cmd = f"_.DIMANGULAR {_fmt_xy((x1, y1))} {_fmt_xy((x2, y2))} {_fmt_xy(pd)}\n"
    else:
        adoc.Utility.Prompt("Прервано пользователем.\n")
        raise SystemExit(0)

    count_before = model.Count
    adoc.SendCommand(cmd)

    # Ждём появления новой сущности
    if not _wait_new_entity(model, count_before, timeout=5.0):
        regen(adoc)
        return False

    # Находим только что созданный размер
    dim_ent = _find_last_dimension(model, count_before)
    if dim_ent is None:
        regen(adoc)
        return False

    # Применяем масштаб ТОЛЬКО к этому размеру
    _apply_per_entity_scale(dim_ent, per_entity_scale)

    regen(adoc)
    return True


# ---------- Тестовый запуск ----------

if __name__ == "__main__":
    cad = ATCadInit()
    if not cad.is_initialized():
        raise SystemExit

    adoc = cad.adoc

    # ---------- Запрос типа размера ----------
    adoc.Utility.Prompt("Введите тип размера (H/V/L/D/R/A), другой символ для выхода:\n")
    dim_type = adoc.Utility.GetString(True)  # только AutoCAD prompt, без консоли
    dim_type = dim_type.upper().strip()
    if dim_type not in ("H", "V", "L", "D", "R", "A"):
        raise SystemExit

    adoc.Utility.Prompt("Выберите первую точку:\n")
    p1 = at_point_input(adoc, as_variant=False)
    if not p1:
        raise SystemExit

    adoc.Utility.Prompt("Выберите вторую точку:\n")
    p2 = at_point_input(adoc, as_variant=False)
    if not p2:
        raise SystemExit

    ok = add_dimension(dim_type, p1, p2, offset=DEFAULT_DIM_OFFSET, per_entity_scale=DEFAULT_DIM_SCALE)

"""