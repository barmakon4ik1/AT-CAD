"""
Файл: at_localization_class.py
Путь: locales\at_localization_class.py

Описание:
Модуль для управления локализацией в приложении AT-CAD. Предоставляет класс Localization
для работы с переводами интерфейса на разные языки (ru, en, de).
Использует настройку языка из user_settings.json через get_setting.
"""

import logging
from config.at_config import get_setting, load_user_settings, save_user_settings
from locales.at_localization import translations

class Localization:
    """
    Класс для управления локализацией интерфейса приложения.

    Атрибуты:
        language (str): Текущий язык локализации (например, "ru", "en", "de").
    """
    def __init__(self, language: str | None = None):
        """
        Инициализирует локализацию с указанным языком или языком из user_settings.json.

        Аргументы:
            language (str | None): Код языка (например, "ru"). Если None, используется язык из user_settings.json.

        Логирует инициализацию выбранного языка.
        """
        self.language = language if language in ["ru", "en", "de"] else get_setting("LANGUAGE")
        logging.info(f"Инициализация локализации с языком: {self.language}")

    def set_language(self, language: str) -> None:
        """
        Устанавливает новый язык локализации и сохраняет его в user_settings.json.

        Аргументы:
            language (str): Код языка для установки (например, "ru", "en", "de").

        Если язык недопустим, сохраняется текущий язык и записывается предупреждение в лог.
        """
        if language in ["ru", "en", "de"]:
            self.language = language
            # Обновляем user_settings.json
            settings = load_user_settings()
            settings["LANGUAGE"] = self.language
            save_user_settings(settings)
            logging.info(f"Язык локализации изменён на: {self.language}")
        else:
            logging.warning(f"Недопустимый язык: {language}, остаётся: {self.language}")

    def get(self, key: str, default: str = "Translation missing") -> str:
        """
        Возвращает перевод строки по ключу для текущего языка.

        Аргументы:
            key (str): Ключ перевода.
            default (str): Значение по умолчанию, если перевод отсутствует.

        Возвращает:
            str: Перевод строки или значение по умолчанию в случае ошибки.

        Логирует успешное получение перевода или ошибки.
        """
        try:
            translation = translations.get(key, {}).get(self.language, default)
            logging.debug(f"Получен перевод для ключа '{key}': {translation}")
            return translation
        except Exception as e:
            logging.error(f"Ошибка получения перевода для ключа '{key}': {e}")
            return default

# Создаём глобальный экземпляр локализации
loc = Localization()
