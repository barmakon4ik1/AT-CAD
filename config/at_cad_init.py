# -*- coding: utf-8 -*-
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

Описание:
Модуль для инициализации AutoCAD через COM (win32com). Проверяет подключение к AutoCAD,
ожидает готовность объектной модели (ActiveDocument/ModelSpace), автоматически создаёт
предопределённые слои и задаёт стиль текста через SetFont().
Реализует паттерн синглтон (однократная инициализация).
Внедрена логика синхронизации (фокус, retry COM, реген) для стабильности операций.
"""

import os
import time
import logging  # ← Уже есть
from typing import Optional, Callable, Any  # ← Добавлено Any для retry

import pythoncom
import win32com.client
import wx  # ← ДОБАВЛЕНО: для Yield в sync

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
        "ru": "Ошибка при создании слоёв: {error}",
        "en": "Error creating layers: {error}",
        "de": "Fehler beim Erstellen von Layern: {error}"
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
        "ru": "Ошибка установки шрифта: {error}",
        "en": "Error setting text font: {error}",
        "de": "Fehler beim Setzen der Schriftart: {error}"
    },
    "sync_success": {  # ← ДОБАВЛЕНО: для логов
        "ru": "Синхронизация фокуса успешна",
        "en": "Focus sync successful",
        "de": "Fokus-Synchronisation erfolgreich"
    },
    "retry_success": {  # ← ДОБАВЛЕНО
        "ru": "Retry успешен на попытке {0}",
        "en": "Retry successful on attempt {0}",
        "de": "Wiederholung erfolgreich beim Versuch {0}"
    },
    "retry_fail": {  # ← ДОБАВЛЕНО
        "ru": "Retry провален после {0} попыток",
        "en": "Retry failed after {0} attempts",
        "de": "Wiederholung fehlgeschlagen nach {0} Versuchen"
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

CAD_READY_TIMEOUT = 5
CAD_READY_INTERVAL = 0.2


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
    def wait_for_autocad_ready(self, timeout: int = CAD_READY_TIMEOUT, interval: float = CAD_READY_INTERVAL) -> bool:
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
            for layer in LAYER_DATA:
                name = layer["name"]
                try:
                    layers.Item(name)  # Проверяем, существует ли слой
                    logging.info(loc.get("layer_already_exists").format(name))
                    continue
                except:
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
            logging.error(f"Ошибка создания слоя: {e}")
            show_popup(loc.get("create_layer_error").format(error=str(e)), popup_type="error")
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
            logging.info(f"Установка стиля текста: {font_name}, bold={bold}, italic={italic}")
        except Exception as e:
            logging.error(f"Установка стиля текста не удалась: {e}")
            show_popup(loc.get("text_style_error").format(error=str(e)), popup_type="error")

    def restore_original_layer(self):
        if self.original_layer and self.adoc:
            self.adoc.ActiveLayer = self.original_layer
            logging.info(f"Восстановлен первоначальный слой: {self.original_layer.Name}")

    # -----------------------------
    # НОВЫЕ МЕТОДЫ: Синхронизация и retry (внедрено)
    # -----------------------------
    def sync_focus(self, delay: float = 0.1) -> bool:
        """
        Активирует фокус AutoCAD и документа для стабильных COM-вызовов.

        Args:
            delay (float): Задержка для sync (0.05-0.2 сек).

        Returns:
            bool: True при успехе (частично).
        """
        if not self.is_initialized():
            logging.warning("AutoCAD не инициализирован — sync пропущен")
            return False

        success = True
        try:
            # Сделай AutoCAD видимым и активным
            self.acad.Visible = True
            try:
                self.acad.WindowState = 0  # 0=normal
            except Exception as ws_e:
                logging.debug(f"WindowState fail (ignore): {ws_e}")  # Не критично
                success = False  # Но продолжаем

            # Активируй документ (fallback, если fail)
            try:
                self.adoc.Activate()
            except Exception as act_e:
                logging.debug(f"Activate fail (fallback): {act_e}")
                try:
                    # Fallback: Установи как ActiveDocument
                    self.acad.ActiveDocument = self.adoc
                except Exception:
                    pass
                success = False

            # Пропусти события wx (если в event loop)
            if wx.GetApp():
                wx.Yield()

            # Delay для COM-sync (уменьшено для 2026)
            time.sleep(delay)

            logging.info(loc.get("sync_success"))
            return success
        except Exception as e:
            logging.error(f"Sync фокуса провален: {e}")
            return False

    def retry_com_call(self, func: Callable, *args, retries: int = 3, delay: float = 0.1) -> Any:
        """
        Обёртка для COM-вызовов (AddText, AddDim и т.д.) с retry на фокус/рассинхрон.

        Args:
            func: COM-метод (e.g., self.adoc.ModelSpace.AddText).
            *args: Аргументы для func.
            retries (int): Кол-во попыток (3-5).
            delay (float): Задержка между (0.1 сек).

        Returns:
            Результат func или None при fail.
        """
        if not self.is_initialized():
            logging.warning("AutoCAD не готов — retry пропущен")
            return None

        for attempt in range(retries):
            try:
                self.sync_focus(delay=0.05)
                result = func(*args)
                self.regen_doc()
                logging.info(loc.get("retry_success").format(attempt + 1))
                return result
            except Exception as e:
                logging.error(f"Retry ошибка {attempt + 1}/{retries}: {e}")
                # Обновим ссылки на документ и ModelSpace
                self.refresh_active_document()
                if attempt < retries - 1:
                    time.sleep(delay)
                    self.sync_focus(delay=0.2)
                else:
                    logging.error(loc.get("retry_fail").format(retries))
                    return None

    def regen_doc(self, mode: int = 0):
        """
        Принудительная регенерация документа.

        Args:
            mode (int): 0=AllViewports, 1=Current, etc.
        """
        if not self.is_initialized():
            return

        try:
            self.sync_focus()
            self.adoc.Regen(mode)
            logging.info("Регенерация документа успешна")
        except Exception as e:
            logging.error(f"Регенерация провалена: {e}")

    # -----------------------------
    # Основная инициализация (ДОБАВЛЕНО: sync после создания doc)
    # -----------------------------
    def _initialize(self) -> None:
        """
        Пытается подключиться к уже запущенному AutoCAD.
        Если AutoCAD не запущен – выводит сообщение и завершает работу без ошибок.
        """
        try:
            # Пробуем подключиться к существующему процессу AutoCAD
            # pythoncom.CoInitialize()
            try:
                self.acad = win32com.client.GetActiveObject("AutoCAD.Application")
                logging.info(f"AutoCAD версия: {self.acad.Version}")
            except Exception:
                logging.info(loc.get("cad_not_ready"))
                self.acad = None
                self.adoc = None
                self.model = None
                self.original_layer = None
                return

            # Проверяем готовность объектной модели
            if not self.wait_for_autocad_ready():
                logging.warning(loc.get("cad_not_ready"))
                self.acad = None
                self.adoc = None
                self.model = None
                self.original_layer = None
                return

            # Получаем объекты документа
            self.adoc = self.acad.ActiveDocument
            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer

            # ← ДОБАВЛЕНО: Sync фокуса после создания doc
            self.sync_focus(delay=0.2)

            # Создание предопределённых слоёв
            self._create_layers()

            # Установка шрифта текстового стиля
            self._set_text_style(TEXT_FONT, bold=TEXT_BOLD, italic=TEXT_ITAL)

            # Устанавливаем активным слой "0"
            self.adoc.ActiveLayer = self.adoc.Layers.Item("0")

            logging.info("Автокад инициализирован успешно")

        except Exception as e:
            logging.error(f"Инициализация провалилась: {e}")
            show_popup(loc.get("cad_init_error_short") + f" {e}", popup_type="error")
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None
        # finally:
        #     pythoncom.CoUninitialize()

    # -----------------------------
    # Обновление активного документа (ДОБАВЛЕНО: sync в refresh)
    # -----------------------------
    def refresh_active_document(self) -> bool:
        """
        Обновляет ссылки на активный документ и пространство модели.
        Надёжно работает при переключении вкладок (включая несохранённые документы).
        """
        try:
            if not self.acad:
                return False

            # Sync перед обновлением
            self.sync_focus(delay=0.1)
            pythoncom.PumpWaitingMessages()

            # Получаем свежий COM-прокси AutoCAD.Application
            try:
                self.acad = win32com.client.GetActiveObject("AutoCAD.Application")
            except Exception as e:
                logging.error(f"Не удалось получить AutoCAD.Application: {e}")
                return False

            pythoncom.PumpWaitingMessages()

            try:
                current_doc = self.acad.ActiveDocument
            except Exception as e:
                logging.error(f"Не удалось прочитать ActiveDocument: {e}")
                self.adoc = None
                self.model = None
                return False

            # Если документ изменился или не установлен, обновляем ссылки
            if (self.adoc is None) or (current_doc != self.adoc):
                self.adoc = current_doc
                try:
                    self.model = self.adoc.ModelSpace
                except Exception as e:
                    logging.error(f"Не удалось получить ModelSpace: {e}")
                    self.model = None
                try:
                    self.original_layer = self.adoc.ActiveLayer
                except Exception:
                    self.original_layer = None
                logging.info(f"Обновлён активный документ: {getattr(self.adoc, 'Name', 'Unknown')}")
            else:
                logging.debug(f"Документ не изменился: {getattr(self.adoc, 'Name', 'Unknown')}")

            return True
        except Exception as e:
            logging.error(f"Не удалось обновить активный документ: {e}")
            self.adoc = None
            self.model = None
            return False

    # -----------------------------
    # Служебные методы
    # -----------------------------
    def is_initialized(self) -> bool:
        """Проверяет, успешно ли инициализирован AutoCAD."""
        return self.acad is not None and self.adoc is not None and self.model is not None

    # -----------------------------
    # Публичный API
    # -----------------------------
    @property
    def application(self) -> Optional[win32com.client.Dispatch]:
        """Возвращает объект AutoCAD Application, если инициализирован."""
        return self.acad if self.is_initialized() else None

    @property
    def document(self) -> Optional[win32com.client.Dispatch]:
        """Возвращает объект ActiveDocument, если инициализирован."""
        return self.adoc if self.is_initialized() else None

    @property
    def model_space(self) -> Optional[win32com.client.Dispatch]:
        """
        Возвращает объект ModelSpace для текущего активного документа.
        Если пользователь переключил вкладку — автоматически обновляет ссылки.
        """
        try:
            if not self.acad:
                return None
            self.refresh_active_document()
        except Exception:
            self.model = None
        return self.model if self.is_initialized() else None

if __name__ == "__main__":
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(loc.get("cad_init_error_short"), popup_type="error")
    else:
        show_popup(loc.get("cad_init_success"), popup_type="success")