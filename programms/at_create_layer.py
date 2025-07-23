# programms/at_create_layer.py
from pyautocad import Autocad, APoint


def at_create_layer():
    """
    Создает предопределенные слои в AutoCAD с заданными параметрами.
    Аналог функции at_create_layer из предоставленного Лисп-кода.
    """
    try:
        # Подключение к AutoCAD
        acad = Autocad(create_if_not_exists=True)
        doc = acad.ActiveDocument
        layers = doc.Layers

        # Список слоев с их параметрами
        layer_data = [
            {"name": "0", "color": 7, "linetype": "CONTINUOUS", "lineweight": 0.25},
            {"name": "SF-ARE", "color": 233, "linetype": "PHANTOM2", "plot": False},
            {"name": "AM_5", "color": 110, "linetype": "CONTINUOUS", "lineweight": 0.05},
            {"name": "LASER-TEXT", "color": 2, "linetype": "CONTINUOUS"},
            {"name": "schrift", "color": 4, "linetype": "CONTINUOUS"},
            {"name": "SF-RAHMEN", "color": 140, "linetype": "CONTINUOUS"},
            {"name": "SF-TEXT", "color": 82, "linetype": "CONTINUOUS"},
            {"name": "TEXT", "color": 2, "linetype": "CONTINUOUS"},
            {"name": "AM_7", "color": 4, "linetype": "AM_ISO08W050", "lineweight": 0.05}
        ]

        for layer in layer_data:
            # Создание нового слоя
            new_layer = layers.Add(layer["name"])

            # Установка цвета (ACI color)
            new_layer.Color = layer["color"]

            # Установка типа линии
            try:
                new_layer.Linetype = layer["linetype"]
            except:
                print(f"Тип линии {layer['linetype']} не найден для слоя {layer['name']}. Установлен CONTINUOUS.")
                new_layer.Linetype = "CONTINUOUS"

            # Установка веса линии, если указан
            if "lineweight" in layer:
                # AutoCAD принимает вес линии в сотых миллиметра (например, 0.25 мм = 25)
                new_layer.Lineweight = int(layer["lineweight"] * 100)

            # Установка параметра печати, если указан
            if "plot" in layer:
                new_layer.Plottable = layer["plot"]

        print("Слои успешно созданы.")

    except Exception as e:
        print(f"Ошибка при создании слоев: {e}")


if __name__ == "__main__":
    at_create_layer()
