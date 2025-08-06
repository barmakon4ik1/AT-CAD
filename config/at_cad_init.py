# config/at_cad_init.py
"""
Модуль для инициализации AutoCAD через .NET API с использованием PythonNET.
Предоставляет синглтон для однократного подключения к AutoCAD и доступа к его объектам.
"""

import clr
import sys
import os
import pythonnet
from pathlib import Path
from config.at_config import ACAD_PATH
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup

# Отладочный вывод
try:
    pythonnet_version = getattr(pythonnet, '__version__', 'Unknown')
except AttributeError:
    pythonnet_version = 'Unknown'
print(f"PythonNET version: {pythonnet_version}")
print(f"Python architecture: {sys.maxsize > 2**32}")
print(f"ACAD_PATH: {ACAD_PATH}")
required_dlls = ["acmgd.dll", "acdbmgd.dll", "accore.dll"]
for dll in required_dlls:
    dll_path = os.path.join(ACAD_PATH, dll) if ACAD_PATH else "N/A"
    print(f"{dll} exists: {os.path.exists(dll_path) if ACAD_PATH else False} at {dll_path}")

# Проверяем, что путь к AutoCAD найден и содержит все необходимые DLL
if not ACAD_PATH or not all(os.path.exists(os.path.join(ACAD_PATH, dll)) for dll in required_dlls):
    show_popup(
        loc.get("cad_init_error_short", f"AutoCAD not found or missing DLLs in path: {ACAD_PATH}"),
        popup_type="error"
    )
else:
    # Добавляем ACAD_PATH в sys.path и PATH для загрузки зависимостей
    sys.path.append(ACAD_PATH)
    os.environ["PATH"] = f"{ACAD_PATH};{os.environ.get('PATH', '')}"
    print(f"Updated PATH: {os.environ['PATH']}")
    try:
        # Проверяем, загружается ли clr
        print("Attempting to load acmgd.dll...")
        clr.AddReference("acmgd")
        print("acmgd.dll loaded successfully.")
        clr.AddReference("acdbmgd")
        print("acdbmgd.dll loaded successfully.")
        from Autodesk.AutoCAD.ApplicationServices import Application
        from Autodesk.AutoCAD.DatabaseServices import *
        print("AutoCAD .NET API imported successfully.")
    except Exception as e:
        show_popup(
            loc.get("cad_init_error_short", f"Failed to load AutoCAD libraries: {str(e)}"),
            popup_type="error"
        )
        raise

class ATCadInit:
    """
    Класс для инициализации и управления подключением к AutoCAD через .NET API.
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
        Выполняет подключение к AutoCAD через .NET API.

        Attributes:
            acad: Экземпляр приложения AutoCAD (DocumentManager).
            adoc: Активный документ AutoCAD (Document).
            model: Модельное пространство (BlockTableRecord).
            original_layer: Исходный активный слой (LayerTableRecord).

        Notes:
            В случае ошибки инициализации показывает всплывающее окно с сообщением.
            Требуется, чтобы AutoCAD 2026 был запущен, а библиотеки acmgd.dll и acdbmgd.dll доступны.
        """
        if not ACAD_PATH or not all(os.path.exists(os.path.join(ACAD_PATH, dll)) for dll in required_dlls):
            self.acad = None
            self.adoc = None
            self.model = None
            self.original_layer = None
            return

        try:
            # Получаем активное приложение AutoCAD
            self.acad = Application.DocumentManager
            self.adoc = self.acad.MdiActiveDocument
            if self.adoc is None:
                raise Exception("No active AutoCAD document found.")

            # Получаем базу данных и модельное пространство
            db = self.adoc.Database
            with db.TransactionManager.StartTransaction() as t:
                block_table = t.GetObject(db.BlockTableId, OpenMode.ForRead)
                self.model = t.GetObject(block_table[BlockTableRecord.ModelSpace], OpenMode.ForWrite)
                self.original_layer = t.GetObject(db.Clayer, OpenMode.ForRead)
                t.Commit()

            # Устанавливаем видимость приложения (аналог acad.visible = True)
            Application.MainWindow.Visible = True

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
            show_popup(
                loc.get("com_release_error", "Error releasing AutoCAD resources."),
                popup_type="error"
            )


def init_cad():
    """
    Пользовательская команда для тестирования инициализации AutoCAD.
    Выполняется как внешний скрипт или через .NET-плагин в AutoCAD.
    """
    try:
        cad = ATCadInit()
        show_popup(
            loc.get("cad_init_success", "AutoCAD initialized successfully.") if cad.is_initialized()
            else loc.get("cad_init_error_short", "AutoCAD initialization error."),
            popup_type="success" if cad.is_initialized() else "error"
        )
    except Exception as e:
        show_popup(
            loc.get("cad_init_error_short", f"AutoCAD initialization error: {str(e)}"),
            popup_type="error"
        )


if __name__ == "__main__":
    """
    Тестирование инициализации AutoCAD при прямом запуске модуля (для отладки вне AutoCAD).
    """
    show_popup(
        loc.get("cad_init_error_short", "AutoCAD initialization error: Run from AutoCAD or as a .NET plugin."),
        popup_type="error"
    )
