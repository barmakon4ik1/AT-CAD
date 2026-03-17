# -*- coding: utf-8 -*-
import math
import time

import pywintypes
import wx
from win32com.client import VARIANT
import pythoncom

from config.at_cad_init import ATCadInit
from programs.at_geometry import ensure_point_variant

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

def draw_polygon(model, poly, layer="AM_5"):

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

    # 👉 Назначаем слой
    pl.Layer = layer

    return pl


def debug_draw_polygon(model, poly, layer="AM_5"):
    draw_polygon(model, poly, layer)


# ---------------------------------------------------------
# Nesting logic
# ---------------------------------------------------------

def bottom_left_place(container, part, step=None, angles=(0, 90)):

    debug("\n===== BOTTOM LEFT PLACE =====")

    cminx, cminy, cmaxx, cmaxy = container.bounds

    best = None

    for angle in angles:

        rp = rotate(part, angle, origin=(0, 0))

        pminx, pminy, pmaxx, pmaxy = rp.bounds

        width = pmaxx - pminx
        height = pmaxy - pminy

        # Автоматический шаг
        if step is None:
            step = min(width, height) * 0.1
            step = max(step, 1.0)

        y = cminy

        while y + height <= cmaxy:

            x = cminx

            while x + width <= cmaxx:

                dx = x - pminx
                dy = y - pminy

                test = translate(rp, dx, dy)

                # НИКАКИХ buffer — всё уже учтено
                if container.covers(test):

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


def generate_residuals(container_poly, placed_poly):

    debug("container area:", container_poly.area)
    debug("placed area:", placed_poly.area)

    residual = container_poly.difference(placed_poly)

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


def update_containers(containers, used_container, placed_poly):

    new_containers = []

    for c in containers:

        if c.equals(used_container):

            residuals = generate_residuals(c, placed_poly)

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


def find_position_in_containers(containers, part):

    containers = sort_containers(containers)

    best = None
    best_container = None

    for container in containers:

        # Быстрая отсечка по площади
        if container.area < part.area:
            continue

        pos = bottom_left_place(container, part)

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

    print("\nВыберите внешний контур (один раз):")

    outer = select_single_object(doc)

    if outer is None:
        return

    container_shape = acad_poly_to_shapely(outer)

    gap = 10.0
    half = gap / 2.0

    # --- ЭФФЕКТИВНЫЙ КОНТЕЙНЕР ---
    container_eff = container_shape.buffer(-half, join_style=2)

    if container_eff.is_empty:
        print("Контейнер слишком мал для заданного зазора")
        return

    # Список доступных областей
    containers = [container_eff]

    debug_draw_polygon(model, container_eff)

    print("\nВыбирайте детали для размещения.")
    print("Esc или Enter без выбора — выход.")

    # -------------------------------------------------
    # ОСНОВНОЙ ЦИКЛ
    # -------------------------------------------------

    while True:

        try:
            print("\nВыберите деталь:")
            insert_obj = select_single_object(doc)
        except pywintypes.com_error:
            print("Выход из режима размещения")
            break

        if insert_obj is None:
            print("Выход")
            break

        part_shape = acad_poly_to_shapely(insert_obj)

        # --- ЭФФЕКТИВНАЯ ДЕТАЛЬ ---
        part_eff = part_shape.buffer(half, join_style=2)

        result = find_position_in_containers(
            containers,
            part_eff
        )

        if result is None:
            print("Не удалось разместить деталь")
            continue

        used_container, placed_eff, x, y, angle = result

        # --- ОБНОВЛЯЕМ ДОСТУПНЫЕ ОБЛАСТИ ---
        containers = update_containers(
            containers,
            used_container,
            placed_eff
        )

        # Отрисовка новых областей (для отладки)
        for c in containers:
            draw_polygon(model, c)

        # --- ПЕРЕМЕЩАЕМ РЕАЛЬНУЮ ДЕТАЛЬ ---

        rotate_object(insert_obj, angle)

        placed_real = placed_eff.buffer(-half, join_style=2)

        pminx, pminy, _, _ = placed_real.bounds

        minpt, _ = get_bbox(insert_obj)

        dx = pminx - minpt[0]
        dy = pminy - minpt[1]

        move_object(insert_obj, dx, dy)

        print("Деталь размещена")

    print("Работа завершена")


# ---------------------------------------------------------
# main
# ---------------------------------------------------------

def main():
    pythoncom.CoInitialize()
    acad = ATCadInit()
    doc = acad.document
    run_algorithm(doc)


if __name__ == "__main__":
    main()