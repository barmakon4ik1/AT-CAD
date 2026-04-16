# -*- coding: utf-8 -*-
"""
Файл: programs/at_input.py

Назначение:
    Унифицированный модуль интерактивного ввода данных из AutoCAD.

Поддерживаемый интерактив:
    1. Выбор точки пользователем в AutoCAD — at_get_point()
    2. Выбор одного примитива — at_get_entity()

Принцип работы:
    - Основной путь: COM API (Utility.GetPoint / Utility.GetEntity)
    - Резервный путь для GetPoint: SendCommand с созданием временного POINT
    - Вся логика LISP-моста исключена

Работа при смене документа:
    Перед каждым интерактивным вводом вызывается _resolve_document(),
    которая через cad.refresh_active_document() получает актуальный
    ActiveDocument. Это позволяет без ошибок переключаться между
    чертежами прямо во время работы программы — GetPoint/GetEntity
    всегда адресуются к тому документу, который видит пользователь.

    Если передан явный adoc — он проверяется на живость (_is_document_alive).
    Если закрыт — автоматически используется текущий ActiveDocument.

Особенности:
    - Поддерживается возврат координат в виде списка [x, y, z]
    - Поддерживается возврат VARIANT (as_variant=True)
    - Код приведён к состоянию без предупреждений статического анализа
"""

from __future__ import annotations

import time
from typing import Optional, List, Sequence, Union

import pythoncom
from comtypes.automation import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_com_utils import safe_utility_call
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# ---------------------------------------------------------------------------
# Внутренние вспомогательные функции
# ---------------------------------------------------------------------------

def _is_document_alive(doc: object) -> bool:
    """
    Проверяет, что COM-объект документа ещё валиден.

    Обращается к двум атрибутам:
        Name       — бросает исключение, если объект закрыт или стал zombie
        ModelSpace — проверяет доступность пространства модели

    Возвращает:
        True  — документ живой, с ним можно работать
        False — документ закрыт или COM-объект протух

    Используется в _resolve_document() для проверки явно переданного adoc.
    """
    try:
        _ = doc.Name          # noqa: F841  — нужен сам вызов, результат не важен
        _ = doc.ModelSpace    # noqa: F841
        return True
    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        return False


def _resolve_document(cad: ATCadInit, adoc: object | None) -> object | None:
    """
    Центральная точка получения рабочего документа перед интерактивным вводом.

    Логика:
        1. Если передан явный adoc и он живой — используем его как есть.
           Это нужно для сценариев, где вызывающий код осознанно работает
           с конкретным документом.
        2. Иначе вызываем cad.refresh_active_document(), который:
              - подхватывает текущий acad.ActiveDocument
              - при необходимости выполняет reconnect()
              - заменяет протухший self.adoc новым COM-объектом
        3. Если обычное обновление не помогло — делаем ещё одну попытку через
           жёсткий reconnect() и повторную актуализацию документа.

    Параметры:
        cad  — экземпляр ATCadInit
        adoc — явно переданный документ или None

    Возвращает:
        COM-объект документа или None, если:
            - AutoCAD недоступен
            - нет открытых документов
            - переподключение не удалось

    Важно:
        Эта функция намеренно не доверяет старому cad.adoc без проверки.
        После переключения листа/документа старый COM-объект может стать
        невалидным, поэтому перед интерактивным вводом всегда выполняется
        попытка актуализации.
    """
    if adoc is not None and _is_document_alive(adoc):
        return adoc

    if cad.refresh_active_document():
        if cad.adoc is not None and _is_document_alive(cad.adoc):
            return cad.adoc

    try:
        cad = ATCadInit.reconnect()
        if cad.refresh_active_document():
            if cad.adoc is not None and _is_document_alive(cad.adoc):
                return cad.adoc
    except Exception:
        pass

    return None


def _get_point_via_sendcommand(document: object, timeout: float = 30.0) -> Optional[List[float]]:
    """
    Резервный способ получения точки через SendCommand.

    Используется, если Utility.GetPoint() вернул None или бросил исключение.
    Работает через создание временного примитива POINT в ModelSpace:
        - запоминаем количество объектов
        - отправляем команду _POINT
        - ожидаем появления нового объекта (пользователь кликнул)
        - читаем координаты из объекта
        - удаляем временный объект (чертёж не должен засоряться)

    Параметры:
        document — COM-объект активного документа
        timeout  — максимальное время ожидания клика в секундах

    Возвращает:
        [x, y, z] или None (таймаут / ошибка / пользователь отменил)

    Примечание:
        Этот путь медленнее и менее надёжен, чем GetPoint. Использовать
        только как fallback. При отмене (Esc) AutoCAD не создаёт объект,
        поэтому цикл дождётся таймаута — учитывай при выборе timeout.
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
                # Удаляем временный объект в любом случае, даже при ошибке чтения
                if point_entity is not None:
                    try:
                        point_entity.Delete()
                    except (AttributeError, RuntimeError, OSError):
                        pass

            return coordinates

        time.sleep(0.05)

    return None


# ---------------------------------------------------------------------------
# Основной API — выбор точки
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

    Алгоритм:
        1. Получаем актуальный документ через _resolve_document().
           Это обязательно делается ДО любой проверки готовности, чтобы не
           обращаться к устаревшему self.adoc после переключения листа
           или документа.
        2. Выводим приглашение в командную строку AutoCAD.
        3. Пытаемся получить точку через Utility.GetPoint() — основной путь.
        4. Если COM-вызов сорвался (например, из-за смены активного документа
           или развала RPC-контекста), выполняем reconnect() и пробуем ещё раз.
        5. Если основной путь не дал результат — используем резервный путь
           через SendCommand + временный POINT.

    Параметры:
        adoc            — документ AutoCAD; если None, берётся текущий ActiveDocument.
                          Если переданный документ уже невалиден, автоматически
                          используется текущий активный документ.
        prompt          — текст приглашения в командной строке AutoCAD.
        as_variant      — вернуть VARIANT вместо списка координат.
        suppress_popups — не показывать всплывающие окна при ошибках и отмене.

    Возвращает:
        [x, y, z]  — координаты выбранной точки
        VARIANT    — если as_variant=True
        None       — пользователь отменил ввод, AutoCAD недоступен или ввод не удался

    Важно:
        Функция не полагается на ранее сохранённый документ из singleton.
        Перед каждым интерактивным вводом она заново получает актуальный
        ActiveDocument, что позволяет безопаснее переживать переключение
        листов и чертежей.
    """
    result_point: Optional[List[float]] = None

    cad = ATCadInit()

    # Сначала получаем актуальный документ, только потом считаем COM готовым.
    document = _resolve_document(cad, adoc)
    if document is None:
        if not suppress_popups:
            show_popup(loc.get("com_failed"), popup_type="error")
        return None

    if prompt is None:
        prompt = loc.get("select_point_prompt", "Укажите точку:")

    try:
        document.Utility.Prompt(prompt + "\n")
    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        pass

    # --- Основной путь: COM Utility.GetPoint ---
    try:
        point_result = safe_utility_call(
            lambda: document.Utility.GetPoint(),
            as_variant=False
        )

        if isinstance(point_result, Sequence) and len(point_result) >= 2:
            result_point = list(point_result)

    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        # COM-контекст мог устареть в момент интерактивного вызова.
        # Пробуем один раз переподключиться и запросить точку повторно.
        try:
            cad = ATCadInit.reconnect()
            document = _resolve_document(cad, None)

            if document is not None:
                point_result = safe_utility_call(
                    lambda: document.Utility.GetPoint(),
                    as_variant=False
                )

                if isinstance(point_result, Sequence) and len(point_result) >= 2:
                    result_point = list(point_result)

        except Exception:
            result_point = None

    # --- Резервный путь: SendCommand + временный POINT ---
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

    Алгоритм:
        1. Получаем актуальный документ через _resolve_document().
           Это делается до любых проверок состояния singleton, чтобы не
           обращаться к устаревшему self.adoc после переключения листа,
           пространства или документа.
        2. Выводим приглашение в командную строку AutoCAD.
        3. Пытаемся выбрать объект через Utility.GetEntity().
        4. Если основной COM-вызов сорвался, выполняем reconnect() и
           повторяем попытку на заново полученном ActiveDocument.
        5. Если выбор не удался, используем эвристику Enter vs Esc через _SELECT.

    Параметры:
        adoc            — документ AutoCAD; если None, берётся текущий ActiveDocument
        prompt          — текст приглашения
        use_bridge      — устаревший параметр, сохранён для совместимости
        suppress_popups — не показывать окно при отмене

    Возвращает:
        Кортеж (entity, pick_point, ok, enter, esc):
            entity      — выбранная сущность или None
            pick_point  — точка выбора [x, y, z] или None
            ok          — True, если объект успешно выбран
            enter       — True, если пользователь завершил ввод Enter
            esc         — True, если была отмена Esc или ошибка

    Важно:
        Функция не должна работать со старым закэшированным документом без
        проверки. Перед каждым интерактивным выбором документ заново
        актуализируется через AutoCAD.ActiveDocument.
    """
    cad = ATCadInit()

    document = _resolve_document(cad, adoc)
    if document is None:
        if not suppress_popups:
            show_popup(loc.get("com_failed"), popup_type="error")
        return None, None, False, False, True

    if prompt is None:
        prompt = loc.get("select_entity_prompt", "Выберите объект:")

    if use_bridge:
        # Параметр устарел; в прошлых версиях активировал LISP-мост.
        pass

    try:
        document.Utility.Prompt(prompt + "\n")
    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        pass

    # --- Основной путь: Utility.GetEntity() ---
    try:
        result = safe_utility_call(
            lambda: document.Utility.GetEntity(),
            as_variant=False
        )

        if isinstance(result, Sequence) and len(result) >= 1:
            entity = result[0]
            pick_point = list(result[1]) if len(result) > 1 else None
            return entity, pick_point, True, False, False

    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        # Если COM-контекст сорвался, пробуем один reconnect и повторяем.
        try:
            cad = ATCadInit.reconnect()
            document = _resolve_document(cad, None)

            if document is not None:
                result = safe_utility_call(
                    lambda: document.Utility.GetEntity(),
                    as_variant=False
                )

                if isinstance(result, Sequence) and len(result) >= 1:
                    entity = result[0]
                    pick_point = list(result[1]) if len(result) > 1 else None
                    return entity, pick_point, True, False, False

        except Exception:
            pass

    # --- Эвристика: Enter vs Esc ---
    try:
        before = document.ModelSpace.Count
        document.SendCommand("_SELECT\n")
        time.sleep(0.2)
        after = document.ModelSpace.Count

        if after == before:
            return None, None, False, True, False

    except (AttributeError, RuntimeError, OSError, pythoncom.com_error):
        pass

    if not suppress_popups:
        show_popup(loc.get("selection_cancelled", "Выбор отменён"), popup_type="info")

    return None, None, False, False, True


# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Тест at_input.py ===")

    # Получаем экземпляр singleton — подключается к запущенному AutoCAD
    autocad = ATCadInit()

    if not autocad.is_initialized():
        print("AutoCAD не найден или нет открытых документов.")
    else:
        # None в качестве adoc — функция сама возьмёт текущий ActiveDocument
        selected_point = at_get_point(None, prompt="Кликни точку для теста:")
        print("Результат:", selected_point)
