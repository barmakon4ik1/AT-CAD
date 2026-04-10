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

import json
import logging
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    "open_sketch":             "✏️  Skizzenordner öffnen",
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
    auto_open_single:       bool  = False   # сразу открыть папку если 1 результат
    auto_show_single:       bool  = True    # показать ResultsDialog если 1 результат
    live_search_if_missing: bool  = True
    window_size:            tuple = (560, 820)

CONFIG = AppConfig()

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
    FULL_RE    = re.compile(r"^K\d{5}$", re.IGNORECASE)
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
        dwg    = sketch / f"ABW-{k_code}.dwg"
        return KEntry(
            k_code=k_code,
            year=year,
            folder_path=str(folder),
            sketch_path=str(sketch),
            dwg_path=str(dwg),
            has_folder=True,
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
            "root":         str(self.cfg.root_dir),
            "start_year":   self.cfg.start_year,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "count":        len(self._items),
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
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.cfg.root_dir}")
        for year in range(self.cfg.start_year, self._current_year() + 1):
            year_path = self.cfg.root_dir / str(year)
            if not year_path.is_dir():
                continue
            for dirpath, dirnames, _ in os.walk(year_path):
                current = Path(dirpath)
                name    = current.name.upper()
                if name == k_code and current.is_dir():
                    return self._make_entry(k_code, year, current)
                if self.FULL_RE.fullmatch(name):
                    dirnames[:] = []
        return None

    def rebuild(self, progress_cb=None) -> int:
        """
        Полная перестройка индекса.
        Заполняет пропуски в диапазоне номеров записями has_folder=False,
        чтобы повторный поиск не шёл на диск для заведомо отсутствующих папок.
        """
        if not self.is_root_available():
            raise FileNotFoundError(f"Root nicht verfügbar: {self.cfg.root_dir}")

        found_items: dict[str, KEntry] = {}
        min_num: int | None = None
        max_num: int | None = None

        for year in range(self.cfg.start_year, self._current_year() + 1):
            year_path = self.cfg.root_dir / str(year)
            found = 0
            if year_path.is_dir():
                for dirpath, dirnames, _ in os.walk(year_path):
                    current = Path(dirpath)
                    name    = current.name.upper()
                    if self.FULL_RE.fullmatch(name):
                        entry = self._make_entry(name, year, current)
                        found_items[name] = entry
                        dirnames[:] = []
                        found += 1
                        num = int(name[1:])
                        min_num = num if min_num is None else min(min_num, num)
                        max_num = num if max_num is None else max(max_num, num)
            if progress_cb:
                progress_cb(f"{year}: {found} Ordner")

        if min_num is None or max_num is None:
            self.save_entries({})
            return 0

        # Заполняем пропуски в диапазоне has_folder=False
        full_items: dict[str, KEntry] = {}
        for num in range(min_num, max_num + 1):
            code = f"K{num:05d}"
            if code in found_items:
                full_items[code] = found_items[code]
            else:
                full_items[code] = KEntry(
                    k_code=code,
                    year=0,
                    folder_path="",
                    sketch_path="",
                    dwg_path="",
                    has_folder=False,
                )

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
            size=wx.Size(1300, 580),
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
        self.tree.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                  wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        cols = [
            (TXT["table_order"],         90),
            (TXT["table_year"],          55),
            (TXT["table_folder_exists"], 120),
            (TXT["table_folder"],        380),
            (TXT["table_sketch"],        340),
            (TXT["table_dwg"],           280),
        ]
        for idx, (hdr, w) in enumerate(cols):
            self.tree.InsertColumn(idx, hdr, width=w)

        for entry in self.entries:
            row = [
                entry.k_code,
                str(entry.year) if entry.year else "—",
                TXT["table_has_folder_yes"] if entry.has_folder else TXT["table_has_folder_no"],
                entry.folder_path if entry.has_folder else "—",
                entry.sketch_path if entry.has_folder else "—",
                entry.dwg_path    if entry.has_folder else "—",
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
        btn_row   = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["open_folder"],  CLR_BTN_OK,      self._open_folder),
            (TXT["open_sketch"],  CLR_BTN_PRIMARY, self._open_sketch),
            (TXT["open_dwg"],     CLR_BTN_PRIMARY, self._open_dwg),
            (TXT["show_dwg"],     CLR_BTN_DARK,    self._select_dwg),
            (TXT["close_dialog"], CLR_BTN_DANGER,  self.Close),
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
        return next((e for e in self.entries if e.k_code == code), None)

    def _require_folder(self) -> Optional[KEntry]:
        entry = self._selected()
        if not entry:
            wx.MessageBox(TXT["msg_select_entry"], TXT["msg_hint"],
                          wx.OK | wx.ICON_INFORMATION)
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
        p = Path(entry.folder_path)
        if p.exists():
            _open_path(p)
        else:
            wx.MessageBox(TXT["msg_folder_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _open_sketch(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.sketch_path)
        if p.exists():
            _open_path(p)
        else:
            wx.MessageBox(TXT["msg_folder_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _open_dwg(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.dwg_path)
        if p.exists():
            _open_path(p)
        else:
            wx.MessageBox(TXT["msg_file_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _select_dwg(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.dwg_path)
        if p.exists():
            _show_in_explorer(p)
        else:
            wx.MessageBox(TXT["msg_file_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

# ============================================================
# Главное окно
# ============================================================

class KFinderFrame(wx.Frame):
    """Главное окно K-Finder в стиле AT-CAD."""

    def __init__(self, cfg: AppConfig = CONFIG):
        super().__init__(
            None,
            title=TXT["app_title"],
            size=wx.Size(*cfg.window_size),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.cfg     = cfg
        self.index   = KIndex(cfg)
        self.service = SearchService(cfg, self.index)

        self._rebuild_running: bool = False
        self._main_buttons:    list[wx.Window] = []
        self._service_buttons: list[wx.Window] = []

        self.SetBackgroundColour(wx.Colour(CLR_BG))
        self.SetMinSize(wx.Size(480, 700))
        self._center()
        self._build()
        self._update_meta()
        self._check_root()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _center(self) -> None:
        sw, sh = wx.GetDisplaySize()
        w, h   = self.GetSize()
        self.SetPosition(wx.Point((sw - w) // 2, (sh - h) // 2))

    def _build(self) -> None:
        outer = wx.BoxSizer(wx.VERTICAL)

        # ── Баннер ─────────────────────────────────────────────────────
        banner = wx.Panel(self)
        banner.SetBackgroundColour(wx.Colour("#2c5f2e"))
        banner_sz = wx.BoxSizer(wx.VERTICAL)

        title_lbl = wx.StaticText(banner, label="K-Finder")
        title_lbl.SetForegroundColour(wx.Colour("#ffffff"))
        title_lbl.SetFont(wx.Font(26, wx.FONTFAMILY_DEFAULT,
                                  wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD,
                                  faceName="Times New Roman"))
        banner_sz.Add(title_lbl, 0, wx.ALIGN_CENTER | wx.TOP, 8)

        sub_lbl = wx.StaticText(banner, label=TXT["app_subtitle"])
        sub_lbl.SetForegroundColour(wx.Colour("#a8d8a8"))
        sub_lbl.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        banner_sz.Add(sub_lbl, 0, wx.ALIGN_CENTER | wx.BOTTOM, 8)
        banner.SetSizer(banner_sz)
        outer.Add(banner, 0, wx.EXPAND)

        # ── Поле ввода ─────────────────────────────────────────────────
        input_sizer = _static_box_sizer(self, TXT["input_box"])

        hint = wx.StaticText(self, label=TXT["input_hint"])
        hint.SetForegroundColour(wx.Colour(CLR_LABEL))
        hint.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        input_sizer.Add(hint, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 4)

        self.entry = wx.TextCtrl(
            self, style=wx.TE_CENTER | wx.TE_PROCESS_ENTER,
            size=wx.Size(200, 38),
        )
        self.entry.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT,
                                   wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.entry.SetForegroundColour(wx.Colour("#1a3a1a"))
        self.entry.Bind(wx.EVT_TEXT_ENTER, lambda _: self._smart_search())
        input_sizer.Add(self.entry, 0, wx.ALIGN_CENTER | wx.ALL, 6)
        outer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ── Действия ───────────────────────────────────────────────────
        action_sizer = _static_box_sizer(self, TXT["actions_box"])
        actions = [
            (TXT["search_show"], CLR_BTN_PRIMARY, "show"),
            (TXT["open_folder"], CLR_BTN_OK,      "folder"),
            (TXT["open_sketch"], CLR_BTN_OK,      "sketch"),
            (TXT["open_dwg"],    CLR_BTN_PRIMARY, "dwg"),
            (TXT["show_dwg"],    CLR_BTN_DARK,    "select_dwg"),
        ]
        for label, color, action in actions:
            btn = _make_gen_button(self, label, color, wx.Size(-1, 40), 11)
            btn.Bind(wx.EVT_BUTTON, lambda _, a=action: self._handle_action(a))
            action_sizer.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            self._main_buttons.append(btn)
        outer.Add(action_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # ── Служебные кнопки ───────────────────────────────────────────
        svc_sizer = _static_box_sizer(self, TXT["service_box"])
        svc_grid  = wx.GridSizer(2, 2, 6, 6)
        svc_actions = [
            (TXT["rebuild_index"],    CLR_BTN_WARN, self._rebuild_async),
            (TXT["open_index_file"],  CLR_BTN_DARK, self._open_index_file),
            (TXT["open_index_folder"],CLR_BTN_DARK, self._open_index_folder),
            (TXT["open_log_file"],    CLR_BTN_DARK, self._open_log_file),
        ]
        for label, color, handler in svc_actions:
            btn = _make_gen_button(self, label, color, wx.Size(-1, 30), 9)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            svc_grid.Add(btn, 0, wx.EXPAND)
            self._service_buttons.append(btn)
        svc_sizer.Add(svc_grid, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(svc_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ── Метаданные ─────────────────────────────────────────────────
        meta_sizer = _static_box_sizer(self, TXT["meta_box"])
        self.meta_lbl = wx.StaticText(self, label="—")
        self.meta_lbl.SetForegroundColour(wx.Colour(CLR_LABEL))
        self.meta_lbl.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT,
                                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        meta_sizer.Add(self.meta_lbl, 0, wx.ALL, 6)
        outer.Add(meta_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # ── Статус ─────────────────────────────────────────────────────
        status_sizer = _static_box_sizer(self, TXT["status_box"])
        self.status_lbl = wx.StaticText(self, label=TXT["status_ready"])
        self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_OK))
        self.status_lbl.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        status_sizer.Add(self.status_lbl, 0, wx.ALL, 6)
        outer.Add(status_sizer, 1, wx.EXPAND | wx.ALL, 10)

        # ── Кнопка выхода ─────────────────────────────────────────────
        exit_btn = _make_gen_button(self, TXT["close_program"],
                                    CLR_BTN_DANGER, wx.Size(-1, 36), 11)
        exit_btn.Bind(wx.EVT_BUTTON, lambda _: self.Close())
        outer.Add(exit_btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)
        self.entry.SetFocus()

    # ------------------------------------------------------------------
    # Статус и блокировка
    # ------------------------------------------------------------------

    def _set_status(self, text: str, level: str = "ok") -> None:
        colors = {"ok": CLR_STATUS_OK, "warn": CLR_STATUS_WARN, "err": CLR_STATUS_ERR}
        self.status_lbl.SetLabel(text)
        self.status_lbl.SetForegroundColour(wx.Colour(colors.get(level, CLR_STATUS_OK)))
        self.status_lbl.Refresh()

    def _set_busy(self, busy: bool) -> None:
        """Блокирует/разблокирует UI на время перестройки индекса."""
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

    def _update_meta(self) -> None:
        meta  = self.index.get_meta()
        count = meta.get("count", 0)
        gen   = meta.get("generated_at", "—")
        root  = meta.get("root", str(self.cfg.root_dir))
        self.meta_lbl.SetLabel(
            f"Einträge: {count}   |   Aktualisiert: {gen}\nPfad: {root}"
        )

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

    def _on_close(self, event: wx.CloseEvent) -> None:
        self.Destroy()

    # ------------------------------------------------------------------
    # Поиск
    # ------------------------------------------------------------------

    def _get_query(self) -> str:
        return self.entry.GetValue().strip()

    def _smart_search(self) -> None:
        raw = self._get_query()
        if not raw:
            wx.MessageBox(TXT["msg_input_required"], TXT["msg_hint"],
                          wx.OK | wx.ICON_INFORMATION)
            self.entry.SetFocus()
            return
        try:
            if self.index.is_full_code(raw):
                self._process_full(self.index.normalize_full(raw), "show")
            else:
                self._process_partial(raw)
        except ValueError as e:
            wx.MessageBox(str(e), TXT["msg_input_error"], wx.OK | wx.ICON_ERROR)
            self.entry.SetFocus()
            self.entry.SelectAll()

    def _handle_action(self, action: str) -> None:
        raw = self._get_query()
        if not raw:
            wx.MessageBox(TXT["msg_input_required"], TXT["msg_hint"],
                          wx.OK | wx.ICON_INFORMATION)
            self.entry.SetFocus()
            return
        try:
            if self.index.is_full_code(raw):
                self._process_full(self.index.normalize_full(raw), action)
            else:
                self._process_partial(raw)
        except ValueError as e:
            wx.MessageBox(str(e), TXT["msg_input_error"], wx.OK | wx.ICON_ERROR)
            self.entry.SetFocus()
            self.entry.SelectAll()
        except (OSError, FileNotFoundError) as e:
            self._set_status(str(e), "err")
            wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR)

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
                p = Path(entry.folder_path)
                if p.exists():
                    _open_path(p)
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
            self._update_meta()
            self._set_status(TXT["status_no_folder"].format(code=k_code), "warn")
            wx.MessageBox(
                TXT["msg_no_folder_full"].format(code=k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        self._update_meta()
        self._set_status(TXT["status_found"].format(code=k_code), "ok")

        if action == "show":
            dlg = ResultsDialog(self, [entry], k_code)
            dlg.ShowModal()
            dlg.Destroy()
            return

        path_map = {
            "folder":     Path(entry.folder_path),
            "sketch":     Path(entry.sketch_path),
            "dwg":        Path(entry.dwg_path),
            "select_dwg": Path(entry.dwg_path),
        }
        path = path_map.get(action)
        if path is None:
            return

        if action == "select_dwg":
            if path.exists():
                _show_in_explorer(path)
            else:
                wx.MessageBox(TXT["msg_file_missing"].format(path=path),
                              TXT["msg_error"], wx.OK | wx.ICON_WARNING)
        elif path.exists():
            _open_path(path)
        else:
            msg = TXT["msg_file_missing"] if action == "dwg" else TXT["msg_folder_missing"]
            wx.MessageBox(msg.format(path=path), TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    # ------------------------------------------------------------------
    # Перестройка индекса
    # ------------------------------------------------------------------

    def _rebuild_async(self) -> None:
        if self._rebuild_running:
            wx.MessageBox(
                TXT["msg_rebuild_already_running"],
                TXT["msg_rebuild_confirm_title"],
                wx.OK | wx.ICON_INFORMATION
            )
            return

        if wx.MessageBox(
            TXT["msg_rebuild_confirm"],
            TXT["msg_rebuild_confirm_title"],
            wx.YES_NO | wx.ICON_QUESTION
        ) != wx.YES:
            return

        self._rebuild_running = True
        self._set_busy(True)

        def worker():
            try:
                self.after(lambda: self._set_status(TXT["status_rebuild_running"], "warn"))
                count = self.index.rebuild(
                    progress_cb=lambda m: self.after(lambda msg=m: self._set_status(msg, "warn"))
                )
                self.after(self._update_meta)
                self.after(lambda: self._set_status(
                    TXT["status_rebuild_done"].format(count=count), "ok"))
                self.after(lambda: wx.MessageBox(
                    TXT["msg_rebuild_done"].format(count=count),
                    TXT["msg_rebuild_done_title"],
                    wx.OK | wx.ICON_INFORMATION
                ))
            except (OSError, FileNotFoundError) as e:
                logger.error(f"rebuild: {e}")
                self.after(lambda: self._set_status(TXT["status_rebuild_error"], "err"))
                self.after(lambda: wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR))
            finally:
                self.after(lambda: setattr(self, "_rebuild_running", False))
                self.after(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def after(self, func) -> None:
        """Безопасный вызов из фонового потока."""
        wx.CallAfter(func)

    # ------------------------------------------------------------------
    # Служебные кнопки
    # ------------------------------------------------------------------

    def _open_index_file(self) -> None:
        p = self.cfg.index_file
        if p.exists():
            _show_in_explorer(p)
        else:
            wx.MessageBox(TXT["msg_index_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _open_index_folder(self) -> None:
        p = self.cfg.index_file.parent
        if p.exists():
            _open_path(p)
        else:
            wx.MessageBox(TXT["msg_dir_missing"].format(path=p),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _open_log_file(self) -> None:
        if _LOG_FILE.exists():
            _show_in_explorer(_LOG_FILE)
        else:
            wx.MessageBox(TXT["msg_log_missing"].format(path=_LOG_FILE),
                          TXT["msg_error"], wx.OK | wx.ICON_WARNING)

# ============================================================
# Запуск
# ============================================================

def main() -> None:
    app = wx.App(False)
    frame = KFinderFrame(CONFIG)
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
