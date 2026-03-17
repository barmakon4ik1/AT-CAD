# -*- coding: utf-8 -*-
"""
Модуль: at_cylinder.py
Путь: programs\at_cylinder.py

Назначение:
    Построение развёртки цилиндра (обечайки) вместе с возможными вырезами
    и развёртками ответвлений (отводов). Управляет вызовами:
        - at_shell — развёртка цилиндра
        - at_cutout — вырезы под отводы
        - at_nozzle — развёртки самих отводов

Возвращает единый результат с entities + metadata.

Особенности реализации в этом файле (кратко):
  - Полные комментарии логики расчётов на русском языке.
  - Защита от некорректных типов, возвращаемых вложенными модулями.
  - Автоматический вертикальный отступ между развёртками отводов (per_nozzle_gap).
  - Точка входа main(data) для API и блок тестирования при запуске как скрипта.
"""

from typing import Dict, List, Any
import math
from config.at_cad_init import ATCadInit
from programs.at_shell import at_shell
from programs.at_cutout import at_cutout
from programs.at_nozzle import at_nozzle  # at_nozzle должен возвращать dict {"success": True/False, ...}
from locales.at_translations import loc
import traceback

from windows.at_gui_utils import show_popup

# ------------------------------------------------------
# Переводы сообщений
# ------------------------------------------------------
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
    Точка входа для вызова модуля из API.

    Args:
        data: Словарь с данными оболочки и отводов.

    Returns:
        Dict: Результат в формате {"entities": [...], "metadata": {...}}.
    """
    return at_cylinder(data)

# ========================================================
# Вспомогательные функции
# ========================================================

def get_insert_point_unwrap(shell_data: Dict, cut: Dict) -> List[float]:
    """
    Рассчитывает точку вставки выреза на развёртке цилиндра.

    Подробное пояснение логики:
    ───────────────────────────
    Развёртка цилиндра представляет собой прямоугольник:
        • Ширина = длина окружности цилиндра = π * D
        • Высота = длина цилиндра

    Каждое отверстие (вырез под отвод) имеет своё положение на поверхности
    цилиндра. Положение задаётся двумя параметрами:
        1. cut['angle_deg'] — угловое положение отверстия на цилиндре.
        2. cut['offset_axial'] — осевой сдвиг вдоль длины цилиндра.

    Чтобы вычислить координаты отверстия на развёртке:
        1) Определяем дуговое расстояние от линии шва до отверстия.
        Линия шва имеет угол shell_data['angle'].
        2) Вычисляем угол:
        angle_from_seam = (cut_angle - seam_angle) mod 360
        3) Если развёртка идёт по часовой стрелке, то направление дуги
        инвертируется:
        angle_from_seam = -angle_from_seam mod 360
        4) Перевод угла в длину дуги:
        arc_length = R * radians(angle_from_seam)
        5) Добавляем X0 — глобальную точку вставки, чтобы привести координаты
        в систему AutoCAD.
    """
    R = shell_data["diameter"] / 2.0
    X0, Y0, Z0 = shell_data["insert_point"]
    seam_angle = float(shell_data.get("angle", 0.0))    # угол шва в градусах (абсолютный)
    clockwise = bool(shell_data.get("clockwise", True)) # True = идти по часовой вдоль развёртки
    cut_angle = float(cut.get("angle_deg", 0.0)) # Абсолютный угол выреза (в градусах)
    offset = float(cut.get("offset", 0.0))

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
        # Теперь angle_from_seam в (0, 360) — это угол вдоль развёртки от шва.

    # Длина дуги:
    arc_length = R * math.radians(angle_from_seam)  # единицы длины = те же, что и R

    # Координаты развёртки: X вдоль развёртки (от шва), Y — осевой (offset_axial)
    return [X0 + arc_length, Y0 + cut.get("offset_axial", 0.0) - offset, 0.0]

# ========================================================
# Основной класс построителя
# ========================================================
class CylinderBuilder:
    """
    Управляет полной сборкой развёртки цилиндра с вырезами и отводами.

    Логические этапы:
    ──────────────────
        1. Проверка входных данных
        2. Построение развёртки цилиндра (at_shell)
        3. Построение развёрток отверстий (at_cutout)
        4. Построение развёрток отвода (at_nozzle)
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
        Проверяет минимальные условия валидности входных данных.

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

    # --------------------------------------------
    @staticmethod
    def _adjust_cutout_diameter(cutout: Dict, cutout_index: int) -> float:
        """
        Коррекция диаметра отвода в зависимости от режима контактирования.

        Углублённая логика режимов:
        ──────────────────────────
        A — d - 2s → вырез меньше на двойную толщину
        D — округление вверх (если дробная часть < 0.5 → +1)
        M — d - s → уменьшение диаметра на толщину
        T — d + 1 → технологический припуск +1 мм


        Проверки:
            • диаметр и толщина должны быть > 0
            • скорректированный диаметр > 0

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
        contact_mode = params.get("contact_mode", "A")

        if d <= 0 or s < 0:
            raise ValueError(loc.get("invalid_cutout_data", "Диаметр или толщина некорректны: d={0}, s={1}").format(d, s, cutout_index))
        # if contact_mode not in ["A", "D", "M", "T"]:
        #     raise ValueError(loc.get("invalid_cutout_data", "Неизвестный тип соединения: {0}").format(contact_mode, cutout_index))
        # Здесь наверное эта проверка излишне. Потому как ниже: adjusted_d = d во всех остальных случаях

        if contact_mode == "A":
            adjusted_d = d - 2 * s
        elif contact_mode == "D":
            # логика округления/коррекции под фланец
            adjusted_d = math.ceil(d)
            adjusted_d += 1 if adjusted_d - d < 0.5 else 0
        elif contact_mode == "M":
            adjusted_d = d - s
        elif contact_mode == "T":
            adjusted_d = d + 1
        else:
            adjusted_d = d

        if adjusted_d <= 0:
            raise ValueError(loc.get("invalid_cutout_data", "Скорректированный диаметр <= 0: {0}").format(adjusted_d, cutout_index))
        return adjusted_d

    # --------------------------------------------
    def get_nozzle_insert_point(self, index: int, cut: Dict, params: Dict) -> List[float]:
        """
        Точка вставки развёртки отвода (за пределами развёртки цилиндра).

        Подробности:
          - Рассчитывается generatrix для базовой позиции (угол 0) аналогично at_nozzle.
            gen0 = length_full - sqrt((0.5*diameter_main)^2 - offset^2)
          - bottom_y = Y0 - nozzle_length (нижняя граница цилиндра на развёртке)
          - insert_y = bottom_y - gen0 - (index-1) * per_nozzle_gap
            где per_nozzle_gap — минимальный вертикальный отступ между развёртками,
            может быть задан в shell_data как 'per_nozzle_gap' (в мм). По умолчанию 200.

        Углублённая логика:
        ───────────────────
        Развёртка отвода располагается под обечайкой. Чтобы избежать
        наложения нескольких отвода друг на друга, каждый следующий
        сдвигается вниз на фиксированное расстояние gap.

        Основной расчёт — определение генератрисы отвода:
            half_Dm = Dm / 2
            gen0 = L_full - sqrt(half_Dm² - offset²)
        где:
            • Dm — диаметр основного цилиндра
            • offset — смещение оси отвода
            • L_full — высота + припуск сварки

        Полученная величина gen0 определяет вертикальное положение
        начала развёртки.
        """
        X0, Y0, _ = self.shell_data["insert_point"]

        # Параметры для вычисления generatrix_length[0]
        diameter_main = float(self.shell_data.get("diameter", 0.0))
        offset = float(cut.get("axial_shift", 0.0))  # смещение отверстия относительно центральной плоскости
        # weld_allowance = float(params.get("weld_allowance", 0.0))
        nozzle_length = float(params.get("height", params.get("length", 0.0)))  # height == length
        # thk_correction = bool(params.get("thk_correction", False))
        # thickness = float(params.get("thickness", 0.0))

        # radius (может быть использован в дальнейших вычислениях)
        # radius = (float(params.get("diameter", 0.0)) - thickness) / 2.0 if thk_correction else float(params.get("diameter", 0.0)) / 2.0

        # length_full — высота развёртки с припуском
        # length_full = nozzle_length + weld_allowance
        length_full = nozzle_length

        # Для первого угла w0 = 2*pi, sin(2*pi) = 0 => упрощённая формула:
        # generatrix0 = length_full - sqrt((0.5*diameter_main)^2 - (offset)^2)
        half_Dm = 0.5 * diameter_main
        sqrt_term = math.sqrt(max(0.0, half_Dm * half_Dm - offset * offset))
        generatrix0 = length_full - sqrt_term

        # safety: если generatrix0 отрицателен — ставим небольшое положительное значение
        if generatrix0 < 0:
            generatrix0 = 0.0

        # Нижняя граница цилиндра на развёртке (координата Y)
        bottom_y = Y0 - nozzle_length

        # Шаг между соседними развёртками отвода (можно задавать в shell_data)
        per_nozzle_gap = float(self.shell_data.get("per_nozzle_gap", 200.0))

        # insert_y так, чтобы верхняя точка развёртки отвода совпадала с нижней границей цилиндра
        Y = bottom_y - generatrix0 - (index - 1) * per_nozzle_gap

        return [X0, Y, 0.0]

    # --------------------------------------------
    def build(self) -> dict[str, list[Any] | dict[Any, Any]] | None:
        """
        Собирает развёртку цилиндра с вырезами и развёртками отвода.

        Returns:
            Dict: Результат в формате {"entities": [...], "metadata": {...}}.
        """
        try:
            # Проверка входных данных
            self._validate_input()

            # ------------------------
            # 1) Построение обечайки (at_shell)
            # ------------------------
            shell_input = {
                "insert_point": self.shell_data.get("insert_point"),
                "diameter": self.shell_data.get("diameter"),
                "length": self.shell_data.get("length"),
                "angle": self.shell_data.get("angle", 0.0),
                "offset": self.shell_data.get("offset", 0.0),
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

            # ------------------------
            # 2) Построение вырезов (at_cutout)
            # ------------------------
            cutouts = self.shell_data.get("cutouts", [])
            for idx, cut in enumerate(cutouts, 1):
                params = cut.get("params", {})

                # Базовая валидация параметров для выреза
                if not all(k in params for k in ["diameter", "thickness", "contact_mode"]):
                    raise ValueError(loc.get("invalid_cutout_data", "Отсутствуют обязательные параметры отвода: {0}").format(params, idx))

                # Точка вставки на развёртке
                insert_unwrap = get_insert_point_unwrap(self.shell_data, cut)

                # Коррекция диаметра
                cut_diameter = self._adjust_cutout_diameter(cut, idx)

                # Быстрые проверки геометрии, чтобы избежать math errors
                R = self.shell_data.get("diameter", 0.0) / 2.0
                r = cut_diameter / 2.0
                offset = cut.get("axial_shift", 0.0)
                if R <= 0:
                    raise ValueError(loc.get("invalid_cutout_data", "Диаметр основной трубы <= 0: {0}").format(R, idx))
                if r <= 0:
                    raise ValueError(loc.get("invalid_cutout_data", "Диаметр отвода <= 0: {0}").format(r, idx))
                if abs(offset / R) > 1:
                    raise ValueError(loc.get("invalid_cutout_data", "Смещение слишком велико: offset={0}, R={1}").format(offset, R, idx))

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

                # Вызов at_cutout
                cut_info = at_cutout(cut_params)
                if not cut_info or not cut_info.get("success"):
                    self.result["entities"].append({
                        "type": "cutout",
                        "outline": [],
                        "metadata": {
                            "error": cut_info.get("error", "unknown") if isinstance(cut_info, dict) else "unknown",
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

            # ------------------------
            # 3) Построение развёрток отвода (at_nozzle)
            # ------------------------
            for idx, cut in enumerate(cutouts, 1):
                params = cut.get("params", {})

                # определяем, нужно ли строить развёртку отвода
                try:
                    height = float(params.get("height", 0.0))
                    thickness = float(params.get("thickness", 0.0))
                except ValueError:
                    height = params.get("height", 0.0)
                    thickness = params.get("thickness", 0.0)
                unroll_branch = bool(params.get("unroll_branch", False))

                if not (height > 0 and thickness > 0 and unroll_branch):
                    # развёртка данного отвода не требуется
                    continue

                # вычисление точки вставки развёртки отвода
                try:
                    nozzle_insert = self.get_nozzle_insert_point(idx, cut, params)
                except Exception as e:
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": f"get_nozzle_insert_point failed: {str(e)}", "cutout_index": idx}
                    })
                    continue

                # корректировка диаметра отвода
                # shell_data["diameter"] — СРЕДНИЙ диаметр обечайки
                # at_nozzle требует НАРУЖНЫЙ диаметр обечайки
                # Для технологической корректности используем ВНУТРЕННИЙ диаметр отвода
                thk = params.get("thickness")
                diameter = params.get("diameter") - thk
                diameter_main = self.shell_data["diameter"] + thk # вернуть должно наружный диаметр!

                # подготовка параметров для at_nozzle
                nozzle_params = {
                    "insert_point": nozzle_insert,
                    "diameter": diameter,
                    "diameter_main": diameter_main,
                    "length": float(height),
                    "thickness": float(thickness),
                    "layer_name": params.get("layer_name", "0"),
                    "text": params.get("text", f"N{idx}"),
                    "weld_allowance": float(params.get("weld_allowance", 0.0)),
                    "offset": float(cut.get("axial_shift", 0.0)),
                    "angle_deg": float(cut.get("angle_deg", 0.0)),
                    "accuracy": int(params.get("accuracy", 180)),
                    "thk_correction": bool(params.get("thk_correction", False)),
                    "mode": params.get("mode", "bulge"),
                    "order_number": self.shell_data.get("order_number", ""),
                    "detail_number": params.get("detail_number", ""),
                    "material": params.get("material", "")
                }

                # быстрые проверки параметров (предотвращение тривиальных проблем)
                if nozzle_params["diameter"] <= 0 or nozzle_params["diameter_main"] <= 0:
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": "Invalid diameters for nozzle", "input": nozzle_params,
                                     "cutout_index": idx}
                    })
                    continue
                if nozzle_params["thickness"] <= 0 or nozzle_params["length"] <= 0:
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": "Invalid height/thickness for nozzle", "input": nozzle_params,
                                     "cutout_index": idx}
                    })
                    continue
                if nozzle_params["thickness"] * 2 >= nozzle_params["diameter"]:
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": "Thickness too large relative to diameter", "input": nozzle_params,
                                     "cutout_index": idx}
                    })
                    continue

                # защита по offset относительно R
                R_nozzle = nozzle_params["diameter_main"] / 2.0
                if abs(nozzle_params["offset"]) > R_nozzle:
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": f"Offset {nozzle_params['offset']} > R {R_nozzle} — invalid for unroll", "cutout_index": idx}
                    })
                    continue

                # вызов at_nozzle с защитой от исключений и от не-dict результат
                try:
                    nozzle_info = at_nozzle(nozzle_params)
                except Exception as e:
                    tb = traceback.format_exc()
                    # Добавляем детальный трейсбек в результат — это поможет локализовать math domain error
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {
                            "error": "Exception during at_nozzle",
                            "exception": str(e),
                            "traceback": tb,
                            "input": nozzle_params,
                            "cutout_index": idx
                        }
                    })
                    # критическая ошибка — показываем всплывающее сообщение
                    show_popup(loc.get("build_error").format(str(e)), popup_type="error")
                    continue

                # Если модуль вернул не dict — фиксируем и продолжаем
                if not isinstance(nozzle_info, dict):
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": f"at_nozzle returned non-dict ({type(nozzle_info).__name__})", "value": nozzle_info, "input": nozzle_params, "cutout_index": idx}
                    })
                    continue

                # Проверяем поле success
                if not nozzle_info.get("success", False):
                    err = nozzle_info.get("error", "unknown nozzle error")
                    self.result["entities"].append({
                        "type": "nozzle",
                        "outline": [],
                        "metadata": {"error": err, "input": nozzle_params, "cutout_index": idx}
                    })
                    continue

                # Вставляем успешную развёртку отвода
                self.result["entities"].append({
                    "type": "nozzle",
                    "outline": nozzle_info.get("outline", []),
                    "metadata": {**nozzle_info.get("metadata", {}), "cutout_index": idx}
                })

                # Добавляем входные данные в metadata
                self.result["metadata"].setdefault("input_data", self.shell_data)
                return self.result

        except Exception as e:
        # Внешняя ошибка: фиксируем и возвращаем результат с типом 'error'
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
    test_shell_data = {
        "diameter": 219.1,
        "length": 265,
        "insert_point": [0, 0, 0],
        "angle": 270,
        "clockwise": False,
        "order_number": "20366-2",
        "detail_number": "1",
        "material": "1.4301",
        "thickness": 3.0,
        "weld_allowance_top": 10,
        "weld_allowance_bottom": 2,
        "axis": True,
        "axis_marks": 10.0,
        "layer_name": "0",
        # Можно задать per_nozzle_gap для изменения расстояния между развёртками
        "per_nozzle_gap": 350.0,
        "cutouts": [
            {
                "angle_deg": 0,
                "offset_axial": 130,
                "axial_shift": 0.0,
                "params": {
                    "diameter": 168.3,
                    "thickness": 3.0,
                    "height": 225,
                    "angle_deg": 0.0,
                    "contact_mode": "A",
                    "text": "N1",
                    "steps": 360,
                    "layer_name": "0",
                    "unroll_branch": True,
                    "flange_present": False,
                    "weld_allowance": 3.0,
                    "mode": "polyline",
                    "material": "1.4301"
                }
            },
            # {
            #     "angle_deg": 180,
            #     "offset_axial": 500,
            #     "axial_shift": 0.0,
            #     "params": {
            #         "diameter": 88.9,
            #         "thickness": 3.0,
            #         "height": 300.0,
            #         "angle_deg": 0.0,
            #         "contact_mode": "D",
            #         "text": "N2",
            #         "steps": 180,
            #         "layer_name": "0",
            #         "unroll_branch": True,
            #         "flange_present": False,
            #         "weld_allowance": 3.0,
            #         "mode": "polyline",
            #         "material": "1.4301"
            #     }
            # },
            # {
            #     "angle_deg": 270,
            #     "offset_axial": 300,
            #     "axial_shift": 0.0,
            #     "params": {
            #         "diameter": 60.3,
            #         "thickness": 3.0,
            #         "height": 250.0,
            #         "angle_deg": 0.0,
            #         "contact_mode": "D",
            #         "text": "N3",
            #         "steps": 180,
            #         "layer_name": "0",
            #         "unroll_branch": True,
            #         "flange_present": False,
            #         "weld_allowance": 3.0,
            #         "mode": "polyline",
            #         "material": "1.4404"
            #     }
            # }
        ]
    }
    # Тест для at_cylinder
    result = at_cylinder(test_shell_data)

