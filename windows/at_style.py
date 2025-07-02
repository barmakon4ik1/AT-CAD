
"""
Модуль для применения стилей к элементам интерфейса в проекте AT-CAD.
Содержит функции для стилизации виджетов wxWidgets с использованием настроек из at_config.
"""

import wx
from config.at_config import (
    FONT_NAME,
    FONT_TYPE,
    FONT_SIZE,
    FOREGROUND_COLOR,
)


def style_textctrl(ctrl: wx.TextCtrl) -> None:
    """
    Применяет стиль к текстовому полю (wx.TextCtrl).

    Args:
        ctrl: Текстовое поле для стилизации.
    """
    font_style = {
        "normal": wx.FONTSTYLE_NORMAL,
        "italic": wx.FONTSTYLE_ITALIC,
        "bold": wx.FONTSTYLE_NORMAL,
        "bolditalic": wx.FONTSTYLE_ITALIC,
    }
    font_weight = {
        "normal": wx.FONTWEIGHT_NORMAL,
        "italic": wx.FONTWEIGHT_NORMAL,
        "bold": wx.FONTWEIGHT_BOLD,
        "bolditalic": wx.FONTWEIGHT_BOLD,
    }
    font = wx.Font(
        FONT_SIZE,
        wx.FONTFAMILY_DEFAULT,
        font_style.get(FONT_TYPE, wx.FONTSTYLE_NORMAL),
        font_weight.get(FONT_TYPE, wx.FONTWEIGHT_NORMAL),
        faceName=FONT_NAME if FONT_NAME else "Times New Roman",
    )
    ctrl.SetFont(font)


def style_combobox(combo: wx.ComboBox) -> None:
    """
    Применяет стиль к выпадающему списку (wx.ComboBox).

    Args:
        combo: Выпадающий список для стилизации.
    """
    font_style = {
        "normal": wx.FONTSTYLE_NORMAL,
        "italic": wx.FONTSTYLE_ITALIC,
        "bold": wx.FONTSTYLE_NORMAL,
        "bolditalic": wx.FONTSTYLE_ITALIC,
    }
    font_weight = {
        "normal": wx.FONTWEIGHT_NORMAL,
        "italic": wx.FONTWEIGHT_NORMAL,
        "bold": wx.FONTWEIGHT_BOLD,
        "bolditalic": wx.FONTWEIGHT_BOLD,
    }
    font = wx.Font(
        FONT_SIZE,
        wx.FONTFAMILY_DEFAULT,
        font_style.get(FONT_TYPE, wx.FONTSTYLE_NORMAL),
        font_weight.get(FONT_TYPE, wx.FONTWEIGHT_NORMAL),
        faceName=FONT_NAME if FONT_NAME else "Times New Roman",
    )
    combo.SetFont(font)


def style_radiobutton(radio: wx.RadioButton) -> None:
    """
    Применяет стиль к радиокнопке (wx.RadioButton).

    Args:
        radio: Радиокнопка для стилизации.
    """
    font_style = {
        "normal": wx.FONTSTYLE_NORMAL,
        "italic": wx.FONTSTYLE_ITALIC,
        "bold": wx.FONTSTYLE_NORMAL,
        "bolditalic": wx.FONTSTYLE_ITALIC,
    }
    font_weight = {
        "normal": wx.FONTWEIGHT_NORMAL,
        "italic": wx.FONTWEIGHT_NORMAL,
        "bold": wx.FONTWEIGHT_BOLD,
        "bolditalic": wx.FONTWEIGHT_BOLD,
    }
    font = wx.Font(
        FONT_SIZE,
        wx.FONTFAMILY_DEFAULT,
        font_style.get(FONT_TYPE, wx.FONTSTYLE_NORMAL),
        font_weight.get(FONT_TYPE, wx.FONTWEIGHT_NORMAL),
        faceName=FONT_NAME if FONT_NAME else "Times New Roman",
    )
    radio.SetFont(font)


def style_staticbox(box: wx.StaticBox) -> None:
    """
    Применяет стиль к статическому контейнеру (wx.StaticBox).

    Args:
        box: Контейнер для стилизации.
    """
    font_style = {
        "normal": wx.FONTSTYLE_NORMAL,
        "italic": wx.FONTSTYLE_ITALIC,
        "bold": wx.FONTSTYLE_NORMAL,
        "bolditalic": wx.FONTSTYLE_ITALIC,
    }
    font_weight = {
        "normal": wx.FONTWEIGHT_NORMAL,
        "italic": wx.FONTWEIGHT_NORMAL,
        "bold": wx.FONTWEIGHT_BOLD,
        "bolditalic": wx.FONTWEIGHT_BOLD,
    }
    font = wx.Font(
        FONT_SIZE,
        wx.FONTFAMILY_DEFAULT,
        font_style.get(FONT_TYPE, wx.FONTSTYLE_NORMAL),
        font_weight.get(FONT_TYPE, wx.FONTWEIGHT_NORMAL),
        faceName=FONT_NAME if FONT_NAME else "Times New Roman",
    )
    box.SetFont(font)
    box.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))


def style_label(label: wx.StaticText) -> None:
    """
    Применяет стиль к метке (wx.StaticText).

    Args:
        label: Метка для стилизации.
    """
    font = wx.Font(FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
    font.SetFaceName(FONT_NAME if FONT_NAME else "Times New Roman")
    label.SetFont(font)
    label.SetForegroundColour(wx.Colour(FOREGROUND_COLOR))
