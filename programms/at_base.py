# programms/at_base.py
"""
Файл: at_base.py
Путь: programms/at_base.py

Описание:
Модуль для базовых операций с AutoCAD через COM-интерфейс.
Предоставляет функции для управления слоями и обновления видового экрана.
"""

from contextlib import contextmanager
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


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


def ensure_layer(adoc: object, layer_name: str) -> bool:
    """
    Проверяет наличие слоя и создает его, если он отсутствует.

    Args:
        adoc: Объект документа AutoCAD.
        layer_name: Имя слоя для проверки/создания.

    Returns:
        bool: True, если слой существует или создан, False при ошибке.
    """
    try:
        if layer_name not in [layer.Name for layer in adoc.Layers]:
            adoc.Layers.Add(layer_name)
        return True
    except Exception:
        return False


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
        show_popup(
            loc.get("layer_set", "Active layer '{}' set.").format(layer_name),
            popup_type="info"
        )
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
        show_popup(
            loc.get("layer_restored", "Original layer '{}' restored.").format(original_layer.Name),
            popup_type="info"
        )
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
        raise
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
        print(
            f'{loc.get("current_layer_label", "Current layer")}: {cad.original_layer.Name}, {loc.get("color_label", "color")}: {cad.original_layer.Color}')
