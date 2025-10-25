"""
Файл: at_cutting.py
Путь: programs/at_cutting.py

Описание:
Модуль для выбора полилиний листов в AutoCAD на слое 'SF-TEXT' с созданием рабочей области
с отступом (margin). Использует shapely для геометрических вычислений и интегрируется с ATCadInit
для COM-взаимодействия. Поддерживает выбор мышкой и обработку ошибок через show_popup.
"""

from typing import List, Dict, Any
from shapely.geometry import Polygon
from config.at_cad_init import ATCadInit
from programs.at_input import at_entity_input, at_action_input
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

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
        "ru": "Выбор завершён (Enter).",
        "de": "Auswahl abgeschlossen (Enter).",
        "en": "Selection completed (Enter)."
    },
    "select_completed_user": {
        "ru": "Выбор завершён (по выбору пользователя).",
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
loc.register_translations(TRANSLATIONS)

def get_sheets(doc: object, margin: float = 10.0) -> List[Dict[str, Any]]:
    """
    Запрашивает у пользователя выбор полилиний на слое 'SF-TEXT' и создаёт рабочие области
    с отступом margin. Использует at_entity_input и at_action_input для стабильного ввода.

    Args:
        doc: Объект активного документа AutoCAD (ActiveDocument).
        margin: Отступ от краёв полилинии (мм).

    Returns:
        List[Dict[str, Any]]: Список словарей с координатами полилиний и их рабочими областями.
    """
    sheets = []
    try:
        if not doc:
            show_popup(loc.get("critical_selection_error").format("No active document"), popup_type="error")
            return sheets

        utility = doc.Utility
        show_popup(loc.get("select_polyline_prompt"), popup_type="info")

        while True:
            entity, _, ok, esc = at_entity_input(doc, prompt=loc.get("select_polyline_prompt"))

            if esc:
                show_popup(loc.get("select_completed_enter"), popup_type="info")
                return sheets

            if not ok or entity is None:
                show_popup(loc.get("no_polyline_selected"), popup_type="error")
                action, ok, esc = at_action_input(doc, actions=["Продолжить", "Завершить", "Прервать"])
                if not ok or esc:
                    show_popup(loc.get("action_input_error"), popup_type="error")
                    return sheets
                elif action == "1":  # Finish
                    show_popup(loc.get("select_completed_user"), popup_type="info")
                    return sheets
                elif action == "2":  # Abort
                    show_popup(loc.get("selection_aborted"), popup_type="error")
                    return sheets
                continue

            # Проверки
            if entity.ObjectName != "AcDbPolyline":
                show_popup(loc.get("invalid_polyline"), popup_type="error")
                action, ok, esc = at_action_input(doc, actions=["Продолжить", "Завершить", "Прервать"])
                if not ok or esc or action == "2":
                    show_popup(loc.get("selection_aborted"), popup_type="error")
                    return sheets
                continue

            if entity.Layer != "SF-TEXT":
                show_popup(loc.get("wrong_layer"), popup_type="error")
                action, ok, esc = at_action_input(doc, actions=["Продолжить", "Завершить", "Прервать"])
                if not ok or esc or action == "2":
                    show_popup(loc.get("selection_aborted"), popup_type="error")
                    return sheets
                continue

            if not entity.Closed:
                show_popup(loc.get("not_closed_polyline"), popup_type="error")
                action, ok, esc = at_action_input(doc, actions=["Продолжить", "Завершить", "Прервать"])
                if not ok or esc or action == "2":
                    show_popup(loc.get("selection_aborted"), popup_type="error")
                    return sheets
                continue

            # Геометрия
            coords = [(entity.Coordinates[i], entity.Coordinates[i + 1])
                      for i in range(0, len(entity.Coordinates), 2)]
            poly = Polygon(coords)
            inner = poly.buffer(-margin)

            if not inner.is_valid or inner.is_empty:
                show_popup(loc.get("invalid_working_area").format(margin), popup_type="error")
                action, ok, esc = at_action_input(doc, actions=["Продолжить", "Завершить", "Прервать"])
                if not ok or esc or action == "2":
                    show_popup(loc.get("selection_aborted"), popup_type="error")
                    return sheets
                continue

            sheets.append({"points": coords, "working_area": inner})
            show_popup(loc.get("sheet_added").format(len(sheets)), popup_type="info")

    except Exception as e:
        show_popup(loc.get("critical_selection_error").format(str(e)), popup_type="error")
        return sheets

def main():
    """
    Основная функция для запуска процесса получения листов в AutoCAD.
    """
    cad = ATCadInit()
    acad = cad.application
    doc = cad.document
    model_space = cad.model_space

    if not cad.is_initialized():
        show_popup(loc.get("critical_selection_error").format("AutoCAD not initialized"), popup_type="error")
        return

    show_popup(loc.get("autocad_version").format(acad.Version), popup_type="info")

    try:
        doc.ActiveLayer = doc.Layers.Item("0")
        show_popup(loc.get("active_layer_set"), popup_type="info")
    except Exception as e:
        show_popup(loc.get("layer_set_error").format(str(e)), popup_type="error")
        raise

    sheets = get_sheets(doc, margin=10.0)
    if not sheets:
        show_popup(loc.get("no_sheets_selected"), popup_type="warning")
    else:
        show_popup(loc.get("sheet_added").format(len(sheets)), popup_type="info")
        for i, sheet in enumerate(sheets, 1):
            bounds = sheet['working_area'].bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            show_popup(
                loc.get("sheet_info").format(i) + "\n" +
                loc.get("sheet_points").format(sheet['points']) + "\n" +
                loc.get("sheet_working_area").format(bounds, width, height, sheet['working_area'].area),
                popup_type="info"
            )

    cad.restore_original_layer()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        show_popup(loc.get("critical_selection_error").format(str(e)), popup_type="error")
