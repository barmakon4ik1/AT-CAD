# -*- coding: utf-8 -*-
"""
Модуль: at_cylinder.py
Путь: programs\at_cylinder.py

Назначение:
    Управляет построением развёртки цилиндра (обечайки) с возможными отводами (штуцерами).
    Вызывает модули at_shell для развёртки цилиндра, at_cutout для вырезов и at_nozzle для отводов.

Возвращает единый результат с entities + metadata.
"""

from typing import Dict, List
import math
from config.at_cad_init import ATCadInit
from programs.at_shell import at_shell
from programs.at_cutout import at_cutout
from programs.at_nozzle import at_nozzle  # Заглушка для будущего модуля
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
    "invalid_shell_data": {
        "ru": "Некорректные данные оболочки",
        "de": "Ungültige Schalendaten",
        "en": "Invalid shell data"
    },
    "invalid_cutout_data": {
        "ru": "Некорректные данные отвода {0}: {1}",
        "de": "Ungültige Aussparungsdaten {0}: {1}",
        "en": "Invalid cutout data {0}: {1}"
    },
}
loc.register_translations(TRANSLATIONS)


def main(data):
    """
    Точка входа для вызова модуля.

    Args:
        data: Словарь с данными оболочки и отводов.

    Returns:
        Dict: Результат в формате {"entities": [...], "metadata": {...}}.
    """
    return at_cylinder(data)


def get_insert_point_unwrap(shell_data: Dict, cut: Dict) -> List[float]:
    """
    Рассчитывает точку вставки выреза на развёртке так:
      - Линия шва shell_data['angle'] считается нулевой линией развёртки (X = 0).
      - Для каждого выреза берём его абсолютный угол cut['angle_deg'] (в градусах,
        в той же системе, что и shell_data['angle'] — обычно от +X против часовой).
      - Вычисляем угол от шва до выреза в диапазоне [0, 360) по направлению,
        заданному shell_data['clockwise'].
      - X = R * radians(angle_from_seam), Y = axial offset.
    Возвращает [X, Y, 0].
    """
    R = shell_data["diameter"] / 2.0
    X0, Y0, Z0 = shell_data["insert_point"]
    seam_angle = float(shell_data.get("angle", 0.0))    # угол шва в градусах (абсолютный)
    clockwise = bool(shell_data.get("clockwise", True)) # True = идти по часовой вдоль развёртки

    # Абсолютный угол выреза (в градусах)
    cut_angle = float(cut.get("angle_deg", 0.0))

    # Разность (cut_angle - seam_angle) в диапазоне [0, 360)
    # Это угол от шва до выреза, считая в направлении "по возрастанию" угла.
    angle_from_seam = (cut_angle - seam_angle) % 360.0

    # В большинстве математических систем угол растёт против часовой (CCW).
    # Нам нужно, чтобы направление развёртки соответствовало флагу `clockwise`.
    # Интерпретация:
    #  - если clockwise == False  (развёртка против часовой), то angle_from_seam оставляем как есть;
    #  - если clockwise == True   (развёртка по часовой), то направление вдоль развёртки
    #    соответствует уменьшению (в математическом смысле) — поэтому зеркалим:
    if clockwise:
        # Превращаем угол в величину, отсчитываемую **по направлению развёртки**
        # (т.е. если по часовой — берём "обратный" ход)
        angle_from_seam = (-angle_from_seam) % 360.0

    # Теперь angle_from_seam в [0, 360) — это угол вдоль развёртки от шва.
    # Длина дуги:
    theta_rad = math.radians(angle_from_seam)
    arc_length = R * theta_rad  # единицы длины = те же, что и R

    # Координаты развёртки: X вдоль развёртки (от шва), Y — осевой (offset_axial)
    X_unwrap = X0 + arc_length
    Y_unwrap = Y0 + cut.get("offset_axial", 0.0)

    insert_point = [X_unwrap, Y_unwrap, 0.0]

    # Отладочный вывод (удобно для тестов)
    print(f"[unwrap] seam={seam_angle:.1f}°, cut={cut_angle:.1f}°, "
          f"angle_from_seam={angle_from_seam:.1f}°, arc={arc_length:.3f}, insert={insert_point}")

    return insert_point


class CylinderBuilder:
    """
    Класс для построения развёртки цилиндра с отводами.
    Вызывает at_shell для цилиндра, at_cutout для вырезов и at_nozzle для отводов.
    """
    def __init__(self, shell_data: Dict):
        """
        Инициализация построителя.

        Args:
            shell_data: Словарь с данными оболочки и отводов, полученный из GUI.
        """
        self.shell_data = shell_data
        self.result = {"entities": [], "metadata": {}}

    def _validate_input(self) -> bool:
        """
        Проверяет валидность входных данных.

        Returns:
            bool: True, если данные валидны, иначе вызывает исключение.
        """
        if not self.shell_data:
            raise ValueError(loc.get("no_data_error", "Данные не введены"))
        if not self.shell_data.get("diameter") or self.shell_data["diameter"] <= 0:
            raise ValueError(loc.get("invalid_shell_data", "Некорректные данные оболочки"))
        if not self.shell_data.get("length") or self.shell_data["length"] <= 0:
            raise ValueError(loc.get("invalid_shell_data", "Некорректные данные оболочки"))
        if "insert_point" not in self.shell_data or not isinstance(self.shell_data["insert_point"], (list, tuple)) or len(self.shell_data["insert_point"]) != 3:
            raise ValueError(loc.get("invalid_point_format", "Точка вставки должна быть [x, y, 0]"))
        return True

    def _adjust_cutout_diameter(self, cutout: Dict, cutout_index: int) -> float:
        """
        Корректирует диаметр отвода в зависимости от типа соединения.

        Args:
            cutout: Словарь с данными отвода.
            cutout_index: Индекс отвода для сообщений об ошибках.

        Returns:
            float: Скорректированный диаметр.

        Raises:
            ValueError: Если диаметр или толщина некорректны.
        """
        params = cutout.get("params", {})
        d = params.get("diameter", 0.0)
        s = params.get("thickness", 0.0)
        mode = params.get("mode", "A")

        if d <= 0 or s < 0:
            raise ValueError(loc.get("invalid_cutout_data", "Диаметр или толщина некорректны: d={0}, s={1}").format(d, s, cutout_index))
        if mode not in ["A", "D", "M", "T"]:
            raise ValueError(loc.get("invalid_cutout_data", "Неизвестный тип соединения: {0}").format(mode, cutout_index))

        if mode == "A":
            adjusted_d = d - 2 * s  # Внутренний диаметр
        elif mode == "D":
            adjusted_d = math.ceil(d)
            adjusted_d += 1 if adjusted_d - d < 0.5 else 0
        elif mode == "M":
            adjusted_d = d - s
        elif mode == "T":
            adjusted_d = d + 1
        else:
            adjusted_d = d

        if adjusted_d <= 0:
            raise ValueError(loc.get("invalid_cutout_data", "Скорректированный диаметр <= 0: {0}").format(adjusted_d, cutout_index))
        return adjusted_d

    def build(self) -> Dict:
        """
        Строит развёртку цилиндра и отводов.

        Returns:
            Dict: Результат в формате {"entities": [...], "metadata": {...}}.
        """
        try:
            # Проверка входных данных
            self._validate_input()

            # 1. Вызов at_shell для построения развёртки цилиндра
            shell_input = {
                "insert_point": self.shell_data.get("insert_point"),
                "diameter": self.shell_data.get("diameter"),
                "length": self.shell_data.get("length"),
                "angle": self.shell_data.get("angle", 0.0),
                "clockwise": self.shell_data.get("clockwise", True),
                "axis": self.shell_data.get("axis", True),
                "axis_marks": self.shell_data.get("axis_marks", 0.0),
                "layer_name": self.shell_data.get("layer_name", "0"),
                "thickness": str(self.shell_data.get("thickness", 0.0)),
                "order_number": self.shell_data.get("order_number", ""),
                "detail_number": self.shell_data.get("detail_number", ""),
                "weld_allowance_top": self.shell_data.get("weld_allowance_top", 0.0),
                "weld_allowance_bottom": self.shell_data.get("weld_allowance_bottom", 0.0)
            }
            shell_info = at_shell(shell_input)
            if not shell_info or not shell_info.get("success"):
                raise RuntimeError(loc.get("build_error", "Ошибка построения: at_shell failed"))
            self.result["entities"].append({
                "type": "shell",
                "outline": shell_info.get("outline", []),
                "metadata": shell_info.get("metadata", {})
            })
            self.result["metadata"].update(shell_info.get("metadata", {}))

            # 2. Вызов at_cutout для вырезов, если есть cutouts
            cutouts = self.shell_data.get("cutouts", [])
            if cutouts:
                for idx, cut in enumerate(cutouts, 1):
                    # Валидация данных отвода
                    params = cut.get("params", {})
                    if not all(k in params for k in ["diameter", "thickness", "mode"]):
                        raise ValueError(loc.get("invalid_cutout_data", "Отсутствуют обязательные параметры отвода: {0}").format(params, idx))

                    # Расчёт точки вставки
                    insert_unwrap = get_insert_point_unwrap(self.shell_data, cut)
                    # Корректировка диаметра
                    cut_diameter = self._adjust_cutout_diameter(cut, idx)
                    # Подготовка параметров для at_cutout
                    cut_params = {
                        "insert_point": insert_unwrap,
                        "diameter": cut_diameter,
                        "diameter_main": self.shell_data.get("diameter", 0.0),
                        "offset": cut.get("axial_shift", 0.0),
                        "steps": params.get("steps", 180),
                        "mode": params.get("bulge_mode", "bulge"),  # Режим отрисовки
                        "text": params.get("text", ""),
                        "layer_name": params.get("layer_name", "0")
                    }
                    # Отладочный вывод
                    print(f"Cutout {idx}: params={cut_params}")

                    # Проверка параметров для предотвращения math domain error
                    R = cut_params["diameter_main"] / 2.0
                    r = cut_params["diameter"] / 2.0
                    offset = cut_params["offset"]
                    if R <= 0:
                        raise ValueError(loc.get("invalid_cutout_data", "Диаметр основной трубы <= 0: {0}").format(R, idx))
                    if r <= 0:
                        raise ValueError(loc.get("invalid_cutout_data", "Диаметр отвода <= 0: {0}").format(r, idx))
                    if abs(offset / R) > 1:
                        raise ValueError(loc.get("invalid_cutout_data", "Смещение слишком велико: offset={0}, R={1}").format(offset, R, idx))

                    # Вызов at_cutout
                    cut_info = at_cutout(cut_params)
                    if not cut_info or not cut_info.get("success"):
                        error_msg = cut_info.get("error") if isinstance(cut_info, dict) else "unknown"
                        self.result["entities"].append({
                            "type": "cutout",
                            "outline": [],
                            "metadata": {
                                "error": error_msg,
                                "input": cut_params,
                                "cutout_index": idx
                            }
                        })
                    else:
                        self.result["entities"].append({
                            "type": "cutout",
                            "outline": cut_info.get("outline", []),
                            "metadata": {**cut_info.get("metadata", {}), "cutout_index": idx}
                        })

            # 3. Вызов at_nozzle для отводов с H, S и unroll_branch="Да"
            for idx, cut in enumerate(cutouts, 1):
                params = cut.get("params", {})
                if (params.get("height", 0.0) > 0 and
                    params.get("thickness", 0.0) > 0 and
                    params.get("unroll_branch") == loc.get("yes", "Да")):
                    nozzle_params = {
                        "insert_point": get_insert_point_unwrap(self.shell_data, cut),
                        "diameter": self._adjust_cutout_diameter(cut, idx),
                        "height": params.get("height", 0.0),
                        "thickness": params.get("thickness", 0.0),
                        "layer_name": params.get("layer_name", "0")
                        # Заглушка: добавить параметры фланца позже
                    }
                    # Отладочный вывод
                    print(f"Nozzle {idx}: params={nozzle_params}")

                    # Вызов at_nozzle (заглушка)
                    nozzle_info = at_nozzle(nozzle_params)
                    if not nozzle_info or not nozzle_info.get("success"):
                        error_msg = nozzle_info.get("error") if isinstance(nozzle_info, dict) else "unknown"
                        self.result["entities"].append({
                            "type": "nozzle",
                            "outline": [],
                            "metadata": {
                                "error": error_msg,
                                "input": nozzle_params,
                                "cutout_index": idx
                            }
                        })
                    else:
                        self.result["entities"].append({
                            "type": "nozzle",
                            "outline": nozzle_info.get("outline", []),
                            "metadata": {**nozzle_info.get("metadata", {}), "cutout_index": idx}
                        })

            # Добавляем входные данные в metadata
            self.result["metadata"].setdefault("input_data", self.shell_data)
            return self.result

        except Exception as e:
            self.result["entities"].append({
                "type": "error",
                "outline": [],
                "metadata": {"error": str(e)}
            })
            self.result["metadata"]["error"] = str(e)
            return self.result


def at_cylinder(data: Dict) -> Dict:
    """
    Основная функция для построения цилиндра с отводами.

    Args:
        data: Словарь с данными оболочки и отводов.

    Returns:
        Dict: Результат в формате {"entities": [...], "metadata": {...}}.
    """
    builder = CylinderBuilder(data)
    return builder.build()


# -----------------------------
# Пример использования
# -----------------------------
if __name__ == "__main__":
    cad = ATCadInit()
    adoc = cad.document

    # Пример входного словаря (на основе ShellContentPanel и BranchWindow)
    shell_data = {
        "diameter": 219.1,
        "length": 1000,
        "insert_point": [0, 0, 0],
        "angle": 0,
        "clockwise": True,
        "order_number": "ORD-001",
        "detail_number": "DET-01",
        "material": "Steel",
        "thickness": 5.0,
        "weld_allowance_top": 10,
        "weld_allowance_bottom": 10,
        "axis": True,
        "axis_marks": 0.0,
        "layer_name": "0",
        "cutouts": [
            {
                "angle_deg": 90,
                "offset_axial": 200,
                "axial_shift": 0.0,
                "params": {
                    "diameter": 108.0,
                    "height": 50.0,
                    "thickness": 4.0,
                    "angle_deg": 0.0,
                    "mode": "A",
                    "text": "N1",
                    "steps": 180,
                    "layer_name": "0",
                    "unroll_branch": loc.get("yes", "Да"),
                    "flange_present": loc.get("no", "Нет"),
                    "weld_allowance": 3.0
                }
            },
            {
                "angle_deg": 180,
                "offset_axial": 500,
                "axial_shift": 0.0,
                "params": {
                    "diameter": 57.0,
                    "height": 0.0,
                    "thickness": 3.0,
                    "angle_deg": 0.0,
                    "mode": "D",
                    "text": "N2",
                    "steps": 180,
                    "layer_name": "0",
                    "unroll_branch": loc.get("no", "Нет"),
                    "flange_present": loc.get("no", "Нет"),
                    "weld_allowance": 3.0
                }
            }
        ]
    }

    # Тест для at_cylinder
    result = at_cylinder(shell_data)
    print("Результат:", result)
