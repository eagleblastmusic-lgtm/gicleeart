"""Wybór Trybu — premium panel komend aktywacyjnych pakietu wiedzy."""

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

# Gallery-paper palette: spokojna, czytelna i niezależna od systemowego motywu Windows.
BG = "#F4F1EB"
CARD = "#FFFFFF"
CARD_SOFT = "#F8F6F1"
BORDER = "#DED9CF"
TEXT = "#202126"
MUTED = "#706C65"
ACCENT = "#303A5B"
ACCENT_HOVER = "#252E4A"
ACCENT_SOFT = "#EEF0F6"
GOLD = "#A5864F"
SUCCESS = "#2D755D"
SUCCESS_SOFT = "#E7F2ED"
WARNING = "#A46720"
WARNING_SOFT = "#F8EDDE"
NEUTRAL = "#747A83"
CODE_BG = "#171B26"
CODE_FG = "#EEF0F5"

_FAMILY_LABELS = {
    "analyst": "ANALIZA",
    "shopify": "SHOPIFY",
    "workflow": "WORKFLOW",
    "legacy": "LEGACY",
}

_VEO_PROFILE_LABELS = {
    "veo_premium": "Premium",
    "veo_krotko": "Krótko",
    "veo_popraw": "Popraw",
    "tryb_flow": "Flow",
    "tryb_image_prompt": "Image Prompt",
    "tryb_image_video_prompt": "Image → Video",
}


class WyborTrybuApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1120, max(860, screen_width - 80))
        window_height = min(820, max(620, screen_height - 100))
        position_toplevel_screen_center(
            self.root,
            window_width,
            window_height,
        )
        self.root.minsize(860, 620)

        try:
            self._catalog = load_catalog()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Nie udało się wczytać danych:\n{exc}",
                parent=root,
            )
            raise
        self._pack_label = self._catalog.knowledge_pack or "aktualny"

        try:
            self._source_check = check_knowledge_sources(self._catalog)
        except OSError as exc:
            # Katalog JSON pozostaje w pełni funkcjonalny także przy błędzie dysku.
            self._source_check = None
            self._source_check_error = str(exc)
        else:
            self._source_check_error = ""

        self._selected_ids: set[str] = set()
        self._profile_map: dict[str, str] = {}
        self._active_mode_id: str | None = None
        self._active_family = "analyst"
        self._preview_visible = False

        self._mode_vars: dict[str, tk.BooleanVar] = {}
        self._mode_rows: dict[str, dict[str, tk.Widget]] = {}
        self._search_entries: dict[str, ttk.Entry] = {}

        self._search_var = tk.StringVar()
        self._category_var = tk.StringVar(value="Wszystkie")
        self._status_var = tk.StringVar(value="Gotowe")
        self._selected_count_var = tk.StringVar(value="Nie wybrano trybów")

        self._configure_styles()
        self._build_ui()
        self._render_mode_list()
        self._render_combinations()
        self._refresh_prompt_preview()

        self.root.bind("<Control-f>", self._focus_search)
        self.root.bind("<Escape>", self._handle_escape)

    # ------------------------------------------------------------------
    # Wygląd i główny shell

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 9))
        style.configure("WT.TFrame", background=BG)
        style.configure("WT.Card.TFrame", background=CARD)
        style.configure("WT.TLabel", background=BG, foreground=TEXT)
        style.configure("WT.Card.TLabel", background=CARD, foreground=TEXT)
        style.configure(
            "WT.TNotebook",
            background=BG,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "WT.TNotebook.Tab",
            background="#E8E4DC",
            foreground=MUTED,
            borderwidth=0,
            padding=(16, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "WT.TNotebook.Tab",
            background=[("selected", CARD), ("active", "#F0EDE7")],
            foreground=[("selected", ACCENT), ("active", TEXT)],
        )
        style.configure(
            "WT.Primary.TButton",
            background=ACCENT,
            foreground="white",
            borderwidth=0,
            padding=(14, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "WT.Primary.TButton",
            background=[("active", ACCENT_HOVER), ("disabled", "#B8BAC1")],
            foreground=[("disabled", "#ECECEF")],
        )
        style.configure(
            "WT.Secondary.TButton",
            background="#ECE8E0",
            foreground=TEXT,
            bordercolor=BORDER,
            borderwidth=1,
            padding=(12, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "WT.Secondary.TButton",
            background=[("active", "#E1DDD5"), ("disabled", "#F0EEE9")],
            foreground=[("disabled", "#9A9894")],
        )
        style.configure(
            "WT.Ghost.TButton",
            background=BG,
            foreground=ACCENT,
            borderwidth=0,
            padding=(8, 6),
            font=("Segoe UI", 9, "bold"),
        )
        style.map("WT.Ghost.TButton", background=[("active", "#E9E5DD")])
        style.configure(
            "WT.Small.TButton",
            background="#ECE8E0",
            foreground=TEXT,
            borderwidth=0,
            padding=(8, 5),
            font=("Segoe UI", 8),
        )
        style.map("WT.Small.TButton", background=[("active", "#DFDBD2")])
        style.configure(
            "WT.TEntry",
            fieldbackground=CARD,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(7, 6),
        )
        style.map("WT.TEntry", bordercolor=[("focus", ACCENT)])
        style.configure(
            "WT.TCombobox",
            fieldbackground=CARD,
            background=CARD,
            foreground=TEXT,
            arrowcolor=ACCENT,
            bordercolor=BORDER,
            padding=(7, 5),
        )
        style.configure(
            "WT.Vertical.TScrollbar",
            background="#D8D3CA",
            troughcolor=CARD_SOFT,
            borderwidth=0,
            arrowcolor=MUTED,
        )

    def _build_ui(self) -> None:
        self._build_header()
        self._build_foundations_bar()

        # Packowany przed notebookiem jako stały dół — nie zapada się przy 820 px.
        self._build_generator_panel()
        self._build_notebook()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=BG, padx=18, pady=14)
        header.pack(fill="x")

        copy = tk.Frame(header, bg=BG)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            copy,
            text=APP_TITLE,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            copy,
            text=(
                "Dobierz tryby i skopiuj aktywator zgodny z pakietem wiedzy "
                f"{self._pack_label}."
            ),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        actions = tk.Frame(header, bg=BG)
        actions.pack(side="right")
        status_text, status_bg = self._source_badge()
        self._source_badge_label = tk.Label(
            actions,
            text=status_text,
            bg=status_bg,
            fg="white",
            padx=12,
            pady=7,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        self._source_badge_label.pack(side="left", padx=(0, 10))
        self._source_badge_label.bind("<Button-1>", self._show_source_details)
        ttk.Button(
            actions,
            text="Wyczyść",
            style="WT.Secondary.TButton",
            command=self._clear_selection,
        ).pack(side="left")

    def _source_badge(self) -> tuple[str, str]:
        if self._source_check is None:
            return "●  Źródła niedostępne", NEUTRAL
        if self._source_check.status == "current":
            return f"●  Źródła {self._pack_label} zgodne", SUCCESS
        if self._source_check.status == "drift":
            return "●  Wykryto drift źródeł", WARNING
        return f"●  Katalog lokalny {self._pack_label}", NEUTRAL

    def _show_source_details(self, _event: tk.Event | None = None) -> None:
        if self._source_check is None:
            text = (
                "Nie udało się sprawdzić folderu plików startowych.\n\n"
                f"{self._source_check_error}\n\n"
                "Wbudowany katalog JSON nadal działa."
            )
        else:
            result = self._source_check
            chunks = [result.message]
            if result.missing_files:
                chunks.append("Brakujące:\n- " + "\n- ".join(result.missing_files))
            if result.unknown_files:
                chunks.append("Nieznane / nowe:\n- " + "\n- ".join(result.unknown_files))
            chunks.append(f"Oczekiwane pliki: {len(result.expected_files)}")
            text = "\n\n".join(chunks)
        messagebox.showinfo(
            f"Źródła pakietu {self._pack_label}",
            text,
            parent=self.root,
        )

    def _build_foundations_bar(self) -> None:
        shell = tk.Frame(self.root, bg=BG, padx=18)
        shell.pack(fill="x", pady=(0, 8))

        bar = tk.Frame(
            shell,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        bar.pack(fill="x")

        tk.Label(
            bar,
            text="STAŁY FUNDAMENT",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 10))

        chip_names = {
            "current_app_state": "Checkpoint",
            "analyst_base": "Analyst Base",
        }
        for foundation in sorted(self._catalog.foundations, key=lambda item: item.order):
            tk.Label(
                bar,
                text=chip_names.get(foundation.id, foundation.name),
                bg=ACCENT_SOFT,
                fg=ACCENT,
                padx=9,
                pady=4,
                font=("Segoe UI", 8, "bold"),
            ).pack(side="left", padx=(0, 6))

        ttk.Button(
            bar,
            text="Szczegóły",
            style="WT.Ghost.TButton",
            command=self._show_foundation_details,
        ).pack(side="right")

    def _show_foundation_details(self) -> None:
        parts: list[str] = []
        for foundation in sorted(self._catalog.foundations, key=lambda item: item.order):
            aliases = ""
            if foundation.aliases:
                aliases = "\nAliasy: " + ", ".join(foundation.aliases)
            parts.append(
                f"{foundation.name}\n{foundation.source_file}\n"
                f"{foundation.purpose}{aliases}"
            )
        messagebox.showinfo(
            "Stały fundament",
            "\n\n".join(parts),
            parent=self.root,
        )

    def _build_notebook(self) -> None:
        self._notebook = ttk.Notebook(self.root, style="WT.TNotebook")
        self._notebook.pack(fill="both", expand=True, padx=18, pady=(0, 8))

        self._analyst_tab = tk.Frame(self._notebook, bg=BG)
        self._shopify_tab = tk.Frame(self._notebook, bg=BG)
        self._combos_tab = tk.Frame(self._notebook, bg=BG)
        self._extra_tab = tk.Frame(self._notebook, bg=BG)

        self._notebook.add(
            self._analyst_tab,
            text=f"Analityczne  ·  {len(self._catalog.modes_by_family('analyst'))}",
        )
        self._notebook.add(
            self._shopify_tab,
            text=f"Shopify  ·  {len(self._catalog.modes_by_family('shopify'))}",
        )
        self._notebook.add(
            self._combos_tab,
            text=f"Kombinacje  ·  {len(self._catalog.combinations)}",
        )
        extra_count = (
            len(self._catalog.modes_by_family("workflow"))
            + len(self._catalog.modes_by_family("legacy"))
        )
        self._notebook.add(self._extra_tab, text=f"Dodatkowe  ·  {extra_count}")

        self._analyst_body = self._build_modes_tab_body(
            self._analyst_tab,
            family="analyst",
        )
        self._shopify_body = self._build_modes_tab_body(
            self._shopify_tab,
            family="shopify",
        )
        self._extra_body = self._build_modes_tab_body(
            self._extra_tab,
            family="extra",
        )
        self._build_combos_tab()
        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ------------------------------------------------------------------
    # Zakładki trybów

    def _build_modes_tab_body(
        self,
        parent: tk.Frame,
        *,
        family: str,
    ) -> dict[str, object]:
        pane = tk.PanedWindow(
            parent,
            orient=tk.HORIZONTAL,
            bg=BG,
            bd=0,
            relief="flat",
            sashwidth=8,
            showhandle=False,
        )
        pane.pack(fill="both", expand=True, pady=(8, 0))

        left = tk.Frame(
            pane,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=12,
        )
        right = tk.Frame(
            pane,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        pane.add(left, minsize=350, width=380, stretch="never")
        pane.add(right, minsize=480, stretch="always")

        filters = tk.Frame(left, bg=CARD)
        filters.pack(fill="x", pady=(0, 10))
        tk.Label(
            filters,
            text="Szukaj",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            filters,
            text="Kategoria",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))

        entry = ttk.Entry(
            filters,
            textvariable=self._search_var,
            style="WT.TEntry",
        )
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(
            filters,
            text="×",
            style="WT.Small.TButton",
            command=lambda: self._search_var.set(""),
        ).grid(row=1, column=1, padx=(5, 0), pady=(4, 0))

        categories = self._categories_for_tab(family)
        category_box = ttk.Combobox(
            filters,
            textvariable=self._category_var,
            values=categories,
            state="readonly",
            style="WT.TCombobox",
            width=16,
        )
        category_box.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(10, 0),
            pady=(4, 0),
        )
        filters.grid_columnconfigure(0, weight=1)
        filters.grid_columnconfigure(2, weight=0)
        self._search_entries[family] = entry

        list_head = tk.Frame(left, bg=CARD)
        list_head.pack(fill="x", pady=(2, 7))
        tk.Label(
            list_head,
            text="TRYBY",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        mode_count_var = tk.StringVar(value="")
        tk.Label(
            list_head,
            textvariable=mode_count_var,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="right")

        list_wrap = tk.Frame(left, bg=CARD)
        list_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            list_wrap,
            bg=CARD,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            list_wrap,
            orient="vertical",
            command=canvas.yview,
            style="WT.Vertical.TScrollbar",
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        list_frame = tk.Frame(canvas, bg=CARD)
        canvas_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def _sync_list_size(_event: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=max(canvas.winfo_width(), 1))

        list_frame.bind("<Configure>", _sync_list_size)
        canvas.bind("<Configure>", _sync_list_size)
        bind_mousewheel_to_canvas(canvas, list_frame)

        detail_head = tk.Frame(right, bg=CARD)
        detail_head.pack(fill="x")
        detail_title = tk.Label(
            detail_head,
            text="Wybierz tryb",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 17, "bold"),
            anchor="w",
        )
        detail_title.pack(anchor="w")

        badges_frame = tk.Frame(detail_head, bg=CARD)
        badges_frame.pack(fill="x", pady=(7, 5))
        detail_source = tk.Label(
            detail_head,
            text="",
            bg=CARD,
            fg=MUTED,
            font=("Consolas", 8),
            anchor="w",
        )
        detail_source.pack(fill="x", pady=(0, 8))

        separator = tk.Frame(right, bg=BORDER, height=1)
        separator.pack(fill="x", pady=(0, 5))

        detail_text = scrolledtext.ScrolledText(
            right,
            height=12,
            wrap="word",
            font=("Segoe UI", 10),
            state="disabled",
            relief="flat",
            bd=0,
            highlightthickness=0,
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            padx=2,
            pady=5,
        )
        detail_text.pack(fill="both", expand=True)
        detail_text.tag_configure(
            "heading",
            foreground=ACCENT,
            font=("Segoe UI", 9, "bold"),
            spacing1=9,
            spacing3=3,
        )
        detail_text.tag_configure(
            "body",
            foreground=TEXT,
            font=("Segoe UI", 10),
            spacing3=5,
        )
        detail_text.tag_configure(
            "warning",
            foreground=WARNING,
            font=("Segoe UI", 10),
            spacing3=5,
        )

        profiles_shell = tk.Frame(
            right,
            bg=CARD_SOFT,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=10,
            pady=9,
        )
        profiles_shell.pack(fill="x", pady=(9, 0))
        profile_heading = tk.Frame(profiles_shell, bg=CARD_SOFT)
        profile_heading.pack(fill="x", pady=(0, 7))
        tk.Label(
            profile_heading,
            text="KOMENDA AKTYWUJĄCA",
            bg=CARD_SOFT,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        tk.Label(
            profile_heading,
            text="Kliknij profil, aby wybrać go i skopiować",
            bg=CARD_SOFT,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="right")

        profiles_frame = tk.Frame(profiles_shell, bg=CARD_SOFT)
        profiles_frame.pack(fill="x")

        actions = tk.Frame(right, bg=CARD)
        actions.pack(fill="x", pady=(9, 0))
        copy_command_btn = ttk.Button(
            actions,
            text="Kopiuj aktywną komendę",
            style="WT.Primary.TButton",
            command=self._copy_active_command,
        )
        copy_command_btn.pack(side="left")

        return {
            "family": family,
            "list_frame": list_frame,
            "canvas": canvas,
            "mode_count_var": mode_count_var,
            "category_box": category_box,
            "detail_title": detail_title,
            "badges_frame": badges_frame,
            "detail_source": detail_source,
            "detail_text": detail_text,
            "profiles_frame": profiles_frame,
            "copy_command_btn": copy_command_btn,
        }

    def _categories_for_tab(self, family: str) -> list[str]:
        if family != "extra":
            return all_categories(self._catalog, family=family)
        categories = {
            mode.category
            for mode in self._catalog.modes
            if mode.selectable and mode.family in {"workflow", "legacy"}
        }
        return ["Wszystkie", *sorted(categories)]

    def _active_tab_body(self) -> dict[str, object]:
        if self._active_family == "shopify":
            return self._shopify_body
        if self._active_family == "extra":
            return self._extra_body
        return self._analyst_body

    @staticmethod
    def _families_for_tab(family: str) -> tuple[str, ...]:
        if family == "extra":
            return ("workflow", "legacy")
        return (family,)

    def _on_tab_changed(self, _event: tk.Event | None = None) -> None:
        tab = self._notebook.index(self._notebook.select())
        family_map = {0: "analyst", 1: "shopify", 3: "extra"}
        if tab not in family_map:
            return
        self._active_family = family_map[tab]
        self._category_var.set("Wszystkie")
        self._render_mode_list()

    def _render_mode_list(self) -> None:
        body = self._active_tab_body()
        list_frame = body["list_frame"]
        assert isinstance(list_frame, tk.Frame)

        for child in list_frame.winfo_children():
            child.destroy()
        self._mode_vars.clear()
        self._mode_rows.clear()

        family = str(body["family"])
        modes: list[WorkMode] = []
        for item_family in self._families_for_tab(family):
            modes.extend(
                filter_modes(
                    self._catalog,
                    query=self._search_var.get(),
                    category=self._category_var.get(),
                    family=item_family,
                )
            )
        modes.sort(key=lambda item: item.order)

        count_var = body["mode_count_var"]
        assert isinstance(count_var, tk.StringVar)
        count_var.set(f"{len(modes)} wyników")

        if not modes:
            tk.Label(
                list_frame,
                text="Brak trybów dla wybranego filtra.",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 10),
                pady=24,
            ).pack(fill="x")
            self._show_empty_details()
            return

        visible_ids = {mode.id for mode in modes}
        if self._active_mode_id not in visible_ids:
            self._active_mode_id = modes[0].id

        for mode in modes:
            self._add_mode_row(list_frame, mode)

        active = self._catalog.mode(self._active_mode_id or "")
        if active is not None:
            self._show_mode_details(active)
        self._refresh_mode_row_styles()

    def _add_mode_row(self, parent: tk.Frame, mode: WorkMode) -> None:
        outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="x", pady=(0, 7), padx=(0, 4))
        inner = tk.Frame(outer, bg=CARD, padx=9, pady=8)
        inner.pack(fill="both", expand=True)

        var = tk.BooleanVar(value=mode.id in self._selected_ids)
        self._mode_vars[mode.id] = var

        def _toggle() -> None:
            if var.get():
                self._selected_ids.add(mode.id)
                self._active_mode_id = mode.id
                self._show_mode_details(mode)
            else:
                self._selected_ids.discard(mode.id)
                self._profile_map.pop(mode.id, None)
            self._refresh_prompt_preview()
            self._refresh_mode_row_styles()

        check = tk.Checkbutton(
            inner,
            variable=var,
            command=_toggle,
            bg=CARD,
            activebackground=CARD,
            selectcolor=ACCENT_SOFT,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        check.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 7), pady=(1, 0))

        name_label = tk.Label(
            inner,
            text=mode.name,
            bg=CARD,
            fg=ACCENT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            cursor="hand2",
        )
        name_label.grid(row=0, column=1, sticky="ew")

        badge = tk.Label(
            inner,
            text=_FAMILY_LABELS.get(mode.family, mode.category.upper()),
            bg=mode.category_color,
            fg="white",
            padx=7,
            pady=2,
            font=("Segoe UI", 7, "bold"),
        )
        badge.grid(row=0, column=2, sticky="e", padx=(7, 0))

        purpose_label = tk.Label(
            inner,
            text=mode.purpose,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=265,
            cursor="hand2",
        )
        purpose_label.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(4, 0))
        inner.grid_columnconfigure(1, weight=1)

        def _select(_event: tk.Event | None = None) -> None:
            self._active_mode_id = mode.id
            self._show_mode_details(mode)
            self._refresh_mode_row_styles()

        for widget in (outer, inner, name_label, purpose_label):
            widget.bind("<Button-1>", _select)

        self._mode_rows[mode.id] = {
            "outer": outer,
            "inner": inner,
            "check": check,
            "name": name_label,
            "purpose": purpose_label,
        }

    def _refresh_mode_row_styles(self) -> None:
        for mode_id, row in self._mode_rows.items():
            selected = mode_id in self._selected_ids
            active = mode_id == self._active_mode_id
            bg = ACCENT_SOFT if selected else CARD
            border = ACCENT if active else BORDER

            outer = row["outer"]
            inner = row["inner"]
            check = row["check"]
            name = row["name"]
            purpose = row["purpose"]
            assert isinstance(outer, tk.Frame)
            assert isinstance(inner, tk.Frame)
            assert isinstance(check, tk.Checkbutton)
            assert isinstance(name, tk.Label)
            assert isinstance(purpose, tk.Label)

            outer.configure(bg=border)
            inner.configure(bg=bg)
            check.configure(bg=bg, activebackground=bg)
            name.configure(bg=bg, fg=ACCENT if active or selected else TEXT)
            purpose.configure(bg=bg)

    def _show_mode_details(self, mode: WorkMode) -> None:
        body = self._active_tab_body()
        title = body["detail_title"]
        badges_frame = body["badges_frame"]
        source = body["detail_source"]
        detail_text = body["detail_text"]
        profiles_frame = body["profiles_frame"]
        copy_btn = body["copy_command_btn"]

        assert isinstance(title, tk.Label)
        assert isinstance(badges_frame, tk.Frame)
        assert isinstance(source, tk.Label)
        assert isinstance(detail_text, scrolledtext.ScrolledText)
        assert isinstance(profiles_frame, tk.Frame)
        assert isinstance(copy_btn, ttk.Button)

        title.configure(text=mode.name)
        legacy_source = (
            f"tryb legacy — bez pliku w pakiecie {self._pack_label}"
        )
        source.configure(text=f"Źródło: {mode.source_file or legacy_source}")
        copy_btn.configure(state="normal")

        for child in badges_frame.winfo_children():
            child.destroy()
        tk.Label(
            badges_frame,
            text=_FAMILY_LABELS.get(mode.family, mode.family.upper()),
            bg=mode.category_color,
            fg="white",
            padx=8,
            pady=3,
            font=("Segoe UI", 7, "bold"),
        ).pack(side="left", padx=(0, 6))
        tk.Label(
            badges_frame,
            text=mode.short_label,
            bg=ACCENT_SOFT,
            fg=ACCENT,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        detail_text.configure(state="normal")
        detail_text.delete("1.0", "end")
        self._insert_detail(detail_text, "CEL", mode.purpose)
        self._insert_detail(detail_text, "KIEDY UŻYWAĆ", mode.when_to_use)
        self._insert_detail(detail_text, "ZAKRES", mode.focus)

        if mode.requires:
            names: list[str] = []
            for mode_id in mode.requires:
                required = self._catalog.mode(mode_id)
                names.append(required.short_label if required else mode_id)
            self._insert_detail(detail_text, "ZALEŻNOŚCI", ", ".join(names))
        if mode.distinction_note:
            detail_text.insert("end", "NIE MYL Z\n", "heading")
            detail_text.insert("end", mode.distinction_note + "\n", "warning")
        detail_text.configure(state="disabled")

        self._render_activation_profiles(profiles_frame, mode)

    @staticmethod
    def _insert_detail(
        widget: scrolledtext.ScrolledText,
        heading: str,
        value: str,
    ) -> None:
        widget.insert("end", heading + "\n", "heading")
        widget.insert("end", value + "\n", "body")

    def _show_empty_details(self) -> None:
        body = self._active_tab_body()
        title = body["detail_title"]
        badges = body["badges_frame"]
        source = body["detail_source"]
        detail_text = body["detail_text"]
        profiles = body["profiles_frame"]
        copy_btn = body["copy_command_btn"]

        assert isinstance(title, tk.Label)
        assert isinstance(badges, tk.Frame)
        assert isinstance(source, tk.Label)
        assert isinstance(detail_text, scrolledtext.ScrolledText)
        assert isinstance(profiles, tk.Frame)
        assert isinstance(copy_btn, ttk.Button)

        title.configure(text="Brak wyników")
        source.configure(text="")
        for frame in (badges, profiles):
            for child in frame.winfo_children():
                child.destroy()
        self._set_text(detail_text, "Zmień wyszukiwanie lub kategorię.")
        copy_btn.configure(state="disabled")

    def _render_activation_profiles(self, parent: tk.Frame, mode: WorkMode) -> None:
        for child in parent.winfo_children():
            child.destroy()

        active_profile = self._profile_map.get(mode.id, mode.default_profile.id)
        profiles = mode.activation_profiles
        if len(profiles) == 1:
            profile = profiles[0]
            command_card = tk.Frame(
                parent,
                bg=CARD,
                highlightbackground=BORDER,
                highlightthickness=1,
                padx=10,
                pady=8,
            )
            command_card.pack(fill="x")
            tk.Label(
                command_card,
                text=profile.command,
                bg=CARD,
                fg=TEXT,
                font=("Consolas", 10),
                anchor="w",
            ).pack(fill="x")
            if profile.description:
                tk.Label(
                    command_card,
                    text=profile.description,
                    bg=CARD,
                    fg=MUTED,
                    font=("Segoe UI", 8),
                    anchor="w",
                ).pack(fill="x", pady=(4, 0))
            return

        for column in range(3):
            parent.grid_columnconfigure(column, weight=1, uniform="profiles")
        for index, profile in enumerate(profiles):
            selected = profile.id == active_profile
            border = ACCENT if selected else BORDER
            card_bg = ACCENT_SOFT if selected else CARD
            card = tk.Frame(parent, bg=border, padx=1, pady=1)
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=(0 if index % 3 == 0 else 5, 0),
                pady=(0 if index < 3 else 6, 0),
            )
            content = tk.Frame(card, bg=card_bg, padx=8, pady=7)
            content.pack(fill="both", expand=True)
            label = _VEO_PROFILE_LABELS.get(profile.id, profile.label)
            button = tk.Button(
                content,
                text=("✓  " if selected else "") + label,
                command=lambda p=profile.id, m=mode: self._activate_profile(m, p),
                bg=card_bg,
                fg=ACCENT,
                activebackground=ACCENT_SOFT,
                activeforeground=ACCENT,
                bd=0,
                relief="flat",
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                anchor="w",
                padx=0,
                pady=0,
            )
            button.pack(fill="x")
            tk.Label(
                content,
                text=profile.description or profile.command,
                bg=card_bg,
                fg=MUTED,
                font=("Segoe UI", 7),
                justify="left",
                anchor="nw",
                wraplength=155,
            ).pack(fill="x", pady=(4, 0))

    def _activate_profile(self, mode: WorkMode, profile_id: str) -> None:
        self._profile_map[mode.id] = profile_id
        self._selected_ids.add(mode.id)
        self._active_mode_id = mode.id
        if mode.id in self._mode_vars:
            self._mode_vars[mode.id].set(True)
        self._show_mode_details(mode)
        self._refresh_mode_row_styles()
        self._refresh_prompt_preview()
        command = command_for_mode(mode, profile_id)
        self._copy_text(command, f"Wybrano i skopiowano: {command}")

    # ------------------------------------------------------------------
    # Kombinacje

    def _build_combos_tab(self) -> None:
        wrap = tk.Frame(self._combos_tab, bg=BG, padx=4, pady=8)
        wrap.pack(fill="both", expand=True)

        head = tk.Frame(wrap, bg=BG)
        head.pack(fill="x", padx=4, pady=(0, 8))
        tk.Label(
            head,
            text="Rekomendowane zestawy",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            head,
            text=f"Prompty są generowane na żywo z katalogu {self._pack_label}.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right")

        list_wrap = tk.Frame(wrap, bg=BG)
        list_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            list_wrap,
            bg=BG,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            list_wrap,
            orient="vertical",
            command=canvas.yview,
            style="WT.Vertical.TScrollbar",
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        combos_frame = tk.Frame(canvas, bg=BG)
        canvas_window = canvas.create_window((0, 0), window=combos_frame, anchor="nw")

        def _sync_combo_size(_event: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=max(canvas.winfo_width(), 1))

        combos_frame.bind("<Configure>", _sync_combo_size)
        canvas.bind("<Configure>", _sync_combo_size)
        bind_mousewheel_to_canvas(canvas, combos_frame)

        self._combos_frame = combos_frame

    def _render_combinations(self) -> None:
        for child in self._combos_frame.winfo_children():
            child.destroy()
        self._combos_frame.grid_columnconfigure(0, weight=1, uniform="combo")
        self._combos_frame.grid_columnconfigure(1, weight=1, uniform="combo")
        for index, combo in enumerate(self._catalog.combinations):
            self._add_combo_card(combo, index)

    def _add_combo_card(self, combo: Combination, index: int) -> None:
        outer = tk.Frame(self._combos_frame, bg=BORDER, padx=1, pady=1)
        outer.grid(
            row=index // 2,
            column=index % 2,
            sticky="nsew",
            padx=5,
            pady=5,
        )
        card = tk.Frame(outer, bg=CARD, padx=13, pady=12)
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            text=combo.name,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            justify="left",
            anchor="w",
            wraplength=470,
        ).pack(fill="x")
        tk.Label(
            card,
            text=combo.best_for,
            bg=CARD,
            fg=GOLD,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(5, 5))
        tk.Label(
            card,
            text=combo.delivers,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=470,
        ).pack(fill="x")
        tk.Label(
            card,
            text=f"Przykład: {combo.usage_example}",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
            justify="left",
            anchor="w",
            wraplength=470,
        ).pack(fill="x", pady=(6, 0))
        if combo.note:
            tk.Label(
                card,
                text=combo.note,
                bg=WARNING_SOFT,
                fg=WARNING,
                padx=7,
                pady=4,
                font=("Segoe UI", 8),
                justify="left",
                anchor="w",
                wraplength=450,
            ).pack(fill="x", pady=(7, 0))

        chips = tk.Frame(card, bg=CARD)
        chips.pack(fill="x", pady=(9, 8))
        for mode_id in combo.mode_ids:
            mode = self._catalog.mode(mode_id)
            if mode is None:
                continue
            tk.Label(
                chips,
                text=mode.short_label,
                bg=mode.category_color,
                fg="white",
                padx=7,
                pady=3,
                font=("Segoe UI", 7, "bold"),
            ).pack(side="left", padx=(0, 5))

        actions = tk.Frame(card, bg=CARD)
        actions.pack(fill="x")
        ttk.Button(
            actions,
            text="Wybierz",
            style="WT.Primary.TButton",
            command=lambda item=combo: self._apply_combination(item),
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Kopiuj krótki",
            style="WT.Small.TButton",
            command=lambda item=combo: self._copy_combination_short(item),
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            actions,
            text="Kopiuj pełny",
            style="WT.Small.TButton",
            command=lambda item=combo: self._copy_combination_full(item),
        ).pack(side="left", padx=(7, 0))

    def _apply_combination(self, combo: Combination) -> None:
        self._selected_ids = set(combo.mode_ids)
        self._profile_map.clear()

        first = self._catalog.mode(combo.mode_ids[0]) if combo.mode_ids else None
        if first is not None:
            if first.family in {"workflow", "legacy"}:
                self._active_family = "extra"
            else:
                self._active_family = first.family
            tab_map = {"analyst": 0, "shopify": 1, "extra": 3}
            self._notebook.select(tab_map.get(self._active_family, 0))
            self._active_mode_id = first.id

        self._render_mode_list()
        self._refresh_prompt_preview()
        self._status_var.set(f"Zestaw: {combo.name}")
        show_toast(self.root, f"Wybrano: {combo.name}")

    # ------------------------------------------------------------------
    # Generator

    def _build_generator_panel(self) -> None:
        shell = tk.Frame(self.root, bg=BG, padx=18)
        shell.pack(side="bottom", fill="x", pady=(4, 14))

        panel = tk.Frame(
            shell,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        panel.pack(fill="x")

        bar = tk.Frame(panel, bg=CARD, padx=12, pady=10)
        bar.pack(fill="x")

        summary = tk.Frame(bar, bg=CARD)
        summary.pack(side="left", fill="x", expand=True)
        head = tk.Frame(summary, bg=CARD)
        head.pack(fill="x")
        tk.Label(
            head,
            textvariable=self._selected_count_var,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        tk.Label(
            head,
            textvariable=self._status_var,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(10, 0))

        self._selected_chips_frame = tk.Frame(summary, bg=CARD)
        self._selected_chips_frame.pack(fill="x", pady=(6, 0))

        actions = tk.Frame(bar, bg=CARD)
        actions.pack(side="right", padx=(12, 0))
        self._preview_toggle_btn = ttk.Button(
            actions,
            text="Pokaż podgląd",
            style="WT.Secondary.TButton",
            command=self._toggle_preview,
        )
        self._preview_toggle_btn.pack(side="left")
        self._copy_short_btn = ttk.Button(
            actions,
            text="Kopiuj krótki",
            style="WT.Secondary.TButton",
            command=self._copy_short_prompt,
        )
        self._copy_short_btn.pack(side="left", padx=(7, 0))
        self._copy_full_btn = ttk.Button(
            actions,
            text="Kopiuj pełny",
            style="WT.Primary.TButton",
            command=self._copy_full_prompt,
        )
        self._copy_full_btn.pack(side="left", padx=(7, 0))

        self._preview_frame = tk.Frame(panel, bg=CODE_BG, padx=10, pady=9)
        self._prompt_preview = scrolledtext.ScrolledText(
            self._preview_frame,
            height=7,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
            relief="flat",
            bd=0,
            highlightthickness=0,
            bg=CODE_BG,
            fg=CODE_FG,
            insertbackground=CODE_FG,
            padx=8,
            pady=6,
        )
        self._prompt_preview.pack(fill="x")

    def _toggle_preview(self) -> None:
        self._preview_visible = not self._preview_visible
        if self._preview_visible:
            self._preview_frame.pack(fill="x")
            self._preview_toggle_btn.configure(text="Ukryj podgląd")
        else:
            self._preview_frame.pack_forget()
            self._preview_toggle_btn.configure(text="Pokaż podgląd")

    def _refresh_prompt_preview(self) -> None:
        for child in self._selected_chips_frame.winfo_children():
            child.destroy()

        ids = list(self._selected_ids)
        if not ids:
            self._selected_count_var.set("Nie wybrano trybów")
            tk.Label(
                self._selected_chips_frame,
                text="Zaznacz tryb albo wybierz gotową kombinację.",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 8),
            ).pack(side="left")
            self._set_text(self._prompt_preview, "")
            self._copy_short_btn.configure(state="disabled")
            self._copy_full_btn.configure(state="disabled")
            self._preview_toggle_btn.configure(state="disabled")
            return

        modes, profiles = resolve_modes_with_dependencies(
            self._catalog,
            ids,
            profile_map=self._profile_map,
        )
        count = len(self._selected_ids)
        if count == 1:
            noun = "tryb"
        elif 2 <= count <= 4:
            noun = "tryby"
        else:
            noun = "trybów"
        self._selected_count_var.set(f"Wybrano {count} {noun}")
        manual = set(ids)
        visible_modes = modes[:5]
        for mode in visible_modes:
            is_auto = mode.id not in manual
            profile = mode.profile(profiles.get(mode.id))
            label = mode.short_label
            if len(mode.activation_profiles) > 1:
                label += f" · {_VEO_PROFILE_LABELS.get(profile.id, profile.label)}"
            if is_auto:
                label += " · AUTO"
            tk.Label(
                self._selected_chips_frame,
                text=label,
                bg=SUCCESS_SOFT if is_auto else ACCENT_SOFT,
                fg=SUCCESS if is_auto else ACCENT,
                padx=8,
                pady=3,
                font=("Segoe UI", 7, "bold"),
            ).pack(side="left", padx=(0, 5))
        if len(modes) > len(visible_modes):
            tk.Label(
                self._selected_chips_frame,
                text=f"+{len(modes) - len(visible_modes)}",
                bg="#ECE8E0",
                fg=MUTED,
                padx=8,
                pady=3,
                font=("Segoe UI", 7, "bold"),
            ).pack(side="left")

        prompt = full_prompt_for_modes(
            self._catalog,
            ids,
            profile_map=self._profile_map,
        )
        self._set_text(self._prompt_preview, prompt)
        self._copy_short_btn.configure(state="normal")
        self._copy_full_btn.configure(state="normal")
        self._preview_toggle_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Akcje

    def _focus_search(self, _event: tk.Event | None = None) -> str:
        if self._notebook.index(self._notebook.select()) == 2:
            return "break"
        body = self._active_tab_body()
        family = str(body["family"])
        entry = self._search_entries.get(family)
        if entry is not None:
            entry.focus_set()
            entry.selection_range(0, "end")
        return "break"

    def _handle_escape(self, _event: tk.Event | None = None) -> str:
        if self._search_var.get():
            self._search_var.set("")
        elif self._preview_visible:
            self._toggle_preview()
        return "break"

    def _clear_selection(self) -> None:
        self._selected_ids.clear()
        self._profile_map.clear()
        for var in self._mode_vars.values():
            var.set(False)
        self._refresh_mode_row_styles()
        self._refresh_prompt_preview()
        self._status_var.set("Wyczyszczono")

    def _copy_text(self, text: str, toast_text: str = "Skopiowano") -> None:
        if not text.strip():
            show_toast(self.root, "Brak tekstu do skopiowania", duration_ms=1400)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        show_toast(self.root, toast_text)

    def _copy_active_command(self) -> None:
        mode = self._catalog.mode(self._active_mode_id or "")
        if mode is None:
            return
        profile_id = self._profile_map.get(mode.id)
        command = command_for_mode(mode, profile_id)
        self._copy_text(command, f"Skopiowano: {command}")

    def _copy_full_prompt(self) -> None:
        self._copy_text(
            full_prompt_for_modes(
                self._catalog,
                list(self._selected_ids),
                profile_map=self._profile_map,
            ),
            "Skopiowano pełny prompt",
        )

    def _copy_short_prompt(self) -> None:
        self._copy_text(
            short_prompt_for_modes(
                self._catalog,
                list(self._selected_ids),
                profile_map=self._profile_map,
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
            "Skopiowano pełny prompt",
        )

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
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
