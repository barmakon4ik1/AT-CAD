# -*- coding: utf-8 -*-
import math
from win32com.client import VARIANT
from typing import Union, List, Tuple
import pythoncom

from config.at_cad_init import ATCadInit
from programs.at_geometry import ensure_point_variant


# -------------------------------------
# Проверка направления обхода полилинии
# -------------------------------------
def polyline_is_ccw(poly):
    """
    Определяет направление обхода замкнутой полилинии.
    Возвращает True, если обход против часовой стрелки (CCW),
    False — если по часовой стрелке (CW).

    Args:
        poly: AcadLWPolyline

    Returns:
        bool: True = CCW, False = CW
    """
    coords = list(poly.Coordinates)
    s = 0.0
    n = len(coords) // 2
    for i in range(n):
        x1, y1 = coords[2 * i], coords[2 * i + 1]
        x2, y2 = coords[2 * ((i + 1) % n)], coords[2 * ((i + 1) % n) + 1]
        s += (x2 - x1) * (y2 + y1)
    # s < 0 → обход против часовой стрелки
    return s < 0


# -------------------------------------
# Offset всегда внутрь
# -------------------------------------
def offset_inside(poly, distance: float):
    """
    Создаёт смещённую полилинию "внутрь" исходного контура,
    независимо от направления обхода вершин.

    Args:
        poly: AcadLWPolyline
        distance: положительное значение смещения

    Returns:
        AcadLWPolyline: первая смещённая полилиния
    """
    # Если полилиния CCW, offset с отрицательным distance идёт внутрь
    # Если CW, offset с положительным distance идёт внутрь
    if polyline_is_ccw(poly):
        distance = -abs(distance)
    else:
        distance = abs(distance)
    inner_offset = poly.Offset(distance)
    # offset может вернуть коллекцию полилиний
    return list(inner_offset)[0] if inner_offset else None


# -------------------------------------
# Пример использования в алгоритме размещения
# -------------------------------------
def make_inner_offset(poly, distance: float):
    """
    Старый интерфейс совместим с offset_inside.
    """
    return offset_inside(poly, distance)


# -------------------------------------
# Функции размещения прямоугольника
# -------------------------------------
def align_polyline_axis(poly):
    coords = list(poly.Coordinates)
    x1, y1 = coords[0], coords[1]
    x2, y2 = coords[2], coords[3]
    angle = math.atan2(y2 - y1, x2 - x1)
    # определяем ближайшую ось
    if abs(math.cos(angle)) > abs(math.sin(angle)):
        target_angle = 0
    else:
        target_angle = math.pi / 2
    delta = target_angle - angle
    base_pt = ensure_point_variant((x1, y1, 0))
    poly.Rotate(base_pt, delta)


def rotate_90(poly):
    minpt, _ = get_bbox(poly)
    base_pt = ensure_point_variant((minpt[0], minpt[1], 0))
    poly.Rotate(base_pt, math.pi / 2)


def get_bbox(obj):
    minpt, maxpt = obj.GetBoundingBox()
    return minpt, maxpt


def move_to_left(inner_poly, insert_poly):
    inner_min, _ = get_bbox(inner_poly)
    ins_min, _ = get_bbox(insert_poly)
    dx = inner_min[0] - ins_min[0]
    dy = inner_min[1] - ins_min[1]
    insert_poly.Move(
        ensure_point_variant((0, 0, 0)),
        ensure_point_variant((dx, dy, 0))
    )


def fits_inside(inner_poly, insert_poly):
    inner_min, inner_max = get_bbox(inner_poly)
    ins_min, ins_max = get_bbox(insert_poly)
    if ins_min[0] < inner_min[0]: return False
    if ins_min[1] < inner_min[1]: return False
    if ins_max[0] > inner_max[0]: return False
    if ins_max[1] > inner_max[1]: return False
    return True


def place_inside(inner_poly, insert_poly):
    align_polyline_axis(insert_poly)
    move_to_left(inner_poly, insert_poly)
    if not fits_inside(inner_poly, insert_poly):
        print("Примитив не помещается внутри.")
        return False
    print("Размещение выполнено.")
    return True


def variant_to_list(value):
    try:
        return list(value)
    except Exception:
        return value


def select_single_object(doc):
    sel_name = "PY_TMP_SEL"

    # удаляем старый набор
    try:
        doc.SelectionSets.Item(sel_name).Delete()
    except:
        pass

    sel = doc.SelectionSets.Add(sel_name)

    print("Выберите объект в AutoCAD...")
    sel.SelectOnScreen()

    if sel.Count == 0:
        return None

    print("Количество выбранных объектов:", sel.Count)

    for i in range(sel.Count):
        o = sel.Item(i)
        print(f"Index {i}: {o.ObjectName}, Handle={o.Handle}")

    return sel.Item(0)


def dump_entity(obj):

    print("\n=== ОСНОВНЫЕ СВОЙСТВА ===")

    base_props = [
        "ObjectName",
        "Layer",
        "Linetype",
        "LinetypeScale",
        "Lineweight",
        "Color",
        "Handle",
        "Visible"
    ]

    for p in base_props:
        try:
            print(f"{p}: {getattr(obj, p)}")
        except:
            pass

    print("\n=== ГЕОМЕТРИЯ ===")

    name = obj.ObjectName

    try:
        if name == "AcDbLine":
            print("StartPoint:", variant_to_list(obj.StartPoint))
            print("EndPoint:", variant_to_list(obj.EndPoint))
            print("Length:", obj.Length)

        elif name == "AcDbCircle":
            print("Center:", variant_to_list(obj.Center))
            print("Radius:", obj.Radius)
            print("Area:", obj.Area)

        elif name == "AcDbArc":
            print("Center:", variant_to_list(obj.Center))
            print("Radius:", obj.Radius)
            print("StartAngle:", obj.StartAngle)
            print("EndAngle:", obj.EndAngle)
            print("ArcLength:", obj.ArcLength)

        elif name == "AcDbPolyline":
            coords = variant_to_list(obj.Coordinates)
            print("Coordinates:", coords)

            vertex_count = len(coords) // 2
            print("VertexCount:", vertex_count)

            bulges = []
            for i in range(vertex_count):
                try:
                    bulges.append(obj.GetBulge(i))
                except:
                    bulges.append(0.0)

            print("Bulges:", bulges)

            print("Length:", obj.Length)
            print("Area:", getattr(obj, "Area", None))
            print("Closed:", obj.Closed)

        elif name == "AcDbPoint":
            print("Coordinates:", variant_to_list(obj.Coordinates))

        else:
            print("Тип не обработан, но COM-свойства доступны.")

    except Exception as e:
        print("Ошибка геометрии:", e)

    print("\n=== ВСЕ ДОСТУПНЫЕ COM-СВОЙСТВА ===")

    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            value = getattr(obj, attr)
            if not callable(value):
                print(f"{attr}: {value}")
        except:
            pass


def object_select():

    pythoncom.CoInitialize()

    acad = ATCadInit()
    doc, model = acad.document, acad.model_space

    obj = select_single_object(doc)

    if obj is None:
        print("Объект не выбран.")
        return

    dump_entity(obj)


# -------------------------------------
# Полный алгоритм размещения
# -------------------------------------
def run_algorithm(doc):

    print("\nВыберите внешний прямоугольник:")
    outer = select_single_object(doc)
    if outer is None:
        return

    inner = make_inner_offset(outer, 10.0)
    if inner is None:
        print("Не удалось создать offset.")
        return

    print("\nВыберите размещаемый прямоугольник:")
    insert_poly = select_single_object(doc)
    if insert_poly is None:
        return

    # первая попытка
    align_polyline_axis(insert_poly)
    move_to_left(inner, insert_poly)

    if fits_inside(inner, insert_poly):
        print("Размещение выполнено без поворота.")
        return

    # если не влез — пробуем повернуть
    print("Не помещается. Пробуем поворот 90°...")

    rotate_90(insert_poly)
    move_to_left(inner, insert_poly)

    if fits_inside(inner, insert_poly):
        print("Размещение выполнено после поворота.")
        return

    print("Примитив не помещается внутрь.")


def main():

    pythoncom.CoInitialize()

    acad = ATCadInit()
    doc, model = acad.document, acad.model_space

    select_operation = input("Ввести код операции: \n1-свойства объекта\n2-размещение\nДругой символ-выход из программы\n")
    if select_operation == "2":
        return run_algorithm(doc)
    elif select_operation == "1":
        obj = select_single_object(doc)

        if obj is None:
            print("Объект не выбран.")
            return None

        return dump_entity(obj)
    else:
        return None


if __name__ == "__main__":
    main()