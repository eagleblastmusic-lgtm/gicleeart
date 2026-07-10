"""Wybór Trybu — panel krótkich komend aktywacyjnych (pakiet wiedzy v38)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .data_loader import (
    Combination,
    WorkMode,
    WorkModeCatalog,
    all_categories,
    filter_modes,
    load_catalog,
    resolve_modes_with_dependencies,
)
from .knowledge_sources import check_knowledge_sources
from .prompt_builder import (
    VEO_MODE_ID,
    command_for_mode,
    full_prompt_for_modes,
    prompt_for_combination,
    short_prompt_for_combination,
    short_prompt_for_modes,
)

APP_TITLE = "Wybór Trybu"
_HINT = (
    "To są krótkie komendy aktywacyjne zgodne z pakietem wiedzy v38. "
    "Pełne prompty znajdziesz w Bazie Promptów."
)

_VEO_PROFILE_BUTTONS: tuple[tuple[str, str, bool], ...] = (
    ("veo_premium", "Kopiuj „Veo premium”", True),
    ("veo_krotko", "Kopiuj „Veo krótko”", True),
    ("veo_popraw", "Kopiuj „Veo popraw”", True),
    ("tryb_flow", "Flow", False),
    ("tryb_image_prompt", "Image Prompt", False),
    ("tryb_image_video_prompt", "Image-Video Prompt", False),
)


class WyborTrybuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 1020, 820)
        self.root.minsize(780, 580)

        try:
            self._catalog = load_catalog()
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror(APP_TITLE, f"Nie udało się wczytać danych:\n{exc}", parent=root)
            raise

        self._source_check = check_knowledge_sources(self._catalog)
        self._selected_ids: set[str] = set()
        self._profile_map: dict[str, str] = {}
        self._active_mode_id: str | None = None
        self._active_family: str = "analyst"
        self._mode_vars: dict[str, tk.BooleanVar] = {}
        self._mode_row_frames: dict[str, tk.Frame] = {}

        self._search_var = tk.StringVar()
        self._category_var = tk.StringVar(value="Wszystkie")
        self._selected_summary_var = tk.StringVar(value="Wybrane: (brak)")
        self._status_var = tk.StringVar(value="")
        self._source_status_var = tk.StringVar(value=self._source_status_text())

        self._modes_canvas: tk.Canvas | None = None
        self._combos_canvas: tk.Canvas | None = None
        self._veo_btn_frame: ttk.Frame | None = None

        self._build_ui()
        self._render_mode_list()
        self._render_combinations()

    def _source_status_text(self) -> str:
        sc = self._source_check
        if sc.status == "current":
            return f"Źródła v38: {sc.message}"
        if sc.status == "unavailable":
            return f"Źródła v38: {sc.message}"
        parts = [sc.message]
        if sc.missing_files:
            parts.append(f"Brak: {', '.join(sc.missing_files[:3])}" + (
                f" (+{len(sc.missing_files) - 3})" if len(sc.missing_files) > 3 else ""
            ))
        if sc.unknown_files:
            parts.append(f"Nowe: {', '.join(sc.unknown_files[:3])}" + (
                f" (+{len(sc.unknown_files) - 3})" if len(sc.unknown_files) > 3 else ""
            ))
        return " | ".join(parts)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Wyczyść wybór", command=self._clear_selection).pack(side="right")

        sub = ttk.Label(
            self.root,
            text="Katalog zgodny z pakietem wiedzy v38",
            padding=(12, 0, 12, 2),
            foreground="#3949ab",
            font=("Segoe UI", 10, "bold"),
        )
        sub.pack(fill="x")

        ttk.Label(
            self.root,
            textvariable=self._source_status_var,
            padding=(12, 0, 12, 4),
            foreground="#555",
            wraplength=960,
        ).pack(fill="x")

        ttk.Label(
            self.root,
            text=_HINT,
            padding=(12, 2, 12, 4),
            foreground="#666",
            wraplength=960,
        ).pack(fill="x")

        self._build_foundations_section()

        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self._analyst_tab = ttk.Frame(self._notebook)
        self._shopify_tab = ttk.Frame(self._notebook)
        self._combos_tab = ttk.Frame(self._notebook)
        self._extra_tab = ttk.Frame(self._notebook)

        self._notebook.add(self._analyst_tab, text="Analityczne")
        self._notebook.add(self._shopify_tab, text="Shopify")
        self._notebook.add(self._combos_tab, text="Kombinacje")
        self._notebook.add(self._extra_tab, text="Dodatkowe")

        self._analyst_body = self._build_modes_tab_body(self._analyst_tab, family="analyst")
        self._shopify_body = self._build_modes_tab_body(self._shopify_tab, family="shopify")
        self._extra_body = self._build_modes_tab_body(self._extra_tab, family="extra")
        self._build_combos_tab()

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_generator_panel()

        ttk.Label(
            self.root, textvariable=self._status_var, padding=(12, 0, 12, 8), foreground="#444"
        ).pack(fill="x")

        self._search_var.trace_add("write", lambda *_: self._render_mode_list())
        self._category_var.trace_add("write", lambda *_: self._render_mode_list())

    def _build_foundations_section(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Stały fundament", padding=(10, 6))
        frame.pack(fill="x", padx=12, pady=(0, 4))
        for foundation in sorted(self._catalog.foundations, key=lambda f: f.order):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=foundation.name, font=("Segoe UI", 9, "bold")).pack(side="left")
            ttk.Label(
                row,
                text=f"  —  {foundation.source_file}",
                foreground="#555",
                font=("Consolas", 9),
            ).pack(side="left")
            if "GicleeApp Architect" in foundation.aliases:
                ttk.Label(
                    row,
                    text="  (alias: GicleeApp Architect)",
                    foreground="#777",
                    font=("Segoe UI", 8),
                ).pack(side="left")

    def _build_modes_tab_body(self, parent: ttk.Frame, *, family: str) -> dict[str, object]:
        body = ttk.Panedwindow(parent, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(body, padding=(0, 0, 6, 0))
        body.add(left, weight=2)

        filters = ttk.Frame(left)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Szukaj:").pack(side="left")
        ttk.Entry(filters, textvariable=self._search_var, width=24).pack(side="left", padx=(6, 12))
        ttk.Label(filters, text="Kategoria:").pack(side="left")
        fam_key = None if family == "extra" else family
        cat_box = ttk.Combobox(
            filters,
            textvariable=self._category_var,
            values=all_categories(self._catalog, family=fam_key),
            state="readonly",
            width=16,
        )
        cat_box.pack(side="left", padx=(6, 0))

        list_wrap = ttk.LabelFrame(left, text="Tryby pracy", padding=6)
        list_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_wrap, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        list_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def _on_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())

        list_frame.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))
        bind_mousewheel_to_canvas(canvas, list_frame)

        right = ttk.LabelFrame(body, text="Szczegóły trybu", padding=10)
        body.add(right, weight=3)

        detail_title = ttk.Label(right, text="Wybierz tryb z listy", font=("Segoe UI", 13, "bold"))
        detail_title.pack(anchor="w")

        detail_category = ttk.Label(right, text="", foreground="#3949ab")
        detail_category.pack(anchor="w", pady=(2, 4))

        detail_source = ttk.Label(right, text="", foreground="#666", font=("Consolas", 9))
        detail_source.pack(anchor="w", pady=(0, 6))

        detail_text = scrolledtext.ScrolledText(
            right, height=14, wrap="word", font=("Segoe UI", 10), state="disabled"
        )
        detail_text.pack(fill="both", expand=True, pady=(0, 6))

        cmd_frame = ttk.LabelFrame(right, text="Komendy aktywujące", padding=6)
        cmd_frame.pack(fill="x", pady=(0, 6))
        detail_command = scrolledtext.ScrolledText(
            cmd_frame, height=4, wrap="word", font=("Consolas", 10), state="disabled"
        )
        detail_command.pack(fill="x")

        veo_frame = ttk.Frame(right)
        veo_frame.pack(fill="x", pady=(0, 6))

        btn_row = ttk.Frame(right)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Kopiuj komendę", command=self._copy_active_command).pack(side="left")
        ttk.Button(
            btn_row, text="Kopiuj domyślną komendę", command=self._copy_active_default_command
        ).pack(side="left", padx=(8, 0))

        return {
            "family": family,
            "list_frame": list_frame,
            "canvas": canvas,
            "detail_title": detail_title,
            "detail_category": detail_category,
            "detail_source": detail_source,
            "detail_text": detail_text,
            "detail_command": detail_command,
            "veo_frame": veo_frame,
        }

    def _build_combos_tab(self) -> None:
        wrap = ttk.Frame(self._combos_tab, padding=8)
        wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrap, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        combos_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=combos_frame, anchor="nw")

        def _on_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=canvas.winfo_width())

        combos_frame.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))
        bind_mousewheel_to_canvas(canvas, combos_frame)

        self._combos_canvas = canvas
        self._combos_frame = combos_frame

    def _build_generator_panel(self) -> None:
        panel = ttk.LabelFrame(self.root, text="Generator wybranych trybów", padding=10)
        panel.pack(fill="both", expand=False, padx=12, pady=(0, 4))

        ttk.Label(panel, textvariable=self._selected_summary_var, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(0, 6)
        )

        self._prompt_preview = scrolledtext.ScrolledText(
            panel, height=8, wrap="word", font=("Consolas", 10), state="disabled"
        )
        self._prompt_preview.pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(panel)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Kopiuj prompt aktywacyjny", command=self._copy_full_prompt).pack(
            side="left"
        )
        ttk.Button(btn_row, text="Kopiuj krótki", command=self._copy_short_prompt).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(btn_row, text="Wyczyść wybór", command=self._clear_selection).pack(
            side="left", padx=(8, 0)
        )

    def _on_tab_changed(self, _event: tk.Event | None = None) -> None:
        tab = self._notebook.index(self._notebook.select())
        family_map = {0: "analyst", 1: "shopify", 3: "extra"}
        if tab in family_map:
            self._active_family = family_map[tab]
            self._category_var.set("Wszystkie")
            self._render_mode_list()

    def _active_tab_body(self) -> dict[str, object]:
        if self._active_family == "shopify":
            return self._shopify_body
        if self._active_family == "extra":
            return self._extra_body
        return self._analyst_body

    def _families_for_tab(self, family: str) -> tuple[str, ...]:
        if family == "extra":
            return ("workflow", "legacy")
        return (family,)

    def _render_mode_list(self) -> None:
        body = self._active_tab_body()
        list_frame: ttk.Frame = body["list_frame"]  # type: ignore[assignment]

        for child in list_frame.winfo_children():
            child.destroy()
        self._mode_vars.clear()
        self._mode_row_frames.clear()

        family = body["family"]  # type: ignore[assignment]
        families = self._families_for_tab(str(family))
        modes: list[WorkMode] = []
        for fam in families:
            modes.extend(
                filter_modes(
                    self._catalog,
                    query=self._search_var.get(),
                    category=self._category_var.get(),
                    family=fam,
                )
            )
        modes.sort(key=lambda m: m.order)

        if not modes:
            ttk.Label(
                list_frame,
                text="Brak trybów dla tego filtra.",
                foreground="#777",
            ).pack(anchor="w", padx=4, pady=8)
            return

        for mode in modes:
            self._add_mode_row(list_frame, mode)

        if self._active_mode_id and self._active_mode_id not in self._mode_row_frames:
            self._active_mode_id = modes[0].id
            self._show_mode_details(modes[0])
        elif self._active_mode_id is None and modes:
            self._active_mode_id = modes[0].id
            self._show_mode_details(modes[0])

        self._highlight_active_row()

    def _add_mode_row(self, parent: ttk.Frame, mode: WorkMode) -> None:
        row = tk.Frame(parent, padx=4, pady=3)
        row.pack(fill="x")

        var = tk.BooleanVar(value=mode.id in self._selected_ids)
        self._mode_vars[mode.id] = var

        def _toggle() -> None:
            if var.get():
                self._selected_ids.add(mode.id)
            else:
                self._selected_ids.discard(mode.id)
                self._profile_map.pop(mode.id, None)
            self._refresh_prompt_preview()

        ttk.Checkbutton(row, variable=var, command=_toggle).pack(side="left")

        num = ttk.Label(row, text=f"{mode.order:>2}.", width=3, font=("Segoe UI", 10, "bold"))
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
        body = self._active_tab_body()
        detail_title: ttk.Label = body["detail_title"]  # type: ignore[assignment]
        detail_category: ttk.Label = body["detail_category"]  # type: ignore[assignment]
        detail_source: ttk.Label = body["detail_source"]  # type: ignore[assignment]
        detail_text: scrolledtext.ScrolledText = body["detail_text"]  # type: ignore[assignment]
        detail_command: scrolledtext.ScrolledText = body["detail_command"]  # type: ignore[assignment]
        veo_frame: ttk.Frame = body["veo_frame"]  # type: ignore[assignment]

        detail_title.configure(text=f"{mode.order}. {mode.name}")
        detail_category.configure(text=f"Rodzina: {mode.family}  |  Kategoria: {mode.category}")
        detail_source.configure(
            text=f"Plik źródłowy: {mode.source_file or '(brak — tryb legacy)'}"
        )

        requires_text = ""
        if mode.requires:
            names = []
            for req_id in mode.requires:
                req_mode = self._catalog.mode(req_id)
                names.append(req_mode.short_label if req_mode else req_id)
            requires_text = f"\n\nZależności:\n" + ", ".join(names)

        distinction = ""
        if mode.distinction_note:
            distinction = f"\n\nNie myl z:\n{mode.distinction_note}"

        commands_block = "\n".join(
            f"• {p.label}: {p.command}" + (f"\n  {p.description}" if p.description else "")
            for p in mode.activation_profiles
        )

        body_text = (
            f"Cel:\n{mode.purpose}\n\n"
            f"Kiedy używać:\n{mode.when_to_use}\n\n"
            f"Zakres:\n{mode.focus}"
            f"{requires_text}"
            f"{distinction}"
        )
        self._set_text(detail_text, body_text)
        self._set_text(detail_command, commands_block)

        for child in veo_frame.winfo_children():
            child.destroy()
        if mode.id == VEO_MODE_ID:
            main_row = ttk.Frame(veo_frame)
            main_row.pack(fill="x", pady=(0, 4))
            sub_row = ttk.Frame(veo_frame)
            sub_row.pack(fill="x")
            for profile_id, label, is_main in _VEO_PROFILE_BUTTONS:
                parent_row = main_row if is_main else sub_row
                ttk.Button(
                    parent_row,
                    text=label,
                    command=lambda pid=profile_id, m=mode: self._copy_veo_profile(m, pid),
                ).pack(side="left", padx=(0, 6) if is_main else (0, 4))

    def _render_combinations(self) -> None:
        for child in self._combos_frame.winfo_children():
            child.destroy()

        for combo in self._catalog.combinations:
            self._add_combo_card(combo)

    def _add_combo_card(self, combo: Combination) -> None:
        card = ttk.LabelFrame(self._combos_frame, text=combo.name, padding=10)
        card.pack(fill="x", pady=(0, 10), padx=4)

        ttk.Label(card, text=f"Najlepsza do: {combo.best_for}", wraplength=860).pack(anchor="w")
        ttk.Label(card, text=f"Co dostajesz: {combo.delivers}", wraplength=860).pack(
            anchor="w", pady=(4, 0)
        )
        ttk.Label(card, text=f"Przykład użycia: {combo.usage_example}", wraplength=860).pack(
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
            text="Kopiuj krótki",
            command=lambda c=combo: self._copy_combination_short(c),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            btn_row,
            text="Kopiuj prompt aktywacyjny",
            command=lambda c=combo: self._copy_combination_full(c),
        ).pack(side="left", padx=(8, 0))

    def _apply_combination(self, combo: Combination) -> None:
        self._selected_ids = set(combo.mode_ids)
        self._profile_map.clear()
        for mode_id, var in self._mode_vars.items():
            var.set(mode_id in self._selected_ids)
        first_mode = self._catalog.mode(combo.mode_ids[0]) if combo.mode_ids else None
        if first_mode is not None:
            self._active_family = first_mode.family if first_mode.family != "legacy" else "extra"
            if first_mode.family == "workflow":
                self._active_family = "extra"
            tab_map = {"analyst": 0, "shopify": 1, "extra": 3}
            self._notebook.select(tab_map.get(self._active_family, 0))
        self._render_mode_list()
        self._refresh_prompt_preview()
        if combo.mode_ids:
            first = self._catalog.mode(combo.mode_ids[0])
            if first is not None:
                self._select_mode(first)
        self._status_var.set(f"Zaznaczono kombinację: {combo.name}")

    def _refresh_prompt_preview(self) -> None:
        ids = list(self._selected_ids)
        if ids:
            modes, _ = resolve_modes_with_dependencies(
                self._catalog, ids, profile_map=self._profile_map
            )
            labels = " + ".join(m.short_label for m in modes)
            self._selected_summary_var.set(f"Wybrane: {labels}")
            self._set_text(
                self._prompt_preview,
                full_prompt_for_modes(self._catalog, ids, profile_map=self._profile_map),
            )
        else:
            self._selected_summary_var.set("Wybrane: (brak)")
            self._set_text(self._prompt_preview, "")

    def _clear_selection(self) -> None:
        self._selected_ids.clear()
        self._profile_map.clear()
        for var in self._mode_vars.values():
            var.set(False)
        self._refresh_prompt_preview()
        self._status_var.set("Wyczyszczono wybór")

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
        profile_id = self._profile_map.get(mode.id)
        self._copy_text(command_for_mode(mode, profile_id), "Skopiowano komendę")

    def _copy_active_default_command(self) -> None:
        if not self._active_mode_id:
            return
        mode = self._catalog.mode(self._active_mode_id)
        if mode is None:
            return
        self._copy_text(command_for_mode(mode), "Skopiowano komendę")

    def _copy_veo_profile(self, mode: WorkMode, profile_id: str) -> None:
        cmd = command_for_mode(mode, profile_id)
        self._copy_text(cmd, f"Skopiowano: {cmd}")

    def _copy_full_prompt(self) -> None:
        self._copy_text(
            full_prompt_for_modes(
                self._catalog, list(self._selected_ids), profile_map=self._profile_map
            ),
            "Skopiowano prompt aktywacyjny",
        )

    def _copy_short_prompt(self) -> None:
        self._copy_text(
            short_prompt_for_modes(
                self._catalog, list(self._selected_ids), profile_map=self._profile_map
            ),
            "Skopiowano krótki prompt",
        )

    def _copy_combination_short(self, combo: Combination) -> None:
        self._copy_text(
            short_prompt_for_combination(self._catalog, combo),
            "Skopiowano kombinację",
        )

    def _copy_combination_full(self, combo: Combination) -> None:
        self._copy_text(
            prompt_for_combination(self._catalog, combo),
            "Skopiowano prompt aktywacyjny",
        )

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
