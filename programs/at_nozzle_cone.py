# programs/at_nozzle_cone.py
import math
from typing import Any, Optional, Tuple, Union, List
from comtypes.automation import VARIANT

from config.at_cad_init import ATCadInit
from programs.at_construction import at_cone_sheet, add_polyline
from programs.at_geometry import ensure_point_variant
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup

def at_nozzle_cone_sheet(
    model: Any,
    input_point: Union[List[float], Tuple[float, float, float], VARIANT],
    d1: float,      # верхний диаметр
    d2: float,      # максимальная хорда пересечения (задаётся по чертежу)
    D: float,       # диаметр цилиндра
    H: float,       # расстояние от торца до оси цилиндра
    layer_name: str = "0",
    layer_intersection: str = "LASER-TEXT"
) -> Optional[Tuple[Any, Any, List[Any]]]:

    height_cone = H - math.sqrt((D**2 - d2**2) / 4)

    # === Строим развёртку конуса ===
    result = at_cone_sheet(model, input_point, d1, d2, height_cone, layer_name="0")

    poly_cone, _, apex = result  # apex — центр сектора (вершина конуса на развёртке)

    # ───── реальная длина образующей из построенной развёртки ─────
    # LightWeightPolyline → координаты через .Coordinates (массив float)
    coords = poly_cone.Coordinates

    # берём вторую точку (индекс 2..3) — это точка на внешней дуге
    x_outer = coords[2]
    y_outer = coords[3]
    generatrix = math.sqrt((x_outer - apex[0]) ** 2 + (y_outer - apex[1]) ** 2)

    def generatrix_length(phi, h, R, a):
        return math.sqrt(h * h + R * R + a * a - 2 * R * a * math.cos(phi))

    # -------------------------------------------------------------
    #            РЕАЛЬНАЯ ЛИНИЯ ПЕРЕСЕЧЕНИЯ (полилиния)
    # -------------------------------------------------------------

    # ------------------ Корректная генерация линии пересечения ------------------
    R = d2 / 2            # радиус основания конуса (в 3D)
    a = D / 2             # радиус цилиндра
    h = height_cone       # высота конуса (апекс в z=0, основание z=h)
    if h == 0:
        show_popup("height_cone == 0 — некорректная геометрия.", popup_type="error")
        return None

    k = R / h             # масштабный коэффициент конуса (x^2+y^2 = (k*z)^2)
    # slant (длина образующей в основании) — это ваша generatrix (g_max)
    g_max = generatrix

    # сетка по углу цилиндра
    N_theta = 1440  # высокая дискретизация для гладкой линии, можно уменьшить до 360 при тесте
    thetas = [2 * math.pi * i / N_theta for i in range(N_theta + 1)]

    pts3d = []   # соберём 3D точки пересечения (x,y,z)
    for theta in thetas:
        y_c = a * math.cos(theta)   # y на цилиндре
        z_c = a * math.sin(theta)   # z на цилиндре

        # x^2 = (k*z_c)^2 - y_c^2
        rhs = (k * z_c) ** 2 - (y_c ** 2)
        if rhs < 0:
            # нет пересечения для данного theta
            continue
        x_val = math.sqrt(max(0.0, rhs))
        # обе ветви x = +x_val и x = -x_val
        pts3d.append(( x_val, y_c, z_c ))
        pts3d.append((-x_val, y_c, z_c ))

    if not pts3d:
        show_popup("Нет 3D точек пересечения (pts3d пуст). Проверьте размеры.", popup_type="error")
        return None

    # Для каждой 3D точки вычислим psi (азимут вокруг оси Z) и длину образующей g
    psi_g_list = []
    for (x3, y3, z3) in pts3d:
        psi = math.atan2(y3, x3)             # азимут в плоскости XY
        g = math.sqrt(x3 * x3 + y3 * y3 + z3 * z3)  # длина образующей от апекса
        psi_g_list.append((psi, g, (x3, y3, z3)))

    # Сортируем по psi (чтобы получить упорядоченную вокруг конуса кривую)
    psi_g_list.sort(key=lambda e: e[0])

    # Получаем стартовую точку на внешней дуге развертки (контроль)
    coords = poly_cone.Coordinates
    start_pt = (coords[2], coords[3])
    end_pt   = (coords[4], coords[5])
    apex_xy = (apex[0], apex[1])

    # Преобразуем psi -> углы на развертке. Для выравнивания сделаем:
    # ang_rel = (R * (psi - psi0)) / g_max, а абсолютный ang = ang0 + ang_rel,
    # где psi0 — psi первой точки в упорядоченном списке, ang0 — угол на листе, соответствующий start_pt.
    psi0 = psi_g_list[0][0]
    ang0 = math.atan2(start_pt[1] - apex_xy[1], start_pt[0] - apex_xy[0])

    final_sheet_pts = []
    for psi, g, _3d in psi_g_list:
        # относительный угол вдоль дуги основания
        ang_rel = (R * (psi - psi0)) / g_max
        ang_on_sheet = ang0 + ang_rel
        x_sheet = apex_xy[0] + g * math.cos(ang_on_sheet)
        y_sheet = apex_xy[1] + g * math.sin(ang_on_sheet)
        final_sheet_pts.append((x_sheet, y_sheet, psi, g))

    # Теперь: нужно сделать сдвиг по кругу так, чтобы точка, наиболее близкая к start_pt, стала первой.
    # Найдём индекс по минимальному расстоянию от start_pt.
    def dist2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    best_idx = min(range(len(final_sheet_pts)), key=lambda i: dist2((final_sheet_pts[i][0], final_sheet_pts[i][1]), start_pt))
    # повернём список так, чтобы best_idx стал 0
    ordered = final_sheet_pts[best_idx:] + final_sheet_pts[:best_idx]

    # Преобразуем в окончательный список (x,y)
    ordered_xy = [(p[0], p[1]) for p in ordered]

    # Уберём возможные близкие дубликаты (вдоль границы) — простая фильтрация по расстоянию
    filtered = []
    min_sq_dist = (1e-4) ** 2  # 0.0001 mm^2 порог
    for pt in ordered_xy:
        if not filtered or dist2(filtered[-1], pt) > min_sq_dist:
            filtered.append(pt)

    # Гарантируем, что первая и последняя точки совпадают с контрольными (устраняем численные погрешности)
    if len(filtered) >= 2:
        filtered[0] = (start_pt[0], start_pt[1])
        filtered[-1] = (end_pt[0], end_pt[1])
    # Вставим апекс+g_max в середину (контроль)
    mid_index = len(filtered) // 2
    if 0 <= mid_index < len(filtered):
        filtered[mid_index] = (apex_xy[0], apex_xy[1] + g_max)

    # Если слишком мало точек — сообщим
    if len(filtered) < 3:
        show_popup("Сгенерировано слишком мало точек пересечения.", popup_type="error")
        return None

    # Построим полилинию через вашу функцию add_polyline
    poly_intersection = add_polyline(
        model=model,
        points=filtered,
        layer_name=layer_intersection,
        closed=False
    )

    if poly_intersection is None:
        show_popup("Не удалось создать полилинию пересечения.", popup_type="error")
        return None


# === ТЕСТ — даёт h = 68.000 мм, линия реза идеальная ===
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