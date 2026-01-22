"""
programs/at_ringe.py
Модуль для построения колец в AutoCAD на основе данных из диалогового окна.
Создаёт окружности с заданными диаметрами и добавляет текстовые метки с номером работы.
"""

from win32com.client import VARIANT
from config.at_cad_init import ATCadInit
from config.at_config import DEFAULT_CIRCLE_LAYER, DEFAULT_DIM_OFFSET
from locales.at_translations import loc
from programs.at_construction import add_circle, add_text, AccompanyText
from programs.at_base import layer_context, regen
from programs.at_geometry import ensure_point_variant
from programs.at_input import at_get_point
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "no_data_error": {
        "ru": "Данные не введены",
        "de": "Keine Daten eingegeben",
        "en": "No data provided"
    },
    "no_diameters": {
        "ru": "Не указаны диаметры",
        "de": "Keine Durchmesser angegeben",
        "en": "No diameters specified"
    },
    "no_center": {
        "ru": "Не указана центральная точка или модель",
        "de": "Kein Mittelpunkt oder Modell angegeben",
        "en": "No center point or model specified"
    },
    "build_success": {
        "ru": "Кольца успешно построены",
        "de": "Ringe erfolgreich erstellt",
        "en": "Rings successfully built"
    },
    "build_error": {
        "ru": "Ошибка построения колец: {}",
        "de": "Fehler beim Erstellen der Ringe: {}",
        "en": "Error building rings: {}"
    },
    "point_conversion_error": {
        "ru": "Ошибка преобразования точки: {}",
        "de": "Fehler bei der Punktkonvertierung: {}",
        "en": "Point conversion error: {}"
    },
    "mm": {
        "ru": "мм",
        "de": "mm",
        "en": "mm"
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)


def main(ring_data: dict = None) -> bool:
    """
    Основная функция для построения колец в AutoCAD.

    Args:
        ring_data: Словарь с данными колец (work_number, diameters, input_point).

    Returns:
        bool: True при успешном выполнении, None при прерывании (отмена) или ошибке.
    """
    # Инициализация AutoCAD
    cad = ATCadInit()
    adoc = cad.document
    model = cad.model_space
    center = at_get_point(
        adoc,
        as_variant=False,
        prompt="Выберите точку вставки"
    )

    # Проверка данных
    if not ring_data:
        show_popup(loc.get("no_data_error", "Данные не введены"), popup_type="error")
        return None

    ring_data["insert_point"] = center
    # Извлекаем данные
    work_number = ring_data.get("order", "")
    detail = ring_data.get("detail", "")
    material = ring_data.get("material", "")
    thickness = ring_data.get("thickness", "")
    diameters = ring_data.get("diameters", {})
    if not diameters:
        show_popup(loc.get("no_diameters", "Не указаны диаметры"), popup_type="error")
        return None

    # Преобразуем центр в VARIANT
    try:
        center_variant = ensure_point_variant(center)
    except Exception as e:
        show_popup(
            loc.get("point_conversion_error", "Ошибка преобразования точки: {}").format(str(e)),
            popup_type="error"
        )
        return None

    # Построение окружностей
    try:
        with layer_context(adoc, DEFAULT_CIRCLE_LAYER):
            for diameter_value in diameters.values():
                if not isinstance(diameter_value, (int, float)) or diameter_value <= 0:
                    show_popup(loc.get("no_diameters", "Не указаны диаметры"), popup_type="error")
                    return None
                radius = diameter_value / 2.0
                add_circle(model, center_variant, radius, DEFAULT_CIRCLE_LAYER)
    except Exception as e:
        show_popup(loc.get("build_error", "Ошибка построения колец: {}").format(str(e)), popup_type="error")
        return None

    # Добавление текста
    if work_number:  # Добавляем текст только если work_number не пустой
        try:
            # Вычисление позиций текста на основе диаметров
            sorted_radii = sorted([d / 2.0 for d in diameters.values()], reverse=True)
            max_radius = sorted_radii[0]
            second_radius = sorted_radii[1] if len(sorted_radii) > 1 else 0
            y_offset = max_radius - (max_radius - second_radius) * 0.5
            p1 = [center[0], center[1] + y_offset, 0]
            p2 = [center[0], center[1] - y_offset, 0]
            p3 = [center[0], center[1]  + max_radius + DEFAULT_DIM_OFFSET + 20, 0]
            p1_variant = ensure_point_variant(p1)
            p2_variant = ensure_point_variant(p2)
            p3_variant = ensure_point_variant(p3)

            # Добавление текста с использованием add_text из at_construction.py
            non_laser_text = f'{work_number}-{detail}'
            add_text(model, p1_variant, text=work_number, layer_name="LASER-TEXT", text_height=7)
            add_text(model, p2_variant, text=non_laser_text, layer_name="schrift", text_height=30)

            AccompanyText({
                "thickness": thickness,
                "material": material,
            }).draw(model, p3_variant, text_alignment=4)

        except Exception as e:
            show_popup(loc.get("build_error", "Ошибка построения колец: {}").format(str(e)), popup_type="error")
            return None

    # Обновляем вид
    regen(adoc)
    return True


if __name__ == "__main__":
    """
    Точка входа в приложение. Для тестирования напрямую (не рекомендуется).
    """
    try:
        # Для тестирования можно передать тестовые данные
        test_data = {
            "order": "TEST123",
            "detail": "1",
            "material": "1.4301",
            "thickness": 3,
            "diameters": {"1": 100, "2": 200},
            "input_point": [0, 0, 0]  # Изменено с insert_point на input_point
        }
        main(test_data)
    except Exception as e:
        show_popup(loc.get("build_error", "Ошибка построения колец: {}").format(str(e)), popup_type="error")
