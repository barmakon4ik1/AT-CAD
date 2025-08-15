# config/at_cad_init.py
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

Описание:
Модуль для инициализации AutoCAD через COM (win32com).
Проверяет подключение к AutoCAD, автоматически создаёт предопределённые слои
и устанавливает TTF-шрифт для текущего стиля текста.
Реализует синглтон для однократной инициализации.
"""

import math
import win32com.client
from locales.at_translations import loc
from windows.at_gui_utils import show_popup
from config.at_config import LAYER_DATA

# Локальный словарь переводов для модуля at_cad_init
TRANSLATIONS = {
    # Ошибка инициализации AutoCAD
    "cad_init_error_short": {
        "ru": "Ошибка инициализации AutoCAD.",
        "de": "Fehler bei der Initialisierung von AutoCAD.",
        "en": "AutoCAD initialization error."
    },
    # Ошибка создания предопределённых слоёв
    "create_layer_error": {
        "ru": "Не удалось создать предопределённые слои.",
        "de": "Fehler beim Erstellen vordefinierter Layer.",
        "en": "Failed to create predefined layers."
    },
    # Ошибка установки шрифта для текстового стиля
    "text_style_error": {
        "ru": "Ошибка установки шрифта: {0}",
        "de": "Fehler beim Setzen der Schriftart: {0}",
        "en": "Error setting font: {0}"
    },
    # Успешная инициализация AutoCAD (для тестового запуска)
    "cad_init_success": {
        "ru": "AutoCAD успешно инициализирован.",
        "de": "AutoCAD erfolgreich initialisiert.",
        "en": "AutoCAD successfully initialized."
    }
}

class ATCadInit:
    """
    Класс для инициализации и управления подключением к AutoCAD через COM.
    Реализует паттерн синглтон для однократной инициализации.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ATCadInit, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def __init__(self):
        """
        Регистрирует локальные переводы модуля в глобальном обработчике локализации.
        """
        loc.register_translations(TRANSLATIONS)

    def _msg(self, key: str, default_ru: str, *args) -> str:
        """
        Получает строку из словаря перевода или возвращает русский текст по умолчанию.
        Поддерживает форматирование строк с аргументами.

        Аргументы:
            key (str): Ключ перевода.
            default_ru (str): Русский текст по умолчанию.
            *args: Аргументы для форматирования строки.

        Возвращает:
            str: Переведённая строка или текст по умолчанию.
        """
        return loc.get(key, default_ru, *args)

    def _initialize(self):
        """
        Выполняет подключение к AutoCAD через COM, создаёт предопределённые слои
        и настраивает шрифт текущего стиля текста.
        """
        try:
            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True
            self.adoc = self.acad.ActiveDocument
            if self.adoc is None:
                raise Exception(self._msg("cad_init_error_short", "Ошибка инициализации AutoCAD."))
            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer
            # Установка масштаба линий
            self.adoc.SetVariable("LTSCALE", 10)
            self.adoc.SetVariable("MSLTSCALE", 1)
            self.adoc.SetVariable("PSLTSCALE", 1)
            self.adoc.SetVariable("CANNOSCALE", "1:10")
            self.adoc.SetVariable("DIMSCALE", 10)

            if not self._create_layers():
                raise Exception(self._msg("create_layer_error", "Не удалось создать предопределённые слои."))

            self._set_current_text_font()

        except Exception as e:
            show_popup(
                self._msg("cad_init_error_short", f"Ошибка инициализации AutoCAD: {0}", str(e)),
                popup_type="error"
            )
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None

    def is_initialized(self):
        """
        Проверяет, успешно ли инициализирован AutoCAD.

        Возвращает:
            bool: True, если AutoCAD инициализирован, иначе False.
        """
        return self.acad is not None and self.adoc is not None and self.model is not None

    def _create_layers(self) -> bool:
        """
        Создает предопределенные слои в AutoCAD с заданными параметрами.

        Возвращает:
            bool: True, если слои успешно созданы, иначе False.
        """
        try:
            layers = self.adoc.Layers
            for layer in LAYER_DATA:
                layer_name = layer["name"]
                if layer_name not in [l.Name for l in layers]:
                    new_layer = layers.Add(layer_name)
                    new_layer.Color = layer["color"]
                    new_layer.Linetype = layer["linetype"]
                    if "lineweight" in layer:
                        new_layer.Lineweight = int(layer["lineweight"] * 100)
                    if "plot" in layer:
                        new_layer.Plottable = layer["plot"]
            return True
        except Exception as e:
            show_popup(
                self._msg("create_layer_error", f"Ошибка при создании слоёв: {0}", str(e)),
                popup_type="error"
            )
            return False

    def _set_current_text_font(self) -> bool:
        """
        Устанавливает для текущего стиля текста TTF-шрифт ISOCPEUR и курсив.
        Работает через коллекцию TextStyles, что поддерживается в AutoCAD Mechanical DE.

        Возвращает:
            bool: True, если шрифт успешно установлен, иначе False.
        """
        try:
            font_name = "ISOCPEUR"  # имя шрифта (TTF)
            current_style_name = self.adoc.ActiveTextStyle.Name
            style = self.adoc.TextStyles.Item(current_style_name)

            try:
                # Предпочтительный способ для TTF
                style.SetFont(font_name, False, True, 0, 0)
            except Exception as e:
                raise Exception(self._msg("text_style_error", f"Не удалось применить SetFont: {0}", str(e)))

            return True
        except Exception as e:
            show_popup(
                self._msg("text_style_error", f"Ошибка установки шрифта: {0}", str(e)),
                popup_type="error"
            )
            return False


if __name__ == "__main__":
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(
            cad._msg("cad_init_error_short", "Ошибка инициализации AutoCAD."),
            popup_type="error"
        )
    else:
        show_popup(
            cad._msg("cad_init_success", "AutoCAD успешно инициализирован."),
            popup_type="success"
        )
