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
        """
        self.supported_languages = ["ru", "en", "de"]
        self._translations = {}  # Сначала создаём словарь!
        self.language = "ru"
        logging.info(f"Инициализация Localization с language={language}")
        self.set_language(language)

    def set_language(self, language: str) -> None:
        """
        Устанавливает новый язык локализации.
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
        """
        if not isinstance(translations, dict):
            logging.error(f"Передан некорректный словарь переводов: {type(translations)}")
            return
        self._translations.update(translations)
        logging.debug(f"Зарегистрированы переводы: {list(translations.keys())}")

    def get(self, key: str, default: str = "Translation missing", *args) -> str:
        """
        Возвращает перевод строки по ключу для текущего языка.
        """
        if not isinstance(key, str):
            logging.warning(f"Получен нестроковый ключ: {key}, возвращается значение по умолчанию")
            return default.format(*args) if args else default

        if not isinstance(default, str):
            logging.warning(f"Нестроковое значение default: {default}, преобразование в строку")
            default = str(default)

        # Берём перевод или default
        translation = self._translations.get(key, {}).get(self.language, default)

        if translation == default:
            logging.warning(f"Перевод для ключа '{key}' и языка '{self.language}' отсутствует")

        if not isinstance(translation, str):
            logging.warning(f"Нестроковый перевод для ключа '{key}' и языка '{self.language}': {translation}, возвращается default")
            return default.format(*args) if args else default

        try:
            return translation.format(*args) if args else translation
        except Exception as e:
            logging.error(f"Ошибка форматирования строки '{translation}': {e}")
            return translation

# Глобальный экземпляр локализации
loc = Localization()
