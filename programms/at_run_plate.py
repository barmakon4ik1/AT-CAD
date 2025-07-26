# programms/at_run_plate.py
"""
Модуль для построения листа для лазерной резки в AutoCAD с использованием pyautocad.
Создает внешнюю и внутреннюю замкнутые полилинии, проставляет размеры и добавляет текст.
"""

import logging
import math
import sys

import pythoncom
from pyautocad import APoint
from programms.at_calculation import at_plate_weight, at_density
from programms.at_construction import add_LWpolyline, at_addText, polar_point
from programms.at_dimension import at_dimension
from typing import Dict, Any, List
from locales.at_localization_class import loc
from config.at_config import *
from windows.at_gui_utils import show_popup
from programms.at_base import regen, init_autocad

# Настройка логирования
# Настройка логирования в консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Вывод в консоль
    ]
)


def run_plate(plate_data: Dict[str, Any]) -> bool:
    """
    Выполняет построение листа для лазерной резки в AutoCAD.

    Создает внешнюю замкнутую полилинию и внутреннюю с использованием метода Offset,
    проставляет размеры (для 4 уникальных точек: только 0-1, 1-2; для >4 уникальных точек:
    дополнительные горизонтальные 2-3, 2-5, 2-7, 2-9 и вертикальные 0-9, 0-7, 0-5, 0-3,
    строго горизонтальные/вертикальные, измеряющие проекции по X/Y) и добавляет текст.

    Args:
        plate_data: Словарь с параметрами листа:
            - insert_point: Точка вставки (APoint или список/кортеж [x, y]).
            - polyline_points: Список точек полилинии [(x0, y0), (x1, y1), ..., (x0, y0)].
            - material: Материал листа.
            - thickness: Толщина листа.
            - melt_no: Номер плавки.
            - allowance: Отступ для внутренней полилинии.

    Returns:
        bool: True, если выполнено успешно, False в случае ошибки.
    """
    try:
        # Инициализация AutoCAD
        cad_objects = init_autocad()
        if cad_objects is None:
            show_popup(loc.get("cad_init_error_short", "Ошибка инициализации AutoCAD"), popup_type="error")
            logging.error("Не удалось инициализировать AutoCAD")
            return False
        adoc, model, original_layer = cad_objects

        # Проверка входных данных
        if not plate_data:
            show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
            logging.error("Данные не предоставлены")
            return False

        # Извлечение данных из plate_data
        insert_point = plate_data.get("insert_point")
        polyline_points = plate_data.get("polyline_points", [])
        allowance = plate_data.get("allowance")
        if not polyline_points:
            show_popup(loc.get("no_input_data", "Не заданы координаты точек полилинии"), popup_type="error")
            logging.error("Не заданы точки полилинии")
            return False
        if not insert_point or not model:
            show_popup(loc.get("invalid_point", "Не указана точка вставки или модель"), popup_type="error")
            logging.error("Не указана точка вставки или модель")
            return False
        if allowance is None or not isinstance(allowance, (int, float)) or allowance < 0:
            show_popup(loc.get("invalid_allowance", "Неверное значение отступа"), popup_type="error")
            logging.error(f"Неверное значение allowance: {allowance}")
            return False

        # Преобразование точек в плоский список для add_LWpolyline
        flat_points = []
        for x, y in polyline_points:
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                show_popup(loc.get("invalid_point_format", "Неверный формат точки"), popup_type="error")
                logging.error(f"Неверный формат точки: ({x}, {y})")
                return False
            flat_points.extend([x, y])

        # Построение внешней замкнутой полилинии
        polyline = add_LWpolyline(model, flat_points, layer_name="SF-TEXT")
        if polyline is None:
            show_popup(loc.get("polyline_creation_error", "Ошибка создания полилинии"), popup_type="error")
            logging.error("Не удалось создать внешнюю полилинию")
            return False

        try:
            # Установка замкнутости внешней полилинии
            if not polyline.Closed:
                polyline.Closed = True
            # Вычисление площади внешней полилинии
            area = polyline.Area
            logging.info(f"Площадь внешней полилинии: {area}")
            # Проверка, что allowance не слишком большой
            min_dimension = min(
                max(x for x, y in polyline_points) - min(x for x, y in polyline_points),
                max(y for x, y in polyline_points) - min(y for x, y in polyline_points)
            )
            if allowance > min_dimension / 2:
                show_popup(loc.get("invalid_allowance", "Слишком большой отступ для данной полилинии"), popup_type="error")
                logging.error(f"Слишком большой allowance: {allowance}, минимальный размер: {min_dimension}")
                return False
        except Exception as e:
            show_popup(loc.get("area_calculation_error", "Ошибка расчета площади"), popup_type="error")
            logging.error(f"Ошибка при вычислении площади: {e}")
            return False

        # Формирование сопроводительного текста
        material = plate_data.get("material")
        density = at_density(material)
        thickness = plate_data.get("thickness")
        melt_no = plate_data.get("melt_no")
        weight = at_plate_weight(thickness, density, area)

        # Находим максимальную Y-координату для размещения текста
        max_y = max(y for x, y in polyline_points)

        # Координаты текста
        point_text = APoint(insert_point[0], max_y + 60)

        # Добавление текста
        text = f'{thickness} mm {material}, {weight} kg, Ch. {melt_no}'
        at_addText(model, point_text, text, layer_name="AM_5", text_height=60, text_angle=0, text_alignment=0)

        # Создание внутренней полилинии
        try:
            logging.info("Шаг 1: Начало выполнения Offset")
            logging.info(f"Шаг 2: Расстояние смещения: {allowance}")
            offset_polylines = None
            try:
                logging.info("Шаг 3: Вызов polyline.Offset(-allowance)")
                offset_polylines = polyline.Offset(-allowance)
                logging.info(
                    f"Шаг 4: Offset выполнен, количество объектов: {len(offset_polylines) if offset_polylines else 0}")
            except Exception as e:
                logging.warning(f"Шаг 3.1: Исключение в Offset: {e}")
                logging.info("Шаг 3.2: Проверка ModelSpace на новые полилинии")
                offset_polylines = []
                for obj in adoc.ModelSpace:
                    if obj.ObjectName == "AcDbPolyline" and obj.Handle != polyline.Handle:
                        offset_polylines.append(obj)
                        logging.info(f"Шаг 3.3: Найдена полилиния: Handle={obj.Handle}")
                        break

            if offset_polylines:
                logging.info(f"Шаг 5: Обработка {len(offset_polylines)} смещённых полилиний")
                for offset_poly in offset_polylines:
                    logging.info(f"Шаг 6: Настройка полилинии Handle={offset_poly.Handle}")
                    offset_poly.Closed = True
                    offset_poly.Layer = "SF-TEXT"  # Тот же слой
                    logging.info(f"Шаг 7: Полилиния настроена: Handle={offset_poly.Handle}, Площадь={offset_poly.Area}")
            else:
                show_popup(loc.get("offset_error", "Не удалось создать смещённую полилинию"), popup_type="error")
                logging.error("Шаг 5.1: Offset не создал полилиний")
                return False

        except Exception as e:
            show_popup(loc.get("offset_error", f"Ошибка при создании смещённой полилинии: {e}"), popup_type="error")
            logging.error(f"Шаг 8: Общая ошибка в Offset: {e}")
            return False

        # Регенерация чертежа
        regen(adoc)
        logging.info("Полилиния, внутренняя полилиния, размеры и текст успешно созданы")
        return True

    except Exception as e:
        show_popup(loc.get("general_error", f"Ошибка: {str(e)}"), popup_type="error")
        logging.error(f"Ошибка в run_plate (programms/at_run_plate.py): {e}")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    input_data = {
        'insert_point': APoint(0, 0, 0.00),
        'point_list': [[3000, 1500]],
        'material': '1.4301',
        'thickness': 0.0,
        'melt_no': '',
        'allowance': 10.0,
        'polyline_points': [
            (0, 0),
            (3000, 0),
            (3000, 1500),
            (0, 1500),
            (0, 0)]
    }
    run_plate(input_data)
