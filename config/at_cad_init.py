# config/at_cad_init.py
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

Описание:
Модуль для инициализации AutoCAD через COM (win32com). Проверяет подключение к AutoCAD,
ожидает готовность объектной модели (ActiveDocument/ModelSpace), автоматически создаёт
предопределённые слои и задаёт стиль текста через SetFont().
Реализует паттерн синглтон (однократная инициализация).
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
# Локальные переводы модуля
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
        "ru": "AutoCAD не готов к работе. Пожалуйста сначала запустите AutoCAD и подготовьте рабочее пространство.",
        "en": "AutoCAD is not ready. Please start AutoCAD first and prepare a workspace.",
        "de": "AutoCAD ist nicht bereit. Bitte starten Sie zuerst AutoCAD und bereiten Sie Ihren Arbeitsbereich vor."
    },
    "create_layer_error": {
        "ru": "Ошибка при создании слоёв: {0}",
        "en": "Error creating layers: {0}",
        "de": "Fehler beim Erstellen von Layern: {0}"
    },
    "layer_already_exists": {
        "ru": "Слой уже существует: {0}",
        "en": "Layer already exists: {0}",
        "de": "Layer existiert bereits: {0}"
    },
    "layer_created": {
        "ru": "Слой создан: {0}",
        "en": "Layer created: {0}",
        "de": "Layer erstellt: {0}"
    },
    "text_style_error": {
        "ru": "Ошибка установки шрифта: {0}",
        "en": "Error setting text font: {0}",
        "de": "Fehler beim Setzen der Schriftart: {0}"
    }
}
# Регистрируем переводы сразу при загрузке модуля (до любых вызовов loc.get)
loc.register_translations(TRANSLATIONS)

# -----------------------------
# Логирование (только в файл)
# -----------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "at_cad_init.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)


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
    def wait_for_autocad_ready(self, timeout: int = 20, interval: float = 0.5) -> bool:
        """
        Ожидает готовность AutoCAD (доступность ActiveDocument и его ModelSpace).

        Args:
            timeout (int): Максимальное время ожидания, сек.
            interval (float): Интервал между попытками, сек.

        Returns:
            bool: True, если AutoCAD готов, иначе False.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            pythoncom.PumpWaitingMessages()
            try:
                if self.acad:
                    # Проверяем доступ к ActiveDocument и ModelSpace.
                    doc = self.acad.ActiveDocument
                    _ = doc.ModelSpace  # сама попытка доступа отловит состояние "не готов"
                    return True
            except Exception:
                time.sleep(interval)
        return False

    def _create_layers(self) -> bool:
        """
        Создаёт предопределённые слои из LAYER_DATA, если их нет.

        Returns:
            bool: True при успехе, False при ошибке.
        """
        try:
            layers = self.adoc.Layers
            existing = {l.Name for l in layers}
            for layer in LAYER_DATA:
                name = layer["name"]
                if name in existing:
                    logging.info(loc.get("layer_already_exists").format(name))
                    continue

                new_layer = layers.Add(name)
                new_layer.Color = layer["color"]
                new_layer.Linetype = layer["linetype"]
                if "lineweight" in layer:
                    new_layer.Lineweight = int(layer["lineweight"] * 100)
                if "plot" in layer:
                    new_layer.Plottable = layer["plot"]
                logging.info(loc.get("layer_created").format(name))
            return True

        except Exception as e:
            logging.error(f"Create layers failed: {e}")
            show_popup(loc.get("create_layer_error").format(str(e)), popup_type="error")
            return False

    def _set_text_style(self, font_name: str, bold: bool = False, italic: bool = False) -> None:
        """
        Устанавливает TTF-шрифт для текущего текстового стиля документа.

        Args:
            font_name (str): Имя гарнитуры (Typeface), например 'ISOCPEUR'.
            bold (bool): Жирный.
            italic (bool): Курсив.

        Notes:
            Используется сигнатура: SetFont(Typeface, Bold, Italic, CharSet, PitchAndFamily).
            Для TTF обычно достаточно CharSet=0 (ANSI), PitchAndFamily=0.
        """
        try:
            # Текущий стиль (как правило, 'Standard' существует всегда)
            style = self.adoc.ActiveTextStyle
            # SetFont(Typeface, Bold, Italic, CharSet, PitchAndFamily)
            style.SetFont(font_name, bool(bold), bool(italic), 0, 0)
            logging.info(f"Text style set: {font_name}, bold={bold}, italic={italic}")
        except Exception as e:
            logging.error(f"Set text style failed: {e}")
            show_popup(loc.get("text_style_error").format(str(e)), popup_type="error")

    # -----------------------------
    # Основная инициализация
    # -----------------------------
    def _initialize(self) -> None:
        """
        Пытается подключиться к уже запущенному AutoCAD.
        Если AutoCAD не запущен – выводит сообщение и завершает работу без ошибок.
        """
        try:
            # Пробуем подключиться к существующему процессу AutoCAD
            try:
                self.acad = win32com.client.GetActiveObject("AutoCAD.Application")
            except Exception:
                show_popup(loc.get("cad_not_ready"), popup_type="error")
                logging.info("AutoCAD is not running. Please start AutoCAD first.")
                self.acad = None
                self.adoc = None
                self.model = None
                self.original_layer = None
                return

            # Проверяем готовность объектной модели
            if not self.wait_for_autocad_ready(timeout=10, interval=0.5):
                show_popup(loc.get("cad_not_ready"), popup_type="error")
                logging.warning("AutoCAD not ready (ActiveDocument/ModelSpace unavailable).")
                self.acad = None
                self.adoc = None
                self.model = None
                self.original_layer = None
                return

            # Получаем объекты документа
            self.adoc = self.acad.ActiveDocument
            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer

            # Создание предопределённых слоёв
            self._create_layers()

            # Установка шрифта текстового стиля
            self._set_text_style(TEXT_FONT, bold=TEXT_BOLD, italic=TEXT_ITAL)

            # Устанавливаем активным слой "0"
            self.adoc.ActiveLayer = self.adoc.Layers.Item("0")

            logging.info("AutoCAD initialized successfully")

        except Exception as e:
            logging.error(f"Initialization failed: {e}")
            show_popup(loc.get("cad_init_error_short") + f" {e}", popup_type="error")
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None

    # -----------------------------
    # Служебные методы
    # -----------------------------
    def is_initialized(self) -> bool:
        """Проверяет, успешно ли инициализирован AutoCAD."""
        return self.acad is not None and self.adoc is not None and self.model is not None


if __name__ == "__main__":
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(loc.get("cad_init_error_short"), popup_type="error")
    else:
        show_popup(loc.get("cad_init_success"), popup_type="success")
