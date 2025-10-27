"""
Файл: at_highlight_utils.py
Путь: programs/at_highlight_utils.py

Описание:
Модуль для визуальной подсветки объектов AutoCAD через COM API.
Содержит функции для временного выделения (Highlight),
изменения цвета, мигания, подсветки контуров и их внутреннего содержимого.
"""

import time
import logging
import win32com.client
import pythoncom
from typing import Tuple, Optional, List

from config.at_cad_init import ATCadInit


# --- Базовые функции ----------------------------------------------------------

def highlight_entity(entity, highlight: bool = True):
    """
    Временная подсветка объекта AutoCAD (аналог выделения).
    """
    try:
        entity.Highlight(highlight)
    except Exception as e:
        logging.warning(f"Ошибка подсветки объекта: {e}")


def blink_entity(entity, blink_count: int = 3, delay: float = 0.3):
    """
    Эффект мигания выделенного объекта.
    """
    try:
        for _ in range(blink_count):
            entity.Highlight(True)
            time.sleep(delay)
            entity.Highlight(False)
            time.sleep(delay)
    except Exception as e:
        logging.warning(f"Ошибка мигания объекта: {e}")


# --- Подсветка через изменение цвета -----------------------------------------

def temp_highlight_color(entity, rgb: Tuple[int, int, int] = (255, 0, 0), duration: float = 1.0):
    """
    Временная подсветка объекта изменением цвета.
    Автоматически возвращает исходный цвет по истечении времени.
    """
    try:
        old_color = entity.TrueColor
        color = win32com.client.Dispatch("AutoCAD.AcCmColor.20")
        color.SetRGB(*rgb)
        entity.TrueColor = color
        entity.Update()
        time.sleep(duration)
        entity.TrueColor = old_color
        entity.Update()
    except Exception as e:
        logging.warning(f"Ошибка подсветки цвета: {e}")


# --- Подсветка группы объектов -----------------------------------------------

def highlight_entities(entities: List, highlight: bool = True):
    """
    Подсветка группы объектов.
    """
    for ent in entities:
        highlight_entity(ent, highlight)


def blink_entities(entities: List, blink_count: int = 2, delay: float = 0.3):
    """
    Мигание группы объектов.
    """
    for _ in range(blink_count):
        for ent in entities:
            highlight_entity(ent, True)
        time.sleep(delay)
        for ent in entities:
            highlight_entity(ent, False)
        time.sleep(delay)


# --- Подсветка объектов внутри контура --------------------------------------

def highlight_inside_polygon(adoc, polygon_entity, include_boundary=True, highlight=True):
    """
    Подсвечивает все объекты внутри замкнутого полигона.
    Требуется установленная библиотека shapely (pip install shapely).

    Args:
        adoc: активный документ AutoCAD.
        polygon_entity: COM-объект полилинии (AcDbPolyline или LWPolyline).
        include_boundary: включать ли границу (саму полилинию).
        highlight: True — включить подсветку, False — выключить.
    """
    try:
        from shapely.geometry import Point, Polygon
    except ImportError:
        logging.error("Библиотека 'shapely' не установлена. Подсветка внутри контура недоступна.")
        return

    # --- Получаем координаты полилинии ---
    try:
        coords = []
        if hasattr(polygon_entity, "Coordinates"):
            arr = polygon_entity.Coordinates
            coords = [(arr[i], arr[i+1]) for i in range(0, len(arr), 2)]
        elif hasattr(polygon_entity, "GetCoordinates"):
            arr = polygon_entity.GetCoordinates()
            coords = [(arr[i], arr[i+1]) for i in range(0, len(arr), 2)]
    except Exception as e:
        logging.error(f"Ошибка получения координат полилинии: {e}")
        return

    if not coords:
        logging.warning("Не удалось получить координаты полигона для подсветки.")
        return

    poly = Polygon(coords)
    if include_boundary:
        highlight_entity(polygon_entity, highlight)

    # --- Подсвечиваем все объекты, чьи центры находятся внутри ---
    for obj in adoc.ModelSpace:
        try:
            if hasattr(obj, "BoundingBox"):
                minp, maxp = obj.BoundingBox
                cx = (minp[0] + maxp[0]) / 2
                cy = (minp[1] + maxp[1]) / 2
                if poly.contains(Point(cx, cy)):
                    obj.Highlight(highlight)
        except Exception:
            continue


# --- Очистка подсветки -------------------------------------------------------

def clear_highlights(adoc):
    """
    Снимает подсветку со всех объектов модели.
    """
    try:
        for obj in adoc.ModelSpace:
            try:
                obj.Highlight(False)
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"Ошибка очистки подсветки: {e}")

def highlight_safe(entity, duration=0.3):
    """Подсветка объекта с защитой от ошибок COM."""
    try:
        if entity is None:
            return
        if hasattr(entity, "Highlight"):
            entity.Highlight(True)
            time.sleep(duration)
            entity.Highlight(False)
    except Exception as e:
        # Логируем ошибку, но не крашимся
        print(f"WARNING: Ошибка подсветки цвета: {e}")


# --- Пример теста ------------------------------------------------------------

if __name__ == "__main__":
    acad  = ATCadInit()
    adoc = acad.document

    adoc.Utility.Prompt("Выберите объект для подсветки:\n")
    ent, pt = adoc.Utility.GetEntity()
    highlight_entity(ent, True)
    time.sleep(1)
    highlight_entity(ent, False)
    temp_highlight_color(ent, (0, 255, 0), 1)
    blink_entity(ent, 3)
    adoc.Utility.Prompt("Тест завершён.\n")
