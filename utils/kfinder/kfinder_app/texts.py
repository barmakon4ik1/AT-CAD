"""
texts.py
========

Централизованные строки интерфейса K-Finder.

Зачем нужен
-----------
В старой версии словарь TXT находился прямо в основном файле приложения.
Теперь он вынесен в отдельный модуль, чтобы:

- уменьшить размер и связность основного GUI-кода;
- упростить поддержку интерфейсных строк;
- подготовить проект к дальнейшей локализации;
- быстро находить все подписи, сообщения и заголовки в одном месте.

Как использовать
----------------
Во всех остальных модулях:

    from .texts import TXT

и дальше:

    TXT["app_title"]
    TXT["msg_error"]
    TXT["dxf_results_title"]

Важно
-----
Пока это обычный Python-словарь.
Позже, если понадобится, его можно будет заменить на JSON/YAML
или на отдельную систему локализации без изменения остального кода.
"""

from __future__ import annotations


TXT: dict[str, str] = {
    # Главное окно
    "app_title":               "K-Finder  —  Auftragsverzeichnis",
    "app_subtitle":            "Auftragsverzeichnis-Suche",
    "input_box":               "Bitte K-Nr., DXF-Nr. o. App.Nr. auswählen und einfügen",
    "actions_box":             "Suchen & Öffnen",
    "service_box":             "Service",
    "meta_box":                "Indexinformationen",
    "status_box":              "Status",

    # Кнопки главного окна
    "search_show":             "🔍  Ergebnisse anzeigen",
    "open_folder":             "📁  K-Auftragsordner",
    "open_sketch":             "✏️  RP - dxf -Skizzen",
    "open_dwg":                "📐  Abwicklungen",
    "open_dxf":                "📄  DXF-Laserzuschnitte",
    "close_program":           "✖  Beenden",

    # Нижние кнопки
    "service_button":          "Service",
    "about_button":            "Info",

    # Статус
    "status_ready_short":       "Bereit.",
    "status_root_warn":         "⚠ Root-Verzeichnis nicht verfügbar",
    "status_no_hits":           "Keine Treffer im Index.",
    "status_rebuild_running":   "Index wird neu aufgebaut…",
    "status_rebuild_done":      "Index neu aufgebaut. Einträge: {count}",
    "status_rebuild_error":     "Fehler beim Neuaufbau",
    "status_found_one":         "1 Treffer: {code}",
    "status_found_many":        "{count} Treffer gefunden.",
    "status_found":             "{code} gefunden.",
    "status_found_with_serial": "{code} gefunden. App.-Nr.: {serials}",
    "status_not_found":         "{code} nicht gefunden.",
    "status_no_folder":         "⚠ {code}: kein eigenes Verzeichnis",
    "status_searching":         "Suche {code}…",
    "status_start_update":      "Automatische Aktualisierung beim Start…",
    "status_ready":             "Bereit.",

    # Режимы поиска
    "input_hint":              "Suchtyp und Nummer eingeben:",
    "input_hint_k":            "K-Nummer:",
    "input_hint_dxf":          "DXF-Nummer:",
    "input_hint_app":          "Apparate-Nr.:",
    "search_mode_k":           "K",
    "search_mode_dxf":         "DXF",
    "search_mode_app":         "App. Nr.",
    "search_mode_menu_title":  "Suchtyp wählen",

    # Сообщения
    "msg_input_required":      "Bitte Auftragsnummer eingeben.",
    "msg_input_error":         "Eingabefehler",
    "msg_hint":                "Hinweis",
    "msg_warning":             "Warnung",
    "msg_error":               "Fehler",
    "msg_not_found_title":     "Nicht gefunden",
    "msg_no_hits_title":       "Keine Treffer",
    "msg_no_folder_title":     "Kein Verzeichnis",
    "msg_select_entry":        "Bitte einen Eintrag auswählen.",
    "msg_folder_missing":      "Ordner nicht gefunden:\n{path}",
    "msg_file_missing":        "Datei nicht gefunden:\n{path}",
    "msg_root_unavailable":    "Root-Verzeichnis nicht erreichbar:\n{path}",
    "msg_not_found_full":      "{code} wurde weder im Index noch auf dem Datenträger gefunden.",
    "msg_no_hits":             "Keine Treffer für '{query}'.",
    "msg_no_folder_single":    "{code} hat keine eigene Verzeichnisstruktur.",
    "msg_no_folder_full": (
        "{code} ist im Index vorhanden, hat aber kein eigenes Verzeichnis.\n"
        "Möglicherweise wurde dieser Auftrag unter einer anderen Nummer abgelegt."
    ),
    "msg_mode_not_supported":  "Diese Aktion ist für den gewählten Suchtyp nicht verfügbar.",

    # Сообщения — DXF-режим
    "msg_dxf_input_error":      "Zulässige Eingabe: nur Ziffern der DXF-Nummer, z. B. 11601 oder 116.",
    "msg_dxf_not_found_title":  "DXF nicht gefunden",
    "msg_dxf_not_found":        "Für DXF '{query}' wurden keine Daten gefunden.",

    # Сообщения — App.Nr.-режим
    "msg_app_input_error":      "Zulässige Eingabe: Apparate-Nr. oder deren Anfang, z. B. 1234 oder 1234.1-2.",
    "msg_app_not_found_title":  "Apparate-Nr. nicht gefunden",
    "msg_app_not_found":        "Für Apparate-Nr. '{query}' wurde keine Zuordnung gefunden.",
    "msg_app_multi_title":      "Mehrere Apparate-Nr. gefunden",
    "msg_app_multi":            "Für Apparate-Nr. '{query}' wurden mehrere Treffer gefunden.",

    # Диалог результатов K-поиска
    "results_box":             "Gefundene Aufträge",
    "results_title":           "Gefundene Aufträge",
    "actions_title":           "Aktionen",
    "close_dialog":            "✖  Schließen",
    "table_order":             "Auftrag",
    "table_year":              "Jahr",
    "table_folder_exists":     "Ordner vorhanden",
    "table_folder":            "Auftragsordner",
    "table_sketch":            "RP-DXF-Skizzen",
    "table_dwg":               "DWG-Datei",
    "table_has_folder_yes":    "✅",
    "table_has_folder_no":     "⚠ kein Ordner",

    # Диалог результатов DXF-поиска
    "dxf_results_title":       "DXF/DWG-Ergebnisse",
    "dxf_box":                 "DXF/DWG-Daten",
    "dxf_actions_box":         "Aktionen",
    "dxf_no_hits_title":       "Keine DXF-Daten",
    "dxf_no_hits":             "Keine DXF/DWG-Daten für '{code}' gefunden.",
    "dxf_open_folder":         "Ordner öffnen",
    "dxf_open_file":           "DWG öffnen",
    "dxf_save_file":           "In Datei speichern",
    "dxf_close":               "Schließen",
    "dxf_select_entry":        "Bitte eine Zeile auswählen.",
    "dxf_file_missing":        "DWG-Datei nicht gefunden:\n{path}",
    "dxf_folder_missing":      "Ordner nicht gefunden:\n{path}",
    "dxf_save_title":          "Ergebnis speichern",
    "dxf_save_done":           "Datei wurde gespeichert:\n{path}",
    "dxf_col_no":              "DXF",
    "dxf_col_k":               "K-Nr.",
    "dxf_col_wst":             "Werkstoff",
    "dxf_col_dicke":           "Dicke, mm",
    "dxf_col_ch_nr":           "Ch.Nr.",
    "dxf_col_area":            "A Kn brutto, qm",
    "dxf_col_length":          "Länge Zuschnitt, mm",
    "dxf_col_price":           "Preis/Länge €",
    "dxf_col_file":            "DWG",

    # Диалог результатов App.Nr.-поиска
    "app_results_title":       "Apparate-Nr.-Ergebnisse",
    "app_box":                 "Gefundene Apparate",
    "app_actions_box":         "Aktionen",
    "app_select_entry":        "Bitte eine Zeile auswählen.",
    "app_col_serial":          "App.-Nr.",
    "app_col_prefix":          "Präfix",
    "app_col_k":               "K-Nr.",
    "app_col_folder_exists":   "Ordner vorhanden",
    "app_col_folder":          "Auftragsordner",

    # Служебный диалог
    "service_dialog_title":    "Service",
    "service_info_box":        "Indexinformationen",
    "service_actions_box":     "Aktionen",
    "service_update_partial":  "Teilaktualisierung",
    "service_update_full":     "Vollständige Neuindizierung",
    "service_close":           "Schließen",
    "service_partial_confirm": "Teilaktualisierung des Indexes ausführen?",
    "service_full_confirm":    "Vollständige Neuindizierung ausführen?",
    "service_update_running":  "Teilaktualisierung läuft…",
    "service_rebuild_running": "Vollständige Neuindizierung läuft…",
    "service_partial_done":    "Aktualisiert. Einträge: {count}",
    "service_full_done":       "Neuindizierung abgeschlossen. Einträge: {count}",
    "service_update_error":    "Fehler bei der Teilaktualisierung",
    "service_rebuild_error":   "Fehler bei der Neuindizierung",

    # Обновление индекса (общие)
    "update_confirm_title":       "Daten aktualisieren",
    "update_confirm":             "Indexdaten aktualisieren?",
    "update_already_running":     "Die Aktualisierung läuft bereits.",
    "update_done_title":          "Fertig",
    "update_done_msg":            "Indexdaten wurden aktualisiert.\nEinträge: {count}",
    "msg_rebuild_confirm_title":  "Index neu aufbauen",
    "msg_rebuild_confirm":        "Index vollständig neu aufbauen?",
    "msg_rebuild_already_running":"Der Indexaufbau läuft bereits.",
    "msg_rebuild_done_title":     "Fertig",
    "msg_rebuild_done":           "Index neu aufgebaut.\nEinträge: {count}",

    # About
    "about_title":             "Über K-Finder",
    "about_text_title":        "K-Finder",
    "about_text_subtitle":     "Suche und Navigation für Auftragsdaten",
    "about_text_body": (
        "Das Programm ermöglicht den schnellen Zugriff auf\n"
        "Auftragsordner, Skizzenordner und DWG-Dateien.\n\n"
        "Unterstützte Suchtypen:\n"
        "• K-Nummer\n"
        "• DXF-Nummer\n"
        "• Apparate-Nr.\n"
    ),
    "about_text_footer": (
        "Autor: A. Tutubalin\n"
        "Version: 4.0\n"
        "© 2026"
    ),
    "about_ok":                "OK",
}