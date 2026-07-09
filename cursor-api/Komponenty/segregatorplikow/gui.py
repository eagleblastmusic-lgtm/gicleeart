"""GUI: Segregator plikow — kafelki folderow docelowych + drag and drop."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from tkinterdnd2 import TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.activity_log_ui import open_activity_log_dialog
from Komponenty._shared.tkdnd_safe import dnd_files_available, parse_dnd_files, register_drop_target
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .dialogs import open_preview_dialog, open_tile_edit_dialog
from .move_service import (
    COMPONENT_NAME,
    MovePlan,
    MoveResult,
    execute_moves,
    filter_file_paths,
    has_name_conflicts,
    plan_moves,
)
from .storage import TileEntry, TileStore, load_tiles, new_tile_id, save_tiles

APP_TITLE = "Segregator plikow"


def _create_root() -> tk.Tk:
    if _HAS_DND:
        return TkinterDnD.Tk()
    return tk.Tk()


class SegregatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(root, 1120, 740)
        self.root.minsize(900, 600)

        self._store = load_tiles()
        self._pending_files: list[Path] = []
        self._session_log: list[str] = []
        self._tile_frames: dict[str, tk.Frame] = {}

        self._build_ui()
        self._refresh_tiles()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(10, 8))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Dodaj kafelek", command=self._add_parent_tile).pack(side="left")
        ttk.Button(toolbar, text="Wybierz pliki...", command=self._browse_files).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(toolbar, text="Wyczysc oczekujace", command=self._clear_pending).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(toolbar, text="Dziennik akcji", command=self._open_global_log).pack(
            side="right"
        )

        dnd_ok = dnd_files_available() and _HAS_DND
        hint = (
            "Przeciagnij pliki na kafelek lub uzyj «Wybierz pliki» i kliknij kafelek docelowy."
            if dnd_ok
            else "DnD niedostepne — uzyj «Wybierz pliki» i kliknij kafelek docelowy. (pip install tkinterdnd2)"
        )
        self._hint_var = tk.StringVar(value=hint)
        ttk.Label(self.root, textvariable=self._hint_var, foreground="#555", padding=(12, 0)).pack(
            anchor="w"
        )

        self._pending_var = tk.StringVar(value="Oczekujace pliki: 0")
        ttk.Label(self.root, textvariable=self._pending_var, padding=(12, 4)).pack(anchor="w")

        paned = ttk.Panedwindow(self.root, orient="vertical")
        paned.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        tiles_outer = ttk.Frame(paned)
        paned.add(tiles_outer, weight=3)

        self._canvas = tk.Canvas(tiles_outer, highlightthickness=0)
        self._tiles_inner = ttk.Frame(self._canvas)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._tiles_inner, anchor="nw")
        vscroll = ttk.Scrollbar(tiles_outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vscroll.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        def _on_inner_configure(_e: object) -> None:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        def _on_canvas_configure(e: tk.Event) -> None:  # type: ignore[type-arg]
            self._canvas.itemconfigure(self._canvas_window, width=e.width)

        self._tiles_inner.bind("<Configure>", _on_inner_configure)
        self._canvas.bind("<Configure>", _on_canvas_configure)
        bind_mousewheel_to_canvas(self._canvas, self._tiles_inner)

        log_outer = ttk.LabelFrame(paned, text="Ostatnie operacje (sesja)", padding=6)
        paned.add(log_outer, weight=1)
        self._log_text = scrolledtext.ScrolledText(
            log_outer, height=8, font=("Consolas", 9), state="disabled"
        )
        self._log_text.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Gotowy")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", padx=10, pady=(0, 8)
        )

    def _open_global_log(self) -> None:
        open_activity_log_dialog(self.root)

    def _append_session_log(self, line: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"{ts}  {line}"
        self._session_log.append(entry)
        if len(self._session_log) > 100:
            self._session_log = self._session_log[-100:]
        self._log_text.configure(state="normal")
        self._log_text.insert("end", entry + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _refresh_tiles(self) -> None:
        for child in self._tiles_inner.winfo_children():
            child.destroy()
        self._tile_frames.clear()

        if not self._store.tiles:
            ttk.Label(
                self._tiles_inner,
                text="Brak kafelkow. Kliknij «Dodaj kafelek» aby zaczac.",
                foreground="#666",
                padding=20,
            ).pack(anchor="w")
            return

        for tile in self._store.tiles:
            self._render_parent_tile(tile)

    def _render_parent_tile(self, tile: TileEntry) -> None:
        outer = ttk.Frame(self._tiles_inner, padding=(0, 8))
        outer.pack(fill="x", anchor="nw")

        card = tk.Frame(outer, bg="#eceff1", highlightbackground="#b0bec5", highlightthickness=1)
        card.pack(fill="x", padx=4, pady=2)
        self._tile_frames[tile.id] = card

        inner = tk.Frame(card, bg="#eceff1", padx=14, pady=12)
        inner.pack(fill="x")

        title = tk.Label(
            inner,
            text=tile.name,
            font=("Segoe UI", 13, "bold"),
            bg="#eceff1",
            fg="#263238",
            anchor="w",
        )
        title.pack(fill="x")
        path_lbl = tk.Label(
            inner,
            text=self._short_path(tile.path),
            font=("Segoe UI", 9),
            bg="#eceff1",
            fg="#546e7a",
            anchor="w",
        )
        path_lbl.pack(fill="x", pady=(2, 8))

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(btn_row, text="Edytuj", command=lambda t=tile: self._edit_tile(t, False)).pack(
            side="left"
        )
        ttk.Button(btn_row, text="Usun", command=lambda t=tile: self._delete_tile(t.id)).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(
            btn_row, text="Dodaj podkafelek", command=lambda t=tile: self._add_child_tile(t)
        ).pack(side="left", padx=(6, 0))

        if tile.children:
            children_row = ttk.Frame(outer, padding=(20, 0, 0, 0))
            children_row.pack(fill="x")
            for child in tile.children:
                self._render_child_tile(children_row, child, tile)

        self._bind_tile_drop(card, tile)
        for w in (inner, title, path_lbl):
            self._bind_tile_drop(w, tile)

    def _render_child_tile(self, parent: ttk.Frame, child: TileEntry, parent_tile: TileEntry) -> None:
        frame = tk.Frame(parent, bg="#e3f2fd", highlightbackground="#90caf9", highlightthickness=1)
        frame.pack(side="left", padx=6, pady=6, ipadx=4, ipady=4)
        self._tile_frames[child.id] = frame

        inner = tk.Frame(frame, bg="#e3f2fd", padx=10, pady=8)
        inner.pack()

        tk.Label(
            inner, text=child.name, font=("Segoe UI", 11, "bold"), bg="#e3f2fd", fg="#1565c0"
        ).pack(anchor="w")
        tk.Label(
            inner,
            text=self._short_path(child.path),
            font=("Segoe UI", 8),
            bg="#e3f2fd",
            fg="#546e7a",
        ).pack(anchor="w")

        btns = ttk.Frame(frame)
        btns.pack(padx=6, pady=(0, 6))
        ttk.Button(btns, text="Ed.", command=lambda c=child: self._edit_tile(c, True)).pack(
            side="left"
        )
        ttk.Button(
            btns, text="X", width=3, command=lambda c=child, p=parent_tile: self._delete_child(p, c.id)
        ).pack(side="left", padx=(4, 0))

        self._bind_tile_drop(frame, child)
        for w in inner.winfo_children():
            self._bind_tile_drop(w, child)

    @staticmethod
    def _short_path(path: str, max_len: int = 72) -> str:
        text = path or "(brak sciezki)"
        if len(text) <= max_len:
            return text
        return "..." + text[-(max_len - 3) :]

    def _bind_tile_drop(self, widget: tk.Misc, tile: TileEntry) -> None:
        def _on_drop(event: object, t: TileEntry = tile) -> None:
            data = getattr(event, "data", "") or ""
            paths = parse_dnd_files(data)
            self._handle_incoming_paths(paths, t)

        def _on_enter(_e: object, w: tk.Misc = widget) -> None:
            try:
                w.configure(bg="#c8e6c9")
            except tk.TclError:
                pass

        def _on_leave(_e: object, w: tk.Misc = widget, orig: str = "#eceff1") -> None:
            try:
                w.configure(bg=orig)
            except tk.TclError:
                pass

        register_drop_target(
            widget,
            on_drop=_on_drop,
            on_drag_enter=_on_enter,
            on_drag_leave=_on_leave,
        )
        widget.bind("<Button-1>", lambda _e, t=tile: self._on_tile_click(t), add="+")

    def _on_tile_click(self, tile: TileEntry) -> None:
        if self._pending_files:
            self._start_move_flow(list(self._pending_files), tile)

    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz pliki do segregacji",
            filetypes=[("Wszystkie pliki", "*.*")],
        )
        if paths:
            self._stage_files([Path(p) for p in paths])

    def _stage_files(self, paths: list[Path]) -> None:
        files, dirs = filter_file_paths(paths)
        if dirs:
            show_toast(self.root, f"Pominieto {len(dirs)} folder(ow) — MVP obsluguje tylko pliki")
            self._append_session_log(f"Pominieto foldery: {len(dirs)}")
        if not files:
            if dirs:
                messagebox.showinfo(APP_TITLE, "Foldery nie sa obslugiwane w MVP. Wybierz pliki.")
            return
        existing = {p.resolve() for p in self._pending_files}
        added = 0
        for f in files:
            try:
                key = f.resolve()
            except OSError:
                key = f
            if key not in existing:
                self._pending_files.append(f)
                existing.add(key)
                added += 1
        self._pending_var.set(f"Oczekujace pliki: {len(self._pending_files)}")
        if added:
            show_toast(self.root, f"Dodano {added} plik(ow) — kliknij kafelek docelowy")
            self.status_var.set(f"Oczekuje na wybor kafelka ({len(self._pending_files)} plikow)")

    def _clear_pending(self) -> None:
        self._pending_files.clear()
        self._pending_var.set("Oczekujace pliki: 0")
        self.status_var.set("Gotowy")

    def _handle_incoming_paths(self, paths: list[Path], tile: TileEntry) -> None:
        """Drop lub bezposrednie pliki — preview tylko przy konflikcie nazw."""
        if not paths:
            return
        files, dirs = filter_file_paths(paths)
        if dirs:
            show_toast(self.root, f"Pominieto {len(dirs)} folder(ow)")
        if not files:
            if dirs:
                messagebox.showinfo(APP_TITLE, "Foldery nie sa obslugiwane w MVP.")
            return
        self._start_move_flow(files, tile)

    def _start_move_flow(self, sources: list[Path], tile: TileEntry) -> None:
        """Bez konfliktu nazw: od razu przenies + toast. Przy duplikacie: dialog podgladu."""
        dest = Path(tile.path)
        if not dest.is_dir():
            messagebox.showerror(
                APP_TITLE,
                f"Folder docelowy nie istnieje:\n{dest}",
            )
            return

        if has_name_conflicts(sources, dest):
            open_preview_dialog(
                self.root,
                sources=sources,
                dest_dir=dest,
                tile_name=tile.name,
                on_confirm=lambda plan: self._execute_confirmed_plan(plan, tile),
            )
        else:
            plan = plan_moves(sources, dest, tile_name=tile.name)
            self._execute_confirmed_plan(plan, tile)

        self._pending_files.clear()
        self._pending_var.set("Oczekujace pliki: 0")

    def _execute_confirmed_plan(self, plan: MovePlan, tile: TileEntry) -> None:
        """Wywolywane WYLACZNIE po kliknieciu Przenies w dialogu podgladu."""
        self.status_var.set("Przenoszenie...")
        self.root.update_idletasks()

        def _work() -> None:
            results = execute_moves(plan)

            def _done() -> None:
                self._on_move_finished(results, tile)

            self.root.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def _on_move_finished(self, results: list[MoveResult], tile: TileEntry) -> None:
        ok = sum(1 for r in results if r.success)
        fail = sum(1 for r in results if not r.success)
        for r in results:
            if r.success:
                self._append_session_log(f"OK  {r.src.name} -> {r.dest}")
            else:
                self._append_session_log(f"ERR {r.src.name}: {r.message}")

        if ok:
            show_toast(self.root, f"Przeniesiono {ok} plik(ow)")
            append_activity(
                COMPONENT_NAME,
                f"Przeniesiono {ok} plik(ow) -> {tile.name}",
                detail=str(tile.path),
            )
        if fail:
            show_toast(self.root, f"Bledy: {fail}", duration_ms=2200)
            append_activity(
                COMPONENT_NAME,
                f"Bledy przenoszenia: {fail}",
                level="error",
                detail=str(tile.path),
            )
        self.status_var.set(f"Gotowy — przeniesiono {ok}, bledow {fail}")

    def _add_parent_tile(self) -> None:
        entry = open_tile_edit_dialog(self.root, title="Nowy kafelek", tile=None, is_child=False)
        if not entry:
            return
        entry.id = new_tile_id()
        self._store.tiles.append(entry)
        save_tiles(self._store)
        self._refresh_tiles()
        show_toast(self.root, "Kafelek dodany")

    def _add_child_tile(self, parent: TileEntry) -> None:
        entry = open_tile_edit_dialog(
            self.root, title=f"Podkafelek — {parent.name}", tile=None, is_child=True
        )
        if not entry:
            return
        entry.id = new_tile_id()
        parent.children.append(entry)
        save_tiles(self._store)
        self._refresh_tiles()
        show_toast(self.root, "Podkafelek dodany")

    def _edit_tile(self, tile: TileEntry, is_child: bool) -> None:
        updated = open_tile_edit_dialog(
            self.root,
            title="Edytuj kafelek",
            tile=tile,
            is_child=is_child,
        )
        if not updated:
            return
        tile.name = updated.name
        tile.path = updated.path
        save_tiles(self._store)
        self._refresh_tiles()
        show_toast(self.root, "Zapisano")

    def _delete_tile(self, tile_id: str) -> None:
        tile = self._store.find(tile_id)
        if not tile:
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac kafelek «{tile.name}» wraz z podkafelkami?",
            parent=self.root,
        ):
            return
        self._store.tiles = [t for t in self._store.tiles if t.id != tile_id]
        save_tiles(self._store)
        self._refresh_tiles()
        show_toast(self.root, "Kafelek usuniety")

    def _delete_child(self, parent: TileEntry, child_id: str) -> None:
        child = next((c for c in parent.children if c.id == child_id), None)
        if not child:
            return
        if not messagebox.askyesno(APP_TITLE, f"Usunac podkafelek «{child.name}»?", parent=self.root):
            return
        parent.children = [c for c in parent.children if c.id != child_id]
        save_tiles(self._store)
        self._refresh_tiles()
        show_toast(self.root, "Podkafelek usuniety")


def main() -> None:
    root = _create_root()
    SegregatorApp(root)
    root.mainloop()
