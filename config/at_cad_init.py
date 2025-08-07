# config/at_cad_init.py
"""
Файл: at_cad_init.py
Путь: config/at_cad_init.py

Описание:
Модуль для инициализации AutoCAD через COM (win32com). Проверяет подключение к AutoCAD,
автоматически создаёт предопределённые слои и предоставляет синглтон для доступа к приложению.
"""

import win32com.client
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup
from config.at_config import LAYER_DATA


class ATCadInit:
    """
    Класс для инициализации и управления подключением к AutoCAD через COM.
    Реализует паттерн синглтон для однократной инициализации.
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
        Выполняет подключение к AutoCAD через COM и создаёт предопределённые слои.

        Attributes:
            acad: Экземпляр приложения AutoCAD (Application).
            adoc: Активный документ AutoCAD (Document).
            model: Модельное пространство AutoCAD (ModelSpace).
            original_layer: Исходный активный слой.

        Notes:
            В случае ошибки инициализации показывает всплывающее окно с сообщением.
            Создаёт слои из LAYER_DATA после инициализации документа.
        """
        try:
            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True
            self.adoc = self.acad.ActiveDocument
            if self.adoc is None:
                raise Exception(loc.get("cad_init_error_short", "AutoCAD initialization error."))
            self.model = self.adoc.ModelSpace
            self.original_layer = self.adoc.ActiveLayer
            # Создание предопределённых слоёв
            if not self._create_layers():
                raise Exception(loc.get("create_layer_error", "Failed to create predefined layers."))
        except Exception as e:
            show_popup(
                loc.get("cad_init_error_short", f"AutoCAD initialization error: {str(e)}"),
                popup_type="error"
            )
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
        return self.acad is not None and self.adoc is not None and self.model is not None

    def _create_layers(self) -> bool:
        """
        Создает предопределенные слои в AutoCAD с заданными параметрами.

        Returns:
            bool: True, если слои созданы, False при ошибке.
        """
        try:
            layers = self.adoc.Layers
            for layer in LAYER_DATA:
                layer_name = layer["name"]
                if layer_name not in [l.Name for l in layers]:
                    new_layer = layers.Add(layer_name)
                    new_layer.Color = layer["color"]
                    new_layer.Linetype = layer["linetype"]
                    if "lineweight" in layer:
                        new_layer.Lineweight = int(layer["lineweight"] * 100)
                    if "plot" in layer:
                        new_layer.Plottable = layer["plot"]
                    show_popup(
                        loc.get("layer_created", "Layer '{}' created.").format(layer_name),
                        popup_type="info"
                    )
            return True
        except Exception as e:
            show_popup(
                loc.get("create_layer_error", f"Error creating layers: {str(e)}"),
                popup_type="error"
            )
            return False


if __name__ == "__main__":
    """
    Тестирование инициализации AutoCAD при прямом запуске модуля.
    """
    cad = ATCadInit()
    if not cad.is_initialized():
        show_popup(
            loc.get("cad_init_error_short", "AutoCAD initialization error."),
            popup_type="error"
        )
    else:
        show_popup(
            loc.get("cad_init_success", "AutoCAD initialized successfully."),
            popup_type="success"
        )
