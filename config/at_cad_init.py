# config/at_cad_init.py
"""
Модуль для инициализации AutoCAD через PyRx.
Предоставляет синглтон для однократного подключения к AutoCAD и доступа к его объектам.
"""

from pyrx import Ap
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


class ATCadInit:
    """
    Класс для инициализации и управления подключением к AutoCAD через PyRx.
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
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Выполняет подключение к AutoCAD через PyRx.

        Attributes:
            acad: Экземпляр приложения AutoCAD (ActiveX).
            adoc: Активный документ AutoCAD.
            model: Модельное пространство (ActiveX ModelSpace).
            original_layer: Исходный активный слой.

        Notes:
            В случае ошибки инициализации показывает всплывающее окно с сообщением.
            Требуется загрузка RxLoader25.1.arx и выполнение команды INIT_CAD в AutoCAD.
        """
        try:
            self.acad = Ap.Application.acadApplication()
            self.acad.visible = True
            self.adoc = self.acad.activeDocument()
            self.model = self.adoc.modelSpace()
            self.original_layer = self.adoc.activeLayer()
        except Exception:
            show_popup(loc.get("cad_init_error_short", "AutoCAD initialization error."), popup_type="error")
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
            self.model = None
            self.adoc = None
            self.original_layer = None
            self.acad = None
        except Exception:
            show_popup(loc.get("com_release_error", "Error releasing AutoCAD resources."), popup_type="error")


@Ap.Command()
def init_cad():
    """
    Пользовательская команда AutoCAD для тестирования инициализации.
    Выполняется в AutoCAD через команду INIT_CAD.
    """
    try:
        cad = ATCadInit()
        show_popup(
            loc.get("cad_init_success", "AutoCAD initialized successfully.") if cad.is_initialized()
            else loc.get("cad_init_error_short", "AutoCAD initialization error."),
            popup_type="success" if cad.is_initialized() else "error"
        )
    except Exception:
        show_popup(loc.get("cad_init_error_short", "AutoCAD initialization error."), popup_type="error")


if __name__ == "__main__":
    """
    Тестирование инициализации AutoCAD при прямом запуске модуля (для отладки вне AutoCAD).
    """
    show_popup(
        loc.get("cad_init_error_short", "AutoCAD initialization error: Run from AutoCAD using INIT_CAD or init_cad.lsp."),
        popup_type="error"
    )
