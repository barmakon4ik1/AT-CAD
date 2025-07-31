import wx
import logging
from locales.at_localization_class import loc
from windows.at_gui_utils import show_popup


def update_status_bar_point_selected(parent: wx.Window, point: object = None) -> None:
    """
    Обновляет строку состояния главного окна, отображая координаты выбранной точки или сообщение о её отсутствии.

    Args:
        parent: Родительский wx.Window (панель контента).
        point: Объект точки с атрибутами x, y (или None, если точка не выбрана).
    """
    try:
        main_window = wx.GetTopLevelParent(parent)
        if hasattr(main_window, "status_text"):
            if point and hasattr(point, "x") and hasattr(point, "y"):
                main_window.status_text.SetLabel(
                    loc.get("point_selected", "Точка выбрана: x={:.2f}, y={:.2f}").format(point.x, point.y)
                )
                logging.info(f"Обновлена строка состояния: точка x={point.x}, y={point.y}")
            else:
                main_window.status_text.SetLabel(loc.get("no_point_selected", "Точка не выбрана"))
                logging.info("Обновлена строка состояния: точка не выбрана")
        else:
            logging.warning("Главное окно не имеет атрибута status_text")
    except Exception as e:
        logging.error(f"Ошибка обновления строки состояния: {e}")
        show_popup(loc.get("error", f"Ошибка обновления строки состояния: {str(e)}"), popup_type="error")
