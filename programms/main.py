# main.py

def get_input_data(window_title: str, window_func) -> dict:
    """
    Функция-оболочка: принимает название окна и функцию, возвращает словарь.

    Args:
        window_title (str): Название окна.
        window_func: Функция, которая принимает название окна и возвращает словарь.

    Returns:
        dict: Словарь, возвращенный функцией window_func.
    """
    return window_func(window_title)
