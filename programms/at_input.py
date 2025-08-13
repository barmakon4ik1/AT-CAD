# programms/at_input.py
"""
Файл: at_input.py
Путь: programms/at_input.py

Описание:
Модуль для обработки пользовательского ввода точек в AutoCAD через COM-интерфейс.
Предоставляет функцию для запроса точки с возможностью повторного ввода при ошибке и выхода при отмене или неактивном окне AutoCAD.
"""

from typing import Optional, List, Union
import pythoncom
from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def at_point_input(adoc: object = None, as_variant: bool = True) -> Optional[Union[List[float], VARIANT]]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD с повторным вводом при ошибке.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument).
              Если None, инициализируется автоматически.
        as_variant: Если True — возвращает готовый COM VARIANT (VT_ARRAY | VT_R8).
                    Если False — возвращает обычный список [x, y, z].

    Returns:
        Optional[Union[List[float], VARIANT]]:
            - Готовый COM VARIANT (VT_ARRAY | VT_R8) в формате [x, y, z], если as_variant=True.
            - Список [x, y, z], если as_variant=False.
            None — в случае отмены или неактивного окна AutoCAD.

            Как работает point_xyz = ...:
            list(point_data) — превращает вход в список, даже если был кортеж или генератор.
            + [0, 0, 0] — добавляет запасные нули, если координат меньше трёх.
            [:3] — обрезает, если вдруг дали больше трёх координат.
            map(float, ...) — всё превращает в float, даже если были строки.

            tuple(...) — делает стабильный контейнер, который VARIANT точно переварит.
            Передаём в VARIANT как VT_ARRAY | VT_R8.
                VARIANT(...) — это обёртка для передачи данных в COM (через pythoncom).
                pythoncom.VT_ARRAY | pythoncom.VT_R8 значит:
                VT_ARRAY → передаём массив
                VT_R8 → элементы типа double (64-битный float).
    """
    if adoc is None:
        cad = ATCadInit()
        adoc = cad.adoc

    while True:
        try:
            adoc.Utility.Prompt(loc.get("prompt_select_point", "Выберите точку: ") + "\n")
            point_data = adoc.Utility.GetPoint()

            # Универсальная подготовка точки: гарантируем 3 координаты, конвертируем в float
            point_xyz = tuple(map(float, (list(point_data) + [0, 0, 0])[:3]))

            return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, point_xyz) if as_variant else list(point_xyz)

        except Exception as e:
            # Проверяем отмену (COMError -2147352567 для Esc)
            if hasattr(e, 'hresult') and e.hresult == -2147352567:
                return None
            # Проверяем неактивное окно AutoCAD (COMError -2147417848)
            if hasattr(e, 'hresult') and e.hresult == -2147417848:
                return None
            # Для других ошибок показываем сообщение и продолжаем цикл
            show_popup(
                loc.get(
                    "point_selection_error",
                    "Ошибка выбора точки: {}. Пожалуйста, повторите ввод или отмените."
                ).format(str(e)),
                popup_type="error"
            )


if __name__ == "__main__":
    """
    Тестирование получения точки при прямом запуске модуля.
    """
    cad = ATCadInit()
    # Пример теста с возвратом VARIANT
    input_point_variant = at_point_input(cad.adoc, as_variant=True)
    print("VARIANT:", input_point_variant)

    # Пример теста с возвратом обычного списка
    input_point_list = at_point_input(cad.adoc, as_variant=False)
    print("List:", input_point_list)
