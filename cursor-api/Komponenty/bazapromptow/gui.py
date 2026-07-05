"""Baza Promptow — przyciski z gotowym tekstem do schowka."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from Komponenty._shared.clipboard_image import copy_pil_image_to_clipboard
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .catalog import load_catalog_rows
from .select_dialog import open_product_select_dialog
from .storage import (
    FOLDER_ALL,
    FOLDER_UNCATEGORIZED,
    DEFAULT_FOLDER_ID,
    FolderEntry,
    PromptEntry,
    PromptStore,
    context_image_path,
    delete_prompt_context_images,
    import_context_image,
    load_prompts,
    delete_context_image_file,
    new_folder_id,
    new_prompt_id,
    next_folder_sort_key,
    next_sort_key,
    save_prompts,
    sync_context_images,
)

APP_TITLE = "Baza Promptow"
_CONTEXT_THUMB_SIZE = (96, 72)


class BazaPromptowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 920, 720)
        self.root.minsize(640, 420)

        self._store = load_prompts()
        self._selected_id: str | None = None
        self._active_folder_view = FOLDER_ALL
        self._button_by_id: dict[str, tk.Button] = {}
        self._folder_tree: ttk.Treeview | None = None
        self._catalog_rows: list[dict] = []
        self._catalog_loading = False
        self._context_thumb_refs: list[tk.PhotoImage] = []

        self._build_ui()
        self._render_folders()
        self._render_buttons()
        self._load_catalog_async()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="+ Dodaj prompt", command=self._add_prompt).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Przenies do folderu", command=self._move_selected_to_folder).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Edytuj", command=self._edit_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Kontekst", command=self._edit_context_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Usun", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez prompty", command=self._reload).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez katalog", command=self._load_catalog_async).pack(side="right", padx=(6, 0))

        hint = ttk.Label(
            self.root,
            text=(
                "Kliknij prompt: w «Strona Główna» od razu kopiuje do schowka; "
                "w pozostalych folderach — wybor artysty i obrazu z katalogu. PPM — edycja."
            ),
            padding=(12, 0, 12, 6),
            foreground="#555",
            wraplength=880,
        )
        hint.pack(fill="x")

        self.status_var = tk.StringVar(value="Ladowanie katalogu produktow...")
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 4)).pack(fill="x")

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 0))

        folders_frame = ttk.LabelFrame(body, text="Foldery", padding=(6, 6, 6, 6))
        body.add(folders_frame, weight=0)

        folders_toolbar = ttk.Frame(folders_frame)
        folders_toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(folders_toolbar, text="+ Folder", command=self._add_folder).pack(side="left")
        ttk.Button(folders_toolbar, text="+ Podfolder", command=self._add_subfolder).pack(side="left", padx=(6, 0))
        ttk.Button(folders_toolbar, text="Usun folder", command=self._delete_active_folder).pack(side="left", padx=(6, 0))

        folder_tree_wrap = ttk.Frame(folders_frame)
        folder_tree_wrap.pack(fill="both", expand=True)
        self._folder_tree = ttk.Treeview(
            folder_tree_wrap,
            show="tree",
            selectmode="browse",
            height=18,
        )
        self._folder_tree.tag_configure("virtual", foreground="#555")
        folder_scroll = ttk.Scrollbar(folder_tree_wrap, orient="vertical", command=self._folder_tree.yview)
        self._folder_tree.configure(yscrollcommand=folder_scroll.set)
        self._folder_tree.pack(side="left", fill="both", expand=True)
        folder_scroll.pack(side="right", fill="y")
        self._folder_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_folder_selected())

        prompts_frame = ttk.Frame(body)
        body.add(prompts_frame, weight=1)

        outer = ttk.Frame(prompts_frame)
        outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        scroll_y = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._buttons_frame = ttk.Frame(self._canvas)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._buttons_frame, anchor="nw")

        self._buttons_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        preview_frame = ttk.LabelFrame(self.root, text="Podglad szablonu (placeholdery)", padding=8)
        preview_frame.pack(fill="x", padx=12, pady=(0, 6))
        self.preview_text = tk.Text(
            preview_frame,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            state="disabled",
            relief="flat",
            background="#f8f8f8",
        )
        self.preview_text.pack(fill="x")

        context_frame = ttk.LabelFrame(
            self.root,
            text="Kontekst (notatki i grafiki — nie ida do schowka przy «Kopiuj prompt»)",
            padding=8,
        )
        context_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.context_preview = tk.Text(
            context_frame,
            height=3,
            wrap="word",
            font=("Segoe UI", 10),
            state="disabled",
            relief="flat",
            background="#f4f6f8",
            foreground="#333",
        )
        self.context_preview.pack(fill="x")
        self.context_images_preview = ttk.Frame(context_frame)
        self.context_images_preview.pack(fill="x", pady=(6, 0))

    def _on_frame_configure(self, _event: tk.Event | None = None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self._canvas.itemconfigure(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        try:
            if self.root.winfo_containing(event.x_root, event.y_root) is None:
                return
        except tk.TclError:
            return
        delta = int(-1 * (event.delta / 120))
        self._canvas.yview_scroll(delta, "units")

    def _render_image_strip(
        self,
        parent: tk.Misc,
        images: list[str],
        *,
        thumb_refs: list[tk.PhotoImage] | None = None,
        on_remove: Callable[[int], None] | None = None,
        on_copy: Callable[[str], None] | None = None,
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        if not images:
            return
        refs = thumb_refs if thumb_refs is not None else self._context_thumb_refs
        for idx, rel in enumerate(images):
            cell = ttk.Frame(parent, padding=(0, 0, 8, 0))
            cell.pack(side="left")
            path = context_image_path(rel)
            photo = None
            try:
                from PIL import Image, ImageTk

                if path.is_file():
                    img = Image.open(path)
                    img.thumbnail(_CONTEXT_THUMB_SIZE)
                    photo = ImageTk.PhotoImage(img)
                    refs.append(photo)
            except Exception:
                photo = None
            if photo is not None:
                ttk.Label(cell, image=photo).pack()
            else:
                ttk.Label(cell, text=path.name, width=14, anchor="center").pack()
            ttk.Label(cell, text=path.name, font=("Segoe UI", 8), foreground="#666").pack()
            btn_row = ttk.Frame(cell)
            btn_row.pack(pady=(2, 0))
            if on_copy is not None:
                ttk.Button(btn_row, text="Schowek", width=8, command=lambda r=rel: on_copy(r)).pack(
                    side="left", padx=(0, 4)
                )
            if on_remove is not None:
                ttk.Button(btn_row, text="Usun", width=6, command=lambda i=idx: on_remove(i)).pack(side="left")

    def _copy_context_image(self, rel_path: str, *, parent: tk.Misc | None = None) -> None:
        path = context_image_path(rel_path)
        if not path.is_file():
            messagebox.showwarning(APP_TITLE, "Plik grafiki nie istnieje.", parent=parent or self.root)
            return
        try:
            from PIL import Image

            copy_pil_image_to_clipboard(Image.open(path))
            host = parent or self.root
            host.clipboard_append("")
            host.update()
            show_toast(host, "Grafika w schowku.", duration_ms=1200)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie skopiowac grafiki:\n{exc}", parent=parent or self.root)

    def _load_catalog_async(self) -> None:
        if self._catalog_loading:
            return
        self._catalog_loading = True
        self.status_var.set("Pobieram katalog produktow z Shopify...")

        def work() -> None:
            try:
                rows = load_catalog_rows(
                    on_progress=lambda s: self.root.after(
                        0, lambda m=s: self.status_var.set(m),
                    ),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda e=exc: (
                        self.status_var.set(f"Blad katalogu: {e}"),
                        messagebox.showerror(APP_TITLE, str(e), parent=self.root),
                    ),
                )
                self.root.after(0, lambda: setattr(self, "_catalog_loading", False))
                return

            def done() -> None:
                self._catalog_rows = rows
                self._catalog_loading = False
                n = len(self._store.prompts)
                self.status_var.set(
                    f"Katalog: {len(rows)} obraz(ow), {n} prompt(ow). Kliknij przycisk, aby wybrac produkt.",
                )

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True, name="bazapromptow-catalog").start()

    def _reload(self) -> None:
        self._store = load_prompts()
        self._selected_id = None
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Odswiezono prompty ({len(self._store.prompts)}).")

    def _folder_label(self, view_id: str) -> str:
        if view_id == FOLDER_ALL:
            return f"Wszystkie ({self._store.count_in_view(FOLDER_ALL)})"
        if view_id == FOLDER_UNCATEGORIZED:
            return f"Bez folderu ({self._store.count_in_view(FOLDER_UNCATEGORIZED)})"
        folder = self._store.find_folder(view_id)
        label = folder.label if folder else view_id
        return f"{label} ({self._store.count_in_view(view_id)})"

    def _active_real_folder_id(self) -> str | None:
        if self._active_folder_view in (FOLDER_ALL, FOLDER_UNCATEGORIZED):
            return None
        return self._active_folder_view

    def _render_folders(self) -> None:
        if self._folder_tree is None:
            return
        for item in self._folder_tree.get_children(""):
            self._folder_tree.delete(item)

        self._folder_tree.insert(
            "",
            "end",
            iid=FOLDER_ALL,
            text=self._folder_label(FOLDER_ALL),
            tags=("virtual",),
            open=True,
        )
        self._folder_tree.insert(
            "",
            "end",
            iid=FOLDER_UNCATEGORIZED,
            text=self._folder_label(FOLDER_UNCATEGORIZED),
            tags=("virtual",),
            open=True,
        )

        def insert_children(parent_id: str, tree_parent: str) -> None:
            for folder in self._store.folder_children(parent_id):
                self._folder_tree.insert(
                    tree_parent,
                    "end",
                    iid=folder.id,
                    text=self._folder_label(folder.id),
                    open=True,
                )
                insert_children(folder.id, folder.id)

        insert_children("", "")

        if self._active_folder_view in self._folder_tree.get_children("") or self._folder_tree.exists(self._active_folder_view):
            self._folder_tree.selection_set(self._active_folder_view)
            self._folder_tree.see(self._active_folder_view)
        else:
            self._active_folder_view = FOLDER_ALL
            self._folder_tree.selection_set(FOLDER_ALL)
            self._folder_tree.see(FOLDER_ALL)

    def _on_folder_selected(self) -> None:
        if self._folder_tree is None:
            return
        sel = self._folder_tree.selection()
        if not sel:
            return
        view_id = str(sel[0])
        self._active_folder_view = view_id
        self._render_buttons()

    def _render_buttons(self) -> None:
        for child in self._buttons_frame.winfo_children():
            child.destroy()
        self._button_by_id.clear()

        prompts = self._store.prompts_in_view(self._active_folder_view)
        if not prompts:
            if self._active_folder_view == FOLDER_ALL:
                empty_text = "Brak promptow. Kliknij «Dodaj prompt», aby utworzyc pierwszy."
            else:
                empty_text = "Brak promptow w tym folderze. Kliknij prompt i uzyj «Przenies do folderu»."
            ttk.Label(
                self._buttons_frame,
                text=empty_text,
                foreground="#777",
                padding=20,
            ).pack(anchor="w")
            self._update_preview(None)
            return

        cols = 2
        for idx, entry in enumerate(prompts):
            row, col = divmod(idx, cols)
            btn = tk.Button(
                self._buttons_frame,
                text=entry.label or "(bez nazwy)",
                font=("Segoe UI", 10),
                relief="raised",
                bd=1,
                padx=10,
                pady=8,
                cursor="hand2",
                anchor="center",
                command=lambda e=entry: self._use_prompt(e),
            )
            btn.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
            btn.bind("<Button-3>", lambda ev, e=entry: self._show_context_menu(ev, e))
            btn.bind("<Control-Button-1>", lambda _ev, e=entry: self._copy_raw(e), add="+")
            self._button_by_id[entry.id] = btn

        for c in range(cols):
            self._buttons_frame.grid_columnconfigure(c, weight=1)

        if self._selected_id:
            self._highlight_selection()

    def _select(self, prompt_id: str) -> None:
        self._selected_id = prompt_id
        self._highlight_selection()
        entry = self._find(prompt_id)
        self._update_preview(entry)

    def _highlight_selection(self) -> None:
        for pid, btn in self._button_by_id.items():
            if pid == self._selected_id:
                btn.configure(bg="#b2dfdb", activebackground="#80cbc4")
            else:
                btn.configure(bg="SystemButtonFace", activebackground="SystemButtonFace")

    def _find(self, prompt_id: str) -> PromptEntry | None:
        for p in self._store.prompts:
            if p.id == prompt_id:
                return p
        return None

    def _update_preview(self, entry: PromptEntry | None) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.context_preview.configure(state="normal")
        self.context_preview.delete("1.0", "end")
        if entry and entry.text.strip():
            preview = entry.text.strip()
            if len(preview) > 600:
                preview = preview[:600] + "..."
            self.preview_text.insert("1.0", preview)
        if entry and entry.context.strip():
            ctx = entry.context.strip()
            if len(ctx) > 400:
                ctx = ctx[:400] + "..."
            self.context_preview.insert("1.0", ctx)
        elif entry and entry.context_images:
            self.context_preview.insert("1.0", f"({len(entry.context_images)} grafik w kontekście)")
        else:
            self.context_preview.insert("1.0", "(brak — użyj «Kontekst», aby dodać notatki lub grafiki)")
        self.preview_text.configure(state="disabled")
        self.context_preview.configure(state="disabled")
        self._context_thumb_refs.clear()
        if entry and entry.context_images:
            self._render_image_strip(
                self.context_images_preview,
                entry.context_images,
                on_copy=lambda rel: self._copy_context_image(rel),
            )
        else:
            for child in self.context_images_preview.winfo_children():
                child.destroy()

    def _is_homepage_prompt(self, entry: PromptEntry) -> bool:
        if not entry.folder_id:
            return False
        if entry.folder_id == DEFAULT_FOLDER_ID:
            return True
        return self._store.is_descendant_of(entry.folder_id, DEFAULT_FOLDER_ID)

    def _use_prompt(self, entry: PromptEntry) -> None:
        self._select(entry.id)
        if self._is_homepage_prompt(entry):
            self._copy_raw(entry, toast=f"Skopiowano: {entry.label}")
            return
        self._open_catalog_dialog(entry)

    def _open_catalog_dialog(self, entry: PromptEntry) -> None:
        if self._catalog_loading:
            messagebox.showinfo(
                APP_TITLE,
                "Katalog produktow jest jeszcze ladowany. Poczekaj chwile.",
                parent=self.root,
            )
            return
        if not self._catalog_rows:
            if messagebox.askyesno(
                APP_TITLE,
                "Katalog jest pusty lub nie zaladowany.\nPobrac produkty z Shopify teraz?",
                parent=self.root,
            ):
                self._load_catalog_async()
            return
        open_product_select_dialog(
            self.root,
            entry=entry,
            catalog_rows=self._catalog_rows,
            on_status=self.status_var.set,
        )

    def _copy_raw(self, entry: PromptEntry, *, toast: str | None = None) -> None:
        """Surowy szablon bez wyboru produktu."""
        text = (entry.text or "").strip()
        if not text:
            return
        self._select(entry.id)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        show_toast(self.root, toast or f"Szablon «{entry.label}» (bez podmiany)", duration_ms=1400)

    def _show_context_menu(self, event: tk.Event, entry: PromptEntry) -> None:
        self._select(entry.id)
        menu = tk.Menu(self.root, tearoff=0)
        if self._is_homepage_prompt(entry):
            menu.add_command(label="Kopiuj prompt", command=lambda: self._copy_raw(entry, toast=f"Skopiowano: {entry.label}"))
            menu.add_command(label="Wybierz obraz i kopiuj...", command=lambda: self._open_catalog_dialog(entry))
        else:
            menu.add_command(label="Wybierz obraz i kopiuj...", command=lambda: self._open_catalog_dialog(entry))
            menu.add_command(label="Kopiuj szablon (surowy)", command=lambda: self._copy_raw(entry))
        menu.add_command(label="Edytuj...", command=lambda: self._edit_prompt(entry))
        menu.add_command(label="Kontekst...", command=lambda: self._edit_context(entry))
        menu.add_separator()
        move_menu = tk.Menu(menu, tearoff=0)
        for folder, depth in self._store.folder_tree_with_depth():
            prefix = ("  " * depth) + ("└ " if depth else "")
            move_menu.add_command(
                label=f"{prefix}{folder.label}",
                command=lambda f=folder: self._move_prompts_to_folder([entry.id], f.id),
            )
        move_menu.add_command(
            label="Bez folderu",
            command=lambda: self._move_prompts_to_folder([entry.id], ""),
        )
        menu.add_cascade(label="Przenies do folderu", menu=move_menu)
        menu.add_separator()
        menu.add_command(label="Przesun w gore", command=lambda: self._move(entry.id, -1))
        menu.add_command(label="Przesun w dol", command=lambda: self._move(entry.id, 1))
        menu.add_separator()
        menu.add_command(label="Usun", command=lambda: self._delete_prompt(entry))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _prompt_dialog(
        self,
        *,
        title: str,
        label: str = "",
        text: str = "",
    ) -> tuple[str, str] | None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 640, 480)
        win.minsize(480, 320)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Nazwa przycisku:").pack(anchor="w")
        label_var = tk.StringVar(value=label)
        label_entry = ttk.Entry(body, textvariable=label_var, font=("Segoe UI", 11))
        label_entry.pack(fill="x", pady=(4, 10))
        label_entry.focus_set()

        ttk.Label(body, text="Tresc promptu (uzyj [autor] i [tytuł]):").pack(anchor="w")
        text_box = tk.Text(body, wrap="word", font=("Consolas", 10), height=14)
        text_box.pack(fill="both", expand=True, pady=(4, 10))
        if text:
            text_box.insert("1.0", text)

        result: dict[str, str | None] = {"value": None}

        def _ok() -> None:
            lbl = label_var.get().strip()
            txt = text_box.get("1.0", "end-1c")
            if not lbl:
                messagebox.showwarning(APP_TITLE, "Podaj nazwe przycisku.", parent=win)
                return
            if not txt.strip():
                messagebox.showwarning(APP_TITLE, "Prompt nie moze byc pusty.", parent=win)
                return
            result["value"] = (lbl, txt)
            win.destroy()

        def _cancel() -> None:
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x")
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Zapisz", command=_ok).pack(side="right", padx=(0, 8))
        win.bind("<Escape>", lambda _e: _cancel())
        win.protocol("WM_DELETE_WINDOW", _cancel)

        self.root.wait_window(win)
        val = result["value"]
        if val is None:
            return None
        return str(val[0]), str(val[1])

    def _add_prompt(self) -> None:
        data = self._prompt_dialog(title="Nowy prompt")
        if not data:
            return
        label, text = data
        entry = PromptEntry(
            id=new_prompt_id(),
            label=label,
            text=text,
            sort_key=next_sort_key(self._store),
            folder_id="" if self._active_folder_view in (FOLDER_ALL, FOLDER_UNCATEGORIZED) else self._active_folder_view,
        )
        self._store.prompts.append(entry)
        save_prompts(self._store)
        self._selected_id = entry.id
        self._render_folders()
        self._render_buttons()
        self._update_preview(entry)
        self.status_var.set(f"Dodano: {label}")

    def _edit_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt (kliknij przycisk).", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._edit_prompt(entry)

    def _edit_prompt(self, entry: PromptEntry) -> None:
        data = self._prompt_dialog(
            title="Edytuj prompt",
            label=entry.label,
            text=entry.text,
        )
        if not data:
            return
        label, text = data
        entry.label = label
        entry.text = text
        save_prompts(self._store)
        self._render_folders()
        self._render_buttons()
        self._update_preview(entry)
        self.status_var.set(f"Zapisano: {label}")

    def _edit_context_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt (kliknij przycisk).", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._edit_context(entry)

    def _edit_context(self, entry: PromptEntry) -> None:
        self._select(entry.id)
        win = tk.Toplevel(self.root)
        win.title(f"Kontekst — {entry.label}")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 760, 620)
        win.minsize(560, 420)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        ttk.Label(
            body,
            text=(
                "Notatki i grafiki powiązane z tym promptem (podgląd w aplikacji).\n"
                "Przy «Kopiuj prompt» do schowka trafia wyłącznie szablon promptu.\n"
                "Grafiki możesz skopiować osobno przyciskiem «Schowek» (np. do Gemini / Nano Banana)."
            ),
            wraplength=700,
            foreground="#555",
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(body, text="Notatki:").pack(anchor="w")
        text_box = tk.Text(body, wrap="word", font=("Segoe UI", 10), height=10)
        text_box.pack(fill="both", expand=True, pady=(4, 10))
        if entry.context:
            text_box.insert("1.0", entry.context)

        images_frame = ttk.LabelFrame(body, text="Grafiki kontekstu", padding=(8, 8))
        images_frame.pack(fill="x", pady=(0, 10))

        images_toolbar = ttk.Frame(images_frame)
        images_toolbar.pack(fill="x", pady=(0, 6))
        images_row = ttk.Frame(images_frame)
        images_row.pack(fill="x")

        working_images: list[str] = list(entry.context_images)
        saved_images = list(entry.context_images)
        added_in_session: list[str] = []
        editor_thumb_refs: list[tk.PhotoImage] = []

        def _render_editor_images() -> None:
            self._render_image_strip(
                images_row,
                working_images,
                thumb_refs=editor_thumb_refs,
                on_remove=_remove_image,
                on_copy=lambda rel: self._copy_context_image(rel, parent=win),
            )

        def _remove_image(idx: int) -> None:
            if idx < 0 or idx >= len(working_images):
                return
            working_images.pop(idx)
            _render_editor_images()

        def _add_images() -> None:
            paths = filedialog.askopenfilenames(
                parent=win,
                title="Dodaj grafiki do kontekstu",
                filetypes=[
                    ("Obrazy", "*.jpg *.jpeg *.png *.webp *.gif *.bmp"),
                    ("Wszystkie pliki", "*.*"),
                ],
            )
            if not paths:
                return
            errors: list[str] = []
            for raw in paths:
                try:
                    rel = import_context_image(entry.id, Path(raw))
                    working_images.append(rel)
                    added_in_session.append(rel)
                except Exception as exc:
                    errors.append(f"{Path(raw).name}: {exc}")
            _render_editor_images()
            if errors:
                messagebox.showwarning(
                    APP_TITLE,
                    "Nie dodano części plików:\n" + "\n".join(errors[:8]),
                    parent=win,
                )

        ttk.Button(images_toolbar, text="Dodaj grafikę…", command=_add_images).pack(side="left")
        _render_editor_images()

        result: dict[str, bool] = {"saved": False}

        def _discard_session_additions() -> None:
            for rel in added_in_session:
                if rel not in entry.context_images:
                    delete_context_image_file(rel)

        def _save() -> None:
            entry.context = text_box.get("1.0", "end-1c")
            sync_context_images(saved_images, working_images)
            entry.context_images = list(working_images)
            save_prompts(self._store)
            self._update_preview(entry)
            n_text = len(entry.context.strip())
            n_img = len(entry.context_images)
            parts: list[str] = []
            if n_text:
                parts.append(f"{n_text} znaków")
            if n_img:
                parts.append(f"{n_img} graf.")
            detail = f" ({', '.join(parts)})" if parts else " (pusty)"
            self.status_var.set(f"Kontekst zapisany: {entry.label}{detail}")
            result["saved"] = True
            win.destroy()

        def _cancel() -> None:
            if not result["saved"]:
                _discard_session_additions()
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x")
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
        ttk.Button(btns, text="Wyczyść notatki", command=lambda: text_box.delete("1.0", "end")).pack(side="left")
        win.bind("<Escape>", lambda _e: _cancel())
        win.bind("<Control-Return>", lambda _e: _save())
        win.protocol("WM_DELETE_WINDOW", _cancel)
        text_box.focus_set()

        self.root.wait_window(win)
        if result["saved"]:
            show_toast(self.root, f"Kontekst: {entry.label}", duration_ms=1200)

    def _delete_selected(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(APP_TITLE, "Zaznacz prompt do usuniecia.", parent=self.root)
            return
        entry = self._find(self._selected_id)
        if entry:
            self._delete_prompt(entry)

    def _delete_prompt(self, entry: PromptEntry) -> None:
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac prompt «{entry.label}»?",
            parent=self.root,
        ):
            return
        delete_prompt_context_images(entry.id, entry.context_images)
        self._store.prompts = [p for p in self._store.prompts if p.id != entry.id]
        save_prompts(self._store)
        self._selected_id = None
        self._render_folders()
        self._render_buttons()
        self.status_var.set("Usunieto prompt.")

    def _move_selected_to_folder(self) -> None:
        if not self._selected_id:
            messagebox.showinfo(
                APP_TITLE,
                "Kliknij prompt, potem uzyj «Przenies do folderu».",
                parent=self.root,
            )
            return
        self._choose_folder_and_move([self._selected_id])

    def _choose_folder_and_move(self, prompt_ids: list[str]) -> None:
        folders = self._store.folder_tree_with_depth()
        if not folders:
            messagebox.showinfo(APP_TITLE, "Brak folderow.", parent=self.root)
            return

        win = tk.Toplevel(self.root)
        win.title("Przenies do folderu")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 460, 360)
        win.minsize(380, 280)

        body = ttk.Frame(win, padding=12)
        body.pack(fill="both", expand=True)

        n = len(prompt_ids)
        ttk.Label(
            body,
            text=f"Przenies {n} prompt(ow) do:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        list_wrap = ttk.Frame(body)
        list_wrap.pack(fill="both", expand=True)
        folder_list = tk.Listbox(list_wrap, exportselection=False, font=("Segoe UI", 10), height=10)
        folder_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=folder_list.yview)
        folder_list.configure(yscrollcommand=folder_scroll.set)
        folder_list.pack(side="left", fill="both", expand=True)
        folder_scroll.pack(side="right", fill="y")

        folder_ids: list[str] = [""]
        folder_list.insert("end", "Bez folderu")
        for folder, depth in folders:
            prefix = ("  " * depth) + ("└ " if depth else "")
            folder_list.insert("end", f"{prefix}{folder.label}")
            folder_ids.append(folder.id)

        folder_list.selection_set(0)

        result: dict[str, str | None] = {"folder_id": None}

        def _ok() -> None:
            sel = folder_list.curselection()
            if not sel:
                return
            result["folder_id"] = folder_ids[int(sel[0])]
            win.destroy()

        def _cancel() -> None:
            win.destroy()

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(12, 0))
        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Przenies", command=_ok).pack(side="right", padx=(0, 8))
        folder_list.bind("<Double-Button-1>", lambda _e: _ok())
        win.bind("<Escape>", lambda _e: _cancel())
        win.protocol("WM_DELETE_WINDOW", _cancel)

        self.root.wait_window(win)
        if result["folder_id"] is None:
            return
        self._move_prompts_to_folder(prompt_ids, str(result["folder_id"]))

    def _move_prompts_to_folder(self, prompt_ids: list[str], folder_id: str) -> None:
        if not prompt_ids:
            return
        moved = 0
        for prompt_id in prompt_ids:
            entry = self._find(prompt_id)
            if not entry:
                continue
            entry.folder_id = folder_id
            moved += 1
        if not moved:
            return
        save_prompts(self._store)
        self._render_folders()
        self._render_buttons()
        if folder_id:
            folder = self._store.find_folder(folder_id)
            target = folder.label if folder else folder_id
        else:
            target = "Bez folderu"
        self.status_var.set(f"Przeniesiono {moved} prompt(ow) do: {target}.")

    def _create_folder(self, *, parent_id: str, title: str) -> None:
        label = simpledialog.askstring(
            APP_TITLE,
            title,
            parent=self.root,
        )
        if not label:
            return
        label = label.strip()
        if not label:
            messagebox.showwarning(APP_TITLE, "Podaj nazwe folderu.", parent=self.root)
            return
        siblings = {f.label.lower() for f in self._store.folder_children(parent_id)}
        if label.lower() in siblings:
            messagebox.showwarning(APP_TITLE, "Folder o takiej nazwie juz istnieje na tym poziomie.", parent=self.root)
            return
        folder = FolderEntry(
            id=new_folder_id(),
            label=label,
            sort_key=next_folder_sort_key(self._store, parent_id),
            parent_id=parent_id,
        )
        self._store.folders.append(folder)
        save_prompts(self._store)
        self._active_folder_view = folder.id
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Dodano folder: {self._store.folder_path_label(folder.id)}")

    def _add_folder(self) -> None:
        self._create_folder(parent_id="", title="Nazwa nowego folderu:")

    def _add_subfolder(self) -> None:
        parent_id = self._active_real_folder_id()
        if not parent_id:
            messagebox.showinfo(
                APP_TITLE,
                "Wybierz folder nadrzedny (nie «Wszystkie» ani «Bez folderu»), potem kliknij «+ Podfolder».",
                parent=self.root,
            )
            return
        parent = self._store.find_folder(parent_id)
        parent_label = parent.label if parent else parent_id
        self._create_folder(
            parent_id=parent_id,
            title=f"Nazwa podfolderu w «{parent_label}»:",
        )

    def _delete_active_folder(self) -> None:
        view_id = self._active_folder_view
        if view_id in (FOLDER_ALL, FOLDER_UNCATEGORIZED):
            messagebox.showinfo(
                APP_TITLE,
                "Wybierz konkretny folder do usuniecia (nie «Wszystkie» ani «Bez folderu»).",
                parent=self.root,
            )
            return
        if view_id == DEFAULT_FOLDER_ID:
            messagebox.showinfo(APP_TITLE, "Folder «Strona Główna» jest domyslny i nie moze byc usuniety.", parent=self.root)
            return
        folder = self._store.find_folder(view_id)
        if not folder:
            return
        remove_ids = self._store.descendant_folder_ids(view_id)
        count = sum(1 for p in self._store.prompts if p.folder_id in remove_ids)
        subfolders = len(remove_ids) - 1
        msg = f"Folder «{folder.label}» zawiera {count} prompt(ow)."
        if subfolders:
            msg += f"\nUsuniete zostana tez {subfolders} podfolder(y)."
        msg += "\nPrompty trafia do «Bez folderu». Kontynuowac?"
        if count and not messagebox.askyesno(APP_TITLE, msg, parent=self.root):
            return
        if not count and subfolders and not messagebox.askyesno(APP_TITLE, msg, parent=self.root):
            return
        for prompt in self._store.prompts:
            if prompt.folder_id in remove_ids:
                prompt.folder_id = ""
        self._store.folders = [f for f in self._store.folders if f.id not in remove_ids]
        save_prompts(self._store)
        self._active_folder_view = FOLDER_ALL
        self._render_folders()
        self._render_buttons()
        self.status_var.set(f"Usunieto folder: {folder.label}")

    def _move(self, prompt_id: str, direction: int) -> None:
        ordered = self._store.sorted()
        ids = [p.id for p in ordered]
        if prompt_id not in ids:
            return
        idx = ids.index(prompt_id)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(ids):
            return
        ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
        for sort_key, pid in enumerate(ids):
            entry = self._find(pid)
            if entry:
                entry.sort_key = sort_key
        save_prompts(self._store)
        self._render_buttons()
        self._select(prompt_id)


def main() -> None:
    root = tk.Tk()
    BazaPromptowApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
