"""
ui_style.py
===========

Единый модуль оформления K-Finder в исходном AT-CAD-стиле.

Здесь собраны:
- цветовая схема;
- фабрика GenButton с hover/press-эффектами;
- фабрика StaticBoxSizer в исходном стиле;
- вспомогательные функции открытия файлов/папок.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import wx
from wx.lib.buttons import GenButton


# ============================================================
# Цветовая схема в исходном стиле
# ============================================================

CLR_BG          = "#508050"   # фон главного окна
CLR_BTN_PRIMARY = "#2980b9"   # синий — основное действие
CLR_BTN_OK      = "#27ae60"   # зелёный — открыть/принять
CLR_BTN_WARN    = "#e67e22"   # оранжевый — осторожное действие
CLR_BTN_DANGER  = "#c0392b"   # красный — закрыть/удалить
CLR_BTN_DARK    = "#2c3e50"   # тёмный — нейтральное действие
CLR_TEXT        = "#ffffff"   # белый текст на кнопках
CLR_LABEL       = "#e8f5e9"   # светло-зелёный для меток
CLR_STATUS_OK   = "#ffffff"   # белый — нормальный статус
CLR_STATUS_WARN = "#f9ca74"   # жёлтый — предупреждение
CLR_STATUS_ERR  = "#f08080"   # красный — ошибка
CLR_BOX_FG      = "#c8e6c9"   # цвет заголовка StaticBox
CLR_PLACEHOLDER = "#A0A0A0"   # серый — placeholder в поле ввода
CLR_INPUT_TEXT  = "#1a3a1a"   # тёмно-зелёный — введённый текст


def _darken(c: str, f: float = 0.88) -> str:
    col = wx.Colour(c)
    return "#{:02x}{:02x}{:02x}".format(
        int(col.Red() * f),
        int(col.Green() * f),
        int(col.Blue() * f),
    )


def _lighten(c: str, f: float = 1.08) -> str:
    col = wx.Colour(c)
    return "#{:02x}{:02x}{:02x}".format(
        min(255, int(col.Red() * f)),
        min(255, int(col.Green() * f)),
        min(255, int(col.Blue() * f)),
    )


def make_gen_button(
    parent: wx.Window,
    label: str,
    color: str,
    size: wx.Size = wx.Size(-1, 36),
    font_size: int = 11,
) -> GenButton:
    """
    Создаёт стилизованную GenButton в исходном стиле AT-CAD.

    Особенности:
    - Hover-эффект: чуть светлее при наведении.
    - Press-эффект: чуть темнее при нажатии.
    - Белый жирный шрифт на цветном фоне.
    - После modal-диалогов и Enable/Disable текст остаётся белым.
    """
    btn = GenButton(parent, label=label, size=size)
    btn._base_color = color  # type: ignore[attr-defined]

    btn.SetBackgroundColour(wx.Colour(color))
    btn.SetForegroundColour(wx.Colour(CLR_TEXT))
    btn.SetOwnForegroundColour(wx.Colour(CLR_TEXT))
    btn.SetFont(wx.Font(
        font_size,
        wx.FONTFAMILY_DEFAULT,
        wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_BOLD,
    ))
    btn.SetBezelWidth(1)
    btn.SetUseFocusIndicator(False)

    hover = _lighten(color)
    press = _darken(color)

    def _apply(bg: str) -> None:
        btn.SetBackgroundColour(wx.Colour(bg))
        btn.SetForegroundColour(wx.Colour(CLR_TEXT))
        btn.SetOwnForegroundColour(wx.Colour(CLR_TEXT))
        btn.Refresh()

    def on_enter(e):
        _apply(hover)
        e.Skip()

    def on_leave(e):
        _apply(color)
        e.Skip()

    def on_down(e):
        _apply(press)
        e.Skip()

    def on_up(e):
        _apply(color)
        e.Skip()

    def on_enable_changed(e):
        # После Enable/Disable wx иногда перерисовывает текст своим цветом.
        # Возвращаем белый текст принудительно.
        _apply(color if btn.IsEnabled() else color)
        e.Skip()

    btn.Bind(wx.EVT_ENTER_WINDOW, on_enter)
    btn.Bind(wx.EVT_LEAVE_WINDOW, on_leave)
    btn.Bind(wx.EVT_LEFT_DOWN, on_down)
    btn.Bind(wx.EVT_LEFT_UP, on_up)

    return btn


def static_box_sizer(parent: wx.Window, label: str) -> wx.StaticBoxSizer:
    """
    Создаёт StaticBoxSizer в исходном стиле:
    светло-зелёный жирный заголовок секции.
    """
    box = wx.StaticBox(parent, label=f"  {label}  ")
    box.SetForegroundColour(wx.Colour(CLR_BOX_FG))
    box.SetFont(wx.Font(
        10,
        wx.FONTFAMILY_DEFAULT,
        wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_BOLD,
    ))
    return wx.StaticBoxSizer(box, wx.VERTICAL)


def open_path(path: Path) -> None:
    """Открывает папку или файл через стандартный обработчик Windows."""
    os.startfile(str(path))  # type: ignore[attr-defined]


def show_in_explorer(path: Path) -> None:
    """Открывает папку в Проводнике с выделением файла."""
    subprocess.run(["explorer", "/select,", str(path)], check=False)
