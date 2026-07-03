"""GUI: Strony do uzycia — linki z opisem mozliwosci."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from urllib.parse import urlparse

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .storage import (
    PageEntry,
    PageStore,
    load_pages,
    new_page_id,
    next_sort_key,
    normalize_url,
    parse_bulk_links,
    save_pages,
    title_from_url,
)

APP_TITLE = "Strony do uzycia"


class StronyDoUzyciaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 980, 720)
        self.root.minsize(720, 520)

        self._store = load_pages()
        self._selected_id: str | None = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")

        toolbar = ttk.Frame(self.root, padding=(12, 8, 12, 6))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Wklej linki…", command=self._paste_links).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="+ Dodaj", command=self._add_page).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Edytuj", command=self._edit_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Usun", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Otworz", command=self._open_selected).pack(side="right", padx=(6, 0))

        hint = ttk.Label(
            self.root,
            text=(
                "Zapisane linki do stron sklepu, panelu Shopify, narzedzi i innych miejsc. "
                "Dwuklik lub «Otworz» — przegladarka. "
                "Pole «Co mozna robic» — opis zadan dostepnych na danej stronie."
            ),
            padding=(12, 0, 12, 8),
            foreground="#555",
            wraplength=920,
        )
        hint.pack(fill="x")

        filter_bar = ttk.Frame(self.root, padding=(12, 0, 12, 6))
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

        list_frame = ttk.LabelFrame(self.root, text="Zapisane strony", padding=(8, 6))
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        columns = ("title", "url", "category")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=12,
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

        desc_frame = ttk.LabelFrame(self.root, text="Co mozna robic", padding=8)
        desc_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.description_text = tk.Text(
            desc_frame,
            height=5,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            background="#fafafa",
        )
        self.description_text.pack(fill="x")
        self.description_text.bind("<FocusOut>", self._save_description_from_preview)
        self.description_text.bind(
            "<Control-s>",
            lambda _e: (self._save_description_from_preview(), "break"),
        )

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
        for page in self._store.sorted():
            if category and category != "(wszystkie)" and page.category != category:
                continue
            hay = f"{page.title} {page.url} {page.category} {page.description}".lower()
            if query and query not in hay:
                continue
            self.tree.insert(
                "",
                "end",
                iid=page.id,
                values=(page.title, page.url, page.category),
            )
            shown += 1

        total = len(self._store.pages)
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
            self._show_description(None)

    def _selected_page(self) -> PageEntry | None:
        if not self._selected_id:
            return None
        return self._store.by_id(self._selected_id)

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self.tree.selection()
        self._selected_id = sel[0] if sel else None
        self._show_description(self._selected_page())

    def _show_description(self, page: PageEntry | None) -> None:
        self.description_text.delete("1.0", "end")
        if page and page.description:
            self.description_text.insert("1.0", page.description)

    def _save_description_from_preview(self, _event: tk.Event | None = None) -> None:
        page = self._selected_page()
        if not page:
            return
        description = self.description_text.get("1.0", "end-1c").strip()
        if description == page.description:
            return
        page.description = description
        save_pages(self._store)

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
        page = self._selected_page()
        if not page:
            messagebox.showinfo(APP_TITLE, "Zaznacz strone z listy.", parent=self.root)
            return
        self._save_description_from_preview()
        self._open_url(page.url)

    def _edit_page_dialog(self, page: PageEntry | None = None) -> PageEntry | None:
        win = tk.Toplevel(self.root)
        win.title("Edytuj strone" if page else "Dodaj strone")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 560, 420)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        title_var = tk.StringVar(value=page.title if page else "")
        url_var = tk.StringVar(value=page.url if page else "")
        category_var = tk.StringVar(value=page.category if page else "Sklep")

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

        ttk.Label(frame, text="Co mozna robic:").grid(row=3, column=0, sticky="nw", pady=(0, 6))
        desc_text = tk.Text(frame, height=6, wrap="word", font=("Segoe UI", 10), width=52)
        desc_text.grid(row=3, column=1, sticky="ew", pady=(0, 6))
        if page and page.description:
            desc_text.insert("1.0", page.description)

        frame.grid_columnconfigure(1, weight=1)

        result: dict[str, PageEntry | None] = {"page": None}

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
            description = desc_text.get("1.0", "end-1c").strip()
            if page:
                page.title = title
                page.url = url
                page.category = category
                page.description = description
                result["page"] = page
            else:
                entry = PageEntry(
                    id=new_page_id(),
                    title=title,
                    url=url,
                    category=category,
                    description=description,
                    sort_key=next_sort_key(self._store, category=category),
                )
                self._store.pages.append(entry)
                result["page"] = entry
            win.destroy()

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text="Zapisz", command=_submit).pack(side="right", padx=(0, 8))

        title_entry.focus_set()
        win.bind("<Escape>", lambda _e: win.destroy())
        self.root.wait_window(win)
        return result["page"]

    def _add_page(self) -> None:
        page = self._edit_page_dialog()
        if not page:
            return
        save_pages(self._store)
        self._selected_id = page.id
        self._refresh_list()
        show_toast(self.root, "Zapisano strone", duration_ms=1400)

    def _edit_selected(self) -> None:
        page = self._selected_page()
        if not page:
            messagebox.showinfo(APP_TITLE, "Zaznacz strone do edycji.", parent=self.root)
            return
        self._save_description_from_preview()
        edited = self._edit_page_dialog(page)
        if not edited:
            return
        save_pages(self._store)
        self._refresh_list()
        show_toast(self.root, "Zaktualizowano", duration_ms=1200)

    def _delete_selected(self) -> None:
        page = self._selected_page()
        if not page:
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac «{page.title}»?",
            parent=self.root,
        ):
            return
        self._store.pages = [p for p in self._store.pages if p.id != page.id]
        save_pages(self._store)
        self._selected_id = None
        self._refresh_list()
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
                "Duplikaty URL zostana pominiete. Opis mozesz uzupelnic pozniej."
            ),
            wraplength=580,
        ).pack(anchor="w", pady=(0, 8))

        category_var = tk.StringVar(value="Sklep")
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
            existing = {p.url.lower().rstrip("/") for p in self._store.pages}
            added = 0
            for title, url in parsed:
                key = url.lower().rstrip("/")
                if key in existing:
                    continue
                self._store.pages.append(
                    PageEntry(
                        id=new_page_id(),
                        title=title,
                        url=url,
                        category=category,
                        sort_key=next_sort_key(self._store, category=category),
                    ),
                )
                existing.add(key)
                added += 1
            save_pages(self._store)
            win.destroy()
            self._refresh_list()
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
    root = tk.Tk()
    StronyDoUzyciaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
