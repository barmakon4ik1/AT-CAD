# -*- coding: utf-8 -*-
"""
Файл: programs/at_run_ecc_red.py
Модуль: at_run_ecc_red
Описание:
    Построение развертки усечённого конуса с одной вертикальной образующей.
    Поддерживаются режимы построения: lines (polyline), bulge (дуги), spline (сплайны).
    Добавляет в модель AutoCAD контур развертки и тексты маркировки/гравировки.

Автор: Alexander Tutubalin
Дата правки: 2025-10-16 (корректировки: локализация, вычисление точки гравировки, докстринги)
"""
import math
from typing import List, Tuple, Any, Dict

import pywintypes

# AutoCAD init & utilities
from config.at_cad_init import ATCadInit
from config.at_config import TEXT_HEIGHT_SMALL, TEXT_DISTANCE, TEXT_HEIGHT_BIG
from programs.at_base import regen
from programs.at_construction import add_polyline, add_spline, add_text
from programs.at_geometry import find_intersection_points, polar_point, ensure_point_variant
from programs.at_input import at_get_point
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "autocad_not_running": {
        "ru": "AutoCAD не запущен. Сначала откройте AutoCAD.",
        "en": "AutoCAD is not running. Please start AutoCAD first.",
        "de": "AutoCAD läuft nicht. Bitte starten Sie zuerst AutoCAD."
    },
    "point_selection_cancelled": {
        "ru": "Выбор точки отменён.",
        "en": "Point selection cancelled.",
        "de": "Punktauswahl abgebrochen."
    },
    "invalid_dimensions": {
        "ru": "Нижний диаметр должен быть больше верхнего.",
        "en": "Bottom diameter must be greater than top diameter.",
        "de": "Der untere Durchmesser muss größer als der obere sein."
    },
    "no_data_error": {
        "ru": "Необходимо заполнить все обязательные поля",
        "en": "All mandatory fields must be filled",
        "de": "Alle Pflichtfelder müssen ausgefüllt werden"
    },
    "text_error_details": {
        "ru": "Ошибка добавления текста {0} ({1}): {2}",
        "en": "Error adding text {0} ({1}): {2}",
        "de": "Fehler beim Hinzufügen von Text {0} ({1}): {2}"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "en": "Build error: {0}",
        "de": "Aufbaufehler: {0}"
    },
    "mm": {
        "ru": "мм",
        "en": "mm",
        "de": "mm"
    }
}
loc.register_translations(TRANSLATIONS)


# -------------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------------
def safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Безопасно делит a / b, возвращая default при малом знаменателе."""
    return a / b if abs(b) > 1e-12 else default


# -------------------------------------------------------------
# Построение половины развёртки (одна сторона вертикальна)
# -------------------------------------------------------------
def build_half_cone_unfold(d: float, h: float, n: int) -> List[Tuple[float, float]]:
    """
    Строит половину развёртки (по одной стороне от оси).
    Возвращает список точек (x, y) в локальной системе координат развёртки.
    Параметры:
        D: диаметр основания (для половины развёртки используется D как диаметр всей окружности)
        H: высота соответствующего (вспомогательного) конуса
        n: количество точек дискретизации дуги (целое положительное)
    """
    points: List[Tuple[float, float]] = []
    apex = (0.0, 0.0)  # вершина (локально)
    first_length = math.sqrt(d ** 2 + h ** 2)
    base_point = (0.0, -first_length)
    points.append(base_point)

    # Длина дуги (ориентировочно) для шага; здесь упрощённый подход
    arc_len = math.pi * d / n
    prev_point = base_point

    # формируем точки для половины дуги (от базовой точки к оси)
    for i in range(1, n // 2 + 1):
        angle_deg = i * 180.0 / n
        l = math.sqrt((d * math.cos(math.radians(angle_deg))) ** 2 + h ** 2)
        intersections = find_intersection_points(apex, l, prev_point, arc_len)
        if not intersections:
            break
        p1, p2 = intersections
        # выбираем точку с большим y
        new_point = p1 if p1[1] > p2[1] else p2
        points.append(new_point)
        prev_point = new_point
    return points


# -------------------------------------------------------------
# Построение полной развертки усечённого конуса
# -------------------------------------------------------------
def build_truncated_cone_from_halves(d1: float, d2: float, h: float, n: int, curve_mode: str = "polyline"):
    """
    Строит контур развертки усечённого конуса (одна вертикальная образующая).
    Возвращает:
        contour (список точек локально), bulge_list, lower_path, upper_path, bulge_lower, bulge_upper
    Параметры:
        d1: верхний диаметр (вершина)
        d2: нижний диаметр (основание)
        h: высота усечения (разность высот)
        n: точность/количество делений
        curve_mode: "polyline"|"bulge"|"spline"
    """
    # Полная высота гипотетического конуса (восстановленного)
    h_full = h * d2 / (d2 - d1) if (d2 - d1) != 0 else 0.0

    # --- Верхний сегмент (меньший радиус)
    upper_half = build_half_cone_unfold(d1, h_full - h, n)
    upper_mirror = [(-x, y) for x, y in upper_half[::-1]]
    upper_curve = upper_mirror[:-1] + upper_half

    # --- Нижний сегмент (больший радиус)
    lower_half = build_half_cone_unfold(d2, h_full, n)
    lower_mirror = [(-x, y) for x, y in lower_half[::-1]]
    lower_curve = lower_mirror[:-1] + lower_half

    # --- Вычисляем крайние точки (для сверки/ориентации)
    upper_left = min(upper_curve, key=lambda p: p[0])
    upper_right = max(upper_curve, key=lambda p: p[0])
    lower_left = min(lower_curve, key=lambda p: p[0])
    lower_right = max(lower_curve, key=lambda p: p[0])

    # --- Расчёт bulge для режимов "bulge" (если выбран)
    bulge_lower: List[float] = []
    bulge_upper: List[float] = []

    if curve_mode == "bulge":
        # длины образующих (как радиусы для дуг)
        # r_lower = math.sqrt(h_full ** 2 + (d2 / 2) ** 2) if h_full else 0.0
        # r_upper = math.sqrt((h_full - h) ** 2 + (d1 / 2) ** 2) if h_full - h else 0.0

        phi_step_lower = math.pi / (len(lower_half) - 1) if len(lower_half) > 1 else 0.0
        phi_step_upper = math.pi / (len(upper_half) - 1) if len(upper_half) > 1 else 0.0

        bulge_lower = [math.tan(phi_step_lower / 4.0)] * len(lower_curve) if phi_step_lower else [0.0] * len(lower_curve)
        bulge_upper = [math.tan(phi_step_upper / 4.0)] * len(upper_curve) if phi_step_upper else [0.0] * len(upper_curve)

    # --- Формируем общий контур (нижняя -> правая образующая -> верхняя (обратная) -> левая образующая)
    # Вместо поиска min/max по X — берём явные торцевые точки
    contour = (
            lower_curve +  # нижняя дуга слева направо
            [upper_curve[-1]] +  # правая образующая: конец нижней → конец верхней
            list(reversed(upper_curve)) +  # верхняя дуга справа налево
            [lower_curve[0]]  # левая образующая: начало верхней → начало нижней
    )
    bulge_list = [0.0] * (len(contour) - 1)

    return contour, bulge_list, lower_curve, upper_curve, bulge_lower, bulge_upper


# -------------------------------------------------------------
# Основная точка входа
# -------------------------------------------------------------
def main(data):
    return at_eccentric_reducer(data)


def at_eccentric_reducer(data: Dict[str, Any]) -> bool:
    """
    Основная функция построения развертки усечённого конуса в AutoCAD.

    Ожидаемый входной словарь (data):
        insert_point: [x, y, z] — точка вставки (может быть None — тогда будет запрошена)
        order_number: str
        detail_number: str
        material: str
        thickness: float
        diameter_top: float  — верхний диаметр (d1)
        diameter_base: float — нижний диаметр (d2)
        height: float        — высота (h)
        mode: str            — "polyline"|"bulge"|"spline"
        accuracy: int
    Возвращает:
        True при успешном построении, False при ошибке.
    """
    try:
        # --- подключение к AutoCAD
        acad = ATCadInit()
        document_acad, modelspace = acad.document, acad.model_space

        if not data:
            show_popup(loc.get("no_data_error"), popup_type="error")
            return False

        # --- читаем входные параметры
        insert_point = data.get("insert_point")
        order_number = data.get("order_number", "")
        detail_number = data.get("detail_number", "")
        material = data.get("material", "")
        thickness = float(data.get("thickness", 0.0))
        d1 = float(data.get("diameter_top", 0.0))   # верхний диаметр
        d2 = float(data.get("diameter_base", 0.0))  # нижний диаметр
        h = float(data.get("height", 0.0))
        curve_mode = data.get("mode", "polyline").lower()
        n = int(data.get("accuracy", 180))

        # Валидация простая
        if d2 <= d1:
            show_popup(loc.get("invalid_dimensions"), popup_type="error")
            return False

        # --- ввод точки вставки (если не передали)
        if not insert_point:
            # Запрашиваем точку у пользователя в AutoCAD
            pt = at_get_point(document_acad, prompt=loc.get("point_prompt", "Укажите вершину развертки"), as_variant=False)
            if not pt or not (isinstance(pt, (list, tuple)) and len(pt) >= 2):
                show_popup(loc.get("point_selection_cancelled"), popup_type="error")
                return False
            # Debug
            # if not pt:
            #     return 0, 0
            insert_point = list(map(float, pt[:3]))
            data["insert_point"] = insert_point
        else:
            insert_point = list(map(float, insert_point[:3]))
            data["insert_point"] = insert_point

        y0: float
        x0, y0 = insert_point[0], insert_point[1]

        # --- Построение контуров развёртки в локальных координатах
        contour_local, bulge_list, lower_path_local, upper_path_local, bulge_lower, bulge_upper = \
            build_truncated_cone_from_halves(d1, d2, h, n, curve_mode)

        # --- Сдвигаем локальные контуры в мировые (с учётом insert_point)
        shift = lambda path: [(x + x0, y + y0) for x, y in path]
        lower_path = shift(lower_path_local)
        upper_path = shift(upper_path_local)
        contour = shift(contour_local)

        # --- Строим в AutoCAD в зависимости от режима ---
        if curve_mode == "spline":
            # отдельные открытые сплайны для верхней и нижней кривых
            add_spline(modelspace, lower_path, layer_name="0", closed=False)
            add_spline(modelspace, upper_path, layer_name="0", closed=False)
            add_polyline(modelspace, [lower_path[0], upper_path[0]], layer_name="0")
            add_polyline(modelspace, [lower_path[-1], upper_path[-1]], layer_name="0")

        elif curve_mode == "bulge":
            # формируем единый замкнутый список точек и bulge'ей
            all_points = (
                lower_path +  # нижняя
                [lower_path[-1], upper_path[-1]] +  # правая вертикальная
                upper_path[::-1] +  # верхняя в обратном порядке
                [upper_path[0], lower_path[0]]  # левая вертикальная
            )
            # bulge: нижняя + 0,0 + верхняя обратная + 0,0
            all_bulges = (
                bulge_lower +
                [0.0, 0.0] +
                list(reversed(bulge_upper)) +
                [0.0, 0.0]
            )
            add_polyline(modelspace, all_points, layer_name="0", bulges=all_bulges, closed=True)

        else:
            # простой режим — замкнутая полилиния по общему контуру
            add_polyline(modelspace, contour, layer_name="0", closed=True)

        # Попытка объединения (join) — если построили по частям (bulge/spline),
        # иначе — пропускаем
        if curve_mode in ["bulge", "spline"]:
            try:
                entities_to_join = []
                for i in range(1, 5):
                    ent = modelspace.Item(modelspace.Count - i)
                    entities_to_join.append(ent)

                base_ent = entities_to_join[0]

                if hasattr(base_ent, "JoinEntities"):
                    base_ent.JoinEntities(entities_to_join[1:])
                    base_ent.Closed = True

            except pywintypes.com_error:
                pass

        # ---------------------------------------------------------
        # Вычисление точек текста
        # ---------------------------------------------------------

        # Значения по умолчанию (на случай пустого контура)
        max_x = x0
        max_y = y0

        # Берём bounding box локального контура и считаем центр:
        if contour_local:
            xs = [p[0] for p in contour_local]
            ys = [p[1] for p in contour_local]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            center_local_x = (min_x + max_x) / 2.0
            center_local_y = (min_y + max_y) / 2.0

            # Переводим локальный центр в мировые координаты
            text_point = (
                center_local_x + x0,
                center_local_y + y0,
                insert_point[2] if len(insert_point) > 2 else 0.0
            )
        else:
            # fallback: если контур пуст — используем insert_point
            text_point = (
                x0,
                y0,
                insert_point[2] if len(insert_point) > 2 else 0.0
            )

        # Точка маркировки — смещение от точки гравировки на 10 мм вверх
        mark_point = polar_point(text_point, distance=10, alpha=90, as_variant=False)

        # ✅ Точка для вывода пояснительного текста (в мировых координатах)
        acc_text_point = ensure_point_variant([
            max_x + x0,
            max_y + y0,
            insert_point[2] if len(insert_point) > 2 else 0.0
        ])

        # ---------------------------------------------------------
        # Формирование текстовых конфигураций
        # ---------------------------------------------------------
        k_text = f"{order_number}"
        f_text = k_text
        if detail_number:
            f_text += f"-{detail_number}"
        text_ab = TEXT_DISTANCE
        text_h = TEXT_HEIGHT_BIG
        text_s = TEXT_HEIGHT_SMALL

        # Приводим численные значения к читаемому виду
        # diameter_base_label = нижний (d2), diameter_top_label = верхний (d1)
        diameter_base_label = d2
        diameter_top_label = d1

        text_configs = [
            # Гравировка — в середине развертки
            {
                "point": ensure_point_variant(text_point),
                "text": k_text,
                "layer_name": "LASER-TEXT",
                "text_height": 7,
                "text_angle": 0,
                "text_alignment": 4
            },
            # Маркировка (смещена от гравировки на 10 мм в направлении 90°)
            {
                "point": ensure_point_variant(mark_point),
                "text": f_text,
                "layer_name": "schrift",
                "text_height": text_s,
                "text_angle": 0,
                "text_alignment": 4
            },
            # Строка К-№ — рядом с гравировкой (здесь используется более крупный текст)
            {
                "point": ensure_point_variant(acc_text_point),
                "text": f"K{f_text}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            # Подробная информация — смещаем вниз от acc_text_point
            {
                "point": ensure_point_variant(polar_point(acc_text_point, distance=text_ab, alpha=-90, as_variant=False)),
                "text": f"D = {diameter_base_label} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(acc_text_point, distance=2 * text_ab, alpha=-90, as_variant=False)),
                "text": f"d = {diameter_top_label} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(acc_text_point, distance=3 * text_ab, alpha=-90, as_variant=False)),
                "text": f"H = {h} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },
            {
                "point": ensure_point_variant(polar_point(acc_text_point, distance=4 * text_ab, alpha=-90, as_variant=False)),
                "text": f"S = {thickness} {loc.get('mm', 'мм')}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            },  #  толщина материала
            {
                "point": ensure_point_variant(polar_point(acc_text_point, distance=5 * text_ab, alpha=-90, as_variant=False)),
                "text": f"Wst: {material}",
                "layer_name": "TEXT",
                "text_height": text_h,
                "text_angle": 0,
                "text_alignment": 0
            } # строка марки материала
        ]

        # Добавляем текстовые объекты в модель
        for i, config in enumerate(text_configs):
            try:
                add_text(modelspace, **config)
            except Exception as e:
                # Формируем локализованное сообщение об ошибке
                err_msg = loc.get("text_error_details", TRANSLATIONS["text_error_details"]["ru"]).format(i + 1, config.get('text', ''), str(e))
                show_popup(err_msg, popup_type="error")
                return False

        # --- обновление документа
        regen(document_acad)

        return True

    except Exception as e:
        # Оборачиваем основную ошибку в локализованное сообщение
        err_msg = loc.get("build_error", TRANSLATIONS["build_error"]["ru"]).format(str(e))
        show_popup(err_msg, popup_type="error")
        return False


# Пример теста при запуске как скрипта
if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    input_data = {
        "insert_point": at_get_point(adoc, prompt=loc.get("select_point", "Укажите точку вставки"), as_variant=False),
        "order_number": "12345",
        "detail_number": "01",
        "material": "1.4301",
        "thickness": 4.0,
        "diameter_top": 267.0,
        "diameter_base": 994.0,
        "height": 918.0,
        "mode": "polyline",
        "accuracy": 360
    }
    ok = at_eccentric_reducer(input_data)
    print("Done:", ok)
