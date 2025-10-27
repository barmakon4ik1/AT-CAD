"""
Файл: at_cutting.py
Путь: programs/at_cutting.py

Описание:
Модуль для выбора полилиний листов в AutoCAD на слое 'SF-TEXT' с созданием рабочей области
с отступом (margin). Использует shapely для геометрических вычислений и интегрируется с ATCadInit
для COM-взаимодействия. Поддерживает выбор мышкой, проверку замкнутости и обработку ошибок
через show_popup. Также содержит функцию выбора примитива на слое "0" и поиска объектов
внутри него без изменения их положения.
"""

from typing import List, Dict, Any
from shapely.geometry import Polygon, Point
from config.at_cad_init import ATCadInit
from programs.at_input import at_entity_input, at_action_input
from locales.at_translations import loc
from windows.at_gui_utils import show_popup

# -----------------------------
# Локальные переводы модуля
# -----------------------------
TRANSLATIONS = {
    "polyline_auto_closed": {
        "ru": "Полилиния была открыта — замкнута автоматически.",
        "de": "Polyline war offen – automatisch geschlossen.",
        "en": "Polyline was open — closed automatically."
    },
    "action_continue_word": {"ru": "Продолжить", "de": "Fortfahren", "en": "Continue"},
    "action_finish_word": {"ru": "Завершить", "de": "Beenden", "en": "Finish"},
    "action_abort_word": {"ru": "Прервать", "de": "Abbrechen", "en": "Abort"},
    "select_polyline_prompt": {
        "ru": "Выберите полилинию(и) листа на слое 'SF-TEXT'. Нажмите Enter для завершения или Esc для выхода.",
        "de": "Wählen Sie die Polylinie(n) des Blattes auf der Ebene 'SF-TEXT' aus. Drücken Sie Enter zum Abschließen oder Esc zum Beenden.",
        "en": "Select polyline(s) of the sheet on layer 'SF-TEXT'. Press Enter to finish or Esc to exit."
    },
    "select_completed_enter": {
        "ru": "Выбор завершён (Enter).", "de": "Auswahl abgeschlossen (Enter).", "en": "Selection completed (Enter)."
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
        "ru": "Ошибка: Полилиния не замкнута!",
        "de": "Fehler: Polyline ist nicht geschlossen!",
        "en": "Error: Polyline is not closed!"
    },
    "invalid_working_area": {
        "ru": "Ошибка: Рабочая область не создана (слишком большой отступ {} мм или некорректная геометрия).",
        "de": "Fehler: Arbeitsbereich nicht erstellt (zu großer Abstand {} mm oder ungültige Geometrie).",
        "en": "Error: Working area not created (margin {} mm too large or invalid geometry)."
    },
    "sheet_added": {
        "ru": "Лист добавлен: {} лист(ов) выбрано.",
        "de": "{} Blatt/Blätter hinzugefügt.",
        "en": "Sheet added: {} selected."
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
    "critical_selection_error": {
        "ru": "Критическая ошибка при выборе: {}",
        "de": "Kritischer Fehler bei der Auswahl: {}",
        "en": "Critical error during selection: {}"
    },
    # Примитивы
    "primitive_prompt": {
        "ru": "Выберите примитив на слое '{}'. Нажмите Enter для завершения или Esc для выхода.",
        "de": "Wählen Sie ein Objekt auf Layer '{}' aus. Enter = Fertig, Esc = Abbrechen.",
        "en": "Select a primitive on layer '{}'. Press Enter to finish or Esc to exit."
    },
    "primitive_added": {
        "ru": "Примитив №{} добавлен. Внутри найдено {} объектов.",
        "de": "Objekt Nr. {} hinzugefügt. {} Elemente innen gefunden.",
        "en": "Primitive #{} added. {} objects found inside."
    },
    "primitive_cancelled_esc": {
        "ru": "Выбор примитивов прерван пользователем (Esc).",
        "de": "Objektauswahl durch Benutzer (Esc) abgebrochen.",
        "en": "Primitive selection aborted by user (Esc)."
    },
    "primitive_completed_enter": {
        "ru": "Выбор примитивов завершён (Enter).",
        "de": "Objektauswahl abgeschlossen (Enter).",
        "en": "Primitive selection completed (Enter)."
    },
    "primitive_not_on_layer": {
        "ru": "Ошибка: Примитив не на слое '{}'.",
        "de": "Fehler: Objekt ist nicht auf Layer '{}'.",
        "en": "Error: Primitive not on layer '{}'."
    },
}
loc.register_translations(TRANSLATIONS)


def get_sheets(doc: object, margin: float = 10.0) -> List[Dict[str, Any]]:
    """
    Запрашивает у пользователя выбор полилиний на слое 'SF-TEXT' и создаёт рабочие области
    с отступом margin. Автоматически замыкает открытые полилинии.
    """
    sheets = []
    try:
        if not doc:
            show_popup("Нет активного документа.", popup_type="error")
            return sheets

        # show_popup(loc.get("select_polyline_prompt"), popup_type="info")

        while True:
            entity, _, ok, enter, esc = at_entity_input(doc, prompt=loc.get("select_polyline_prompt"))

            if esc:
                show_popup(loc.get("selection_aborted"), popup_type="warning")
                break

            if enter:
                if sheets:
                    show_popup(loc.get("select_completed_enter"), popup_type="info")
                else:
                    show_popup(loc.get("no_polyline_selected"), popup_type="warning")
                break

            if not ok or entity is None:
                show_popup(loc.get("no_polyline_selected"), popup_type="warning")
                continue

            if entity.ObjectName != "AcDbPolyline":
                show_popup(loc.get("invalid_polyline"), popup_type="error")
                continue

            if entity.Layer != "SF-TEXT":
                show_popup(loc.get("wrong_layer"), popup_type="error")
                continue

            if not entity.Closed:
                try:
                    entity.Closed = True
                    show_popup(loc.get("polyline_auto_closed"), popup_type="info")
                except Exception:
                    show_popup(loc.get("not_closed_polyline"), popup_type="error")
                    continue

            coords = [(entity.Coordinates[i], entity.Coordinates[i + 1])
                      for i in range(0, len(entity.Coordinates), 2)]
            poly = Polygon(coords)
            inner = poly.buffer(-margin)

            if not inner.is_valid or inner.is_empty:
                show_popup(loc.get("invalid_working_area").format(margin), popup_type="error")
                continue

            sheets.append({"points": coords, "working_area": inner})
            show_popup(loc.get("sheet_added").format(len(sheets)), popup_type="info")

            # выбор действия
            action, act_ok, act_esc = at_action_input(
                doc,
                actions=[
                    loc.get("action_continue_word", "Продолжить"),
                    loc.get("action_finish_word", "Завершить"),
                    loc.get("action_abort_word", "Прервать"),
                ],
            )

            if act_esc:
                show_popup(loc.get("selection_aborted_input_error"), popup_type="warning")
                break
            if not act_ok:
                show_popup(loc.get("selection_aborted_input_error"), popup_type="warning")
                break

            if action in (loc.get("action_finish_word"), "Finish", "1"):
                show_popup(loc.get("select_completed_user"), popup_type="info")
                break
            if action in (loc.get("action_abort_word"), "Abort", "2"):
                show_popup(loc.get("selection_aborted"), popup_type="warning")
                break

        return sheets

    except Exception as e:
        show_popup(loc.get("critical_selection_error").format(str(e)), popup_type="error")
        return sheets


def get_primitive_with_contents(doc: object, layer: str = "0") -> Dict[str, Any]:
    """
    Выбирает один или несколько примитивов (полилиния, окружность и т.п.) на указанном слое.
    После выбора — собирает все объекты, полностью находящиеся внутри контура примитива.
    """
    result = {}
    try:
        if not doc:
            show_popup("Нет активного документа.", popup_type="error")
            return result

        ms = doc.ModelSpace
        count = 1
        show_popup(loc.get("primitive_prompt").format(layer), popup_type="info")

        while True:
            entity, _, ok, enter, esc = at_entity_input(doc, prompt=f"Выберите примитив №{count}")

            if esc:
                show_popup(loc.get("primitive_cancelled_esc"), popup_type="warning")
                break
            if enter:
                show_popup(loc.get("primitive_completed_enter"), popup_type="info")
                break
            if not ok or entity is None:
                show_popup(loc.get("no_polyline_selected"), popup_type="warning")
                continue

            if entity.Layer != layer:
                show_popup(loc.get("primitive_not_on_layer").format(layer), popup_type="error")
                continue

            if entity.ObjectName == "AcDbPolyline":
                coords = [(entity.Coordinates[i], entity.Coordinates[i + 1])
                          for i in range(0, len(entity.Coordinates), 2)]
                poly = Polygon(coords)
            elif entity.ObjectName == "AcDbCircle":
                c = entity.Center
                poly = Point(c[0], c[1]).buffer(entity.Radius)
            else:
                show_popup("Ошибка: выберите полилинию или окружность.", popup_type="error")
                continue

            inside_objects = []
            for obj in ms:
                try:
                    if obj.ObjectID == entity.ObjectID:
                        continue

                    shp = None
                    if hasattr(obj, "Coordinates"):
                        pts = [(obj.Coordinates[i], obj.Coordinates[i + 1])
                               for i in range(0, len(obj.Coordinates), 2)]
                        if len(pts) >= 3:
                            shp = Polygon(pts)
                        elif len(pts) == 2:
                            shp = Point(pts[0][0], pts[0][1]).buffer(0.1)
                    elif hasattr(obj, "InsertionPoint"):
                        ip = obj.InsertionPoint
                        shp = Point(ip[0], ip[1])
                    elif hasattr(obj, "Center") and hasattr(obj, "Radius"):
                        c = obj.Center
                        shp = Point(c[0], c[1]).buffer(obj.Radius)

                    if shp and poly.contains(shp):
                        inside_objects.append(obj)
                except Exception:
                    continue

            result[f"primitive{count}"] = {
                "primitive": entity,
                "contents": inside_objects,
                "bounds": poly.bounds,
            }

            show_popup(loc.get("primitive_added").format(count, len(inside_objects)), popup_type="info")
            count += 1

        return result

    except Exception as e:
        show_popup(f"Ошибка при обработке примитивов: {e}", popup_type="error")
        return {}


def main():
    cad = ATCadInit()
    doc = cad.document

    sheets = get_sheets(doc, margin=10.0)
    print(f"Листы: {sheets}")

    primitives = get_primitive_with_contents(doc, layer="0")
    for name, data in primitives.items():
        prim = data["primitive"]
        inside = data["contents"]
        show_popup(f"{name}: {prim.ObjectName}, внутри {len(inside)} объектов.", popup_type="info")
        print(prim)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        show_popup(loc.get("critical_selection_error").format(str(e)), popup_type="error")
