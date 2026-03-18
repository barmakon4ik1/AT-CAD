# -*- coding: utf-8 -*-
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

НАДЁЖНАЯ ИНИЦИАЛИЗАЦИЯ AutoCAD через COM (win32com)

✔ Сохранена локализация
✔ Без управления фокусом окна
✔ Устойчива к RPC_E_CALL_REJECTED
✔ Ожидает появления ActiveDocument
✔ Ожидает завершения команд (CMDACTIVE = 0)
✔ Работает в GUI-приложениях (wxPython)
✔ Singleton
"""

import os
import time
import logging
from typing import Optional, Callable, Any

import pythoncom
import win32com.client

from locales.at_translations import loc
from windows.at_gui_utils import show_popup
from config.at_config import LAYER_DATA, TEXT_FONT, TEXT_BOLD, TEXT_ITAL


# ============================================================
# ЛОКАЛИЗАЦИЯ
# ============================================================

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
        "en": "AutoCAD is not ready.",
        "de": "AutoCAD ist nicht bereit."
    },
    "create_layer_error": {
        "ru": "Ошибка при создании слоёв: {error}",
        "en": "Error creating layers: {error}",
        "de": "Fehler beim Erstellen von Layern: {error}"
    },
    "text_style_error": {
        "ru": "Ошибка установки шрифта: {error}",
        "en": "Error setting text font: {error}",
        "de": "Fehler beim Setzen der Schriftart: {error}"
    },
    "no_documents": {
        "ru": "Нет открытых документов AutoCAD.",
        "en": "No open AutoCAD documents.",
        "de": "Keine geöffneten AutoCAD-Dokumente."
    }
}

loc.register_translations(TRANSLATIONS)


# ============================================================
# КОНСТАНТЫ
# ============================================================

RPC_E_CALL_REJECTED = -2147418111

DOC_WAIT_TIMEOUT = 15
IDLE_WAIT_TIMEOUT = 10
RETRY_DELAY = 0.1


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "at_cad_init.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)


# ============================================================
# КЛАСС ИНИЦИАЛИЗАЦИИ
# ============================================================

class ATCadInit:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    # =========================================================
    # COM RETRY
    # =========================================================

    def _com_retry(self, func: Callable, *args,
                   retries: int = 50,
                   delay: float = RETRY_DELAY) -> Any:

        for _ in range(retries):
            try:
                pythoncom.PumpWaitingMessages()
                return func(*args)

            except pythoncom.com_error as e:
                if e.hresult == RPC_E_CALL_REJECTED:
                    time.sleep(delay)
                    continue
                raise

        raise TimeoutError("COM call rejected too many times")

    # =========================================================

    def _wait_for_document(self) -> bool:

        start = time.time()

        while time.time() - start < DOC_WAIT_TIMEOUT:
            try:
                if self.acad.Documents.Count > 0:
                    return True
            except pythoncom.com_error:
                pass

            time.sleep(0.2)

        return False

    # =========================================================

    def _wait_idle(self) -> bool:

        start = time.time()

        while time.time() - start < IDLE_WAIT_TIMEOUT:
            try:
                doc = self.acad.ActiveDocument
                if doc.GetVariable("CMDACTIVE") == 0:
                    return True
            except pythoncom.com_error:
                pass

            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)

        return False

    # =========================================================
    # ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _initialize(self) -> None:

        self.acad = None
        self.adoc = None
        self.model = None
        self.original_layer = None

        # Подключение к AutoCAD
        try:
            self.acad = win32com.client.GetActiveObject("AutoCAD.Application")
            logging.info(f"AutoCAD version: {self.acad.Version}")

        except Exception:
            logging.warning(loc.get("cad_not_ready"))
            return

        # Ожидание документа
        if not self._wait_for_document():
            logging.warning(loc.get("no_documents"))
            return

        # Получение ActiveDocument
        try:
            self.adoc = self._com_retry(lambda: self.acad.ActiveDocument)
        except Exception as e:
            logging.error(f"ActiveDocument error: {e}")
            return

        # Ожидание idle
        if not self._wait_idle():
            logging.warning(loc.get("cad_not_ready"))
            return

        # ModelSpace
        try:
            self.model = self._com_retry(lambda: self.adoc.ModelSpace)
            self.original_layer = self._com_retry(
                lambda: self.adoc.ActiveLayer
            )
        except Exception as e:
            logging.error(f"ModelSpace error: {e}")
            return

        # Настройка документа
        self._create_layers()
        self._set_text_style(TEXT_FONT, TEXT_BOLD, TEXT_ITAL)

        try:
            self.adoc.ActiveLayer = self.adoc.Layers.Item("0")
        except Exception:
            pass

        logging.info(loc.get("cad_init_success"))

    # =========================================================
    # ОБНОВЛЕНИЕ ДОКУМЕНТА
    # =========================================================

    def refresh_active_document(self) -> bool:

        if not self.acad:
            return False

        try:
            current_doc = self._com_retry(lambda: self.acad.ActiveDocument)
        except Exception:
            self.adoc = None
            self.model = None
            return False

        if self.adoc != current_doc:
            self.adoc = current_doc

            try:
                self.model = self._com_retry(
                    lambda: self.adoc.ModelSpace
                )
            except Exception:
                self.model = None

            try:
                self.original_layer = self.adoc.ActiveLayer
            except Exception:
                self.original_layer = None

            logging.info(f"Активный документ: {self.adoc.Name}")

        return True

    # =========================================================
    # СОЗДАНИЕ СЛОЁВ
    # =========================================================

    def _create_layers(self) -> bool:

        try:
            layers = self.adoc.Layers

            for layer in LAYER_DATA:
                name = layer["name"]

                try:
                    layers.Item(name)
                    continue
                except Exception:
                    new_layer = layers.Add(name)

                new_layer.Color = layer["color"]
                new_layer.Linetype = layer["linetype"]

                if "lineweight" in layer:
                    new_layer.Lineweight = int(layer["lineweight"] * 100)

                if "plot" in layer:
                    new_layer.Plottable = layer["plot"]

            return True

        except Exception as e:
            logging.error(str(e))
            show_popup(
                loc.get("create_layer_error").format(error=str(e)),
                popup_type="error"
            )
            return False

    # =========================================================
    # ШРИФТ
    # =========================================================

    def _set_text_style(self, font_name: str,
                        bold: bool = False,
                        italic: bool = False) -> None:

        try:
            style = self.adoc.ActiveTextStyle
            style.SetFont(font_name, bool(bold), bool(italic), 0, 0)

        except Exception as e:
            logging.error(str(e))
            show_popup(
                loc.get("text_style_error").format(error=str(e)),
                popup_type="error"
            )

    # =========================================================

    def restore_original_layer(self):

        if self.original_layer and self.adoc:
            self.adoc.ActiveLayer = self.original_layer

    # =========================================================

    def is_initialized(self) -> bool:

        return (
            self.acad is not None and
            self.adoc is not None and
            self.model is not None
        )

    def regen_doc(self, mode: int = 0):
        """
        Принудительная регенерация документа.

        Args:
            mode (int): 0=AllViewports, 1=Current, etc.
        """
        if not self.is_initialized():
            return

        try:
            self.adoc.Regen(mode)
            logging.info("Регенерация документа успешна")
        except Exception as e:
            logging.error(f"Регенерация провалена: {e}")

    # =========================================================
    # ПУБЛИЧНЫЙ API
    # =========================================================

    @property
    def application(self):
        return self.acad if self.is_initialized() else None

    @property
    def document(self):
        return self.adoc if self.is_initialized() else None

    @property
    def model_space(self):

        if not self.acad:
            return None

        self.refresh_active_document()
        return self.model if self.is_initialized() else None


# ============================================================
# ТЕСТ
# ============================================================

if __name__ == "__main__":

    import wx

    app = wx.App(False)

    cad = ATCadInit()

    if not cad.is_initialized():
        show_popup(loc.get("cad_init_error_short"), popup_type="error")
    else:
        show_popup(loc.get("cad_init_success"), popup_type="success")

    app.MainLoop()