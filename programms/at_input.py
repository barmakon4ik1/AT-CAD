# programms/at_input.py
"""
Файл: at_input.py
Путь: programms/at_input.py

Описание:
Модуль для обработки пользовательского ввода точек в AutoCAD через COM-интерфейс.
Предоставляет функцию для запроса точки с возможностью повторного ввода при ошибке и выхода при отмене или неактивном окне AutoCAD.
"""

from typing import Optional, List
from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def at_point_input(adoc: object = None) -> Optional[List[float]]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD с повторным вводом при ошибке.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument). Если None, инициализируется автоматически.

    Returns:
        Optional[List[float]]: Выбранная точка в виде списка [x, y, z] или None в случае отмены или неактивного окна AutoCAD.
    """
    if adoc is None:
        cad = ATCadInit()
        adoc = cad.adoc

    while True:
        try:
            adoc.Utility.Prompt(loc.get("prompt_select_point", "Выберите точку: ") + "\n")
            point_data = adoc.Utility.GetPoint()
            point_list = [float(point_data[0]), float(point_data[1]), float(point_data[2])]
            return point_list
        except Exception as e:
            # Проверяем отмену (COMError -2147352567 для Esc)
            if hasattr(e, 'hresult') and e.hresult == -2147352567:
                return None
            # Проверяем неактивное окно AutoCAD (COMError -2147417848)
            if hasattr(e, 'hresult') and e.hresult == -2147417848:
                return None
            # Для других ошибок показываем сообщение и продолжаем цикл
            show_popup(
                loc.get("point_selection_error",
                        "Ошибка выбора точки: {}. Пожалуйста, повторите ввод или отмените.").format(str(e)),
                popup_type="error"
            )


if __name__ == "__main__":
    """
    Тестирование получения точки при прямом запуске модуля.
    """
    cad = ATCadInit()
    input_point = at_point_input(cad.adoc)
    if input_point:
        print(f'{loc.get("point_selected", "Выбрана точка")}: {input_point}')
    else:
        print(f'{loc.get("point_selection_cancelled", "Выбор точки отменён.")}')
