# locales/at_localization_manager.py
"""
Модуль для управления записями локализации: добавление, редактирование, удаление.
Поддерживает интерактивный и программный режимы.

Методы add_translation, edit_translation, delete_translation можно использовать в коде.
Пример использования:
manager = LocalizationManager()
manager.add_translation("new_key", {"ru": "Новый текст", "de": "Neuer Text", "en": "New Text"})
manager.edit_translation("new_key", {"ru": "Изменённый текст", "de": "Geänderter Text", "en": "Edited Text"})
manager.delete_translation("new_key")
"""

import json
import logging
from typing import Dict
from pathlib import Path
from locales.at_localization import translations
from locales.at_localization_class import Localization  # Обновлённый импорт

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class LocalizationManager:
    """
    Класс для управления записями локализации.
    """

    def __init__(self, localization_file: str = "locales/at_localization.py"):
        """
        Инициализирует менеджер локализации.

        Args:
            localization_file: Путь к файлу локализации (содержит только translations).
        """
        # Формируем абсолютный путь относительно корня проекта
        self.project_root = Path(__file__).parent.parent
        self.localization_file = self.project_root / localization_file
        self.translations = translations
        self.valid_languages = {"ru", "de", "en"}
        logging.info(f"LocalizationManager initialized with file: {self.localization_file}")

    def add_translation(self, key: str, translations_dict: Dict[str, str]) -> bool:
        """
        Добавляет новую запись перевода.
        """
        if key in self.translations:
            logging.error(f"Translation key '{key}' already exists")
            return False

        if not all(lang in self.valid_languages for lang in translations_dict):
            logging.error(f"Invalid language in translations: {translations_dict}")
            return False

        self.translations[key] = translations_dict
        self._save_to_file()
        logging.info(f"Added translation for key '{key}': {translations_dict}")
        return True

    def edit_translation(self, key: str, translations_dict: Dict[str, str]) -> bool:
        """
        Редактирует существующую запись перевода.
        """
        if key not in self.translations:
            logging.error(f"Translation key '{key}' not found")
            return False

        if not all(lang in self.valid_languages for lang in translations_dict):
            logging.error(f"Invalid language in translations: {translations_dict}")
            return False

        self.translations[key] = translations_dict
        self._save_to_file()
        logging.info(f"Edited translation for key '{key}': {translations_dict}")
        return True

    def delete_translation(self, key: str) -> bool:
        """
        Удаляет запись перевода.
        """
        if key not in self.translations:
            logging.error(f"Translation key '{key}' not found")
            return False

        del self.translations[key]
        self._save_to_file()
        logging.info(f"Deleted translation for key '{key}'")
        return True

    def _save_to_file(self) -> None:
        """
        Сохраняет словарь переводов в файл локализации.
        """
        try:
            # Убедимся, что директория существует
            self.localization_file.parent.mkdir(parents=True, exist_ok=True)

            # Формируем содержимое файла
            content = (
                '"""\n'
                'Модуль для хранения словаря переводов.\n'
                'Поддерживает переводы на русский, немецкий и английский языки.\n'
                '"""\n\n'
                f'translations = {json.dumps(self.translations, indent=4, ensure_ascii=False)}\n'
            )

            # Записываем файл
            with open(self.localization_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Localization file saved successfully: {self.localization_file}")
        except Exception as e:
            logging.error(f"Error saving localization file: {e}")
            raise

    def interactive_mode(self) -> None:
        """
        Запускает интерактивный режим для управления локализацией.
        """
        while True:
            print("\nМенеджер локализации")
            print("1. Добавить перевод")
            print("2. Редактировать перевод")
            print("3. Удалить перевод")
            print("4. Выход")
            choice = input("Выберите действие (1-4): ")

            if choice == "1":
                key = input("Введите ключ перевода: ")
                if key in self.translations:
                    print(f"Ключ '{key}' уже существует!")
                    continue

                translations_dict = {}
                for lang in self.valid_languages:
                    text = input(f"Введите перевод для {lang} (например, 'ru' для русского): ")
                    translations_dict[lang] = text

                if self.add_translation(key, translations_dict):
                    print(f"Перевод для ключа '{key}' успешно добавлен.")
                else:
                    print("Ошибка при добавлении перевода.")

            elif choice == "2":
                key = input("Введите ключ перевода для редактирования: ")
                if key not in self.translations:
                    print(f"Ключ '{key}' не найден!")
                    continue

                print(f"Текущие переводы: {self.translations[key]}")
                translations_dict = {}
                for lang in self.valid_languages:
                    text = input(f"Введите новый перевод для {lang} (оставьте пустым для сохранения текущего): ")
                    translations_dict[lang] = text if text else self.translations[key][lang]

                if self.edit_translation(key, translations_dict):
                    print(f"Перевод для ключа '{key}' успешно отредактирован.")
                else:
                    print("Ошибка при редактировании перевода.")

            elif choice == "3":
                key = input("Введите ключ перевода для удаления: ")
                if self.delete_translation(key):
                    print(f"Перевод для ключа '{key}' успешно удалён.")
                else:
                    print(f"Ключ '{key}' не найден.")

            elif choice == "4":
                print("Выход из менеджера локализации.")
                break

            else:
                print("Неверный выбор, попробуйте снова.")


if __name__ == "__main__":
    manager = LocalizationManager()
    manager.interactive_mode()
