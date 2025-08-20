# locales/at_translations.py
"""
Файл: at_translations.py
Путь: locales/at_translations.py
Описание: Модуль для управления локализацией. Обрабатывает переводы из локальных словарей модулей
и поддерживает динамическую смену языка.
"""

import os
import json
import logging


class Localization:
    """
    Класс для управления локализацией приложения AT-CAD.
    Работает с локальными словарями переводов в каждом модуле.
    """
    def __init__(self, language: str = None):
        """
        Инициализирует локализацию. Язык берётся из config/user_language.json,
        если файл доступен. Приоритет: аргумент > json > "ru".
        """
        self.supported_languages = ["ru", "en", "de"]
        self._translations = {}

        # Значение по умолчанию
        self.language = "ru"

        # Путь к файлу языка
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "user_language.json")
        config_path = os.path.abspath(config_path)

        # Загружаем язык из JSON, если есть
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "language" in data:
                    file_lang = data["language"]
                    if language is None:  # приоритет у аргумента
                        language = file_lang
            except Exception as e:
                logging.critical(f"Ошибка чтения user_language.json: {e}")

        # Устанавливаем язык (аргумент > json > fallback "ru")
        self.set_language(language or "ru")

    def set_language(self, language: str) -> None:
        """
        Устанавливает новый язык локализации.
        """
        if not isinstance(language, str):
            logging.critical(f"Попытка установить нестроковый язык: {language}, тип: {type(language)}")
            return
        if language not in self.supported_languages:
            # Если язык не поддерживается — молча остаёмся на текущем
            return
        self.language = language

    def register_translations(self, translations: dict) -> None:
        """
        Регистрирует словарь переводов из модуля.
        """
        if not isinstance(translations, dict):
            logging.critical(f"Передан некорректный словарь переводов: {type(translations)}")
            return
        self._translations.update(translations)

    def get(self, key: str, default: str = "Translation missing", *args) -> str:
        """
        Возвращает перевод строки по ключу для текущего языка.
        """
        if not isinstance(key, str):
            return default.format(*args) if args else default

        if not isinstance(default, str):
            default = str(default)

        translation = self._translations.get(key, {}).get(self.language, default)

        if not isinstance(translation, str):
            logging.critical(f"Нестроковый перевод для ключа '{key}' и языка '{self.language}': {translation}")
            return default.format(*args) if args else default

        try:
            return translation.format(*args) if args else translation
        except Exception as e:
            logging.critical(f"Ошибка форматирования строки '{translation}': {e}")
            return translation


# Глобальный экземпляр локализации
loc = Localization()

if __name__ == "__main__":
    import pprint

    print("=== Тестирование модуля Localization ===")

    # Создаём экземпляр
    localization = Localization()

    # Вывод текущего языка
    print(f"Текущий язык (после чтения user_language.json): {localization.language}")

    # Если словарь JSON читается корректно — покажем содержимое
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "user_language.json")
    config_path = os.path.abspath(config_path)
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print("Содержимое user_language.json:")
            pprint.pprint(data)
        except Exception as e:
            print(f"Ошибка чтения user_language.json: {e}")
    else:
        print("Файл user_language.json не найден")
