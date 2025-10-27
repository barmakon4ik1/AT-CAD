"""
Файл: at_input.py
Путь: programs/at_input.py

Описание:
Модуль для обработки пользовательского ввода в AutoCAD через COM-интерфейс.
Содержит функции для безопасного запроса точки, выбора объекта и выбора ключевых слов.
Обеспечивает защиту от потери COM-сессии и поддержку локализации.
"""
import logging
from typing import Optional, List, Union, Tuple

import pythoncom
import win32com
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_com_utils import safe_utility_call
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "prompt_select_point": {
        "ru": "Укажите точку: ",
        "de": "Geben Sie einen Punkt an: ",
        "en": "Specify a point: ",
    },
    "prompt_select_entity": {
        "ru": "Выберите объект: ",
        "de": "Wählen Sie ein Objekt aus: ",
        "en": "Select an entity: ",
    },
    "prompt_select_action": {
        "ru": "Действие [0-Продолжить/1-Отменить/2-Завершить] <0>: ",
        "de": "Aktion [0-Weiter/1-Abbrechen/2-Beenden] <0>: ",
        "en": "Action [0-Next/1-Cancel/2-Finish] <0>: ",
    },
    "error_point_input": {
        "ru": "Ошибка при получении точки",
        "de": "Fehler beim Abrufen des Punkts",
        "en": "Error getting point",
    },
    "error_entity_input": {
        "ru": "Ошибка при выборе объекта",
        "de": "Fehler bei der Objektauswahl",
        "en": "Error selecting entity",
    },
    "error_keyword_input": {
        "ru": "Ошибка при вводе ключевого слова",
        "de": "Fehler bei der Schlüsselwort-Eingabe",
        "en": "Error during keyword input",
    },
    "error_action_input": {
        "ru": "Ошибка при выборе действия",
        "de": "Fehler bei der Aktionseingabe",
        "en": "Error during action input",
    },
    "com_failed": {
        "ru": "Не удалось установить соединение с AutoCAD",
        "de": "COM-Verbindung konnte nicht hergestellt werden",
        "en": "Failed to establish COM connection",
    }
}
loc.register_translations(TRANSLATIONS)

# -----------------------------
# Функции ввода
# -----------------------------
def at_point_input(adoc: object = None, as_variant: bool = True, prompt: Optional[str] = None) -> Optional[Union[List[float], VARIANT]]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD с защитой от потери COM-сессии.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument).
        as_variant: Если True — возвращает COM VARIANT (VT_ARRAY | VT_R8),
                    иначе список координат [x, y, z].
        prompt: Текст приглашения (опционально).

    Returns:
        Optional[Union[List[float], VARIANT]]:
            - Точка в виде VARIANT или списка.
            - None, если выбор отменён или COM потерян.
    """
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            show_popup(loc.get("error_point_input") + f": {loc.get('com_failed')}", popup_type="error")
            return None
        adoc = adoc or cad.document

        if prompt is None:
            prompt = loc.get("prompt_select_point")

        adoc.Utility.Prompt(prompt + "\n")
        return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)

    except Exception as e:
        show_popup(loc.get("error_point_input") + f": {str(e)}", popup_type="error")
        return None


def at_entity_input(adoc: object = None, prompt: Optional[str] = None) -> Tuple[Optional[object], Optional[List[float]], bool, bool, bool]:
    """
    Безопасно запрашивает у пользователя выбор объекта в AutoCAD через COM-интерфейс.

    Returns:
        Tuple[Optional[object], Optional[List[float]], bool, bool, bool]:
            - entity: выбранный объект (или None)
            - point: координаты места щелчка [x,y,z] (или None)
            - ok: True, если объект выбран корректно
            - enter: True, если пользователь нажал Enter (без выбора) — это сигнал "завершить выбор"
            - esc: True, если пользователь нажал Esc (отмена)
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()
        adoc = cad.document

        if not adoc:
            logging.error("AutoCAD документ не найден или не инициализирован.")
            return None, None, False, False, False

        if prompt is None:
            prompt = loc.get("prompt_select_entity")
        adoc.Utility.Prompt(prompt + "\n")

        # Прямой вызов GetEntity — safe_utility_call универсален, но GetEntity возвращает (entity, point)
        try:
            res = adoc.Utility.GetEntity()
        except Exception as e:
            hr = getattr(e, "hresult", None)
            # -2147352567 обычно означает операция отменена (Esc) при COM-вызове
            if hr == -2147352567:
                return None, None, False, False, True
            # другие исключения — логируем и пробуем восстановление ниже
            logging.warning(f"GetEntity exception: {e}")
            res = None

        # Если метод вернул значение
        if res:
            # Ожидаем кортеж (entity, pickpoint)
            if isinstance(res, tuple) and len(res) >= 2:
                entity = res[0]
                pick = res[1]
                try:
                    point = list(pick) if pick is not None else None
                except Exception:
                    point = None
                return entity, point, True, False, False
            # Если вернули одиночный объект (маловероятно) — считаем выбранным
            return res, None, True, False, False

        # Если res is None — значит Enter (пользователь нажал Enter без выбора) или метод вернул None
        # Различим Enter от Esc уже выше по исключению; здесь — считаем Enter.
        return None, None, False, True, False

    except Exception as e:
        logging.error(f"{loc.get('error_entity_input')}: {e}")

        # Попытка восстановления COM
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            logging.info(loc.get("com_restored").format(adoc.Name))

            adoc.Utility.Prompt(prompt or loc.get("prompt_select_entity") + "\n")
            res = adoc.Utility.GetEntity()
            if res and isinstance(res, tuple) and len(res) >= 2:
                entity = res[0]
                pick = res[1]
                try:
                    point = list(pick) if pick is not None else None
                except Exception:
                    point = None
                return entity, point, True, False, False
            return None, None, False, True, False

        except Exception as e2:
            logging.error(f"Не удалось восстановить COM после потери соединения: {e2}")
            return None, None, False, False, True


def at_keyword_input(adoc: object = None,
                     prompt: Optional[str] = None,
                     keywords: Optional[List[str]] = None,
                     default: Optional[str] = None) -> str:
    """
    Запрашивает у пользователя выбор ключевого слова через командную строку AutoCAD.

    Args:
        adoc: Объект активного документа AutoCAD.
        prompt: Текст приглашения (опционально).
        keywords: Список допустимых ключевых слов.
        default: Значение по умолчанию (если нажато Enter).

    Returns:
        str: Выбранное ключевое слово ("Продолжить", "Отменить", "Завершить" или "Esc").
    """
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            show_popup(loc.get("error_keyword_input") + f": {loc.get('com_failed')}", popup_type="error")
            return "Esc"
        adoc = adoc or cad.document

        if not keywords:
            keywords = ["Продолжить", "Отменить", "Завершить"] if loc.language == "ru" else ["Next", "Cancel", "Finish"]
        if default is None:
            default = keywords[0]  # "Продолжить" или "Next"

        prompt = prompt or loc.get("prompt_select_action").format(keywords[0], keywords[1], keywords[2])

        adoc.Utility.Prompt(prompt + "\n")
        response = safe_utility_call(lambda: adoc.Utility.GetString(0, prompt))

        if response is None:
            return "Esc"

        response = response.strip()
        try:
            if response and response[0] in ('0', '1', '2'):
                response = int(response[0])
            else:
                response = int(response) if response else 0
        except ValueError:
            if response.lower() in ("", "enter", "cancel"):
                response = 0
            else:
                response = -1

        if response in (0, 1, 2):
            return keywords[response]
        return "Esc"

    except Exception as e:
        show_popup(loc.get("error_keyword_input") + f": {str(e)}", popup_type="error")
        return "Esc"


def at_action_input(adoc: object = None, actions: Optional[List[str]] = None) -> Tuple[str, bool, bool]:
    """
    Позволяет пользователю выбрать одно из действий из списка (через GetString с числовым вводом).

    Args:
        adoc: Активный документ AutoCAD.
        actions: Список возможных действий (например: ["Продолжить", "Отменить", "Завершить"]).

    Returns:
        Tuple[str, bool, bool]:
            - keyword: выбранное действие ("0", "1", "2" или ""),
            - ok: True если выбор сделан корректно,
            - esc: True если отменено (ESC).
    """
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            show_popup(loc.get("error_action_input") + f": {loc.get('com_failed')}", popup_type="error")
            return "", False, True
        adoc = adoc or cad.document

        if not actions:
            actions = ["Продолжить", "Отменить", "Завершить"] if loc.language == "ru" else ["Next", "Cancel", "Finish"]

        prompt = loc.get("prompt_select_action").format(actions[0], actions[1], actions[2])

        adoc.Utility.Prompt(prompt + "\n")
        response = safe_utility_call(lambda: adoc.Utility.GetString(0, prompt))

        if response is None:
            return "", False, True

        response = response.strip()
        try:
            if response and response[0] in ('0', '1', '2'):
                response = int(response[0])
            else:
                response = int(response) if response else 0
        except ValueError:
            if response.lower() in ("", "enter", "cancel"):
                response = 0
            else:
                response = -1

        if response in (0, 1, 2):
            return str(response), True, False
        return "", False, False

    except Exception as e:
        show_popup(loc.get("error_action_input") + f": {str(e)}", popup_type="error")
        return "", False, True


# -----------------------------
# Тестирование при запуске напрямую
# -----------------------------
if __name__ == "__main__":
    cad = ATCadInit()
    doc = cad.document

    # Тест запроса точки
    point = at_point_input(doc, as_variant=False)
    print("Point:", point if point else "Failed")

    # Тест выбора объекта
    entity, point, ok, enter, esc = at_entity_input(doc)
    print("Entity:", entity, "Point:", point, "ok:", ok, "esc:", esc)

    # Тест ключевого слова
    kw = at_keyword_input(doc, keywords=["Продолжить", "Отменить", "Завершить"], default="Продолжить")
    print("Keyword:", kw)

    # Тест выбора действия
    action, ok, esc = at_action_input(doc, ["Продолжить", "Отменить", "Завершить"])
    print("Action:", action, "ok:", ok, "esc:", esc)