"""
Файл: at_com_utils.py
Путь: programs/at_com_utils.py

Описание:
Утилиты для безопасного вызова методов AutoCAD через COM API.
Включает обёртку для автоматического повтора при временной недоступности AutoCAD
(например, при слишком быстром клике мышью, занятости приложения или временных сбоях RPC).
"""

import time
from typing import Callable, Optional, Union, List, Any
import pythoncom
from win32com.client import VARIANT
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def _to_xyz_list(value: Any) -> List[float]:
    """
    Преобразует результат COM-вызова точки в список [x, y, z] float.
    Дополняет нулями и обрезает до 3 координат.
    """
    # Некоторые COM-объекты возвращают tuple, некоторые - массивы; list(...) здесь безопасен
    xyz = (list(value) + [0, 0, 0])[:3]
    return [float(x) for x in xyz]


def safe_utility_call(
    method: Callable[[], Any],
    *,
    retries: int = 5,
    delay: float = 0.2,
    as_variant: bool = False
) -> Optional[Union[List[float], VARIANT]]:
    """
    Безопасно вызывает переданный нулераргументный метод/функцию (например, lambda: adoc.Utility.GetPoint()),
    повторяя попытку при временных COM-ошибках.

    Args:
        method: Нулераргументный вызываемый объект (например, lambda: adoc.Utility.GetPoint()).
        retries: Количество повторов при временных сбоях (по умолчанию 5).
        delay: Пауза между повторами в секундах (по умолчанию 0.2).
        as_variant: Если True — результат будет возвращён в виде COM VARIANT (VT_ARRAY | VT_R8),
                    иначе список [x, y, z].

    Returns:
        - Список [x, y, z] (float), если as_variant=False.
        - VARIANT(VT_ARRAY | VT_R8, [x, y, z]), если as_variant=True.
        - None при отмене (Esc) или неактивном окне.

    Обрабатываемые ситуации:
        - Esc/отмена: hresult == -2147352567 → возврат None.
        - Окно неактивно / не готово: hresult == -2147417848 → возврат None.
        - Временная занятость/отклонение вызова/проблемы RPC: ретраи и пауза.
          Коды: -2147418111 (Call was rejected by callee),
                -2147417846 (Server busy / The message filter indicated that the application is busy),
                -2147023174 (The RPC server is unavailable),
                -2147023170 (RPC/E_FAIL-семейство, встречается у некоторых сборок).
          Также проверяется текст ошибки на "Call was rejected by callee", "RPC", "server busy".
    """
    for attempt in range(retries):
        try:
            result = method()
            if result is None:
                # Пользователь мог отменить ввод (или метод вернул None)
                return None

            xyz = _to_xyz_list(result)
            if as_variant:
                return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(xyz))
            return xyz

        except Exception as e:
            hr = getattr(e, "hresult", None)
            msg = str(e)

            # Отмена (Esc)
            if hr == -2147352567:
                return None

            # Окно AutoCAD неактивно / not responding
            if hr == -2147417848:
                return None

            # Временная занятость / отклонение вызова / RPC-проблемы — пробуем повтор
            transient = (
                hr in (-2147418111, -2147417846, -2147023174, -2147023170)
                or "Call was rejected by callee" in msg
                or "server busy" in msg.lower()
                or "rpc" in msg.lower()
            )
            if transient and attempt < retries - 1:
                time.sleep(delay)
                continue

            # Прочие ошибки — покажем сообщение и вернём None
            show_popup(
                loc.get("com_call_error", "Ошибка при вызове AutoCAD API: {}").format(msg),
                popup_type="error"
            )
            return None

    # Если не удалось за N попыток — считаем как отмену/недоступность
    return None
