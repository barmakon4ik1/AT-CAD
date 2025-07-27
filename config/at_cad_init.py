# config/at_cad_init.py
"""
Модуль для инициализации AutoCAD через COM-интерфейс с использованием синглтона.
Обеспечивает однократное подключение к AutoCAD и предоставляет доступ к его объектам.
"""
import win32com.client
import pythoncom
import logging
from locales.at_localization_class import loc

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
        Выполняет подключение к AutoCAD и настройку объектов через win32com.
        Логирует ошибку в случае неудачи, но не показывает всплывающее окно.
        """
        try:
            pythoncom.CoInitialize()  # Инициализация COM
            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True
            self.adoc = self.acad.ActiveDocument
            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer
            logging.info("AutoCAD успешно инициализирован")
        except Exception as e:
            logging.error(f"Ошибка инициализации AutoCAD: {e}")
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

    def cleanup(self):
        """
        Освобождает ресурсы, связанные с AutoCAD.
        """
        try:
            if self.acad is not None:
                self.model = None
                self.adoc = None
                self.original_layer = None
                self.acad = None
                pythoncom.CoUninitialize()
                logging.info("Ресурсы AutoCAD освобождены")
        except Exception as e:
            logging.error(f"Ошибка при освобождении ресурсов AutoCAD: {e}")

    def reinitialize(self):
        """
        Переподключаемся к AutoCAD, если соединение потеряно.
        """
        if not self.is_initialized():
            self._initialized = False
            self._initialize()
            logging.info("AutoCAD переинициализирован")

if __name__ == "__main__":
    """
    Тестирование инициализации AutoCAD при прямом запуске модуля.
    """
    from windows.at_gui_utils import show_popup
    cad = ATCadInit()
    show_popup(loc.get('cad_init_success') if cad.is_initialized() else loc.get('cad_init_error_short'),
               popup_type="success" if cad.is_initialized() else "error")
