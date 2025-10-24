"""
Файл: at_com_utils.py
Путь: programs/at_com_utils.py

Описание:
Утилиты для безопасного вызова методов AutoCAD через COM API.
Поддерживает вызовы GetPoint, GetEntity, GetKeyword и другие, с автоопределением возвращаемого типа.
"""

import time
from typing import Callable, Optional, Union, List, Any, Tuple
import pythoncom
from win32com.client import VARIANT, CDispatch
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def _to_xyz_list(value: Any) -> List[float]:
    """Преобразует результат COM-вызова точки в [x, y, z]."""
    xyz = (list(value) + [0, 0, 0])[:3]
    return [float(x) for x in xyz]


def safe_utility_call(
    method: Callable[[], Any],
    *,
    retries: int = 5,
    delay: float = 0.2,
    as_variant: bool = False
) -> Optional[Any]:
    """
    Универсальный безопасный вызов метода AutoCAD Utility:
    корректно обрабатывает точки, объекты, строки и отмену (ESC).
    """
    for attempt in range(retries):
        try:
            result = method()
            if result is None:
                return None  # пользователь отменил (ESC)

            # --- Определяем тип результата ---
            # 1. Ключевое слово (строка)
            if isinstance(result, str):
                return result

            # 2. COM-объект (например, AcadLWPolyline)
            if isinstance(result, CDispatch):
                return result

            # 3. Кортеж из (Entity, Point)
            if isinstance(result, tuple) and len(result) == 2:
                entity, point = result
                try:
                    point_xyz = _to_xyz_list(point)
                except Exception:
                    point_xyz = [0.0, 0.0, 0.0]
                return entity, point_xyz

            # 4. Координаты точки (список/кортеж из чисел)
            if isinstance(result, (list, tuple)) and all(isinstance(x, (int, float)) for x in result):
                xyz = _to_xyz_list(result)
                if as_variant:
                    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(xyz))
                return xyz

            # 5. Всё остальное возвращаем как есть
            return result

        except Exception as e:
            hr = getattr(e, "hresult", None)
            msg = str(e)

            # Отмена (Esc)
            if hr == -2147352567:
                return None

            # Окно AutoCAD неактивно / не готово
            if hr == -2147417848:
                return None

            # Временные COM-ошибки — повторяем
            transient = (
                hr in (-2147418111, -2147417846, -2147023174, -2147023170)
                or "Call was rejected by callee" in msg
                or "server busy" in msg.lower()
                or "rpc" in msg.lower()
            )
            if transient and attempt < retries - 1:
                time.sleep(delay)
                continue

            # Иные ошибки — показать пользователю
            show_popup(
                loc.get("com_call_error", "Ошибка при вызове AutoCAD API: {}").format(msg),
                popup_type="error",
            )
            return None

    return None
