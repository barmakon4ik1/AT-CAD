"""
windows/at_content_registry.py
Модуль для хранения реестра контента AT-CAD.
Содержит словарь CONTENT_REGISTRY, в котором хранятся данные о панелях контента,
включая путь к модулю, метку для отображения и модуль построения.
"""

# Словарь с именами модулей контента, их метками и программами построения
CONTENT_REGISTRY = {
    "cone": {
        "module": "windows.content_cone",
        "label": "at_run_cone",
        "build_module": "programms.at_run_cone"
    },
    "content_apps": {
        "module": "windows.content_apps",
        "label": "apps_title"
    },
    "rings": {
        "module": "windows.content_rings",
        "label": "at_run_rings",
        "build_module": "programms.at_ringe"
    },
    "head": {
        "module": "windows.content_head",
        "label": "at_run_heads",
        "build_module": "programms.at_addhead"
    },
    "plate": {
        "module": "windows.content_plate",
        "label": "at_run_plate",
        "build_module": "programms.at_run_plate"
    }
}
