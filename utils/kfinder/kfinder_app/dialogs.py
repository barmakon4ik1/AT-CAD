"""
dialogs.py
==========

Диалоговые окна приложения K-Finder.

Стиль и логика:
- оформление в стиле исходного монолита;
- DXF-таблица включает колонку Ch.Nr.;
- ServiceDialog снова содержит обе кнопки:
  Teilaktualisierung и Vollständige Neuindizierung.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import wx

from .models import AppNrRecord, DXFSearchResult, KEntry
from .texts import TXT
from .ui_style import (
    CLR_BG,
    CLR_BTN_DANGER,
    CLR_BTN_DARK,
    CLR_BTN_OK,
    CLR_BTN_PRIMARY,
    CLR_BTN_WARN,
    CLR_LABEL,
    make_gen_button,
    open_path,
    static_box_sizer,
)


class ResultsDialog(wx.Dialog):
    """
    Окно результатов K-поиска.
    """

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

        tbl_sizer = static_box_sizer(self, TXT["results_box"])

        self.tree = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self.tree.SetBackgroundColour(wx.Colour("#f0f4f0"))
        self.tree.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
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

        act_sizer = static_box_sizer(self, TXT["actions_title"])
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["open_folder"], CLR_BTN_OK, self._open_folder),
            (TXT["open_sketch"], CLR_BTN_OK, self._open_sketch),
            (TXT["open_dwg"], CLR_BTN_PRIMARY, self._open_dwg),
            (TXT["close_dialog"], CLR_BTN_DANGER, self.Close),
        ]
        for label, color, handler in actions:
            btn = make_gen_button(self, label, color, wx.Size(-1, 34), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            btn_row.Add(btn, 1, wx.RIGHT, 6)

        act_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 6)

        outer.Add(tbl_sizer, 1, wx.EXPAND | wx.ALL, 10)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _selected(self) -> Optional[KEntry]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.entries):
            return None
        return self.entries[idx]

    def _require_folder(self) -> Optional[KEntry]:
        entry = self._selected()
        if not entry:
            wx.MessageBox(TXT["msg_select_entry"], TXT["msg_hint"], wx.OK | wx.ICON_INFORMATION)
            return None
        if not entry.has_folder:
            wx.MessageBox(
                TXT["msg_no_folder_single"].format(code=entry.k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING,
            )
            return None
        return entry

    def _open_folder(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.folder_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _open_sketch(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.sketch_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _open_dwg(self) -> None:
        entry = self._require_folder()
        if not entry:
            return
        p = Path(entry.dwg_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_file_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )


class DXFResultsDialog(wx.Dialog):
    """
    Окно результатов DXF-поиска.

    Важно:
    - колонка Ch.Nr. возвращена;
    - экспорт TXT/CSV тоже включает Ch.Nr.
    """

    def __init__(self, parent: wx.Window, results: list[DXFSearchResult], title: str):
        super().__init__(
            parent,
            title=title or TXT["dxf_results_title"],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1220, 560),
        )
        self.results = results
        self._build()
        self.CentreOnScreen()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        data_sizer = static_box_sizer(self, TXT["dxf_box"])

        self.tree = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self.tree.SetBackgroundColour(wx.Colour("#f0f4f0"))
        self.tree.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))

        cols = [
            (TXT["dxf_col_no"], 90),
            (TXT["dxf_col_k"], 90),
            (TXT["dxf_col_wst"], 110),
            (TXT["dxf_col_dicke"], 90),
            (TXT["dxf_col_ch_nr"], 110),
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
                res.ch_nr,
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

        act_sizer = static_box_sizer(self, TXT["dxf_actions_box"])
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["dxf_open_folder"], CLR_BTN_OK, self._open_dwg_folder),
            (TXT["dxf_open_file"], CLR_BTN_PRIMARY, self._open_dwg_file),
            (TXT["dxf_save_file"], CLR_BTN_DARK, self._save_to_file),
            (TXT["dxf_close"], CLR_BTN_DANGER, self.Close),
        ]
        for label, color, handler in actions:
            btn = make_gen_button(self, label, color, wx.Size(-1, 34), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            btn_row.Add(btn, 1, wx.RIGHT, 6)

        act_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 6)

        outer.Add(data_sizer, 1, wx.EXPAND | wx.ALL, 10)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _selected(self) -> Optional[DXFSearchResult]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.results):
            return None
        return self.results[idx]

    def _require_selected(self) -> Optional[DXFSearchResult]:
        item = self._selected()
        if not item:
            wx.MessageBox(TXT["dxf_select_entry"], TXT["msg_hint"], wx.OK | wx.ICON_INFORMATION)
        return item

    def _open_dwg_folder(self) -> None:
        item = self._require_selected()
        if not item:
            return

        path = Path(item.main_dwg_path)
        folder = path.parent
        if folder.exists():
            open_path(folder)
        else:
            wx.MessageBox(
                TXT["dxf_folder_missing"].format(path=folder),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _open_dwg_file(self) -> None:
        item = self._require_selected()
        if not item:
            return

        path = Path(item.main_dwg_path)
        if item.has_main_dwg and path.exists():
            open_path(path)
        else:
            wx.MessageBox(
                TXT["dxf_file_missing"].format(path=path),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
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

        def _fmt(v) -> str:
            return "" if v is None else str(v)

        try:
            if is_csv:
                lines = [
                    "DXF;K-Nr.;Werkstoff;Dicke,mm;Ch.Nr.;A Kn brutto,qm;Länge Zuschnitt,mm;Preis/Länge €;DWG"
                ]
                for r in self.results:
                    lines.append(
                        f"{r.dxf_no};{r.k_num};{r.wst};"
                        f"{_fmt(r.dicke_mm)};{r.ch_nr};{_fmt(r.a_kn_brutto_qm)};"
                        f"{_fmt(r.laenge_zuschnitt_mm)};{_fmt(r.preis_pro_laenge_eur)};"
                        f"{r.main_dwg_path}"
                    )
            else:
                lines = []
                sep = "-" * 60
                for r in self.results:
                    lines += [
                        f"DXF: {r.dxf_no}",
                        f"K-Nr.: {r.k_num}",
                        f"Werkstoff: {r.wst}",
                        f"Dicke, mm: {_fmt(r.dicke_mm)}",
                        f"Ch.Nr.: {r.ch_nr}",
                        f"A Kn brutto, qm: {_fmt(r.a_kn_brutto_qm)}",
                        f"Länge Zuschnitt, mm: {_fmt(r.laenge_zuschnitt_mm)}",
                        f"Preis/Länge €: {_fmt(r.preis_pro_laenge_eur)}",
                        f"DWG: {r.main_dwg_path}",
                        sep,
                    ]

            target.write_text("\n".join(lines), encoding="utf-8")
            wx.MessageBox(
                TXT["dxf_save_done"].format(path=target),
                TXT["update_done_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
        except OSError as e:
            wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR)


class AppNrResultsDialog(wx.Dialog):
    """
    Окно результатов поиска по Apparate-Nr.
    """

    def __init__(self, parent: wx.Window, records: list[AppNrRecord], title: str):
        super().__init__(
            parent,
            title=title or TXT["app_results_title"],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=wx.Size(1100, 560),
        )
        self.owner = parent
        self.records = records
        self._entries_cache: list[Optional[KEntry]] = []
        self._build()
        self.CentreOnScreen()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        tbl_sizer = static_box_sizer(self, TXT["app_box"])

        self.tree = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self.tree.SetBackgroundColour(wx.Colour("#f0f4f0"))
        self.tree.SetFont(wx.Font(
            10,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))

        cols = [
            (TXT["app_col_serial"], 180),
            (TXT["app_col_prefix"], 100),
            (TXT["app_col_k"], 120),
            (TXT["app_col_folder_exists"], 130),
            (TXT["app_col_folder"], 420),
        ]
        for idx, (hdr, width) in enumerate(cols):
            self.tree.InsertColumn(idx, hdr, width=width)

        for rec in self.records:
            entry = None
            if hasattr(self.owner, "k_service"):
                try:
                    entry = self.owner.k_service.get_or_search(rec.k_code)
                except Exception:
                    entry = None

            self._entries_cache.append(entry)

            has_folder = bool(entry and entry.has_folder)
            folder_path = entry.folder_path if has_folder else "—"

            row = [
                rec.serial_no,
                rec.serial_prefix,
                rec.k_code,
                TXT["table_has_folder_yes"] if has_folder else TXT["table_has_folder_no"],
                folder_path,
            ]
            idx = self.tree.InsertItem(self.tree.GetItemCount(), row[0])
            for col, val in enumerate(row[1:], 1):
                self.tree.SetItem(idx, col, val)

            if not has_folder:
                self.tree.SetItemBackgroundColour(idx, wx.Colour("#fff0a0"))

        self.tree.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _: self._open_folder())
        tbl_sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 6)

        act_sizer = static_box_sizer(self, TXT["app_actions_box"])
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        actions = [
            (TXT["open_folder"], CLR_BTN_OK, self._open_folder),
            (TXT["open_sketch"], CLR_BTN_OK, self._open_sketch),
            (TXT["open_dwg"], CLR_BTN_PRIMARY, self._open_dwg),
            (TXT["open_dxf"], CLR_BTN_DARK, self._show_dxf),
            (TXT["close_dialog"], CLR_BTN_DANGER, self.Close),
        ]
        for label, color, handler in actions:
            btn = make_gen_button(self, label, color, wx.Size(-1, 34), 10)
            btn.Bind(wx.EVT_BUTTON, lambda _, h=handler: h())
            btn_row.Add(btn, 1, wx.RIGHT, 6)

        act_sizer.Add(btn_row, 0, wx.EXPAND | wx.ALL, 6)

        outer.Add(tbl_sizer, 1, wx.EXPAND | wx.ALL, 10)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _selected_record(self) -> Optional[AppNrRecord]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self.records):
            return None
        return self.records[idx]

    def _selected_entry(self) -> Optional[KEntry]:
        idx = self.tree.GetFirstSelected()
        if idx == wx.NOT_FOUND or idx < 0 or idx >= len(self._entries_cache):
            return None
        return self._entries_cache[idx]

    def _require_selected_record(self) -> Optional[AppNrRecord]:
        item = self._selected_record()
        if not item:
            wx.MessageBox(TXT["app_select_entry"], TXT["msg_hint"], wx.OK | wx.ICON_INFORMATION)
        return item

    def _require_selected_entry(self) -> Optional[KEntry]:
        rec = self._require_selected_record()
        if not rec:
            return None

        entry = self._selected_entry()
        if not entry or not entry.has_folder:
            wx.MessageBox(
                TXT["msg_no_folder_single"].format(code=rec.k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING,
            )
            return None
        return entry

    def _open_folder(self) -> None:
        entry = self._require_selected_entry()
        if not entry:
            return
        p = Path(entry.folder_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _open_sketch(self) -> None:
        entry = self._require_selected_entry()
        if not entry:
            return
        p = Path(entry.sketch_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_folder_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _open_dwg(self) -> None:
        entry = self._require_selected_entry()
        if not entry:
            return
        p = Path(entry.dwg_path)
        if p.exists():
            open_path(p)
        else:
            wx.MessageBox(
                TXT["msg_file_missing"].format(path=p),
                TXT["msg_error"],
                wx.OK | wx.ICON_WARNING,
            )

    def _show_dxf(self) -> None:
        rec = self._require_selected_record()
        if not rec:
            return
        if hasattr(self.owner, "_show_dxf_results"):
            self.owner._show_dxf_results(rec.k_code)


class ServiceDialog(wx.Dialog):
    """
    Служебное окно.

    Возвращены обе кнопки:
    - Teilaktualisierung
    - Vollständige Neuindizierung
    """

    def __init__(self, parent: "wx.Window", title: str):
        super().__init__(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE,
            size=wx.Size(500, 360),
        )
        self.owner = parent
        self._build()
        self._refresh_info()
        self.CentreOnParent()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        info_sizer = static_box_sizer(self, TXT["service_info_box"])
        self.info_lbl = wx.StaticText(self, label="—")
        self.info_lbl.SetForegroundColour(wx.Colour(CLR_LABEL))
        self.info_lbl.SetFont(wx.Font(
            9,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))
        info_sizer.Add(self.info_lbl, 0, wx.ALL | wx.EXPAND, 6)
        outer.Add(info_sizer, 0, wx.EXPAND | wx.ALL, 10)

        act_sizer = static_box_sizer(self, TXT["service_actions_box"])
        btn_col = wx.BoxSizer(wx.VERTICAL)

        self.btn_partial = make_gen_button(
            self, TXT["service_update_partial"], CLR_BTN_WARN, wx.Size(-1, 34), 10
        )
        self.btn_partial.Bind(wx.EVT_BUTTON, lambda _: self._run_partial())

        self.btn_full = make_gen_button(
            self, TXT["service_update_full"], CLR_BTN_DANGER, wx.Size(-1, 34), 10
        )
        self.btn_full.Bind(wx.EVT_BUTTON, lambda _: self._run_full())

        btn_close = make_gen_button(
            self, TXT["service_close"], CLR_BTN_DARK, wx.Size(-1, 34), 10
        )
        btn_close.Bind(wx.EVT_BUTTON, lambda _: self.Close())

        btn_col.Add(self.btn_partial, 0, wx.EXPAND | wx.BOTTOM, 6)
        btn_col.Add(self.btn_full, 0, wx.EXPAND | wx.BOTTOM, 6)
        btn_col.Add(btn_close, 0, wx.EXPAND)

        act_sizer.Add(btn_col, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(act_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)

    def _refresh_info(self) -> None:
        meta = self.owner.k_index.get_meta()
        count = meta.get("count", 0)
        gen = meta.get("generated_at", "—")
        root = meta.get("root", str(self.owner.paths.root_dir))

        self.info_lbl.SetLabel(
            f"Einträge: {count}\n"
            f"Aktualisiert: {gen}\n"
            f"Pfad: {root}\n"
            f"Rückschritt: {self.owner.indexing.k.tail_backtrack}\n"
            f"Geprüfte Jahre: {self.owner.indexing.k.tail_years_to_scan}"
        )

    def _run_partial(self) -> None:
        if wx.MessageBox(
            TXT["service_partial_confirm"],
            TXT["update_confirm_title"],
            wx.YES_NO | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        self.owner.run_partial_update(silent=False, on_done=self._refresh_info)

    def _run_full(self) -> None:
        if wx.MessageBox(
            TXT["service_full_confirm"],
            TXT["msg_rebuild_confirm_title"],
            wx.YES_NO | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        self.owner.run_full_rebuild(on_done=self._refresh_info)


class AboutDialog(wx.Dialog):
    """
    Окно «О программе».
    """

    def __init__(self, parent: wx.Window):
        super().__init__(
            parent,
            title=TXT["about_title"],
            style=wx.DEFAULT_DIALOG_STYLE,
            size=wx.Size(430, 410),
        )
        self._build()
        self.CentreOnParent()

    def _build(self) -> None:
        self.SetBackgroundColour(wx.Colour(CLR_BG))
        outer = wx.BoxSizer(wx.VERTICAL)

        header = wx.Panel(self)
        header.SetBackgroundColour(wx.Colour("#2c5f2e"))
        header_sz = wx.BoxSizer(wx.VERTICAL)

        title_lbl = wx.StaticText(header, label=TXT["about_text_title"])
        title_lbl.SetForegroundColour(wx.Colour("#ffffff"))
        title_lbl.SetFont(wx.Font(
            14,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD,
        ))

        subtitle_lbl = wx.StaticText(header, label=TXT["about_text_subtitle"])
        subtitle_lbl.SetForegroundColour(wx.Colour("#d9f2da"))
        subtitle_lbl.SetFont(wx.Font(
            12,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_ITALIC,
            wx.FONTWEIGHT_NORMAL,
        ))

        header_sz.Add(title_lbl, 0, wx.ALIGN_CENTER | wx.TOP, 12)
        header_sz.Add(subtitle_lbl, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        header.SetSizer(header_sz)
        outer.Add(header, 0, wx.EXPAND)

        body = wx.Panel(self)
        body.SetBackgroundColour(wx.Colour(CLR_BG))
        body_sz = wx.BoxSizer(wx.VERTICAL)

        body_lbl = wx.StaticText(body, label=TXT["about_text_body"])
        body_lbl.SetForegroundColour(wx.Colour(CLR_LABEL))
        body_lbl.SetFont(wx.Font(
            12,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))

        footer_lbl = wx.StaticText(body, label=TXT["about_text_footer"])
        footer_lbl.SetForegroundColour(wx.Colour("#ffffff"))
        footer_lbl.SetFont(wx.Font(
            12,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD,
        ))

        body_sz.Add(body_lbl, 0, wx.EXPAND | wx.ALL, 16)
        body_sz.Add(footer_lbl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        body.SetSizer(body_sz)
        outer.Add(body, 1, wx.EXPAND)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = make_gen_button(self, TXT["about_ok"], CLR_BTN_PRIMARY, wx.Size(100, 32), 10)
        ok_btn.Bind(wx.EVT_BUTTON, lambda _: self.EndModal(wx.ID_OK))
        btn_row.AddStretchSpacer(1)
        btn_row.Add(ok_btn, 0)

        outer.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.SetSizer(outer)
