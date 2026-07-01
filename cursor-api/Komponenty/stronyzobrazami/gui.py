"""GUI: zakladki do muzeow, galerii i katalogow online."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk
from urllib.parse import urlparse

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .storage import (
    SiteEntry,
    SiteStore,
    load_sites,
    new_site_id,
    next_sort_key,
    normalize_url,
    parse_bulk_links,
    save_sites,
    title_from_url,
)

APP_TITLE = "Strony z obrazami"


class StronyZObrazamiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 980, 680)
        self.root.minsize(720, 480)

        self._store = load_sites()
        self._selected_id: str | None = None
        self._search_tab: tk.Misc | None = None
        self._image_search_tab: tk.Misc | None = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        bookmarks_tab = ttk.Frame(notebook)
        search_tab = ttk.Frame(notebook)
        image_search_tab = ttk.Frame(notebook)
        download_tab = ttk.Frame(notebook)
        notebook.add(bookmarks_tab, text="Zakladki")
        notebook.add(search_tab, text="Wyszukiwarka")
        notebook.add(image_search_tab, text="Szukaj po obrazie")
        notebook.add(download_tab, text="Pobierz obraz")

        self._search_tab = search_tab
        self._image_search_tab = image_search_tab
        self._build_bookmarks_tab(bookmarks_tab)

        from .search_gui import build_search_tab

        build_search_tab(
            search_tab,
            self.root,
            get_store=lambda: self._store,
        )

        from .image_search_gui import build_image_search_tab

        build_image_search_tab(
            image_search_tab,
            self.root,
            get_store=lambda: self._store,
        )

        from .download_gui import build_download_tab

        build_download_tab(download_tab, self.root)

    def _refresh_search_sources(self) -> None:
        tab = self._search_tab
        if tab and hasattr(tab, "_refresh_search_sources"):
            tab._refresh_search_sources()  # type: ignore[attr-defined]
        img_tab = self._image_search_tab
        if img_tab and hasattr(img_tab, "_refresh_image_search_sources"):
            img_tab._refresh_image_search_sources()  # type: ignore[attr-defined]

    def _build_bookmarks_tab(self, parent: tk.Misc) -> None:
        toolbar = ttk.Frame(parent, padding=(8, 8, 8, 6))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Wklej linki…", command=self._paste_links).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="+ Dodaj", command=self._add_site).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Edytuj", command=self._edit_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Usun", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Otworz", command=self._open_selected).pack(side="right", padx=(6, 0))

        hint = ttk.Label(
            parent,
            text=(
                "Zapisane linki do muzeow, galerii i katalogow. "
                "Dwuklik lub «Otworz» — przegladarka. "
                "Zakladka «Wyszukiwarka» przeszukuje API tych muzeow."
            ),
            padding=(8, 0, 8, 8),
            foreground="#555",
            wraplength=920,
        )
        hint.pack(fill="x")

        filter_bar = ttk.Frame(parent, padding=(8, 0, 8, 6))
        filter_bar.pack(fill="x")
        ttk.Label(filter_bar, text="Kategoria:").pack(side="left")
        self.category_var = tk.StringVar(value="(wszystkie)")
        self.category_combo = ttk.Combobox(
            filter_bar,
            textvariable=self.category_var,
            state="readonly",
            width=18,
        )
        self.category_combo.pack(side="left", padx=(6, 12))
        self.category_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_list())

        ttk.Label(filter_bar, text="Filtr listy:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_bar, textvariable=self.search_var, width=32)
        search_entry.pack(side="left", padx=(6, 0))
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())

        self.count_var = tk.StringVar(value="")
        ttk.Label(filter_bar, textvariable=self.count_var, foreground="#0a6").pack(side="right")

        list_frame = ttk.LabelFrame(parent, text="Zapisane strony", padding=(8, 6))
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("title", "url", "category")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=14,
        )
        self.tree.heading("title", text="Nazwa")
        self.tree.heading("url", text="Adres URL")
        self.tree.heading("category", text="Kategoria")
        self.tree.column("title", width=240, stretch=True)
        self.tree.column("url", width=420, stretch=True)
        self.tree.column("category", width=120, stretch=False)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self._open_selected())
        self.tree.bind("<Return>", lambda _e: self._open_selected())
        self.tree.bind("<Delete>", lambda _e: self._delete_selected())

        notes_frame = ttk.LabelFrame(parent, text="Notatka", padding=8)
        notes_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.notes_text = tk.Text(
            notes_frame,
            height=3,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            background="#fafafa",
        )
        self.notes_text.pack(fill="x")
        self.notes_text.bind("<FocusOut>", self._save_notes_from_preview)
        self.notes_text.bind("<Control-s>", lambda _e: (self._save_notes_from_preview(), "break"))

    def _category_filter_values(self) -> list[str]:
        return ["(wszystkie)", *self._store.categories]

    def _refresh_list(self) -> None:
        selected = self._selected_id
        self.category_combo.configure(values=self._category_filter_values())

        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_var.get().strip().lower()
        category = self.category_var.get().strip()
        shown = 0
        for site in self._store.sorted():
            if category and category != "(wszystkie)" and site.category != category:
                continue
            hay = f"{site.title} {site.url} {site.category} {site.notes}".lower()
            if query and query not in hay:
                continue
            self.tree.insert(
                "",
                "end",
                iid=site.id,
                values=(site.title, site.url, site.category),
            )
            shown += 1

        total = len(self._store.sites)
        self.count_var.set(f"Pokazano {shown} / {total}")

        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
            self.tree.focus(selected)
        elif self.tree.get_children():
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._on_select()
        else:
            self._selected_id = None
            self._show_notes(None)

    def _selected_site(self) -> SiteEntry | None:
        if not self._selected_id:
            return None
        return self._store.by_id(self._selected_id)

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self.tree.selection()
        self._selected_id = sel[0] if sel else None
        self._show_notes(self._selected_site())

    def _show_notes(self, site: SiteEntry | None) -> None:
        self.notes_text.delete("1.0", "end")
        if site and site.notes:
            self.notes_text.insert("1.0", site.notes)

    def _save_notes_from_preview(self, _event: tk.Event | None = None) -> None:
        site = self._selected_site()
        if not site:
            return
        notes = self.notes_text.get("1.0", "end-1c").strip()
        if notes == site.notes:
            return
        site.notes = notes
        save_sites(self._store)

    def _open_url(self, url: str) -> None:
        target = normalize_url(url)
        if not target:
            messagebox.showwarning(APP_TITLE, "Brak poprawnego adresu URL.", parent=self.root)
            return
        try:
            webbrowser.open(target)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=self.root)

    def _open_selected(self) -> None:
        site = self._selected_site()
        if not site:
            messagebox.showinfo(APP_TITLE, "Zaznacz strone z listy.", parent=self.root)
            return
        self._save_notes_from_preview()
        self._open_url(site.url)

    def _edit_site_dialog(self, site: SiteEntry | None = None) -> SiteEntry | None:
        win = tk.Toplevel(self.root)
        win.title("Edytuj strone" if site else "Dodaj strone")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 520, 320)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        title_var = tk.StringVar(value=site.title if site else "")
        url_var = tk.StringVar(value=site.url if site else "")
        category_var = tk.StringVar(value=site.category if site else "Muzeum")
        notes_var = tk.StringVar(value=site.notes if site else "")

        ttk.Label(frame, text="Nazwa:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        title_entry = ttk.Entry(frame, textvariable=title_var, width=52)
        title_entry.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(frame, text="URL:").grid(row=1, column=0, sticky="w", pady=(0, 6))
        url_entry = ttk.Entry(frame, textvariable=url_var, width=52)
        url_entry.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(frame, text="Kategoria:").grid(row=2, column=0, sticky="w", pady=(0, 6))
        category_combo = ttk.Combobox(
            frame,
            textvariable=category_var,
            values=self._store.categories,
            width=24,
        )
        category_combo.grid(row=2, column=1, sticky="w", pady=(0, 6))

        ttk.Label(frame, text="Notatka:").grid(row=3, column=0, sticky="nw", pady=(0, 6))
        notes_entry = ttk.Entry(frame, textvariable=notes_var, width=52)
        notes_entry.grid(row=3, column=1, sticky="ew", pady=(0, 6))

        frame.grid_columnconfigure(1, weight=1)

        result: dict[str, SiteEntry | None] = {"site": None}

        def _submit() -> None:
            url = normalize_url(url_var.get())
            if not url:
                messagebox.showerror(APP_TITLE, "Podaj adres URL.", parent=win)
                return
            parsed = urlparse(url)
            if not parsed.netloc:
                messagebox.showerror(APP_TITLE, "Niepoprawny adres URL.", parent=win)
                return
            title = title_var.get().strip() or title_from_url(url)
            category = category_var.get().strip() or "Inne"
            if category not in self._store.categories:
                self._store.categories.append(category)
            notes = notes_var.get().strip()
            if site:
                site.title = title
                site.url = url
                site.category = category
                site.notes = notes
                result["site"] = site
            else:
                entry = SiteEntry(
                    id=new_site_id(),
                    title=title,
                    url=url,
                    category=category,
                    notes=notes,
                    sort_key=next_sort_key(self._store, category=category),
                )
                self._store.sites.append(entry)
                result["site"] = entry
            win.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text="Zapisz", command=_submit).pack(side="right", padx=(0, 8))

        title_entry.focus_set()
        win.bind("<Return>", lambda _e: _submit())
        win.bind("<Escape>", lambda _e: win.destroy())
        self.root.wait_window(win)
        return result["site"]

    def _add_site(self) -> None:
        site = self._edit_site_dialog()
        if not site:
            return
        save_sites(self._store)
        self._selected_id = site.id
        self._refresh_list()
        self._refresh_search_sources()
        show_toast(self.root, "Zapisano strone", duration_ms=1400)

    def _edit_selected(self) -> None:
        site = self._selected_site()
        if not site:
            messagebox.showinfo(APP_TITLE, "Zaznacz strone do edycji.", parent=self.root)
            return
        self._save_notes_from_preview()
        edited = self._edit_site_dialog(site)
        if not edited:
            return
        save_sites(self._store)
        self._refresh_list()
        self._refresh_search_sources()
        show_toast(self.root, "Zaktualizowano", duration_ms=1200)

    def _delete_selected(self) -> None:
        site = self._selected_site()
        if not site:
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac «{site.title}»?",
            parent=self.root,
        ):
            return
        self._store.sites = [s for s in self._store.sites if s.id != site.id]
        save_sites(self._store)
        self._selected_id = None
        self._refresh_list()
        self._refresh_search_sources()
        show_toast(self.root, "Usunieto", duration_ms=1200)

    def _paste_links(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Wklej linki")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 640, 460)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=(
                "Wklej linki (po jednym w linii). Opcjonalnie: «Nazwa | https://…».\n"
                "Duplikaty URL zostana pominięte."
            ),
            wraplength=580,
        ).pack(anchor="w", pady=(0, 8))

        category_var = tk.StringVar(value="Muzeum")
        cat_row = ttk.Frame(frame)
        cat_row.pack(fill="x", pady=(0, 8))
        ttk.Label(cat_row, text="Kategoria dla nowych:").pack(side="left")
        ttk.Combobox(
            cat_row,
            textvariable=category_var,
            values=self._store.categories,
            width=24,
        ).pack(side="left", padx=(8, 0))

        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, height=14, wrap="none", font=("Consolas", 10))
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        try:
            clip = self.root.clipboard_get()
            if clip.strip():
                text.insert("1.0", clip.strip())
        except tk.TclError:
            pass

        text.focus_set()

        def _import() -> None:
            category = category_var.get().strip() or "Inne"
            if category not in self._store.categories:
                self._store.categories.append(category)
            parsed = parse_bulk_links(text.get("1.0", "end"))
            if not parsed:
                messagebox.showerror(APP_TITLE, "Nie znaleziono poprawnych linkow.", parent=win)
                return
            existing = {s.url.lower().rstrip("/") for s in self._store.sites}
            added = 0
            for title, url in parsed:
                key = url.lower().rstrip("/")
                if key in existing:
                    continue
                self._store.sites.append(
                    SiteEntry(
                        id=new_site_id(),
                        title=title,
                        url=url,
                        category=category,
                        sort_key=next_sort_key(self._store, category=category),
                    ),
                )
                existing.add(key)
                added += 1
            save_sites(self._store)
            win.destroy()
            self._refresh_list()
            self._refresh_search_sources()
            show_toast(
                self.root,
                f"Dodano {added} stron" if added else "Wszystkie linki juz byly na liscie",
                duration_ms=1800,
            )

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text="Dodaj do listy", command=_import).pack(side="right", padx=(0, 8))

        win.bind("<Escape>", lambda _e: win.destroy())


def main() -> None:
    try:
        from tkinterdnd2 import TkinterDnD  # type: ignore

        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    StronyZObrazamiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
