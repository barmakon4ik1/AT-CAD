# -*- coding: utf-8 -*-
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

НАДЁЖНАЯ ИНИЦИАЛИЗАЦИЯ AutoCAD через COM (win32com)

Особенности:
✔ Singleton
✔ Поддержка RPC_E_CALL_REJECTED через собственную COMRetryWrapper
✔ Ожидание появления документа и завершения команд (CMDACTIVE=0)
✔ Безопасные вызовы COM через safe_call
✔ Удобная работа с ModelSpace и слоями
✔ Не конвертирует точки в VARIANT автоматически — используем списки координат
"""

import os
import time
import logging
from contextlib import contextmanager
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

DOC_WAIT_TIMEOUT = 15      # время ожидания документа
IDLE_WAIT_TIMEOUT = 10     # время ожидания окончания команд
RETRY_DELAY = 0.1          # задержка между попытками COM
RPC_E_CALL_REJECTED = -2147418111  # HRESULT для RPC_E_CALL_REJECTED

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
# COM RETRY WRAPPER
# ============================================================

class COMRetryWrapper:
    """
    Безопасная обёртка COM:

    ✔ retry при RPC_E_CALL_REJECTED
    ✔ корректно работает с COM свойствами и методами
    ✔ НЕ использует callable() (это важно!)
    """

    def __init__(self, com_obj):
        self._com_obj = com_obj

    def __getattr__(self, item):
        """
        Ленивый доступ к COM:

        ВАЖНО:
        - сначала пробуем получить значение
        - если это метод — возвращаем callable wrapper
        - если это COM объект — оборачиваем
        """

        def getter():
            return getattr(self._com_obj, item)

        value = self._retry(getter)

        # Если это COM объект — оборачиваем
        if hasattr(value, "_oleobj_"):
            return COMRetryWrapper(value)

        # Если это вызываемый объект (метод)
        if callable(value):
            def method(*args, **kwargs):
                return self._retry(lambda: value(*args, **kwargs))
            return method

        # обычное значение
        return value

    def _retry(self, func, retries: int = 50, delay: float = RETRY_DELAY):
        for _ in range(retries):
            try:
                pythoncom.PumpWaitingMessages()
                return func()

            except pythoncom.com_error as e:
                if e.hresult == RPC_E_CALL_REJECTED:
                    time.sleep(delay)
                    continue
                raise

        raise TimeoutError("COM retry timeout")

# ============================================================
# ATCADINIT
# ============================================================

class ATCadInit:
    """
    Singleton для инициализации AutoCAD через COM.

    Использует COMRetryWrapper для автоматического ретрая вызовов,
    безопасный доступ к ActiveDocument и ModelSpace.
    """

    _instance: Optional["ATCadInit"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def safe_call(self,
                  func: Callable,
                  default: Any = None,
                  log: bool = True) -> Any:
        """
        Упрощённый safe_call:

        ✔ БЕЗ retry (его делает COMRetryWrapper)
        ✔ Только защита и логирование
        ✔ Используется как безопасный guard

        ВАЖНО:
        func должен быть ЛЯМБДОЙ:
            lambda: self.adoc.ModelSpace
        """

        try:
            return func()

        except Exception as e:
            if log:
                logging.error(f"COM safe_call error: {e}")
            return default

    def _wait_for_document(self) -> bool:
        """
        Ожидаем появления документа.

        Учитываем:
        ✔ Documents.Count
        ✔ ActiveDocument fallback
        """

        start = time.time()

        while time.time() - start < DOC_WAIT_TIMEOUT:
            try:
                # основной путь
                if self.acad.Documents.Count > 0:
                    return True
            except Exception:
                pass

            # fallback
            try:
                doc = self.acad.ActiveDocument
                if doc:
                    return True
            except Exception:
                pass

            time.sleep(0.2)

        return False

    def _wait_idle(self) -> bool:
        """
        Ожидание окончания команд (CMDACTIVE=0)
        """

        start = time.time()

        while time.time() - start < IDLE_WAIT_TIMEOUT:
            cmd_active = self.safe_call(
                lambda: self.adoc.GetVariable("CMDACTIVE"),
                default=1
            )

            if cmd_active == 0:
                return True

            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)

        return False

    def _ensure_model_space(self):
        """Переключение в ModelSpace."""
        try:
            if self.adoc.ActiveSpace != 1:
                self.adoc.ActiveSpace = 1
                time.sleep(0.05)
        except Exception as e:
            logging.warning(f"Не удалось переключиться в ModelSpace: {e}")

    def unwrap(self, obj):
        """Возвращает сырой COM-объект. Это нужно для, например, информации о геометрии"""
        if hasattr(obj, "_com_obj"):
            return obj._com_obj
        return obj

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _initialize(self) -> None:
        """
        Инициализация AutoCAD через COM.

        ✔ Только подключение к существующему экземпляру
        ❌ НЕ запускает AutoCAD
        """

        self.acad = None
        self.adoc = None
        self.model = False
        self.original_layer = None

        # --------------------------------------------------------
        # ТОЛЬКО GetActiveObject
        # --------------------------------------------------------
        try:
            raw = win32com.client.GetActiveObject("AutoCAD.Application")
            self.acad = COMRetryWrapper(raw)

            logging.info("Подключено к запущенному AutoCAD")

        except Exception:
            logging.warning(loc.get("cad_not_ready"))
            return

        # --------------------------------------------------------
        # ДАЛЬШЕ КАК БЫЛО
        # --------------------------------------------------------
        if not self._wait_for_document():
            logging.warning(loc.get("no_documents"))
            return

        try:
            self.adoc = self.acad.ActiveDocument
        except Exception as e:
            logging.error(f"ActiveDocument error: {e}")
            return

        if not self._wait_idle():
            logging.warning(loc.get("cad_not_ready"))
            return

        self.model = True

        try:
            self.original_layer = self.adoc.ActiveLayer
        except Exception:
            self.original_layer = None

        self._post_init_document()
        logging.info(loc.get("cad_init_success"))

    # =========================================================
    # ДОКУМЕНТ
    # =========================================================

    def refresh_active_document(self) -> bool:
        """Обновление ActiveDocument, если пользователь сменил документ."""
        if not self.acad:
            return False

        current_doc = self.safe_call(lambda: self.acad.ActiveDocument)
        if not current_doc:
            self.adoc = None
            self.model = False
            return False

        changed = self.adoc != current_doc
        if changed:
            self.adoc = current_doc
            self.original_layer = self.safe_call(lambda: self.adoc.ActiveLayer)
            logging.info(f"Активный документ: {self.adoc.Name}")
            self._post_init_document()
        return True

    # =========================================================
    # ЛОГИКА СЛОЕВ
    # =========================================================

    def _create_layers(self) -> bool:
        """Создание слоёв из конфигурации LAYER_DATA."""
        try:
            layers = self.adoc.Layers
            for layer in LAYER_DATA:
                name = layer["name"]

                existing = self.safe_call(lambda: layers.Item(name), default=None)

                if existing:
                    continue

                new_layer = layers.Add(name)
                # Установка цвета через TrueColor (устойчиво)
                color_value = layer["color"]

                color = new_layer.TrueColor
                color.SetRGB(color_value, color_value, color_value)

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
        """Установка шрифта ActiveTextStyle."""
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
    # POST-INIT
    # =========================================================

    def _post_init_document(self):
        """Применение конфигурации документа: слои, шрифт, восстановление слоя '0'."""
        try:
            self._wait_idle()
            self._create_layers()
            self._set_text_style(TEXT_FONT, TEXT_BOLD, TEXT_ITAL)
            # вернуть слой "0"
            layer0 = self.safe_call(lambda: self.adoc.Layers.Item("0"))
            if layer0:
                self.safe_call(lambda: setattr(self.adoc, "ActiveLayer", layer0))
        except Exception as e:
            logging.error(f"Post init error: {e}")

    # =========================================================
    # API
    # =========================================================

    @property
    def application(self):
        return self.acad if self.is_initialized() else None

    @property
    def document(self):
        return self.adoc if self.is_initialized() else None

    @property
    def model_space(self):
        if not self.acad or not self.refresh_active_document():
            return None
        self._ensure_model_space()
        return self.safe_call(lambda: self.adoc.ModelSpace)

    def is_initialized(self) -> bool:
        return self.acad is not None and self.adoc is not None

    def restore_original_layer(self):
        if self.original_layer and self.adoc:
            self.adoc.ActiveLayer = self.original_layer

    @contextmanager
    def cad_transaction(self, layer: Optional[str] = None, regen: bool = True):
        """
        Контекст безопасной работы с AutoCAD:
        - Переключает слой (если задан)
        - Возвращает исходный слой
        - Делает regen по завершению
        """
        if not self.is_initialized():
            yield
            return

        self.refresh_active_document()
        prev_layer = self.safe_call(lambda: self.adoc.ActiveLayer)

        try:
            if layer:
                if not self.safe_call(lambda: self.adoc.Layers.Item(layer)):
                    self._create_layers()
                try:
                    self.adoc.ActiveLayer = self.adoc.Layers.Item(layer)
                except Exception as e:
                    logging.warning(f"Layer switch failed: {e}")
            yield
        finally:
            if prev_layer:
                try:
                    self.adoc.ActiveLayer = prev_layer
                except Exception:
                    pass
            if regen:
                try:
                    self.adoc.Regen(0)
                except Exception:
                    pass

    def safe_add(self, func: Callable, *args) -> Optional[Any]:
        """Безопасное создание объектов в ModelSpace."""
        if not self.is_initialized():
            return None
        model = self.model_space
        if not model:
            return None
        return self.safe_call(lambda: func(model, *args))

    def regen_doc(self, mode: int = 0):
        """Принудительная регенерация документа."""
        if not self.is_initialized():
            return
        try:
            self.adoc.Regen(mode)
            logging.info("Регенерация документа успешна")
        except Exception as e:
            logging.error(f"Регенерация провалена: {e}")

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