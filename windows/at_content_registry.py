"""
windows/at_content_registry.py
Модуль для хранения реестра контента AT-CAD.
Содержит словарь CONTENT_REGISTRY, в котором хранятся данные о панелях контента,
включая путь к модулю, метку для отображения и модуль построения.
"""

import logging
from programs.at_base import run_program
from locales.at_translations import loc
from importlib import import_module

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
    },
    "at_run_eccentric": {
        "ru": "Эксцентричный конус",
        "de": "Exzentrischer Kegel",
        "en": "Eccentric Cone"
    },
    "at_run_cone_pipe": {
        "ru": "Конусный отвод",
        "de": "Kegelpassung",
        "en": "Cone fitting"
    },
    "at_name_plate": {
        "ru": "Мостики для табличек",
        "en": "Name Plates Bracket",
        "de": "Typenschildträger"
    },
    "footer_hint_default": {
        "ru": "Выберите модуль для начала работы",
        "de": "Wählen Sie ein Modul, um zu beginnen",
        "en": "Select a module to start working"
    },
    "at_info": {
        "ru": "Инфо о примитиве(ах)",
        "de": "Info ü. Objekt(en)",
        "en": "Info about entity(ies)"
    },
    "footer_hint_cone": {
        "ru": "Построение развертки прямого и усеченного конуса",
        "de": "Abwicklung eines geraden oder abgestumpften Kegels",
        "en": "Development of a straight or truncated cone"
    },

    "footer_hint_shell": {
        "ru": "Развертка цилиндрической обечайки",
        "de": "Abwicklung eines zylindrischen Mantels",
        "en": "Cylindrical shell development"
    },

    "footer_hint_plate": {
        "ru": "Работа с плоскими листовыми заготовками",
        "de": "Arbeiten mit ebenen Blechzuschnitten",
        "en": "Flat plate operations"
    },

    "footer_hint_vessel_name": {
        "ru": "Создание и управление табличками оборудования",
        "de": "Erstellung und Verwaltung von Typenschildern",
        "en": "Create and manage equipment name plates"
    },

    "at_run_slotted_hole": {
        "ru": "Продолговатое отверстие",
        "de": "Langloch",
        "en": "Slotted hole"
    },
    "footer_hint_slotted_hole": {
        "ru": "Построение продолговатого отверстия",
        "de": "Langloch zeichnen",
        "en": "Draw slotted hole"
    },
    "at_run_plate_with_holes": {
        "ru": "Пластина с отверстиями",
        "de": "Platte mit Löchern",
        "en": "Plate with hole"
    },

}

# Регистрируем локальные переводы
loc.register_translations(TRANSLATIONS)


# Словарь с именами модулей контента, их метками и программами построения
"""
    Записи в регистре на примере продолговатого отверстия:
    
    Ключ "slotted_hole" — это имя модуля, по которому вся система его находит. Внутри:

    "module" — путь к файлу диалогового окна. Отсюда импортируется open_dialog().
    "label" — ключ локализации. По нему content_apps.py берёт текст ссылки в списке модулей (loc.get("at_run_slotted_hole") → "Продолговатое отверстие").
    "footer_hint" — ключ локализации для подсказки в футере главного окна. Обновляется через update_footer_hint().
    "type": "dialog" — говорит run_build() что это модальное окно, а не встраиваемая панель.
    "build_module" — путь к модулю построения. После того как диалог вернул словарь, run_build() вызывает main() именно отсюда.
"""
CONTENT_REGISTRY = {
    "cone": {
        "module": "windows.content_cone",
        "label": "at_run_cone",
        "footer_hint": "footer_hint_cone",
        "build_module": "programs.at_run_cone"
    },
    "content_apps": {
        "module": "windows.content_apps",
        "label": "apps_title",
        "footer_hint": "footer_hint_default"
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
        "footer_hint": "footer_hint_plate",
        "build_module": "programs.at_run_plate"
    },
    "shell": {
        "module": "windows.content_shell",
        "label": "at_run_shell",
        "footer_hint": "footer_hint_shell",
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
    },
    "eccentric_reducer": {
        "module": "windows.content_eccentric",
        "label": "at_run_eccentric",
        "build_module": "programs.at_run_ecc_red"
    },
    "cone_pipe": {
        "module": "windows.content_cone_pipe",
        "label": "at_run_cone_pipe",
        "build_module": "programs.at_nozzle_cone",
    },
    "vessel_name": {
        "module": "windows.content_bracket",
        "label": "at_name_plate",
        # "build_module": "windows.nameplate_dialog",
    },
    "info": {
        "module": "windows.at_entity_inspector",
        "label": "at_info",
        "type": "dialog",
        "build_module": "None",
    },
    "slotted_hole": {
        "module": "windows.slotted_hole_dialog",
        "label": "at_run_slotted_hole",
        "footer_hint": "footer_hint_slotted_hole",
        "type": "dialog",
        "build_module": "programs.at_slotted_hole",
    },
    "plate_with_holes": {
        "module": "windows.content_rect_plate",
        "label": "at_run_plate_with_holes",
        "build_module": "programs.at_rect_plate",
    }
}


def run_build(content_name: str, data=None, parent=None):
    """
    Унифицированный запуск build_module для указанного контента.

    Args:
        content_name (str): Имя контента из CONTENT_REGISTRY.
        data: Данные для передачи в программу.
        parent: Родительское окно
    Returns:
        object | None: Результат выполнения build_module или None при ошибке.
    """
    info = CONTENT_REGISTRY.get(content_name)
    if not info:
        # логируем и возвращаем None, сообщение локализовано
        logging.error(loc.get("content_not_found", f"Content '{content_name}' not found").format(content_name))
        return None

    content_type = info.get("type", "content")

    # ====== КОНТЕНТ ======
    if content_type == "content":
        build_module = info.get("build_module")
        if not build_module:
            logging.error(loc.get("no_build_module").format(content_name))
            return None
        return run_program(build_module, data)
   # ====== ДИАЛОГ ======
    elif content_type == "dialog":

        mod = import_module(info["module"])
        if not hasattr(mod, "open_dialog"):
            raise RuntimeError(f"{info['module']} must define open_dialog(parent) -> dict | None")

        data = mod.open_dialog(parent)

        if data is not None:
            build_module_path = info.get("build_module")
            if build_module_path:
                return run_program(build_module_path, data)
            else:
                logging.warning(f"dialog '{content_name}' вернул данные, но build_module не указан")

        return None
    return None

