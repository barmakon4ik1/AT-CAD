"""
Файл: at_input.py
Путь: programms/at_input.py

Описание:
Модуль для обработки пользовательского ввода точек в AutoCAD через COM-интерфейс.
Предоставляет функцию для запроса точки с возможностью повторного ввода при ошибке и выхода при отмене или неактивном окне AutoCAD.
"""

from typing import Optional, List, Union
from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from programms.at_com_utils import safe_utility_call


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

            Как работает нормализация точки:
            list(point_data) — превращает вход в список, даже если был кортеж или генератор.
            + [0, 0, 0] — добавляет запасные нули, если координат меньше трёх.
            [:3] — обрезает, если вдруг дали больше трёх координат.
            map(float, ...) — всё превращает в float, даже если были строки.
    """
    if adoc is None:
        cad = ATCadInit()
        adoc = cad.adoc

    # Печатаем приглашение, затем безопасно запрашиваем точку.
    adoc.Utility.Prompt(loc.get("prompt_select_point", "Выберите точку: ") + "\n")

    # ВАЖНО: передаём ЛЯМБДА-ВЫЗОВ, а не метод как объект.
    # Так мы всегда вызываем метод правильно, и анализаторы не ругаются, что "ожидался возвращаемый объект".
    return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)


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
