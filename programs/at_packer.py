# Файл: programs/at_packer.py
"""
Описание:
Модуль упаковки замкнутых полилиний (слой 0) внутрь базового контура (слой SF-TEXT)
с минимизацией занимаемой площади и обеспечением отступов между объектами.

Алгоритм:
1. Пользователь выбирает базовый контур (SF-TEXT).
2. Пользователь выбирает несколько замкнутых полилиний (слой 0).
3. Модуль вычисляет габариты каждой фигуры и располагает их внутри базового контура
   с зазором 10 мм между собой и от границ.

Использует:
 - ATCadInit  (инициализация AutoCAD)
 - safe_utility_call из at_com_utils
"""

import math
from typing import List, Tuple, Optional
from win32com.client import CDispatch

from config.at_cad_init import ATCadInit
from programs.at_com_utils import safe_utility_call
from windows.at_gui_utils import show_popup
from locales.at_localization_class import loc


# --- Константы упаковки ---
MARGIN = 10.0  # мм, отступ от границы и между объектами


# --- Вспомогательные функции ---
def get_polyline_bounding_box(poly: CDispatch) -> Optional[Tuple[float, float, float, float]]:
    """Возвращает габариты полилинии (xmin, ymin, xmax, ymax)."""
    try:
        ext = poly.GetBoundingBox()
        pmin, pmax = ext[0], ext[1]
        xmin, ymin = pmin[0], pmin[1]
        xmax, ymax = pmax[0], pmax[1]
        return xmin, ymin, xmax, ymax
    except Exception:
        return None


def get_polyline_area(poly: CDispatch) -> float:
    """Возвращает площадь замкнутой полилинии."""
    try:
        return abs(poly.Area)
    except Exception:
        return 0.0


def move_entity(ent: CDispatch, dx: float, dy: float) -> None:
    """Перемещает объект на (dx, dy)."""
    try:
        base_point = [0, 0, 0]
        disp = [dx, dy, 0]
        ent.Move(base_point, disp)
    except Exception as e:
        print("Move error:", e)


# --- Основной алгоритм упаковки ---
def pack_entities_inside_base():
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(loc.get("cad_not_ready"), popup_type="error")
        return

    adoc = cad.document
    util = adoc.Utility

    # 1️⃣ Выбор базовой полилинии
    base_sel = safe_utility_call(lambda: util.GetEntity("\nВыберите базовую полилинию (слой SF-TEXT): "))
    if not base_sel:
        show_popup("Выбор базовой полилинии отменён.", popup_type="info")
        return

    base_poly, _ = base_sel
    if base_poly.Layer != "SF-TEXT":
        show_popup("Выбранный объект не на слое SF-TEXT.", popup_type="warning")
        return

    # 2️⃣ Выбор полилиний для упаковки
    pack_objects: List[CDispatch] = []
    while True:
        ent_sel = safe_utility_call(lambda: util.GetEntity("\nВыберите полилинию для упаковки (слой 0, ENTER для завершения): "))
        if not ent_sel:
            break
        entity, _ = ent_sel
        if entity.Layer == "0":
            pack_objects.append(entity)
        else:
            show_popup("Объект не на слое 0, пропущен.", popup_type="warning")

    if not pack_objects:
        show_popup("Нет выбранных объектов для упаковки.", popup_type="warning")
        return

    # --- Получаем габариты базового контура ---
    bbox_base = get_polyline_bounding_box(base_poly)
    if not bbox_base:
        show_popup("Не удалось определить габариты базового контура.", popup_type="error")
        return
    bxmin, bymin, bxmax, bymax = bbox_base
    width = bxmax - bxmin - 2 * MARGIN
    height = bymax - bymin - 2 * MARGIN

    # --- Упрощённый алгоритм размещения (строчное размещение слева направо, сверху вниз) ---
    x_cursor = bxmin + MARGIN
    y_cursor = bymax - MARGIN
    row_height = 0

    for ent in sorted(pack_objects, key=get_polyline_area, reverse=True):
        bbox = get_polyline_bounding_box(ent)
        if not bbox:
            continue
        xmin, ymin, xmax, ymax = bbox
        w = xmax - xmin
        h = ymax - ymin

        if x_cursor + w > bxmax - MARGIN:
            # Переход на новую строку
            x_cursor = bxmin + MARGIN
            y_cursor -= (row_height + MARGIN)
            row_height = 0

        # Проверка по высоте
        if y_cursor - h < bymin + MARGIN:
            show_popup("Недостаточно места для всех фигур внутри базового контура.", popup_type="warning")
            break

        # Перемещаем фигуру
        move_entity(ent, x_cursor - xmin, y_cursor - ymax)

        # Обновляем курсоры
        x_cursor += w + MARGIN
        row_height = max(row_height, h)

    show_popup("Упаковка завершена.", popup_type="success")


# --- Тестовый запуск ---
if __name__ == "__main__":
    pack_entities_inside_base()
