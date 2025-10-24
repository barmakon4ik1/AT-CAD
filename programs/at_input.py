"""
Файл: at_input.py
Путь: programs/at_input.py

Описание:
Модуль для обработки пользовательского ввода в AutoCAD через COM-интерфейс.
Содержит функции для безопасного запроса точки, выбора объекта и выбора ключевых слов.
Обеспечивает защиту от потери COM-сессии и поддержку локализации.
"""

import logging
import time

import pythoncom
import win32com.client
from typing import Optional, List, Union, Tuple
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_com_utils import safe_utility_call
from locales.at_translations import loc


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
        "ru": "Действие [0-Далее/1-Назад/2-Завершить] <0>: ",
        "de": "Aktion [0-Weiter/1-Zurück/2-Beenden] <0>: ",
        "en": "Action [0-Next/1-Back/2-Finish] <0>: ",
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
    "com_restored": {
        "ru": "COM-сессия восстановлена, активный документ: {0}",
        "de": "COM-Sitzung wiederhergestellt, aktives Dokument: {0}",
        "en": "COM session restored, active document: {0}",
    },
    "action_selected": {
        "ru": "Выбранное действие: '{}'",
        "de": "Ausgewählte Aktion: '{}'",
        "en": "Selected action: '{}'"
    },
    "invalid_action": {
        "ru": "Ошибка: Неверное действие '{}'. Доступные действия: 0, 1, 2.",
        "de": "Fehler: Ungültige Aktion '{}'. Verfügbare Aktionen: 0, 1, 2.",
        "en": "Error: Invalid action '{}'. Available actions: 0, 1, 2."
    },
    "action_input_error": {
        "ru": "Ошибка ввода действия (возможно, нажат Esc). Считаем 'Прервать'.",
        "de": "Fehler bei der Aktionseingabe (möglicherweise Esc gedrückt). Als 'Abbrechen' gewertet.",
        "en": "Action input error (possibly Esc pressed). Considered as 'Abort'."
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
            - None, если выбор отменён или COM потерян окончательно.
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()

        adoc = cad.document
        if not adoc:
            logging.error("AutoCAD документ не найден или не инициализирован.")
            return None

        if prompt is None:
            prompt = loc.get("prompt_select_point")

        adoc.Utility.Prompt(prompt + "\n")
        return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)

    except Exception as e:
        logging.error(f"{loc.get('error_point_input')}: {e}")

        # Попытка восстановить COM-подключение
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            logging.info(loc.get("com_restored").format(adoc.Name))

            adoc.Utility.Prompt(prompt or loc.get("prompt_select_point") + "\n")
            return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)

        except Exception as e2:
            logging.error(f"Не удалось восстановить COM после потери соединения: {e2}")
            return None


def at_entity_input(adoc: object = None, prompt: Optional[str] = None) -> Tuple[Optional[object], Optional[List[float]], bool, bool]:
    """
    Безопасно запрашивает у пользователя выбор объекта в AutoCAD через COM-интерфейс.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument).
        prompt: Текст приглашения (опционально).

    Returns:
        Tuple[Optional[object], Optional[List[float]], bool, bool]:
            - Первый элемент: выбранный объект (или None).
            - Второй элемент: координаты точки выбора [x, y, z] (или None).
            - Третий элемент: True, если выбор выполнен успешно.
            - Четвёртый элемент: True, если пользователь нажал ESC или Enter без выбора.
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()
        adoc = cad.document

        if not adoc:
            logging.error("AutoCAD документ не найден или не инициализирован.")
            return None, None, False, False

        if prompt is None:
            prompt = loc.get("prompt_select_entity")
        adoc.Utility.Prompt(prompt + "\n")

        # Непосредственный вызов COM-функции без safe_utility_call
        try:
            result = adoc.Utility.GetEntity()
        except Exception as e:
            if e.args and e.args[0] == -2147352567:  # ESC
                return None, None, False, True
            raise

        if not result or len(result) < 2:
            return None, None, False, True

        entity, picked_point = result
        # picked_point может быть VARIANT (x, y, z)
        point_list = list(picked_point) if picked_point is not None else None

        return entity, point_list, True, False

    except Exception as e:
        logging.error(f"{loc.get('error_entity_input')}: {e}")

        # Попытка восстановления COM
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            logging.info(loc.get("com_restored").format(adoc.Name))

            adoc.Utility.Prompt(prompt or loc.get("prompt_select_entity") + "\n")
            result = adoc.Utility.GetEntity()
            if not result or len(result) < 2:
                return None, None, False, True

            entity, picked_point = result
            point_list = list(picked_point) if picked_point is not None else None
            return entity, point_list, True, False

        except Exception as e2:
            logging.error(f"Не удалось восстановить COM после потери соединения: {e2}")
            return None, None, False, True


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
        str: Выбранное ключевое слово, "Esc" — если нажато ESC.
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()
        adoc = cad.document

        if not adoc:
            logging.error("AutoCAD документ не найден или не инициализирован.")
            return "Esc"

        if not keywords:
            keywords = ["Continue", "Finish", "Abort"]
        if default is None:
            default = "Finish"

        prompt = prompt or f"\n[{ '/'.join(keywords) }] <{default}>: "

        adoc.Utility.InitializeUserInput(0, " ".join(keywords))
        kw = safe_utility_call(lambda: adoc.Utility.GetKeyword(prompt))
        if not kw:
            return default
        return kw

    except Exception as e:
        if e.args and e.args[0] == -2147352567:
            return "Esc"
        logging.error(f"{loc.get('error_keyword_input')}: {e}")

        # Попытка восстановления COM
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            logging.info(loc.get("com_restored").format(adoc.Name))

            adoc.Utility.InitializeUserInput(0, " ".join(keywords))
            kw = safe_utility_call(lambda: adoc.Utility.GetKeyword(prompt))
            if not kw:
                return default
            return kw

        except Exception as e2:
            logging.error(f"Не удалось восстановить COM после потери соединения: {e2}")
            return "Esc"


def at_action_input(adoc: object = None, actions: Optional[List[str]] = None) -> Tuple[str, bool, bool]:
    """
    Позволяет пользователю выбрать одно из действий из списка (через GetString с числовым вводом).
    Работает с поддержкой ESC, ENTER и локализованных подсказок.

    Args:
        adoc: Активный документ AutoCAD.
        actions: Список возможных действий (например: ["Далее", "Назад", "Завершить"] для ru).

    Returns:
        Tuple[str, bool, bool]:
            - keyword: выбранное действие ("0", "1", "2" или "" при ESC/Enter),
            - ok: True если выбор сделан корректно,
            - esc: True если отменено (ESC).
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()
        adoc = cad.document
        if not adoc:
            print("AutoCAD документ не найден или не инициализирован.")
            return "", False, True

        if not actions:
            actions = ["Далее", "Назад", "Завершить"] if loc.language == "ru" else ["Next", "Back", "Finish"]

        # Формируем локализованную подсказку с числами
        prompt = loc.get("prompt_select_action").format(actions[0], actions[1], actions[2])

        # Сбрасываем командную строку
        adoc.SendCommand("._\n")
        time.sleep(0.2)  # Задержка для стабилизации

        # Выводим подсказку
        adoc.Utility.Prompt(prompt + "\n")

        # Запрашиваем строку и преобразуем в число
        response = adoc.Utility.GetString(1, prompt).strip()
        try:
            response = int(response) if response else 0
        except ValueError:
            response = -1
        print(loc.get("action_selected").format(response if response != -1 else "<Неверный ввод>"))

        if response in (0, 1, 2):
            return str(response), True, False
        else:
            print(loc.get("invalid_action").format(response if response != -1 else "<Неверный ввод>"))
            return "", False, False

    except Exception as e:
        error_code = e.args[0] if e.args else None
        if error_code == -2147352567:  # ESC
            print(loc.get("action_input_error"))
            return "", False, True
        print(f"Ошибка в at_action_input: {e}")

        # Попытка восстановления COM
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            print(loc.get("com_restored").format(adoc.Name))

            adoc.SendCommand("._\n")
            time.sleep(0.2)
            adoc.Utility.Prompt(prompt + "\n")
            response = adoc.Utility.GetString(1, prompt).strip()
            try:
                response = int(response) if response else 0
            except ValueError:
                response = -1
            print(loc.get("action_selected").format(response if response != -1 else "<Неверный ввод>"))

            if response in (0, 1, 2):
                return str(response), True, False
            else:
                print(loc.get("invalid_action").format(response if response != -1 else "<Неверный ввод>"))
                return "", False, False

        except Exception as e2:
            print(f"Не удалось восстановить COM после потери соединения: {e2}")
            return "", False, True


# -----------------------------
# Тестирование при запуске напрямую
# -----------------------------
if __name__ == "__main__":
    cad = ATCadInit()
    doc = cad.document

    # Тест запроса точки
    # point = at_point_input(doc, as_variant=False)
    # print("Point:", point)

    # Тест выбора объекта
    # entity, point, ok, esc = at_entity_input(doc)
    # print("Entity:", entity, "Point:", point, "ok:", ok, "esc:", esc)

    # Тест ключевого слова
    # kw = at_keyword_input(doc, "Тест ключевого слова [Yes/No] <Yes>: ", ["Yes", "No"], "Yes")
    # print("Keyword:", kw)

    # Тест выбора действия
    print("=== Тест выбора действия ===")
    action, ok, esc = at_action_input(doc, ["Next", "Back", "Finish"])
    print("Action:", action, "ok:", ok, "esc:", esc)
