"""
Файл: programs/at_input_lisp.py

Описание:
Безопасные функции выбора точки и примитива (объекта) через LISP-мост.
Замена нестабильным COM-вызовам вроде doc.Utility.GetPoint() и doc.Utility.GetEntity().
Работает через модуль lisp_bridge.py.
"""

from typing import Optional, Tuple, Any
from programs.lisp_bridge import send_lisp_command


def get_point(prompt: str = "Укажите точку:") -> Optional[Tuple[float, float, float]]:
    """
    Запрашивает точку у пользователя через LISP.
    Возвращает координаты (x, y, z) или None при отмене.
    """
    result = send_lisp_command("get_point", {"prompt": prompt})
    if result and "point" in result:
        return tuple(result["point"])
    return None


def get_entity(prompt: str = "Выберите объект:") -> Optional[dict]:
    """
    Запрашивает выбор примитива у пользователя.
    Возвращает словарь с данными объекта (handle, тип, слой и т.д.) или None при отмене.
    """
    result = send_lisp_command("get_entity", {"prompt": prompt})
    if result and "entity" in result:
        return result["entity"]
    return None
