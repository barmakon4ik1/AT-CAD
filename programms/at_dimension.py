# programms/at_dimension.py
"""
Модуль для простановки размеров в AutoCAD с использованием pyautocad.
"""

from pyautocad import APoint
from config.at_cad_init import ATCadInit
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
import logging


def at_dimension(
        dim_type: str,
        start_point: APoint,
        end_point: APoint,
        dim_point: APoint,
        adoc: object = None,
        layer: str = "AM_5"
) -> bool:
    """
    Создает размер в AutoCAD с использованием текущего стиля.

    Args:
        layer: Слой для нанесения размеров (по умолчанию "AM_5")
        dim_type (str): Тип размера ('L' - линейный, 'D' - диаметр, 'R' - радиус).
        start_point (APoint): Начальная точка размера.
        end_point (APoint): Конечная точка размера.
        dim_point (APoint): Точка размещения размерной линии.
        adoc: Объект активного документа AutoCAD (ActiveDocument). Если None, инициализируется.

    Returns:
        bool: True, если размер создан, False в случае ошибки.
    """
    # Инициализация AutoCAD
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(loc.get('cad_init_error', 'Ошибка инициализации AutoCAD'), popup_type="error")
        return False

    adoc = cad.adoc if adoc is None else adoc
    model = cad.model

    try:
        # Создание размера
        dim_type = dim_type.upper()
        if dim_type == 'L':
            dim = model.AddDimAligned(start_point, end_point, dim_point)
        elif dim_type == 'D':
            # Для диаметра: start_point и end_point - противоположные точки на окружности/дуге
            # LeaderLength - радиус (половина диаметра) - отступ для текстовой метки
            leader_length = ((end_point[0] - start_point[0]) ** 2 + (end_point[1] - start_point[1]) ** 2) ** 0.5 / 2 + 5
            dim = model.AddDimDiametric(start_point, end_point, leader_length)
        elif dim_type == 'R':
            # Для радиуса: start_point - центр, dim_point - точка на окружности
            leader_length = ((dim_point[0] - start_point[0]) ** 2 + (dim_point[1] - start_point[1]) ** 2) ** 0.5
            dim = model.AddDimRadial(start_point, dim_point, leader_length)
        else:
            show_popup(loc.get('invalid_dim_type', 'Недопустимый тип размера'), popup_type="error")
            return False
        dim.Layer = layer
        dim.ScaleFactor = 10

        logging.info(f"Размер типа '{dim_type}' создан")
        return True

    except Exception as e:
        logging.error(f"Ошибка при создании размера: {e}")
        show_popup(loc.get('dim_creation_error', 'Ошибка при создании размера'), popup_type="error")
        return False


def test_dimension():
    """
    Тестовый запуск функции at_dimension с запросом точек и типа размера.
    """
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(loc.get('cad_init_error', 'Ошибка инициализации AutoCAD'), popup_type="error")
        return

    adoc = cad.adoc
    try:
        # Запрос типа размера
        dim_types = ['L', 'D', 'R']
        adoc.Utility.Prompt(f"Выберите тип размера ({', '.join(dim_types)}): ")
        dim_type = adoc.Utility.GetString(1).strip().upper()
        if dim_type not in dim_types:
            show_popup(loc.get('invalid_dim_type', 'Недопустимый тип размера'), popup_type="error")
            return

        # Запрос точек с учетом типа размера
        if dim_type == 'L':
            adoc.Utility.Prompt("Выберите начальную точку размера:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                return

            adoc.Utility.Prompt("Выберите конечную точку размера:\n")
            end_point = at_point_input(adoc)
            if not end_point:
                return

            adoc.Utility.Prompt("Выберите точку размещения размерной линии:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                return
        elif dim_type == 'D':
            adoc.Utility.Prompt("Выберите первую точку на окружности/дуге:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                return

            adoc.Utility.Prompt("Выберите противоположную точку на окружности/дуге:\n")
            end_point = at_point_input(adoc)
            if not end_point:
                return

            adoc.Utility.Prompt("Выберите точку размещения размерной линии:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                return
        elif dim_type == 'R':
            adoc.Utility.Prompt("Выберите центр окружности/дуги:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                return

            adoc.Utility.Prompt("Выберите точку на окружности/дуге:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                return

            end_point = dim_point  # Для радиуса end_point не используется, присваиваем dim_point

        # Вызов функции простановки размера
        if at_dimension(dim_type, start_point, end_point, dim_point):
            show_popup(loc.get('dim_success', 'Размер успешно создан с масштабом 10'), popup_type="success")
        else:
            show_popup(loc.get('dim_creation_error', 'Ошибка при создании размера'), popup_type="error")

    except Exception as e:
        logging.error(f"Ошибка в тестовом режиме: {e}")
        show_popup(loc.get('test_error', 'Ошибка в тестовом режиме'), popup_type="error")


if __name__ == "__main__":
    test_dimension()

    # start = APoint(0, 0)
    # end = APoint(1000, 0)
    # dim = APoint(500, 50)
    # at_dimension("L", start, end, dim, layer="AM_5")
"""
Использование в программе:


from pyautocad import APoint
from programms.at_dimension import at_dimension

start = APoint(0, 0)
end = APoint(10, 0)
dim = APoint(5, 5)
at_dimension("horizontal", start, end, dim, layer="AM_5")
"""
