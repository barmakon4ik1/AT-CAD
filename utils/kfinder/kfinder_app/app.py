"""
app.py
======

Точка входа основного приложения K-Finder.

Назначение
----------
Этот модуль связывает вместе все основные части проекта:

- загрузку конфигурации из data/config.json;
- настройку логирования;
- создание wx.App;
- создание главного окна KFinderFrame;
- установку иконки приложения;
- запуск главного цикла GUI.

Архитектурно
------------
launcher.py должен быть максимально маленьким и стабильным.
Вся реальная логика запуска вынесена сюда.

Схема запуска:
--------------
launcher.py
    -> from kfinder_app.app import run
    -> run()

Важно
-----
Этот модуль не должен содержать бизнес-логику поиска, индексации
или работу с Excel. Только старт приложения.
"""

from __future__ import annotations

import sys
from pathlib import Path

import wx

from .config import load_config
from .logging_setup import setup_logging, get_logger
from .main_frame import KFinderFrame
from .paths import BASE_DIR
from .texts import TXT


def _set_windows_app_id() -> None:
    """
    Устанавливает AppUserModelID в Windows.

    Это помогает:
    - корректно показывать иконку в панели задач;
    - отделять приложение от других Python/wx-приложений.

    На других ОС ничего не делает.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AT-CAD.kfinder")
    except RuntimeError:
        # Ошибка здесь не критична для запуска приложения.
        pass


def _find_icon_path() -> Path:
    """
    Возвращает путь к иконке приложения.

    По договорённости иконка лежит рядом с launcher.py / exe,
    то есть в BASE_DIR.
    """
    return BASE_DIR / "kfinder.ico"


def _apply_icon(window: wx.TopLevelWindow) -> None:
    """
    Устанавливает иконку окну, если файл иконки найден.
    """
    icon_path = _find_icon_path()
    if not icon_path.is_file():
        return

    try:
        icon = wx.Icon(str(icon_path), wx.BITMAP_TYPE_ICO)
        if icon.IsOk():
            window.SetIcon(icon)
    except RuntimeError:
        # Иконка необязательна для запуска.
        pass


def run() -> None:
    """
    Основной запуск приложения.

    Алгоритм:
    1. Настраивает Windows App ID.
    2. Настраивает логирование.
    3. Загружает конфиг.
    4. Создаёт wx.App.
    5. Создаёт главное окно.
    6. Устанавливает иконку.
    7. Запускает MainLoop().
    """
    _set_windows_app_id()

    setup_logging()
    logger = get_logger()

    try:
        settings = load_config()
    except Exception as e:
        # На этом этапе GUI ещё нет, поэтому поднимаем минимальный wx.App
        # только чтобы показать пользователю понятную ошибку.
        app = wx.App(False)
        wx.MessageBox(
            str(e),
            "Konfigurationsfehler",
            wx.OK | wx.ICON_ERROR,
        )
        return

    try:
        app = wx.App(False)
        app.SetAppDisplayName(TXT["app_title"])
        app.SetVendorName("AT-CAD")

        frame = KFinderFrame(settings)
        _apply_icon(frame)
        frame.Show()

        logger.error("K-Finder gestartet.") if False else None
        app.MainLoop()

    except Exception as e:
        logger.error(f"App start failed: {e}")
        try:
            wx.MessageBox(
                str(e),
                TXT["msg_error"],
                wx.OK | wx.ICON_ERROR,
            )
        except Exception:
            pass
        raise