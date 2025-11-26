# programs/at_nozzle_cone.py
import math
from pprint import pprint
from typing import Any, Optional, Tuple, Union, List
from comtypes.automation import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_construction import at_cone_sheet, add_polyline
from programs.at_geometry import ensure_point_variant, find_intersection_points
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup


# ─────────────────────────────────────────────────────────────
#      ПОМОГАЮЩИЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────────

def dist2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def point_on_arc(apex: Tuple[float, float], radius: float, angle: float) -> Tuple[float, float]:
    """Возвращает координату точки на дуге развёртки (плоско)."""
    return (
        apex[0] + radius * math.cos(angle),
        apex[1] + radius * math.sin(angle)
    )


def choose_candidate_right_of_prev(candidates: List[Tuple[float, float]],
                                   prev_pt: Tuple[float, float]) -> Tuple[float, float]:
    """
    Выбор кандидата: сперва предпочитаем точку правее предыдущей по X.
    Если обе правее — выбираем ту, что ближе по X к prev (меньшее приращение),
    иначе выбираем максимальную по X (чтобы идти слева->справа).
    В случае равенства X — выбираем ближе по евклидовой.
    """
    if not candidates:
        raise ValueError("No candidates to choose from")

    prev_x = prev_pt[0]

    # Разделим кандидатов на правые и непр. правые
    right = [c for c in candidates if c[0] > prev_x]
    if right:
        # среди правых выбрать тот, у которого |dx| минимально (не резкое скачкообразное перемещение)
        best = min(right, key=lambda c: abs(c[0] - prev_x))
        return best

    # если нет правых — берем с наибольшим X (двигаемся максимально вправо)
    best = max(candidates, key=lambda c: (c[0], -dist2d(c, prev_pt)))
    return best


# ─────────────────────────────────────────────────────────────
#      ОСНОВНАЯ ФУНКЦИЯ
# ─────────────────────────────────────────────────────────────

def at_nozzle_cone_sheet(
    model: Any,
    input_point: Union[List[float], Tuple[float, float, float], VARIANT],
    d1: float,      # верхний диаметр
    d2: float,      # диаметр нижнего основания (на сечении)
    D: float,       # диаметр цилиндра
    H: float,       # расстояние от торца до оси цилиндра
    layer_name: str = "0",
    layer_intersection: str = "LASER-TEXT"
) -> Optional[Tuple[Any, Any, List[Any]]]:

    # высота усечённого конуса (высота от апекса до уровня пересечения)
    height_cone = H - math.sqrt((D * D - d2 * d2) / 4.0)

    # строим развёртку конуса (используем вашу функцию)
    # at_cone_sheet возвращает (poly_cone, ..., apex)
    poly_cone, _, apex = at_cone_sheet(
        model, input_point, d1, d2, height_cone, layer_name=layer_name
    )

    coords = poly_cone.Coordinates
    pprint(coords)

    # Точки внешней дуги развёртки конуса (контрольные)
    start_pt = (coords[2], coords[3])
    end_pt = (coords[4], coords[5])

    # Максимальная образующая (радиус дуги развёртки от апекса до внешнего контура)
    g_max = dist2d(apex, start_pt)

    # Длина дуги развёртки (расстояние по плоскости между start и end на развёртке)
    L_unfold = dist2d(start_pt, end_pt)

    # Полный угол дуги на развертке (phi_max)
    # угол (в радианах) на развёртке = длина дуги / радиус
    if g_max == 0:
        show_popup("Ошибка: апекс совпадает с внешней точкой развёртки.", popup_type="error")
        return None

    phi_max = L_unfold / g_max

    # Начальный угол на развертке (вокруг апекса) — чтобы класть точки вдоль дуги
    phi0 = math.atan2(start_pt[1] - apex[1], start_pt[0] - apex[0])
    # phi1 = phi0 + phi_max  # если понадобится

    # Геометрические параметры 3D
    R = d2 / 2.0
    a = D / 2.0
    h = height_cone

    # Точная длина образующей в 3D для угла phi (на цилиндре)
    def generatrix_length(phi: float, h_val: float, R_val: float, a_val: float) -> float:
        return math.sqrt(h_val * h_val + R_val * R_val + a_val * a_val - 2.0 * R_val * a_val * math.cos(phi))

    # Параметры дискретизации
    N = 80  # можно уменьшить/увеличить; должно делиться на 4 по твоему требованию
    if N % 4 != 0:
        show_popup("N должно делиться на 4", popup_type="error")
        return None

    # Шаг угла по развёртке (плоский шаг)
    dphi = phi_max / float(N)

    # Подготовим список phi в 3D (соответствуют равномерным сегментам основания окружности)
    # В 3D phi_cyl = 0..2pi. Берём N точек равномерно по окружности цилиндра.
    phis_3d = [2.0 * math.pi * i / float(N) for i in range(N)]

    # Длины всех образующих (для phi_i)
    generatrices = [generatrix_length(phi, h, R, a) for phi in phis_3d]

    # ─────────────────────────────────────────────────────────────
    #     ОСНОВНОЙ АЛГОРИТМ: лучи от апекса к точкам дуги развёртки
    #     и поиск реальной точки пересечения по длине образующей
    # ─────────────────────────────────────────────────────────────

    result_pts: List[Tuple[float, float]] = []
    prev_pt = start_pt
    result_pts.append(prev_pt)

    # задаём очень маленький радиус для вызова find_intersection_points (мы будем искать пересечение
    # окружности радиуса г_i вокруг апекса с "окружностью" малого радиуса вокруг target_pt).
    # однако в этой реализации мы используем пересечение окружности (apex, g_i) с центром=target_pt радиус=eps,
    # а затем из кандидатов выбираем ту, что правее prev_pt (см. логику выше).
    # Это имитирует проекцию точки на луч, расположенную в направлении target_pt.
    eps_base = max(0.001, g_max * 1e-6)

    for i in range(1, N):
        # угол на развертке в плоскости (от апекса), равномерно по дуге start->end
        phi_flat = phi0 + i * dphi

        # точка на дуге (плоско) — ожидаемая позиция (центр второго "маленького" круга)
        target_pt = point_on_arc(apex, g_max, phi_flat)

        # Радиус первой окружности — длина соответствующей образующей (берём i мод N для доступа)
        # Соответствие i->phis_3d: хотим, чтобы i==0 соответствовало phi=0 в 3D, т.е. сдвигать индекс
        idx_3d = i % N
        g_i = generatrices[idx_3d]

        # Попытаемся найти пересечение окружности (apex, g_i) и "маленькой" окружности (target_pt, eps)
        eps = eps_base
        inter = find_intersection_points((apex[0], apex[1]), g_i, (target_pt[0], target_pt[1]), eps)
        # небольшая попытка по гибкости радиуса
        if not inter:
            inter = find_intersection_points((apex[0], apex[1]), g_i, (target_pt[0], target_pt[1]), eps * 5.0)
        if not inter:
            inter = find_intersection_points((apex[0], apex[1]), g_i, (target_pt[0], target_pt[1]), eps * 0.2)

        if inter:
            candidates = inter if isinstance(inter, list) else [inter]
            # выбираем ту кандидат-точку, которая правее предыдущей (по X)
            chosen = choose_candidate_right_of_prev(candidates, prev_pt)
        else:
            # fallback: если пересечение не найдено (численные/геометрич. причины),
            # откладываем образующую g_i от апекса в направлении target_pt (по углу)
            ang = math.atan2(target_pt[1] - apex[1], target_pt[0] - apex[0])
            chosen = (apex[0] + g_i * math.cos(ang), apex[1] + g_i * math.sin(ang))
            pprint({
                "warning": "no intersection - fallback used",
                "i": i,
                "g_i": g_i,
                "target_pt": target_pt,
                "fallback_chosen": chosen
            })

        # Добавляем в результирующий список
        result_pts.append(chosen)
        prev_pt = chosen

    # Устранение числового шума: последняя точка — точно end_pt
    if result_pts:
        result_pts[-1] = (end_pt[0], end_pt[1])

    # Опционально: вставляем контрольную точку апекса + g_max в середину (как маркер)
    mid_index = len(result_pts) // 2
    if 0 <= mid_index < len(result_pts):
        # не заменяем крайние контрольные точки
        if mid_index != 0 and mid_index != len(result_pts) - 1:
            result_pts[mid_index] = (apex[0], apex[1] + g_max)

    pprint(result_pts)

    # строим полилинию через твою функцию add_polyline
    poly_intersection = add_polyline(
        model=model,
        points=result_pts,
        layer_name=layer_intersection,
        closed=False
    )

    # возвращаем развертку, апекс и список точек (можно использовать для сравнения/экспорта)
    return poly_cone, apex, result_pts


# === ТЕСТ ===
if __name__ == '__main__':
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space
    pt = at_get_point(adoc, prompt="Точка вставки:", as_variant=False)

    at_nozzle_cone_sheet(
        model=model,
        input_point=pt,
        d1=102,
        d2=138,
        D=273,
        H=185.78
    )
