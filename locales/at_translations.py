# locales/at_translations.py
"""
Файл: at_translations.py
Путь: locales/at_translations.py
Описание: Модуль для управления локализацией. Обрабатывает переводы из локальных словарей модулей
и поддерживает динамическую смену языка.
"""

import logging

class Localization:
    """
    Класс для управления локализацией приложения AT-CAD.
    Работает с локальными словарями переводов в каждом модуле.
    """
    def __init__(self, language: str = "ru"):
        """
        Инициализирует локализацию с указанным языком.
        Аргументы:
            language (str): Код языка (например, "ru", "en", "de").
        """
        self.language = "ru"
        self.supported_languages = ["ru", "en", "de"]
        logging.info(f"Инициализация Localization с language={language}")
        self.set_language(language)
        self._translations = {}  # Кэш для словарей переводов из модулей

    def set_language(self, language: str) -> None:
        """
        Устанавливает новый язык локализации.
        Аргументы:
            language (str): Код языка для установки (например, "ru", "en", "de").
        """
        if not isinstance(language, str):
            logging.error(f"Попытка установить нестроковый язык: {language}, тип: {type(language)}, остаётся: {self.language}")
            return
        if language not in self.supported_languages:
            logging.warning(f"Недопустимый язык: {language}, остаётся: {self.language}")
            return
        logging.info(f"Смена языка на: {language}")
        self.language = language

    def register_translations(self, translations: dict) -> None:
        """
        Регистрирует словарь переводов из модуля.
        Аргументы:
            translations (dict): Словарь переводов модуля.
        """
        self._translations.update(translations)
        logging.debug(f"Зарегистрированы переводы: {list(translations.keys())}")

    def get(self, key: str, default: str = "Translation missing", *args) -> str:
        """
        Возвращает перевод строки по ключу для текущего языка.
        Аргументы:
            key (str): Ключ перевода.
            default (str): Значение по умолчанию, если перевод отсутствует.
            *args: Аргументы для форматирования строки.
        Возвращает:
            str: Перевод строки или значение по умолчанию.
        """
        if not isinstance(key, str):
            logging.warning(f"Получен нестроковый ключ: {key}, возвращается значение по умолчанию")
            return default.format(*args) if args else default

        if not isinstance(default, str):
            logging.warning(f"Нестроковое значение default: {default}, преобразование в строку")
            default = str(default)

        translation = self._translations.get(key, {}).get(self.language, default)
        if translation == default:
            logging.warning(f"Перевод для ключа '{key}' и языка '{self.language}' отсутствует, возвращается значение по умолчанию")

        if not isinstance(translation, str):
            logging.warning(f"Нестроковый перевод для ключа '{key}' и языка '{self.language}': {translation}, возвращается значение по умолчанию")
            return default.format(*args) if args else default

        logging.debug(f"Получен перевод для ключа '{key}': {translation}")
        return translation.format(*args) if args else translation

# Глобальный экземпляр локализации
loc = Localization()
