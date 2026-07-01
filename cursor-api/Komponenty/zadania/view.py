"""Inline-view komponentu Zadania.

Glowny ekran: lista wszystkich zadan ze statusami, filtry, akcje:
- Nowe zadanie (manualne lub z generatora LLM)
- Filtry po statusie, kanale, jezyku, priorytecie, RYNKU
- Sortowanie po dowolnej kolumnie (klik nagloka - asc, drugi klik - desc)
- PPM na zadaniu: Generuj post (otwiera socialmedia generator), Oznacz, Edytuj, Usun
- Toolbar: [Generator zadan (LLM)] [Nowy task recznie] [Odswiez] [Eksport CSV]

Wsparcie multi-channel (zadanie moze trafic na kilka platform) i multi-market
(zadanie kierowane na kilka rynkow Shopify; tlumaczenia opisu pokazane w edytorze
i tooltipie).

`on_back` wraca do launchera.
"""

from __future__ import annotations

import csv
import tkinter as tk
from collections.abc import Callable
from datetime import date, timedelta
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import storage
from .generator_zadan import open_tasks_generator

_BG = "#f4f4f7"

# Etykiety + ikony statusow
_STATUS_LABELS = {
    "pending": "⏳ Oczekuje",
    "in_progress": "▶ W toku",
    "done": "✅ Zrobione",
    "skipped": "⏭ Pominiete",
}
_STATUS_ORDER = ["pending", "in_progress", "done", "skipped"]
_STATUS_RANK = {"in_progress": 0, "pending": 1, "done": 2, "skipped": 3}

# Polskie etykiety priorytetow (z ikona)
_PRIORITY_LABELS_PL = {
    "urgent": "🔴 Pilne",
    "high":   "🟠 Wysoki",
    "normal": "⚪ Zwykly",
    "low":    "🔵 Niski",
}
_PRIORITY_ORDER = ["urgent", "high", "normal", "low"]
_PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

_CHANNEL_LABELS = {
    "ig_feed": "📷 IG Feed",
    "ig_stories": "✨ IG Stories",
    "ig_reels": "🎬 IG Reels",
    "fb": "📘 Facebook",
    "tiktok": "🎵 TikTok",
    "pinterest": "📌 Pinterest",
    "blog": "📝 Blog",
    "newsletter": "📧 Newsletter",
    "other": "📋 Inne",
}

_MARKET_LABELS = {
    "pl": "🇵🇱 PL",
    "eu": "🇪🇺 EU",
    "fr": "🇫🇷 FR",
    "de": "🇩🇪 DE",
    "es": "🇪🇸 ES",
    "nl": "🇳🇱 NL",
    "it": "🇮🇹 IT",
}
_MARKET_ORDER = ["pl", "eu", "fr", "de", "es", "nl", "it"]

_LANGUAGE_FLAGS = {
    "pl": "🇵🇱", "en": "🇬🇧", "de": "🇩🇪", "fr": "🇫🇷",
    "es": "🇪🇸", "nl": "🇳🇱", "it": "🇮🇹",
}


def _format_channels(channels: list[str]) -> str:
    if not channels:
        return ""
    if len(channels) == 1:
        return _CHANNEL_LABELS.get(channels[0], channels[0])
    # multi: pokaz ikony + skrocone nazwy
    return " + ".join(_CHANNEL_LABELS.get(c, c).split(" ", 1)[0] for c in channels) + f"  ({len(channels)})"


def _format_markets(markets: list[str]) -> str:
    if not markets:
        return ""
    return " ".join(_MARKET_LABELS.get(m, m).split(" ", 1)[0] for m in markets)


def _format_languages(languages: list[str]) -> str:
    if not languages:
        return "pl"
    return " ".join(_LANGUAGE_FLAGS.get(lg, lg) for lg in languages)


def _shift_date_value(raw_date: str, delta_days: int) -> str:
    value = (raw_date or "").strip()
    if not value:
        return ""
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return ""
    return (parsed + timedelta(days=delta_days)).isoformat()


class ZadaniaView:
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back
        self.frame = tk.Frame(parent, bg=_BG)
        self._iid_to_id: dict[str, str] = {}
        # Sortowanie: (kolumna, rosnaco) - None = wg domyslnego key
        self._sort_state: tuple[str, bool] | None = None
        self._build()
        self._refresh()

    # ---------- build ----------
    def _build(self) -> None:
        # Toolbar top
        toolbar = tk.Frame(self.frame, bg=_BG)
        toolbar.pack(fill="x", padx=14, pady=(12, 4))
        ttk.Button(toolbar, text="< Powrot", command=self.on_back).pack(side="left")
        tk.Label(
            toolbar, text="Zadania marketingowe", bg=_BG,
            font=("Segoe UI", 18, "bold"), fg="#222",
        ).pack(side="left", padx=(14, 0))
        tk.Label(
            toolbar, text="Organizer: blog + social + newsletter + evergreen",
            bg=_BG, fg="#666", font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 0), pady=(8, 0))

        # Action bar
        actions = tk.Frame(self.frame, bg=_BG)
        actions.pack(fill="x", padx=14, pady=(0, 6))
        ttk.Button(
            actions, text="🤖 Generator zadan (LLM)",
            command=self._open_generator,
        ).pack(side="left")
        ttk.Button(
            actions, text="＋ Nowe zadanie (recznie)",
            command=self._new_task_manual,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="🔄 Odswiez", command=self._refresh).pack(side="left", padx=(6, 0))
        ttk.Button(
            actions, text="📅 Wszystkie -1 dzien",
            command=lambda: self._shift_all_tasks_days(-1),
        ).pack(side="left", padx=(12, 0))
        ttk.Button(
            actions, text="📅 Wszystkie +1 dzien",
            command=lambda: self._shift_all_tasks_days(1),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            actions, text="🎯 Zaznaczone -1 dzien",
            command=lambda: self._shift_selected_task_days(-1),
        ).pack(side="left", padx=(12, 0))
        ttk.Button(
            actions, text="🎯 Zaznaczone +1 dzien",
            command=lambda: self._shift_selected_task_days(1),
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            actions, text="⬇ Eksport CSV",
            command=lambda: self._export_csv(self._filtered_tasks()),
        ).pack(side="right")

        # Filters
        filters = tk.Frame(self.frame, bg=_BG)
        filters.pack(fill="x", padx=14, pady=(0, 6))

        self.status_filter = tk.StringVar(value="(wszystkie)")
        self.channel_filter = tk.StringVar(value="(wszystkie)")
        self.language_filter = tk.StringVar(value="(wszystkie)")
        self.priority_filter = tk.StringVar(value="(wszystkie)")
        self.market_filter = tk.StringVar(value="(wszystkie)")

        ttk.Label(filters, text="Status:").pack(side="left", padx=(0, 4))
        ttk.Combobox(
            filters, textvariable=self.status_filter,
            values=["(wszystkie)"] + _STATUS_ORDER,
            state="readonly", width=14,
        ).pack(side="left")

        ttk.Label(filters, text="Kanal:").pack(side="left", padx=(10, 4))
        ttk.Combobox(
            filters, textvariable=self.channel_filter,
            values=["(wszystkie)"] + list(_CHANNEL_LABELS.keys()),
            state="readonly", width=14,
        ).pack(side="left")

        ttk.Label(filters, text="Jezyk:").pack(side="left", padx=(10, 4))
        ttk.Combobox(
            filters, textvariable=self.language_filter,
            values=["(wszystkie)", "pl", "en", "de", "fr", "es", "nl", "it"],
            state="readonly", width=10,
        ).pack(side="left")

        ttk.Label(filters, text="Rynek:").pack(side="left", padx=(10, 4))
        ttk.Combobox(
            filters, textvariable=self.market_filter,
            values=["(wszystkie)"] + _MARKET_ORDER,
            state="readonly", width=10,
        ).pack(side="left")

        ttk.Label(filters, text="Priorytet:").pack(side="left", padx=(10, 4))
        ttk.Combobox(
            filters, textvariable=self.priority_filter,
            values=["(wszystkie)"] + _PRIORITY_ORDER,
            state="readonly", width=12,
        ).pack(side="left")

        for v in (
            self.status_filter, self.channel_filter, self.language_filter,
            self.priority_filter, self.market_filter,
        ):
            v.trace_add("write", lambda *_: self._refresh())

        # Tree
        tv_frame = tk.Frame(self.frame, bg=_BG)
        tv_frame.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        cols = ("status", "due_date", "priority", "channel", "lang", "markets", "title", "source", "linked")
        self.tree = ttk.Treeview(tv_frame, columns=cols, show="headings", selectmode="extended")

        # Naglowki - kazdy klikalny do sortowania
        headings: dict[str, str] = {
            "status":   "Status",
            "due_date": "Termin",
            "priority": "Priorytet",
            "channel":  "Kanal",
            "lang":     "Jezyk",
            "markets":  "Rynki",
            "title":    "Tytul",
            "source":   "Zrodlo",
            "linked":   "Post",
        }
        for col, title in headings.items():
            self.tree.heading(col, text=title, command=lambda c=col: self._on_heading_click(c))

        self.tree.column("status", width=110, anchor="w")
        self.tree.column("due_date", width=100, anchor="w")
        self.tree.column("priority", width=110, anchor="w")
        self.tree.column("channel", width=160, anchor="w")
        self.tree.column("lang", width=70, anchor="center")
        self.tree.column("markets", width=120, anchor="w")
        self.tree.column("title", width=300, anchor="w")
        self.tree.column("source", width=80, anchor="w")
        self.tree.column("linked", width=50, anchor="center")

        vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Tagi - kolory wg statusu/priorytetu
        self.tree.tag_configure("done", foreground="#2e7d32", font=("Segoe UI", 9, "overstrike"))
        self.tree.tag_configure("skipped", foreground="#888", font=("Segoe UI", 9, "overstrike"))
        self.tree.tag_configure("in_progress", foreground="#1976d2", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("pending", foreground="#111")
        self.tree.tag_configure("overdue", foreground="#c62828", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("urgent_bg", background="#ffebee")
        self.tree.tag_configure("high_bg", background="#fff8e1")
        self.tree.tag_configure("multi_market", background="#e3f2fd")

        # Menu PPM
        self.menu = tk.Menu(self.tree, tearoff=0)
        self.tree.bind("<Button-3>", self._popup_menu)
        self.tree.bind("<Double-1>", lambda _e: self._edit_selected())

        # Status bar / licznik
        self.status_bar = tk.Frame(self.frame, bg=_BG)
        self.status_bar.pack(fill="x", padx=14, pady=(0, 12))
        self.counter_var = tk.StringVar(value="")
        tk.Label(
            self.status_bar, textvariable=self.counter_var,
            bg=_BG, fg="#555", font=("Segoe UI", 9),
        ).pack(side="left")

    # ---------- sortowanie ----------
    def _on_heading_click(self, col: str) -> None:
        """Toggle: pierwsze klikniecie - asc; drugie tej samej - desc; trzecie - reset (wg priorytetu)."""
        if self._sort_state is None or self._sort_state[0] != col:
            self._sort_state = (col, True)   # asc
        elif self._sort_state[1]:
            self._sort_state = (col, False)  # desc
        else:
            self._sort_state = None          # reset
        self._update_heading_arrows()
        self._refresh()

    def _update_heading_arrows(self) -> None:
        labels = {
            "status": "Status", "due_date": "Termin", "priority": "Priorytet",
            "channel": "Kanal", "lang": "Jezyk", "markets": "Rynki",
            "title": "Tytul", "source": "Zrodlo", "linked": "Post",
        }
        for col, base in labels.items():
            if self._sort_state and self._sort_state[0] == col:
                arrow = "  ▲" if self._sort_state[1] else "  ▼"
                self.tree.heading(col, text=base + arrow)
            else:
                self.tree.heading(col, text=base)

    def _sort_tasks(self, tasks: list[storage.Task]) -> list[storage.Task]:
        if self._sort_state is None:
            tasks.sort(key=_default_sort_key)
            return tasks
        col, asc = self._sort_state

        def key_for(t: storage.Task) -> tuple:
            if col == "status":
                return (_STATUS_RANK.get(t.status, 99), t.created_at)
            if col == "due_date":
                return (t.due_date or "9999-99-99",)
            if col == "priority":
                return (_PRIORITY_RANK.get(t.priority, 99),)
            if col == "channel":
                return (t.channel,)
            if col == "lang":
                return (",".join(t.languages),)
            if col == "markets":
                return (",".join(t.target_markets),)
            if col == "title":
                return (t.title.lower(),)
            if col == "source":
                return (t.source,)
            if col == "linked":
                return (0 if t.linked_post_ids else 1,)
            return (t.created_at,)

        tasks.sort(key=key_for, reverse=not asc)
        return tasks

    # ---------- data ----------
    def _filtered_tasks(self) -> list[storage.Task]:
        tasks = storage.load_tasks()
        sv = self.status_filter.get()
        if sv != "(wszystkie)":
            tasks = [t for t in tasks if t.status == sv]
        cv = self.channel_filter.get()
        if cv != "(wszystkie)":
            tasks = [t for t in tasks if cv in t.channels]
        lv = self.language_filter.get()
        if lv != "(wszystkie)":
            tasks = [t for t in tasks if lv in t.languages]
        pv = self.priority_filter.get()
        if pv != "(wszystkie)":
            tasks = [t for t in tasks if t.priority == pv]
        mv = self.market_filter.get()
        if mv != "(wszystkie)":
            tasks = [t for t in tasks if mv in t.target_markets]
        return self._sort_tasks(tasks)

    def _refresh(self) -> None:
        self._iid_to_id.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        today = date.today().isoformat()
        all_tasks = self._filtered_tasks()
        cnt_by_status: dict[str, int] = {s: 0 for s in _STATUS_ORDER}
        for t in all_tasks:
            cnt_by_status[t.status] = cnt_by_status.get(t.status, 0) + 1
            status_label = _STATUS_LABELS.get(t.status, t.status)
            channel_label = _format_channels(t.channels)
            markets_label = _format_markets(t.target_markets)
            lang_label = _format_languages(t.languages)
            linked = "●" if t.linked_post_ids else ""
            prio_label = _PRIORITY_LABELS_PL.get(t.priority, t.priority)
            tags: list[str] = [t.status]
            if t.status == "pending" and t.due_date and t.due_date < today:
                tags.append("overdue")
                prio_label = prio_label + " ⚠"
            if t.priority == "urgent":
                tags.append("urgent_bg")
            elif t.priority == "high":
                tags.append("high_bg")
            iid = self.tree.insert(
                "", "end",
                values=(
                    status_label, t.due_date or "", prio_label,
                    channel_label, lang_label, markets_label,
                    t.title, t.source, linked,
                ),
                tags=tuple(tags),
            )
            self._iid_to_id[iid] = t.id
        self.counter_var.set(
            f"Razem: {len(all_tasks)}  |  ⏳ {cnt_by_status['pending']}   "
            f"▶ {cnt_by_status['in_progress']}   ✅ {cnt_by_status['done']}   "
            f"⏭ {cnt_by_status['skipped']}"
        )
        self._update_heading_arrows()

    # ---------- actions ----------
    def _selected(self) -> list[storage.Task]:
        out: list[storage.Task] = []
        for iid in self.tree.selection():
            tid = self._iid_to_id.get(iid)
            if not tid:
                continue
            t = storage.get_task(tid)
            if t:
                out.append(t)
        return out

    def _open_generator(self) -> None:
        open_tasks_generator(
            self.frame.winfo_toplevel(),
            on_saved=lambda _n: self._refresh(),
        )

    def _new_task_manual(self) -> None:
        _open_edit_dialog(self.frame.winfo_toplevel(), None, on_saved=self._refresh)

    def _edit_selected(self) -> None:
        sel = self._selected()
        if not sel:
            return
        _open_edit_dialog(self.frame.winfo_toplevel(), sel[0], on_saved=self._refresh)

    def _generate_post_from_task(self) -> None:
        sel = self._selected()
        if not sel:
            return
        task = sel[0]
        primary = task.channel
        if primary == "blog":
            self._open_blog_generator(task)
        elif primary in {"ig_feed", "ig_stories", "ig_reels", "fb", "tiktok", "pinterest"}:
            self._open_sm_generator(task)
        else:
            messagebox.showinfo(
                "Brak generatora",
                f"Zadanie ma kanal '{primary}' - dla ktorego nie mamy dedykowanego generatora.\n"
                f"Mozesz oznaczyc je jako zrobione recznie.",
                parent=self.frame,
            )

    def _open_sm_generator(self, task: storage.Task) -> None:
        try:
            from Komponenty.socialmedia.generator_tresci import open_content_generator
        except ImportError as e:
            messagebox.showerror("Brak komponentu socialmedia", str(e), parent=self.frame)
            return
        # Multi-channel: przekaz wszystkie social-channels z zadania
        sm_channels = [c for c in task.channels if c in {
            "ig_feed", "ig_stories", "ig_reels", "fb", "tiktok", "pinterest",
        }]
        if not sm_channels:
            sm_channels = [task.channel]
        primary_lang = task.language if task.language in ("pl", "en") else "pl"
        topic = task.suggested_topic or task.title
        if task.status == "pending":
            storage.set_status(task.id, "in_progress")
            self._refresh()
        open_content_generator(
            self.frame.winfo_toplevel(),
            initial_topic=topic,
            initial_platform=sm_channels[0],
            initial_platforms=sm_channels,
            initial_language=primary_lang,
            initial_link="",
            from_task_id=task.id,
            on_saved=lambda _n: self._on_post_saved_from_task(task.id),
        )

    def _on_post_saved_from_task(self, task_id: str) -> None:
        try:
            from Komponenty.socialmedia import storage as sm_storage
        except ImportError:
            return
        posts = sorted(sm_storage.load_posts(), key=lambda p: p.created_at, reverse=True)
        if not posts:
            return
        latest = posts[0]
        if not latest.from_task_id:
            sm_storage.update_post(latest.id, from_task_id=task_id)
        storage.link_post(task_id, latest.id)
        self._refresh()

    def _open_blog_generator(self, task: storage.Task) -> None:
        try:
            from Komponenty.blog.generator_tresci import open_content_generator as blog_open
        except ImportError as e:
            messagebox.showerror("Brak komponentu blog", str(e), parent=self.frame)
            return
        topic = task.suggested_topic or task.title
        if task.status == "pending":
            storage.set_status(task.id, "in_progress")
            self._refresh()
        blog_open(self.frame.winfo_toplevel(), initial_topic=topic)

    def _copy_topic(self) -> None:
        sel = self._selected()
        if not sel:
            return
        text = sel[0].suggested_topic or sel[0].title
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(text)
            self.frame.update()
            show_toast(self.frame, "Skopiowano temat", duration_ms=1000)
        except tk.TclError:
            pass

    def _set_status(self, status: str) -> None:
        sel = self._selected()
        if not sel:
            return
        for t in sel:
            storage.set_status(t.id, status)
        self._refresh()
        show_toast(self.frame, f"Status: {_STATUS_LABELS.get(status, status)}", duration_ms=1200)

    def _shift_all_tasks_days(self, delta_days: int) -> None:
        tasks = storage.load_tasks()
        moved = 0
        skipped = 0
        for task in tasks:
            new_due = _shift_date_value(task.due_date, delta_days)
            if not new_due:
                skipped += 1
                continue
            storage.update_task(task.id, due_date=new_due)
            moved += 1
        self._refresh()
        sign = "+" if delta_days > 0 else ""
        show_toast(
            self.frame,
            f"Przesunieto {moved} zadan o {sign}{delta_days} dzien (pominieto {skipped})",
            duration_ms=1800,
        )

    def _shift_selected_task_days(self, delta_days: int) -> None:
        selected = self._selected()
        if not selected:
            messagebox.showinfo("Brak zaznaczenia", "Zaznacz zadanie do przesuniecia.", parent=self.frame)
            return
        task = selected[0]
        new_due = _shift_date_value(task.due_date, delta_days)
        if not new_due:
            messagebox.showwarning(
                "Brak terminu",
                "Zaznaczone zadanie nie ma poprawnego terminu (YYYY-MM-DD).",
                parent=self.frame,
            )
            return
        storage.update_task(task.id, due_date=new_due)
        self._refresh()
        sign = "+" if delta_days > 0 else ""
        show_toast(self.frame, f"Przesunieto zadanie o {sign}{delta_days} dzien", duration_ms=1300)

    def _delete(self) -> None:
        sel = self._selected()
        if not sel:
            return
        if not messagebox.askyesno(
            "Usunac?", f"Usunac {len(sel)} zadanie(a)?", parent=self.frame,
        ):
            return
        for t in sel:
            storage.remove_task(t.id)
        self._refresh()

    def _popup_menu(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        if not self.tree.selection():
            return
        m = self.menu
        m.delete(0, "end")
        m.add_command(label="✍️ Generuj post (otworz generator)", command=self._generate_post_from_task)
        m.add_separator()
        m.add_command(label="Edytuj...", command=self._edit_selected)
        m.add_command(label="Kopiuj temat (do schowka)", command=self._copy_topic)
        m.add_separator()
        status_m = tk.Menu(m, tearoff=0)
        status_m.add_command(label=_STATUS_LABELS["pending"], command=lambda: self._set_status("pending"))
        status_m.add_command(label=_STATUS_LABELS["in_progress"], command=lambda: self._set_status("in_progress"))
        status_m.add_command(label=_STATUS_LABELS["done"], command=lambda: self._set_status("done"))
        status_m.add_command(label=_STATUS_LABELS["skipped"], command=lambda: self._set_status("skipped"))
        m.add_cascade(label="Zmien status", menu=status_m)
        m.add_separator()
        m.add_command(label="Usun...", command=self._delete)
        m.tk_popup(event.x_root, event.y_root)

    # ---------- CSV ----------
    def _export_csv(self, tasks: list[storage.Task]) -> None:
        if not tasks:
            messagebox.showinfo("Pusto", "Brak zadan do eksportu.", parent=self.frame)
            return
        path = filedialog.asksaveasfilename(
            title="Zapisz CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
            initialfile="zadania_marketingowe.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "id", "status", "due_date", "priority", "channels", "languages",
                    "target_markets", "title", "description", "description_translations",
                    "suggested_topic", "source", "source_ref",
                    "linked_post_ids", "notes", "created_at",
                ])
                for t in tasks:
                    tr_str = "; ".join(f"{k}={v}" for k, v in t.description_translations.items())
                    writer.writerow([
                        t.id, t.status, t.due_date, t.priority,
                        ",".join(t.channels), ",".join(t.languages),
                        ",".join(t.target_markets),
                        t.title, t.description, tr_str,
                        t.suggested_topic, t.source, t.source_ref,
                        " ".join(t.linked_post_ids), t.notes, t.created_at,
                    ])
        except OSError as e:
            messagebox.showerror("Blad zapisu", str(e), parent=self.frame)
            return
        show_toast(self.frame, f"Zapisano {len(tasks)} zadan do CSV", duration_ms=1500)


# ---------------------------------------------------------------------------
# Edit dialog (new/edit task)
# ---------------------------------------------------------------------------

def _open_edit_dialog(
    parent: tk.Misc,
    task: storage.Task | None,
    *,
    on_saved: Callable[[], None],
) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Nowe zadanie" if task is None else "Edycja zadania")
    position_toplevel_screen_center(dlg, 780, 780)
    dlg.minsize(680, 640)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    root = ttk.Frame(dlg, padding=12)
    root.pack(fill="both", expand=True)

    grid = ttk.Frame(root)
    grid.pack(fill="both", expand=True)
    grid.columnconfigure(1, weight=1)

    row_idx = [0]

    def _add_row(label: str, widget: tk.Widget, sticky: str = "ew") -> None:
        ttk.Label(grid, text=label).grid(row=row_idx[0], column=0, sticky="nw", padx=(0, 8), pady=3)
        widget.grid(row=row_idx[0], column=1, sticky=sticky, pady=3)
        row_idx[0] += 1

    title_var = tk.StringVar(value=task.title if task else "")
    _add_row("Tytul:", ttk.Entry(grid, textvariable=title_var))

    # Multi-select kanalow (Listbox z extended select)
    channel_frame = ttk.Frame(grid)
    channel_lb = tk.Listbox(channel_frame, selectmode="extended", height=5, exportselection=False)
    for ch in _CHANNEL_LABELS:
        channel_lb.insert("end", f"{_CHANNEL_LABELS[ch]}  [{ch}]")
    if task:
        for i, ch in enumerate(_CHANNEL_LABELS):
            if ch in task.channels:
                channel_lb.selection_set(i)
    else:
        channel_lb.selection_set(0)  # ig_feed default
    channel_lb.pack(side="left", fill="x", expand=True)
    ttk.Label(
        channel_frame,
        text="Ctrl/Shift\n+ klik\n= multi",
        foreground="#888", font=("Segoe UI", 8),
    ).pack(side="left", padx=(6, 0))
    _add_row("Kanaly (multi):", channel_frame)

    # Multi-select languages
    lang_frame = ttk.Frame(grid)
    lang_lb = tk.Listbox(lang_frame, selectmode="extended", height=4, exportselection=False)
    lang_codes = ["pl", "en", "de", "fr", "es", "nl", "it"]
    for lc in lang_codes:
        lang_lb.insert("end", f"{_LANGUAGE_FLAGS.get(lc, '')} {lc}")
    if task:
        for i, lc in enumerate(lang_codes):
            if lc in task.languages:
                lang_lb.selection_set(i)
    else:
        lang_lb.selection_set(0)
    lang_lb.pack(side="left", fill="x", expand=True)
    _add_row("Jezyki (multi):", lang_frame)

    # Multi-select markets
    market_frame = ttk.Frame(grid)
    market_lb = tk.Listbox(market_frame, selectmode="extended", height=4, exportselection=False)
    for mk in _MARKET_ORDER:
        market_lb.insert("end", f"{_MARKET_LABELS[mk]}")
    if task:
        for i, mk in enumerate(_MARKET_ORDER):
            if mk in task.target_markets:
                market_lb.selection_set(i)
    else:
        market_lb.selection_set(0)
    market_lb.pack(side="left", fill="x", expand=True)
    _add_row("Rynki Shopify (multi):", market_frame)

    due_var = tk.StringVar(value=task.due_date if task else "")
    _add_row("Termin (YYYY-MM-DD):", ttk.Entry(grid, textvariable=due_var))

    prio_var = tk.StringVar(value=task.priority if task else "normal")
    prio_cb = ttk.Combobox(
        grid, textvariable=prio_var, state="readonly",
        values=_PRIORITY_ORDER,
    )
    _add_row("Priorytet:", prio_cb)

    source_var = tk.StringVar(value=task.source if task else "manual")
    _add_row("Zrodlo:", ttk.Combobox(
        grid, textvariable=source_var, state="readonly",
        values=["shopify", "holiday", "llm", "manual", "evergreen"],
    ))

    source_ref_var = tk.StringVar(value=task.source_ref if task else "")
    _add_row("Ref. zrodla:", ttk.Entry(grid, textvariable=source_ref_var))

    suggested_var = tk.StringVar(value=task.suggested_topic if task else "")
    _add_row("Sugestia tematu:", ttk.Entry(grid, textvariable=suggested_var))

    status_var = tk.StringVar(value=task.status if task else "pending")
    _add_row("Status:", ttk.Combobox(
        grid, textvariable=status_var, state="readonly",
        values=_STATUS_ORDER,
    ))

    # Opis (PL)
    desc_lf = ttk.LabelFrame(grid, text="Opis (po polsku - dla Ciebie)", padding=4)
    desc_text = tk.Text(desc_lf, height=4, wrap="word", font=("Segoe UI", 9))
    desc_text.pack(fill="both", expand=True)
    if task:
        desc_text.insert("1.0", task.description)
    desc_lf.grid(row=row_idx[0], column=0, columnspan=2, sticky="ew", pady=(8, 3))
    grid.rowconfigure(row_idx[0], weight=0)
    row_idx[0] += 1

    # Tlumaczenia opisu (zwijane sekcje)
    tr_lf = ttk.LabelFrame(
        grid,
        text="Tlumaczenia opisu (uzywaj dla zadan na zagraniczne rynki - zostaw puste jesli niepotrzebne)",
        padding=4,
    )
    tr_grid = ttk.Frame(tr_lf)
    tr_grid.pack(fill="both", expand=True)
    tr_grid.columnconfigure(1, weight=1)
    tr_widgets: dict[str, tk.Text] = {}
    for ti, tlang in enumerate(["en", "de", "fr", "es", "nl", "it"]):
        ttk.Label(
            tr_grid,
            text=f"{_LANGUAGE_FLAGS.get(tlang, '')} {tlang}:",
            width=6,
        ).grid(row=ti, column=0, sticky="nw", padx=(0, 6), pady=2)
        txt = tk.Text(tr_grid, height=2, wrap="word", font=("Segoe UI", 9))
        txt.grid(row=ti, column=1, sticky="ew", pady=2)
        if task and tlang in task.description_translations:
            txt.insert("1.0", task.description_translations[tlang])
        tr_widgets[tlang] = txt
    tr_lf.grid(row=row_idx[0], column=0, columnspan=2, sticky="ew", pady=3)
    row_idx[0] += 1

    notes_lf = ttk.LabelFrame(grid, text="Notatki", padding=4)
    notes_text = tk.Text(notes_lf, height=2, wrap="word", font=("Segoe UI", 9))
    notes_text.pack(fill="both", expand=True)
    if task:
        notes_text.insert("1.0", task.notes)
    notes_lf.grid(row=row_idx[0], column=0, columnspan=2, sticky="ew", pady=3)
    row_idx[0] += 1

    btns = ttk.Frame(root)
    btns.pack(fill="x", pady=(10, 0))

    def _collect_listbox(lb: tk.Listbox, codes: list[str]) -> list[str]:
        out = [codes[i] for i in lb.curselection() if 0 <= i < len(codes)]
        return out

    def _save() -> None:
        title = title_var.get().strip()
        if not title:
            messagebox.showwarning("Brak tytulu", "Podaj tytul zadania.", parent=dlg)
            return
        sel_channels = _collect_listbox(channel_lb, list(_CHANNEL_LABELS.keys())) or ["other"]
        sel_languages = _collect_listbox(lang_lb, lang_codes) or ["pl"]
        sel_markets = _collect_listbox(market_lb, _MARKET_ORDER) or ["pl"]
        translations: dict[str, str] = {}
        for tlang, w in tr_widgets.items():
            v = w.get("1.0", "end-1c").strip()
            if v:
                translations[tlang] = v
        if task is None:
            t = storage.Task.new(
                title=title,
                description=desc_text.get("1.0", "end-1c").strip(),
                description_translations=translations,
                channels=sel_channels,
                languages=sel_languages,
                target_markets=sel_markets,
                due_date=due_var.get().strip(),
                priority=prio_var.get().strip(),
                source=source_var.get().strip(),
                source_ref=source_ref_var.get().strip(),
                suggested_topic=suggested_var.get().strip(),
                notes=notes_text.get("1.0", "end-1c").strip(),
            )
            storage.add_tasks([t], dedup_key="none")
        else:
            storage.update_task(
                task.id,
                title=title,
                description=desc_text.get("1.0", "end-1c").strip(),
                description_translations=translations,
                channels=sel_channels,
                languages=sel_languages,
                target_markets=sel_markets,
                due_date=due_var.get().strip(),
                priority=prio_var.get().strip(),
                source=source_var.get().strip(),
                source_ref=source_ref_var.get().strip(),
                suggested_topic=suggested_var.get().strip(),
                status=status_var.get().strip(),
                notes=notes_text.get("1.0", "end-1c").strip(),
            )
        show_toast(dlg, "Zapisano", duration_ms=1000)
        on_saved()
        dlg.destroy()

    ttk.Button(btns, text="💾 Zapisz", command=_save).pack(side="right")
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 6))
    dlg.bind("<Escape>", lambda _e: dlg.destroy())


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def _default_sort_key(t: storage.Task) -> tuple[int, int, str, str]:
    status_rank = _STATUS_RANK.get(t.status, 4)
    prio_rank = _PRIORITY_RANK.get(t.priority, 4)
    return (status_rank, prio_rank, t.due_date or "9999", t.created_at)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    view = ZadaniaView(parent, on_back)
    return view.frame
