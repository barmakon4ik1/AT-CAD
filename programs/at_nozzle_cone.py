"""
programs/at_nozzle_cone.py

Шаг 1: принимаем словарь параметров, извлекаем значения в переменные.
Тестовая функция run_test() формирует примерный словарь (как из GUI) и вызывает main().
"""
import math
from pprint import pprint
from typing import Any, Dict, Optional, Tuple

from config.at_cad_init import ATCadInit
from programs.at_construction import at_cone_sheet
from programs.at_geometry import distance_2points, make_cone_arc_points


def main(params: Dict[str, Any]) -> Tuple[Any, Any, float, float, float, float, str]:
    """
    Основная функция (шаг 1).
    Принимает словарь params и извлекает в локальные переменные:
        model, input_point, diameter_top, diameter_base, diameter_pipe, height_full, layout

    Возвращает кортеж (model, input_point, diameter_top, diameter_base, diameter_pipe, height_full, layout)
    для удобства тестирования и последующей передачи в другие функции.

    Ожидаемые ключи в params:
        - "model"            : объект model space (любой тип)
        - "input_point"      : точка вставки (список/кортеж или VARIANT)
        - "diameter_top"     : float (d1)
        - "diameter_base"    : float (d2)
        - "diameter_pipe"    : float (D)
        - "height_full"      : float  (H)
        - "layout"           : str (необязательно, по умолчанию "LASER-TEXT")
        - N                  : int количество точек разбиения дуги
    """

    # Считываем и проверяем параметры (простейшая валидация)
    # model и input_point могут быть любого типа, оставляем как есть
    try:
        model = params["model"]
    except KeyError:
        raise KeyError("Отсутствует обязательный параметр 'model' в params")

    try:
        input_point = params["input_point"]
    except KeyError:
        raise KeyError("Отсутствует обязательный параметр 'input_point' в params")

    # Числовые параметры — пробуем привести к float и выдаём информативную ошибку при отсутствии
    def _get_float(key: str) -> float:
        if key not in params:
            raise KeyError(f"Отсутствует обязательный параметр '{key}' в params")
        val = params[key]
        try:
            return float(val)
        except Exception as e:
            raise ValueError(f"Параметр '{key}' должен быть числом (не удалось привести {val!r}): {e}")

    diameter_top = _get_float("diameter_top")
    diameter_base = _get_float("diameter_base")
    diameter_pipe = _get_float("diameter_pipe")
    height_full = _get_float("height_full")
    layout = params.get("layout", "0")
    N = params.get("N", 12)  # количество точек разбиения дуги

    # layout — опционально, по умолчанию "LASER-TEXT"
    layout = params.get("layout", "LASER-TEXT")
    if layout is None:
        layout = "LASER-TEXT"

    # Находим высоту конуса
    height = height_full - math.sqrt((diameter_pipe / 2) ** 2 - (diameter_base / 2) ** 2)

    # Строим развертку конуса и получаем точку апекса развертки
    cone = at_cone_sheet(model, input_point, diameter_base, diameter_top, height, layer_name="0")
    cone_points_list, input_point, apex, theta_rad = cone

    print(cone_points_list, input_point, apex, theta_rad, sep="\n")

    # Вычисляем длину первой образующей — r2 - он же радиус внешней дуги развертки конуса
    p2 = (cone_points_list[1][0], cone_points_list[1][1])
    r2 = distance_2points(apex, p2)
    print(f"r2 = {r2}")

    # Находим угол сегмента
    angle = theta_rad / N

    # Список точек внешней дуги
    arc_points = make_cone_arc_points(apex, r2, theta_rad, N)
    pprint(f"arc_points = {arc_points}")

    # ------------------------------
    # Три особые точки внешней дуги
    # ------------------------------

    # Левая точка (крайняя первая точка полилинии)
    left_point = cone_points_list[2]

    # Правая точка (последняя точка в списке)
    right_point = cone_points_list[1]

    # Верхняя точка над апексом: X совпадает, Y = apex.y + r2
    apex_x, apex_y = apex[:2]
    top_point = (apex_x, apex_y + r2)

    print("Left point:", left_point)
    print("Right point:", right_point)
    print("Top point:", top_point)


# ----------------- Тест -----------------
def run_test():
    """
    Тестовая функция: собирает примерный словарь параметров (как из GUI) и вызывает main().
    Здесь model заменён на None — в реальной среде туда будет передаваться объект ModelSpace AutoCAD.
    """
    acad = ATCadInit()
    adoc, model = acad.document, acad.model_space

    data = {
        "model": model,
        "input_point": [0.0, 0.0],          # пример точки вставки
        "diameter_top": 102.0,              # верхний диаметр конуса
        "diameter_base": 138.0,             # нижний диаметр / хорда
        "diameter_pipe": 273.0,             # диаметр цилиндра
        "height_full": 185.78,              # H — расстояние от верхнего основания до плоскости оси цилиндра
        "layout": "LASER-TEXT",              # имя слоя (опционально)
        "N": 12
    }


    main(data)

if __name__ == "__main__":
    run_test()
