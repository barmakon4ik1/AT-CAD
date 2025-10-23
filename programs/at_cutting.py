import comtypes.client
import comtypes.automation
from shapely.geometry import Polygon, Point
from shapely.affinity import translate, rotate
import numpy as np
import ezdxf
import time
import pythoncom
from config.at_cad_init import ATCadInit
from programs.at_construction import add_polyline, add_circle

# 1. Инициализация AutoCAD через ATCadInit (без создания слоев)
cad = ATCadInit()
acad = cad.application
doc = cad.document
model_space = cad.model_space
utility = doc.Utility

print(f"AutoCAD версия: {acad.Version}")
# Установка активного слоя "0"
doc.ActiveLayer = doc.Layers.Item("0")
print("Активный слой установлен: 0")

# 2. Запрос выбора области в AutoCAD
print("Выберите полилинию области выбора в AutoCAD...")
selected_object = None
max_attempts = 5
attempt = 0
while attempt < max_attempts:
    try:
        time.sleep(0.2)  # Задержка для стабилизации AutoCAD
        utility.Prompt("Выберите полилинию области: \n")
        selected_object = utility.GetEntity()[0]  # Берем первый элемент (объект)
        print(f"Выбран объект: {selected_object.ObjectName}, Слой: {selected_object.Layer}, Закрыт: {selected_object.Closed}")
        if selected_object.ObjectName != "AcDbPolyline" or not selected_object.Closed:
            print("Выберите замкнутую полилинию!")
            attempt += 1
            continue
        break
    except Exception as e:
        print(f"Ошибка при выборе (попытка {attempt + 1}/{max_attempts}): {str(e)}")
        attempt += 1
        if attempt >= max_attempts:
            raise Exception("Не удалось выбрать полилинию после максимального количества попыток")
        continue

if selected_object is None:
    raise Exception("Полилиния области не выбрана")

# Извлечение координат области выбора
selection_points = [(selected_object.Coordinates[i], selected_object.Coordinates[i+1]) for i in range(0, len(selected_object.Coordinates), 2)]
selection_poly = Polygon(selection_points)
print(f"Область выбора (SF-RAHMEN): границы {selection_poly.bounds}, площадь {selection_poly.area}")

# 3. Извлечение полилиний и окружностей
polylines = []
circles = []
for item in model_space:
    if item.ObjectName == "AcDbPolyline" and item.Closed:
        points = [(item.Coordinates[i], item.Coordinates[i+1]) for i in range(0, len(item.Coordinates), 2)]
        polylines.append({"points": points, "layer": item.Layer, "handle": item.ObjectID})
    elif item.ObjectName == "AcDbCircle":
        circles.append({"center": (item.Center[0], item.Center[1]), "radius": item.Radius, "layer": item.Layer, "handle": item.ObjectID})

# 4. Определение листа (слой "SF-TEXT")
sheet = None
for poly in polylines:
    if poly["layer"] == "SF-TEXT":
        sheet = Polygon(poly["points"])
        polylines.remove(poly)
        break

if sheet is None:
    raise ValueError("Лист не найден (слой SF-TEXT)")
print(f"Лист (SF-TEXT): границы {sheet.bounds}, площадь {sheet.area}")

# Нормализация листа к (0, 0)
sheet_centroid = sheet.centroid
normalized_sheet = translate(sheet, xoff=-sheet_centroid.x, yoff=-sheet_centroid.y)
sheet_bounds = normalized_sheet.bounds
print(f"Нормализованные границы листа: {sheet_bounds}")

# 5. Определение примитивов (слой "0")
primitives = []
for poly in polylines:
    if poly["layer"] == "0":
        shapely_poly = Polygon(poly["points"])
        if selection_poly.contains(shapely_poly):
            # Нормализация примитива относительно центроида листа
            normalized_points = [(p[0] - sheet_centroid.x, p[1] - sheet_centroid.y) for p in poly["points"]]
            normalized_poly = Polygon(normalized_points)
            primitives.append({"exterior": normalized_poly, "holes": [], "dxf_entity": {"points": normalized_points}})
            print(f"Примитив (полилиния): площадь {normalized_poly.area}, границы {normalized_poly.bounds}, точки {normalized_points}")

for circle in circles:
    if circle["layer"] == "0":
        shapely_circle = Point(circle["center"]).buffer(circle["radius"])
        if selection_poly.contains(shapely_circle):
            # Нормализация центра окружности
            normalized_center = (circle["center"][0] - sheet_centroid.x, circle["center"][1] - sheet_centroid.y)
            normalized_circle = Point(normalized_center).buffer(circle["radius"])
            primitives.append({"exterior": normalized_circle, "holes": [], "dxf_entity": {"center": normalized_center, "radius": circle["radius"]}})
            print(f"Примитив (окружность): площадь {normalized_circle.area}, центр {normalized_center}, радиус {circle['radius']}")

print(f"Найдено примитивов: {len(primitives)}")

# 6. Сортировка примитивов по площади
primitives.sort(key=lambda p: p["exterior"].area, reverse=True)

# 7. Тестовый вызов add_polyline с жесткими координатами
try:
    test_points = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 10.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 0.0)]
    polyline = add_polyline(model_space, test_points, layer_name="0", closed=True)
    if polyline:
        print("Тестовая полилиния с жесткими координатами создана")
    else:
        print("Ошибка при создании тестовой полилинии. Проверьте logs/at_construction.log")
except Exception as e:
    print(f"Ошибка при тестовом создании полилинии: {str(e)}")

# 8. Тестовое размещение первого примитива
if primitives:
    prim = primitives[0]
    exterior = prim["exterior"]
    print(f"Тестовое размещение первого примитива (площадь {exterior.area}) в (0, 0)")
    try:
        if prim["dxf_entity"].get("points"):  # Полилиния
            points = prim["dxf_entity"]["points"]
            print(f"Координаты полилинии: {points}")
            if len(points) < 2:
                raise ValueError("Полилиния должна содержать не менее 2 точек")
            points_3d = [(p[0], p[1], 0.0) for p in points]
            points_3d.append(points_3d[0])  # Замыкаем полилинию
            print(f"Нормализованные 3D-координаты: {points_3d}")
            polyline = add_polyline(model_space, points_3d, layer_name="0", closed=True)
            if polyline:
                print("Тестовая полилиния размещена в (0, 0)")
            else:
                print("Ошибка при создании тестовой полилинии. Проверьте logs/at_construction.log")
                raise Exception("Failed to create test polyline")
        elif prim["dxf_entity"].get("center"):  # Окружность
            center = [prim["dxf_entity"]["center"][0], prim["dxf_entity"]["center"][1], 0.0]
            radius = prim["dxf_entity"]["radius"]
            circle = add_circle(model_space, center, radius, layer_name="0")
            if circle:
                print(f"Тестовая окружность размещена: центр={center}, радиус={radius}")
            else:
                print("Ошибка при создании тестовой окружности. Проверьте logs/at_construction.log")
                raise Exception("Failed to create test circle")
    except Exception as e:
        print(f"Ошибка при тестовом размещении: {str(e)}")
        raise

# 9. Размещение примитивов
offset = 0.01  # Минимальный отступ
step = 10  # Шаг сетки (увеличен для оптимизации)
placed_primitives = []
print(f"Нормализованные границы листа для размещения: {sheet_bounds}")

for prim in primitives:
    placed = False
    exterior = prim["exterior"]
    prim_bounds = exterior.bounds
    print(f"Попытка размещения примитива с площадью {exterior.area}, границы {prim_bounds}")
    # Ограничиваем перебор с учетом размеров примитива
    x_range = np.arange(0, sheet_bounds[2] - (prim_bounds[2] - prim_bounds[0]) + offset, step)
    y_range = np.arange(0, sheet_bounds[3] - (prim_bounds[3] - prim_bounds[1]) + offset, step)
    position_count = 0
    for x in x_range:
        for y in y_range:
            for angle in [0, 90]:  # Ограничено до 0 и 90 градусов
                position_count += 1
                candidate = rotate(translate(exterior, x, y), angle, origin='centroid')
                buffered = candidate.buffer(offset)
                print(f"Проверка позиции #{position_count}: x={x}, y={y}, угол={angle}, границы кандидата {candidate.bounds}")
                if not normalized_sheet.contains(buffered):
                    print(f"Примитив не помещается при x={x}, y={y}, угол={angle}")
                    continue
                intersects = False
                for placed_prim in placed_primitives:
                    if buffered.intersects(placed_prim["exterior"].buffer(offset)):
                        intersects = True
                        print(f"Пересечение с размещенным примитивом при x={x}, y={y}, угол={angle}")
                        break
                if not intersects:
                    # Прямое размещение в модельном пространстве (с возвращением к исходным координатам листа)
                    if prim["dxf_entity"].get("points"):  # Полилиния
                        points = prim["dxf_entity"]["points"]
                        print(f"Координаты полилинии: {points}")
                        if len(points) < 2:
                            raise ValueError("Полилиния должна содержать не менее 2 точек")
                        rotated_points = rotate(Polygon(points), angle, origin='centroid')
                        translated_points = translate(rotated_points, x + sheet_centroid.x, y + sheet_centroid.y)
                        coords = list(translated_points.exterior.coords)[:-1]
                        coords_3d = [(p[0], p[1], 0.0) for p in coords]
                        coords_3d.append(coords_3d[0])  # Замыкаем полилинию
                        print(f"Размещенные 3D-координаты: {coords_3d}")
                        polyline = add_polyline(model_space, coords_3d, layer_name="0", closed=True)
                        if polyline:
                            print(f"Полилиния размещена: x={x}, y={y}, угол={angle}")
                        else:
                            print("Ошибка при создании полилинии. Проверьте logs/at_construction.log")
                            raise Exception("Failed to create polyline")
                        # Добавление отверстий (если включено)
                        for hole in prim["holes"]:
                            hole_points = list(hole.exterior.coords)[:-1]
                            hole_points_3d = [(p[0], p[1], 0.0) for p in hole_points]
                            hole_points_3d.append(hole_points_3d[0])
                            hole_polyline = add_polyline(model_space, hole_points_3d, layer_name="0", closed=True)
                            if hole_polyline:
                                print(f"Отверстие (полилиния) добавлено")
                            else:
                                print("Ошибка при создании отверстия. Проверьте logs/at_construction.log")
                                raise Exception("Failed to create hole polyline")
                    elif prim["dxf_entity"].get("center"):  # Окружность
                        center = prim["dxf_entity"]["center"]
                        new_center = [center[0] + x + sheet_centroid.x, center[1] + y + sheet_centroid.y, 0.0]
                        radius = prim["dxf_entity"]["radius"]
                        circle = add_circle(model_space, new_center, radius, layer_name="0")
                        if circle:
                            print(f"Окружность размещена: центр={new_center}, радиус={radius}")
                        else:
                            print("Ошибка при создании окружности. Проверьте logs/at_construction.log")
                            raise Exception("Failed to create circle")
                    placed_primitives.append({"exterior": candidate})
                    placed = True
                    break
            if placed:
                break
        if placed:
            break
    if not placed:
        print(f"Не удалось разместить примитив с площадью {exterior.area}")
    else:
        print(f"Примитив размещен после {position_count} проверок")

# 10. Создание DXF для результата
new_doc = ezdxf.new()
new_msp = new_doc.modelspace()
new_msp.add_lwpolyline(list(sheet.exterior.coords), dxfattribs={"layer": "SF-TEXT"})

# Добавление размещенных примитивов в DXF
for prim in placed_primitives:
    if prim["exterior"].type == "Polygon":
        # Денормализация координат для DXF
        denormalized_coords = [(p[0] + sheet_centroid.x, p[1] + sheet_centroid.y) for p in prim["exterior"].exterior.coords]
        new_msp.add_lwpolyline(denormalized_coords, dxfattribs={"layer": "0"})
    elif prim["exterior"].type == "Polygon" and prim["exterior"].buffer(0).type == "Polygon":  # Окружность как полигон
        radius = (prim["exterior"].buffer(0).area / np.pi) ** 0.5
        centroid = prim["exterior"].centroid.coords[0]
        denormalized_center = (centroid[0] + sheet_centroid.x, centroid[1] + sheet_centroid.y)
        new_msp.add_circle(denormalized_center, radius, dxfattribs={"layer": "0"})

# Сохранение результата
new_doc.saveas("d:\\a\\output.dxf")
print(f"Сохранено {len(placed_primitives)} примитивов в d:\\a\\output.dxf")

# Восстановление исходного слоя
cad.restore_original_layer()
