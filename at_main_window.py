"""
Главное окно приложения AT-CAD.
Содержит меню, баннер, основную область, область кнопок и строку статуса.
"""

import wx
import os
import logging
from config.at_config import ICON_PATH, LANGUAGE, LANGUAGE_ICONS, BANNER_COLOR, BANNER_TEXT_COLOR, set_language, \
    BACKGROUND_COLOR, EXIT_BUTTON_COLOR, BANNER_HIGH, WINDOW_SIZE, LOGO_SIZE, FONT_SIZE
from windows.at_style import style_label
from locales.at_localization import loc
from windows.at_window_utils import load_last_position, save_last_position, apply_styles_to_panel, get_button_font
from windows.at_gui_utils import show_popup
from config.at_cad_init import ATCadInit

# Устанавливаем текущую рабочую директорию в корень проекта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, filename="at_cad.log",
                    format="%(asctime)s - %(levelname)s - %(message)s")


class ATMainWindow(wx.Frame):
    def __init__(self):
        # Инициализируем локализацию
        logging.info(f"Initial language: {loc.language}, program_title: {loc.get('program_title')}")
        super().__init__(parent=None, title=loc.get("program_title"), size=WINDOW_SIZE,
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.SetMinSize(WINDOW_SIZE)
        self.SetMaxSize(WINDOW_SIZE)

        # Создаем главную панель для всего содержимого
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))

        # Инициализация AutoCAD
        # self.cad = ATCadInit()
        # if not self.cad.is_initialized():
        #     show_popup(loc.get("cad_init_error_short"), popup_type="error")
        #     self.Close()
        #     return

        # Отладка: вывод текущей рабочей директории и путей
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info(f"ICON_PATH: {ICON_PATH}")
        logging.info(f"LANGUAGE_ICONS: {LANGUAGE_ICONS}")

        # Устанавливаем иконку приложения
        icon_path = os.path.abspath(ICON_PATH)
        if os.path.exists(icon_path):
            try:
                icon_bitmap = wx.Bitmap(icon_path, wx.BITMAP_TYPE_ANY)
                if icon_bitmap.IsOk():
                    icon_bitmap = self.scale_bitmap(icon_bitmap, 32, 32)
                    self.SetIcon(wx.Icon(icon_bitmap))
                    logging.info(f"App icon loaded: {icon_path}")
                else:
                    logging.error(f"Invalid bitmap for app icon: {icon_path}")
            except Exception as e:
                logging.error(f"Error loading app icon {icon_path}: {e}")
        else:
            logging.error(f"App icon not found: {icon_path}")

        # Загружаем последнее положение окна
        x, y = load_last_position()
        if x != -1 and y != -1:
            self.SetPosition((x, y))
        else:
            self.Centre()

        # Создаем главный сайзер (вертикальный)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Создаем баннер
        self.create_banner()

        # Создаем меню
        self.create_menu()

        # Основная область (контейнер для будущего контента)
        self.content_panel = wx.Panel(self.panel)
        self.content_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.main_sizer.Add(self.content_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        # Область кнопок
        self.button_panel = wx.Panel(self.panel)
        self.button_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.create_exit_button()
        self.button_panel.SetSizer(self.button_sizer)
        self.main_sizer.Add(self.button_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Строка статуса и копирайт
        self.create_status_bar()

        # Устанавливаем сайзер для панели
        self.panel.SetSizer(self.main_sizer)
        self.panel.Layout()

        # Применяем стили ко всем элементам
        apply_styles_to_panel(self.panel)

        # Привязываем обработчик закрытия окна для сохранения позиции
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
        if bitmap.IsOk():
            image = bitmap.ConvertToImage()
            image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(image)
        return bitmap

    def create_banner(self):
        """Создает баннер с логотипом, названием и флажком языка."""
        banner_panel = wx.Panel(self.panel)
        banner_panel.SetBackgroundColour(wx.Colour(BANNER_COLOR))
        if BANNER_HIGH < 20:
            logging.warning(f"BANNER_HIGH ({BANNER_HIGH}) is too small, setting to 20")
            banner_height = 20
        else:
            banner_height = BANNER_HIGH
        banner_panel.SetMinSize((-1, banner_height))
        banner_panel.SetMaxSize((-1, banner_height))
        banner_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Логотип слева
        logo_path = os.path.abspath(ICON_PATH)
        if os.path.exists(logo_path):
            try:
                logo_bitmap = wx.Bitmap(logo_path, wx.BITMAP_TYPE_ANY)
                if logo_bitmap.IsOk():
                    logo_bitmap = self.scale_bitmap(logo_bitmap, LOGO_SIZE[0], LOGO_SIZE[1])
                    logo = wx.StaticBitmap(banner_panel, bitmap=logo_bitmap)
                    banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
                    logging.info(f"Logo loaded: {logo_path}, size: {logo_bitmap.GetWidth()}x{logo_bitmap.GetHeight()}")
                else:
                    logging.error(f"Invalid bitmap: {logo_path}")
                    logo = wx.StaticText(banner_panel, label="[Logo]")
                    banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
            except Exception as e:
                logging.error(f"Error loading logo {logo_path}: {e}")
                logo = wx.StaticText(banner_panel, label="[Logo]")
                banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
        else:
            logging.error(f"Logo file not found: {logo_path}")
            logo = wx.StaticText(banner_panel, label="[Logo]")
            banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)

        banner_sizer.AddStretchSpacer()

        # Название программы по центру
        title = wx.StaticText(banner_panel, label=loc.get("program_title"))
        style_label(title)
        title.SetForegroundColour(wx.Colour(BANNER_TEXT_COLOR))
        if BANNER_HIGH >= 100:
            font = title.GetFont()
            font.SetPointSize(FONT_SIZE + 10)  # Увеличиваем шрифт для крупного баннера
            title.SetFont(font)
        banner_sizer.Add(title, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)

        banner_sizer.AddStretchSpacer()

        # Флажок языка справа
        lang_icon_path = os.path.abspath(LANGUAGE_ICONS.get(LANGUAGE, LANGUAGE_ICONS["ru"]))
        if os.path.exists(lang_icon_path):
            try:
                flag_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                if flag_bitmap.IsOk():
                    flag_bitmap = self.scale_bitmap(flag_bitmap, BANNER_HIGH - 10, BANNER_HIGH - 10)
                    self.flag_button = wx.StaticBitmap(banner_panel, bitmap=flag_bitmap)
                    self.flag_button.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
                    banner_sizer.Add(self.flag_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                                     border=10)
                    logging.info(
                        f"Flag icon loaded: {lang_icon_path}, size: {flag_bitmap.GetWidth()}x{flag_bitmap.GetHeight()}")
                else:
                    logging.error(f"Invalid bitmap: {lang_icon_path}")
                    flag_label = wx.StaticText(banner_panel, label=f"[{LANGUAGE}]")
                    banner_sizer.Add(flag_label, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
            except Exception as e:
                logging.error(f"Error loading flag icon {lang_icon_path}: {e}")
                flag_label = wx.StaticText(banner_panel, label=f"[{LANGUAGE}]")
                banner_sizer.Add(flag_label, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
        else:
            logging.error(f"Flag icon file not found: {lang_icon_path}")
            flag_label = wx.StaticText(banner_panel, label=f"[{LANGUAGE}]")
            banner_sizer.Add(flag_label, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)

        banner_panel.SetSizer(banner_sizer)
        self.main_sizer.Add(banner_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

    def create_menu(self):
        """Создает меню приложения."""
        menu_bar = wx.MenuBar()

        # Меню "Файл"
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, loc.get("button_exit"))
        menu_bar.Append(file_menu, loc.get("menu_file"))

        # Меню "Язык"
        self.language_menu = wx.Menu()
        self.lang_items = {
            "ru": self.language_menu.Append(wx.ID_ANY, loc.get("lang_ru"), kind=wx.ITEM_RADIO),
            "de": self.language_menu.Append(wx.ID_ANY, loc.get("lang_de"), kind=wx.ITEM_RADIO),
            "en": self.language_menu.Append(wx.ID_ANY, loc.get("lang_en"), kind=wx.ITEM_RADIO)
        }
        self.lang_items[LANGUAGE].Check(True)
        menu_bar.Append(self.language_menu, loc.get("language_menu"))

        # Меню "Справка"
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, loc.get("menu_about"))
        menu_bar.Append(help_menu, loc.get("menu_help"))

        self.SetMenuBar(menu_bar)

        # Привязываем обработчики
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        for lang, item in self.lang_items.items():
            self.Bind(wx.EVT_MENU, self.on_language_change, item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def create_status_bar(self):
        """Создает строку статуса и копирайт."""
        status_panel = wx.Panel(self.panel)
        status_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        status_panel.SetMinSize((-1, 30))
        status_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Строка статуса
        self.status_text = wx.StaticText(status_panel, label=loc.get("status_ready"))
        style_label(self.status_text)
        status_sizer.Add(self.status_text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)

        # Копирайт
        self.copyright_text = wx.StaticText(status_panel, label=loc.get("copyright"))
        style_label(self.copyright_text)
        status_sizer.Add(self.copyright_text, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)

        status_panel.SetSizer(status_sizer)
        self.main_sizer.Add(status_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

    def create_exit_button(self):
        """Создает кнопку выхода в button_panel."""
        self.exit_button = wx.Button(self.button_panel, label=loc.get("button_exit"))
        button_font = get_button_font()
        self.exit_button.SetFont(button_font)
        self.exit_button.SetBackgroundColour(wx.Colour(EXIT_BUTTON_COLOR))
        self.exit_button.SetForegroundColour(wx.Colour("white"))
        self.exit_button.Bind(wx.EVT_BUTTON, self.on_exit)

        # Рассчитываем максимальную ширину кнопки для всех языков
        max_width = 0
        languages = ['ru', 'en', 'de']
        for lang in languages:
            temp_loc = loc.__class__(lang)
            label = temp_loc.get("button_exit")
            dc = wx.ClientDC(self.exit_button)
            dc.SetFont(button_font)
            width, _ = dc.GetTextExtent(label)
            max_width = max(max_width, width + 20)
        self.exit_button.SetMinSize((max_width, 30))

        self.button_sizer.AddStretchSpacer()
        self.button_sizer.Add(self.exit_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)

    def on_language_change(self, event):
        """Обработчик смены языка через меню."""
        lang_map = {
            self.lang_items["ru"].GetId(): "ru",
            self.lang_items["de"].GetId(): "de",
            self.lang_items["en"].GetId(): "en"
        }
        event_id = event.GetId()
        new_lang = lang_map.get(event_id)
        if new_lang:
            logging.info(f"Смена языка через меню на: {new_lang}")
            set_language(new_lang)
            self.update_language_icon(new_lang)
            self.update_ui()

    def on_change_language(self, event):
        """Обработчик смены языка через значок."""
        current_langs = ["ru", "en", "de"]
        current_index = current_langs.index(loc.language) if loc.language in current_langs else 0
        new_index = (current_index + 1) % len(current_langs)
        new_lang = current_langs[new_index]
        logging.info(f"Смена языка через значок на: {new_lang}")
        set_language(new_lang)
        self.update_language_icon(new_lang)
        self.update_ui()

    def update_language_icon(self, new_lang: str):
        """Обновляет иконку языка."""
        lang_icon_path = os.path.abspath(LANGUAGE_ICONS.get(new_lang, LANGUAGE_ICONS["ru"]))
        if os.path.exists(lang_icon_path):
            try:
                flag_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                if flag_bitmap.IsOk():
                    flag_bitmap = self.scale_bitmap(flag_bitmap, BANNER_HIGH - 10, BANNER_HIGH - 10)
                    self.flag_button.SetBitmap(flag_bitmap)
                    logging.info(
                        f"Flag icon updated: {lang_icon_path}, size: {flag_bitmap.GetWidth()}x{flag_bitmap.GetHeight()}")
                else:
                    logging.error(f"Invalid bitmap for flag update: {lang_icon_path}")
                    self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")
            except Exception as e:
                logging.error(f"Error updating flag icon {lang_icon_path}: {e}")
                self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")
        else:
            logging.error(f"Flag icon file not found for update: {lang_icon_path}")
            self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")

        # Обновляем радиокнопки
        for lang, item in self.lang_items.items():
            item.Check(lang == new_lang)

    def update_ui(self):
        """Обновляет текст элементов интерфейса после смены языка."""
        self.SetTitle(loc.get("program_title"))
        self.status_text.SetLabel(loc.get("status_ready"))
        self.copyright_text.SetLabel(loc.get("copyright"))
        self.exit_button.SetLabel(loc.get("button_exit"))
        self.GetMenuBar().SetMenuLabel(0, loc.get("menu_file"))
        self.GetMenuBar().SetMenuLabel(1, loc.get("language_menu"))
        self.GetMenuBar().SetMenuLabel(2, loc.get("menu_help"))
        for lang, item in self.lang_items.items():
            item.SetItemLabel(loc.get(f"lang_{lang}"))
        apply_styles_to_panel(self.panel)
        self.panel.Layout()
        self.Refresh()

    def on_about(self, event):
        """Обработчик пункта меню 'О программе'."""
        show_popup(loc.get("about_text"), title=loc.get("menu_about"), popup_type="info")

    def on_exit(self, event):
        """Обработчик выхода из приложения."""
        self.Close()

    def on_close(self, event):
        """Обработчик закрытия окна."""
        x, y = self.GetPosition()
        save_last_position(x, y)
        event.Skip()


if __name__ == "__main__":
    app = wx.App()
    window = ATMainWindow()
    window.Show()
    app.MainLoop()
