# config/at_cad_init.py
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

Описание:
Модуль для инициализации AutoCAD через COM (win32com). Проверяет подключение к AutoCAD,
автоматически создаёт предопределённые слои и задаёт стиль текста.
"""

import os
import time
import logging
import pythoncom
import win32com.client
from locales.at_translations import loc
from windows.at_gui_utils import show_popup
from config.at_config import LAYER_DATA, TEXT_FONT, TEXT_BOLD, TEXT_ITAL

# -----------------------------
# Настройка логирования (только в файл, без раздражающих popup)
# -----------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "config/at_cad_init.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

# -----------------------------
# Переводы для этого модуля
# -----------------------------
TRANSLATIONS = {
    "cad_init_error_short": {
        "ru": "Ошибка инициализации AutoCAD.",
        "en": "AutoCAD initialization error.",
        "de": "Fehler bei der AutoCAD-Initialisierung."
    },
    "cad_init_success": {
        "ru": "AutoCAD успешно инициализирован.",
        "en": "AutoCAD initialized successfully.",
        "de": "AutoCAD erfolgreich initialisiert."
    },
    "cad_not_ready": {
        "ru": "AutoCAD не готов к работе.",
        "en": "AutoCAD NOT READY.",
        "de": "Fehler bei der AutoCAD-Not-Ready."
    },
    "create_layer_error": {
        "ru": "Ошибка при создании слоёв: {0}",
        "en": "Error creating layers: {0}",
        "de": "Fehler beim Erstellen von Layern: {0}"
    },
    "layer_created": {
        "ru": "Слой '{0}' создан.",
        "en": "Layer '{0}' created.",
        "de": "Layer '{0}' erstellt."
    },
    "text_style_error": {
        "ru": "Ошибка установки шрифта: {0}",
        "en": "Error setting text font: {0}",
        "de": "Fehler beim Setzen der Schriftart: {0}"
    }
}

# Регистрируем переводы один раз при загрузке модуля
loc.register_translations(TRANSLATIONS)


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

    # -----------------------------
    # Вспомогательные методы
    # -----------------------------
    def wait_for_autocad_ready(self, timeout: int = 20) -> bool:
        """
        Ожидает готовность AutoCAD (доступность ActiveDocument).

        Args:
            timeout (int): максимальное время ожидания в секундах.

        Returns:
            bool: True, если AutoCAD готов, иначе False.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            pythoncom.PumpWaitingMessages()
            try:
                if self.acad and self.acad.ActiveDocument:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def _create_layers(self) -> bool:
        """Создаёт предопределённые слои в AutoCAD, если их нет."""
        try:
            layers = self.adoc.Layers
            existing_names = [l.Name for l in layers]
            for layer in LAYER_DATA:
                name = layer["name"]
                if name in existing_names:
                    logging.info(f"Слой уже существует: {name}")
                    continue

                new_layer = layers.Add(name)
                new_layer.Color = layer["color"]
                new_layer.Linetype = layer["linetype"]
                if "lineweight" in layer:
                    new_layer.Lineweight = int(layer["lineweight"] * 100)
                if "plot" in layer:
                    new_layer.Plottable = layer["plot"]
                logging.info(f"Создан слой: {name}")
            return True
        except Exception as e:
            logging.error(f"Ошибка создания слоёв: {e}")
            show_popup(loc.get("create_layer_error", f"Ошибка создания слоёв: {e}"), "error")
            return False

    def _set_text_style(self, font_name: str, bold: bool = False, italic: bool = False):
        """
        Устанавливает стиль текста для текущего документа.
        """
        try:
            styles = self.adoc.TextStyles
            style = styles.Item("Standard")
            # SetFont(Typeface, Bold, Italic, CharSet, PitchAndFamily)
            style.SetFont(font_name, bold, italic, 1, 0)
        except Exception as e:
            show_popup(
                loc.get("text_style_error").format(str(e)),
                popup_type="error"
            )


    # -----------------------------
    # Основная инициализация
    # -----------------------------
    def _initialize(self):
        try:
            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True

            # Ждём готовности AutoCAD
            if not self.wait_for_autocad_ready():
                raise Exception(loc.get("cad_not_ready", "AutoCAD не готов к работе."))

            self.adoc = self.acad.ActiveDocument
            if self.adoc is None:
                raise Exception(loc.get("cad_init_error_short"))

            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer

            # Создание предопределённых слоёв
            if not self._create_layers():
                raise Exception(loc.get("create_layer_error", "Ошибка при создании слоёв."))

            # Установка стиля текста
            self._set_text_style(TEXT_FONT, bold=TEXT_BOLD, italic=TEXT_ITAL)

            # Установка активным слоя 0
            self.adoc.ActiveLayer = self.adoc.Layers.Item("0")

            logging.info("AutoCAD успешно инициализирован")

        except Exception as e:
            logging.error(f"Ошибка инициализации AutoCAD: {e}")
            show_popup(
                loc.get("cad_init_error_short") + f" {e}",
                popup_type="error"
            )
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None

    # -----------------------------
    # Служебные методы
    # -----------------------------
    def is_initialized(self):
        """Проверяет, успешно ли инициализирован AutoCAD."""
        return self.acad is not None and self.adoc is not None and self.model is not None


if __name__ == "__main__":
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(
            loc.get("cad_init_error_short"),
            popup_type="error"
        )
    else:
        show_popup(
            loc.get("cad_init_success"),
            popup_type="success"
        )
