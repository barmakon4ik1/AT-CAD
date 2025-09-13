"""
programms/at_shell.py
Программа отрисовки развертки цилиндра с нанесением осей, текста и размеров
"""

import math

from config.at_cad_init import ATCadInit
from locales.at_translations import loc
from programms.at_base import regen
from programms.at_construction import add_text
from programms.at_geometry import ensure_point_variant, get_unwrapped_points, offset_point
from programms.at_input import at_point_input


def at_shell():
    from at_construction import add_rectangle, add_line, add_dimension

    cad = ATCadInit()
    adoc = cad.document
    model = cad.model

    diameter = 500
    width, height = math.pi * diameter, 1000
    a_deg = 40.6

    input_point_list = at_point_input(adoc, prompt=loc.get("select_point", "Укажите левый нижний угол"), as_variant=False)
    input_point = ensure_point_variant(input_point_list)

    # Нарисовать прямоугольник развертки
    add_rectangle(model, input_point, width, height)

    # Получить точки для углов на развертке цилиндра
    points = get_unwrapped_points(D=diameter, L=height, A_deg=a_deg, clockwise=False)

    # Точки для размерных линий
    end_point = offset_point(input_point, width, height)
    top_point = offset_point(input_point, 0, height)

    # Размеры
    add_dimension(adoc, "H", top_point, end_point, offset=200)
    add_dimension(adoc, "V", input_point, top_point, offset=80)

    drawn_x = set()  # будем помнить, какие линии уже проведены
    # Отрисовка осей
    for angle, x, y in points:
        # пропускаем 360°, чтобы не дублировать 0°
        if angle == 360:
            continue

        base_x = input_point_list[0] + x
        base_y = input_point_list[1] + y

        # если по этому X линия уже нарисована – пропускаем
        if round(base_x, 6) in drawn_x:
            continue
        drawn_x.add(round(base_x, 6))

        point1 = [base_x, base_y]
        point2 = [base_x, base_y + height]
        point_text = [base_x, base_y - 60]
        point_text2 = [base_x + width, base_y - 60]

        # Форматируем угол: если целое — без дробной части, иначе с одной
        angle_text = f"{int(angle)}°" if angle.is_integer() else f"{angle:.1f}°"

        if angle == a_deg:
            # правая граница: только подпись (слева и справа)
            add_text(model, point_text, angle_text, layer_name="AM_5")
            add_text(model, point_text2, angle_text, layer_name="AM_5")

        else:
            # остальные углы: линия + подпись
            add_line(model, point1, point2, layer_name="AM_5")
            add_text(model, point_text, angle_text, layer_name="AM_5")

        # print(f"Угол: {angle:.1f}°, X: {base_x:>7.2f}, Y: {base_y}")

    regen(adoc)


if __name__ == "__main__":
    at_shell()