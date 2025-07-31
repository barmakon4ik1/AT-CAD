import os
import json
import logging
from typing import Dict
from config.at_config import RESOURCE_DIR
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def save_last_input(file_name: str, data: Dict) -> None:
    """
    Сохраняет введённые данные в JSON-файл для указанной панели.

    Args:
        file_name: Имя файла для сохранения данных (например, 'last_cone_input.json').
        data: Словарь с данными для сохранения.
    """
    try:
        if not file_name:
            logging.warning("Имя файла для сохранения данных не указано")
            return
        file_path = os.path.join(RESOURCE_DIR, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info(f"Данные сохранены в {file_path}: {data}")
    except Exception as e:
        logging.error(f"Ошибка сохранения данных в {file_name}: {e}")
        show_popup(loc.get("error", f"Ошибка сохранения данных: {str(e)}"), popup_type="error")
