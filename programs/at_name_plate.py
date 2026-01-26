# noinspection SpellCheckingInspection
"""
File: programs\at_name_plate.py

Назначение:
    Построение разверток мостиков для табличек сосудов под давлением.

Функциональность:
    - геометрия мостиков различных типов (type1 … type5)
    - вырезы в мостике (прямой / скругление / фаска)
    - размещение табличек
    - стандартные и сопроводительные тексты

Примечание:
    Модуль работает с входным словарем bridge_data,
    структура которого описана в BridgeConfig.
"""

from __future__ import annotations
import json
import math
from typing import Dict, List
from config.at_cad_init import ATCadInit
from config.at_config import NAME_PLATES_FILE, DEFAULT_TEXT_LAYER, DEFAULT_LASER_LAYER, DEFAULT_DIM_OFFSET, \
    TEXT_HEIGHT_LASER, TEXT_HEIGHT_SMALL, TEXT_DISTANCE, \
    DEFAULT_CUTOUT_LAYER, DEFAULT_DIM_LAYER
from programs.at_base import regen
from programs.at_construction import add_polyline, add_text, add_rectangle, add_circle, add_line, AccompanyText
from locales.at_translations import loc
from programs.at_dimension import add_dimension
from programs.at_geometry import polar_point, PolylineBuilder, ensure_point_variant, distance_2points, \
    bulge_chord, circle_line_intersection
from programs.at_input import at_get_point
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
            "AutoCAD не запущен или нет доступа к пространству модели"
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

    def draw(self, modelspace, center_point):
        """
            Отрисовка блока табличек и отверстий.

            Args:
                modelspace: Пространство модели AutoCAD.
                center_point: Центральная точка мостика (x, y).
        """
        if not self.plates:
            return

        cx, cy = center_point[0], center_point[1]
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
                model=modelspace,
                point=plate_center,
                width=float(plate_data["a1"]),
                height=float(plate_data["b1"]),
                layer_name="AM_5",
                point_direction="center",
                radius=float(plate_data.get("r", 0.0)),
            )

            # --- отверстия ---
            PlateHoles(plate_data).draw(model_space, plate_center)

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

    def draw(self, modelspace, center_point):
        """
        Нанесение стандартных текстов мостика.

        Args:
            modelspace: Пространство модели AutoCAD.
            center_point: Центральная точка мостика (x, y).
        """
        order_number = self.data["order_number"]
        detail_number = self.data["detail_number"]
        material = self.data["material"]

        # основной текст
        add_text(
            model=modelspace,
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
                model=modelspace,
                point=center_point,
                text=order_number,
                layer_name=DEFAULT_LASER_LAYER,
                text_height=TEXT_HEIGHT_LASER,
                text_angle=0,
                text_alignment=4,
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
    Генерирует и чертит отверстия таблички
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

    def draw(self, modelspace, plate_center, layer_name="0"):
        """
        Отрисовка отверстий.
        """
        for hole in self.get_global_positions(plate_center):
            add_circle(
                model=modelspace,
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

    Класс НЕ выполняет расчёты.
    Он только:
    - извлекает данные из входного словаря
    - хранит их в логически разделённом виде
    - предоставляет удобный доступ к данным через proxy-свойства
    """

    def __init__(self, data: dict):

        # -------------------------------------------------
        # Тип мостика
        # -------------------------------------------------
        self.bridge_type: str = data["type"]

        # -------------------------------------------------
        # Технологические / текстовые данные
        # (НЕ участвуют в расчётах геометрии)
        # -------------------------------------------------
        self.order_number: str = data["order_number"]
        self.detail_number: str = data["detail_number"]
        self.material: str = data["material"]

        # -------------------------------------------------
        # Геометрия мостика (обязательная)
        # -------------------------------------------------
        self.geometry: dict[str, float | list[float]] = data["geometry"]

        # Толщина листа — участвует в геометрии!
        self.thickness: float = float(data["thickness"])

        # -------------------------------------------------
        # Вырез в мостике (может отсутствовать)
        # -------------------------------------------------
        self.cutout: dict | None = data.get("cutout")

        # -------------------------------------------------
        # Специфичные параметры типа мостика
        # -------------------------------------------------
        self.specific: dict = data.get("specific", {})

        # -------------------------------------------------
        # Таблички
        # -------------------------------------------------
        self.plates: list = data.get("plates", [])
        self.plates_gap: float = float(data.get("plates_gap", 5.0))

    # =================================================
    # Proxy-свойства: геометрия
    # =================================================

    @property
    def center_point(self):
        return self.geometry["center_point"]

    @property
    def width(self):
        return self.geometry["width"]

    @property
    def height(self):
        return self.geometry["height"]

    @property
    def length(self):
        return self.geometry["length"]

    # =================================================
    # Proxy-свойства: вырез
    # =================================================

    @property
    def h_cut(self):
        if not self.cutout:
            return 0.0
        return self.cutout["height"]

    @property
    def l_cut(self):
        if not self.cutout:
            return 0.0
        return self.cutout["length"]

    @property
    def r_cut(self):
        if not self.cutout:
            return 0.0
        return self.cutout["radius"]

    # =================================================
    # Proxy-свойства: специфичные параметры
    # =================================================
    @property
    def shell_diameter(self):
        return self.specific["shell_diameter"]

    @property
    def angle(self):
        """
        Угол раскрытия / скоса боковин.
        Используется в type3 / type5.
        """
        return self.specific["edge_angle"]


def build_type1(modelspace, cfg: BridgeConfig):
    """
    Тип 1 — плоский мостик с перемычкой.
    """

    # --------------------------------------------------
    # Геометрия мостика
    # --------------------------------------------------
    center_point = cfg.geometry["center_point"]
    bridge_width = cfg.geometry["width"]
    bridge_height = cfg.geometry["height"]

    # Радиус скругления углов мостика
    radius = cfg.specific["corner_radius"]

    # --------------------------------------------------
    # Контур мостика
    # --------------------------------------------------
    add_rectangle(
        model=modelspace,
        point=center_point,
        width=bridge_width,
        height=bridge_height,
        layer_name="0",
        point_direction="center",
        radius=radius,
    )

    # --------------------------------------------------
    # Размеры
    # --------------------------------------------------
    cx, cy = center_point[0], center_point[1]
    x_min = cx - bridge_width / 2
    x_max = cx + bridge_width / 2
    y_min = cy - bridge_height / 2
    y_max = cy + bridge_height / 2

    p_left_max = (x_min, y_max)

    add_dimension(adoc, "H",
                  ensure_point_variant((x_min, y_max)),
                  ensure_point_variant((x_max, y_max)),
                  offset=DEFAULT_DIM_OFFSET)

    add_dimension(adoc, "V",
                  ensure_point_variant((x_min, y_min)),
                  ensure_point_variant((x_min, y_max)),
                  offset=DEFAULT_DIM_OFFSET)

    # --------------------------------------------------
    # Перемычка (специфика type1)
    # --------------------------------------------------
    web_length = cfg.geometry["length"]
    web_height = cfg.specific["web_height"]

    if web_length > 0 and web_height > 0 and cfg.cutout:
        h_cut = cfg.cutout["height"]
        l_cut = cfg.cutout["length"]
        r_cut = cfg.cutout["radius"]
    else:
        h_cut = 0.0
        l_cut = 0.0
        r_cut = 0.0

    web_h1 = (web_height - h_cut) / 2

    p0 = (cx + bridge_width / 2 + 100, cy - bridge_height / 2)
    p1 = (p0[0] + web_length, p0[1])
    p2 = (p1[0], p1[1] + web_h1)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], p4[1])
    p6 = (p1[0], p1[1] + web_height)
    p7 = (p0[0], p6[1])

    pb = PolylineBuilder(p0)
    pb.line_to(p1)
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

    add_polyline(modelspace, pb.vertices(), layer_name="0", closed=True)

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

    # --------------------------------------------------
    # Точка для сопроводительного текста
    # --------------------------------------------------
    text_insert_point = polar_point(p_left_max, TEXT_DISTANCE + DEFAULT_DIM_OFFSET,90)

    # ------------------------------------------------------------------
    # 4. Тексты на перемычке
    # ------------------------------------------------------------------

    web_text_point = polar_point(p0, 10, 45)
    web_text = f'{cfg.order_number}-{cfg.specific["add_detail_number"]}'
    if web_length < web_height:
        text_angle = math.radians(90)
        text_alignment = 6
    else:
        text_angle = math.radians(0)
        text_alignment = 0

    add_text(
        model=modelspace,
        point=web_text_point,
        text=web_text,
        layer_name=DEFAULT_TEXT_LAYER,
        text_height=TEXT_HEIGHT_SMALL,
        text_angle=text_angle,
        text_alignment=text_alignment
    )

    # лазерная маркировка
    if cfg.material not in ("3.7035", "3.7235"):
        add_text(
            model=modelspace,
            point=web_text_point,
            text=cfg.order_number,
            layer_name=DEFAULT_LASER_LAYER,
            text_height=TEXT_HEIGHT_LASER,
            text_angle=0,
            text_alignment=0,
        )

    return {
        "bridge_top_left": p_left_max,
        "center": center_point,
        "accompany_text_point": text_insert_point,
    }


def build_type2(modelspace, cfg: BridgeConfig):
    """
    Построение развертки мостика типа BentStraight (type2).
    """
    geom = cfg.geometry
    cut = cfg.cutout
    spec = cfg.specific

    center_point = geom["center_point"]
    width = geom["width"]
    bridge_height = geom["height"]
    length = geom["length"]
    thickness = cfg.thickness

    shell_diameter = spec["shell_diameter1"]
    shell_radius = shell_diameter / 2 if shell_diameter else 0.0

    if cut:
        h_cut = cut["height"]
        l_cut = cut["length"]
        r_cut = cut["radius"]
    else:
        h_cut = l_cut = r_cut = 0.0

    # --------------------------------------------------
    # Расчет полной длины
    # --------------------------------------------------
    if shell_radius:
        length_full = length + shell_radius - (shell_radius ** 2 - width ** 2 / 4) ** 0.5
    else:
        length_full = length

    # --------------------------------------------------
    # Геометрия
    # --------------------------------------------------
    cx, cy = center_point[0], center_point[1]
    h1_cut = (bridge_height - h_cut) / 2.0

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
        modelspace,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(modelspace, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p15, p8, layer_name=DEFAULT_DIM_LAYER)

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


def build_type3(modelspace, cfg: BridgeConfig):
    """
    Построение развертки мостика типа 3 —
    скоба с двумя сгибами по сторонам (как для Cyba-Geige).
    """

    # ------------------------------------------------------------------
    # Исходные данные (ТОЛЬКО чтение из BridgeConfig)
    # ------------------------------------------------------------------

    geom = cfg.geometry
    cut = cfg.cutout
    spec = cfg.specific

    center_point = geom["center_point"]
    width = geom["width"]
    bridge_height = geom["height"]
    length = geom["length"]
    thickness = cfg.thickness

    # Диаметр обечайки (обязателен для type3)
    shell_diameter = spec["shell_diameter1"]

    # Угол открытия мостика
    angle = spec["edge_angle"]

    # Вырез
    if cut:
        h_cut = cut["height"]
        l_cut = cut["length"]
        r_cut = cut["radius"]
    else:
        h_cut = l_cut = r_cut = 0.0

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    h1_cut = (bridge_height - h_cut) / 2
    radius = shell_diameter / 2.0
    angle_rad = math.radians(angle)
    alpha_rad = (math.pi - angle_rad) / 2.0
    xs = thickness / math.sin(angle_rad / 2.0)
    w1 = width - 2 * thickness
    l1 = 0.5 * w1 / math.cos(alpha_rad) - (radius - ((xs - thickness) * (xs + thickness)) ** 0.5)
    l2 = radius + (length - thickness) - 0.5 * w1 * math.tan(alpha_rad) - xs

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------
    cx, cy = center_point[0], center_point[1]

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
        modelspace,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(modelspace, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p01, p67, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p15, p8, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p1415, p89, layer_name=DEFAULT_DIM_LAYER)

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


def build_type4(modelspace, cfg: BridgeConfig):
    """
    Построение развертки мостика типа BentStraight
    для посадки на горизонтальный цилиндр (type4).

    Args:
        modelspace (object): пространство модели
        cfg: конфигурация мостика
    """

    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------
    geom = cfg.geometry
    spec = cfg.specific
    cut = cfg.cutout

    center_point = geom["center_point"]
    width = geom["width"]
    bridge_height = geom["height"]
    length = geom["length"]
    thickness = cfg.thickness

    # Диаметр горизонтального цилиндра (обязательный для type4)
    shell_diameter = spec["shell_diameter1"]

    # Параметры выреза
    if cut:
        h_cut = cut["height"]
        l_cut = cut["length"]
        # Если r_cut = 0 — повторяет окружность цилиндра,
        # > 0 — скругление, < 0 — фаска
        r_cut = cut["radius"]
    else:
        h_cut = l_cut = r_cut = 0.0

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    h1_cut = (bridge_height - h_cut) / 2
    l1 = length - thickness
    w1 = 0.5 * width - thickness
    r2 = shell_diameter / 2.0
    a = bridge_height / 2 - h1_cut
    x = l1 + r2 - (r2 ** 2 - bridge_height ** 2 / 4) ** 0.5
    l2 = math.sqrt(r2 ** 2 - a ** 2)

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # ------------------------------------------------------------------
    cx, cy = center_point[0], center_point[1]

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

    # cp = (cx + w1 + l1 + r2, cy) # На всякий случай, если где потребуется

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
        modelspace,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(modelspace, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p15, p8, layer_name=DEFAULT_DIM_LAYER)

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


def build_type5(modelspace, cfg: BridgeConfig):
    """
    Построение развертки мостика со скошенными краями
    для посадки на горизонтальный цилиндр (type5).
    """
    # TODO (GUI):
    #   variant logic is temporary.
    #   In GUI all type5 variants must be normalized to:
    #       - L  (length)
    #       - L1 (shelf length before bevel)
    #   build_type5 must NOT contain variant-specific logic.

    # ------------------------------------------------------------------
    # Исходные данные (read-only из BridgeConfig)
    # ------------------------------------------------------------------
    geom = cfg.geometry
    spec = cfg.specific
    cut = cfg.cutout

    center_point = geom["center_point"]
    width = geom["width"]
    bridge_height = geom["height"]
    length = geom["length"]
    thickness = cfg.thickness

    # Специфические параметры type5
    shell_diameter1 = spec["shell_diameter1"]
    shell_diameter2 = spec.get("shell_diameter2", shell_diameter1)
    angle = spec["edge_angle"]
    variant = spec["variant"]

    l1 = spec.get("l1", 0.0) # длина полочки до скоса
    l2 = spec.get("l2", 0.0) # длина полочки до пересечения с цилиндром

    # Параметры выреза
    if cut:
        h_cut = cut["height"]
        l_cut = cut["length"]
        # r_cut = 0 — повтор окружности
        # >0 — скругление, <0 — фаска
        r_cut = cut["radius"]
    else:
        h_cut = l_cut = r_cut = 0.0

    # ------------------------------------------------------------------
    # Расчетные данные
    # ------------------------------------------------------------------
    w1 = 0.5 * width - thickness # приводим к внутренней ширине для развертки
    h1 = bridge_height / 2.0
    r1 = shell_diameter1 / 2.0
    r2 = shell_diameter2 / 2.0
    h1_cut = h_cut / 2.0
    a = math.radians(angle) / 2.0 # половина угла скоса
    l = length - thickness

    cx, cy = center_point[0], center_point[1]

    # ------------------------------------------------------------------
    # Расчет точек
    # ------------------------------------------------------------------
    p0 = (cx + w1, cy - h1)

    # variant 1 - известны L, L1, D, A, H
    # variant 2 - известны L, D, A, H, линия наклона проходит через центр окружности
    # variant 3 - известны L2, L1, D, A, H
    if variant == 1:
        l01 = l1 - thickness # приводим к внутренней длине для развертки
        dx = 0.0
    elif variant == 2:
        l01 = l + r1 - (h1 / math.tan(a))
        dx = 0.0
    elif variant == 3:
        l2 -= thickness
        l01 = l1 - thickness

        # вертикальное смещение точки пересечения от оси цилиндра
        dy = (l2 - l01) * math.tan(a)

        if abs(dy) > r1:
            raise ValueError("variant 3: dy > radius")

        dx = r1 - math.sqrt(r1 * r1 - dy * dy)
    else:
        raise ValueError("variant must be 1, 2 or 3")

    center1 = (cx + w1 + l + r1 - dx, cy)
    center2 = (cx - w1 - l - r1 + dx, cy)

    cx1, cy1 = center1
    cx2, cy2 = center2

    p01 = (p0[0] + l01, p0[1])
    p1 = circle_line_intersection(p01, center1, shell_diameter1, a)

    # Debug---------------------
    add_circle(model_space, center1, r1, layer_name="AM_5")
    add_circle(model_space, center2, r2, layer_name="AM_5")

    # --------------------------

    p2 = (center1[0] - math.sqrt(r1 * r1 - h1_cut * h1_cut), cy - h1_cut)
    p3 = (p2[0] - l_cut, p2[1])
    p4 = (p3[0], p3[1] + h_cut)
    p5 = (p2[0], cy + h1_cut)
    p6 = (p1[0], cy + (cy1 - p1[1]))
    p67 = (p01[0], cy + h1)
    p7 = (p0[0], p67[1])

    p8 = (cx - w1, p7[1])
    p89 = (p8[0] - l01, p67[1])
    p15 = (p8[0], p01[1])
    p1415 = (p89[0], p01[1])

    p14 = circle_line_intersection(p1415, center2, shell_diameter2, -a)
    p9 = (p14[0], cy + (cy2 - p14[1]))
    p13 = (center2[0] + math.sqrt(r2 * r2 - h1_cut * h1_cut), cy - h1_cut)
    p10 = (p13[0], p5[1])
    p11 = (p10[0] + l_cut, p10[1])
    p12 = (p11[0], p3[1])

    chord1 = distance_2points(p1, p2)

    if chord1 > 2 * r1:
        raise ValueError(
            f"Invalid chord: {chord1:.3f} > diameter {2 * r1:.3f}\n"
            f"p1={p1}, p2={p2}, r={r1}"
        )

    chord2 = distance_2points(p13, p14)

    if chord2 > 2 * r2:
        raise ValueError(
            f"Invalid chord: {chord2:.3f} > diameter {2 * r2:.3f}\n"
            f"p1={p13}, p2={p14}, r={r2}"
        )

    # ------------------------------------------------------------------
    # 1. Контур мостика
    # # ------------------------------------------------------------------
    pb = PolylineBuilder(p0)

    pb.line_to(p01)
    pb.line_to(p1)
    if l_cut != 0.0 and h_cut != 0.0:
        bulge = bulge_chord(r1, distance_2points(p1, p2))
        bulge1 = bulge_chord(r1 + r_cut, distance_2points(p3, p4))
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
        bulge2 = bulge_chord(r2, distance_2points(p13, p14))
        bulge3 = bulge_chord(r2 + r_cut, distance_2points(p11, p12))
        pb.arc_to(p9, -bulge2)
        pb.line_to(p10)
        if r_cut == 0.0:
            pb.arc_to(p11, -bulge3)
            pb.line_to(p12)
        else:
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)
        pb.arc_to(p13, -bulge2)
    else:
        chord1 = distance_2points(p1, p6)
        chord2 = distance_2points(p9, p14)
        bulge = bulge_chord(r1, chord1)
        bulge3 = bulge_chord(r2, chord2)
        pb.arc_to(p1, -bulge)
        pb.line_to(p6)
        pb.line_to(p67)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.line_to(p89)
        pb.arc_to(p9, -bulge3)

    pb.line_to(p14)
    pb.line_to(p1415)
    pb.line_to(p15)
    pb.line_to(p0)

    pb.close()

    # Контур
    add_polyline(
        modelspace,
        pb.vertices(),
        layer_name=DEFAULT_CUTOUT_LAYER,
        closed=True,
    )

    # ------------------------------------------------------------------
    # Линии сгиба
    # ------------------------------------------------------------------

    add_line(modelspace, p0, p7, layer_name=DEFAULT_DIM_LAYER)
    add_line(modelspace, p15, p8, layer_name=DEFAULT_DIM_LAYER)

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

    Дирижер для:
    - построения геометрии
    - текстов
    - табличек
    - сопроводительной информации
    """

    def __init__(self, cfg: BridgeConfig, plates_data: dict):
        self.cfg = cfg
        self.plates_data = plates_data

    def build(self, modelspace):

        # 1. Геометрия мостика
        key_points = self._build_unfold(modelspace)

        # 2. Тексты на мостике
        self._draw_texts(modelspace)

        # 3. Таблички
        self._draw_plates(modelspace)

        # 4. Сопроводительный текст
        accompany_text_point = key_points.get("accompany_text_point")
        if accompany_text_point:
            self._draw_accompany_text(modelspace, accompany_text_point)

    # -------------------------------------------------

    def _build_unfold(self, modelspace: object) -> dict:
        bridge_type = self.cfg.bridge_type

        if bridge_type == "type1":
            key_points = build_type1(modelspace, self.cfg)
        elif bridge_type == "type2":
            key_points = build_type2(model_space, self.cfg)
        elif bridge_type == "type3":
            key_points = build_type3(modelspace, self.cfg)
        elif bridge_type == "type4":
            key_points = build_type4(modelspace, self.cfg)
        elif bridge_type == "type5":
            key_points = build_type5(modelspace, self.cfg)
        else:
            raise ValueError(f"Unsupported bridge type: {bridge_type}")

        return key_points

    # -------------------------------------------------

    def _draw_texts(self, modelspace):
        BridgeTexts({
            "order_number": self.cfg.order_number,
            "detail_number": self.cfg.detail_number,
            "material": self.cfg.material,
        }).draw(modelspace, self.cfg.center_point)

    def _draw_plates(self, modelspace):
        if not self.cfg.plates:
            return

        PlateBlock(
            plates=self.cfg.plates,
            plates_data=self.plates_data,
            bridge_height=self.cfg.height,
            plates_gap=self.cfg.plates_gap,
        ).draw(modelspace, self.cfg.center_point)

    def _draw_accompany_text(self, modelspace, text_point):
        if not text_point:
            return

        AccompanyText({
            "thickness": self.cfg.thickness,
            "material": self.cfg.material,
        }).draw(modelspace, text_point)


# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    cad = ATCadInit()
    adoc = cad.document
    model_space = cad.model_space

    pt = at_get_point(adoc, prompt="Введите точку", as_variant=False)

    np = NamePlate()
    bridge_data = {
        # --------------------------------------------------
        # Тип мостика
        # --------------------------------------------------
        # "type1" | "type2" | "type3" | "type4" | "type5"
        "type": "type1",

        # --------------------------------------------------
        # Технологические параметры (обязательные)
        # НЕ участвуют в геометрии, но нужны для сопровождения
        # --------------------------------------------------
        "order_number": "20374",
        "detail_number": "11",
        "material": "1.4541",

        # Толщина листа — УЧАСТВУЕТ в геометрии (НЕ meta!)
        "thickness": 3.0,

        # --------------------------------------------------
        # Геометрия мостика (базовая)
        # --------------------------------------------------
        "geometry": {
            "center_point": pt,  # базовая точка построения
            "width": 160.0,  # ширина мостика
            "height": 160.0,  # высота мостика
            "length": 67.0,  # длина площадки
        },

        # --------------------------------------------------
        # Специфические параметры типа мостика
        # --------------------------------------------------
        # ВНИМАНИЕ:
        # - наличие параметра означает, что он ЗАДАН
        # - отсутствие параметра означает, что он НЕ НУЖЕН
        # - никаких значений "по умолчанию" тут быть не должно
        # --------------------------------------------------
        "specific": {
            # --- Тип 1 ---
            # Радиус скругления углов мостика
            "corner_radius": 0.0,
            "add_detail_number": "10",
            # Высота перемычки (если отличается от height мостика)
            "web_height": 80.0,

            # --- Тип 2 / 3 / 4 / 5 ---
            # Диаметр обечайки (вертикальной или горизонтальной)
            # shell_diameter1 - основной, когда нужен только один диаметр
            "shell_diameter1": 0.0,
            "shell_diameter2": 0.0,

            # --- Тип 3 / 5 ---
            # Угол раскрытия / скоса боковин
            "edge_angle": 90.0,

            # --- Тип 5 ---
            # Вариант набора исходных данных
            # variant 1 - известны L, L1, D, A, H, здесь L - расстояние от плоскости таблички до касания цилиндра
            # variant 2 - известны L, D, A, H, линия наклона проходит через центр окружности, L как и в варианте 1
            # variant 3 - известны L2, L1, D, A, H, здесь L2 - расстояние от плоскости таблички до точки пересечения скоса с цилиндром
            "variant": 1,
            "l1": 50,
            "l2": 100,

            # --- Будущее развитие ---
            # Для посадки на конус, смещения от вершины и т.п.
            # "cone_top_offset": 0.0,
            # "cone_length": 0.0,
            # "cone_diameter_top": 0.0,
            # "cone_diameter_bottom": 0.0,
        },

        # --------------------------------------------------
        # Геометрия выреза в мостике (если есть)
        # --------------------------------------------------
        # Если вырез НЕ нужен — секцию "cutout" УДАЛЯЕМ целиком
        # --------------------------------------------------
        "cutout": {
            "height": 50.0,  # высота выреза
            "length": 15.0,  # длина выреза
            # r_cut:
            #   = 0   → повторяет окружность цилиндра
            #   > 0   → скругление
            #   < 0   → фаска (abs)
            "radius": 0.0,
        },

        # --------------------------------------------------
        # Таблички
        # --------------------------------------------------
        "plates": [
            {
                "name": "GEA_gross",   # имя из name_plates.json
                # "offset_top": 0.0    # отступ верхнего края от верха мостика
            },
            # {
            #     "name": "GEA_klein",
            # },
        ],

        # Расстояние между краями табличек
        "plates_gap": 5.0,
    }

    if model_space:
        config = BridgeConfig(bridge_data)
        builder = BridgeBuilder(config, np.plates)
        builder.build(model_space)

        regen(adoc)
    else:
        show_popup((loc.tr("cad_not_ready")), "error")