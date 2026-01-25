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
from typing import Optional, List, Sequence, Union

from comtypes.automation import VARIANT

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

def at_get_point(
    adoc: object | None = None,
    *,
    prompt: Optional[str] = None,
    as_variant: bool = False,
    suppress_popups: bool = False,
) -> Optional[Union[List[float], VARIANT]]:
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

    document = adoc or cad.document
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
# Тестовый запуск
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Тест at_input.py ===")

    cad = ATCadInit()
    adoc = cad.document

    selected_point = at_get_point(adoc, as_variant=False)
    print("Результат:", selected_point)
