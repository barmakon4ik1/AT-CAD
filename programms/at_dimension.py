# programms/at_dimension.py
"""
Модуль для простановки размеров в AutoCAD с использованием win32com.
Инициализация AutoCAD выполняется в модуле.
Использует команду DIMLINEAR через SendCommand для создания горизонтальных и вертикальных размеров.
"""

import win32com.client
import pythoncom
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
import logging
import time

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Устанавливаем DEBUG для подробного логирования
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def initialize_autocad(max_attempts=3, delay=2):
    """
    Инициализирует AutoCAD с повторными попытками.

    Args:
        max_attempts (int): Максимальное количество попыток подключения.
        delay (int): Задержка между попытками в секундах.

    Returns:
        tuple: (acad, adoc, model) или (None, None, None) в случае неудачи.
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            pythoncom.CoInitialize()  # Инициализация COM в MTA
            logging.debug("Инициализация COM выполнена")
            # Попытка подключения к открытому AutoCAD
            try:
                acad = win32com.client.GetActiveObject("AutoCAD.Application")
                logging.debug("Подключение к существующему AutoCAD успешно")
            except:
                logging.debug("AutoCAD не найден, запуск нового экземпляра")
                acad = win32com.client.Dispatch("AutoCAD.Application")
                acad.Visible = True  # Делаем AutoCAD видимым
                time.sleep(delay)  # Даём время на запуск
            adoc = acad.ActiveDocument
            model = adoc.ModelSpace
            # Установка стиля размеров
            try:
                adoc.ActiveDimStyle = adoc.DimStyles.Item("Standard")
                logging.debug("Установлен стиль размеров: Standard")
            except Exception as e:
                logging.warning(f"Не удалось установить стиль размеров: {e}")
            logging.info("AutoCAD успешно инициализирован")
            return acad, adoc, model
        except Exception as e:
            logging.error(f"Попытка {attempt + 1} инициализации AutoCAD не удалась: {e}")
            attempt += 1
            time.sleep(delay)
        finally:
            pythoncom.CoUninitialize()
    logging.error("Не удалось инициализировать AutoCAD после всех попыток")
    return None, None, None


def at_dimension(
        dim_type: str,
        start_point: tuple,
        end_point: tuple,
        dim_point: tuple,
        layer: str = "AM_5"
) -> bool:
    """
    Создает размер в AutoCAD с использованием команды DIMLINEAR через SendCommand.

    Args:
        layer: Слой для нанесения размеров (по умолчанию "AM_5").
        dim_type (str): Тип размера ('L' - линейный, 'H' - горизонтальный, 'V' - вертикальный, 'D' - диаметр, 'R' - радиус).
        start_point (tuple): Начальная точка размера (x, y, z).
        end_point (tuple): Конечная точка размера (x, y, z).
        dim_point (tuple): Точка размещения размерной линии (x, y, z).

    Returns:
        bool: True, если размер создан, False в случае ошибки.
    """
    # Инициализация AutoCAD
    acad, adoc, model = initialize_autocad()
    if not adoc or not model:
        show_popup(loc.get('cad_init_error', 'Ошибка инициализации AutoCAD'), popup_type="error")
        logging.error("Не удалось инициализировать AutoCAD")
        return False

    try:
        pythoncom.CoInitialize()

        # Настройка параметров размеров
        try:
            adoc.SetVariable("DIMSE1", 0)  # Включение выносных линий
            adoc.SetVariable("DIMSE2", 0)
            adoc.SetVariable("DIMSCALE", 10)  # Масштаб размера
            adoc.SetVariable("CLAYER", layer)  # Установка текущего слоя
            logging.debug(f"Установлены переменные: DIMSE1=0, DIMSE2=0, DIMSCALE=10, CLAYER={layer}")
        except Exception as e:
            logging.warning(f"Не удалось настроить системные переменные: {e}")

        # Преобразование точек в списки [x, y, z]
        start_point_list = [float(start_point[0]), float(start_point[1]), float(start_point[2])]
        end_point_list = [float(end_point[0]), float(end_point[1]), float(end_point[2])]
        dim_point_list = [float(dim_point[0]), float(dim_point[1]), float(dim_point[2])]

        # Корректировка координат для горизонтальных и вертикальных размеров
        dim_type = dim_type.upper()
        if dim_type == 'H':
            # Горизонтальный размер: фиксируем y-координату
            end_point_list = [end_point_list[0], start_point_list[1], 0.0]
            logging.debug(
                f"Горизонтальный размер: start={start_point_list}, end={end_point_list}, dim={dim_point_list}")
        elif dim_type == 'V':
            # Вертикальный размер: фиксируем x-координату
            end_point_list = [start_point_list[0], end_point_list[1], 0.0]
            logging.debug(f"Вертикальный размер: start={start_point_list}, end={end_point_list}, dim={dim_point_list}")

        # Формирование команды DIMLINEAR
        try:
            if dim_type in ['H', 'V', 'L']:
                # Формат команды: DIMLINEAR <start_x,start_y> <end_x,end_y> <dim_x,dim_y>
                command = (
                    f"DIMLINEAR "
                    f"{start_point_list[0]},{start_point_list[1]} "
                    f"{end_point_list[0]},{end_point_list[1]} "
                    f"{dim_point_list[0]},{dim_point_list[1]}\n"
                )
                logging.debug(f"Отправка команды: {command}")
                adoc.SendCommand(command)
                time.sleep(0.5)  # Задержка для обработки команды
            elif dim_type == 'D':
                # Диаметрический размер
                command = (
                    f"DIMDIAMETER "
                    f"{start_point_list[0]},{start_point_list[1]} "
                    f"{end_point_list[0]},{end_point_list[1]} "
                    f"{dim_point_list[0]},{dim_point_list[1]}\n"
                )
                logging.debug(f"Отправка команды: {command}")
                adoc.SendCommand(command)
                time.sleep(0.5)
            elif dim_type == 'R':
                # Радиальный размер
                command = (
                    f"DIMRADIUS "
                    f"{start_point_list[0]},{start_point_list[1]} "
                    f"{dim_point_list[0]},{dim_point_list[1]}\n"
                )
                logging.debug(f"Отправка команды: {command}")
                adoc.SendCommand(command)
                time.sleep(0.5)
            else:
                show_popup(loc.get('invalid_dim_type', 'Недопустимый тип размера'), popup_type="error")
                logging.error(f"Недопустимый тип размера: {dim_type}")
                return False
        except Exception as e:
            logging.error(f"Ошибка при выполнении SendCommand: {e}")
            show_popup(loc.get('dim_creation_error', f"Ошибка при создании размера: {str(e)}"), popup_type="error")
            return False

        # Регенерация чертежа
        try:
            adoc.Regen(0)  # acActiveViewport
            logging.debug("Чертеж регенерирован")
        except Exception as e:
            logging.warning(f"Ошибка регенерации чертежа: {e}")

        logging.info(f"Размер типа '{dim_type}' успешно создан через SendCommand")
        return True

    except Exception as e:
        logging.error(f"Общая ошибка при создании размера: {e}")
        show_popup(loc.get('dim_creation_error', f"Общая ошибка при создании размера: {str(e)}"), popup_type="error")
        return False
    finally:
        pythoncom.CoUninitialize()


def test_dimension():
    """
    Тестовый запуск функции at_dimension с запросом точек и типа размера.
    """
    acad, adoc, model = initialize_autocad()
    if not adoc or not model:
        show_popup(loc.get('cad_init_error', 'Ошибка инициализации AutoCAD'), popup_type="error")
        logging.error("Не удалось инициализировать AutoCAD в тестовом режиме")
        return

    try:
        pythoncom.CoInitialize()

        # Запрос типа размера
        dim_types = ['L', 'H', 'V', 'D', 'R']
        adoc.Utility.Prompt(f"Выберите тип размера ({', '.join(dim_types)}): ")
        dim_type = adoc.Utility.GetString(1).strip().upper()
        if dim_type not in dim_types:
            show_popup(loc.get('invalid_dim_type', 'Недопустимый тип размера'), popup_type="error")
            logging.error(f"Недопустимый тип размера: {dim_type}")
            return

        # Запрос точек с учетом типа размера
        if dim_type in ['L', 'H', 'V']:
            adoc.Utility.Prompt("Выберите начальную точку размера:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                logging.error("Не выбрана начальная точка размера")
                return

            adoc.Utility.Prompt("Выберите конечную точку размера:\n")
            end_point = at_point_input(adoc)
            if not end_point:
                logging.error("Не выбрана конечная точка размера")
                return

            adoc.Utility.Prompt("Выберите точку размещения размерной линии:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                logging.error("Не выбрана точка размещения размерной линии")
                return
        elif dim_type == 'D':
            adoc.Utility.Prompt("Выберите первую точку на окружности/дуге:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                logging.error("Не выбрана первая точка для диаметра")
                return

            adoc.Utility.Prompt("Выберите противоположную точку на окружности/дуге:\n")
            end_point = at_point_input(adoc)
            if not end_point:
                logging.error("Не выбрана противоположная точка для диаметра")
                return

            adoc.Utility.Prompt("Выберите точку размещения размерной линии:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                logging.error("Не выбрана точка размещения размерной линии для диаметра")
                return
        elif dim_type == 'R':
            adoc.Utility.Prompt("Выберите центр окружности/дуги:\n")
            start_point = at_point_input(adoc)
            if not start_point:
                logging.error("Не выбран центр для радиального размера")
                return

            adoc.Utility.Prompt("Выберите точку на окружности/дуге:\n")
            dim_point = at_point_input(adoc)
            if not dim_point:
                logging.error("Не выбрана точка на окружности/дуге для радиального размера")
                return

            end_point = dim_point

        # Преобразование точек в кортежи (x, y, z)
        start_point = (start_point[0], start_point[1], 0)
        end_point = (end_point[0], end_point[1], 0)
        dim_point = (dim_point[0], dim_point[1], 0)

        # Вызов функции простановки размера
        if at_dimension(dim_type, start_point, end_point, dim_point):
            show_popup(loc.get('dim_success', 'Размер успешно создан с масштабом 10'), popup_type="success")
        else:
            show_popup(loc.get('dim_creation_error', 'Ошибка при создании размера'), popup_type="error")

    except Exception as e:
        logging.error(f"Ошибка в тестовом режиме: {e}")
        show_popup(loc.get('test_error', f"Ошибка в тестовом режиме: {str(e)}"), popup_type="error")
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    test_dimension()
