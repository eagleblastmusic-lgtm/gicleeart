"""GUI 'dodajobraz' - drag-and-drop, kolejka plikow, tryb batch LLM w Cursorze.

Funkcje:
- Kolejka plikow (wrzucasz wiele na raz).
- Automatyczne tlumaczenie obcojezycznego tytulu (przez LLM w Cursorze).
- Dogrywanie kolejnych zdjec do istniejacego produktu (plik z sufiksem ' F2', ' F3', ...).
- Jeden prompt dla wszystkich nowych produktow + tablica JSON zwrotna z LLM.
- Masowa zmiana cen wszystkich produktow (przycisk 'Zmien ceny').
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from .create import (
    find_existing_product_for_new,
    get_artist_products,
    get_main_image_listing,
    get_reference_variant_rows,
    process_batch,
    update_all_product_prices,
)
from .markets import (
    base_market_code,
    compute_market_price,
    discover_shopify_market_ids,
    format_price,
    load_markets,
    push_markup_to_shopify,
    update_market_markup,
)
from .parser import is_polish_title, parse_filename, parse_title_metadata
from .prompt_builder import build_batch_prompt, parse_batch_response_json


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
        self.root.geometry("1010x880")
        self.root.minsize(900, 640)

        self.queue_items: list[dict[str, Any]] = []
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._toast_after_ids: list[Any] = []
        self._toast_win: tk.Toplevel | None = None

        self._build_ui()
        self._poll_log_queue()

    # ---------------------- UI construction ----------------------
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", **pad)
        ttk.Button(toolbar, text="Instrukcja", command=self._show_help).pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="Zestawienie produktow...", command=self._on_show_listing).pack(side="right", padx=(0, 8))
        ttk.Button(toolbar, text="Zmien ceny...", command=self._on_change_prices).pack(side="right", padx=(0, 8))
        ttk.Button(toolbar, text="Szablony...", command=self._on_open_templates).pack(side="right", padx=(0, 8))
        ttk.Button(toolbar, text="Rynki...", command=self._on_open_markets).pack(side="right", padx=(0, 8))

        drop_text = (
            "Przeciagnij i upusc JEDEN LUB WIELE plikow graficznych tutaj\n"
            "(format nazwy: 'Artysta - Tytul obrazu.jpg', dopuszczalne sufiksy: F2, F3..., WK, KK)\n\n"
            "albo kliknij, aby wybrac pliki"
        ) if _HAS_DND else (
            "Kliknij, aby wybrac pliki (Ctrl/Shift = wiele)\n"
            "(drag-and-drop wymaga: pip install tkinterdnd2)\n\n"
            "Format: 'Artysta - Tytul.jpg' (sufiksy: F2, F3..., WK, KK)"
        )
        self.drop_label = tk.Label(
            main,
            text=drop_text,
            relief="groove",
            bd=2,
            bg="#f5f5f5",
            fg="#333",
            cursor="hand2",
            height=4,
            font=("Segoe UI", 10),
        )
        self.drop_label.pack(fill="x", **pad)
        self.drop_label.bind("<Button-1>", lambda _e: self._browse_files())
        if _HAS_DND:
            self.drop_label.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

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
        self.counts_var = tk.StringVar(value="0 plikow")
        ttk.Label(queue_btns, textvariable=self.counts_var, foreground="#0a6").pack(fill="x", pady=(10, 2))
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

        for w in (self.step1, self.prompt_text, self.step1_btn_row):
            w.bind("<Button-1>", self._on_step1_click, add="+")

        self.step2 = ttk.LabelFrame(
            main,
            text="Krok 2: Wklej TABLICE JSON ktora zwrocil LLM (dla dogrywek F2+ niepotrzebne)",
        )
        self.step2.pack(fill="both", expand=True, **pad)
        self.json_text = scrolledtext.ScrolledText(self.step2, height=10, wrap="word", font=("Consolas", 9))
        self.json_text.pack(fill="both", expand=True, padx=6, pady=6)

        self.step2.bind("<Button-1>", self._on_step2_click, add="+")
        self.json_text.bind("<Button-1>", self._on_json_text_click, add="+")

        row_actions = ttk.Frame(main)
        row_actions.pack(fill="x", **pad)
        self.create_btn = ttk.Button(row_actions, text="Utworz wszystko", command=self._on_create_clicked)
        self.create_btn.pack(side="left")
        self.status_var = tk.StringVar(value="Gotowy. Dodaj pliki do kolejki.")
        ttk.Label(row_actions, textvariable=self.status_var, foreground="#666").pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=4, wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

    # ---------------------- Drag & drop / browse ----------------------
    def _on_drop(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        raw = (event.data or "").strip()
        paths: list[str] = []
        i = 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.find("}", i + 1)
                if end == -1:
                    break
                paths.append(raw[i + 1:end])
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
        paths = [p.strip() for p in paths if p.strip()]
        if not paths:
            return
        self._add_files([Path(p) for p in paths])

    def _browse_files(self) -> None:
        ps = filedialog.askopenfilenames(
            title="Wybierz zdjecia obrazow (Ctrl/Shift = wiele)",
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff"), ("Wszystkie", "*.*")],
        )
        if ps:
            self._add_files([Path(p) for p in ps])

    # ---------------------- Queue management ----------------------
    def _add_files(self, paths: list[Path]) -> None:
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
            base_title, fnum, correction = parse_title_metadata(raw_title)
            pl = is_polish_title(base_title)
            display_title = base_title if (fnum or correction) else raw_title
            item = {
                "path": p,
                "artist": artist,
                "title": display_title,
                "base_title": base_title,
                "follow_up_number": fnum,
                "correction_suffix": correction,
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
                "[W kolejce sa tylko dogrywki F2+] Prompt niepotrzebny - klik 'Utworz wszystko'.",
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
            base_title, fnum, correction = parse_title_metadata(new_val)
            item["title"] = base_title if (fnum or correction) else new_val
            item["base_title"] = base_title
            item["follow_up_number"] = fnum
            item["correction_suffix"] = correction
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
        if item.get("follow_up_number") is not None:
            return "dogrywka"
        action = item.get("action")
        if action is None:
            return "(sprawdzam...)" if item.get("_precheck_started") else "(oczekuje)"
        pid = item.get("existing_product_id")
        pid_s = f" id={pid}" if pid else ""
        return {
            "create": "Utworz nowy",
            "force_create": f"Utworz mimo to{pid_s}",
            "replace_image": f"Podmien zdjecie{pid_s}",
            "replace_image_and_description": f"Podmien obraz+opis{pid_s}",
            "skip": "Pomiń",
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
        corr = item.get("correction_suffix")
        mode = f"Dogrywka F{fnum}" if fnum else "Nowy produkt"
        if corr:
            mode = f"{mode} ({corr})"
        if fnum:
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

    def _refresh_counts_and_status(self) -> None:
        n_new = sum(1 for it in self.queue_items if it["follow_up_number"] is None)
        n_fu = len(self.queue_items) - n_new
        self.counts_var.set(f"{len(self.queue_items)} plik(ow): {n_new} nowych, {n_fu} dogrywek")
        if not self.queue_items:
            self.status_var.set("Gotowy. Dodaj pliki do kolejki.")
            self.create_btn.configure(text="Utworz wszystko", state="normal")
        else:
            parts = []
            if n_new:
                parts.append(f"{n_new} nowy(ch)")
            if n_fu:
                parts.append(f"{n_fu} dogrywk(i)")
            self.create_btn.configure(text=f"Utworz wszystko ({'+'.join(parts)})", state="normal")
            self.status_var.set(f"W kolejce: {' + '.join(parts)}.")

    def _has_new_items(self) -> bool:
        return any(it["follow_up_number"] is None for it in self.queue_items)

    # ---------------------- Prompt / JSON ----------------------
    def _generate_prompt(self, *, model: str | None = None) -> None:
        if model is not None:
            self._prompt_model = model
        target_model = self._prompt_model or "opus"
        new_items = [it for it in self.queue_items if it["follow_up_number"] is None]
        if not new_items:
            self.prompt_text.configure(state="normal")
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert(
                "1.0",
                "[Brak nowych produktow w kolejce] Prompt LLM niepotrzebny - same dogrywki.",
            )
            self.prompt_text.configure(state="disabled")
            self.prompt_model_var.set("")
            return
        prompt_items = [
            {
                "filename": it["path"].name,
                "artist": it["artist"],
                "title": it["title"],
                "title_is_polish": it["title_is_polish"],
            }
            for it in new_items
        ]
        prompt = build_batch_prompt(prompt_items, model=target_model)
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", prompt)
        self.prompt_text.configure(state="disabled")
        label = "Opus (Claude)" if target_model == "opus" else "GPT"
        self.prompt_model_var.set(f"Wariant: {label}")
        self.status_var.set(
            f"Prompt ({label}) wygenerowany dla {len(new_items)} nowego/ych produktu(ow)."
        )
        self._copy_prompt()

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
        self.json_text.delete("1.0", "end")
        self.json_text.insert("1.0", data)
        self.json_text.see("1.0")
        self._show_copy_toast("Wklejono JSON ze schowka.")

    def _on_step2_click(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Klik w obszar Kroku 2 (ramka) wkleja zawartosc schowka do pola JSON."""
        self._paste_clipboard_into_json()

    def _on_json_text_click(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        """Klik w pole JSON: jesli puste, wklej zawartosc schowka (nie zepsuje edycji)."""
        if not self.json_text.get("1.0", "end").strip():
            self._paste_clipboard_into_json()

    def _copy_prompt(self) -> None:
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

    # ---------------------- Live precheck (on add) ----------------------
    def _kick_precheck(self, items: list[dict[str, Any]]) -> None:
        """Odpala w tle sprawdzenie, czy produkt juz istnieje w Shopify.

        Po zakonczeniu w watku glownym pokazuje modale i zapisuje wybrana akcje na pozycji.
        """
        self.status_var.set(f"Sprawdzam Shopify w tle ({len(items)} plik(ow))...")

        def worker() -> None:
            artist_cache: dict[str, list[dict[str, Any]]] = {}
            results: list[tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None]] = []
            for it in items:
                try:
                    existing = find_existing_product_for_new(
                        artist=it["artist"],
                        filename_title=it["title"],
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
        target = existing
        if target is None and candidates:
            picked = self._ask_artist_product_picker(item, candidates)
            if picked == "skip":
                item["action"] = "skip"
                item["existing_product_id"] = None
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
            item["action"] = "skip"
        else:
            item["action"] = choice
        item["existing_product_id"] = int(target.get("id") or 0) or None

    # ---------------------- Execution ----------------------
    def _on_create_clicked(self) -> None:
        if not self.queue_items:
            messagebox.showwarning(APP_TITLE, "Kolejka jest pusta - dodaj pliki.")
            return

        new_items = [it for it in self.queue_items if it["follow_up_number"] is None]

        pending_running = [it for it in new_items if it.get("_precheck_started") and "action" not in it]
        if pending_running:
            messagebox.showinfo(
                APP_TITLE,
                f"Trwa jeszcze sprawdzanie Shopify ({len(pending_running)} plik(ow)). "
                "Poczekaj chwile i klik 'Utworz wszystko' ponownie.",
            )
            return

        unresolved = [it for it in new_items if "action" not in it]
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

        needs_json = [
            it["path"].name for it in new_items
            if (it.get("action") or "create") in ("create", "replace_image_and_description", "force_create")
        ]
        if needs_json and not llm_items:
            messagebox.showwarning(
                APP_TITLE,
                f"Dla {len(needs_json)} pozycji potrzebny jest JSON z LLM (krok 2):\n"
                + "\n".join(f"  - {n}" for n in needs_json)
                + "\n\nWklej tablice JSON albo zmien akcje na 'Pomin' / 'Podmien tylko zdjecie'.",
            )
            return
        if llm_items is not None:
            missing = [n for n in needs_json if n not in llm_map]
            if missing:
                if not messagebox.askyesno(
                    APP_TITLE,
                    "W JSON-ie brakuje pozycji dla:\n"
                    + "\n".join(f"  - {m}" for m in missing)
                    + "\n\nKontynuowac (te pliki beda pominiete)?",
                ):
                    return

        self.create_btn.configure(state="disabled")
        self.status_var.set("Przetwarzam kolejke... (patrz log)")
        self._append_log(f"\n=== BATCH START: {len(self.queue_items)} plik(ow) ===")

        enriched = [dict(it) for it in self.queue_items]

        def worker() -> None:
            try:
                summary = process_batch(
                    items=enriched,
                    llm_items=llm_items,
                    logger=self._enqueue_log,
                )
                self.root.after(0, lambda: self._show_batch_summary(summary))
                self.root.after(
                    0,
                    lambda: self.status_var.set(
                        f"Gotowe. Utworzono/zaktualizowano {len(summary['created'])}, "
                        f"dograno/podmieniono {len(summary['followed_up'])}, bledow {len(summary['errors'])}."
                    ),
                )
            except Exception as exc:
                self._enqueue_log(f"[BLAD] {exc}")
                self.root.after(0, lambda: self.status_var.set("Blad - zobacz log."))
                self.root.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Blad:\n{e}"))
            finally:
                self.root.after(0, lambda: self.create_btn.configure(state="normal"))

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
        make_btn("Pomin ten plik", None)

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=14, pady=(6, 0))
        ttk.Label(
            dlg,
            text="Wskazowka: 'Podmien zdjecie + nowy opis' wymaga JSON-a z LLM dla tego pliku.",
            foreground="#666",
            wraplength=420,
            padding=(14, 6, 14, 14),
        ).pack(fill="x")

        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 460)
        h = dlg.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

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

        btns = ttk.Frame(dlg, padding=(14, 0, 14, 14))
        btns.pack(fill="x")
        ttk.Button(btns, text="Uzyj wybranego", command=do_pick).pack(side="left")
        ttk.Button(btns, text="Utworz nowy", command=do_create_new).pack(side="left", padx=(8, 0))
        ttk.Button(btns, text="Pomin plik", command=do_skip).pack(side="right")

        lb.bind("<Double-Button-1>", lambda _e: do_pick())

        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 640)
        h = max(dlg.winfo_reqheight(), 440)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self.root.wait_window(dlg)
        return result["value"]

    def _show_batch_summary(self, summary: dict[str, Any]) -> None:
        lines: list[str] = []
        lines.append("Przetwarzanie kolejki zakonczone.")
        lines.append("")
        lines.append(f"Utworzono nowych produktow: {len(summary['created'])}")
        for r in summary["created"]:
            lines.append(f"  [OK] {r['file']}  ->  {r.get('admin_url')}")
        lines.append(f"\nDograno zdjec: {len(summary['followed_up'])}")
        for r in summary["followed_up"]:
            lines.append(f"  [OK] {r['file']}  (F{r.get('follow_up_number')})  ->  {r.get('admin_url')}")
        if summary["skipped"]:
            lines.append(f"\nPominiete ({len(summary['skipped'])}):")
            for r in summary["skipped"]:
                lines.append(f"  [!]  {r['file']}: {r['reason']}")
        if summary["errors"]:
            lines.append(f"\nBledy ({len(summary['errors'])}):")
            for r in summary["errors"]:
                lines.append(f"  [X]  {r['file']}: {r['error']}")
        if not summary["errors"] and not summary["skipped"]:
            lines.append("\nWszystko zostalo poprawnie wyslane.")

        dlg = tk.Toplevel(self.root)
        dlg.title("Raport batch")
        dlg.geometry("720x520")
        dlg.transient(self.root)
        txt = scrolledtext.ScrolledText(dlg, wrap="word", font=("Consolas", 9))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")
        ttk.Button(dlg, text="OK", command=dlg.destroy, width=16).pack(side="right", padx=10, pady=(0, 10))

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

    # ---------------------- Markets / per-rynek markup ----------------------
    def _on_open_markets(self) -> None:
        """Otwiera dialog do regulacji % markup per rynek (PL = baza).

        Tabela renderowana przez ttk.Treeview - idealne wyrownanie kolumn,
        sortowanie kliknieciem naglowka, filtrowanie tekstem, edycja markupu
        przez double-click na komorke 'Markup %'.
        """
        try:
            markets_initial = load_markets()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Nie udalo sie wczytac markets_config.json:\n{exc}")
            return
        if not markets_initial:
            messagebox.showwarning(APP_TITLE, "Brak rynkow w konfiguracji.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Rynki - markup % nad cena PL")
        dlg.geometry("820x600")
        dlg.minsize(720, 480)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(
            dlg,
            text=(
                "Dla kazdego rynku ustaw % narzutu nad cena bazowa (PL). "
                "Klik nagloweka = sortowanie. Double-click w kolumne 'Markup %' = edycja. "
                "Zmiany zapisywane natychmiast do markets_config.json."
            ),
            justify="left",
            foreground="#444",
            wraplength=780,
        ).pack(side="top", fill="x", padx=12, pady=(10, 6))

        # ---------- Pasek: cena bazowa + filtr ----------
        toolbar = ttk.Frame(dlg)
        toolbar.pack(side="top", fill="x", padx=12, pady=(0, 4))

        ttk.Label(toolbar, text="Cena bazowa (PL) do podgladu:").pack(side="left")
        sample_var = tk.StringVar(value="100.00")
        ttk.Entry(toolbar, textvariable=sample_var, width=10, justify="right").pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(toolbar, text="PLN").pack(side="left", padx=(4, 14))

        ttk.Label(toolbar, text="Filtr:").pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(toolbar, textvariable=filter_var, width=22)
        filter_entry.pack(side="left", padx=(6, 4))
        ttk.Button(
            toolbar, text="Wyczysc", width=10,
            command=lambda: filter_var.set(""),
        ).pack(side="left")

        # ---------- Panel: kursy walut (NBP) ----------
        fx_bar = ttk.Frame(dlg)
        fx_bar.pack(side="top", fill="x", padx=12, pady=(2, 4))
        ttk.Label(fx_bar, text="Kurs walut:").pack(side="left")
        fx_status_var = tk.StringVar(value="(ladowanie...)")
        ttk.Label(fx_bar, textvariable=fx_status_var, foreground="#1565c0").pack(
            side="left", padx=(6, 10)
        )

        def _refresh_fx_button(*, force: bool = False) -> None:
            _refresh_fx_cache(force=force)
            parts: list[str] = []
            for cur, rate in state["fx_rates"].items():
                info = state["fx_info"].get(cur, {})
                source = info.get("source", "?")
                stale = " [CACHE]" if info.get("stale") else ""
                parts.append(f"1 {cur} = {rate:.4f} PLN ({source}{stale})")
            if not parts:
                fx_status_var.set("(brak walut obcych - tylko PLN)")
            else:
                fx_status_var.set("  |  ".join(parts))
            _render()

        def _set_manual_rate() -> None:
            from tkinter import simpledialog as _sd
            cur = _sd.askstring(
                APP_TITLE, "Waluta (EUR/USD/...):",
                parent=dlg, initialvalue="EUR",
            )
            if not cur:
                return
            val = _sd.askstring(
                APP_TITLE, f"Kurs recznie (ile PLN za 1 {cur.upper()}):",
                parent=dlg, initialvalue="4.30",
            )
            if not val:
                return
            try:
                rate = float(val.replace(",", "."))
            except ValueError:
                messagebox.showerror(APP_TITLE, "Kurs musi byc liczba.", parent=dlg)
                return
            try:
                from Komponenty._shared import fx_rates as fx
                fx.set_manual_rate(cur.upper(), rate)
            except (ValueError, OSError) as e:
                messagebox.showerror(APP_TITLE, f"Nie udalo sie zapisac kursu:\n{e}", parent=dlg)
                return
            _refresh_fx_button(force=False)

        ttk.Button(
            fx_bar, text="Odswiez kursy (NBP)",
            command=lambda: _refresh_fx_button(force=True),
        ).pack(side="right")
        ttk.Button(
            fx_bar, text="Kurs recznie...",
            command=_set_manual_rate,
        ).pack(side="right", padx=(0, 6))

        # Wstepna aktualizacja etykiety
        dlg.after(50, lambda: _refresh_fx_button(force=False))

        ttk.Separator(dlg, orient="horizontal").pack(side="top", fill="x", padx=12, pady=(6, 0))

        # ---------- Treeview ----------
        tree_wrap = ttk.Frame(dlg)
        tree_wrap.pack(side="top", fill="both", expand=True, padx=12, pady=(6, 4))

        cols = ("name_pl", "code", "locale", "markup", "preview")
        headings_def: dict[str, tuple[str, int, str, bool]] = {
            # col_id : (label, width_px, anchor, stretch)
            "name_pl": ("Rynek",          220, "w", True),
            "code":    ("Kod",             70, "center", False),
            "locale":  ("Locale",          80, "center", False),
            "markup":  ("Markup %",       120, "e", False),
            "preview": ("Podglad ceny",   160, "e", True),
        }

        tree = ttk.Treeview(
            tree_wrap, columns=cols, show="headings",
            selectmode="browse", height=10,
        )
        for c, (txt, w, anch, stretch) in headings_def.items():
            tree.heading(c, text=txt, command=lambda _c=c: _sort_by(_c))
            tree.column(c, width=w, anchor=anch, stretch=stretch, minwidth=max(50, w // 2))

        # tagi do podswietlania bazowego rynku + parzystych wierszy
        tree.tag_configure("base",   background="#f3f3f3", foreground="#777")
        tree.tag_configure("alt",    background="#fafafa")
        tree.tag_configure("normal", background="#ffffff")

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ---------- State ----------
        state: dict[str, Any] = {
            "markets": list(markets_initial),
            "sort_col": "name_pl",
            "sort_desc": False,
            "fx_rates": {},  # {currency: rate} - uzupelniane z NBP/cache
            "fx_info": {},   # {currency: {"source", "fetched_at", "stale"}}
        }

        def _refresh_fx_cache(*, force: bool = False) -> None:
            """Pobiera kursy z NBP (z cache 24h) dla niepolskich walut uzywanych przez rynki."""
            needed = sorted(
                {(m.currency or "").upper() for m in state["markets"]
                 if (m.currency or "").upper() not in ("", "PLN")}
            )
            try:
                from Komponenty._shared import fx_rates as fx
            except ImportError:
                return
            rates: dict[str, float] = {}
            info: dict[str, dict[str, Any]] = {}
            for cur in needed:
                try:
                    rate, _info = fx.get_rate(cur, force_refresh=force)
                    rates[cur] = rate
                    info[cur] = _info
                except fx.FxError as exc:
                    info[cur] = {"error": str(exc)}
            state["fx_rates"] = rates
            state["fx_info"] = info

        _refresh_fx_cache()

        def _current_base() -> float:
            try:
                return float((sample_var.get() or "0").replace(",", "."))
            except ValueError:
                return 0.0

        def _row_values(m: Any, base: float) -> tuple:
            pct = 0.0 if m.is_base else float(m.markup_percent)
            cur = (m.currency or "PLN").upper()
            rate = state["fx_rates"].get(cur) if cur != "PLN" else None
            price = compute_market_price(base, pct, currency=cur, fx_rate=rate)
            markup_txt = ("baza" if m.is_base else f"{pct:+.1f}%")
            return (
                m.name_pl,
                m.code,
                m.locale,
                markup_txt,
                format_price(price, m.currency),
            )

        def _sort_key(m: Any, col: str) -> Any:
            if col == "name_pl":
                return (m.name_pl or "").lower()
            if col == "code":
                return (m.code or "").lower()
            if col == "locale":
                return (m.locale or "").lower()
            if col == "markup":
                return -1.0 if m.is_base else float(m.markup_percent)
            if col == "preview":
                pct = 0.0 if m.is_base else float(m.markup_percent)
                cur = (m.currency or "PLN").upper()
                rate = state["fx_rates"].get(cur) if cur != "PLN" else None
                return compute_market_price(
                    _current_base(), pct, currency=cur, fx_rate=rate,
                )
            return ""

        def _render() -> None:
            tree.delete(*tree.get_children())
            ftxt = (filter_var.get() or "").strip().lower()
            items = list(state["markets"])
            if ftxt:
                items = [
                    m for m in items
                    if ftxt in (m.name_pl or "").lower()
                    or ftxt in (m.name_en or "").lower()
                    or ftxt in (m.code or "").lower()
                    or ftxt in (m.locale or "").lower()
                    or ftxt in (m.currency or "").lower()
                ]
            col = state["sort_col"]
            desc = state["sort_desc"]
            items.sort(key=lambda m: _sort_key(m, col), reverse=desc)
            base = _current_base()
            for idx, m in enumerate(items):
                if m.is_base:
                    tag = "base"
                else:
                    tag = "alt" if idx % 2 == 1 else "normal"
                tree.insert("", "end", iid=m.code, values=_row_values(m, base), tags=(tag,))
            for c, (txt, _w, _a, _s) in headings_def.items():
                arrow = ""
                if c == col:
                    arrow = "  v" if desc else "  ^"
                tree.heading(c, text=txt + arrow)

        def _sort_by(col: str) -> None:
            if state["sort_col"] == col:
                state["sort_desc"] = not state["sort_desc"]
            else:
                state["sort_col"] = col
                state["sort_desc"] = False
            _render()

        def _reload_from_disk() -> None:
            try:
                state["markets"] = load_markets()
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f"Blad ladowania konfiguracji: {exc}")
                return
            _render()

        # ---------- Inline edit ----------
        def _begin_edit_markup(rowid: str) -> None:
            m = next((x for x in state["markets"] if x.code == rowid), None)
            if not m or m.is_base:
                return
            bbox = tree.bbox(rowid, column="markup")
            if not bbox:
                return
            x, y, w, h = bbox
            ed_var = tk.StringVar(value=f"{float(m.markup_percent):.1f}")
            ed = ttk.Spinbox(
                tree, from_=-50.0, to=200.0, increment=0.5,
                textvariable=ed_var, format="%.1f", justify="right",
            )
            ed.place(x=x, y=y, width=w, height=h)
            ed.focus_set()
            ed.selection_range(0, "end")

            def _commit(_evt=None) -> None:
                raw = (ed_var.get() or "").strip().replace(",", ".")
                try:
                    pct = float(raw)
                except ValueError:
                    ed.destroy()
                    return
                try:
                    update_market_markup(m.code, pct)
                    m.markup_percent = pct
                    self._enqueue_log(f"[rynki] {m.code}: markup zapisany ({pct:+.1f}%).")
                except Exception as exc:
                    self._enqueue_log(f"[rynki] BLAD zapisu {m.code}: {exc}")
                ed.destroy()
                _render()

            def _cancel(_evt=None) -> None:
                ed.destroy()

            ed.bind("<Return>", _commit)
            ed.bind("<KP_Enter>", _commit)
            ed.bind("<FocusOut>", _commit)
            ed.bind("<Escape>", _cancel)

        def _on_double_click(event: Any) -> None:
            rowid = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if not rowid:
                return
            try:
                col_idx = int(col_id.lstrip("#")) - 1
            except (ValueError, AttributeError):
                return
            if 0 <= col_idx < len(cols) and cols[col_idx] == "markup":
                _begin_edit_markup(rowid)

        tree.bind("<Double-1>", _on_double_click)

        filter_var.trace_add("write", lambda *_a: _render())
        sample_var.trace_add("write", lambda *_a: _render())

        _render()

        # ---------- Bottom bar ----------
        ttk.Separator(dlg, orient="horizontal").pack(side="bottom", fill="x", padx=12, pady=(0, 0))
        bottom = ttk.Frame(dlg)
        bottom.pack(side="bottom", fill="x", padx=12, pady=8)

        ttk.Button(bottom, text="Zamknij", command=dlg.destroy, width=14).pack(side="right")

        # ---------- Buttons (refresh in-place, no dlg.destroy) ----------
        def _do_discover() -> None:
            self.status_var.set("Pobieram dane rynkow z Shopify...")
            def _worker() -> None:
                try:
                    updated = discover_shopify_market_ids(logger=self._enqueue_log)
                    matched_codes = [m.code for m in updated if m.shopify_price_list_gid]
                    not_matched = [
                        m.code for m in updated
                        if not m.is_base and not m.shopify_price_list_gid
                    ]
                    self.root.after(0, _reload_from_disk)
                    self.root.after(
                        0, lambda: messagebox.showinfo(
                            APP_TITLE,
                            "Pobrano dane rynkow z Shopify.\n\n"
                            f"Dopasowane: {', '.join(matched_codes) or '(brak)'}\n"
                            f"Niedopasowane: {', '.join(not_matched) or '(brak)'}\n\n"
                            "Tabela zostala odswiezona.",
                            parent=dlg,
                        )
                    )
                except Exception as exc:
                    self._enqueue_log(f"[markets] BLAD discover: {exc}")
                    self.root.after(
                        0, lambda e=exc: messagebox.showerror(
                            APP_TITLE,
                            "Nie udalo sie pobrac rynkow z Shopify.\n\n"
                            f"{e}\n\n"
                            "Mozliwa przyczyna: brak scope 'read_markets'/'write_markets' "
                            "w .env oraz shopify.app.toml. Po dodaniu uruchom: "
                            "cd cursor-api && npm run oauth",
                            parent=dlg,
                        )
                    )
                finally:
                    self.root.after(0, lambda: self.status_var.set("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        def _do_push_all() -> None:
            if not messagebox.askyesno(
                APP_TITLE,
                "Wypchnac markupy WSZYSTKICH rynkow (oprocz PL) do Shopify?\n\n"
                "Wymaga: scope 'write_markets' + wczesniej uruchomionego 'Pobierz dane rynkow'.",
                parent=dlg,
            ):
                return
            self.status_var.set("Pushuje markupy do Shopify...")
            def _worker() -> None:
                try:
                    pushed: list[str] = []
                    skipped: list[str] = []
                    failed: list[str] = []
                    for m in load_markets():
                        if m.is_base:
                            continue
                        try:
                            res = push_markup_to_shopify(m.code, logger=self._enqueue_log)
                            if res.get("ok"):
                                pushed.append(m.code)
                            else:
                                skipped.append(f"{m.code}: {res.get('reason','')}")
                        except Exception as e:
                            failed.append(f"{m.code}: {e}")
                            self._enqueue_log(f"[markets] BLAD push {m.code}: {e}")
                    self.root.after(0, _reload_from_disk)
                    self.root.after(0, lambda: messagebox.showinfo(
                        APP_TITLE,
                        f"Push zakonczony.\n\nWyslano: {', '.join(pushed) or '-'}\n"
                        f"Pominieto: {len(skipped)} (szczegoly w logu)\n"
                        f"Bledow: {len(failed)} (szczegoly w logu)\n\n"
                        "Tabela zostala odswiezona.",
                        parent=dlg,
                    ))
                finally:
                    self.root.after(0, lambda: self.status_var.set("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        def _do_pull_markups() -> None:
            self.status_var.set("Pobieram markupy z Shopify...")
            def _worker() -> None:
                try:
                    updated = discover_shopify_market_ids(logger=self._enqueue_log)
                    lines = [
                        f"  {m.code}: {m.markup_percent:+.1f}%"
                        for m in updated if not m.is_base and m.shopify_price_list_gid
                    ]
                    skipped = [
                        m.code for m in updated
                        if not m.is_base and not m.shopify_price_list_gid
                    ]
                    msg = "Markupy zsynchronizowane z Shopify:\n\n" + (
                        "\n".join(lines) if lines else "(brak dopasowanych rynkow)"
                    )
                    if skipped:
                        msg += f"\n\nPominieto (brak GID): {', '.join(skipped)}"
                    msg += "\n\nTabela zostala odswiezona."
                    self.root.after(0, _reload_from_disk)
                    self.root.after(
                        0, lambda m=msg: messagebox.showinfo(APP_TITLE, m, parent=dlg)
                    )
                except Exception as exc:
                    self._enqueue_log(f"[markets] BLAD pull markup: {exc}")
                    self.root.after(
                        0, lambda e=exc: messagebox.showerror(
                            APP_TITLE,
                            "Nie udalo sie pobrac markupow z Shopify.\n\n"
                            f"{e}\n\n"
                            "Sprawdz czy masz scope 'read_markets'.",
                            parent=dlg,
                        )
                    )
                finally:
                    self.root.after(0, lambda: self.status_var.set("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        ttk.Button(bottom, text="Pobierz dane rynkow z Shopify", command=_do_discover).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bottom, text="Pobierz markupy z Shopify", command=_do_pull_markups).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bottom, text="Wyslij markupy do Shopify", command=_do_push_all).pack(side="left")

    # ---------------------- Change prices ----------------------
    def _on_change_prices(self) -> None:
        self.status_var.set("Pobieram wzorcowe warianty...")

        def fetch_and_open() -> None:
            try:
                rows = get_reference_variant_rows(logger=self._enqueue_log)
            except Exception as exc:
                self._enqueue_log(f"[BLAD] {exc}")
                self.root.after(
                    0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Nie udalo sie pobrac wariantow:\n{e}")
                )
                self.root.after(0, lambda: self.status_var.set("Blad pobierania wariantow."))
                return
            self.root.after(0, lambda: self._open_price_dialog(rows))
            self.root.after(0, lambda: self.status_var.set("Gotowy."))

        threading.Thread(target=fetch_and_open, daemon=True).start()

    def _open_price_dialog(self, rows: list[dict]) -> None:
        if not rows:
            messagebox.showwarning(APP_TITLE, "Produkt referencyjny nie ma zadnych wariantow.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Zmien ceny (wszystkie produkty)")
        dlg.geometry("760x680")
        dlg.minsize(640, 480)
        dlg.transient(self.root)
        dlg.grab_set()

        header = ttk.Label(
            dlg,
            text=(
                "Wpisz NOWE ceny. Puste pola = brak zmiany.\n"
                "Ceny zostana ustawione w KAZDYM produkcie typu 'Obraz' na sklepie, ktory ma wariant\n"
                "pasujacy do wybranego klucza (Rodzaj drewna / Rozmiar / Kolor)."
            ),
            wraplength=720,
            justify="left",
            foreground="#444",
        )
        header.pack(side="top", fill="x", padx=12, pady=(10, 6))

        # ---------------- Przelacznik widoku (Globalny / Szczegolowy) ----------------
        view_bar = ttk.Frame(dlg)
        view_bar.pack(side="top", fill="x", padx=12, pady=(0, 6))

        ttk.Label(view_bar, text="Widok:", foreground="#444").pack(side="left", padx=(0, 8))

        view_mode = tk.StringVar(value="global")
        btn_global = ttk.Button(view_bar, text="Globalny", width=14)
        btn_detail = ttk.Button(view_bar, text="Szczegolowy", width=14)
        btn_global.pack(side="left", padx=(0, 4))
        btn_detail.pack(side="left")

        view_hint = ttk.Label(view_bar, text="", foreground="#777")
        view_hint.pack(side="left", padx=(12, 0))

        btns = ttk.Frame(dlg)
        btns.pack(side="bottom", fill="x", padx=12, pady=10)

        ttk.Separator(dlg, orient="horizontal").pack(side="bottom", fill="x")

        content = ttk.Frame(dlg)
        content.pack(side="top", fill="both", expand=True, padx=(12, 0), pady=(0, 6))

        canvas = tk.Canvas(content, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y", padx=(0, 6))

        inner = ttk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event: tk.Event) -> None:  # type: ignore[type-arg]
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:  # type: ignore[type-arg]
            canvas.itemconfigure(inner_window, width=event.width)

        def _on_mousewheel(event: tk.Event) -> None:  # type: ignore[type-arg]
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        dlg.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), dlg.destroy()))

        _COL_CUR_W = 14
        _COL_NEW_W = 10
        _LABEL_MINSIZE = 260

        # ---------------- Przygotowanie danych dla obu widokow ----------------
        # Stan zachowywany przy przelaczaniu widoku - ostatnio wpisana wartosc.
        detail_values: dict[tuple[str, ...], str] = {row["key"]: "" for row in rows}

        # Grupowanie do widoku globalnego: klucz = (wood, size) z labela.
        # Label ma postac "<wood> / <size> / <color>" (lub krotsza, jesli mniej opcji).
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        group_order: list[tuple[str, str]] = []
        for row in rows:
            parts = [p.strip() for p in str(row["label"]).split(" / ")]
            wood = parts[0] if len(parts) >= 1 else ""
            size = parts[1] if len(parts) >= 2 else ""
            gkey = (wood, size)
            if gkey not in groups:
                groups[gkey] = {
                    "label": f"{wood} {size}".strip() or "(bez nazwy)",
                    "rows": [],
                    "prices": [],
                }
                group_order.append(gkey)
            groups[gkey]["rows"].append(row)
            if row.get("price"):
                groups[gkey]["prices"].append(str(row["price"]))

        # Stan widoku globalnego.
        global_values: dict[tuple[str, str], str] = {gkey: "" for gkey in group_order}

        detail_entries: list[tuple[tuple[str, ...], tk.StringVar]] = []
        global_entries: list[tuple[tuple[str, str], tk.StringVar]] = []

        # ---------------- Renderowanie widokow ----------------
        def _clear_inner() -> None:
            for child in inner.winfo_children():
                child.destroy()
            detail_entries.clear()
            global_entries.clear()

        def _render_detail() -> None:
            _clear_inner()
            grid = ttk.Frame(inner)
            grid.pack(fill="x", padx=10, pady=(2, 6), anchor="w")
            grid.columnconfigure(0, minsize=_LABEL_MINSIZE)
            grid.columnconfigure(1, minsize=110)
            grid.columnconfigure(2, minsize=100)

            ttk.Label(
                grid,
                text="Wariant (Rodzaj drewna / Rozmiar / Kolor)",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
            ttk.Label(
                grid,
                text="Obecna cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_CUR_W,
            ).grid(row=0, column=1, sticky="e", padx=(0, 12))
            ttk.Label(
                grid,
                text="Nowa cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_NEW_W,
            ).grid(row=0, column=2, sticky="e")

            ttk.Separator(grid, orient="horizontal").grid(
                row=1, column=0, columnspan=3, sticky="ew", pady=(0, 2)
            )

            for i, row in enumerate(rows):
                r = 2 + 2 * i
                ttk.Label(grid, text=row["label"]).grid(
                    row=r, column=0, sticky="w", padx=(0, 16), pady=4
                )
                ttk.Label(
                    grid,
                    text=row["price"] or "-",
                    foreground="#777",
                    anchor="e",
                    width=_COL_CUR_W,
                ).grid(row=r, column=1, sticky="e", padx=(0, 12))
                var = tk.StringVar(value=detail_values.get(row["key"], ""))

                def _sync(_a: str, _b: str, _c: str, _k=row["key"], _v=var) -> None:
                    detail_values[_k] = _v.get()

                var.trace_add("write", _sync)
                ttk.Entry(grid, textvariable=var, width=_COL_NEW_W, justify="right").grid(
                    row=r, column=2, sticky="e"
                )
                detail_entries.append((row["key"], var))
                if i < len(rows) - 1:
                    ttk.Separator(grid, orient="horizontal").grid(
                        row=r + 1, column=0, columnspan=3, sticky="ew"
                    )

        def _render_global() -> None:
            _clear_inner()
            grid = ttk.Frame(inner)
            grid.pack(fill="x", padx=10, pady=(2, 6), anchor="w")
            grid.columnconfigure(0, minsize=_LABEL_MINSIZE)
            grid.columnconfigure(1, minsize=140)
            grid.columnconfigure(2, minsize=100)

            ttk.Label(
                grid,
                text="Grupa (Rodzaj drewna + Rozmiar)",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
            ttk.Label(
                grid,
                text="Obecna cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_CUR_W,
            ).grid(row=0, column=1, sticky="e", padx=(0, 12))
            ttk.Label(
                grid,
                text="Nowa cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_NEW_W,
            ).grid(row=0, column=2, sticky="e")

            ttk.Separator(grid, orient="horizontal").grid(
                row=1, column=0, columnspan=3, sticky="ew", pady=(0, 2)
            )

            for i, gkey in enumerate(group_order):
                r = 2 + 2 * i
                ginfo = groups[gkey]
                color_count = len(ginfo["rows"])
                label_txt = f"{ginfo['label']}   ({color_count} kolor.)"
                ttk.Label(grid, text=label_txt).grid(
                    row=r, column=0, sticky="w", padx=(0, 16), pady=4
                )

                uniq_prices = sorted(set(ginfo["prices"]))
                if not uniq_prices:
                    cur_txt = "-"
                elif len(uniq_prices) == 1:
                    cur_txt = uniq_prices[0]
                else:
                    cur_txt = f"rozne ({len(uniq_prices)})"
                ttk.Label(
                    grid,
                    text=cur_txt,
                    foreground="#777",
                    anchor="e",
                    width=_COL_CUR_W,
                ).grid(row=r, column=1, sticky="e", padx=(0, 12))

                var = tk.StringVar(value=global_values.get(gkey, ""))

                def _sync(_a: str, _b: str, _c: str, _k=gkey, _v=var) -> None:
                    global_values[_k] = _v.get()

                var.trace_add("write", _sync)
                ttk.Entry(grid, textvariable=var, width=_COL_NEW_W, justify="right").grid(
                    row=r, column=2, sticky="e"
                )
                global_entries.append((gkey, var))
                if i < len(group_order) - 1:
                    ttk.Separator(grid, orient="horizontal").grid(
                        row=r + 1, column=0, columnspan=3, sticky="ew"
                    )

        def _set_view(mode: str) -> None:
            view_mode.set(mode)
            if mode == "global":
                btn_global.state(["disabled"])
                btn_detail.state(["!disabled"])
                view_hint.configure(
                    text="Jedna cena = wszystkie warianty kolorystyczne w grupie."
                )
                _render_global()
            else:
                btn_detail.state(["disabled"])
                btn_global.state(["!disabled"])
                view_hint.configure(text="Edycja kazdego wariantu osobno.")
                _render_detail()
            canvas.yview_moveto(0.0)

        btn_global.configure(command=lambda: _set_view("global"))
        btn_detail.configure(command=lambda: _set_view("detail"))

        # Domyslnie startujemy w widoku Globalnym (zgodnie z prosba uzytkownika).
        _set_view("global")

        def on_cancel() -> None:
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            dlg.destroy()

        def on_apply() -> None:
            mapping: dict[tuple[str, ...], str] = {}
            mode = view_mode.get()

            if mode == "detail":
                for key, var in detail_entries:
                    val = var.get().strip().replace(",", ".")
                    if not val:
                        continue
                    try:
                        float(val)
                    except ValueError:
                        messagebox.showerror(
                            APP_TITLE,
                            f"Niepoprawna cena: '{val}' dla wariantu {' / '.join(key)}",
                        )
                        return
                    mapping[key] = val
            else:
                # Globalny: jedna cena -> wszystkie warianty kolorystyczne w grupie.
                touched_groups = 0
                for gkey, var in global_entries:
                    val = var.get().strip().replace(",", ".")
                    if not val:
                        continue
                    try:
                        float(val)
                    except ValueError:
                        messagebox.showerror(
                            APP_TITLE,
                            f"Niepoprawna cena: '{val}' dla grupy {groups[gkey]['label']}",
                        )
                        return
                    for row in groups[gkey]["rows"]:
                        mapping[row["key"]] = val
                    touched_groups += 1
                if touched_groups and not mapping:
                    messagebox.showwarning(
                        APP_TITLE, "Wybrane grupy nie maja zadnych wariantow do aktualizacji."
                    )
                    return

            if not mapping:
                messagebox.showwarning(APP_TITLE, "Nie podano zadnej nowej ceny.")
                return

            if mode == "global":
                groups_count = sum(
                    1 for _g, var in global_entries if var.get().strip()
                )
                msg = (
                    f"Tryb GLOBALNY: zaktualizowac {groups_count} grup(y) "
                    f"= {len(mapping)} wariant(y) we WSZYSTKICH produktach typu 'Obraz' na sklepie?\n\n"
                    "Operacji nie mozna cofnac automatycznie."
                )
            else:
                msg = (
                    f"Zaktualizowac {len(mapping)} wariant(y) we WSZYSTKICH produktach "
                    "typu 'Obraz' na sklepie?\n\n"
                    "Operacji nie mozna cofnac automatycznie."
                )
            confirm = messagebox.askyesno(APP_TITLE, msg)
            if not confirm:
                return
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            dlg.destroy()
            self._run_bulk_price_update(mapping)

        ttk.Button(btns, text="Anuluj", command=on_cancel, width=16).pack(side="right")
        ttk.Button(btns, text="Zatwierdz", command=on_apply, width=16).pack(side="right", padx=8)

    def _run_bulk_price_update(self, mapping: dict[tuple[str, ...], str]) -> None:
        self.status_var.set("Aktualizuje ceny... (patrz log)")
        self._append_log("\n=== ZMIANA CEN ===")
        for key, price in mapping.items():
            self._append_log(f"  {' / '.join(key)} -> {price}")

        def worker() -> None:
            try:
                summary = update_all_product_prices(
                    option_values_to_price=mapping,
                    logger=self._enqueue_log,
                )
                self.root.after(
                    0,
                    lambda: self.status_var.set(
                        f"Ceny zaktualizowane: {summary['variants_updated']} (bledow: {len(summary['errors'])})"
                    ),
                )
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        APP_TITLE,
                        (
                            "Zmiana cen zakonczona.\n\n"
                            f"Produktow przetworzonych: {summary['products_total']}\n"
                            f"Zaktualizowanych wariantow: {summary['variants_updated']}\n"
                            f"Pominietych: {summary['variants_skipped']}\n"
                            f"Bledow: {len(summary['errors'])}"
                        ),
                    ),
                )
            except Exception as exc:
                self._enqueue_log(f"[BLAD] {exc}")
                self.root.after(0, lambda: self.status_var.set("Blad - zobacz log."))
                self.root.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Blad:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------- Log plumbing ----------------------
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
        dlg.geometry("1100x640")
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
1. **Dodaj pliki** - przeciagnij i upusc obrazy na okno aplikacji,
   ALBO kliknij szare pole zeby wybrac z dysku.
   - Format nazwy: `Artysta - Tytul obrazu.jpg`
   - Drugi format zdjecia: `Artysta - Tytul F2.jpg` (dogrywka do istniejacego produktu)
   - Dopuszczalne sufiksy korekty na koncu nazwy (patrz **Slowniczek**):
     `Artysta - Tytul KK.jpg`, `Artysta - Tytul WK.jpg`,
     a takze laczone: `Artysta - Tytul F2 KK.jpg`.

## Slowniczek sufiksow nazw plikow
- **F2, F3, ...** - dogrywka kolejnego zdjecia do *istniejacego* produktu.
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
5. **Krok 2: Wklej odpowiedz** - klik w pole `Krok 2`, **schowek zostanie automatycznie wklejony**.
6. **Wykonaj akcje** - aplikacja parsuje JSON, dodaje produkty, dogrywa zdjecia.
   Postep w panelu **Log**.

## Tipy
- **Klik w prompt** kopiuje go do schowka (jesli niepusty).
- **Klik w pole Krok 2** wkleja schowek (jesli niepuste).
- **Zmien ceny...** - aktualizacja masowa cen produktow w sklepie.
- Jesli kolumny w kolejce sa za wask (cos sie urywa), aplikacja sama poszerzy okno.
- Log ma 4 linijki + scroll - cala historia zostaje, tylko widoczne sa ostatnie wpisy.

## Konfiguracja
- W `cursor-api/.env` musi byc:
  - `SHOPIFY_STORE` - subdomena sklepu (`xxx.myshopify.com`).
  - `SHOPIFY_ACCESS_TOKEN` - admin API token.
- Bez tego upload do Shopify nie zadziala (prompt sie nadal generuje).
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
