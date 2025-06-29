# at_main_window.py
"""
Модуль главного окна программы AT-CAD.
Содержит основное окно с меню, ссылками на программы и кнопкой выхода.
"""

import wx
import os
import logging
import traceback
from typing import Optional, Dict, Callable
from at_cone_input_window import ConeInputWindow
from at_shell_input_window import ShellInputWindow
from at_ringe_window import RingInputWindow
from at_head_input_window import HeadInputWindow
from at_window_utils import create_window, show_popup, get_button_font
from at_localization import loc
import at_config
from at_run_cone import run_application
from at_window_utils import apply_styles_to_panel

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename="at_cad.log",
                    format="%(asctime)s - %(levelname)s - %(message)s")


class MainWindow(wx.Frame):
    """
    Главное окно программы AT-CAD.
    Содержит меню, ссылки на программы, строку статуса и кнопку выхода.
    """

    def __init__(self, parent=None):
        """
        Инициализирует окно с фиксированным размером и элементами.

        Args:
            parent: Родительское окно (по умолчанию None).
        """
        super().__init__(parent, title="AT-CAD", style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        self.panel = wx.Panel(self)

        # Установка иконки приложения
        icon_path = at_config.ICON_PATH
        if os.path.exists(icon_path):
            icon_bitmap = wx.Bitmap(icon_path, wx.BITMAP_TYPE_PNG)
            if icon_bitmap.IsOk():
                icon_bitmap = self.scale_bitmap(icon_bitmap, 32, 32)
                icon = wx.Icon()
                icon.CopyFromBitmap(icon_bitmap)
                self.SetIcon(icon)
            else:
                logging.error(f"Ошибка: файл иконки '{icon_path}' повреждён!")
        else:
            logging.error(f"Ошибка: файл иконки '{icon_path}' не найден!")

        # Фиксированный размер окна
        self.SetSize((800, 600))
        self.SetMinSize((800, 600))
        self.SetMaxSize((800, 600))

        # Панель
        self.panel.SetBackgroundColour(wx.Colour(at_config.BACKGROUND_COLOR))

        # Создаём меню
        self._create_menu()

        # Внешний вертикальный сайзер
        self.outer_sizer = wx.BoxSizer(wx.VERTICAL)

        # Заголовок (баннер с логотипом и иконкой языка)
        self.header_panel, self.header_sizer = self._create_header()
        self.outer_sizer.Add(self.header_panel, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)

        # Основной контент сайзер
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Ссылки на программы
        self.links_sizer = self._create_program_links()
        self.main_sizer.Add(self.links_sizer, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопка выхода
        self.exit_sizer = self._create_exit_button()
        self.main_sizer.Add(self.exit_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        # Добавляем основной контент внутрь внешнего сайзера
        self.outer_sizer.Add(self.main_sizer, 1, wx.EXPAND)

        # Текст копирайта
        self.copyright_label = wx.StaticText(self.panel, label=loc.get("copyright"))
        self.copyright_label.SetForegroundColour(wx.Colour(at_config.FOREGROUND_COLOR))
        self.copyright_label.SetFont(wx.Font(8, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        copyright_sizer = wx.BoxSizer(wx.HORIZONTAL)
        copyright_sizer.AddStretchSpacer()
        copyright_sizer.Add(self.copyright_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.outer_sizer.Add(copyright_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

        # Установка сайзера
        self.panel.SetSizer(self.outer_sizer)
        self.panel.Layout()
        self.Centre()

        # Статусная строка
        self.CreateStatusBar()
        self.GetStatusBar().SetFieldsCount(1)
        self.GetStatusBar().SetStatusText("")
        self.GetStatusBar().SetBackgroundColour(wx.Colour(at_config.BANNER_COLOR))

        # Применение стилей
        apply_styles_to_panel(self.panel)
        logging.info("Интерфейс главного окна успешно настроен")

        # Обработчик закрытия окна
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def scale_bitmap(self, bitmap: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
        """
        Масштабирует изображение с сохранением пропорций.

        Args:
            bitmap: wx.Bitmap для масштабирования.
            width: Целевая ширина.
            height: Целевая высота.

        Returns:
            wx.Bitmap: Масштабированное изображение.
        """
        image = bitmap.ConvertToImage()
        image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    def _create_header(self) -> tuple[wx.Panel, wx.BoxSizer]:
        """
        Создаёт заголовок с логотипом, названием и иконкой языка.

        Returns:
            tuple[wx.Panel, wx.BoxSizer]: Панель заголовка и её сайзер.
        """
        header_panel = wx.Panel(self.panel)
        header_panel.SetBackgroundColour(wx.Colour(at_config.BANNER_COLOR))
        sizer_header = wx.BoxSizer(wx.HORIZONTAL)

        logo_path = at_config.ICON_PATH
        logo_bitmap = wx.Bitmap(logo_path, wx.BITMAP_TYPE_PNG) if os.path.exists(logo_path) else wx.NullBitmap
        if logo_bitmap.IsOk():
            logo_bitmap = self.scale_bitmap(logo_bitmap, 100, 100)
        else:
            logging.error(f"Ошибка: файл логотипа '{logo_path}' не найден или повреждён!")
        self.logo = wx.StaticBitmap(header_panel, bitmap=logo_bitmap)
        self.logo.SetMinSize((100, 100))
        sizer_header.Add(self.logo, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        sizer_header.AddStretchSpacer()

        self.title = wx.StaticText(header_panel, label="AT-Metal Unfold Pro System", style=wx.ALIGN_CENTER)
        self.title.SetForegroundColour(wx.Colour(at_config.BANNER_TEXT_COLOR))
        self.title.SetFont(wx.Font(24, wx.DEFAULT, wx.NORMAL, wx.BOLD))
        sizer_header.Add(self.title, 0, wx.ALIGN_CENTER_VERTICAL, 0)

        sizer_header.AddStretchSpacer()

        self.language_icon = self._update_language_icon(header_panel)
        self.language_icon.SetMinSize((64, 64))
        self.language_icon.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
        sizer_header.Add(self.language_icon, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        header_panel.SetSizer(sizer_header)
        header_panel.Layout()
        logging.info("Заголовок успешно создан")
        return header_panel, sizer_header

    def _update_language_icon(self, parent: wx.Window) -> wx.StaticBitmap:
        """
        Создаёт или обновляет иконку языка в зависимости от текущего loc.language.

        Args:
            parent: Родительский элемент для wx.StaticBitmap.

        Returns:
            wx.StaticBitmap: Иконка языка или заглушка, если файл не найден.
        """
        language_file = at_config.LANGUAGE_ICONS.get(loc.language, at_config.LANGUAGE_ICONS["ru"])
        if os.path.exists(language_file):
            bitmap = wx.Bitmap(language_file, wx.BITMAP_TYPE_PNG)
            if bitmap.IsOk():
                bitmap = self.scale_bitmap(bitmap, 64, 64)
            else:
                logging.error(f"Ошибка: файл иконки языка '{language_file}' повреждён!")
                bitmap = wx.NullBitmap
        else:
            logging.error(f"Ошибка: файл иконки языка '{language_file}' не найден!")
            bitmap = wx.NullBitmap
        return wx.StaticBitmap(parent, bitmap=bitmap)

    def _get_language_bitmap(self) -> wx.Bitmap:
        """
        Возвращает масштабированный битмап для текущего языка.

        Returns:
            wx.Bitmap: Масштабированный битмап иконки языка или заглушка.
        """
        language_file = at_config.LANGUAGE_ICONS.get(loc.language, at_config.LANGUAGE_ICONS["ru"])
        if os.path.exists(language_file):
            bitmap = wx.Bitmap(language_file, wx.BITMAP_TYPE_PNG)
            if bitmap.IsOk():
                bitmap = self.scale_bitmap(bitmap, 64, 64)
                logging.info(f"Иконка языка '{language_file}' успешно загружена")
            else:
                logging.error(f"Ошибка: файл иконки языка '{language_file}' повреждён!")
                bitmap = wx.NullBitmap
        else:
            logging.error(f"Ошибка: файл иконки языка '{language_file}' не найден!")
            bitmap = wx.NullBitmap
        return bitmap

    def _create_menu(self) -> None:
        """
        Создаёт строку меню с пунктом "О программе".
        """
        menu_bar = wx.MenuBar()
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, loc.get("menu_about"))
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        menu_bar.Append(help_menu, loc.get("menu_help"))
        self.SetMenuBar(menu_bar)
        logging.info("Меню успешно создано")

    def _create_program_links(self) -> wx.BoxSizer:
        """
        Создаёт ссылки на модули программ в один столбец, выровненные по левому краю.

        Returns:
            wx.BoxSizer: Сайзер с ссылками на программы.
        """
        sizer_links = wx.BoxSizer(wx.VERTICAL)

        programs = [
            (loc.get("at_run_cone"), lambda: run_application()),
            (loc.get("program_shell"), lambda: create_window(ShellInputWindow, parent=self)),
            (loc.get("at_ringe"), lambda: create_window(RingInputWindow, parent=self)),
            (loc.get("at_run_heads"), lambda: create_window(HeadInputWindow, parent=self)),
        ]

        self.link_labels = []
        for label, callback in programs:
            link = wx.StaticText(self.panel, label=label)
            link.SetFont(wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.BOLD))
            link.SetForegroundColour(wx.Colour(at_config.FOREGROUND_COLOR))
            link.Bind(wx.EVT_LEFT_DOWN, lambda evt, cb=callback: self.on_program_link(evt, cb))
            sizer_links.Add(link, 0, wx.ALIGN_LEFT | wx.LEFT | wx.TOP, 10)
            self.link_labels.append(link)

        logging.info("Ссылки на программы успешно созданы")
        return sizer_links

    def _create_exit_button(self) -> wx.BoxSizer:
        """
        Создаёт кнопку выхода, аналогичную кнопке "Отмена" из at_window_utils.py.

        Returns:
            wx.BoxSizer: Сайзер с кнопкой выхода.
        """
        self.exit_button = wx.Button(self.panel, label=loc.get("button_exit"))
        button_font = get_button_font()
        self.exit_button.SetFont(button_font)
        self.exit_button.SetBackgroundColour(wx.Colour(at_config.EXIT_BUTTON_COLOR))
        self.exit_button.SetForegroundColour(wx.Colour("white"))
        self.exit_button.Bind(wx.EVT_BUTTON, self.on_exit)

        # Рассчитываем максимальную ширину кнопки для всех языков
        max_width = 0
        languages = ['ru', 'de', 'en']
        for lang in languages:
            temp_loc = loc.__class__(lang)
            label = temp_loc.get("button_exit")
            dc = wx.ClientDC(self.exit_button)
            dc.SetFont(button_font)
            width, _ = dc.GetTextExtent(label)
            max_width = max(max_width, width + 20)
        self.exit_button.SetMinSize((max_width, 30))  # Фиксированная высота

        sizer_bottom = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bottom.AddStretchSpacer()
        sizer_bottom.Add(self.exit_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 10)
        logging.info("Кнопка выхода успешно создана")
        return sizer_bottom

    def on_program_link(self, event: wx.Event, callback: Callable) -> Optional[Dict]:
        """
        Обрабатывает запуск дочернего окна или программы.

        Args:
            event: Событие нажатия на ссылку.
            callback: Функция, вызывающая программу или окно.

        Returns:
            Optional[Dict]: Результат выполнения, если применимо.
        """
        was_iconized = self.IsIconized()
        self.Iconize(False)
        self.Raise()
        result = callback()  # Вызываем run_application или create_window
        if result is False:  # Если run_application вернула False (нажата "Отмена")
            self.GetStatusBar().SetStatusText(loc.get("operation_cancelled"))
        elif result is True:  # Если run_application вернула True (успех или ошибка с продолжением)
            self.GetStatusBar().SetStatusText(loc.get("operation_completed"))
        if was_iconized:
            self.Iconize(True)
        else:
            self.Iconize(False)
        self.Raise()
        self.SetFocus()
        return None  # run_application возвращает bool, поэтому возвращаем None

    def on_change_language(self, event: wx.Event) -> None:
        """
        Обрабатывает смену языка интерфейса.

        Args:
            event: Событие нажатия на иконку языка (wx.EVT_LEFT_DOWN).
        """
        try:
            current_langs = ["ru", "de", "en"]
            current_index = current_langs.index(loc.language) if loc.language in current_langs else 0
            new_index = (current_index + 1) % len(current_langs)
            new_lang = current_langs[new_index]
            logging.info(f"Смена языка на: {new_lang}")
            at_config.set_language(new_lang)
            logging.info(f"После set_language, at_config.LANGUAGE: {at_config.LANGUAGE}, loc.language: {loc.language}")
            self._refresh_ui()
        except Exception as e:
            logging.error(f"Ошибка при смене языка: {e}")
            show_popup(loc.get("language_change_error", str(e)), popup_type="error")
            traceback.print_exc()

    def _refresh_ui(self) -> None:
        """
        Обновляет элементы интерфейса после смены языка.
        """
        try:
            logging.info("Начало обновления UI")
            # Обновление заголовка
            self.title.SetLabel("AT-Metal Unfold Pro System")
            # Обновление иконки языка
            self.language_icon.SetBitmap(self._get_language_bitmap())

            # Обновление ссылок на программы
            programs = [
                loc.get("at_run_cone"),
                loc.get("program_shell"),
                loc.get("at_ringe"),
                loc.get("at_run_heads"),
            ]
            for link, label in zip(self.link_labels, programs):
                link.SetLabel(label)

            # Обновление кнопки выхода
            self.exit_button.SetLabel(loc.get("button_exit"))
            self.exit_button.SetBackgroundColour(wx.Colour(at_config.EXIT_BUTTON_COLOR))
            self.exit_button.SetForegroundColour(wx.Colour("white"))

            # Обновление текста копирайта
            self.copyright_label.SetLabel(loc.get("copyright"))
            self.copyright_label.SetForegroundColour(wx.Colour(at_config.FOREGROUND_COLOR))

            # Обновление меню
            self.SetMenuBar(None)
            self._create_menu()

            self.panel.Layout()
            self.Refresh()
            self.Update()
            logging.info("UI успешно обновлено")
        except Exception as e:
            logging.error(f"Ошибка обновления UI: {e}")
            show_popup(loc.get("ui_refresh_error", str(e)), popup_type="error")
            traceback.print_exc()

    def on_about(self, event: wx.Event) -> None:
        """
        Отображает информацию о программе.

        Args:
            event: Событие меню (wx.EVT_MENU).
        """
        about_info = loc.get("about_text")
        show_popup(about_info, popup_type="info")

    def on_exit(self, event: wx.Event) -> None:
        """
        Закрывает программу.

        Args:
            event: Событие кнопки (wx.EVT_BUTTON).
        """
        self.Close(True)

    def on_close(self, event: wx.Event) -> None:
        """
        Обрабатывает закрытие окна.

        Args:
            event: Событие закрытия (wx.EVT_CLOSE).
        """
        self.Destroy()


def main():
    """
    Точка входа в программу.
    """
    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
