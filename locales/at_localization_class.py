# locales/at_localization_class.py
"""
Модуль для управления локализацией текстовых сообщений.
"""

from typing import Union
import logging
from config.at_config import LANGUAGE
from locales.at_localization import translations

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Localization:
    """
    Класс для управления локализацией текстовых сообщений.
    """

    def __init__(self, language: str = LANGUAGE):
        """
        Инициализирует локализацию с заданным языком.

        Args:
            language: Код языка ("ru", "de", "en"). По умолчанию берётся из at_config.LANGUAGE.
        """
        self._valid_languages = {"ru", "de", "en"}
        self.language = language if language in self._valid_languages else "ru"
        logging.info(f"Localization initialized with language: {self.language}")

    def set_language(self, language: str) -> None:
        """
        Устанавливает язык локализации.

        Args:
            language: Код языка ("ru", "de", "en").
        """
        self.language = language if language in self._valid_languages else "ru"
        logging.info(f"Language set to: {self.language}")

    def get(self, key: str, default: str = None, *args) -> str:
        """
        Возвращает переведённое сообщение.

        Args:
            key: Ключ строки.
            default: Значение по умолчанию, если ключ не найден.
            *args: Параметры форматирования.

        Returns:
            str: Переведённая строка или значение по умолчанию, если перевод не найден.
        """
        if self.language not in self._valid_languages:
            self.language = "ru"
            logging.warning(f"Invalid language detected, reverted to: {self.language}")

        text = translations.get(key, {}).get(self.language, default if default is not None else key)
        logging.debug(f"Localization: key={key}, language={self.language}, result={text}")

        if not args:
            return text
        try:
            return text.format(*args)
        except (IndexError, KeyError, ValueError) as e:
            logging.error(f"Error formatting localization string: key={key}, text={text}, args={args}, error={e}")
            return text


# Глобальный объект локализации
loc = Localization()
