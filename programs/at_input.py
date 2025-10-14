"""
Файл: at_input.py
Путь: programs/at_input.py

Описание:
Модуль для обработки пользовательского ввода точек в AutoCAD через COM-интерфейс.
Предоставляет функцию для запроса точки с возможностью повторного ввода при ошибке
и автоматическим восстановлением COM-сессии при её потере.
"""

import logging
import pythoncom
import win32com.client
from typing import Optional, List, Union
from win32com.client import VARIANT

from config.at_cad_init import ATCadInit
from locales.at_localization_class import loc
from programs.at_com_utils import safe_utility_call


def at_point_input(adoc: object = None, as_variant: bool = True, prompt: str = None) -> Optional[Union[List[float], VARIANT]]:
    """
    Запрашивает у пользователя выбор точки в AutoCAD с защитой от потери COM-сессии.

    Args:
        adoc: Объект активного документа AutoCAD (ActiveDocument).
        as_variant: Если True — возвращает COM VARIANT (VT_ARRAY | VT_R8),
                    иначе список координат [x, y, z].
        prompt: Текст приглашения (опционально).

    Returns:
        Optional[Union[List[float], VARIANT]]:
            - Точка в виде VARIANT или списка.
            - None, если выбор отменён или COM потерян окончательно.
    """
    try:
        cad = ATCadInit()
        cad.refresh_active_document()

        adoc = cad.document
        if not adoc:
            logging.error("AutoCAD документ не найден или не инициализирован.")
            return None

        if prompt is None:
            prompt = loc.get("prompt_select_point", "Выберите точку: ") + "\n"

        adoc.Utility.Prompt(prompt)
        return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)

    except Exception as e:
        logging.error(f"Ошибка при получении точки: {e}")

        # Попытка восстановить COM-подключение
        try:
            pythoncom.CoInitialize()
            acad = win32com.client.GetActiveObject("AutoCAD.Application")
            adoc = acad.ActiveDocument
            model = adoc.ModelSpace
            logging.info(f"COM-сессия восстановлена, активный документ: {adoc.Name}")

            if prompt is None:
                prompt = loc.get("prompt_select_point", "Выберите точку: ") + "\n"
            adoc.Utility.Prompt(prompt)

            return safe_utility_call(lambda: adoc.Utility.GetPoint(), as_variant=as_variant)

        except Exception as e2:
            logging.error(f"Не удалось восстановить COM после потери соединения: {e2}")
            return None


if __name__ == "__main__":
    """
    Тестирование получения точки при прямом запуске модуля.
    """
    cad = ATCadInit()

    # Пример теста с возвратом VARIANT
    prompt1 = "Введите точку для вариантной точки"
    point_variant = at_point_input(cad.document, as_variant=True, prompt=prompt1)
    print("VARIANT:", point_variant)

    # Пример теста с возвратом списка
    prompt2 = "Введите точку для списка координат"
    point_list = at_point_input(cad.document, as_variant=False, prompt=prompt2)
    print("List:", point_list)
