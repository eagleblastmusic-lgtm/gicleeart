"""Notatnik - osobista baza wiedzy w markdownie z rozdzialami.

Struktura danych:
- Folder `Komponenty/notatnik/notatki/` zawiera pliki `.md` i **podfoldery**
  traktowane jako rozdzialy (z zagniezdzeniem).
- Rozdzial = podfolder. Notatka = plik `.md`.
- Ulubione: plik `Komponenty/notatnik/notatki/.favorites.json` z lista
  wzglednych sciezek notatek.

Lewa kolumna: `ttk.Treeview` - hierarchia rozdzialow + sekcja "⭐ Ulubione" na
gorze. PPM na rozdziale / notatce otwiera menu operacji.

Prawa kolumna: podglad (renderowany markdown z klikalnymi linkami) lub edycja
(tk.Text z highlightingiem linkow Ctrl+klik + markdown toolbar).

Skroty:
- Ctrl+S - zapisz w trybie edycji.
- Ctrl+N - nowa notatka (w aktualnie zaznaczonym rozdziale).
- Ctrl+F - wyszukiwarka globalna (fuzzy search po tytulach + tresciach).
- Ctrl+klik na link w edytorze - otwiera URL w przegladarce.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

try:
    from Komponenty._shared.toast import show_toast
except ImportError:  # pragma: no cover
    def show_toast(parent: tk.Misc, text: str, **_kw) -> None:  # type: ignore[override]
        print(f"[toast] {text}")


APP_TITLE = "Notatnik - osobista baza wiedzy"

_FAV_FILE = ".favorites.json"  # wzgledem notes_dir
_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _sanitize_name(name: str) -> str:
    """Dozwolone litery PL, cyfry, spacje, myslniki, podkreslenia."""
    name = (name or "").strip()
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", "-", name)
    return cleaned.strip(". ").strip("-")


class NotatnikApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x780")
        self.root.minsize(900, 560)

        self.notes_dir = Path(__file__).resolve().parent / "notatki"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_seed_notes()

        self._current_path: Path | None = None
        self._edit_mode = False
        self._original_content: str = ""
        self._modified_after_ms: str | None = None  # handle after() dla throttle

        self._build_ui()
        self._refresh_tree()

    # ======================================================================
    # Struktura widoku
    # ======================================================================
    def _build_ui(self) -> None:
        # ---- Toolbar glowny ----
        toolbar = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Notatnik", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="Instrukcja", command=self._show_help).pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="Otworz folder", command=self._open_notes_folder).pack(side="right", padx=4)
        ttk.Button(toolbar, text="+ Nowy rozdzial", command=self._new_chapter).pack(side="right", padx=4)
        ttk.Button(toolbar, text="+ Nowa notatka", command=self._new_note).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Odswiez", command=self._refresh_tree).pack(side="right", padx=4)

        # ---- Search bar ----
        search_bar = ttk.Frame(self.root, padding=(10, 0, 10, 4))
        search_bar.pack(fill="x")
        ttk.Label(search_bar, text="Szukaj:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_bar, textvariable=self.search_var, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        search_entry.bind("<Return>", lambda _e: self._do_search())
        search_entry.bind("<Escape>", lambda _e: (self.search_var.set(""), self._clear_search()))
        ttk.Button(search_bar, text="Znajdz", command=self._do_search).pack(side="left", padx=(6, 0))
        ttk.Button(search_bar, text="Wyczysc", command=self._clear_search).pack(side="left", padx=(4, 0))
        self._search_entry = search_entry

        # ---- Body ----
        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # Lewa strona - drzewko
        left_frame = ttk.LabelFrame(body, text="Rozdzialy i notatki")
        body.add(left_frame, weight=1)

        tree_wrap = ttk.Frame(left_frame)
        tree_wrap.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree = ttk.Treeview(
            tree_wrap, show="tree", selectmode="browse",
            height=28,
        )
        self.tree.pack(side="left", fill="both", expand=True)
        sb_t = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        sb_t.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb_t.set)
        self.tree.tag_configure("chapter", font=("Segoe UI", 10, "bold"))
        self.tree.tag_configure("note", font=("Segoe UI", 10))
        self.tree.tag_configure("favorite", foreground="#b88a00")
        self.tree.tag_configure("search_hit", background="#fff3cd")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_tree_selected())
        self.tree.bind("<Double-1>", lambda _e: self._on_tree_double_click())
        self.tree.bind("<Button-3>", self._show_tree_context_menu)
        self.tree.bind("<Delete>", lambda _e: self._delete_from_tree())

        # Prawa strona
        right_frame = ttk.Frame(body)
        body.add(right_frame, weight=3)

        # Pasek naglowka prawej strony
        right_head = ttk.Frame(right_frame)
        right_head.pack(fill="x", pady=(0, 4))
        self.title_var = tk.StringVar(value="(brak wybranej notatki)")
        ttk.Label(
            right_head, textvariable=self.title_var,
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        self.fav_btn = ttk.Button(right_head, text="☆ Ulubione", command=self._toggle_favorite, state="disabled")
        self.fav_btn.pack(side="right", padx=(0, 6))
        self.copy_btn = ttk.Button(right_head, text="Kopiuj", command=self._copy_current_content, state="disabled")
        self.copy_btn.pack(side="right", padx=(0, 6))
        self.edit_btn = ttk.Button(right_head, text="Edytuj", command=self._toggle_edit, state="disabled")
        self.edit_btn.pack(side="right", padx=(0, 6))
        self.save_btn = ttk.Button(right_head, text="Zapisz", command=self._save_current, state="disabled")
        self.save_btn.pack(side="right", padx=(0, 6))
        self.cancel_btn = ttk.Button(right_head, text="Anuluj", command=self._cancel_edit, state="disabled")
        self.cancel_btn.pack(side="right", padx=(0, 6))
        self.delete_btn = ttk.Button(right_head, text="Usun", command=self._delete_current, state="disabled")
        self.delete_btn.pack(side="right", padx=(0, 12))

        # Markdown toolbar (tylko w trybie edycji)
        self.md_toolbar = ttk.Frame(right_frame)
        # NIE pakujemy od razu - pojawia sie w trybie edycji
        for label, action in [
            ("B", lambda: self._wrap_selection("**", "**")),
            ("I", lambda: self._wrap_selection("*", "*")),
            ("Link", self._insert_link),
            ("Kod", lambda: self._wrap_selection("`", "`")),
            ("H2", lambda: self._prefix_line("## ")),
            ("H3", lambda: self._prefix_line("### ")),
            ("Lista", lambda: self._prefix_line("- ")),
            ("Cytat", lambda: self._prefix_line("> ")),
        ]:
            ttk.Button(self.md_toolbar, text=label, width=5, command=action).pack(side="left", padx=1)
        ttk.Separator(self.md_toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(self.md_toolbar, text="Ctrl+klik na linku otwiera w przegladarce",
                  foreground="#888").pack(side="left", padx=(4, 0))

        # Kontenery preview / edit
        self.preview_frame = ttk.Frame(right_frame)
        self.edit_frame = ttk.Frame(right_frame)
        self.preview_frame.pack(fill="both", expand=True)

        # Preview
        self.preview_text = tk.Text(
            self.preview_frame, wrap="word", padx=12, pady=10,
            bg="#fdfdfd", relief="flat", borderwidth=0,
            font=("Segoe UI", 10), cursor="arrow",
        )
        sb_p = ttk.Scrollbar(self.preview_frame, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=sb_p.set)
        self.preview_text.pack(side="left", fill="both", expand=True)
        sb_p.pack(side="right", fill="y")
        self.preview_text.configure(state="disabled")
        self.preview_text.bind("<Button-3>", self._show_preview_context_menu)

        # Edit
        self.edit_text = tk.Text(
            self.edit_frame, wrap="word", padx=8, pady=8,
            font=("Consolas", 10), undo=True,
        )
        sb_e = ttk.Scrollbar(self.edit_frame, command=self.edit_text.yview)
        self.edit_text.configure(yscrollcommand=sb_e.set)
        self.edit_text.pack(side="left", fill="both", expand=True)
        sb_e.pack(side="right", fill="y")
        self.edit_text.tag_configure("link_edit", foreground="#1a73e8", underline=True)
        self.edit_text.bind("<<Modified>>", self._on_edit_modified)
        self.edit_text.bind("<Control-Button-1>", self._on_editor_ctrl_click)
        # Po Ctrl+najechaniu na link - kursor dloni (heurystyka: tylko gdy pod kursorem jest tag)
        self.edit_text.bind("<Control-Motion>", self._on_editor_ctrl_motion)
        self.edit_text.bind("<KeyRelease-Control_L>", lambda _e: self.edit_text.configure(cursor="xterm"))
        self.edit_text.bind("<KeyRelease-Control_R>", lambda _e: self.edit_text.configure(cursor="xterm"))

        # Status bar
        status = ttk.Frame(self.root, padding=(10, 4))
        status.pack(fill="x")
        self.status_var = tk.StringVar(value=f"Folder: {self.notes_dir}")
        ttk.Label(status, textvariable=self.status_var, foreground="#777").pack(side="left")
        self.wordcount_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.wordcount_var, foreground="#555").pack(side="right")

        # Skroty klawiszowe
        self.root.bind("<Control-s>", lambda _e: self._save_current() if self._edit_mode else None)
        self.root.bind("<Control-n>", lambda _e: self._new_note())
        self.root.bind("<Control-f>", lambda _e: self._focus_search())

    # ======================================================================
    # Drzewko
    # ======================================================================
    def _load_favorites(self) -> set[str]:
        fav_path = self.notes_dir / _FAV_FILE
        if not fav_path.is_file():
            return set()
        try:
            data = json.loads(fav_path.read_text(encoding="utf-8"))
            return set(str(x) for x in (data.get("paths") or []))
        except (OSError, json.JSONDecodeError):
            return set()

    def _save_favorites(self, favs: set[str]) -> None:
        fav_path = self.notes_dir / _FAV_FILE
        try:
            fav_path.write_text(
                json.dumps({"paths": sorted(favs)}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie zapisac ulubionych:\n{e}")

    def _refresh_tree(self, *, keep_selection: bool = True) -> None:
        """Odbudowuje drzewko z systemu plikow."""
        prev_sel = None
        if keep_selection:
            sel = self.tree.selection()
            if sel:
                prev_sel = sel[0]

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Sekcja "Ulubione" na gorze
        favs = self._load_favorites()
        if favs:
            fav_root = self.tree.insert(
                "", "end", iid="__favorites__",
                text="⭐ Ulubione",
                open=True, tags=("chapter", "favorite"),
            )
            for fav_rel in sorted(favs):
                abs_p = self.notes_dir / fav_rel
                if not abs_p.is_file():
                    continue
                title = self._extract_title(abs_p) or abs_p.stem
                self.tree.insert(
                    fav_root, "end",
                    iid=f"__fav__::{fav_rel}",
                    text=f"📝 {title}",
                    tags=("note", "favorite"),
                    values=(str(abs_p),),
                )

        # Katalog glowny
        self._insert_tree_dir(self.notes_dir, parent="")

        # Licznik
        count = sum(1 for _ in self.notes_dir.rglob("*.md"))
        self.status_var.set(f"Folder: {self.notes_dir}  |  {count} notatek")

        # Przywroc zaznaczenie
        if prev_sel and self.tree.exists(prev_sel):
            self.tree.selection_set(prev_sel)
            self.tree.see(prev_sel)

    def _insert_tree_dir(self, directory: Path, *, parent: str) -> None:
        """Rekurencyjnie wstawia foldery i pliki .md."""
        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return
        for entry in entries:
            if entry.name.startswith("."):
                continue  # .favorites.json i inne ukryte
            rel = entry.relative_to(self.notes_dir)
            iid = str(rel).replace("\\", "/")
            if entry.is_dir():
                node = self.tree.insert(
                    parent, "end", iid=iid,
                    text=f"📁 {entry.name}",
                    tags=("chapter",),
                    open=False,
                )
                self._insert_tree_dir(entry, parent=node)
            elif entry.suffix.lower() == ".md":
                title = self._extract_title(entry) or entry.stem
                self.tree.insert(
                    parent, "end", iid=iid,
                    text=f"📝 {title}",
                    tags=("note",),
                    values=(str(entry),),
                )

    def _resolve_tree_path(self, iid: str) -> tuple[Path, bool]:
        """Zwraca (absolute_path, is_favorites_virtual) dla iid z drzewka.

        Dla iid zaczynajacego sie od `__fav__::` zwracamy faktyczny plik.
        """
        if not iid:
            return self.notes_dir, False
        if iid == "__favorites__":
            return self.notes_dir, True
        if iid.startswith("__fav__::"):
            rel = iid.split("::", 1)[1]
            return self.notes_dir / rel, False
        return self.notes_dir / iid, False

    def _on_tree_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        path, is_virtual = self._resolve_tree_path(iid)
        if is_virtual:
            return  # sekcja "Ulubione" sama w sobie nie jest notatka
        if path.is_file() and path.suffix.lower() == ".md":
            if self._edit_mode and self._has_unsaved_changes():
                if not messagebox.askyesno(
                    "Niezapisane zmiany",
                    "Masz niezapisane zmiany. Porzucic je i otworzyc inna notatke?",
                ):
                    return
                self._exit_edit_mode()
            self._load_note(path)

    def _on_tree_double_click(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        path, is_virtual = self._resolve_tree_path(sel[0])
        if path.is_dir() or is_virtual:
            # Toggle otwieranie/zamykanie
            self.tree.item(sel[0], open=not self.tree.item(sel[0], "open"))

    def _show_tree_context_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        path, is_virtual = self._resolve_tree_path(iid) if iid else (self.notes_dir, False)

        m = tk.Menu(self.tree, tearoff=0)
        if not iid:
            m.add_command(label="+ Nowy rozdzial", command=self._new_chapter)
            m.add_command(label="+ Nowa notatka", command=self._new_note)
        elif is_virtual:
            m.add_command(label="(sekcja wirtualna - bez akcji)", state="disabled")
        elif path.is_dir():
            m.add_command(label="+ Nowa notatka tutaj",
                          command=lambda: self._new_note(chapter_dir=path))
            m.add_command(label="+ Nowy podrozdzial",
                          command=lambda: self._new_chapter(parent_dir=path))
            m.add_separator()
            m.add_command(label="Zmien nazwe rozdzialu...",
                          command=lambda: self._rename_chapter(path))
            m.add_command(label="Usun rozdzial",
                          command=lambda: self._delete_chapter(path))
        else:
            m.add_command(label="Otworz w edytorze (Edytuj)",
                          command=self._enter_edit_mode)
            m.add_command(label="Kopiuj tresc",
                          command=self._copy_current_content)
            m.add_separator()
            in_favs = str(path.relative_to(self.notes_dir)).replace("\\", "/") in self._load_favorites()
            m.add_command(
                label="Usun z ulubionych" if in_favs else "Dodaj do ulubionych",
                command=self._toggle_favorite,
            )
            m.add_command(label="Zmien nazwe notatki...",
                          command=lambda: self._rename_note(path))
            m.add_command(label="Przenies do rozdzialu...",
                          command=lambda: self._move_note_to_chapter(path))
            m.add_separator()
            m.add_command(label="Usun notatke...",
                          command=lambda: self._delete_note(path))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # ======================================================================
    # Operacje na rozdzialach
    # ======================================================================
    def _new_chapter(self, *, parent_dir: Path | None = None) -> None:
        if parent_dir is None:
            parent_dir = self._current_chapter_dir()
        name = simpledialog.askstring(
            "Nowy rozdzial",
            f"Nazwa rozdzialu (tworzony w: {parent_dir.relative_to(self.notes_dir) or '.'}):",
            parent=self.root,
        )
        if not name:
            return
        safe = _sanitize_name(name)
        if not safe:
            messagebox.showerror("Blad", "Niepoprawna nazwa rozdzialu.")
            return
        target = parent_dir / safe
        if target.exists():
            messagebox.showerror("Blad", f"Rozdzial juz istnieje: {safe}")
            return
        try:
            target.mkdir(parents=True, exist_ok=False)
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie utworzyc rozdzialu:\n{e}")
            return
        self._refresh_tree()
        # Rozwin rodzica i zaznacz nowy rozdzial
        parent_rel = str(target.relative_to(self.notes_dir)).replace("\\", "/")
        if self.tree.exists(parent_rel):
            self.tree.selection_set(parent_rel)
            self.tree.see(parent_rel)
        show_toast(self.root, f"Utworzono rozdzial: {safe}")

    def _rename_chapter(self, path: Path) -> None:
        old_name = path.name
        new_name = simpledialog.askstring(
            "Zmien nazwe rozdzialu",
            f"Nowa nazwa rozdzialu '{old_name}':",
            initialvalue=old_name,
            parent=self.root,
        )
        if not new_name or new_name == old_name:
            return
        safe = _sanitize_name(new_name)
        if not safe:
            messagebox.showerror("Blad", "Niepoprawna nazwa.")
            return
        new_path = path.parent / safe
        if new_path.exists():
            messagebox.showerror("Blad", f"Rozdzial juz istnieje: {safe}")
            return
        try:
            path.rename(new_path)
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie zmienic nazwy:\n{e}")
            return
        # Zaktualizuj sciezki w ulubionych
        self._fixup_favorites_after_move(path, new_path)
        self._refresh_tree()

    def _delete_chapter(self, path: Path) -> None:
        try:
            content = list(path.iterdir())
        except OSError:
            content = []
        if content:
            if not messagebox.askyesno(
                "Usun rozdzial",
                f"Rozdzial '{path.name}' zawiera {len(content)} elementow.\n"
                f"Usunac rozdzial wraz z cala zawartoscia?",
                icon="warning",
                parent=self.root,
            ):
                return
            import shutil
            try:
                shutil.rmtree(path)
            except OSError as e:
                messagebox.showerror("Blad", f"Nie udalo sie usunac:\n{e}")
                return
        else:
            try:
                path.rmdir()
            except OSError as e:
                messagebox.showerror("Blad", f"Nie udalo sie usunac:\n{e}")
                return
        self._refresh_tree()
        show_toast(self.root, f"Usunieto rozdzial: {path.name}")

    def _current_chapter_dir(self) -> Path:
        """Zwraca folder rozdzialu (dla aktualnego zaznaczenia, z fallbackiem do root)."""
        sel = self.tree.selection()
        if not sel:
            return self.notes_dir
        path, is_virtual = self._resolve_tree_path(sel[0])
        if is_virtual:
            return self.notes_dir
        return path if path.is_dir() else path.parent

    # ======================================================================
    # Operacje na notatkach
    # ======================================================================
    def _new_note(self, *, chapter_dir: Path | None = None) -> None:
        if chapter_dir is None:
            chapter_dir = self._current_chapter_dir()
        chapter_dir.mkdir(parents=True, exist_ok=True)
        name = simpledialog.askstring(
            "Nowa notatka",
            f"Nazwa notatki (w rozdziale: {chapter_dir.relative_to(self.notes_dir) or '.'}):",
            parent=self.root,
        )
        if not name:
            return
        safe = _sanitize_name(name)
        if not safe:
            messagebox.showerror("Blad", "Niepoprawna nazwa.")
            return
        path = chapter_dir / f"{safe}.md"
        if path.exists():
            messagebox.showerror("Blad", f"Notatka juz istnieje: {safe}.md")
            return
        title_pretty = name.strip()
        title_pretty = title_pretty[:1].upper() + title_pretty[1:] if title_pretty else "Nowa notatka"
        try:
            path.write_text(
                f"# {title_pretty}\n\nWpisz tresc tutaj...\n",
                encoding="utf-8",
            )
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie utworzyc notatki:\n{e}")
            return
        self._refresh_tree()
        rel = str(path.relative_to(self.notes_dir)).replace("\\", "/")
        if self.tree.exists(rel):
            self.tree.selection_set(rel)
            self.tree.see(rel)
            self._on_tree_selected()
            self._enter_edit_mode()

    def _rename_note(self, path: Path) -> None:
        old_stem = path.stem
        new_name = simpledialog.askstring(
            "Zmien nazwe notatki",
            f"Nowa nazwa pliku (bez .md) dla '{old_stem}':",
            initialvalue=old_stem,
            parent=self.root,
        )
        if not new_name or new_name == old_stem:
            return
        safe = _sanitize_name(new_name)
        if not safe:
            messagebox.showerror("Blad", "Niepoprawna nazwa.")
            return
        new_path = path.parent / f"{safe}.md"
        if new_path.exists():
            messagebox.showerror("Blad", f"Notatka juz istnieje: {safe}.md")
            return
        try:
            path.rename(new_path)
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie zmienic nazwy:\n{e}")
            return
        self._fixup_favorites_after_move(path, new_path)
        if self._current_path == path:
            self._current_path = new_path
        self._refresh_tree()

    def _move_note_to_chapter(self, path: Path) -> None:
        """Dialog - wybierz folder docelowy z listy istniejacych rozdzialow."""
        chapters = ["(katalog glowny)"]
        for d in sorted(self.notes_dir.rglob("*")):
            if d.is_dir() and not d.name.startswith("."):
                try:
                    rel = d.relative_to(self.notes_dir)
                    chapters.append(str(rel).replace("\\", "/"))
                except ValueError:
                    pass
        if len(chapters) == 1:
            messagebox.showinfo("Brak rozdzialow", "Utworz najpierw rozdzial (+ Nowy rozdzial).")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Przenies notatke")
        dlg.geometry("400x420")
        dlg.transient(self.root)
        ttk.Label(dlg, text=f"Przenies '{path.name}' do rozdzialu:").pack(padx=10, pady=(10, 4), anchor="w")

        lb = tk.Listbox(dlg)
        lb.pack(fill="both", expand=True, padx=10, pady=4)
        for ch in chapters:
            lb.insert("end", ch)
        lb.selection_set(0)

        def _do_move() -> None:
            sel = lb.curselection()
            if not sel:
                return
            target = chapters[sel[0]]
            target_dir = self.notes_dir if target == "(katalog glowny)" else (self.notes_dir / target)
            new_path = target_dir / path.name
            if new_path == path:
                dlg.destroy()
                return
            if new_path.exists():
                messagebox.showerror("Blad", f"Notatka o tej nazwie juz istnieje w: {target}", parent=dlg)
                return
            try:
                path.rename(new_path)
            except OSError as e:
                messagebox.showerror("Blad", f"Nie udalo sie przeniesc:\n{e}", parent=dlg)
                return
            self._fixup_favorites_after_move(path, new_path)
            if self._current_path == path:
                self._current_path = new_path
            dlg.destroy()
            self._refresh_tree()
            show_toast(self.root, f"Przeniesiono do: {target}")

        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=10, pady=8)
        ttk.Button(btns, text="Przenies", command=_do_move).pack(side="right")
        ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 6))
        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        dlg.bind("<Return>", lambda _e: _do_move())

    def _delete_note(self, path: Path) -> None:
        if not messagebox.askyesno(
            "Usun notatke",
            f"Na pewno usunac notatke?\n\n{path.name}",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            path.unlink()
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie usunac:\n{e}")
            return
        # Usun z ulubionych
        favs = self._load_favorites()
        rel = str(path.relative_to(self.notes_dir)).replace("\\", "/")
        favs.discard(rel)
        self._save_favorites(favs)
        if self._current_path == path:
            self._current_path = None
            self.title_var.set("(brak wybranej notatki)")
            self._render_preview("")
            self.edit_text.delete("1.0", "end")
            for btn in (self.edit_btn, self.delete_btn, self.save_btn,
                        self.cancel_btn, self.copy_btn, self.fav_btn):
                btn.configure(state="disabled")
        self._refresh_tree()

    def _delete_current(self) -> None:
        if self._current_path:
            self._delete_note(self._current_path)

    def _delete_from_tree(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        path, is_virtual = self._resolve_tree_path(sel[0])
        if is_virtual:
            return
        if path.is_dir():
            self._delete_chapter(path)
        elif path.is_file():
            self._delete_note(path)

    def _fixup_favorites_after_move(self, old: Path, new: Path) -> None:
        """Po przeniesieniu/renamie aktualizuje wzgledne sciezki w ulubionych."""
        favs = self._load_favorites()
        if not favs:
            return
        old_rel = str(old.relative_to(self.notes_dir)).replace("\\", "/")
        new_rel = str(new.relative_to(self.notes_dir)).replace("\\", "/")
        changed = False
        updated: set[str] = set()
        for f in favs:
            if f == old_rel:
                updated.add(new_rel)
                changed = True
            elif f.startswith(old_rel + "/"):
                updated.add(new_rel + f[len(old_rel):])
                changed = True
            else:
                updated.add(f)
        if changed:
            self._save_favorites(updated)

    # ======================================================================
    # Ulubione
    # ======================================================================
    def _toggle_favorite(self) -> None:
        if not self._current_path:
            return
        favs = self._load_favorites()
        rel = str(self._current_path.relative_to(self.notes_dir)).replace("\\", "/")
        if rel in favs:
            favs.discard(rel)
            show_toast(self.root, "Usunieto z ulubionych")
        else:
            favs.add(rel)
            show_toast(self.root, "Dodano do ulubionych")
        self._save_favorites(favs)
        self._update_fav_button_label()
        self._refresh_tree()

    def _update_fav_button_label(self) -> None:
        if not self._current_path:
            self.fav_btn.configure(text="☆ Ulubione")
            return
        rel = str(self._current_path.relative_to(self.notes_dir)).replace("\\", "/")
        in_fav = rel in self._load_favorites()
        self.fav_btn.configure(text="★ Ulubione" if in_fav else "☆ Ulubione")

    # ======================================================================
    # Ladowanie / zapisywanie notatki
    # ======================================================================
    def _load_note(self, path: Path) -> None:
        self._current_path = path
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie wczytac pliku:\n{path}\n\n{e}")
            return
        title = self._extract_title(path) or path.stem
        rel = path.relative_to(self.notes_dir)
        self.title_var.set(f"{title}   ({rel})")
        self._render_preview(content)
        self.edit_text.delete("1.0", "end")
        self.edit_text.insert("1.0", content)
        self._highlight_edit_links()
        self._original_content = content
        for btn in (self.edit_btn, self.delete_btn, self.copy_btn, self.fav_btn):
            btn.configure(state="normal")
        self._update_fav_button_label()
        self._update_wordcount(content)

    def _save_current(self) -> None:
        if not self._current_path or not self._edit_mode:
            return
        content = self.edit_text.get("1.0", "end-1c")
        try:
            self._current_path.write_text(content, encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie zapisac:\n{e}")
            return
        self._original_content = content
        self._render_preview(content)
        title = self._extract_title(self._current_path) or self._current_path.stem
        rel = self._current_path.relative_to(self.notes_dir)
        self.title_var.set(f"{title}   ({rel})")
        self._refresh_tree()
        self._exit_edit_mode()
        show_toast(self.root, f"Zapisano: {self._current_path.name}")

    def _cancel_edit(self) -> None:
        if not self._edit_mode:
            return
        if self._has_unsaved_changes():
            if not messagebox.askyesno(
                "Anuluj edycje",
                "Porzucic niezapisane zmiany?",
            ):
                return
        self.edit_text.delete("1.0", "end")
        self.edit_text.insert("1.0", self._original_content)
        self._highlight_edit_links()
        self._exit_edit_mode()

    def _has_unsaved_changes(self) -> bool:
        if not self._edit_mode:
            return False
        return self.edit_text.get("1.0", "end-1c") != self._original_content

    # ======================================================================
    # Tryb edycji vs podgladu
    # ======================================================================
    def _toggle_edit(self) -> None:
        if self._edit_mode:
            self._exit_edit_mode()
        else:
            self._enter_edit_mode()

    def _enter_edit_mode(self) -> None:
        if not self._current_path:
            return
        self._edit_mode = True
        self.preview_frame.pack_forget()
        self.md_toolbar.pack(fill="x", pady=(0, 4))
        self.edit_frame.pack(fill="both", expand=True)
        self.edit_btn.configure(text="Podglad")
        self.save_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal")
        self.edit_text.focus_set()
        self._highlight_edit_links()

    def _exit_edit_mode(self) -> None:
        self._edit_mode = False
        self.edit_frame.pack_forget()
        self.md_toolbar.pack_forget()
        self.preview_frame.pack(fill="both", expand=True)
        self.edit_btn.configure(text="Edytuj")
        self.save_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")

    # ======================================================================
    # Markdown toolbar
    # ======================================================================
    def _wrap_selection(self, prefix: str, suffix: str) -> None:
        try:
            start = self.edit_text.index("sel.first")
            end = self.edit_text.index("sel.last")
            selected = self.edit_text.get(start, end)
        except tk.TclError:
            # Brak zaznaczenia - wstaw placeholder
            self.edit_text.insert("insert", f"{prefix}tekst{suffix}")
            return
        self.edit_text.delete(start, end)
        self.edit_text.insert(start, f"{prefix}{selected}{suffix}")

    def _prefix_line(self, prefix: str) -> None:
        try:
            line_idx = self.edit_text.index("insert linestart")
            line_text = self.edit_text.get(line_idx, f"{line_idx} lineend")
            if line_text.startswith(prefix):
                return  # juz jest
            self.edit_text.insert(line_idx, prefix)
        except tk.TclError:
            pass

    def _insert_link(self) -> None:
        url = simpledialog.askstring("Wstaw link", "URL:", parent=self.root)
        if not url:
            return
        text_for_link = simpledialog.askstring(
            "Wstaw link", "Tekst linku (Enter = URL):",
            initialvalue=url,
            parent=self.root,
        ) or url
        self.edit_text.insert("insert", f"[{text_for_link}]({url})")

    # ======================================================================
    # Highlighting linkow w edytorze
    # ======================================================================
    def _on_edit_modified(self, _event: tk.Event) -> None:
        # Event <<Modified>> odpala sie stale - trzeba zresetowac flage
        try:
            self.edit_text.edit_modified(False)
        except tk.TclError:
            return
        if self._modified_after_ms is not None:
            try:
                self.root.after_cancel(self._modified_after_ms)
            except ValueError:
                pass
        self._modified_after_ms = self.root.after(200, self._highlight_edit_links)

    def _highlight_edit_links(self) -> None:
        self._modified_after_ms = None
        self.edit_text.tag_remove("link_edit", "1.0", "end")
        content = self.edit_text.get("1.0", "end-1c")
        for match in _MD_LINK_RE.finditer(content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.edit_text.tag_add("link_edit", start, end)
        for match in _URL_RE.finditer(content):
            # Pomin jesli juz jest czescia markdown-linka
            if content[max(0, match.start() - 2):match.start()] == "](":
                continue
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.edit_text.tag_add("link_edit", start, end)
        # Wordcount
        self._update_wordcount(content)

    def _on_editor_ctrl_click(self, event: tk.Event) -> str | None:
        """Ctrl+klik na link w edytorze otwiera URL w przegladarce."""
        index = self.edit_text.index(f"@{event.x},{event.y}")
        tags = self.edit_text.tag_names(index)
        if "link_edit" not in tags:
            return None
        # Wyciagnij URL - znajdz zakres tagu pod kursorem
        ranges = self.edit_text.tag_ranges("link_edit")
        for i in range(0, len(ranges), 2):
            start, end = ranges[i], ranges[i + 1]
            if self.edit_text.compare(index, ">=", start) and self.edit_text.compare(index, "<=", end):
                span = self.edit_text.get(start, end)
                url = self._extract_url_from_span(span)
                if url:
                    try:
                        webbrowser.open(url)
                        show_toast(self.root, f"Otwarto: {url[:60]}")
                    except (webbrowser.Error, OSError):
                        messagebox.showerror("Blad", f"Nie udalo sie otworzyc:\n{url}")
                return "break"
        return None

    def _on_editor_ctrl_motion(self, event: tk.Event) -> None:
        index = self.edit_text.index(f"@{event.x},{event.y}")
        tags = self.edit_text.tag_names(index)
        if "link_edit" in tags:
            self.edit_text.configure(cursor="hand2")
        else:
            self.edit_text.configure(cursor="xterm")

    @staticmethod
    def _extract_url_from_span(span: str) -> str:
        m = _MD_LINK_RE.match(span)
        if m:
            return m.group(2)
        m2 = _URL_RE.match(span)
        if m2:
            return m2.group(0)
        return span.strip()

    # ======================================================================
    # Kopiowanie
    # ======================================================================
    def _copy_current_content(self) -> None:
        if not self._current_path:
            return
        try:
            content = self._current_path.read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie odczytac:\n{e}")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update()
        except tk.TclError:
            return
        show_toast(self.root, "Skopiowano do schowka")

    def _show_preview_context_menu(self, event: tk.Event) -> None:
        m = tk.Menu(self.preview_text, tearoff=0)
        # Kopiuj zaznaczenie (jesli jest)
        try:
            selected = self.preview_text.get("sel.first", "sel.last")
        except tk.TclError:
            selected = ""
        if selected:
            m.add_command(
                label="Kopiuj zaznaczenie",
                command=lambda: (self.root.clipboard_clear(),
                                 self.root.clipboard_append(selected),
                                 show_toast(self.root, "Skopiowano")),
            )
        m.add_command(label="Kopiuj cala notatke",
                      command=self._copy_current_content)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # ======================================================================
    # Rendering markdown w podgladzie
    # ======================================================================
    def _render_preview(self, content: str) -> None:
        try:
            from Komponenty._shared.help_dialog import _render_markdown, _setup_tags
        except ImportError:
            _setup_tags = None
            _render_markdown = None
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        if _setup_tags and _render_markdown:
            _setup_tags(self.preview_text)
            _render_markdown(self.preview_text, content)
        else:
            self.preview_text.insert("1.0", content)
        self.preview_text.configure(state="disabled")

    @staticmethod
    def _extract_title(path: Path) -> str:
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("# "):
                        return stripped[2:].strip()
            return ""
        except OSError:
            return ""

    def _update_wordcount(self, content: str) -> None:
        words = len(content.split())
        chars = len(content)
        self.wordcount_var.set(f"{words} slow, {chars} znakow")

    # ======================================================================
    # Wyszukiwarka
    # ======================================================================
    def _focus_search(self) -> None:
        self._search_entry.focus_set()
        self._search_entry.select_range(0, "end")

    def _do_search(self) -> None:
        query = (self.search_var.get() or "").strip().lower()
        if not query:
            self._clear_search()
            return
        matching_files: set[str] = set()
        for f in self.notes_dir.rglob("*.md"):
            rel = str(f.relative_to(self.notes_dir)).replace("\\", "/")
            # Szukaj w nazwie i w zawartosci
            if query in rel.lower():
                matching_files.add(rel)
                continue
            try:
                if query in f.read_text(encoding="utf-8").lower():
                    matching_files.add(rel)
            except OSError:
                continue

        # Podswietl wyniki
        for iid in self._walk_tree_iids(""):
            self.tree.item(iid, tags=self._update_tags_for_iid(iid, matching_files))
        # Rozwin parentow zeby bylo widac trafienia
        for rel in matching_files:
            parts = rel.split("/")
            for i in range(1, len(parts)):
                parent_iid = "/".join(parts[:i])
                if self.tree.exists(parent_iid):
                    self.tree.item(parent_iid, open=True)
            if self.tree.exists(rel):
                self.tree.see(rel)

        if not matching_files:
            show_toast(self.root, f"Brak wynikow dla: {query}", duration_ms=1400)
        else:
            show_toast(self.root, f"Znaleziono: {len(matching_files)}", duration_ms=1200)

    def _walk_tree_iids(self, parent: str):
        for child in self.tree.get_children(parent):
            yield child
            yield from self._walk_tree_iids(child)

    def _update_tags_for_iid(self, iid: str, matching: set[str]) -> tuple[str, ...]:
        current = list(self.tree.item(iid, "tags") or [])
        # Usun poprzedni search_hit
        current = [t for t in current if t != "search_hit"]
        if iid in matching or iid.startswith("__fav__::") and iid.split("::", 1)[1] in matching:
            current.append("search_hit")
        return tuple(current)

    def _clear_search(self) -> None:
        for iid in self._walk_tree_iids(""):
            tags = tuple(t for t in (self.tree.item(iid, "tags") or ()) if t != "search_hit")
            self.tree.item(iid, tags=tags)

    # ======================================================================
    # Folder
    # ======================================================================
    def _open_notes_folder(self) -> None:
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(str(self.notes_dir))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.notes_dir)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(self.notes_dir)])  # noqa: S607
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie otworzyc folderu:\n{e}")

    # ======================================================================
    # Help
    # ======================================================================
    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            messagebox.showinfo("Instrukcja", _NOTATNIK_HELP)
            return
        show_help(self.root, title="Instrukcja - Notatnik", text=_NOTATNIK_HELP)

    # ======================================================================
    # Seed
    # ======================================================================
    def _ensure_seed_notes(self) -> None:
        """Tworzy zaczatkowe notatki przy pierwszym uruchomieniu (folder pusty)."""
        has_any_md = any(self.notes_dir.rglob("*.md"))
        if has_any_md:
            return
        for filename, content in _SEED_NOTES.items():
            (self.notes_dir / filename).write_text(content, encoding="utf-8")


_NOTATNIK_HELP = """# Notatnik - osobista baza wiedzy

Notatki w **Markdown** zorganizowane w rozdzialy (foldery).

## Organizacja
- **Rozdzial** = podfolder w `Komponenty/notatnik/notatki/`.
- **Notatka** = plik `.md` w dowolnym rozdziale (lub w roocie).
- Mozesz tworzyc **podrozdzialy** (zagniezdzanie folderow).
- **Ulubione** - pojawiaja sie w sekcji `⭐ Ulubione` na gorze drzewa.

## Operacje
- **+ Nowy rozdzial** / **+ Nowa notatka** - przyciski w toolbarze.
- **PPM na rozdziale**: dodaj notatke, dodaj podrozdzial, zmien nazwe, usun.
- **PPM na notatce**: edytuj, kopiuj, ulubione, zmien nazwe, przenies do
  innego rozdzialu, usun.
- **Delete** na zaznaczonym elemencie - usun (z potwierdzeniem).
- **Drag**: mozesz tez recznie przeniesc plik w Eksploratorze - kliknij
  **Odswiez** w notatniku.

## Edycja i formatowanie
- **Ctrl+S** - zapisz w trybie edycji.
- **Ctrl+N** - nowa notatka.
- **Ctrl+F** - fokus na wyszukiwarce.
- **Markdown toolbar**: B / I / Link / Kod / H2 / H3 / Lista / Cytat.
- **Ctrl+klik na linku w edytorze** - otwiera URL w przegladarce.
- W trybie podgladu klikniecie w link `[tekst](url)` otwiera URL.

## Kopiowanie
- **Kopiuj** - caly tekst notatki do schowka.
- **PPM na podgladzie** - kopiuj zaznaczenie albo cala tresc.

## Wyszukiwanie
Wpisz fraze w pole **Szukaj** i Enter. Podswietlone zolto notatki w drzewie
to te, w ktorych fraza pasuje do nazwy pliku lub do tresci.

## Lokalizacja
`cursor-api/Komponenty/notatnik/notatki/`
"""


# ============================================================================
# Seed notatek (pokazywane tylko gdy caly folder jest pusty)
# ============================================================================

_SEED_NOTES: dict[str, str] = {
    "01-shopify-cli.md": """# Shopify CLI w Cursorze

## Logowanie
1. Otworz terminal w Cursorze.
2. Sprawdz czy CLI jest zainstalowane:
   ```
   shopify version
   ```
3. Zaloguj sie do sklepu:
   ```
   shopify auth login
   ```

## Polaczenie ze sklepem
```
shopify theme dev --store=twoj-sklep.myshopify.com
```

## Linki
- [Shopify CLI docs](https://shopify.dev/docs/apps/tools/cli)
- [Theme CLI](https://shopify.dev/docs/themes/tools/cli)
""",

    "02-szablony-shopify.md": """# Szablony Shopify

## Sciaganie
```
shopify theme pull --live
```

## Edycja lokalna
```
shopify theme dev
```

## Wysylka na serwer (do kopii, nie na live!)
```
shopify theme push --theme=<ID-kopii>
```
""",

    "03-workflow-gicleeapp.md": """# Workflow z GicleeApp

1. **Pobierz obraz** - wklej URL, pobierze do H:/Nowe obrazy/.
2. **Nazwij obraz** - przeciagnij pliki, wyszukaj nazwy, zmien nazwy.
3. **Dodaj obraz** - publikacja w Shopify (prompt dla LLM + import JSON).
4. **Notatnik** - zapisuj tutaj powtarzajace sie instrukcje.
""",
}


def main() -> None:
    root = tk.Tk()
    NotatnikApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
