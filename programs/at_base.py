# programs/at_base.py
"""
Файл: at_base.py
Путь: programs/at_base.py

Описание:
Модуль для базовых операций с AutoCAD через COM-интерфейс.
Предоставляет функции для управления слоями и обновления видового экрана.
"""

from contextlib import contextmanager

import win32com.client
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from programs.at_geometry import ensure_point_variant
from windows.at_gui_utils import show_popup
import importlib
import logging
from typing import Any, List


def run_program(module_name: str, data: Any = None) -> Any:
    """
    Универсальный запуск build-модуля по имени модуля.
    1) Пытается вызвать module.main(data)
    2) Если main отсутствует — пробует вызвать функцию с именем module_name.split('.')[-1]
    Возвращает результат вызова или None при ошибке.
    """
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        logging.error(f"[run_program] Не удалось импортировать модуль {module_name}: {e}")
        return None

    # 1) main
    if hasattr(module, "main"):
        try:
            return getattr(module, "main")(data)
        except Exception as e:
            logging.exception(f"[run_program] Ошибка при вызове {module_name}.main: {e}")
            return None

    # 2) fallback по имени модуля (последняя часть)
    func_name = module_name.split(".")[-1]
    if hasattr(module, func_name):
        try:
            return getattr(module, func_name)(data)
        except Exception as e:
            logging.exception(f"[run_program] Ошибка при вызове {module_name}.{func_name}: {e}")
            return None

    logging.debug(f"[run_program] В модуле {module_name} нет функции 'main' и нет '{func_name}'")
    return None


def regen(adoc: object) -> bool:
    """
    Обновляет видовой экран AutoCAD.

    Args:
        adoc: Объект документа AutoCAD.

    Returns:
        bool: True, если обновление выполнено, False при ошибке.
    """
    try:
        adoc.Regen(0)
        return True
    except Exception:
        return False


def ensure_layer(
        adoc,
        layer_name: str,
        color_index: int = 7,  # ACI от 1 до 255 (7 = белый/чёрный в зависимости от темы)
        line_type: str = "Continuous"
) -> Any:
    """
    Проверяет наличие слоя в документе AutoCAD и создаёт его при необходимости.
    Устанавливает цвет через TrueColor (AcCmColor) и тип линии (если доступен).

    Args:
        adoc: Объект активного документа AutoCAD (acad.ActiveDocument)
        layer_name: Имя слоя (строка)
        color_index: Индекс цвета ACI (1–255), по умолчанию 7
        line_type: Имя типа линии (должен существовать в чертеже)

    Returns:
        Объект слоя (IAcadLayer) или None в случае критической ошибки
    """
    layers = adoc.Layers

    try:
        layer = layers.Item(layer_name)
        # Слой уже существует → можно здесь обновить свойства, если нужно
        # (например, всегда принудительно устанавливать цвет и тип линии)
    except Exception:
        # Слой не найден → создаём новый
        try:
            layer = layers.Add(layer_name)
        except Exception as e:
            print(f"Ошибка создания слоя '{layer_name}': {e}")
            return None

    # ─── Установка цвета через TrueColor (правильный способ в 2020–2026) ───
    try:
        color_obj = win32com.client.Dispatch("AutoCAD.AcCmColor")
        color_obj.ColorIndex = color_index  # ACI-индекс (1=red, 2=yellow, 3=green, ..., 7=white/black)
        # Альтернатива: color_obj.SetRGB(255, 128, 0)  # для TrueColor RGB
        layer.TrueColor = color_obj
    except Exception as e:
        print(f"Не удалось установить цвет слоя '{layer_name}': {e}")

    # ─── Установка типа линии (опционально, может не существовать) ───
    try:
        layer.Linetype = line_type
    except Exception:
        # Тип линии отсутствует в чертеже или недоступен → оставляем "Continuous" по умолчанию
        pass

    return layer


def set_layer(adoc: object, layer_name: str) -> bool:
    """
    Устанавливает активный слой в AutoCAD.

    Args:
        adoc: Объект документа AutoCAD.
        layer_name: Имя слоя для установки.

    Returns:
        bool: True, если слой установлен, False при ошибке.
    """
    try:
        if layer_name not in [layer.Name for layer in adoc.Layers]:
            ensure_layer(adoc, layer_name)
        adoc.ActiveLayer = adoc.Layers.Item(layer_name)
        return True
    except Exception:
        return False


def restore_layer(adoc: object, original_layer: object) -> bool:
    """
    Восстанавливает исходный активный слой.

    Args:
        adoc: Объект документа AutoCAD.
        original_layer: Исходный слой для восстановления.

    Returns:
        bool: True, если слой восстановлен, False при ошибке.
    """
    try:
        adoc.ActiveLayer = original_layer
        return True
    except Exception:
        show_popup(
            loc.get("layer_restore_error", "Error restoring original layer: {}").format(str(Exception)),
            popup_type="error"
        )
        return False


@contextmanager
def layer_context(adoc: object, layer_name: str):
    """
    Контекстный менеджер для временного переключения слоя с восстановлением.

    Args:
        adoc: Объект документа AutoCAD.
        layer_name: Имя слоя для установки.

    Yields:
        None: Выполняет код в контексте указанного слоя.
    """
    original_layer = adoc.ActiveLayer
    try:
        set_layer(adoc, layer_name)
        yield
    except Exception as e:
        show_popup(
            loc.get("layer_context_error", "Error in layer context '{}': {}").format(layer_name, str(e)),
            popup_type="error"
        )
    finally:
        restore_layer(adoc, original_layer)



if __name__ == "__main__":
    """
    Тестирование базовых операций при прямом запуске модуля.
    """
    cad = ATCadInit()
    if cad.original_layer is None:
        show_popup(
            loc.get("cad_init_error_short", "AutoCAD initialization error."),
            popup_type="error"
        )
    else:
        show_popup(
            f'{loc.get("current_layer_label", "Current layer")}: {cad.original_layer.Name}, \n'
            f'{loc.get("color_label", "color")}: {cad.original_layer.Color}',
            popup_type="info"
        )
