"""
windows/at_style.py

Модуль стилизации UI-элементов AT-CAD.

Все шрифты и цвета берутся из user_settings.json через get_setting().
Модуль не создаёт шрифты вручную — используется единый источник:
    windows.at_window_utils
"""

import wx
from config.at_config import get_setting, DEFAULT_SETTINGS, FORM_CONFIG
from windows.at_gui_utils import get_standard_font


# ----------------------------------------------------------------------
# Внутренние утилиты
# ----------------------------------------------------------------------

def _get_color(key: str, fallback_key: str | None = None) -> wx.Colour:
    """
    Возвращает wx.Colour по ключу user_settings.
    Если ключ отсутствует — используется fallback или DEFAULT_SETTINGS.
    """
    value = get_setting(key)

    if not value and fallback_key:
        value = get_setting(fallback_key)

    if not value:
        value = DEFAULT_SETTINGS.get(key)

    try:
        return wx.Colour(value)
    except Exception:
        return wx.Colour("black")


# ----------------------------------------------------------------------
# Базовые стили
# ----------------------------------------------------------------------

def apply_base_font(ctrl: wx.Window) -> None:
    """
    Применяет стандартный UI-шрифт к контролу.
    """
    ctrl.SetFont(get_standard_font())


def style_label(label: wx.StaticText) -> None:
    """
    Стилизует wx.StaticText.
    """
    apply_base_font(label)
    label.SetForegroundColour(_get_color("LABEL_FONT_COLOR", "FOREGROUND_COLOR"))


def style_textctrl(ctrl: wx.TextCtrl) -> None:
    """
    Стилизует wx.TextCtrl.
    """
    apply_base_font(ctrl)
    ctrl.SetForegroundColour(wx.Colour("black"))
    ctrl.SetBackgroundColour(FORM_CONFIG["field_bg_color"])


def style_combobox(combo: wx.ComboBox) -> None:
    """
    Стилизует wx.ComboBox.
    """
    apply_base_font(combo)
    combo.SetForegroundColour(wx.Colour("black"))
    combo.SetBackgroundColour(FORM_CONFIG["field_bg_color"])


def style_radiobutton(radio: wx.RadioButton) -> None:
    """
    Стилизует wx.RadioButton.
    """
    apply_base_font(radio)
    radio.SetForegroundColour(FORM_CONFIG["field_bg_color"])


def style_staticbox(box: wx.StaticBox) -> None:
    """
    Стилизует wx.StaticBox.
    """
    apply_base_font(box)
    box.SetForegroundColour(_get_color("FOREGROUND_COLOR"))


# ----------------------------------------------------------------------
# Рекурсивное применение стиля
# ----------------------------------------------------------------------

def apply_styles_recursively(window: wx.Window) -> None:
    """
    Рекурсивно применяет стили ко всем дочерним элементам.

    Использовать для:
        - диалогов
        - панелей
        - динамически создаваемых форм
    """

    for child in window.GetChildren():

        if isinstance(child, wx.StaticText):
            style_label(child)

        elif isinstance(child, wx.TextCtrl):
            style_textctrl(child)

        elif isinstance(child, wx.ComboBox):
            style_combobox(child)

        elif isinstance(child, wx.RadioButton):
            style_radiobutton(child)

        elif isinstance(child, wx.StaticBox):
            style_staticbox(child)

        # Рекурсивный обход
        apply_styles_recursively(child)
