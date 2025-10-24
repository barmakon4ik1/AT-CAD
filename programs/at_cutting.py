import comtypes.client
import comtypes.automation
from shapely.geometry import Polygon
import time
import pythoncom
from config.at_cad_init import ATCadInit
from locales.at_translations import loc

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "select_polyline_prompt": {
        "ru": "Выберите полилинию(и) листа на слое 'SF-TEXT'. Нажмите Enter для завершения или Esc для выхода.",
        "de": "Wählen Sie die Polylinie(n) des Blattes auf der Ebene 'SF-TEXT' aus. Drücken Sie Enter zum Abschließen oder Esc zum Beenden.",
        "en": "Select polyline(s) of the sheet on layer 'SF-TEXT'. Press Enter to finish or Esc to exit."
    },
    "select_polyline_action": {
        "ru": "Действие [0-Продолжить/1-Завершить/2-Прервать] <0>: ",
        "de": "Aktion [0-Fortfahren/1-Beenden/2-Abbrechen] <0>: ",
        "en": "Action [0-Continue/1-Finish/2-Abort] <0>: "
    },
    "select_completed_enter": {
        "ru": "Выбор завершен (Enter).",
        "de": "Auswahl abgeschlossen (Enter).",
        "en": "Selection completed (Enter)."
    },
    "select_completed_user": {
        "ru": "Выбор завершен (по выбору пользователя).",
        "de": "Auswahl abgeschlossen (durch Benutzerwahl).",
        "en": "Selection completed (by user choice)."
    },
    "no_polyline_selected": {
        "ru": "Ошибка: Не выбрана полилиния (возможно, промах или нажат Esc).",
        "de": "Fehler: Keine Polylinie ausgewählt (möglicherweise Fehlklick oder Esc gedrückt).",
        "en": "Error: No polyline selected (possibly missed or Esc pressed)."
    },
    "invalid_polyline": {
        "ru": "Ошибка: Выберите полилинию!",
        "de": "Fehler: Wählen Sie eine Polylinie!",
        "en": "Error: Select a polyline!"
    },
    "wrong_layer": {
        "ru": "Ошибка: Выберите полилинию на слое 'SF-TEXT'!",
        "de": "Fehler: Wählen Sie eine Polylinie auf der Ebene 'SF-TEXT'!",
        "en": "Error: Select a polyline on layer 'SF-TEXT'!"
    },
    "not_closed_polyline": {
        "ru": "Ошибка: Выберите замкнутую полилинию!",
        "de": "Fehler: Wählen Sie eine geschlossene Polylinie!",
        "en": "Error: Select a closed polyline!"
    },
    "invalid_working_area": {
        "ru": "Ошибка: Рабочая область не создана (слишком большой отступ {} мм или некорректная геометрия)",
        "de": "Fehler: Arbeitsbereich nicht erstellt (zu großer Abstand {} mm oder ungültige Geometrie)",
        "en": "Error: Working area not created (margin {} mm too large or invalid geometry)"
    },
    "working_area_not_contained": {
        "ru": "Ошибка: Рабочая область не помещается в лист (площадь {:.2f} мм²)",
        "de": "Fehler: Arbeitsbereich passt nicht in das Blatt (Fläche {:.2f} mm²)",
        "en": "Error: Working area does not fit in the sheet (area {:.2f} mm²)"
    },
    "invalid_area_size": {
        "ru": "Ошибка: Площадь рабочей области ({:.2f} мм²) больше или равна площади листа ({:.2f} мм²)",
        "de": "Fehler: Fläche des Arbeitsbereichs ({:.2f} mm²) ist größer oder gleich der Blattfläche ({:.2f} mm²)",
        "en": "Error: Working area ({:.2f} mm²) is larger than or equal to sheet area ({:.2f} mm²)"
    },
    "action_selected": {
        "ru": "Выбранное действие: '{}'",
        "de": "Ausgewählte Aktion: '{}'",
        "en": "Selected action: '{}'"
    },
    "action_input_error": {
        "ru": "Ошибка ввода действия (возможно, нажат Esc). Считаем 'Прервать'.",
        "de": "Fehler bei der Aktionseingabe (möglicherweise Esc gedrückt). Als 'Abbrechen' gewertet.",
        "en": "Action input error (possibly Esc pressed). Considered as 'Abort'."
    },
    "selection_aborted": {
        "ru": "Выбор прерван пользователем.",
        "de": "Auswahl vom Benutzer abgebrochen.",
        "en": "Selection aborted by user."
    },
    "selection_aborted_input_error": {
        "ru": "Выбор прерван пользователем (ошибка ввода).",
        "de": "Auswahl vom Benutzer abgebrochen (Eingabefehler).",
        "en": "Selection aborted by user (input error)."
    },
    "critical_action_error": {
        "ru": "Критическая ошибка при выборе действия: {}",
        "de": "Kritischer Fehler bei der Auswahl der Aktion: {}",
        "en": "Critical error during action selection: {}"
    },
    "critical_selection_error": {
        "ru": "Критическая ошибка при выборе: {}",
        "de": "Kritischer Fehler bei der Auswahl: {}",
        "en": "Critical error during selection: {}"
    },
    "sheet_added": {
        "ru": "Лист добавлен: {} листов выбрано.",
        "de": "Blatt hinzugefügt: {} Blätter ausgewählt.",
        "en": "Sheet added: {} sheets selected."
    },
    "no_sheets_selected": {
        "ru": "Предупреждение: Не выбрано ни одного листа.",
        "de": "Warnung: Kein Blatt ausgewählt.",
        "en": "Warning: No sheets selected."
    },
    "sheet_info": {
        "ru": "Лист {}:",
        "de": "Blatt {}:",
        "en": "Sheet {}:"
    },
    "sheet_points": {
        "ru": "  Координаты углов: {}",
        "de": "  Koordinaten der Ecken: {}",
        "en": "  Corner coordinates: {}"
    },
    "sheet_working_area": {
        "ru": "  Рабочая область: границы {}, размеры {:.2f}x{:.2f} мм, площадь {:.2f} мм²",
        "de": "  Arbeitsbereich: Grenzen {}, Abmessungen {:.2f}x{:.2f} mm, Fläche {:.2f} mm²",
        "en": "  Working area: bounds {}, dimensions {:.2f}x{:.2f} mm, area {:.2f} mm²"
    },
    "sheet_details": {
        "ru": "Лист: границы {}, размеры {:.2f}x{:.2f} мм, площадь {:.2f} мм²",
        "de": "Blatt: Grenzen {}, Abmessungen {:.2f}x{:.2f} mm, Fläche {:.2f} mm²",
        "en": "Sheet: bounds {}, dimensions {:.2f}x{:.2f} mm, area {:.2f} mm²"
    },
    "active_layer_set": {
        "ru": "Активный слой установлен: 0",
        "de": "Aktiver Layer gesetzt: 0",
        "en": "Active layer set: 0"
    },
    "layer_set_error": {
        "ru": "Ошибка установки слоя '0': {}",
        "de": "Fehler beim Setzen des Layers '0': {}",
        "en": "Error setting layer '0': {}"
    },
    "autocad_version": {
        "ru": "AutoCAD версия: {}",
        "de": "AutoCAD-Version: {}",
        "en": "AutoCAD version: {}"
    },
    "invalid_action": {
        "ru": "Ошибка: Неверное действие '{}'. Доступные действия: 0, 1, 2.",
        "de": "Fehler: Ungültige Aktion '{}'. Verfügbare Aktionen: 0, 1, 2.",
        "en": "Error: Invalid action '{}'. Available actions: 0, 1, 2."
    }
}
# Регистрируем переводы сразу при загрузке модуля
loc.register_translations(TRANSLATIONS)

def get_user_action(utility):
    """Запрашивает действие у пользователя через GetKeyword с безопасной обработкой Enter/Esc."""
    try:
        # Разрешаем только ключевые слова — Enter не считается пустым вводом
        utility.InitializeUserInput(0, "Continue Finish Abort")
        action = utility.GetKeyword("\nДействие [Продолжить/Завершить/Прервать] <Завершить>: ")

        if not action:
            # Если пользователь просто нажал Enter — считаем "Finish"
            return "Finish"

        return action

    except Exception as e:
        # Обработка кода ошибки COM (-2147352567)
        if e.args and e.args[0] == -2147352567:
            # Проверим состояние командной строки — если Esc, считаем Abort
            print("Ошибка ввода действия (возможно, нажат Esc). Считаем 'Прервать'.")
            return "Abort"

        print(f"Неожиданная ошибка GetKeyword: {e}")
        return "Abort"


def get_sheets(utility, model_space, doc, margin=10.0):
    sheets = []
    print(loc.get("select_polyline_prompt"))

    while True:
        obj, ok, esc = get_entity_safe(utility, "\nВыберите полилинию листа: ")

        if esc:
            print(loc.get("select_completed_user"))
            return sheets

        if not ok or obj is None:
            action = get_action(utility, loc)
            if action == "Finish":
                print(loc.get("select_completed_user"))
                return sheets
            elif action == "Abort":
                raise Exception(loc.get("selection_aborted"))
            continue

        # --- Проверки ---
        if obj.ObjectName != "AcDbPolyline":
            print(loc.get("invalid_polyline"))
            if get_action(utility, loc) == "Abort":
                raise Exception(loc.get("selection_aborted"))
            continue

        if obj.Layer != "SF-TEXT":
            print(loc.get("wrong_layer"))
            if get_action(utility, loc) == "Abort":
                raise Exception(loc.get("selection_aborted"))
            continue

        if not obj.Closed:
            print(loc.get("not_closed_polyline"))
            if get_action(utility, loc) == "Abort":
                raise Exception(loc.get("selection_aborted"))
            continue

        # --- Геометрия ---
        coords = [(obj.Coordinates[i], obj.Coordinates[i+1])
                  for i in range(0, len(obj.Coordinates), 2)]
        poly = Polygon(coords)
        inner = poly.buffer(-margin)

        if not inner.is_valid or inner.is_empty:
            print(loc.get("invalid_working_area").format(margin))
            if get_action(utility, loc) == "Abort":
                raise Exception(loc.get("selection_aborted"))
            continue

        sheets.append({"points": coords, "working_area": inner})
        print(loc.get("sheet_added").format(len(sheets)))



def main():
    """
    Основная функция для запуска процесса получения листов в AutoCAD.
    """
    # Инициализация AutoCAD
    cad = ATCadInit()
    acad = cad.application
    doc = cad.document
    model_space = cad.model_space
    utility = doc.Utility

    print(loc.get("autocad_version").format(acad.Version))
    # Установка активного слоя "0"
    try:
        doc.ActiveLayer = doc.Layers.Item("0")
        print(loc.get("active_layer_set"))
    except Exception as e:
        print(loc.get("layer_set_error").format(str(e)))
        raise

    # Получение листов с отступом 10 мм
    sheets = get_sheets(utility, model_space, doc, margin=10.0)
    if not sheets:
        print(loc.get("no_sheets_selected"))
    else:
        print(loc.get("sheet_added").format(len(sheets)))
        for i, sheet in enumerate(sheets, 1):
            print(loc.get("sheet_info").format(i))
            print(loc.get("sheet_points").format(sheet['points']))
            bounds = sheet['working_area'].bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            print(loc.get("sheet_working_area").format(bounds, width, height, sheet['working_area'].area))

    # Восстановление исходного слоя
    cad.restore_original_layer()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(loc.get("critical_selection_error").format(str(e)))
