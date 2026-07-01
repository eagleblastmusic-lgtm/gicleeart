"""Inline-view komponentu 'Planer'.

Funkcjonalnosci:
- dwa widoki: DZIEN (szczegolowa lista zadan) lub TYDZIEN (7 kolumn Pn-Nd),
- wybor daty (Entry + przyciski poprzedni/nastepny/dzisiaj),
- dodawanie/usuwanie zadan, odhaczanie, priorytety, kolory tla,
- reorder przyciskami up/down lub sortowanie (recznie / priorytet / alfabet),
- **przenoszenie zadania na inny dzien** (jutro / pojutrze / pojutrze+7 / wybierz),
- **"Przenies niedokonczone na jutro"** - jednym przyciskiem,
- filtry: search tekstowy, ukryj zrobione, filter priorytetu,
- klikalne linki w tekscie zadania (ikonka 🔗 obok jesli tekst zawiera URL),
- Ctrl+Enter = szybkie dodanie, Ctrl+Shift+Enter = dodanie z priorytetem 'high'.

Persystencja: jeden plik JSON na date w `Komponenty/planer/dane/YYYY-MM-DD.json`.
"""

from __future__ import annotations

import json
import re
import tkinter as tk
import uuid
import webbrowser
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import colorchooser, messagebox, simpledialog, ttk

try:
    from Komponenty._shared.toast import show_toast
except ImportError:  # pragma: no cover
    def show_toast(parent: tk.Misc, text: str, **_kw) -> None:  # type: ignore[override]
        print(f"[toast] {text}")


_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "dane"

# Priorytety: (key, symbol, color_text, label).
_PRIORITIES = [
    ("none", "—", "#9e9e9e", "brak"),
    ("low", "↓", "#1976d2", "niski"),
    ("normal", "•", "#43a047", "normalny"),
    ("high", "↑", "#fb8c00", "wysoki"),
    ("critical", "‼", "#e53935", "krytyczny"),
]
_PRI_BY_KEY = {p[0]: p for p in _PRIORITIES}
_PRI_NEXT = {
    p[0]: _PRIORITIES[(i + 1) % len(_PRIORITIES)][0]
    for i, p in enumerate(_PRIORITIES)
}
_PRI_RANK = {p[0]: i for i, p in enumerate(_PRIORITIES)}

_PALETTE = [
    ("", "brak"),
    ("#fff9c4", "zolty"),
    ("#c8e6c9", "zielony"),
    ("#bbdefb", "niebieski"),
    ("#ffcdd2", "czerwony"),
    ("#e1bee7", "fioletowy"),
    ("#ffe0b2", "pomaranczowy"),
]

_DAY_NAMES_PL = [
    "poniedzialek", "wtorek", "sroda", "czwartek",
    "piatek", "sobota", "niedziela",
]
_DAY_ABBR_PL = ["Pn", "Wt", "Sr", "Cz", "Pt", "Sb", "Nd"]

_URL_RE = re.compile(r"https?://\S+")


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _file_for_date(d: date) -> Path:
    return _DATA_DIR / f"{d.isoformat()}.json"


def _load_tasks(d: date) -> list[dict]:
    p = _file_for_date(d)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return []
    tasks = data.get("tasks") or []
    cleaned: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        cleaned.append(
            {
                "id": str(t.get("id") or uuid.uuid4().hex[:10]),
                "text": str(t.get("text") or ""),
                "done": bool(t.get("done")),
                "priority": str(t.get("priority") or "none"),
                "color": str(t.get("color") or ""),
            }
        )
    return cleaned


def _save_tasks(d: date, tasks: list[dict]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = _file_for_date(d)
    payload = {
        "date": d.isoformat(),
        "tasks": tasks,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        p.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as e:
        messagebox.showerror("Planer", f"Nie udalo sie zapisac:\n{e}")


def _first_url(text: str) -> str | None:
    m = _URL_RE.search(text or "")
    return m.group(0) if m else None


def _week_dates(reference: date) -> list[date]:
    """Zwraca liste 7 dat pon-nd dla tygodnia zawierajacego `reference`."""
    monday = reference - timedelta(days=reference.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


class PlanerView(ttk.Frame):
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        super().__init__(parent)
        self.on_back = on_back
        self.current_date: date = date.today()
        self.tasks: list[dict] = []
        self._text_vars: dict[str, tk.StringVar] = {}
        self._row_widgets: dict[str, dict] = {}

        # Widok: "day" | "week"
        self.view_mode: tk.StringVar = tk.StringVar(value="day")

        # Filtry / sortowanie
        self.filter_text: tk.StringVar = tk.StringVar(value="")
        self.hide_done: tk.BooleanVar = tk.BooleanVar(value=False)
        self.priority_filter: tk.StringVar = tk.StringVar(value="(wszystkie)")
        self.sort_mode: tk.StringVar = tk.StringVar(value="Recznie")

        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._build()
        self._load_for_date()

    # ======================================================================
    # UI
    # ======================================================================
    def _build(self) -> None:
        # ---- Toolbar ----
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(8, 4))
        ttk.Button(toolbar, text="← Wroc", command=self.on_back).pack(side="left")
        ttk.Label(
            toolbar, text="Planer", font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=(10, 0))

        # Toggle widoku (Dzien / Tydzien)
        view_box = ttk.Frame(toolbar)
        view_box.pack(side="left", padx=(18, 0))
        ttk.Radiobutton(
            view_box, text="Dzien", variable=self.view_mode, value="day",
            command=self._on_view_mode_changed,
        ).pack(side="left")
        ttk.Radiobutton(
            view_box, text="Tydzien", variable=self.view_mode, value="week",
            command=self._on_view_mode_changed,
        ).pack(side="left", padx=(6, 0))

        ttk.Button(toolbar, text="Instrukcja", command=self._show_help).pack(side="right")
        ttk.Button(
            toolbar, text="Otworz folder danych", command=self._open_data_folder
        ).pack(side="right", padx=6)
        ttk.Button(
            toolbar, text="→ Niedokonczone na jutro",
            command=self._move_undone_to_tomorrow,
        ).pack(side="right", padx=6)

        # ---- Date bar ----
        date_bar = ttk.Frame(self)
        date_bar.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Button(date_bar, text="◀", width=3, command=lambda: self._shift_date(-1)).pack(
            side="left"
        )
        self.date_var = tk.StringVar(value=self.current_date.isoformat())
        date_entry = ttk.Entry(
            date_bar,
            textvariable=self.date_var,
            width=14,
            justify="center",
            font=("Segoe UI", 11),
        )
        date_entry.pack(side="left", padx=4)
        date_entry.bind("<Return>", lambda _e: self._on_date_entered())
        date_entry.bind("<FocusOut>", lambda _e: self._on_date_entered())
        ttk.Button(date_bar, text="▶", width=3, command=lambda: self._shift_date(1)).pack(
            side="left"
        )
        ttk.Button(date_bar, text="Dzis", command=self._goto_today).pack(
            side="left", padx=(8, 0)
        )
        self.day_label = ttk.Label(date_bar, text="", foreground="#666")
        self.day_label.pack(side="left", padx=(12, 0))

        self.summary_var = tk.StringVar(value="")
        ttk.Label(
            date_bar, textvariable=self.summary_var, foreground="#444"
        ).pack(side="right")

        # ---- Pasek filtrow (tylko w widoku dnia) ----
        self.filter_bar = ttk.Frame(self)
        self.filter_bar.pack(fill="x", padx=10, pady=(0, 4))
        ttk.Label(self.filter_bar, text="Szukaj:").pack(side="left")
        ft_entry = ttk.Entry(self.filter_bar, textvariable=self.filter_text, width=26)
        ft_entry.pack(side="left", padx=(4, 10))
        self.filter_text.trace_add("write", lambda *_: self._render_tasks())

        ttk.Checkbutton(
            self.filter_bar, text="Ukryj zrobione",
            variable=self.hide_done, command=self._render_tasks,
        ).pack(side="left", padx=(0, 10))

        ttk.Label(self.filter_bar, text="Priorytet:").pack(side="left")
        pri_values = ["(wszystkie)"] + [p[0] for p in _PRIORITIES]
        ttk.Combobox(
            self.filter_bar, textvariable=self.priority_filter,
            values=pri_values, state="readonly", width=11,
        ).pack(side="left", padx=(4, 10))
        self.priority_filter.trace_add("write", lambda *_: self._render_tasks())

        ttk.Label(self.filter_bar, text="Sortowanie:").pack(side="left")
        ttk.Combobox(
            self.filter_bar, textvariable=self.sort_mode,
            values=["Recznie", "Priorytet", "Alfabet", "Nierobione->Zrobione"],
            state="readonly", width=22,
        ).pack(side="left", padx=(4, 0))
        self.sort_mode.trace_add("write", lambda *_: self._render_tasks())

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=10)

        # ---- Body (kontener dla widoku dnia lub tygodnia) ----
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True, padx=10, pady=(4, 4))

        # Day view: scroll lista
        self._build_day_body()
        self._build_week_body()

        # Bottom bar (dodawanie)
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(4, 10))
        self.new_text_var = tk.StringVar()
        new_entry = ttk.Entry(
            bottom, textvariable=self.new_text_var, font=("Segoe UI", 11)
        )
        new_entry.pack(side="left", fill="x", expand=True)
        new_entry.bind("<Return>", lambda _e: self._add_from_entry())
        new_entry.bind("<Shift-Return>", lambda _e: self._add_from_entry(priority="high"))
        ttk.Button(
            bottom, text="+ Dodaj zadanie", command=self._add_from_entry,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            bottom, text="+ Pilne (Shift+Enter)",
            command=lambda: self._add_from_entry(priority="high"),
        ).pack(side="left", padx=(6, 0))

    def _build_day_body(self) -> None:
        self.day_frame = ttk.Frame(self.body)
        self.day_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(self.day_frame, borderwidth=0, highlightthickness=0)
        sb = ttk.Scrollbar(self.day_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.task_holder = ttk.Frame(canvas)
        self._task_window = canvas.create_window(
            (0, 0), window=self.task_holder, anchor="nw"
        )
        self._canvas = canvas

        def _on_inner(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas(e: tk.Event) -> None:
            canvas.itemconfigure(self._task_window, width=e.width)

        self.task_holder.bind("<Configure>", _on_inner)
        canvas.bind("<Configure>", _on_canvas)

        from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas

        bind_mousewheel_to_canvas(canvas, self.task_holder)

    def _build_week_body(self) -> None:
        self.week_frame = ttk.Frame(self.body)
        # NIE pakujemy domyslnie - pokazujemy tylko gdy view_mode == "week"

        # 7 kolumn: po jednej na dzien
        self._week_columns: list[ttk.Frame] = []
        for i in range(7):
            col = ttk.Frame(self.week_frame, relief="solid", borderwidth=1)
            col.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)
            self.week_frame.columnconfigure(i, weight=1)
            self._week_columns.append(col)
        self.week_frame.rowconfigure(0, weight=1)

    def _on_view_mode_changed(self) -> None:
        if self.view_mode.get() == "week":
            self.day_frame.pack_forget()
            self.filter_bar.pack_forget()
            self.week_frame.pack(fill="both", expand=True)
            self._render_week()
        else:
            self.week_frame.pack_forget()
            # Filter bar + day frame pakujemy ponownie (pack respektuje kolejnosc wywolan
            # - a filter_bar byl spakowany przed body w _build, wiec pojdzie pod toolbar).
            self.filter_bar.pack(fill="x", padx=10, pady=(0, 4),
                                 before=self.body)
            self.day_frame.pack(fill="both", expand=True)
            self._render_tasks()

    # ======================================================================
    # Nawigacja daty
    # ======================================================================
    def _shift_date(self, days: int) -> None:
        self.current_date = self.current_date + timedelta(days=days)
        self.date_var.set(self.current_date.isoformat())
        self._load_for_date()

    def _goto_today(self) -> None:
        self.current_date = date.today()
        self.date_var.set(self.current_date.isoformat())
        self._load_for_date()

    def _on_date_entered(self) -> None:
        d = _parse_date(self.date_var.get())
        if d is None:
            messagebox.showwarning(
                "Planer",
                "Nie rozpoznaje daty. Uzyj formatu YYYY-MM-DD.",
            )
            self.date_var.set(self.current_date.isoformat())
            return
        if d == self.current_date:
            return
        self.current_date = d
        self.date_var.set(d.isoformat())
        self._load_for_date()

    # ======================================================================
    # Data
    # ======================================================================
    def _load_for_date(self) -> None:
        self.tasks = _load_tasks(self.current_date)
        weekday = _DAY_NAMES_PL[self.current_date.weekday()]
        delta = (self.current_date - date.today()).days
        if delta == 0:
            rel = "dzis"
        elif delta == 1:
            rel = "jutro"
        elif delta == -1:
            rel = "wczoraj"
        elif delta > 0:
            rel = f"za {delta} dni"
        else:
            rel = f"{-delta} dni temu"
        self.day_label.configure(text=f"{weekday} ({rel})")
        if self.view_mode.get() == "week":
            self._render_week()
        else:
            self._render_tasks()

    def _persist(self) -> None:
        _save_tasks(self.current_date, self.tasks)
        self._update_summary()

    def _update_summary(self) -> None:
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.get("done"))
        high = sum(1 for t in self.tasks if t.get("priority") in ("high", "critical"))
        if total == 0:
            self.summary_var.set("0 zadan")
        else:
            self.summary_var.set(f"{done}/{total} zrobione   |   {high} pilne")

    # ======================================================================
    # Filtrowanie + sortowanie (widok dnia)
    # ======================================================================
    def _filtered_sorted_tasks(self) -> list[tuple[int, dict]]:
        """Zwraca (original_index, task) dla zadan zgodnych z filtrami."""
        ft = (self.filter_text.get() or "").lower().strip()
        pri_f = self.priority_filter.get()
        hide_done = self.hide_done.get()

        items = list(enumerate(self.tasks))
        if ft:
            items = [(i, t) for i, t in items if ft in (t.get("text", "") or "").lower()]
        if pri_f != "(wszystkie)":
            items = [(i, t) for i, t in items if t.get("priority") == pri_f]
        if hide_done:
            items = [(i, t) for i, t in items if not t.get("done")]

        mode = self.sort_mode.get()
        if mode == "Priorytet":
            items.sort(key=lambda it: -_PRI_RANK.get(it[1].get("priority", "none"), 0))
        elif mode == "Alfabet":
            items.sort(key=lambda it: (it[1].get("text") or "").lower())
        elif mode == "Nierobione->Zrobione":
            items.sort(key=lambda it: (1 if it[1].get("done") else 0))
        return items

    # ======================================================================
    # Add / remove
    # ======================================================================
    def _add_from_entry(self, *, priority: str = "normal") -> None:
        txt = (self.new_text_var.get() or "").strip()
        if not txt:
            return
        self.tasks.append(
            {
                "id": uuid.uuid4().hex[:10],
                "text": txt,
                "done": False,
                "priority": priority,
                "color": "",
            }
        )
        self.new_text_var.set("")
        self._persist()
        if self.view_mode.get() == "week":
            self._render_week()
        else:
            self._render_tasks()

    def _delete_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._text_vars.pop(task_id, None)
        self._persist()
        self._render_tasks()

    def _move(self, task_id: str, direction: int) -> None:
        idx = next((i for i, t in enumerate(self.tasks) if t["id"] == task_id), -1)
        if idx == -1:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.tasks):
            return
        self.tasks[idx], self.tasks[new_idx] = self.tasks[new_idx], self.tasks[idx]
        self._persist()
        self._render_tasks()

    # ======================================================================
    # Field updates
    # ======================================================================
    def _toggle_done(self, task_id: str, var: tk.IntVar) -> None:
        for t in self.tasks:
            if t["id"] == task_id:
                t["done"] = bool(var.get())
                break
        self._persist()
        self._refresh_row_appearance(task_id)

    def _cycle_priority(self, task_id: str, btn: tk.Button) -> None:
        for t in self.tasks:
            if t["id"] == task_id:
                t["priority"] = _PRI_NEXT.get(t.get("priority", "none"), "none")
                _, sym, col, lbl = _PRI_BY_KEY[t["priority"]]
                btn.configure(text=sym, fg=col)
                self._tooltip(btn, f"Priorytet: {lbl}")
                break
        self._persist()

    def _pick_color(self, task_id: str, swatch: tk.Label) -> None:
        menu = tk.Menu(self, tearoff=0)
        for color, name in _PALETTE:
            menu.add_command(
                label=name,
                background=color or "",
                command=lambda c=color: self._set_color(task_id, swatch, c),
            )
        menu.add_separator()
        menu.add_command(
            label="Wlasny kolor...",
            command=lambda: self._set_color_custom(task_id, swatch),
        )
        try:
            menu.tk_popup(swatch.winfo_rootx(), swatch.winfo_rooty() + 24)
        finally:
            menu.grab_release()

    def _set_color_custom(self, task_id: str, swatch: tk.Label) -> None:
        color = colorchooser.askcolor(title="Wybierz kolor zadania")
        if not color or not color[1]:
            return
        self._set_color(task_id, swatch, color[1])

    def _set_color(self, task_id: str, swatch: tk.Label, color: str) -> None:
        for t in self.tasks:
            if t["id"] == task_id:
                t["color"] = color
                break
        bg = color or "#ffffff"
        try:
            swatch.configure(bg=bg)
        except tk.TclError:
            pass
        self._persist()
        self._refresh_row_appearance(task_id)

    def _on_text_changed(self, task_id: str) -> None:
        var = self._text_vars.get(task_id)
        if var is None:
            return
        new_val = var.get()
        for t in self.tasks:
            if t["id"] == task_id and t.get("text") != new_val:
                t["text"] = new_val
                self._persist()
                # Moglo sie pojawic / zniknac URL - odswiezamy caly wiersz
                self._render_tasks()
                break

    # ======================================================================
    # Przenoszenie na inna date
    # ======================================================================
    def _move_to_date(self, task_id: str, target: date) -> None:
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if task is None:
            return
        if target == self.current_date:
            return
        # Zapisz target
        target_tasks = _load_tasks(target)
        target_tasks.append(task)
        _save_tasks(target, target_tasks)
        # Usun z biezacej
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._persist()
        self._render_tasks()
        show_toast(
            self.winfo_toplevel(),
            f"Przeniesiono na {target.isoformat()}",
            duration_ms=1400,
        )

    def _open_move_menu(self, task_id: str, anchor: tk.Widget) -> None:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        next_week = today + timedelta(days=7)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=f"Jutro ({tomorrow.isoformat()})",
            command=lambda: self._move_to_date(task_id, tomorrow),
        )
        menu.add_command(
            label=f"Pojutrze ({day_after.isoformat()})",
            command=lambda: self._move_to_date(task_id, day_after),
        )
        menu.add_command(
            label=f"Za tydzien ({next_week.isoformat()})",
            command=lambda: self._move_to_date(task_id, next_week),
        )
        menu.add_separator()
        menu.add_command(
            label="Wybierz date...",
            command=lambda: self._move_to_chosen_date(task_id),
        )
        try:
            menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + 24)
        finally:
            menu.grab_release()

    def _move_to_chosen_date(self, task_id: str) -> None:
        s = simpledialog.askstring(
            "Przenies zadanie",
            "Data docelowa (YYYY-MM-DD):",
            initialvalue=(self.current_date + timedelta(days=1)).isoformat(),
            parent=self.winfo_toplevel(),
        )
        if not s:
            return
        d = _parse_date(s)
        if d is None:
            messagebox.showwarning("Planer", "Nie rozpoznaje daty.")
            return
        self._move_to_date(task_id, d)

    def _move_undone_to_tomorrow(self) -> None:
        undone = [t for t in self.tasks if not t.get("done")]
        if not undone:
            messagebox.showinfo("Planer", "Brak niedokonczonych zadan na ten dzien.")
            return
        tomorrow = self.current_date + timedelta(days=1)
        if not messagebox.askyesno(
            "Planer",
            f"Przeniesc {len(undone)} niedokonczone zadanie(a) na {tomorrow.isoformat()}?",
            parent=self.winfo_toplevel(),
        ):
            return
        target_tasks = _load_tasks(tomorrow)
        target_tasks.extend(undone)
        _save_tasks(tomorrow, target_tasks)
        self.tasks = [t for t in self.tasks if t.get("done")]
        self._persist()
        self._render_tasks()
        show_toast(
            self.winfo_toplevel(),
            f"Przeniesiono {len(undone)} na {tomorrow.isoformat()}",
        )

    # ======================================================================
    # Rendering - widok dnia
    # ======================================================================
    def _render_tasks(self) -> None:
        for child in self.task_holder.winfo_children():
            child.destroy()
        self._text_vars.clear()
        self._row_widgets = {}

        filtered = self._filtered_sorted_tasks()
        if not filtered:
            msg = (
                "(brak zadan na ten dzien - wpisz tytul ponizej i Enter)"
                if not self.tasks else
                "(brak zadan pasujacych do filtra)"
            )
            empty = ttk.Label(
                self.task_holder, text=msg,
                foreground="#888", padding=(12, 18),
            )
            empty.pack(anchor="w")
            self._update_summary()
            return

        for idx, (orig_idx, t) in enumerate(filtered):
            self._render_row(orig_idx, t, is_first=idx == 0, is_last=idx == len(filtered) - 1)
        self._update_summary()

    def _render_row(self, idx: int, task: dict, *, is_first: bool, is_last: bool) -> None:
        tid = task["id"]
        bg = task.get("color") or ""
        row = tk.Frame(
            self.task_holder,
            bg=bg or self.task_holder.tk.eval("ttk::style lookup TFrame -background"),
            bd=1, relief="solid", highlightthickness=0,
        )
        row.pack(fill="x", pady=2, padx=2)

        # 1) Checkbox done
        done_var = tk.IntVar(value=1 if task.get("done") else 0)
        cb = tk.Checkbutton(
            row, variable=done_var,
            command=lambda: self._toggle_done(tid, done_var),
        )
        if bg:
            cb.configure(bg=bg, activebackground=bg)
        cb.pack(side="left", padx=(6, 4), pady=4)

        # 2) Priorytet
        pri = task.get("priority", "none")
        _, sym, col, lbl = _PRI_BY_KEY.get(pri, _PRI_BY_KEY["none"])
        pri_btn = tk.Button(
            row, text=sym, fg=col,
            font=("Segoe UI", 12, "bold"), width=2,
            relief="flat", cursor="hand2", takefocus=False,
        )
        if bg:
            pri_btn.configure(bg=bg, activebackground=bg)
        pri_btn.configure(command=lambda b=pri_btn: self._cycle_priority(tid, b))
        self._tooltip(pri_btn, f"Priorytet: {lbl}")
        pri_btn.pack(side="left", padx=2)

        # 3) Swatch koloru
        swatch_bg = bg or "#ffffff"
        swatch = tk.Label(
            row, text=" ", bg=swatch_bg, width=2,
            cursor="hand2", relief="solid", borderwidth=1,
        )
        swatch.bind("<Button-1>", lambda _e, s=swatch: self._pick_color(tid, s))
        self._tooltip(swatch, "Kolor")
        swatch.pack(side="left", padx=4, pady=4)

        # 4) Tekst
        txt_var = tk.StringVar(value=task.get("text", ""))
        self._text_vars[tid] = txt_var

        font_args: dict = {"font": ("Segoe UI", 11)}
        if task.get("done"):
            font_args["font"] = ("Segoe UI", 11, "overstrike")
        entry = tk.Entry(
            row, textvariable=txt_var, relief="flat",
            bg=swatch_bg,
            fg="#666" if task.get("done") else "#111",
            insertbackground="#111", highlightthickness=0,
            **font_args,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(4, 4), pady=4, ipady=3)
        entry.bind("<FocusOut>", lambda _e, k=tid: self._on_text_changed(k))
        entry.bind("<Return>", lambda _e, k=tid: self._on_text_changed(k))

        # 5) Link (jesli tekst zawiera URL)
        url = _first_url(task.get("text", ""))
        if url:
            link_btn = tk.Button(
                row, text="🔗", width=2, relief="flat", takefocus=False,
                cursor="hand2", fg="#1a73e8",
                command=lambda u=url: webbrowser.open(u),
            )
            if bg:
                link_btn.configure(bg=bg, activebackground=bg)
            self._tooltip(link_btn, f"Otworz: {url[:60]}")
            link_btn.pack(side="right", padx=1, pady=4)

        # 6) Przyciski akcji
        del_btn = tk.Button(
            row, text="✕", width=2, relief="flat", takefocus=False,
            fg="#b00020", command=lambda: self._confirm_delete(tid),
        )
        move_btn = tk.Button(
            row, text="→", width=2, relief="flat", takefocus=False,
            cursor="hand2",
            command=lambda b=None: None,  # placeholder - podmienimy ponizej
        )
        move_btn.configure(command=lambda b=move_btn: self._open_move_menu(tid, b))
        self._tooltip(move_btn, "Przenies na inny dzien")

        down_btn = tk.Button(
            row, text="▼", width=2, relief="flat", takefocus=False,
            command=lambda: self._move(tid, +1),
        )
        up_btn = tk.Button(
            row, text="▲", width=2, relief="flat", takefocus=False,
            command=lambda: self._move(tid, -1),
        )
        for b in (del_btn, move_btn, down_btn, up_btn):
            if bg:
                b.configure(bg=bg, activebackground=bg)
            b.pack(side="right", padx=1, pady=4)

        # up/down blokujemy tylko dla trybu recznego sortowania
        if self.sort_mode.get() != "Recznie":
            for b in (up_btn, down_btn):
                b.configure(state="disabled")
        else:
            if is_first:
                up_btn.configure(state="disabled")
            if is_last:
                down_btn.configure(state="disabled")

        self._row_widgets[tid] = {
            "row": row, "entry": entry, "cb": cb, "swatch": swatch,
            "pri_btn": pri_btn,
            "buttons": (up_btn, down_btn, del_btn, move_btn),
        }

    def _refresh_row_appearance(self, task_id: str) -> None:
        info = self._row_widgets.get(task_id)
        if not info:
            return
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if task is None:
            return
        bg = task.get("color") or "#ffffff"
        is_done = bool(task.get("done"))
        info["row"].configure(bg=bg)
        for w in (info["cb"], info["swatch"], info["pri_btn"], *info["buttons"]):
            try:
                w.configure(bg=bg, activebackground=bg)
            except tk.TclError:
                pass
        try:
            info["entry"].configure(
                bg=bg,
                fg="#666" if is_done else "#111",
                font=("Segoe UI", 11, "overstrike") if is_done else ("Segoe UI", 11),
            )
        except tk.TclError:
            pass

    def _confirm_delete(self, task_id: str) -> None:
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return
        if not messagebox.askyesno(
            "Planer",
            f"Usunac zadanie?\n\n  • {task.get('text', '')[:80]}",
            parent=self.winfo_toplevel(),
        ):
            return
        self._delete_task(task_id)

    # ======================================================================
    # Rendering - widok tygodnia
    # ======================================================================
    def _render_week(self) -> None:
        week = _week_dates(self.current_date)
        for col_frame, d in zip(self._week_columns, week):
            for child in col_frame.winfo_children():
                child.destroy()
            today = date.today()
            is_today = d == today

            header_bg = "#1976d2" if is_today else "#e8eaf6"
            header_fg = "#ffffff" if is_today else "#222"
            header = tk.Frame(col_frame, bg=header_bg)
            header.pack(fill="x")
            label_text = f"{_DAY_ABBR_PL[d.weekday()]}  {d.day:02d}.{d.month:02d}"
            tk.Label(
                header, text=label_text, bg=header_bg, fg=header_fg,
                font=("Segoe UI", 10, "bold"), padx=6, pady=4,
                cursor="hand2",
            ).pack(fill="x")
            header.bind("<Button-1>", lambda _e, dd=d: self._goto_specific_date(dd))
            for c in header.winfo_children():
                c.bind("<Button-1>", lambda _e, dd=d: self._goto_specific_date(dd))

            # Lista zadan tego dnia
            tasks_d = _load_tasks(d)
            done_count = sum(1 for t in tasks_d if t.get("done"))
            tk.Label(
                col_frame,
                text=f"{done_count}/{len(tasks_d)}" if tasks_d else "(puste)",
                fg="#666", font=("Segoe UI", 9),
            ).pack(fill="x", pady=(2, 4))

            for t in tasks_d[:20]:  # max 20 zeby nie zapchac UI
                bg = t.get("color") or ""
                text = t.get("text", "")[:40]
                pri = t.get("priority", "none")
                _, sym, col, _lbl = _PRI_BY_KEY.get(pri, _PRI_BY_KEY["none"])
                font = ("Segoe UI", 9, "overstrike") if t.get("done") else ("Segoe UI", 9)
                fg = "#888" if t.get("done") else "#111"
                row = tk.Frame(col_frame, bg=bg or "#fafafa")
                row.pack(fill="x", padx=4, pady=1)
                tk.Label(
                    row, text=sym, fg=col, bg=bg or "#fafafa",
                    font=("Segoe UI", 10, "bold"), padx=2,
                ).pack(side="left")
                tk.Label(
                    row, text=text, fg=fg, bg=bg or "#fafafa",
                    font=font, anchor="w", justify="left", wraplength=140,
                ).pack(side="left", fill="x", expand=True)
            if len(tasks_d) > 20:
                tk.Label(
                    col_frame, text=f"... i {len(tasks_d) - 20} wiecej",
                    fg="#888", font=("Segoe UI", 9, "italic"),
                ).pack(fill="x", padx=4)

    def _goto_specific_date(self, d: date) -> None:
        self.current_date = d
        self.date_var.set(d.isoformat())
        self.view_mode.set("day")
        self._on_view_mode_changed()
        self._load_for_date()

    # ======================================================================
    # Helpers
    # ======================================================================
    def _open_data_folder(self) -> None:
        try:
            import os as _os
            import subprocess as _sp
            import sys as _sys

            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            if _sys.platform.startswith("win"):
                _os.startfile(str(_DATA_DIR))  # noqa: S606
            elif _sys.platform == "darwin":
                _sp.Popen(["open", str(_DATA_DIR)])  # noqa: S607
            else:
                _sp.Popen(["xdg-open", str(_DATA_DIR)])  # noqa: S607
        except OSError as e:
            messagebox.showerror("Planer", f"Nie udalo sie otworzyc folderu:\n{e}")

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
            show_help(self.winfo_toplevel(), title="Instrukcja - Planer", text=_PLANER_HELP)
        except ImportError:
            messagebox.showinfo("Instrukcja - Planer", _PLANER_HELP)

    def _tooltip(self, widget: tk.Widget, text: str) -> None:
        tip = {"win": None}

        def _show(_e: tk.Event) -> None:
            if tip["win"] is not None:
                return
            try:
                x = widget.winfo_rootx() + 16
                y = widget.winfo_rooty() + widget.winfo_height() + 4
            except tk.TclError:
                return
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tk.Label(
                tw, text=text, bg="#ffffe0", fg="#222",
                relief="solid", borderwidth=1, padx=6, pady=2,
                font=("Segoe UI", 9),
            ).pack()
            tip["win"] = tw

        def _hide(_e: tk.Event) -> None:
            if tip["win"] is not None:
                try:
                    tip["win"].destroy()
                except tk.TclError:
                    pass
                tip["win"] = None

        widget.bind("<Enter>", _show, add="+")
        widget.bind("<Leave>", _hide, add="+")
        widget.bind("<ButtonPress>", _hide, add="+")


_PLANER_HELP = """# Planer - dzienny i tygodniowy

## Widoki
- **Dzien** - szczegolowa lista zadan z edycja, filtrami, kolorami.
- **Tydzien** - 7 kolumn (Pn-Nd), klik w naglowek kolumny przechodzi do
  widoku dnia. Sluzy do szybkiego przegladu co masz w biezacym tygodniu.

## Zadania
- **+ Dodaj zadanie** (Enter w polu) - zwykle.
- **+ Pilne** (Shift+Enter) - priorytet 'wysoki' od razu.
- **Checkbox** - oznacz zrobione (tekst przekreslony).
- **Symbol priorytetu** - klik cyklicznie: brak → niski → normal → wysoki → krytyczny.
- **Kolorowy kwadrat** - paleta kolorow (lub custom).
- **▲ / ▼** - zmiana kolejnosci (tylko w trybie 'Recznie').
- **→** - przenies zadanie na inny dzien (menu: jutro / pojutrze / za tydzien / wybierz date).
- **🔗** - jesli zadanie zawiera URL, ikonka pojawia sie po prawej i otwiera go w przegladarce.
- **✕** - usuwa zadanie.

## Filtry i sortowanie (widok dnia)
- **Szukaj** - filtruje po tekscie zadania.
- **Ukryj zrobione** - chowa zafajkowane.
- **Priorytet** - pokazuj tylko dany priorytet.
- **Sortowanie** - Recznie / Priorytet / Alfabet / Nierobione->Zrobione.

## Szybkie akcje
- **→ Niedokonczone na jutro** - masowe przeniesienie wszystkich zadan
  nieukonczonych z dzis na jutro.

## Klikalne linki
Jesli wpiszesz w zadaniu URL (np. `https://...`) - pojawi sie ikonka 🔗
po prawej, ktora otwiera go w przegladarce.

## Zapis
Wszystkie zmiany sa auto-zapisywane do pliku JSON na danej dacie
(`Komponenty/planer/dane/YYYY-MM-DD.json`).
"""


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    """Kontrakt inline-komponentu wymagany przez launcher."""
    view = PlanerView(parent, on_back)
    return view
