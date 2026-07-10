"""Rozszerzenie UI Notatnika o trwala reczna kolejnosc notatek."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from . import gui as _gui
from .note_order import NoteOrderStore


class OrderedNotatnikApp(_gui.NotatnikApp):
    """Notatnik z przyciskami Wyzej/Nizej i lokalnym plikiem kolejnosci."""

    @property
    def _note_orders(self) -> NoteOrderStore:
        store = getattr(self, "_note_order_store", None)
        if store is None:
            store = NoteOrderStore(self.notes_dir)
            self._note_order_store = store
        return store

    def _build_ui(self) -> None:
        super()._build_ui()

        left_frame = self.tree.master.master
        order_bar = ttk.Frame(left_frame)
        order_bar.pack(fill="x", padx=4, pady=(0, 4))

        self.move_up_btn = ttk.Button(
            order_bar,
            text="↑ Wyzej",
            command=lambda: self._move_selected_note(-1),
            state="disabled",
        )
        self.move_up_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.move_down_btn = ttk.Button(
            order_bar,
            text="↓ Nizej",
            command=lambda: self._move_selected_note(1),
            state="disabled",
        )
        self.move_down_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.tree.bind("<<TreeviewSelect>>", self._on_order_selection_changed, add="+")
        self.tree.bind("<Alt-Up>", lambda _event: self._move_selected_note(-1), add="+")
        self.tree.bind("<Alt-Down>", lambda _event: self._move_selected_note(1), add="+")

    def _refresh_tree(self, *, keep_selection: bool = True) -> None:
        super()._refresh_tree(keep_selection=keep_selection)
        if hasattr(self, "move_up_btn"):
            self._update_order_buttons()

    def _insert_tree_dir(self, directory: Path, *, parent: str) -> None:
        """Wstawia rozdzialy alfabetycznie, a notatki w zapisanej kolejnosci."""
        try:
            entries = [entry for entry in directory.iterdir() if not entry.name.startswith(".")]
        except OSError:
            return

        directories = sorted(
            (entry for entry in entries if entry.is_dir()),
            key=lambda item: item.name.casefold(),
        )
        notes = {
            entry.name: entry
            for entry in entries
            if entry.is_file() and entry.suffix.lower() == ".md"
        }

        for entry in directories:
            rel = entry.relative_to(self.notes_dir)
            iid = str(rel).replace("\\", "/")
            node = self.tree.insert(
                parent,
                "end",
                iid=iid,
                text=f"📁 {entry.name}",
                tags=("chapter",),
                open=False,
            )
            self._insert_tree_dir(entry, parent=node)

        for filename in self._note_orders.ordered_names(directory, notes):
            entry = notes[filename]
            rel = entry.relative_to(self.notes_dir)
            iid = str(rel).replace("\\", "/")
            title = self._extract_title(entry) or entry.stem
            self.tree.insert(
                parent,
                "end",
                iid=iid,
                text=f"📝 {title}",
                tags=("note",),
                values=(str(entry),),
            )

    def _on_tree_selected(self) -> None:
        """Nie przeladowuj tej samej notatki po przebudowie drzewa w trybie edycji."""
        selected = self._selected_real_note()
        if self._edit_mode and selected is not None and selected == self._current_path:
            self._update_order_buttons()
            return
        super()._on_tree_selected()

    def _on_order_selection_changed(self, _event: tk.Event | None = None) -> None:
        self._update_order_buttons()

    def _selected_real_note(self) -> Path | None:
        selection = self.tree.selection()
        if not selection:
            return None
        iid = selection[0]
        if iid == "__favorites__" or iid.startswith("__fav__::"):
            return None
        path, is_virtual = self._resolve_tree_path(iid)
        if is_virtual or not path.is_file() or path.suffix.lower() != ".md":
            return None
        return path

    @staticmethod
    def _note_names(directory: Path) -> list[str]:
        try:
            return [
                item.name
                for item in directory.iterdir()
                if item.is_file()
                and item.suffix.lower() == ".md"
                and not item.name.startswith(".")
            ]
        except OSError:
            return []

    def _can_move_path(self, path: Path, delta: int) -> bool:
        return self._note_orders.can_move(
            path.parent,
            path.name,
            delta,
            self._note_names(path.parent),
        )

    def _update_order_buttons(self) -> None:
        path = self._selected_real_note()
        up = path is not None and self._can_move_path(path, -1)
        down = path is not None and self._can_move_path(path, 1)
        self.move_up_btn.configure(state="normal" if up else "disabled")
        self.move_down_btn.configure(state="normal" if down else "disabled")

    def _move_selected_note(self, delta: int) -> str:
        path = self._selected_real_note()
        if path is None:
            return "break"
        try:
            moved = self._note_orders.move(
                path.parent,
                path.name,
                delta,
                self._note_names(path.parent),
            )
        except OSError as exc:
            messagebox.showerror(
                "Blad",
                f"Nie udalo sie zapisac kolejnosci notatek:\n{exc}",
                parent=self.root,
            )
            return "break"
        if not moved:
            self._update_order_buttons()
            return "break"

        iid = str(path.relative_to(self.notes_dir)).replace("\\", "/")
        self._refresh_tree()
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)
        self._update_order_buttons()
        _gui.show_toast(
            self.root,
            "Przeniesiono notatke wyzej" if delta < 0 else "Przeniesiono notatke nizej",
        )
        return "break"

    def _show_tree_context_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        path, is_virtual = self._resolve_tree_path(iid) if iid else (self.notes_dir, False)

        menu = tk.Menu(self.tree, tearoff=0)
        if not iid:
            menu.add_command(label="+ Nowy rozdzial", command=self._new_chapter)
            menu.add_command(label="+ Nowa notatka", command=self._new_note)
        elif is_virtual:
            menu.add_command(label="(sekcja wirtualna - bez akcji)", state="disabled")
        elif path.is_dir():
            menu.add_command(
                label="+ Nowa notatka tutaj",
                command=lambda: self._new_note(chapter_dir=path),
            )
            menu.add_command(
                label="+ Nowy podrozdzial",
                command=lambda: self._new_chapter(parent_dir=path),
            )
            menu.add_separator()
            menu.add_command(
                label="Zmien nazwe rozdzialu...",
                command=lambda: self._rename_chapter(path),
            )
            menu.add_command(label="Usun rozdzial", command=lambda: self._delete_chapter(path))
        else:
            menu.add_command(label="Otworz w edytorze (Edytuj)", command=self._enter_edit_mode)
            menu.add_command(label="Kopiuj tresc", command=self._copy_current_content)
            menu.add_separator()
            in_favs = str(path.relative_to(self.notes_dir)).replace("\\", "/") in self._load_favorites()
            menu.add_command(
                label="Usun z ulubionych" if in_favs else "Dodaj do ulubionych",
                command=self._toggle_favorite,
            )
            menu.add_command(
                label="Zmien nazwe notatki...",
                command=lambda: self._rename_note(path),
            )
            menu.add_separator()
            is_real_tree_note = not iid.startswith("__fav__::")
            menu.add_command(
                label="Przenies wyzej",
                command=lambda: self._move_selected_note(-1),
                state="normal"
                if is_real_tree_note and self._can_move_path(path, -1)
                else "disabled",
            )
            menu.add_command(
                label="Przenies nizej",
                command=lambda: self._move_selected_note(1),
                state="normal"
                if is_real_tree_note and self._can_move_path(path, 1)
                else "disabled",
            )
            menu.add_command(
                label="Przenies do rozdzialu...",
                command=lambda: self._move_note_to_chapter(path),
            )
            menu.add_separator()
            menu.add_command(label="Usun notatke...", command=lambda: self._delete_note(path))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _new_note(self, *, chapter_dir: Path | None = None) -> None:
        target = chapter_dir or self._current_chapter_dir()
        before = set(self._note_names(target))
        super()._new_note(chapter_dir=chapter_dir)
        added = set(self._note_names(target)) - before
        if len(added) == 1:
            path = target / added.pop()
            try:
                self._note_orders.append_note(path)
            except OSError as exc:
                messagebox.showerror(
                    "Blad",
                    f"Notatka powstala, ale nie zapisano jej kolejnosci:\n{exc}",
                )
            self._refresh_tree()

    def _rename_note(self, path: Path) -> None:
        before = set(self._note_names(path.parent))
        super()._rename_note(path)
        added = set(self._note_names(path.parent)) - before
        if not path.exists() and len(added) == 1:
            new_path = path.parent / added.pop()
            try:
                self._note_orders.rename_note(path, new_path)
            except OSError as exc:
                messagebox.showerror(
                    "Blad",
                    f"Zmieniono nazwe, ale nie zapisano kolejnosci:\n{exc}",
                )
            self._refresh_tree()

    def _delete_note(self, path: Path) -> None:
        super()._delete_note(path)
        if not path.exists():
            try:
                self._note_orders.remove_note(path)
            except OSError as exc:
                messagebox.showerror(
                    "Blad",
                    f"Usunieto notatke, ale nie zapisano kolejnosci:\n{exc}",
                )

    def _rename_chapter(self, path: Path) -> None:
        try:
            before = {item.name for item in path.parent.iterdir() if item.is_dir()}
        except OSError:
            before = set()
        super()._rename_chapter(path)
        try:
            added = {item.name for item in path.parent.iterdir() if item.is_dir()} - before
        except OSError:
            added = set()
        if not path.exists() and len(added) == 1:
            new_path = path.parent / added.pop()
            try:
                self._note_orders.rename_chapter(path, new_path)
            except OSError as exc:
                messagebox.showerror(
                    "Blad",
                    f"Zmieniono rozdzial, ale nie zapisano kolejnosci:\n{exc}",
                )
            self._refresh_tree()

    def _delete_chapter(self, path: Path) -> None:
        super()._delete_chapter(path)
        if not path.exists():
            try:
                self._note_orders.remove_chapter(path)
            except OSError as exc:
                messagebox.showerror(
                    "Blad",
                    f"Usunieto rozdzial, ale nie zapisano kolejnosci:\n{exc}",
                )

    def _move_note_to_chapter(self, path: Path) -> None:
        chapters = ["(katalog glowny)"]
        for directory in sorted(self.notes_dir.rglob("*")):
            if directory.is_dir() and not directory.name.startswith("."):
                try:
                    chapters.append(
                        str(directory.relative_to(self.notes_dir)).replace("\\", "/")
                    )
                except ValueError:
                    pass
        if len(chapters) == 1:
            messagebox.showinfo(
                "Brak rozdzialow",
                "Utworz najpierw rozdzial (+ Nowy rozdzial).",
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Przenies notatke")
        _gui.position_toplevel_screen_center(dialog, 400, 420)
        dialog.transient(self.root)
        ttk.Label(dialog, text=f"Przenies '{path.name}' do rozdzialu:").pack(
            padx=10,
            pady=(10, 4),
            anchor="w",
        )

        listbox = tk.Listbox(dialog)
        listbox.pack(fill="both", expand=True, padx=10, pady=4)
        for chapter in chapters:
            listbox.insert("end", chapter)
        listbox.selection_set(0)

        def do_move() -> None:
            selection = listbox.curselection()
            if not selection:
                return
            target = chapters[selection[0]]
            target_dir = (
                self.notes_dir
                if target == "(katalog glowny)"
                else self.notes_dir / target
            )
            new_path = target_dir / path.name
            if new_path == path:
                dialog.destroy()
                return
            if new_path.exists():
                messagebox.showerror(
                    "Blad",
                    f"Notatka o tej nazwie juz istnieje w: {target}",
                    parent=dialog,
                )
                return
            try:
                path.rename(new_path)
                self._note_orders.rename_note(path, new_path)
            except OSError as exc:
                if new_path.exists() and not path.exists():
                    try:
                        new_path.rename(path)
                    except OSError:
                        pass
                messagebox.showerror(
                    "Blad",
                    f"Nie udalo sie przeniesc:\n{exc}",
                    parent=dialog,
                )
                return
            self._fixup_favorites_after_move(path, new_path)
            if self._current_path == path:
                self._current_path = new_path
            dialog.destroy()
            self._refresh_tree()
            _gui.show_toast(self.root, f"Przeniesiono do: {target}")

        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=10, pady=8)
        ttk.Button(buttons, text="Przenies", command=do_move).pack(side="right")
        ttk.Button(buttons, text="Anuluj", command=dialog.destroy).pack(
            side="right",
            padx=(0, 6),
        )
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.bind("<Return>", lambda _event: do_move())


def main() -> None:
    """Uruchom oryginalny entry point z rozszerzona klasa aplikacji."""
    original_class = _gui.NotatnikApp
    _gui.NotatnikApp = OrderedNotatnikApp
    try:
        _gui.main()
    finally:
        _gui.NotatnikApp = original_class
