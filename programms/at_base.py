"""
Модуль для базовых операций с AutoCAD через COM-интерфейс.
"""
from contextlib import contextmanager

from locales.at_localization import loc
from config.at_config import LANGUAGE
from config.at_cad_init import ATCadInit
from windows.at_gui_utils import show_popup
from functools import wraps
from pythoncom import CoInitialize, CoUninitialize
from typing import Optional, Tuple

loc.language = LANGUAGE  # Установка языка локализации

_cad_instance = None  # Глобальный экземпляр AutoCAD


def handle_errors(func):
    """
    Декоратор для обработки ошибок в функциях.
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
    """
    adoc.Regen(0)
    return adoc


@handle_errors
def set_layer(adoc: object, layer_name: str) -> Optional[object]:
    """
    Устанавливает активный слой в AutoCAD.
    """
    adoc.ActiveLayer = adoc.Layers.Item(layer_name)
    return adoc


@handle_errors
def restore_layer(adoc: object, original_layer: object) -> Optional[object]:
    """
    Восстанавливает исходный активный слой.
    """
    adoc.ActiveLayer = original_layer
    return adoc


@handle_errors
def ensure_layer(adoc: object, layer_name: str) -> Optional[object]:
    """
    Проверяет наличие слоя и создает его, если он отсутствует.
    """
    if layer_name not in [layer.Name for layer in adoc.Layers]:
        adoc.Layers.Add(layer_name)
    return adoc.Layers.Item(layer_name)


@contextmanager
def layer_context(adoc: object, layer_name: str):
    """
    Контекстный менеджер для временного переключения слоя с восстановлением.
    """
    original_layer = adoc.ActiveLayer
    try:
        set_layer(adoc, layer_name)
        yield
    finally:
        restore_layer(adoc, original_layer)
