# at_rectangle.py
from at_gui_utils import show_popup
from at_utils import *
try:
    from at_config import RECTANGLE_LAYER
except ImportError:
    RECTANGLE_LAYER = "0"


def main():
    logger = AtLogging(console_output=True)  # Включаем консольный вывод для отладки

    # Инициализация AutoCAD
    logger.info("Инициализация AutoCAD...")
    cad_objects = init_autocad()
    if cad_objects is None:
        logger.error("Не удалось инициализировать AutoCAD")
        return
    adoc, model, original_layer = cad_objects
    logger.info(f"adoc: {adoc}, model: {model}, original_layer: {original_layer.Name}")

    # Проверяем состояние слоев
    logger.info(f"Доступные слои: {[layer.Name for layer in adoc.Layers]}")

    # Параметры прямоугольника
    insert_point = APoint(0, 0)  # Точка вставки (левый нижний угол)
    width = 100.0  # Ширина
    height = 50.0  # Высота
    layer_name = RECTANGLE_LAYER
    points_list = add_rectangle_points(insert_point, width, height, point_direction="left_bottom)")

    # Построение прямоугольника
    logger.info(f"Создание прямоугольника: точка=({insert_point.x}, {insert_point.y}), ширина={width}, высота={height}, слой={layer_name}")
    try:
        with layer_context(adoc, layer_name):
            ensure_layer(adoc, layer_name)
            add_rectangle(model, points_list, layer_name="0")
            logger.info(loc.get('rectangle_success', width, height))
    except Exception as e:
        logger.error(f"Ошибка построения прямоугольника: {str(e)}")
        show_popup(f"{loc.get('rectangle_error')}: {str(e)}", popup_type="error")
        return

    # Обновляем вид
    try:
        logger.info("Обновление вида...")
        regen(adoc)
    except Exception as e:
        logger.error(f"Ошибка обновления вида: {str(e)}")
        show_popup(loc.get('regen_error'), popup_type="error")
        return


if __name__ == "__main__":
    main()