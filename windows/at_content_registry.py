"""
windows/at_content_registry.py
Модуль для хранения реестра контента AT-CAD.
Содержит словарь CONTENT_REGISTRY, в котором хранятся данные о панелях контента,
включая путь к модулю, метку для отображения и модуль построения.
"""

import logging
from programs.at_base import run_program
from locales.at_translations import loc

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    # Ошибки / сообщения
    "content_not_found": {
        "ru": "Контент '{0}' не найден",
        "de": "Inhalt '{0}' nicht gefunden",
        "en": "Content '{0}' not found"
    },
    "no_build_module": {
        "ru": "Для '{0}' не указан build_module",
        "de": "Für '{0}' ist kein build_module angegeben",
        "en": "No build_module specified for '{0}'"
    },

    # Метки для меню (локальные дубли, как в остальных файлах)
    "at_run_cone": {
        "ru": "Конус",
        "de": "Kegel",
        "en": "Cone"
    },
    "apps_title": {
        "ru": "Приложения",
        "de": "Anwendungen",
        "en": "Applications"
    },
    "at_run_rings": {
        "ru": "Кольца",
        "de": "Ringe",
        "en": "Rings"
    },
    "at_run_heads": {
        "ru": "Днище",
        "de": "Boden",
        "en": "Head"
    },
    "at_run_shell": {
        "ru": "Обечайка",
        "de": "Mantel",
        "en": "Shell"
    },
    "at_run_nozzle": {
        "ru": "Отвод",
        "de": "Stutzen",
        "en": "Nozzle"
    },
    "at_run_plate": {
        "ru": "Лист",
        "de": "Platte",
        "en": "Plate"
    },
    "at_run_cutout": {
        "ru": "Вырез",
        "de": "Ausschnitt",
        "en": "Cutout"
    }
}

# Регистрируем локальные переводы
loc.register_translations(TRANSLATIONS)


# Словарь с именами модулей контента, их метками и программами построения
CONTENT_REGISTRY = {
    "cone": {
        "module": "windows.content_cone",
        "label": "at_run_cone",
        "build_module": "programs.at_run_cone"
    },
    "content_apps": {
        "module": "windows.content_apps",
        "label": "apps_title"
    },
    "rings": {
        "module": "windows.content_rings",
        "label": "at_run_rings",
        "build_module": "programs.at_ringe"
    },
    "head": {
        "module": "windows.content_head",
        "label": "at_run_heads",
        "build_module": "programs.at_addhead"
    },
    "plate": {
        "module": "windows.content_plate",
        "label": "at_run_plate",
        "build_module": "programs.at_run_plate"
    },
    "shell": {
        "module": "windows.content_shell",
        "label": "at_run_shell",
        "build_module": "programs.at_cylinder"
    },
    "nozzle": {
        "module": "windows.content_nozzle",
        "label": "at_run_nozzle",
        "build_module": "programs.at_nozzle"
    },
    "cutout": {
        "module": "windows.content_cutout",
        "label": "at_run_cutout",
        "build_module": "programs.at_cutout"
    }
}


def run_build(content_name: str, data=None):
    """
    Унифицированный запуск build_module для указанного контента.

    Args:
        content_name (str): Имя контента из CONTENT_REGISTRY.
        data: Данные для передачи в программу.

    Returns:
        object | None: Результат выполнения build_module или None при ошибке.
    """
    info = CONTENT_REGISTRY.get(content_name)
    if not info:
        # логируем и возвращаем None, сообщение локализовано
        logging.error(loc.get("content_not_found", f"Content '{content_name}' not found").format(content_name))
        return None

    build_module = info.get("build_module")
    if not build_module:
        logging.error(loc.get("no_build_module", f"No build_module specified for '{content_name}'").format(content_name))
        return None

    try:
        return run_program(build_module, data)
    except Exception as e:
        logging.error(f"[at_content_registry] Ошибка при запуске {build_module}: {e}")
        return None
