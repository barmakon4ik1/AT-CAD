"""
windows/at_bitmap_utils.py

Утилиты работы с изображениями и иконками AT-CAD.

Назначение
----------
Единый модуль загрузки, масштабирования и конвертации wx.Bitmap.
Все модули проекта, которым нужны иконки (кнопки, матрицы, тулбары),
импортируют функции отсюда — а не дублируют их у себя.

Публичный API
-------------
load_icon(path, size)           — загрузить PNG по абсолютному пути, вернуть wx.Bitmap
load_icon_from_dir(dir, name, size) — загрузить PNG из указанной папки
bmp_to_bundle(bmp)              — wx.Bitmap → wx.BitmapBundle (для BitmapButton)
make_placeholder(size, colour)  — серый placeholder-bitmap (файл не найден)
load_icon_set(directory, files, size) — загрузить словарь {ключ: Bitmap}

Зависимости
-----------
Только stdlib + wxPython. Никаких других модулей AT-CAD намеренно —
чтобы модуль можно было использовать без риска циклических импортов.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import wx

logger = logging.getLogger(__name__)

# Цвет placeholder-а по умолчанию (светло-серый)
_PLACEHOLDER_COLOUR = wx.Colour(220, 220, 220)


# ======================================================================
# Внутренние утилиты
# ======================================================================

def _scale_bitmap(bmp: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
    """
    Масштабирует wx.Bitmap до заданного размера.

    Используется внутри модуля и может вызываться напрямую.
    Аналог scale_bitmap() из at_window_utils, но без зависимости от него —
    чтобы избежать циклического импорта.
    """
    if not bmp.IsOk():
        return bmp
    img = bmp.ConvertToImage()
    img = img.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    return wx.Bitmap(img)


# ======================================================================
# Публичный API
# ======================================================================

def make_placeholder(
    size: tuple[int, int],
    colour: wx.Colour = _PLACEHOLDER_COLOUR,
) -> wx.Bitmap:
    """
    Создаёт пустой bitmap-заглушку заданного размера.

    Используется вместо иконки, если файл не найден.
    Позволяет UI не падать при отсутствии ресурсов (режим разработки без assets).

    Args:
        size:    (ширина, высота) в пикселях.
        colour:  цвет заливки (по умолчанию светло-серый).

    Returns:
        wx.Bitmap
    """
    bmp = wx.Bitmap(size[0], size[1])
    dc = wx.MemoryDC(bmp)
    dc.SetBackground(wx.Brush(colour))
    dc.Clear()
    dc.SelectObject(wx.NullBitmap)
    return bmp


def load_icon(
    path: Union[str, Path],
    size: tuple[int, int],
) -> wx.Bitmap:
    """
    Загружает PNG-иконку по абсолютному пути и масштабирует до size.

    Если файл не существует — возвращает placeholder (без исключения).
    Если файл повреждён или не является изображением — логирует ошибку
    и возвращает placeholder.

    Args:
        path:  полный путь к файлу изображения.
        size:  целевой размер (ширина, высота) в пикселях.

    Returns:
        wx.Bitmap — всегда валидный объект, никогда не None.
    """
    path = Path(path)

    if not path.exists():
        logger.debug("load_icon: файл не найден: %s — возвращаю placeholder", path)
        return make_placeholder(size)

    try:
        bmp = wx.Bitmap(str(path), wx.BITMAP_TYPE_ANY)
        if not bmp.IsOk():
            raise ValueError(f"wx.Bitmap невалиден: {path}")
        return _scale_bitmap(bmp, size[0], size[1])

    except Exception as e:
        logger.warning("load_icon: ошибка загрузки %s: %s", path, e)
        return make_placeholder(size)


def load_icon_from_dir(
    directory: Union[str, Path],
    filename: str,
    size: tuple[int, int],
) -> wx.Bitmap:
    """
    Загружает иконку из указанной папки по имени файла.

    Удобная обёртка над load_icon() для случаев, когда все иконки
    хранятся в одной директории (например, ARROWS_IMAGE_PATH).

    Args:
        directory: папка с иконками.
        filename:  имя файла (например, 'circle.png').
        size:      целевой размер (ширина, высота) в пикселях.

    Returns:
        wx.Bitmap
    """
    return load_icon(Path(directory) / filename, size)


def bmp_to_bundle(bmp: wx.Bitmap) -> wx.BitmapBundle:
    """
    Конвертирует wx.Bitmap → wx.BitmapBundle.

    wx.BitmapBundle требуется для wx.BitmapButton начиная с wxPython 4.1+.
    Использовать везде, где нужна иконка на кнопке.

    Args:
        bmp: исходный wx.Bitmap (должен быть валидным).

    Returns:
        wx.BitmapBundle
    """
    return wx.BitmapBundle.FromBitmap(bmp)


def load_icon_set(
    directory: Union[str, Path],
    files: dict[str, str],
    size: tuple[int, int],
) -> dict[str, wx.Bitmap]:
    """
    Загружает набор иконок из одной директории в словарь.

    Удобно для матриц иконок (например, матрица углов пластины),
    где все иконки хранятся в одной папке и имеют предсказуемые имена.

    Args:
        directory: папка с иконками.
        files:     словарь {ключ: имя_файла}, например {"00": "lt.png"}.
        size:      целевой размер всех иконок (ширина, высота).

    Returns:
        dict[ключ, wx.Bitmap] — каждый bitmap гарантированно валиден.

    Пример:
        bitmaps = load_icon_set(ARROWS_IMAGE_PATH, ICON_FILES, (30, 30))
    """
    directory = Path(directory)
    return {
        key: load_icon(directory / filename, size)
        for key, filename in files.items()
    }
