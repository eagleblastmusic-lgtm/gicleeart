"""Inline-view komponentu 'Produkcja'.

Funkcjonalnosci:
- Lista zamowien (lewa kolumna) z sortowaniem kolumn i filtrem tekstowym.
- Detal zamowienia (prawa kolumna) z polami:
    klient, wariant ramki (Dab/Sosna S/L/XL), ilosc, tytul obrazu, data.
- Kroki produkcji:
    Wydruk:    Przyjete -> Po korekcji kolorystycznej -> Wydrukowany
    Ramka:     Drewno dostepne -> Ramka wycieta -> Wyszlifowana -> Pomalowana
               (po pomalowaniu: 72-godzinne live countdown utwardzania)
    Finalizacja: Zlozone -> Spakowane -> Wyslane
- Live countdown (dni godziny minuty sekundy) - odswiezany co 1s.
- Pasek postepu utwardzania + kolorowe tlo (czerwone <24h / zolte 24-48h / zielone >48h).
- Sortowanie kolumn treeview (klik naglowka).
- Filtr tekstowy nad lista (search po kliencie / tytule / Shopify order no).
- Przycisk 'Pobierz z Shopify' - sync zamowien z sklepu.
- Eksport CSV listy zamowien.
- Alerty opoznionych (>14 dni nie-wyslane) - czerwone tlo.
- Single-source-of-truth: `Komponenty/produkcja/dane/zamowienia.json`.

Wszystko zapisuje sie po kazdej zmianie (auto-save).
Polling zamowien z Shopify obsluguje launcher (co 5 min) przez `orders_sync.py`.
"""

from __future__ import annotations

import csv
import json
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from typing import Any

try:
    from Komponenty._shared.toast import show_toast
except ImportError:  # pragma: no cover
    def show_toast(parent: tk.Misc, text: str, **_kw) -> None:  # type: ignore[override]
        print(f"[toast] {text}")


_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "dane"
_ORDERS_FILE = _DATA_DIR / "zamowienia.json"

_FRAME_VARIANTS = [
    "Dab S", "Dab L", "Dab XL",
    "Sosna S", "Sosna L", "Sosna XL",
]

# Utwardzanie farby - 72 godziny (dokladne liczenie do sekundy).
_PAINT_CURE_HOURS = 72
_PAINT_CURE_SECONDS = _PAINT_CURE_HOURS * 3600

# Alert opoznienia - zamowienie starsze niz tyle dni a jeszcze nie wyslane.
_OVERDUE_THRESHOLD_DAYS = 14


@dataclass
class _StepDef:
    key: str
    label: str
    waiting_hint: str


_WYDRUK_STEPS: list[_StepDef] = [
    _StepDef("po_korekcji", "Po korekcji kolorystycznej",
             "Oczekiwanie na korekcje kolorystyczna"),
    _StepDef("wydrukowany", "Wydrukowany",
             "Oczekiwanie na wydruk"),
]
_WYDRUK_INITIAL = "Przyjete do realizacji"

_RAMKA_STEPS: list[_StepDef] = [
    _StepDef("drewno_dostepne", "Drewno dostepne",
             "Oczekuje na drewno"),
    _StepDef("wycieta", "Ramka wycieta",
             "Ramka oczekuje na wyciecie"),
    _StepDef("wyszlifowana", "Ramka wyszlifowana",
             "Ramka oczekuje na szlif"),
    _StepDef("pomalowana", "Ramka pomalowana (start utwardzania)",
             "Ramka oczekuje na malowanie"),
]


# ============================================================================
# Persistence
# ============================================================================


def _ensure_storage() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _ORDERS_FILE.exists():
        _ORDERS_FILE.write_text(
            json.dumps({"next_id": 1, "orders": []}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _load_db() -> dict[str, Any]:
    _ensure_storage()
    try:
        data = json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("next_id", 1)
    if not isinstance(data.get("orders"), list):
        data["orders"] = []
    # Migracja: stary format `data_pomalowania = "YYYY-MM-DD"` -> "YYYY-MM-DDT00:00:00"
    for o in data["orders"]:
        raw = o.get("data_pomalowania")
        if raw and isinstance(raw, str) and len(raw) == 10 and raw[4] == "-" and "T" not in raw:
            o["data_pomalowania"] = raw + "T00:00:00"
    return data


def _save_db(db: dict[str, Any]) -> None:
    _ensure_storage()
    try:
        _ORDERS_FILE.write_text(
            json.dumps(db, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        messagebox.showerror("Produkcja", f"Nie udalo sie zapisac:\n{e}")


def _new_order_template(order_id: str) -> dict[str, Any]:
    today = date.today().isoformat()
    return {
        "id": order_id,
        "shopify_order_no": "",
        "shopify_order_id": 0,
        "shopify_line_item_id": 0,
        "client": "",
        "ramka_wariant": _FRAME_VARIANTS[0],
        "ilosc": 1,
        "tytul_obrazu": "",
        "data_zamowienia": today,
        "wydruk_step": 0,
        "ramka_step": 0,
        "data_pomalowania": None,  # ISO8601 z czasem, np. "2026-04-18T12:34:56"
        "zlozone": False,
        "spakowane": False,
        "wyslane": False,
        "data_wyslania": None,
        "adres_wysylki": "",
        "tracking_number": "",
        "notatka": "",
        # Rentownosc (do wypelnienia recznie - wszystko PLN):
        "cena_sprzedazy": 0.0,
        "koszt_plotno": 0.0,
        "koszt_wydruku": 0.0,
        "koszt_drewna": 0.0,
        "koszt_farby": 0.0,
        "koszt_wysylki": 0.0,
        "koszt_inne": 0.0,
    }


def _profit_summary(o: dict) -> dict[str, float]:
    """Wylicza marze (brutto) i marze% dla zamowienia."""
    def _f(key: str) -> float:
        try:
            return float(o.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0
    sprzedaz = _f("cena_sprzedazy")
    koszty = sum(_f(k) for k in (
        "koszt_plotno", "koszt_wydruku", "koszt_drewna",
        "koszt_farby", "koszt_wysylki", "koszt_inne",
    ))
    marza = sprzedaz - koszty
    marza_pct = (marza / sprzedaz * 100) if sprzedaz > 0 else 0.0
    return {
        "sprzedaz": sprzedaz,
        "koszty": koszty,
        "marza": marza,
        "marza_pct": marza_pct,
    }


# ============================================================================
# Status / countdown helpers
# ============================================================================


def _wydruk_status(o: dict) -> tuple[str, str]:
    s = int(o.get("wydruk_step") or 0)
    if s <= 0:
        return ("Przyjete do realizacji", "Oczekiwanie na korekcje kolorystyczna")
    if s == 1:
        return ("Po korekcji kolorystycznej", "Oczekiwanie na wydruk")
    return ("Wydrukowany", "Wydruk gotowy")


def _ramka_status(o: dict) -> tuple[str, str]:
    s = int(o.get("ramka_step") or 0)
    if s <= 0:
        return ("Oczekuje na drewno", "Czekam az drewno bedzie dostepne")
    if s == 1:
        return ("Drewno dostepne", "Ramka oczekuje na wyciecie")
    if s == 2:
        return ("Ramka wycieta", "Ramka oczekuje na szlif")
    if s == 3:
        return ("Ramka wyszlifowana", "Ramka oczekuje na malowanie")
    remaining = _cure_remaining_seconds(o)
    if remaining > 0:
        return (
            f"Ramka pomalowana - utwardzanie ({_format_countdown(remaining)})",
            "Czekam na utwardzenie",
        )
    return ("Ramka utwardzona, gotowa do zlozenia", "Mozna skladac elementy")


def _cure_start(o: dict) -> datetime | None:
    raw = o.get("data_pomalowania")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _cure_end(o: dict) -> datetime | None:
    start = _cure_start(o)
    if start is None:
        return None
    return start + timedelta(hours=_PAINT_CURE_HOURS)


def _cure_remaining_seconds(o: dict) -> int:
    end = _cure_end(o)
    if end is None:
        return 0
    delta = end - datetime.now()
    return max(0, int(delta.total_seconds()))


def _cure_progress_fraction(o: dict) -> float:
    """0.0 (start) -> 1.0 (utwardzone)."""
    start = _cure_start(o)
    if start is None:
        return 0.0
    elapsed = (datetime.now() - start).total_seconds()
    return max(0.0, min(1.0, elapsed / _PAINT_CURE_SECONDS))


def _format_countdown(seconds: int) -> str:
    """Format '2d 05g 43m 12s' (albo '43m 12s' jesli <1h, etc.)."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if days > 0:
        return f"{days}d {hours:02d}g {minutes:02d}m {secs:02d}s"
    if hours > 0:
        return f"{hours:02d}g {minutes:02d}m {secs:02d}s"
    if minutes > 0:
        return f"{minutes:02d}m {secs:02d}s"
    return f"{secs}s"


def _cure_color(o: dict) -> str:
    """Kolor tla countdown w zaleznosci od czasu pozostalego."""
    remaining = _cure_remaining_seconds(o)
    if remaining <= 0:
        return "#2e7d32"  # zielony - utwardzone
    hours = remaining / 3600
    if hours < 24:
        return "#c62828"  # czerwony - ostatnie 24h
    if hours < 48:
        return "#ef6c00"  # pomaranczowy - 24-48h
    return "#43a047"  # zielony - ma duzo czasu (>48h)


def _ramka_ready(o: dict) -> bool:
    s = int(o.get("ramka_step") or 0)
    if s < 4:
        return False
    return _cure_remaining_seconds(o) == 0


def _wydruk_ready(o: dict) -> bool:
    return int(o.get("wydruk_step") or 0) >= 2


def _is_overdue(o: dict) -> bool:
    """Zamowienie stare >14 dni a jeszcze nie wyslane."""
    if o.get("wyslane"):
        return False
    try:
        d = date.fromisoformat(str(o.get("data_zamowienia") or ""))
    except ValueError:
        return False
    return (date.today() - d).days >= _OVERDUE_THRESHOLD_DAYS


def _progress_steps(o: dict) -> tuple[int, int]:
    """Zwraca (completed_steps, total_steps) dla ogolnego postepu zamowienia (0-5)."""
    total = 5  # wydruk_gotowy + ramka_pomalowana + utwardzona + zlozone + wyslane
    completed = 0
    if _wydruk_ready(o):
        completed += 1
    if int(o.get("ramka_step") or 0) >= 4:
        completed += 1
    if _ramka_ready(o):
        completed += 1
    if o.get("zlozone"):
        completed += 1
    if o.get("wyslane"):
        completed += 1
    return (completed, total)


def _overall_status(o: dict) -> tuple[str, str]:
    if o.get("wyslane"):
        return ("Zamowienie zrealizowane", "#2e7d32")
    if _is_overdue(o):
        return ("OPOZNIONE - " + _base_status_label(o), "#b71c1c")
    return (_base_status_label(o), _base_status_color(o))


def _base_status_label(o: dict) -> str:
    if o.get("spakowane"):
        return "Gotowe do wysylki"
    if o.get("zlozone"):
        return "Oczekiwanie na spakowanie"
    if _ramka_ready(o) and _wydruk_ready(o):
        return "Oczekuje na zlozenie elementow"
    waiting: list[str] = []
    if not _wydruk_ready(o):
        _, wh = _wydruk_status(o)
        waiting.append(f"wydruk: {wh}")
    if not _ramka_ready(o):
        _, rh = _ramka_status(o)
        waiting.append(f"ramka: {rh}")
    return "W produkcji  -  " + " | ".join(waiting)


def _base_status_color(o: dict) -> str:
    if o.get("spakowane"):
        return "#1565c0"
    if o.get("zlozone"):
        return "#6a1b9a"
    if _ramka_ready(o) and _wydruk_ready(o):
        return "#ef6c00"
    return "#5d4037"


# ============================================================================


class ProdukcjaView(ttk.Frame):
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        super().__init__(parent)
        self.on_back = on_back
        self.db: dict[str, Any] = _load_db()
        self.filter_mode = tk.StringVar(value="aktywne")
        self.search_text = tk.StringVar(value="")
        self.selected_id: str | None = None
        self._field_vars: dict[str, tk.Variable] = {}

        # Sortowanie Treeview
        self._sort_col: str | None = None
        self._sort_desc: bool = False

        # Cache do live countdown: referencje do widgetow countdown-a w detalu
        self._countdown_widgets: list[tuple[tk.Widget, str]] = []  # (widget, role)
        self._countdown_progressbar: ttk.Progressbar | None = None

        self._build()
        self._refresh_list()
        # Live countdown tick co 1s
        self.after(1000, self._tick_countdown)
        # Pelne odswiezanie listy co 60s (alerty/statusy)
        self.after(60_000, self._tick_full_refresh)

    # ----------------- UI build -----------------
    def _build(self) -> None:
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))
        ttk.Button(toolbar, text="← Wroc", command=self.on_back).pack(side="left")
        ttk.Label(toolbar, text="Produkcja", font=("Segoe UI", 14, "bold")).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(toolbar, text="Instrukcja", command=self._show_help).pack(side="right")
        ttk.Button(
            toolbar, text="Otworz folder danych", command=self._open_data_folder
        ).pack(side="right", padx=6)
        ttk.Button(toolbar, text="⬇ Eksport CSV", command=self._export_csv).pack(
            side="right", padx=6
        )
        ttk.Button(
            toolbar, text="📦 Archiwizuj stare",
            command=self._run_archive_dialog,
        ).pack(side="right", padx=6)
        ttk.Button(
            toolbar, text="↓ Pobierz z Shopify",
            command=self._sync_from_shopify,
        ).pack(side="right", padx=6)
        ttk.Button(toolbar, text="+ Nowe zamowienie", command=self._new_order).pack(
            side="right", padx=6
        )

        # Sync status
        self.sync_status_var = tk.StringVar(value="")
        ttk.Label(
            toolbar, textvariable=self.sync_status_var,
            foreground="#666", font=("Segoe UI", 9),
        ).pack(side="right", padx=(0, 10))
        self._update_sync_status_label()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(4, 6))

        # ---- LEFT ----
        left = ttk.Frame(paned)
        paned.add(left, weight=2)

        # Pasek filtrow
        filt_row1 = ttk.Frame(left)
        filt_row1.pack(fill="x", pady=(2, 2))
        ttk.Label(filt_row1, text="Filtr:").pack(side="left")
        for val, lbl in (
            ("aktywne", "Aktywne"),
            ("wszystkie", "Wszystkie"),
            ("zrealizowane", "Zrealizowane"),
            ("opoznione", "Opoznione"),
        ):
            ttk.Radiobutton(
                filt_row1, text=lbl, value=val,
                variable=self.filter_mode, command=self._refresh_list,
            ).pack(side="left", padx=(6, 0))
        self.count_var = tk.StringVar(value="0 zamowien")
        ttk.Label(filt_row1, textvariable=self.count_var, foreground="#666").pack(side="right")

        # Search bar
        filt_row2 = ttk.Frame(left)
        filt_row2.pack(fill="x", pady=(0, 4))
        ttk.Label(filt_row2, text="Szukaj:").pack(side="left")
        search_entry = ttk.Entry(filt_row2, textvariable=self.search_text)
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 4))
        self.search_text.trace_add("write", lambda *_: self._refresh_list())
        ttk.Button(
            filt_row2, text="Wyczysc",
            command=lambda: self.search_text.set(""),
        ).pack(side="left")

        # Treeview
        cols = ("id", "client", "wariant", "progress", "status")
        self.tree = ttk.Treeview(
            left, columns=cols, show="headings", selectmode="browse", height=18
        )
        self.tree.heading("id", text="ID", command=lambda: self._sort_by("id"))
        self.tree.heading("client", text="Klient / tytul", command=lambda: self._sort_by("client"))
        self.tree.heading("wariant", text="Ramka", command=lambda: self._sort_by("wariant"))
        self.tree.heading("progress", text="Postep", command=lambda: self._sort_by("progress"))
        self.tree.heading("status", text="Status", command=lambda: self._sort_by("status"))
        self.tree.column("id", width=90, stretch=False)
        self.tree.column("client", width=180)
        self.tree.column("wariant", width=80, stretch=False)
        self.tree.column("progress", width=80, stretch=False, anchor="center")
        self.tree.column("status", width=260)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_row_selected())

        self.tree.tag_configure("done", foreground="#888")
        self.tree.tag_configure("ready", foreground="#0d47a1")
        self.tree.tag_configure("waiting", foreground="#5d4037")
        self.tree.tag_configure("overdue", background="#ffebee", foreground="#b71c1c")
        self.tree.tag_configure("cure_urgent", background="#ffe0e0")

        # ---- RIGHT ----
        right_outer = ttk.Frame(paned)
        paned.add(right_outer, weight=3)

        canvas = tk.Canvas(right_outer, borderwidth=0, highlightthickness=0)
        sb = ttk.Scrollbar(right_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._right_canvas = canvas

        self.detail_holder = ttk.Frame(canvas)
        self._detail_window = canvas.create_window(
            (0, 0), window=self.detail_holder, anchor="nw"
        )
        self.detail_holder.bind(
            "<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(self._detail_window, width=e.width),
        )

        def _wheel(e: tk.Event) -> None:
            if not e.delta:
                return
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        self._render_empty_detail()

    # ----------------- List / sort / filter ----------------
    def _orders_filtered(self) -> list[dict]:
        mode = self.filter_mode.get()
        ft = (self.search_text.get() or "").lower().strip()
        out: list[dict] = []
        for o in self.db.get("orders", []):
            if mode == "aktywne" and o.get("wyslane"):
                continue
            if mode == "zrealizowane" and not o.get("wyslane"):
                continue
            if mode == "opoznione" and not _is_overdue(o):
                continue
            if ft:
                haystack = " ".join([
                    str(o.get("id", "")),
                    str(o.get("client", "")),
                    str(o.get("tytul_obrazu", "")),
                    str(o.get("shopify_order_no", "")),
                    str(o.get("ramka_wariant", "")),
                    str(o.get("notatka", "")),
                ]).lower()
                if ft not in haystack:
                    continue
            out.append(o)

        if self._sort_col:
            out.sort(key=lambda x: self._sort_key(x, self._sort_col), reverse=self._sort_desc)
        else:
            out.sort(key=lambda x: (x.get("data_zamowienia", ""), x.get("id", "")), reverse=True)
        return out

    def _sort_key(self, o: dict, col: str) -> Any:
        if col == "id":
            return o.get("id", "")
        if col == "client":
            return (str(o.get("client") or "").lower(),
                    str(o.get("tytul_obrazu") or "").lower())
        if col == "wariant":
            return str(o.get("ramka_wariant") or "")
        if col == "progress":
            done, total = _progress_steps(o)
            return (done / total) if total else 0
        if col == "status":
            return _overall_status(o)[0]
        return ""

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False
        self._refresh_list()

    def _refresh_list(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        items = self._orders_filtered()
        for o in items:
            status, _color = _overall_status(o)
            client_part = o.get("client") or "(bez klienta)"
            title_part = o.get("tytul_obrazu") or ""
            cl_text = client_part if not title_part else f"{client_part}  -  {title_part}"
            done, total = _progress_steps(o)
            progress_str = "■" * done + "□" * (total - done)
            tags: list[str] = []
            if o.get("wyslane"):
                tags.append("done")
            elif o.get("spakowane") or o.get("zlozone"):
                tags.append("ready")
            else:
                tags.append("waiting")
            if _is_overdue(o):
                tags.append("overdue")
            elif int(o.get("ramka_step") or 0) >= 4:
                remaining = _cure_remaining_seconds(o)
                if 0 < remaining < 24 * 3600:
                    tags.append("cure_urgent")
            self.tree.insert(
                "", "end",
                iid=o["id"],
                values=(o["id"], cl_text, o.get("ramka_wariant", ""), progress_str, status),
                tags=tuple(tags),
            )
        total_cnt = len(items)
        self.count_var.set(f"{total_cnt} zamowien")

        # Naglowki z ikonka sortowania
        for c, base in (("id", "ID"), ("client", "Klient / tytul"),
                       ("wariant", "Ramka"), ("progress", "Postep"), ("status", "Status")):
            arrow = ""
            if self._sort_col == c:
                arrow = "  ▼" if self._sort_desc else "  ▲"
            self.tree.heading(c, text=base + arrow, command=lambda col=c: self._sort_by(col))

        if self.selected_id and self.tree.exists(self.selected_id):
            self.tree.selection_set(self.selected_id)
            self.tree.see(self.selected_id)
        elif items:
            first = items[0]["id"]
            self.tree.selection_set(first)
            self.tree.see(first)
            self.selected_id = first
            self._render_detail()
        else:
            self.selected_id = None
            self._render_empty_detail()

    def _refresh_list_keep_selection(self) -> None:
        """Odswieza tylko wartosci wierszy w tree (bez zmiany zaznaczenia/detalu)."""
        for o in self.db.get("orders", []):
            iid = o["id"]
            if not self.tree.exists(iid):
                continue
            status, _c = _overall_status(o)
            client_part = o.get("client") or "(bez klienta)"
            title_part = o.get("tytul_obrazu") or ""
            cl_text = client_part if not title_part else f"{client_part}  -  {title_part}"
            done, total = _progress_steps(o)
            progress_str = "■" * done + "□" * (total - done)
            self.tree.item(
                iid,
                values=(o["id"], cl_text, o.get("ramka_wariant", ""), progress_str, status),
            )

    def _on_row_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        oid = sel[0]
        if oid == self.selected_id:
            return
        self.selected_id = oid
        self._render_detail()

    # ----------------- Order CRUD -----------------
    def _new_order(self) -> None:
        next_id_n = int(self.db.get("next_id") or 1)
        order_id = f"ORD-{next_id_n:04d}"
        self.db["next_id"] = next_id_n + 1
        order = _new_order_template(order_id)
        self.db.setdefault("orders", []).append(order)
        _save_db(self.db)
        self.selected_id = order_id
        self._refresh_list()
        show_toast(self.winfo_toplevel(), f"Utworzono {order_id}", duration_ms=1500)

    def _delete_order(self, order_id: str) -> None:
        if not messagebox.askyesno(
            "Produkcja",
            f"Usunac zamowienie {order_id}? Tej operacji nie mozna cofnac.",
            icon="warning",
            parent=self.winfo_toplevel(),
        ):
            return
        self.db["orders"] = [o for o in self.db.get("orders", []) if o["id"] != order_id]
        _save_db(self.db)
        if self.selected_id == order_id:
            self.selected_id = None
        self._refresh_list()

    def _current_order(self) -> dict | None:
        if not self.selected_id:
            return None
        for o in self.db.get("orders", []):
            if o["id"] == self.selected_id:
                return o
        return None

    def _persist(self) -> None:
        _save_db(self.db)

    # ----------------- Shopify sync -----------------
    def _sync_from_shopify(self) -> None:
        import threading

        def _worker() -> None:
            try:
                from . import orders_sync
                added = orders_sync.sync_orders(logger=lambda m: None)
            except Exception as exc:  # noqa: BLE001
                try:
                    self.after(0, lambda: messagebox.showerror(
                        "Produkcja",
                        f"Nie udalo sie zsynchronizowac z Shopify:\n{exc}",
                    ))
                except tk.TclError:
                    pass
                return
            self.db = _load_db()
            try:
                self.after(0, lambda: self._refresh_list())
                self.after(0, self._update_sync_status_label)
                if added:
                    first = added[0]
                    self.after(0, lambda: show_toast(
                        self.winfo_toplevel(),
                        f"Dodano {len(added)} zamowien "
                        f"(pierwsze: {first.get('shopify_order_no') or '?'})",
                        duration_ms=2500,
                    ))
                else:
                    self.after(0, lambda: show_toast(
                        self.winfo_toplevel(),
                        "Brak nowych zamowien z Shopify",
                        duration_ms=1500,
                    ))
            except tk.TclError:
                pass

        self.sync_status_var.set("Synchronizuje z Shopify...")
        threading.Thread(target=_worker, daemon=True).start()

    def _update_sync_status_label(self) -> None:
        try:
            from . import orders_sync
            state = orders_sync.get_sync_state()
        except ImportError:
            return
        iso = state.get("last_sync_iso")
        if not iso:
            self.sync_status_var.set("Shopify: (jeszcze nie synchronizowano)")
            return
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            self.sync_status_var.set(
                f"Shopify sync: {dt.strftime('%Y-%m-%d %H:%M')}"
            )
        except ValueError:
            self.sync_status_var.set(f"Shopify sync: {iso}")

    # ----------------- Eksport CSV -----------------
    def _export_csv(self) -> None:
        items = self._orders_filtered()
        if not items:
            messagebox.showinfo("Produkcja", "Brak zamowien do eksportu (wg filtrow).",
                                parent=self.winfo_toplevel())
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
            initialfile="zamowienia_produkcja.csv",
            parent=self.winfo_toplevel(),
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "id", "shopify_order_no", "client", "tytul_obrazu",
                    "ramka_wariant", "ilosc", "data_zamowienia", "status",
                    "wydruk_step", "ramka_step", "data_pomalowania",
                    "zlozone", "spakowane", "wyslane", "data_wyslania",
                    "adres_wysylki", "notatka",
                ])
                for o in items:
                    status, _c = _overall_status(o)
                    writer.writerow([
                        o.get("id", ""), o.get("shopify_order_no", ""),
                        o.get("client", ""), o.get("tytul_obrazu", ""),
                        o.get("ramka_wariant", ""), o.get("ilosc", 1),
                        o.get("data_zamowienia", ""), status,
                        o.get("wydruk_step", 0), o.get("ramka_step", 0),
                        o.get("data_pomalowania", ""),
                        int(bool(o.get("zlozone"))),
                        int(bool(o.get("spakowane"))),
                        int(bool(o.get("wyslane"))),
                        o.get("data_wyslania", "") or "",
                        (o.get("adres_wysylki") or "").replace("\n", " / "),
                        (o.get("notatka") or "").replace("\n", " / "),
                    ])
        except OSError as e:
            messagebox.showerror("Produkcja", f"Blad zapisu:\n{e}", parent=self.winfo_toplevel())
            return
        show_toast(self.winfo_toplevel(), f"Zapisano {len(items)} zamowien")

    # ----------------- Detail rendering -----------------
    def _clear_detail(self) -> None:
        for child in self.detail_holder.winfo_children():
            child.destroy()
        self._field_vars.clear()
        self._countdown_widgets = []
        self._countdown_progressbar = None

    def _render_empty_detail(self) -> None:
        self._clear_detail()
        ttk.Label(
            self.detail_holder,
            text="(zaznacz zamowienie z lewej kolumny lub utworz nowe)",
            foreground="#888",
            padding=(12, 24),
        ).pack(anchor="w")

    def _render_detail(self) -> None:
        self._clear_detail()
        o = self._current_order()
        if not o:
            self._render_empty_detail()
            return

        # Banner
        status_text, color = _overall_status(o)
        banner = tk.Frame(self.detail_holder, bg=color)
        banner.pack(fill="x", padx=2, pady=(2, 8))
        tk.Label(
            banner,
            text=f"  {o['id']}  -  {status_text}  ",
            bg=color, fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=8, pady=8,
        ).pack(side="left")
        if o.get("shopify_order_no"):
            tk.Label(
                banner, text=f"Shopify: {o['shopify_order_no']}",
                bg=color, fg="#ffeb3b",
                font=("Segoe UI", 9, "italic"), padx=8,
            ).pack(side="left")
        tk.Button(
            banner, text="Usun zamowienie",
            command=lambda oid=o["id"]: self._delete_order(oid),
            relief="flat", bg="#ffebee", fg="#b00020",
            cursor="hand2", takefocus=False,
        ).pack(side="right", padx=8, pady=4)

        # Ogolny progress
        done, total = _progress_steps(o)
        prog_wrap = ttk.Frame(self.detail_holder)
        prog_wrap.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(
            prog_wrap, text=f"Postep: {done}/{total} krokow",
            font=("Segoe UI", 9, "bold"), foreground="#555",
        ).pack(side="left")
        overall_pb = ttk.Progressbar(
            prog_wrap, orient="horizontal", length=300,
            mode="determinate", maximum=total, value=done,
        )
        overall_pb.pack(side="left", padx=(8, 0), fill="x", expand=True)

        self._build_basic_section(o)
        self._build_wydruk_section(o)
        self._build_ramka_section(o)
        self._build_final_section(o)
        self._build_profitability_section(o)

    def _section_header(self, title: str) -> ttk.Frame:
        wrap = ttk.LabelFrame(self.detail_holder, text=title)
        wrap.pack(fill="x", padx=6, pady=(4, 8))
        return wrap

    def _build_basic_section(self, o: dict) -> None:
        sec = self._section_header("Dane zamowienia")
        grid = ttk.Frame(sec)
        grid.pack(fill="x", padx=8, pady=6)
        for c in range(4):
            grid.columnconfigure(c, weight=1 if c in (1, 3) else 0)

        ttk.Label(grid, text="Klient:").grid(row=0, column=0, sticky="w", pady=2)
        client_var = tk.StringVar(value=o.get("client", ""))
        ttk.Entry(grid, textvariable=client_var).grid(
            row=0, column=1, sticky="ew", padx=(4, 12), pady=2
        )
        client_var.trace_add("write", lambda *_a: self._set_field("client", client_var.get()))

        ttk.Label(grid, text="Tytul obrazu:").grid(row=0, column=2, sticky="w", pady=2)
        title_var = tk.StringVar(value=o.get("tytul_obrazu", ""))
        ttk.Entry(grid, textvariable=title_var).grid(
            row=0, column=3, sticky="ew", pady=2
        )
        title_var.trace_add(
            "write", lambda *_a: self._set_field("tytul_obrazu", title_var.get())
        )

        ttk.Label(grid, text="Wariant ramki:").grid(row=1, column=0, sticky="w", pady=2)
        var_var = tk.StringVar(value=o.get("ramka_wariant", _FRAME_VARIANTS[0]))
        cb = ttk.Combobox(
            grid, textvariable=var_var,
            values=_FRAME_VARIANTS, state="readonly", width=14,
        )
        cb.grid(row=1, column=1, sticky="w", padx=(4, 12), pady=2)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._set_field("ramka_wariant", var_var.get()))

        ttk.Label(grid, text="Ilosc sztuk:").grid(row=1, column=2, sticky="w", pady=2)
        qty_var = tk.IntVar(value=int(o.get("ilosc") or 1))
        spin = ttk.Spinbox(grid, from_=1, to=99, textvariable=qty_var, width=6)
        spin.grid(row=1, column=3, sticky="w", pady=2)

        def _on_qty(*_a) -> None:
            try:
                v = int(qty_var.get())
            except (tk.TclError, ValueError):
                v = 1
            self._set_field("ilosc", max(1, v))

        qty_var.trace_add("write", _on_qty)

        ttk.Label(grid, text="Data zamowienia:").grid(row=2, column=0, sticky="w", pady=2)
        date_var = tk.StringVar(value=o.get("data_zamowienia") or date.today().isoformat())
        ttk.Entry(grid, textvariable=date_var, width=14).grid(
            row=2, column=1, sticky="w", padx=(4, 12), pady=2
        )
        date_var.trace_add(
            "write", lambda *_a: self._set_field("data_zamowienia", date_var.get())
        )

        ttk.Label(grid, text="Nr Shopify (opc.):").grid(
            row=2, column=2, sticky="w", pady=2
        )
        sho_var = tk.StringVar(value=o.get("shopify_order_no", ""))
        ttk.Entry(grid, textvariable=sho_var).grid(
            row=2, column=3, sticky="ew", pady=2
        )
        sho_var.trace_add(
            "write", lambda *_a: self._set_field("shopify_order_no", sho_var.get())
        )

        ttk.Label(grid, text="Notatka:").grid(row=3, column=0, sticky="nw", pady=(4, 2))
        notatka = tk.Text(grid, height=2, wrap="word", font=("Segoe UI", 9))
        notatka.grid(row=3, column=1, columnspan=3, sticky="ew", pady=(4, 2))
        notatka.insert("1.0", o.get("notatka", ""))

        def _on_notatka_change(_e: tk.Event) -> None:
            self._set_field("notatka", notatka.get("1.0", "end-1c"))

        notatka.bind("<FocusOut>", _on_notatka_change)
        notatka.bind("<KeyRelease>", _on_notatka_change)

    def _build_wydruk_section(self, o: dict) -> None:
        sec = self._section_header("Wydruk")
        cur, hint = _wydruk_status(o)
        ttk.Label(
            sec, text=f"Aktualnie: {cur}    →    {hint}",
            foreground="#1565c0", font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=8, pady=(4, 6))
        ttk.Label(sec, text=f"   ☑  {_WYDRUK_INITIAL}", foreground="#444").pack(
            anchor="w", padx=8
        )
        cur_step = int(o.get("wydruk_step") or 0)
        for i, step in enumerate(_WYDRUK_STEPS, start=1):
            checked_var = tk.IntVar(value=1 if cur_step >= i else 0)

            def _on_toggle(target_step: int = i, var: tk.IntVar = checked_var) -> None:
                self._set_wydruk_step(target_step, bool(var.get()))

            ttk.Checkbutton(
                sec, text=f"   {step.label}",
                variable=checked_var, command=_on_toggle,
            ).pack(anchor="w", padx=8, pady=2)

    def _set_wydruk_step(self, target: int, checked: bool) -> None:
        o = self._current_order()
        if not o:
            return
        cur = int(o.get("wydruk_step") or 0)
        new_step = max(cur, target) if checked else min(cur, target - 1)
        new_step = max(0, min(2, new_step))
        if new_step != cur:
            o["wydruk_step"] = new_step
            self._persist()
            self._render_detail()
            self._refresh_list_keep_selection()

    def _build_ramka_section(self, o: dict) -> None:
        sec = self._section_header("Ramka")
        cur, hint = _ramka_status(o)
        ttk.Label(
            sec, text=f"Aktualnie: {cur}    →    {hint}",
            foreground="#6a1b9a", font=("Segoe UI", 10, "bold"),
            wraplength=540, justify="left",
        ).pack(anchor="w", padx=8, pady=(4, 6))

        cur_step = int(o.get("ramka_step") or 0)
        for i, step in enumerate(_RAMKA_STEPS, start=1):
            checked_var = tk.IntVar(value=1 if cur_step >= i else 0)

            def _on_toggle(target_step: int = i, var: tk.IntVar = checked_var) -> None:
                self._set_ramka_step(target_step, bool(var.get()))

            ttk.Checkbutton(
                sec, text=f"   {step.label}",
                variable=checked_var, command=_on_toggle,
            ).pack(anchor="w", padx=8, pady=2)

        # Countdown utwardzania (tylko gdy pomalowana)
        if cur_step >= 4:
            countdown_box = tk.Frame(sec, bg=_cure_color(o))
            countdown_box.pack(fill="x", padx=8, pady=(10, 6))

            remaining = _cure_remaining_seconds(o)
            if remaining > 0:
                txt = f"⏳ Utwardzanie: {_format_countdown(remaining)}"
            else:
                txt = "✅ Utwardzone - gotowe do zlozenia"
            label = tk.Label(
                countdown_box, text=txt, bg=_cure_color(o), fg="white",
                font=("Consolas", 13, "bold"), padx=12, pady=8,
            )
            label.pack(side="left")

            start = _cure_start(o)
            end = _cure_end(o)
            if start and end:
                info = tk.Label(
                    countdown_box,
                    text=f"   start: {start.strftime('%Y-%m-%d %H:%M')}  |  "
                         f"koniec: {end.strftime('%Y-%m-%d %H:%M')}",
                    bg=_cure_color(o), fg="white",
                    font=("Segoe UI", 9),
                )
                info.pack(side="left", padx=(6, 0))
                self._countdown_widgets.append((info, "info"))

            # Progressbar utwardzania
            pb = ttk.Progressbar(
                sec, orient="horizontal", length=600,
                mode="determinate", maximum=100,
                value=round(_cure_progress_fraction(o) * 100),
            )
            pb.pack(fill="x", padx=8, pady=(0, 4))
            self._countdown_progressbar = pb

            # Zapamietaj referencje do aktualizacji co 1s
            self._countdown_widgets.append((label, "label"))
            self._countdown_widgets.append((countdown_box, "bg"))

    def _set_ramka_step(self, target: int, checked: bool) -> None:
        o = self._current_order()
        if not o:
            return
        cur = int(o.get("ramka_step") or 0)
        new_step = max(cur, target) if checked else min(cur, target - 1)
        new_step = max(0, min(4, new_step))
        prev_painted = cur >= 4
        new_painted = new_step >= 4
        if new_painted and not prev_painted:
            # Timestamp z sekunda precyzja - kluczowe dla live countdown
            o["data_pomalowania"] = datetime.now().isoformat(timespec="seconds")
        elif not new_painted and prev_painted:
            o["data_pomalowania"] = None
        if new_step != cur or (new_painted and not prev_painted):
            o["ramka_step"] = new_step
            self._persist()
            self._render_detail()
            self._refresh_list_keep_selection()

    def _build_final_section(self, o: dict) -> None:
        sec = self._section_header("Zlozenie / pakowanie / wysylka")
        ready = _ramka_ready(o) and _wydruk_ready(o)
        if not ready:
            hint = "Najpierw skoncz wydruk i ramke (z utwardzaniem)."
            color = "#b71c1c"
        elif not o.get("zlozone"):
            hint = "Komponenty gotowe - zloz elementy."
            color = "#ef6c00"
        elif not o.get("spakowane"):
            hint = "Zlozone - oczekiwanie na spakowanie."
            color = "#6a1b9a"
        elif not o.get("wyslane"):
            hint = "Spakowane - kliknij 'Wyslij...' i zatwierdz wysylke."
            color = "#1565c0"
        else:
            hint = "Zamowienie zrealizowane."
            color = "#2e7d32"

        ttk.Label(
            sec, text=hint, foreground=color, font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=8, pady=(4, 6))

        z_var = tk.IntVar(value=1 if o.get("zlozone") else 0)
        cb_z = ttk.Checkbutton(
            sec, text="   Zlozone", variable=z_var,
            command=lambda: self._set_step("zlozone", bool(z_var.get())),
        )
        cb_z.pack(anchor="w", padx=8, pady=2)
        if not ready:
            cb_z.state(["disabled"])

        s_var = tk.IntVar(value=1 if o.get("spakowane") else 0)
        cb_s = ttk.Checkbutton(
            sec, text="   Spakowane", variable=s_var,
            command=lambda: self._set_step("spakowane", bool(s_var.get())),
        )
        cb_s.pack(anchor="w", padx=8, pady=2)
        if not o.get("zlozone"):
            cb_s.state(["disabled"])

        ws = ttk.Frame(sec)
        ws.pack(fill="x", padx=8, pady=2)
        w_var = tk.IntVar(value=1 if o.get("wyslane") else 0)
        cb_w = ttk.Checkbutton(
            ws, text="   Wyslane", variable=w_var,
            command=lambda: self._set_step("wyslane", bool(w_var.get())),
        )
        cb_w.pack(side="left")
        if not o.get("spakowane"):
            cb_w.state(["disabled"])

        send_btn = ttk.Button(
            ws, text="Wyslij...", command=self._open_send_dialog
        )
        send_btn.pack(side="right")
        if not o.get("spakowane") or o.get("wyslane"):
            send_btn.state(["disabled"])

        ship_btn = ttk.Button(
            ws, text="📦 Przygotuj przesylke...",
            command=self._open_shipping_dialog,
        )
        ship_btn.pack(side="right", padx=(0, 6))
        if not o.get("spakowane"):
            ship_btn.state(["disabled"])

        adr_row = ttk.Frame(sec)
        adr_row.pack(fill="x", padx=8, pady=(6, 4))
        ttk.Label(adr_row, text="Adres wysylki:", foreground="#555").grid(
            row=0, column=0, sticky="nw"
        )
        adr_entry = tk.Text(adr_row, height=3, wrap="word", font=("Segoe UI", 9))
        adr_entry.insert("1.0", o.get("adres_wysylki", ""))
        adr_entry.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        adr_row.columnconfigure(1, weight=1)

        def _save_adr(_e: tk.Event) -> None:
            self._set_field("adres_wysylki", adr_entry.get("1.0", "end-1c"))

        adr_entry.bind("<FocusOut>", _save_adr)

        tracking_row = ttk.Frame(sec)
        tracking_row.pack(fill="x", padx=8, pady=(4, 4))
        ttk.Label(tracking_row, text="Nr trackingu:", foreground="#555").pack(side="left")
        tr_var = tk.StringVar(value=o.get("tracking_number", "") or "")
        ttk.Entry(tracking_row, textvariable=tr_var, width=28).pack(
            side="left", padx=(6, 0), fill="x", expand=True
        )
        tr_var.trace_add(
            "write", lambda *_a: self._set_field("tracking_number", tr_var.get())
        )

        if o.get("data_wyslania"):
            ttk.Label(
                sec, text=f"Wyslano: {o['data_wyslania']}",
                foreground="#2e7d32",
            ).pack(anchor="w", padx=8, pady=(2, 4))

    def _open_send_dialog(self) -> None:
        o = self._current_order()
        if not o:
            return
        if not o.get("spakowane"):
            messagebox.showinfo("Produkcja", "Najpierw oznacz zamowienie jako spakowane.")
            return
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title(f"Wyslij {o['id']}")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        dlg.geometry("520x340")

        ttk.Label(
            dlg, text=f"Wysylka zamowienia {o['id']}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(
            dlg,
            text=(
                f"Klient: {o.get('client') or '(brak)'}\n"
                f"Tytul:  {o.get('tytul_obrazu') or '(brak)'}\n"
                f"Ramka:  {o.get('ramka_wariant', '')}  x {o.get('ilosc', 1)}"
            ),
            justify="left", foreground="#444",
        ).pack(anchor="w", padx=12)

        ttk.Label(dlg, text="Adres wysylki:", foreground="#555").pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        adr_text = scrolledtext.ScrolledText(dlg, height=6, wrap="word")
        adr_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        adr_text.insert("1.0", o.get("adres_wysylki", ""))

        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=12, pady=8)

        def _confirm() -> None:
            adr = adr_text.get("1.0", "end-1c").strip()
            o["adres_wysylki"] = adr
            o["wyslane"] = True
            o["data_wyslania"] = date.today().isoformat()
            self._persist()
            dlg.destroy()
            self._render_detail()
            self._refresh_list()
            show_toast(
                self.winfo_toplevel(),
                f"{o['id']} - oznaczone jako wyslane",
                duration_ms=1800,
            )

        ttk.Button(btns, text="Anuluj", command=dlg.destroy, width=14).pack(side="right")
        ttk.Button(btns, text="Potwierdz wysylke", command=_confirm, width=22).pack(
            side="right", padx=8
        )

    # ----------------- Field helpers -----------------
    def _set_field(self, name: str, value: Any) -> None:
        o = self._current_order()
        if not o:
            return
        if o.get(name) == value:
            return
        o[name] = value
        self._persist()
        self._refresh_list_keep_selection()

    def _set_step(self, name: str, value: bool) -> None:
        o = self._current_order()
        if not o:
            return
        if bool(o.get(name)) == value:
            return
        o[name] = value
        if name == "zlozone" and not value:
            o["spakowane"] = False
            o["wyslane"] = False
            o["data_wyslania"] = None
        if name == "spakowane" and not value:
            o["wyslane"] = False
            o["data_wyslania"] = None
        if name == "wyslane":
            if value:
                o["data_wyslania"] = date.today().isoformat()
            else:
                o["data_wyslania"] = None
        self._persist()
        self._render_detail()
        self._refresh_list()

    # ----------------- Live tick (co 1s) -----------------
    def _tick_countdown(self) -> None:
        """Co 1s odswieza tylko widget countdown utwardzania (bez re-renderu detalu)."""
        try:
            o = self._current_order()
            if o and int(o.get("ramka_step") or 0) >= 4:
                remaining = _cure_remaining_seconds(o)
                color = _cure_color(o)
                new_text = (
                    f"⏳ Utwardzanie: {_format_countdown(remaining)}"
                    if remaining > 0 else
                    "✅ Utwardzone - gotowe do zlozenia"
                )
                for widget, role in self._countdown_widgets:
                    try:
                        if role == "label":
                            widget.configure(text=new_text, bg=color)
                        elif role == "bg":
                            widget.configure(bg=color)
                        elif role == "info":
                            widget.configure(bg=color)
                    except tk.TclError:
                        pass
                if self._countdown_progressbar is not None:
                    try:
                        self._countdown_progressbar.configure(
                            value=round(_cure_progress_fraction(o) * 100)
                        )
                    except tk.TclError:
                        pass
                # Jezeli wlasnie minela granica 24h - odswiezamy liste (kolor alertu)
                if remaining == 0 and self._countdown_progressbar is not None:
                    # Osignieto 0 - re-render caly detal, zeby pokazac ze ramka gotowa
                    self._render_detail()
                    self._refresh_list_keep_selection()
        finally:
            try:
                self.after(1000, self._tick_countdown)
            except tk.TclError:
                pass

    def _tick_full_refresh(self) -> None:
        """Co 60s odswieza tagi w liscie (overdue/cure_urgent) i sync status."""
        try:
            self._refresh_list_keep_selection()
            # Full refresh listy (bez nowego selekcji) co 5 min - zeby overdue/cure_urgent
            # sie przeliczyly poprawnie
            self._update_sync_status_label()
        finally:
            try:
                self.after(60_000, self._tick_full_refresh)
            except tk.TclError:
                pass

    # ----------------- Rentownosc -----------------
    def _build_profitability_section(self, o: dict) -> None:
        sec = self._section_header("Rentownosc (wszystko PLN brutto)")
        summary = _profit_summary(o)

        # Podsumowanie na gorze
        head = ttk.Frame(sec)
        head.pack(fill="x", padx=8, pady=(6, 4))
        if summary["sprzedaz"] > 0:
            marza_color = "#2e7d32" if summary["marza"] >= 0 else "#c62828"
            ttk.Label(
                head,
                text=f"Sprzedaz: {summary['sprzedaz']:.2f} zl  |  "
                     f"Koszty: {summary['koszty']:.2f} zl",
                foreground="#555",
            ).pack(side="left")
            tk.Label(
                head,
                text=f"  Marza: {summary['marza']:+.2f} zl ({summary['marza_pct']:+.1f}%)  ",
                fg="white", bg=marza_color,
                font=("Segoe UI", 10, "bold"),
                padx=6, pady=2,
            ).pack(side="right")
        else:
            ttk.Label(
                head,
                text="(wpisz cene sprzedazy i koszty zeby zobaczyc marze)",
                foreground="#888", font=("Segoe UI", 9, "italic"),
            ).pack(side="left")

        # Pola do edycji
        grid = ttk.Frame(sec)
        grid.pack(fill="x", padx=8, pady=(4, 8))
        for c in range(4):
            grid.columnconfigure(c, weight=1 if c in (1, 3) else 0)

        def _add_money_field(row: int, col_start: int, label: str, key: str) -> None:
            ttk.Label(grid, text=label + ":").grid(
                row=row, column=col_start, sticky="w", pady=2
            )
            var = tk.StringVar(value=f"{float(o.get(key) or 0):.2f}")
            ent = ttk.Entry(grid, textvariable=var, width=12, justify="right")
            ent.grid(row=row, column=col_start + 1, sticky="w", padx=(4, 12), pady=2)

            def _on_change(*_a, k=key, v=var) -> None:
                try:
                    val = float((v.get() or "0").replace(",", "."))
                except ValueError:
                    val = 0.0
                self._set_field(k, val)
                # Po zmianie - przelicz podsumowanie
                order = self._current_order()
                if order:
                    summary2 = _profit_summary(order)
                    # Uzywamy render_detail zeby przebudowac sekcje (tani koszt)
                    # ale tylko jesli uzytkownik juz nie jest w polu - zeby nie tracic focusu.
                    # Wiec tylko aktualizujemy status w liscie.
                    self._refresh_list_keep_selection()

            var.trace_add("write", _on_change)

        _add_money_field(0, 0, "Cena sprzedazy", "cena_sprzedazy")
        _add_money_field(0, 2, "Koszt plotna",    "koszt_plotno")
        _add_money_field(1, 0, "Koszt wydruku",   "koszt_wydruku")
        _add_money_field(1, 2, "Koszt drewna",    "koszt_drewna")
        _add_money_field(2, 0, "Koszt farby",     "koszt_farby")
        _add_money_field(2, 2, "Koszt wysylki",   "koszt_wysylki")
        _add_money_field(3, 0, "Inne koszty",     "koszt_inne")

        ttk.Label(
            sec,
            text="Uwaga: zmiana pola nie odswieza powyzszego banera automatycznie.\n"
                 "Kliknij inne zamowienie i wroc, albo zaznacz inne + ponownie to, aby przeliczyc.",
            foreground="#888", font=("Segoe UI", 8, "italic"),
        ).pack(anchor="w", padx=8, pady=(0, 4))

    # ----------------- Wysylka -----------------
    def _open_shipping_dialog(self) -> None:
        o = self._current_order()
        if not o:
            return
        try:
            from . import shipping
        except ImportError as e:
            messagebox.showerror("Produkcja", f"Brak modulu shipping: {e}")
            return
        url, carrier_name = shipping.pick_carrier_url(o)
        clipboard_data = shipping.format_clipboard_data(o)

        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title(f"Przygotuj przesylke - {carrier_name}")
        dlg.geometry("640x560")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(
            dlg,
            text=f"Przesylka: {carrier_name}",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(
            dlg,
            text=(
                f"Krok 1: Kliknij 'Kopiuj dane do schowka' - wszystkie dane\n"
                f"odbiorcy + wymiary paczki sa ponizej do skopiowania.\n"
                f"Krok 2: Kliknij 'Otworz {carrier_name}' - otworzy sie strona.\n"
                f"Krok 3: Wklej dane (Ctrl+V) w formularzu kuriera,\n"
                f"dobierz kuriera, zaplac i wygeneruj etykiete PDF.\n"
                f"Krok 4: Wklej nr trackingu w polu 'Nr trackingu' w Produkcji."
            ),
            foreground="#555", justify="left",
        ).pack(anchor="w", padx=12)

        text_frame = ttk.Frame(dlg)
        text_frame.pack(fill="both", expand=True, padx=12, pady=8)
        text = scrolledtext.ScrolledText(text_frame, wrap="word", font=("Consolas", 9), height=16)
        text.pack(fill="both", expand=True)
        text.insert("1.0", clipboard_data)

        def _copy_to_clipboard() -> None:
            current = text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(current)
            self.update()
            show_toast(self.winfo_toplevel(), "Skopiowano do schowka")

        def _open_carrier() -> None:
            import webbrowser
            try:
                webbrowser.open(url)
            except OSError as exc:
                messagebox.showerror("Produkcja", f"Nie mozna otworzyc:\n{exc}", parent=dlg)

        btns = ttk.Frame(dlg)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="Zamknij", command=dlg.destroy).pack(side="right")
        ttk.Button(btns, text=f"Otworz {carrier_name}", command=_open_carrier).pack(
            side="right", padx=(0, 6)
        )
        ttk.Button(btns, text="Kopiuj dane do schowka",
                   command=_copy_to_clipboard).pack(side="right", padx=(0, 6))

        dlg.bind("<Escape>", lambda _e: dlg.destroy())

    # ----------------- Retention -----------------
    def _run_archive_dialog(self) -> None:
        months = simpledialog.askinteger(
            "Archiwizacja",
            "Zarchiwizowac zrealizowane zamowienia starsze niz (miesiace):",
            initialvalue=6, minvalue=1, maxvalue=60,
            parent=self.winfo_toplevel(),
        )
        if months is None:
            return
        try:
            from . import retention
            result = retention.archive_old_orders(months=months, logger=lambda m: None)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Archiwizacja", f"Blad:\n{exc}", parent=self.winfo_toplevel())
            return
        self.db = _load_db()
        self._refresh_list()
        messagebox.showinfo(
            "Archiwizacja",
            f"Zarchiwizowano: {result['archived']} zamowien\n"
            f"Pozostalo aktywnych/zrealizowanych: {result['kept']}\n"
            f"Bledne daty: {result['errors']}\n\n"
            f"Archiwa sa w Komponenty/produkcja/dane/archive_YYYY.json.",
            parent=self.winfo_toplevel(),
        )

    # ----------------- Misc -----------------
    def _open_data_folder(self) -> None:
        try:
            import os as _os
            import subprocess as _sp
            import sys as _sys

            if _sys.platform.startswith("win"):
                _os.startfile(str(_DATA_DIR))  # noqa: S606
            elif _sys.platform == "darwin":
                _sp.Popen(["open", str(_DATA_DIR)])  # noqa: S607
            else:
                _sp.Popen(["xdg-open", str(_DATA_DIR)])  # noqa: S607
        except OSError as e:
            messagebox.showerror("Produkcja", f"Nie udalo sie otworzyc folderu:\n{e}")

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
            show_help(self.winfo_toplevel(), title="Instrukcja - Produkcja", text=_PRODUKCJA_HELP)
        except ImportError:
            messagebox.showinfo("Instrukcja - Produkcja", _PRODUKCJA_HELP)


# ============================================================================


_PRODUKCJA_HELP = """# Produkcja - zamowienia i status

## Przeplyw pracy
1. Zamowienie wpada (recznie **+ Nowe zamowienie** albo automatycznie z Shopify).
2. Trzy sekcje do odhaczenia:
   - **Wydruk**: Przyjete -> Po korekcji -> Wydrukowany.
   - **Ramka**: Drewno -> Wyciecie -> Szlif -> Malowanie.
     Po zaznaczeniu 'Pomalowana' rusza **72-godzinny licznik utwardzania**
     (live countdown w formacie `2d 05g 43m 12s`).
   - **Finalizacja**: Zlozone -> Spakowane -> Wyslane.
3. Wysylka: przycisk **Wyslij...** otwiera dialog z adresem; potwierdzenie
   zapisuje date wysylki.

## Integracja z Shopify
- Aplikacja **auto-synchronizuje** zamowienia z Shopify co 5 minut (polling).
- Kazdy zaplacony order -> tworzony jest rekord produkcji (dedup po
  `shopify_order_id + shopify_line_item_id`).
- Wymaga scope `read_orders` w `shopify.app.toml` + ponowny OAuth
  (`npm run deploy -- --allow-updates && npm run oauth` w `cursor-api/`).
- Przycisk **↓ Pobierz z Shopify** wymusza natychmiastowa synchronizacje.

## Live countdown utwardzania
- Kolor tla: czerwony (<24h), pomaranczowy (24-48h), zielony (>48h).
- Pasek postepu pokazuje % uplynietego czasu utwardzania.
- Label co 1s aktualizuje sekundy - bez zacinek reszty UI
  (odswiezamy tylko ten jeden widget).

## Lista zamowien
- **Filtry**: Aktywne / Wszystkie / Zrealizowane / Opoznione (>14 dni).
- **Szukaj**: po kliencie / tytule / numerze Shopify / notatce.
- **Sortowanie**: klik w naglowek kolumny.
- **Postep**: kolumna `■■■□□` pokazuje ile z 5 glownych krokow jest gotowe.
- **Overdue** - czerwone tlo wiersza (zamowienie starsze niz 14 dni a nie
  wyslane).
- **Cure urgent** - rozowe tlo wiersza (utwardzanie zostalo <24h).

## Eksport CSV
Przycisk **⬇ Eksport CSV** zapisuje biezaca liste (po filtrach) do pliku CSV
z separatorem `;` i BOM UTF-8 (otwiera sie poprawnie w Excelu).

## Dane
- Wszystkie zamowienia: `Komponenty/produkcja/dane/zamowienia.json`.
- Stan sync Shopify: `Komponenty/produkcja/dane/sync_state.json`.
- Mozesz backupowac/wersjonowac te pliki w git.
"""


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    view = ProdukcjaView(parent, on_back)
    return view
