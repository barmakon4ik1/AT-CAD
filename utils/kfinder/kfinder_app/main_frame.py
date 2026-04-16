"""
main_frame.py
=============

Главное окно приложения K-Finder.

Возвращено поведение из исходного файла:
- строка статуса снова показывает поиск / найдено / количество совпадений;
- в статусе снова показывается App.-Nr. для найденного K-кода;
- добавлен блок Indexinformationen;
- ServiceDialog снова открывает и частичную, и полную индексацию.

pyinstaller launcher.py --onefile --noconsole --icon=kfinder.ico --name=kfinder --collect-all wx
"""

from __future__ import annotations

import threading
from pathlib import Path

import wx

from .config import AppSettings
from .dialogs import AboutDialog, AppNrResultsDialog, DXFResultsDialog, ResultsDialog, ServiceDialog
from .k_repository import KIndex, SearchService
from .logging_setup import get_logger
from .repositories import AppNrRepository, DXFRepository
from .texts import TXT
from .ui_style import (
    CLR_BG,
    CLR_BTN_DANGER,
    CLR_BTN_DARK,
    CLR_BTN_OK,
    CLR_BTN_PRIMARY,
    CLR_BTN_WARN,
    CLR_INPUT_TEXT,
    CLR_PLACEHOLDER,
    CLR_STATUS_ERR,
    CLR_STATUS_OK,
    CLR_STATUS_WARN,
    CLR_LABEL,
    make_gen_button,
    open_path,
    static_box_sizer,
)

logger = get_logger()


class KFinderFrame(wx.Frame):
    """
    Главное окно K-Finder в исходной логике поведения статуса.
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.paths = settings.paths
        self.indexing = settings.indexing
        self.ui_cfg = settings.ui

        self.k_index = KIndex(settings)
        self.k_service = SearchService(settings, self.k_index)
        self.dxf_repo = DXFRepository(settings)
        self.appnr_repo = AppNrRepository(settings)

        self._busy = False
        self._main_buttons: list[wx.Window] = []

        super().__init__(
            None,
            title=TXT["app_title"],
            size=wx.Size(*self.ui_cfg.window_size),
            style=wx.CAPTION | wx.CLOSE_BOX | wx.MINIMIZE_BOX | wx.SYSTEM_MENU,
        )

        self.SetBackgroundColour(wx.Colour(CLR_BG))
        self.SetMinSize(wx.Size(*self.ui_cfg.window_size))
        self._center()
        self._build()
        self._set_search_mode(TXT["search_mode_k"], clear_entry=False)
        self._check_root()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _center(self) -> None:
        sw, sh = wx.GetDisplaySize()
        w, h = self.GetSize()
        self.SetPosition(wx.Point((sw - w) // 2, (sh - h) // 2))

    def _build(self) -> None:
        outer = wx.BoxSizer(wx.VERTICAL)
        ctrl_height = 36
        text_height = 12

        # Ввод
        input_sizer = static_box_sizer(self, TXT["input_box"])
        row = wx.BoxSizer(wx.HORIZONTAL)

        self.search_mode_value = TXT["search_mode_k"]
        self.search_mode_btn = make_gen_button(
            self, self.search_mode_value, CLR_BTN_PRIMARY,
            wx.Size(85, ctrl_height), text_height,
        )
        self.search_mode_btn.Bind(wx.EVT_BUTTON, self._on_search_mode_button)

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
            wx.FONTWEIGHT_BOLD,
        ))
        self.entry.SetForegroundColour(wx.Colour(CLR_INPUT_TEXT))
        self.entry.Bind(wx.EVT_TEXT_ENTER, lambda _: self._smart_search())
        self.entry.Bind(wx.EVT_SET_FOCUS, self._on_entry_focus)
        self.entry.Bind(wx.EVT_KILL_FOCUS, self._on_entry_kill_focus)

        self._current_hint = ""
        self._update_input_hint(force=True)

        clear_btn = make_gen_button(self, "✖", CLR_BTN_DANGER, wx.Size(36, ctrl_height), text_height)
        clear_btn.Bind(wx.EVT_BUTTON, lambda _: self._clear_search_form())

        row.Add(self.search_mode_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(self.entry, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(clear_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        input_sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Действия
        action_sizer = static_box_sizer(self, TXT["actions_box"])
        actions = [
            (TXT["search_show"], CLR_BTN_PRIMARY, "show"),
            (TXT["open_folder"], CLR_BTN_OK, "folder"),
            (TXT["open_sketch"], CLR_BTN_OK, "sketch"),
            (TXT["open_dwg"], CLR_BTN_PRIMARY, "dwg"),
            (TXT["open_dxf"], CLR_BTN_DARK, "dxf"),
        ]
        for label, color, action in actions:
            btn = make_gen_button(self, label, color, wx.Size(-1, ctrl_height), text_height)
            btn.Bind(wx.EVT_BUTTON, lambda _, a=action: self._handle_action(a))
            action_sizer.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            self._main_buttons.append(btn)
        outer.Add(action_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Метаданные индекса
        meta_sizer = static_box_sizer(self, TXT["meta_box"])
        self.meta_lbl = wx.StaticText(self, label="—")
        self.meta_lbl.SetForegroundColour(wx.Colour(CLR_LABEL))
        self.meta_lbl.SetFont(wx.Font(
            9,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
        ))
        meta_sizer.Add(self.meta_lbl, 0, wx.ALL | wx.EXPAND, 6)
        outer.Add(meta_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # Статус
        status_sizer = static_box_sizer(self, TXT["status_box"])
        self.status_lbl = wx.StaticText(self, label=TXT["status_ready_short"])
        self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_OK))
        self.status_lbl.SetFont(wx.Font(
            text_height,
            wx.FONTFAMILY_DEFAULT,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD,
        ))
        self.status_lbl.Wrap(340)
        status_sizer.Add(self.status_lbl, 0, wx.ALL | wx.EXPAND, 6)
        outer.Add(status_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Нижняя строка
        bottom_row = wx.BoxSizer(wx.HORIZONTAL)

        service_btn = make_gen_button(self, TXT["service_button"], CLR_BTN_WARN, wx.Size(-1, ctrl_height), text_height)
        service_btn.Bind(wx.EVT_BUTTON, lambda _: self._open_service_dialog())

        about_btn = make_gen_button(self, TXT["about_button"], CLR_BTN_DARK, wx.Size(-1, ctrl_height), text_height)
        about_btn.Bind(wx.EVT_BUTTON, lambda _: self._show_about())

        exit_btn = make_gen_button(self, TXT["close_program"], CLR_BTN_DANGER, wx.Size(-1, ctrl_height), text_height)
        exit_btn.Bind(wx.EVT_BUTTON, lambda _: self.Close())

        bottom_row.Add(service_btn, 1, wx.RIGHT, 6)
        bottom_row.Add(about_btn, 1, wx.RIGHT, 6)
        bottom_row.Add(exit_btn, 1)

        self._main_buttons.extend([service_btn, about_btn, exit_btn])

        outer.Add(bottom_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)
        self._refresh_meta()

    # --------------------------------------------------------
    # Placeholder / режимы
    # --------------------------------------------------------

    def _on_entry_focus(self, event: wx.FocusEvent) -> None:
        if self.entry.GetValue() == self._current_hint:
            self.entry.SetValue("")
            self.entry.SetForegroundColour(wx.Colour(CLR_INPUT_TEXT))
        event.Skip()

    def _on_entry_kill_focus(self, event: wx.FocusEvent) -> None:
        if not self.entry.GetValue().strip():
            self.entry.SetValue(self._current_hint)
            self.entry.SetForegroundColour(wx.Colour(CLR_PLACEHOLDER))
            self.entry.SetInsertionPoint(0)
        event.Skip()

    def _update_input_hint(self, force: bool = False) -> None:
        hints = {
            TXT["search_mode_k"]: TXT["input_hint_k"],
            TXT["search_mode_dxf"]: TXT["input_hint_dxf"],
            TXT["search_mode_app"]: TXT["input_hint_app"],
        }
        new_hint = hints.get(self.search_mode_value, "")
        current_value = self.entry.GetValue()

        if force:
            if not current_value or current_value == self._current_hint:
                self._current_hint = new_hint
                self.entry.SetValue(new_hint)
                self.entry.SetForegroundColour(wx.Colour(CLR_PLACEHOLDER))
                self.entry.SetInsertionPoint(0)
                return

        self._current_hint = new_hint

    def _get_search_mode_color(self, mode: str) -> str:
        if mode == TXT["search_mode_dxf"]:
            return CLR_BTN_DARK
        if mode == TXT["search_mode_app"]:
            return CLR_BTN_WARN
        return CLR_BTN_PRIMARY

    def _set_search_mode(self, mode: str, clear_entry: bool = True) -> None:
        self.search_mode_value = mode
        self.search_mode_btn.SetLabel(mode)
        self.search_mode_btn.SetBackgroundColour(wx.Colour(self._get_search_mode_color(mode)))
        self.search_mode_btn.Refresh()
        if clear_entry:
            self.entry.SetValue("")
        self._update_input_hint(force=True)
        self.entry.SetFocus()

    def _on_search_mode_button(self, event: wx.CommandEvent) -> None:
        menu = wx.Menu()
        item_k = menu.Append(wx.ID_ANY, TXT["search_mode_k"])
        item_dxf = menu.Append(wx.ID_ANY, TXT["search_mode_dxf"])
        item_app = menu.Append(wx.ID_ANY, TXT["search_mode_app"])

        self.Bind(wx.EVT_MENU, lambda _: self._set_search_mode(TXT["search_mode_k"]), item_k)
        self.Bind(wx.EVT_MENU, lambda _: self._set_search_mode(TXT["search_mode_dxf"]), item_dxf)
        self.Bind(wx.EVT_MENU, lambda _: self._set_search_mode(TXT["search_mode_app"]), item_app)

        btn = event.GetEventObject()
        if isinstance(btn, wx.Window):
            btn.PopupMenu(menu)
        menu.Destroy()

    def _clear_search_form(self) -> None:
        self._set_search_mode(TXT["search_mode_k"])

    def _refresh_button_styles(self) -> None:
        """
        Разово восстанавливает базовый цвет и белый текст кнопок
        после возврата из modal-диалогов или после Enable/Disable.
        """
        buttons = [self.search_mode_btn, *self._main_buttons]

        for btn in buttons:
            base_color = getattr(btn, "_base_color", None)
            if base_color:
                btn.SetBackgroundColour(wx.Colour(base_color))
            btn.SetForegroundColour(wx.Colour("#ffffff"))

        self.Refresh(False)

    # --------------------------------------------------------
    # Статус / мета / root
    # --------------------------------------------------------

    def _set_status(self, text: str, level: str = "ok") -> None:
        self.status_lbl.SetLabel(text)
        if level == "warn":
            self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_WARN))
        elif level == "err":
            self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_ERR))
        else:
            self.status_lbl.SetForegroundColour(wx.Colour(CLR_STATUS_OK))
        self.Layout()

    def _refresh_meta(self) -> None:
        meta = self.k_index.get_meta()
        count = meta.get("count", 0)
        gen = meta.get("generated_at", "—")
        root = meta.get("root", str(self.paths.root_dir))
        self.meta_lbl.SetLabel(
            f"Einträge: {count}\n"
            f"Aktualisiert: {gen}\n"
            f"Pfad: {root}"
        )
        self.Layout()

    def _check_root(self) -> None:
        if not self.k_index.is_root_available():
            self._set_status(TXT["status_root_warn"], "warn")
        else:
            self._set_status(TXT["status_ready"], "ok")

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.search_mode_btn.Enable(not value)
        self.entry.Enable(not value)

        for btn in self._main_buttons:
            btn.Enable(not value)

        wx.CallAfter(self._refresh_button_styles)

    def after(self, func) -> None:
        wx.CallAfter(func)

    # --------------------------------------------------------
    # Основная маршрутизация
    # --------------------------------------------------------

    def _get_effective_entry_value(self) -> str:
        value = self.entry.GetValue().strip()
        if value == self._current_hint:
            return ""
        return value

    def _smart_search(self) -> None:
        self._handle_action("show")

    def _handle_action(self, action: str) -> None:
        if self._busy:
            return

        raw = self._get_effective_entry_value()
        if not raw:
            wx.MessageBox(TXT["msg_input_required"], TXT["msg_input_error"], wx.OK | wx.ICON_INFORMATION)
            self.entry.SetFocus()
            return

        try:
            if self.search_mode_value == TXT["search_mode_k"]:
                if self.k_index.is_full_code(raw):
                    self._process_full(self.k_index.normalize_full(raw), action)
                else:
                    self._process_partial(raw)
            elif self.search_mode_value == TXT["search_mode_dxf"]:
                self._process_dxf(raw, action)
            else:
                self._process_app_nr(raw, action)
        except Exception as e:
            logger.error(f"_handle_action: {e}")
            wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR)

    # --------------------------------------------------------
    # K-логика со старым поведением статуса
    # --------------------------------------------------------

    def _get_serials_text_for_k(self, k_code: str) -> str:
        serials = self.appnr_repo.get_serials_for_k(k_code)
        if not serials:
            return ""
        return ", ".join(serials)

    def _process_full(self, k_code: str, action: str) -> None:
        self._set_status(TXT["status_searching"].format(code=k_code), "ok")
        entry = self.k_service.get_or_search(k_code)

        if not entry:
            self._set_status(TXT["status_not_found"].format(code=k_code), "warn")
            wx.MessageBox(
                TXT["msg_not_found_full"].format(code=k_code),
                TXT["msg_not_found_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        if not entry.has_folder:
            self._set_status(TXT["status_no_folder"].format(code=k_code), "warn")
            wx.MessageBox(
                TXT["msg_no_folder_full"].format(code=k_code),
                TXT["msg_no_folder_title"],
                wx.OK | wx.ICON_WARNING,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            return

        serials_text = self._get_serials_text_for_k(k_code)
        if serials_text:
            self._set_status(
                TXT["status_found_with_serial"].format(code=k_code, serials=serials_text),
                "ok",
            )
        else:
            self._set_status(TXT["status_found"].format(code=k_code), "ok")

        if action == "show":
            title = k_code
            if serials_text:
                short = serials_text if len(serials_text) <= 60 else serials_text[:57] + "..."
                title = f"{k_code} | App. Nr.: {short}"
            dlg = ResultsDialog(self, [entry], title)
            dlg.ShowModal()
            dlg.Destroy()
            return

        if action == "dxf":
            self._show_dxf_results(k_code)
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
            open_path(path)
        else:
            msg = TXT["msg_file_missing"] if action == "dwg" else TXT["msg_folder_missing"]
            wx.MessageBox(msg.format(path=path), TXT["msg_error"], wx.OK | wx.ICON_WARNING)

    def _process_partial(self, raw: str) -> None:
        results = self.k_index.find_partial(raw)

        if not results:
            self._set_status(TXT["status_no_hits"], "warn")
            wx.MessageBox(
                TXT["msg_no_hits"].format(query=raw),
                TXT["msg_no_hits_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            self._refresh_button_styles()
            return

        if len(results) == 1:
            entry = results[0]

            if not entry.has_folder:
                self._set_status(TXT["status_no_folder"].format(code=entry.k_code), "warn")
                wx.MessageBox(
                    TXT["msg_no_folder_single"].format(code=entry.k_code),
                    TXT["msg_no_folder_title"],
                    wx.OK | wx.ICON_WARNING,
                )
                self.entry.SetFocus()
                self.entry.SelectAll()
                self._refresh_button_styles()
                return

            if self.ui_cfg.auto_open_single:
                p = Path(entry.folder_path)
                if p.exists():
                    open_path(p)
                    self._set_status(TXT["status_found_one"].format(code=entry.k_code), "ok")
                    self._refresh_button_styles()
                    return

            if self.ui_cfg.auto_show_single:
                dlg = ResultsDialog(self, [entry], entry.k_code)
                dlg.ShowModal()
                dlg.Destroy()
                self._set_status(TXT["status_found_one"].format(code=entry.k_code), "ok")
                self._refresh_button_styles()
                return

        dlg = ResultsDialog(self, results, f"Treffer für '{raw}'")
        dlg.ShowModal()
        dlg.Destroy()
        self._set_status(TXT["status_found_many"].format(count=len(results)), "ok")
        self._refresh_button_styles()

    # --------------------------------------------------------
    # DXF
    # --------------------------------------------------------

    def _show_dxf_results(self, k_code: str) -> None:
        results = self.dxf_repo.search_by_k_num(k_code)

        if not results:
            wx.MessageBox(
                TXT["dxf_no_hits"].format(code=k_code),
                TXT["dxf_no_hits_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            self._refresh_button_styles()
            return

        dlg = DXFResultsDialog(self, results, f"{TXT['dxf_results_title']} — {k_code}")
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_button_styles()

    def _process_dxf(self, raw: str, action: str) -> None:
        s = raw.strip()
        if not s or not s.isdigit():
            raise ValueError(TXT["msg_dxf_input_error"])

        results = self.dxf_repo.search_by_dxf_partial(s)
        if not results:
            wx.MessageBox(
                TXT["msg_dxf_not_found"].format(query=s),
                TXT["msg_dxf_not_found_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            self._refresh_button_styles()
            return

        self._set_status(TXT["status_found_many"].format(count=len(results)), "ok")

        if action in ("show", "dxf") or len(results) != 1:
            dlg = DXFResultsDialog(self, results, f"{TXT['dxf_results_title']} — {s}")
            dlg.ShowModal()
            dlg.Destroy()
            self._refresh_button_styles()
            return

        result = results[0]
        path = Path(result.main_dwg_path)

        if action == "folder":
            folder = path.parent
            if folder.exists():
                open_path(folder)
            else:
                wx.MessageBox(TXT["dxf_folder_missing"].format(path=folder), TXT["msg_error"], wx.OK | wx.ICON_WARNING)
            self._refresh_button_styles()
            return

        if action == "dwg":
            if result.has_main_dwg and path.exists():
                open_path(path)
            else:
                wx.MessageBox(TXT["dxf_file_missing"].format(path=path), TXT["msg_error"], wx.OK | wx.ICON_WARNING)
            self._refresh_button_styles()
            return

        if action == "sketch":
            wx.MessageBox(TXT["msg_mode_not_supported"], TXT["msg_hint"], wx.OK | wx.ICON_INFORMATION)
            self._refresh_button_styles()

    # --------------------------------------------------------
    # App.Nr.
    # --------------------------------------------------------

    def _process_app_nr(self, raw: str, action: str) -> None:
        records = self.appnr_repo.search(raw)

        if not records:
            wx.MessageBox(
                TXT["msg_app_not_found"].format(query=raw),
                TXT["msg_app_not_found_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            self.entry.SetFocus()
            self.entry.SelectAll()
            self._refresh_button_styles()
            return

        self._set_status(TXT["status_found_many"].format(count=len(records)), "ok")

        if action == "show" or len(records) > 1:
            dlg = AppNrResultsDialog(self, records, f"{TXT['app_results_title']} — {raw}")
            dlg.ShowModal()
            dlg.Destroy()
            self._refresh_button_styles()
            return

        rec = records[0]
        if action == "dxf":
            self._show_dxf_results(rec.k_code)
            return

        self._process_full(rec.k_code, action)

    # --------------------------------------------------------
    # Диалоги
    # --------------------------------------------------------

    def _open_service_dialog(self) -> None:
        dlg = ServiceDialog(self, TXT["service_dialog_title"])
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_button_styles()

    def _show_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
        self._refresh_button_styles()

    # --------------------------------------------------------
    # Индексация
    # --------------------------------------------------------

    def run_partial_update(self, silent: bool = False, on_done=None) -> None:
        if self._busy:
            if not silent:
                wx.MessageBox(
                    TXT["update_already_running"],
                    TXT["update_confirm_title"],
                    wx.OK | wx.ICON_INFORMATION,
                )
            return

        self._set_busy(True)
        self._set_status(TXT["service_update_running"], "warn")

        def worker():
            try:
                self.after(lambda: self._set_status("K: Tail-Index…", "warn"))
                k_count = self.k_index.update_tail(
                    backtrack=self.indexing.k.tail_backtrack,
                    tail_years_to_scan=self.indexing.k.tail_years_to_scan,
                    progress_cb=lambda m: self.after(lambda msg=m: self._set_status(msg, "warn")),
                )

                self.after(lambda: self._set_status("DXF: Excel-Index…", "warn"))
                dxf_excel_count = self.dxf_repo.rebuild_excel_index()

                self.after(lambda: self._set_status("DXF: Datei-Index…", "warn"))
                dxf_file_count = self.dxf_repo.rebuild_files_index_full()

                self.after(lambda: self._set_status("App.Nr.: Tail-Index…", "warn"))
                appnr_count = self.appnr_repo.rebuild_tail()

                self.after(lambda: self._set_status(
                    f"K: {k_count} | DXF-Excel: {dxf_excel_count} | DXF-Dateien: {dxf_file_count} | App.Nr.: {appnr_count}",
                    "ok",
                ))
                self.after(self._refresh_meta)

                if not silent:
                    self.after(lambda: wx.MessageBox(
                        "Teilaktualisierung abgeschlossen.\n\n"
                        f"K-Index: {k_count}\n"
                        f"DXF-Excel: {dxf_excel_count}\n"
                        f"DXF-Dateien: {dxf_file_count}\n"
                        f"App.Nr. (tail): {appnr_count}",
                        TXT["update_done_title"],
                        wx.OK | wx.ICON_INFORMATION,
                    ))

                if on_done:
                    self.after(on_done)

            except Exception as e:
                logger.error(f"run_partial_update: {e}")
                self.after(lambda: self._set_status(TXT["service_update_error"], "err"))
                self.after(lambda: wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR))
            finally:
                self.after(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def run_full_rebuild(self, on_done=None) -> None:
        if self._busy:
            wx.MessageBox(
                TXT["msg_rebuild_already_running"],
                TXT["msg_rebuild_confirm_title"],
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        self._set_busy(True)
        self._set_status(TXT["service_rebuild_running"], "warn")

        def worker():
            try:
                self.after(lambda: self._set_status("K: Vollaufbau…", "warn"))
                k_count = self.k_index.rebuild(
                    progress_cb=lambda m: self.after(lambda msg=m: self._set_status(msg, "warn")),
                )

                self.after(lambda: self._set_status("DXF: Excel Vollaufbau…", "warn"))
                dxf_excel_count = self.dxf_repo.rebuild_excel_index()

                self.after(lambda: self._set_status("DXF: Datei Vollaufbau…", "warn"))
                dxf_file_count = self.dxf_repo.rebuild_files_index_full()

                self.after(lambda: self._set_status("App.Nr.: Vollaufbau…", "warn"))
                appnr_count = self.appnr_repo.rebuild_full()

                self.after(lambda: self._set_status(
                    f"K: {k_count} | DXF-Excel: {dxf_excel_count} | DXF-Dateien: {dxf_file_count} | App.Nr.: {appnr_count}",
                    "ok",
                ))
                self.after(self._refresh_meta)

                self.after(lambda: wx.MessageBox(
                    "Vollständige Neuindizierung abgeschlossen.\n\n"
                    f"K-Index: {k_count}\n"
                    f"DXF-Excel: {dxf_excel_count}\n"
                    f"DXF-Dateien: {dxf_file_count}\n"
                    f"App.Nr.: {appnr_count}",
                    TXT["msg_rebuild_done_title"],
                    wx.OK | wx.ICON_INFORMATION,
                ))

                if on_done:
                    self.after(on_done)

            except Exception as e:
                logger.error(f"run_full_rebuild: {e}")
                self.after(lambda: self._set_status(TXT["service_rebuild_error"], "err"))
                self.after(lambda: wx.MessageBox(str(e), TXT["msg_error"], wx.OK | wx.ICON_ERROR))
            finally:
                self.after(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def _on_close(self, _evt: wx.CloseEvent) -> None:
        self.Destroy()
