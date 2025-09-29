"""
Файл: programs/at_run_cone.py
Описание:
Модуль для построения развертки конуса в AutoCAD с использованием Win32com (COM).
Использует данные из окна content_cone.py для создания развертки конуса, добавления текстовых меток
и размеров. Локализация через словарь TRANSLATIONS. Поддерживает слои LASER-TEXT, schrift, TEXT.
"""

import logging
from typing import Dict, Optional

import win32com
from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from config.at_config import TEXT_HEIGHT_BIG, TEXT_HEIGHT_SMALL, TEXT_DISTANCE, DEFAULT_DIM_OFFSET
from locales.at_translations import loc
from programs.at_construction import at_cone_sheet, polar_point, add_text
from programs.at_base import ensure_layer, regen
from programs.at_dimension import add_dimension
from programs.at_geometry import ensure_point_variant
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "invalid_point_format": {
        "ru": "Точка вставки должна быть [x, y, 0]",
        "de": "Einfügepunkt muss [x, y, 0] sein",
        "en": "Insertion point must be [x, y, 0]"
    },
    "cone_sheet_error": {
        "ru": "Ошибка построения развертки конуса",
        "de": "Fehler beim Erstellen der Kegelabwicklung",
        "en": "Error building cone sheet"
    },
    "text_error_details": {
        "ru": "Ошибка добавления текста {0} ({1}): {2}",
        "de": "Fehler beim Hinzufügen von Text {0} ({1}): {2}",
        "en": "Error adding text {0} ({1}): {2}"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "de": "Baufehler: {0}",
        "en": "Build error: {0}"
    },
    "com_release_error": {
        "ru": "Ошибка освобождения COM: {0}",
        "de": "Fehler beim Freigeben von COM: {0}",
        "en": "Error releasing COM: {0}"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main(data: Dict[str, any]) -> bool:
    """
    Основная функция для построения развертки конуса в AutoCAD.

    Args:
        data: Словарь с данными конуса, полученными из окна content_cone.py
              (order_number, detail_number, material, thickness, diameter_top,
              diameter_base, d_type, D_type, height, steigung, angle, weld_allowance,
              insert_point, thickness_text).

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    try:
        # Инициализация AutoCAD
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space

        # Проверка данных
        if not data:
            show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
            logging.error("Данные не введены")
            return None

        # Извлекаем данные
        required_keys = ["insert_point", "diameter_base", "diameter_top", "height", "material", "thickness", "thickness_text"]
        for key in required_keys:
            if key not in data or data[key] is None:
                show_popup(loc.get("no_data_error", f"Missing or None value for key: {key}"), popup_type="error")
                logging.error(f"Отсутствует или None значение для ключа: {key}")
                return None

        insert_point = data.get("insert_point")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")
        diameter_base = float(data.get("diameter_base", 0.0))
        diameter_top = float(data.get("diameter_top", 0.0))
        height = float(data.get("height", 0.0))
        thickness_text = data.get("thickness_text", "")
        weld_allowance = float(data.get("weld_allowance", 0.0))

        # Проверяем insert_point
        if not isinstance(insert_point, (list, tuple)) or len(insert_point) != 3:
            show_popup(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"), popup_type="error")
            logging.error(f"Некорректная точка вставки: {insert_point}")
            return None
        insert_point = list(map(float, insert_point[:3]))  # Берём [x, y, z]
        data["insert_point"] = insert_point  # Обновляем в data

        # Создание слоёв
        # for layer in ["LASER-TEXT", "schrift", "TEXT"]:
        #     ensure_layer(model, layer)

        # Построение развертки конуса
        build_result = at_cone_sheet(
            model=model,
            input_point=ensure_point_variant(insert_point),
            diameter_base=diameter_base,
            diameter_top=diameter_top,
            height=height,
            layer_name="0"
        )
        if build_result is None:
            show_popup(loc.get("cone_sheet_error", "Ошибка построения развертки конуса"), popup_type="error")
            logging.error("Ошибка построения развертки конуса")
            return None

        # Формирование текста для меток
        k_text = f"{order_number}"
        f_text = k_text
        if detail_number:
            f_text += f"-{detail_number}"
        text_ab = TEXT_DISTANCE
        text_h = TEXT_HEIGHT_BIG
        text_s = TEXT_HEIGHT_SMALL
        text_point = polar_point(insert_point, 300, 0, as_variant=False)

        # Список текстов для добавления
        text_configs = [
            {
                "point": ensure_point_variant(insert_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 4
            },  # Гравировка
            {
                "point": ensure_point_variant(polar_point(insert_point, distance=20, alpha=-90, as_variant=False)),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": text_s,
                "text_angle": 0,
                "text_alignment": 4
            },  # Маркировка
            {
                "point": ensure_point_variant(text_point),
                "text": f"Komm.Nr. {f_text}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },  # Строка К-№
            {
                "point": ensure_point_variant(polar_point(text_point, distance=text_ab, alpha=-90, as_variant=False)),
                "text": f"D = {diameter_base} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(text_point, distance=2 * text_ab, alpha=-90, as_variant=False)),
                "text": f"d = {diameter_top} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(text_point, distance=3 * text_ab, alpha=-90, as_variant=False)),
                "text": f"H = {height} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(text_point, distance=4 * text_ab, alpha=-90, as_variant=False)),
                "text": f"Dicke = {thickness_text}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(text_point, distance=5 * text_ab, alpha=-90, as_variant=False)),
                "text": f"Wst: {material}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            }
        ]

        # Добавление текстов
        for i, config in enumerate(text_configs):
            try:
                add_text(
                    model=model,
                    point=config["point"],
                    text=config["text"],
                    layer_name=config["layer_name"],
                    text_height=config["text_height"],
                    text_angle=config["text_angle"],
                    text_alignment=config["text_alignment"]
                )
            except Exception as e:
                show_popup(
                    loc.get("text_error_details", f"Ошибка добавления текста {i + 1} ({config['text']}): {str(e)}").format(i + 1, config['text'], str(e)),
                    popup_type="error"
                )
                logging.error(f"Ошибка добавления текста {i + 1}: {e}")
                return None

        # Простановка размеров (пример для диаметров и высоты)
        # Для диаметра основания
        # base_point = ensure_point_variant([insert_point[0], insert_point[1] + diameter_base / 2, insert_point[2]])
        # base_ref_point = ensure_point_variant([insert_point[0], insert_point[1] - diameter_base / 2, insert_point[2]])
        # add_dimension(adoc, "H", base_point, base_ref_point, offset=DEFAULT_DIM_OFFSET)
        #
        # # Для диаметра вершины
        # top_point = ensure_point_variant([insert_point[0], insert_point[1] + diameter_top / 2, insert_point[2]])
        # top_ref_point = ensure_point_variant([insert_point[0], insert_point[1] - diameter_top / 2, insert_point[2]])
        # add_dimension(adoc, "H", top_point, top_ref_point, offset=DEFAULT_DIM_OFFSET + TEXT_DISTANCE)
        #
        # # Для высоты
        # height_point = ensure_point_variant([insert_point[0], insert_point[1], insert_point[2] + height])
        # add_dimension(adoc, "V", ensure_point_variant(insert_point), height_point, offset=DEFAULT_DIM_OFFSET)

        regen(adoc)
        logging.info("Развертка конуса успешно построена")
        return True
    except Exception as e:
        show_popup(loc.get("build_error", f"Ошибка построения: {str(e)}").format(str(e)), popup_type="error")
        logging.error(f"Ошибка в main: {e}")
        return None


if __name__ == "__main__":
    """
    Тестовый запуск построения развертки конуса.
    """
    input_data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter_base": 1000.0,
        "diameter_top": 500.0,
        "height": 800.0,
        "material": "1.4301",
        "thickness": 4.0,
        "thickness_text": "4.00 мм",
        "order_number": "12345",
        "detail_number": "01",
        "layer_name": "0",
        "weld_allowance": 3.0
    }
    main(input_data)
