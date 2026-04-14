# -*- coding: utf-8 -*-
"""
Файл: programs/at_input.py

Назначение:
    Унифицированный модуль интерактивного ввода данных из AutoCAD.

Поддерживаемый интерактив:
    1. Выбор точки пользователем в AutoCAD (основная задача проекта).

Принцип работы:
    - Основной путь: COM API (Utility.GetPoint)
    - Резервный путь: SendCommand с созданием временного POINT
    - Вся логика LISP-моста исключена

Особенности:
    - Поддерживается возврат координат в виде списка [x, y, z]
    - Поддерживается возврат VARIANT (as_variant=True)
    - Код приведён к состоянию без предупреждений статического анализа
"""

from __future__ import annotations
import time
from typing import Optional, List, Sequence
from _ctypes import COMError
from config.at_cad_init import ATCadInit
from programs.at_com_utils import safe_utility_call
from locales.at_translations import loc
from windows.at_gui_utils import show_popup


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def _get_point_via_sendcommand(document: object, timeout: float = 30.0) -> Optional[List[float]]:
    """
    Резервный способ получения точки через SendCommand.

    Алгоритм:
        - запоминаем количество объектов в ModelSpace
        - отправляем команду POINT
        - ожидаем появления нового объекта
        - читаем координаты
        - удаляем временный объект

    Возвращает:
        [x, y, z] или None
    """
    try:
        modelspace = document.ModelSpace
        initial_count = modelspace.Count
    except (AttributeError, RuntimeError):
        return None

    try:
        document.SendCommand("_POINT\n")
    except (AttributeError, RuntimeError):
        return None

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            current_count = modelspace.Count
        except (AttributeError, RuntimeError):
            return None

        if current_count > initial_count:
            point_entity = None
            coordinates = None

            try:
                point_entity = modelspace.Item(current_count - 1)
                coordinates = list(point_entity.Coordinates)
            except (AttributeError, RuntimeError, OSError):
                return None
            finally:
                if point_entity is not None:
                    try:
                        point_entity.Delete()
                    except (AttributeError, RuntimeError, OSError):
                        pass

            return coordinates

        time.sleep(0.05)

    return None


# ---------------------------------------------------------------------------
# Основной API
# ---------------------------------------------------------------------------

# programs/at_input.py

def _resolve_document(cad: ATCadInit, adoc: object | None) -> object | None:
    """
    Возвращает рабочий документ:
    - если передан adoc и он живой — используем его
    - иначе берём актуальный ActiveDocument через refresh
    """
    if adoc is not None and _is_document_alive(adoc):
        return adoc

    # refresh_active_document обновляет cad.adoc до ActiveDocument
    if not cad.refresh_active_document():
        return None

    return cad.adoc  # уже актуальный после refresh

def _is_document_alive(doc: object) -> bool:
    """Проверяет, что COM-объект документа ещё валиден."""
    try:
        _ = doc.Name          # бросит исключение если документ закрыт
        _ = doc.ModelSpace    # проверяем доступность ModelSpace
        return True
    except (AttributeError, RuntimeError, OSError, COMError):
        return False

def at_get_point(adoc=None, *, prompt=None, as_variant=False, suppress_popups=False):
    """
    Запрашивает у пользователя точку в AutoCAD.

    Параметры:
        adoc            — документ AutoCAD (если None, берётся активный)
        prompt          — текст приглашения
        as_variant      — вернуть VARIANT вместо списка координат
        suppress_popups — не показывать всплывающие окна при ошибках

    Возвращает:
        [x, y, z] | VARIANT | None
    """

    result_point: Optional[List[float]] = None

    cad = ATCadInit()
    if not cad.is_initialized():
        if not suppress_popups:
            show_popup(loc.get("com_failed"), popup_type="error")
        return None

    if adoc is not None and not _is_document_alive(adoc):
        adoc = None

    document = _resolve_document(cad, adoc)

    if document is None:
        if not suppress_popups:
            show_popup(loc.get("com_failed"), popup_type="error")
        return None

    if prompt is None:
        prompt = loc.get("select_point_prompt", "Укажите точку:")

    # Печатаем приглашение
    try:
        document.Utility.Prompt(prompt + "\n")
    except (AttributeError, RuntimeError):
        pass

    # --- Основной путь: COM GetPoint ---
    try:
        point_result = safe_utility_call(
            lambda: document.Utility.GetPoint(),
            as_variant=False
        )

        if isinstance(point_result, Sequence) and len(point_result) >= 2:
            result_point = list(point_result)

    except (AttributeError, RuntimeError, OSError):
        result_point = None

    # --- Резервный путь: SendCommand ---
    if result_point is None:
        result_point = _get_point_via_sendcommand(document)

    if result_point is None:
        if not suppress_popups:
            show_popup(loc.get("point_selection_cancelled"), popup_type="warning")
        return None

    if as_variant:
        return safe_utility_call(lambda: result_point, as_variant=True)

    return result_point


# ---------------------------------------------------------------------------
# Выбор примитива (entity)
# ---------------------------------------------------------------------------

def at_get_entity(
    adoc: object | None = None,
    *,
    prompt: Optional[str] = None,
    use_bridge: bool = False,   # оставлено для совместимости, не используется
    suppress_popups: bool = False,
) -> tuple[object | None, Optional[List[float]], bool, bool, bool]:
    """
    Запрашивает у пользователя выбор одного объекта в AutoCAD.

    Возвращает:
        (entity, pick_point, ok, enter, esc)

    Где:
        entity      — COM-объект выбранной сущности или None
        pick_point  — точка выбора [x,y,z] или None
        ok          — True если объект выбран
        enter       — True если нажат Enter (завершить ввод)
        esc         — True если отмена (Esc)
    """

    cad = ATCadInit()
    if not cad.is_initialized():
        if not suppress_popups:
            show_popup(loc.get("com_failed"), popup_type="error")
        return None, None, False, False, True

    document = _resolve_document(cad, adoc)
    if document is None:
        return None, None, False, False, True

    if prompt is None:
        prompt = "Выберите объект:"

    if use_bridge:
        print("В данной версии не поддерживается")

    # Вывод приглашения в командную строку AutoCAD
    try:
        document.Utility.Prompt(prompt + "\n")
    except RuntimeError:
        pass

    # -------------------------------------------------------------------
    # Основной путь: Utility.GetEntity()
    # -------------------------------------------------------------------
    try:
        result = safe_utility_call(
            lambda: document.Utility.GetEntity(),
            as_variant=False
        )

        if isinstance(result, Sequence) and len(result) >= 1:
            entity = result[0]
            pick_point = list(result[1]) if len(result) > 1 else None
            return entity, pick_point, True, False, False

    except RuntimeError:
        pass

    # -------------------------------------------------------------------
    # Если пользователь нажал Enter — обычно COM бросает исключение
    # Проверим через команду SELECT
    # -------------------------------------------------------------------
    try:
        before = document.ModelSpace.Count
        document.SendCommand("_SELECT\n")
        time.sleep(0.2)
        after = document.ModelSpace.Count

        # Если ничего не выбрано — считаем Enter
        if after == before:
            return None, None, False, True, False

    except RuntimeError:
        pass

    # -------------------------------------------------------------------
    # Отмена (Esc)
    # -------------------------------------------------------------------
    if not suppress_popups:
        show_popup(loc.get("selection_cancelled", "Выбор отменён"), popup_type="info")

    return None, None, False, False, True


# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Тест at_input.py ===")

    autocad = ATCadInit()
    autocaddoc = autocad.document

    selected_point = at_get_point(autocaddoc, as_variant=False)
    print("Результат:", selected_point)
