# windows/content_apps.py
"""
Модуль для создания панели со списком доступных программ.
Отображает текстовые ссылки на программы в один столбец.
"""
import wx
import logging
from config.at_config import load_user_settings, DEFAULT_SETTINGS
from windows.at_gui_utils import show_popup
from windows.at_window_utils import BaseContentPanel, get_link_font
from locales.at_localization_class import loc
from windows.at_run_dialog_window import load_content

# Настройка логирования
logging.basicConfig(
    level=logging.ERROR,
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


class AppsContentPanel(BaseContentPanel):
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
        self.links = []  # Список ссылок для последующего обновления
        self.setup_ui()

    def setup_ui(self):
        """
        Настраивает интерфейс с текстовыми ссылками в один столбец.
        """
        # Очищаем существующий sizer, если он есть
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.links.clear()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSpacer(20)

        # Создаём BoxSizer для вертикального размещения ссылок
        link_sizer = wx.BoxSizer(wx.VERTICAL)

        # Получаем список программ из CONTENT_REGISTRY через load_content
        programs = load_content("get_content_menu", self)
        if not programs:
            logging.error("Не удалось загрузить список программ для меню")
            programs = []

        # Обрабатываем programs как список кортежей [(content_name, label_key)]
        for content_name, label_key in programs:
            # Проверяем, что content_name — строка
            if not isinstance(content_name, str):
                logging.warning(f"Нестроковый content_name: {content_name}, преобразование в строку")
                content_name = str(content_name)

            # Проверяем, что label_key — строка
            if not isinstance(label_key, str):
                logging.warning(f"Нестроковый label_key: {label_key}, использование content_name в качестве запасного варианта")
                label_key = content_name

            label = loc.get(label_key, label_key)  # Получаем локализованную метку
            if not isinstance(label, str):
                logging.warning(f"Нестроковый перевод для ключа '{label_key}': {label}, использование значения по умолчанию")
                label = label_key

            link = wx.StaticText(self, label=label, style=wx.ALIGN_LEFT)
            link.SetForegroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))  # Устанавливаем цвет текста
            link.SetFont(get_link_font())  # Устанавливаем шрифт
            link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            link.Bind(wx.EVT_LEFT_DOWN, lambda evt, name=content_name: self.on_link_click(name))
            self.links.append(link)  # Сохраняем ссылку
            link_sizer.Add(link, 0, wx.ALL | wx.ALIGN_LEFT, 10)

        main_sizer.Add(link_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(main_sizer)
        self.Layout()
        logging.info("Интерфейс AppsContentPanel успешно настроен")

    def update_ui_language(self):
        """
        Обновляет текст ссылок при смене языка.
        """
        logging.debug("Обновление языка UI для AppsContentPanel")
        try:
            programs = load_content("get_content_menu", self)
            if not programs:
                logging.error("Не удалось загрузить список программ для обновления языка")
                return

            # Обрабатываем programs как список кортежей [(content_name, label_key)]
            for i, (content_name, label_key) in enumerate(programs):
                # Проверяем, что content_name — строка
                if not isinstance(content_name, str):
                    logging.warning(f"Нестроковый content_name: {content_name}, преобразование в строку")
                    content_name = str(content_name)

                # Проверяем, что label_key — строка
                if not isinstance(label_key, str):
                    logging.warning(f"Нестроковый label_key: {label_key}, использование content_name в качестве запасного варианта")
                    label_key = content_name

                if i < len(self.links):
                    new_label = loc.get(label_key, label_key)
                    if not isinstance(new_label, str):
                        logging.warning(f"Нестроковый перевод для ключа '{label_key}': {new_label}, использование значения по умолчанию")
                        new_label = label_key
                    self.links[i].SetLabel(new_label)
                    self.links[i].SetFont(get_link_font())  # Обновляем шрифт
                    self.links[i].SetForegroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))  # Обновляем цвет

            self.Layout()
            logging.info("Язык UI AppsContentPanel успешно обновлён")
        except Exception as e:
            logging.error(f"Ошибка обновления языка UI: {e}")
            show_popup(loc.get("error", f"Ошибка обновления языка: {str(e)}"), popup_type="error")

    def on_link_click(self, content_name: str):
        """
        Обрабатывает клик по ссылке, переключая содержимое content_panel.

        Args:
            content_name: Имя модуля контента для переключения.
        """
        if not isinstance(content_name, str):
            logging.warning(f"Нестроковый content_name в on_link_click: {content_name}, преобразование в строку")
            content_name = str(content_name)
        self.switch_content_panel(content_name)
