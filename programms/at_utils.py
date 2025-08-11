"""
Модуль утилит для работы с AutoCAD (фасад).
"""

import math
from functools import wraps


def handle_errors(func):
    """
    Декоратор для обработки ошибок в функциях.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return None
    return wrapper


def finder(x, r, accuracy):
    '''
    Представление числа x, округленного до знака accuracy через простую дробь из числа в диапазоне от 1 до r
    '''
    a = int(x)
    b = 1
    for i in range(r):
        y = a / b
        if round(y, accuracy) == x:
            print(a, " / ", b, " = ", round(y, accuracy))
            break
        else:
            if y < x:
                a += 1
            else:
                b += 1


if __name__ == '__main__':
    finder(round(math.pi, 6), 10000, 6)
    finder(round(math.sqrt(2), 2), 1000, 4)
    finder(0.6667, 10000, 4)
    finder(0.3333, 10000, 4)
    finder(3.1818, 1000, 4)
