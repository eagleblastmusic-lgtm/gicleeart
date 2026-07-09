"""Dialogi: edycja kafelka, podglad operacji przed przeniesieniem."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .move_service import DuplicatePolicy, MovePlan, MovePlanItem, PlanStatus, plan_moves
from .storage import TileEntry, normalize_path


def open_tile_edit_dialog(
    parent: tk.Misc,
    *,
    title: str,
    tile: TileEntry | None = None,
    is_child: bool = False,
) -> TileEntry | None:
    """Zwraca TileEntry z danymi lub None przy anulowaniu."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    position_toplevel_screen_center(dlg, 560, 220)
    dlg.transient(parent.winfo_toplevel())
    dlg.grab_set()

    name_var = tk.StringVar(value=tile.name if tile else "")
    path_var = tk.StringVar(value=tile.path if tile else "")

    body = ttk.Frame(dlg, padding=14)
    body.pack(fill="both", expand=True)
    body.columnconfigure(1, weight=1)

    ttk.Label(body, text="Nazwa:").grid(row=0, column=0, sticky="w", pady=4)
    name_entry = ttk.Entry(body, textvariable=name_var, width=48)
    name_entry.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))

    ttk.Label(body, text="Sciezka:").grid(row=1, column=0, sticky="w", pady=4)
    path_entry = ttk.Entry(body, textvariable=path_var, width=48)
    path_entry.grid(row=1, column=1, sticky="ew", pady=4, padx=(8, 0))

    def _pick_folder() -> None:
        initial = path_var.get() or os.getcwd()
        chosen = filedialog.askdirectory(initialdir=initial, parent=dlg)
        if chosen:
            path_var.set(chosen)

    ttk.Button(body, text="Wybierz folder...", command=_pick_folder).grid(
        row=2, column=1, sticky="w", pady=(4, 0), padx=(8, 0)
    )

    if is_child:
        ttk.Label(
            body,
            text="Podkafelek (1 poziom pod kafelkiem glownym).",
            foreground="#666",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    result: list[TileEntry | None] = [None]

    def _save() -> None:
        name = name_var.get().strip()
        path = normalize_path(path_var.get())
        if not name:
            messagebox.showerror(title, "Podaj nazwe kafelka.", parent=dlg)
            return
        if not path:
            messagebox.showerror(title, "Podaj sciezke folderu docelowego.", parent=dlg)
            return
        if not Path(path).is_dir():
            if not messagebox.askyesno(
                title,
                "Folder docelowy nie istnieje.\nZapisac kafelek mimo to?\n"
                "(Przenoszenie bedzie zablokowane do utworzenia folderu.)",
                parent=dlg,
            ):
                return
        entry = TileEntry(
            id=tile.id if tile else "",
            name=name,
            path=path,
            children=tile.children if tile else [],
        )
        result[0] = entry
        dlg.destroy()

    def _cancel() -> None:
        dlg.destroy()

    bar = ttk.Frame(dlg, padding=(14, 0, 14, 12))
    bar.pack(fill="x")
    ttk.Button(bar, text="Zapisz", command=_save).pack(side="right")
    ttk.Button(bar, text="Anuluj", command=_cancel).pack(side="right", padx=(0, 8))

    name_entry.focus_set()
    dlg.wait_window()
    return result[0]


class PreviewDialog:
    """Dialog podgladu operacji — jedyny punkt wejscia do execute_moves."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        sources: list[Path],
        dest_dir: Path,
        tile_name: str,
        on_confirm: Callable[[MovePlan], None],
    ) -> None:
        self._parent = parent
        self._sources = sources
        self._dest_dir = dest_dir
        self._tile_name = tile_name
        self._on_confirm = on_confirm
        self._policy = tk.StringVar(value=DuplicatePolicy.RENAME.value)
        self._per_file_replace: dict[Path, bool] = {}
        self._plan: MovePlan | None = None
        self._dlg: tk.Toplevel | None = None
        self._tree: ttk.Treeview | None = None

    def show(self) -> None:
        dlg = tk.Toplevel(self._parent)
        self._dlg = dlg
        dlg.title("Podglad operacji przenoszenia")
        position_toplevel_screen_center(dlg, 820, 520)
        dlg.transient(self._parent.winfo_toplevel())
        dlg.grab_set()

        header = ttk.Frame(dlg, padding=(14, 12, 14, 4))
        header.pack(fill="x")
        ttk.Label(
            header,
            text=f"Cel: {self._tile_name}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=str(self._dest_dir),
            foreground="#444",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"Plikow do przetworzenia: {len(self._sources)}",
            foreground="#666",
        ).pack(anchor="w", pady=(4, 0))

        policy_frame = ttk.LabelFrame(dlg, text="Duplikaty (plik docelowy juz istnieje)", padding=10)
        policy_frame.pack(fill="x", padx=14, pady=8)

        ttk.Radiobutton(
            policy_frame,
            text="Zmien nazwe automatycznie (domyslnie)",
            variable=self._policy,
            value=DuplicatePolicy.RENAME.value,
            command=self._rebuild_plan,
        ).pack(anchor="w")
        ttk.Radiobutton(
            policy_frame,
            text="Pomin plik",
            variable=self._policy,
            value=DuplicatePolicy.SKIP.value,
            command=self._rebuild_plan,
        ).pack(anchor="w")
        ttk.Radiobutton(
            policy_frame,
            text="Anuluj cala operacje",
            variable=self._policy,
            value=DuplicatePolicy.CANCEL.value,
            command=self._rebuild_plan,
        ).pack(anchor="w")

        replace_row = ttk.Frame(policy_frame)
        replace_row.pack(anchor="w", pady=(6, 0))
        ttk.Label(
            replace_row,
            text="Zastap istniejacy plik — w kolejnej wersji (MVP: wylaczone)",
            foreground="#999",
        ).pack(side="left")

        tree_frame = ttk.Frame(dlg, padding=(14, 4))
        tree_frame.pack(fill="both", expand=True)
        cols = ("src", "dest", "status")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        self._tree = tree
        tree.heading("src", text="Zrodlo")
        tree.heading("dest", text="Cel")
        tree.heading("status", text="Status")
        tree.column("src", width=280)
        tree.column("dest", width=280)
        tree.column("status", width=180)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._summary_var = tk.StringVar()
        ttk.Label(dlg, textvariable=self._summary_var, padding=(14, 4)).pack(anchor="w")

        bar = ttk.Frame(dlg, padding=(14, 8, 14, 12))
        bar.pack(fill="x")
        self._move_btn = ttk.Button(bar, text="Przenies", command=self._confirm)
        self._move_btn.pack(side="right")
        ttk.Button(bar, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 8))

        self._rebuild_plan()

    def _current_policy(self) -> DuplicatePolicy:
        try:
            return DuplicatePolicy(self._policy.get())
        except ValueError:
            return DuplicatePolicy.RENAME

    def _rebuild_plan(self) -> None:
        policy = self._current_policy()
        self._plan = plan_moves(
            self._sources,
            self._dest_dir,
            tile_name=self._tile_name,
            duplicate_policy=policy,
            per_file_replace=self._per_file_replace,
        )
        self._refresh_tree()

    def _status_label(self, item: MovePlanItem) -> str:
        if item.status == PlanStatus.OK:
            if item.resolved_dest and item.resolved_dest != item.dest:
                return "OK (zmiana nazwy)"
            return "OK"
        if item.status == PlanStatus.DUPLICATE and item.allow_replace:
            return "Zastapi (po potwierdzeniu)"
        mapping = {
            PlanStatus.DUPLICATE: "Duplikat",
            PlanStatus.MISSING_SRC: "Brak pliku zrodlowego",
            PlanStatus.MISSING_DEST_DIR: "Brak folderu docelowego",
            PlanStatus.SKIP: "Pominiety",
            PlanStatus.CANCELLED: "Anulowano",
            PlanStatus.ERROR: "Blad",
        }
        base = mapping.get(item.status, item.status.value)
        if item.error:
            return f"{base}: {item.error}"
        return base

    def _refresh_tree(self) -> None:
        if self._tree is None or self._plan is None:
            return
        self._tree.delete(*self._tree.get_children())
        for item in self._plan.items:
            dest = item.effective_dest or item.dest
            self._tree.insert(
                "",
                "end",
                values=(str(item.src), str(dest), self._status_label(item)),
            )
        if self._plan.cancelled:
            self._summary_var.set("Operacja zostanie anulowana — nic nie zostanie przeniesione.")
            self._move_btn.configure(state="disabled")
        else:
            n = self._plan.movable_count
            blocked = self._plan.blocked_count
            self._summary_var.set(
                f"Do przeniesienia: {n}  |  Zablokowane/pominiete: {blocked}"
            )
            self._move_btn.configure(
                state="normal" if n > 0 else "disabled",
                text=f"Przenies ({n})" if n else "Przenies",
            )

    def _confirm(self) -> None:
        if self._plan is None or self._dlg is None:
            return
        policy = self._current_policy()
        if policy == DuplicatePolicy.CANCEL or self._plan.cancelled:
            self._dlg.destroy()
            return
        n = self._plan.movable_count
        if n == 0:
            messagebox.showwarning(
                "Podglad",
                "Brak plikow do przeniesienia.",
                parent=self._dlg,
            )
            return
        if not messagebox.askyesno(
            "Potwierdzenie",
            f"Przeniesc {n} plik(ow) do:\n{self._dest_dir}\n\nTej operacji nie mozna cofnac latwo.",
            parent=self._dlg,
        ):
            return
        plan = self._plan
        self._dlg.destroy()
        self._on_confirm(plan)


def open_preview_dialog(
    parent: tk.Misc,
    *,
    sources: list[Path],
    dest_dir: Path,
    tile_name: str,
    on_confirm: Callable[[MovePlan], None],
) -> None:
    """Pokazuje podglad — execute_moves wywolywane tylko w on_confirm po kliknieciu Przenies."""
    PreviewDialog(
        parent,
        sources=sources,
        dest_dir=dest_dir,
        tile_name=tile_name,
        on_confirm=on_confirm,
    ).show()
