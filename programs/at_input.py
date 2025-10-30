# ================================================================
# Файл: programs/at_input.py
# Назначение: Прослойка для ввода данных из AutoCAD (точки, объекты, числа, действия)
# Описание:
#     Модуль объединяет функции ввода, которые могут работать
#     либо через COM (основной способ), либо через мост AutoLISP
#     (LISP Bridge), если COM недоступен или требуется интерактивный ввод.
#
#     Язык локализации читается из config/user_language.json.
#     Локализация управляется через locales/at_translations.py.
# ================================================================

import logging
from typing import Optional, Tuple, List, Union
from comtypes.automation import VARIANT

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programs import lisp_bridge
from programs.at_com_utils import safe_utility_call
from windows.at_gui_utils import show_popup


# ================================================================
# Локальные переводы модуля
# ================================================================
_translations = {
    "select_point_prompt": {
        "ru": "Укажите точку:",
        "de": "Wählen Sie einen Punkt:",
        "en": "Select a point:",
    },
    "select_entity_prompt": {
        "ru": "Выберите объект:",
        "de": "Wählen Sie ein Objekt:",
        "en": "Select an entity:",
    },
    "enter_number_prompt": {
        "ru": "Введите число:",
        "de": "Geben Sie eine Zahl ein:",
        "en": "Enter a number:",
    },
    "enter_keyword_prompt": {
        "ru": "Введите ключевое слово:",
        "de": "Geben Sie ein Schlüsselwort ein:",
        "en": "Enter a keyword:",
    },
    "enter_action_prompt": {
        "ru": "Выберите действие:",
        "de": "Wählen Sie eine Aktion:",
        "en": "Select an action:",
    },
    "bridge_error_point": {
        "ru": "Ошибка: не удалось получить точку через мост.",
        "de": "Fehler: Punkt konnte über Bridge nicht empfangen werden.",
        "en": "Error: failed to get point through bridge.",
    },
    "bridge_error_entity": {
        "ru": "Ошибка: не удалось получить объект через мост.",
        "de": "Fehler: Objekt konnte über Bridge nicht empfangen werden.",
        "en": "Error: failed to get entity through bridge.",
    },
    "com_failed": {
        "ru": "AutoCAD недоступен или не инициализирован.",
        "de": "AutoCAD ist nicht verfügbar oder wurde nicht initialisiert.",
        "en": "AutoCAD is not available or not initialized.",
    },
    "invalid_input": {
        "ru": "Некорректный ввод.",
        "de": "Ungültige Eingabe.",
        "en": "Invalid input.",
    },
}
loc.register_translations(_translations)


# ================================================================
# Основные функции для AutoCAD-ввода
# ================================================================
def at_get_point(adoc: object = None,
                 as_variant: bool = True,
                 prompt: Optional[str] = None,
                 use_bridge: bool = False) -> Optional[Union[List[float], VARIANT]]:
    """
    Запрашивает точку у пользователя.
    Если use_bridge=True — через LISP мост (интерактивный ввод в AutoCAD),
    иначе — через COM.

    Возвращает:
        [x, y, z] — если успешно,
        None — при ошибке или отмене.
    """
    # --- Режим моста ---
    if use_bridge:
        try:
            result = lisp_bridge.send_lisp_command("get_point")
            if not result or "point" not in result:
                print(loc.get("bridge_error_point"))
                return None
            return result["point"]
        except Exception as e:
            logging.error(f"Ошибка при получении точки (мост): {e}")
            return None

    # --- Режим COM ---
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            show_popup(loc.get("com_failed"), popup_type="error")
            return None

        adoc = adoc or cad.document
        if not adoc:
            show_popup(loc.get("com_failed"), popup_type="error")
            return None

        if prompt is None:
            prompt = loc.get("select_point_prompt")

        adoc.Utility.Prompt(prompt + "\n")

        # Вызов безопасного COM-ввода
        point = safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)
        return point

    except Exception as e:
        logging.error(f"Ошибка COM-ввода точки: {e}")
        show_popup(f"{loc.get('bridge_error_point')}: {e}", popup_type="error")
        return None


def at_get_entity(adoc: object = None,
                  prompt: Optional[str] = None,
                  use_bridge: bool = True) -> Tuple[Optional[object], Optional[List[float]], bool, bool, bool]:
    """
    Запрашивает объект у пользователя.
    Если use_bridge=True — через LISP мост (интерактивный ввод в AutoCAD),
    иначе — попытка COM-ввода.

    Возвращает:
        (entity, pick_point, ok, cancelled, error)
    """
    if use_bridge:
        try:
            result = lisp_bridge.send_lisp_command("get_entity")
            if not result or "entity" not in result:
                print(loc.get("bridge_error_entity"))
                return None, None, False, False, True
            return result["entity"], None, True, False, False
        except Exception as e:
            logging.error(f"Ошибка при получении объекта через мост: {e}")
            return None, None, False, False, True
    else:
        try:
            cad = ATCadInit()
            cad.refresh_active_document()
            adoc = cad.document
            if not adoc:
                show_popup(loc.get("com_failed"), popup_type="error")
                return None, None, False, False, True

            if prompt is None:
                prompt = loc.get("select_entity_prompt")

            adoc.Utility.Prompt(prompt + "\n")

            res = adoc.Utility.GetEntity()
            if res and isinstance(res, tuple) and len(res) >= 2:
                entity = res[0]
                pick = res[1]
                point = list(pick) if pick is not None else None
                return entity, point, True, False, False
            return None, None, False, True, False

        except Exception as e:
            logging.error(f"Ошибка при выборе объекта через COM: {e}")
            return None, None, False, False, True


# ================================================================
# Универсальные функции ввода (CLI)
# ================================================================
def keyword_input(prompt_key="enter_keyword_prompt", keywords=None):
    prompt = loc.get(prompt_key)
    if keywords:
        prompt += " [" + "/".join(keywords) + "]: "
    value = input(prompt).strip().lower()
    if not keywords or value in [k.lower() for k in keywords]:
        return value
    print(loc.get("invalid_input"))
    return None


def numeric_input(prompt_key="enter_number_prompt", cast_func=float):
    prompt = loc.get(prompt_key) + " "
    value = input(prompt).strip().replace(",", ".")
    try:
        return cast_func(value)
    except Exception:
        print(loc.get("invalid_input"))
        return None


def action_input(actions: dict):
    print(loc.get("enter_action_prompt"))
    for key, (desc, _) in actions.items():
        print(f"  {key}. {desc}")
    choice = input("→ ").strip()
    if choice in actions:
        func = actions[choice][1]
        if callable(func):
            return func()
        else:
            logging.error(f"Действие '{choice}' не является функцией.")
    else:
        print(loc.get("invalid_input"))
    return None


# ================================================================
# Тестовый запуск (для проверки моста)
# ================================================================
if __name__ == "__main__":
    print("=== Тест модуля at_input.py ===")

    print("\nПопытка получить точку через COM...")
    pt = at_get_point(use_bridge=False, as_variant=False)
    print("Результат точки:", pt)

    print("\nПопытка получить объект через COM...")
    ent = at_get_entity(use_bridge=False)
    print("Результат объекта:", ent)

    print("\nПопытка получить точку через мост...")
    pt2 = at_get_point(use_bridge=True)
    print("Результат (мост):", pt2)
