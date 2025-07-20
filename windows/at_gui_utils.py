"""
Файл: at_gui_utils.py
Путь: windows\at_gui_utils.py

Описание:
Модуль с утилитами для создания графического интерфейса в приложении AT-CAD.
Содержит функцию show_popup для отображения всплывающих окон с сообщениями.
Использует настройки шрифтов из user_settings.json через get_setting и пути
к изображениям из at_config.py.
"""

from config.at_config import get_setting, IMAGES_DIR, DONE_ICON_PATH
from locales.at_localization_class import loc
import wx
import os

def show_popup(message: str, title: str = None, popup_type: str = "error", icon_size: int = 32,
               buttons: list = ["OK"]) -> int:
    """
    Показывает всплывающее окно с сообщением.

    Args:
        message: Текст сообщения.
        title: Заголовок окна (если None, используется локализованный заголовок).
        popup_type: Тип окна ("error", "success", "info").
        icon_size: Размер иконки в пикселях.
        buttons: Список кнопок ("OK", "Cancel").

    Returns:
        int: Код возврата (1 для OK, 0 для Cancel).
    """
    # Создание приложения wxPython, если оно еще не инициализировано
    app = wx.App(False) if wx.GetApp() is None else None

    # Установка заголовка по умолчанию
    default_titles = {
        "error": loc.get("error", "Ошибка"),
        "success": loc.get("success", "Успех"),
        "info": loc.get("info", "Информация")
    }
    title = title or default_titles.get(popup_type.lower(), loc.get("error", "Ошибка"))

    # Инициализация диалогового окна
    dialog = wx.Dialog(None, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
    dialog.SetMinSize((300, 150))

    # Выбор иконки
    if popup_type.lower() == "success":
        try:
            icon_bitmap = wx.Bitmap(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DONE_ICON_PATH), wx.BITMAP_TYPE_ANY)
            if not icon_bitmap.IsOk():
                raise ValueError(loc.get("image_not_found"))
            icon = wx.Icon(icon_bitmap)
            dialog.SetIcon(icon)
            if icon_size != icon_bitmap.GetWidth():
                image = icon_bitmap.ConvertToImage()
                scaled_image = image.Scale(icon_size, icon_size, wx.IMAGE_QUALITY_HIGH)
                icon_bitmap = wx.Bitmap(scaled_image)
        except Exception:
            # Использование стандартной иконки при ошибке
            art_id = wx.ART_INFORMATION
            icon = wx.ArtProvider.GetIcon(art_id, wx.ART_MESSAGE_BOX, (16, 16))
            dialog.SetIcon(icon)
            icon_bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_MESSAGE_BOX, (icon_size, icon_size))
    else:
        icon_map = {
            "error": wx.ART_ERROR,
            "info": wx.ART_INFORMATION
        }
        art_id = icon_map.get(popup_type.lower(), wx.ART_ERROR)
        icon = wx.ArtProvider.GetIcon(art_id, wx.ART_MESSAGE_BOX, (16, 16))
        dialog.SetIcon(icon)
        icon_bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_MESSAGE_BOX, (icon_size, icon_size))

    # Настройка шрифта
    font_styles = {
        "italic": (wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL),
        "bold": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
        "normal": (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
    }
    style, weight = font_styles.get(get_setting("FONT_TYPE").lower(), (wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    font = wx.Font(int(get_setting("FONT_SIZE")), wx.FONTFAMILY_DEFAULT, style, weight, faceName=get_setting("FONT_NAME"))

    # Макет окна
    main_sizer = wx.BoxSizer(wx.VERTICAL)
    h_sizer = wx.BoxSizer(wx.HORIZONTAL)
    h_sizer.AddSpacer(10)

    # Иконка
    icon_ctrl = wx.StaticBitmap(dialog, bitmap=icon_bitmap)
    h_sizer.Add(icon_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

    # Текст сообщения
    label = wx.StaticText(dialog, label=message)
    label.SetFont(font)
    label.Wrap(250)
    h_sizer.Add(label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

    main_sizer.AddStretchSpacer()
    main_sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 10)
    main_sizer.AddStretchSpacer()

    # Кнопки
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    button_map = {
        "OK": wx.ID_OK,
        "Cancel": wx.ID_CANCEL
    }

    for btn_text in buttons:
        button = wx.Button(dialog, id=button_map.get(btn_text, wx.ID_OK))
        button.SetFont(font)
        button_sizer.Add(button, 0, wx.ALL, 5)

    main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

    # Применение макета
    dialog.SetSizer(main_sizer)
    dialog.Fit()
    dialog.Centre()

    # Отображение диалога и возврат результата
    result = dialog.ShowModal()
    dialog.Destroy()

    return 1 if result == wx.ID_OK else 0
