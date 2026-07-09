"""Wybór Trybu — panel krótkich komend aktywacyjnych."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .data_loader import Combination, WorkMode, WorkModeCatalog, all_categories, filter_modes, load_catalog
from .prompt_builder import (
    full_prompt_for_modes,
    prompt_for_combination,
    short_command_for_mode,
    short_prompt_for_combination,
    short_prompt_for_modes,
)

APP_TITLE = "Wybór Trybu"
_HINT = (
    "To są krótkie komendy aktywacyjne. Pełne prompty znajdziesz w Bazie Promptów."
)


class WyborTrybuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 980, 760)
        self.root.minsize(760, 560)

        try:
            self._catalog = load_catalog()
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie wczytac danych:\n{exc}", parent=root)
            raise

        self._selected_ids: set[str] = set()
        self._active_mode_id: str | None = None
        self._mode_vars: dict[str, tk.BooleanVar] = {}
        self._mode_row_frames: dict[str, tk.Frame] = {}
        self._combo_cards: dict[str, tk.Frame] = {}

        self._search_var = tk.StringVar()
        self._category_var = tk.StringVar(value="Wszystkie")
        self._selected_summary_var = tk.StringVar(value="Wybrane: (brak)")
        self._status_var = tk.StringVar(value="")

        self._modes_canvas: tk.Canvas | None = None
        self._combos_canvas: tk.Canvas | None = None

        self._build_ui()
        self._render_mode_list()
        self._render_combinations()
        self._refresh_prompt_preview()
        self._bind_list_mousewheels()

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Wyczysc wybor", command=self._clear_selection).pack(side="right")

        hint = ttk.Label(
            self.root,
            text=_HINT,
            padding=(12, 2, 12, 4),
            foreground="#666",
            wraplength=920,
        )
        hint.pack(fill="x")

        subhint = ttk.Label(
            self.root,
            text="Wybierz tryby, podejrzyj szczegoly i skopiuj gotowy prompt aktywacyjny.",
            padding=(12, 0, 12, 8),
            foreground="#555",
            wraplength=920,
        )
        subhint.pack(fill="x")

        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._modes_tab = ttk.Frame(self._notebook)
        self._combos_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._modes_tab, text="Tryby")
        self._notebook.add(self._combos_tab, text="Kombinacje")

        self._build_modes_tab()
        self._build_combos_tab()
        self._build_generator_panel()

        ttk.Label(self.root, textvariable=self._status_var, padding=(12, 0, 12, 8), foreground="#444").pack(
            fill="x"
        )

        self._search_var.trace_add("write", lambda *_: self._render_mode_list())
        self._category_var.trace_add("write", lambda *_: self._render_mode_list())

    def _build_modes_tab(self) -> None:
        body = ttk.Panedwindow(self._modes_tab, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(body, padding=(0, 0, 6, 0))
        body.add(left, weight=2)

        filters = ttk.Frame(left)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Szukaj:").pack(side="left")
        ttk.Entry(filters, textvariable=self._search_var, width=24).pack(side="left", padx=(6, 12))
        ttk.Label(filters, text="Kategoria:").pack(side="left")
        cat_box = ttk.Combobox(
            filters,
            textvariable=self._category_var,
            values=all_categories(self._catalog),
            state="readonly",
            width=16,
        )
        cat_box.pack(side="left", padx=(6, 0))

        list_wrap = ttk.LabelFrame(left, text="Tryby pracy", padding=6)
        list_wrap.pack(fill="both", expand=True)

        self._modes_canvas = tk.Canvas(list_wrap, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=self._modes_canvas.yview)
        self._modes_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._modes_canvas.pack(side="left", fill="both", expand=True)

        canvas = self._modes_canvas
        self._modes_list_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self._modes_list_frame, anchor="nw")

        def _on_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())

        self._modes_list_frame.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        right = ttk.LabelFrame(body, text="Szczegoly trybu", padding=10)
        body.add(right, weight=3)

        self._detail_title = ttk.Label(right, text="Wybierz tryb z listy", font=("Segoe UI", 13, "bold"))
        self._detail_title.pack(anchor="w")

        self._detail_category = ttk.Label(right, text="", foreground="#3949ab")
        self._detail_category.pack(anchor="w", pady=(2, 8))

        self._detail_text = scrolledtext.ScrolledText(
            right, height=18, wrap="word", font=("Segoe UI", 10), state="disabled"
        )
        self._detail_text.pack(fill="both", expand=True, pady=(0, 8))

        cmd_frame = ttk.LabelFrame(right, text="Przykladowa komenda", padding=6)
        cmd_frame.pack(fill="x", pady=(0, 8))
        self._detail_command = scrolledtext.ScrolledText(
            cmd_frame, height=4, wrap="word", font=("Consolas", 10), state="disabled"
        )
        self._detail_command.pack(fill="x")

        btn_row = ttk.Frame(right)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Kopiuj komende", command=self._copy_active_command).pack(side="left")
        ttk.Button(
            btn_row,
            text="Kopiuj naglowek trybu",
            command=self._copy_active_mode_short,
        ).pack(side="left", padx=(8, 0))

    def _build_combos_tab(self) -> None:
        wrap = ttk.Frame(self._combos_tab, padding=8)
        wrap.pack(fill="both", expand=True)

        self._combos_canvas = tk.Canvas(wrap, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=self._combos_canvas.yview)
        self._combos_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._combos_canvas.pack(side="left", fill="both", expand=True)

        canvas = self._combos_canvas
        self._combos_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self._combos_frame, anchor="nw")

        def _on_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())

        self._combos_frame.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))

    def _bind_list_mousewheels(self) -> None:
        canvases = tuple(c for c in (self._modes_canvas, self._combos_canvas) if c is not None)

        def _over_viewport(canvas: tk.Canvas, x_root: int, y_root: int) -> bool:
            try:
                if canvas.winfo_width() <= 2 or canvas.winfo_height() <= 2:
                    return False
                x = canvas.winfo_rootx()
                y = canvas.winfo_rooty()
                return (
                    x <= x_root < x + canvas.winfo_width()
                    and y <= y_root < y + canvas.winfo_height()
                )
            except tk.TclError:
                return False

        def _over_text_widget(evt: tk.Event) -> bool:
            w: tk.Misc | None = evt.widget
            while w is not None:
                if isinstance(w, tk.Text):
                    return True
                try:
                    w = w.master
                except tk.TclError:
                    break
            return False

        def _scroll_canvas(canvas: tk.Canvas, evt: tk.Event) -> None:
            if evt.delta:
                canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
            elif evt.num == 4:
                canvas.yview_scroll(-1, "units")
            elif evt.num == 5:
                canvas.yview_scroll(1, "units")

        def _canvas_for_widget(widget: tk.Misc | None) -> tk.Canvas | None:
            if widget is None:
                return None
            inner_by_canvas = {
                self._modes_canvas: self._modes_list_frame,
                self._combos_canvas: self._combos_frame,
            }
            for canvas, inner in inner_by_canvas.items():
                if canvas is None or inner is None:
                    continue
                w: tk.Misc | None = widget
                while w is not None:
                    if w == canvas or w == inner:
                        return canvas
                    try:
                        w = w.master
                    except tk.TclError:
                        break
            return None

        def _event_root_coords(evt: tk.Event) -> tuple[int, int]:
            x_root = int(getattr(evt, "x_root", -1))
            y_root = int(getattr(evt, "y_root", -1))
            if x_root >= 0 and y_root >= 0:
                return x_root, y_root
            try:
                w = evt.widget
                return w.winfo_rootx() + int(evt.x), w.winfo_rooty() + int(evt.y)
            except tk.TclError:
                return -1, -1

        def _on_mousewheel(evt: tk.Event) -> str | None:
            if _over_text_widget(evt):
                return None
            x_root, y_root = _event_root_coords(evt)
            if x_root >= 0 and y_root >= 0:
                for canvas in canvases:
                    if _over_viewport(canvas, x_root, y_root):
                        _scroll_canvas(canvas, evt)
                        return "break"
            canvas = _canvas_for_widget(evt.widget)
            if canvas is not None:
                _scroll_canvas(canvas, evt)
                return "break"
            return None

        self.root.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", _on_mousewheel, add="+")
        self.root.bind_all("<Button-5>", _on_mousewheel, add="+")

    def _build_generator_panel(self) -> None:
        panel = ttk.LabelFrame(self.root, text="Generator komendy", padding=10)
        panel.pack(fill="both", expand=False, padx=12, pady=(0, 4))

        ttk.Label(panel, textvariable=self._selected_summary_var, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(0, 6)
        )

        self._prompt_preview = scrolledtext.ScrolledText(
            panel, height=7, wrap="word", font=("Consolas", 10), state="disabled"
        )
        self._prompt_preview.pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(panel)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Kopiuj prompt aktywacyjny", command=self._copy_full_prompt).pack(side="left")
        ttk.Button(btn_row, text="Kopiuj krotki", command=self._copy_short_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(btn_row, text="Wyczysc wybor", command=self._clear_selection).pack(side="left", padx=(8, 0))

    def _render_mode_list(self) -> None:
        for child in self._modes_list_frame.winfo_children():
            child.destroy()
        self._mode_vars.clear()
        self._mode_row_frames.clear()

        modes = filter_modes(
            self._catalog,
            query=self._search_var.get(),
            category=self._category_var.get(),
        )
        if not modes:
            ttk.Label(
                self._modes_list_frame,
                text="Brak trybow dla tego filtra.",
                foreground="#777",
            ).pack(anchor="w", padx=4, pady=8)
            return

        for mode in modes:
            self._add_mode_row(mode)

        if self._active_mode_id and self._active_mode_id not in self._mode_row_frames:
            self._active_mode_id = modes[0].id
            self._show_mode_details(modes[0])
        elif self._active_mode_id is None and modes:
            self._active_mode_id = modes[0].id
            self._show_mode_details(modes[0])

        self._highlight_active_row()

    def _add_mode_row(self, mode: WorkMode) -> None:
        row = tk.Frame(self._modes_list_frame, padx=4, pady=3)
        row.pack(fill="x")

        var = tk.BooleanVar(value=mode.id in self._selected_ids)
        self._mode_vars[mode.id] = var

        def _toggle() -> None:
            if var.get():
                self._selected_ids.add(mode.id)
            else:
                self._selected_ids.discard(mode.id)
            self._refresh_prompt_preview()

        chk = ttk.Checkbutton(row, variable=var, command=_toggle)
        chk.pack(side="left")

        num = ttk.Label(row, text=f"{mode.number:>2}.", width=3, font=("Segoe UI", 10, "bold"))
        num.pack(side="left")

        name_btn = tk.Label(
            row,
            text=mode.name,
            font=("Segoe UI", 10),
            fg="#1a237e",
            cursor="hand2",
            anchor="w",
        )
        name_btn.pack(side="left", fill="x", expand=True)
        name_btn.bind("<Button-1>", lambda _e, m=mode: self._select_mode(m))

        cat = tk.Label(
            row,
            text=mode.category,
            font=("Segoe UI", 8, "bold"),
            fg="white",
            bg=mode.category_color,
            padx=6,
            pady=1,
        )
        cat.pack(side="right", padx=(6, 0))

        purpose = ttk.Label(
            row,
            text=mode.purpose[:90] + ("..." if len(mode.purpose) > 90 else ""),
            foreground="#555",
            wraplength=360,
        )
        purpose.pack(fill="x", padx=(28, 0), pady=(2, 0))
        purpose.bind("<Button-1>", lambda _e, m=mode: self._select_mode(m))

        self._mode_row_frames[mode.id] = row

    def _select_mode(self, mode: WorkMode) -> None:
        self._active_mode_id = mode.id
        self._show_mode_details(mode)
        self._highlight_active_row()

    def _highlight_active_row(self) -> None:
        for mode_id, row in self._mode_row_frames.items():
            if mode_id == self._active_mode_id:
                row.configure(bg="#e8eaf6", highlightbackground="#3949ab", highlightthickness=1)
            else:
                row.configure(bg=self.root.cget("bg"), highlightthickness=0)

    def _show_mode_details(self, mode: WorkMode) -> None:
        self._detail_title.configure(text=f"{mode.number}. {mode.name}")
        self._detail_category.configure(text=f"Kategoria: {mode.category}")

        body = (
            f"Do czego sluzy:\n{mode.purpose}\n\n"
            f"Na co patrze (czym rozni sie od innych):\n{mode.focus}\n\n"
            f"Kiedy uzywac:\n{mode.when_to_use}\n\n"
            f"Najprosciej (oczekiwany efekt):\n{mode.simplest}"
        )
        self._set_text(self._detail_text, body)
        self._set_text(self._detail_command, mode.sample_command)

    def _render_combinations(self) -> None:
        for child in self._combos_frame.winfo_children():
            child.destroy()
        self._combo_cards.clear()

        for combo in self._catalog.combinations:
            self._add_combo_card(combo)

    def _add_combo_card(self, combo: Combination) -> None:
        card = ttk.LabelFrame(self._combos_frame, text=combo.name, padding=10)
        card.pack(fill="x", pady=(0, 10), padx=4)
        self._combo_cards[combo.id] = card

        ttk.Label(card, text=f"Najlepsza do: {combo.best_for}", wraplength=860).pack(anchor="w")
        ttk.Label(card, text=f"Co dostajesz: {combo.delivers}", wraplength=860).pack(anchor="w", pady=(4, 0))
        ttk.Label(card, text=f"Przyklad uzycia: {combo.usage_example}", wraplength=860).pack(
            anchor="w", pady=(4, 0)
        )
        if combo.note:
            ttk.Label(card, text=f"Uwaga: {combo.note}", foreground="#666", wraplength=860).pack(
                anchor="w", pady=(4, 0)
            )

        chips = ttk.Frame(card)
        chips.pack(anchor="w", pady=(8, 0))
        for mode_id in combo.mode_ids:
            mode = self._catalog.mode(mode_id)
            if mode is None:
                continue
            tk.Label(
                chips,
                text=mode.short_label,
                font=("Segoe UI", 8, "bold"),
                fg="white",
                bg=mode.category_color,
                padx=6,
                pady=2,
            ).pack(side="left", padx=(0, 6))

        btn_row = ttk.Frame(card)
        btn_row.pack(anchor="w", pady=(10, 0))
        ttk.Button(
            btn_row,
            text="Wybierz tryby",
            command=lambda c=combo: self._apply_combination(c),
        ).pack(side="left")
        ttk.Button(
            btn_row,
            text="Kopiuj kombinacje",
            command=lambda c=combo: self._copy_combination_short(c),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            btn_row,
            text="Kopiuj prompt aktywacyjny",
            command=lambda c=combo: self._copy_combination_full(c),
        ).pack(side="left", padx=(8, 0))

        for widget in (card,):
            widget.bind("<Button-1>", lambda _e, c=combo: self._apply_combination(c))

    def _apply_combination(self, combo: Combination) -> None:
        self._selected_ids = set(combo.mode_ids)
        for mode_id, var in self._mode_vars.items():
            var.set(mode_id in self._selected_ids)
        self._render_mode_list()
        self._refresh_prompt_preview()
        self._notebook.select(self._modes_tab)
        if combo.mode_ids:
            first = self._catalog.mode(combo.mode_ids[0])
            if first is not None:
                self._select_mode(first)
        self._status_var.set(f"Zaznaczono kombinacje: {combo.name}")

    def _selected_modes_ordered(self) -> list[WorkMode]:
        order = {mode.id: mode.number for mode in self._catalog.modes}
        ids = sorted(self._selected_ids, key=lambda mid: order.get(mid, 999))
        return self._catalog.modes_for_ids(ids)

    def _refresh_prompt_preview(self) -> None:
        modes = self._selected_modes_ordered()
        if modes:
            labels = " + ".join(m.short_label for m in modes)
            self._selected_summary_var.set(f"Wybrane: {labels}")
            self._set_text(self._prompt_preview, full_prompt_for_modes(modes))
        else:
            self._selected_summary_var.set("Wybrane: (brak)")
            self._set_text(self._prompt_preview, "")

    def _clear_selection(self) -> None:
        self._selected_ids.clear()
        for var in self._mode_vars.values():
            var.set(False)
        self._refresh_prompt_preview()
        self._status_var.set("Wyczyszczono wybor")

    def _copy_text(self, text: str, toast: str = "Skopiowano!") -> None:
        if not text.strip():
            show_toast(self.root, "Brak tekstu do skopiowania", duration_ms=1400)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        show_toast(self.root, toast)

    def _copy_active_command(self) -> None:
        if not self._active_mode_id:
            return
        mode = self._catalog.mode(self._active_mode_id)
        if mode is None:
            return
        self._copy_text(mode.sample_command, "Skopiowano komende")

    def _copy_active_mode_short(self) -> None:
        if not self._active_mode_id:
            return
        mode = self._catalog.mode(self._active_mode_id)
        if mode is None:
            return
        self._copy_text(short_command_for_mode(mode), "Skopiowano naglowek trybu")

    def _copy_full_prompt(self) -> None:
        modes = self._selected_modes_ordered()
        self._copy_text(full_prompt_for_modes(modes), "Skopiowano prompt aktywacyjny")

    def _copy_short_prompt(self) -> None:
        modes = self._selected_modes_ordered()
        self._copy_text(short_prompt_for_modes(modes), "Skopiowano krotki prompt")

    def _copy_combination_short(self, combo: Combination) -> None:
        modes = self._catalog.modes_for_ids(list(combo.mode_ids))
        self._copy_text(short_prompt_for_combination(combo, modes), "Skopiowano kombinacje")

    def _copy_combination_full(self, combo: Combination) -> None:
        modes = self._catalog.modes_for_ids(list(combo.mode_ids))
        self._copy_text(prompt_for_combination(combo, modes), "Skopiowano prompt aktywacyjny")

    @staticmethod
    def _set_text(widget: scrolledtext.ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    WyborTrybuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
