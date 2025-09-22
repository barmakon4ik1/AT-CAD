"""
Файл: windows/content_apps.py

Модуль для создания панели со списком доступных программ.
Эта панель отображает текстовые ссылки (StaticText) в один столбец.
При клике на ссылку управление передаётся главному окну ATMainWindow,
которое вызывает switch_content и переключает отображаемый контент.

Особенности:
- Панель не создаёт вложенные панели самостоятельно.
- Все панели-контенты равноправные: их создание и переключение управляется ATMainWindow.
- Локализация текста выполняется через loc.get и словарь TRANSLATIONS.
"""

import logging
import wx
from windows.at_window_utils import BaseContentPanel, get_link_font
from windows.at_run_dialog_window import load_content
from locales.at_translations import loc

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "at_run_rings": {
        "ru": "Кольца",
        "de": "Ringe",
        "en": "Rings"
    },
    "apps_title": {
        "ru": "Приложения",
        "de": "Anwendungen",
        "en": "Applications"
    },
    "at_run_cone": {
        "ru": "Конус",
        "de": "Kegel",
        "en": "Cone"
    },
    "at_run_plate": {
        "ru": "Лист",
        "de": "Platte",
        "en": "Plate"
    },
    "at_run_heads": {
        "ru": "Днище",
        "de": "Boden",
        "en": "Head"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


def create_window(parent: wx.Window) -> wx.Panel:
    """
    Фабричная функция для создания панели со списком программ.

    Args:
        parent (wx.Window): Родительская панель (обычно content_panel в ATMainWindow).

    Returns:
        wx.Panel: Инициализированный экземпляр AppsContentPanel.
    """
    return AppsContentPanel(parent)


class AppsContentPanel(BaseContentPanel):
    """
    Панель для отображения списка программ в виде текстовых ссылок.
    Эта панель всегда живёт в главном окне как самостоятельный контент.

    Атрибуты:
        content_name (str): Имя контента (используется в CONTENT_REGISTRY).
        links (list): Список ссылок (wx.StaticText), добавленных в панель.
    """
    content_name = "content_apps"

    def __init__(self, parent: wx.Window):
        """
        Инициализирует панель приложений.

        Args:
            parent (wx.Window): Родительский элемент интерфейса.
        """
        super().__init__(parent)
        self.links = []
        self.setup_ui()
        logging.info(f"AppsContentPanel: UI инициализирован с языком {loc.language}")

    def setup_ui(self):
        """
        Строит интерфейс панели: добавляет список ссылок на доступные программы.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.links.clear()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSpacer(20)

        link_sizer = wx.BoxSizer(wx.VERTICAL)

        # Получаем список доступных программ из CONTENT_REGISTRY через load_content
        programs = load_content("get_content_menu", self) or []
        logging.info(f"AppsContentPanel: Получены программы: {programs}")

        # Исключаем саму панель content_apps
        filtered_programs = [(name, label_key) for name, label_key in programs if name != "content_apps"]
        logging.info(f"AppsContentPanel: Отфильтрованные программы: {filtered_programs}")

        for content_name, label_key in filtered_programs:
            if not isinstance(content_name, str):
                content_name = str(content_name)
            if not isinstance(label_key, str):
                label_key = content_name

            label = loc.get(label_key, label_key)
            if not isinstance(label, str):
                label = label_key

            link = wx.StaticText(self, label=label, style=wx.ALIGN_LEFT)
            link.SetForegroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))
            link.SetFont(get_link_font())
            link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            link.Bind(wx.EVT_LEFT_DOWN, lambda evt, name=content_name: self.on_link_click(name))
            self.links.append(link)
            link_sizer.Add(link, 0, wx.ALL | wx.ALIGN_LEFT, 10)
            logging.info(f"AppsContentPanel: Добавлена ссылка: {label} (content_name={content_name}, label_key={label_key})")

        main_sizer.Add(link_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(main_sizer)
        self.GetParent().Layout()
        self.GetParent().Refresh()
        logging.info(f"AppsContentPanel: UI настроен с языком {loc.language}")

    def update_ui_language(self):
        """
        Обновляет тексты интерфейса при смене языка.
        Пересобирает список ссылок с новыми переводами.
        """
        print("[DEBUG] AppsContentPanel.update_ui_language вызван")
        self.setup_ui()

    def on_link_click(self, content_name: str):
        """
        Обрабатывает клик по ссылке и передаёт управление главному окну.

        Args:
            content_name (str): Имя модуля контента для загрузки (например, 'cone').
        """
        print(f"[DEBUG] on_link_click: content_name={content_name}")
        main_window = wx.GetTopLevelParent(self)
        if hasattr(main_window, "switch_content"):
            main_window.switch_content(content_name)
        else:
            print("[DEBUG] main_window не имеет метода switch_content")


if __name__ == "__main__":
    """
    Тестовый запуск для проверки панели.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Test AppsContentPanel", size=(800, 600))
    loc.set_language("en")  # Тестируем с английским языком
    panel = AppsContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
