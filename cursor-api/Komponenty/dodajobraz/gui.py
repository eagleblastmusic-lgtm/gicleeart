"""GUI 'dodajobraz' - drag-and-drop, kolejka plikow, tryb batch LLM w Cursorze.

Funkcje:
- Kolejka plikow (wrzucasz wiele na raz).
- Automatyczne tlumaczenie obcojezycznego tytulu (przez LLM w Cursorze).
- Dogrywanie kolejnych zdjec do istniejacego produktu (plik z sufiksem ' F2', ' F3', ...).
- Jeden prompt dla wszystkich nowych produktow + tablica JSON zwrotna z LLM.
"""
from __future__ import annotations

import queue
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any, Callable

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from .create import (
    add_full_image,
    add_preview_image,
    assign_products_to_collection_title,
    create_artist_collection_and_menu,
    find_existing_product_for_new,
    get_artist_products,
    get_main_image_listing,
    process_batch,
)
from .cloudflare_usage_dialog import open_cloudflare_usage_dialog
from .r2_usage import collect_r2_usage, format_usage_line
from .r2_storage import zoom_parallel_products_default
from .zoom_publish import format_timing_line, publish_zoom_for_queue_item
from .parser import (
    FOLLOW_UP_KIND_I,
    IMAGE_ROLE_FULL,
    IMAGE_ROLE_MOCKUP,
    IMAGE_ROLE_PREVIEW,
    is_polish_title,
    parse_filename,
    parse_title_metadata,
)
from .queue_audit import audit_preview_full_pairs, format_pair_status
from .prompt_builder import (
    PROMPT_CHUNK_SIZE,
    build_all_prompt_chunks,
    dedupe_items_for_prompt,
    dedupe_queue_items_by_work,
    format_merged_json,
    lookup_llm_entry,
    merge_json_part_lists,
    parse_batch_response_json,
)
from . import shopify_client as sc
from .shopify_client import OperationCancelled

from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.activity_log_ui import open_activity_log_dialog
from Komponenty._shared.task_notify import notify_long_task_done
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.mockup.templates import (
    MOCKUP_ALL_VARIANTS_LABEL,
    MockupSet,
    list_mockup_sets,
    mockup_set_choices,
    resolve_mockup_sets,
)

APP_TITLE = "dodajobraz"

# Kolejka: szerokość kolumn z pomiaru tekstu (px), z rozsądnym limitem na bardzo długie napisy.
# Margines przy pomiarze tekstu (Treeview ma jeszcze wlasny padding naglowka/komorki).
_QUEUE_COL_PAD = 14
_MIN_QUEUE_COL_WIDTH = 48
_MAX_QUEUE_COL_WIDTH = 480
# Ostatnia kolumna rozciaga sie z Treeview — brak pustego pasa miedzy „Akcja” a scrollbarem.
_QUEUE_STRETCH_COL = "action"


class App:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 1010, 880)
        self.root.minsize(900, 640)

        self.queue_items: list[dict[str, Any]] = []
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._toast_after_ids: list[Any] = []
        self._toast_win: tk.Toplevel | None = None
        self._precheck_skip_all = False
        self._zoom_timing_lock = threading.Lock()
        self._zoom_timing_active: dict[str, str] = {}
        self._zoom_timing_agg = {"tiles": 0.0, "upload": 0.0, "shopify": 0.0, "n": 0}
        self._zoom_last_timing: dict[str, Any] | None = None
        self.mockup_sets: list[MockupSet] = list_mockup_sets()
        self.mockup_var = tk.BooleanVar(value=True)
        self.mockup_set_var = tk.StringVar(
            value=MOCKUP_ALL_VARIANTS_LABEL if self.mockup_sets else ""
        )

        self._build_ui()
        self._poll_log_queue()
        self.root.after(400, self._refresh_r2_usage)

    # ---------------------- UI construction ----------------------
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", **pad)
        ttk.Button(toolbar, text="Dziennik akcji", command=self._on_activity_log).pack(
            side="right", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Instrukcja", command=self._show_help).pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="Zestawienie produktow...", command=self._on_show_listing).pack(
            side="right", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Kontrola kolekcji...", command=self._on_collection_control).pack(
            side="right", padx=(0, 8)
        )
        ttk.Button(toolbar, text="Szablony...", command=self._on_open_templates).pack(side="right", padx=(0, 8))

        self._build_role_drop_zones(main, pad)

        list_frame = ttk.LabelFrame(main, text="Kolejka plikow")
        self._list_frame = list_frame
        list_frame.pack(fill="x", expand=False, **pad)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        cols = ("file", "artist", "title", "mode", "lang", "action")
        self._queue_col_ids = cols
        self._queue_heading_text = {
            "file": "Plik",
            "artist": "Artysta",
            "title": "Tytul",
            "mode": "Tryb",
            "lang": "Jezyk tytulu",
            "action": "Akcja",
        }
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=self._queue_heading_text[c])
            self.tree.column(
                c,
                width=_MIN_QUEUE_COL_WIDTH,
                anchor="w",
                stretch=(c == _QUEUE_STRETCH_COL),
                minwidth=_MIN_QUEUE_COL_WIDTH,
            )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self.tree.bind("<Configure>", self._on_tree_configure, add="+")
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click, add="+")
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self._tree_scroll = tree_scroll
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=6)

        queue_btns = ttk.Frame(list_frame)
        self._queue_btns_frame = queue_btns
        ttk.Button(queue_btns, text="Usun zaznaczone", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(queue_btns, text="Wyczysc liste", command=self._clear_queue).pack(fill="x", pady=2)
        ttk.Button(
            queue_btns,
            text="Przelacz polski/obcy",
            command=self._toggle_language_selected,
        ).pack(fill="x", pady=2)
        pid_frame = ttk.LabelFrame(queue_btns, text="Dogrywka do produktu", padding=(4, 4))
        pid_frame.pack(fill="x", pady=(8, 2))
        ttk.Label(
            pid_frame,
            text="Nr produktu Shopify (lub URL admin):",
            wraplength=200,
        ).pack(anchor="w")
        self.manual_product_id_var = tk.StringVar(value="")
        ttk.Entry(pid_frame, textvariable=self.manual_product_id_var, width=16).pack(
            fill="x", pady=(4, 4)
        )
        ttk.Button(
            pid_frame,
            text="Przypisz do zaznaczonych",
            command=self._assign_manual_product_id,
        ).pack(fill="x", pady=(0, 2))
        ttk.Button(
            pid_frame,
            text="Przypisz do calej kolejki",
            command=lambda: self._assign_manual_product_id(all_items=True),
        ).pack(fill="x")
        self.counts_var = tk.StringVar(value="0 plikow")
        ttk.Label(queue_btns, textvariable=self.counts_var, foreground="#0a6").pack(fill="x", pady=(10, 2))
        self.pair_status_var = tk.StringVar(value="")
        self.pair_status_lbl = ttk.Label(
            queue_btns,
            textvariable=self.pair_status_var,
            foreground="#a33",
            wraplength=200,
            justify="left",
        )
        self.pair_status_lbl.pack(fill="x", pady=(4, 2))
        queue_btns.grid(row=0, column=2, sticky="ns", padx=(4, 6), pady=6)

        self._autosize_queue_columns()

        self.step1 = ttk.LabelFrame(
            main,
            text="Krok 1: Wygeneruj prompt dla NOWYCH produktow, wklej do Cursora / ChatGPT",
        )
        self.step1.pack(fill="both", expand=False, **pad)
        self.prompt_text = scrolledtext.ScrolledText(self.step1, height=8, wrap="word", font=("Consolas", 9))
        self.prompt_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.prompt_text.configure(state="disabled")
        self._prompt_model: str = "opus"
        self.step1_btn_row = ttk.Frame(self.step1)
        self.step1_btn_row.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(
            self.step1_btn_row, text="Wygeneruj prompt (Opus)",
            command=lambda: self._generate_prompt(model="opus"),
        ).pack(side="left")
        ttk.Button(
            self.step1_btn_row, text="Wygeneruj prompt (GPT)",
            command=lambda: self._generate_prompt(model="gpt"),
        ).pack(side="left", padx=6)
        ttk.Button(self.step1_btn_row, text="Kopiuj do schowka", command=self._copy_prompt).pack(side="left", padx=6)
        self.prompt_model_var = tk.StringVar(value="")
        ttk.Label(self.step1_btn_row, textvariable=self.prompt_model_var, foreground="#0a6").pack(side="left", padx=10)

        self._prompt_chunks: list[tuple[int, int, str]] = []
        self.prompt_chunks_outer = ttk.Frame(self.step1)
        self.prompt_chunks_outer.pack(fill="x", padx=6, pady=(0, 6))
        self.prompt_chunks_summary_var = tk.StringVar(value="")
        ttk.Label(
            self.prompt_chunks_outer,
            textvariable=self.prompt_chunks_summary_var,
            foreground="#666",
            wraplength=880,
        ).pack(anchor="w")
        chunk_btn_row = ttk.Frame(self.prompt_chunks_outer)
        chunk_btn_row.pack(fill="x", pady=(4, 0))
        self.prompt_chunks_btn_frame = ttk.Frame(chunk_btn_row)
        self.prompt_chunks_btn_frame.pack(side="left", fill="x", expand=True)
        preview_row = ttk.Frame(chunk_btn_row)
        preview_row.pack(side="right")
        ttk.Label(preview_row, text="Podglad:").pack(side="left", padx=(8, 4))
        self.prompt_part_var = tk.StringVar(value="1")
        self.prompt_part_combo = ttk.Combobox(
            preview_row,
            textvariable=self.prompt_part_var,
            width=4,
            state="readonly",
        )
        self.prompt_part_combo.pack(side="left")
        self.prompt_part_combo.bind("<<ComboboxSelected>>", self._on_prompt_part_selected)
        self.prompt_chunks_outer.pack_forget()

        for w in (self.step1, self.prompt_text, self.step1_btn_row):
            w.bind("<Button-1>", self._on_step1_click, add="+")

        self.step2 = ttk.LabelFrame(
            main,
            text="Krok 2: Wklej TABLICE JSON ktora zwrocil LLM (dla dogrywek F2+ niepotrzebne)",
        )
        self.step2.pack(fill="both", expand=True, **pad)

        self._json_parts: dict[int, list[dict[str, Any]]] = {}
        self._json_parts_expected = 0
        self.json_parts_outer = ttk.Frame(self.step2)
        self.json_parts_outer.pack(fill="x", padx=6, pady=(6, 0))
        self.json_parts_summary_var = tk.StringVar(value="")
        ttk.Label(
            self.json_parts_outer,
            textvariable=self.json_parts_summary_var,
            foreground="#666",
            wraplength=880,
        ).pack(anchor="w")
        json_parts_btn_row = ttk.Frame(self.json_parts_outer)
        json_parts_btn_row.pack(fill="x", pady=(4, 0))
        self.json_parts_btn_frame = ttk.Frame(json_parts_btn_row)
        self.json_parts_btn_frame.pack(side="left", fill="x", expand=True)
        ttk.Button(
            json_parts_btn_row,
            text="Wyczysc czesci",
            command=self._clear_json_parts,
            width=14,
        ).pack(side="right", padx=(6, 0))
        self.json_parts_outer.pack_forget()

        self.json_text = scrolledtext.ScrolledText(self.step2, height=10, wrap="word", font=("Consolas", 9))
        self.json_text.pack(fill="both", expand=True, padx=6, pady=6)

        self.step2.bind("<Button-1>", self._on_step2_click, add="+")
        self.json_text.bind("<Button-1>", self._on_json_text_click, add="+")

        row_actions = ttk.Frame(main)
        row_actions.pack(fill="x", **pad)
        self.create_btn = ttk.Button(row_actions, text="Utworz wszystko", command=self._on_create_clicked)
        self.create_btn.pack(side="left")
        self.zoom_btn = ttk.Button(
            row_actions, text="Zoom HD -> R2", command=self._on_publish_zoom_clicked
        )
        self.zoom_btn.pack(side="left", padx=(8, 0))
        mockup_row = ttk.Frame(row_actions)
        mockup_row.pack(side="left", padx=(10, 0))
        self.mockup_chk = ttk.Checkbutton(mockup_row, text="Mockup", variable=self.mockup_var)
        self.mockup_chk.pack(side="left")
        if self.mockup_sets:
            ttk.Combobox(
                mockup_row,
                textvariable=self.mockup_set_var,
                values=mockup_set_choices(self.mockup_sets),
                state="readonly",
                width=30,
            ).pack(side="left", padx=(4, 0))
        else:
            self.mockup_var.set(False)
            self.mockup_chk.configure(state="disabled")
        ttk.Button(
            row_actions, text="Cloudflare", command=self._show_cloudflare_dialog, width=12
        ).pack(side="left", padx=(4, 0))
        ttk.Button(
            row_actions, text="Odswiez R2", command=self._refresh_r2_usage, width=12
        ).pack(side="left", padx=(4, 0))
        ttk.Button(row_actions, text="?", command=self._show_r2_usage_help, width=3).pack(
            side="left", padx=(2, 0)
        )
        self.status_var = tk.StringVar(value="Gotowy. Dodaj pliki do kolejki.")
        ttk.Label(row_actions, textvariable=self.status_var, foreground="#666").pack(side="left", padx=12)

        prog_row = ttk.Frame(main)
        prog_row.pack(fill="x", **pad)
        prog_row.columnconfigure(1, weight=1)
        ttk.Label(prog_row, text="Shopify:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.batch_progress_var = tk.DoubleVar(value=0.0)
        self.batch_progress = ttk.Progressbar(
            prog_row, variable=self.batch_progress_var, maximum=100.0, mode="determinate"
        )
        self.batch_progress.grid(row=0, column=1, sticky="ew")
        self.batch_progress_label_var = tk.StringVar(value="")
        ttk.Label(
            prog_row, textvariable=self.batch_progress_label_var, width=14, foreground="#0a6"
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ttk.Label(prog_row, text="Zoom HD:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.zoom_progress_var = tk.DoubleVar(value=0.0)
        self.zoom_progress = ttk.Progressbar(
            prog_row, variable=self.zoom_progress_var, maximum=100.0, mode="determinate"
        )
        self.zoom_progress.grid(row=1, column=1, sticky="ew", pady=(6, 0))
        self.zoom_progress_label_var = tk.StringVar(value="")
        ttk.Label(
            prog_row, textvariable=self.zoom_progress_label_var, width=14, foreground="#06a"
        ).grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(6, 0))
        self.zoom_timing_var = tk.StringVar(value="")
        ttk.Label(prog_row, text="Czas:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        ttk.Label(
            prog_row,
            textvariable=self.zoom_timing_var,
            foreground="#555",
            wraplength=820,
            justify="left",
        ).grid(row=2, column=1, columnspan=2, sticky="ew", pady=(4, 0))
        self.r2_usage_var = tk.StringVar(value="R2: (ladowanie...)")
        ttk.Label(prog_row, text="R2:").grid(row=3, column=0, sticky="nw", padx=(0, 8), pady=(6, 0))
        ttk.Label(
            prog_row,
            textvariable=self.r2_usage_var,
            foreground="#444",
            wraplength=820,
            justify="left",
        ).grid(row=3, column=1, columnspan=2, sticky="ew", pady=(6, 0))

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=4, wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

    # ---------------------- Drag & drop / browse ----------------------
    def _build_role_drop_zones(self, parent: tk.Misc, pad: dict[str, int]) -> None:
        zones_row = ttk.Frame(parent)
        zones_row.pack(fill="x", **pad)
        for col in (0, 1, 2):
            zones_row.columnconfigure(col, weight=1, uniform="dropzone")

        dnd_note = "" if _HAS_DND else "\n(brak DnD: pip install tkinterdnd2)"
        specs: list[tuple[str, str, str, str, str]] = [
            (
                IMAGE_ROLE_PREVIEW,
                "Preview (kolekcje / menu)",
                "#eef6ff",
                "Przeciagnij lub kliknij\n"
                "«Artysta - Tytul - (preview).webp»" + dnd_note,
                "Wybierz preview...",
            ),
            (
                IMAGE_ROLE_FULL,
                "Full (galeria produktu)",
                "#f0faf0",
                "Przeciagnij lub kliknij\n"
                "«Artysta - Tytul - Full.webp»" + dnd_note,
                "Wybierz Full...",
            ),
            (
                "other",
                "Pozostale",
                "#f7f5f0",
                "Przeciagnij lub kliknij\n"
                "F2, I1–I3, (mockup), WK, KK, zwykly tytul" + dnd_note,
                "Wybierz pliki...",
            ),
        ]
        self._drop_zones: dict[str, tk.Label] = {}
        for col, (role, title, bg, hint, browse_caption) in enumerate(specs):
            lf = ttk.LabelFrame(zones_row, text=title)
            lf.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 4, 0))
            zone = tk.Label(
                lf,
                text=hint,
                relief="groove",
                bd=2,
                bg=bg,
                fg="#333",
                height=4,
                font=("Segoe UI", 9),
                justify="center",
                cursor="hand2",
            )
            zone.pack(fill="both", expand=True, padx=6, pady=(4, 2))
            zone.bind(
                "<Button-1>",
                lambda _e, r=role: self._browse_files(expected_role=r),
            )
            if _HAS_DND:
                zone.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                zone.dnd_bind(  # type: ignore[attr-defined]
                    "<<Drop>>",
                    lambda e, r=role: self._on_drop_for_role(e, r),
                )
            self._drop_zones[role] = zone
            ttk.Button(
                lf,
                text=browse_caption,
                command=lambda r=role: self._browse_files(expected_role=r),
            ).pack(pady=(0, 6))

    @staticmethod
    def _parse_dnd_paths(raw: str) -> list[Path]:
        paths: list[str] = []
        i = 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.find("}", i + 1)
                if end == -1:
                    break
                paths.append(raw[i + 1 : end])
                i = end + 1
            elif raw[i].isspace():
                i += 1
            else:
                end = raw.find(" ", i)
                if end == -1:
                    paths.append(raw[i:])
                    break
                paths.append(raw[i:end])
                i = end + 1
        return [Path(p.strip()) for p in paths if p.strip()]

    def _on_drop_for_role(self, event: tk.Event, expected_role: str) -> None:  # type: ignore[type-arg]
        raw = (event.data or "").strip()
        if not raw:
            return
        self._add_files(self._parse_dnd_paths(raw), expected_role=expected_role)

    def _browse_files(self, *, expected_role: str | None = None) -> None:
        titles = {
            IMAGE_ROLE_PREVIEW: "Wybierz pliki PREVIEW — nazwa musi konczyc sie na «(preview)»",
            IMAGE_ROLE_FULL: "Wybierz pliki FULL — nazwa musi konczyc sie na «Full»",
            "other": "Wybierz pozostale (F2, I1, (mockup), WK, KK — bez preview/Full)",
        }
        ps = filedialog.askopenfilenames(
            title=titles.get(expected_role or "", "Wybierz zdjecia"),
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff"), ("Wszystkie", "*.*")],
        )
        if ps:
            self._add_files([Path(p) for p in ps], expected_role=expected_role)

    def _role_mismatch_message(self, path: Path, expected_role: str, actual: str | None) -> str:
        if expected_role == IMAGE_ROLE_PREVIEW:
            if actual == IMAGE_ROLE_PREVIEW:
                return ""
            return (
                f"{path.name}: oczekiwano sufiksu «(preview)» w tytule "
                f"(np. Artysta - Tytul - (preview).webp)."
            )
        if expected_role == IMAGE_ROLE_FULL:
            if actual == IMAGE_ROLE_FULL:
                return ""
            return (
                f"{path.name}: oczekiwano sufiksu «Full» w tytule "
                f"(np. Artysta - Tytul - Full.webp)."
            )
        if actual == IMAGE_ROLE_PREVIEW:
            return f"{path.name}: to plik preview — uzyj pola «Preview» (nie «Pozostale»)."
        if actual == IMAGE_ROLE_FULL:
            return f"{path.name}: to plik Full — uzyj pola «Full»."
        if actual == IMAGE_ROLE_MOCKUP:
            return f"{path.name}: to plik (mockup) — uzyj pola «Pozostale»."
        return ""

    # ---------------------- Queue management ----------------------
    def _add_files(
        self,
        paths: list[Path],
        *,
        expected_role: str | None = None,
    ) -> None:
        added = 0
        errors: list[str] = []
        existing = {str(it["path"]) for it in self.queue_items}
        for p in paths:
            if not p.is_file():
                errors.append(f"{p} - plik nie istnieje")
                continue
            if str(p) in existing:
                continue
            try:
                artist, raw_title = parse_filename(p)
            except ValueError as e:
                errors.append(f"{p.name}: {e}")
                continue
            base_title, fnum, correction, image_role, fkind = parse_title_metadata(raw_title)
            if expected_role:
                msg = self._role_mismatch_message(p, expected_role, image_role)
                if msg:
                    errors.append(msg)
                    continue
            pl = is_polish_title(base_title)
            display_title = base_title if (fnum or correction or image_role) else raw_title
            item = {
                "path": p,
                "artist": artist,
                "title": display_title,
                "base_title": base_title,
                "follow_up_number": fnum,
                "follow_up_kind": fkind,
                "correction_suffix": correction,
                "image_role": image_role,
                "title_is_polish": pl,
            }
            self.queue_items.append(item)
            existing.add(str(p))
            added += 1
        self._refresh_tree()
        self._refresh_counts_and_status()
        to_check = [
            it for it in self.queue_items
            if it.get("follow_up_number") is None
            and it.get("image_role") != "preview"
            and "action" not in it
            and not it.get("_precheck_started")
        ]
        if to_check:
            for it in to_check:
                it["_precheck_started"] = True
            self._refresh_tree()
            self._kick_precheck(to_check)
        if added and self._has_new_items():
            self._generate_prompt()
        elif added:
            self.prompt_text.configure(state="normal")
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert(
                "1.0",
                "[W kolejce sa tylko dogrywki / preview / Full bez nowego produktu] "
                "Prompt niepotrzebny - klik 'Utworz wszystko'.",
            )
            self.prompt_text.configure(state="disabled")
        if errors:
            messagebox.showwarning(APP_TITLE, "Niektorych plikow nie dodano:\n\n" + "\n".join(errors))

    def _remove_selected(self) -> None:
        selected = set(self.tree.selection())
        if not selected:
            return
        keep: list[dict[str, Any]] = []
        for iid, item in zip(self._iids(), self.queue_items):
            if iid not in selected:
                keep.append(item)
        self.queue_items = keep
        self._refresh_tree()
        self._refresh_counts_and_status()
        if self._has_new_items():
            self._generate_prompt()
        else:
            self.prompt_text.configure(state="normal")
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.configure(state="disabled")

    def _clear_queue(self) -> None:
        if not self.queue_items:
            return
        if not messagebox.askyesno(APP_TITLE, "Wyczyscic cala kolejke plikow?"):
            return
        self.queue_items.clear()
        self._refresh_tree()
        self._refresh_counts_and_status()
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.configure(state="disabled")

    def _parse_manual_product_id(self, raw: str) -> int | None:
        s = (raw or "").strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        m = re.search(r"/products/(\d+)", s)
        if m:
            return int(m.group(1))
        m = re.search(r"\bid[=\s:]+(\d+)", s, re.I)
        if m:
            return int(m.group(1))
        return None

    def _action_for_manual_product_assign(self, item: dict[str, Any]) -> str:
        role = item.get("image_role")
        if role in (IMAGE_ROLE_FULL, IMAGE_ROLE_PREVIEW) or item.get("follow_up_number") is not None:
            return "skip"
        return "replace_image"

    def _assign_manual_product_id(self, *, all_items: bool = False) -> None:
        if not self.queue_items:
            messagebox.showwarning(APP_TITLE, "Kolejka jest pusta.")
            return
        pid = self._parse_manual_product_id(self.manual_product_id_var.get())
        if not pid:
            messagebox.showwarning(
                APP_TITLE,
                "Podaj numer produktu Shopify (np. 1234567890)\n"
                "lub URL z panelu admin: .../admin/products/1234567890",
            )
            return

        if all_items:
            targets = list(self.queue_items)
        else:
            selected = set(self.tree.selection())
            if not selected:
                messagebox.showinfo(
                    APP_TITLE,
                    "Zaznacz pozycje w kolejce albo uzyj «Przypisz do calej kolejki».",
                )
                return
            targets = [
                item
                for iid, item in zip(self._iids(), self.queue_items)
                if iid in selected
            ]

        self.status_var.set(f"Sprawdzam produkt id={pid}...")
        try:
            shop, token = sc.load_session()
            prod = sc.get_product(shop, token, pid)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Nie mozna pobrac produktu id={pid}:\n{exc}")
            self.status_var.set("Blad przypisania produktu.")
            return
        if not prod:
            messagebox.showerror(APP_TITLE, f"Nie znaleziono produktu id={pid} w Shopify.")
            self.status_var.set("Blad przypisania produktu.")
            return

        title = (prod.get("title") or "").strip()
        handle = (prod.get("handle") or "").strip()
        if not messagebox.askyesno(
            APP_TITLE,
            f"Przypisac produkt do {len(targets)} pozycji?\n\n"
            f"id={pid}\n{title}\nhandle={handle}",
        ):
            return

        for item in targets:
            item.pop("_precheck_started", None)
            item["existing_product_id"] = int(pid)
            item["manual_product_id"] = True
            item["handle"] = handle
            item["action"] = self._action_for_manual_product_assign(item)

        self._refresh_tree()
        self._refresh_counts_and_status()
        self._enqueue_log(
            f"[reczne id] Przypisano produkt id={pid} ({title}) do {len(targets)} plik(ow)."
        )
        self.status_var.set(
            f"Przypisano id={pid} do {len(targets)} pozycji — mozesz dograc Full / Zoom HD."
        )

    def _toggle_language_selected(self) -> None:
        """Reczne przelaczenie 'polski' <-> 'OBCY' dla zaznaczonych pozycji.

        Auto-detekcja `is_polish_title` czasem sie myli (np. krotki tytul
        bez diakrytykow interpretowany jako polski, choc jest obcy).
        Ta akcja pozwala rotkowi poprawic flage recznie - zmiana przeplynie
        do promptu LLM (pole `title_is_polish`) i do logiki matchingu produktu.
        Pomija dogrywki F2+ (nie tworza nowego produktu, flaga jest bez znaczenia).
        """
        selected = set(self.tree.selection())
        if not selected:
            messagebox.showinfo(APP_TITLE, "Zaznacz najpierw pozycje w kolejce.")
            return
        toggled = 0
        for iid, item in zip(self._iids(), self.queue_items):
            if iid not in selected:
                continue
            if item.get("follow_up_number") is not None:
                continue
            item["title_is_polish"] = not item.get("title_is_polish", True)
            item["title_is_polish_manual"] = True
            toggled += 1
        if not toggled:
            messagebox.showinfo(
                APP_TITLE,
                "Zaznaczone pozycje to dogrywki F2+ - jezyk tytulu nie ma dla nich znaczenia.",
            )
            return
        self._refresh_tree()
        if self._has_new_items():
            self._generate_prompt()
        self.status_var.set(f"Przelaczono jezyk tytulu dla {toggled} pozycji - prompt odswiezony.")

    def _on_tree_double_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Dwuklik na komorce kolejki:
        - 'lang' -> przelacza polski/obcy,
        - 'artist' / 'title' -> inline-edycja wartosci (Entry-overlay).
        Pozostale kolumny ignorujemy.
        """
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id = self.tree.identify_column(event.x)
        try:
            col_idx = int(col_id.replace("#", "")) - 1
        except ValueError:
            return
        if col_idx < 0 or col_idx >= len(self._queue_col_ids):
            return
        col_name = self._queue_col_ids[col_idx]
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        iids = self._iids()
        try:
            pos = iids.index(iid)
        except ValueError:
            return
        if pos >= len(self.queue_items):
            return
        item = self.queue_items[pos]
        if col_name == "lang":
            if item.get("follow_up_number") is not None:
                return
            item["title_is_polish"] = not item.get("title_is_polish", True)
            item["title_is_polish_manual"] = True
            self._refresh_tree()
            if self._has_new_items():
                self._generate_prompt()
            new_lang = "polski" if item["title_is_polish"] else "OBCY"
            self.status_var.set(f"{item['path'].name}: jezyk tytulu -> {new_lang} (recznie).")
            return
        if col_name in ("artist", "title"):
            self._begin_cell_edit(iid, col_id, col_name, item)

    # ---------------------- Inline edycja komorek (artysta / tytul) ----------------------
    def _begin_cell_edit(
        self,
        iid: str,
        col_id: str,
        col_name: str,
        item: dict[str, Any],
    ) -> None:
        """Otwiera overlay-Entry nad zaznaczona komorka. Enter = zapisz, Esc = anuluj."""
        existing = getattr(self, "_cell_editor", None)
        if existing is not None:
            try:
                existing.destroy()
            except tk.TclError:
                pass
            self._cell_editor = None
        try:
            bbox = self.tree.bbox(iid, col_id)
        except tk.TclError:
            bbox = None
        if not bbox:
            return
        x, y, w, h = bbox
        current = item.get(col_name, "") or ""
        entry = tk.Entry(self.tree, borderwidth=1, relief="solid", font=self._queue_tree_font())
        entry.insert(0, str(current))
        entry.select_range(0, "end")
        entry.icursor("end")
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        self._cell_editor = entry
        cancelled = {"v": False}

        def commit(_e: tk.Event | None = None) -> None:  # type: ignore[type-arg]
            if cancelled["v"]:
                return
            new_val = entry.get().strip()
            try:
                entry.destroy()
            except tk.TclError:
                pass
            self._cell_editor = None
            self._apply_cell_edit(item, col_name, new_val)

        def cancel(_e: tk.Event | None = None) -> None:  # type: ignore[type-arg]
            cancelled["v"] = True
            try:
                entry.destroy()
            except tk.TclError:
                pass
            self._cell_editor = None

        entry.bind("<Return>", commit)
        entry.bind("<KP_Enter>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", cancel)

    def _apply_cell_edit(self, item: dict[str, Any], col_name: str, new_val: str) -> None:
        """Zapisuje edytowana wartosc do pozycji kolejki i odswieza stan GUI.

        - Kolumna 'artist': update `item['artist']` (nazwa artysty dla kolekcji + promptu).
        - Kolumna 'title': update `item['title']` + re-parse metadata (F<N>/KK/WK)
          i re-detekcja jezyka tytulu (chyba ze user juz przelaczyl jezyk recznie).
        Jesli wartosc pusta lub bez zmian -> tylko refresh (brak NPE).
        """
        if not new_val:
            self._refresh_tree()
            return
        if col_name == "artist":
            if new_val == item.get("artist"):
                return
            item["artist"] = new_val
            self._refresh_tree()
            if self._has_new_items():
                self._generate_prompt()
            self.status_var.set(f"{item['path'].name}: artysta -> {new_val}.")
            return
        if col_name == "title":
            if new_val == item.get("title"):
                return
            base_title, fnum, correction, image_role, fkind = parse_title_metadata(new_val)
            item["title"] = base_title if (fnum or correction or image_role) else new_val
            item["base_title"] = base_title
            item["follow_up_number"] = fnum
            item["follow_up_kind"] = fkind
            item["correction_suffix"] = correction
            item["image_role"] = image_role
            if not item.get("title_is_polish_manual"):
                item["title_is_polish"] = is_polish_title(base_title)
            for k in ("action", "existing_product_id", "_precheck_started"):
                item.pop(k, None)
            self._refresh_tree()
            self._refresh_counts_and_status()
            if self._has_new_items():
                self._generate_prompt()
            self.status_var.set(f"{item['path'].name}: tytul -> {item['title']}.")
            if fnum is None and not item.get("_precheck_started"):
                item["_precheck_started"] = True
                self._refresh_tree()
                self._kick_precheck([item])

    def _describe_action(self, item: dict[str, Any]) -> str:
        role = item.get("image_role")
        if role == IMAGE_ROLE_PREVIEW:
            return "Podglad (preview)"
        if role == IMAGE_ROLE_FULL:
            return "Full (galeria)"
        if role == IMAGE_ROLE_MOCKUP:
            return "Mockup"
        fkind = item.get("follow_up_kind")
        fnum = item.get("follow_up_number")
        if fnum is not None:
            if fkind == FOLLOW_UP_KIND_I:
                return f"Dogrywka I{fnum}"
            return f"Dogrywka F{fnum}"
        action = item.get("action")
        if action is None:
            return "(sprawdzam...)" if item.get("_precheck_started") else "(oczekuje)"
        pid = item.get("existing_product_id")
        manual = item.get("manual_product_id")
        pid_s = f" id={pid}" + (" (reczne)" if manual and pid else "") if pid else ""
        attach_lbl = item.get("_attach_label")
        if attach_lbl:
            return {
                "attach_preview": f"Dodaj preview{pid_s}",
                "zoom_hd_r2": f"Zoom HD -> R2{pid_s}",
                "attach_mockups": f"Dodaj mockupy{pid_s}",
                "attach_full_kit": f"Caly komplet{pid_s}",
            }.get(str(attach_lbl), str(attach_lbl))
        if action == "skip" and manual and pid:
            role = item.get("image_role")
            if role == IMAGE_ROLE_FULL:
                return f"Dogrywka Full{pid_s}"
            if role == IMAGE_ROLE_PREVIEW:
                return f"Dogrywka preview{pid_s}"
            if item.get("follow_up_number") is not None:
                return f"Dogrywka F/I{pid_s}"
        return {
            "create": "Utworz nowy",
            "force_create": f"Utworz mimo to{pid_s}",
            "replace_image": f"Podmien zdjecie{pid_s}",
            "replace_image_and_description": f"Podmien obraz+opis{pid_s}",
            "attach_preview": f"Dodaj preview{pid_s}",
            "zoom_hd_r2": f"Zoom HD -> R2{pid_s}",
            "attach_mockups": f"Dodaj mockupy{pid_s}",
            "skip": f"Pomin{pid_s}" if pid_s else "Pomin",
        }.get(action, action)

    def _queue_tree_font(self) -> tkfont.Font:
        f = getattr(self, "_queue_tv_font", None)
        if f is None:
            spec = ttk.Style(self.root).lookup("Treeview", "font")
            try:
                if spec:
                    self._queue_tv_font = tkfont.Font(self.root, font=spec)
                else:
                    self._queue_tv_font = tkfont.nametofont("TkDefaultFont")
            except tk.TclError:
                self._queue_tv_font = tkfont.nametofont("TkDefaultFont")
            f = self._queue_tv_font
        return f

    def _queue_col_text_width(self, text: str) -> int:
        t = text.replace("\n", " ") if text else ""
        if not t.strip():
            t = " "
        return self._queue_tree_font().measure(t)

    def _row_values(self, item: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
        fnum = item["follow_up_number"]
        fkind = item.get("follow_up_kind")
        corr = item.get("correction_suffix")
        role = item.get("image_role")
        if role == IMAGE_ROLE_PREVIEW:
            mode = "Podglad (preview)"
        elif role == IMAGE_ROLE_FULL:
            mode = "Full (galeria)"
        elif role == IMAGE_ROLE_MOCKUP:
            mode = "Mockup"
        elif fnum is not None and fkind == FOLLOW_UP_KIND_I:
            mode = f"Dogrywka I{fnum}"
        elif fnum:
            mode = f"Dogrywka F{fnum}"
        else:
            mode = "Nowy produkt"
        if corr:
            mode = f"{mode} ({corr})"
        if fnum is not None or role in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_FULL, IMAGE_ROLE_MOCKUP):
            lang = "-"
        else:
            lang = "polski" if item["title_is_polish"] else "OBCY (do tlumacz.)"
            if item.get("title_is_polish_manual"):
                lang = f"{lang} *"
        return (
            item["path"].name,
            item["artist"],
            item["title"],
            mode,
            lang,
            self._describe_action(item),
        )

    def _autosize_queue_columns(self) -> None:
        if not self.queue_items:
            self._equalize_queue_columns()
            return
        for i, col in enumerate(self._queue_col_ids):
            header = self._queue_heading_text[col]
            parts: list[str] = [header]
            for item in self.queue_items:
                parts.append(self._row_values(item)[i])
            wpx = max(self._queue_col_text_width(p) for p in parts) + _QUEUE_COL_PAD
            wpx = max(_MIN_QUEUE_COL_WIDTH, min(wpx, _MAX_QUEUE_COL_WIDTH))
            self.tree.column(
                col,
                width=wpx,
                minwidth=_MIN_QUEUE_COL_WIDTH,
                stretch=(col == _QUEUE_STRETCH_COL),
            )
        self.root.after_idle(self._fit_window_to_content)

    def _on_tree_configure(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self.queue_items:
            self._equalize_queue_columns()

    def _equalize_queue_columns(self) -> None:
        """Pusta kolejka: podziel szerokosc Treeview rowno miedzy kolumny."""
        self.root.update_idletasks()
        try:
            tree_w = self.tree.winfo_width()
        except tk.TclError:
            tree_w = 0
        n = len(self._queue_col_ids)
        if tree_w < 40 * n:
            # jeszcze przed renderem — uzyj szerokosci Treeview z list_frame
            try:
                tree_w = max(self._list_frame.winfo_width() - 180, 40 * n)
            except tk.TclError:
                tree_w = 40 * n
        share = max(_MIN_QUEUE_COL_WIDTH, tree_w // n)
        for col in self._queue_col_ids:
            self.tree.column(
                col,
                width=share,
                minwidth=_MIN_QUEUE_COL_WIDTH,
                stretch=True,
            )

    def _needed_window_width(self) -> int:
        """Szerokosc okna wynikajaca z zawartosci (gl. kolejki plikow)."""
        try:
            sum_cols = sum(int(self.tree.column(c, "width")) for c in self._queue_col_ids)
        except (tk.TclError, ValueError, AttributeError):
            sum_cols = _MIN_QUEUE_COL_WIDTH * len(self._queue_col_ids)
        scroll_w = 18
        try:
            if self._tree_scroll.winfo_exists() and self._tree_scroll.winfo_width() > 1:
                scroll_w = self._tree_scroll.winfo_width()
        except tk.TclError:
            pass
        try:
            btns_w = self._queue_btns_frame.winfo_reqwidth()
        except tk.TclError:
            btns_w = 130
        if btns_w <= 1:
            btns_w = 130
        # Wiersz list_frame: tree padx 6 | kolumny | scrollbar | 4 | przyciski | 6
        inner = 6 + sum_cols + scroll_w + 4 + btns_w + 6
        # Marginesy: ramka LabelFrame (padx=10 dwa razy) + padding okna
        extra = 48
        return inner + extra

    def _fit_window_to_content(self, *, shrink: bool = False) -> None:
        """Dopasowuje szerokosc (i opcjonalnie wysokosc) okna do zawartosci.

        shrink=False: tylko poszerza okno jesli tresc sie nie miesci (po dodaniu plikow).
        shrink=True: ustawia startowa szerokosc i wysokosc dokladnie pod zawartosc.
        """
        if not getattr(self, "_list_frame", None):
            return
        self.root.update_idletasks()
        need_w = self._needed_window_width()
        try:
            req_w = self.root.winfo_reqwidth()
        except tk.TclError:
            req_w = need_w
        need_w = max(need_w, req_w)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        mn_w, mn_h = 640, 560
        try:
            mn_w, mn_h = self.root.minsize()  # type: ignore[assignment]
        except (tk.TclError, ValueError):
            pass
        need_w = max(mn_w, min(need_w, screen_w - 40))
        try:
            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
        except tk.TclError:
            return
        new_w = need_w if (shrink or cur_w < need_w) else cur_w
        new_h = cur_h
        if shrink:
            try:
                req_h = self.root.winfo_reqheight()
            except tk.TclError:
                req_h = cur_h
            new_h = max(mn_h, min(req_h, screen_h - 80))
        if new_w != cur_w or new_h != cur_h:
            self.root.geometry(f"{new_w}x{new_h}")

    def _refresh_tree(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for item in self.queue_items:
            self.tree.insert("", "end", values=self._row_values(item))
        self._autosize_queue_columns()

    def _iids(self) -> list[str]:
        return list(self.tree.get_children())

    def _refresh_pair_status(self) -> None:
        miss = audit_preview_full_pairs(self.queue_items)
        summary = format_pair_status(self.queue_items)
        self.pair_status_var.set(summary)
        if miss:
            self.pair_status_lbl.configure(foreground="#a33")
        elif self.queue_items:
            self.pair_status_lbl.configure(foreground="#0a6")
        else:
            self.pair_status_lbl.configure(foreground="#666")

    def _show_missing_pairs_dialog(self, missing: list[str]) -> None:
        body = (
            "Kazde dzielo w kolejce (ten sam artysta i tytul bazowy) musi miec\n"
            "plik preview oraz plik Full.\n\n"
            + "\n".join(missing[:24])
        )
        if len(missing) > 24:
            body += f"\n... i {len(missing) - 24} kolejnych."
        messagebox.showwarning(APP_TITLE, body)

    def _refresh_counts_and_status(self) -> None:
        n_prev = sum(1 for it in self.queue_items if it.get("image_role") == IMAGE_ROLE_PREVIEW)
        n_full = sum(1 for it in self.queue_items if it.get("image_role") == IMAGE_ROLE_FULL)
        n_other = len(self.queue_items) - n_prev - n_full
        n_new = sum(
            1
            for it in self.queue_items
            if it["follow_up_number"] is None and it.get("image_role") != IMAGE_ROLE_PREVIEW
        )
        self.counts_var.set(
            f"{len(self.queue_items)} pl.: preview {n_prev}, Full {n_full}, pozost. {n_other}"
        )
        self._refresh_pair_status()
        if not self.queue_items:
            self.status_var.set("Gotowy. Dodaj preview + Full dla kazdego dziela.")
            self.create_btn.configure(text="Utworz wszystko", state="normal")
        else:
            parts = []
            if n_new:
                parts.append(f"{n_new} do LLM")
            miss = audit_preview_full_pairs(self.queue_items)
            if miss:
                parts.append(f"brak pary: {len(miss)}")
            self.create_btn.configure(
                text=f"Utworz wszystko ({'+'.join(parts)})" if parts else "Utworz wszystko",
                state="normal",
            )
            if miss:
                self.status_var.set(
                    f"Brakuje preview lub Full dla {len(miss)} dziel — uzupelnij kolejke."
                )
            else:
                self.status_var.set("Komplet preview+Full — mozesz tworzyc w Shopify.")

    def _has_new_items(self) -> bool:
        return bool(dedupe_queue_items_by_work(self.queue_items))

    @staticmethod
    def _item_needs_precheck_action(item: dict[str, Any]) -> bool:
        """Tylko pozycje tworzace/aktualizujace produkt (JSON) — nie preview/mockup/dogrywki."""
        if item.get("follow_up_number") is not None:
            return False
        if item.get("image_role") in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_MOCKUP):
            return False
        return "action" not in item

    # ---------------------- Prompt / JSON ----------------------
    def _generate_prompt(self, *, model: str | None = None) -> None:
        if model is not None:
            self._prompt_model = model
        target_model = self._prompt_model or "opus"
        prompt_items = dedupe_items_for_prompt(self.queue_items)
        if not prompt_items:
            self._prompt_chunks = []
            self._rebuild_prompt_chunk_buttons()
            self._reset_json_parts(0)
            self.prompt_text.configure(state="normal")
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert(
                "1.0",
                "[Brak dziel do opisu] Prompt LLM niepotrzebny — same preview/mockup/dogrywki.",
            )
            self.prompt_text.configure(state="disabled")
            self.prompt_model_var.set("")
            return

        self._prompt_chunks = build_all_prompt_chunks(prompt_items, model=target_model)
        label = "Opus (Claude)" if target_model == "opus" else "GPT"
        self.prompt_model_var.set(f"Wariant: {label}")

        multi = len(self._prompt_chunks) > 1
        self._rebuild_prompt_chunk_buttons(len(prompt_items))
        self._reset_json_parts(len(self._prompt_chunks) if multi else 0)

        if multi:
            self._show_prompt_part(1)
            self.status_var.set(
                f"Prompt ({label}) — {len(prompt_items)} dziel w {len(self._prompt_chunks)} "
                f"czesciach. Kopiuj prompt → LLM → «Wklej czesc …» w Kroku 2."
            )
        else:
            prompt = self._prompt_chunks[0][2] if self._prompt_chunks else ""
            self.prompt_text.configure(state="normal")
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", prompt)
            self.prompt_text.configure(state="disabled")
            self.status_var.set(
                f"Prompt ({label}) — {len(prompt_items)} dziel "
                f"({len(self.queue_items)} plik(ow) w kolejce)."
            )
            self._copy_prompt()

    def _rebuild_prompt_chunk_buttons(self, work_count: int = 0) -> None:
        for w in self.prompt_chunks_btn_frame.winfo_children():
            w.destroy()
        chunks = self._prompt_chunks
        if len(chunks) <= 1:
            self.prompt_chunks_outer.pack_forget()
            return

        self.prompt_chunks_outer.pack(fill="x", padx=6, pady=(0, 6))
        self.prompt_chunks_summary_var.set(
            f"{work_count} dziel → {len(chunks)} osobnych promptow "
            f"(max {PROMPT_CHUNK_SIZE} obrazy na request). "
            f"Wyslij kazda czesc osobno do LLM, potem w Kroku 2: «Wklej czesc …» (auto-scalanie)."
        )
        part_labels = [str(i) for i in range(1, len(chunks) + 1)]
        self.prompt_part_combo.configure(values=part_labels)
        self.prompt_part_var.set("1")

        for part_no, part_total, text in chunks:
            ttk.Button(
                self.prompt_chunks_btn_frame,
                text=f"Kopiuj czesc {part_no}/{part_total}",
                command=lambda t=text, p=part_no, pt=part_total: self._copy_prompt_chunk(t, p, pt),
            ).pack(side="left", padx=(0, 6), pady=2)

    def _show_prompt_part(self, part_no: int) -> None:
        idx = part_no - 1
        if idx < 0 or idx >= len(self._prompt_chunks):
            return
        part_no, part_total, text = self._prompt_chunks[idx]
        header = (
            f"--- PODGLAD CZESCI {part_no}/{part_total} "
            f"(uzyj przycisku «Kopiuj czesc {part_no}/{part_total}») ---\n\n"
        )
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", header + text)
        self.prompt_text.configure(state="disabled")

    def _on_prompt_part_selected(self, _event: tk.Event | None = None) -> None:
        try:
            part_no = int(self.prompt_part_var.get())
        except ValueError:
            return
        self._show_prompt_part(part_no)

    def _copy_prompt_chunk(self, text: str, part_no: int, part_total: int) -> None:
        if not text.strip():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._show_copy_toast(f"Skopiowano czesc {part_no}/{part_total} promptu do schowka.")

    def _reset_json_parts(self, expected: int) -> None:
        self._json_parts_expected = max(0, int(expected))
        self._json_parts = {}
        if self._json_parts_expected > 1:
            self.json_text.delete("1.0", "end")
            self.json_text.insert(
                "1.0",
                f"[Oczekuje na odpowiedzi LLM — uzyj przyciskow «Wklej czesc 1/{self._json_parts_expected}» … "
                f"ponizej. Po kazdym wklejeniu tablica scala sie automatycznie.]",
            )
        self._rebuild_json_paste_buttons()

    def _rebuild_json_paste_buttons(self) -> None:
        for w in self.json_parts_btn_frame.winfo_children():
            w.destroy()
        total = self._json_parts_expected
        if total <= 1:
            self.json_parts_outer.pack_forget()
            return
        self.json_parts_outer.pack(fill="x", padx=6, pady=(6, 0), before=self.json_text)
        self._update_json_parts_summary()
        for part_no in range(1, total + 1):
            done = part_no in self._json_parts
            label = f"Wklej czesc {part_no}/{total}" + (" ✓" if done else "")
            ttk.Button(
                self.json_parts_btn_frame,
                text=label,
                command=lambda p=part_no: self._paste_json_part(p),
            ).pack(side="left", padx=(0, 6), pady=2)

    def _update_json_parts_summary(self) -> None:
        total = self._json_parts_expected
        if total <= 1:
            return
        filled = len(self._json_parts)
        merged = merge_json_part_lists(self._json_parts, total_parts=total)
        self.json_parts_summary_var.set(
            f"Odpowiedzi LLM: {filled}/{total} czesci wklejone, lacznie {len(merged)} obiektow w polu ponizej."
        )

    def _merge_json_parts_to_field(self) -> int:
        total = self._json_parts_expected
        if total <= 1:
            return 0
        merged = merge_json_part_lists(self._json_parts, total_parts=total)
        self.json_text.delete("1.0", "end")
        if merged:
            self.json_text.insert("1.0", format_merged_json(merged))
        else:
            self.json_text.insert(
                "1.0",
                f"[Brak wklejonych czesci — uzyj «Wklej czesc 1/{total}» …]",
            )
        self.json_text.see("1.0")
        self._update_json_parts_summary()
        return len(merged)

    def _paste_json_part(self, part_no: int) -> None:
        total = self._json_parts_expected
        if total <= 1:
            self._paste_clipboard_into_json()
            return
        try:
            raw = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(APP_TITLE, "Schowek jest pusty.")
            return
        if not raw or not raw.strip():
            messagebox.showwarning(APP_TITLE, "Schowek jest pusty.")
            return
        try:
            items = parse_batch_response_json(raw)
        except ValueError as e:
            messagebox.showerror(
                APP_TITLE,
                f"Niepoprawna odpowiedz dla czesci {part_no}/{total}:\n{e}",
            )
            return
        self._json_parts[part_no] = items
        count = self._merge_json_parts_to_field()
        self._rebuild_json_paste_buttons()
        filled = len(self._json_parts)
        msg = f"Czesc {part_no}/{total}: {len(items)} obiektow. Lacznie {count} w polu JSON."
        if filled == total:
            msg += " — wszystkie czesci gotowe."
        self._show_copy_toast(msg)

    def _clear_json_parts(self) -> None:
        if self._json_parts_expected <= 1:
            self.json_text.delete("1.0", "end")
            return
        self._json_parts = {}
        self._merge_json_parts_to_field()
        self._rebuild_json_paste_buttons()
        self._show_copy_toast("Wyczyszczono wklejone czesci JSON.")

    def _on_step1_click(self, event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Klik w obszar Kroku 1 kopiuje prompt do schowka."""
        self._copy_prompt()

    def _paste_clipboard_into_json(self) -> None:
        try:
            data = self.root.clipboard_get()
        except tk.TclError:
            return
        if not data or not data.strip():
            return
        if self._json_parts_expected > 1:
            messagebox.showinfo(
                APP_TITLE,
                f"Masz {self._json_parts_expected} czesci promptu — uzyj przyciskow "
                f"«Wklej czesc 1/{self._json_parts_expected}» itd. (auto-scalanie).",
            )
            return
        self.json_text.delete("1.0", "end")
        self.json_text.insert("1.0", data)
        self.json_text.see("1.0")
        self._show_copy_toast("Wklejono JSON ze schowka.")

    def _on_step2_click(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Klik w obszar Kroku 2 wkleja schowek (pojedynczy JSON lub pierwsza pusta czesc)."""
        if self._json_parts_expected > 1:
            for part_no in range(1, self._json_parts_expected + 1):
                if part_no not in self._json_parts:
                    self._paste_json_part(part_no)
                    return
            self._paste_clipboard_into_json()
            return
        self._paste_clipboard_into_json()

    def _json_field_is_placeholder(self) -> bool:
        raw = self.json_text.get("1.0", "end").strip()
        return not raw or raw.startswith("[Oczekuje") or raw.startswith("[Brak wklejonych")

    def _on_json_text_click(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Klik w pole JSON: jesli puste / placeholder, wklej (lub pierwsza brakujaca czesc)."""
        if self._json_parts_expected > 1:
            if not self._json_field_is_placeholder():
                return
            for part_no in range(1, self._json_parts_expected + 1):
                if part_no not in self._json_parts:
                    self._paste_json_part(part_no)
                    return
            return
        if not self.json_text.get("1.0", "end").strip():
            self._paste_clipboard_into_json()

    def _copy_prompt(self) -> None:
        if len(self._prompt_chunks) > 1:
            try:
                part_no = int(self.prompt_part_var.get())
            except ValueError:
                part_no = 1
            idx = part_no - 1
            if 0 <= idx < len(self._prompt_chunks):
                _pno, ptotal, text = self._prompt_chunks[idx]
                self._copy_prompt_chunk(text, part_no, ptotal)
            return
        txt = self.prompt_text.get("1.0", "end").strip()
        if not txt:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self._show_copy_toast(self._copy_prompt_toast_message(txt))

    def _copy_prompt_toast_message(self, copied_txt: str) -> str:
        """Tekst toasta po skopiowaniu promptu: Opus / GPT albo informacja bez LLM."""
        if "[Brak nowych produktow w kolejce]" in copied_txt[:160]:
            return "Skopiowano do schowka (bez promptu LLM — w kolejce tylko dogrywki)."
        m = self._prompt_model or "opus"
        label = "Opus" if m == "opus" else "GPT"
        return f"Skopiowano do schowka — {label}."

    def _cancel_copy_toast(self) -> None:
        for aid in self._toast_after_ids:
            try:
                self.root.after_cancel(aid)
            except (tk.TclError, ValueError):
                pass
        self._toast_after_ids.clear()
        w = self._toast_win
        self._toast_win = None
        if w is not None:
            try:
                if w.winfo_exists():
                    w.destroy()
            except tk.TclError:
                pass

    def _show_copy_toast(self, message: str = "Skopiowano do schowka.") -> None:
        self._cancel_copy_toast()
        win = tk.Toplevel(self.root)
        self._toast_win = win
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        lbl = tk.Label(
            win,
            text=message,
            bg="#2d2d2d",
            fg="#ffffff",
            font=("Segoe UI", 10),
            padx=20,
            pady=12,
        )
        lbl.pack()
        win.update_idletasks()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        ww = win.winfo_reqwidth()
        wh = win.winfo_reqheight()
        x = rx + max(0, (rw - ww) // 2)
        y = ry + rh - wh - 36
        win.geometry(f"+{x}+{y}")

        use_alpha = True
        try:
            win.attributes("-alpha", 0.0)
        except tk.TclError:
            use_alpha = False

        def close_toast() -> None:
            try:
                if win.winfo_exists():
                    win.destroy()
            except tk.TclError:
                pass
            if self._toast_win is win:
                self._toast_win = None

        n_in = 6

        def fade_in(i: int) -> None:
            if not win.winfo_exists():
                return
            if use_alpha:
                try:
                    win.attributes("-alpha", (i + 1) / n_in)
                except tk.TclError:
                    pass
            if i + 1 < n_in:
                self._toast_after_ids.append(self.root.after(28, lambda: fade_in(i + 1)))
            else:
                self._toast_after_ids.append(self.root.after(1200, lambda: fade_out(1)))

        n_out = 10

        def fade_out(i: int) -> None:
            if not win.winfo_exists():
                return
            if use_alpha:
                try:
                    win.attributes("-alpha", max(0.0, 1.0 - i / n_out))
                except tk.TclError:
                    pass
            if i < n_out:
                self._toast_after_ids.append(self.root.after(32, lambda j=i + 1: fade_out(j)))
            else:
                close_toast()

        if use_alpha:
            fade_in(0)
        else:
            self._toast_after_ids.append(self.root.after(1500, close_toast))

    # ---------------------- Pasek postepu ----------------------
    def _reset_batch_progress(self) -> None:
        self.batch_progress_var.set(0.0)
        self.batch_progress_label_var.set("")
        self._reset_zoom_progress()

    def _reset_zoom_progress(self) -> None:
        self.zoom_progress_var.set(0.0)
        self.zoom_progress_label_var.set("")
        self._reset_zoom_timing()

    def _reset_zoom_timing(self) -> None:
        with self._zoom_timing_lock:
            self._zoom_timing_active.clear()
            self._zoom_timing_agg = {"tiles": 0.0, "upload": 0.0, "shopify": 0.0, "n": 0}
            self._zoom_last_timing = None
        self.zoom_timing_var.set("")

    def _refresh_zoom_timing_label(self) -> None:
        with self._zoom_timing_lock:
            active = dict(self._zoom_timing_active)
            agg = dict(self._zoom_timing_agg)
            last = dict(self._zoom_last_timing) if self._zoom_last_timing else None
        parts: list[str] = []
        if active:
            act_txt = ", ".join(
                f"{fn if len(fn) <= 22 else fn[:19] + '…'}: {ph}"
                for fn, ph in list(active.items())[:3]
            )
            if len(active) > 3:
                act_txt += f" (+{len(active) - 3})"
            parts.append(f"W toku: {act_txt}")
        if last and last.get("phase") == "done":
            short = last.get("file") or ""
            if len(short) > 24:
                short = short[:21] + "…"
            line = format_timing_line(
                tiles_s=last.get("tiles_s"),
                upload_s=last.get("upload_s"),
                shopify_s=last.get("shopify_s"),
            )
            if short:
                parts.append(f"Ostatni ({short}): {line}")
            else:
                parts.append(line)
        n = int(agg.get("n") or 0)
        if n > 0:
            parts.append(
                f"Średnio ({n}): kafelki {agg['tiles'] / n:.1f}s · "
                f"R2 {agg['upload'] / n:.1f}s · Shopify {agg['shopify'] / n:.1f}s"
            )
        self.zoom_timing_var.set("  |  ".join(parts) if parts else "")

    def _apply_zoom_timing(self, info: dict[str, Any]) -> None:
        phase = str(info.get("phase") or "")
        fn = str(info.get("file") or "").strip()
        with self._zoom_timing_lock:
            if phase == "tiles" and fn:
                self._zoom_timing_active[fn] = "kafelki"
            elif phase == "upload" and fn:
                self._zoom_timing_active[fn] = "R2"
            elif phase == "done" and fn:
                self._zoom_timing_active.pop(fn, None)
                ts = float(info.get("tiles_s") or 0)
                us = float(info.get("upload_s") or 0)
                ss = float(info.get("shopify_s") or 0)
                self._zoom_timing_agg["tiles"] += ts
                self._zoom_timing_agg["upload"] += us
                self._zoom_timing_agg["shopify"] += ss
                self._zoom_timing_agg["n"] += 1
                self._zoom_last_timing = dict(info)
        self._refresh_zoom_timing_label()

    def _enqueue_zoom_timing(self, info: dict[str, Any]) -> None:
        self.root.after(0, lambda i=dict(info): self._apply_zoom_timing(i))

    def _set_zoom_progress(self, done: int, total: int, label: str) -> None:
        if total <= 0:
            pct = 0.0
            text = label or ""
        else:
            pct = min(100.0, (done / total) * 100.0)
            short = label if len(label) <= 28 else label[:25] + "..."
            text = f"{done}/{total}" + (f" — {short}" if short else "")
        self.zoom_progress_var.set(pct)
        self.zoom_progress_label_var.set(text)

    def _enqueue_zoom_progress(self, done: int, total: int, label: str) -> None:
        self.root.after(0, lambda d=done, t=total, lb=label: self._set_zoom_progress(d, t, lb))

    def _zoom_progress_callbacks(self, fname: str) -> tuple[
        Callable[[int, int, str], None],
        Callable[[dict[str, Any]], None],
    ]:
        """Postep i czasy dla jednego pliku zoom (batch rownolegly)."""

        def on_progress(done: int, total: int, label: str) -> None:
            self._enqueue_zoom_progress(done, total, f"{fname}: {label}")

        def on_timing(info: dict[str, Any]) -> None:
            payload = dict(info)
            if fname and not payload.get("file"):
                payload["file"] = fname
            self._enqueue_zoom_timing(payload)

        return on_progress, on_timing

    def _refresh_r2_usage(self) -> None:
        self.r2_usage_var.set("R2: sprawdzam...")

        def worker() -> None:
            try:
                snap = collect_r2_usage()
                text = format_usage_line(snap)
            except Exception as exc:
                text = f"R2: niedostepne ({exc})"

            self.root.after(0, lambda t=text: self.r2_usage_var.set(t))

        threading.Thread(target=worker, daemon=True).start()

    def _show_cloudflare_dialog(self) -> None:
        open_cloudflare_usage_dialog(self.root)

    def _show_r2_usage_help(self) -> None:
        messagebox.showinfo(
            APP_TITLE,
            "Zużycie Cloudflare R2\n\n"
            "• Magazyn — ile danych jest w buckecie (limit domyslnie 10 GB / mies. na free tier).\n"
            "• zoom/ — tylko kafelki Zoom HD.\n"
            "• Egress (transfer do odwiedzajacych) z R2 i r2.dev jest u Cloudflare bezplatny.\n"
            "• Operacje A/B — zapisy i odczyty API (wymaga CLOUDFLARE_API_TOKEN w .env).\n"
            "• „~N kolejnych zoomow” — z wolnego miejsca i sredniej z ostatnich uploadow\n"
            "  (historia w aplikacji lub dziela w R2; domyslnie ~450 MB).\n\n"
            "Opcjonalnie w .env:\n"
            "  R2_STORAGE_QUOTA_GB=10\n"
            "  R2_ZOOM_ESTIMATE_MB=450\n"
            "  R2_CLASS_A_QUOTA=1000000\n"
            "  R2_CLASS_B_QUOTA=10000000\n"
            "  R2_UPLOAD_WORKERS=12  (rownolegle kafelki na produkt)\n"
            "  R2_ZOOM_PARALLEL=3    (ile zoomow naraz przy batchu)\n"
            "  CLOUDFLARE_API_TOKEN=... (Analytics / R2 Read)\n\n"
            "Pod paskiem Zoom HD widać czas: kafelki (CPU) vs R2 vs Shopify.",
        )

    def _set_batch_progress(self, done: int, total: int, label: str) -> None:
        if total <= 0:
            pct = 0.0
            text = label or ""
        else:
            pct = min(100.0, (done / total) * 100.0)
            short = label if len(label) <= 28 else label[:25] + "..."
            text = f"{done}/{total}" + (f" — {short}" if short else "")
        self.batch_progress_var.set(pct)
        self.batch_progress_label_var.set(text)

    def _enqueue_batch_progress(self, done: int, total: int, label: str) -> None:
        self.root.after(0, lambda d=done, t=total, lb=label: self._set_batch_progress(d, t, lb))

    def _zoom_batch_offer_count(self) -> int:
        """Ile plikow Full mozna by dodac do zoom przy batchu (wymaga R2 w .env)."""
        if not self._zoom_full_items():
            return 0
        try:
            from .r2_storage import load_r2_config

            load_r2_config()
        except Exception:
            return 0
        return len(self._zoom_full_items())

    def _ask_zoom_with_batch(self, n: int) -> bool:
        return messagebox.askyesno(
            APP_TITLE,
            f"Dla {n} plik(ow) Full przygotowac rowniez Zoom HD -> R2?\n\n"
            "Kafelki + upload R2 + szablon: nowy-szblon-produktu.\n\n"
            "Tak = Shopify i zoom rownolegle (szybciej).\n"
            "Nie = tylko operacje Shopify.",
        )

    def _new_zoom_batch_coordinator(
        self,
        *,
        run_zoom: bool,
        zoom_names: set[str],
        executor: ThreadPoolExecutor,
    ) -> dict[str, Any]:
        """Planuje zoom w tle (rownolegle produkty — R2_ZOOM_PARALLEL w .env)."""
        scheduled: set[str] = set()
        lock = threading.Lock()
        done_count = [0]
        stats = {"ok": 0, "err": 0, "total": len(zoom_names)}

        def schedule(
            item: dict[str, Any],
            product_id: int,
            handle: str | None = None,
        ) -> None:
            if not run_zoom or not zoom_names:
                return
            fname = item["path"].name
            if fname not in zoom_names:
                return
            with lock:
                if fname in scheduled:
                    return
                scheduled.add(fname)

            zitem = dict(item)
            zitem["existing_product_id"] = int(product_id)
            if handle:
                zitem["handle"] = handle

            def job() -> None:
                on_prog, on_time = self._zoom_progress_callbacks(fname)
                try:
                    publish_zoom_for_queue_item(
                        zitem,
                        logger=self._enqueue_log,
                        on_progress=on_prog,
                        on_timing=on_time,
                    )
                    stats["ok"] += 1
                except Exception as exc:
                    stats["err"] += 1
                    self._enqueue_log(f"[zoom] BLAD {fname}: {exc}")
                finally:
                    done_count[0] += 1
                    self._enqueue_zoom_progress(done_count[0], stats["total"], fname)

            executor.submit(job)

        def flush_remaining(
            items: list[dict[str, Any]],
            summary: dict[str, Any] | None = None,
        ) -> None:
            pid_by_file: dict[str, int] = {}
            handle_by_file: dict[str, str] = {}
            if summary:
                for r in (summary.get("created") or []) + (summary.get("followed_up") or []):
                    fn = (r.get("file") or "").strip()
                    pid = r.get("product_id")
                    if fn and pid:
                        pid_by_file[fn] = int(pid)
                        h = (r.get("handle") or "").strip()
                        if h:
                            handle_by_file[fn] = h
            for it in items:
                fname = it["path"].name
                if fname not in zoom_names:
                    continue
                pid = it.get("existing_product_id") or pid_by_file.get(fname)
                if not pid:
                    continue
                schedule(
                    it,
                    int(pid),
                    it.get("handle") or handle_by_file.get(fname),
                )

        return {"schedule": schedule, "flush": flush_remaining, "stats": stats}

    # ---------------------- Live precheck (on add) ----------------------
    def _apply_precheck_skip(
        self,
        item: dict[str, Any],
        existing: dict[str, Any] | None = None,
    ) -> None:
        """Pomin plik; przy znanym produkcie zostaw id (np. pod Zoom HD)."""
        item["action"] = "skip"
        if existing and existing.get("id"):
            item["existing_product_id"] = int(existing["id"])
        else:
            item["existing_product_id"] = None

    def _kick_precheck(self, items: list[dict[str, Any]]) -> None:
        """Odpala w tle sprawdzenie, czy produkt juz istnieje w Shopify.

        Po zakonczeniu w watku glownym pokazuje modale i zapisuje wybrana akcje na pozycji.
        """
        self._precheck_skip_all = False
        total = len(items)
        self._reset_batch_progress()
        self.status_var.set(f"Sprawdzam Shopify w tle ({total} plik(ow))...")

        def worker() -> None:
            artist_cache: dict[str, list[dict[str, Any]]] = {}
            results: list[tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None]] = []
            for idx, it in enumerate(items, start=1):
                self._enqueue_batch_progress(idx - 1, total, it["path"].name)
                try:
                    existing = find_existing_product_for_new(
                        artist=it["artist"],
                        filename_title=it.get("base_title") or it["title"],
                        polish_title=None,
                        logger=self._enqueue_log,
                    )
                except Exception as e:
                    self._enqueue_log(f"[precheck] {it['path'].name}: {e}")
                    existing = None

                candidates: list[dict[str, Any]] | None = None
                if existing is None and not it.get("title_is_polish", True):
                    key = it["artist"].strip().lower()
                    if key in artist_cache:
                        candidates = artist_cache[key]
                    else:
                        try:
                            candidates = get_artist_products(it["artist"], logger=self._enqueue_log)
                        except Exception as e:
                            self._enqueue_log(f"[precheck] artist products: {e}")
                            candidates = []
                        artist_cache[key] = candidates or []
                    if not candidates:
                        candidates = None
                results.append((it, existing, candidates))
                self._enqueue_batch_progress(idx, total, it["path"].name)
            self.root.after(0, lambda: self._on_precheck_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _on_precheck_done(
        self,
        results: list[tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None]],
    ) -> None:
        for it, existing, candidates in results:
            if it not in self.queue_items:
                continue  # user usunal go z kolejki w miedzyczasie
            it.pop("_precheck_started", None)
            self._resolve_item_interactive(it, existing, candidates)
            self._refresh_tree()
        self._refresh_counts_and_status()

    def _resolve_item_interactive(
        self,
        item: dict[str, Any],
        existing: dict[str, Any] | None,
        candidates: list[dict[str, Any]] | None,
    ) -> None:
        """Pokazuje modale (jesli trzeba) i zapisuje 'action' + 'existing_product_id' na pozycji."""
        if self._precheck_skip_all:
            self._apply_precheck_skip(item, existing)
            return

        target = existing
        if target is None and candidates:
            picked = self._ask_artist_product_picker(item, candidates)
            if picked == "skip":
                self._apply_precheck_skip(item, existing)
                return
            if picked in (None, "create_new"):
                item["action"] = "create"
                return
            target = picked  # type: ignore[assignment]

        if target is None:
            item["action"] = "create"
            return

        choice = self._ask_existing_product_action(item, target)
        if choice is None:
            self._apply_precheck_skip(item, target)
        elif choice in ("attach_preview", "zoom_hd_r2", "attach_mockups", "attach_full_kit"):
            item["existing_product_id"] = int(target.get("id") or 0) or None
            item["handle"] = (target.get("handle") or "").strip()
            item["action"] = "skip"
            item["_attach_label"] = choice
            self._run_existing_product_attach(item, target, choice)
        else:
            item["action"] = choice
            item["existing_product_id"] = int(target.get("id") or 0) or None

    def _work_key(self, item: dict[str, Any]) -> tuple[str, str]:
        artist = (item.get("artist") or "").strip()
        base = (item.get("base_title") or item.get("title") or "").strip()
        return artist, base

    def _queue_items_same_work(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        key = self._work_key(item)
        return [it for it in self.queue_items if self._work_key(it) == key]

    def _find_queue_item_by_role(
        self, item: dict[str, Any], role: str
    ) -> dict[str, Any] | None:
        if item.get("image_role") == role:
            return item
        for it in self._queue_items_same_work(item):
            if it.get("image_role") == role:
                return it
        return None

    def _run_existing_product_attach(
        self,
        item: dict[str, Any],
        existing: dict[str, Any],
        kind: str,
    ) -> None:
        """Wykonuje dogrywke preview / zoom / mockup do istniejacego produktu (z dialogu)."""
        pid = int(existing.get("id") or 0)
        handle = (existing.get("handle") or "").strip()
        if not pid:
            messagebox.showerror(APP_TITLE, "Brak id produktu Shopify.", parent=self.root)
            return

        self.status_var.set(f"Dogrywam do produktu id={pid}...")

        def work() -> None:
            err: str | None = None
            ok_msg = ""
            try:
                if kind == "attach_preview":
                    prev = self._find_queue_item_by_role(item, IMAGE_ROLE_PREVIEW)
                    if not prev:
                        raise ValueError(
                            "Brak pliku (preview) w kolejce dla tego dziela.\n"
                            "Dodaj «Artysta - Tytul - (preview).webp»."
                        )
                    res = add_preview_image(
                        image_path=prev["path"],
                        artist=prev["artist"],
                        base_title=prev.get("base_title") or prev["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    prev["existing_product_id"] = pid
                    prev["handle"] = res.get("handle") or handle
                    prev["action"] = "skip"
                    ok_msg = f"Wgrano preview do id={pid}."
                elif kind == "zoom_hd_r2":
                    full = self._find_queue_item_by_role(item, IMAGE_ROLE_FULL)
                    if not full:
                        raise ValueError(
                            "Brak pliku Full w kolejce.\n"
                            "Dodaj «Artysta - Tytul - Full.webp»."
                        )
                    full["existing_product_id"] = pid
                    full["handle"] = handle
                    add_full_image(
                        image_path=full["path"],
                        artist=full["artist"],
                        base_title=full.get("base_title") or full["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    publish_zoom_for_queue_item(
                        full,
                        logger=self._enqueue_log,
                    )
                    full["action"] = "skip"
                    ok_msg = f"Wgrano Full + zoom HD (R2) do id={pid}."
                elif kind == "attach_mockups":
                    src = self._find_queue_item_by_role(item, IMAGE_ROLE_PREVIEW)
                    if not src:
                        src = self._find_queue_item_by_role(item, IMAGE_ROLE_FULL)
                    if not src:
                        raise ValueError(
                            "Brak pliku zrodlowego (preview lub Full) w kolejce."
                        )
                    mockup_sets = self._selected_mockup_sets()
                    if not mockup_sets:
                        raise ValueError(
                            "Wlacz Mockup i wybierz szablon w glownym oknie (nad przyciskiem Utworz)."
                        )
                    from Komponenty.mockup.publish import publish_mockup

                    done = 0
                    for mockup_set in mockup_sets:
                        res = publish_mockup(
                            src["path"],
                            mockup_set,
                            product_id=pid,
                            skip_if_exists=True,
                            logger=self._enqueue_log,
                        )
                        if not res.get("skipped"):
                            done += 1
                    ok_msg = f"Dodano mockupy ({done}/{len(mockup_sets)}) do id={pid}."
                elif kind == "attach_full_kit":
                    prev = self._find_queue_item_by_role(item, IMAGE_ROLE_PREVIEW)
                    full = self._find_queue_item_by_role(item, IMAGE_ROLE_FULL)
                    if not prev:
                        raise ValueError(
                            "Brak pliku (preview) w kolejce.\n"
                            "Dodaj «Artysta - Tytul - (preview).webp»."
                        )
                    if not full:
                        raise ValueError(
                            "Brak pliku Full w kolejce.\n"
                            "Dodaj «Artysta - Tytul - Full.webp»."
                        )
                    mockup_sets = self._selected_mockup_sets()
                    if not mockup_sets:
                        raise ValueError(
                            "Wlacz Mockup i wybierz szablon w glownym oknie."
                        )
                    from Komponenty.mockup.publish import publish_mockup

                    res = add_preview_image(
                        image_path=prev["path"],
                        artist=prev["artist"],
                        base_title=prev.get("base_title") or prev["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    prev["existing_product_id"] = pid
                    prev["handle"] = res.get("handle") or handle
                    prev["action"] = "skip"
                    self._enqueue_log(f"[komplet] 1/3 preview OK id={pid}")

                    full["existing_product_id"] = pid
                    full["handle"] = handle
                    add_full_image(
                        image_path=full["path"],
                        artist=full["artist"],
                        base_title=full.get("base_title") or full["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    publish_zoom_for_queue_item(
                        full,
                        logger=self._enqueue_log,
                    )
                    full["action"] = "skip"
                    self._enqueue_log(f"[komplet] 2/3 Full + zoom HD OK id={pid}")

                    done = 0
                    for mockup_set in mockup_sets:
                        mres = publish_mockup(
                            prev["path"],
                            mockup_set,
                            product_id=pid,
                            skip_if_exists=True,
                            logger=self._enqueue_log,
                        )
                        if not mres.get("skipped"):
                            done += 1
                    self._enqueue_log(
                        f"[komplet] 3/3 mockupy {done}/{len(mockup_sets)} OK id={pid}"
                    )
                    ok_msg = (
                        f"Caly komplet gotowy (preview + Full/zoom + mockupy "
                        f"{done}/{len(mockup_sets)}) -> id={pid}."
                    )
                else:
                    raise ValueError(f"Nieznana akcja: {kind}")

                item["existing_product_id"] = pid
                item["handle"] = handle
                item["action"] = "skip"
                item.pop("_attach_label", None)
                self._enqueue_log(f"[dogrywka] {ok_msg}")
            except Exception as exc:
                err = str(exc)
                self._enqueue_log(f"[dogrywka] BLAD ({kind}) id={pid}: {exc}")

            def done_ui() -> None:
                self._refresh_tree()
                self._refresh_counts_and_status()
                if err:
                    messagebox.showerror(APP_TITLE, err, parent=self.root)
                    self.status_var.set("Blad dogrywki do produktu.")
                else:
                    self.status_var.set(ok_msg)
                    if kind in ("zoom_hd_r2", "attach_full_kit"):
                        self._refresh_r2_usage()
                    messagebox.showinfo(APP_TITLE, ok_msg, parent=self.root)

            self.root.after(0, done_ui)

        threading.Thread(target=work, daemon=True).start()

    # ---------------------- Execution ----------------------
    def _on_create_clicked(self) -> None:
        if not self.queue_items:
            messagebox.showwarning(APP_TITLE, "Kolejka jest pusta - dodaj pliki.")
            return

        missing_pairs = audit_preview_full_pairs(self.queue_items)
        if missing_pairs:
            self._show_missing_pairs_dialog(missing_pairs)
            return

        new_items = dedupe_queue_items_by_work(self.queue_items)

        pending_running = [
            it for it in self.queue_items
            if it.get("_precheck_started") and self._item_needs_precheck_action(it)
        ]
        if pending_running:
            messagebox.showinfo(
                APP_TITLE,
                f"Trwa jeszcze sprawdzanie Shopify ({len(pending_running)} plik(ow)). "
                "Poczekaj chwile i klik 'Utworz wszystko' ponownie.",
            )
            return

        unresolved = [it for it in self.queue_items if self._item_needs_precheck_action(it)]
        if unresolved:
            for it in unresolved:
                it["_precheck_started"] = True
            self._refresh_tree()
            self._kick_precheck(unresolved)
            self.status_var.set(
                "Uruchomilem sprawdzanie dla pozycji bez decyzji. "
                "Po odpowiedzi w oknach klik 'Utworz wszystko' jeszcze raz."
            )
            return

        llm_items: list[dict[str, Any]] | None = None
        if new_items:
            raw_json = self.json_text.get("1.0", "end").strip()
            if raw_json:
                try:
                    llm_items = parse_batch_response_json(raw_json)
                except ValueError as e:
                    messagebox.showerror(APP_TITLE, f"Niepoprawny JSON (tablica):\n{e}")
                    return

        llm_map: dict[str, dict[str, Any]] = {
            (it.get("plik") or "").strip(): it
            for it in (llm_items or [])
            if (it.get("plik") or "").strip()
        }

        needs_json_items = [
            it
            for it in new_items
            if (it.get("action") or "create")
            in ("create", "replace_image_and_description", "force_create")
        ]
        needs_json = [it["path"].name for it in needs_json_items]
        if needs_json and not llm_items:
            messagebox.showwarning(
                APP_TITLE,
                f"Dla {len(needs_json)} pozycji potrzebny jest JSON z LLM (krok 2):\n"
                + "\n".join(f"  - {n}" for n in needs_json)
                + "\n\nWklej tablice JSON albo zmien akcje na 'Pomin' / 'Podmien tylko zdjecie'.",
            )
            return
        if llm_items is not None:
            missing = [
                it["path"].name
                for it in needs_json_items
                if lookup_llm_entry(it, llm_map) is None
            ]
            if missing:
                if not messagebox.askyesno(
                    APP_TITLE,
                    "W JSON-ie brakuje pozycji dla:\n"
                    + "\n".join(f"  - {m}" for m in missing)
                    + "\n\nKontynuowac (te pliki beda pominiete)?",
                ):
                    return

        zoom_offer = self._zoom_batch_offer_count()
        run_zoom = bool(zoom_offer and self._ask_zoom_with_batch(zoom_offer))
        zoom_names = {it["path"].name for it in self._zoom_full_items()} if run_zoom else set()

        mockup_items = self._mockup_eligible_items()
        mockup_sets = self._selected_mockup_sets()
        run_mockup = bool(self.mockup_var.get() and mockup_items and mockup_sets)
        mockup_names = {it["path"].name for it in mockup_items} if run_mockup else set()
        mockup_label = self._mockup_variants_label(mockup_sets)

        self.create_btn.configure(state="disabled")
        self.zoom_btn.configure(state="disabled")
        self._reset_batch_progress()
        if run_zoom:
            self._reset_zoom_timing()
            self._enqueue_zoom_progress(0, len(zoom_names), "oczekuje")
        zoom_note = f" + zoom HD ({len(zoom_names)})" if run_zoom else ""
        mockup_note = (
            f" + mockup {mockup_label} ({len(mockup_names)})"
            if run_mockup and mockup_sets
            else ""
        )
        self.status_var.set(f"Przetwarzam kolejke{zoom_note}{mockup_note}... (patrz log)")
        self._append_log(
            f"\n=== BATCH START: {len(self.queue_items)} plik(ow)"
            + (f" | zoom rownolegle: {len(zoom_names)}" if run_zoom else "")
            + (
                f" | mockup rownolegle: {mockup_label} x{len(mockup_names)}"
                if run_mockup and mockup_sets
                else ""
            )
            + " ==="
        )

        enriched = [dict(it) for it in self.queue_items]

        def worker() -> None:
            parallel_workers = max(2, zoom_parallel_products_default())
            parallel_exec: ThreadPoolExecutor | None = None
            if (run_zoom and zoom_names) or (run_mockup and mockup_names):
                parallel_exec = ThreadPoolExecutor(max_workers=parallel_workers)

            zoom_coord: dict[str, Any] | None = None
            if run_zoom and zoom_names and parallel_exec:
                zoom_coord = self._new_zoom_batch_coordinator(
                    run_zoom=True,
                    zoom_names=zoom_names,
                    executor=parallel_exec,
                )
                schedule = zoom_coord["schedule"]
                for it in enriched:
                    if (it.get("action") or "").strip() != "skip":
                        continue
                    pid = it.get("existing_product_id")
                    if pid and it["path"].name in zoom_names:
                        schedule(it, int(pid), it.get("handle"))

            mockup_coord: dict[str, Any] | None = None
            if run_mockup and mockup_names and mockup_sets and parallel_exec:
                mockup_coord = self._new_mockup_batch_coordinator(
                    run_mockup=True,
                    mockup_names=mockup_names,
                    mockup_sets=mockup_sets,
                    executor=parallel_exec,
                )

            def on_product_ready(item: dict[str, Any], res: dict[str, Any]) -> None:
                pid = res.get("product_id")
                if not pid:
                    return
                handle = (res.get("handle") or "").strip() or None
                if zoom_coord:
                    zoom_coord["schedule"](item, int(pid), handle)
                if mockup_coord:
                    mockup_coord["schedule"](item, int(pid), handle)

            try:
                summary = process_batch(
                    items=enriched,
                    llm_items=llm_items,
                    logger=self._enqueue_log,
                    on_batch_progress=self._enqueue_batch_progress,
                    on_product_ready=on_product_ready if (zoom_coord or mockup_coord) else None,
                )
                if zoom_coord:
                    zoom_coord["flush"](enriched, summary)
                if mockup_coord:
                    mockup_coord["flush"](enriched, summary)
                if parallel_exec:
                    parallel_exec.shutdown(wait=True)

                created_by_file = {r.get("file"): r for r in summary.get("created") or []}
                for r in (summary.get("followed_up") or []):
                    fn = r.get("file")
                    if fn:
                        created_by_file.setdefault(fn, r)
                for it in self.queue_items:
                    hit = created_by_file.get(it["path"].name)
                    if hit:
                        it["existing_product_id"] = hit.get("product_id") or it.get(
                            "existing_product_id"
                        )
                        it["handle"] = hit.get("handle") or it.get("handle")

                if zoom_coord:
                    summary["zoom"] = dict(zoom_coord["stats"])
                if mockup_coord:
                    summary["mockup"] = dict(mockup_coord["stats"])

                def _show() -> None:
                    gaps = summary.get("collection_gaps") or []
                    self._show_batch_summary(
                        summary,
                        on_close=(lambda g=gaps: self._show_collection_fix_dialog(g)) if gaps else None,
                    )
                    msg = (
                        f"Gotowe. Utworzono/zaktualizowano {len(summary['created'])}, "
                        f"dograno/podmieniono {len(summary['followed_up'])}, "
                        f"bledow {len(summary['errors'])}."
                    )
                    z = summary.get("zoom")
                    if z:
                        msg += f" Zoom HD: OK {z.get('ok', 0)}, bledy {z.get('err', 0)}."
                    self.status_var.set(msg)

                self.root.after(0, _show)
            except Exception as exc:
                if parallel_exec:
                    parallel_exec.shutdown(wait=True)
                self._enqueue_log(f"[BLAD] {exc}")
                self.root.after(0, lambda: self.status_var.set("Blad - zobacz log."))
                self.root.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Blad:\n{e}"))
            finally:
                def _unlock() -> None:
                    self.create_btn.configure(state="normal")
                    self.zoom_btn.configure(state="normal")
                    if run_zoom:
                        zt = len(zoom_names)
                        self._set_zoom_progress(zt, zt, "Gotowe")
                    if run_zoom:
                        self._refresh_r2_usage()

                self.root.after(0, _unlock)

        threading.Thread(target=worker, daemon=True).start()

    def _selected_mockup_sets(self) -> list[MockupSet]:
        return resolve_mockup_sets(self.mockup_sets, self.mockup_set_var.get())

    def _mockup_variants_label(self, sets: list[MockupSet]) -> str:
        if len(sets) > 1:
            suffixes = ", ".join(s.name_suffix for s in sets if s.name_suffix)
            return f"wszystkie ({suffixes})" if suffixes else "wszystkie"
        if sets:
            return sets[0].name_suffix or sets[0].name
        return ""

    def _mockup_eligible_items(self) -> list[dict[str, Any]]:
        """Pliki, z ktorych mozna zlozyc mockup po utworzeniu / dogrywce produktu."""
        out: list[dict[str, Any]] = []
        for it in self.queue_items:
            if (it.get("action") or "create") == "skip":
                continue
            role = it.get("image_role")
            if role in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_MOCKUP):
                continue
            fnum = it.get("follow_up_number")
            if fnum is not None and role != IMAGE_ROLE_FULL:
                continue
            out.append(it)
        return out

    def _new_mockup_batch_coordinator(
        self,
        *,
        run_mockup: bool,
        mockup_names: set[str],
        mockup_sets: list[MockupSet],
        executor: ThreadPoolExecutor,
    ) -> dict[str, Any]:
        from Komponenty.mockup.publish import publish_mockup

        scheduled: set[str] = set()
        lock = threading.Lock()
        stats = {
            "ok": 0,
            "err": 0,
            "skip": 0,
            "total": len(mockup_names) * max(1, len(mockup_sets)),
        }

        def schedule(
            item: dict[str, Any],
            product_id: int,
            handle: str | None = None,
        ) -> None:
            if not run_mockup or not mockup_names:
                return
            fname = item["path"].name
            if fname not in mockup_names:
                return
            with lock:
                if fname in scheduled:
                    return
                scheduled.add(fname)

            def job() -> None:
                for mockup_set in mockup_sets:
                    try:
                        res = publish_mockup(
                            item["path"],
                            mockup_set,
                            product_id=int(product_id),
                            skip_if_exists=True,
                            logger=self._enqueue_log,
                        )
                        if res.get("skipped"):
                            stats["skip"] += 1
                        else:
                            stats["ok"] += 1
                            append_activity(
                                "mockup",
                                f"Dodajobraz: {fname} -> {mockup_set.name_suffix}",
                                detail=res.get("admin_url", ""),
                            )
                    except Exception as exc:
                        stats["err"] += 1
                        self._enqueue_log(
                            f"[mockup] BLAD {fname} ({mockup_set.name_suffix}): {exc}"
                        )

            executor.submit(job)

        def flush_remaining(
            items: list[dict[str, Any]],
            summary: dict[str, Any] | None = None,
        ) -> None:
            pid_by_file: dict[str, int] = {}
            handle_by_file: dict[str, str] = {}
            if summary:
                for r in (summary.get("created") or []) + (summary.get("followed_up") or []):
                    fn = (r.get("file") or "").strip()
                    pid = r.get("product_id")
                    if fn and pid:
                        pid_by_file[fn] = int(pid)
                        h = (r.get("handle") or "").strip()
                        if h:
                            handle_by_file[fn] = h
            for it in items:
                fname = it["path"].name
                if fname not in mockup_names:
                    continue
                pid = it.get("existing_product_id") or pid_by_file.get(fname)
                if not pid:
                    continue
                schedule(
                    it,
                    int(pid),
                    it.get("handle") or handle_by_file.get(fname),
                )

        return {"schedule": schedule, "flush": flush_remaining, "stats": stats}

    def _zoom_full_items(self) -> list[dict[str, Any]]:
        return [
            it
            for it in self.queue_items
            if it.get("image_role") == IMAGE_ROLE_FULL and it.get("follow_up_number") is None
        ]

    def _resolve_product_id_for_zoom(self, item: dict[str, Any]) -> int | None:
        pid = item.get("existing_product_id") or item.get("product_id")
        if pid:
            if not item.get("handle"):
                try:
                    shop, token = sc.load_session()
                    prod = sc.get_product(shop, token, int(pid))
                    if prod and prod.get("handle"):
                        item["handle"] = prod.get("handle")
                except Exception:
                    pass
            return int(pid)
        try:
            existing = find_existing_product_for_new(
                artist=item["artist"],
                filename_title=item.get("base_title") or item["title"],
                polish_title=None,
                logger=None,
            )
        except Exception:
            existing = None
        if existing and existing.get("id"):
            item["existing_product_id"] = int(existing["id"])
            item["handle"] = existing.get("handle") or item.get("handle")
            return int(existing["id"])
        return None

    def _queue_attach_items_with_product_id(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for it in self.queue_items:
            if not it.get("existing_product_id"):
                continue
            if it.get("image_role") in (IMAGE_ROLE_PREVIEW, IMAGE_ROLE_FULL):
                out.append(it)
        return out

    def _upload_attached_images_for_product_ids(self) -> dict[str, int]:
        """Wgrywa preview/Full do Shopify dla pozycji z przypisanym existing_product_id."""
        stats = {"preview": 0, "full": 0, "err": 0}
        items = self._queue_attach_items_with_product_id()
        preview_first = sorted(
            items,
            key=lambda it: 0 if it.get("image_role") == IMAGE_ROLE_PREVIEW else 1,
        )
        for it in preview_first:
            pid = int(it["existing_product_id"])
            fname = it["path"].name
            try:
                if it.get("image_role") == IMAGE_ROLE_PREVIEW:
                    res = add_preview_image(
                        image_path=it["path"],
                        artist=it["artist"],
                        base_title=it.get("base_title") or it["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    stats["preview"] += 1
                    it["handle"] = res.get("handle") or it.get("handle")
                    self._enqueue_log(f"[dogrywka] OK preview -> id={pid} ({fname})")
                elif it.get("image_role") == IMAGE_ROLE_FULL:
                    res = add_full_image(
                        image_path=it["path"],
                        artist=it["artist"],
                        base_title=it.get("base_title") or it["title"],
                        product_id=pid,
                        logger=self._enqueue_log,
                    )
                    stats["full"] += 1
                    it["handle"] = res.get("handle") or it.get("handle")
                    self._enqueue_log(f"[dogrywka] OK Full -> id={pid} ({fname})")
            except Exception as exc:
                stats["err"] += 1
                self._enqueue_log(f"[dogrywka] BLAD {fname} (id={pid}): {exc}")
        return stats

    def _on_publish_zoom_clicked(self) -> None:
        items = self._zoom_full_items()
        if not items:
            messagebox.showwarning(
                APP_TITLE,
                "Brak plikow Full w kolejce.\n"
                "Dodaj «Artysta - Tytul - Full.webp» dla dziel, ktore maja juz produkt w Shopify.",
            )
            return
        attach_items = self._queue_attach_items_with_product_id()
        missing_pid = [
            it for it in items if not (it.get("existing_product_id") or it.get("product_id"))
        ]
        if missing_pid:
            names = "\n".join(f"  - {it['path'].name}" for it in missing_pid[:6])
            messagebox.showwarning(
                APP_TITLE,
                "Brak przypisanego produktu Shopify dla plikow Full.\n"
                "Wpisz ID produktu i kliknij «Przypisz do zaznaczonych».\n\n"
                + names,
            )
            return
        attach_note = ""
        if attach_items:
            attach_note = (
                f"\n\nNajpierw wgram do Shopify: "
                f"{sum(1 for i in attach_items if i.get('image_role') == IMAGE_ROLE_PREVIEW)} preview, "
                f"{sum(1 for i in attach_items if i.get('image_role') == IMAGE_ROLE_FULL)} Full."
            )
        if not messagebox.askyesno(
            APP_TITLE,
            f"Przygotowac zoom HD (kafelki + R2) dla {len(items)} plik(ow) Full?\n"
            "Wymaga .env (R2) i produktu w Shopify.\n"
            "Ustawi szablon motywu: nowy-szblon-produktu (zoom tylko tam)."
            f"{attach_note}",
        ):
            return

        self.create_btn.configure(state="disabled")
        self.zoom_btn.configure(state="disabled")
        self._reset_batch_progress()
        self._reset_zoom_timing()
        zoom_names = {it["path"].name for it in items}
        self._enqueue_zoom_progress(0, len(zoom_names), "start")
        self._append_log(f"\n=== ZOOM HD START: {len(items)} plik(ow) ===")

        def worker() -> None:
            if attach_items:
                up = self._upload_attached_images_for_product_ids()
                self._enqueue_log(
                    f"[dogrywka] Shopify: preview={up['preview']}, "
                    f"Full={up['full']}, bledy={up['err']}"
                )
            with ThreadPoolExecutor(
                max_workers=zoom_parallel_products_default()
            ) as zoom_exec:
                coord = self._new_zoom_batch_coordinator(
                    run_zoom=True,
                    zoom_names=zoom_names,
                    executor=zoom_exec,
                )
                schedule = coord["schedule"]
                for it in items:
                    pid = self._resolve_product_id_for_zoom(it)
                    if not pid:
                        self._enqueue_log(
                            f"[zoom] POMINIETO {it['path'].name}: brak produktu w Shopify."
                        )
                        coord["stats"]["err"] += 1
                        continue
                    schedule(it, int(pid), it.get("handle"))
                zoom_exec.shutdown(wait=True)
            stats = coord["stats"]

            def _done() -> None:
                self.create_btn.configure(state="normal")
                self.zoom_btn.configure(state="normal")
                self._set_zoom_progress(len(zoom_names), len(zoom_names), "Gotowe")
                self.status_var.set(
                    f"Zoom HD: OK {stats['ok']}, bledy {stats['err']}."
                )
                self._refresh_r2_usage()
                self._refresh_tree()
                msg = f"Zoom HD zakonczone.\nOK: {stats['ok']}\nBledy: {stats['err']}"
                if attach_items:
                    msg += (
                        "\n\nSprawdz produkt w Shopify — powinny byc wgrane preview/Full "
                        "oraz metapole zoom (szablon: nowy-szblon-produktu)."
                    )
                messagebox.showinfo(APP_TITLE, msg)

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _ask_existing_product_action(
        self, item: dict[str, Any], existing: dict[str, Any]
    ) -> str | None:
        """Modal: 4 opcje (skip / replace_image / replace_image_and_description / force_create).

        Zwraca identyfikator akcji lub None dla 'Pomin'.
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("Produkt juz istnieje")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)

        shop_info = existing.get("handle") or existing.get("id")
        msg = (
            f"Plik: {item['path'].name}\n"
            f"Artysta: {item['artist']}\n"
            f"Tytul: {item['title']}\n\n"
            f"W Shopify juz istnieje produkt:\n"
            f"  '{existing.get('title')}'  (handle: {shop_info})\n\n"
            f"Co chcesz zrobic?"
        )
        ttk.Label(dlg, text=msg, justify="left", padding=14).pack(fill="x")

        result: dict[str, str | None] = {"value": None}

        def make_btn(text: str, val: str | None, emphasize: bool = False) -> ttk.Button:
            def on() -> None:
                result["value"] = val
                dlg.destroy()
            btn = ttk.Button(dlg, text=text, command=on)
            btn.pack(fill="x", padx=16, pady=3)
            if emphasize:
                try:
                    btn.configure(style="Accent.TButton")
                except tk.TclError:
                    pass
            return btn

        make_btn("Podmien tylko zdjecie glowne", "replace_image", emphasize=True)
        make_btn("Podmien zdjecie + wygeneruj nowy opis", "replace_image_and_description")
        make_btn("Utworz mimo to (zostawi oba produkty)", "force_create")

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=14, pady=(8, 4))
        ttk.Label(
            dlg,
            text="Dogrywka do istniejacego produktu (bez nowego opisu):",
            foreground="#333",
            padding=(14, 0, 14, 4),
        ).pack(fill="x")

        has_preview = self._find_queue_item_by_role(item, IMAGE_ROLE_PREVIEW) is not None
        has_full = self._find_queue_item_by_role(item, IMAGE_ROLE_FULL) is not None
        has_mockup = bool(self.mockup_sets)

        if has_preview and has_full and has_mockup:
            make_btn(
                "Caly komplet (preview + zoom + mockupy)",
                "attach_full_kit",
                emphasize=True,
            )

        if has_preview:
            make_btn("Dodaj preview", "attach_preview")
        if has_full:
            make_btn("Zoom HD -> R2", "zoom_hd_r2")
        if has_mockup:
            make_btn("Dodaj mockupy", "attach_mockups")
        if not (has_preview or has_full or has_mockup):
            ttk.Label(
                dlg,
                text="(Brak pliku preview/Full w kolejce lub szablonow mockup)",
                foreground="#888",
                padding=(14, 0, 14, 4),
            ).pack(fill="x")

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=14, pady=(8, 4))
        make_btn("Pomin ten plik", None)

        def on_skip_all() -> None:
            self._precheck_skip_all = True
            result["value"] = None
            dlg.destroy()

        skip_all_btn = ttk.Button(dlg, text="Pomin wszystkie", command=on_skip_all)
        skip_all_btn.pack(fill="x", padx=16, pady=(6, 3))

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=14, pady=(6, 0))
        ttk.Label(
            dlg,
            text=(
                "Wskazowka: 'Podmien zdjecie + nowy opis' wymaga JSON-a z LLM.\n"
                "«Caly komplet» = preview + Full/zoom HD + mockupy (wymaga obu plikow w kolejce "
                "i wlaczonego Mockup)."
            ),
            foreground="#666",
            wraplength=420,
            padding=(14, 6, 14, 14),
        ).pack(fill="x")

        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 460)
        h = dlg.winfo_reqheight()
        position_toplevel_screen_center(dlg, w, h)

        self.root.wait_window(dlg)
        return result["value"]

    def _ask_artist_product_picker(
        self, item: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> dict[str, Any] | str | None:
        """Dla obcojezycznego tytulu bez auto-dopasowania - pozwala wskazac produkt.

        Zwraca:
          - dict (wybrany produkt) -> traktowany jako 'istniejacy' -> dalej dialog akcji,
          - 'create_new'           -> stworz nowy produkt (default),
          - 'skip'                 -> pomin plik,
          - None                   -> uzytkownik zamknal okno (rowne 'create_new').
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("Wybierz istniejacy produkt artysty")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.minsize(560, 420)

        header = (
            f"Plik: {item['path'].name}\n"
            f"Artysta: {item['artist']}\n"
            f"Tytul (obcy): {item['title']}\n\n"
            f"Nie znalazlem produktu po tytule z pliku. Jesli ten obraz istnieje juz w Shopify "
            f"pod polskim tytulem - wybierz go z listy ponizej. "
            f"Jesli nie istnieje, wybierz 'Utworz nowy'."
        )
        ttk.Label(dlg, text=header, justify="left", padding=14, wraplength=600).pack(fill="x")

        list_frame = ttk.Frame(dlg, padding=(14, 0, 14, 8))
        list_frame.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        lb = tk.Listbox(list_frame, selectmode="browse", height=12, yscrollcommand=sb.set, activestyle="dotbox")
        sb.configure(command=lb.yview)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        sorted_candidates = sorted(candidates, key=lambda p: (p.get("title") or "").lower())
        for p in sorted_candidates:
            title = (p.get("title") or "").strip() or f"id={p.get('id')}"
            handle = (p.get("handle") or "").strip()
            lb.insert("end", f"{title}    [{handle}]" if handle else title)

        result: dict[str, Any] = {"value": None}

        def do_pick() -> None:
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo(APP_TITLE, "Wybierz produkt z listy albo klinij 'Utworz nowy'.")
                return
            result["value"] = sorted_candidates[int(sel[0])]
            dlg.destroy()

        def do_create_new() -> None:
            result["value"] = "create_new"
            dlg.destroy()

        def do_skip() -> None:
            result["value"] = "skip"
            dlg.destroy()

        def do_skip_all() -> None:
            self._precheck_skip_all = True
            result["value"] = "skip"
            dlg.destroy()

        btns = ttk.Frame(dlg, padding=(14, 0, 14, 14))
        btns.pack(fill="x")
        ttk.Button(btns, text="Uzyj wybranego", command=do_pick).pack(side="left")
        ttk.Button(btns, text="Utworz nowy", command=do_create_new).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Pomin wszystkie", command=do_skip_all).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Pomin plik", command=do_skip).pack(side="right")

        lb.bind("<Double-Button-1>", lambda _e: do_pick())

        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 640)
        h = max(dlg.winfo_reqheight(), 440)
        position_toplevel_screen_center(dlg, w, h)

        self.root.wait_window(dlg)
        return result["value"]

    @staticmethod
    def _batch_result_tag(r: dict[str, Any]) -> str:
        mode = (r.get("mode") or "").strip()
        if mode == "preview":
            return "(preview)"
        if mode == "full":
            return "(Full)"
        if mode in ("mockup", IMAGE_ROLE_MOCKUP):
            return "(mockup)"
        fn = r.get("follow_up_number")
        fk = r.get("follow_up_kind")
        if fk == FOLLOW_UP_KIND_I and fn:
            return f"(I{fn})"
        if fn:
            return f"(F{fn})"
        return ""

    def _show_collection_fix_dialog(self, gaps: list[dict[str, Any]]) -> None:
        """Produkty poza kolekcja artysty — wpisz poprawna nazwe kolekcji w Shopify."""
        total = sum(len(g.get("products") or []) for g in gaps)
        dlg = tk.Toplevel(self.root)
        dlg.title("Kolekcja artysty")
        position_toplevel_screen_center(dlg, 700, min(760, 220 + len(gaps) * 320))
        dlg.transient(self.root)
        dlg.grab_set()

        intro = (
            f"{total} nowych produkt(ow) nie jest w kolekcji artysty.\n"
            "Jesli kolekcja artysty JESZCZE NIE ISTNIEJE — kliknij «Stworz artyste»: utworzy "
            "kolekcje, doda ja do menu pod «ARTYŚCI» i przypisze produkty.\n"
            "Jesli kolekcja juz istnieje pod inna nazwa — popraw nazwe i kliknij «Przypisz».\n"
            "Dla kolekcji smart produkt musi spelniac reguly — reczne dodanie dziala tylko dla custom."
        )
        ttk.Label(dlg, text=intro, wraplength=580, justify="left").pack(
            anchor="w", padx=12, pady=(12, 8)
        )

        body = ttk.Frame(dlg)
        body.pack(fill="both", expand=True, padx=12, pady=4)
        title_vars: dict[str, tk.StringVar] = {}
        for grp in gaps:
            artist = grp.get("artist") or "?"
            frame = ttk.LabelFrame(body, text=artist)
            frame.pack(fill="x", pady=(0, 8))
            var = tk.StringVar(value=(grp.get("collection_title_default") or "").strip())
            title_vars[artist] = var
            ttk.Label(frame, text="Nazwa kolekcji w Shopify:").pack(anchor="w", padx=8, pady=(6, 0))
            entry_row = ttk.Frame(frame)
            entry_row.pack(fill="x", padx=8, pady=(2, 4))
            ttk.Entry(entry_row, textvariable=var, width=44).pack(
                side="left", fill="x", expand=True
            )

            # Daty zycia (naglowek <h4> na stronie kolekcji), jak u innych artystow.
            ttk.Label(frame, text="Daty zycia (np. 14 Lis 1840 – 5 Gru 1926):").pack(
                anchor="w", padx=8, pady=(4, 0)
            )
            lifespan_var = tk.StringVar(value="")
            ttk.Entry(frame, textvariable=lifespan_var, width=56).pack(
                fill="x", padx=8, pady=(2, 4)
            )

            # Krotki opis (akapity rozdziel pusta linia), jak u innych artystow.
            ttk.Label(frame, text="Krotki opis (jak u innych artystow):").pack(
                anchor="w", padx=8, pady=(4, 0)
            )
            desc_text = tk.Text(frame, height=4, width=56, wrap="word", font=("Segoe UI", 9))
            desc_text.pack(fill="x", padx=8, pady=(2, 4))

            # Zdjecie (portret) — wgrywane do Shopify Files i osadzane w opisie.
            portrait_holder: dict[str, Any] = {"path": None}
            portrait_var = tk.StringVar(value="(brak — opcjonalnie)")
            portrait_row = ttk.Frame(frame)
            portrait_row.pack(fill="x", padx=8, pady=(0, 4))
            ttk.Label(portrait_row, text="Zdjecie artysty:").pack(side="left")

            def _pick_portrait(
                holder: dict[str, Any] = portrait_holder,
                lbl: tk.StringVar = portrait_var,
            ) -> None:
                path = filedialog.askopenfilename(
                    title="Wybierz zdjecie artysty",
                    filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp"), ("Wszystkie", "*.*")],
                    parent=dlg,
                )
                if path:
                    holder["path"] = path
                    lbl.set(Path(path).name)

            ttk.Button(
                portrait_row, text="Wgraj zdjecie...", width=16, command=_pick_portrait
            ).pack(side="left", padx=(6, 6))
            ttk.Label(portrait_row, textvariable=portrait_var, foreground="#555").pack(
                side="left"
            )

            ttk.Button(
                frame,
                text="Stworz artyste",
                width=16,
                command=(
                    lambda g=grp, v=var, lv=lifespan_var, dt=desc_text, ph=portrait_holder: (
                        self._on_create_artist(g, v, lv, dt, ph, status_var, dlg)
                    )
                ),
            ).pack(anchor="w", padx=8, pady=(2, 6))

            prods = grp.get("products") or []
            lines = [f"  - {p.get('file') or p.get('product_id')}" for p in prods[:10]]
            if len(prods) > 10:
                lines.append(f"  ... i {len(prods) - 10} kolejnych")
            ttk.Label(frame, text="\n".join(lines), foreground="#555", justify="left").pack(
                anchor="w", padx=8, pady=(0, 8)
            )

        status_var = tk.StringVar(value="")
        ttk.Label(dlg, textvariable=status_var, foreground="#666", wraplength=580).pack(
            anchor="w", padx=12, pady=(0, 4)
        )

        btn_row = ttk.Frame(dlg)
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        def _assign() -> None:
            assign_btn.configure(state="disabled")
            status_var.set("Przypisywanie...")
            dlg.update_idletasks()

            def worker() -> None:
                added_total = 0
                already_total = 0
                failed_lines: list[str] = []
                for grp in gaps:
                    artist = grp.get("artist") or ""
                    var = title_vars.get(artist)
                    title = var.get().strip() if var else ""
                    pids = [
                        int(p["product_id"])
                        for p in (grp.get("products") or [])
                        if p.get("product_id")
                    ]
                    if not pids:
                        continue
                    try:
                        res = assign_products_to_collection_title(
                            collection_title=title,
                            product_ids=pids,
                            logger=self._enqueue_log,
                        )
                        added_total += len(res.get("added") or [])
                        already_total += len(res.get("already") or [])
                        for fail in res.get("failed") or []:
                            failed_lines.append(
                                f"{artist} id={fail.get('product_id')}: {fail.get('error')}"
                            )
                    except Exception as e:
                        failed_lines.append(f"{artist}: {e}")

                def _done() -> None:
                    assign_btn.configure(state="normal")
                    if failed_lines:
                        status_var.set(
                            f"Dodano: {added_total}, juz bylo: {already_total}. "
                            f"Bledy: {len(failed_lines)} — zobacz log."
                        )
                        self._append_log("\n[kolekcja-fix] Bledy przypisania:")
                        for line in failed_lines:
                            self._append_log(f"  {line}")
                        messagebox.showwarning(
                            APP_TITLE,
                            f"Dodano do kolekcji: {added_total}.\n"
                            f"Juz w kolekcji: {already_total}.\n"
                            f"Nie udalo sie: {len(failed_lines)} (szczegoly w logu).",
                            parent=dlg,
                        )
                    else:
                        status_var.set(
                            f"Gotowe. Dodano: {added_total}, juz bylo w kolekcji: {already_total}."
                        )
                        messagebox.showinfo(
                            APP_TITLE,
                            f"Przypisano {added_total} produkt(ow) do kolekcji.\n"
                            f"Juz bylo: {already_total}.",
                            parent=dlg,
                        )
                        dlg.destroy()

                self.root.after(0, _done)

            threading.Thread(target=worker, daemon=True).start()

        assign_btn = ttk.Button(btn_row, text="Przypisz do kolekcji", command=_assign, width=22)
        assign_btn.pack(side="left")
        ttk.Button(btn_row, text="Pomin", command=dlg.destroy, width=12).pack(side="right")

    def _on_create_artist(
        self,
        grp: dict[str, Any],
        var: "tk.StringVar",
        lifespan_var: "tk.StringVar",
        desc_text: "tk.Text",
        portrait_holder: dict[str, Any],
        status_var: "tk.StringVar",
        dlg: "tk.Toplevel",
    ) -> None:
        """Tworzy artyste (kolekcja custom + opis + zdjecie + pozycja w menu) i przypisuje produkty."""
        title = var.get().strip()
        if not title:
            messagebox.showwarning(
                APP_TITLE,
                "Podaj nazwe artysty/kolekcji (format «Nazwisko, Imie», np. «Butti, Lorenzo»).",
                parent=dlg,
            )
            return
        description = desc_text.get("1.0", "end").strip()
        lifespan = lifespan_var.get().strip()
        portrait_path = portrait_holder.get("path")
        pids = [
            int(p["product_id"])
            for p in (grp.get("products") or [])
            if p.get("product_id")
        ]
        extras = []
        extras.append("opis" if description else "bez opisu")
        extras.append("zdjecie" if portrait_path else "bez zdjecia")
        if not messagebox.askyesno(
            APP_TITLE,
            f"Utworzyc artyste «{title}»?\n\n"
            "- nowa kolekcja custom (jesli nie istnieje)\n"
            f"- strona kolekcji: {', '.join(extras)}\n"
            "- pozycja w menu pod «ARTYŚCI» (alfabetycznie)\n"
            f"- przypisanie {len(pids)} produkt(ow)",
            parent=dlg,
        ):
            return

        status_var.set(f"Tworze artyste «{title}»...")
        dlg.update_idletasks()

        def worker() -> None:
            try:
                res = create_artist_collection_and_menu(
                    collection_title=title,
                    product_ids=pids,
                    description=description or None,
                    lifespan=lifespan or None,
                    portrait_path=portrait_path,
                    logger=self._enqueue_log,
                )
            except Exception as e:
                self.root.after(
                    0,
                    lambda e=e: (
                        status_var.set(f"Blad: {e}"),
                        messagebox.showerror(
                            APP_TITLE,
                            f"Nie udalo sie stworzyc artysty:\n{e}",
                            parent=dlg,
                        ),
                    ),
                )
                return

            def _done() -> None:
                added = len(res.get("added") or [])
                already = len(res.get("already") or [])
                coll_txt = "utworzona" if res.get("created_collection") else "juz istniala"
                if res.get("menu_added"):
                    menu_txt = "dodano pod ARTYŚCI"
                elif res.get("menu_error"):
                    menu_txt = f"blad ({res['menu_error']})"
                else:
                    menu_txt = "juz byl w menu"
                if res.get("enrich_error"):
                    page_txt = f"blad opisu/zdjecia ({res['enrich_error']})"
                elif res.get("portrait_url"):
                    page_txt = "opis + zdjecie ustawione"
                elif description:
                    page_txt = "opis ustawiony"
                else:
                    page_txt = "bez opisu/zdjecia"
                status_var.set(
                    f"Gotowe «{title}»: kolekcja {coll_txt}, {page_txt}, menu — {menu_txt}, przypisano {added}."
                )
                msg = (
                    f"Artysta «{res.get('collection_title')}» gotowy.\n\n"
                    f"Kolekcja: {coll_txt} (id={res.get('collection_id')})\n"
                    f"Strona kolekcji: {page_txt}\n"
                    f"Menu: {menu_txt}\n"
                    f"Przypisano produktow: {added} (juz bylo: {already})"
                )
                failed = res.get("failed") or []
                if failed:
                    msg += f"\nNie przypisano: {len(failed)} (szczegoly w logu)"
                    self._append_log("\n[artysta] Bledy przypisania:")
                    for f in failed:
                        self._append_log(
                            f"  id={f.get('product_id')}: {f.get('error')}"
                        )
                    messagebox.showwarning(APP_TITLE, msg, parent=dlg)
                else:
                    messagebox.showinfo(APP_TITLE, msg, parent=dlg)

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _show_batch_summary(
        self,
        summary: dict[str, Any],
        *,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        append_activity(
            "dodajobraz",
            f"Batch: nowe {len(summary['created'])}, dogrania {len(summary['followed_up'])}, "
            f"bledow {len(summary['errors'])}, pominieto {len(summary['skipped'])}.",
        )
        notify_long_task_done(self.root)
        lines: list[str] = []
        lines.append("Przetwarzanie kolejki zakonczone.")
        lines.append("")
        lines.append(f"Utworzono nowych produktow: {len(summary['created'])}")
        for r in summary["created"]:
            lines.append(f"  [OK] {r['file']}  ->  {r.get('admin_url')}")
        lines.append(f"\nDograno zdjec: {len(summary['followed_up'])}")
        for r in summary["followed_up"]:
            tag = self._batch_result_tag(r)
            suffix = f"  {tag}" if tag else ""
            lines.append(f"  [OK] {r['file']}{suffix}  ->  {r.get('admin_url')}")
        if summary["skipped"]:
            lines.append(f"\nPominiete ({len(summary['skipped'])}):")
            for r in summary["skipped"]:
                lines.append(f"  [!]  {r['file']}: {r['reason']}")
        if summary["errors"]:
            lines.append(f"\nBledy ({len(summary['errors'])}):")
            for r in summary["errors"]:
                lines.append(f"  [X]  {r['file']}: {r['error']}")
        z = summary.get("zoom")
        if z:
            lines.append(
                f"\nZoom HD -> R2: OK {z.get('ok', 0)}, bledy {z.get('err', 0)} "
                f"(planowano {z.get('total', 0)} plikow Full)."
            )
        m = summary.get("mockup")
        if m:
            lines.append(
                f"\nMockup: OK {m.get('ok', 0)}, pominiete {m.get('skip', 0)}, "
                f"bledy {m.get('err', 0)} (planowano {m.get('total', 0)})."
            )
        gaps = summary.get("collection_gaps") or []
        if gaps:
            ng = sum(len(g.get("products") or []) for g in gaps)
            lines.append(
                f"\nKolekcja artysty: {ng} produkt(ow) poza kolekcja — "
                "otworzy sie okno z mozliwoscia wpisania poprawnej nazwy."
            )
        if not summary["errors"] and not summary["skipped"] and not gaps:
            lines.append("\nWszystko zostalo poprawnie wyslane.")

        dlg = tk.Toplevel(self.root)
        dlg.title("Raport batch")
        position_toplevel_screen_center(dlg, 720, 520)
        dlg.transient(self.root)
        txt = scrolledtext.ScrolledText(dlg, wrap="word", font=("Consolas", 9))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")

        def _ok() -> None:
            dlg.destroy()
            if on_close:
                on_close()

        ttk.Button(dlg, text="OK", command=_ok, width=16).pack(side="right", padx=10, pady=(0, 10))

    # ---------------------- Szablony wariantow ----------------------
    def _on_open_templates(self) -> None:
        """Otwiera dialog CRUD szablonow wariantow (lokalny snapshot zamiast
        ciaglego pytania Shopify o REFERENCE_PRODUCT_ID)."""
        try:
            from .templates_dialog import open_templates_dialog
        except ImportError as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie zaladowac dialogu:\n{exc}")
            return
        open_templates_dialog(self.root)

    # ---------------------- Dziennik akcji ----------------------
    def _on_activity_log(self) -> None:
        open_activity_log_dialog(self.root, title="Dziennik akcji (dodajobraz)")

    def _enqueue_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    # ---------------------- Kontrola kolekcji ----------------------
    def _on_collection_control(self) -> None:
        from .collection_control_dialog import open_collection_control_dialog

        open_collection_control_dialog(
            self.root,
            enqueue_log=self._enqueue_log,
            set_status=lambda s: self.status_var.set(s),
        )

    # ---------------------- Zestawienie glownych grafik ----------------------
    def _on_show_listing(self) -> None:
        self.status_var.set("Pobieram zestawienie produktow...")

        def fetch_and_open() -> None:
            try:
                rows = get_main_image_listing(logger=self._enqueue_log)
            except Exception as exc:
                self._enqueue_log(f"[BLAD] {exc}")
                self.root.after(
                    0,
                    lambda e=exc: messagebox.showerror(
                        APP_TITLE, f"Nie udalo sie pobrac listy produktow:\n{e}"
                    ),
                )
                self.root.after(0, lambda: self.status_var.set("Blad pobierania listy."))
                return
            self.root.after(0, lambda: self._open_listing_dialog(rows))
            self.root.after(0, lambda: self.status_var.set(f"Zestawienie: {len(rows)} produkt(ow)."))

        threading.Thread(target=fetch_and_open, daemon=True).start()

    def _open_listing_dialog(self, rows: list[dict[str, Any]]) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Zestawienie glownych grafik produktow")
        position_toplevel_screen_center(dlg, 1100, 640)
        dlg.minsize(820, 420)
        dlg.transient(self.root)

        header = ttk.Frame(dlg, padding=(12, 10, 12, 6))
        header.pack(side="top", fill="x")
        ttk.Label(
            header,
            text=(
                f"Wczytano {len(rows)} produkt(ow). Sortowanie domyslne: po nazwisku artysty (A-Z), "
                "potem po imieniu. Klik w naglowek kolumny = sortuj po niej (kolejny klik = odwrot)."
            ),
            foreground="#444",
            wraplength=1040,
            justify="left",
        ).pack(side="left", fill="x", expand=True)

        # Filtr (search)
        filter_bar = ttk.Frame(dlg, padding=(12, 0, 12, 6))
        filter_bar.pack(side="top", fill="x")
        ttk.Label(filter_bar, text="Filtr:", foreground="#444").pack(side="left")
        filter_var = tk.StringVar(value="")
        ttk.Entry(filter_bar, textvariable=filter_var, width=40).pack(side="left", padx=(6, 8))
        count_var = tk.StringVar(value=f"{len(rows)} produkt(ow)")
        ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left", padx=(8, 0))
        ttk.Button(
            filter_bar, text="Wyczysc filtr", command=lambda: filter_var.set("")
        ).pack(side="right")

        # Tabela
        table_frame = ttk.Frame(dlg, padding=(12, 0, 12, 6))
        table_frame.pack(side="top", fill="both", expand=True)

        cols = ("surname", "firstname", "painting_title", "main_image_filename", "handle")
        headings = {
            "surname": "Nazwisko",
            "firstname": "Imie",
            "painting_title": "Tytul obrazu",
            "main_image_filename": "Nazwa pliku glownej grafiki",
            "handle": "Handle (slug)",
        }
        col_widths = {
            "surname": 160,
            "firstname": 140,
            "painting_title": 360,
            "main_image_filename": 320,
            "handle": 200,
        }

        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=22)
        sort_state: dict[str, bool] = {}  # col -> reverse?

        def _make_sort_handler(col: str) -> Any:
            def handler() -> None:
                reverse = sort_state.get(col, False)
                _sort_by(col, reverse)
                sort_state.clear()
                sort_state[col] = not reverse
                _refresh_arrows(active=col, reverse=not reverse)
            return handler

        for c in cols:
            tree.heading(c, text=headings[c], command=_make_sort_handler(c))
            tree.column(c, width=col_widths[c], anchor="w", stretch=(c == "painting_title"))

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Pasek dolny
        bottom = ttk.Frame(dlg, padding=(12, 4, 12, 12))
        bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="Kopiuj zaznaczone", command=lambda: _copy_selected()).pack(side="left")
        ttk.Button(bottom, text="Eksportuj CSV...", command=lambda: _export_csv()).pack(side="left", padx=(8, 0))
        ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right")

        # ---------------- Logika sortowania / filtrowania ----------------
        current_view: list[dict[str, Any]] = list(rows)

        def _refresh_arrows(active: str, reverse: bool) -> None:
            arrow = " \u25bc" if reverse else " \u25b2"
            for c in cols:
                base = headings[c]
                tree.heading(c, text=(base + arrow) if c == active else base)

        def _populate(items: list[dict[str, Any]]) -> None:
            for iid in tree.get_children():
                tree.delete(iid)
            for r in items:
                tree.insert(
                    "",
                    "end",
                    iid=str(r["id"]),
                    values=(
                        r.get("surname", ""),
                        r.get("firstname", ""),
                        r.get("painting_title", ""),
                        r.get("main_image_filename", ""),
                        r.get("handle", ""),
                    ),
                )
            count_var.set(f"{len(items)} z {len(rows)} produkt(ow)")

        def _sort_by(col: str, reverse: bool) -> None:
            current_view.sort(
                key=lambda r: ((r.get(col) or "").lower(), (r.get("surname") or "").lower(), (r.get("firstname") or "").lower()),
                reverse=reverse,
            )
            _populate(current_view)

        def _apply_filter(*_args: Any) -> None:
            q = filter_var.get().strip().lower()
            if not q:
                filtered = list(rows)
            else:
                filtered = [
                    r for r in rows
                    if q in (r.get("surname") or "").lower()
                    or q in (r.get("firstname") or "").lower()
                    or q in (r.get("painting_title") or "").lower()
                    or q in (r.get("main_image_filename") or "").lower()
                    or q in (r.get("handle") or "").lower()
                ]
            current_view.clear()
            current_view.extend(filtered)
            # Po filtrze zachowaj aktualny porzadek sortowania (jesli byl).
            active = next(iter(sort_state), None)
            if active is not None:
                _sort_by(active, sort_state[active])
            else:
                _populate(current_view)

        filter_var.trace_add("write", _apply_filter)

        def _copy_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            lines = []
            for iid in sel:
                vals = tree.item(iid, "values")
                lines.append("\t".join(str(v) for v in vals))
            text = "\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._show_copy_toast(f"Skopiowano {len(sel)} wiersz(y) (TSV).")

        def _export_csv() -> None:
            from tkinter import filedialog as _fd
            path = _fd.asksaveasfilename(
                title="Zapisz zestawienie jako CSV",
                defaultextension=".csv",
                filetypes=[("CSV (separator: ;)", "*.csv"), ("Wszystkie", "*.*")],
                initialfile="zestawienie_grafik.csv",
            )
            if not path:
                return
            import csv
            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f, delimiter=";")
                    w.writerow([headings[c] for c in cols])
                    for r in current_view:
                        w.writerow([r.get(c, "") for c in cols])
                messagebox.showinfo(APP_TITLE, f"Zapisano:\n{path}")
            except OSError as e:
                messagebox.showerror(APP_TITLE, f"Nie udalo sie zapisac:\n{e}")

        # Domyslnie: po nazwisku rosnaco (rows juz tak posortowane przez backend).
        _populate(current_view)
        sort_state["surname"] = False
        _refresh_arrows(active="surname", reverse=False)

        dlg.update_idletasks()

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            messagebox.showinfo("Instrukcja", _DODAJ_HELP)
            return
        show_help(self.root, title="Instrukcja - Dodaj obraz", text=_DODAJ_HELP)


_DODAJ_HELP = """# Dodaj obraz - tworzenie produktow Shopify

Aplikacja przyspiesza dodawanie produktow malarskich do sklepu Shopify.
Z listy plikow generuje **prompt** dla AI (Opus/GPT/Cursor), parsuje
zwrotka, i sama wykonuje upload + linkowanie do oferty.

## Workflow
1. **Dodaj pliki** — trzy pola (przeciagnij lub kliknij):
   - **Preview** — tylko pliki z «(preview)» w nazwie
   - **Full** — tylko pliki z «Full» w nazwie
   - **Pozostale** — F2, I1/I2/I3, (mockup), WK, KK, zwykly tytul (bez preview/Full)
   Dla kazdego dziela w kolejce (ten sam artysta + tytul) musza byc **preview i Full**
   (wyjatek: sama dogrywka F2+ do istniejacego produktu).
   - Format nazwy: `Artysta - Tytul obrazu.jpg`
   - Podglad (kolekcje/menu, nie w galerii PDP): `Artysta - Tytul - (preview).webp`
   - Pelna rozdzielczosc (galeria produktu): `Artysta - Tytul - Full.webp`
   - Dogrywka: `Artysta - Tytul F2.jpg` (inne zdjecia w galerii)
   - Dopuszczalne sufiksy korekty na koncu nazwy (patrz **Slowniczek**):
     `Artysta - Tytul KK.jpg`, `Artysta - Tytul WK.jpg`,
     a takze laczone: `Artysta - Tytul F2 KK.jpg`.

## Slowniczek sufiksow nazw plikow
- **(preview)** - mniejszy podglad: widoczny w kolekcjach i menu Katalog,
  ukryty w galerii na stronie produktu (wymaga istniejacego produktu lub batch z Full/JSON).
- **Full** - pelny plik: pierwszy w galerii PDP; JSON LLM moze byc przypisany do pliku Full
  przy tworzeniu nowego produktu.
- **F2, F3, ...** - dogrywka kolejnego zdjecia do *istniejacego* produktu.
- **I1, I2, I3, ...** - wariant instalacji / wizualizacji (jak dogrywka, alt `(I<N>)`).
- **(mockup)** - mockup produktu (dogrywka, widoczny w galerii na stronie produktu).
- **KK** - koncowa korekta kolorystyczna (po HSL, finalna wersja pliku).
- **WK** - wstepna korekta kolorystyczna (bez HSL, robocza wersja pliku).

Sufiksy WK / KK sa traktowane jak metadane: aplikacja **ignoruje je przy
wyszukiwaniu produktu**, wiec plik `Hans Dahl - Babie lato KK.jpg` trafi do
tego samego produktu co `Hans Dahl - Babie lato.jpg`. W kolumnie *Tryb*
zobaczysz adnotacje `(KK)` lub `(WK)`.
2. W kolumnie **Akcja** zobaczysz "Pomin" przy plikach juz w bazie
   lub "Doda" przy nowych. Mozesz zaznaczyc/odznaczyc rzedy.
3. **Krok 1: Wygeneruj prompt** - klik przycisk **Opus** lub **GPT**.
   Tekst promptu zostanie automatycznie skopiowany do schowka (toast informuje).
4. Wklej w Cursor / ChatGPT, otrzymujesz odpowiedz JSON z opisem produktu.
5. **Krok 2: Wklej odpowiedz** - klik w pole `Krok 2` wkleja schowek (jeden JSON).
   Przy **wiecej niz 4 dzielach** prompt jest w czesciach: uzyj **«Wklej czesc 1/N»** …
   (kazda odpowiedz LLM osobno) — aplikacja **scala tablice** w polu JSON.
6. **Wykonaj akcje** - aplikacja parsuje JSON, dodaje produkty, dogrywa zdjecia.
   Postep: pasek nad **Log** (X/Y + nazwa pliku) oraz szczegoly w **Log**.
7. Jesli produkt **nie trafil do kolekcji artysty**, na koncu pojawi sie okno z lista
   i polem na **poprawna nazwe kolekcji** w Shopify (np. «Monet, Claude»).

## Kontrola kolekcji
- Przycisk **Kontrola kolekcji...** (gorny pasek): zestawienie wszystkich produktow typu Obraz,
  oczekiwana kolekcja artysty (format «Nazwisko, Imie») vs to, co jest w Shopify.
  Zaznacz wiele wierszy (Ctrl / Shift) i **Przypisz zaznaczone**. Mozesz tez usunac z custom.
  Kolekcje smart — tylko przez reguly/tagi.

## Tipy
- **Klik w prompt** kopiuje go do schowka (jesli niepusty).
- **Klik w pole Krok 2** wkleja schowek (pojedynczy JSON) lub pierwsza brakujaca czesc.
- **Wklej czesc …** — przy duzej kolejce: wklej kazda odpowiedz LLM osobno, auto-scalanie.
- Jesli kolumny w kolejce sa za wask (cos sie urywa), aplikacja sama poszerzy okno.
- Log ma 4 linijki + scroll - cala historia zostaje, tylko widoczne sa ostatnie wpisy.

## Konfiguracja
- W `cursor-api/.env` musi byc:
  - `SHOPIFY_STORE` - subdomena sklepu (`xxx.myshopify.com`).
  - `SHOPIFY_ACCESS_TOKEN` - admin API token.
- Bez tego upload do Shopify nie zadziala (prompt sie nadal generuje).
- **R2 (Zoom HD):** `R2_ACCOUNT_ID`, `R2_BUCKET`, klucze S3, `R2_PUBLIC_BASE_URL`.
  Pod paskami postepu widać zużycie magazynu w buckeie (domyslny limit 10 GB — `R2_STORAGE_QUOTA_GB`).
  Transfer (egress) z R2 jest u Cloudflare bezplatny. Opcjonalnie `CLOUDFLARE_API_TOKEN` — liczniki operacji A/B.
  Szybkosc uploadu: `R2_UPLOAD_WORKERS` (domyslnie 12 rownoleglych PUT-ow kafelkow) i
  `R2_ZOOM_PARALLEL` (domyslnie 3 zoomy/produkty naraz przy batchu z Shopify).
"""


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    # Bootstrap szablonu 'Podstawowy' przy pierwszym uruchomieniu
    # (dziala bezszelestnie jesli Shopify odpowiada; log do stdout jesli nie).
    try:
        from . import templates as _variant_templates
        _variant_templates.bootstrap_default_if_missing(
            logger=lambda m: print(m),
        )
    except Exception as _exc:  # noqa: BLE001
        print(f"[szablony] bootstrap pominieto: {_exc}")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
