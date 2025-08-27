"""
windows/content_apps.py
Модуль для создания панели со списком доступных программ.
Отображает текстовые ссылки на программы в один столбец.
"""

import wx
import importlib
from config.at_config import load_user_settings, DEFAULT_SETTINGS
from windows.at_window_utils import BaseContentPanel, get_link_font
from windows.at_run_dialog_window import at_load_content, load_content
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
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


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
        self.current_panel = None  # Для сохранения текущей панели
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
        programs = load_content("get_content_menu", self) or []

        # Обрабатываем programs как список кортежей [(content_name, label_key)]
        for content_name, label_key in programs:
            # Проверяем, что content_name и label_key — строки
            if not isinstance(content_name, str):
                content_name = str(content_name)
            if not isinstance(label_key, str):
                label_key = content_name

            label = loc.get(label_key, label_key)  # Получаем локализованную метку
            if not isinstance(label, str):
                label = label_key

            link = wx.StaticText(self, label=label, style=wx.ALIGN_LEFT)
            link.SetForegroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))
            link.SetFont(get_link_font())
            link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            link.Bind(wx.EVT_LEFT_DOWN, lambda evt, name=content_name: self.on_link_click(name))
            self.links.append(link)
            link_sizer.Add(link, 0, wx.ALL | wx.ALIGN_LEFT, 10)

        main_sizer.Add(link_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.SetSizer(main_sizer)
        self.Layout()

    def update_ui_language(self):
        """
        Обновляет текст ссылок при смене языка.
        """
        programs = load_content("get_content_menu", self) or []
        for i, (content_name, label_key) in enumerate(programs):
            if not isinstance(content_name, str):
                content_name = str(content_name)
            if not isinstance(label_key, str):
                label_key = content_name
            if i < len(self.links):
                new_label = loc.get(label_key, label_key)
                if not isinstance(new_label, str):
                    new_label = label_key
                self.links[i].SetLabel(new_label)
                self.links[i].SetFont(get_link_font())
                self.links[i].SetForegroundColour(wx.Colour(self.settings["LABEL_FONT_COLOR"]))
        self.Layout()

    def on_link_click(self, content_name: str):
        """
        Обрабатывает клик по ссылке, загружая панель контента и вызывая программу построения.

        Args:
            content_name: Имя модуля контента для загрузки (например, 'rings').
        """
        from windows.at_content_registry import CONTENT_REGISTRY
        # Очищаем текущую панель
        parent = self.GetParent()
        sizer = parent.GetSizer()
        if sizer:
            sizer.Clear(True)

        # Загружаем панель
        if content_name == "rings":
            from windows.content_rings import create_window as create_rings_window
            panel = create_rings_window(parent)  # Родитель — wx.Frame, а не self
        else:
            panel = at_load_content(content_name, parent)

        if not panel:
            # Возвращаем начальную панель, если загрузка не удалась
            sizer.Add(create_window(parent), 1, wx.EXPAND)
            parent.Layout()
            return

        # Сохраняем панель как сильную ссылку
        self.current_panel = panel
        # Добавляем панель в sizer
        sizer.Add(self.current_panel, 1, wx.EXPAND)
        parent.Layout()

        # Устанавливаем callback для получения данных
        def on_submit(data):
            from windows.at_content_registry import CONTENT_REGISTRY
            if not data:
                return

            content_info = CONTENT_REGISTRY.get(content_name)
            if not content_info or "build_module" not in content_info:
                return

            build_module = importlib.import_module(content_info["build_module"])
            build_func = getattr(build_module, "main")
            success = build_func(data)
            if success:
                # Возвращаем начальную панель
                sizer = parent.GetSizer()
                if sizer:
                    sizer.Clear(True)
                    new_panel = create_window(parent)
                    sizer.Add(new_panel, 1, wx.EXPAND)
                    parent.Layout()

        self.current_panel.on_submit_callback = on_submit


if __name__ == "__main__":
    """
    Тестовый запуск для проверки панели.
    """
    app = wx.App(False)
    frame = wx.Frame(None, title="Test AppsContentPanel", size=(800, 600))
    panel = AppsContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
