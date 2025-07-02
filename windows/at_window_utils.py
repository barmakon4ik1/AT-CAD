"""
Модуль с утилитами для главного окна AT-CAD.

Содержит функции для работы с позицией окна, всплывающими окнами, шрифтами и стилизацией интерфейса.
"""

import os
import json
import logging
from typing import Tuple, Dict
import wx
from config.at_config import FONT_NAME, FONT_TYPE, FONT_SIZE, BACKGROUND_COLOR
from locales.at_localization import loc
from windows.at_style import style_textctrl, style_combobox, style_radiobutton, style_staticbox


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_last_position() -> Tuple[int, int]:
    """
    Загружает координаты последней позиции окна из файла 'config/last_position.json'.

    Returns:
        Tuple[int, int]: Координаты окна (x, y) или (-1, -1) при ошибке или отсутствии файла.
    """
    config_path = os.path.join("config", "last_position.json")
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            return (data.get("x", -1), data.get("y", -1))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {config_path}: {e}")
        return (-1, -1)


def save_last_position(x: int, y: int) -> None:
    """
    Сохраняет координаты позиции окна в файл 'config/last_position.json'.

    Args:
        x: Координата x окна.
        y: Координата y окна.
    """
    config_path = os.path.join("config", "last_position.json")
    try:
        with open(config_path, "w") as f:
            json.dump({"x": x, "y": y}, f, indent=2)
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {config_path}: {e}")


def load_common_data() -> Dict:
    """
    Загружает данные о материалах, толщинах и конфигурации днищ из файлов 'common_data.json' и 'config.json'.

    Returns:
        Dict: Словарь с ключами 'material', 'thicknesses', 'h1_table', 'head_types', 'fields'.
              Возвращает пустые значения при ошибке.
    """
    result = {"material": [], "thicknesses": [], "h1_table": {}, "head_types": {}, "fields": [{}]}
    try:
        with open("common_data.json", "r") as f:
            data = json.load(f)
            if not isinstance(data.get("dimensions"), dict):
                raise ValueError("Некорректная структура common_data.json")
            dimensions = data.get("dimensions", {})
            result["material"] = dimensions.get("material", []) if isinstance(dimensions.get("material"), list) else []
            result["thicknesses"] = dimensions.get("thicknesses", []) if isinstance(dimensions.get("thicknesses"), list) else []
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error(f"Ошибка загрузки common_data.json: {e}")
        show_popup(loc.get("config_file_missing", "common_data.json"), popup_type="error")

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            result["h1_table"] = config.get("h1_table", {}) if isinstance(config.get("h1_table"), dict) else {}
            result["head_types"] = config.get("head_types", {}) if isinstance(config.get("head_types"), dict) else {}
            result["fields"] = config.get("fields", [{}]) if isinstance(config.get("fields"), list) else [{}]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки config.json: {e}")
        show_popup(loc.get("config_file_missing", "config.json"), popup_type="error")

    return result


def load_last_input(filename: str) -> Dict:
    """
    Загружает последние введённые данные из указанного файла.

    Args:
        filename: Имя файла для загрузки (например, 'last_cone_input.json').

    Returns:
        Dict: Словарь с данными или пустой словарь при ошибке.
    """
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Ошибка загрузки {filename}: {e}")
        return {}


def save_last_input(filename: str, data: Dict) -> None:
    """
    Сохраняет введённые данные в указанный файл.

    Args:
        filename: Имя файла для сохранения.
        data: Словарь с данными.
    """
    try:
        with open(filename, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (PermissionError, OSError) as e:
        logging.error(f"Ошибка сохранения {filename}: {e}")


def show_popup(message: str, popup_type: str = "info") -> None:
    """
    Отображает всплывающее окно с сообщением.

    Args:
        message: Текст сообщения.
        popup_type: Тип сообщения ("info" для информационного, "error" для ошибки).
    """
    style = wx.OK | (wx.ICON_INFORMATION if popup_type == "info" else wx.ICON_ERROR)
    wx.MessageBox(message, loc.get("error" if popup_type == "error" else "info"), style)


def get_standard_font() -> wx.Font:
    """
    Возвращает стандартный шрифт на основе конфигурации.

    Returns:
        wx.Font: Объект шрифта с заданным размером, стилем и именем.
    """
    font_name = FONT_NAME if FONT_NAME else "Times New Roman"
    font_styles = {
        "normal": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
        "italic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL),
        "bold": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
        "bolditalic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD),
    }
    style, weight = font_styles.get(FONT_TYPE.lower(), (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    return wx.Font(FONT_SIZE, wx.FONTFAMILY_DEFAULT, style, weight, faceName=font_name)


def get_button_font() -> wx.Font:
    """
    Возвращает шрифт для кнопок (на 2 пункта больше стандартного).

    Returns:
        wx.Font: Объект шрифта для кнопок.
    """
    font = get_standard_font()
    font.SetPointSize(FONT_SIZE + 2)
    return font


def fit_text_to_height(ctrl, text, max_width, max_height, font_name, style_flags):
    """
    Подбирает наибольший размер шрифта, при котором текст помещается по высоте.
    """
    font_size = 48  # начнем с большого размера
    min_size = 8

    while font_size >= min_size:
        font = wx.Font(
            font_size,
            wx.FONTFAMILY_DEFAULT,
            style_flags.get("style", wx.FONTSTYLE_NORMAL),
            style_flags.get("weight", wx.FONTWEIGHT_NORMAL),
            faceName=font_name,
        )
        ctrl.SetFont(font)
        ctrl.SetLabel(text)
        ctrl.Wrap(max_width)

        dc = wx.ClientDC(ctrl)
        dc.SetFont(font)
        _, text_height = dc.GetMultiLineTextExtent(ctrl.GetLabel())

        if text_height <= max_height:
            return font_size  # нашли подходящий размер

        font_size -= 1  # уменьшаем и пробуем снова

    return min_size  # минимально допустимый