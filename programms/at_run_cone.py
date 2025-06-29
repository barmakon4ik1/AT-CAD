# at_run_cone.py
import pythoncom
from pyautocad import APoint
from at_construction import at_cone_sheet, polar_point, at_addText
from at_cone_input_window import ConeInputWindow  # Импортируем класс напрямую
from typing import Optional, Dict, Any
from at_localization import loc
from at_config import LANGUAGE, TEXT_DISTANCE, TEXT_HEIGHT_BIG, TEXT_HEIGHT_SMALL
from at_gui_utils import show_popup
from at_base import ensure_layer, regen
from at_input import at_point_input
import wx

loc.language = LANGUAGE


def run_application() -> bool:
    """
    Запускает приложение, открывая окно ConeInputWindow в немодальном режиме и выполняя построение развертки конуса.
    Возвращает True, если построение выполнено успешно, False, если пользователь отменил ввод.

    Returns:
        bool: True если выполнено, False если отменено.
    """
    try:
        # Создаём окно ConeInputWindow
        window = ConeInputWindow(parent=None)

        # Переменная для хранения результата
        result = [False]  # Используем список для изменения значения в замыкании

        def on_window_close(evt: wx.CloseEvent) -> None:
            """
            Обрабатывает закрытие окна ConeInputWindow и выполняет построение развертки.
            """
            nonlocal result
            if hasattr(window, 'result') and window.result:
                data = window.result
                try:
                    input_point = data.get('input_point')
                    if input_point is None:
                        raise ValueError("input_point is None: не удалось получить точку ввода")
                    model = data.get("model")
                    if model is None:
                        raise ValueError("model is None: не удалось получить модельное пространство")

                    # Проверка входных данных
                    required_keys = ["diameter_base", "diameter_top", "height", "layer_name",
                                     "order_number", "detail_number", "thickness_text", "material"]
                    for key in required_keys:
                        if key not in data or data[key] is None:
                            raise ValueError(f"Отсутствует или None значение для ключа: {key}")

                    # Создание слоёв
                    for layer in ["LASER-TEXT", "schrift", "TEXT"]:
                        ensure_layer(model, layer)

                    # Построение развертки конуса
                    build_result = at_cone_sheet(
                        model=model,
                        input_point=input_point,
                        diameter_base=data["diameter_base"],
                        diameter_top=data["diameter_top"],
                        height=data["height"],
                        layer_name=data["layer_name"]
                    )
                    if build_result is None:
                        show_popup(loc.get("cone_sheet_error"), popup_type="error")
                        result[0] = True  # Продолжаем цикл, несмотря на ошибку
                        evt.Skip()
                        return

                    k_text = f"{data['order_number']}"
                    if data['detail_number']:
                        k_text += f"-{data['detail_number']}"
                    text_ab = TEXT_DISTANCE
                    text_h = TEXT_HEIGHT_BIG
                    text_s = TEXT_HEIGHT_SMALL
                    text_point = polar_point(input_point, 300, 0)

                    # Список текстов для добавления
                    text_configs = [
                        {
                            "point": input_point,
                            "text": k_text,
                            "layer_name": "LASER-TEXT",
                            "text_height": 7,
                            "text_angle": 0,
                            "text_alignment": 4
                        },
                        {
                            "point": polar_point(input_point, distance=20, alpha=-90),
                            "text": k_text,
                            "layer_name": "schrift",
                            "text_height": text_s,
                            "text_angle": 0,
                            "text_alignment": 4
                        },
                        {
                            "point": text_point,
                            "text": f"Komm.Nr. {k_text}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        },
                        {
                            "point": polar_point(text_point, distance=text_ab, alpha=-90),
                            "text": f"D = {data['diameter_base']} {(loc.get('mm'))}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        },
                        {
                            "point": polar_point(text_point, distance=2 * text_ab, alpha=-90),
                            "text": f"d = {data['diameter_top']} {(loc.get('mm'))}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        },
                        {
                            "point": polar_point(text_point, distance=3 * text_ab, alpha=-90),
                            "text": f"H = {data['height']} {(loc.get('mm'))}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        },
                        {
                            "point": polar_point(text_point, distance=4 * text_ab, alpha=-90),
                            "text": f"Dicke = {data['thickness_text']}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        },
                        {
                            "point": polar_point(text_point, distance=5 * text_ab, alpha=-90),
                            "text": f"Wst: {data['material']}",
                            "layer_name": "TEXT",
                            "text_height": text_h,
                            "text_angle": 0,
                            "text_alignment": 0
                        }
                    ]

                    # Добавление текстов с логированием
                    for i, config in enumerate(text_configs):
                        try:
                            at_addText(
                                model=model,
                                point=config["point"],
                                text=config["text"],
                                layer_name=config["layer_name"],
                                text_height=config["text_height"],
                                text_angle=config["text_angle"],
                                text_alignment=config["text_alignment"]
                            )
                        except Exception as e:
                            show_popup(f"Ошибка при добавлении текста {i + 1} ({config['text']}): {str(e)}",
                                       popup_type="error")
                            raise
                    regen(model)  # Обновление чертежа после добавления всех текстов
                    result[0] = True  # Успешное выполнение
                except Exception as e:
                    show_popup(loc.get("build_error", str(e)), popup_type="error")
                    result[0] = True  # Продолжаем цикл, несмотря на ошибку
            else:
                result[0] = False  # Пользователь нажал "Отмена"
            evt.Skip()

        # Привязываем обработчик закрытия
        window.Bind(wx.EVT_CLOSE, on_window_close)

        # Показываем окно в немодальном режиме
        window.Show()

        # Ждём завершения обработки в главном цикле
        app = wx.GetApp() or wx.App(False)  # Получаем или создаём приложение
        app.MainLoop()  # Запускаем цикл для обработки событий окна

        return result[0]  # Возвращаем результат после закрытия окна
    except Exception as e:
        show_popup(loc.get("error_in_function", "run_application", str(e)), popup_type="error")
        return False  # Ошибка на верхнем уровне, прерываем цикл


if __name__ == "__main__":
    try:
        pythoncom.CoInitialize()  # Инициализация COM один раз
        while True:
            if not run_application():  # Прерываем цикл, если пользователь нажал "Отмена"
                break
    except Exception as e:
        show_popup(loc.get("error_in_main", str(e)), popup_type="error")
    finally:
        try:
            pythoncom.CoUninitialize()  # Освобождение COM в конце
        except Exception as e:
            show_popup(loc.get("com_release_error", str(e)), popup_type="error")
