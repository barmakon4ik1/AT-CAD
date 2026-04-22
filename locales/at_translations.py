# -*- coding: utf-8 -*-
# locales/at_translations.py
"""
Файл: at_translations.py
Путь: locales/at_translations.py

Описание:
    Модуль локализации приложения AT-CAD.
    Реализует паттерн «модульных переводов»: каждый модуль проекта
    регистрирует свой словарь переводов через loc.register_translations(),
    а для получения строки в любом месте кода достаточно loc.get(key).

Архитектура:
    Единственный экземпляр Localization (loc) создаётся при импорте модуля
    и живёт всё время работы приложения. Это позволяет:
        - регистрировать переводы из разных модулей в любом порядке
        - менять язык в рантайме через loc.set_language() — все следующие
          вызовы loc.get() сразу вернут строки нового языка

Язык при старте (приоритет по убыванию):
    1. Аргумент конструктора Localization(language="de")
    2. Файл config/user_language.json → {"language": "en"}
    3. Fallback: "ru"

Поддерживаемые языки:
    "ru", "en", "de"

Формат словаря переводов:
    {
        "ключ": {
            "ru": "Русский текст",
            "en": "English text",
            "de": "Deutscher Text",
        },
        ...
    }

Пример использования:
    from locales.at_translations import loc

    TRANSLATIONS = {
        "my_key": {"ru": "Привет, {}!", "en": "Hello, {}!", "de": "Hallo, {}!"},
    }
    loc.register_translations(TRANSLATIONS)

    print(loc.get("my_key", "Fallback", "Мир"))  # → "Привет, Мир!"
    print(loc.tr("my_key", "Fallback", "World")) # то же самое
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

# ============================================================
# ЛОГИРОВАНИЕ
# Используем именованный logger, чтобы не перебивать
# корневой basicConfig приложения.
# ============================================================

logger = logging.getLogger("at_translations")


# ============================================================
# КЛАСС ЛОКАЛИЗАЦИИ
# ============================================================

class Localization:
    """
    Менеджер локализации приложения AT-CAD.

    Хранит все зарегистрированные переводы в едином словаре _translations.
    Каждый модуль регистрирует свои строки через register_translations()
    при импорте — это позволяет держать переводы рядом с кодом,
    а не в одном глобальном файле.

    Атрибуты:
        language            — текущий активный язык ("ru" / "en" / "de")
        supported_languages — список допустимых языков
    """

    SUPPORTED_LANGUAGES: list[str] = ["ru", "en", "de"]
    _DEFAULT_LANGUAGE: str = "ru"
    _LANGUAGE_CONFIG: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "config", "user_language.json")
    )

    def __init__(self, language: Optional[str] = None) -> None:
        """
        Инициализирует локализацию.

        Порядок определения языка:
            1. Аргумент language (если передан и поддерживается)
            2. Файл config/user_language.json ({"language": "..."})
            3. Fallback: "ru"

        Параметры:
            language — явное указание языка; None = автоопределение из файла
        """
        self.supported_languages: list[str] = self.SUPPORTED_LANGUAGES
        self._translations: dict[str, dict[str, str]] = {}
        self.language: str = self._DEFAULT_LANGUAGE

        # Читаем язык из JSON-файла (если аргумент не задан)
        file_lang: Optional[str] = self._read_language_from_config()

        # Приоритет: аргумент > файл > fallback
        resolved = language or file_lang or self._DEFAULT_LANGUAGE
        self.set_language(resolved)

    # =========================================================
    # ПРИВАТНЫЕ МЕТОДЫ
    # =========================================================

    def _read_language_from_config(self) -> Optional[str]:
        """
        Читает язык из config/user_language.json.

        Возвращает:
            Строку языка ("ru" / "en" / "de") или None если файл
            не найден, нечитаем, или содержит некорректные данные.
        """
        if not os.path.isfile(self._LANGUAGE_CONFIG):
            return None

        try:
            with open(self._LANGUAGE_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка чтения user_language.json: {e}")
            return None

        if not isinstance(data, dict):
            logger.warning(f"user_language.json: ожидался dict, получен {type(data).__name__}")
            return None

        lang = data.get("language")
        if not isinstance(lang, str):
            logger.warning(f"user_language.json: поле 'language' не является строкой: {lang!r}")
            return None

        return lang

    # =========================================================
    # ПУБЛИЧНЫЙ API
    # =========================================================

    def set_language(self, language: str) -> bool:
        """
        Устанавливает язык локализации.

        Если язык не поддерживается — текущий язык сохраняется без изменений.

        Параметры:
            language — код языка из supported_languages

        Возвращает:
            True  — язык установлен
            False — язык не поддерживается или передан не-строковый тип

        Пример:
            loc.set_language("en")
        """
        if not isinstance(language, str):
            logger.error(
                f"set_language: ожидалась строка, получен {type(language).__name__!r}: {language!r}"
            )
            return False

        lang = language.lower().strip()

        if lang not in self.supported_languages:
            logger.warning(
                f"set_language: язык {lang!r} не поддерживается. "
                f"Допустимые: {self.supported_languages}. Язык не изменён."
            )
            return False

        self.language = lang
        logger.debug(f"Язык установлен: {lang!r}")
        return True

    def register_translations(self, translations: dict[str, dict[str, str]]) -> None:
        """
        Регистрирует словарь переводов из модуля.

        Вызывается при импорте каждого модуля, который имеет локализованные строки.
        Новые ключи добавляются; если ключ уже существует — он перезаписывается
        (последний зарегистрированный побеждает). Это позволяет переопределять
        строки из других модулей.

        Параметры:
            translations — словарь вида:
                {
                    "ключ": {"ru": "...", "en": "...", "de": "..."},
                    ...
                }

        Пример:
            TRANSLATIONS = {
                "save_error": {
                    "ru": "Ошибка сохранения файла",
                    "en": "File save error",
                    "de": "Fehler beim Speichern",
                }
            }
            loc.register_translations(TRANSLATIONS)
        """
        if not isinstance(translations, dict):
            logger.error(
                f"register_translations: ожидался dict, получен {type(translations).__name__!r}"
            )
            return

        self._translations.update(translations)
        logger.debug(f"Зарегистрировано ключей: {len(translations)}")

    def get(self, key: str, default: str = "Translation missing", *args: object) -> str:
        """
        Возвращает локализованную строку по ключу для текущего языка.

        Алгоритм:
            1. Ищем ключ в _translations
            2. Ищем перевод для текущего языка
            3. Если не нашли — возвращаем default
            4. Если есть позиционные аргументы args — форматируем через .format()

        Параметры:
            key     — строковый ключ перевода
            default — значение по умолчанию если ключ не найден
            *args   — аргументы для str.format() (позиционные)

        Возвращает:
            Локализованную строку или default при отсутствии ключа.
            Никогда не бросает исключений.

        Пример:
            loc.get("save_error")
            loc.get("file_not_found", "Файл не найден")
            loc.get("layer_error", "Ошибка слоя: {}", layer_name)
        """
        if not isinstance(key, str):
            logger.warning(f"get: ключ не является строкой: {key!r}")
            return self._safe_format(default, args)

        if not isinstance(default, str):
            default = str(default)

        # Ищем перевод: сначала для текущего языка, затем default
        entry = self._translations.get(key)
        if entry is None:
            # Ключ вообще не зарегистрирован — тихо возвращаем default
            return self._safe_format(default, args)

        translation = entry.get(self.language)
        if translation is None:
            # Перевод для текущего языка отсутствует — возвращаем default
            logger.debug(f"get: нет перевода ключа {key!r} для языка {self.language!r}")
            return self._safe_format(default, args)

        if not isinstance(translation, str):
            logger.error(
                f"get: перевод ключа {key!r} для {self.language!r} "
                f"не является строкой: {translation!r}"
            )
            return self._safe_format(default, args)

        return self._safe_format(translation, args)

    def tr(self, key: str, default: str = "Translation missing", *args: object) -> str:
        """
        Алиас для get(). Семантически означает «translate».

        Используй get() или tr() — по вкусу, они идентичны.
        tr() короче при частом использовании в UI-коде.
        """
        return self.get(key, default, *args)

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    @staticmethod
    def _safe_format(template: str, args: tuple[object, ...]) -> str:
        """
        Безопасно форматирует строку через str.format(*args).

        Если форматирование падает (например, шаблон не совпадает с args)
        — возвращает исходный шаблон без форматирования. Никогда не бросает.

        Параметры:
            template — строка-шаблон (может содержать {} или {0} и т.д.)
            args     — позиционные аргументы; если пусто — форматирование не применяется
        """
        if not args:
            return template
        try:
            return template.format(*args)
        except (IndexError, KeyError, ValueError) as e:
            logger.warning(f"_safe_format: ошибка форматирования {template!r} с {args!r}: {e}")
            return template

    def get_all_keys(self) -> list[str]:
        """
        Возвращает список всех зарегистрированных ключей перевода.
        Полезно при отладке для проверки полноты словарей.
        """
        return list(self._translations.keys())

    def has_key(self, key: str) -> bool:
        """
        Проверяет, зарегистрирован ли ключ перевода.

        Параметры:
            key — ключ для проверки

        Возвращает:
            True если ключ есть в словаре (не гарантирует наличие всех языков)
        """
        return key in self._translations

    def missing_translations(self) -> dict[str, list[str]]:
        """
        Находит ключи, для которых отсутствует перевод хотя бы на один язык.

        Возвращает:
            Словарь {ключ: [список языков без перевода]}.
            Пустой словарь если всё заполнено.

        Полезно при разработке для выявления «дыр» в локализации.
        """
        result: dict[str, list[str]] = {}
        for key, translations in self._translations.items():
            missing = [
                lang for lang in self.supported_languages
                if lang not in translations or not isinstance(translations[lang], str)
            ]
            if missing:
                result[key] = missing
        return result


# ============================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================

#: Глобальный синглтон локализации. Импортируй его напрямую:
#:     from locales.at_translations import loc
loc = Localization()


# ============================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================

if __name__ == "__main__":
    import pprint

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s")

    print("=== Тест at_translations.py ===\n")

    test_loc = Localization()
    print(f"Текущий язык: {test_loc.language!r}")
    print(f"Путь к конфигу: {Localization._LANGUAGE_CONFIG}")

    # Читаем user_language.json и выводим содержимое
    if os.path.isfile(Localization._LANGUAGE_CONFIG):
        with open(Localization._LANGUAGE_CONFIG, "r", encoding="utf-8") as _f:
            print("\nСодержимое user_language.json:")
            pprint.pprint(json.load(_f))
    else:
        print("\nФайл user_language.json не найден — используется fallback 'ru'")

    # Регистрируем тестовые переводы
    TEST_TRANSLATIONS = {
        "hello":       {"ru": "Привет, {}!", "en": "Hello, {}!", "de": "Hallo, {}!"},
        "save_error":  {"ru": "Ошибка сохранения", "en": "Save error"},  # de — отсутствует намеренно
        "ru_only":     {"ru": "Только русский"},
    }
    test_loc.register_translations(TEST_TRANSLATIONS)

    print(f"\nЗарегистрированные ключи: {test_loc.get_all_keys()}")

    # Тест get() с аргументом
    print("\n[Тест 1] get() с аргументом:")
    print(f"  ru: {test_loc.get('hello', 'Fallback', 'Мир')}")
    test_loc.set_language("en")
    print(f"  en: {test_loc.get('hello', 'Fallback', 'World')}")
    test_loc.set_language("de")
    print(f"  de: {test_loc.get('hello', 'Fallback', 'Welt')}")

    # Тест отсутствующего ключа
    print("\n[Тест 2] Несуществующий ключ → default:")
    print(f"  {test_loc.get('no_such_key', 'ключ не найден')!r}")

    # Тест has_key
    print("\n[Тест 3] has_key:")
    print(f"  'hello' → {test_loc.has_key('hello')}")
    print(f"  'ghost' → {test_loc.has_key('ghost')}")

    # Тест missing_translations
    print("\n[Тест 4] missing_translations:")
    pprint.pprint(test_loc.missing_translations())

    # Тест set_language с недопустимым значением
    print("\n[Тест 5] set_language с недопустимым значением:")
    ok = test_loc.set_language("fr")
    print(f"  set_language('fr') → {ok}, язык остался: {test_loc.language!r}")

    print("\n=== Тест завершён ===")