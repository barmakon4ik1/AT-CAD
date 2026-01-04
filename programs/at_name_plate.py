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
from programs.at_geometry import polar_point, fillet_points, PolylineBuilder, ensure_point_variant
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
        "en": "Name plate data not loaded"
    },
    "nameplate.file_not_found": {
        "ru": "Файл конфигурации не найден: {0}",
        "en": "Configuration file not found: {0}"
    },
    "nameplate.invalid_format": {
        "ru": "Файл name_plates.json должен содержать список объектов",
        "en": "name_plates.json must contain a list of objects"
    },
    "nameplate.not_found": {
        "ru": "Табличка '{0}' не найдена",
        "en": "Name plate '{0}' not found"
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
        if material != "3.7035" or material != "3.7235":
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
# Вертикальная компоновка табличек
# ---------------------------------------------------------------------------
class PlateLayoutVertical:
    """
    Отвечает только за расчет позиций табличек
    относительно центра мостика.
    """

    @staticmethod
    def compute_positions(
        bridge_height: float,
        plates: list[dict],
        plates_data: dict,
        gap: float = 5.0,
        offset_top: float | str = "center",
    ) -> list[tuple[float, float]]:
        """
        Возвращает список (dx, dy) для каждой таблички
        относительно центра мостика.
        """

        heights = [float(plates_data[p["name"]]["b1"]) for p in plates]
        n = len(heights)

        # --- частный, но ОБЯЗАТЕЛЬНЫЙ случай ---
        if n == 1 and offset_top == "center":
            return [(0.0, 0.0)]

        block_height = sum(heights) + gap * (n - 1)

        # положение верхнего края блока относительно ВЕРХНЕГО края мостика
        if offset_top == "center":
            top_edge_offset = (bridge_height - block_height) / 2
        else:
            top_edge_offset = float(offset_top)

        # y верхнего края блока относительно ЦЕНТРА мостика
        y_top = bridge_height / 2 - top_edge_offset

        positions = []
        current_top = y_top

        for h in heights:
            # центр таблички относительно ЦЕНТРА мостика
            y_center = current_top - h / 2
            positions.append((0.0, y_center))
            current_top -= h + gap

        return positions


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
class BaseBridge:
    """
    Базовый класс мостика таблички.
    Отвечает только за подготовку данных.
    """

    @staticmethod
    def create_bridge(user_data: dict, plate_data: dict):
        bridge_type = user_data.get("type")

        if bridge_type == "flat_web":
            return FlatWebBridge(user_data, plate_data)

        if bridge_type == "bent_straight":
            return BentStraightBridge(user_data, plate_data)

        if bridge_type == "bent_pipe":
            return BentPipeBridge(user_data, plate_data)

        if bridge_type == "bent_cone":
            return BentConeBridge(user_data, plate_data)

        raise ValueError(f"Unsupported bridge type: {bridge_type}")

    def __init__(self, data: dict, plates_data: dict):
        self.data = data
        self.plates_data = plates_data

        self.validate()

    def validate(self) -> None:
        raise NotImplementedError

    def get_unfold_data(self) -> dict:
        """
        Возвращает нормализованные данные
        для дальнейшего построения.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Мостик для таблички Тип 1 — плоский с перемычкой
# ---------------------------------------------------------------------------
class FlatWebBridge(BaseBridge):
    """
    Тип 1 — плоский мостик с перемычкой

    Входящий словарь (self.data):

    {
        "type": "flat_web",         # тип мостика - мостик - плата с перемычкой

        # геометрия мостика
        "pt": [x, y],               # точка вставки (центр мостика)
        "width": float,             # полная ширина мостика
        "height": float,            # полная высота мостика
        "radius": float,            # поведение углов:
                                    # > 0 - скругление
                                    # < 0 - фаска
                                    # == 0 - просто углы

        # перемычка (будет реализовано позже)
        "length": float,            # длина перемычки (расстояние от мостика до сосуда)
        "height_web": float,        # высота перемычки
        "h_cut": float,             # вырез, горизонтальный размер от края
        "l_cut": float,             # вырез, вертикальный симметричный размер
        "r_cut": float,             # тип углов выреза:
                                    # r_cut = 0      → прямой угол
                                    # r_cut > 0      → скругление (радиус = r_cut)
                                    # r_cut < 0      → фаска (длина = |r_cut|)
        "web_detail_number": str,   # номер детали перемычки

        # таблички, их может быть несколько
        "plates": [
            {
                "name": "GEA_gross",
                # опционально
                "offset_top": "center" | float # Отступ от верхнего края таблички до верхнего края мостика
            },
            {
                "name": "GEA_klein"
            }
        ],

    # вертикальные параметры размещения
    "plates_gap": 5.0,              # расстояние между краями табличек (опц., default = 5)

        # обязательные технологические параметры
        "order_number": str,        # номер заказа детали
        "detail_number": str,       # номер детали мостика
        "material": str,            # материал
        "thickness": float,         # толщина
    }
    """

    def validate(self) -> None:
        required = (
            "pt", "width", "height", "radius",
            "length", "height_web", "h_cut", "l_cut", "r_cut",
            "order_number", "detail_number", "material", "thickness"
        )
        for key in required:
            if key not in self.data:
                raise ValueError(f"Missing parameter: {key}")

    def build(self, model):
        data = self.data
        plates = data.get("plates", [])

        center_point = data["pt"]
        bridge_width = data["width"]
        bridge_height = data["height"]

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
            radius=data.get("radius", 0.0),
        )

        # ------------------------------------------------------------------
        # 2. Таблички + отверстия
        # ------------------------------------------------------------------
        if plates:
            gap = data.get("plates_gap", 5.0)
            offset_top = plates[0].get("offset_top", "center")

            positions = PlateLayoutVertical.compute_positions(
                bridge_height=bridge_height,
                plates=plates,
                plates_data=self.plates_data,
                gap=gap,
                offset_top=offset_top,
            )

            for plate_cfg, (dx, dy) in zip(plates, positions):
                plate_name = plate_cfg["name"]
                plate_data = self.plates_data[plate_name]

                # центр таблички в координатах мостика
                plate_center = (
                    center_point[0] + dx,
                    center_point[1] + dy,
                )

                a1 = float(plate_data["a1"])
                b1 = float(plate_data["b1"])
                a = float(plate_data["a"])
                b = float(plate_data["b"])
                d = float(plate_data["d"])

                # ----------------------------------------------------------
                # 2.1 Контур таблички
                # ----------------------------------------------------------
                add_rectangle(
                    model=model,
                    point=plate_center,
                    width=a1,
                    height=b1,
                    layer_name="AM_5",
                    point_direction="center",
                    radius=float(plate_data.get("r", 0.0)),
                )

                # ----------------------------------------------------------
                # 2.2 Отверстия таблички (перенос в развертку)
                # ----------------------------------------------------------
                cx, cy = plate_center
                a2 = a / 2.0

                # 2 отверстия
                if b == 0:
                    hole_positions = [
                        (-a2, 0.0),
                        (a2, 0.0),
                    ]
                # 4 отверстия
                else:
                    b2 = b / 2.0
                    hole_positions = [
                        (-a2, -b2),
                        (a2, -b2),
                        (a2, b2),
                        (-a2, b2),
                    ]

                for hx, hy in hole_positions:
                    add_circle(
                        model=model,
                        center=(cx + hx, cy + hy),
                        radius=d / 2.0,
                        layer_name="0",
                    )

        # ------------------------------------------------------------------
        # 3. Тексты номера заказа и лазерная гравировка на мостике
        # ------------------------------------------------------------------
        BridgeTexts(data).draw(model, center_point)

        # ------------------------------------------------------------------
        # 4. Перемычка
        # ------------------------------------------------------------------
        web_l = data.get("length")
        web_h = data.get("height_web")
        h_cut = data.get("h_cut")
        web_h1 = (web_h - h_cut) / 2
        web_l_cut = data.get("l_cut")
        r_cut = data.get("r_cut", 0.0)

        # Определяем вершины контура перемычки
        p0 = (center_point[0] + bridge_width / 2.0 + 100, center_point[1] - bridge_height / 2.0)
        p1 = (p0[0] + web_l, p0[1])
        p2 = (p1[0], p1[1] + web_h1)
        p3 = (p2[0] - web_l_cut, p2[1])
        p4 = (p3[0], p3[1] + h_cut)
        p5 = (p2[0], p4[1])
        p6 = (p1[0], p1[1] + web_h)
        p7 = (p0[0], p6[1])

        pb = PolylineBuilder(p0)

        # Прямые сегменты
        pb.line_to(p1)
        pb.line_to(p2)

        if r_cut == 0.0:
            # все сегменты прямые
            pb.line_to(p3)
            pb.line_to(p4)
        else:
            # скругления или фаски через corner
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)

        # Завершаем прямые сегменты
        pb.line_to(p5)
        pb.line_to(p6)
        pb.line_to(p7)
        pb.close()

        # Строим полилинию
        add_polyline(model, pb.vertices(), layer_name="0", closed=True)

        # ------------------------------------------------------------------
        # 5. Размеры
        # ------------------------------------------------------------------
        cx, cy = center_point

        # Габариты мостика
        x_min = cx - bridge_width / 2
        x_max = cx + bridge_width / 2
        y_min = cy - bridge_height / 2
        y_max = cy + bridge_height / 2

        # горизонтальный габарит мостика (общая ширина)
        p_left_max = (x_min, y_max)
        add_dimension(
            adoc,
            "H",
            ensure_point_variant(p_left_max),
            ensure_point_variant((x_max, y_max)),
            offset=DEFAULT_DIM_OFFSET,
        )
        # вертикальный габарит мостика (общая высота)
        add_dimension(
            adoc,
            "V",
            ensure_point_variant((x_min, y_min)),
            ensure_point_variant((x_min, y_max)),
            offset=DEFAULT_DIM_OFFSET,
        )
        # горизонтальный размер перемычки (ширина перемычки)
        add_dimension(
            adoc,
            "H",
            ensure_point_variant(p1),
            ensure_point_variant(p0),
            offset=DEFAULT_DIM_OFFSET,
        )
        # вертикальный размер перемычки (высота перемычки)
        add_dimension(
            adoc,
            "V",
            ensure_point_variant(p6),
            ensure_point_variant(p1),
            offset=DEFAULT_DIM_OFFSET,
        )

        # ------------------------------------------------------------------
        # 6. Сопроводительный текст
        # ------------------------------------------------------------------
        text_insert_point = polar_point(p_left_max, TEXT_DISTANCE + DEFAULT_DIM_OFFSET, 90)
        AccompanyText(data).draw(model, text_insert_point)

        # ------------------------------------------------------------------
        # 7. Тексты номера заказа и лазерная гравировка на перемычке
        # ------------------------------------------------------------------
        web_text_point = polar_point(p0, 10, 45)
        order_number = data.get("order_number")
        detail_number = data.get("web_detail_number")
        material = data.get("material")

        add_text(
            model=model,
            point=web_text_point,
            text=f"{order_number}-{detail_number}",
            layer_name=DEFAULT_TEXT_LAYER,
            text_height=TEXT_HEIGHT_SMALL,
            text_angle=math.radians(90),
            text_alignment=6,
        )

        # лазерная маркировка
        if material != "3.7035" or material != "3.7235":
            add_text(
                model=model,
                point=web_text_point,
                text=order_number,
                layer_name=DEFAULT_LASER_LAYER,
                text_height=TEXT_HEIGHT_LASER,
                text_angle=0,
                text_alignment=0,
            )


# ---------------------------------------------------------------------------
# Мостик для таблички Тип 2 — гнутый с прямыми краями
# ---------------------------------------------------------------------------
class BentStraightBridge(BaseBridge):
    bridge_type = "bent_straight"

    def validate(self) -> None:
        required = ("width", "height", "length", "thickness")
        for key in required:
            if key not in self.data:
                raise ValueError(f"Missing parameter: {key}")

    def build(self, model):
        data = self.data
        plates = data.get("plates", [])

        center_point = data["pt"]
        width = data["width"]
        bridge_height = data["height"]
        length = data["length"]
        thickness = data["thickness"]
        order_number = data["order_number"]
        detail_number = data["detail_number"]
        material = data["material"]
        shell_radius = data.get("shell_diameter", 0.0) / 2

        h_cut = data.get("h_cut")
        h1_cut = (bridge_height - h_cut) / 2
        l_cut = data.get("l_cut")
        r_cut = data.get("r_cut", 0.0)

        if shell_radius != 0.0:
            length_full = length + shell_radius - (shell_radius ** 2 - width ** 2 / 4) ** 0.5
        else:
            length_full = length

        # ------------------------------------------------------------------
        # 1. Контур мостика
        # ------------------------------------------------------------------

        # Расчетные точки:
        cx, cy = center_point
        p0 = cx + (0.5 * width - thickness), cy - (0.5 * bridge_height - thickness)
        p1 = p0[0] + (length_full - thickness), p0[1]
        p15 = cx - (0.5 * width - thickness), p0[1]
        p14 = p15[0] - (length_full - thickness), p1[1]
        p2 = p1[0], p1[1] + h1_cut
        p3 = p2[0] - l_cut, p2[1]
        p4 = p3[0], p3[1] + h_cut
        p5 = p2[0], p4[1]
        p6 = p1[0], p1[1] + bridge_height
        p7 = p0[0], p6[1]
        p8 = p15[0], p6[1]
        p9 = p14[0], p6[1]
        p10 = p9[0], p4[1]
        p11 = p10[0] + l_cut, p10[1]
        p12 = p11[0], p3[1]
        p13 = p14[0], p3[1]

        pb = PolylineBuilder(p0)

        # Прямые сегменты
        pb.line_to(p1)
        pb.line_to(p2)

        if r_cut == 0.0:
            # все сегменты прямые
            pb.line_to(p3)
            pb.line_to(p4)
        else:
            # скругления или фаски через corner
            pb.corner(p3, p4, r_cut)
            pb.corner(p4, p5, r_cut)

        # Далее прямые сегменты
        pb.line_to(p5)
        pb.line_to(p6)
        pb.line_to(p7)
        pb.line_to(p8)
        pb.line_to(p9)
        pb.line_to(p10)

        if r_cut == 0.0:
            # все сегменты прямые
            pb.line_to(p11)
            pb.line_to(p12)
        else:
            # скругления или фаски через corner
            pb.corner(p11, p12, r_cut)
            pb.corner(p12, p13, r_cut)

        pb.line_to(p13)
        pb.line_to(p14)
        pb.line_to(p15)
        pb.line_to(p0)

        pb.close()

        # Строим полилинию
        add_polyline(model, pb.vertices(), layer_name=DEFAULT_CUTOUT_LAYER, closed=True)

        # Линии гиба
        add_line(model, p0, p7, layer_name=DEFAULT_DIM_LAYER)
        add_line(model, p15, p8, layer_name=DEFAULT_DIM_LAYER)

        # ------------------------------------------------------------------
        # 2. Таблички + отверстия
        # ------------------------------------------------------------------
        if plates:
            gap = data.get("plates_gap", 5.0)
            offset_top = plates[0].get("offset_top", "center")

            positions = PlateLayoutVertical.compute_positions(
                bridge_height=bridge_height,
                plates=plates,
                plates_data=self.plates_data,
                gap=gap,
                offset_top=offset_top,
            )

            for plate_cfg, (dx, dy) in zip(plates, positions):
                plate_name = plate_cfg["name"]
                plate_data = self.plates_data[plate_name]

                # центр таблички в координатах мостика
                plate_center = (
                    center_point[0] + dx,
                    center_point[1] + dy,
                )

                a1 = float(plate_data["a1"])
                b1 = float(plate_data["b1"])
                a = float(plate_data["a"])
                b = float(plate_data["b"])
                d = float(plate_data["d"])

                # ----------------------------------------------------------
                # 2.1 Контур таблички
                # ----------------------------------------------------------
                add_rectangle(
                    model=model,
                    point=plate_center,
                    width=a1,
                    height=b1,
                    layer_name="AM_5",
                    point_direction="center",
                    radius=float(plate_data.get("r", 0.0)),
                )

                # ----------------------------------------------------------
                # 2.2 Отверстия таблички (перенос в развертку)
                # ----------------------------------------------------------
                cx, cy = plate_center
                a2 = a / 2.0

                # 2 отверстия
                if b == 0:
                    hole_positions = [
                        (-a2, 0.0),
                        (a2, 0.0),
                    ]
                # 4 отверстия
                else:
                    b2 = b / 2.0
                    hole_positions = [
                        (-a2, -b2),
                        (a2, -b2),
                        (a2, b2),
                        (-a2, b2),
                    ]

                for hx, hy in hole_positions:
                    add_circle(
                        model=model,
                        center=(cx + hx, cy + hy),
                        radius=d / 2.0,
                        layer_name="0",
                    )

        # ------------------------------------------------------------------
        # 3. Тексты номера заказа и лазерная гравировка на мостике
        # ------------------------------------------------------------------
        BridgeTexts(data).draw(model, center_point)

        # ------------------------------------------------------------------
        # 4. Размеры
        # ------------------------------------------------------------------
        p9v = ensure_point_variant(p9)
        p8v = ensure_point_variant(p8)
        p7v = ensure_point_variant(p7)
        p6v = ensure_point_variant(p6)
        p14v = ensure_point_variant(p14)

        add_dimension(adoc,"H", p9v, p8v, offset=DEFAULT_DIM_OFFSET)
        add_dimension(adoc,"H", p8v, p7v, offset=DEFAULT_DIM_OFFSET)
        add_dimension(adoc,"H", p7v, p6v, offset=DEFAULT_DIM_OFFSET)
        add_dimension(adoc,"H", p9v, p6v, offset=2 * DEFAULT_DIM_OFFSET)
        add_dimension(adoc,"V", p14v, p9v, offset=DEFAULT_DIM_OFFSET)

        # ------------------------------------------------------------------
        # 5. Сопроводительный текст
        # ------------------------------------------------------------------
        text_insert_point = polar_point(p9, TEXT_DISTANCE + 2 * DEFAULT_DIM_OFFSET, 90)
        AccompanyText(data).draw(model, text_insert_point)


# ---------------------------------------------------------------------------
# Мостик для таблички Тип 3 — гнутый под трубу (одинаковые диаметры)
# ---------------------------------------------------------------------------
class BentPipeBridge(BaseBridge):
    bridge_type = "bent_pipe"

    def validate(self) -> None:
        required = ("width", "height", "length", "thickness", "diameter")
        for key in required:
            if key not in self.data:
                raise ValueError(f"Missing parameter: {key}")

    def get_unfold_data(self) -> dict:
        return {
            "type": self.bridge_type,
            "width": self.data["width"],
            "height": self.data["height"],
            "length": self.data["length"],
            "thickness": self.data["thickness"],
            "diameter_left": self.data["diameter"],
            "diameter_right": self.data["diameter"],
        }

# ---------------------------------------------------------------------------
# Мостик для таблички Тип 4 — гнутый под конус (разные диаметры)
# ---------------------------------------------------------------------------
class BentConeBridge(BaseBridge):
    bridge_type = "bent_cone"

    def validate(self) -> None:
        required = (
            "width",
            "height",
            "length",
            "thickness",
            "diameter_left",
            "diameter_right",
        )
        for key in required:
            if key not in self.data:
                raise ValueError(f"Missing parameter: {key}")

    def get_unfold_data(self) -> dict:
        return {
            "type": self.bridge_type,
            "width": self.data["width"],
            "height": self.data["height"],
            "length": self.data["length"],
            "thickness": self.data["thickness"],
            "diameter_left": self.data["diameter_left"],
            "diameter_right": self.data["diameter_right"],
        }



# ---------------------------------------------------------------------------
# Тестовый запуск
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    np = NamePlate()
    pt = [0,0]

    # bridge_data = {
    #     "type": "flat_web", # "bent_straight"
    #
    #     # --------------------------------------------------
    #     # Геометрия мостика
    #     # --------------------------------------------------
    #     "pt": pt,
    #     "width": 160.0,
    #     "height": 220.0,
    #     "radius": 0.0,
    #
    #     # --------------------------------------------------
    #     # Перемычка
    #     # --------------------------------------------------
    #     "length": 50.0,
    #     "height_web": 120.0,
    #     "h_cut": 80.0,
    #     "l_cut": 20.0,
    #     "r_cut": 10.0,
    #     "web_detail_number": "2",
    #
    #     # --------------------------------------------------
    #     # Таблички
    #     # --------------------------------------------------
    #     "plates": [
    #         {
    #             "name": "GEA_gross",  # имя из name_plates.json
    #             # "offset_top": 5.0 # отступ верхнего края таблички от верха мостика
    #         },
    #         {"name": "GEA_klein"},
    #     ],
    #
    #     "plates_gap": 5.0,  # расстояние между краями табличек
    #
    #     # --------------------------------------------------
    #     # Технологические параметры (обязательные)
    #     # --------------------------------------------------
    #     "order_number": "22000",
    #     "detail_number": "1",
    #     "material": "1.4301",
    #     "thickness": 3.0,
    # }

    bridge_data = {
        "type": "bent_straight",

        # --------------------------------------------------
        # Геометрия мостика
        # --------------------------------------------------
        "pt": pt,
        "width": 170.0,
        "height": 160.0,
        "radius": 0.0,
        "shell_diameter": 0,
        "length": 100.0,
        "h_cut": 120.0,
        "l_cut": 20.0,
        "r_cut": 10.0,

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

        # --------------------------------------------------
        # Технологические параметры (обязательные)
        # --------------------------------------------------
        "order_number": "22000",
        "detail_number": "1",
        "material": "1.4301",
        "thickness": 3.0,
    }


    bridge = BaseBridge.create_bridge(bridge_data, np.plates)
    if model:
        bridge.build(model)

        regen(adoc)
    else:
        show_popup("Невозможно выполнить тестовый запуск программы. Автокад не запущен или нет доступа к пространству модели.", "error")
