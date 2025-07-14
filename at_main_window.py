# at_main_window.py
"""
Главное окно приложения AT-CAD.
Содержит меню, баннер, основную область, область кнопок и строку статуса.
"""

import wx
import os
import logging
from config.at_config import (
    ICON_PATH,
    LANGUAGE,
    LANGUAGE_ICONS,
    BANNER_COLOR,
    BANNER_TEXT_COLOR,
    BACKGROUND_COLOR,
    EXIT_BUTTON_COLOR,
    BANNER_HIGH,
    WINDOW_SIZE,
    LOGO_SIZE,
    FONT_SIZE,
    FONT_TYPE,
    STATUS_FONT_SIZE,
    STATUS_TEXT_COLOR,
    FONT_NAME,
    BANNER_FONT_SIZE,
    MENU_ICONS,
)
from locales.at_localization_class import loc, Localization
from windows.at_window_utils import load_last_position, save_last_position, get_button_font, fit_text_to_height
from windows.at_gui_utils import show_popup
from config.at_cad_init import ATCadInit
from windows.at_run_dialog_window import load_content, at_load_content
from windows.at_content_registry import CONTENT_REGISTRY

# Устанавливаем текущую рабочую директорию в корень проекта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.INFO,  # Изменено на INFO для захвата всех сообщений
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class ATMainWindow(wx.Frame):
    def __init__(self):
        """
        Инициализирует главное окно приложения.
        """
        self.last_input = {}  # Для хранения последних введенных данных
        # Инициализируем локализацию
        super().__init__(
            parent=None,
            title=loc.get("program_title"),
            size=WINDOW_SIZE,
            style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
        )
        self.SetMinSize(WINDOW_SIZE)
        self.SetMaxSize(WINDOW_SIZE)

        # # Инициализация AutoCAD
        # self.cad = ATCadInit()
        # if not self.cad.is_initialized():
        #     show_popup(loc.get("cad_init_error", "Ошибка инициализации AutoCAD"), popup_type="error")
        #     logging.error("AutoCAD не инициализирован")

        # Инициализируем атрибуты для пунктов меню
        self.exit_item = None
        self.about_item = None

        # Создаем главную панель для всего содержимого
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))

        # Устанавливаем иконку приложения
        icon_path = os.path.abspath(ICON_PATH)
        if os.path.exists(icon_path):
            try:
                icon_bitmap = wx.Bitmap(icon_path, wx.BITMAP_TYPE_ANY)
                if icon_bitmap.IsOk():
                    icon_bitmap = self.scale_bitmap(icon_bitmap, 32, 32)
                    self.SetIcon(wx.Icon(icon_bitmap))
                else:
                    logging.error(f"Недопустимый формат иконки приложения: {icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки приложения {icon_path}: {e}")
        else:
            logging.error(f"Иконка приложения не найдена: {icon_path}")

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

        # Основная область (контейнер для контента)
        self.content_panel = wx.Panel(self.panel)
        self.content_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)  # Сайзер для динамического контента
        self.content_panel.SetSizer(self.content_sizer)
        self.current_content = None  # Текущая панель контента
        self.main_sizer.Add(self.content_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        # Загружаем начальную страницу
        self.switch_content("content_apps")

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

    def switch_content(self, content_name: str):
        """
        Переключает содержимое content_panel на указанную панель.

        Args:
            content_name: Имя модуля контента (например, 'content_apps').
        """
        # Удаляем текущий контент, если он есть
        if self.current_content:
            self.current_content.Destroy()
            self.current_content = None

        # Загружаем новый контент через at_load_content
        try:
            logging.info(f"Переключение на контент {content_name}")
            new_content = at_load_content(content_name, self.content_panel)
            if new_content and isinstance(new_content, wx.Window):
                self.current_content = new_content
                self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
            else:
                logging.error(f"Некорректный контент возвращён для {content_name}")
                self.current_content = wx.StaticText(self.content_panel, label=f"Ошибка загрузки {content_name}")
                self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        except Exception as e:
            logging.error(f"Ошибка переключения на контент {content_name}: {e}")
            self.current_content = wx.StaticText(self.content_panel, label=f"Ошибка загрузки {content_name}")
            self.content_sizer.Add(self.current_content, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        self.content_panel.Layout()
        self.Refresh()

    def create_banner(self):
        """Создает баннер с логотипом, названием и флажком языка."""
        banner_panel = wx.Panel(self.panel)
        banner_panel.SetBackgroundColour(wx.Colour(BANNER_COLOR))

        banner_height = max(BANNER_HIGH, 20)
        banner_panel.SetMinSize((wx.DefaultCoord, banner_height))
        banner_panel.SetMaxSize((wx.DefaultCoord, banner_height))

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
                else:
                    raise ValueError("Недопустимый формат логотипа")
            except Exception as e:
                logging.error(f"Ошибка загрузки логотипа {logo_path}: {e}")
                logo = wx.StaticText(banner_panel, label="[Logo]")
                banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)
        else:
            logging.error(f"Файл логотипа не найден: {logo_path}")
            logo = wx.StaticText(banner_panel, label="[Logo]")
            banner_sizer.Add(logo, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=10)

        banner_sizer.AddStretchSpacer()

        # Название программы по центру с переносом строк и адаптивным шрифтом
        max_width = WINDOW_SIZE[0] - 2 * LOGO_SIZE[0] - 50
        max_height = banner_height - 20  # отступы сверху и снизу

        self.title = wx.StaticText(
            banner_panel,
            label="",
            style=wx.ST_NO_AUTORESIZE
        )
        self.title.SetMinSize((max_width, -1))

        # Вычисляем оптимальный размер шрифта
        title_text = loc.get("program_title")
        style_flags = {
            "style": wx.FONTSTYLE_NORMAL if FONT_TYPE == "normal" else wx.FONTSTYLE_ITALIC,
            "weight": wx.FONTWEIGHT_BOLD if FONT_TYPE in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL
        }
        optimal_size = fit_text_to_height(
            self.title, title_text, max_width, max_height, FONT_NAME, style_flags
        )

        font = wx.Font(
            optimal_size,
            wx.FONTFAMILY_DEFAULT,
            style_flags["style"],
            style_flags["weight"],
            faceName=FONT_NAME
        )
        self.title.SetFont(font)
        self.title.SetForegroundColour(wx.Colour(BANNER_TEXT_COLOR))
        self.title.SetLabel(title_text)
        self.title.Wrap(max_width)

        banner_sizer.Add(self.title, proportion=0, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        banner_sizer.AddStretchSpacer()

        # Флажок языка справа
        lang_icon_path = os.path.abspath(LANGUAGE_ICONS.get(LANGUAGE, LANGUAGE_ICONS["ru"]))
        if os.path.exists(lang_icon_path):
            try:
                flag_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                if flag_bitmap.IsOk():
                    flag_bitmap = self.scale_bitmap(flag_bitmap, banner_height - 10, banner_height - 10)
                    self.flag_button = wx.StaticBitmap(banner_panel, bitmap=flag_bitmap)
                    self.flag_button.Bind(wx.EVT_LEFT_DOWN, self.on_change_language)
                    banner_sizer.Add(self.flag_button, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
                else:
                    raise ValueError("Недопустимый формат иконки флага")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки флага {lang_icon_path}: {e}")
                flag_label = wx.StaticText(banner_panel, label=f"[{LANGUAGE}]")
                banner_sizer.Add(flag_label, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)
        else:
            logging.error(f"Файл иконки флага не найден: {lang_icon_path}")
            flag_label = wx.StaticText(banner_panel, label=f"[{LANGUAGE}]")
            banner_sizer.Add(flag_label, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=10)

        banner_panel.SetSizer(banner_sizer)
        banner_panel.Layout()
        banner_panel.Refresh()

        self.main_sizer.Add(banner_panel, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

    def create_menu(self):
        """Создает меню приложения."""
        menu_bar = wx.MenuBar()

        # Меню "Файл"
        file_menu = wx.Menu()
        self.exit_item = file_menu.Append(wx.ID_EXIT, loc.get("button_exit"))  # Сохраняем как атрибут
        # Устанавливаем иконку для пункта "Выход"
        exit_icon_path = os.path.abspath(MENU_ICONS.get("exit", ""))
        if os.path.exists(exit_icon_path):
            try:
                exit_bitmap = wx.Bitmap(exit_icon_path, wx.BITMAP_TYPE_ANY)
                if exit_bitmap.IsOk():
                    exit_bitmap = self.scale_bitmap(exit_bitmap, 16, 16)  # Масштабируем до 16x16
                    self.exit_item.SetBitmap(exit_bitmap)
                else:
                    logging.error(f"Недопустимый формат иконки выхода: {exit_icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки выхода {exit_icon_path}: {e}")
        else:
            logging.error(f"Иконка выхода не найдена: {exit_icon_path}")
        menu_bar.Append(file_menu, loc.get("menu_file"))

        # Меню "Язык"
        self.language_menu = wx.Menu()
        self.lang_items = {
            "ru": self.language_menu.Append(wx.ID_ANY, loc.get("lang_ru"), kind=wx.ITEM_RADIO),
            "de": self.language_menu.Append(wx.ID_ANY, loc.get("lang_de"), kind=wx.ITEM_RADIO),
            "en": self.language_menu.Append(wx.ID_ANY, loc.get("lang_en"), kind=wx.ITEM_RADIO),
        }
        self.lang_items[LANGUAGE].Check(True)
        # Устанавливаем иконки для пунктов языка
        for lang, item in self.lang_items.items():
            lang_icon_path = os.path.abspath(MENU_ICONS.get(f"lang_{lang}", ""))
            if os.path.exists(lang_icon_path):
                try:
                    lang_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                    if lang_bitmap.IsOk():
                        lang_bitmap = self.scale_bitmap(lang_bitmap, 16, 16)
                        item.SetBitmap(lang_bitmap)
                    else:
                        logging.error(f"Недопустимый формат иконки lang_{lang}: {lang_icon_path}")
                except Exception as e:
                    logging.error(f"Ошибка загрузки иконки lang_{lang} {lang_icon_path}: {e}")
            else:
                logging.error(f"Иконка lang_{lang} не найдена: {lang_icon_path}")
        menu_bar.Append(self.language_menu, loc.get("language_menu"))

        # Меню "Справка"
        help_menu = wx.Menu()
        self.about_item = help_menu.Append(wx.ID_ABOUT, loc.get("menu_about"))  # Сохраняем как атрибут
        # Устанавливаем иконку для пункта "О программе"
        about_icon_path = os.path.abspath(MENU_ICONS.get("about", ""))
        if os.path.exists(about_icon_path):
            try:
                about_bitmap = wx.Bitmap(about_icon_path, wx.BITMAP_TYPE_ANY)
                if about_bitmap.IsOk():
                    about_bitmap = self.scale_bitmap(about_bitmap, 16, 16)
                    self.about_item.SetBitmap(about_bitmap)
                else:
                    logging.error(f"Недопустимый формат иконки about: {about_icon_path}")
            except Exception as e:
                logging.error(f"Ошибка загрузки иконки about {about_icon_path}: {e}")
        else:
            logging.error(f"Иконка about не найдена: {about_icon_path}")
        menu_bar.Append(help_menu, loc.get("menu_help"))

        self.SetMenuBar(menu_bar)

        # Привязываем обработчики
        self.Bind(wx.EVT_MENU, self.on_exit, self.exit_item)
        for lang, item in self.lang_items.items():
            self.Bind(wx.EVT_MENU, self.on_language_change, item)
        self.Bind(wx.EVT_MENU, self.on_about, self.about_item)

    def on_content_menu(self, event):
        """Обработчик выбора пункта меню 'Контент'."""
        content_name = self.content_menu_items.get(event.GetId())
        if content_name:
            self.switch_content(content_name)

    def create_status_bar(self):
        """Создает строку статуса и копирайт."""
        status_panel = wx.Panel(self.panel)
        status_panel.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        status_panel.SetMinSize((-1, 30))
        status_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Строка статуса
        self.status_text = wx.StaticText(status_panel, label=loc.get("status_ready"))
        font = wx.Font(
            STATUS_FONT_SIZE,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL if FONT_TYPE == "normal" else wx.FONTSTYLE_ITALIC,
            wx.FONTWEIGHT_BOLD if FONT_TYPE in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL,
            faceName=FONT_NAME,
        )
        self.status_text.SetFont(font)
        self.status_text.SetForegroundColour(wx.Colour(STATUS_TEXT_COLOR))
        status_sizer.Add(self.status_text, proportion=1, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=5)
        logging.info(f"Строка статуса создана: размер шрифта={STATUS_FONT_SIZE}, цвет={STATUS_TEXT_COLOR}")

        # Копирайт
        self.copyright_text = wx.StaticText(status_panel, label=loc.get("copyright"))
        self.copyright_text.SetFont(font)
        self.copyright_text.SetForegroundColour(wx.Colour(STATUS_TEXT_COLOR))
        status_sizer.Add(self.copyright_text, proportion=0, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        logging.info(f"Копирайт создан: размер шрифта={STATUS_FONT_SIZE}, цвет={STATUS_TEXT_COLOR}")

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
        languages = ["ru", "en", "de"]
        for lang in languages:
            temp_loc = Localization(lang)
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
            self.lang_items["en"].GetId(): "en",
        }
        event_id = event.GetId()
        new_lang = lang_map.get(event_id)
        if new_lang:
            logging.info(f"Смена языка через меню на: {new_lang}")
            loc.set_language(new_lang)
            self.update_language_icon(new_lang)
            self.update_ui()

    def on_change_language(self, event):
        """Обработчик смены языка через значок."""
        current_langs = ["ru", "en", "de"]
        current_index = current_langs.index(loc.language) if loc.language in current_langs else 0
        new_index = (current_index + 1) % len(current_langs)
        new_lang = current_langs[new_index]
        logging.info(f"Смена языка через значок на: {new_lang}")
        loc.set_language(new_lang)
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
                    logging.info(f"Иконка флага обновлена: {lang_icon_path}, размер: {flag_bitmap.GetWidth()}x{flag_bitmap.GetHeight()}")
                else:
                    logging.error(f"Недопустимый формат иконки флага: {lang_icon_path}")
                    self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")
            except Exception as e:
                logging.error(f"Ошибка обновления иконки флага {lang_icon_path}: {e}")
                self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")
        else:
            logging.error(f"Файл иконки флага не найден: {lang_icon_path}")
            self.flag_button = wx.StaticText(self.flag_button.GetParent(), label=f"[{new_lang}]")

        # Обновляем радиокнопки
        for lang, item in self.lang_items.items():
            item.Check(lang == new_lang)

    def update_ui(self):
        """Обновляет текст элементов интерфейса после смены языка."""
        self.SetTitle(loc.get("program_title"))

        if hasattr(self, "title"):
            title_text = loc.get("program_title")
            self.title.SetLabel("")  # временно сбрасываем

            max_width = WINDOW_SIZE[0] - 2 * LOGO_SIZE[0] - 50
            max_height = max(BANNER_HIGH, 20) - 20  # с учётом отступов
            style_flags = {
                "style": wx.FONTSTYLE_NORMAL if FONT_TYPE == "normal" else wx.FONTSTYLE_ITALIC,
                "weight": wx.FONTWEIGHT_BOLD if FONT_TYPE in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL
            }

            optimal_size = fit_text_to_height(
                self.title, title_text, max_width, max_height, FONT_NAME, style_flags
            )

            font = wx.Font(
                optimal_size,
                wx.FONTFAMILY_DEFAULT,
                style_flags["style"],
                style_flags["weight"],
                faceName=FONT_NAME
            )
            self.title.SetFont(font)
            self.title.SetForegroundColour(wx.Colour(BANNER_TEXT_COLOR))
            self.title.SetLabel(title_text)
            self.title.Wrap(max_width)

        self.status_text.SetLabel(loc.get("status_ready"))
        font = wx.Font(
            STATUS_FONT_SIZE,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL if FONT_TYPE == "normal" else wx.FONTSTYLE_ITALIC,
            wx.FONTWEIGHT_BOLD if FONT_TYPE in ["bold", "bolditalic"] else wx.FONTWEIGHT_NORMAL,
            faceName=FONT_NAME,
        )
        self.status_text.SetFont(font)
        self.status_text.SetForegroundColour(wx.Colour(STATUS_TEXT_COLOR))

        self.copyright_text.SetLabel(loc.get("copyright"))
        self.copyright_text.SetFont(font)
        self.copyright_text.SetForegroundColour(wx.Colour(STATUS_TEXT_COLOR))

        self.exit_button.SetLabel(loc.get("button_exit"))
        self.GetMenuBar().SetMenuLabel(0, loc.get("menu_file"))
        self.GetMenuBar().SetMenuLabel(1, loc.get("language_menu"))
        self.GetMenuBar().SetMenuLabel(2, loc.get("menu_help"))

        # Обновляем иконки для пунктов меню языка
        for lang, item in self.lang_items.items():
            item.SetItemLabel(loc.get(f"lang_{lang}"))
            lang_icon_path = os.path.abspath(MENU_ICONS.get(f"lang_{lang}", ""))
            if os.path.exists(lang_icon_path):
                try:
                    lang_bitmap = wx.Bitmap(lang_icon_path, wx.BITMAP_TYPE_ANY)
                    if lang_bitmap.IsOk():
                        lang_bitmap = self.scale_bitmap(lang_bitmap, 16, 16)
                        item.SetBitmap(lang_bitmap)
                    else:
                        logging.error(f"Недопустимый формат иконки lang_{lang} в update_ui: {lang_icon_path}")
                except Exception as e:
                    logging.error(f"Ошибка обновления иконки lang_{lang} {lang_icon_path}: {e}")
            else:
                logging.error(f"Иконка lang_{lang} не найдена в update_ui: {lang_icon_path}")

        # Обновляем текст пунктов подменю
        if self.exit_item:
            self.exit_item.SetItemLabel(loc.get("button_exit"))
            logging.info(f"Обновлён текст пункта меню выхода: {loc.get('button_exit')}")
        if self.about_item:
            self.about_item.SetItemLabel(loc.get("menu_about"))
            logging.info(f"Обновлён текст пункта меню 'О программе': {loc.get('menu_about')}")

        # Обновляем текущую панель контента
        if self.current_content and hasattr(self.current_content, "update_ui_language"):
            try:
                self.current_content.update_ui_language()
            except Exception as e:
                logging.error(f"Ошибка при обновлении языка панели {self.current_content.__class__.__name__}: {e}")
                show_popup(
                    loc.get("error", "Ошибка") + f": {loc.get('error_in_function', 'Ошибка в {}: {}').format('update_ui_language', str(e))}",
                    popup_type="error"
                )

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
        # Освобождаем ресурсы AutoCAD
        if hasattr(self, "cad") and self.cad is not None:
            self.cad.cleanup()
            self.cad = None
        event.Skip()


if __name__ == "__main__":
    app = wx.App()
    window = ATMainWindow()
    window.Show()
    app.MainLoop()
