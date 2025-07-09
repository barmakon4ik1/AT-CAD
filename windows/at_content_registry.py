# windows/at_content_registry.py
"""
Модуль для хранения реестра контента AT-CAD.

Содержит словарь CONTENT_REGISTRY, в котором хранятся данные о панелях контента,
включая путь к модулю, метку для отображения
"""

# Словарь с именами модулей контента и их метками для отображения
CONTENT_REGISTRY = {
    "cone": {
        "module": "windows.content_cone",  # Модуль для панели развертки конуса
        "label": "at_run_cone"             # Ключ локализации для отображения названия
    },
    "content_apps": {
        "module": "windows.content_apps",  # Модуль для панели приложений
        "label": "apps_title"             # Ключ локализации для отображения названия
    },
    "rings": {
        "module": "windows.content_rings",  # Модуль для панели ввода параметров колец
        "label": "at_run_rings"            # Ключ локализации для отображения названия
    },
    "head": {
        "module": "windows.content_head",
        "label": "at_run_heads"
    }
}
