"""
Файл: at_main_window.py
Путь: windows/at_main_window.py

Описание:
Главное окно приложения AT-CAD. Содержит меню, баннер, основную область для контента,
область кнопок и строку статуса. Управляет переключением контента и локализацией интерфейса.
"""

import wx
import os
import logging
import json
from config.at_config import (
    ICON_PATH,
    BANNER_HIGH,
    WINDOW_SIZE,
    LOGO_SIZE,
    MENU_ICONS,
    LANGUAGE_ICONS,
    DEFAULT_SETTINGS,
    load_user_settings,
    save_user_settings,
    USER_LANGUAGE_PATH,
)
from locales.at_localization_class import loc, Localization
from windows.at_window_utils import load_last_position, save_last_position, get_button_font, fit_text_to_height
from windows.at_gui_utils import show_popup
from config.at_cad_init import ATCadInit
from windows.at_run_dialog_window import load_content, at_load_content
from windows.at_content_registry import CONTENT_REGISTRY

# Устанавливаем текущую рабочую директорию в корень проекта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,  # Основной уровень для ошибок
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class ATMainWindow(wx.Frame):
    """
    Класс главного окна приложения AT-CAD.

    Атрибуты:
        last_input (dict): Словарь для хранения последних введённых данных.
        settings (dict): Текущие настройки приложения.
        exit_item (wx.MenuItem): Пункт меню "Выход".
        about_item (wx.MenuItem): Пункт меню "О программе".
        settings_item (wx.MenuItem): Пункт меню "Настройки".
        panel (wx.Panel): Главная панель окна.
        content_panel (wx.Panel): Панель для отображения контента.
        content_sizer (wx.BoxSizer): Сайзер для контента.
        current_content (wx.Window | None): Текущий контент в content_panel.
        button_panel (wx.Panel): Панель для кнопок.
        button_sizer (wx.BoxSizer): Сайзер для кнопок.
        exit_button (wx.Button): Кнопка выхода.
        main_sizer (wx.BoxSizer): Главный сайзер окна.
        banner_panel (wx.Panel): Панель баннера.
        title (wx.StaticText): Заголовок в баннере.
        flag_button (wx.StaticBitmap | wx.StaticText): Иконка языка в баннере.
        language_menu (wx.Menu): Меню выбора языка.
        lang_items (dict): Словарь пунктов меню для языков.
        status_text (wx.StaticText): Текст строки статуса.
        copyright_text (wx.StaticText): Текст копирайта.
    """

    def __init__(self):
        """
        Инициализирует главное окно приложения AT-CAD.
        """
        self.last_input = {}  # Для хранения последних введённых данных
        self.settings = load_user_settings()  # Загружаем настройки

        # Загрузка языка из user_language.json
        try:
            if os.path.exists(USER_LANGUAGE_PATH):
                with open(USER_LANGUAGE_PATH, 'r', encoding='utf-8') as f:
                    lang_data = json.load(f)
                    lang = lang_data.get("language")
                    if isinstance(lang, str) and lang in ["ru", "en", "de"]:
                        loc.set_language(lang)
                        logging.info(f"Язык загружен из user_language.json: {lang}")
                    else:
                        logging.warning(
                            f"Некорректный или отсутствующий язык в user_language.json: {lang}, используется {loc.language}")
            else:
                logging.info(f"Файл user_language.json не найден, используется язык по умолчанию: {loc.language}")
        except Exception as e:
            logging.error(f"Ошибка чтения user_language.json: {e}")

        logging.info(f"Загруженные настройки: {self.settings}")
        super().__init__(
            parent=None,
            title=loc.get("program_title", "AT-CAD"),
            size=WINDOW_SIZE,  # type: ignore
            style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
        )

        # Инициализация атрибутов для пунктов меню
        self.exit_item = None
        self.about_item = None
        self.settings_item = None

        # Создание главной панели
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        logging.info(f"Установлен цвет фона главной панели: {self.settings.get('BACKGROUND_COLOR', DEFAULT_SETTINGS['BACKGROUND_COLOR'])}")

        # Установка иконки приложения
        icon_path = os.path.abspath(ICON_PATH)
        if os.path.exists(icon_path):
            try:
                icon_bitmap = wx.Bitmap(icon_path, wx.BITMAP_TYPE_ANY)
                if icon_bitmap.IsOk():
                    icon_bitmap = self.scale_bitmap(icon_bitmap, 32, 32)
                    self.SetIcon(wx.Icon(icon_bitmap))
                    logging.info(f"Иконка приложения установлена: {icon_path}")
                else:
                    logging.error(f"Недопустимый формат иконки приложения: {icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки приложения {icon_path}: {e}")
        else:
            logging.error(f"Иконка приложения не найдена: {icon_path}")

        # Загрузка последнего положения окна с проверкой границ всех дисплеев
        x, y = load_last_position()
        window_size = self.GetSize()
        position_valid = False

        # Проверяем все доступные дисплеи
        for display_idx in range(wx.Display.GetCount()): # для получения количества подключенных дисплеев
            display = wx.Display(display_idx)
            screen_rect = display.GetClientArea()  # Область экрана (без учета панели задач)
            if (x != -1 and y != -1 and
                    screen_rect.x <= x <= screen_rect.x + screen_rect.width - window_size.width and
                    screen_rect.y <= y <= screen_rect.y + screen_rect.height - window_size.height):
                self.SetPosition((x, y))
                logging.info(f"Установлено последнее положение окна: x={x}, y={y} на дисплее {display_idx}")
                position_valid = True
                break

        if not position_valid:
            self.Centre()
            logging.info("Окно отцентрировано, так как позиция за пределами всех дисплеев или не определена")

        # Создание главного сайзера (вертикального)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Создание баннера
        self.create_banner()

        # Создание меню
        self.create_menu()

        # Создание основной области для контента
        self.content_panel = wx.Panel(self.panel)
        self.content_panel.SetBackgroundColour(wx.Colour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.content_panel.SetSizer(self.content_sizer)
        self.current_content = None
        self.main_sizer.Add(self.content_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        # Создание области кнопок
        self.button_panel = wx.Panel(self.panel)
        self.button_panel.SetBackgroundColour(wx.Colour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.create_exit_button()
        self.button_panel.SetSizer(self.button_sizer)
        self.main_sizer.Add(self.button_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Создание строки статуса и копирайта
        self.create_status_bar()

        # Установка сайзера для панели
        self.panel.SetSizer(self.main_sizer)
        self.panel.Layout()

        # Загрузка начальной страницы
        self.switch_content("content_apps")

        # Привязка обработчика закрытия окна
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Обновление UI с текущими настройками
        self.update_ui(self.settings)

    def scale_bitmap(self, bitmap: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
        """
        Масштабирует изображение до заданных размеров.

        Args:
            bitmap (wx.Bitmap): Исходное изображение.
            width (int): Целевая ширина.
            height (int): Целевая высота.

        Returns:
            wx.Bitmap: Масштабированное изображение.
        """
        if bitmap.IsOk():
            image = bitmap.ConvertToImage()
            image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(image)
        return bitmap

    def switch_content(self, content_name: str) -> None:
        """
        Переключает содержимое основной области на указанный контент.

        Args:
            content_name (str): Имя контента для отображения.
        """
        if not isinstance(content_name, str):
            logging.warning(f"Нестроковый content_name: {content_name}, преобразование в строку")
            content_name = str(content_name)

        logging.info(
            f"Переключение на контент: {content_name}, текущий контент: {self.current_content.__class__.__name__ if self.current_content else None}")

        # Очищаем content_sizer полностью
        if self.current_content:
            self.current_content.Destroy()
            self.current_content = None
        self.content_sizer.Clear(True)  # Полная очистка сайзера

        try:
            new_content = at_load_content(content_name, self.content_panel)
            if new_content and isinstance(new_content, wx.Window):
                self.current_content = new_content
                self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
                if hasattr(self.current_content, 'update_ui_language'):
                    self.current_content.update_ui_language()
                    logging.info(f"Обновлён язык для контента: {content_name}")
                else:
                    logging.warning(f"Контент {content_name} не имеет метода update_ui_language")
            else:
                error_msg = f"Ошибка загрузки {content_name}"
                logging.error(f"Некорректный контент возвращён для {content_name}")
                self.current_content = wx.StaticText(self.content_panel, label=error_msg)
                self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        except Exception as e:
            error_msg = f"Ошибка загрузки {content_name}: {str(e)}"
            logging.error(f"Ошибка переключения на контент {content_name}: {e}")
            self.current_content = wx.StaticText(self.content_panel, label=error_msg)
            self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        self.content_panel.Layout()
        self.content_panel.Refresh()
        self.content_panel.Update()
        self.update_ui(self.settings)
        logging.info(f"Контент переключён на {content_name}, интерфейс обновлён")

    def create_banner(self) -> None:
        """
        Создаёт баннер в верхней части окна с логотипом, названием и иконкой языка.
        """
        self.banner_panel = wx.Panel(self.panel)
        self.banner_panel.SetBackgroundColour(wx.Colour(self.settings.get("BANNER_COLOR", DEFAULT_SETTINGS["BANNER_COLOR"])))
        logging.info(f"Установлен цвет фона баннера: {self.settings.get('BANNER_COLOR', DEFAULT_SETTINGS['BANNER_COLOR'])}")

        banner_height = max(BANNER_HIGH, 20)
        self.banner_panel.SetMinSize((wx.DefaultCoord, banner_height))
        self.banner_panel.SetMaxSize((wx.DefaultCoord, banner_height))

        banner_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Логотип слева
        logo_path = os.path.abspath(ICON_PATH)
        if os.path.exists(logo_path):
            try:
                logo_bitmap = wx.Bitmap(logo_path, wx.BITMAP_TYPE_ANY)
                if logo_bitmap.IsOk():
                    logo_bitmap = self.scale_bitmap(logo_bitmap, LOGO_SIZE[0], LOGO_SIZE[1])
                    self.logo = wx.StaticBitmap(self.banner_panel, bitmap=logo_bitmap)
                    banner_sizer.Add(self.logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
                    logging.info(f"Логотип загружен: {logo_path}")
                else:
                    raise ValueError("Недопустимый формат логотипа")
            except Exception as e:
                logging.error(f"Ошибка загрузки логотипа {logo_path}: {e}")
                self.logo = wx.StaticText(self.banner_panel, label="[Logo]")
                banner_sizer.Add(self.logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
        else:
            logging.error(f"Файл логотипа не найден: {logo_path}")
            self.logo = wx.StaticText(self.banner_panel, label="[Logo]")
            banner_sizer.Add(self.logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)

        banner_sizer.AddStretchSpacer()

        # Название программы по центру
        max_width = WINDOW_SIZE[0] - 2 * LOGO_SIZE[0] - 50
        max_height = banner_height - 20

        self.title = wx.StaticText(self.banner_panel, label="", style=wx.ST_NO_AUTORESIZE)
        self.title.SetMinSize((max_width, -1))

        title_text = loc.get("program_title", "AT-CAD")
        style_flags = {
            "style": wx.FONTSTYLE_NORMAL if self.settings.get("FONT_TYPE", "normal") == "normal" else wx.FONTSTYLE_ITALIC,
            "weight": wx.FONTWEIGHT_BOLD if self.settings.get("FONT_TYPE", "normal") in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL
        }
        optimal_size = fit_text_to_height(self.title, title_text, max_width, max_height, self.settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"]), style_flags)

        font = wx.Font(
            optimal_size,
            wx.FONTFAMILY_DEFAULT,
            style_flags["style"],
            style_flags["weight"],
            faceName=self.settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"])
        )
        self.title.SetFont(font)
        self.title.SetForegroundColour(wx.Colour(self.settings.get("BANNER_TEXT_COLOR", DEFAULT_SETTINGS["BANNER_TEXT_COLOR"])))
        self.title.SetLabel(title_text)
        self.title.Wrap(max_width)
        logging.info(f"Заголовок баннера установлен: {title_text}, шрифт={self.settings.get('FONT_NAME', DEFAULT_SETTINGS['FONT_NAME'])}, размер={optimal_size}")

        banner_sizer.Add(self.title, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        banner_sizer.AddStretchSpacer()

        # Флажок языка справа
        lang_icon_path = os.path.abspath(LANGUAGE_ICONS.get(loc.language, LANGUAGE_ICONS["ru"]))
        if os.path.exists(lang_icon_path):
            try:
                flag_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                if flag_bitmap.IsOk():
                    flag_bitmap = self.scale_bitmap(flag_bitmap, banner_height - 10, banner_height - 10)
                    self.flag_button = wx.StaticBitmap(self.banner_panel, bitmap=flag_bitmap)
                    self.flag_button.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
                    banner_sizer.Add(self.flag_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
                    logging.info(f"Иконка флага установлена: {lang_icon_path}")
                else:
                    raise ValueError("Недопустимый формат иконки флага")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки флага {lang_icon_path}: {e}")
                self.flag_button = wx.StaticText(self.banner_panel, label=f"[{loc.language}]")
                banner_sizer.Add(self.flag_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
        else:
            logging.error(f"Файл иконки флага не найден: {lang_icon_path}")
            self.flag_button = wx.StaticText(self.banner_panel, label=f"[{loc.language}]")
            banner_sizer.Add(self.flag_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)

        self.banner_panel.SetSizer(banner_sizer)
        self.banner_panel.Layout()
        self.banner_panel.Refresh()
        self.main_sizer.Add(self.banner_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

    def create_menu(self) -> None:
        """
        Создаёт меню приложения.
        """
        menu_bar = wx.MenuBar()

        # Меню "Файл"
        file_menu = wx.Menu()
        self.exit_item = file_menu.Append(wx.ID_EXIT, loc.get("button_exit", "Выход"))
        exit_icon_path = os.path.abspath(MENU_ICONS.get("exit", ""))
        if os.path.exists(exit_icon_path):
            try:
                exit_bitmap = wx.Bitmap(exit_icon_path, wx.BITMAP_TYPE_ANY)
                if exit_bitmap.IsOk():
                    exit_bitmap = self.scale_bitmap(exit_bitmap, 16, 16)
                    self.exit_item.SetBitmap(exit_bitmap)
                    logging.info(f"Иконка выхода установлена: {exit_icon_path}")
                else:
                    logging.error(f"Недопустимый формат иконки выхода: {exit_icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки выхода {exit_icon_path}: {e}")
        menu_bar.Append(file_menu, loc.get("menu_file", "Файл"))

        # Меню "Язык"
        self.language_menu = wx.Menu()
        self.lang_items = {
            "ru": self.language_menu.Append(wx.ID_ANY, loc.get("lang_ru", "Русский"), kind=wx.ITEM_RADIO),
            "de": self.language_menu.Append(wx.ID_ANY, loc.get("lang_de", "Deutsch"), kind=wx.ITEM_RADIO),
            "en": self.language_menu.Append(wx.ID_ANY, loc.get("lang_en", "English"), kind=wx.ITEM_RADIO),
        }
        self.lang_items[loc.language].Check(True)
        for lang, item in self.lang_items.items():
            lang_icon_path = os.path.abspath(MENU_ICONS.get(f"lang_{lang}", ""))
            if os.path.exists(lang_icon_path):
                try:
                    lang_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                    if lang_bitmap.IsOk():
                        lang_bitmap = self.scale_bitmap(lang_bitmap, 16, 16)
                        item.SetBitmap(lang_bitmap)
                        logging.info(f"Иконка языка {lang} установлена: {lang_icon_path}")
                    else:
                        logging.error(f"Недопустимый формат иконки lang_{lang}: {lang_icon_path}")
                except Exception as e:
                    logging.error(f"Ошибка загрузки иконки lang_{lang} {lang_icon_path}: {e}")
            else:
                logging.warning(f"Иконка lang_{lang} не найдена: {lang_icon_path}")
        menu_bar.Append(self.language_menu, loc.get("language_menu", "Язык"))

        # Меню "Справка"
        help_menu = wx.Menu()
        self.settings_item = help_menu.Append(wx.ID_ANY, loc.get("settings_title", "Настройки"))
        self.about_item = help_menu.Append(wx.ID_ABOUT, loc.get("menu_about", "О программе"))
        about_icon_path = os.path.abspath(MENU_ICONS.get("about", ""))
        settings_icon_path = os.path.abspath(MENU_ICONS.get("settings", ""))
        if os.path.exists(about_icon_path):
            try:
                about_bitmap = wx.Bitmap(about_icon_path, wx.BITMAP_TYPE_ANY)
                if about_bitmap.IsOk():
                    about_bitmap = self.scale_bitmap(about_bitmap, 16, 16)
                    self.about_item.SetBitmap(about_bitmap)
                    logging.info(f"Иконка 'О программе' установлена: {about_icon_path}")
                else:
                    logging.error(f"Недопустимый формат иконки about: {about_icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки about {about_icon_path}: {e}")
        if os.path.exists(settings_icon_path):
            try:
                settings_bitmap = wx.Bitmap(settings_icon_path, wx.BITMAP_TYPE_ANY)
                if settings_bitmap.IsOk():
                    settings_bitmap = self.scale_bitmap(settings_bitmap, 16, 16)
                    self.settings_item.SetBitmap(settings_bitmap)
                    logging.info(f"Иконка настроек установлена: {settings_icon_path}")
                else:
                    logging.error(f"Недопустимый формат иконки settings: {settings_icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки settings {settings_icon_path}: {e}")
        menu_bar.Append(help_menu, loc.get("menu_help", "Справка"))

        self.SetMenuBar(menu_bar)

        # Привязываем обработчики
        self.Bind(wx.EVT_MENU, self.on_exit, self.exit_item)
        self.Bind(wx.EVT_MENU, self.on_settings, self.settings_item)
        self.Bind(wx.EVT_MENU, self.on_about, self.about_item)
        for lang, item in self.lang_items.items():
            self.Bind(wx.EVT_MENU, lambda evt, l=lang: self.on_language_change(l), item)

    def on_settings(self, event) -> None:
        """
        Открывает окно настроек и обновляет настройки после закрытия.
        """
        from windows.at_settings_window import SettingsWindow
        dialog = SettingsWindow(self)
        dialog.ShowModal()
        self.settings = load_user_settings()
        self.update_ui(self.settings)
        logging.info("Настройки обновлены после закрытия окна настроек")
        dialog.Destroy()

    def create_status_bar(self) -> None:
        """
        Создаёт строку статуса и копирайт в нижней части окна.
        """
        status_panel = wx.Panel(self.panel)
        status_panel.SetBackgroundColour(wx.Colour(self.settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        status_panel.SetMinSize((-1, 30))
        status_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Строка статуса
        self.status_text = wx.StaticText(status_panel, label=loc.get("status_ready", "Готово"))
        font = wx.Font(
            self.settings.get("FONT_SIZE", DEFAULT_SETTINGS["FONT_SIZE"]),
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL if self.settings.get("FONT_TYPE", "normal") == "normal" else wx.FONTSTYLE_ITALIC,
            wx.FONTWEIGHT_BOLD if self.settings.get("FONT_TYPE", "normal") in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL,
            faceName=self.settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"]),
        )
        self.status_text.SetFont(font)
        self.status_text.SetForegroundColour(wx.Colour(self.settings.get("STATUS_TEXT_COLOR", DEFAULT_SETTINGS["STATUS_TEXT_COLOR"])))
        status_sizer.Add(self.status_text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)
        logging.info(f"Строка статуса создана: размер шрифта={self.settings.get('FONT_SIZE', DEFAULT_SETTINGS['FONT_SIZE'])}, цвет={self.settings.get('STATUS_TEXT_COLOR', DEFAULT_SETTINGS['STATUS_TEXT_COLOR'])}")

        # Копирайт
        self.copyright_text = wx.StaticText(status_panel, label=loc.get("copyright", "© AT-CAD"))
        self.copyright_text.SetFont(font)
        self.copyright_text.SetForegroundColour(wx.Colour(self.settings.get("STATUS_TEXT_COLOR", DEFAULT_SETTINGS["STATUS_TEXT_COLOR"])))
        status_sizer.Add(self.copyright_text, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        logging.info(f"Копирайт создан: размер шрифта={self.settings.get('FONT_SIZE', DEFAULT_SETTINGS['FONT_SIZE'])}, цвет={self.settings.get('STATUS_TEXT_COLOR', DEFAULT_SETTINGS['STATUS_TEXT_COLOR'])}")

        status_panel.SetSizer(status_sizer)
        self.main_sizer.Add(status_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

    def create_exit_button(self) -> None:
        """
        Создаёт кнопку выхода.
        """
        self.exit_button = wx.Button(self.button_panel, label=loc.get("button_exit", "Выход"))
        button_font = get_button_font()
        self.exit_button.SetFont(button_font)
        self.exit_button.SetBackgroundColour(
            wx.Colour(self.settings.get("EXIT_BUTTON_COLOR", DEFAULT_SETTINGS["EXIT_BUTTON_COLOR"])))
        self.exit_button.SetForegroundColour(
            wx.Colour(self.settings.get("BUTTON_FONT_COLOR", DEFAULT_SETTINGS["BUTTON_FONT_COLOR"])))
        self.exit_button.Bind(wx.EVT_BUTTON, self.on_exit)

        # Рассчитываем минимальную ширину кнопки на основе текущего языка
        label = loc.get("button_exit", "Выход")
        dc = wx.ClientDC(self.exit_button)
        dc.SetFont(button_font)
        width, _ = dc.GetTextExtent(label)
        max_width = width + 20
        self.exit_button.SetMinSize((max_width, 30))

        self.button_sizer.AddStretchSpacer()
        self.button_sizer.Add(self.exit_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=10)
        logging.info(
            f"Кнопка выхода создана: текст={loc.get('button_exit', 'Выход')}, размер={max_width}x30")

    def on_language_change(self, new_lang: str) -> None:
        """
        Обрабатывает смену языка через меню.

        Args:
            new_lang (str): Новый язык (ru, en, de).
        """
        if not isinstance(new_lang, str):
            logging.error(f"Нестроковый new_lang в on_language_change: {new_lang}, игнорируется")
            return
        loc.set_language(new_lang)
        self.update_language_icon(new_lang)
        self.update_ui(self.settings)
        logging.info(f"Смена языка через меню на: {new_lang}")

    def on_change_language(self, event) -> None:
        """
        Обрабатывает смену языка через иконку флага.
        """
        current_langs = ["ru", "en", "de"]
        if not isinstance(loc.language, str):
            logging.error(f"loc.language не строка в on_change_language: {loc.language}, установка языка по умолчанию: ru")
            loc.language = "ru"
        current_index = current_langs.index(loc.language) if loc.language in current_langs else 0
        new_index = (current_index + 1) % len(current_langs)
        new_lang = current_langs[new_index]
        loc.set_language(new_lang)
        self.update_language_icon(new_lang)
        self.update_ui(self.settings)
        logging.info(f"Смена языка через значок на: {new_lang}")

    def update_language_icon(self, new_lang: str) -> None:
        """
        Обновляет иконку флага в баннере.

        Args:
            new_lang (str): Код языка (ru, en, de).
        """
        if not isinstance(new_lang, str):
            logging.error(f"Нестроковый new_lang в update_language_icon: {new_lang}, использование языка по умолчанию: ru")
            new_lang = "ru"
        lang_icon_path = os.path.abspath(LANGUAGE_ICONS.get(new_lang, LANGUAGE_ICONS["ru"]))
        if os.path.exists(lang_icon_path):
            try:
                flag_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                if flag_bitmap.IsOk():
                    flag_bitmap = self.scale_bitmap(flag_bitmap, BANNER_HIGH - 10, BANNER_HIGH - 10)
                    if isinstance(self.flag_button, wx.StaticBitmap):
                        self.flag_button.SetBitmap(flag_bitmap)
                    else:
                        self.flag_button.Destroy()
                        self.flag_button = wx.StaticBitmap(self.banner_panel, bitmap=flag_bitmap)
                        self.banner_panel.GetSizer().Replace(self.flag_button, self.flag_button)
                    self.flag_button.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
                    logging.info(f"Иконка флага обновлена: {lang_icon_path}")
                else:
                    logging.error(f"Недопустимый формат иконки флага: {lang_icon_path}")
                    self.replace_flag_button_with_text(new_lang)
            except Exception as e:
                logging.error(f"Ошибка обновления иконки флага {lang_icon_path}: {e}")
                self.replace_flag_button_with_text(new_lang)
        else:
            logging.warning(f"Файл иконки флага не найден: {lang_icon_path}")
            self.replace_flag_button_with_text(new_lang)

        # Обновляем радиокнопки
        for lang, item in self.lang_items.items():
            item.Check(lang == new_lang)
        self.banner_panel.Layout()
        self.banner_panel.Refresh()
        self.banner_panel.Update()

    def replace_flag_button_with_text(self, new_lang: str) -> None:
        """
        Заменяет иконку флага на текстовую метку при ошибке загрузки.

        Args:
            new_lang (str): Код языка (ru, en, de).
        """
        if not isinstance(new_lang, str):
            logging.error(f"Нестроковый new_lang в replace_flag_button_with_text: {new_lang}, использование языка по умолчанию: ru")
            new_lang = "ru"
        if isinstance(self.flag_button, wx.StaticBitmap):
            self.flag_button.Destroy()
        self.flag_button = wx.StaticText(self.banner_panel, label=f"[{new_lang}]")
        self.banner_panel.GetSizer().Replace(self.flag_button, self.flag_button)
        self.flag_button.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
        logging.info(f"Иконка флага заменена текстом: [{new_lang}]")

    def update_ui(self, settings: dict) -> None:
        """
        Обновляет пользовательский интерфейс с использованием указанных настроек.

        Args:
            settings (dict): Словарь с настройками интерфейса.
        """
        self.settings = settings.copy()
        logging.info(f"Обновление UI: title={loc.get('program_title', 'AT-CAD')}, language={loc.language}")

        # Обновляем заголовок окна
        self.SetTitle(loc.get("program_title", "AT-CAD"))

        # Обновляем баннер
        if hasattr(self, "banner_panel"):
            self.banner_panel.SetBackgroundColour(wx.Colour(settings.get("BANNER_COLOR", DEFAULT_SETTINGS["BANNER_COLOR"])))
        if hasattr(self, "title"):
            title_text = loc.get("program_title", "AT-CAD")
            self.title.SetLabel("")
            max_width = WINDOW_SIZE[0] - 2 * LOGO_SIZE[0] - 50
            max_height = max(BANNER_HIGH, 20) - 20
            style_flags = {
                "style": wx.FONTSTYLE_NORMAL if settings.get("FONT_TYPE", "normal") == "normal" else wx.FONTSTYLE_ITALIC,
                "weight": wx.FONTWEIGHT_BOLD if settings.get("FONT_TYPE", "normal") in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL
            }
            optimal_size = fit_text_to_height(self.title, title_text, max_width, max_height, settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"]), style_flags)
            font = wx.Font(
                optimal_size,
                wx.FONTFAMILY_DEFAULT,
                style_flags["style"],
                style_flags["weight"],
                faceName=settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"])
            )
            self.title.SetFont(font)
            self.title.SetForegroundColour(wx.Colour(settings.get("BANNER_TEXT_COLOR", DEFAULT_SETTINGS["BANNER_TEXT_COLOR"])))
            self.title.SetLabel(title_text)
            self.title.Wrap(max_width)
            logging.info(f"Обновлён заголовок баннера: {title_text}")

        # Обновляем цвета панелей
        if hasattr(self, "panel"):
            self.panel.SetBackgroundColour(wx.Colour(settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        if hasattr(self, "content_panel"):
            self.content_panel.SetBackgroundColour(wx.Colour(settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))
        if hasattr(self, "button_panel"):
            self.button_panel.SetBackgroundColour(wx.Colour(settings.get("BACKGROUND_COLOR", DEFAULT_SETTINGS["BACKGROUND_COLOR"])))

        # Обновляем кнопку выхода
        if hasattr(self, "exit_button"):
            self.exit_button.SetBackgroundColour(wx.Colour(settings.get("EXIT_BUTTON_COLOR", DEFAULT_SETTINGS["EXIT_BUTTON_COLOR"])))
            self.exit_button.SetForegroundColour(wx.Colour(settings.get("BUTTON_FONT_COLOR", DEFAULT_SETTINGS["BUTTON_FONT_COLOR"])))
            self.exit_button.SetLabel(loc.get("button_exit", "Выход"))
            button_font = get_button_font()
            self.exit_button.SetFont(button_font)
            logging.info(f"Обновлена кнопка выхода: текст={loc.get('button_exit', 'Выход')}")

        # Обновляем строку статуса и копирайт
        if hasattr(self, "status_text"):
            self.status_text.SetLabel(loc.get("status_ready", "Готово"))
            font = wx.Font(
                settings.get("FONT_SIZE", DEFAULT_SETTINGS["FONT_SIZE"]),
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL if settings.get("FONT_TYPE", "normal") == "normal" else wx.FONTSTYLE_ITALIC,
                wx.FONTWEIGHT_BOLD if settings.get("FONT_TYPE", "normal") in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL,
                faceName=settings.get("FONT_NAME", DEFAULT_SETTINGS["FONT_NAME"]),
            )
            self.status_text.SetFont(font)
            self.status_text.SetForegroundColour(wx.Colour(settings.get("STATUS_TEXT_COLOR", DEFAULT_SETTINGS["STATUS_TEXT_COLOR"])))
            logging.info(f"Обновлена строка статуса: текст={loc.get('status_ready', 'Готово')}")

        if hasattr(self, "copyright_text"):
            self.copyright_text.SetLabel(loc.get("copyright", "© AT-CAD"))
            self.copyright_text.SetFont(font)
            self.copyright_text.SetForegroundColour(wx.Colour(settings.get("STATUS_TEXT_COLOR", DEFAULT_SETTINGS["STATUS_TEXT_COLOR"])))
            logging.info(f"Обновлён копирайт: текст={loc.get('copyright', '© AT-CAD')}")

        # Обновляем меню
        menu_bar = self.GetMenuBar()
        if menu_bar:
            menu_bar.SetMenuLabel(0, loc.get("menu_file", "Файл"))
            menu_bar.SetMenuLabel(1, loc.get("language_menu", "Язык"))
            menu_bar.SetMenuLabel(2, loc.get("menu_help", "Справка"))
            for lang, item in self.lang_items.items():
                item.SetItemLabel(loc.get(f"lang_{lang}", lang.capitalize()))
                lang_icon_path = os.path.abspath(MENU_ICONS.get(f"lang_{lang}", ""))
                if os.path.exists(lang_icon_path):
                    try:
                        lang_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                        if lang_bitmap.IsOk():
                            lang_bitmap = self.scale_bitmap(lang_bitmap, 16, 16)
                            item.SetBitmap(lang_bitmap)
                            logging.info(f"Обновлена иконка языка {lang}: {lang_icon_path}")
                        else:
                            logging.error(f"Недопустимый формат иконки lang_{lang} в update_ui: {lang_icon_path}")
                    except Exception as e:
                        logging.error(f"Ошибка обновления иконки lang_{lang} {lang_icon_path}: {e}")
                else:
                    logging.warning(f"Иконка lang_{lang} не найдена в update_ui: {lang_icon_path}")

        if self.exit_item:
            self.exit_item.SetItemLabel(loc.get("button_exit", "Выход"))
        if self.about_item:
            self.about_item.SetItemLabel(loc.get("menu_about", "О программе"))
        if self.settings_item:
            self.settings_item.SetItemLabel(loc.get("settings_title", "Настройки"))
        logging.info("Меню обновлено")

        # Обновляем текущий контент
        if self.current_content and hasattr(self.current_content, "update_ui_language"):
            try:
                self.current_content.update_ui_language()
                logging.info(f"Язык контента {self.current_content.__class__.__name__} обновлён")
            except Exception as e:
                error_msg = f"Ошибка: Ошибка в update_ui_language: {str(e)}"
                show_popup(error_msg, popup_type="error")
                logging.error(f"Ошибка при обновлении языка панели {self.current_content.__class__.__name__}: {e}")

        # Перерисовываем интерфейс
        if hasattr(self, "panel"):
            self.panel.Layout()
        if hasattr(self, "banner_panel"):
            self.banner_panel.Layout()
        if hasattr(self, "content_panel"):
            self.content_panel.Layout()
        if hasattr(self, "button_panel"):
            self.button_panel.Layout()
        self.Refresh()
        self.Update()
        logging.info("Интерфейс главного окна полностью обновлён")

    def on_about(self, event) -> None:
        """
        Показывает информацию о программе.
        """
        show_popup(loc.get("about_text", "О программе AT-CAD"), title=loc.get("menu_about", "О программе"), popup_type="info")
        logging.info("Открыто окно 'О программе'")

    def on_exit(self, event) -> None:
        """
        Закрывает приложение.
        """
        logging.info("Закрытие приложения")
        self.Close()

    def on_close(self, event) -> None:
        """
        Сохраняет позицию окна и язык при закрытии.
        """
        x, y = self.GetPosition()
        save_last_position(x, y)
        logging.info(f"Позиция окна сохранена: x={x}, y={y}")
        # Сохранение текущего языка в user_language.json
        try:
            language = loc.language
            if isinstance(language, str) and language in ["ru", "en", "de"]:
                with open(USER_LANGUAGE_PATH, 'w', encoding='utf-8') as f:
                    json.dump({"language": language}, f, indent=4, ensure_ascii=False)
                logging.info(f"Язык сохранён в user_language.json: {language}")
            else:
                logging.warning(f"Не удалось сохранить язык: {language} недопустим, пропуск сохранения")
        except Exception as e:
            logging.error(f"Ошибка сохранения user_language.json: {e}")
        event.Skip()


if __name__ == "__main__":
    app = wx.App()
    window = ATMainWindow()
    window.Show()
    app.MainLoop()
