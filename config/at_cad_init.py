# -*- coding: utf-8 -*-
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

НАДЁЖНАЯ ИНИЦИАЛИЗАЦИЯ AutoCAD через COM (win32com)

Особенности:
✔ Singleton — единственный экземпляр на всё время работы приложения
✔ Поддержка RPC_E_CALL_REJECTED через собственную COMRetryWrapper
✔ Ожидание появления документа и завершения команд (CMDACTIVE=0)
✔ Безопасные вызовы COM через safe_call / _safe_call
✔ Удобная работа с ModelSpace и слоями
✔ Не конвертирует точки в VARIANT автоматически — используем списки координат
✔ Переподключение к AutoCAD через reconnect()
✔ refresh_active_document() — автоматическое переключение при смене чертежа

Принцип работы при смене документа:
    AutoCAD позволяет держать несколько чертежей открытыми одновременно.
    ATCadInit хранит ссылку только на приложение (self.acad = AcadApplication).
    Активный документ (self.adoc) обновляется динамически через
    refresh_active_document(), который вызывается из model_space и
    публичных точек входа в at_input.py перед каждым интерактивным вводом.
    Это гарантирует, что GetPoint/GetEntity всегда работают с тем чертежом,
    который виден пользователю в момент запроса.
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

DOC_WAIT_TIMEOUT: float = 15.0   # сек — ожидание появления документа при старте
IDLE_WAIT_TIMEOUT: float = 10.0  # сек — ожидание завершения активной команды
RETRY_DELAY: float = 0.1         # сек — пауза между повторами при RPC_E_CALL_REJECTED

# HRESULT: AutoCAD занят предыдущей операцией, вызов надо повторить позже
RPC_E_CALL_REJECTED: int = -2147418111

# HRESULT: COM-контекст развалился / удалённый вызов больше невалиден.
# В реальной работе AutoCAD это часто происходит при переключении документа,
# листа, закрытии/открытии чертежа или потере актуальности старого COM-объекта.
RPC_S_CALL_FAILED: int = -2147023170

# Кортеж COM-исключений, перехватываемых во всех safe_call / guard-блоках.
# AttributeError включён, потому что обращение к атрибуту закрытого COM-объекта
# иногда даёт AttributeError вместо pythoncom.com_error.
_COM_ERRORS = (OSError, pythoncom.com_error, AttributeError)


# ============================================================
# COM RETRY WRAPPER
# ============================================================

class COMRetryWrapper:
    """
    Прозрачная обёртка над любым COM-объектом win32com.

    Зачем нужна:
        AutoCAD иногда отвечает RPC_E_CALL_REJECTED (занят предыдущей операцией).
        Вместо того чтобы расставлять retry-циклы по всему коду, оборачиваем
        COM-объект один раз — и все обращения к атрибутам и методам автоматически
        повторяются до успеха или таймаута.

    Принцип работы:
        __getattr__ перехватывает любое обращение (obj.Name, obj.GetPoint() и т.д.)
        и пропускает его через _retry. Если результат — снова COM-объект,
        оборачиваем рекурсивно, чтобы цепочки (obj.Utility.GetPoint) тоже
        получали защиту. Если результат — callable, оборачиваем вызов.
        Примитивы (строки, числа) возвращаем как есть.

        __setattr__ проксирует присвоение атрибутов на сырой COM-объект,
        что позволяет писать obj.ActiveLayer = layer естественным образом.

    Намеренно НЕ использует __slots__ — это позволяет избежать ложных
    предупреждений PyCharm о read-only атрибутах COM-объектов, которые
    устанавливаются через переопределённый __setattr__.
    """

    def __init__(self, com_obj: Any) -> None:
        # Обходим __setattr__, чтобы не уйти в рекурсию при записи _com_obj
        object.__setattr__(self, "_com_obj", com_obj)

    def __getattr__(self, item: str) -> Any:
        """
        Ленивый доступ к COM-атрибуту с retry:
          - COM-объект  → оборачиваем рекурсивно в COMRetryWrapper
          - callable    → оборачиваем вызов в retry-замыкание
          - примитив    → возвращаем как есть
        """
        com_obj = object.__getattribute__(self, "_com_obj")
        value = COMRetryWrapper._retry(lambda: getattr(com_obj, item))

        if hasattr(value, "_oleobj_"):
            # Это COM-объект — оборачиваем, чтобы цепочки тоже были защищены
            return COMRetryWrapper(value)

        if callable(value):
            # Это COM-метод — оборачиваем вызов
            def method(*args: Any, **kwargs: Any) -> Any:
                return COMRetryWrapper._retry(lambda: value(*args, **kwargs))
            return method

        return value

    def __setattr__(self, item: str, value: Any) -> None:
        """
        Проксирует присвоение атрибута на сырой COM-объект.
        Исключение: _com_obj записывается напрямую в __dict__ экземпляра.
        """
        if item == "_com_obj":
            object.__setattr__(self, item, value)
        else:
            com_obj = object.__getattribute__(self, "_com_obj")
            setattr(com_obj, item, value)

    @staticmethod
    def _retry(func: Callable, retries: int = 50, delay: float = RETRY_DELAY) -> Any:
        """
        Повторяет вызов func при RPC_E_CALL_REJECTED (AutoCAD временно занят).

        Что считаем нормальным сценарием для retry:
            RPC_E_CALL_REJECTED — AutoCAD ещё обрабатывает предыдущую операцию,
            нужно немного подождать и попробовать снова.

        Что НЕ ретраим:
            RPC_S_CALL_FAILED — старый COM-контекст больше невалиден
            (например, пользователь переключил документ/лист, закрыл чертёж,
            AutoCAD пересоздал внутренний объект и т.п.).
            Такой случай должен обрабатываться уровнем выше через reconnect()
            и повторное получение ActiveDocument.

        Прочие COM-ошибки пробрасываются немедленно без retry.

        Примечание: getattr(e, 'hresult') вместо e.hresult — stub-файлы
        pythoncom не объявляют этот атрибут явно, что даёт ложное
        предупреждение PyCharm о несуществующем атрибуте.
        """
        last_error: Optional[BaseException] = None

        for _ in range(retries):
            try:
                pythoncom.PumpWaitingMessages()
                return func()

            except pythoncom.com_error as e:
                hr = getattr(e, "hresult", None)
                last_error = e

                if hr == RPC_E_CALL_REJECTED:
                    time.sleep(delay)
                    continue

                if hr == RPC_S_CALL_FAILED:
                    raise

                raise

        raise TimeoutError(f"COM retry timeout: {last_error}")


# ============================================================
# ATCADINIT
# ============================================================

class ATCadInit:
    """
    Singleton для инициализации и работы с AutoCAD через COM.

    Жизненный цикл:
        ATCadInit() — подключается к уже запущенному AutoCAD (GetActiveObject).
        Если AutoCAD не запущен или нет открытых документов — инициализация
        завершается с is_initialized() == False, без исключений.

        После инициализации:
            cad.acad  — AcadApplication (живёт всю сессию AutoCAD)
            cad.adoc  — текущий ActiveDocument (обновляется через refresh_active_document)

    Смена документа:
        При открытии нового чертежа пользователь переключается между вкладками
        AutoCAD. ATCadInit не отслеживает это событие автоматически (COM не даёт
        надёжных событий без регистрации sink). Вместо этого refresh_active_document()
        вызывается явно перед каждым интерактивным вводом — это дёшево (один COM-вызов)
        и достаточно надёжно для нашего сценария.

    Переподключение после перезапуска AutoCAD:
        ATCadInit.reconnect() — сбрасывает Singleton и создаёт новое подключение.
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

        Пример:
            cad = ATCadInit.reconnect()
        """
        cls._instance = None
        return cls()

    # =========================================================
    # ИНИЦИАЛИЗАЦИЯ
    # =========================================================

    def _initialize(self) -> None:
        """
        Подключается к уже запущенному AutoCAD через COM (GetActiveObject).
        Не запускает AutoCAD самостоятельно — только присоединяется.

        Последовательность:
            1. GetActiveObject("AutoCAD.Application") → self.acad
            2. Ожидание открытого документа → _wait_for_document()
            3. Получение ActiveDocument → self.adoc
            4. Ожидание idle (CMDACTIVE=0) → _wait_idle()
            5. Применение конфигурации → _post_init_document()
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
        Тихий guard для некритичных COM-обращений внутри класса.
        При любой ошибке из _COM_ERRORS молча возвращает default.
        Не логирует — используется там, где ошибка ожидаема (например,
        проверка существования слоя, проверка живости объекта).
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
        Публичный guard для COM-обращений из внешнего кода.
        При ошибке возвращает default и опционально пишет в лог.

        Пример:
            ms = cad.safe_call(lambda: cad.adoc.ModelSpace)
        """
        try:
            return func()
        except _COM_ERRORS as e:
            if log:
                logger.error(f"COM safe_call error: {e}")
            return default

    def _wait_for_document(self) -> bool:
        """
        Ожидает появления хотя бы одного открытого документа.
        Нужно при старте: AutoCAD может быть запущен, но документ ещё не загружен.
        Таймаут: DOC_WAIT_TIMEOUT секунд.
        """
        start = time.monotonic()
        while time.monotonic() - start < DOC_WAIT_TIMEOUT:
            if self._safe_call(lambda: self.acad.Documents.Count, default=0) > 0:
                return True
            if self._safe_call(lambda: self.acad.ActiveDocument) is not None:
                return True
            time.sleep(0.2)
        return False

    def _wait_idle(self) -> bool:
        """
        Ждёт, пока AutoCAD не завершит активную команду (CMDACTIVE=0).
        Нужно перед _post_init_document(), чтобы не мешать текущей работе.
        Таймаут: IDLE_WAIT_TIMEOUT секунд.
        """
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
        """
        Переключает активное пространство в ModelSpace (acSpace=1).
        Вызывается из model_space property перед возвратом ModelSpace.
        Если уже в ModelSpace — ничего не делает.
        """
        try:
            if self.adoc.ActiveSpace != 1:
                self.adoc.ActiveSpace = 1
                time.sleep(0.05)
        except _COM_ERRORS as e:
            logger.warning(f"Не удалось переключиться в ModelSpace: {e}")

    def _is_com_alive(self) -> bool:
        """
        Лёгкая проверка живости COM-соединения с приложением.
        Запрашивает Version — дешёвый атрибут, всегда доступный.
        Возвращает False, если AutoCAD был закрыт после инициализации.
        """
        return self._safe_call(lambda: self.acad.Version) is not None

    @staticmethod
    def unwrap(obj: Any) -> Any:
        """
        Возвращает сырой COM-объект из COMRetryWrapper.
        Нужно в редких случаях прямого доступа к геометрии объектов,
        когда COMRetryWrapper мешает (например, передача в сторонние
        функции, ожидающие сырой win32com-объект).
        """
        if isinstance(obj, COMRetryWrapper):
            return object.__getattribute__(obj, "_com_obj")
        return obj

    # =========================================================
    # ДОКУМЕНТ
    # =========================================================

    def refresh_active_document(self) -> bool:
        """
        Обновляет self.adoc до текущего активного документа AutoCAD.

        Назначение:
            Это центральная точка актуализации рабочего документа перед
            интерактивным вводом и построением. Метод безопасно переживает:
                - переключение между открытыми чертежами
                - переключение между листами/пространствами
                - устаревание старого COM-объекта документа
                - частичный развал COM-контекста после действий пользователя

        Алгоритм:
            1. Проверяем, что приложение AutoCAD ещё доступно.
               Если нет — выполняем reconnect().
            2. Пытаемся получить acad.ActiveDocument.
            3. Если чтение ActiveDocument упало — пробуем reconnect() ещё раз.
            4. Если имя текущего документа отличается от self.adoc.Name —
               обновляем self.adoc и заново применяем _post_init_document().
            5. Возвращаем True только если итоговый self.adoc валиден.

        Возвращает:
            True  — текущий активный документ успешно получен и валиден
            False — документа нет, AutoCAD недоступен или переподключение не удалось

        Важно:
            Этот метод не обязан сохранять прежний self.adoc любой ценой.
            Напротив: если старый COM-объект документа протух, он должен быть
            отброшен и заменён новым ActiveDocument.
        """
        if not self.acad or not self._is_com_alive():
            try:
                fresh = self.__class__.reconnect()
                self.acad = fresh.acad
                self.adoc = fresh.adoc
                self.model = fresh.model
                self.original_layer = fresh.original_layer
            except Exception as e:
                logger.error(f"refresh_active_document reconnect(app): {e}")
                self.acad = None
                self.adoc = None
                self.model = False
                self.original_layer = None
                return False

        current_doc = self._safe_call(lambda: self.acad.ActiveDocument)
        if current_doc is None:
            try:
                fresh = self.__class__.reconnect()
                self.acad = fresh.acad
                self.adoc = fresh.adoc
                self.model = fresh.model
                self.original_layer = fresh.original_layer
            except Exception as e:
                logger.error(f"refresh_active_document reconnect(doc): {e}")
                self.adoc = None
                self.model = False
                self.original_layer = None
                return False

            current_doc = self._safe_call(lambda: self.acad.ActiveDocument) if self.acad else None
            if current_doc is None:
                self.adoc = None
                self.model = False
                self.original_layer = None
                return False

        current_name = self._safe_call(lambda: current_doc.Name)
        existing_name = self._safe_call(lambda: self.adoc.Name) if self.adoc else None

        if self.adoc is None or current_name != existing_name:
            self.adoc = current_doc
            self.original_layer = self._safe_call(lambda: self.adoc.ActiveLayer)
            logger.info(f"Активный документ изменён: {current_name}")
            self._post_init_document()

        self.model = self.adoc is not None
        return self._safe_call(lambda: self.adoc.Name) is not None

    # =========================================================
    # СЛОИ
    # =========================================================

    def _create_layers(self) -> bool:
        """
        Создаёт слои из LAYER_DATA в текущем документе, если они ещё не существуют.
        Существующие слои не трогает (идемпотентная операция).

        Цвет устанавливается через layer.color = ACI-индекс напрямую.
        Имя захватывается по значению (n=name) — защита от ловушки замыкания
        в lambda внутри цикла.
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
                    continue  # слой уже есть — пропускаем

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
        """
        Устанавливает шрифт для ActiveTextStyle текущего документа.
        Вызывается из _post_init_document при каждом подключении к документу.
        """
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
        """
        Применяет конфигурацию к документу после подключения или смены чертежа:
            - ожидает idle (AutoCAD не занят командой)
            - создаёт слои из LAYER_DATA
            - устанавливает шрифт TEXT_FONT
            - переключает активный слой на '0' (нейтральный старт)

        Вызывается из _initialize() при первом подключении и из
        refresh_active_document() при каждой смене активного чертежа.
        """
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
        """Возвращает COM-объект AcadApplication или None если не инициализирован."""
        return self.acad if self.is_initialized() else None

    @property
    def document(self) -> Optional[COMRetryWrapper]:
        """
        Возвращает текущий активный документ.

        Важно: это property динамически возвращает self.adoc — но self.adoc
        обновляется только при вызове refresh_active_document(). Поэтому
        для работы с интерактивным вводом используй _resolve_document()
        из at_input.py, который вызывает refresh явно.
        """
        return self.adoc if self.is_initialized() else None

    @property
    def model_space(self) -> Optional[COMRetryWrapper]:
        """
        Возвращает ModelSpace текущего активного документа.
        Перед возвратом вызывает refresh_active_document() — то есть
        автоматически подхватывает смену чертежа при любом обращении
        к ModelSpace из кода построения.
        """
        if not self.acad or not self.refresh_active_document():
            return None
        self._ensure_model_space()
        return self._safe_call(lambda: self.adoc.ModelSpace)

    def is_initialized(self) -> bool:
        """
        Проверяет общую готовность AutoCAD-соединения к работе.

        Что считается инициализированным состоянием:
            1. Есть ссылка на приложение (self.acad)
            2. Есть ссылка на документ (self.adoc)
            3. COM-соединение с приложением живо
            4. Текущий документ можно актуализировать через refresh_active_document()

        Почему здесь вызывается refresh_active_document():
            Ранее метод проверял только старый self.adoc и тем самым мог
            обращаться к уже невалидному COM-объекту после переключения
            документа/листа. Теперь проверка готовности включает попытку
            актуализировать ActiveDocument, то есть опирается не на старый
            кэш, а на текущее состояние AutoCAD.

        Возвращает:
            True  — AutoCAD доступен, активный документ найден и валиден
            False — приложение/документ недоступны
        """
        if self.acad is None:
            return False

        if not self._is_com_alive():
            return False

        return self.refresh_active_document()

    def restore_original_layer(self) -> None:
        """
        Восстанавливает слой, который был активен до начала построения.
        Вызывается из кода построения после завершения операции.
        """
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
        Контекстный менеджер для безопасной работы с AutoCAD.

        Действия при входе:
            - refresh_active_document() — подхватываем текущий чертёж
            - запоминаем активный слой
            - переключаем на нужный слой (если layer задан)

        Действия при выходе (в любом случае, включая исключения):
            - восстанавливаем исходный слой
            - делаем Regen (если regen=True)

        Пример:
            with cad.cad_transaction(layer="schrift"):
                # рисуем текст
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
        Безопасно создаёт объект в ModelSpace текущего документа.
        func(model, *args) — первым аргументом получает ModelSpace.

        Пример:
            cad.safe_add(lambda ms, p, r: ms.AddCircle(p, r), point, radius)
        """
        if not self.is_initialized():
            return None
        model = self.model_space
        if model is None:
            return None
        return self.safe_call(lambda: func(model, *args))

    def regen_doc(self, mode: int = 0) -> None:
        """
        Принудительная регенерация текущего документа.
        mode=0 — acAllViewports (все видовые экраны).
        """
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
