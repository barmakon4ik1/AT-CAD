# -*- coding: utf-8 -*-
import math
import time

import pywintypes
import wx
from win32com.client import VARIANT
from typing import Union, List, Tuple, Any
import pythoncom

from config.at_cad_init import ATCadInit
from programs.at_geometry import ensure_point_variant
from windows.at_entity_inspector import EntityInspectorFrame
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import translate, rotate

DEBUG = True

def debug(*args):
    if DEBUG:
        print(*args)

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

    def com_retry(func, retries=10, delay=0.1):

        for _ in range(retries):
            try:
                return func()
            except pywintypes.com_error as e:
                if e.args[0] == -2147418111:
                    time.sleep(delay)
                    continue
                raise
        raise RuntimeError("AutoCAD COM не отвечает")

    count = com_retry(lambda: sel.Count)
    obj = com_retry(lambda: sel.Item(0))

    print("Количество выбранных объектов:", count)

    for i in range(count):
        o = sel.Item(i)
        print(f"Index {i}: {o.ObjectName}, Handle={o.Handle}")

    return sel.Item(0)


def dump_entity(obj) -> list[str]:
    """
    Собирает информацию об объекте AutoCAD в список строк.
    Не печатает сам — возвращает lines.
    """
    lines = ["=== ОСНОВНЫЕ СВОЙСТВА ==="]

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
            lines.append(f"{p}: {getattr(obj, p)}")
        except Exception:
            pass

    lines.append("\n=== ГЕОМЕТРИЯ ===")

    name = obj.ObjectName

    try:
        if name == "AcDbLine":
            sp = variant_to_list(obj.StartPoint)
            ep = variant_to_list(obj.EndPoint)
            lines.append(f"StartPoint: {tuple(round(c,3) for c in sp)}")
            lines.append(f"EndPoint:   {tuple(round(c,3) for c in ep)}")
            lines.append(f"Length:     {round(obj.Length,3)}")

        elif name == "AcDbCircle":
            center = variant_to_list(obj.Center)
            lines.append(f"Center: {tuple(round(c,3) for c in center)}")
            lines.append(f"Radius: {round(obj.Radius,3)}")
            lines.append(f"Area:   {round(obj.Area,3) / 1000000}")

        elif name == "AcDbArc":
            center = variant_to_list(obj.Center)
            lines.append(f"Center:     {tuple(round(c,3) for c in center)}")
            lines.append(f"Radius:     {round(obj.Radius,3)}")
            lines.append(f"StartAngle: {round(obj.StartAngle,3)}")
            lines.append(f"EndAngle:   {round(obj.EndAngle,3)}")
            lines.append(f"ArcLength:  {round(obj.ArcLength,3)}")

        elif name == "AcDbPolyline":
            coords = variant_to_list(obj.Coordinates)
            vertex_count = len(coords) // 2
            lines.append(f"VertexCount: {vertex_count}")
            lines.append(f"Length: {round(obj.Length,3)} мм")
            lines.append(f"Area: {round(getattr(obj,'Area',0),3) / 1000000} м²")
            lines.append(f"Closed: {obj.Closed}")

            lines.append("\nCoordinates (X,Y) | Bulge")
            bulges = []
            for i in range(vertex_count):
                try:
                    bulge = obj.GetBulge(i)
                except Exception:
                    bulge = 0.0
                bulges.append(round(bulge,3))
                x = round(coords[2*i],3)
                y = round(coords[2*i+1],3)
                lines.append(f"{x:10.3f}, {y:10.3f} | {bulges[i]:6.3f}")

        elif name == "AcDbPoint":
            coords = variant_to_list(obj.Coordinates)
            lines.append(f"Coordinates: {tuple(round(c,3) for c in coords)}")

        else:
            lines.append("Тип не обработан, но COM-свойства доступны.")

    except Exception as e:
        lines.append(f"Ошибка геометрии: {e}")

    # --- все COM-свойства ---
    lines.append("\n=== ВСЕ ДОСТУПНЫЕ COM-СВОЙСТВА ===")
    exclude_props = {"Coordinates"}

    for attr in dir(obj):
        if attr.startswith("_") or attr in exclude_props:
            continue

        try:
            value = getattr(obj, attr)
            if callable(value):
                continue

            # пропускаем длинные массивы координат
            if isinstance(value, (list, tuple)) and len(value) > 3:
                continue

            if isinstance(value, float):
                value = round(value,3)
            lines.append(f"{attr}: {value}")
        except:
            raise "Ошибка получения аттрибутов или свойств"

    return lines


def object_select():

    pythoncom.CoInitialize()

    acad = ATCadInit()
    doc, model = acad.document, acad.model_space

    obj = select_single_object(doc)

    if obj is None:
        print("Объект не выбран.")
        return

    lines = dump_entity(obj)
    for line in lines:
        print(line)


# -------------------------------------
# Временный габарит окружности (прямоугольник)
# -------------------------------------
def make_circle_bbox_poly(model, circle):
    """
    Создаёт временную прямоугольную полилинию по габариту окружности.
    Нужна для использования существующего алгоритма размещения.
    """
    cx, cy, cz = circle.Center
    r = circle.Radius

    pts = [
        cx - r, cy - r,
        cx + r, cy - r,
        cx + r, cy + r,
        cx - r, cy + r
    ]

    pl = model.AddLightWeightPolyline(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, pts))
    pl.Closed = True

    return pl


def move_circle_to_bbox(circle, bbox_poly):
    """
    Перемещает окружность туда же, куда был перемещён её габарит.
    """
    circ_min, _ = get_bbox(circle)
    bbox_min, _ = get_bbox(bbox_poly)

    dx = bbox_min[0] - circ_min[0]
    dy = bbox_min[1] - circ_min[1]

    circle.Move(
        ensure_point_variant((0,0,0)),
        ensure_point_variant((dx,dy,0))
    )


def place_circle_inside(inner_poly, circle, model):

    bbox_poly = make_circle_bbox_poly(model, circle)

    align_polyline_axis(bbox_poly)
    move_to_left(inner_poly, bbox_poly)

    if fits_inside(inner_poly, bbox_poly):
        move_circle_to_bbox(circle, bbox_poly)
        bbox_poly.Delete()
        print("Окружность размещена.")
        return True

    rotate_90(bbox_poly)
    move_to_left(inner_poly, bbox_poly)

    if fits_inside(inner_poly, bbox_poly):
        move_circle_to_bbox(circle, bbox_poly)
        bbox_poly.Delete()
        print("Окружность размещена после поворота.")
        return True

    bbox_poly.Delete()
    print("Окружность не помещается.")
    return False


def show_entity_window(obj):

    app = wx.GetApp()
    created_here = False

    if app is None:
        app = wx.App(False)
        created_here = True

    frame = EntityInspectorFrame(obj)
    frame.Show()

    if created_here:
        app.MainLoop()


def move_object(obj, dx, dy):

    obj.Move(
        ensure_point_variant((0,0,0)),
        ensure_point_variant((dx,dy,0))
    )


def grid_search_place(inner_poly, obj, step=20.0):

    inner_min, inner_max = get_bbox(inner_poly)
    obj_min, obj_max = get_bbox(obj)

    width = obj_max[0] - obj_min[0]
    height = obj_max[1] - obj_min[1]

    start_x = inner_min[0]
    start_y = inner_min[1]

    max_x = inner_max[0] - width
    max_y = inner_max[1] - height

    x = start_x

    while x <= max_x:

        y = start_y

        while y <= max_y:

            # возвращаем объект в исходную позицию
            cur_min, _ = get_bbox(obj)

            dx = x - cur_min[0]
            dy = y - cur_min[1]

            move_object(obj, dx, dy)

            if fits_inside(inner_poly, obj):
                print(f"Найдена позиция grid: {x:.1f}, {y:.1f}")
                return True

            y += step

        x += step

    return False


# -------------------------------------
# Bottom-left размещение
# -------------------------------------
def place_bottom_left(inner_poly, insert_obj, step=1.0, max_iter=10000):
    """
    Улучшенное размещение объекта.
    Объект сначала ставится в левый нижний угол,
    затем постепенно сдвигается вниз и влево,
    пока возможно.

    Args:
        inner_poly: контейнер
        insert_obj: размещаемый объект
        step: шаг поиска
        max_iter: защита от бесконечного цикла
    """

    # начальная позиция
    move_to_left(inner_poly, insert_obj)

    if not fits_inside(inner_poly, insert_obj):
        return False

    moved = True
    iterations = 0

    while moved and iterations < max_iter:

        moved = False
        iterations += 1

        # пробуем вниз
        insert_obj.Move(
            ensure_point_variant((0,0,0)),
            ensure_point_variant((0,-step,0))
        )

        if fits_inside(inner_poly, insert_obj):
            moved = True
            continue
        else:
            # откат
            insert_obj.Move(
                ensure_point_variant((0,0,0)),
                ensure_point_variant((0,step,0))
            )

        # пробуем влево
        insert_obj.Move(
            ensure_point_variant((0,0,0)),
            ensure_point_variant((-step,0,0))
        )

        if fits_inside(inner_poly, insert_obj):
            moved = True
            continue
        else:
            # откат
            insert_obj.Move(
                ensure_point_variant((0,0,0)),
                ensure_point_variant((step,0,0))
            )

    return True


# -------------------------------------
# Быстрое bottom-left размещение
# -------------------------------------
def place_bottom_left_fast(inner_poly, insert_obj, step=5.0):

    inner_min, inner_max = get_bbox(inner_poly)
    ins_min, ins_max = get_bbox(insert_obj)

    width = ins_max[0] - ins_min[0]
    height = ins_max[1] - ins_min[1]

    best_x = None
    best_y = None

    y = inner_min[1]

    while y + height <= inner_max[1]:

        x = inner_min[0]

        while x + width <= inner_max[0]:

            test_min = (x, y)
            test_max = (x + width, y + height)

            if (
                test_min[0] >= inner_min[0] and
                test_min[1] >= inner_min[1] and
                test_max[0] <= inner_max[0] and
                test_max[1] <= inner_max[1]
            ):
                best_x = x
                best_y = y
                break

            x += step

        if best_x is not None:
            break

        y += step

    if best_x is None:
        return False

    dx = best_x - ins_min[0]
    dy = best_y - ins_min[1]

    insert_obj.Move(
        ensure_point_variant((0,0,0)),
        ensure_point_variant((dx,dy,0))
    )

    return True


def rotate_object(obj, angle):
    """Универсальная функция вращения"""
    minpt, _ = get_bbox(obj)
    base_pt = ensure_point_variant((minpt[0], minpt[1], 0))
    obj.Rotate(base_pt, math.radians(angle))


# -------------------------------------
# размещение с вращением
# -------------------------------------
def place_with_rotation(inner_poly, insert_obj, angles=(0,90)):

    for angle in angles:

        if angle != 0:
            rotate_object(insert_obj, angle)

        ok = place_bottom_left_fast(inner_poly, insert_obj)

        if ok:
            print(f"Размещено с углом {angle}°")
            return True

    return False


def polygon_vertices(poly):
    """
    Возвращает список вершин Shapely Polygon.
    Последняя точка (дублирующая первую) удаляется.
    """

    coords = list(poly.exterior.coords)

    # последняя вершина повторяет первую
    return coords[:-1]


def touch_place(container, part, gap, model=None, angles=(0,90)):
    """
    Контактное размещение детали.

    Алгоритм:
    каждая вершина детали совмещается
    с каждой вершиной контейнера.

    Добавлен полный DEBUG-контроль.
    """

    debug("\n===== TOUCH PLACE START =====")

    debug("container bounds:", container.bounds)
    debug("part bounds:", part.bounds)

    # контейнер с учетом технологического зазора
    inner_container = container.buffer(-gap)

    debug("container buffer(-gap) bounds:", inner_container.bounds)

    container_vertices = polygon_vertices(container)

    debug("container vertices:")
    for v in container_vertices:
        debug("   ", v)

    best = None

    for angle in angles:

        debug("\n---- rotation:", angle)

        # вращаем деталь
        rp = rotate(part, angle, origin=(0,0))

        debug("rotated part bounds:", rp.bounds)

        part_vertices = polygon_vertices(rp)

        debug("part vertices:")
        for v in part_vertices:
            debug("   ", v)

        for cvx, cvy in container_vertices:

            for pvx, pvy in part_vertices:

                # вычисляем смещение
                dx = cvx - pvx
                dy = cvy - pvy

                debug("\n--- candidate ---")
                debug("container vertex:", cvx, cvy)
                debug("part vertex:", pvx, pvy)
                debug("translation:", dx, dy)

                # создаём тестовую позицию
                test = translate(rp, dx, dy)

                debug("test bounds:", test.bounds)

                # быстрый bbox тест
                cminx, cminy, cmaxx, cmaxy = inner_container.bounds
                tminx, tminy, tmaxx, tmaxy = test.bounds

                bbox_ok = (
                    tminx >= cminx and
                    tminy >= cminy and
                    tmaxx <= cmaxx and
                    tmaxy <= cmaxy
                )

                debug("bbox inside:", bbox_ok)

                # точная проверка
                inside = inner_container.contains(test)
                intersects = inner_container.intersects(test)

                debug("contains:", inside)
                debug("intersects:", intersects)

                if not inside:
                    continue

                minx, miny, _, _ = test.bounds

                debug("VALID POSITION FOUND")

                if best is None:

                    best = (test, minx, miny, angle)

                    debug("first best:", best)

                else:

                    _, bx, by, _ = best

                    # bottom-left критерий
                    if miny < by or (miny == by and minx < bx):

                        debug("better position found")

                        best = (test, minx, miny, angle)

    debug("\ncontainer area:", container.area)
    debug("part area:", part.area)

    if best:
        debug("BEST RESULT:", best)
    else:
        debug("NO VALID POSITION FOUND")

    return best


def minkowski_sum(polyA, polyB):

    result = []

    for ax, ay in polyA.exterior.coords:
        shifted = translate(polyB, ax, ay)
        result.append(shifted)

    union = result[0]

    for g in result[1:]:
        union = union.union(g)

    return union


def invert_polygon(poly):

    coords = [(-x, -y) for x, y in poly.exterior.coords]

    return Polygon(coords)


def compute_nfp(container, part):

    inv = invert_polygon(part)

    nfp = minkowski_sum(container, inv)

    return nfp


def find_best_point(nfp):

    best = None

    for x, y in nfp.exterior.coords:

        if best is None:
            best = (x, y)
        else:
            bx, by = best

            if y < by or (y == by and x < bx):
                best = (x, y)

    return best


def place_part(container, part, gap):

    nfp = compute_nfp(container.buffer(-gap), part)

    point = find_best_point(nfp)

    if point is None:
        return None

    px, py = point

    placed = translate(part, px, py)

    if container.contains(placed):

        return placed, px, py

    return None


def nfp_solver(container, parts, gap=0):

    placements = []

    current_container = container

    for part in parts:

        res = place_part(current_container, part, gap)

        if res is None:
            break

        placed, x, y = res

        placements.append(placed)

        # вырезаем деталь из контейнера
        current_container = current_container.difference(
            placed.buffer(gap)
        )

    return placements


def best_rotation(container, part, gap):

    angles = [0, 90, 180, 270]

    best = None

    for a in angles:

        rp = rotate(part, a, origin=(0,0))

        res = place_part(container, rp, gap)

        if res is None:
            continue

        placed, x, y = res

        minx, miny, _, _ = placed.bounds

        if best is None:
            best = (placed, minx, miny, a)

        else:
            _, bx, by, _ = best

            if miny < by or (miny == by and minx < bx):
                best = (placed, minx, miny, a)

    return best


# -------------------------------------
# Полный алгоритм размещения
# -------------------------------------
def run_algorithm(doc):
    model = doc.ModelSpace

    print("\nВыберите внешний прямоугольник:")
    outer = select_single_object(doc)
    if outer is None:
        return

    inner = outer
    if inner is None:
        print("Не удалось создать offset.")
        return

    print("\nВыберите размещаемый объект:")
    insert_obj = select_single_object(doc)
    if insert_obj is None:
        return

    if insert_obj.ObjectName not in ("AcDbPolyline", "AcDbCircle"):
        print("Поддерживаются только полилиния и окружность.")
        return

    if insert_obj.ObjectName == "AcDbCircle":
        place_circle_inside(inner, insert_obj, model)
        return

    insert_poly = insert_obj

    container_shape = acad_poly_to_shapely(inner)
    part_shape = acad_poly_to_shapely(insert_poly)

    # debug исходного контейнера
    debug_draw_polygon(model, container_shape)

    # debug внутреннего контейнера
    draw_container_debug(model, container_shape, 10)

    # debug детали
    debug_draw_polygon(model, part_shape)

    debug("------ CONTAINER ------")
    debug(container_shape)

    debug("------ PART ------")
    debug(part_shape)

    if not hasattr(run_algorithm, "containers"):
        # первый запуск
        run_algorithm.containers = [container_shape]

    result = find_position_in_containers(
        run_algorithm.containers,
        part_shape,
        gap=10,
        model=None
    )

    if result is None:
        print("Не удалось разместить деталь")
        return

    used_container, placed_poly, x, y, angle = result

    # обновляем контейнеры
    run_algorithm.containers = update_containers(
        run_algorithm.containers,
        used_container,
        placed_poly,
        gap=10
    )

    for c in run_algorithm.containers:
        draw_polygon(model, c)

    rotate_object(insert_poly, angle)

    pminx, pminy, _, _ = placed_poly.bounds

    minpt, _ = get_bbox(insert_poly)

    dx = pminx - minpt[0]
    dy = pminy - minpt[1]

    move_object(insert_poly, dx, dy)

    print("Размещение выполнено NFP solver")



def generate_residuals(container_poly, placed_poly, gap):
    """
    Генерация остаточных контейнеров.

    Используется половинный gap,
    чтобы суммарный зазор между деталями был ровно gap.
    """

    occupied = placed_poly.buffer(gap/2, join_style=2)

    residual = container_poly.difference(occupied)

    if residual.is_empty:
        return []

    if isinstance(residual, Polygon):
        return [residual]

    if isinstance(residual, MultiPolygon):
        return list(residual.geoms)

    return []


def filter_residuals(polygons, min_area=100):

    """
    Удаляет слишком маленькие остаточные полигоны.
    """

    return [p for p in polygons if p.area > min_area]


def draw_polygon(model, poly):
    """
    Рисует Shapely Polygon в AutoCAD как полилинию.
    """

    coords = list(poly.exterior.coords)

    pts = []

    for x, y in coords:
        pts.extend([x, y])

    pts_variant = VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8,
        pts
    )

    pl = model.AddLightWeightPolyline(pts_variant)

    pl.Closed = True

    return pl


def debug_draw_polygon(model, poly):

    coords = list(poly.exterior.coords)

    pts = []
    for x, y in coords:
        pts.extend([x, y])

    pts_variant = VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8,
        pts
    )

    pl = model.AddLightWeightPolyline(pts_variant)
    pl.Closed = True


def draw_point(model, x, y):

    model.AddPoint(
        ensure_point_variant((x,y,0))
    )


def update_containers(containers, used_container, placed_poly, gap):

    """
    Обновляет список контейнеров после размещения детали.
    """

    new_containers = []

    for c in containers:

        if c == used_container:

            residuals = generate_residuals(c, placed_poly, gap)

            residuals = filter_residuals(residuals)
            for r in residuals:
                debug("residual area:", r.area)

            new_containers.extend(residuals)

        else:
            new_containers.append(c)

    return new_containers


def sort_containers(containers):

    return sorted(
        containers,
        key=lambda p: (p.bounds[1], p.bounds[0])
    )


def find_position_in_containers(containers, part, gap, model):

    """
    Ищет позицию детали среди всех доступных контейнеров.

    Контейнеры сортируются по правилу Bottom-Left.

    Args:
        containers : list[Polygon]
        part : Polygon
        gap : float
        model : AutoCAD ModelSpace (для debug)

    Returns:
        (container, placed_poly, x, y, angle) или None
    """

    debug("\n===== SEARCH CONTAINER =====")

    containers = sort_containers(containers)

    debug("containers count:", len(containers))

    best = None
    best_container = None

    for i, container in enumerate(containers):

        debug("\ncontainer index:", i)
        debug("container bounds:", container.bounds)
        debug("container area:", container.area)

        pos = bottom_left_place(container, part, gap)

        if pos is None:
            debug("no position in this container")
            continue

        placed_poly, x, y, angle = pos

        debug("candidate placement:", x, y)

        if best is None:

            best = pos
            best_container = container

        else:

            _, bx, by, _ = best

            if y < by or (y == by and x < bx):

                debug("better container found")

                best = pos
                best_container = container

    if best is None:

        debug("NO CONTAINER FOUND")

        return None

    debug("\nSELECTED CONTAINER")
    debug("position:", best[1], best[2])

    return best_container, *best


def nesting_solver(container, parts, gap):
    debug("===== SOLVER START =====")
    debug("container area:", container.area)
    debug("parts:", len(parts))
    debug("gap:", gap)
    containers = [container]
    placements = []

    for part in parts:

        result = find_position_in_containers(
            containers,
            part,
            gap,
            None
        )

        if result is None:
            print("Деталь не помещается")
            break

        used_container, placed_poly, x, y, angle = result

        placements.append((placed_poly, x, y, angle))

        containers = update_containers(
            containers,
            used_container,
            placed_poly,
            gap
        )

    return placements, containers


def acad_poly_to_shapely(poly):

    coords = list(poly.Coordinates)

    pts = []
    for i in range(0, len(coords), 2):
        pts.append((coords[i], coords[i+1]))

    debug("AutoCAD vertices:", pts)

    shp = Polygon(pts)

    debug("Shapely valid:", shp.is_valid)
    debug("Shapely area:", shp.area)
    debug("Shapely bounds:", shp.bounds)

    if not shp.is_valid:
        debug("FIXING geometry using buffer(0)")
        shp = shp.buffer(0)

    return shp


def shapely_bbox(poly):

    minx, miny, maxx, maxy = poly.bounds
    return minx, miny, maxx, maxy


def bottom_left_place(container, part, gap, step=20, angles=(0,90)):
    """
    Bottom-Left размещение детали.

    ВАЖНО:
    gap учитывается через buffer детали,
    поэтому контейнер НЕ уменьшается.

    Это обеспечивает:
    • отступ от стенки
    • правильный зазор между деталями
    """

    debug("\n===== BOTTOM LEFT PLACE =====")

    cminx, cminy, cmaxx, cmaxy = container.bounds

    best = None

    for angle in angles:

        debug("\nrotation:", angle)

        rp = rotate(part, angle, origin=(0,0))

        pminx, pminy, pmaxx, pmaxy = rp.bounds

        width = pmaxx - pminx
        height = pmaxy - pminy

        y = cminy

        while y + height <= cmaxy:

            x = cminx

            while x + width <= cmaxx:

                dx = x - pminx
                dy = y - pminy

                test = translate(rp, dx, dy)

                # учитываем технологический зазор
                test_gap = test.buffer(gap/2, join_style=2)

                if container.contains(test_gap):

                    if best is None:

                        best = (test, x, y, angle)

                    else:

                        _, bx, by, _ = best

                        if y < by or (y == by and x < bx):

                            best = (test, x, y, angle)

                    break

                x += step

            if best:
                break

            y += step

    return best


def draw_container_debug(model, container, gap):
    """
    Рисует внутренний контейнер (учёт технологического зазора).

    Используется только для визуального контроля алгоритма.
    Сам solver работает с исходным контейнером.
    """

    inner = container.buffer(-gap, join_style=2)

    if inner.is_empty:
        print("Container vanished after buffer")
        return None

    return draw_polygon(model, inner)


def main():

    pythoncom.CoInitialize()

    acad = ATCadInit()
    doc, model = acad.document, acad.model_space

    while True:
        select_operation = input("Ввести код операции: \n1-свойства объекта (окно)\n2-размещение\n3-свойства объекта (консоль)\nДругой символ-выход из программы\n")
        if select_operation == "2":
            run_algorithm(doc)
        elif select_operation == "3":
            obj = select_single_object(doc)

            if obj is None:
                print("Объект не выбран.")

            lines = dump_entity(obj)
            for line in lines:
                print(line)
        elif select_operation == "1":
            obj = select_single_object(doc)
            if obj:
                show_entity_window(obj)
        else:
            return False


if __name__ == "__main__":
    main()