# ==============================================================
# Файл: programs/at_packing.py
# Назначение: Упаковка примитивов (слой "0") внутри контейнера (слой "SF-TEXT")
# Автор: (your project)
# ==============================================================

import math
import random
import time
from typing import List, Tuple, Dict, Any, Optional

from shapely.geometry import Polygon, Point
from shapely.affinity import translate as shp_translate, rotate as shp_rotate
from shapely.ops import unary_union
from shapely.geometry.base import BaseGeometry

from config.at_cad_init import ATCadInit
from programs.at_input import at_get_entity  # используем ваши функции ввода
from windows.at_gui_utils import show_popup

# ---------------------------------------
# Вспомогательные типы
# ---------------------------------------
Transform = Tuple[float, float, float]  # (dx, dy, angle_deg)


# ---------------------------------------
# Сбор объектов внутри примитива (Acad COM)
# ---------------------------------------
def collect_objects_inside(entity, doc) -> List[Any]:
    """
    Собирает объекты (COM-объекты) из ModelSpace, полностью содержащиеся в геометрии 'entity'.
    Возвращает список объектов (не shapely).
    """
    ms = doc.ModelSpace
    inside = []
    try:
        # получаем геометрию entity через Coordinates/Center/Radius/InsertionPoint
        # Для определения принадлежности используем центры/геометрию объектов.
        # Это простая эвристика; при необходимости заменить точной проверкой (bounding box/shape).
        if hasattr(entity, "Coordinates"):
            pts = [(entity.Coordinates[i], entity.Coordinates[i + 1]) for i in range(0, len(entity.Coordinates), 2)]
            container_poly = Polygon(pts)
        elif hasattr(entity, "Center") and hasattr(entity, "Radius"):
            c = entity.Center
            container_poly = Point(c[0], c[1]).buffer(entity.Radius)
        else:
            return inside

        for obj in ms:
            try:
                if obj.ObjectID == entity.ObjectID:
                    continue
                # точка опоры/инсерции
                if hasattr(obj, "InsertionPoint"):
                    ip = obj.InsertionPoint
                    pt = Point(ip[0], ip[1])
                    if container_poly.contains(pt):
                        inside.append(obj)
                elif hasattr(obj, "Center") and hasattr(obj, "Radius"):
                    c = obj.Center
                    pt = Point(c[0], c[1])
                    if container_poly.contains(pt):
                        inside.append(obj)
                elif hasattr(obj, "Coordinates"):
                    pts2 = [(obj.Coordinates[i], obj.Coordinates[i + 1]) for i in range(0, len(obj.Coordinates), 2)]
                    shp = Polygon(pts2) if len(pts2) >= 3 else None
                    if shp and container_poly.contains(shp):
                        inside.append(obj)
                else:
                    # неизвестный тип — пропускаем
                    continue
            except Exception:
                continue
    except Exception:
        pass
    return inside


# ---------------------------------------
# Преобразование COM-entity в shapely Polygon
# ---------------------------------------
def entity_to_shapely(entity) -> Optional[BaseGeometry]:
    """
    Преобразует AutoCAD-entity (полилиния/окружность) в shapely-геометрию.
    """
    try:
        if hasattr(entity, "Coordinates"):
            pts = [(entity.Coordinates[i], entity.Coordinates[i + 1]) for i in range(0, len(entity.Coordinates), 2)]
            return Polygon(pts)
        elif hasattr(entity, "Center") and hasattr(entity, "Radius"):
            c = entity.Center
            return Point(c[0], c[1]).buffer(entity.Radius, resolution=64)
    except Exception:
        return None
    return None


# ---------------------------------------
# Утилита: проверка вхождения и пересечений
# ---------------------------------------
def fits_without_overlap(candidate_poly: BaseGeometry, placed_polys: List[BaseGeometry], container_inner: BaseGeometry) -> bool:
    """
    Проверяет, помещается ли candidate_poly внутри container_inner и не пересекается с placed_polys.
    """
    if not container_inner.contains(candidate_poly):
        return False
    for p in placed_polys:
        if candidate_poly.intersects(p):
            return False
    return True


# ---------------------------------------
# Спиральный поиск позиции (grid/spiral sampling)
# ---------------------------------------
def generate_candidate_positions(container_bounds: Tuple[float, float, float, float], center: Tuple[float, float],
                                 step: float, max_radius: float):
    """
    Генерирует позиции в виде спирали от центра — yield (x,y).
    """
    cx, cy = center
    # простой spiral grid
    angle = 0.0
    r = 0.0
    while r <= max_radius:
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        yield (x, y)
        angle += step / (r + 1e-6)
        if angle > 2 * math.pi:
            angle -= 2 * math.pi
            r += step


# ---------------------------------------
# Инициализация размещения (greedy)
# ---------------------------------------
def initial_greedy_placement(container_poly: BaseGeometry,
                              primitives: List[BaseGeometry],
                              margin_between: float,
                              margin_to_wall: float,
                              allow_rotation: bool,
                              rotation_steps: List[float]) -> List[Transform]:
    """
    Возвращает список трансформаций (dx, dy, angle) для каждой примитивной фигуры.
    Greedy: ставим по убыванию площади, спирально ищем позицию.
    """
    # рабочие фигуры: учтём margin: увеличим primitives на margin_between/2 для проверки столкновений
    placed_polys = []
    transforms: List[Transform] = []
    container_inner = container_poly.buffer(-margin_to_wall)
    if container_inner.is_empty:
        raise ValueError("Container becomes empty after applying margin_to_wall")

    # precompute center and bounds
    bounds = container_inner.bounds
    center = ((bounds[0] + bounds[2]) / 2.0, (bounds[1] + bounds[3]) / 2.0)
    max_radius = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) * 1.5
    step = max((bounds[2] - bounds[0]), (bounds[3] - bounds[1])) / 50.0

    # sort primitives by area descending
    indexed = sorted(enumerate(primitives), key=lambda it: -it[1].area)

    # For collision checks, we'll use buffered versions:
    buffered_prims = [p.buffer(margin_between / 2.0, join_style=2) for _, p in indexed]

    # iterate
    for idx, prim in indexed:
        bp = prim
        placed = False
        # try rotations
        for angle in rotation_steps if allow_rotation else [0.0]:
            # base rotated shape
            rot = shp_rotate(bp, angle, origin='centroid', use_radians=False)
            # sample candidate positions
            for (x, y) in generate_candidate_positions(bounds, center, step, max_radius):
                # translate so centroid goes to x,y
                cx, cy = rot.centroid.x, rot.centroid.y
                dx, dy = x - cx, y - cy
                cand = shp_translate(rot, xoff=dx, yoff=dy)
                # check
                if fits_without_overlap(cand, placed_polys, container_inner):
                    placed_polys.append(cand)
                    transforms.append((dx, dy, angle))
                    placed = True
                    break
            if placed:
                break
        if not placed:
            # не удалось разместить — возвращаем ошибку/пустую трансформацию
            transforms.append((0.0, 0.0, 0.0))
            placed_polys.append(shp_translate(shp_rotate(bp, 0.0, origin='centroid'), 0, 0))
            # Пометка: можно вернуть информацию о неудаче
    # transforms соответствуют порядку primitives
    # Но мы собрали по индексу order; нужно вернуть в исходном порядке
    # transforms list currently in index-sorted order, we need to map back
    result = [None] * len(primitives)
    for k, (orig_idx, _) in enumerate(indexed):
        result[orig_idx] = transforms[k]
    return result


# ---------------------------------------
# Целевая функция: площадь объединения (можно использовать convex hull area)
# ---------------------------------------
def compute_objective(placed_polys: List[BaseGeometry]) -> float:
    """
    Возвращает метрику компактности — площадь объединения (меньше — лучше).
    """
    try:
        union = unary_union(placed_polys)
        return union.area
    except Exception:
        # fallback: sum of areas
        return sum(p.area for p in placed_polys)


# ---------------------------------------
# Локальное улучшение через простое улучшение/annealing
# ---------------------------------------
def refine_placement(container_poly: BaseGeometry,
                     primitives: List[BaseGeometry],
                     initial_transforms: List[Transform],
                     margin_between: float,
                     margin_to_wall: float,
                     allow_rotation: bool,
                     rotation_steps: List[float],
                     max_iters: int = 1000,
                     time_limit: float = 5.0) -> List[Transform]:
    """
    Простая имлементация simulated annealing / local search.
    Перемещаем случайный примитив небольшим шагом и принимаем если лучше.
    """
    start = time.time()
    # build current placed polys
    container_inner = container_poly.buffer(-margin_to_wall)
    placed_polys = []
    for prim, (dx, dy, angle) in zip(primitives, initial_transforms):
        poly = shp_rotate(prim, angle, origin='centroid', use_radians=False)
        poly = shp_translate(poly, xoff=dx, yoff=dy)
        placed_polys.append(poly.buffer(margin_between / 2.0, join_style=2))

    best_transforms = initial_transforms[:]
    best_score = compute_objective(placed_polys)

    it = 0
    while it < max_iters and (time.time() - start) < time_limit:
        it += 1
        # choose random index
        i = random.randrange(len(primitives))
        # propose small random perturbation
        dx, dy, angle = best_transforms[i]
        # small move: up to 10% of primitive bbox
        bbox = primitives[i].bounds
        max_step = max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.2
        ndx = dx + random.uniform(-max_step, max_step) * 0.5
        ndy = dy + random.uniform(-max_step, max_step) * 0.5
        if allow_rotation:
            nang = angle + random.choice(rotation_steps)
        else:
            nang = angle

        # reconstruct candidate placed polys
        cand_polys = []
        ok = True
        for j, prim in enumerate(primitives):
            tj = best_transforms[j] if j != i else (ndx, ndy, nang)
            px = shp_rotate(prim, tj[2], origin='centroid', use_radians=False)
            px = shp_translate(px, xoff=tj[0], yoff=tj[1])
            # buffer for collision detection
            bpx = px.buffer(margin_between / 2.0, join_style=2)
            # containment
            if not container_inner.contains(bpx):
                ok = False
                break
            cand_polys.append(bpx)
        if not ok:
            continue
        # check pairwise intersections
        collision = False
        for a in range(len(cand_polys)):
            for b in range(a + 1, len(cand_polys)):
                if cand_polys[a].intersects(cand_polys[b]):
                    collision = True
                    break
            if collision:
                break
        if collision:
            continue

        # evaluate objective
        score = compute_objective(cand_polys)
        # accept if improved (simple hill-climb), or with small prob (annealing)
        if score < best_score or random.random() < 0.01:
            best_score = score
            best_transforms[i] = (ndx, ndy, nang)
            # update placed polys
            placed_polys = cand_polys

    return best_transforms


# ---------------------------------------
# Главная функция упаковки (API)
# ---------------------------------------
def pack_primitives_in_container(container_entity, primitive_entities,
                                 doc=None,
                                 margin_between: float = 10.0,
                                 margin_to_wall: float = 10.0,
                                 allow_rotation: bool = True,
                                 rotation_step_deg: float = 90.0,
                                 time_limit: float = 5.0) -> Dict[str, Any]:
    """
    Основная обёртка: принимает AutoCAD-entity (container) и список primitive entities,
    возвращает словарь с трансформами и результатом (успех/неуспех).
    Не перемещает объекты в AutoCAD — только вычисляет размещение.
    Для применения трансформаций использовать apply_transforms_to_entities().
    """
    # prepare doc
    if doc is None:
        cad = ATCadInit()
        doc = cad.document

    # convert to shapely
    container_poly = entity_to_shapely(container_entity)
    if container_poly is None:
        raise ValueError("container_entity to shapely failed")

    primitives = []
    for e in primitive_entities:
        shp = entity_to_shapely(e)
        if shp is None:
            raise ValueError(f"primitive to shapely failed for {e}")
        primitives.append(shp)

    # rotation candidates
    rotations = []
    if allow_rotation:
        steps = int(360 / rotation_step_deg)
        rotations = [i * rotation_step_deg for i in range(steps)]
    else:
        rotations = [0.0]

    # initial placement
    transforms = initial_greedy_placement(container_poly, primitives, margin_between, margin_to_wall, allow_rotation, rotations)

    # refine
    transforms = refine_placement(container_poly, primitives, transforms, margin_between, margin_to_wall, allow_rotation, rotations, max_iters=2000, time_limit=time_limit)

    # prepare results (map transforms to each entity)
    results = {}
    for ent, (dx, dy, ang) in zip(primitive_entities, transforms):
        results[getattr(ent, "ObjectID", str(ent))] = {
            "entity": ent,
            "dx": dx,
            "dy": dy,
            "angle": ang
        }
    return {
        "success": True,
        "container": container_entity,
        "transforms": results
    }


# ---------------------------------------
# Применение трансформаций к COM-объектам AutoCAD
# ---------------------------------------
def apply_transforms_to_entities(results: Dict[str, Any], doc) -> None:
    """
    Принимает results["transforms"] (описание выше) и применяет Move/Rotate к объектам в AutoCAD.
    ВАЖНО: переносит сам primitive *и* вложенные в него объекты (их надо собрать заранее).
    """
    for oid, info in results.items():
        ent = info["entity"]
        dx = info["dx"]
        dy = info["dy"]
        ang = info["angle"]  # градусы

        try:
            # Рассчитываем опорную точку — centroid original
            if hasattr(ent, "Coordinates"):
                pts = [(ent.Coordinates[i], ent.Coordinates[i + 1]) for i in range(0, len(ent.Coordinates), 2)]
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                base = win32_point(cx, cy)
            elif hasattr(ent, "Center"):
                c = ent.Center
                base = win32_point(c[0], c[1])
            else:
                base = win32_point(0, 0)

            # Move: используем AutoCAD Move (две точки): base -> base+(dx,dy)
            # Подготовим базовую точку и конечную точку (массив/tuple)
            src = base
            dst = win32_point(base[0] + dx, base[1] + dy)

            # Move entity and its contents: если вы заранее собрали список objects_inside,
            # переместите их все вместе. Здесь простая версия: перемещаем сам ent.
            try:
                ent.Move(src, dst)
            except Exception:
                # fallback: SendCommand (если Move недоступен) — нежелательно, но на всякий случай
                try:
                    doc.SendCommand(f'-MOVE {ent.ObjectID} {src[0]},{src[1]} {dst[0]},{dst[1]} ')
                except Exception:
                    pass

            # Rotate: вокруг точки src на угол ang (в радианах)
            if abs(ang) > 1e-6:
                rad = math.radians(ang)
                try:
                    ent.Rotate(dst, rad)
                except Exception:
                    try:
                        doc.SendCommand(f'-ROTATE {ent.ObjectID} {dst[0]},{dst[1]} {ang} ')
                    except Exception:
                        pass

        except Exception as e:
            # логируй, но не кидай
            print("Ошибка применения трансформации:", e)


# ---------------------------------------
# Малые помощники
# ---------------------------------------
def win32_point(x, y, z=0.0):
    # возвращаем простой кортеж — при вызове Move/Rotate AutoCAD API ожидает SAFEARRAY или подходящий COM-тип;
    # в нашем коде выше мы пробуем использовать ent.Move(src, dst) — возможно, этот метод требует VARIANT,
    # а в вашей среде уже есть helper — в противном случае обёртку нужно добавить (см. at_com_utils.safe_get_*).
    return (float(x), float(y), float(z))


# ==============================================================
# Пример использования:
# ==============================================================

def example_run():
    cad = ATCadInit()
    doc = cad.document

    # Шаг 1: выбор контейнера (SF-TEXT)
    c_entity, _, ok, enter, esc = at_get_entity(use_bridge=False, prompt="Выберите контейнер (SF-TEXT):")
    if not ok or c_entity is None:
        show_popup("Контейнер не выбран", popup_type="error")
        return

    # Шаг 2: выбор примитивов (слой 0) — повторный выбор (или мультивыбор если есть)
    primitives = []
    while True:
        ent, _, ok, enter, esc = at_get_entity(use_bridge=False, prompt="Выберите примитив (слой 0). Enter — закончить:")
        if esc:
            show_popup("Отмена", popup_type="info")
            return
        if enter:
            break
        if not ok or ent is None:
            continue
        primitives.append(ent)

    # Шаг 3: запуск упаковки (не перемещает объекты)
    res = pack_primitives_in_container(c_entity, primitives, doc=doc, margin_between=10.0, margin_to_wall=10.0, allow_rotation=True, rotation_step_deg=90.0, time_limit=6.0)
    # res['transforms'] — mapping ObjectID -> {entity, dx, dy, angle}

    # Шаг 4: показать результат и подтвердить применение
    # Для простоты — сразу применяем
    apply_transforms_to_entities(res["transforms"], doc)
    show_popup("Упаковка выполнена (попробовано применить трансформации).", popup_type="info")



if __name__ == "__main__":
    example_run()