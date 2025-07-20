"""
Файл: at_settings_window.py
Путь: E:\\AT-CAD\\windows\\at_settings_window.py

Описание:
Окно настроек приложения AT-CAD. Позволяет изменять шрифт, стиль шрифта, размер шрифта,
цвета интерфейса и другие параметры. Сохраняет настройки в user_settings.json.
"""

import wx
from config.at_config import load_user_settings, save_user_settings, DEFAULT_SETTINGS
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
import logging


class SettingsWindow(wx.Dialog):
    """
    Класс окна настроек приложения AT-CAD.

    Атрибуты:
        parent (wx.Frame): Родительское окно (ATMainWindow).
        settings (dict): Текущие настройки, загруженные из user_settings.json.
        font_name_combo (wx.ComboBox): Выбор названия шрифта.
        font_type_combo (wx.ComboBox): Выбор стиля шрифта.
        font_size_spin (wx.SpinCtrl): Выбор размера шрифта.
        label_font_name_combo (wx.ComboBox): Выбор названия шрифта для меток.
        label_font_type_combo (wx.ComboBox): Выбор стиля шрифта для меток.
        label_font_weight_combo (wx.ComboBox): Выбор веса шрифта для меток.
        label_font_size_spin (wx.SpinCtrl): Выбор размера шрифта для меток.
        bg_color_button (wx.Button): Кнопка выбора цвета фона.
        fg_color_button (wx.Button): Кнопка выбора цвета текста.
        banner_color_button (wx.Button): Кнопка выбора цвета баннера.
        banner_text_color_button (wx.Button): Кнопка выбора цвета текста баннера.
        exit_button_color_button (wx.Button): Кнопка выбора цвета кнопки выхода.
        status_text_color_button (wx.Button): Кнопка выбора цвета текста статуса.
        label_font_color_button (wx.Button): Кнопка выбора цвета шрифта меток.
        button_font_color_button (wx.Button): Кнопка выбора цвета шрифта кнопок.
    """
    def __init__(self, parent):
        """
        Инициализирует окно настроек.

        Аргументы:
            parent (wx.Frame): Родительское окно (ATMainWindow).
        """
        super().__init__(parent, title=loc.get("settings_title", "Настройки"), size=(400, 750))
        self.parent = parent
        self.settings = load_user_settings()
        self.init_ui()
        self.Centre()

    def init_ui(self) -> None:
        """
        Инициализирует пользовательский интерфейс окна настроек.
        """
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Шрифт
        font_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, label=loc.get("font_settings", "Настройки шрифта")),
                                       wx.VERTICAL)

        # Название шрифта
        font_name_label = wx.StaticText(panel, label=loc.get("font_name", "Название шрифта"))
        self.font_name_combo = wx.ComboBox(panel, value=self.settings["FONT_NAME"],
                                           choices=wx.FontEnumerator.GetFacenames(), style=wx.CB_READONLY)
        font_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        font_name_sizer.Add(font_name_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        font_name_sizer.Add(self.font_name_combo, 1, wx.ALL | wx.EXPAND, 5)
        font_sizer.Add(font_name_sizer, 0, wx.EXPAND)

        # Стиль шрифта
        font_type_label = wx.StaticText(panel, label=loc.get("font_type", "Стиль шрифта"))
        self.font_type_combo = wx.ComboBox(panel, value=self.settings["FONT_TYPE"],
                                           choices=["normal", "italic", "bold", "bolditalic"], style=wx.CB_READONLY)
        font_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        font_type_sizer.Add(font_type_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        font_type_sizer.Add(self.font_type_combo, 1, wx.ALL | wx.EXPAND, 5)
        font_sizer.Add(font_type_sizer, 0, wx.EXPAND)

        # Размер шрифта
        font_size_label = wx.StaticText(panel, label=loc.get("font_size", "Размер шрифта"))
        self.font_size_spin = wx.SpinCtrl(panel, value=str(self.settings["FONT_SIZE"]), min=8, max=72)
        font_size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        font_size_sizer.Add(font_size_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        font_size_sizer.Add(self.font_size_spin, 1, wx.ALL | wx.EXPAND, 5)
        font_sizer.Add(font_size_sizer, 0, wx.EXPAND)

        sizer.Add(font_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Шрифт меток
        label_font_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, label=loc.get("label_font_settings", "Настройки шрифта меток")),
                                             wx.VERTICAL)

        # Название шрифта меток
        label_font_name_label = wx.StaticText(panel, label=loc.get("label_font_name", "Название шрифта меток"))
        self.label_font_name_combo = wx.ComboBox(panel, value=self.settings["LABEL_FONT_NAME"],
                                                 choices=wx.FontEnumerator.GetFacenames(), style=wx.CB_READONLY)
        label_font_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_font_name_sizer.Add(label_font_name_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        label_font_name_sizer.Add(self.label_font_name_combo, 1, wx.ALL | wx.EXPAND, 5)
        label_font_sizer.Add(label_font_name_sizer, 0, wx.EXPAND)

        # Стиль шрифта меток
        label_font_type_label = wx.StaticText(panel, label=loc.get("label_font_type", "Стиль шрифта меток"))
        self.label_font_type_combo = wx.ComboBox(panel, value=self.settings["LABEL_FONT_TYPE"],
                                                 choices=["normal", "italic", "bold", "bolditalic"], style=wx.CB_READONLY)
        label_font_type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_font_type_sizer.Add(label_font_type_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        label_font_type_sizer.Add(self.label_font_type_combo, 1, wx.ALL | wx.EXPAND, 5)
        label_font_sizer.Add(label_font_type_sizer, 0, wx.EXPAND)

        # Вес шрифта меток
        label_font_weight_label = wx.StaticText(panel, label=loc.get("label_font_weight", "Вес шрифта меток"))
        self.label_font_weight_combo = wx.ComboBox(panel, value=self.settings["LABEL_FONT_WEIGHT"],
                                                  choices=["normal", "bold"], style=wx.CB_READONLY)
        label_font_weight_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_font_weight_sizer.Add(label_font_weight_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        label_font_weight_sizer.Add(self.label_font_weight_combo, 1, wx.ALL | wx.EXPAND, 5)
        label_font_sizer.Add(label_font_weight_sizer, 0, wx.EXPAND)

        # Размер шрифта меток
        label_font_size_label = wx.StaticText(panel, label=loc.get("label_font_size", "Размер шрифта меток"))
        self.label_font_size_spin = wx.SpinCtrl(panel, value=str(self.settings["LABEL_FONT_SIZE"]), min=8, max=72)
        label_font_size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_font_size_sizer.Add(label_font_size_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        label_font_size_sizer.Add(self.label_font_size_spin, 1, wx.ALL | wx.EXPAND, 5)
        label_font_sizer.Add(label_font_size_sizer, 0, wx.EXPAND)

        sizer.Add(label_font_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Цвета
        color_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, label=loc.get("color_settings", "Настройки цвета")),
                                        wx.VERTICAL)

        # Цвет фона
        bg_color_label = wx.StaticText(panel, label=loc.get("background_color", "Цвет фона"))
        self.bg_color_button = wx.Button(panel, label=self.settings["BACKGROUND_COLOR"])
        self.bg_color_button.SetBackgroundColour(wx.Colour(self.settings["BACKGROUND_COLOR"]))
        self.bg_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "BACKGROUND_COLOR"))
        bg_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bg_color_sizer.Add(bg_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        bg_color_sizer.Add(self.bg_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(bg_color_sizer, 0, wx.EXPAND)

        # Цвет текста
        fg_color_label = wx.StaticText(panel, label=loc.get("foreground_color", "Цвет текста"))
        self.fg_color_button = wx.Button(panel, label=self.settings["FOREGROUND_COLOR"])
        self.fg_color_button.SetBackgroundColour(wx.Colour(self.settings["FOREGROUND_COLOR"]))
        self.fg_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "FOREGROUND_COLOR"))
        fg_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        fg_color_sizer.Add(fg_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        fg_color_sizer.Add(self.fg_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(fg_color_sizer, 0, wx.EXPAND)

        # Цвет баннера
        banner_color_label = wx.StaticText(panel, label=loc.get("banner_color", "Цвет баннера"))
        self.banner_color_button = wx.Button(panel, label=self.settings["BANNER_COLOR"])
        self.banner_color_button.SetBackgroundColour(wx.Colour(self.settings["BANNER_COLOR"]))
        self.banner_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "BANNER_COLOR"))
        banner_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        banner_color_sizer.Add(banner_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        banner_color_sizer.Add(self.banner_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(banner_color_sizer, 0, wx.EXPAND)

        # Цвет текста баннера
        banner_text_color_label = wx.StaticText(panel, label=loc.get("banner_text_color", "Цвет текста баннера"))
        self.banner_text_color_button = wx.Button(panel, label=self.settings["BANNER_TEXT_COLOR"])
        self.banner_text_color_button.SetBackgroundColour(wx.Colour(self.settings["BANNER_TEXT_COLOR"]))
        self.banner_text_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "BANNER_TEXT_COLOR"))
        banner_text_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        banner_text_color_sizer.Add(banner_text_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        banner_text_color_sizer.Add(self.banner_text_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(banner_text_color_sizer, 0, wx.EXPAND)

        # Цвет кнопки выхода
        exit_button_color_label = wx.StaticText(panel, label=loc.get("exit_button_color", "Цвет кнопки выхода"))
        self.exit_button_color_button = wx.Button(panel, label=self.settings["EXIT_BUTTON_COLOR"])
        self.exit_button_color_button.SetBackgroundColour(wx.Colour(self.settings["EXIT_BUTTON_COLOR"]))
        self.exit_button_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "EXIT_BUTTON_COLOR"))
        exit_button_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        exit_button_color_sizer.Add(exit_button_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        exit_button_color_sizer.Add(self.exit_button_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(exit_button_color_sizer, 0, wx.EXPAND)

        # Цвет текста статуса
        status_text_color_label = wx.StaticText(panel, label=loc.get("status_text_color", "Цвет текста статуса"))
        self.status_text_color_button = wx.Button(panel, label=self.settings["STATUS_TEXT_COLOR"])
        self.status_text_color_button.SetBackgroundColour(wx.Colour(self.settings["STATUS_TEXT_COLOR"]))
        self.status_text_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "STATUS_TEXT_COLOR"))
        status_text_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        status_text_color_sizer.Add(status_text_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        status_text_color_sizer.Add(self.status_text_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(status_text_color_sizer, 0, wx.EXPAND)

        # Цвет шрифта меток
        label_font_color_label = wx.StaticText(panel, label=loc.get("label_font_color", "Цвет шрифта меток"))
        self.label_font_color_button = wx.Button(panel, label=self.settings["LABEL_FONT_COLOR"])
        self.label_font_color_button.SetBackgroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))
        self.label_font_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "LABEL_FONT_COLOR"))
        label_font_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label_font_color_sizer.Add(label_font_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        label_font_color_sizer.Add(self.label_font_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(label_font_color_sizer, 0, wx.EXPAND)

        # Цвет шрифта кнопок
        button_font_color_label = wx.StaticText(panel, label=loc.get("button_font_color", "Цвет шрифта кнопок"))
        self.button_font_color_button = wx.Button(panel, label=self.settings["BUTTON_FONT_COLOR"])
        self.button_font_color_button.SetBackgroundColour(wx.Colour(self.settings["BUTTON_FONT_COLOR"]))
        self.button_font_color_button.Bind(wx.EVT_BUTTON, lambda evt: self.on_choose_color(evt, "BUTTON_FONT_COLOR"))
        button_font_color_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_font_color_sizer.Add(button_font_color_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        button_font_color_sizer.Add(self.button_font_color_button, 1, wx.ALL | wx.EXPAND, 5)
        color_sizer.Add(button_font_color_sizer, 0, wx.EXPAND)

        sizer.Add(color_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Кнопки
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_button = wx.Button(panel, label=loc.get("save", "Сохранить"))
        save_button.Bind(wx.EVT_BUTTON, self.on_save)
        reset_button = wx.Button(panel, label=loc.get("reset_to_default", "Сбросить настройки"))
        reset_button.Bind(wx.EVT_BUTTON, self.on_reset)
        cancel_button = wx.Button(panel, label=loc.get("cancel", "Отмена"))
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        button_sizer.Add(save_button, 0, wx.ALL, 5)
        button_sizer.Add(reset_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)
        panel.Layout()

    def on_choose_color(self, event, color_key: str) -> None:
        """
        Открывает диалог выбора цвета и обновляет соответствующую настройку.

        Аргументы:
            event: Событие кнопки.
            color_key (str): Ключ настройки цвета (например, "BACKGROUND_COLOR").
        """
        color_data = wx.ColourData()
        color_data.SetColour(wx.Colour(self.settings[color_key]))
        dialog = wx.ColourDialog(self, color_data)
        if dialog.ShowModal() == wx.ID_OK:
            color = dialog.GetColourData().GetColour()
            self.settings[color_key] = color.GetAsString(wx.C2S_HTML_SYNTAX)
            button = event.GetEventObject()
            button.SetLabel(self.settings[color_key])
            button.SetBackgroundColour(color)
            button.Refresh()
        dialog.Destroy()

    def on_save(self, event) -> None:
        """
        Сохраняет настройки и обновляет интерфейс главного окна.
        """
        self.settings["FONT_NAME"] = self.font_name_combo.GetValue()
        self.settings["FONT_TYPE"] = self.font_type_combo.GetValue()
        self.settings["FONT_SIZE"] = self.font_size_spin.GetValue()
        self.settings["LABEL_FONT_NAME"] = self.label_font_name_combo.GetValue()
        self.settings["LABEL_FONT_TYPE"] = self.label_font_type_combo.GetValue()
        self.settings["LABEL_FONT_WEIGHT"] = self.label_font_weight_combo.GetValue()
        self.settings["LABEL_FONT_SIZE"] = self.label_font_size_spin.GetValue()
        self.settings["BACKGROUND_COLOR"] = self.bg_color_button.GetLabel()
        self.settings["FOREGROUND_COLOR"] = self.fg_color_button.GetLabel()
        self.settings["BANNER_COLOR"] = self.banner_color_button.GetLabel()
        self.settings["BANNER_TEXT_COLOR"] = self.banner_text_color_button.GetLabel()
        self.settings["EXIT_BUTTON_COLOR"] = self.exit_button_color_button.GetLabel()
        self.settings["STATUS_TEXT_COLOR"] = self.status_text_color_button.GetLabel()
        self.settings["LABEL_FONT_COLOR"] = self.label_font_color_button.GetLabel()
        self.settings["BUTTON_FONT_COLOR"] = self.button_font_color_button.GetLabel()
        save_user_settings(self.settings)
        logging.info(f"Настройки сохранены: {self.settings}")
        # Передаём настройки в родительское окно для обновления UI
        self.parent.update_ui(self.settings)
        show_popup(loc.get("settings_saved", "Настройки сохранены"), popup_type="info")
        self.EndModal(wx.ID_OK)

    def on_reset(self, event) -> None:
        """
        Сбрасывает настройки на значения по умолчанию и обновляет интерфейс главного окна.
        """
        self.settings = DEFAULT_SETTINGS.copy()
        save_user_settings(self.settings)
        logging.info(f"Настройки сброшены: {self.settings}")
        # Передаём настройки в родительское окно для обновления UI
        self.parent.update_ui(self.settings)
        show_popup(loc.get("settings_reset", "Настройки сброшены"), popup_type="info")
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event) -> None:
        """
        Закрывает окно настроек без сохранения изменений.
        """
        self.EndModal(wx.ID_CANCEL)
