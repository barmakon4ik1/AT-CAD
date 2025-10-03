# -*- coding: utf-8 -*-
"""
Модуль: at_unwrap.py
Путь: programs\at_unwrap.py

Назначение:
    Управляет процессом построения развёртки цилиндрической обечайки
    и размещением на ней вырезов.

Возвращает единый результат с entities + metadata.
"""

from typing import List, Dict

from config.at_cad_init import ATCadInit
from programs.at_geometry import get_insert_point_on_shell
from programs.at_input import at_point_input
from programs.at_shell import at_shell
from programs.at_cutout import at_cutout
from locales.at_translations import loc

# Переводы сообщений
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "invalid_point_format": {
        "ru": "Точка вставки должна быть [x, y, 0]",
        "de": "Einfügepunkt muss [x, y, 0] sein",
        "en": "Insertion point must be [x, y, 0]"
    },
    "build_error": {
        "ru": "Ошибка построения: {0}",
        "de": "Baufehler: {0}",
        "en": "Build error: {0}"
    },
    "contour_not_built": {
        "ru": "Контур выреза не построен (нет допустимых точек)",
        "de": "Schnittkontur nicht erstellt (keine gültigen Punkte)",
        "en": "Cutout contour not built (no valid points)"
    },
    "select_point": {
        "ru": "Укажите точку вставки: ",
        "de": "Punkt auswählen: ",
        "en": "Select point: "
    },
    "unknown_mode": {
        "ru": "Неизвестный режим: {0}",
        "de": "Unbekannter Modus: {0}",
        "en": "Unknown mode: {0}"
    },
}
loc.register_translations(TRANSLATIONS)

import math


def get_insert_point_unwrap(shell_data: dict, cut: dict) -> list:
    R = shell_data["diameter"] / 2.0
    X0, Y0, Z0 = shell_data["insert_point"]
    cut_angle_ref = shell_data.get("cut_angle_ref", 0.0)
    clockwise = shell_data.get("unroll_dir", "CW") == "CW"

    # Относительный угол выреза
    angle_rel = cut["angle_deg"] - cut_angle_ref
    # Убираем инверсию угла, так как at_shell учитывает направление
    theta_rad = math.radians(angle_rel)

    # Координаты на развертке
    X_unwrap = R * theta_rad
    Y_unwrap = cut["offset_axial"]

    # Нормализация X_unwrap
    circumference = 2 * math.pi * R
    X_unwrap = X_unwrap % circumference
    if X_unwrap < 0:
        X_unwrap += circumference

    insert_point = [X_unwrap + X0, Y_unwrap + Y0, 0.0]
    print(f"Cut: angle_deg={cut['angle_deg']}, offset_axial={cut['offset_axial']}, axial_shift={cut.get('axial_shift', 0)}, insert_unwrap={insert_point}")
    return insert_point


class ShellUnwrap:
    def __init__(self, shell_data: Dict):
        """
        shell_data: полный словарь оболочки со всеми параметрами
        """
        self.shell_data = shell_data
        self.cutouts: List[Dict] = []
        self.shell_info: Dict = {}

    def add_cutout(self, angle_deg: float, offset_axial: float,
                   axial_shift: float = 0.0, params: Dict = None):
        """
        Регистрирует вырез с параметрами.
        params: полный словарь, сформированный пользователем через GUI
        """
        self.cutouts.append({
            "angle_deg": angle_deg,
            "offset_axial": offset_axial,
            "axial_shift": axial_shift,
            "params": params or {}
        })

    def build(self) -> Dict:
        """
        Строит развёртку оболочки и всех вырезов.
        Возвращает: {"entities": [...], "metadata": {...}}
        """
        result = {"entities": [], "metadata": {}}

        # Проверка параметров
        if self.shell_data["diameter"] <= 0 or self.shell_data["length"] <= 0:
            raise ValueError("Invalid shell_data")
        if "insert_point" not in self.shell_data:
            raise ValueError("insert_point missing")

        # Развёртка оболочки
        shell_input = dict(self.shell_data)
        shell_input["angle"] = self.shell_data.get("cut_angle_ref", 0.0)
        shell_input["clockwise"] = self.shell_data.get("unroll_dir", "CW") == "CW"
        shell_info = at_shell(shell_input)
        if not shell_info or not shell_info.get("success"):
            raise RuntimeError("Shell unwrap failed")

        self.shell_info = shell_info
        result["entities"].append({
            "type": "shell",
            "outline": shell_info.get("outline", []),
            "metadata": shell_info.get("metadata", {})
        })
        result["metadata"].update(shell_info.get("metadata", {}))
        result["metadata"].setdefault("cutouts_input", []).extend(self.cutouts)

        # Построение вырезов
        for cut in self.cutouts:
            insert_unwrap = get_insert_point_unwrap(self.shell_data, cut)
            cut_params = dict(cut["params"])
            cut_params["insert_point"] = insert_unwrap
            cut_params["offset"] = cut.get("axial_shift", 0.0)  # Передаем axial_shift как offset
            cut_info = at_cutout(cut_params)
            if not cut_info or not cut_info.get("success"):
                result["entities"].append({
                    "type": "cutout",
                    "outline": [],
                    "metadata": {
                        "error": cut_info.get("error") if isinstance(cut_info, dict) else "unknown",
                        "input": cut_params
                    }
                })
            else:
                result["entities"].append({
                    "type": "cutout",
                    "outline": cut_info.get("outline", []),
                    "metadata": cut_info.get("metadata", {})
                })

        return result


# -----------------------------
# Пример использования
# -----------------------------
if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space

    shell_data = {
        "diameter": 219.1,
        "length": 1000,
        "insert_point": at_point_input(adoc, prompt=loc.get("select_point", "Укажите точку вставки"), as_variant=False),
        "cut_angle_ref": 0,
        "unroll_dir": "CCW",
        "weld_allowance_top": 10,
        "weld_allowance_bottom": 10,
        "order_number": "ORD-001",
        "detail_number": "DET-01",
        "material": "Steel",
        "thickness": 5.0
    }
    cutouts = [
        {
            "angle_deg": 90,
            "offset_axial": 200,
            "axial_shift": 0.0,  # Радиальное смещение штуцера (мм)
            "params": {
                "diameter": 108.0,
                "diameter_main": 219.1,
                "mode": "bulge",
                "text": "N1",
                "steps": 180,
                "layer_name": "0"
            }
        },
        {
            "angle_deg": 180,
            "offset_axial": 500,
            "axial_shift": 0.0,
            "params": {
                "diameter": 57.0,
                "diameter_main": 219.1,
                "mode": "bulge",
                "text": "N2",
                "steps": 180,
                "layer_name": "0"
            }
        }
    ]

    unwrap = ShellUnwrap(shell_data)
    for c in cutouts:
        unwrap.add_cutout(**c)

    result = unwrap.build()

