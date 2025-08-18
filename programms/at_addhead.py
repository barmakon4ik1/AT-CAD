# at_addhead.py
"""
Модуль для построения днища в AutoCAD.
Создает внутреннюю и внешнюю полилинии днища на основе заданных параметров.
"""
from programms.at_base import layer_context, ensure_layer
from programms.at_construction import *
from programms.at_geometry import at_bulge
from programms.at_utils import handle_errors

try:
    from at_config import HEADS_LAYER
except ImportError:
    HEADS_LAYER = "0"  # Слой по умолчанию, если конфигурация недоступна


@handle_errors
def create_polyline(model: object, points: List[Tuple[float, float]],
                    bulge_data: List[Tuple[int, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]]],
                    layer_name: str) -> Optional[object]:
    """
    Создает полилинию с заданными точками и коэффициентами выпуклости.

    Args:
        model: Модельное пространство AutoCAD.
        points: Список точек полилинии [(x1, y1), (x2, y2), ...].
        bulge_data: Список кортежей (индекс, (начальная_точка, конечная_точка, центр)).
        layer_name: Имя слоя.

    Returns:
        object: Объект полилинии или None при ошибке.
    """
    points_list = [coord for point in points for coord in point]
    poly = add_LWpolyline(model, points_list, layer_name)
    for idx, (start, end, center) in bulge_data:
        poly.SetBulge(idx, at_bulge(start, end, center))
    return poly


@handle_errors
def at_add_head(D: float, s: float, R: float, r: float, h1: float, insert_point: Optional[APoint] = None,
                layer: str = HEADS_LAYER, adoc: Optional[object] = None) -> Optional[dict]:
    """
    Строит днище в AutoCAD, создавая внутреннюю и внешнюю полилинии.

    Args:
        D: Диаметр днища.
        s: Толщина материала.
        R: Большой радиус.
        r: Малый радиус.
        h1: Высота днища.
        insert_point: Точка вставки (APoint).
        layer: Имя слоя.
        adoc: Активный документ AutoCAD (если уже инициализирован).

    Returns:
        dict: Словарь с координатами точек или None при ошибке.
    """
    # Вычисление базовых координат
    x0, y0 = 0.0, 0.0
    b = 0.5 * float(D) - float(s)
    bs = 0.5 * float(D)
    R1 = float(R) - float(r)
    Rs = float(R) + float(s)
    h = float(h1)

    # Словарь точек для построения
    points = {
        "p1": [x0 + b, y0],
        "p17": [x0 - b, y0],
        "p2": [x0 + bs, y0],
        "p16": [x0 - bs, y0],
        "p4": [x0 + b, h],
        "p14": [x0 - b, h],
        "p3": [x0 + bs, h],
        "p15": [x0 - bs, h],
        "p5": [x0 + b - r, h],
        "p13": [x0 - b + r, h],
        "p6": [x0, h],
        "p18": [x0, h - math.sqrt(R1 ** 2 - (b - r) ** 2)],
    }
    points["p7"] = [x0, points["p18"][1] + R]
    points["p10"] = [x0, points["p7"][1] + s]
    a = points["p5"][0] - x0
    hc = points["p6"][1] - points["p18"][1]
    dR = R / R1
    dRs = Rs / R1
    points["p8"] = [x0 + a * dR, points["p18"][1] + hc * dR]
    points["p12"] = [x0 - a * dR, points["p18"][1] + hc * dR]
    points["p9"] = [x0 + a * dRs, points["p18"][1] + hc * dRs]
    points["p11"] = [x0 - a * dRs, points["p18"][1] + hc * dRs]

    # Инициализация AutoCAD, если adoc не передан
    if adoc is None:
        cad_objects = ATCadInit()
        if cad_objects is None:
            show_popup(loc.get('cad_init_error'), popup_type="error")
            return None
        adoc, model, _ = cad_objects
    else:
        model = adoc.ModelSpace
        _ = adoc.ActiveLayer

    # Смещение точек, если задана точка вставки
    if insert_point:
        x0, y0 = float(insert_point[0]), float(insert_point[1])
        points = {k: [p[0] + x0, p[1] + y0] for k, p in points.items()}

    try:
        with layer_context(adoc, layer):
            ensure_layer(adoc, layer)

            # Построение внутренней полилинии
            inner_points = (
                points["p1"], points["p4"], points["p8"],
                points["p12"], points["p14"], points["p17"], points["p1"]
            )
            inner_bulge_data = [
                (1, (points["p4"], points["p8"], points["p5"])),
                (2, (points["p8"], points["p12"], points["p18"])),
                (3, (points["p12"], points["p14"], points["p13"]))
            ]
            create_polyline(model, inner_points, inner_bulge_data, layer)

            # Построение внешней полилинии
            outer_points = (
                points["p2"], points["p3"], points["p9"],
                points["p11"], points["p15"], points["p16"], points["p2"]
            )
            outer_bulge_data = [
                (1, (points["p3"], points["p9"], points["p5"])),
                (2, (points["p9"], points["p11"], points["p18"])),
                (3, (points["p11"], points["p15"], points["p13"]))
            ]
            create_polyline(model, outer_points, outer_bulge_data, layer)
    except Exception:
        show_popup(loc.get('heads_error', ''), popup_type="error")
        return None

    try:
        regen(adoc)
    except Exception:
        show_popup(loc.get('regen_error'), popup_type="error")
        return None

    return points


if __name__ == "__main__":
    """
    Тестирование построения днища с тестовыми параметрами.
    """
    at_add_head(1000, 5, 1000, 100, 20)
