# -*- coding: utf-8 -*-
"""
Файл: at_base.py
Путь: programs/at_base.py

Описание:
    Модуль базовых операций с AutoCAD через COM-интерфейс.
    Предоставляет инструменты для:
        - динамического запуска build-модулей по имени (run_program)
        - регенерации видового экрана (regen)
        - создания и проверки слоёв (ensure_layer)
        - переключения активного слоя (set_layer, restore_layer)
        - контекстного менеджера временного слоя (layer_context)

Зависимости:
    config.at_cad_init  — ATCadInit (Singleton COM-подключения)
    locales             — loc (локализация строк)
    windows.at_gui_utils — show_popup (всплывающие окна)

Логирование:
    Именованный logger "at_base" пишет в корневой обработчик приложения.
    Уровень: WARNING и выше (ошибки слоёв, ошибки запуска модулей).
"""

from __future__ import annotations

import importlib
import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional
import pythoncom
import win32com.client
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# ============================================================
# ЛОГИРОВАНИЕ
# Именованный logger не перебивает корневой basicConfig.
# Уровень не устанавливаем явно — наследуется от root logger.
# ============================================================

logger = logging.getLogger("at_base")

# Тип COM-исключений, перехватываемых в guard-блоках
_COM_ERRORS = (OSError, pythoncom.com_error, AttributeError, RuntimeError)


# ============================================================
# ДИНАМИЧЕСКИЙ ЗАПУСК МОДУЛЕЙ
# ============================================================

def run_program(module_name: str, data: Any = None) -> Any:
    """
    Универсальный запуск build-модуля по его полному имени.

    Алгоритм поиска точки входа:
        1. Пытается вызвать module.main(data)
        2. Если main отсутствует — пробует вызвать функцию
           с именем, равным последней части module_name
           (например, "programs.at_schrift" → ищет at_schrift(data))

    Параметры:
        module_name — полное имя модуля в dot-notation ("programs.at_schrift")
        data        — произвольные данные, передаваемые в точку входа

    Возвращает:
        Результат вызова функции или None при любой ошибке.
        Ошибки логируются, исключения не пробрасываются.

    Пример:
        result = run_program("programs.at_schrift", point_data)
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        logger.info("Нет обрабатывающего модуля - он не нужен?")
        return None
    except ImportError as e:
        logger.error(f"[run_program] Не удалось импортировать модуль '{module_name}': {e}")
        return None
    except Exception as e:  # noqa: BLE001 — ловим всё, т.к. импорт может дать SyntaxError и др.
        logger.error(f"[run_program] Неожиданная ошибка при импорте '{module_name}': {e}")
        return None

    # 1) Ищем main()
    if hasattr(module, "main"):
        try:
            return module.main(data)
        except Exception as e:
            logger.exception(f"[run_program] Ошибка при вызове '{module_name}.main': {e}")
            return None

    # 2) Fallback: функция по имени последней части модуля
    func_name = module_name.split(".")[-1]
    func = getattr(module, func_name, None)
    if func is not None and callable(func):
        try:
            return func(data)
        except Exception as e:
            logger.exception(f"[run_program] Ошибка при вызове '{module_name}.{func_name}': {e}")
            return None

    logger.debug(
        f"[run_program] В модуле '{module_name}' нет функции 'main' и нет '{func_name}'"
    )
    return None


# ============================================================
# РЕГЕНЕРАЦИЯ
# ============================================================

def regen(adoc: object) -> bool:
    """
    Выполняет регенерацию видового экрана AutoCAD (acAllViewports).

    Параметры:
        adoc — COM-объект активного документа AutoCAD

    Возвращает:
        True  — регенерация выполнена успешно
        False — ошибка COM или adoc недоступен

    Примечание:
        Эквивалент команды REGEN в командной строке AutoCAD.
        Regen(0) = acAllViewports — обновляет все видовые экраны.
    """
    try:
        adoc.Regen(0)
        return True
    except _COM_ERRORS as e:
        logger.warning(f"regen: не удалось выполнить регенерацию: {e}")
        return False


# ============================================================
# СЛОИ
# ============================================================

def ensure_layer(
        adoc: object,
        layer_name: str,
        color_index: int = 7,
        line_type: str = "Continuous",
) -> Optional[object]:
    """
    Проверяет наличие слоя и создаёт его при необходимости.

    Если слой уже существует — возвращает его без изменения свойств.
    Если не существует — создаёт новый и устанавливает цвет и тип линии.

    Цвет устанавливается через объект AcCmColor (TrueColor API) —
    это корректный способ для AutoCAD 2020–2026. Прямое присвоение
    layer.Color устарело и не поддерживает TrueColor.

    Параметры:
        adoc        — COM-объект активного документа AutoCAD
        layer_name  — имя слоя (регистр важен для AutoCAD)
        color_index — индекс цвета ACI (1=красный, 2=жёлтый, 3=зелёный,
                      7=белый/чёрный в зависимости от темы). Диапазон: 1–255.
        line_type   — имя типа линии; должен быть загружен в чертёж.
                      Если отсутствует — тип линии не изменяется (не ошибка).

    Возвращает:
        COM-объект слоя (IAcadLayer) или None при критической ошибке создания.

    Пример:
        layer = ensure_layer(adoc, "schrift", color_index=3, line_type="DASHED")
    """
    try:
        layers = adoc.Layers
    except _COM_ERRORS as e:
        logger.error(f"ensure_layer: нет доступа к Layers документа: {e}")
        return None

    # Пробуем получить существующий слой
    try:
        layer = layers.Item(layer_name)
        return layer  # слой существует — возвращаем без изменений
    except _COM_ERRORS:
        pass  # слой не найден — создаём ниже

    # Создаём новый слой
    try:
        layer = layers.Add(layer_name)
    except _COM_ERRORS as e:
        logger.error(f"ensure_layer: не удалось создать слой '{layer_name}': {e}")
        return None

    # Устанавливаем цвет через TrueColor API
    try:
        color_obj = win32com.client.Dispatch("AutoCAD.AcCmColor")
        color_obj.ColorIndex = color_index
        layer.TrueColor = color_obj
    except _COM_ERRORS as e:
        # Некритично — слой создан, цвет останется по умолчанию
        logger.warning(f"ensure_layer: не удалось установить цвет слоя '{layer_name}': {e}")

    # Устанавливаем тип линии (необязательно — может не быть в шаблоне)
    try:
        layer.Linetype = line_type
    except _COM_ERRORS:
        # Тип линии не загружен в чертёж — оставляем Continuous, не ошибка
        pass

    return layer


def set_layer(adoc: object, layer_name: str) -> bool:
    """
    Устанавливает указанный слой как активный в документе AutoCAD.
    Если слой не существует — создаёт его через ensure_layer.

    Параметры:
        adoc       — COM-объект активного документа AutoCAD
        layer_name — имя слоя для активации

    Возвращает:
        True  — слой активирован
        False — ошибка COM или слой не удалось создать

    Примечание:
        Не итерируем по adoc.Layers для проверки существования —
        используем ensure_layer, который делает это через Item() (O(1) vs O(n)).
    """
    try:
        # ensure_layer вернёт None только если не смогла создать слой
        layer = ensure_layer(adoc, layer_name)
        if layer is None:
            return False
        adoc.ActiveLayer = adoc.Layers.Item(layer_name)
        return True
    except _COM_ERRORS as e:
        logger.warning(f"set_layer: не удалось установить слой '{layer_name}': {e}")
        return False


def restore_layer(adoc: object, original_layer: object) -> bool:
    """
    Восстанавливает ранее сохранённый активный слой.

    Параметры:
        adoc           — COM-объект активного документа AutoCAD
        original_layer — COM-объект слоя, который нужно восстановить

    Возвращает:
        True  — слой восстановлен
        False — ошибка; показывает popup с сообщением об ошибке

    Примечание:
        Обычно вызывается из finally-блока layer_context или cad_transaction,
        поэтому не пробрасывает исключения.
    """
    try:
        adoc.ActiveLayer = original_layer
        return True
    except _COM_ERRORS as e:
        # Важно: передаём экземпляр исключения (e), а не класс (Exception)
        logger.error(f"restore_layer: не удалось восстановить слой: {e}")
        show_popup(
            loc.get("layer_restore_error", "Ошибка восстановления слоя: {}").format(str(e)),
            popup_type="error"
        )
        return False


@contextmanager
def layer_context(adoc: object, layer_name: str) -> Generator[None, None, None]:
    """
    Контекстный менеджер для временного переключения активного слоя.

    При входе:  сохраняет текущий слой, активирует layer_name
    При выходе: восстанавливает исходный слой (даже при исключении)

    Исключения внутри блока with НЕ подавляются — они пробрасываются
    после восстановления слоя. Это позволяет вызывающему коду
    обрабатывать ошибки построения самостоятельно.

    Параметры:
        adoc       — COM-объект активного документа AutoCAD
        layer_name — имя слоя для временной активации

    Пример:
        with layer_context(adoc, "schrift"):
            # здесь рисуем текст — слой "schrift" активен
        # здесь слой восстановлен автоматически

    Raises:
        Любое исключение из тела блока with пробрасывается наружу.
    """
    # Сохраняем текущий слой до любых переключений
    try:
        original_layer = adoc.ActiveLayer
    except _COM_ERRORS as e:
        logger.error(f"layer_context: не удалось получить текущий слой: {e}")
        # Не можем сохранить — нет смысла продолжать
        raise

    try:
        if not set_layer(adoc, layer_name):
            logger.warning(f"layer_context: не удалось переключиться на слой '{layer_name}'")
        yield  # выполняем тело блока with
    finally:
        # Восстанавливаем слой в любом случае — и при успехе, и при исключении
        restore_layer(adoc, original_layer)


# ============================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================

if __name__ == "__main__":
    import sys
    import wx

    # Нужен wx.App для show_popup
    _app = wx.App(False)

    print("=== Тест at_base.py ===")

    cad = ATCadInit()

    if not cad.is_initialized():
        show_popup(
            loc.get("cad_init_error_short", "AutoCAD не инициализирован."),
            popup_type="error"
        )
        sys.exit(1)

    autocaddoc = cad.document
    if autocaddoc is None:
        show_popup("Нет активного документа AutoCAD.", popup_type="error")
        sys.exit(1)

    print(f"Документ: {autocaddoc.Name}")

    # --- Тест 1: ensure_layer ---
    print("\n[Тест 1] ensure_layer — создание тестового слоя...")
    test_layer_name = "_AT_BASE_TEST"
    test_layer = ensure_layer(autocaddoc, test_layer_name, color_index=3)
    if test_layer is not None:
        print(f"  OK: слой '{test_layer_name}' создан/получен")
    else:
        print(f"  FAIL: слой '{test_layer_name}' не создан")

    # --- Тест 2: set_layer / restore_layer ---
    print("\n[Тест 2] set_layer / restore_layer...")
    original = autocaddoc.ActiveLayer
    print(f"  Исходный слой: {original.Name}")
    ok = set_layer(autocaddoc, test_layer_name)
    print(f"  set_layer('{test_layer_name}'): {'OK' if ok else 'FAIL'}")
    print(f"  Активный слой сейчас: {autocaddoc.ActiveLayer.Name}")
    ok2 = restore_layer(autocaddoc, original)
    print(f"  restore_layer: {'OK' if ok2 else 'FAIL'}")
    print(f"  Активный слой восстановлен: {autocaddoc.ActiveLayer.Name}")

    # --- Тест 3: layer_context ---
    print("\n[Тест 3] layer_context...")
    print(f"  До: {autocaddoc.ActiveLayer.Name}")
    with layer_context(autocaddoc, test_layer_name):
        print(f"  Внутри: {autocaddoc.ActiveLayer.Name}")
    print(f"  После: {autocaddoc.ActiveLayer.Name}")

    # --- Тест 4: regen ---
    print("\n[Тест 4] regen...")
    ok3 = regen(autocaddoc)
    print(f"  regen: {'OK' if ok3 else 'FAIL'}")

    # --- Тест 5: run_program с несуществующим модулем ---
    print("\n[Тест 5] run_program — несуществующий модуль...")
    result = run_program("programs._nonexistent_module_test_")
    print(f"  Ожидаем None: {'OK' if result is None else 'FAIL'}")

    print("\n=== Тест завершён ===")
    show_popup("Тест at_base.py завершён.\nСм. консоль для результатов.", popup_type="info")