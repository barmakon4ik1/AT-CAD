"""
File: programms/at_cutout.py
Назначение: Построение выреза в трубе для штуцера (корректная версия).
           Строит один замкнутый контур: left -> top -> right -> bottom -> (замыкание в AutoCAD).
           Универсальный алгоритм работает для любого offset (включая 0).
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_polyline, add_dimension, add_line
from programms.at_geometry import ensure_point_variant, convert_to_variant_points
from windows.at_gui_utils import show_popup

# Переводы (локальные)
TRANSLATIONS = {
    "no_data_error": {"ru": "Данные не введены", "de": "Keine Daten eingegeben", "en": "No data provided"},
    "invalid_point_format": {"ru": "Точка вставки должна быть [x, y, 0]", "de": "Einfügepunkt muss [x, y, 0] sein", "en": "Insertion point must be [x, y, 0]"},
    "build_error": {"ru": "Ошибка построения: {0}", "de": "Baufehler: {0}", "en": "Build error: {0}"},
    "contour_not_built": {"ru": "Контур выреза не построен (нет допустимых точек)", "de": "Schnittkontur nicht erstellt (keine gültigen Punkte)", "en": "Cutout contour not built (no valid points)"},
}
loc.register_translations(TRANSLATIONS)


def _f_discr(alpha: float, R: float, r: float, offset: float) -> float:
    """
    Подкоренное выражение: discr(alpha) = r^2 - (R*cos(alpha) - offset)^2
    Если discr >= 0, существует пересечение на этой альфе и y = sqrt(discr).
    """
    term = R * math.cos(alpha) - offset
    return r * r - term * term


def _find_root_bisect(f, a: float, b: float, args: Tuple, tol: float = 1e-9, max_iter: int = 80) -> Optional[float]:
    """
    Бисекция: находит корень f(alpha, *args)=0 на отрезке [a,b].
    Требуется f(a) и f(b) разных знаков. Возвращает корень или None.
    """
    fa = f(a, *args)
    fb = f(b, *args)
    if abs(fa) <= tol:
        return a
    if abs(fb) <= tol:
        return b
    if fa * fb > 0:
        return None
    lo, hi = a, b
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fm = f(mid, *args)
        if abs(fm) <= tol:
            return mid
        if fa * fm <= 0:
            hi, fb = mid, fm
        else:
            lo, fa = mid, fm
    return 0.5 * (lo + hi)


def build_cutout_contour(
    R: float,
    r: float,
    offset: float = 0.0,
    steps: int = 360,
    insert_point: Tuple[float, float] = (0.0, 0.0)
) -> List[Tuple[float, float]]:
    """
    Возвращает список вершин замкнутого контура выреза.
    Алгоритм универсален: работает при offset = 0 и offset != 0.

    Параметры:
      R - радиус основной трубы (мм)
      r - радиус штуцера (мм)
      offset - смещение центра выреза по оси X (мм)
      steps - количество шагов сетки по alpha (чем больше — тем точнее)
      insert_point - (x0, y0) базовая точка развёртки (центр)

    Логика:
      - формируем сетку alpha ∈ [-π, π]
      - находим блок, где discr(alpha) >= 0
      - уточняем границы блока (бисекция)
      - находим alpha_center (максимум y)
      - строим верхнюю ветвь (left→right), нижнюю (right→left)
      - добавляем больше точек около xmin и xmax для сглаживания
    """
    x0, y0 = insert_point

    # 1. сетка alpha
    alpha_grid = [-math.pi + (2.0 * math.pi) * i / steps for i in range(steps + 1)]
    discr_vals = [_f_discr(a, R, r, offset) for a in alpha_grid]
    valid_mask = [d >= 0.0 for d in discr_vals]

    valid_idxs = [i for i, v in enumerate(valid_mask) if v]
    if not valid_idxs:
        return []

    # 2. блоки непрерывных alpha
    blocks: List[Tuple[int, int]] = []
    start_idx, prev_idx = valid_idxs[0], valid_idxs[0]
    for idx in valid_idxs[1:]:
        if idx == prev_idx + 1:
            prev_idx = idx
        else:
            blocks.append((start_idx, prev_idx))
            start_idx, prev_idx = idx, idx
    blocks.append((start_idx, prev_idx))

    # 3. выбираем блок с max(y)
    best_block, best_maxy = None, -1.0
    for b0, b1 in blocks:
        block_maxy = max(math.sqrt(discr_vals[ii]) for ii in range(b0, b1 + 1) if discr_vals[ii] >= 0)
        if block_maxy > best_maxy:
            best_maxy = block_maxy
            best_block = (b0, b1)
    if best_block is None:
        return []

    b0, b1 = best_block
    left_alpha, right_alpha = alpha_grid[b0], alpha_grid[b1]

    # 4. уточняем границы
    if b0 > 0 and not valid_mask[b0 - 1]:
        root_l = _find_root_bisect(_f_discr, alpha_grid[b0 - 1], alpha_grid[b0], (R, r, offset))
        if root_l is not None:
            left_alpha = root_l
    if b1 < len(alpha_grid) - 1 and not valid_mask[b1 + 1]:
        root_r = _find_root_bisect(_f_discr, alpha_grid[b1], alpha_grid[b1 + 1], (R, r, offset))
        if root_r is not None:
            right_alpha = root_r
    if right_alpha <= left_alpha:
        return []

    # 5. центр (max y)
    nsearch = max(50, int((right_alpha - left_alpha) / (2.0 * math.pi) * steps * 3))
    alpha_center = max(
        (left_alpha + (right_alpha - left_alpha) * j / nsearch for j in range(nsearch + 1)),
        key=lambda aa: math.sqrt(_f_discr(aa, R, r, offset)) if _f_discr(aa, R, r, offset) >= 0 else -1
    )

    # 6. дискретизация
    n_seg = max(16, int(round((right_alpha - left_alpha) / (2.0 * math.pi) * steps * 2)))
    center_x = x0 + offset

    # 7. точки границы
    root_l, root_r = left_alpha, right_alpha
    left_point = (center_x + R * (root_l - alpha_center), y0)
    right_point = (center_x + R * (root_r - alpha_center), y0)

    pts: List[Tuple[float, float]] = []
    pts.append(left_point)

    # верх: добавляем точки ближе к краям (сглаживание)
    for j in range(1, n_seg):
        aa = left_alpha + (right_alpha - left_alpha) * j / n_seg
        d = _f_discr(aa, R, r, offset)
        if d < 0:
            continue
        x = center_x + R * (aa - alpha_center)
        y = y0 + math.sqrt(d)
        pts.append((x, y))
    pts.append(right_point)

    # низ: симметрично, обратный проход
    for j in range(n_seg - 1, 0, -1):
        aa = left_alpha + (right_alpha - left_alpha) * j / n_seg
        d = _f_discr(aa, R, r, offset)
        if d < 0:
            continue
        x = center_x + R * (aa - alpha_center)
        y = y0 - math.sqrt(d)
        pts.append((x, y))

    # фильтрация подряд одинаковых
    cleaned: List[Tuple[float, float]] = []
    last = None
    for p in pts:
        if last is None or abs(p[0] - last[0]) > 1e-6 or abs(p[1] - last[1]) > 1e-6:
            cleaned.append(p)
            last = p

    return cleaned


def at_cutout(data: Dict[str, Any]) -> bool:
    """
    Интеграция с AutoCAD: строит полилинию выреза и добавляет контрольные линии/размер.
    Ожидаемые ключи data:
      insert_point: [x, y, z]
      diameter: диаметр штуцера
      diameter_main: диаметр основной трубы
      offset: смещение центра выреза (мм)
      steps: шаг дискретизации (по умолчанию 45..720)
      layer_name: слой для полилинии
    """
    try:
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model

        insert_point = data["insert_point"]
        diameter = float(data["diameter"])
        diameter_main = float(data["diameter_main"])
        offset = float(data["offset"])
        steps = int(data.get("steps", 45))
        layer_name = data.get("layer_name", "0")

        r = diameter / 2.0
        R = diameter_main / 2.0

        contour_pairs = build_cutout_contour(R, r, offset=offset, steps=steps, insert_point=(insert_point[0], insert_point[1]))
        if not contour_pairs:
            show_popup(loc.get("contour_not_built"), popup_type="error")
            return False

        var_pts = convert_to_variant_points(contour_pairs)
        poly = add_polyline(model, var_pts, layer_name=layer_name, closed=True)
        if poly is None:
            show_popup(loc.get("build_error").format("Не удалось создать полилинию"), popup_type="error")
            return False

        # контрольный размер и линии
        center_x = insert_point[0] + offset
        p_top = ensure_point_variant([center_x, insert_point[1] + r, 0.0])
        p_bottom = ensure_point_variant([center_x, insert_point[1] - r, 0.0])
        add_dimension(adoc, "V", p_bottom, p_top, offset=r + 100)

        add_line(model, p_bottom, p_top, layer_name="AM_7")
        p_links = ensure_point_variant([center_x - 1.3 * r, insert_point[1], 0.0])
        p_right = ensure_point_variant([center_x + 1.3 * r, insert_point[1], 0.0])
        add_line(model, p_links, p_right, layer_name="AM_7")

        regen(adoc)
        return True

    except Exception as e:
        show_popup(loc.get("build_error").format(str(e)), popup_type="error")
        return False


if __name__ == "__main__":
    # Пример локального теста
    data = {
        "insert_point": [0.0, 0.0, 0.0],
        "diameter": 200.0,
        "diameter_main": 300.0,
        "offset": 0.0,
        "steps": 720,
        "layer_name": "0",
    }
    at_cutout(data)
