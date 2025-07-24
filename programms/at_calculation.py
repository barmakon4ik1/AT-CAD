"""
Файл: at_calculation.py
Путь: programms/at_calculation.py
"""
import json
import os


def at_plate_weight(thickness: float, density: float, area: float) -> float:
    """
    Возвращает вес листа в зависимости от материала, толщины и площади фигуры
    Args:
        thickness: толщина материала, мм
        density: плотность материала кг/м куб.
        area: площадь фигуры кв.м

    Returns: вычисленный вес листа, кг

    """
    return round(thickness * density * area / 1e6, 2)


def at_density(material: str) -> float:
    """
    Возвращает плотность материала в зависимости от ее марки
    Args:
        material: строковое название материала из json

    Returns: плотность материала в кг/м куб.

    Raises:
        ValueError: если материал не найден в JSON-файле
    """
    # Получаем путь к папке, где находится скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Формируем абсолютный путь к JSON-файлу
    json_path = os.path.join(script_dir, '..', 'config', 'common_data.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Файл не найден по пути: {json_path}")

    for item in data['dimensions']['material']:
        if item['name'] == material:
            return item['density']

    raise ValueError(f"Материал {material} не найден в JSON-файле")


if __name__ == "__main__":
    material = "3.7035"
    density = at_density(material)
    print(at_plate_weight(3, density, 4.5))
