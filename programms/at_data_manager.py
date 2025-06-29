# at_data_manager.py
"""
Модуль для управления данными, загружаемыми из JSON-файла.
Предоставляет доступ к конфигурационным данным по заданным путям.
"""

import json
from typing import Any, List, Dict


class DataManager:
    """
    Класс для загрузки и доступа к данным из JSON-файла.
    """
    def __init__(self, filepath: str = "common_data.json") -> None:
        """
        Инициализирует менеджер данных с указанным файлом.

        Args:
            filepath: Путь к JSON-файлу с данными (по умолчанию 'common_data.json').
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
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
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
            return data
        except (KeyError, TypeError):
            return []


# Создание глобального экземпляра менеджера данных
data_manager = DataManager()
