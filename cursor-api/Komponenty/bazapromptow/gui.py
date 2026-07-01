"""Baza Promptow — przyciski z gotowym tekstem do schowka."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .catalog import load_catalog_rows
from .select_dialog import open_product_select_dialog
from .storage import (
    PromptEntry,
    PromptStore,
    load_prompts,
    new_prompt_id,
    next_sort_key,
    save_prompts,
)

APP_TITLE = "Baza Promptow"


class BazaPromptowApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 920, 640)
        self.root.minsize(640, 420)

        self._store = load_prompts()
        self._selected_id: str | None = None
        self._button_by_id: dict[str, tk.Button] = {}
        self._catalog_rows: list[dict] = []
        self._catalog_loading = False

        self._build_ui()
        self._render_buttons()
        self._load_catalog_async()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="+ Dodaj prompt", command=self._add_prompt).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Edytuj", command=self._edit_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Usun", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez prompty", command=self._reload).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Odswiez katalog", command=self._load_catalog_async).pack(side="right", padx=(6, 0))

        hint = ttk.Label(
            self.root,
            text=(
                "Kliknij przycisk → wybierz artyste i obraz → prompt z [autor]/[tytuł] "
                "trafia do schowka (+ grafika osobno). PPM — edycja."
            ),
            padding=(12, 0, 12, 6),
            foreground="#555",
            wraplength=880,
        )
        hint.pack(fill="x")

        self.status_var = tk.StringVar(value="Ladowanie katalogu produktow...")
        ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 4)).pack(fill="x")

        outer = ttk.Frame(self.root, padding=(12, 0, 12, 12))
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
        preview_frame.pack(fill="x", padx=12, pady=(0, 12))
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
        self._render_buttons()
        self.status_var.set(f"Odswiezono prompty ({len(self._store.prompts)}).")

    def _render_buttons(self) -> None:
        for child in self._buttons_frame.winfo_children():
            child.destroy()
        self._button_by_id.clear()

        prompts = self._store.sorted()
        if not prompts:
            ttk.Label(
                self._buttons_frame,
                text="Brak promptow. Kliknij «Dodaj prompt», aby utworzyc pierwszy.",
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
        if entry and entry.text.strip():
            preview = entry.text.strip()
            if len(preview) > 600:
                preview = preview[:600] + "..."
            self.preview_text.insert("1.0", preview)
        self.preview_text.configure(state="disabled")

    def _use_prompt(self, entry: PromptEntry) -> None:
        self._select(entry.id)
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

    def _copy_raw(self, entry: PromptEntry) -> None:
        """Ctrl+klik — surowy szablon bez wyboru produktu."""
        text = (entry.text or "").strip()
        if not text:
            return
        self._select(entry.id)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        show_toast(self.root, f"Szablon «{entry.label}» (bez podmiany)", duration_ms=1400)

    def _show_context_menu(self, event: tk.Event, entry: PromptEntry) -> None:
        self._select(entry.id)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Wybierz obraz i kopiuj...", command=lambda: self._use_prompt(entry))
        menu.add_command(label="Kopiuj szablon (surowy)", command=lambda: self._copy_raw(entry))
        menu.add_command(label="Edytuj...", command=lambda: self._edit_prompt(entry))
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
        )
        self._store.prompts.append(entry)
        save_prompts(self._store)
        self._selected_id = entry.id
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
        self._render_buttons()
        self._update_preview(entry)
        self.status_var.set(f"Zapisano: {label}")

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
        self._store.prompts = [p for p in self._store.prompts if p.id != entry.id]
        save_prompts(self._store)
        self._selected_id = None
        self._render_buttons()
        self.status_var.set("Usunieto prompt.")

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
