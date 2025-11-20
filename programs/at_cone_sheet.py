# -*- coding: utf-8 -*-
"""
programs/at_cone_sheet.py

Построение развертки усечённого конуса и построение линии пересечения реального 3D-конуса
(ось конуса направлена вдоль +X, апекс в начале координат) с цилиндром (ось цилиндра вдоль Z),
который располагается с центром на оси конуса (без смещения по Y/Z), то есть патрубок
подключается перпендикулярно магистрали.

Ключевые моменты:
- Конус: апекс в локальной системе (0,0,0), ось вдоль +X, радиус в сечении x равен x * tan(alpha).
- Цилиндр: радиус R = D_cylinder/2, ось вдоль Z, центры пересечений параметризуются углом theta.
- Формула пересечения (аналитическая): для точки цилиндра (x=R*cosθ, y=R*sinθ, z=t)
  подстановка в уравнение конуса даёт t^2 = R^2 (cos^2θ * tan^2α - sin^2θ). Если правое
  выражение >= 0 — есть два значения t = ±R*sqrt(...).
- Только те точки пересечения где x = R*cosθ попадают в осевой диапазон усечённого конуса
  (между x1 и x2) включаются в кривую выреза.
- Для развёртки конуса используется стандартная карта (s, ψ) → (ρ, φ):
    s = x / cosα,  ψ = atan2(z, y)
    φ_dev = ψ * sinα
    X_dev = s * cos φ_dev, Y_dev = s * sin φ_dev

Все вспомогательные функции документированы. Встроенные вызовы AutoCAD выполняются
через ваши утилиты add_polyline/add_spline/add_line и ожидают, что insert_point передаётся
как Python-список [x, y, z] (вы используете at_get_point(..., as_variant=False)).
"""

import math
from typing import List, Tuple, Optional

from config.at_cad_init import ATCadInit
from programs.at_geometry import circle_center_from_points
from programs.at_construction import add_polyline, add_spline, add_line
from programs.at_input import at_get_point

# небольшой тип для точки 2D
Pt2 = Tuple[float, float]
Pt3 = Tuple[float, float, float]


# --------------------------------------------------------------------------
# GEOMETRY HELPERS
# --------------------------------------------------------------------------

def cone_geometry_from_dimensions(d1: float, d2: float, H: float) -> Tuple[float, float, float, float]:
    """
    Вычисляет геометрические параметры конуса по входным размерам.

    :param d1: float - диаметр верхнего (малого) основания конуса (мм).
    :param d2: float - диаметр нижнего (большого) основания конуса (мм).
    :param H: float - осевая высота между d1 и d2 (мм).
    :returns: tuple (alpha, x1, x2, s_frag)
        - alpha: полуугол конуса (радианы)
        - x1: координата по оси X малого основания (от апекса)
        - x2: координата по оси X большого основания (от апекса)
        - s_frag: длина образующей между кругами (фрагмент образующей)
    :raises ValueError: при некорректных входных данных
    """
    if H <= 0:
        raise ValueError("Height H must be positive")
    r1 = d1 / 2.0
    r2 = d2 / 2.0
    if r1 < 0 or r2 < 0:
        raise ValueError("Diameters must be non-negative")

    # тангенс угла: tan(alpha) = (r2 - r1) / H
    # alpha = atan((r2 - r1) / H)
    delta_r = r2 - r1
    alpha = math.atan2(delta_r, H)  # в радианах; учёт знака delta_r
    if abs(math.cos(alpha)) < 1e-12:
        raise ValueError("Invalid cone angle (cos alpha ≈ 0)")

    # координаты малой и большой круговых сечений по оси X (апекс в 0)
    # r = x * tan(alpha) -> x = r / tan(alpha)
    if abs(math.tan(alpha)) < 1e-12:
        # почти цилиндр — представим x1,x2 как:
        x1 = 0.0
        x2 = H
        s_frag = H  # образующая ~ высота
    else:
        x1 = r1 / math.tan(alpha)
        x2 = r2 / math.tan(alpha)
        s_frag = math.hypot(H, delta_r)  # длина образующей между кругами

    return alpha, x1, x2, s_frag


def compute_development_radii(r1: float, r2: float, s_frag: float) -> Tuple[float, float]:
    """
    Вычисляет расстояния от апекса до малого и большого круга на развертке (s1 и s2).

    Формула:
        s1 = r1 * s_frag / (r2 - r1)
        s2 = s1 + s_frag

    :param r1: радиус малого круга (мм)
    :param r2: радиус большого круга (мм)
    :param s_frag: длина образующей между кругами (мм)
    :returns: (s1, s2)
    """
    if abs(r2 - r1) < 1e-12:
        # почти цилиндр
        s1 = 0.0
        s2 = s_frag
    else:
        s1 = r1 * s_frag / (r2 - r1)
        s2 = s1 + s_frag
    return s1, s2


# --------------------------------------------------------------------------
# INTERSECTION: cone (axis X) with cylinder (axis Z)
# --------------------------------------------------------------------------

def compute_cone_cylinder_intersection_points_3d(
    D: float,
    d1: float,
    d2: float,
    H: float,
    n_theta: int = 360
) -> List[Pt3]:
    """
    Вычисляет точки пересечения 3D-конуса (апекс в 0, ось вдоль X, малый диаметр d1 у x=x1,
    большой диаметр d2 у x=x2) с цилиндром радиуса R = D/2 и осью вдоль Z,
    расположенным так, что ось цилиндра пересекает ось конуса в апексе (0,0,0).

    Формулы:
        Конус: sqrt(y^2 + z^2) = x * tan(alpha)
        Цилиндр: x = R*cos(theta), y = R*sin(theta), z = t

        Подстановка даёт:
            t^2 = R^2 * (cos^2(theta) * tan^2(alpha) - sin^2(theta))

    :param D: Диаметр цилиндра (мм)
    :param d1: Диаметр малого основания конуса (мм)
    :param d2: Диаметр большого основания конуса (мм)
    :param H: Высота между d1 и d2 (мм)
    :param n_theta: число шагов по углу (рекомендуется >= 72)
    :return: список 3D-точек (x,y,z). Может возвращать пустой список, если пересечения нет.
    """
    R = D / 2.0
    r1 = d1 / 2.0
    r2 = d2 / 2.0

    alpha, x1, x2, s_frag = cone_geometry_from_dimensions(d1, d2, H)
    tan_a = math.tan(alpha)

    pts3d: List[Pt3] = []

    # проходим по углам цилиндра θ ∈ [0, 2π)
    n = max(12, int(n_theta))
    for i in range(n):
        theta = 2.0 * math.pi * i / (n - 1)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        # x координата точки на цилиндре
        x_c = R * cos_t
        # условие принадлежности по оси X (в пределах усечённого конуса)
        # допускаем небольшой eps
        eps = 1e-9
        if x_c + eps < x1 or x_c - eps > x2:
            # точка цилиндра по x вне усечённого конуса
            continue

        # подкоренное выражение
        D_theta = (cos_t * cos_t) * (tan_a * tan_a) - (sin_t * sin_t)
        if D_theta < 0:
            # нет действительных z
            continue

        z_mag = R * math.sqrt(D_theta)
        # две ветви по z
        y_c = R * sin_t
        # точки:
        pts3d.append((x_c, y_c, z_mag))
        if abs(z_mag) > 1e-12:
            pts3d.append((x_c, y_c, -z_mag))

    return pts3d


def map_3d_point_to_development(
    pt3: Pt3,
    alpha: float
) -> Pt2:
    """
    Отображает 3D-точку (x,y,z) на развертку конуса (по средней линии).
    Предполагается, что апекс конуса в (0,0,0), ось вдоль +X.

    :param pt3: (x, y, z)
    :param alpha: полуугол конуса (радианы)
    :return: (X_dev, Y_dev) координаты в плоскости развёртки
    """
    x, y, z = pt3
    # slant length s от апекса до этой точки по образующей:
    # x = s * cos(alpha)  => s = x / cos(alpha)
    cos_a = math.cos(alpha)
    sin_a = math.sin(alpha)
    if abs(cos_a) < 1e-12:
        raise ValueError("cos(alpha) too small")

    s = x / cos_a

    # угловая координата вокруг оси конуса (в плоскости поперечного сечения y-z):
    # psi = atan2(z, y)
    psi = math.atan2(z, y)

    # угол на развертке (phi_dev) связан с psi коэффициентом sin(alpha):
    # дуговая длина на конусе при угле psi: s * sin(alpha) * psi
    # в развертке при радиусе s этот длинный дуге соответствует углу phi_dev = (arc_length)/s = psi*sin(alpha)
    phi_dev = psi * sin_a

    Xdev = s * math.cos(phi_dev)
    Ydev = s * math.sin(phi_dev)
    return Xdev, Ydev

def _compute_bulges(pts: List[Tuple[float, float]], mode: str) -> List[float]:
    """
    Вычисляет булжи для сегментов полилинии.
    Используется только когда mode == "bulge".
    Если mode == "polyline" — возвращаются нули.

    :param pts: список 2D точек [(x,y), ...]
    :param mode: "polyline" или "bulge"
    :return: список значений bulge длиной len(pts)-1
    """
    if mode != "bulge":
        return [0.0] * (len(pts) - 1)

    bulges = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]

        # вычисляем угол сегмента
        dx = x2 - x1
        dy = y2 - y1
        ang = math.atan2(dy, dx)

        # bulge = tan(Δφ / 4)
        # но в отсутствии информации о реальном дуговом сегменте
        # мы просто ставим очень маленький bulge — это даёт «почти прямую»,
        # но AutoCAD считает сегмент дугой, что нужно иногда для стыковки.
        bulge = 0.0  # можно поставить, например: math.tan(ang / 4)

        bulges.append(bulge)

    return bulges


# --------------------------------------------------------------------------
# MAIN: build development + draw intersection curve
# --------------------------------------------------------------------------

def at_cone_sheet(
    model,
    input_point: List[float],
    diameter_base: float,
    diameter_top: float,
    height: float,
    D_cylinder: Optional[float] = None,
    layer_name: str = "0",
    accuracy: int = 180,
    mode: str = "polyline"
) -> Optional[bool]:
    """
    Построение развертки усечённого конуса и (опционально) кривой пересечения с цилиндром.

    :param model: AutoCAD ModelSpace COM object (win32com)
    :param input_point: [x, y, z] - точка вставки (python list; as_variant=False у at_get_point)
    :param diameter_base: float - диаметр нижнего (большого) круга d2
    :param diameter_top: float - диаметр верхнего (малого) круга d1
    :param height: float - осевая высота между d1 и d2
    :param D_cylinder: Optional[float] - диаметр цилиндра (магистрали). Если None — кривая не строится
    :param layer_name: str - имя слоя (существующего) для записи полилиний
    :param accuracy: int - число шагов/точек на дугу (рекомендуется >= 72)
    :param mode: str - "polyline", "bulge" или "spline" — режим построения контура
    :return: True при успехе, None при ошибке
    """
    try:
        # input_point гарантированно список [x,y,z]
        ix = float(input_point[0])
        iy = float(input_point[1])

        d1 = float(diameter_top)
        d2 = float(diameter_base)
        H = float(height)

        if d1 <= 0 or d2 <= 0 or H <= 0:
            print("Invalid dimensions provided")
            return None

        # базовые параметры конуса
        alpha, x1, x2, s_frag = cone_geometry_from_dimensions(d1, d2, H)
        r1 = d1 / 2.0
        r2 = d2 / 2.0

        # расстояния на развертке
        s1, s2 = compute_development_radii(r1, r2, s_frag)

        # центральный угол сектора развертки
        if abs(s2) < 1e-12:
            theta = 2.0 * math.pi
        else:
            theta = 2.0 * math.pi * r2 / s2

        # дискретизация дуг
        n = max(8, int(accuracy))

        # точки нижней и верхней дуг в плоскости развёртки (до смещения insert)
        # нижняя дуга радиус s2, угол 0..theta
        bottom_dev_pts: List[Pt2] = [
            (s2 * math.cos(theta * i/(n-1)), s2 * math.sin(theta * i/(n-1)))
            for i in range(n)
        ]
        # верхняя дуга радиус s1, угол theta..0 (обратный обход)
        top_dev_pts: List[Pt2] = [
            (s1 * math.cos(theta - theta * i/(n-1)), s1 * math.sin(theta - theta * i/(n-1)))
            for i in range(n)
        ]

        # Преобразуем dev_pts в координаты с учётом точки вставки (смещение по ix,iy)
        bottom_pts = [(ix + x, iy + y, 0.0) for (x, y) in bottom_dev_pts]
        top_pts = [(ix + x, iy + y, 0.0) for (x, y) in top_dev_pts]

        mode = (mode or "polyline").lower()
        if mode not in ("polyline", "bulge", "spline"):
            mode = "polyline"

        # --- Режим spline: рисуем дуги сплайнами и соединительные линии ---
        if mode == "spline":
            add_spline(model, [[p[0], p[1]] for p in bottom_pts], layer_name, closed=False)
            add_spline(model, [[p[0], p[1]] for p in top_pts], layer_name, closed=False)
            # правая и левая образующие — прямые
            add_line(model, bottom_pts[-1], top_pts[0], layer_name)
            add_line(model, top_pts[-1], bottom_pts[0], layer_name)
        else:
            # --- POLYLINE / BULGE режим ---
            bottom_b = _compute_bulges([(p[0], p[1]) for p in bottom_pts], mode)
            top_b = _compute_bulges([(p[0], p[1]) for p in top_pts], mode)

            contour: List[Tuple[float, float, float]] = []
            # нижняя дуга (все точки кроме последней)
            for i, p in enumerate(bottom_pts[:-1]):
                contour.append((p[0], p[1], bottom_b[i]))
            # правая образующая (последняя нижней -> первая верхней)
            contour.append((bottom_pts[-1][0], bottom_pts[-1][1], 0.0))
            contour.append((top_pts[0][0], top_pts[0][1], 0.0))
            # верхняя дуга
            for i, p in enumerate(top_pts[:-1]):
                contour.append((p[0], p[1], top_b[i]))
            # левая образующая (последняя верхней -> первая нижней)
            contour.append((top_pts[-1][0], top_pts[-1][1], 0.0))
            contour.append((bottom_pts[0][0], bottom_pts[0][1], 0.0))

            # удалить подряд дубли (если есть)
            cleaned = []
            eps = 1e-8
            for p in contour:
                if not cleaned or abs(cleaned[-1][0] - p[0]) > eps or abs(cleaned[-1][1] - p[1]) > eps:
                    cleaned.append(p)

            if len(cleaned) < 3:
                print("Contour too small")
                return None

            add_polyline(model, cleaned, layer_name=layer_name, closed=True)

        print("Развертка конуса построена.")

        # -------------------------
        # Построение кривой пересечения
        # -------------------------
        if D_cylinder is not None:
            # 1) вычисляем 3D точки пересечения
            pts3d = compute_cone_cylinder_intersection_points_3d(D_cylinder, d1, d2, H, n_theta=accuracy)
            if not pts3d:
                print("Нет пересечений конуса и цилиндра (по заданным параметрам).")
                return True  # развертка есть, просто нет выреза

            # 2) получаем alpha заранее (используется в отображении)
            alpha_local, _, _, _ = cone_geometry_from_dimensions(d1, d2, H)

            # 3) отображаем все 3D точки в развертку (2D)
            dev_pts_2d: List[Pt2] = []
            for p3 in pts3d:
                try:
                    xdev, ydev = map_3d_point_to_development(p3, alpha_local)
                except Exception as ex:
                    # возможные редкие проблемные точки (деление на 0) — пропускаем
                    print(f"map_3d_point_to_development skipped point {p3}: {ex}")
                    continue
                dev_pts_2d.append((ix + xdev, iy + ydev))  # смещение в точку вставки

            # если получилось мало точек — ничего не строим
            if len(dev_pts_2d) < 2:
                print("Недостаточно точек пересечения для построения кривой.")
                return True

            # упорядочим точки по углу в развёртке, чтобы полилиния была непрерывной
            # вычислим полярный угол точки относительно insert (ix,iy) в развёртке
            angles_and_pts = []
            for (x, y) in dev_pts_2d:
                ang = math.atan2(y - iy, x - ix)
                angles_and_pts.append((ang, (x, y)))
            angles_and_pts.sort(key=lambda a: a[0])

            ordered_pts = [ (p[0], p[1], 0.0) for (_, p) in angles_and_pts ]

            # добавляем полилинию (ломаная) для кривой пересечения
            add_polyline(model, ordered_pts, layer_name=layer_name, closed=False)
            print("Кривая пересечения (в развёртке) добавлена как полилиния.")

        return True

    except Exception as e:
        print("Ошибка построения:", e)
        return None


# --------------------------------------------------------------------------
# TEST RUN
# --------------------------------------------------------------------------

if __name__ == '__main__':
    """
    Тестовый вызов:
    - Запустите AutoCAD, откройте чертёж с нужными слоями.
    - Запустите этот модуль, укажите точку вставки через at_get_point (as_variant=False).
    - Программа построит развертку и (опционально) кривую пересечения с цилиндром.
    """
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    # Получаем точку вставки как Python-list (as_variant=False)
    input_point = at_get_point(adoc, prompt="Укажите точку вставки", as_variant=False)

    # Пример параметров: d1 (верх), d2 (низ), H (высота), D_cylinder (магистраль)
    # Обрати внимание: апекс конуса будет в локальной нулевой точке (0,0,0) перед перемещением в insert.
    at_cone_sheet(
        model=model,
        input_point=input_point,
        diameter_base=138.0,    # d2
        diameter_top=102.0,     # d1
        height=68.0,
        D_cylinder=273.0,       # диаметр магистральной трубы (для выреза)
        layer_name="0",
        accuracy=360,
        mode="polyline"
    )
