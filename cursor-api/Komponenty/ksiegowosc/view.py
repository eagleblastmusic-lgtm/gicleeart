"""Widok inline — Księgowość (Działalność nierejestrowana, JDG)."""



from __future__ import annotations



import tkinter as tk

from collections.abc import Callable

from pathlib import Path



from Komponenty._shared.tile_grid import InlineTileView, TileSpec

from Komponenty._shared.toast import show_toast



_COMPONENT_DIR = Path(__file__).resolve().parent





def _open_kpir(parent: tk.Misc, _spec: TileSpec) -> None:

    from Komponenty.kpir.view import build_view



    top = parent.winfo_toplevel()

    win = tk.Toplevel(top)

    win.title("KPiR — JDG")

    win.geometry("1000x700")

    build_view(win, on_back=win.destroy).pack(fill="both", expand=True)





def _in_progress(label: str) -> Callable[[tk.Misc, TileSpec], None]:

    def _open(parent: tk.Misc, _spec: TileSpec) -> None:

        show_toast(parent, f"{label}: w budowie", duration_ms=1800, bg="#444", fg="white")



    return _open





def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:

    tiles = [

        TileSpec(

            key="dnr",

            label="Działalność nierejestrowana",

            icon="📋",

            color="#5c6bc0",

            target_kind="callable",

            callback=_in_progress("Działalność nierejestrowana"),

            description="Ewidencja sprzedaży i kosztów (limit DNR).",

        ),

        TileSpec(

            key="jdg",

            label="JDG — KPiR",

            icon="📒",

            color="#2e7d32",

            target_kind="callable",

            callback=_open_kpir,

            description="Księga Przychodów i Rozchodów — pełny moduł.",

        ),

    ]

    view = InlineTileView(

        title="Księgowość",

        subtitle="Wybierz formę rozliczeń",

        tiles=tiles,

        component_dir=_COMPONENT_DIR,

        on_back=on_back,

    )

    return view.mount(parent)

