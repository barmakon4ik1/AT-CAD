"""
Главный модуль для запуска приложения.
Открывает диалоговое окно для ввода параметров днища и выполняет построение в AutoCAD.
"""

import pythoncom
from at_addhead import at_add_head
from windows.at_run_dialog_window import at_run_dialog_window
from typing import Optional, Dict, Any

from at_localization import loc
from at_config import LANGUAGE

loc.language = LANGUAGE


def run_application() -> None:
    """
    Запускает приложение, открывая диалоговое окно и выполняя построение днища.

    Returns:
        None
    """
    try:
        # Запуск диалогового окна для получения параметров
        data: Optional[Dict[str, Any]] = at_run_dialog_window("at_head_input_window")

        if data:
            # Построение днища с использованием переданных параметров
            try:
                result = at_add_head(
                    D=data["D"],
                    s=data["s"],
                    R=data["R"],
                    r=data["r"],
                    h1=data["h1"],
                    insert_point=data["insert_point"],
                    layer=data["layer"],
                    adoc=data["adoc"]  # Передача существующего объекта AutoCAD
                )
                if result is None:
                    print(loc.get("head_build_error"))  # Локализованное сообщение
            except Exception as e:
                print(loc.get("build_error", str(e)))  # Локализованное сообщение с параметром
        else:
            print(loc.get("no_input_data"))  # Локализованное сообщение
    except Exception as e:
        print(loc.get("error_in_function", "run_application", str(e)))  # Локализованное сообщение
    finally:
        try:
            # Освобождение COM-объекта AutoCAD
            pythoncom.CoUninitialize()
        except Exception as e:
            print(loc.get("com_release_error", str(e)))  # Локализованное сообщение


if __name__ == "__main__":
    """
    Точка входа в приложение.
    """
    run_application()
