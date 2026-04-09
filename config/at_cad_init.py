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
✔ Переподключение к AutoCAD через reconnect()
"""

import time
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Callable, Any, Generator

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
# ЛОГИРОВАНИЕ
# Именованный logger — не перебивает корневой basicConfig.
# pathlib.Path — единообразно с остальным проектом.
# ============================================================

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "at_cad_init.log"

logger = logging.getLogger("at_cad_init")

if not logger.handlers:
    _handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ============================================================
# КОНСТАНТЫ
# ============================================================

DOC_WAIT_TIMEOUT: float = 15.0
IDLE_WAIT_TIMEOUT: float = 10.0
RETRY_DELAY: float = 0.1
RPC_E_CALL_REJECTED: int = -2147418111  # HRESULT для RPC_E_CALL_REJECTED

# Тип для COM-исключений, которые ловим повсюду
_COM_ERRORS = (OSError, pythoncom.com_error, AttributeError)

# ============================================================
# COM RETRY WRAPPER
# ============================================================

class COMRetryWrapper:
    """
    Прозрачная обёртка COM-объекта.

    ✔ retry при RPC_E_CALL_REJECTED
    ✔ корректно работает с COM свойствами и методами
    ✔ __setattr__ проксирует присвоение на COM-объект

    Намеренно НЕ использует __slots__ — это позволяет избежать
    ложных предупреждений PyCharm о read-only атрибутах COM-объектов,
    которые устанавливаются через переопределённый __setattr__.
    """

    def __init__(self, com_obj: Any) -> None:
        # Обходим __setattr__, чтобы не уйти в рекурсию
        object.__setattr__(self, "_com_obj", com_obj)

    def __getattr__(self, item: str) -> Any:
        """
        Ленивый доступ к COM-атрибуту с retry:
        - COM-объект  → оборачиваем рекурсивно
        - callable    → оборачиваем вызов в retry
        - примитив    → возвращаем как есть
        """
        com_obj = object.__getattribute__(self, "_com_obj")
        value = COMRetryWrapper._retry(lambda: getattr(com_obj, item))

        if hasattr(value, "_oleobj_"):
            return COMRetryWrapper(value)

        if callable(value):
            def method(*args: Any, **kwargs: Any) -> Any:
                return COMRetryWrapper._retry(lambda: value(*args, **kwargs))
            return method

        return value

    def __setattr__(self, item: str, value: Any) -> None:
        """Проксирует присвоение атрибута на COM-объект."""
        if item == "_com_obj":
            object.__setattr__(self, item, value)
        else:
            com_obj = object.__getattribute__(self, "_com_obj")
            setattr(com_obj, item, value)

    @staticmethod
    def _retry(func: Callable, retries: int = 50, delay: float = RETRY_DELAY) -> Any:
        """
        Повторяет вызов func при RPC_E_CALL_REJECTED.
        Прочие COM-ошибки пробрасываются немедленно.
        getattr(e, 'hresult') вместо e.hresult — stub-файлы pythoncom
        не объявляют этот атрибут явно, что даёт ложное предупреждение PyCharm.
        """
        for _ in range(retries):
            try:
                pythoncom.PumpWaitingMessages()
                return func()
            except pythoncom.com_error as e:
                if getattr(e, "hresult", None) == RPC_E_CALL_REJECTED:
                    time.sleep(delay)
                    continue
                raise
        raise TimeoutError("COM retry timeout: AutoCAD не отвечает")


# ============================================================
# ATCADINIT
# ============================================================

class ATCadInit:
    """
    Singleton для инициализации и работы с AutoCAD через COM.

    Для переподключения к AutoCAD после его перезапуска:
        ATCadInit.reconnect()
    """

    _instance: Optional["ATCadInit"] = None

    def __new__(cls) -> "ATCadInit":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """
        Объявляет атрибуты экземпляра для статического анализа PyCharm.
        Реальная инициализация — в _initialize(), вызываемой из __new__.
        hasattr-защита предотвращает сброс атрибутов при повторных ATCadInit().
        """
        if not hasattr(self, "acad"):
            self.acad: Optional[COMRetryWrapper] = None
            self.adoc: Optional[COMRetryWrapper] = None
            self.model: bool = False
            self.original_layer: Any = None

    @classmethod
    def reconnect(cls) -> "ATCadInit":
        """
        Сбрасывает Singleton и создаёт новое подключение к AutoCAD.
        Вызывать, если AutoCAD был перезапущен после старта AT-CAD.
        """
        cls._instance = None
        return cls()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _initialize(self) -> None:
        """
        Подключается к уже запущенному AutoCAD через COM.
        Не запускает AutoCAD самостоятельно.
        """
        self.acad = None
        self.adoc = None
        self.model = False
        self.original_layer = None

        try:
            raw = win32com.client.GetActiveObject("AutoCAD.Application")
            self.acad = COMRetryWrapper(raw)
            logger.info("Подключено к запущенному AutoCAD")
        except (OSError, pythoncom.com_error):
            logger.warning(loc.get("cad_not_ready"))
            return

        if not self._wait_for_document():
            logger.warning(loc.get("no_documents"))
            return

        try:
            self.adoc = self.acad.ActiveDocument
        except pythoncom.com_error as e:
            logger.error(f"ActiveDocument error: {e}")
            return

        if not self._wait_idle():
            logger.warning(loc.get("cad_not_ready"))
            return

        self.model = True
        self.original_layer = self._safe_call(lambda: self.adoc.ActiveLayer)

        self._post_init_document()
        logger.info(loc.get("cad_init_success"))

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    @staticmethod
    def _safe_call(func: Callable, default: Any = None) -> Any:
        """
        Тихий guard: возвращает default при ошибке, не логирует.
        Используется внутри класса для некритичных COM-обращений.
        """
        try:
            return func()
        except _COM_ERRORS:
            return default

    def safe_call(self,
                  func: Callable,
                  default: Any = None,
                  log: bool = True) -> Any:
        """
        Публичный guard: возвращает default при ошибке, опционально логирует.
        func должен быть лямбдой: lambda: self.adoc.ModelSpace
        """
        try:
            return func()
        except _COM_ERRORS as e:
            if log:
                logger.error(f"COM safe_call error: {e}")
            return default

    def _wait_for_document(self) -> bool:
        """Ожидает появления хотя бы одного открытого документа."""
        start = time.monotonic()
        while time.monotonic() - start < DOC_WAIT_TIMEOUT:
            if self._safe_call(lambda: self.acad.Documents.Count, default=0) > 0:
                return True
            if self._safe_call(lambda: self.acad.ActiveDocument) is not None:
                return True
            time.sleep(0.2)
        return False

    def _wait_idle(self) -> bool:
        """Ждёт, пока AutoCAD не завершит активную команду (CMDACTIVE=0)."""
        start = time.monotonic()
        while time.monotonic() - start < IDLE_WAIT_TIMEOUT:
            cmd_active = self._safe_call(
                lambda: self.adoc.GetVariable("CMDACTIVE"),
                default=1
            )
            if cmd_active == 0:
                return True
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
        return False

    def _ensure_model_space(self) -> None:
        """Переключает активное пространство в ModelSpace (acSpace=1)."""
        try:
            if self.adoc.ActiveSpace != 1:
                self.adoc.ActiveSpace = 1
                time.sleep(0.05)
        except _COM_ERRORS as e:
            logger.warning(f"Не удалось переключиться в ModelSpace: {e}")

    def _is_com_alive(self) -> bool:
        """
        Проверяет живость COM-соединения лёгким вызовом.
        Возвращает False, если AutoCAD был закрыт.
        """
        return self._safe_call(lambda: self.acad.Version) is not None

    @staticmethod
    def unwrap(obj: Any) -> Any:
        """
        Возвращает сырой COM-объект из COMRetryWrapper.
        Нужно для прямого доступа к геометрии объектов.
        """
        if isinstance(obj, COMRetryWrapper):
            return object.__getattribute__(obj, "_com_obj")
        return obj

    # =========================================================
    # ДОКУМЕНТ
    # =========================================================

    def refresh_active_document(self) -> bool:
        """
        Обновляет adoc, если пользователь переключился на другой документ.
        Сравнение по имени — надёжнее, чем == на COM-объектах.
        """
        if not self.acad:
            return False

        current_doc = self._safe_call(lambda: self.acad.ActiveDocument)
        if current_doc is None:
            self.adoc = None
            self.model = False
            return False

        current_name = self._safe_call(lambda: current_doc.Name)
        existing_name = self._safe_call(lambda: self.adoc.Name) if self.adoc else None

        if current_name != existing_name:
            self.adoc = current_doc
            self.original_layer = self._safe_call(lambda: self.adoc.ActiveLayer)
            logger.info(f"Активный документ изменён: {current_name}")
            self._post_init_document()

        return True

    # =========================================================
    # СЛОИ
    # =========================================================

    def _create_layers(self) -> bool:
        """
        Создаёт слои из LAYER_DATA, если они ещё не существуют.

        Цвет устанавливается через layer.color = ACI-индекс напрямую.
        Имя захватывается по значению (n=name) — защита от ловушки замыкания.
        Явные int()/str() касты устраняют предупреждения PyCharm о типе 'object'
        из-за сигнатуры LAYER_DATA: list[dict[str, object]].
        """
        if not self.adoc:
            return False

        try:
            layers = self.adoc.Layers

            for layer_def in LAYER_DATA:
                name: str = str(layer_def["name"])
                existing = self._safe_call(lambda n=name: layers.Item(n))
                if existing is not None:
                    continue

                new_layer = layers.Add(name)
                new_layer.color = int(layer_def.get("color", 7))  # type: ignore[arg-type]

                linetype: str = str(layer_def.get("linetype", "CONTINUOUS"))
                try:
                    new_layer.Linetype = linetype
                except _COM_ERRORS:
                    pass  # тип линии может отсутствовать в шаблоне — не критично

            return True

        except _COM_ERRORS as e:
            logger.error(f"_create_layers: {e}")
            show_popup(
                loc.get("create_layer_error").format(error=str(e)),
                popup_type="error"
            )
            return False

    # =========================================================
    # ШРИФТ
    # =========================================================

    def _set_text_style(self,
                        font_name: str,
                        bold: bool = False,
                        italic: bool = False) -> None:
        """Устанавливает шрифт для ActiveTextStyle."""
        try:
            style = self.adoc.ActiveTextStyle
            style.SetFont(font_name, bool(bold), bool(italic), 0, 0)
        except _COM_ERRORS as e:
            logger.error(f"_set_text_style: {e}")
            show_popup(
                loc.get("text_style_error").format(error=str(e)),
                popup_type="error"
            )

    # =========================================================
    # POST-INIT
    # =========================================================

    def _post_init_document(self) -> None:
        """Применяет конфигурацию к документу: слои, шрифт, сброс на слой '0'."""
        if not self.adoc:
            return
        try:
            self._wait_idle()
            self._create_layers()
            self._set_text_style(TEXT_FONT, TEXT_BOLD, TEXT_ITAL)

            layer0 = self._safe_call(lambda: self.adoc.Layers.Item("0"))
            if layer0 is not None:
                self.adoc.ActiveLayer = layer0

        except _COM_ERRORS as e:
            logger.error(f"_post_init_document: {e}")

    # =========================================================
    # PUBLIC API
    # =========================================================

    @property
    def application(self) -> Optional[COMRetryWrapper]:
        return self.acad if self.is_initialized() else None

    @property
    def document(self) -> Optional[COMRetryWrapper]:
        return self.adoc if self.is_initialized() else None

    @property
    def model_space(self) -> Optional[COMRetryWrapper]:
        if not self.acad or not self.refresh_active_document():
            return None
        self._ensure_model_space()
        return self._safe_call(lambda: self.adoc.ModelSpace)

    def is_initialized(self) -> bool:
        """Проверяет not None и живость COM-соединения."""
        if self.acad is None or self.adoc is None:
            return False
        return self._is_com_alive()

    def restore_original_layer(self) -> None:
        """Восстанавливает слой, активный до начала построения."""
        if self.original_layer is not None and self.adoc is not None:
            try:
                self.adoc.ActiveLayer = self.original_layer
            except _COM_ERRORS as e:
                logger.warning(f"restore_original_layer: {e}")

    @contextmanager
    def cad_transaction(self,
                        layer: Optional[str] = None,
                        regen: bool = True) -> Generator[None, None, None]:
        """
        Контекстный менеджер для безопасной работы с AutoCAD:
        - переключает активный слой (если задан)
        - гарантирует возврат исходного слоя после выхода
        - делает Regen по завершению (если regen=True)

        Использование:
            with cad.cad_transaction(layer="schrift"):
                # рисуем
        """
        if not self.is_initialized():
            yield
            return

        self.refresh_active_document()
        prev_layer = self._safe_call(lambda: self.adoc.ActiveLayer)

        try:
            if layer:
                target = self._safe_call(lambda: self.adoc.Layers.Item(layer))
                if target is None:
                    self._create_layers()
                    target = self._safe_call(lambda: self.adoc.Layers.Item(layer))
                if target is not None:
                    try:
                        self.adoc.ActiveLayer = target
                    except _COM_ERRORS as e:
                        logger.warning(f"cad_transaction layer switch: {e}")
            yield

        finally:
            if prev_layer is not None:
                try:
                    self.adoc.ActiveLayer = prev_layer
                except _COM_ERRORS:
                    pass
            if regen:
                try:
                    self.adoc.Regen(0)
                except _COM_ERRORS:
                    pass

    def safe_add(self, func: Callable, *args: Any) -> Optional[Any]:
        """
        Безопасно создаёт объект в ModelSpace.
        func(model, *args) — принимает ModelSpace первым аргументом.
        """
        if not self.is_initialized():
            return None
        model = self.model_space
        if model is None:
            return None
        return self.safe_call(lambda: func(model, *args))

    def regen_doc(self, mode: int = 0) -> None:
        """Принудительная регенерация документа."""
        if not self.is_initialized():
            return
        try:
            self.adoc.Regen(mode)
            logger.info("Регенерация документа выполнена")
        except _COM_ERRORS as e:
            logger.error(f"regen_doc: {e}")


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