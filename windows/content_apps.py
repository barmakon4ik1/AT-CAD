"""
windows/content_apps.py
Модуль для создания панели со списком доступных программ.
Отображает текстовые ссылки на программы в один столбец.
"""
import logging
import sys
import wx
import importlib
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

# # Настройка логирования в консоль
# print("Инициализация логирования в content_apps.py")
# logging.getLogger().handlers = []
# logging.getLogger().setLevel(logging.INFO)
# handler = logging.StreamHandler(sys.stdout)
# handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# logging.getLogger().addHandler(handler)
# print(f"content_apps.py: sys.stdout = {sys.stdout}")
# # Дополнительная проверка записи в sys.stdout
# try:
#     sys.stdout.write("Проверка прямого вывода в sys.stdout из content_apps.py\n")
#     sys.stdout.flush()
# except Exception as e:
#     print(f"content_apps.py: Ошибка записи в sys.stdout: {e}")

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
    content_name = "content_apps"

    def __init__(self, parent):
        """
        Инициализирует панель со списком программ.

        Args:
            parent: Родительский wx.Window.
        """
        super().__init__(parent)
        self.links = []
        self.current_panel = None
        self.setup_ui()
        logging.info(f"AppsContentPanel: UI инициализирован с языком {loc.language}")

    def setup_ui(self):
        """
        Настраивает интерфейс с текстовыми ссылками в один столбец.
        """
        if self.GetSizer():
            self.GetSizer().Clear(True)
        self.links.clear()

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSpacer(20)

        link_sizer = wx.BoxSizer(wx.VERTICAL)
        programs = load_content("get_content_menu", self) or []
        logging.info(f"AppsContentPanel: Получены программы: {programs}")

        # Фильтруем content_apps из списка
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

    def on_link_click(self, content_name: str):
        """
        Обрабатывает клик по ссылке, загружая панель контента и вызывая программу построения.

        Args:
            content_name: Имя модуля контента для загрузки (например, 'rings').
        """
        parent = self.GetParent()
        sizer = parent.GetSizer()
        if sizer:
            sizer.Clear(True)

        if content_name == "rings":
            from windows.content_rings import create_window as create_rings_window
            panel = create_rings_window(parent)
        else:
            panel = at_load_content(content_name, parent)

        if not panel:
            logging.error(f"AppsContentPanel: Не удалось загрузить контент {content_name}")
            sizer.Add(create_window(parent), 1, wx.EXPAND)
            parent.Layout()
            return

        self.current_panel = panel
        sizer.Add(self.current_panel, 1, wx.EXPAND)
        parent.Layout()
        logging.info(f"AppsContentPanel: Загружен контент {content_name}")

        def on_submit(data):
            from windows.at_content_registry import CONTENT_REGISTRY
            if not data:
                logging.warning("AppsContentPanel: Пустые данные от on_submit")
                return

            content_info = CONTENT_REGISTRY.get(content_name)
            if not content_info or "build_module" not in content_info:
                logging.error(f"AppsContentPanel: Некорректный CONTENT_REGISTRY для {content_name}")
                return

            build_module = importlib.import_module(content_info["build_module"])
            build_func = getattr(build_module, "main")
            success = build_func(data)
            if success and content_name != "cone":
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
    loc.set_language("en")  # Тестируем с английским языком
    panel = AppsContentPanel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Layout()
    frame.Show()
    app.MainLoop()
