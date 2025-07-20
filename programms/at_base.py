"""
Файл: at_base.py
Путь: programms\at_base.py

Описание:
Модуль для базовых операций с AutoCAD через COM-интерфейс.
Предоставляет функции для инициализации AutoCAD, управления слоями
и обновления видового экрана. Использует локализацию из at_localization_class.py
и настройки из user_settings.json через get_setting.
"""

from contextlib import contextmanager
from locales.at_localization_class import loc
from config.at_config import get_setting
from config.at_cad_init import ATCadInit
from windows.at_gui_utils import show_popup
from functools import wraps
from pythoncom import CoInitialize, CoUninitialize
from typing import Optional, Tuple

loc.set_language(get_setting("LANGUAGE"))  # Установка языка локализации из user_settings.json

_cad_instance = None  # Глобальный экземпляр AutoCAD

def handle_errors(func):
    """
    Декоратор для обработки ошибок в функциях.

    Args:
        func: Функция для декорирования.

    Returns:
        wrapper: Обёрнутая функция с обработкой ошибок.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return None
    return wrapper

@handle_errors
def init_autocad() -> Optional[Tuple[object, object, object]]:
    """
    Инициализирует AutoCAD и возвращает его объекты.

    Returns:
        Optional[Tuple[object, object, object]]: Кортеж из объектов AutoCAD
        (документ, модельное пространство, исходный слой) или None при ошибке.
    """
    global _cad_instance
    if _cad_instance is not None and _cad_instance.is_initialized():
        return _cad_instance.adoc, _cad_instance.model, _cad_instance.original_layer
    CoInitialize()
    _cad_instance = ATCadInit()
    if not _cad_instance.is_initialized():
        show_popup(loc.get('cad_init_error'), popup_type="error")
        CoUninitialize()
        return None
    return _cad_instance.adoc, _cad_instance.model, _cad_instance.original_layer

@handle_errors
def regen(adoc: object) -> Optional[object]:
    """
    Обновляет видовой экран AutoCAD.

    Args:
        adoc: Объект документа AutoCAD.

    Returns:
        Optional[object]: Объект документа AutoCAD или None при ошибке.
    """
    adoc.Regen(0)
    return adoc

@handle_errors
def set_layer(adoc: object, layer_name: str) -> Optional[object]:
    """
    Устанавливает активный слой в AutoCAD.

    Args:
        adoc: Объект документа AutoCAD.
        layer_name: Имя слоя для установки.

    Returns:
        Optional[object]: Объект документа AutoCAD или None при ошибке.
    """
    adoc.ActiveLayer = adoc.Layers.Item(layer_name)
    return adoc

@handle_errors
def restore_layer(adoc: object, original_layer: object) -> Optional[object]:
    """
    Восстанавливает исходный активный слой.

    Args:
        adoc: Объект документа AutoCAD.
        original_layer: Исходный слой для восстановления.

    Returns:
        Optional[object]: Объект документа AutoCAD или None при ошибке.
    """
    adoc.ActiveLayer = original_layer
    return adoc

@handle_errors
def ensure_layer(adoc: object, layer_name: str) -> Optional[object]:
    """
    Проверяет наличие слоя и создает его, если он отсутствует.

    Args:
        adoc: Объект документа AutoCAD.
        layer_name: Имя слоя для проверки/создания.

    Returns:
        Optional[object]: Объект слоя AutoCAD или None при ошибке.
    """
    if layer_name not in [layer.Name for layer in adoc.Layers]:
        adoc.Layers.Add(layer_name)
    return adoc.Layers.Item(layer_name)

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
    finally:
        restore_layer(adoc, original_layer)
