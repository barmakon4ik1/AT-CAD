# programms/at_dimension.py
"""
Модуль для простановки размеров в AutoCAD с использованием win32com.
Создаёт линейные размеры через ENTMAKE с DXF-списком, диаметрические и радиальные — через SendCommand.
Использует стиль AM_ISO и слой AM_5.
"""

import win32com.client
import pythoncom
from programms.at_input import at_point_input
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
import logging
import time

# Настройка логирования
# logging.basicConfig(
#     level=logging.DEBUG,
#     filename="at_dimension.log",
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     force=True
# )


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
            pythoncom.CoInitialize()
            logging.debug("Инициализация COM выполнена")
            try:
                acad = win32com.client.GetActiveObject("AutoCAD.Application")
                logging.debug("Подключение к существующему AutoCAD успешно")
            except:
                logging.debug("AutoCAD не найден, запуск нового экземпляра")
                acad = win32com.client.Dispatch("AutoCAD.Application")
                acad.Visible = True
                time.sleep(delay)
            adoc = acad.ActiveDocument
            model = adoc.ModelSpace
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


def create_dxf_dimension(dim_type: str, start_point: tuple, end_point: tuple, dim_point: tuple, layer: str = "AM_5"):
    """
    Формирует DXF-список для линейного размера (H, V, L).

    Args:
        dim_type (str): Тип размера ('H', 'V', 'L').
        start_point (tuple): Начальная точка (x, y, z).
        end_point (tuple): Конечная точка (x, y, z).
        dim_point (tuple): Точка размерной линии (x, y, z).
        layer (str): Слой размера.

    Returns:
        str: LISP-строка для ENTMAKE.
    """
    dim_type = dim_type.upper()
    # Корректировка координат
    start_x, start_y, start_z = float(start_point[0]), float(start_point[1]), float(start_point[2])
    end_x, end_y, end_z = float(end_point[0]), float(end_point[1]), float(end_point[2])
    dim_x, dim_y, dim_z = float(dim_point[0]), float(dim_point[1]), float(dim_point[2])

    if dim_type == 'H':
        end_y = start_y  # Фиксируем y для горизонтального
    elif dim_type == 'V':
        end_x = start_x  # Фиксируем x для вертикального

    # DXF-список с обязательными кодами
    dxf_list = [
        "(0 . \"DIMENSION\")",
        "(100 . \"AcDbEntity\")",
        "(100 . \"AcDbDimension\")",
        f"(10 {dim_x} {dim_y} {dim_z})",  # Точка размерной линии
        f"(11 {dim_x} {dim_y} {dim_z})",  # Точка текста (совпадает с 10)
        f"(13 {start_x} {start_y} {start_z})",  # Первая выносная точка
        f"(14 {end_x} {end_y} {end_z})",  # Вторая выносная точка
        "(70 . 32)",  # Тип: AlignedDimension
        "(100 . \"AcDbAlignedDimension\")"
    ]

    # Формирование LISP-строки
    lisp_str = f"(entmake '({' '.join(dxf_list)}))"
    logging.debug(f"Сформирован DXF: {lisp_str}")
    return lisp_str


def at_dimension(
        dim_type: str,
        start_point: tuple,
        end_point: tuple,
        dim_point: tuple,
        layer: str = "AM_5"
) -> bool:
    """
    Создает размер в AutoCAD через ENTMAKE для линейных размеров и SendCommand для D/R.

    Args:
        layer: Слой для размеров (по умолчанию "AM_5").
        dim_type (str): Тип размера ('L', 'H', 'V', 'D', 'R').
        start_point (tuple): Начальная точка размера (x, y, z).
        end_point (tuple): Конечная точка размера (x, y, z).
        dim_point (tuple): Точка размерной линии (x, y, z).

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

        # Настройка стиля размеров
        try:
            adoc.SendCommand("DIMSTYLE WIEDERHERSTELLEN AM_ISO\n")
            time.sleep(0.5)
            logging.debug("Стиль AM_ISO восстановлен")
        except Exception as e:
            logging.warning(f"Не удалось восстановить стиль AM_ISO: {e}")

        dim_type = dim_type.upper()
        if dim_type in ['H', 'V', 'L']:
            # Линейный размер через ENTMAKE
            lisp_command = create_dxf_dimension(dim_type, start_point, end_point, dim_point, layer)
            try:
                adoc.SendCommand(lisp_command + "\n")
                time.sleep(1.5)
                # Проверка результата
                adoc.SendCommand("(princ (entlast))\n")
                time.sleep(0.5)
                adoc.SendCommand("REGEN\n")
                time.sleep(0.5)
                logging.info(f"Размер типа '{dim_type}' создан через ENTMAKE")
            except Exception as e:
                logging.error(f"Ошибка при выполнении ENTMAKE: {e}")
                show_popup(loc.get('dim_creation_error', f"Ошибка при создании размера: {str(e)}"), popup_type="error")
                return False
        else:
            # Диаметрические и радиальные размеры через SendCommand
            start_point_list = [float(start_point[0]), float(start_point[1]), float(start_point[2])]
            end_point_list = [float(end_point[0]), float(end_point[1]), float(end_point[2])]
            dim_point_list = [float(dim_point[0]), float(dim_point[1]), float(dim_point[2])]
            try:
                if dim_type == 'D':
                    command = (
                        f"DIMDIAMETER "
                        f"{start_point_list[0]},{start_point_list[1]} "
                        f"{end_point_list[0]},{end_point_list[1]} "
                        f"{dim_point_list[0]},{dim_point_list[1]}\n"
                    )
                    logging.debug(f"Отправка команды: {command}")
                    adoc.SendCommand(command)
                    time.sleep(1.5)
                elif dim_type == 'R':
                    command = (
                        f"DIMRADIUS "
                        f"{start_point_list[0]},{start_point_list[1]} "
                        f"{dim_point_list[0]},{dim_point_list[1]}\n"
                    )
                    logging.debug(f"Отправка команды: {command}")
                    adoc.SendCommand(command)
                    time.sleep(1.5)
                else:
                    show_popup(loc.get('invalid_dim_type', 'Недопустимый тип размера'), popup_type="error")
                    logging.error(f"Недопустимый тип размера: {dim_type}")
                    return False
                adoc.SendCommand("REGEN\n")
                time.sleep(0.5)
                logging.info(f"Размер типа '{dim_type}' создан через SendCommand")
            except Exception as e:
                logging.error(f"Ошибка при выполнении SendCommand: {e}")
                show_popup.error(f"Ошибка при создании размера: {str(e)}")
                return False

    except Exception as e:
        logging.error(f"Общая ошибка: {str(e)}")
        show_popup(loc.get('dim_error', f"Ошибка при создании размера: {str(e)}"), popup_type="error")
        return False
    finally:
        pythoncom.CoUninitialize()


def at_amautodim(adoc, object, start_point, dim_point):
    cmd = f'"_amautodim_cli""\n""_p""\n""_b""\n""_n""\n""_n""\n""_n""\n"{object}\n"{start_point}\n"{dim_point}\n"'
    print(cmd)
    adoc.SendCommand(cmd)


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

