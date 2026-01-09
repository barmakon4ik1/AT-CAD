# File: programs/at_name_plate.py
"""
Модуль отрисовки таблички сосуда под давлением по заданным параметрам
"""

from __future__ import annotations

import json
import math
from typing import Dict, List

from config.at_cad_init import ATCadInit
from config.at_config import NAME_PLATES_FILE, DEFAULT_TEXT_LAYER, DEFAULT_LASER_LAYER, DEFAULT_DIM_OFFSET, \
    DEFAULT_ACCOMPANY_TEXT_LAYER, TEXT_HEIGHT_BIG, TEXT_HEIGHT_LASER, TEXT_HEIGHT_SMALL, TEXT_DISTANCE, \
    DEFAULT_CUTOUT_LAYER, DEFAULT_DIM_LAYER
from programs.at_base import regen
from programs.at_construction import add_polyline, add_text, add_rectangle, add_circle, add_line
from locales.at_translations import loc
from programs.at_dimension import add_dimension
from programs.at_geometry import polar_point, PolylineBuilder, ensure_point_variant, bulge_from_center, at_bulge, \
    calculate_angles, distance_2points, bulge_chord
from windows.at_gui_utils import show_popup

# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    "select_point_prompt": {
        "ru": "Укажите точку:",
        "de": "Wählen Sie einen Punkt:",
        "en": "Select a point:",
    },
    "nameplate.no_data": {
        "ru": "Данные табличек не загружены",
        "de": "Die Typenschilddaten wurden nicht geladen",
        "en": "Name plate data not loaded",
    },
    "nameplate.file_not_found": {
        "ru": "Файл конфигурации не найден: {0}",
        "de": "Konfigurationsdatei nicht gefunden: {0}",
        "en": "Configuration file not found: {0}",
    },
    "nameplate.invalid_format": {
        "ru": "Файл name_plates.json должен содержать список объектов",
        "de": "Die Datei name_plates.json muss eine Liste von Objekten enthalten",
        "en": "name_plates.json must contain a list of objects",
    },
    "nameplate.not_found": {
        "ru": "Табличка '{0}' не найдена",
        "de": "Typenschild '{0}' wurde nicht gefunden",
        "en": "Name plate '{0}' not found",
    },
    "cad_not_ready": {
        "ru": (
            "Невозможно выполнить тестовый запуск программы. "
            "Автокад не запущен или нет доступа к пространству модели"
        ),
        "de": (
            "Der Testlauf kann nicht ausgeführt werden. "
            "AutoCAD ist nicht gestartet oder es besteht kein Zugriff auf den Modellbereich"
        ),
        "en": (
            "Unable to execute the test run. "
            "AutoCAD is not running or there is no access to the model space"
        ),
    },
}


loc.register_translations(TRANSLATIONS)


# ---------------------------------------------------------------------------
# Табличка
# ---------------------------------------------------------------------------
class NamePlate:
    """
    Класс для загрузки и хранения параметров табличек сосудов
    из файла config/name_plates.json.
    """

    def __init__(self) -> None:
        self.config_path = NAME_PLATES_FILE

        if not self.config_path.is_file():
            raise FileNotFoundError(
                loc.tr("nameplate.file_not_found", str(self.config_path))
            )

        # Хранилище всех табличек по имени
        self.plates: Dict[str, Dict[str, float | str]] = {}
        self._load()

    def _load(self) -> None:
        """Чтение и разбор JSON-файла."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                loc.tr("nameplate.file_not_found", str(self.config_path))
            )

        with self.config_path.open(encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(loc.tr("nameplate.invalid_format"))

        for item in data:
            self._add_plate(item)

    def _add_plate(self, item: dict) -> None:
        """Добавление одной таблички в хранилище."""
        name = item.get("name")
        if not name:
            return

        self.plates[name] = {
            "a": float(item.get("a", 0.0)),
            "b": float(item.get("b", 0.0)),
            "a1": float(item.get("a1", 0.0)),
            "b1": float(item.get("b1", 0.0)),
            "d": float(item.get("d", 0.0)),
            "r": float(item.get("r", 0.0)),
            "s": float(item.get("s", 0.0)),
            "remark": item.get("remark", "")
        }

    def get(self, name: str) -> Dict[str, float | str]:
        """Получить параметры таблички по имени."""
        try:
            return self.plates[name]
        except KeyError:
            raise KeyError(loc.tr("nameplate.not_found", name))

    def names(self) -> List[str]:
        """Список доступных имен табличек."""
        return sorted(self.plates.keys())

    def __repr__(self) -> str:
        return f"<NamePlate count={len(self.plates)} path='{self.config_path}'>"


# ---------------------------------------------------------------------------
# Блок табличек + отверстий
# ---------------------------------------------------------------------------
class PlateBlock:
    """
    Универсальная отрисовка табличек и отверстий
    для всех типов мостиков.
    """

    def __init__(
        self,
        plates: list[dict],
        plates_data: dict,
        bridge_height: float,
        plates_gap: float = 5.0,
    ):
        self.plates = plates
        self.plates_data = plates_data
        self.bridge_height = bridge_height
        self.plates_gap = plates_gap

    def draw(self, model, center_point):
        if not self.plates:
            return

        cx, cy = center_point
        y_top_bridge = cy + self.bridge_height / 2

        heights = [
            float(self.plates_data[p["name"]]["b1"])
            for p in self.plates
        ]

        offset_top_cfg = self.plates[0].get("offset_top")

        offset_top, block_height = PlateLayoutVertical.compute_offset_top(
            bridge_height=self.bridge_height,
            heights=heights,
            plates_gap=self.plates_gap,
            offset_top=offset_top_cfg,
        )

        # Y верхнего края блока табличек
        y_top_block = y_top_bridge - offset_top

        current_y = y_top_block

        for i, (plate_cfg, h) in enumerate(zip(self.plates, heights)):
            plate_data = self.plates_data[plate_cfg["name"]]

            # центр текущей таблички
            plate_center = (
                cx,
                current_y - h / 2,
            )

            # --- контур таблички ---
            add_rectangle(
                model=model,
                point=plate_center,
                width=float(plate_data["a1"]),
                height=float(plate_data["b1"]),
                layer_name="AM_5",
                point_direction="center",
                radius=float(plate_data.get("r", 0.0)),
            )

            # --- отверстия ---
            PlateHoles(plate_data).draw(model, plate_center)

            # переход к следующей табличке
            if len(self.plates) > 1:
                current_y -= h + self.plates_gap


# ---------------------------------------------------------------------------
# Стандартные тексты мостика
# ---------------------------------------------------------------------------
class BridgeTexts:
    """
    Единый обработчик стандартных текстов для всех типов мостиков.
    """

    def __init__(self, data: dict):
        self.data = data

    def draw(self, model, center_point):
        """
        Нанесение стандартных текстов мостика
        """
        order_number = self.data["order_number"]
        detail_number = self.data["detail_number"]
        material = self.data["material"]

        # основной текст
        add_text(
            model=model,
            point=center_point,
            text=f"{order_number}-{detail_number}",
            layer_name=DEFAULT_TEXT_LAYER,
            text_height=TEXT_HEIGHT_SMALL,
            text_angle=0,
            text_alignment=4,
        )

        # лазерная маркировка
        if material not in ("3.7035" , "3.7235"):
            add_text(
                model=model,
                point=center_point,
                text=order_number,
                layer_name=DEFAULT_LASER_LAYER,
                text_height=TEXT_HEIGHT_LASER,
                text_angle=0,
                text_alignment=4,
            )


class AccompanyText:
    """
    Сопроводительный текст с толщиной и маркой материала
    """

    def __init__(self, data: dict):
        self.data = data

    def draw(self, model, text_insert_point):
        """
        Отображение текста
        """
        thickness = self.data["thickness"]
        material = self.data["material"]

        add_text(
            model=model,
            point=text_insert_point,
            text=f"{thickness}mm {material}",
            layer_name=DEFAULT_ACCOMPANY_TEXT_LAYER,
            text_height=TEXT_HEIGHT_BIG,
            text_angle=0,
            text_alignment=0,
        )


# ---------------------------------------------------------------------------
# Вертикальная компоновка табличек (от верхнего края мостика)
# ---------------------------------------------------------------------------
class PlateLayoutVertical:
    """
    Отвечает ТОЛЬКО за вертикальную компоновку блока табличек
    относительно ВЕРХНЕГО КРАЯ мостика.
    """

    @staticmethod
    def compute_offset_top(
        bridge_height: float,
        heights: list[float],
        plates_gap: float,
        offset_top: float | None,
    ) -> tuple[float, float]:
        """
        Возвращает:
        - offset_top: расстояние от верхнего края мостика до верхнего края блока
        - block_height: полная высота блока табличек
        """

        if not heights:
            return 0.0, 0.0

        n = len(heights)
        block_height = sum(heights) + plates_gap * (n - 1)

        # Центрирование блока
        if offset_top is None:
            offset_top = (bridge_height - block_height) / 2

        return float(offset_top), block_height


# ---------------------------------------------------------------------------
# Отверстия таблички (генерация по a, b, d)
# ---------------------------------------------------------------------------
class PlateHoles:
    """
    Генерирует и отрисовывает отверстия таблички
    по параметрам a, b, d из JSON.
    """

    def __init__(self, plate_data: dict):
        self.a = float(plate_data["a"])
        self.b = float(plate_data["b"])
        self.d = float(plate_data["d"])

    def get_local_positions(self):
        """
        Локальные координаты отверстий относительно центра таблички.
        """
        a2 = self.a / 2.0

        # 2 отверстия
        if self.b == 0:
            return [
                (-a2, 0.0),
                ( a2, 0.0),
            ]

        # 4 отверстия
        b2 = self.b / 2.0
        return [
            (-a2, -b2),
            ( a2, -b2),
            ( a2,  b2),
            (-a2,  b2),
        ]

    def get_global_positions(self, plate_center):
        """
        Перенос отверстий в координаты развертки.
        """
        cx, cy = plate_center
        result = []

        for x, y in self.get_local_positions():
            result.append({
                "x": cx + x,
                "y": cy + y,
                "d": self.d,
            })

        return result

    def draw(self, model, plate_center, layer_name="0"):
        """
        Отрисовка отверстий.
        """
        for hole in self.get_global_positions(plate_center):
            add_circle(
                model=model,
                center=(hole["x"], hole["y"]),
                radius=hole["d"] / 2.0,
                layer_name=layer_name,
            )


# ---------------------------------------------------------------------------
# Мостик для таблички
# ---------------------------------------------------------------------------
class BridgeConfig:
    """
    Read-only конфигурация мостика.
    Все параметры извлекаются один раз из словаря GUI.
    """

    __slots__ = (
        # main data
        "order_number",
        "detail_number",
        "material",

        # type
        "bridge_type",

        # insert point
        "center_point",

        # dimension
        "thickness",
        "width",
        "height",
        "length",
        "parameter1",
        "parameter2",
        "angle",

        # cut
        "h_cut",
        "l_cut",
        "r_cut",

        # plates and offsets
        "plates",
        "offset_top",
        "plates_gap",
    )

    def __init__(self, data: dict):

        # -------------------------------------------------
        # main data
        self.order_number = data["order_number"]
        self.detail_number = data["detail_number"]
        self.material = data["material"]

        # -------------------------------------------------
        # type
        self.bridge_type = data["type"]

        # -------------------------------------------------
        # insert point
        self.center_point = self._get_center_point(data)

        # -------------------------------------------------
        # dimensions
        self.thickness = float(data["thickness"])
        self.width = float(data["width"])
        self.height = float(data["height"])
        self.length = float(data["length"])

        self.parameter1 = float(data.get("parameter1", 0.0))
        self.parameter2 = float(data.get("parameter2", 0.0))
        self.angle = float(data.get("angle", 0))

        # -------------------------------------------------
        # cut
        self.h_cut = float(data["h_cut"])
        self.l_cut = float(data["l_cut"])
        self.r_cut = float(data["r_cut"])

        # -------------------------------------------------
        # plates
        self.plates = data.get("plates", [])
        self.offset_top = float(data.get("offset_top", 0.0))
        self.plates_gap = float(data.get("plates_gap", 5.0))

    # =====================================================
    # helpers
    # =====================================================

    @staticmethod
    def _get_center_point(data: dict):
        """
        Возвращает точку вставки.
        """
        center_point = data.get("center_point")
        if center_point is None:
            return [0, 0]
        return tuple(center_point)


def build_type1(model, cfg: BridgeConfig):
    """
    Тип 1 — плоский мостик с перемычкой.
    Геометрия + размеры + тексты на перемычке.
    """

    # ------------------------------------------------------------------
    # Исходные данные (read-only)
    # ------------------------------------------------------------------

    center_point = cfg.center_point
    bridge_width = cfg.width
    bridge_height = cfg.height
    radius = cfg.parameter1 / 2  # поведение углов мостика

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------

    add_rectangle(
        model=model,
        point=center_point,
        width=bridge_width,
        height=bridge_height,
        layer_name="0",
        point_direction="center",
        radius=radius,
    )

    # ------------------------------------------------------------------
    # 2. Перемычка
    # ------------------------------------------------------------------

    web_l = cfg.length
    web_h = cfg.parameter2
    h_cut = cfg.h_cut
    web_h1 = (web_h - h_cut) / 2
    web_l_cut = cfg.l_cut
    r_cut = cfg.r_cut

    cx, cy = center_point

    p0 = (
        cx + bridge_width / 2.0 + 100,
        cy - bridge_height / 2.0,
    )
    p1 = (p0[0] + web_l, p0[1])
    p2 = (p1[0], p1[1] + web_h1)
    p3 = (p2[0] - web_l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])
    p6 = (p1[0], p1[1] + web_h)
    p7 = (p0[0], p6[1])

    pb = PolylineBuilder(p0)

    pb.line_to(p1)

    if web_h != 0 and h_cut != 0:
        pb.line_to(p2)

        if r_cut == 0.0:
            pb.line_to(p3)
            pb.line_to(p4)
        else:
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)

        pb.line_to(p5)

    pb.line_to(p6)
    pb.line_to(p7)
    pb.close()

    add_polyline(
        model,
        pb.vertices(),
        layer_name="0",
        closed=True,
    )

    # ------------------------------------------------------------------
    # 3. Размеры
    # ------------------------------------------------------------------

    x_min = cx - bridge_width / 2
    x_max = cx + bridge_width / 2
    y_min = cy - bridge_height / 2
    y_max = cy + bridge_height / 2

    p_left_max = (x_min, y_max)

    # габарит мостика — ширина
    add_dimension(
        adoc,
        "H",
        ensure_point_variant(p_left_max),
        ensure_point_variant((x_max, y_max)),
        offset=DEFAULT_DIM_OFFSET,
    )

    # габарит мостика — высота
    add_dimension(
        adoc,
        "V",
        ensure_point_variant((x_min, y_min)),
        ensure_point_variant((x_min, y_max)),
        offset=DEFAULT_DIM_OFFSET,
    )

    # ширина перемычки
    add_dimension(
        adoc,
        "H",
        ensure_point_variant(p1),
        ensure_point_variant(p0),
        offset=DEFAULT_DIM_OFFSET,
    )

    # высота перемычки
    add_dimension(
        adoc,
        "V",
        ensure_point_variant(p6),
        ensure_point_variant(p1),
        offset=DEFAULT_DIM_OFFSET,
    )

    # ------------------------------------------------------------------
    # 4. Тексты на перемычке
    # ------------------------------------------------------------------

    web_text_point = polar_point(p0, 10, 45)

    add_text(
        model=model,
        point=web_text_point,
        text=f"{cfg.order_number}",
        layer_name=DEFAULT_TEXT_LAYER,
        text_height=TEXT_HEIGHT_SMALL,
        text_angle=math.radians(90),
        text_alignment=6,
    )

    # лазерная маркировка
    if cfg.material not in ("3.7035", "3.7235"):
        add_text(
            model=model,
            point=web_text_point,
            text=cfg.order_number,
            layer_name=DEFAULT_LASER_LAYER,
            text_height=TEXT_HEIGHT_LASER,
            text_angle=0,
            text_alignment=0,
        )

    # Возвращаем ключевые точки для внешней логики
    text_insert_point = polar_point(p_left_max, TEXT_DISTANCE + DEFAULT_DIM_OFFSET, 90)
    return {
        "bridge_top_left": p_left_max,
        "web_start": p0,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


def build_type2(model, cfg: BridgeConfig):
    """
    Построение развертки мостика типа BentStraight (type2).
    """

    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------

    center_point = cfg.center_point
    width = cfg.width
    bridge_height = cfg.height
    length = cfg.length
    thickness = cfg.thickness

    shell_radius = cfg.parameter1 / 2 if cfg.parameter1 else 0.0

    h_cut = cfg.h_cut
    h1_cut = (bridge_height - h_cut) / 2
    l_cut = cfg.l_cut
    r_cut = cfg.r_cut

    # ------------------------------------------------------------------
    # Расчет полной длины
    # ------------------------------------------------------------------

    if shell_radius != 0.0:
        length_full = (length + shell_radius - (shell_radius**2 - width**2 / 4) ** 0.5)
    else:
        length_full = length

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------

    cx, cy = center_point

    p0 = (cx + (0.5 * width - thickness), cy - (0.5 * bridge_height))
    p1 = (p0[0] + (length_full - thickness), p0[1])
    p15 = (cx - (0.5 * width - thickness), p0[1])
    p14 = (p15[0] - (length_full - thickness), p1[1])

    p2 = (p1[0], p1[1] + h1_cut)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])

    p6 = (p1[0], p1[1] + bridge_height)
    p7 = (p0[0], p6[1])
    p8 = (p15[0], p6[1])
    p9 = (p14[0], p6[1])

    p10 = (p9[0], p4[1])
    p11 = (p10[0] + l_cut, p10[1])
    p12 = (p11[0], p3[1])
    p13 = (p14[0], p3[1])

    pb = PolylineBuilder(p0)

    pb.line_to(p1)
    if l_cut != 0.0 and h_cut != 0.0:
        pb.line_to(p2)
        if r_cut == 0.0:
            pb.line_to(p3)
            pb.line_to(p4)
        else:
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)
        pb.line_to(p5)

    pb.line_to(p6)
    pb.line_to(p7)
    pb.line_to(p8)
    pb.line_to(p9)

    if l_cut != 0.0 and h_cut != 0.0:
        pb.line_to(p10)
        if r_cut == 0.0:
            pb.line_to(p11)
            pb.line_to(p12)
        else:
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)
        pb.line_to(p13)

    pb.line_to(p14)
    pb.line_to(p15)
    pb.line_to(p0)

    pb.close()

    # Контур
    add_polyline(
        model,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии гиба
    # ------------------------------------------------------------------

    add_line(model, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p15, p8, layer_name=DEFAULT_DIM_LAYER)

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------

    p9v = ensure_point_variant(p9)
    p8v = ensure_point_variant(p8)
    p7v = ensure_point_variant(p7)
    p6v = ensure_point_variant(p6)
    p14v = ensure_point_variant(p14)

    add_dimension(adoc, "H", p9v, p8v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p8v, p7v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p7v, p6v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p9v, p6v, offset=2 * DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "V", p14v, p9v, offset=DEFAULT_DIM_OFFSET)

    # Возвращаем ключевые точки, если понадобятся дальше
    # Габариты мостика

    text_insert_point = polar_point(p9, TEXT_DISTANCE + 2 * DEFAULT_DIM_OFFSET, 90)
    return {
        "top_right": p6,
        "top_left": p9,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


def build_type3(model, cfg: BridgeConfig):
    """
    Построение развертки мостика типа 3 - как на Cyba-Geige - скобой с двумя гибами по сторонам (type3).
    """
    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------

    center_point = cfg.center_point
    width = cfg.width
    bridge_height = cfg.height
    length = cfg.length
    thickness = cfg.thickness
    angle = cfg.angle
    if angle <= 0:
        angle = 90
    parameter1 = cfg.parameter1
    h_cut = cfg.h_cut
    l_cut = cfg.l_cut
    r_cut = cfg.r_cut

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    h1_cut = (bridge_height - h_cut) / 2
    radius = parameter1 / 2.0
    angle_rad = math.radians(angle)
    alpha_rad = (math.pi - angle_rad) / 2.0
    xs = thickness / math.sin(angle_rad / 2.0)
    w1 = width - 2 * thickness
    l1 = 0.5 * w1 / math.cos(alpha_rad) - (radius - ((xs - thickness) * (xs + thickness)) ** 0.5)
    l2 = radius + (length - thickness) - 0.5 * w1 * math.tan(alpha_rad) - xs

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------
    cx, cy = center_point

    p0 = (cx + (0.5 * width - thickness), cy - (0.5 * bridge_height))
    p01 = (p0[0] + l2, p0[1])
    p1 = (p01[0] + l1, p0[1])
    p15 = (cx - (0.5 * width - thickness), p0[1])
    p1415 = (p15[0] - l2, p1[1])
    p14 = (p1415[0] - l1, p1[1])

    p2 = (p1[0], p1[1] + h1_cut)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])

    p6 = (p1[0], p1[1] + bridge_height)
    p67 = (p01[0], p6[1])
    p7 = (p0[0], p6[1])
    p8 = (p15[0], p6[1])
    p89 = (p1415[0], p6[1])
    p9 = (p14[0], p6[1])

    p10 = (p9[0], p4[1])
    p11 = (p10[0] + l_cut, p10[1])
    p12 = (p11[0], p3[1])
    p13 = (p14[0], p3[1])

    pb = PolylineBuilder(p0)

    pb.line_to(p01)
    pb.line_to(p1)

    if l_cut != 0.0 and h_cut != 0.0:
        pb.line_to(p2)
        if r_cut == 0.0:
            pb.line_to(p3)
            pb.line_to(p4)
        else:
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)
        pb.line_to(p5)

    pb.line_to(p6)
    pb.line_to(p67)
    pb.line_to(p7)
    pb.line_to(p8)
    pb.line_to(p89)
    pb.line_to(p9)

    if l_cut != 0.0 and h_cut != 0.0:
        pb.line_to(p10)
        if r_cut == 0.0:
            pb.line_to(p11)
            pb.line_to(p12)
        else:
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)
        pb.line_to(p13)

    pb.line_to(p14)
    pb.line_to(p1415)
    pb.line_to(p15)
    pb.line_to(p0)

    pb.close()

    # Контур
    add_polyline(
        model,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(model, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p01, p67, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p15, p8, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p1415, p89, layer_name=DEFAULT_DIM_LAYER)

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------

    p9v = ensure_point_variant(p9)
    p89v = ensure_point_variant(p89)
    p8v = ensure_point_variant(p8)
    p7v = ensure_point_variant(p7)
    p67v = ensure_point_variant(p67)
    p6v = ensure_point_variant(p6)
    p14v = ensure_point_variant(p14)

    add_dimension(adoc, "H", p9v, p89v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p89v, p8v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p8v, p7v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p7v, p67v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p67v, p6v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p9v, p6v, offset=2 * DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "V", p14v, p9v, offset=DEFAULT_DIM_OFFSET)

    # Возвращаем ключевые точки, если понадобятся дальше
    # Габариты мостика

    text_insert_point = polar_point(p9, TEXT_DISTANCE + 2 * DEFAULT_DIM_OFFSET, 90)
    return {
        "top_right": p6,
        "top_left": p9,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


def build_type4(model, cfg: BridgeConfig):
    """
    Построение развертки мостика типа BentStraight на трубу (type4).
    """

    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------
    center_point = cfg.center_point
    width = cfg.width
    bridge_height = cfg.height
    length = cfg.length
    thickness = cfg.thickness
    parameter2 = cfg.parameter2

    h_cut = cfg.h_cut
    l_cut = cfg.l_cut
    # Если r_cut = 0 - сегмент будет повторять окружность цилиндра с вырезом,
    # иначе - вертикальный прямой, но со скруглением (>0) или фаской abs(<0)
    r_cut = cfg.r_cut

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    h1_cut = (bridge_height - h_cut) / 2
    l1 = length - thickness
    w1 = 0.5 * width - thickness
    r2 = parameter2 / 2.0
    a = bridge_height / 2 - h1_cut
    x = l1 + r2 - (r2 ** 2 - bridge_height ** 2 / 4) ** 0.5
    # alpha = math.atan(bridge_height / (2 * r2))
    l2 = math.sqrt(r2 ** 2 - a ** 2)

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------
    cx, cy = center_point

    p0 = (cx + w1, cy - bridge_height / 2.0)
    p1 =(p0[0] + x, p0[1])
    p15 = (cx - w1, p0[1])
    p14 = (p15[0] - x, p0[1])
    # pc = (p0[0] + l1, cy)

    p2 = (p0[0] + (l1 + r2 - l2), p1[1] + h1_cut)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])

    p6 = (p1[0], p1[1] + bridge_height)
    p7 = (p0[0], p6[1])
    p8 = (p15[0], p6[1])
    p9 = (p14[0], p6[1])

    p10 = (p8[0] - (l1 + r2 - l2), p9[1] - h1_cut)
    p11 = (p10[0] + l_cut, p10[1])
    p12 = (p11[0], p3[1])
    p13 = (p10[0], p3[1])

    cp = (cx + w1 + l1 + r2, cy)

    pb = PolylineBuilder(p0)

    if l_cut != 0.0 and h_cut != 0.0:
        chord = distance_2points(p1, p2)
        bulge = bulge_chord(r2, chord)
        chord1 = distance_2points(p3, p4)
        bulge1 = bulge_chord(r2 + r_cut, chord1)
        pb.arc_to(p1, -bulge)
        pb.line_to(p2)
        if r_cut == 0.0:
            pb.arc_to(p3, -bulge1)
            pb.line_to(p4)
        else:
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)
        pb.arc_to(p5, -bulge)
        pb.line_to(p6)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.arc_to(p9, -bulge)
        pb.line_to(p10)
        if r_cut == 0.0:
            pb.arc_to(p11, -bulge1)
            pb.line_to(p12)
        else:
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)
        pb.arc_to(p13, -bulge)
    else:
        chord = distance_2points(p1, p6)
        bulge = bulge_chord(r2, chord)
        pb.arc_to(p1, -bulge)
        pb.line_to(p6)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.arc_to(p9, -bulge)

    pb.line_to(p14)
    pb.line_to(p15)
    pb.line_to(p0)

    pb.close()

    # Контур
    add_polyline(
        model,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(model, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p15, p8, layer_name=DEFAULT_DIM_LAYER)

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------

    p9v = ensure_point_variant(p9)
    p8v = ensure_point_variant(p8)
    p7v = ensure_point_variant(p7)
    p6v = ensure_point_variant(p6)
    p14v = ensure_point_variant(p14)

    add_dimension(adoc, "H", p9v, p8v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p8v, p7v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p7v, p6v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p9v, p6v, offset=2 * DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "V", p14v, p9v, offset=DEFAULT_DIM_OFFSET)

    # Возвращаем ключевые точки, если понадобятся дальше
    # Габариты мостика

    text_insert_point = polar_point(p9, TEXT_DISTANCE + 2 * DEFAULT_DIM_OFFSET, 90)
    return {
        "top_right": p6,
        "top_left": p9,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


def build_type5(model, cfg: BridgeConfig):
    """
    Построение развертки мостика со скошенными краями на трубу (type5).
    """

    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------
    center_point = cfg.center_point
    width = cfg.width
    bridge_height = cfg.height
    length = cfg.length
    thickness = cfg.thickness
    parameter2 = cfg.parameter2
    angle = cfg.angle

    h_cut = cfg.h_cut
    l_cut = cfg.l_cut
    # Если r_cut = 0 - сегмент будет повторять окружность цилиндра с вырезом,
    # иначе - вертикальный прямой, но со скруглением (>0) или фаской abs(<0)
    r_cut = cfg.r_cut

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    angle_rad = math.radians(angle)
    h1_cut = (bridge_height - h_cut) / 2
    l1 = length - thickness
    w1 = 0.5 * width - thickness
    r2 = parameter2 / 2.0
    l_full = w1 + l1 + r2
    lx = bridge_height / (2 * math.tan(angle_rad / 2.0))
    l01 = l_full - lx

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------
    cx, cy = center_point

    p0 = (cx + w1, cy - bridge_height / 2.0)
    p01 = (cx + l01, p0[1])
    cp = (cx + w1 + l1 + r2, cy)
    cp1 = (cx - w1 - l1 - r2, cy)
    l1x = lx * r2 / (distance_2points(p01, cp))
    h1x = math.sqrt(r2 * r2 - l1x * l1x)
    p1 =(cp[0] - l1x , cp[1] - h1x)
    p15 = (p0[0] - 2 * w1, p0[1])
    p14 = (cp1[0] + l1x , cp[1] - h1x)
    l2x = (math.sqrt(r2 * r2 - (h_cut / 2.0) ** 2))
    p2 = (cp[0] - l2x, cy - h_cut / 2.0)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])

    p6 = (p1[0], cp[1] + h1x)
    p67 = (p01[0], p0[1] + bridge_height)
    p7 = (p0[0], p67[1])
    p8 = (p15[0], p67[1])
    p89 = (cx - l01, p67[1])
    p9 = (p14[0], p6[1])

    p10 = (cp1[0] + l2x, cy + h_cut / 2.0)
    p11 = (p10[0] + l_cut, p10[1])
    p12 = (p11[0], p3[1])
    p13 = (p10[0], p3[1])
    p1415 = (p89[0], p0[1])

    pb = PolylineBuilder(p0)

    pb.line_to(p01)
    pb.line_to(p1)
    if l_cut != 0.0 and h_cut != 0.0:
        bulge = bulge_chord(r2, distance_2points(p1, p2))
        bulge1 = bulge_chord(r2 + r_cut, distance_2points(p3, p4))
        pb.arc_to(p1, -bulge)
        pb.line_to(p2)
        if r_cut == 0.0:
            pb.arc_to(p3, -bulge1)
            pb.line_to(p4)
        else:
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)
        pb.arc_to(p5, -bulge)
        pb.line_to(p6)
        pb.line_to(p67)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.line_to(p89)
        pb.arc_to(p9, -bulge)
        pb.line_to(p10)
        if r_cut == 0.0:
            pb.arc_to(p11, -bulge1)
            pb.line_to(p12)
        else:
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)
        pb.arc_to(p13, -bulge)
    else:
        chord = distance_2points(p1, p6)
        bulge = bulge_chord(r2, chord)
        pb.arc_to(p1, -bulge)
        pb.line_to(p6)
        pb.line_to(p67)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.line_to(p89)
        pb.arc_to(p9, -bulge)

    pb.line_to(p14)
    pb.line_to(p1415)
    pb.line_to(p15)
    pb.line_to(p0)

    pb.close()

    # Контур
    add_polyline(
        model,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(model, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(model, p15, p8, layer_name=DEFAULT_DIM_LAYER)

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------

    p9v = ensure_point_variant(p9)
    p89v = ensure_point_variant(p89)
    p8v = ensure_point_variant(p8)
    p7v = ensure_point_variant(p7)
    p6v = ensure_point_variant(p6)
    p1415v = ensure_point_variant(p1415)
    off_v_89_1415 = abs(p9[0] - p89[0])
    off_h_9_89 = abs(p89[1] - p9[1])

    add_dimension(adoc, "H", p9v, p8v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p8v, p7v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p7v, p6v, offset=DEFAULT_DIM_OFFSET)
    add_dimension(adoc, "H", p9v, p6v, offset=2 * DEFAULT_DIM_OFFSET + off_h_9_89)
    add_dimension(adoc, "V", p1415v, p89v, offset=DEFAULT_DIM_OFFSET + off_v_89_1415)

    # Возвращаем ключевые точки, если понадобятся дальше
    # Габариты мостика

    text_insert_point = polar_point(p9, TEXT_DISTANCE + off_h_9_89 + 2 * DEFAULT_DIM_OFFSET, 90)
    return {
        "top_right": p6,
        "top_left": p9,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


class BridgeBuilder:
    """
    Центральный класс построения развертки мостика.
    """

    def __init__(self, cfg: BridgeConfig, plates_data: dict):
        self.cfg = cfg
        self.plates_data = plates_data

    def build(self, model):

        # 1. Геометрия мостика
        key_points = self._build_unfold(model)

        # 2. Тексты на мостике
        self._draw_texts(model)

        # 3. Таблички
        self._draw_plates(model)

        # 4. Сопроводительный текст
        accompany_text_point = key_points.get("accompany_text_point")
        if accompany_text_point:
            self._draw_accompany_text(model, accompany_text_point)

    # -------------------------------------------------

    def _build_unfold(self, model: object) -> dict:
        bridge_type = self.cfg.bridge_type

        if bridge_type == "type1":
            key_points = build_type1(model, self.cfg)
        elif bridge_type == "type2":
            key_points = build_type2(model, self.cfg)
        elif bridge_type == "type3":
            key_points = build_type3(model, self.cfg)
        elif bridge_type == "type4":
            key_points = build_type4(model, self.cfg)
        elif bridge_type == "type5":
            key_points = build_type5(model, self.cfg)
        else:
            raise ValueError(f"Unsupported bridge type: {bridge_type}")

        return key_points

    # -------------------------------------------------

    def _draw_texts(self, model):
        BridgeTexts({
            "order_number": self.cfg.order_number,
            "detail_number": self.cfg.detail_number,
            "material": self.cfg.material,
        }).draw(model, self.cfg.center_point)

    def _draw_plates(self, model):
        if not self.cfg.plates:
            return

        PlateBlock(
            plates=self.cfg.plates,
            plates_data=self.plates_data,
            bridge_height=self.cfg.height,
            plates_gap=self.cfg.plates_gap,
        ).draw(model, self.cfg.center_point)

    def _draw_accompany_text(self, model, text_point):
        if not text_point:
            return

        AccompanyText({
            "thickness": self.cfg.thickness,
            "material": self.cfg.material,
        }).draw(model, text_point)


# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    # pt = at_get_point(adoc, prompt="Введите точку", as_variant=False)

    np = NamePlate()
    bridge_data = {
        "type": "type4",
        # --------------------------------------------------
        # Технологические параметры (обязательные)
        # --------------------------------------------------
        "order_number": "22000-1",
        "detail_number": "10",
        "material": "1.4301",
        "thickness": 3.0,
        # --------------------------------------------------
        # Геометрия мостика
        # --------------------------------------------------
        "center_point": [0, 0],
        "width": 170.0,
        "height": 160.0,
        "parameter1": 168.3,
        "parameter2": 500,
        "length": 100.0,
        "angle": 90.0,
        # --------------------------------------------------
        # Геометрия выреза в мостике
        # --------------------------------------------------
        "h_cut": 30.0,
        "l_cut": 20.0,
        "r_cut": 0.0,
        # --------------------------------------------------
        # Таблички
        # --------------------------------------------------
        "plates": [
            {
                "name": "GEA_gross",  # имя из name_plates.json
                # "offset_top": 5.0 # отступ верхнего края таблички от верха мостика
            },
            # {"name": "GEA_klein"},
        ],
        "plates_gap": 5.0,  # расстояние между краями табличек
    }


    if model:
        cfg = BridgeConfig(bridge_data)
        builder = BridgeBuilder(cfg, np.plates)
        builder.build(model)

        regen(adoc)
    else:
        show_popup((loc.tr("cad_not_ready")), "error")