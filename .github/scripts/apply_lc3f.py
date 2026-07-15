from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one LC-3F match in {path}, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    dnd_path = ROOT / "cursor-api/giclee_app/dragdrop_category_launcher.py"
    launcher_docs = ROOT / "cursor-api/giclee_app/docs/launcher.md"
    contract = ROOT / "cursor-api/giclee_app/docs/launcher-composition-lc3f-contract.md"

    replace_once(
        dnd_path,
        "from .launcher_layout import resolve_sections, save_layout\n",
        "from .launcher_layout import resolve_sections, save_layout\n"
        "from .launcher_tk_drag_bindings import install_tile_drag_bindings\n",
    )

    replace_once(
        dnd_path,
        '''        setattr(tile, "_launcher_dnd_kind", kind)\n'''
        '''        setattr(tile, "_launcher_dnd_key", key)\n'''
        '''        self._dnd_tiles.append(tile)\n'''
        '''\n'''
        '''        def bind_recursive(widget: tk.Widget) -> None:\n'''
        '''            # Bazowe kafelki uruchamiały akcję już na Button-1. Przy DnD klik\n'''
        '''            # wykonujemy dopiero na zwolnieniu przycisku, o ile nie rozpoczęto drag.\n'''
        '''            try:\n'''
        '''                widget.unbind("<Button-1>")\n'''
        '''            except tk.TclError:\n'''
        '''                pass\n'''
        '''            widget.bind(\n'''
        '''                "<ButtonPress-1>",\n'''
        '''                lambda event: self._on_tile_press(event, tile, kind, key, activate),\n'''
        '''                add="+",\n'''
        '''            )\n'''
        '''            widget.bind("<B1-Motion>", self._on_tile_motion, add="+")\n'''
        '''            widget.bind("<ButtonRelease-1>", self._on_tile_release, add="+")\n'''
        '''            try:\n'''
        '''                widget.configure(cursor="hand2")\n'''
        '''            except tk.TclError:\n'''
        '''                pass\n'''
        '''            for child in widget.winfo_children():\n'''
        '''                bind_recursive(child)\n'''
        '''\n'''
        '''        bind_recursive(tile)\n''',
        '''        setattr(tile, "_launcher_dnd_kind", kind)\n'''
        '''        setattr(tile, "_launcher_dnd_key", key)\n'''
        '''        self._dnd_tiles.append(tile)\n'''
        '''        install_tile_drag_bindings(\n'''
        '''            tile,\n'''
        '''            on_press=lambda event: self._on_tile_press(\n'''
        '''                event, tile, kind, key, activate\n'''
        '''            ),\n'''
        '''            on_motion=self._on_tile_motion,\n'''
        '''            on_release=self._on_tile_release,\n'''
        '''        )\n''',
    )

    replace_once(
        launcher_docs,
        "**LC-3E drag gesture decisions:** `launcher_drag_gesture.py` rozstrzyga `WAITING / START / CONTINUE` dla motion oraz `ACTIVATE / REORDER / NOOP` dla release. Mutable state, widgety, feedback, auto-scroll i persistence pozostają w `DragDropCategoryGicleeApp`.\n",
        "**LC-3E drag gesture decisions:** `launcher_drag_gesture.py` rozstrzyga `WAITING / START / CONTINUE` dla motion oraz `ACTIVATE / REORDER / NOOP` dla release. Mutable state, widgety, feedback, auto-scroll i persistence pozostają w `DragDropCategoryGicleeApp`.\n\n"
        "**LC-3F Tk drag binding adapter:** `launcher_tk_drag_bindings.py` izoluje rekursywne zdjęcie bazowego kliknięcia, trzy bindingi myszy i kursor `hand2`. Metadane kafelka, closure press, stan gestu i persistence pozostają w `DragDropCategoryGicleeApp`.\n",
    )

    replace_once(
        contract,
        "**Status:** fresh reconnaissance · contract freeze  \n",
        "**Status:** LC-3F implemented\n",
    )


if __name__ == "__main__":
    main()
