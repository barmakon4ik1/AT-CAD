"""
Файл: kfinder_gui.py

Поисковая утилита заказов (K-Finder).
Ищет папки заказов по K-номеру в корневом каталоге G:\\Auftragsdokumente.
Индекс хранится в k_index.json рядом со скриптом.

Архитектура:
  - AppConfig        — замороженный dataclass с настройками
  - KEntry           — модель одной записи индекса
  - KIndex           — работа с JSON-индексом (in-memory cache)
  - SearchService    — логика поиска (индекс → диск)
  - KFinderFrame     — главное окно (wx.Frame в стиле AT-CAD)
  - ResultsDialog    — окно результатов (wx.Dialog)
"""

from __future__ import annotations
import os
import subprocess
import threading
from datetime import datetime
import json
import logging
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from openpyxl import load_workbook
import wx
from wx.lib.buttons import GenButton

# ============================================================
# Рабочая папка
# ============================================================

def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

APP_DIR = _app_dir()

# ============================================================
# Логирование — только ошибки, именованный logger
# ============================================================

_LOG_FILE = APP_DIR / "kfinder.log"
logger = logging.getLogger("kfinder")
logger.propagate = False

if not logger.handlers:
    _h = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _h.setLevel(logging.ERROR)
    logger.addHandler(_h)

logger.setLevel(logging.ERROR)

# ============================================================
# Все строки интерфейса в одном месте
# ============================================================

TXT = {
    "app_title":               "K-Finder  —  Auftragsverzeichnis",
    "app_subtitle":            "Auftragsverzeichnis-Suche",
    "input_box":               "Auftragserfassung",
    "input_hint":              "Voll- oder Teil-K-Nummer eingeben:",
    "actions_box":             "Suchen & Öffnen",
    "service_box":             "Service",
    "meta_box":                "Indexinformationen",
    "status_box":              "Status",
    "results_box":             "Gefundene Aufträge",
    "results_title":           "Gefundene Aufträge",
    "actions_title":           "Aktionen",
    "search_show":             "🔍  Ordner anzeigen",
    "open_folder":             "📁  Auftragsordner öffnen",
    "open_sketch":             "✏️  RP - dxf -Skizzen",
    "open_dwg":                "📐  ABW-K…dwg öffnen",
    "show_dwg":                "🔍  ABW-K…dwg im Explorer",
    "rebuild_index":           "🔄  Index aufbauen",
    "open_index_file":         "📄  Indexdatei",
    "open_index_folder":       "📂  Indexordner",
    "open_log_file":           "📋  Logdatei",
    "close_program":           "✖  Programm beenden",
    "close_dialog":            "✖  Schließen",
    "status_ready":            "Bereit.",
    "status_root_warn":        "⚠ Root-Verzeichnis nicht verfügbar",
    "status_no_hits":          "Keine Treffer im Index.",
    "status_rebuild_running":  "Index wird neu aufgebaut…",
    "status_rebuild_done":     "Index neu aufgebaut. Einträge: {count}",
    "status_rebuild_error":    "Fehler beim Neuaufbau",
    "status_found_one":        "1 Treffer: {code}",
    "status_found_many":       "{count} Treffer gefunden.",
    "status_found":            "{code} gefunden.",
    "status_not_found":        "{code} nicht gefunden.",
    "status_no_folder":        "⚠ {code}: kein eigenes Verzeichnis",
    "status_searching":        "Suche {code}…",
    "msg_input_required":      "Bitte Auftragsnummer eingeben.",
    "msg_input_error":         "Eingabefehler",
    "msg_hint":                "Hinweis",
    "msg_warning":             "Warnung",
    "msg_error":               "Fehler",
    "msg_not_found_title":     "Nicht gefunden",
    "msg_no_hits_title":       "Keine Treffer",
    "msg_no_folder_title":     "Kein Verzeichnis",
    "msg_root_unavailable":    "Root-Verzeichnis nicht erreichbar:\n{path}",
    "msg_not_found_full":      "{code} wurde weder im Index noch auf dem Datenträger gefunden.",
    "msg_no_hits":             "Keine Treffer für '{query}'.",
    "msg_no_folder_single":    "{code} hat keine eigene Verzeichnisstruktur.",
    "msg_no_folder_full":      (
        "{code} ist im Index vorhanden, hat aber kein eigenes Verzeichnis.\n"
        "Möglicherweise wurde dieser Auftrag unter einer anderen Nummer abgelegt."
    ),
    "msg_rebuild_confirm_title":    "Index neu aufbauen",
    "msg_rebuild_confirm":          "Index vollständig neu aufbauen?",
    "msg_rebuild_done_title":       "Fertig",
    "msg_rebuild_done":             "Index neu aufgebaut.\nEinträge: {count}",
    "msg_rebuild_already_running":  "Der Indexaufbau läuft bereits.",
    "msg_select_entry":        "Bitte einen Eintrag auswählen.",
    "msg_folder_missing":      "Ordner nicht gefunden:\n{path}",
    "msg_file_missing":        "Datei nicht gefunden:\n{path}",
    "msg_index_missing":       "Indexdatei nicht gefunden:\n{path}",
    "msg_log_missing":         "Logdatei nicht gefunden:\n{path}",
    "msg_dir_missing":         "Ordner nicht gefunden:\n{path}",
    "table_order":             "Auftrag",
    "table_year":              "Jahr",
    "table_folder_exists":     "Ordner vorhanden",
    "table_folder":            "Auftragsordner",
    "table_sketch":            "Skizzenordner",
    "table_dwg":               "DWG-Datei",
    "table_has_folder_yes":    "✅",
    "table_has_folder_no":     "⚠ kein Ordner",
    "about_button":            "Info",
    "about_title":             "Info",
    "about_text":              (
        "K-Finder\n\n"
        "Das Programm ermöglicht das schnelle Navigieren\n"
        "zu einem Dokumentenordner und das Öffnen einer\n"
        "DWG-Zeichnung.\n"
        "Es durchsucht sowohl die Bestellnummer als auch die Seriennummer.\n\n"
        "Autor: A. Tutubalin\n"
        "Version: 3.0\n"
        "© 2026"
    ),
    "update_data":             "Daten aktualisieren",
    "full_rebuild":            "Vollständig neu aufbauen",
    "update_confirm_title":    "Daten aktualisieren",
    "update_confirm":          "Indexdaten aktualisieren?",
    "update_running":          "Indexdaten werden aktualisiert…",
    "update_done":             "Aktualisierung abgeschlossen. Einträge: {count}",
    "update_done_title":       "Fertig",
    "update_done_msg":         "Indexdaten wurden aktualisiert.\nEinträge: {count}",
    "update_error":            "Fehler bei der Aktualisierung",
    "update_already_running":  "Die Aktualisierung läuft bereits.",
    "open_dxf": "📄  DXF/DWG anzeigen",
    "dxf_results_title": "DXF/DWG-Ergebnisse",
    "dxf_box": "DXF/DWG-Daten",
    "dxf_actions_box": "Aktionen",
    "dxf_no_hits_title": "Keine DXF-Daten",
    "dxf_no_hits": "Keine DXF/DWG-Daten für '{code}' gefunden.",
    "dxf_open_folder": "Ordner öffnen",
    "dxf_open_file": "DWG öffnen",
    "dxf_save_file": "In Datei speichern",
    "dxf_close": "Schließen",
    "dxf_select_entry": "Bitte eine Zeile auswählen.",
    "dxf_file_missing": "DWG-Datei nicht gefunden:\n{path}",
    "dxf_folder_missing": "Ordner nicht gefunden:\n{path}",
    "dxf_save_title": "Ergebnis speichern",
    "dxf_save_done": "Datei wurde gespeichert:\n{path}",
    "dxf_col_no": "DXF",
    "dxf_col_k": "K-Nr.",
    "dxf_col_wst": "Werkstoff",
    "dxf_col_dicke": "Dicke, mm",
    "dxf_col_area": "A Kn brutto, qm",
    "dxf_col_length": "Länge Zuschnitt, mm",
    "dxf_col_price": "Preis/Länge €",
    "dxf_col_file": "DWG",
    "service_button": "Service",
    "service_dialog_title": "Service",
    "service_info_box": "Indexinformationen",
    "service_actions_box": "Aktionen",
    "service_update_partial": "Teilaktualisierung",
    "service_update_full": "Vollständige Neuindizierung",
    "service_close": "Schließen",
    "service_partial_confirm": "Teilaktualisierung des Indexes ausführen?",
    "service_full_confirm": "Vollständige Neuindizierung ausführen?",
    "service_update_running": "Teilaktualisierung läuft…",
    "service_rebuild_running": "Vollständige Neuindizierung läuft…",
    "service_partial_done": "Teilaktualisierung abgeschlossen. Einträge: {count}",
    "service_full_done": "Neuindizierung abgeschlossen. Einträge: {count}",
    "service_update_error": "Fehler bei der Teilaktualisierung",
    "service_rebuild_error": "Fehler bei der Neuindizierung",
    "status_start_update": "Automatische Aktualisierung beim Start…",
    "status_ready_short": "Bereit.",
    "input_hint": "Suchtyp und Nummer eingeben:",
    "search_type_label": "Typ:",
    "search_mode_k": "K",
    "search_mode_dxf": "DXF",
    "search_mode_app": "App. Nr.",

    "msg_mode_not_supported": "Diese Aktion ist für den gewählten Suchtyp nicht verfügbar.",
    "msg_dxf_input_error": "Zulässige Eingabe: nur DXF-Nummer, z. B. 11601.",
    "msg_dxf_not_found_title": "DXF nicht gefunden",
    "msg_dxf_not_found": "Für DXF '{query}' wurden keine Daten gefunden.",

    "msg_app_input_error": "Zulässige Eingabe: Apparate-Nr. oder deren Präfix, z. B. 1234 oder 1234.1-2.",
    "msg_app_not_found_title": "Apparate-Nr. nicht gefunden",
    "msg_app_not_found": "Für Apparate-Nr. '{query}' wurde keine Zuordnung gefunden.",
    "msg_app_multi_title": "Mehrere K-Nummern gefunden",
    "msg_app_multi": "Für Apparate-Nr. '{query}' wurden mehrere K-Nummern gefunden:\n{codes}",

    "status_found_with_serial": "{code} gefunden. App.-Nr.: {serials}",
}

# ============================================================
# Конфигурация
# ============================================================

@dataclass(frozen=True)
class AppConfig:
    root_dir:               Path  = Path(r"G:\Auftragsdokumente")
    index_file:             Path  = APP_DIR / "k_index.json"
    start_year:             int   = 2011
    sketch_folder_name:     str   = "RP - dxf -Skizzen"

    auto_open_single:       bool  = False
    auto_show_single:       bool  = True
    live_search_if_missing: bool  = True

    window_size:            tuple = (410, 520)
    service_window_size:    tuple = (500, 360)

    tail_backtrack:         int   = 50
    tail_years_to_scan:     int   = 2

    auto_update_on_start:   bool  = True

APP_CONFIG = AppConfig()

# ============================================================
# Цвета (стиль AT-CAD)
# ============================================================

CLR_BG          = "#508050"
CLR_BTN_PRIMARY = "#2980b9"
CLR_BTN_OK      = "#27ae60"
CLR_BTN_WARN    = "#e67e22"
CLR_BTN_DANGER  = "#c0392b"
CLR_BTN_DARK    = "#2c3e50"
CLR_TEXT        = "#ffffff"
CLR_LABEL       = "#e8f5e9"
CLR_STATUS_OK   = "#a8d8a8"
CLR_STATUS_WARN = "#f9ca74"
CLR_STATUS_ERR  = "#f08080"
CLR_BOX_FG      = "#c8e6c9"

# ============================================================
# Модель записи
# ============================================================

@dataclass
class KEntry:
    k_code:      str
    year:        int
    folder_path: str
    sketch_path: str
    dwg_path:    str
    has_folder:  bool = True

    @property
    def folder_exists(self) -> bool:
        return Path(self.folder_path).is_dir()

    @property
    def sketch_exists(self) -> bool:
        return Path(self.sketch_path).is_dir()

    @property
    def dwg_exists(self) -> bool:
        return Path(self.dwg_path).is_file()

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "KEntry":
        return KEntry(
            k_code=d["k_code"],
            year=int(d["year"]),
            folder_path=d["folder_path"],
            sketch_path=d["sketch_path"],
            dwg_path=d["dwg_path"],
            has_folder=bool(d.get("has_folder", True)),
        )

# ============================================================
# Индекс
# ============================================================

class KIndex:
    FULL_RE = re.compile(r"^K\d{5}$", re.IGNORECASE)
    PARTIAL_RE = re.compile(r"^[Kk]?\d{1,5}$")

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._items: dict[str, KEntry] = {}
        self._meta: dict = {}
        self._load_cache()

    # ------ кэш ------

    def _load_cache(self) -> None:
        data = self._load_raw()
        self._meta = data.get("_meta", {})
        self._items = {}
        for code, d in data.get("items", {}).items():
            try:
                self._items[code] = KEntry.from_dict(d)
            except (KeyError, ValueError, TypeError):
                logger.error(f"_load_cache: invalid entry {code}")

    def reload(self) -> None:
        self._load_cache()

    # ------ утилиты ------

    def _current_year(self) -> int:
        return datetime.now().year

    def is_root_available(self) -> bool:
        return self.cfg.root_dir.exists() and self.cfg.root_dir.is_dir()

    def normalize_full(self, text: str) -> str:
        s = text.strip().upper()
        if re.fullmatch(r"\d{5}", s):
            return f"K{s}"
        if self.FULL_RE.fullmatch(s):
            return s
        raise ValueError("Eingabe: Kxxxxx oder 5 Ziffern")

    def normalize_partial(self, text: str) -> str:
        s = text.strip().upper()
        if not s:
            return ""
        if not self.PARTIAL_RE.fullmatch(s):
            raise ValueError("Zulässige Eingabe: K20500, 20500, K205, 205 usw.")
        return s

    def is_full_code(self, text: str) -> bool:
        s = text.strip().upper()
        return bool(self.FULL_RE.fullmatch(s) or re.fullmatch(r"\d{5}", s))

    def _make_entry(self, k_code: str, year: int, folder: Path) -> KEntry:
        sketch = folder / self.cfg.sketch_folder_name
        dwg = sketch / f"ABW-{k_code}.dwg"
        return KEntry(
            k_code=k_code,
            year=year,
            folder_path=str(folder),
            sketch_path=str(sketch),
            dwg_path=str(dwg),
            has_folder=True,
        )

    def _code_to_num(self, k_code: str) -> int:
        return int(k_code[1:])

    def _num_to_code(self, num: int) -> str:
        return f"K{num:05d}"

    def _max_known_number(self) -> int:
        nums = [self._code_to_num(code) for code in self._items if self.FULL_RE.fullmatch(code)]
        return max(nums) if nums else 0

    def _make_missing_entry(self, k_code: str) -> KEntry:
        return KEntry(
            k_code=k_code,
            year=0,
            folder_path="",
            sketch_path="",
            dwg_path="",
            has_folder=False,
        )

    # ------ JSON ------

    def _load_raw(self) -> dict:
        if not self.cfg.index_file.is_file():
            return {"_meta": {}, "items": {}}
        try:
            with self.cfg.index_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "items" not in data:
                return {"_meta": {}, "items": {}}
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"_load_raw: {e}")
            return {"_meta": {}, "items": {}}

    def _save_raw(self, data: dict) -> None:
        self.cfg.index_file.parent.mkdir(parents=True, exist_ok=True)
        with self.cfg.index_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_entries(self) -> dict[str, KEntry]:
        return dict(self._items)

    def save_entries(self, items: dict[str, KEntry]) -> None:
        self._items = dict(items)
        self._meta = {
            "root": str(self.cfg.root_dir),
            "start_year": self.cfg.start_year,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "count": len(self._items),
        }
        payload = {
            "_meta": self._meta,
            "items": {k: v.to_dict() for k, v in sorted(self._items.items())},
        }
        self._save_raw(payload)

    def get_meta(self) -> dict:
        return dict(self._meta)

    def update_entry(self, entry: KEntry) -> None:
        self._items[entry.k_code] = entry
        self.save_entries(self._items)

    # ------ быстрый массовый проход по диску ------

    def _scan_years_for_kfolders(
        self,
        start_year: int,
        end_year: int,
        progress_cb=None,
    ) -> dict[str, KEntry]:
        """
        Один массовый проход по указанным годам.
        Возвращает словарь найденных папок Kxxxxx.
        """
        found: dict[str, KEntry] = {}

        for year in range(start_year, end_year + 1):
            year_path = self.cfg.root_dir / str(year)
            count_year = 0

            if year_path.is_dir():
                for dirpath, dirnames, _ in os.walk(year_path):
                    current = Path(dirpath)
                    name = current.name.upper()

                    if self.FULL_RE.fullmatch(name):
                        found[name] = self._make_entry(name, year, current)
                        dirnames[:] = []
                        count_year += 1

            if progress_cb:
                progress_cb(f"{year}: {count_year} Ordner")

        return found

    # ------ поиск ------

    def find_exact(self, k_code: str) -> Optional[KEntry]:
        return self._items.get(k_code)

    def find_partial(self, query: str) -> list[KEntry]:
        q = self.normalize_partial(query)
        if not q:
            return []

        q_digits = q[1:] if q.startswith("K") else q
        results = [
            e for code, e in self._items.items()
            if code.startswith(q) or code[1:].startswith(q_digits)
        ]
        results.sort(key=lambda e: (e.year, e.k_code))
        return results

    def search_on_disk(self, k_code: str) -> Optional[KEntry]:
        """
        Точечный поиск одного номера по всем годам.
        Используется только для разового поиска конкретного K-кода.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.cfg.root_dir}")

        for year in range(self.cfg.start_year, self._current_year() + 1):
            year_path = self.cfg.root_dir / str(year)
            if not year_path.is_dir():
                continue

            for dirpath, dirnames, _ in os.walk(year_path):
                current = Path(dirpath)
                name = current.name.upper()

                if name == k_code and current.is_dir():
                    return self._make_entry(k_code, year, current)

                if self.FULL_RE.fullmatch(name):
                    dirnames[:] = []

        return None

    def update_tail(
        self,
        backtrack: int = 100,
        tail_years_to_scan: int = 2,
        progress_cb=None,
    ) -> int:
        """
        Инкрементальное обновление индекса.

        Логика:
          1. Берём последний известный номер из индекса.
          2. Откатываемся назад на backtrack номеров.
          3. Один раз сканируем только последние tail_years_to_scan лет.
          4. Обновляем хвост индекса по найденным папкам.
          5. Если номера в диапазоне не найдены, записываем has_folder=False.
          6. Если обнаружены новые номера выше текущего хвоста, добавляем их тоже.

        Важно:
          - без сотен повторных os.walk по всему серверу
          - один массовый проход вместо сотен точечных поисков
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.cfg.root_dir}")

        items = dict(self._items)
        max_known = self._max_known_number()

        if max_known <= 0:
            return self.rebuild(progress_cb=progress_cb)

        current_year = self._current_year()
        start_year_scan = max(self.cfg.start_year, current_year - tail_years_to_scan + 1)

        found_recent = self._scan_years_for_kfolders(
            start_year=start_year_scan,
            end_year=current_year,
            progress_cb=progress_cb,
        )

        found_recent_nums = [
            self._code_to_num(code)
            for code in found_recent.keys()
            if self.FULL_RE.fullmatch(code)
        ]

        max_found_recent = max(found_recent_nums) if found_recent_nums else max_known
        start_num = max(1, max_known - backtrack)
        end_num = max(max_known, max_found_recent)

        for num in range(start_num, end_num + 1):
            code = self._num_to_code(num)
            if code in found_recent:
                items[code] = found_recent[code]
            else:
                # Обновляем только хвостовой диапазон.
                # Старые записи вне хвоста не трогаем.
                items[code] = self._make_missing_entry(code)

        # Обрезаем хвостовые пустые номера ВЫШЕ последнего реально найденного
        last_real_num = 0
        for code, entry in items.items():
            if entry.has_folder and self.FULL_RE.fullmatch(code):
                last_real_num = max(last_real_num, self._code_to_num(code))

        trimmed_items: dict[str, KEntry] = {}
        for code, entry in items.items():
            if not self.FULL_RE.fullmatch(code):
                trimmed_items[code] = entry
                continue

            if self._code_to_num(code) <= last_real_num:
                trimmed_items[code] = entry

        self.save_entries(trimmed_items)
        return len(trimmed_items)

    def rebuild(self, progress_cb=None) -> int:
        """
        Полная перестройка индекса.
        Заполняет пропуски в диапазоне номеров записями has_folder=False.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.cfg.root_dir}")

        found_items = self._scan_years_for_kfolders(
            start_year=self.cfg.start_year,
            end_year=self._current_year(),
            progress_cb=progress_cb,
        )

        found_nums = [
            self._code_to_num(code)
            for code in found_items.keys()
            if self.FULL_RE.fullmatch(code)
        ]

        if not found_nums:
            self.save_entries({})
            return 0

        min_num = min(found_nums)
        max_num = max(found_nums)

        full_items: dict[str, KEntry] = {}
        for num in range(min_num, max_num + 1):
            code = self._num_to_code(num)
            if code in found_items:
                full_items[code] = found_items[code]
            else:
                full_items[code] = self._make_missing_entry(code)

        self.save_entries(full_items)
        return len(full_items)

# ============================================================
# Сервис
# ============================================================

class SearchService:
    def __init__(self, cfg: AppConfig, index: KIndex):
        self.cfg   = cfg
        self.index = index

    def get_or_search(self, k_code: str) -> Optional[KEntry]:
        entry = self.index.find_exact(k_code)

        # Уже в индексе (в т.ч. has_folder=False) — не идём на диск
        if entry is not None:
            return entry

        if not self.cfg.live_search_if_missing:
            return None

        entry = self.index.search_on_disk(k_code)
        if entry:
            self.index.update_entry(entry)
            return entry

        # Не найден на диске — сохраняем как has_folder=False
        missing = KEntry(
            k_code=k_code,
            year=0,
            folder_path="",
            sketch_path="",
            dwg_path="",
            has_folder=False,
        )
        self.index.update_entry(missing)
        return missing

# ============================================================
# GUI-утилиты
# ============================================================

def _make_gen_button(parent: wx.Window,
                     label: str,
                     color: str,
                     size: wx.Size = wx.Size(-1, 36),
                     font_size: int = 11) -> GenButton:
    """Стилизованная GenButton в стиле AT-CAD с hover-эффектом."""
    btn = GenButton(parent, label=label, size=size)
    btn.SetBackgroundColour(wx.Colour(color))
    btn.SetForegroundColour(wx.Colour(CLR_TEXT))
    btn.SetFont(wx.Font(font_size, wx.FONTFAMILY_DEFAULT,
                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
    btn.SetBezelWidth(1)
    btn.SetUseFocusIndicator(False)

    _orig = color

    def _darken(c: str, f: float = 0.88) -> str:
        col = wx.Colour(c)
        return "#{:02x}{:02x}{:02x}".format(
            int(col.Red() * f), int(col.Green() * f), int(col.Blue() * f))

    def _lighten(c: str, f: float = 1.08) -> str:
        col = wx.Colour(c)
        return "#{:02x}{:02x}{:02x}".format(
            min(255, int(col.Red() * f)),
            min(255, int(col.Green() * f)),
            min(255, int(col.Blue() * f)))

    hover = _lighten(_orig)
    press = _darken(_orig)

    def on_enter(e): btn.SetBackgroundColour(wx.Colour(hover)); btn.Refresh(); e.Skip()
    def on_leave(e): btn.SetBackgroundColour(wx.Colour(_orig)); btn.Refresh(); e.Skip()
    def on_down(e):  btn.SetBackgroundColour(wx.Colour(press)); btn.Refresh(); e.Skip()
    def on_up(e):    btn.SetBackgroundColour(wx.Colour(_orig)); btn.Refresh(); e.Skip()

    btn.Bind(wx.EVT_ENTER_WINDOW, on_enter)
    btn.Bind(wx.EVT_LEAVE_WINDOW, on_leave)
    btn.Bind(wx.EVT_LEFT_DOWN,    on_down)
    btn.Bind(wx.EVT_LEFT_UP,      on_up)
    return btn


def _static_box_sizer(parent: wx.Window, label: str) -> wx.StaticBoxSizer:
    """StaticBoxSizer в стиле AT-CAD."""
    box = wx.StaticBox(parent, label=f"  {label}  ")
    box.SetForegroundColour(wx.Colour(CLR_BOX_FG))
    box.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT,
                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
    return wx.StaticBoxSizer(box, wx.VERTICAL)


def _open_path(path: Path) -> None:
    os.startfile(str(path))

def _show_in_explorer(path: Path) -> None:
    subprocess.run(["explorer", "/select,", str(path)], check=False)

# ============================================================
# Окно результатов
# ============================================================

class ResultsDialog(wx.Dialog):
    """Модальное окно с таблицей найденных заказов."""

    def __init__(self, parent: wx.Window, entries: list[KEntry], title: str):
        super().__init__(
            parent,
            title=title or TXT["results_title"],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1100, 560),
        )
        self.entries = entries
        self._build()
        self.CentreOnScreen()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        # --- Таблица ---
        tbl_sizer = _static_box_sizer(self, TXT["results_box"])

        self.tree = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self.tree.SetBackgroundColour(wx.Colour("#f0f4f0"))
        self.tree.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        ))

        cols = [
            (TXT["table_order"], 90),
            (TXT["table_year"], 60),
            (TXT["table_folder_exists"], 130),
            (TXT["table_folder"], 330),
            (TXT["table_sketch"], 280),
            (TXT["table_dwg"], 220),
        ]
        for idx, (hdr, width) in enumerate(cols):
            self.tree.InsertColumn(idx, hdr, width=width)

        for entry in self.entries:
            row = [
                entry.k_code,
                str(entry.year) if entry.year else "—",
                TXT["table_has_folder_yes"] if entry.has_folder else TXT["table_has_folder_no"],
                entry.folder_path if entry.has_folder else "—",
                entry.sketch_path if entry.has_folder else "—",
                entry.dwg_path if entry.has_folder else "—",
            ]
            idx = self.tree.InsertItem(self.tree.GetItemCount(), row[0])
            for col, val in enumerate(row[1:], 1):
                self.tree.SetItem(idx, col, val)

            if not entry.has_folder:
                self.tree.SetItemBackgroundColour(idx, wx.Colour("#fff0a0"))

        self.tree.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _: self._open_folder())
        tbl_sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 6)

        # --- Кнопки действий ---
        act_sizer = _static_box_sizer(self, TXT["actions_title"])
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["open_folder"], CLR_BTN_OK, self._open_folder),
            (TXT["open_sketch"], CLR_BTN_OK, self._open_sketch),
            (TXT["open_dwg"], CLR_BTN_PRIMARY, self._open_dwg),
            (TXT["close_dialog"], CLR_BTN_DANGER, self.Close),
        ]

        for label, color, handler in actions:
            btn = _make_gen_button(self, label, color, wx.Size(-1, 34), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            btn_row.Add(btn, 1, wx.RIGHT, 6)

        act_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 6)

        outer.Add(tbl_sizer, 1, wx.EXPAND | wx.ALL, 10)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _selected(self) -> Optional[KEntry]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND:
            return None

        code = self.tree.GetItemText(idx, 0)
        for entry in self.entries:
            if entry.k_code == code:
                return entry
        return None

    def _require_folder(self) -> Optional[KEntry]:
        entry = self._selected()
        if not entry:
            wx.MessageBox(
                TXT["msg_select_entry"],
                TXT["msg_hint"],
                wx.OK | wx.ICON_INFORMATION
            )
            return None

        if not entry.has_folder:
            wx.MessageBox(
                TXT["msg_no_folder_single"].format(code=entry.k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING
            )
            return None

        return entry

    def _open_folder(self) -> None:
        entry = self._require_folder()
        if not entry:
            return

        path = Path(entry.folder_path)
        if path.exists():
            _open_path(path)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

    def _open_sketch(self) -> None:
        entry = self._require_folder()
        if not entry:
            return

        path = Path(entry.sketch_path)
        if path.exists():
            _open_path(path)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

    def _open_dwg(self) -> None:
        entry = self._require_folder()
        if not entry:
            return

        path = Path(entry.dwg_path)
        if path.exists():
            _open_path(path)
        else:
            wx.MessageBox(
                TXT["msg_file_missing"].format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

class DXFResultsDialog(wx.Dialog):
    """Модальное окно с результатами поиска DXF/DWG по K-номеру."""

    def __init__(self, parent: wx.Window, results: list[DXFSearchResult], title: str):
        super().__init__(
            parent,
            title=title or TXT["dxf_results_title"],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1120, 560),
        )
        self.results = results
        self._build()
        self.CentreOnScreen()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        # --- Таблица результатов ---
        data_sizer = _static_box_sizer(self, TXT["dxf_box"])

        self.tree = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self.tree.SetBackgroundColour(wx.Colour("#f0f4f0"))
        self.tree.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        ))

        cols = [
            (TXT["dxf_col_no"], 90),
            (TXT["dxf_col_k"], 90),
            (TXT["dxf_col_wst"], 110),
            (TXT["dxf_col_dicke"], 90),
            (TXT["dxf_col_area"], 120),
            (TXT["dxf_col_length"], 150),
            (TXT["dxf_col_price"], 100),
            (TXT["dxf_col_file"], 250),
        ]
        for idx, (hdr, width) in enumerate(cols):
            self.tree.InsertColumn(idx, hdr, width=width)

        for res in self.results:
            file_name = Path(res.main_dwg_path).name if res.main_dwg_path else "—"
            row = [
                str(res.dxf_no),
                res.k_num,
                res.wst,
                "" if res.dicke_mm is None else f"{res.dicke_mm:g}",
                "" if res.a_kn_brutto_qm is None else f"{res.a_kn_brutto_qm:g}",
                "" if res.laenge_zuschnitt_mm is None else f"{res.laenge_zuschnitt_mm:g}",
                "" if res.preis_pro_laenge_eur is None else f"{res.preis_pro_laenge_eur:g}",
                file_name,
            ]

            idx = self.tree.InsertItem(self.tree.GetItemCount(), row[0])
            for col, val in enumerate(row[1:], 1):
                self.tree.SetItem(idx, col, val)

            if not res.has_main_dwg:
                self.tree.SetItemBackgroundColour(idx, wx.Colour("#fff0a0"))

        self.tree.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _: self._open_dwg_file())
        data_sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 6)

        # --- Кнопки действий ---
        act_sizer = _static_box_sizer(self, TXT["dxf_actions_box"])
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["dxf_open_folder"], CLR_BTN_OK, self._open_dwg_folder),
            (TXT["dxf_open_file"], CLR_BTN_PRIMARY, self._open_dwg_file),
            (TXT["dxf_save_file"], CLR_BTN_DARK, self._save_to_file),
            (TXT["dxf_close"], CLR_BTN_DANGER, self.Close),
        ]

        for label, color, handler in actions:
            btn = _make_gen_button(self, label, color, wx.Size(-1, 34), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            btn_row.Add(btn, 1, wx.RIGHT, 6)

        act_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 6)

        outer.Add(data_sizer, 1, wx.EXPAND | wx.ALL, 10)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _selected(self) -> Optional[DXFSearchResult]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND:
            return None

        dxf_no_txt = self.tree.GetItemText(idx, 0)
        try:
            dxf_no = int(dxf_no_txt)
        except ValueError:
            return None

        for res in self.results:
            if res.dxf_no == dxf_no:
                return res
        return None

    def _require_selected(self) -> Optional[DXFSearchResult]:
        res = self._selected()
        if not res:
            wx.MessageBox(
                TXT["dxf_select_entry"],
                TXT["msg_hint"],
                wx.OK | wx.ICON_INFORMATION
            )
            return None
        return res

    def _open_dwg_folder(self) -> None:
        res = self._require_selected()
        if not res:
            return

        if not res.main_dwg_path:
            wx.MessageBox(
                TXT["dxf_folder_missing"].format(path="—"),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )
            return

        folder = Path(res.main_dwg_path).parent
        if folder.exists():
            _open_path(folder)
        else:
            wx.MessageBox(
                TXT["dxf_folder_missing"].format(path=folder),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

    def _open_dwg_file(self) -> None:
        res = self._require_selected()
        if not res:
            return

        path = Path(res.main_dwg_path)
        if res.has_main_dwg and path.exists():
            _open_path(path)
        else:
            wx.MessageBox(
                TXT["dxf_file_missing"].format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

    def _save_to_file(self) -> None:
        if not self.results:
            return

        dlg = wx.FileDialog(
            self,
            message=TXT["dxf_save_title"],
            wildcard="Textdateien (*.txt)|*.txt|CSV-Dateien (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        target = Path(dlg.GetPath())
        dlg.Destroy()

        is_csv = target.suffix.lower() == ".csv"

        try:
            if is_csv:
                lines = [
                    "DXF;K-Nr.;Werkstoff;Dicke,mm;A Kn brutto,qm;Länge Zuschnitt,mm;Preis/Länge €;DWG"
                ]
                for r in self.results:
                    lines.append(
                        f"{r.dxf_no};{r.k_num};{r.wst};"
                        f"{'' if r.dicke_mm is None else r.dicke_mm};"
                        f"{'' if r.a_kn_brutto_qm is None else r.a_kn_brutto_qm};"
                        f"{'' if r.laenge_zuschnitt_mm is None else r.laenge_zuschnitt_mm};"
                        f"{'' if r.preis_pro_laenge_eur is None else r.preis_pro_laenge_eur};"
                        f"{r.main_dwg_path}"
                    )
                target.write_text("\n".join(lines), encoding="utf-8")
            else:
                lines = []
                for r in self.results:
                    lines.append(f"DXF: {r.dxf_no}")
                    lines.append(f"K-Nr.: {r.k_num}")
                    lines.append(f"Werkstoff: {r.wst}")
                    lines.append(f"Dicke, mm: {'' if r.dicke_mm is None else r.dicke_mm}")
                    lines.append(f"A Kn brutto, qm: {'' if r.a_kn_brutto_qm is None else r.a_kn_brutto_qm}")
                    lines.append(f"Länge Zuschnitt, mm: {'' if r.laenge_zuschnitt_mm is None else r.laenge_zuschnitt_mm}")
                    lines.append(f"Preis/Länge €: {'' if r.preis_pro_laenge_eur is None else r.preis_pro_laenge_eur}")
                    lines.append(f"DWG: {r.main_dwg_path}")
                    lines.append("-" * 60)
                target.write_text("\n".join(lines), encoding="utf-8")

            wx.MessageBox(
                TXT["dxf_save_done"].format(path=target),
                TXT["update_done_title"],
                wx.OK | wx.ICON_INFORMATION
            )
        except OSError as e:
            wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR)

class ServiceDialog(wx.Dialog):
    """Служебное окно с действиями по индексу и краткой информацией."""

    def __init__(self, parent: wx.Window, title: str):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE,
            size=wx.Size(*parent.cfg.service_window_size), # type: ignore
        )
        self.owner = parent
        self._build()
        self._refresh_info()
        self.CentreOnParent()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        info_sizer = _static_box_sizer(self, TXT["service_info_box"])

        self.info_lbl = wx.StaticText(self, label="—")
        self.info_lbl.SetForegroundColour(wx.Colour(CLR_LABEL))
        self.info_lbl.SetFont(wx.Font(
            9,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        ))
        info_sizer.Add(self.info_lbl, 0, wx.ALL | wx.EXPAND, 6)

        outer.Add(info_sizer, 0, wx.EXPAND | wx.ALL, 10)

        act_sizer = _static_box_sizer(self, TXT["service_actions_box"])
        btn_col = wx.BoxSizer(wx.VERTICAL)

        self.btn_partial = _make_gen_button(
            self, TXT["service_update_partial"], CLR_BTN_WARN, wx.Size(-1, 34), 10
        )
        self.btn_partial.Bind(wx.EVT_BUTTON, lambda _: self._run_partial())

        self.btn_full = _make_gen_button(
            self, TXT["service_update_full"], CLR_BTN_DANGER, wx.Size(-1, 34), 10
        )
        self.btn_full.Bind(wx.EVT_BUTTON, lambda _: self._run_full())

        self.btn_close = _make_gen_button(
            self, TXT["service_close"], CLR_BTN_DARK, wx.Size(-1, 34), 10
        )
        self.btn_close.Bind(wx.EVT_BUTTON, lambda _: self.Close())

        btn_col.Add(self.btn_partial, 0, wx.EXPAND | wx.BOTTOM, 6)
        btn_col.Add(self.btn_full, 0, wx.EXPAND | wx.BOTTOM, 6)
        btn_col.Add(self.btn_close, 0, wx.EXPAND)

        act_sizer.Add(btn_col, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)

    def _refresh_info(self) -> None:
        meta = self.owner.index.get_meta() # type: ignore
        count = meta.get("count", 0)
        gen = meta.get("generated_at", "—")
        root = meta.get("root", str(self.owner.cfg.root_dir)) # type: ignore

        self.info_lbl.SetLabel(
            f"Einträge: {count}\n"
            f"Aktualisiert: {gen}\n"
            f"Pfad: {root}\n"
            f"Rückschritt: {self.owner.cfg.tail_backtrack}\n" # type: ignore
            f"Geprüfte Jahre: {self.owner.cfg.tail_years_to_scan}" # type: ignore
        )

    def _run_partial(self) -> None:
        if wx.MessageBox(
                TXT["service_partial_confirm"],
                TXT["update_confirm_title"],
                wx.YES_NO | wx.ICON_QUESTION
        ) != wx.YES:
            return

        self.owner.run_partial_update(
            silent=False,
            on_done=self._refresh_info
        )

    def _run_full(self) -> None:
        if wx.MessageBox(
                TXT["service_full_confirm"],
                TXT["msg_rebuild_confirm_title"],
                wx.YES_NO | wx.ICON_QUESTION
        ) != wx.YES:
            return

        self.owner.run_full_rebuild(
            on_done=self._refresh_info
        )

# ============================================================
# Главное окно
# ============================================================

class KFinderFrame(wx.Frame):
    """Главное окно K-Finder в стиле AT-CAD."""

    def __init__(self, cfg: AppConfig = APP_CONFIG):
        super().__init__(
            None,
            title=TXT["app_title"],
            size=wx.Size(*cfg.window_size),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.cfg = cfg
        self.index = KIndex(cfg)
        self.service = SearchService(cfg, self.index)
        self.dxf_repo = DXFRepository()
        self.appnr_repo = AppNrRepository()

        self._rebuild_running: bool = False
        self._main_buttons: list[wx.Window] = []
        self._service_buttons: list[wx.Window] = []

        self.SetBackgroundColour(wx.Colour(CLR_BG))
        self.SetMinSize(wx.Size(390, 500))
        self._center()
        self._build()
        self._check_root()
        self.Bind(wx.EVT_CLOSE, self._on_close)

        if self.cfg.auto_update_on_start:
            wx.CallLater(300, lambda: self._update_tail_async(
                ask=False,
                silent=True
            ))

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _center(self) -> None:
        sw, sh = wx.GetDisplaySize()
        w, h = self.GetSize()
        self.SetPosition(wx.Point((sw - w) // 2, (sh - h) // 2))

    def _build(self) -> None:
        outer = wx.BoxSizer(wx.VERTICAL)

        # ── Поле ввода и тип поиска ───────────────────────────────────────
        input_sizer = _static_box_sizer(self, TXT["input_box"])

        hint = wx.StaticText(self, label=TXT["input_hint"])
        hint.SetForegroundColour(wx.Colour(CLR_LABEL))
        hint.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL
        ))
        input_sizer.Add(hint, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 4)

        row = wx.BoxSizer(wx.HORIZONTAL)

        # --- Общая высота элементов ---
        ctrl_height = 36

        # --- Choice (выровнен по высоте) ---
        self.search_mode = wx.Choice(
            self,
            choices=[
                TXT["search_mode_k"],
                TXT["search_mode_dxf"],
                TXT["search_mode_app"],
            ],
            size=wx.Size(50, ctrl_height),
        )
        self.search_mode.SetSelection(0)
        self.search_mode.SetMinSize(wx.Size(95, ctrl_height))
        self.search_mode.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD
        ))

        # --- Поле ввода ---
        self.entry = wx.TextCtrl(
            self,
            style=wx.TE_CENTER | wx.TE_PROCESS_ENTER,
            size=wx.Size(170, ctrl_height),
        )
        self.entry.SetMinSize(wx.Size(170, ctrl_height))
        self.entry.SetFont(wx.Font(
            18,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD
        ))
        self.entry.SetForegroundColour(wx.Colour("#1a3a1a"))
        self.entry.Bind(wx.EVT_TEXT_ENTER, lambda _: self._smart_search())

        # --- Кнопка очистки ---
        clear_btn = _make_gen_button(
            self,
            "✖",
            CLR_BTN_DANGER,
            wx.Size(36, ctrl_height),
            12
        )

        def _clear():
            self.entry.SetValue("")
            self.search_mode.SetSelection(0)  # возврат к "K"
            self.entry.SetFocus()

        clear_btn.Bind(wx.EVT_BUTTON, lambda _: _clear())

        # --- Компоновка ---
        row.Add(self.search_mode, 0, wx.RIGHT, 8)
        row.Add(self.entry, 1, wx.RIGHT, 6)
        row.Add(clear_btn, 0)

        input_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ── Основные действия ─────────────────────────────────────────────
        action_sizer = _static_box_sizer(self, TXT["actions_box"])
        actions = [
            (TXT["search_show"], CLR_BTN_PRIMARY, "show"),
            (TXT["open_folder"], CLR_BTN_OK, "folder"),
            (TXT["open_sketch"], CLR_BTN_OK, "sketch"),
            (TXT["open_dwg"], CLR_BTN_PRIMARY, "dwg"),
            (TXT["open_dxf"], CLR_BTN_DARK, "dxf"),
        ]
        for label, color, action in actions:
            btn = _make_gen_button(self, label, color, wx.Size(-1, 38), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, a=action: self._handle_action(a))
            action_sizer.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            self._main_buttons.append(btn)

        outer.Add(action_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # ── Компактный статус ─────────────────────────────────────────────
        status_sizer = _static_box_sizer(self, TXT["status_box"])

        self.status_lbl = wx.StaticText(self, label=TXT["status_ready_short"])
        self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_OK))
        self.status_lbl.SetFont(wx.Font(
            9,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD
        ))
        self.status_lbl.Wrap(340)
        status_sizer.Add(self.status_lbl, 0, wx.ALL | wx.EXPAND, 6)

        outer.Add(status_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ── Нижние кнопки ─────────────────────────────────────────────────
        bottom_row = wx.BoxSizer(wx.HORIZONTAL)

        service_btn = _make_gen_button(
            self, TXT["service_button"], CLR_BTN_WARN, wx.Size(-1, 30), 9
        )
        service_btn.Bind(wx.EVT_BUTTON, lambda _: self._open_service_dialog())

        about_btn = _make_gen_button(
            self, TXT["about_button"], CLR_BTN_DARK, wx.Size(-1, 30), 9
        )
        about_btn.Bind(wx.EVT_BUTTON, lambda _: self._show_about())

        exit_btn = _make_gen_button(
            self, TXT["close_program"], CLR_BTN_DANGER, wx.Size(-1, 30), 9
        )
        exit_btn.Bind(wx.EVT_BUTTON, lambda _: self.Close())

        bottom_row.Add(service_btn, 1, wx.RIGHT, 6)
        bottom_row.Add(about_btn, 1, wx.RIGHT, 6)
        bottom_row.Add(exit_btn, 1)

        outer.Add(bottom_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)
        self.entry.SetFocus()

    # ------------------------------------------------------------------
    # Статус и блокировка
    # ------------------------------------------------------------------

    def _set_status(self, text: str, level: str = "ok") -> None:
        colors = {
            "ok": CLR_STATUS_OK,
            "warn": CLR_STATUS_WARN,
            "err": CLR_STATUS_ERR,
        }
        self.status_lbl.SetLabel(text)
        self.status_lbl.SetForegroundColour(wx.Colour(colors.get(level, CLR_STATUS_OK)))
        self.status_lbl.Wrap(340)
        self.status_lbl.Refresh()
        self.Layout()

    def _set_busy(self, busy: bool) -> None:
        """Блокирует/разблокирует основное окно на время индексации."""
        self.entry.Enable(not busy)

        for btn in self._main_buttons:
            btn.Enable(not busy)

        for btn in self._service_buttons:
            btn.Enable(not busy)

        if busy:
            if not wx.IsBusy():
                wx.BeginBusyCursor()
        else:
            if wx.IsBusy():
                wx.EndBusyCursor()

    # ------------------------------------------------------------------
    # DXF/DWG
    # ------------------------------------------------------------------

    def _show_dxf_results(self, k_code: str) -> None:
        results = self.dxf_repo.search_by_k_num(k_code)

        if not results:
            wx.MessageBox(
                TXT["dxf_no_hits"].format(code=k_code),
                TXT["dxf_no_hits_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        dlg = DXFResultsDialog(self, results, f"{TXT['dxf_results_title']} — {k_code}")
        dlg.ShowModal()
        dlg.Destroy()

    # ------------------------------------------------------------------
    # Служебное окно
    # ------------------------------------------------------------------

    def _open_service_dialog(self) -> None:
        dlg = ServiceDialog(self, TXT["service_dialog_title"])
        dlg.ShowModal()
        dlg.Destroy()

    # ------------------------------------------------------------------
    # Обновление индекса
    # ------------------------------------------------------------------

    def _update_tail_async(self, ask: bool = True, silent: bool = False, on_done=None) -> None:
        if self._rebuild_running:
            if not silent:
                wx.MessageBox(
                    TXT["update_already_running"],
                    TXT["update_confirm_title"],
                    wx.OK | wx.ICON_INFORMATION
                )
            return

        if ask:
            if wx.MessageBox(
                TXT["update_confirm"],
                TXT["update_confirm_title"],
                wx.YES_NO | wx.ICON_QUESTION
            ) != wx.YES:
                return

        self._rebuild_running = True
        self._set_busy(True)
        self._set_status(
            TXT["status_start_update"] if silent else TXT["service_update_running"],
            "warn"
        )

        def worker():
            try:
                count = self.index.update_tail(
                    backtrack=self.cfg.tail_backtrack,
                    tail_years_to_scan=self.cfg.tail_years_to_scan,
                    progress_cb=lambda m: self.after(lambda msg=m: self._set_status(msg, "warn"))
                )
                self.after(lambda: self._set_status(
                    TXT["service_partial_done"].format(count=count), "ok"
                ))
                if not silent:
                    self.after(lambda: wx.MessageBox(
                        TXT["update_done_msg"].format(count=count),
                        TXT["update_done_title"],
                        wx.OK | wx.ICON_INFORMATION
                    ))
                if on_done:
                    self.after(on_done)
            except (OSError, FileNotFoundError) as e:
                logger.error(f"update_tail: {e}")
                self.after(lambda: self._set_status(TXT["service_update_error"], "err"))
                if not silent:
                    self.after(lambda: wx.MessageBox(
                        str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR
                    ))
            finally:
                self.after(lambda: setattr(self, "_rebuild_running", False))
                self.after(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def _rebuild_async(self, ask: bool = True, on_done=None) -> None:
        if self._rebuild_running:
            wx.MessageBox(
                TXT["msg_rebuild_already_running"],
                TXT["msg_rebuild_confirm_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            return

        if ask:
            if wx.MessageBox(
                TXT["msg_rebuild_confirm"],
                TXT["msg_rebuild_confirm_title"],
                wx.YES_NO | wx.ICON_QUESTION
            ) != wx.YES:
                return

        self._rebuild_running = True
        self._set_busy(True)
        self._set_status(TXT["service_rebuild_running"], "warn")

        def worker():
            try:
                count = self.index.rebuild(
                    progress_cb=lambda m: self.after(lambda msg=m: self._set_status(msg, "warn"))
                )
                self.after(lambda: self._set_status(
                    TXT["service_full_done"].format(count=count), "ok"
                ))
                self.after(lambda: wx.MessageBox(
                    TXT["msg_rebuild_done"].format(count=count),
                    TXT["msg_rebuild_done_title"],
                    wx.OK | wx.ICON_INFORMATION
                ))
                if on_done:
                    self.after(on_done)
            except (OSError, FileNotFoundError) as e:
                logger.error(f"rebuild: {e}")
                self.after(lambda: self._set_status(TXT["service_rebuild_error"], "err"))
                self.after(lambda: wx.MessageBox(
                    str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR
                ))
            finally:
                self.after(lambda: setattr(self, "_rebuild_running", False))
                self.after(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def after(self, func) -> None:
        """Безопасный вызов из фонового потока."""
        wx.CallAfter(func)

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    def _check_root(self) -> None:
        if not self.index.is_root_available():
            self._set_status(TXT["status_root_warn"], "warn")
            wx.MessageBox(
                TXT["msg_root_unavailable"].format(path=self.cfg.root_dir),
                TXT["msg_warning"],
                wx.OK | wx.ICON_WARNING
            )

    def _on_close(self, _event: wx.CloseEvent) -> None:
        self.Destroy()

    # ------------------------------------------------------------------
    # Поиск и действия
    # ------------------------------------------------------------------

    def _get_query(self) -> str:
        return self.entry.GetValue().strip()

    def _get_search_mode(self) -> str:
        return self.search_mode.GetStringSelection()

    def _get_serials_text_for_k(self, k_code: str) -> str:
        serials = self.appnr_repo.get_serials_for_k(k_code)
        return ", ".join(serials)

    def _resolve_app_to_k_codes(self, raw: str) -> list[str]:
        records = self.appnr_repo.search_by_serial(raw)
        codes = sorted({r.k_code for r in records})
        return codes

    def _normalize_dxf_input(self, raw: str) -> str:
        s = raw.strip()
        if not s or not s.isdigit():
            raise ValueError(TXT["msg_dxf_input_error"])
        return s

    def _smart_search(self) -> None:
        raw = self._get_query()
        if not raw:
            wx.MessageBox(
                TXT["msg_input_required"],
                TXT["msg_hint"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            return

        mode = self._get_search_mode()

        try:
            if mode == TXT["search_mode_k"]:
                if self.index.is_full_code(raw):
                    self._process_full(self.index.normalize_full(raw), "show")
                else:
                    self._process_partial(raw)
                return

            if mode == TXT["search_mode_dxf"]:
                dxf_no = self._normalize_dxf_input(raw)
                self._process_dxf(dxf_no, "show")
                return

            if mode == TXT["search_mode_app"]:
                self._process_app_nr(raw, "show")
                return

        except ValueError as e:
            wx.MessageBox(str(e), TXT["msg_input_error"], wx.OK | wx.ICON_ERROR)
            self.entry.SetFocus()
            self.entry.SelectAll()

    def _handle_action(self, action: str) -> None:
        raw = self._get_query()
        if not raw:
            wx.MessageBox(
                TXT["msg_input_required"],
                TXT["msg_hint"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            return

        mode = self._get_search_mode()

        try:
            if mode == TXT["search_mode_k"]:
                if action == "dxf":
                    if not self.index.is_full_code(raw):
                        wx.MessageBox(
                            TXT["msg_input_error"],
                            TXT["msg_hint"],
                            wx.OK | wx.ICON_INFORMATION
                        )
                        self.entry.SetFocus()
                        self.entry.SelectAll()
                        return

                    self._show_dxf_results(self.index.normalize_full(raw))
                    return

                if self.index.is_full_code(raw):
                    self._process_full(self.index.normalize_full(raw), action)
                else:
                    self._process_partial(raw)
                return

            if mode == TXT["search_mode_dxf"]:
                dxf_no = self._normalize_dxf_input(raw)
                self._process_dxf(dxf_no, action)
                return

            if mode == TXT["search_mode_app"]:
                self._process_app_nr(raw, action)
                return

        except ValueError as e:
            wx.MessageBox(str(e), TXT["msg_input_error"], wx.OK | wx.ICON_ERROR)
            self.entry.SetFocus()
            self.entry.SelectAll()
        except (OSError, FileNotFoundError) as e:
            self._set_status(str(e), "err")
            wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR)

    def _process_dxf(self, dxf_no: str, action: str) -> None:
        results = self.dxf_repo.search_by_dxf_no(dxf_no)

        if not results:
            wx.MessageBox(
                TXT["msg_dxf_not_found"].format(query=dxf_no),
                TXT["msg_dxf_not_found_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        if action in ("show", "dxf"):
            dlg = DXFResultsDialog(self, results, f"{TXT['dxf_results_title']} — {dxf_no}")
            dlg.ShowModal()
            dlg.Destroy()
            return

        # Для прямого DXF действия открываем первый найденный основной DWG
        first = results[0]
        path = Path(first.main_dwg_path)

        if action == "folder":
            folder = path.parent
            if folder.exists():
                _open_path(folder)
            else:
                wx.MessageBox(
                    TXT["dxf_folder_missing"].format(path=folder),
                    TXT["msg_error"],
                    wx.OK | wx.ICON_WARNING
                )
            return

        if action == "dwg":
            if first.has_main_dwg and path.exists():
                _open_path(path)
            else:
                wx.MessageBox(
                    TXT["dxf_file_missing"].format(path=path),
                    TXT["msg_error"],
                    wx.OK | wx.ICON_WARNING
                )
            return

        if action == "sketch":
            wx.MessageBox(
                TXT["msg_mode_not_supported"],
                TXT["msg_hint"],
                wx.OK | wx.ICON_INFORMATION
            )

    def _process_app_nr(self, raw: str, action: str) -> None:
        codes = self._resolve_app_to_k_codes(raw)

        if not codes:
            wx.MessageBox(
                TXT["msg_app_not_found"].format(query=raw),
                TXT["msg_app_not_found_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        if len(codes) > 1:
            wx.MessageBox(
                TXT["msg_app_multi"].format(query=raw, codes=", ".join(codes)),
                TXT["msg_app_multi_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        k_code = codes[0]

        if action == "dxf":
            self._show_dxf_results(k_code)
            return

        self._process_full(k_code, action)

    def _process_full(self, k_code: str, action: str) -> None:
        self._set_status(TXT["status_searching"].format(code=k_code), "ok")
        entry = self.service.get_or_search(k_code)

        if not entry:
            self._set_status(TXT["status_not_found"].format(code=k_code), "warn")
            wx.MessageBox(
                TXT["msg_not_found_full"].format(code=k_code),
                TXT["msg_not_found_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        if not entry.has_folder:
            self._set_status(TXT["status_no_folder"].format(code=k_code), "warn")
            wx.MessageBox(
                TXT["msg_no_folder_full"].format(code=k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        serials_text = self._get_serials_text_for_k(k_code)
        if serials_text:
            self._set_status(
                TXT["status_found_with_serial"].format(code=k_code, serials=serials_text),
                "ok"
            )
        else:
            self._set_status(TXT["status_found"].format(code=k_code), "ok")

        if action == "show":
            title = k_code
            if serials_text:
                short_serials = serials_text if len(serials_text) <= 60 else serials_text[:57] + "..."
                title = f"{k_code} | App. Nr.: {short_serials}"

            dlg = ResultsDialog(self, [entry], title)
            dlg.ShowModal()
            dlg.Destroy()
            return

        path_map = {
            "folder": Path(entry.folder_path),
            "sketch": Path(entry.sketch_path),
            "dwg": Path(entry.dwg_path),
        }
        path = path_map.get(action)
        if path is None:
            return

        if path.exists():
            _open_path(path)
        else:
            msg = TXT["msg_file_missing"] if action == "dwg" else TXT["msg_folder_missing"]
            wx.MessageBox(
                msg.format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING
            )

    def _process_partial(self, raw: str) -> None:
        results = self.index.find_partial(raw)
        if not results:
            self._set_status(TXT["status_no_hits"], "warn")
            wx.MessageBox(
                TXT["msg_no_hits"].format(query=raw),
                TXT["msg_no_hits_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        if len(results) == 1:
            entry = results[0]
            if not entry.has_folder:
                self._set_status(TXT["status_no_folder"].format(code=entry.k_code), "warn")
                wx.MessageBox(
                    TXT["msg_no_folder_single"].format(code=entry.k_code),
                    TXT["msg_no_folder_title"],
                    wx.OK | wx.ICON_WARNING
                )
                self.entry.SetFocus()
                self.entry.SelectAll()
                return

            if self.cfg.auto_open_single:
                path = Path(entry.folder_path)
                if path.exists():
                    _open_path(path)
                    self._set_status(TXT["status_found_one"].format(code=entry.k_code), "ok")
                    return

            if self.cfg.auto_show_single:
                dlg = ResultsDialog(self, [entry], entry.k_code)
                dlg.ShowModal()
                dlg.Destroy()
                self._set_status(TXT["status_found_one"].format(code=entry.k_code), "ok")
                return

        dlg = ResultsDialog(self, results, f"Treffer für '{raw}'")
        dlg.ShowModal()
        dlg.Destroy()
        self._set_status(TXT["status_found_many"].format(count=len(results)), "ok")

    # ------------------------------------------------------------------
    # Служебные кнопки
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        wx.MessageBox(
            TXT["about_text"],
            TXT["about_title"],
            wx.OK | wx.ICON_INFORMATION
        )

    def run_partial_update(self, silent: bool = False, on_done=None) -> None:
        """Публичный запуск частичного обновления индекса."""
        self._update_tail_async(ask=False, silent=silent, on_done=on_done)

    def run_full_rebuild(self, on_done=None) -> None:
        """Публичный запуск полной переиндексации."""
        self._rebuild_async(ask=False, on_done=on_done)


# ============================================================
# DXF - Module
# ============================================================
"""
Ядро DXF/DWG-модуля.

Назначение:
  - читать DXF-таблицу Excel
  - читать карту диапазонов DXF-номеров
  - индексировать основные DWG-файлы
  - искать записи по K-номеру
  - объединять данные Excel и файловой системы

Архитектура:
  - DXFConfig            — настройки путей
  - DXFRange             — диапазон DXF-номеров -> папка
  - DXFExcelRecord       — запись из Excel-таблицы
  - DXFFileRecord        — запись о найденном основном DWG
  - DXFSearchResult      — объединённый результат поиска
  - DXFRepository        — работа с Excel, диапазонами, JSON и файлами
"""

# ============================================================
# Конфигурация
# ============================================================

@dataclass(frozen=True)
class DXFConfig:
    dxf_root_dir: Path = Path(r"G:\Drawing\DXF-LASER")
    excel_file: Path = Path(r"G:\Drawing\DXF-LASER\DXF-2017.xlsm")

    ranges_json: Path = APP_DIR / "dxf_ranges.json"
    excel_index_json: Path = APP_DIR / "dxf_excel_index.json"
    files_index_json: Path = APP_DIR / "dxf_index.json"

    min_dxf_no: int = 7801
    max_dxf_no: int = 20000

    # Хвостовое обновление индекса файлов
    file_tail_backtrack: int = 100
    file_tail_forward_scan: int = 700


DXF_CONFIG = DXFConfig()

# ============================================================
# Apparate-Nr. / Seriennummer
# ============================================================

@dataclass(frozen=True)
class AppNrConfig:
    excel_file: Path = Path(r"G:\Auftragsdokumente\Apparate-Nr.xlsx")
    index_json: Path = APP_DIR / "appnr_index.json"


APPNR_CONFIG = AppNrConfig()


@dataclass
class AppNrRecord:
    serial_no: str
    serial_prefix: str
    k_code: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "AppNrRecord":
        return AppNrRecord(
            serial_no=str(d["serial_no"]),
            serial_prefix=str(d["serial_prefix"]),
            k_code=str(d["k_code"]),
        )


class AppNrRepository:
    """
    Репозиторий серийных номеров аппаратов.

    Источник данных:
      - Excel-файл Apparate-Nr.xlsx
      - столбец A: серийный номер
      - столбец E: K-номер

    Индексы:
      - prefix -> записи
      - k_code -> список серийных номеров
    """

    FULL_K_RE = re.compile(r"^K\d{5}$", re.IGNORECASE)

    def __init__(self, cfg: AppNrConfig = APPNR_CONFIG):
        self.cfg = cfg
        self._by_prefix: dict[str, list[AppNrRecord]] = {}
        self._by_k_code: dict[str, list[str]] = {}
        self.reload()

    # --------------------------------------------------------
    # Служебные методы
    # --------------------------------------------------------

    def _normalize_k_code(self, value) -> str:
        if value is None:
            return ""

        s = str(value).strip().upper()
        if not s:
            return ""

        if re.fullmatch(r"\d{5}", s):
            return f"K{s}"

        if self.FULL_K_RE.fullmatch(s):
            return s

        return ""

    def _normalize_serial_text(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _extract_prefix(self, serial_text: str) -> str:
        """
        Для поиска используем только префикс до точки.
        Примеры:
          1234      -> 1234
          1234.1    -> 1234
          1234.1-2  -> 1234
        """
        s = serial_text.strip()
        if not s:
            return ""

        head = s.split(".", 1)[0].strip()
        m = re.match(r"^(\d+)", head)
        return m.group(1) if m else ""

    def is_excel_available(self) -> bool:
        return self.cfg.excel_file.exists() and self.cfg.excel_file.is_file()

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    def _load_raw(self) -> dict:
        if not self.cfg.index_json.is_file():
            return {"items": []}

        try:
            with self.cfg.index_json.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "items" not in data:
                return {"items": []}
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"AppNrRepository._load_raw: {e}")
            return {"items": []}

    def _save_raw(self, data: dict) -> None:
        self.cfg.index_json.parent.mkdir(parents=True, exist_ok=True)
        with self.cfg.index_json.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def reload(self) -> None:
        data = self._load_raw()
        self._by_prefix = {}
        self._by_k_code = {}

        for item in data.get("items", []):
            try:
                rec = AppNrRecord.from_dict(item)
            except (KeyError, TypeError, ValueError):
                continue

            self._by_prefix.setdefault(rec.serial_prefix, []).append(rec)
            self._by_k_code.setdefault(rec.k_code, []).append(rec.serial_no)

        for prefix in self._by_prefix:
            self._by_prefix[prefix].sort(key=lambda x: (x.k_code, x.serial_no))

        for k_code in self._by_k_code:
            self._by_k_code[k_code] = sorted(set(self._by_k_code[k_code]))

    # --------------------------------------------------------
    # Построение индекса
    # --------------------------------------------------------

    def rebuild_index(self) -> int:
        """
        Полная перестройка индекса из Apparate-Nr.xlsx.
        """
        if not self.is_excel_available():
            raise FileNotFoundError(f"Excel-Datei nicht gefunden: {self.cfg.excel_file}")

        wb = load_workbook(self.cfg.excel_file, data_only=True, read_only=True)
        ws = wb.active

        items: list[AppNrRecord] = []
        first = True

        for row in ws.iter_rows(values_only=True):
            if first:
                first = False
                continue

            serial_no = self._normalize_serial_text(row[0] if len(row) > 0 else None)
            k_code = self._normalize_k_code(row[4] if len(row) > 4 else None)

            if not serial_no or not k_code:
                continue

            prefix = self._extract_prefix(serial_no)
            if not prefix:
                continue

            items.append(
                AppNrRecord(
                    serial_no=serial_no,
                    serial_prefix=prefix,
                    k_code=k_code,
                )
            )

        payload = {
            "items": [x.to_dict() for x in items]
        }
        self._save_raw(payload)
        self.reload()
        return len(items)

    def ensure_index(self) -> None:
        if not self._by_prefix and self.is_excel_available():
            self.rebuild_index()

    # --------------------------------------------------------
    # Поиск
    # --------------------------------------------------------

    def search_by_serial(self, query: str) -> list[AppNrRecord]:
        self.ensure_index()

        prefix = self._extract_prefix(str(query).strip())
        if not prefix:
            return []

        return list(self._by_prefix.get(prefix, []))

    def get_serials_for_k(self, k_code: str) -> list[str]:
        self.ensure_index()
        return list(self._by_k_code.get(k_code.strip().upper(), []))


# ============================================================
# Модели
# ============================================================

@dataclass
class DXFRange:
    min_no: int
    max_no: int
    folder_name: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "DXFRange":
        return DXFRange(
            min_no=int(d["min_no"]),
            max_no=int(d["max_no"]),
            folder_name=str(d["folder_name"]),
        )


@dataclass
class DXFExcelRecord:
    dxf_no: int
    k_num: str
    schluessel: str
    wst: str
    dicke_mm: float | None
    a_kn_brutto_qm: float | None
    laenge_zuschnitt_mm: float | None
    preis_pro_laenge_eur: float | None
    bemerkung: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "DXFExcelRecord":
        return DXFExcelRecord(
            dxf_no=int(d["dxf_no"]),
            k_num=str(d["k_num"]),
            schluessel=str(d.get("schluessel", "")),
            wst=str(d.get("wst", "")),
            dicke_mm=d.get("dicke_mm"),
            a_kn_brutto_qm=d.get("a_kn_brutto_qm"),
            laenge_zuschnitt_mm=d.get("laenge_zuschnitt_mm"),
            preis_pro_laenge_eur=d.get("preis_pro_laenge_eur"),
            bemerkung=str(d.get("bemerkung", "")),
        )


@dataclass
class DXFFileRecord:
    dxf_no: int
    folder_name: str
    folder_path: str
    main_dwg_path: str
    has_main_dwg: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "DXFFileRecord":
        return DXFFileRecord(
            dxf_no=int(d["dxf_no"]),
            folder_name=str(d["folder_name"]),
            folder_path=str(d["folder_path"]),
            main_dwg_path=str(d["main_dwg_path"]),
            has_main_dwg=bool(d["has_main_dwg"]),
        )


@dataclass
class DXFSearchResult:
    dxf_no: int
    k_num: str
    wst: str
    dicke_mm: float | None
    a_kn_brutto_qm: float | None
    laenge_zuschnitt_mm: float | None
    preis_pro_laenge_eur: float | None
    main_dwg_path: str
    has_main_dwg: bool

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Репозиторий
# ============================================================

class DXFRepository:
    """
    Главный сервис DXF-модуля.
    """

    PRIMARY_DWG_RE = re.compile(r"^(\d+)\.dwg$", re.IGNORECASE)
    FULL_K_RE = re.compile(r"^K\d{5}$", re.IGNORECASE)

    def __init__(self, cfg: DXFConfig = DXF_CONFIG):
        self.cfg = cfg
        self._ranges: list[DXFRange] = []
        self._excel_index: dict[str, list[DXFExcelRecord]] = {}
        self._files_index: dict[int, DXFFileRecord] = {}

        self.reload_all()

    # --------------------------------------------------------
    # Общие утилиты
    # --------------------------------------------------------

    def reload_all(self) -> None:
        self._ranges = self._load_ranges_json()
        self._excel_index = self._load_excel_index_json()
        self._files_index = self._load_files_index_json()

    def _normalize_k_num(self, value) -> str:
        """
        Приведение K-номера к формату K12345.
        """
        if value is None:
            return ""

        s = str(value).strip().upper()

        if not s:
            return ""

        if re.fullmatch(r"\d+", s):
            return f"K{int(s):05d}"

        if self.FULL_K_RE.fullmatch(s):
            return s

        # Иногда в ячейке может быть что-то не строго числовое — такие строки пропускаем
        return ""

    def _safe_float(self, value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _ensure_parent(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def is_dxf_root_available(self) -> bool:
        return self.cfg.dxf_root_dir.exists() and self.cfg.dxf_root_dir.is_dir()

    def is_excel_available(self) -> bool:
        return self.cfg.excel_file.exists() and self.cfg.excel_file.is_file()

    def _get_range_for_dxf(self, dxf_no: int) -> Optional[DXFRange]:
        for r in self._ranges:
            if r.min_no <= dxf_no <= r.max_no:
                return r
        return None

    def is_primary_dwg_name(self, filename: str) -> bool:
        """
        Основной DWG — только строго xxxxx.dwg без суффиксов.
        """
        return bool(self.PRIMARY_DWG_RE.fullmatch(filename.strip()))

    def search_by_dxf_no(self, query: str) -> list[DXFSearchResult]:
        """
        Поиск по самому DXF-номеру.

        Логика:
          - ищем все строки Excel, где встречается этот DXF
          - если строк Excel нет, но файл существует в индексе файлов,
            всё равно возвращаем минимальную запись
          - результат всегда список, чтобы можно было переиспользовать
            уже существующий DXFResultsDialog
        """
        raw = str(query).strip()
        if not raw or not raw.isdigit():
            return []

        dxf_no = int(raw)
        results: list[DXFSearchResult] = []

        # Ищем все строки Excel с этим DXF
        for rows in self._excel_index.values():
            for row in rows:
                if row.dxf_no != dxf_no:
                    continue

                file_rec = self._files_index.get(dxf_no)
                results.append(
                    DXFSearchResult(
                        dxf_no=row.dxf_no,
                        k_num=row.k_num,
                        wst=row.wst,
                        dicke_mm=row.dicke_mm,
                        a_kn_brutto_qm=row.a_kn_brutto_qm,
                        laenge_zuschnitt_mm=row.laenge_zuschnitt_mm,
                        preis_pro_laenge_eur=row.preis_pro_laenge_eur,
                        main_dwg_path=file_rec.main_dwg_path if file_rec else "",
                        has_main_dwg=file_rec.has_main_dwg if file_rec else False,
                    )
                )

        # Если в Excel ничего нет, но файл известен, возвращаем минимальную запись
        if not results:
            file_rec = self._files_index.get(dxf_no)
            if file_rec:
                results.append(
                    DXFSearchResult(
                        dxf_no=dxf_no,
                        k_num="",
                        wst="",
                        dicke_mm=None,
                        a_kn_brutto_qm=None,
                        laenge_zuschnitt_mm=None,
                        preis_pro_laenge_eur=None,
                        main_dwg_path=file_rec.main_dwg_path,
                        has_main_dwg=file_rec.has_main_dwg,
                    )
                )

        results.sort(key=lambda x: (x.dxf_no, x.k_num))
        return results

    # --------------------------------------------------------
    # JSON: ranges
    # --------------------------------------------------------

    def _load_ranges_json(self) -> list[DXFRange]:
        if not self.cfg.ranges_json.is_file():
            return []

        try:
            with self.cfg.ranges_json.open("r", encoding="utf-8") as f:
                data = json.load(f)

            result: list[DXFRange] = []
            for item in data:
                result.append(DXFRange.from_dict(item))
            return result
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"_load_ranges_json: {e}")
            return []

    def _save_ranges_json(self, ranges: list[DXFRange]) -> None:
        self._ensure_parent(self.cfg.ranges_json)
        payload = [r.to_dict() for r in ranges]
        with self.cfg.ranges_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # --------------------------------------------------------
    # JSON: excel index
    # --------------------------------------------------------

    def _load_excel_index_json(self) -> dict[str, list[DXFExcelRecord]]:
        if not self.cfg.excel_index_json.is_file():
            return {}

        try:
            with self.cfg.excel_index_json.open("r", encoding="utf-8") as f:
                data = json.load(f)

            result: dict[str, list[DXFExcelRecord]] = {}
            for k_num, items in data.items():
                result[k_num] = [DXFExcelRecord.from_dict(x) for x in items]
            return result
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"_load_excel_index_json: {e}")
            return {}

    def _save_excel_index_json(self, index_data: dict[str, list[DXFExcelRecord]]) -> None:
        self._ensure_parent(self.cfg.excel_index_json)
        payload = {
            k_num: [item.to_dict() for item in items]
            for k_num, items in sorted(index_data.items())
        }
        with self.cfg.excel_index_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # --------------------------------------------------------
    # JSON: files index
    # --------------------------------------------------------

    def _load_files_index_json(self) -> dict[int, DXFFileRecord]:
        if not self.cfg.files_index_json.is_file():
            return {}

        try:
            with self.cfg.files_index_json.open("r", encoding="utf-8") as f:
                data = json.load(f)

            result: dict[int, DXFFileRecord] = {}
            for key, item in data.items():
                result[int(key)] = DXFFileRecord.from_dict(item)
            return result
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.error(f"_load_files_index_json: {e}")
            return {}

    def _save_files_index_json(self, index_data: dict[int, DXFFileRecord]) -> None:
        self._ensure_parent(self.cfg.files_index_json)
        payload = {
            str(dxf_no): item.to_dict()
            for dxf_no, item in sorted(index_data.items())
        }
        with self.cfg.files_index_json.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # --------------------------------------------------------
    # Excel: ranges из листа Key
    # --------------------------------------------------------

    def rebuild_ranges_from_workbook(self) -> int:
        """
        Полная перестройка dxf_ranges.json из листа Key.
        """
        if not self.is_excel_available():
            raise FileNotFoundError(f"Excel-Datei nicht gefunden: {self.cfg.excel_file}")

        wb = load_workbook(self.cfg.excel_file, data_only=True, read_only=True, keep_vba=True)
        if "Key" not in wb.sheetnames:
            raise KeyError("Blatt 'Key' wurde in der Excel-Datei nicht gefunden.")

        ws = wb["Key"]
        result: list[DXFRange] = []

        first = True
        for row in ws.iter_rows(values_only=True):
            if first:
                first = False
                continue

            min_no, max_no, path_name = row[:3]

            if min_no is None or max_no is None or path_name is None:
                continue

            try:
                result.append(
                    DXFRange(
                        min_no=int(min_no),
                        max_no=int(max_no),
                        folder_name=str(path_name).strip(),
                    )
                )
            except (TypeError, ValueError):
                continue

        self._save_ranges_json(result)
        self._ranges = result
        return len(result)

    # --------------------------------------------------------
    # Excel: индекс строк по K-номеру
    # --------------------------------------------------------

    def rebuild_excel_index(self) -> int:
        """
        Полная перестройка dxf_excel_index.json из Tabelle1.
        Индексируется только полезные строки:
          - есть DXF-номер
          - есть K-номер (Komm.)
        """
        if not self.is_excel_available():
            raise FileNotFoundError(f"Excel-Datei nicht gefunden: {self.cfg.excel_file}")

        wb = load_workbook(self.cfg.excel_file, data_only=True, read_only=True, keep_vba=True)
        if "Tabelle1" not in wb.sheetnames:
            raise KeyError("Blatt 'Tabelle1' wurde in der Excel-Datei nicht gefunden.")

        ws = wb["Tabelle1"]

        index_data: dict[str, list[DXFExcelRecord]] = {}

        # Колонки:
        # A DXF
        # B Komm.
        # C Schlüssel
        # D Wst.
        # E Dicke tn, mm
        # I A Kn brutto, qm
        # K Länge Zuschnitt, mm
        # N Preis/ Länge €
        # S Bemerkungen
        first = True
        total_records = 0

        for row in ws.iter_rows(values_only=True):
            if first:
                first = False
                continue

            dxf_no = row[0]
            komm = row[1]

            if dxf_no is None or komm is None:
                continue

            try:
                dxf_no_int = int(dxf_no)
            except (TypeError, ValueError):
                continue

            k_num = self._normalize_k_num(komm)
            if not k_num:
                continue

            record = DXFExcelRecord(
                dxf_no=dxf_no_int,
                k_num=k_num,
                schluessel=str(row[2] or ""),
                wst=str(row[3] or ""),
                dicke_mm=self._safe_float(row[4]),
                a_kn_brutto_qm=self._safe_float(row[8]),
                laenge_zuschnitt_mm=self._safe_float(row[10]),
                preis_pro_laenge_eur=self._safe_float(row[13]),
                bemerkung=str(row[18] or ""),
            )

            index_data.setdefault(k_num, []).append(record)
            total_records += 1

        # Сортировка строк внутри каждого K-номера по DXF
        for k_num in index_data:
            index_data[k_num].sort(key=lambda x: (x.dxf_no, x.schluessel))

        self._save_excel_index_json(index_data)
        self._excel_index = index_data
        return total_records

    # --------------------------------------------------------
    # Индекс файлов DWG
    # --------------------------------------------------------

    def _build_file_record(self, dxf_no: int) -> DXFFileRecord:
        """
        Построить запись по одному DXF-номеру на основе карты диапазонов.
        """
        r = self._get_range_for_dxf(dxf_no)
        if r is None:
            return DXFFileRecord(
                dxf_no=dxf_no,
                folder_name="",
                folder_path="",
                main_dwg_path="",
                has_main_dwg=False,
            )

        folder_path = self.cfg.dxf_root_dir / r.folder_name
        main_dwg = folder_path / f"{dxf_no}.dwg"

        return DXFFileRecord(
            dxf_no=dxf_no,
            folder_name=r.folder_name,
            folder_path=str(folder_path),
            main_dwg_path=str(main_dwg),
            has_main_dwg=main_dwg.is_file(),
        )

    def rebuild_files_index_full(self, progress_cb=None) -> int:
        """
        Полная перестройка индекса основных DWG-файлов.
        Индексируются номера от min_dxf_no до max_dxf_no.
        """
        if not self.is_dxf_root_available():
            raise FileNotFoundError(f"DXF-Root nicht verfügbar: {self.cfg.dxf_root_dir}")

        if not self._ranges:
            self.rebuild_ranges_from_workbook()

        result: dict[int, DXFFileRecord] = {}
        total = self.cfg.max_dxf_no - self.cfg.min_dxf_no + 1
        done = 0

        for dxf_no in range(self.cfg.min_dxf_no, self.cfg.max_dxf_no + 1):
            result[dxf_no] = self._build_file_record(dxf_no)
            done += 1

            if progress_cb and (done % 100 == 0 or done == total):
                progress_cb(f"DXF {dxf_no} geprüft ({done}/{total})")

        self._save_files_index_json(result)
        self._files_index = result
        return len(result)

    def update_files_index_tail(self, backtrack: int | None = None, forward_scan: int | None = None, progress_cb=None) -> int:
        """
        Хвостовое обновление индекса файлов.
        Перепроверяются последние номера:
          - назад на backtrack
          - вперёд на forward_scan
        """
        if not self.is_dxf_root_available():
            raise FileNotFoundError(f"DXF-Root nicht verfügbar: {self.cfg.dxf_root_dir}")

        if not self._ranges:
            self.rebuild_ranges_from_workbook()

        if not self._files_index:
            return self.rebuild_files_index_full(progress_cb=progress_cb)

        if backtrack is None:
            backtrack = self.cfg.file_tail_backtrack
        if forward_scan is None:
            forward_scan = self.cfg.file_tail_forward_scan

        known_numbers = list(self._files_index.keys())
        max_known = max(known_numbers) if known_numbers else self.cfg.min_dxf_no

        start_no = max(self.cfg.min_dxf_no, max_known - backtrack)
        end_no = min(self.cfg.max_dxf_no, max_known + forward_scan)

        result = dict(self._files_index)
        total = end_no - start_no + 1
        done = 0

        for dxf_no in range(start_no, end_no + 1):
            result[dxf_no] = self._build_file_record(dxf_no)
            done += 1

            if progress_cb and (done % 50 == 0 or done == total):
                progress_cb(f"DXF {dxf_no} geprüft ({done}/{total})")

        # Убираем хвост выше последнего реально существующего основного DWG
        last_real = 0
        for dxf_no, rec in result.items():
            if rec.has_main_dwg:
                last_real = max(last_real, dxf_no)

        trimmed: dict[int, DXFFileRecord] = {}
        for dxf_no, rec in result.items():
            if dxf_no <= last_real:
                trimmed[dxf_no] = rec

        self._save_files_index_json(trimmed)
        self._files_index = trimmed
        return len(trimmed)

    # --------------------------------------------------------
    # Поиск
    # --------------------------------------------------------

    def search_by_k_num(self, k_num: str) -> list[DXFSearchResult]:
        """
        Поиск всех DXF-записей по K-номеру.
        Возвращает объединённый результат:
          - данные из Excel
          - путь к основному DWG
          - признак существования основного DWG

        В результат намеренно включены только рабочие поля,
        без служебных и второстепенных колонок.
        """
        k_norm = self._normalize_k_num(k_num)
        if not k_norm:
            return []

        excel_rows = self._excel_index.get(k_norm, [])
        results: list[DXFSearchResult] = []

        for row in excel_rows:
            file_rec = self._files_index.get(row.dxf_no)

            results.append(
                DXFSearchResult(
                    dxf_no=row.dxf_no,
                    k_num=row.k_num,
                    wst=row.wst,
                    dicke_mm=row.dicke_mm,
                    a_kn_brutto_qm=row.a_kn_brutto_qm,
                    laenge_zuschnitt_mm=row.laenge_zuschnitt_mm,
                    preis_pro_laenge_eur=row.preis_pro_laenge_eur,
                    main_dwg_path=file_rec.main_dwg_path if file_rec else "",
                    has_main_dwg=file_rec.has_main_dwg if file_rec else False,
                )
            )

        results.sort(key=lambda x: x.dxf_no)
        return results

    # --------------------------------------------------------
    # Быстрая инициализация
    # --------------------------------------------------------

    def ensure_minimum_indexes(self) -> None:
        """
        Создаёт недостающие индексы, если их ещё нет.
        """
        if not self._ranges:
            self.rebuild_ranges_from_workbook()

        if not self._excel_index:
            self.rebuild_excel_index()

        if not self._files_index:
            self.rebuild_files_index_full()

# ============================================================
# Запуск
# ============================================================

def main() -> None:
    app = wx.App(False)
    frame = KFinderFrame(APP_CONFIG)
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()


"""
Сборка exe с иконкой:
pyinstaller --noconfirm --clean --onefile --windowed --icon=kfinder.ico --name=kfinder kfinder_gui.py
pyinstaller --noconfirm --clean --onefile --windowed --icon=kfinder.ico --name=kfinder --hidden-import=openpyxl kfinder_gui.py
"""
