# -*- coding: utf-8 -*-
"""
Файл: at_gui_utils.py
Путь: windows/at_gui_utils.py

Описание:
    Модуль GUI-утилит приложения AT-CAD.
    Содержит:
        show_popup()        — универсальное всплывающее окно с иконкой и кнопками
        get_standard_font() — базовый шрифт интерфейса из настроек пользователя

Зависимости:
    config.at_config          — get_setting(), DEFAULT_SETTINGS, DONE_ICON_PATH
    locales.at_translations   — loc (глобальный экземпляр Localization)
    wxPython                  — GUI-фреймворк

Особенности:
    - show_popup() безопасно создаёт wx.App если он ещё не инициализирован,
      сохраняя ссылку в модульной переменной (_wx_app_ref) для предотвращения
      сборки мусора.
    - Все настройки шрифта защищены fallback-значениями из DEFAULT_SETTINGS,
      чтобы ни один None из get_setting() не вызвал AttributeError или ValueError.
    - Поддерживается тип "warning" (иконка ART_WARNING).
"""

from __future__ import annotations

import os
from typing import List, Optional

import wx

from config.at_config import DEFAULT_SETTINGS, DONE_ICON_PATH, get_setting
# ИСПРАВЛЕНО: импорт из at_translations (новый модуль с register_translations),
# а не из at_localization_class (старый модуль без этого метода).
from locales.at_translations import loc

# ============================================================
# ЛОКАЛИЗАЦИЯ МОДУЛЯ
# ============================================================

TRANSLATIONS = {
    "warning": {"ru": "Предупреждение", "de": "Warnung",     "en": "Warning"},
    "error":   {"ru": "Ошибка",         "de": "Fehler",      "en": "Error"},
    "success": {"ru": "Удачно",         "de": "Erfolg",      "en": "Success"},
    "info":    {"ru": "Информация",     "de": "Information", "en": "Information"},
}
loc.register_translations(TRANSLATIONS)

# ============================================================
# МОДУЛЬНАЯ ССЫЛКА НА wx.App
#
# wx требует ровно один экземпляр wx.App на процесс.
# Если show_popup() вызывается из модуля, где wx.App ещё не создан
# (например, при прямом запуске скрипта), мы создаём его здесь
# и держим ссылку в модульной переменной, чтобы сборщик мусора
# не уничтожил его до ShowModal(). Без этой ссылки wx.App,
# созданный внутри функции, может быть уничтожен немедленно.
# ============================================================

_wx_app_ref: Optional[wx.App] = None


def _ensure_wx_app() -> None:
    """
    Гарантирует существование wx.App перед любыми wx-вызовами.
    Вызывается в начале show_popup() и get_standard_font().
    Если wx.App уже создан (например, главным окном приложения) — ничего не делает.
    """
    global _wx_app_ref
    if wx.GetApp() is None:
        _wx_app_ref = wx.App(False)


# ============================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ШРИФТА
# ============================================================

def _resolve_font_params() -> tuple[str, int, wx.FontStyle, wx.FontWeight]:
    """
    Читает параметры шрифта из настроек пользователя с fallback на DEFAULT_SETTINGS.

    Возвращает:
        (face_name, size, style, weight) — готово для передачи в wx.Font()

    Защита от None:
        get_setting() может вернуть None если ключ отсутствует в user_settings.json.
        Каждый параметр защищён оператором or с DEFAULT_SETTINGS.
    """
    font_name: str = get_setting("FONT_NAME") or DEFAULT_SETTINGS["FONT_NAME"]
    font_type: str = (get_setting("FONT_TYPE") or DEFAULT_SETTINGS["FONT_TYPE"]).lower()

    # Защита от нечислового значения в FONT_SIZE
    try:
        font_size: int = int(get_setting("FONT_SIZE") or DEFAULT_SETTINGS["FONT_SIZE"])
    except (ValueError, TypeError):
        font_size = int(DEFAULT_SETTINGS["FONT_SIZE"])

    # Полная таблица стилей включая bolditalic
    font_styles: dict[str, tuple[wx.FontStyle, wx.FontWeight]] = {
        "normal":     (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
        "italic":     (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL),
        "bold":       (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
        "bolditalic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD),
    }
    style, weight = font_styles.get(font_type, (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

    return font_name, font_size, style, weight


# ============================================================
# ПУБЛИЧНЫЙ API
# ============================================================

def show_popup(
        message: str,
        title: Optional[str] = None,
        popup_type: str = "info",
        icon_size: int = 32,
        buttons: Optional[List[str]] = None,
) -> int:
    """
    Показывает модальное всплывающее окно с иконкой, сообщением и кнопками.

    Параметры:
        message    — текст сообщения (поддерживает переносы \\n)
        title      — заголовок окна; если None — берётся из локализации
                     в соответствии с popup_type
        popup_type — тип окна: "error" | "success" | "info" | "warning"
                     Определяет иконку и заголовок по умолчанию.
        icon_size  — размер иконки в пикселях (масштабируется при необходимости)
        buttons    — список кнопок: ["OK"] | ["OK", "Cancel"] и т.д.
                     По умолчанию: ["OK"]

    Возвращает:
        1 — пользователь нажал OK
        0 — пользователь нажал Cancel или закрыл окно

    Пример:
        result = show_popup("Точка не выбрана.", popup_type="warning")
        result = show_popup("Удалить объект?", buttons=["OK", "Cancel"])
    """
    _ensure_wx_app()

    if buttons is None:
        buttons = ["OK"]

    # Заголовки по умолчанию для каждого типа
    default_titles: dict[str, str] = {
        "error":   loc.get("error",   "Ошибка"),
        "success": loc.get("success", "Успех"),
        "info":    loc.get("info",    "Информация"),
        "warning": loc.get("warning", "Предупреждение"),
    }
    resolved_title = title or default_titles.get(popup_type.lower(), loc.get("error", "Ошибка"))

    # ── Диалоговое окно ──
    dialog = wx.Dialog(None, title=resolved_title, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dialog.SetMinSize(wx.Size(300, 150))

    # ── Иконка ──
    icon_bitmap = _resolve_icon_bitmap(dialog, popup_type, icon_size)

    # ── Шрифт ──
    font_name, font_size, style, weight = _resolve_font_params()
    font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, style, weight, faceName=font_name)

    # ── Макет ──
    main_sizer = wx.BoxSizer(wx.VERTICAL)

    h_sizer = wx.BoxSizer(wx.HORIZONTAL)
    h_sizer.AddSpacer(10)

    icon_ctrl = wx.StaticBitmap(dialog, bitmap=icon_bitmap)
    h_sizer.Add(icon_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

    label = wx.StaticText(dialog, label=message)
    label.SetFont(font)
    label.Wrap(250)
    h_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

    main_sizer.AddStretchSpacer()
    main_sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 10)
    main_sizer.AddStretchSpacer()

    # ── Кнопки ──
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    button_id_map: dict[str, int] = {
        "OK":     wx.ID_OK,
        "Cancel": wx.ID_CANCEL,
    }
    for btn_text in buttons:
        btn_id = button_id_map.get(btn_text, wx.ID_OK)
        btn = wx.Button(dialog, id=btn_id, label=btn_text)
        btn.SetFont(font)
        button_sizer.Add(btn, 0, wx.ALL, 5)

    main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

    dialog.SetSizer(main_sizer)
    dialog.Fit()
    dialog.Centre()

    result = dialog.ShowModal()
    dialog.Destroy()

    return 1 if result == wx.ID_OK else 0


def get_standard_font() -> wx.Font:
    """
    Возвращает базовый шрифт интерфейса из настроек пользователя.

    Используется для заголовков, label'ов, статусной строки и большинства
    текстовых элементов интерфейса AT-CAD.

    Настройки (user_settings.json):
        FONT_NAME      — имя гарнитуры (например, "Arial")
        FONT_TYPE      — стиль: normal | italic | bold | bolditalic
        FONT_SIZE      — размер в пунктах (целое число)

    Если параметр отсутствует в user_settings.json — используется
    значение из DEFAULT_SETTINGS (защита от KeyError и None).

    Возвращает:
        wx.Font, готовый к использованию в SetFont()

    Примечание:
        Требует активного wx.App. Если wx.App ещё не создан —
        создаётся автоматически через _ensure_wx_app().
    """
    _ensure_wx_app()

    font_name, font_size, style, weight = _resolve_font_params()
    return wx.Font(font_size, wx.FONTFAMILY_DEFAULT, style, weight, faceName=font_name)


# ============================================================
# ВНУТРЕННИЕ ФУНКЦИИ ИКОНОК
# ============================================================

def _resolve_icon_bitmap(
        dialog: wx.Dialog,
        popup_type: str,
        icon_size: int,
) -> wx.Bitmap:
    """
    Возвращает wx.Bitmap для иконки диалога в соответствии с popup_type.

    Для типа "success" пытается загрузить кастомную иконку из DONE_ICON_PATH.
    При любой ошибке загрузки автоматически падает в fallback — ART_INFORMATION.

    Для остальных типов используются системные иконки wxArtProvider:
        "error"   → ART_ERROR
        "warning" → ART_WARNING
        "info"    → ART_INFORMATION
        (любой другой) → ART_INFORMATION

    Параметры:
        dialog     — родительский wx.Dialog (нужен для SetIcon)
        popup_type — тип окна (определяет иконку)
        icon_size  — размер иконки в пикселях

    Возвращает:
        wx.Bitmap — всегда возвращает валидный bitmap (никогда не None)
    """
    ptype = popup_type.lower()

    if ptype == "success":
        return _load_custom_icon(dialog, icon_size)

    art_map: dict[str, str] = {
        "error":   wx.ART_ERROR,
        "warning": wx.ART_WARNING,
        "info":    wx.ART_INFORMATION,
    }
    art_id = art_map.get(ptype, wx.ART_INFORMATION)

    icon = wx.ArtProvider.GetIcon(art_id, wx.ART_MESSAGE_BOX, wx.Size(16, 16))
    dialog.SetIcon(icon)

    return wx.ArtProvider.GetBitmap(art_id, wx.ART_MESSAGE_BOX, wx.Size(icon_size, icon_size))


def _load_custom_icon(dialog: wx.Dialog, icon_size: int) -> wx.Bitmap:
    """
    Загружает кастомную иконку успеха из DONE_ICON_PATH.

    Путь вычисляется относительно расположения этого файла:
        <project_root> / DONE_ICON_PATH

    При любой ошибке (файл отсутствует, битый формат, wx-исключение)
    возвращает стандартную системную иконку ART_INFORMATION.

    Параметры:
        dialog    — родительский wx.Dialog для SetIcon
        icon_size — целевой размер масштабирования в пикселях

    Возвращает:
        wx.Bitmap — кастомный или системный fallback
    """
    fallback_art = wx.ART_INFORMATION

    try:
        # Путь к иконке: два уровня вверх от windows/ → корень проекта
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(project_root, DONE_ICON_PATH)

        icon_bitmap = wx.Bitmap(icon_path, wx.BITMAP_TYPE_ANY)

        if not icon_bitmap.IsOk():
            raise ValueError(f"Bitmap невалиден: {icon_path}")

        # Устанавливаем иконку окна (16×16 — стандарт для заголовка)
        dialog.SetIcon(wx.Icon(icon_bitmap))

        # Масштабируем до нужного размера если отличается
        if icon_bitmap.GetWidth() != icon_size or icon_bitmap.GetHeight() != icon_size:
            image = icon_bitmap.ConvertToImage()
            image = image.Scale(icon_size, icon_size, wx.IMAGE_QUALITY_HIGH)
            icon_bitmap = wx.Bitmap(image)

        return icon_bitmap

    except (RuntimeError, ValueError, OSError):
        # Любая ошибка загрузки — возвращаем системный fallback
        icon = wx.ArtProvider.GetIcon(fallback_art, wx.ART_MESSAGE_BOX, wx.Size(16, 16))
        dialog.SetIcon(icon)
        return wx.ArtProvider.GetBitmap(fallback_art, wx.ART_MESSAGE_BOX, wx.Size(icon_size, icon_size))


# ============================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================

if __name__ == "__main__":
    _app = wx.App(False)   # явный wx.App для __main__

    print("=== Тест at_gui_utils.py ===")

    # Тест 1: все типы окон
    for test_ptype in ("info", "success", "warning", "error"):
        print(f"  Показываем popup: {test_ptype}")
        test_result = show_popup(
            message=f"Тестовое сообщение\nТип: {test_ptype}",
            popup_type=test_ptype,
        )
        print(f"    Результат: {test_result}")

    # Тест 2: окно с двумя кнопками
    print("  Показываем popup с кнопками OK / Cancel...")
    test_result = show_popup(
        message="Вы хотите продолжить?",
        title="Подтверждение",
        popup_type="info",
        buttons=["OK", "Cancel"],
    )
    print(f"    Результат: {'OK' if test_result == 1 else 'Cancel'}")

    # Тест 3: get_standard_font
    print("  Тест get_standard_font()...")
    test_font = get_standard_font()
    print(f"    Шрифт: {test_font.GetFaceName()}, {test_font.GetPointSize()}pt")

    print("=== Тест завершён ===")