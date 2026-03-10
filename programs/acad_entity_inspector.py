# -*- coding: utf-8 -*-
import math
import time

import pywintypes
import wx
from win32com.client import VARIANT
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


# ---------------------------------------------------------
# COM helpers
# ---------------------------------------------------------

def variant_to_list(value):
    try:
        return list(value)
    except Exception:
        return value


def get_bbox(obj):
    minpt, maxpt = obj.GetBoundingBox()
    return minpt, maxpt


def move_object(obj, dx, dy):
    obj.Move(
        ensure_point_variant((0, 0, 0)),
        ensure_point_variant((dx, dy, 0))
    )


def rotate_object(obj, angle):
    minpt, _ = get_bbox(obj)
    base_pt = ensure_point_variant((minpt[0], minpt[1], 0))
    obj.Rotate(base_pt, math.radians(angle))


# ---------------------------------------------------------
# AutoCAD selection
# ---------------------------------------------------------

def select_single_object(doc):

    sel_name = "PY_TMP_SEL"

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

    return obj


# ---------------------------------------------------------
# Entity inspector
# ---------------------------------------------------------

def dump_entity(obj):

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
        except:
            pass

    lines.append("\n=== ГЕОМЕТРИЯ ===")

    name = obj.ObjectName

    try:

        if name == "AcDbPolyline":

            coords = variant_to_list(obj.Coordinates)

            vertex_count = len(coords) // 2

            lines.append(f"VertexCount: {vertex_count}")
            lines.append(f"Length: {round(obj.Length,3)} мм")
            lines.append(f"Area: {round(getattr(obj,'Area',0),3) / 1000000} м²")

    except Exception as e:
        lines.append(f"Ошибка геометрии: {e}")

    return lines


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


# ---------------------------------------------------------
# Geometry conversion
# ---------------------------------------------------------

def acad_poly_to_shapely(poly):

    coords = list(poly.Coordinates)

    pts = []

    for i in range(0, len(coords), 2):
        pts.append((coords[i], coords[i + 1]))

    debug("AutoCAD vertices:", pts)

    shp = Polygon(pts)

    debug("Shapely valid:", shp.is_valid)
    debug("Shapely area:", shp.area)
    debug("Shapely bounds:", shp.bounds)

    if not shp.is_valid:
        shp = shp.buffer(0)

    return shp


# ---------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------

def draw_polygon(model, poly):

    coords = list(poly.exterior.coords)[:-1]

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
    draw_polygon(model, poly)


# def draw_container_debug(model, container, gap):
#
#     inner = container.buffer(-gap, join_style=2)
#
#     if inner.is_empty:
#         return None
#
#     return draw_polygon(model, inner)


# ---------------------------------------------------------
# Nesting logic
# ---------------------------------------------------------

def bottom_left_place(container, part, gap, step=None, angles=(0, 90)):

    debug("\n===== BOTTOM LEFT PLACE =====")
    if step is None:
        step = gap / 2

    cminx, cminy, cmaxx, cmaxy = container.bounds

    best = None

    for angle in angles:

        rp = rotate(part, angle, origin=(0, 0))

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

                test_gap = test.buffer(gap / 2, join_style=2)

                if container.covers(test_gap):

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


def generate_residuals(container_poly, placed_poly, gap):

    occupied = placed_poly.buffer(gap, join_style=2)

    debug("occupied area:", occupied.area)
    debug("container area:", container_poly.area)

    residual = container_poly.difference(occupied)

    debug("residual area:", residual.area if not residual.is_empty else 0)

    if residual.is_empty:
        return []

    if isinstance(residual, Polygon):
        return [residual]

    if isinstance(residual, MultiPolygon):
        return list(residual.geoms)

    return []


def filter_residuals(polygons, min_area=100):

    return [p for p in polygons if p.area > min_area]


def update_containers(containers, used_container, placed_poly, gap):

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


def find_position_in_containers(containers, part, gap):

    containers = sort_containers(containers)

    best = None
    best_container = None

    for container in containers:

        pos = bottom_left_place(container, part, gap)

        if pos is None:
            continue

        placed_poly, x, y, angle = pos

        if best is None:
            best = pos
            best_container = container

        else:

            _, bx, by, _ = best

            if y < by or (y == by and x < bx):
                best = pos
                best_container = container

    if best is None:
        return None

    return best_container, *best


# ---------------------------------------------------------
# Main algorithm
# ---------------------------------------------------------

def run_algorithm(doc):

    model = doc.ModelSpace

    print("\nВыберите внешний контур:")

    outer = select_single_object(doc)

    if outer is None:
        return

    print("\nВыберите размещаемую деталь:")

    insert_obj = select_single_object(doc)

    if insert_obj is None:
        return

    container_shape = acad_poly_to_shapely(outer)
    part_shape = acad_poly_to_shapely(insert_obj)

    debug_draw_polygon(model, container_shape)

    debug_draw_polygon(model, part_shape)

    if not hasattr(run_algorithm, "containers"):
        run_algorithm.containers = [container_shape]

    result = find_position_in_containers(
        run_algorithm.containers,
        part_shape,
        gap=10
    )

    if result is None:
        print("Не удалось разместить деталь")
        return

    used_container, placed_poly, x, y, angle = result

    run_algorithm.containers = update_containers(
        run_algorithm.containers,
        used_container,
        placed_poly,
        gap=10
    )

    for c in run_algorithm.containers:
        if not c.equals(container_shape):
            draw_polygon(model, c)

    rotate_object(insert_obj, angle)

    pminx, pminy, _, _ = placed_poly.bounds

    minpt, _ = get_bbox(insert_obj)

    dx = pminx - minpt[0]
    dy = pminy - minpt[1]

    move_object(insert_obj, dx, dy)

    print("Размещение выполнено")


# ---------------------------------------------------------
# main
# ---------------------------------------------------------

def main():

    pythoncom.CoInitialize()

    acad = ATCadInit()

    doc = acad.document

    while True:

        cmd = input(
            "\n1-свойства объекта (окно)\n"
            "2-размещение\n"
            "3-свойства объекта (консоль)\n"
            "другое - выход\n"
        )

        if cmd == "2":

            run_algorithm(doc)

        elif cmd == "3":

            obj = select_single_object(doc)

            lines = dump_entity(obj)

            for line in lines:
                print(line)

        elif cmd == "1":

            obj = select_single_object(doc)

            if obj:
                show_entity_window(obj)

        else:
            return


if __name__ == "__main__":
    main()