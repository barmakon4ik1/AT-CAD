import logging

import pythoncom
from pyautocad import APoint
from programms.at_construction import at_cone_sheet, polar_point, at_addText
from typing import Dict, Any
from locales.at_localization_class import loc
from config.at_config import *
from windows.at_gui_utils import show_popup
from programms.at_base import ensure_layer, regen

loc.language = load_user_settings()


def run_application(data: Dict[str, Any]) -> bool:
    """
    Выполняет построение развертки конуса на основе предоставленных данных.

    Args:
        data: Словарь с параметрами конуса (model, input_point, diameter_base, diameter_top, height, layer_name, order_number, detail_number, material, thickness_text).

    Returns:
        bool: True если выполнено успешно, False если ошибка.
    """
    try:
        pythoncom.CoInitialize()  # Инициализация COM
        # Проверка входных данных
        required_keys = ["model", "input_point", "diameter_base", "diameter_top", "height", "layer_name",
                         "order_number", "detail_number", "thickness_text", "material"]
        for key in required_keys:
            if key not in data or data[key] is None:
                show_popup(loc.get("missing_data", key), popup_type="error")
                logging.error(f"Отсутствует или None значение для ключа: {key}")
                return False

        model = data["model"]
        input_point = data["input_point"]

        # Создание слоёв
        for layer in ["LASER-TEXT", "schrift", "TEXT"]:
            ensure_layer(model, layer)

        # Построение развертки конуса
        build_result = at_cone_sheet(
            model=model,
            input_point=input_point,
            diameter_base=data["diameter_base"],
            diameter_top=data["diameter_top"],
            height=data["height"],
            layer_name=data["layer_name"]
        )
        if build_result is None:
            show_popup(loc.get("cone_sheet_error"), popup_type="error")
            logging.error("Ошибка построения развертки конуса")
            return False

        k_text = f"{data['order_number']}"
        f_text = k_text
        if data['detail_number']:
            f_text += f"-{data['detail_number']}"
        text_ab = TEXT_DISTANCE
        text_h = TEXT_HEIGHT_BIG
        text_s = TEXT_HEIGHT_SMALL
        text_point = polar_point(input_point, 300, 0)

        # Список текстов для добавления

        text_configs = [
            {
                "point": input_point,
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 4
            },  # Гравировка
            {
                "point": polar_point(input_point, distance=20, alpha=-90),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": text_s,
                "text_angle": 0,
                "text_alignment": 4
            },  # Маркировка
            {
                "point": text_point,
                "text": f"Komm.Nr. {f_text}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },  # Строка К-№
            {
                "point": polar_point(text_point, distance=text_ab, alpha=-90),
                "text": f"D = {data['diameter_base']} {(loc.get('mm'))}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": polar_point(text_point, distance=2 * text_ab, alpha=-90),
                "text": f"d = {data['diameter_top']} {(loc.get('mm'))}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": polar_point(text_point, distance=3 * text_ab, alpha=-90),
                "text": f"H = {data['height']} {(loc.get('mm'))}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": polar_point(text_point, distance=4 * text_ab, alpha=-90),
                "text": f"Dicke = {data['thickness_text']}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": polar_point(text_point, distance=5 * text_ab, alpha=-90),
                "text": f"Wst: {data['material']}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            }
        ]

        # Добавление текстов
        for i, config in enumerate(text_configs):
            try:
                at_addText(
                    model=model,
                    point=config["point"],
                    text=config["text"],
                    layer_name=config["layer_name"],
                    text_height=config["text_height"],
                    text_angle=config["text_angle"],
                    text_alignment=config["text_alignment"]
                )
            except Exception as e:
                show_popup(f"Ошибка при добавлении текста {i + 1} ({config['text']}): {str(e)}", popup_type="error")
                logging.error(f"Ошибка добавления текста {i + 1}: {e}")
                return False
        regen(model)
        logging.info("Развертка конуса успешно построена")
        return True
    except Exception as e:
        show_popup(loc.get("build_error", str(e)), popup_type="error")
        logging.error(f"Ошибка в run_application: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception as e:
            show_popup(loc.get("com_release_error", str(e)), popup_type="error")
            logging.error(f"Ошибка освобождения COM: {e}")
