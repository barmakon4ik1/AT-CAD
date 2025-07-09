# locales/at_localization.py
"""
Модуль для локализации текстовых сообщений в проекте.
Поддерживает переводы на русский, немецкий и английский языки.
"""

from typing import Union
import logging
from config.at_config import LANGUAGE


# Настройка логирования для отладки
logging.basicConfig(
    level=logging.ERROR,
    filename="at_cad.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

translations = {
    "about_text": {
        "ru": "Информация о программе AT-CAD...",
        "de": "Informationen über das Programm AT-CAD...",
        "en": "Information about the AT-CAD program..."
    },
    "allowance_non_negative": {
        "ru": "Припуск на сварку не может быть отрицательной.",
        "de": "Schweißnahtzugabe darf nicht negativ sein.",
        "en": "Weld allowance cannot be negative."
    },
    "angle_range_error": {
        "ru": "Недопустимый диапазон углов!",
        "de": "Unzulässiger Winkelbereich!",
        "en": "Invalid angle range!"
    },
    "at_run_cone": {
        "ru": "Развертка прямого конуса",
        "de": "Abwicklung eines geraden Kegels",
        "en": "Straight cone sheet"
    },
    "at_run_heads": {
        "ru": "Выпуклые днища",
        "de": "Konvexe Böden",
        "en": "Convex heads"
    },
    "at_run_rings": {
        "ru": "Кольца",
        "de": "Ringe",
        "en": "Rings"
    },
    "autocad_activated": {
        "ru": "Окно AutoCAD активировано.",
        "de": "AutoCAD-Fenster aktiviert.",
        "en": "AutoCAD window activated."
    },
    "autocad_activation_error": {
        "ru": "Ошибка активации окна AutoCAD: {}",
        "de": "Fehler bei der Aktivierung des AutoCAD-Fensters: {}",
        "en": "Error activating AutoCAD window: {}"
    },
    "autocad_window_not_found": {
        "ru": "Окно AutoCAD не найдено.",
        "de": "AutoCAD-Fenster nicht gefunden.",
        "en": "AutoCAD window not found."
    },
    "both_parameters_error": {
        "ru": "Требуется только один параметр!",
        "de": "Nur ein Parameter erforderlich!",
        "en": "Only one parameter is required!"
    },
    "bottom_allowance_label": {
        "ru": "Припуск снизу, мм",
        "de": "Zugabe unten, mm",
        "en": "Bottom allowance, mm"
    },
    "build": {
        "ru": "Построить",
        "de": "Erstellen",
        "en": "Build"
    },
    "build_error": {
        "ru": "Ошибка построения: {}",
        "de": "Fehler beim Erstellen: {}",
        "en": "Build error: {}"
    },
    "button_exit": {
        "ru": "&Выйти",
        "de": "&Beenden",
        "en": "&Exit"
    },
    "cad_init_error": {
        "ru": "Ошибка инициализации AutoCAD.",
        "de": "Fehler bei der Initialisierung von AutoCAD.",
        "en": "Error initializing AutoCAD."
    },
    "cad_init_error_details": {
        "ru": "Ошибка при подключении к AutoCAD: {}",
        "de": "Fehler beim Verbinden mit AutoCAD: {}",
        "en": "Error connecting to AutoCAD: {}"
    },
    "cad_init_error_short": {
        "ru": "Ошибка инициализации AutoCAD.",
        "de": "AutoCAD-Initialisierungsfehler.",
        "en": "AutoCAD initialization error."
    },
    "cad_init_success": {
        "ru": "AutoCAD инициализирован успешно.",
        "de": "AutoCAD erfolgreich initialisiert.",
        "en": "AutoCAD initialized successfully."
    },
    "cancel_button": {
        "ru": "Отмена",
        "de": "Abbrechen",
        "en": "Cancel"
    },
    "circle_error": {
        "ru": "Ошибка при построении окружностей.",
        "de": "Fehler beim Erstellen von Kreisen.",
        "en": "Error creating circles."
    },
    "circle_success": {
        "ru": "Построена окружность с диаметром {} мм.",
        "de": "Kreis mit Durchmesser {} mm erstellt.",
        "en": "Circle created with diameter {} mm."
    },
    "clear_button": {
        "ru": "Очистить",
        "de": "Löschen",
        "en": "Clear"
    },
    "clockwise_label": {
        "ru": "По часовой стрелке",
        "de": "Im Uhrzeigersinn",
        "en": "Clockwise"
    },
    "com_release_error": {
        "ru": "Ошибка при освобождении COM: {}",
        "de": "Fehler beim Freigeben von COM: {}",
        "en": "Error releasing COM: {}"
    },
    "cone_sheet_error": {
        "ru": "Ошибка построения развертки конуса.",
        "de": "Fehler beim Erstellen der Kegelabwicklung.",
        "en": "Error creating cone sheet."
    },
    "copyright": {
        "ru": "Дизайн и разработка: А.Тутубалин © 2025",
        "de": "Design und Entwicklung: A.Tutubalin © 2025",
        "en": "Design and development: A.Tutubalin © 2025"
    },
    "counterclockwise_label": {
        "ru": "Против часовой стрелки",
        "de": "Gegen den Uhrzeigersinn",
        "en": "Counterclockwise"
    },
    "diameter": {
        "ru": "Диаметр",
        "de": "Durchmesser",
        "en": "Diameter"
    },    "diameters": {
        "ru": "Диаметры",
        "de": "Durchmesser",
        "en": "Diameters"
    },
    "diameter_base_positive": {
        "ru": "Диаметр D должен быть положительным!",
        "de": "Durchmesser D muss positiv sein!",
        "en": "Diameter D must be positive!"
    },
    "diameter_column_label": {
        "ru": "Диаметр, мм",
        "de": "Durchmesser, mm",
        "en": "Diameter, mm"
    },
    "diameter_invalid_number": {
        "ru": "Недопустимое число в строке {0}",
        "de": "Ungültige Zahl in Zeile {0}",
        "en": "Invalid number in row {0}"
    },
    "diameter_invalid_separator": {
        "ru": "Недопустимый формат разделителя в строке {0}",
        "de": "Ungültiges Trennzeichenformat in Zeile {0}",
        "en": "Invalid separator format in row {0}"
    },
    "diameter_label": {
        "ru": "Диаметр",
        "de": "Durchmesser",
        "en": "Diameter"
    },
    "diameters_label": {
        "ru": "Диаметры (через запятую)",
        "de": "Durchmesser (durch Kommas getrennt)",
        "en": "Diameters (separated by commas)"
    },
    "diameter_missing_error": {
        "ru": "Не введён ни один диаметр",
        "de": "Kein Durchmesser eingegeben",
        "en": "No diameter entered"
    },
    "diameter_positive_error": {
        "ru": "Ошибка: Диаметр должен быть положительным",
        "de": "Fehler: Durchmesser muss positiv sein",
        "en": "Error: Diameter must be positive"
    },
    "diameter_result_positive_error": {
        "ru": "Ошибка: Средний диаметр должен быть положительным",
        "de": "Fehler: Mittlerer Durchmesser muss positiv sein",
        "en": "Error: Mean diameter must be positive"
    },
    "diameter_top_non_negative": {
        "ru": "Диаметр d должен быть положительным!",
        "de": "Durchmesser d muss positiv sein!",
        "en": "Diameter d must be positive!"
    },
    "dia_error": {
        "ru": "Какой диаметр задан?",
        "de": "Welcher Durchmesser wurde angegeben?",
        "en": "Which diameter was specified?"
    },
    "error": {
        "ru": "Ошибка",
        "de": "Fehler",
        "en": "Error"
    },
    "error_in_function": {
        "ru": "Ошибка в '{}': {}",
        "de": "Fehler in '{}': {}",
        "en": "Error in '{}': {}"
    },
    "fittings_placeholder_label": {
        "ru": "Параметры штуцеров и отводов (будет реализовано позже)",
        "de": "Parameter für Anschlüsse und Abzweige (wird später implementiert)",
        "en": "Fittings and branches parameters (to be implemented later)"
    },
    "fittings_tab_label": {
        "ru": "Штуцеры и отводы",
        "de": "Anschlüsse und Abzweige",
        "en": "Fittings and branches"
    },
    "gradient_plus": {
        "ru": "Наклон должен быть положительным числом!",
        "de": "Die Neigung muss eine positive Zahl sein!",
        "en": "Gradient must be a positive number!"
    },
    "head_built": {
        "ru": "Днище построено!",
        "de": "Boden erstellt!",
        "en": "Head created!"
    },
    "head_build_error": {
        "ru": "Ошибка построения в at_add_head",
        "de": "Fehler beim Erstellen in at_add_head",
        "en": "Error building in at_add_head"
    },
    "head_type_label": {
        "ru": "Тип днища:",
        "de": "Bodentyp:",
        "en": "Head type:"
    },
    "heads_error": {
        "ru": "Ошибка построения днища.",
        "de": "Fehler beim Erstellen des Bodens.",
        "en": "Error creating head."
    },
    "height_h1_label": {
        "ru": "Высота h1 (мм):",
        "de": "Höhe h1 (mm):",
        "en": "Height h1 (mm):"
    },
    "height_label": {
        "ru": "Высота",
        "de": "Höhe",
        "en": "Height"
    },
    "height_positive": {
        "ru": "Высота должна быть положительной!",
        "de": "Höhe muss positiv sein!",
        "en": "Height must be positive!"
    },
    "info": {
        "ru": "Информация",
        "de": "Information",
        "en": "Information"
    },
    "inner_label": {
        "ru": "внутренний",
        "de": "innen",
        "en": "inner"
    },
    "insert_point_label": {
        "ru": "Точка вставки",
        "de": "Einfügepunkt",
        "en": "Insertion point"
    },
    "insert_point_not_selected": {
        "ru": "Выберите точку вставки.",
        "de": "Einfügepunkt auswählen.",
        "en": "Select insertion point."
    },
    "invalid_angle": {
        "ru": "Некорректный угол!",
        "de": "Ungültiger Winkel!",
        "en": "Invalid angle!"
    },
    "invalid_geometry": {
        "ru": "Ошибка геометрии.",
        "de": "Geometriefehler.",
        "en": "Geometry error."
    },
    "invalid_gradient": {
        "ru": "Некорректный наклон!",
        "de": "Ungültige Neigung!",
        "en": "Invalid gradient!"
    },
    "invalid_number": {
        "ru": "Некорректное число!",
        "de": "Ungültige Zahl!",
        "en": "Invalid number!"
    },
    "invalid_number_format_error": {
        "ru": "Ошибка: Неверный формат числа",
        "de": "Fehler: Ungültiges Zahlenformat",
        "en": "Error: Invalid number format"
    },
    "invalid_point": {
        "ru": "Некорректная точка вставки.",
        "de": "Ungültiger Einfügepunkt.",
        "en": "Invalid insertion point."
    },
    "invalid_points_list": {
        "ru": "Некорректный список точек: {}",
        "de": "Ungültige Punkteliste: {}",
        "en": "Invalid points list: {}"
    },
    "invalid_points_type": {
        "ru": "Все координаты должны быть числами: {}",
        "de": "Alle Koordinaten müssen Zahlen sein: {}",
        "en": "All coordinates must be numbers: {}"
    },
    "invalid_result": {
        "ru": "Некорректный результат!",
        "de": "Ungültiges Ergebnis!",
        "en": "Invalid result!"
    },
    "lang_de": {
        "ru": "Немецкий",
        "de": "Deutsch",
        "en": "German"
    },
    "lang_en": {
        "ru": "Английский",
        "de": "Englisch",
        "en": "English"
    },
    "lang_ru": {
        "ru": "Русский",
        "de": "Russisch",
        "en": "Russian"
    },
    "language_menu": {
        "ru": "&Язык",
        "de": "&Sprache",
        "en": "&Language"
    },
    "layer_context_error": {
        "ru": "Ошибка в контексте слоя '{}': {}",
        "de": "Fehler im Kontext der Ebene '{}': {}",
        "en": "Error in layer context '{}': {}"
    },
    "layer_created": {
        "ru": "Создан слой '{}'.",
        "de": "Ebene '{}' erstellt.",
        "en": "Layer '{}' created."
    },
    "layer_label": {
        "ru": "Слой:",
        "de": "Ebene:",
        "en": "Layer:"
    },
    "layer_locked": {
        "ru": "Слой '{}' заблокирован, разблокируем.",
        "de": "Ebene '{}' ist gesperrt, wird entsperrt.",
        "en": "Layer '{}' is locked, unlocking."
    },
    "layer_restored": {
        "ru": "Восстановлен исходный слой '{}'.",
        "de": "Ursprüngliche Ebene '{}' wiederhergestellt.",
        "en": "Original layer '{}' restored."
    },
    "layer_restore_error": {
        "ru": "Ошибка при восстановлении исходного слоя: {}",
        "de": "Fehler beim Wiederherstellen der ursprünglichen Ebene: {}",
        "en": "Error restoring original layer: {}"
    },
    "layer_set": {
        "ru": "Установлен активный слой '{}'.",
        "de": "Aktive Ebene '{}' gesetzt.",
        "en": "Active layer '{}' set."
    },
    "length_positive_error": {
        "ru": "Ошибка: Высота обечайки должна быть положительной",
        "de": "Fehler: Höhe des Behälters muss positiv sein",
        "en": "Error: Shell height must be positive"
    },
    "main_data_label": {
        "ru": "Основные данные",
        "de": "Hauptdaten",
        "en": "Main data"
    },
    "material_label": {
        "ru": "Материал:",
        "de": "Material:",
        "en": "Material:"
    },
    "math_error": {
        "ru": "Математическая ошибка!",
        "de": "Mathematischer Fehler!",
        "en": "Mathematical error!"
    },
    "menu_about": {
        "ru": "&О программе",
        "de": "&Über das Programm",
        "en": "&About the program"
    },
    "menu_file": {
        "ru": "&Файл",
        "de": "&Datei",
        "en": "&File"
    },
    "menu_help": {
        "ru": "&Справка",
        "de": "&Hilfe",
        "en": "&Help"
    },
    "middle_label": {
        "ru": "средний",
        "de": "mitte",
        "en": "middle"
    },
    "missing_data": {
        "ru": "Недостаточно данных!",
        "de": "Unzureichende Daten!",
        "en": "Insufficient data!"
    },
    "missing_height_data": {
        "ru": "Необходимо указать высоту, наклон или угол.",
        "de": "Höhe, Neigung oder Winkel müssen angegeben werden.",
        "en": "Height, gradient, or angle must be specified."
    },
    "mm": {
        "ru": "мм",
        "de": "mm",
        "en": "mm"
    },
    "no_center": {
        "ru": "Не указана центральная точка",
        "de": "Kein Mittelpunkt angegeben",
        "en": "No center point specified"
    },
    "no_diameters": {
        "ru": "Не указаны диаметры",
        "de": "Keine Durchmesser angegeben",
        "en": "No diameters specified"
    },
    "no_input_data": {
        "ru": "Ввод отменен или данные отсутствуют.",
        "de": "Eingabe abgebrochen oder keine Daten vorhanden.",
        "en": "Input canceled or no data provided."
    },
    "offset_non_negative_error": {
        "ru": "Ошибка: Отступ не может быть отрицательным",
        "de": "Fehler: Versatz darf nicht negativ sein",
        "en": "Error: Offset cannot be negative"
    },
    "ok_button": {
        "ru": "ОК",
        "de": "OK",
        "en": "OK"
    },
    "operation_success": {
        "ru": "Операция завершена.",
        "de": "Vorgang abgeschlossen.",
        "en": "Operation completed."
    },
    "outer_label": {
        "ru": "наружный",
        "de": "außen",
        "en": "outer"
    },
    "point_not_selected": {
        "ru": "Точка не выбрана. Попробуйте снова или нажмите Отмена.",
        "de": "Kein Punkt ausgewählt. Versuchen Sie es erneut oder klicken Sie auf Abbrechen.",
        "en": "No point selected. Try again or press Cancel."
    },
    "point_not_selected_error": {
        "ru": "Ошибка: точка вставки не выбрана или AutoCAD не инициализирован",
        "de": "Fehler: Einfügepunkt nicht ausgewählt oder AutoCAD nicht initialisiert",
        "en": "Error: Insertion point not selected or AutoCAD not initialized"
    },
    "point_selected": {
        "ru": "Точка выбрана: x={}, y={}",
        "de": "Punkt ausgewählt: x={}, y={}",
        "en": "Point selected: x={}, y={}"
    },
    "point_selection_error": {
        "ru": "Ошибка при выборе точки: {}",
        "de": "Fehler bei der Punktauswahl: {}",
        "en": "Error selecting point: {}"
    },
    "polyline_points": {
        "ru": "Координаты полилинии: {}",
        "de": "Polylinienkoordinaten: {}",
        "en": "Polyline coordinates: {}"
    },
    "polyline_success": {
        "ru": "Полилиния создана.",
        "de": "Polylinie erstellt.",
        "en": "Polyline created."
    },
    "preview": {
        "ru": "Предпросмотр",
        "de": "Vorschau",
        "en": "Preview"
    },
    "program_shell": {
        "ru": "Развертка обечайки",
        "de": "Abwicklung eines Behälters",
        "en": "Vessel shell sheet"
    },
    "program_title": {
        "ru": "AT-CAD: Инженерная система автоматизированной развертки металла",
        "de": "AT-CAD: Automatisiertes Profisystem für Metallabwicklung",
        "en": "AT-CAD Metal Unfold Pro System"
    },
    "prompt_select_point": {
        "ru": "Укажите точку: ",
        "de": "Punkt auswählen: ",
        "en": "Select point: "
    },
    "radius_R_label": {
        "ru": "Радиус R (мм):",
        "de": "Radius R (mm):",
        "en": "Radius R (mm):"
    },
    "radius_r_label": {
        "ru": "Радиус r (мм):",
        "de": "Radius r (mm):",
        "en": "Radius r (mm):"
    },
    "rectangle_error": {
        "ru": "Ошибка при создании прямоугольника.",
        "de": "Fehler beim Erstellen des Rechtecks.",
        "en": "Error creating rectangle."
    },
    "rectangle_points_calculated": {
        "ru": "Точки прямоугольника рассчитаны для направления: {}",
        "de": "Rechteckpunkte für Richtung berechnet: {}",
        "en": "Rectangle points calculated for direction: {}"
    },
    "rectangle_success": {
        "ru": "Прямоугольник создан: ширина {}, высота {}",
        "de": "Rechteck erstellt: Breite {}, Höhe {}",
        "en": "Rectangle created: width {}, height {}"
    },
    "regen_error": {
        "ru": "Ошибка обновления вида",
        "de": "Fehler beim Aktualisieren der Ansicht",
        "en": "Error regenerating view"
    },
    "ring_build_error": {
        "ru": "Ошибка построения колец: {0}",
        "de": "Fehler beim Erstellen von Ringen: {0}",
        "en": "Ring construction error: {0}"
    },
    "ring_build_failed": {
        "ru": "Построение колец отменено или завершилось с ошибкой",
        "de": "Ringbau abgebrochen oder fehlerhaft",
        "en": "Ring construction cancelled or failed"
    },
    "save_error": {
        "ru": "Ошибка сохранения значения: {}",
        "de": "Fehler beim Speichern des Werts: {}",
        "en": "Error saving value: {}"
    },
    "save_success": {
        "ru": "Значение {} сохранено.",
        "de": "Wert {} gespeichert.",
        "en": "Value {} saved."
    },
    "save_value": {
        "ru": "Сохранить значение",
        "de": "Wert speichern",
        "en": "Save value"
    },
    "seam_angle_label": {
        "ru": "Расположение продольного шва",
        "de": "Position der Längsnaht",
        "en": "Longitudinal seam position"
    },
    "seam_angle_range_error": {
        "ru": "Ошибка: Угол шва должен быть в диапазоне от 0 до 360 градусов",
        "de": "Fehler: Nahtwinkel muss zwischen 0 und 360 Grad liegen",
        "en": "Error: Seam angle must be between 0 and 360 degrees"
    },
    "select_point_button": {
        "ru": "Выбрать точку",
        "de": "Punkt auswählen",
        "en": "Select point"
    },
    "shell_tab_label": {
        "ru": "Обечайка",
        "de": "Behälter",
        "en": "Shell"
    },
    "status_ready": {
        "ru": "Готов",
        "de": "Bereit",
        "en": "Ready"
    },
    "steigung_label": {
        "ru": "Наклон 1:k",
        "de": "Neigung 1:k",
        "en": "Gradient 1:k"
    },
    "success": {
        "ru": "Успех",
        "de": "Erfolg",
        "en": "Success"
    },
    "success_title": {
        "ru": "Успех",
        "de": "Erfolg",
        "en": "Success"
    },
    "text_error": {
        "ru": "Ошибка при добавлении текста.",
        "de": "Fehler beim Hinzufügen von Text.",
        "en": "Error adding text."
    },
    "text_error_details": {
        "ru": "Ошибка при добавлении текста: {}",
        "de": "Fehler beim Hinzufügen von Text: {}",
        "en": "Error adding text: {}"
    },
    "text_layer_error": {
        "ru": "Не удалось добавить текст на слой '{}'.",
        "de": "Text konnte nicht auf Ebene '{}' hinzugefügt werden.",
        "en": "Failed to add text to layer '{}'."
    },
    "text_success": {
        "ru": "Текст '{}' успешно добавлен на слой '{}' в точке {}.",
        "de": "Text '{}' erfolgreich auf Ebene '{}' an Punkt {} hinzugefügt.",
        "en": "Text '{}' successfully added to layer '{}' at point {}."
    },
    "thickness_label": {
        "ru": "Толщина s (мм):",
        "de": "Dicke s (mm):",
        "en": "Thickness s (mm):"
    },
    "thickness_positive_error": {
        "ru": "Ошибка: Толщина должна быть положительной",
        "de": "Fehler: Dicke muss positiv sein",
        "en": "Error: Thickness must be positive"
    },
    "top_allowance_label": {
        "ru": "Припуск сверху, мм",
        "de": "Zugabe oben, mm",
        "en": "Top allowance, mm"
    },
    "weld_allowance_label": {
        "ru": "Припуск на сварку (мм):",
        "de": "Schweißnahtzugabe (mm):",
        "en": "Weld allowance (mm):"
    },
    "window_title_cone": {
        "ru": "Параметры развертки конуса",
        "de": "Parameter der Kegelabwicklung",
        "en": "Cone sheet parameters"
    },
    "window_title_head": {
        "ru": "Параметры днища",
        "de.":
        "Bodenparameter",
        "en": "Head parameters"
    },
    "window_title_ring": {
        "ru": "Параметры колец",
        "de": "Ringparameter",
        "en": "Ring parameters"
    },
    "window_title_shell": {
        "ru": "Параметры развертки обечайки вертикального сосуда",
        "de": "Parameter der Abwicklung eines vertikalen Behälters",
        "en": "Vertical vessel shell sheet parameters"
    },
    "work_number_invalid": {
        "ru": "Номер работы не задан!",
        "de": "Arbeitsnummer nicht angegeben!",
        "en": "Work number not specified!"
    },
    "work_number_label": {
        "ru": "Номер работы:",
        "de": "Arbeitsnummer:",
        "en": "Work number:"
    },
    "zero_error": {
        "ru": "Деление на ноль невозможно!",
        "de": "Division durch Null ist unmöglich!",
        "en": "Division by zero is impossible!"
    }
}


class Localization:
    """
    Класс для управления локализацией текстовых сообщений.
    """

    def __init__(self, language: str = LANGUAGE):
        """
        Инициализирует локализацию с заданным языком.

        Args:
            language: Код языка ("ru", "de", "en"). По умолчанию берётся из at_config.LANGUAGE.
        """
        self._valid_languages = {"ru", "de", "en"}
        self.language = language if language in self._valid_languages else "ru"
        logging.info(f"Localization initialized with language: {self.language}")

    def set_language(self, language: str) -> None:
        """
        Устанавливает язык локализации.

        Args:
            language: Код языка ("ru", "de", "en").
        """
        self.language = language if language in self._valid_languages else "ru"
        logging.info(f"Language set to: {self.language}")

    def get(self, key: str, default: str = None, *args) -> str:
        """
        Возвращает переведённое сообщение.

        Args:
            key: Ключ строки.
            default: Значение по умолчанию, если ключ не найден.
            *args: Параметры форматирования.

        Returns:
            str: Переведённая строка или значение по умолчанию, если перевод не найден.
        """
        if self.language not in self._valid_languages:
            self.language = "ru"
            logging.warning(f"Invalid language detected, reverted to: {self.language}")

        text = translations.get(key, {}).get(self.language, default if default is not None else key)
        logging.debug(f"Localization: key={key}, language={self.language}, result={text}")

        if not args:
            return text
        try:
            return text.format(*args)
        except (IndexError, KeyError, ValueError) as e:
            logging.error(f"Error formatting localization string: key={key}, text={text}, args={args}, error={e}")
            return text  # Возвращаем текст без форматирования в случае ошибки


# Глобальный объект локализации
loc = Localization()
