# ================================================================
# Файл: programs/at_input.py  (обновлённая версия)
# Назначение: Прослойка для ввода данных из AutoCAD (точки, объекты, числа, действия)
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
    "bridge_load_failed": {
        "ru": "Не удалось загрузить LISP-модуль моста.",
        "de": "LISP-Bridge konnte nicht geladen werden.",
        "en": "Failed to load LISP bridge module.",
    },
}
loc.register_translations(_translations)

# ================================================================
# Вспомогательные функции
# ================================================================
def _ensure_lisp_loaded(suppress_logs: bool = False) -> bool:
    """
    Пытается убедиться, что LISP-функции моста загружены в AutoCAD.
    Возвращает True, если, похоже, мост готов к использованию.
    Поддерживает несколько контрактов для programs.lisp_bridge:
      - lisp_bridge.ensure_lisp_loaded()
      - lisp_bridge.load_lisp()
      - lisp_bridge.send_lisp_command("load_lisp")
    Если ничего не найдено — логируем и возвращаем False.
    """
    try:
        if hasattr(lisp_bridge, "ensure_lisp_loaded") and callable(lisp_bridge.ensure_lisp_loaded):
            return bool(lisp_bridge.ensure_lisp_loaded())
        if hasattr(lisp_bridge, "load_lisp") and callable(lisp_bridge.load_lisp):
            return bool(lisp_bridge.load_lisp())
        # fallback: try to call a nominal command that мост может понимать
        if hasattr(lisp_bridge, "send_lisp_command") and callable(lisp_bridge.send_lisp_command):
            try:
                # попытка вызвать специализированную команду "load_lisp" у моста
                resp = lisp_bridge.send_lisp_command("load_lisp")
                # ожидаем хоть какое-то подтверждение
                return bool(resp)
            except Exception:
                # последний шанс: проверить есть ли уже функции (get_point)
                try:
                    test = lisp_bridge.send_lisp_command("ping")  # если мост умеет отвечать
                    return True
                except Exception:
                    pass
    except Exception as e:
        if not suppress_logs:
            logging.debug(f"_ensure_lisp_loaded exception: {e}")
    # не смогли явно загрузить — возвращаем False
    return False


# ================================================================
# Основные функции для AutoCAD-ввода
# ================================================================
def at_get_point(adoc: object = None,
                 as_variant: bool = True,
                 prompt: Optional[str] = None,
                 use_bridge: bool = False,
                 suppress_popups: bool = False) -> Optional[Union[List[float], VARIANT]]:
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
            ok = _ensure_lisp_loaded()
            if not ok:
                logging.debug("LISP bridge не подтверждён как загруженный.")
            result = lisp_bridge.send_lisp_command("get_point")
            if not result:
                if not suppress_popups:
                    print(loc.get("bridge_error_point"))
                return None
            # result может быть словарём с ключом 'point' или прямым списком
            if isinstance(result, dict):
                pt = result.get("point") or result.get("pick") or result.get("p")
            else:
                pt = result
            if not pt:
                if not suppress_popups:
                    print(loc.get("bridge_error_point"))
                return None
            return list(pt) if isinstance(pt, (list, tuple)) else pt
        except Exception as e:
            logging.error(f"Ошибка при получении точки (мост): {e}", exc_info=True)
            if not suppress_popups:
                show_popup(f"{loc.get('bridge_error_point')}\n{e}", popup_type="error")
            return None

    # --- Режим COM ---
    try:
        cad = ATCadInit()
        if not cad.is_initialized():
            if not suppress_popups:
                show_popup(loc.get("com_failed"), popup_type="error")
            return None

        adoc = adoc or cad.document
        if not adoc:
            if not suppress_popups:
                show_popup(loc.get("com_failed"), popup_type="error")
            return None

        if prompt is None:
            prompt = loc.get("select_point_prompt")

        # Вывод промпта и попытка фокусировки UI
        try:
            adoc.Utility.Prompt(prompt + "\n")
        except Exception:
            # не критично
            pass

        try:
            app = adoc.Application
            # явная попытка сделать приложение видимым и восстановить окно
            try:
                app.Visible = True
                # окно: 1=min,2=max,3=normal — некоторым версиям нужен другой набор, поэтому в try
                app.WindowState = 3
            except Exception:
                pass
            # пробуем GetString для фокусировки командной строки (не критично)
            try:
                adoc.Utility.GetString("")
            except Exception:
                pass
        except Exception:
            # если нет Application — не фатально
            pass

        # безопасный вызов GetPoint через обёртку
        point = safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)
        return point

    except Exception as e:
        logging.error(f"Ошибка COM-ввода точки: {e}", exc_info=True)
        if not suppress_popups:
            show_popup(f"{loc.get('bridge_error_point')}: {e}", popup_type="error")
        return None


def at_get_entity(adoc: object = None,
                  prompt: Optional[str] = None,
                  use_bridge: bool = True,
                  suppress_popups: bool = False) -> Tuple[Optional[object], Optional[List[float]], bool, bool, bool]:
    """
    Запрашивает объект у пользователя.
    Если use_bridge=True — через LISP мост (интерактивный ввод в AutoCAD),
    иначе — попытка COM-ввода.

    Возвращает:
        (entity, pick_point, ok, cancelled, error)
    """
    # --- режим LISP-моста ---
    if use_bridge:
        try:
            ok = _ensure_lisp_loaded()
            if not ok:
                logging.debug("LISP bridge не подтверждён как загруженный перед get_entity.")
            result = lisp_bridge.send_lisp_command("get_entity")
            if not result:
                if not suppress_popups:
                    print(loc.get("bridge_error_entity"))
                return None, None, False, False, True

            # Возможные форматы результата:
            #  - dict: {'entity': <handle/oid/...>, 'pick': [x,y,z]}
            #  - tuple/list: (entity, pick)
            if isinstance(result, dict):
                entity = result.get("entity") or result.get("ent") or result.get("handle")
                pick = result.get("pick") or result.get("point") or result.get("p")
            elif isinstance(result, (list, tuple)) and len(result) >= 1:
                entity = result[0]
                pick = result[1] if len(result) > 1 else None
            else:
                entity = result
                pick = None

            if not entity:
                if not suppress_popups:
                    print(loc.get("bridge_error_entity"))
                return None, None, False, False, True

            pick_point = list(pick) if isinstance(pick, (list, tuple)) else None
            return entity, pick_point, True, False, False

        except Exception as e:
            logging.error(f"Ошибка при получении объекта через мост: {e}", exc_info=True)
            if not suppress_popups:
                show_popup(f"{loc.get('bridge_error_entity')}\n{e}", popup_type="error")
            return None, None, False, False, True

    # --- режим COM ---
    try:
        cad = ATCadInit()
        cad.refresh_active_document()
        adoc = adoc or cad.document
        if not adoc:
            if not suppress_popups:
                show_popup(loc.get("com_failed"), popup_type="error")
            return None, None, False, False, True

        if prompt is None:
            prompt = loc.get("select_entity_prompt")

        try:
            adoc.Utility.Prompt(prompt + "\n")
        except Exception:
            pass

        # безопасный вызов GetEntity
        res = safe_utility_call(lambda: adoc.Utility.GetEntity(), as_variant=False)
        # res может быть None, или кортеж (entity, pick), или объект/ошибка
        if res and isinstance(res, tuple) and len(res) >= 2:
            entity = res[0]
            pick = res[1]
            point = list(pick) if pick is not None else None
            return entity, point, True, False, False
        # если res == None — отмена
        if res is None:
            return None, None, False, True, False

        # если вернулся один объект (редко) — считаем успехом без pick
        return res, None, True, False, False

    except Exception as e:
        logging.error(f"Ошибка при выборе объекта через COM: {e}", exc_info=True)
        if not suppress_popups:
            show_popup(f"{loc.get('bridge_error_entity')}: {e}", popup_type="error")
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
