# at_cad_init.py
"""
Модуль для инициализации AutoCAD через COM-интерфейс с использованием синглтона.
Обеспечивает однократное подключение к AutoCAD и предоставляет доступ к его объектам.
"""

from pyautocad import Autocad
from windows.at_gui_utils import show_popup
from config.at_config import LANGUAGE
from locales.at_localization import loc

loc.language = LANGUAGE  # Установка языка локализации из конфигурации


class ATCadInit:
    """
    Класс для инициализации и управления подключением к AutoCAD.
    Реализует паттерн синглтон для предотвращения множественной инициализации.
    """
    _instance = None

    def __new__(cls):
        """
        Гарантирует создание только одного экземпляра класса.

        Returns:
            ATCadInit: Единственный экземпляр класса.
        """
        if cls._instance is None:
            cls._instance = super(ATCadInit, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Инициализирует подключение к AutoCAD, если оно еще не выполнено.
        """
        if not self._initialized:
            self.acad = None  # Экземпляр AutoCAD
            self.adoc = None  # Активный документ
            self.model = None  # Модельное пространство
            self.original_layer = None  # Исходный активный слой
            self._initialize()
            self._initialized = True

    def _initialize(self):
        """
        Выполняет подключение к AutoCAD и настройку объектов.
        В случае ошибки показывает всплывающее окно с сообщением.
        """
        try:
            self.acad = Autocad(create_if_not_exists=True)  # Подключение или запуск AutoCAD
            self.adoc = self.acad.ActiveDocument
            self.model = self.acad.model
            self.original_layer = self.adoc.ActiveLayer
        except Exception:
            show_popup(loc.get('cad_init_error'), popup_type="error")
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None

    def is_initialized(self):
        """
        Проверяет, успешно ли инициализирован AutoCAD.

        Returns:
            bool: True, если AutoCAD готов к работе, иначе False.
        """
        return self.model is not None and self.adoc is not None


if __name__ == "__main__":
    """
    Тестирование инициализации AutoCAD при прямом запуске модуля.
    """
    cad = ATCadInit()
    show_popup(loc.get('cad_init_success') if cad.is_initialized() else loc.get('cad_init_error_short'),
               popup_type="success" if cad.is_initialized() else "error")
