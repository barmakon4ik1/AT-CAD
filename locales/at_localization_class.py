"""
Файл: at_localization_class.py
Путь: locales/at_localization_class.py

Описание:
Модуль для управления локализацией в приложении AT-CAD. Предоставляет класс Localization
для работы с переводами интерфейса на разные языки (ru, en, de).
"""

import logging
from locales.at_localization import translations


class Localization:
    """
    Класс для управления локализацией интерфейса приложения.

    Атрибуты:
        language (str): Текущий язык локализации (например, "ru", "en", "de").
    """
    def __init__(self, language: str | None = None):
        """
        Инициализирует локализацию с указанным языком или языком по умолчанию.

        Аргументы:
            language (str | None): Код языка (например, "ru"). Если None, используется "ru".

        Логирует инициализацию выбранного языка.
        """
        self.language = language if isinstance(language, str) and language in ["ru", "en", "de"] else "ru"
        logging.info(f"Инициализация локализации с языком: {self.language}")

    def set_language(self, language: str) -> None:
        """
        Устанавливает новый язык локализации.

        Аргументы:
            language (str): Код языка для установки (например, "ru", "en", "de").

        Если язык недопустим, сохраняется текущий язык и записывается предупреждение в лог.
        """
        if not isinstance(language, str):
            logging.error(f"Попытка установить нестроковый язык: {language}, тип: {type(language)}, остаётся: {self.language}")
            return
        if language not in ["ru", "en", "de"]:
            logging.warning(f"Недопустимый язык: {language}, остаётся: {self.language}")
            return
        self.language = language
        logging.info(f"Язык локализации изменён на: {self.language}")

    def get(self, key: str, default: str = "Translation missing") -> str:
        """
        Возвращает перевод строки по ключу для текущего языка.

        Аргументы:
            key (str): Ключ перевода (строка).
            default (str): Значение по умолчанию, если перевод отсутствует.

        Возвращает:
            str: Перевод строки или значение по умолчанию, если ключ отсутствует.
        """
        if not isinstance(key, str):
            logging.warning(f"Получен нестроковый ключ: {key}, возвращается значение по умолчанию")
            return default if isinstance(default, str) else str(default)

        # Проверяем, что default — строка
        if not isinstance(default, str):
            logging.warning(f"Нестроковое значение default: {default}, преобразование в строку")
            default = str(default)

        # Проверяем, что self.language — строка
        if not isinstance(self.language, str):
            logging.error(f"self.language не строка: {self.language}, тип: {type(self.language)}, установка языка по умолчанию: ru")
            self.language = "ru"

        # Проверяем наличие ключа в translations
        if key not in translations:
            logging.warning(f"Ключ '{key}' отсутствует в translations, возвращается значение по умолчанию")
            return default

        # Проверяем наличие перевода для текущего языка
        translation = translations[key].get(self.language)
        if translation is None:
            logging.warning(f"Перевод для ключа '{key}' и языка '{self.language}' отсутствует, возвращается значение по умолчанию")
            return default

        # Проверяем, что translation — строка
        if not isinstance(translation, str):
            logging.warning(f"Нестроковый перевод для ключа '{key}' и языка '{self.language}': {translation}, возвращается значение по умолчанию")
            return default

        logging.debug(f"Получен перевод для ключа '{key}': {translation}")
        return translation


# Создаём глобальный экземпляр локализации
loc = Localization()
