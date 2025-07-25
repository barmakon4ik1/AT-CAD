# programms/at_run_plate.py
"""
Модуль для построения листа для лазерной резки в AutoCAD с использованием pyautocad.
Создает внешнюю и внутреннюю замкнутые полилинии, проставляет размеры и добавляет текст.
"""

import logging
import pythoncom
from pyautocad import APoint
from programms.at_calculation import at_plate_weight, at_density
from programms.at_construction import add_LWpolyline, at_addText
from programms.at_dimension import at_dimension
from typing import Dict, Any, List
from locales.at_localization_class import loc
from config.at_config import *
from windows.at_gui_utils import show_popup
from programms.at_base import regen, init_autocad

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
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

        # # Построение внутренней полилинии с использованием Offset
        # try:
        #     # Создаем внутреннюю полилинию, смещенную внутрь на allowance
        #     offset_objects = polyline.Offset(-allowance)  # Отрицательное значение для смещения внутрь
        #     if not offset_objects or len(offset_objects) == 0:
        #         show_popup(loc.get("offset_error", "Ошибка создания внутренней полилинии"), popup_type="error")
        #         logging.error("Не удалось создать внутреннюю полилинию с помощью Offset")
        #         return False
        #     inner_polyline = offset_objects[0]  # Берем первый объект (должен быть полилинией)
        #     inner_polyline.Layer = "SF-TEXT"
        #     if not inner_polyline.Closed:
        #         inner_polyline.Closed = True
        #     # Проверка корректности внутренней полилинии
        #     inner_area = inner_polyline.Area
        #     if inner_area >= area:
        #         show_popup(loc.get("offset_error", "Внутренняя полилиния больше или равна внешней"), popup_type="error")
        #         logging.error(f"Некорректная внутренняя полилиния: площадь {inner_area} >= {area}")
        #         return False
        #     logging.info(f"Внутренняя полилиния успешно создана с площадью: {inner_area}")
        # except Exception as e:
        #     show_popup(loc.get("offset_error", f"Ошибка при создании внутренней полилинии: {str(e)}"), popup_type="error")
        #     logging.error(f"Ошибка при создании внутренней полилинии с Offset: {e}, polyline_points: {polyline_points}, allowance: {allowance}")
        #     return False

        # Простановка размеров
        # Обязательные размеры: 0-1 (горизонтальный, y-70) и 1-2 (вертикальный, x+70)
        if len(polyline_points) >= 2:
            # Размер 0-1: горизонтальный
            start = APoint(polyline_points[0][0], polyline_points[0][1])
            end = APoint(polyline_points[1][0], polyline_points[1][1])
            dim_x = (start.x + end.x) / 2
            dim_y = min(start.y, end.y) - 70
            dim_point = APoint(dim_x, dim_y)
            if not at_dimension("H", start, end, dim_point, adoc=adoc, layer="AM_5"):
                logging.error("Не удалось проставить размер между точками 0 и 1")
                show_popup(loc.get("dim_creation_error", "Ошибка при создании размера"), popup_type="error")

        if len(polyline_points) >= 3:
            # Размер 1-2: вертикальный
            start = APoint(polyline_points[1][0], polyline_points[1][1])
            end = APoint(polyline_points[2][0], polyline_points[2][1])
            dim_x = max(start.x, end.x) + 70
            dim_y = (start.y + end.y) / 2
            dim_point = APoint(dim_x, dim_y)
            if not at_dimension("V", start, end, dim_point, adoc=adoc, layer="AM_5"):
                logging.error("Не удалось проставить размер между точками 1 и 2")
                show_popup(loc.get("dim_creation_error", "Ошибка при создании размера"), popup_type="error")

        # Дополнительные размеры (только для полилиний с более чем 4 уникальными точками)
        if len(polyline_points) > 5:
            # Горизонтальные размеры: 2-3, 2-5, 2-7, 2-9 (шаг по Y +70)
            horizontal_pairs = [(2, 3), (2, 5), (2, 7), (2, 9)]
            y_offset = 70
            for start_idx, end_idx in horizontal_pairs:
                if end_idx < len(polyline_points):
                    start = APoint(polyline_points[start_idx][0], polyline_points[start_idx][1])
                    # Для горизонтального размера используем только разницу по X
                    end = APoint(polyline_points[end_idx][0], polyline_points[start_idx][1])  # y = y2
                    dim_x = (start.x + end.x) / 2
                    dim_y = start.y + y_offset
                    dim_point = APoint(dim_x, dim_y)
                    if not at_dimension("H", start, end, dim_point, adoc=adoc, layer="AM_5"):
                        logging.error(f"Не удалось проставить горизонтальный размер между точками {start_idx} и {end_idx}")
                        show_popup(loc.get("dim_creation_error", "Ошибка при создании размера"), popup_type="error")
                    y_offset += 70

            # Вертикальные размеры: 0-9, 0-7, 0-5, 0-3 (шаг по X -70)
            vertical_pairs = [(0, 9), (0, 7), (0, 5), (0, 3)]
            x_offset = -70
            for start_idx, end_idx in vertical_pairs:
                if end_idx < len(polyline_points):
                    start = APoint(polyline_points[start_idx][0], polyline_points[start_idx][1])
                    # Для вертикального размера используем только разницу по Y
                    end = APoint(polyline_points[start_idx][0], polyline_points[end_idx][1])  # x = x0
                    dim_x = start.x + x_offset
                    dim_y = (start.y + end.y) / 2
                    dim_point = APoint(dim_x, dim_y)
                    if not at_dimension("V", start, end, dim_point, adoc=adoc, layer="AM_5"):
                        logging.error(f"Не удалось проставить вертикальный размер между точками {start_idx} и {end_idx}")
                        show_popup(loc.get("dim_creation_error", "Ошибка при создании размера"), popup_type="error")
                    x_offset -= 70

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

        # Регенерация чертежа
        regen(adoc)

        logging.info("Полилиния, внутренняя полилиния, размеры и текст успешно созданы")
        return True

    except Exception as e:
        show_popup(loc.get("general_error", f"Ошибка: {str(e)}"), popup_type="error")
        logging.error(f"Ошибка в run_plate (programms/at_run_plate.py): {e}")
        return False
