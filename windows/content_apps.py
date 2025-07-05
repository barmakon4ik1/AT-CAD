# windows/content_apps.py
"""
Модуль для создания панели со списком доступных программ.
Отображает текстовые ссылки на программы в несколько колонок.
"""

import wx
import logging
from config.at_config import BACKGROUND_COLOR, LABEL_FONT_COLOR
from windows.at_window_utils import show_popup, get_standard_font, get_link_font
from locales.at_localization import loc
from windows.at_run_dialog_window import load_content

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Создаёт панель со списком программ в виде текстовых ссылок.

    Args:
        parent: Родительский wx.Window (content_panel из ATMainWindow).

    Returns:
        wx.Panel: Панель со списком программ.
    """
    return AppsContentPanel(parent)


class AppsContentPanel(wx.Panel):
    """
    Панель для отображения списка программ в виде текстовых ссылок.
    """
    def __init__(self, parent):
        """
        Инициализирует панель со списком программ.

        Args:
            parent: Родительский wx.Window.
        """
        super().__init__(parent)
        self.SetBackgroundColour(wx.Colour(BACKGROUND_COLOR))
        self.parent = parent
        self.links = []  # Список ссылок для последующего обновления
        self.setup_ui()

    def setup_ui(self):
        """
        Настраивает интерфейс с текстовыми ссылками в несколько колонок.
        """
        # Очищаем существующий sizer, если он есть
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.links.clear()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSpacer(20)

        # Получаем список программ из CONTENT_REGISTRY через load_content
        programs = load_content("get_content_menu", self)
        if not programs:
            logging.error("Не удалось загрузить список программ для меню")
            programs = []

        # Определяем количество колонок (например, 3)
        num_columns = 3
        num_rows = (len(programs) + num_columns - 1) // num_columns

        # Создаём FlexGridSizer для размещения ссылок
        grid_sizer = wx.FlexGridSizer(rows=num_rows, cols=num_columns, vgap=10, hgap=20)

        for content_name, label_key in programs:
            label = loc.get(label_key, label_key)  # Получаем локализованную метку
            link = wx.StaticText(self, label=label, style=wx.ALIGN_LEFT)
            link.SetForegroundColour(wx.Colour(LABEL_FONT_COLOR))  # Устанавливаем цвет текста
            link.SetFont(get_link_font())  # Устанавливаем шрифт
            link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            link.Bind(wx.EVT_LEFT_DOWN, lambda evt, name=content_name: self.on_link_click(name))
            self.links.append(link)  # Сохраняем ссылку
            grid_sizer.Add(link, 0, wx.ALL, 5)

        # Добавляем пустые элементы, если нужно заполнить сетку
        for _ in range(len(programs), num_rows * num_columns):
            grid_sizer.Add(wx.StaticText(self, label=""), 0, wx.ALL, 5)

        main_sizer.Add(grid_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(main_sizer)
        self.Layout()

    def update_ui_language(self):
        """
        Обновляет текст ссылок при смене языка.
        """
        programs = load_content("get_content_menu", self)
        if not programs:
            logging.error("Не удалось загрузить список программ для обновления языка")
            return

        for i, (content_name, label_key) in enumerate(programs):
            if i < len(self.links):
                new_label = loc.get(label_key, label_key)
                self.links[i].SetLabel(new_label)
                self.links[i].SetFont(get_link_font())  # Обновляем шрифт
                self.links[i].SetForegroundColour(wx.Colour(LABEL_FONT_COLOR))  # Обновляем цвет

        self.Layout()

    def on_link_click(self, content_name: str):
        """
        Обрабатывает клик по ссылке, переключая содержимое content_panel.

        Args:
            content_name: Имя модуля контента для переключения.
        """
        main_window = wx.GetTopLevelParent(self)
        if hasattr(main_window, "switch_content"):
            main_window.switch_content(content_name)
            logging.info(f"Переключение на контент: {content_name}")
        else:
            logging.error("Главное окно не имеет метода switch_content")
            show_popup(loc.get("error_switch_content", "Ошибка: невозможно переключить контент"), popup_type="error")
