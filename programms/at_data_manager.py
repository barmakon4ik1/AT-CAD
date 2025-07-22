# at_data_manager.py
"""
Модуль для управления данными, загружаемыми из JSON-файла.
Предоставляет доступ к конфигурационным данным по заданным путям.
"""

import json
import os
from typing import Any, List, Dict
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class DataManager:
    """
    Класс для загрузки и доступа к данным из JSON-файла.
    """
    def __init__(self, filepath: str) -> None:
        """
        Инициализирует менеджер данных с указанным файлом.

        Args:
            filepath: Путь к JSON-файлу с данными.
        """
        self.filepath = filepath
        self.data = self.load_data()

    def load_data(self) -> Dict:
        """
        Загружает данные из JSON-файла.

        Returns:
            dict: Данные из файла или пустой словарь при ошибке.
        """
        try:
            if not os.path.exists(self.filepath):
                logging.error(f"Файл конфигурации '{self.filepath}' не найден")
                return {}
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"Конфигурация загружена из '{self.filepath}'")
                return data
        except Exception as e:
            logging.error(f"Ошибка загрузки конфигурации из '{self.filepath}': {e}")
            return {}

    def get_data(self, path: str) -> List[Any]:
        """
        Извлекает данные по указанному пути в формате 'section.subsection.key'.

        Args:
            path: Путь к данным (например, 'dimensions.diameters').

        Returns:
            list: Данные по указанному пути или пустой список при ошибке.
        """
        keys = path.split('.')
        data = self.data
        try:
            for key in keys:
                data = data[key]
            return [str(item) for item in data] if isinstance(data, list) else []
        except (KeyError, TypeError) as e:
            logging.error(f"Ошибка получения данных по пути '{path}': {e}")
            return []


# Глобальные экземпляры менеджера данных
config_manager = DataManager("config/config.json")  # Для config.json
common_data_manager = DataManager("config/common_data.json")  # Для common_data.json
