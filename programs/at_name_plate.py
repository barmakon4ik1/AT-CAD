# File: programs/at_name_plate.py
"""
Модуль отрисовки таблички сосуда под давлением по заданным параметрам
"""

from __future__ import annotations

import json
from typing import Dict, List

from config.at_cad_init import ATCadInit
from config.at_config import NAME_PLATES_FILE, DEFAULT_TEXT_LAYER, DEFAULT_LASER_LAYER
from programs.at_base import regen
from programs.at_construction import add_polyline, add_text, add_rectangle
from programs.at_geometry import polar_point
from locales.at_translations import loc

# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------

TRANSLATIONS = {
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

    def __init__(self, data: dict, plate_data: dict):
        self.data = data            # из пользовательского окна
        self.plate = plate_data     # параметры таблички

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
        "type": "flat_web",

        # геометрия мостика
        "pt": [x, y],               # точка вставки (центр мостика)
        "width": float,             # полная ширина мостика
        "height": float,            # полная высота мостика
        "radius": float,            # радиус скругления углов

        # перемычка (будет реализовано позже)
        "length": float,
        "height_web": float,
        "h_cut": float,
        "l_cut": float,
        "r_cut": float,

        # обязательные технологические параметры
        "order_number": str,
        "detail_number": str,
        "material": str,
        "thickness": float,
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

        # ------------------------------------------------------------------
        # 1. Извлечение и базовая нормализация параметров
        # ------------------------------------------------------------------
        center_point = data["pt"]
        width = data["width"]
        height = data["height"]
        radius = data.get("radius", 0.0)

        # ------------------------------------------------------------------
        # 2. Построение контура мостика
        # ------------------------------------------------------------------
        add_rectangle(model=model, point=center_point, width=width, height=height,
                      layer_name="0", point_direction="center", radius=radius)



        # ------------------------------------------------------------------
        # 5. Тексты
        # ------------------------------------------------------------------
        add_text(
            model=model,
            point=center_point,
            text=data["order_number"] + data["detail_number"],
            layer_name=DEFAULT_TEXT_LAYER,
            text_height=30,
            text_angle=0,
            text_alignment=4,
        )

        add_text(
            model=model,
            point=center_point,
            text=data["order_number"],
            layer_name=DEFAULT_LASER_LAYER,
            text_height=7,
            text_angle=0,
            text_alignment=4,
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

    def get_unfold_data(self) -> dict:
        return {
            "type": self.bridge_type,
            "width": self.data["width"],
            "height": self.data["height"],
            "length": self.data["length"],
            "thickness": self.data["thickness"],
            "edges": "straight",
        }

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

    np = NamePlate()
    name = "GEA_gross"
    name_plate = np.get(name)

    bridge_data = {
        "type": "flat_web",

        # геометрия мостика
        "pt": [0, 0],  # точка вставки (центр мостика)
        "width": 148,  # полная ширина мостика
        "height": 148,  # полная высота мостика
        "radius": 2,  # радиус скругления углов

        # перемычка (будет реализовано позже)
        "length": 50,
        "height_web": 120,
        "h_cut": 20,
        "l_cut": 20,
        "r_cut": 10,

        # обязательные технологические параметры
        "order_number": "K-Nr",
        "detail_number": "1",
        "material": "1.4301",
        "thickness": 3,
    }

    acad = ATCadInit()
    adoc = acad.document
    model = acad.model_space

    bridge = BaseBridge.create_bridge(bridge_data, name_plate)
    bridge.build(model)

    regen(adoc)