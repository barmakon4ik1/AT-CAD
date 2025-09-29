"""
programs/at_addhead.py
Модуль для построения днища в AutoCAD.
Создаёт внутреннюю и внешнюю полилинии днища на основе заданных параметров.
Поддерживает локализацию, логирование и интеграцию с ATCadInit.
"""

import math
import logging
from typing import Tuple, List, Optional, Dict
import wx
from config.at_cad_init import ATCadInit
from programs.at_base import layer_context, ensure_layer
from programs.at_geometry import at_bulge
from windows.at_window_utils import show_popup
from locales.at_translations import loc

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True  # Принудительное пересоздание обработчика логов
)
logging.info("Логирование инициализировано в at_addhead.py")
logging.getLogger().handlers[0].flush()

# Локальные переводы модуля
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "heads_error": {
        "ru": "Ошибка построения днища",
        "de": "Fehler beim Erstellen des Kopfes",
        "en": "Error building head"
    },
    "regen_error": {
        "ru": "Ошибка регенерации чертежа",
        "de": "Fehler bei der Zeichnungsregenerierung",
        "en": "Error regenerating drawing"
    },
    "invalid_parameters": {
        "ru": "Недопустимые параметры для построения днища",
        "de": "Ungültige Parameter für den Kopfaufbau",
        "en": "Invalid parameters for head construction"
    }
}
# Регистрируем переводы
loc.register_translations(TRANSLATIONS)

# Слой по умолчанию
DEFAULT_LAYER = "0"


def add_polyline(model: object, points: List[float], layer_name: str) -> Optional[object]:
    """
    Создаёт полилинию в AutoCAD.

    Args:
        model: Модельное пространство AutoCAD.
        points: Список координат [x1, y1, x2, y2, ...].
        layer_name: Имя слоя.

    Returns:
        Optional[object]: Объект полилинии AutoCAD или None при ошибке.
    """
    try:
        import pythoncom
        from win32com.client import VARIANT
        # Проверка корректности координат
        if not points or len(points) % 2 != 0:
            raise ValueError(f"Некорректный список координат: {points}")
        for coord in points:
            if not isinstance(coord, (int, float)) or math.isnan(coord) or math.isinf(coord):
                raise ValueError(f"Некорректная координата: {coord}")
        # Преобразование в VARIANT
        points_variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, points)
        poly = model.AddLightWeightPolyline(points_variant)
        poly.Closed = True
        poly.Layer = layer_name
        logging.info(f"Полилиния создана на слое {layer_name} с координатами: {points}")
        return poly
    except Exception as e:
        logging.error(f"Ошибка при создании полилинии на слое {layer_name}: {e}")
        logging.error(f"Переданные координаты: {points}")
        logging.getLogger().handlers[0].flush()
        return None

def create_polyline(model: object, points: List[Tuple[float, float]],
                    bulge_data: List[Tuple[int, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]]],
                    layer_name: str) -> Optional[object]:
    """
    Создаёт полилинию с заданными точками и коэффициентами выпуклости.

    Args:
        model: Модельное пространство AutoCAD.
        points: Список точек полилинии [(x1, y1), (x2, y2), ...].
        bulge_data: Список кортежей (индекс, (начальная_точка, конечная_точка, центр)).
        layer_name: Имя слоя.

    Returns:
        Optional[object]: Объект полилинии или None при ошибке.
    """
    try:
        points_list = [coord for point in points for coord in point]
        poly = add_polyline(model, points_list, layer_name)
        if poly is None:
            logging.error(f"Не удалось создать полилинию на слое {layer_name}")
            if wx.GetApp() is not None:
                show_popup(loc.get("polyline_error", "Ошибка при создании полилинии"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return None
        for idx, (start, end, center) in bulge_data:
            bulge = at_bulge(start, end, center)
            poly.SetBulge(idx, bulge)
            logging.info(f"Установлен коэффициент выпуклости {bulge:.4f} для индекса {idx}")
        logging.info(f"Полилиния успешно создана на слое {layer_name}")
        return poly
    except Exception as e:
        logging.error(f"Ошибка при создании полилинии: {e}")
        if wx.GetApp() is not None:
            show_popup(loc.get("heads_error", "Ошибка построения днища") + f": {str(e)}", popup_type="error")
        else:
            logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
        logging.getLogger().handlers[0].flush()
        return None


def main(data: Dict) -> bool:
    """
    Строит днище в AutoCAD на основе данных из словаря.

    Args:
        data: Словарь с параметрами:
            - D: Диаметр днища (float).
            - s: Толщина материала (float).
            - R: Большой радиус (float).
            - r: Малый радиус (float).
            - h1: Высота днища (float).
            - insert_point: Точка вставки (list[float]).
            - layer: Имя слоя (str).

    Returns:
        bool: True, если построение успешно, иначе False.
    """
    try:
        logging.info(f"Начало построения днища с параметрами: {data}")
        logging.getLogger().handlers[0].flush()

        # Проверка входных параметров
        required_keys = ["D", "s", "h1", "R", "r", "insert_point", "layer"]
        if not all(key in data for key in required_keys):
            logging.error(f"Отсутствуют необходимые параметры: {required_keys}")
            if wx.GetApp() is not None:
                show_popup(loc.get("invalid_parameters", "Недопустимые параметры для построения днища"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return False

        D = float(data["D"])
        s = float(data["s"])
        h1 = float(data["h1"])
        R = float(data["R"])
        r = float(data["r"])
        insert_point = data["insert_point"]
        layer = data["layer"] if data["layer"] else DEFAULT_LAYER

        if any(param <= 0 for param in [D, s, h1, R, r]):
            logging.error(f"Параметры должны быть положительными: D={D}, s={s}, h1={h1}, R={R}, r={r}")
            if wx.GetApp() is not None:
                show_popup(loc.get("invalid_parameters", "Недопустимые параметры для построения днища"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return False

        if not (isinstance(insert_point, list) and len(insert_point) == 3):
            logging.error(f"Некорректная точка вставки: {insert_point}")
            if wx.GetApp() is not None:
                show_popup(loc.get("invalid_parameters", "Недопустимые параметры для построения днища"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return False

        # Инициализация AutoCAD
        cad = ATCadInit()
        adoc = cad.document
        model = cad.model_space
        if adoc is None:
            logging.error("Не удалось инициализировать AutoCAD")
            if wx.GetApp() is not None:
                show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return False

        # Вычисление координат
        x0, y0 = 0.0, 0.0
        b = 0.5 * D - s
        bs = 0.5 * D
        R1 = R - r
        Rs = R + s
        h = h1

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

        # Смещение точек, если задана точка вставки
        x0, y0 = float(insert_point[0]), float(insert_point[1])
        points = {k: [p[0] + x0, p[1] + y0] for k, p in points.items()}

        # Построение полилиний
        with layer_context(adoc, layer):
            ensure_layer(adoc, layer)
            logging.info(f"Создание полилиний на слое {layer}")

            # Внутренняя полилиния
            inner_points = (
                points["p1"], points["p4"], points["p8"],
                points["p12"], points["p14"], points["p17"], points["p1"]
            )
            inner_bulge_data = [
                (1, (points["p4"], points["p8"], points["p5"])),
                (2, (points["p8"], points["p12"], points["p18"])),
                (3, (points["p12"], points["p14"], points["p13"]))
            ]
            inner_poly = create_polyline(model, inner_points, inner_bulge_data, layer)
            if not inner_poly:
                logging.error("Не удалось создать внутреннюю полилинию")
                return False

            # Внешняя полилиния
            outer_points = (
                points["p2"], points["p3"], points["p9"],
                points["p11"], points["p15"], points["p16"], points["p2"]
            )
            outer_bulge_data = [
                (1, (points["p3"], points["p9"], points["p5"])),
                (2, (points["p9"], points["p11"], points["p18"])),
                (3, (points["p11"], points["p15"], points["p13"]))
            ]
            outer_poly = create_polyline(model, outer_points, outer_bulge_data, layer)
            if not outer_poly:
                logging.error("Не удалось создать внешнюю полилинию")
                return False

        # Регенерация чертежа
        try:
            adoc.Regen(1)  # acActiveViewport
            logging.info("Чертеж успешно регенерирован")
        except Exception as e:
            logging.error(f"Ошибка регенерации чертежа: {e}")
            if wx.GetApp() is not None:
                show_popup(loc.get("regen_error", "Ошибка регенерации чертежа"), popup_type="error")
            else:
                logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
            logging.getLogger().handlers[0].flush()
            return False

        logging.info("Днище успешно построено")
        logging.getLogger().handlers[0].flush()
        return True

    except Exception as e:
        logging.error(f"Ошибка в main: {e}")
        if wx.GetApp() is not None:
            show_popup(loc.get("heads_error", "Ошибка построения днища") + f": {str(e)}", popup_type="error")
        else:
            logging.warning("Не удалось показать всплывающее окно: wx.App не инициализирован")
        logging.getLogger().handlers[0].flush()
        return False


if __name__ == "__main__":
    """
    Тестирование построения днища с тестовыми параметрами.
    """
    import wx
    app = wx.App(False)  # Инициализация wx.App
    test_data = {
        "D": 1000.0,
        "s": 5.0,
        "h1": 20.0,
        "R": 1000.0,
        "r": 100.0,
        "insert_point": [0.0, 0.0, 0.0],
        "layer": "0"
    }
    success = main(test_data)
    print(f"Результат построения: {'Успешно' if success else 'Ошибка'}")
    app.MainLoop()
