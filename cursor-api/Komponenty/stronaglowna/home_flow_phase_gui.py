"""Edytor ustawień faz GICLÉE HOME FLOW.

Dwuklik fazy w głównym drzewie lub przycisk w oknie HOME FLOW otwiera
formularz powiązany z kanonicznym plikiem ``home_flow_phases.json``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Iterable

from . import home_flow_gui as base_gui
from .home_flow import flow_item_by_id
from .home_flow_phase_settings import (
    CURTAIN_ID,
    HERO_HOLD_ID,
    HERO_RISE_ID,
    INTRO_HOLD_ID,
    KNOWN_PHASE_IDS,
    PHASE_LABELS,
    PORTAL_ID,
    SOUND_ID,
    effective_phase_config,
    reset_phase_config,
    set_phase_config,
)
from .homepage_variants import active_variant_id, variant_label


def _walk(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def _widget_text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text") or "")
    except (tk.TclError, AttributeError):
        return ""


def _selected_phase(tree: ttk.Treeview) -> str:
    selected = tree.selection()
    stable_id = str(selected[0]) if selected else ""
    return stable_id if stable_id in KNOWN_PHASE_IDS else ""


def _add_int_row(
    parent: ttk.Frame,
    label: str,
    variable: tk.IntVar,
    *,
    minimum: int,
    maximum: int,
    hint: str = "",
) -> None:
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(0, 10))
    ttk.Label(row, text=label + ":", width=31).pack(side="left", anchor="n")
    col = ttk.Frame(row)
    col.pack(side="left", fill="x", expand=True)
    ttk.Spinbox(
        col,
        from_=minimum,
        to=maximum,
        textvariable=variable,
        width=7,
    ).pack(anchor="w")
    if hint:
        ttk.Label(col, text=hint, foreground="#777", wraplength=520).pack(
            anchor="w", pady=(3, 0)
        )


def _add_entry_row(
    parent: ttk.Frame,
    label: str,
    variable: tk.StringVar,
    *,
    hint: str = "",
    width: int = 56,
) -> None:
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(0, 10))
    ttk.Label(row, text=label + ":", width=31).pack(side="left", anchor="n")
    col = ttk.Frame(row)
    col.pack(side="left", fill="x", expand=True)
    ttk.Entry(col, textvariable=variable, width=width).pack(fill="x", expand=True)
    if hint:
        ttk.Label(col, text=hint, foreground="#777", wraplength=520).pack(
            anchor="w", pady=(3, 0)
        )


def _open_phase_editor(
    host: tk.Misc,
    stable_id: str,
    *,
    on_saved: Callable[[], None] | None = None,
) -> None:
    if stable_id not in KNOWN_PHASE_IDS:
        return

    variant_id = active_variant_id()
    item = flow_item_by_id(variant_id, stable_id)
    values = effective_phase_config(variant_id, stable_id)
    title = item.display_name if item is not None else PHASE_LABELS.get(stable_id, stable_id)
    code = item.code if item is not None else ""

    existing = getattr(host, "_giclee_home_phase_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.destroy()
        except tk.TclError:
            pass

    win = tk.Toplevel(host.winfo_toplevel())
    host._giclee_home_phase_window = win  # type: ignore[attr-defined]
    win.title(f"{code} — {title}")
    win.transient(host.winfo_toplevel())
    win.grab_set()
    win.geometry("760x650" if stable_id == SOUND_ID else "700x540")
    win.minsize(590, 420)

    outer = ttk.Frame(win, padding=(16, 14))
    outer.pack(fill="both", expand=True)

    ttk.Label(outer, text=f"{code}  {title}", font=("", 13, "bold")).pack(anchor="w")
    ttk.Label(
        outer,
        text=(
            f"ID techniczne: {stable_id} · wariant: {variant_label(variant_id)}\n"
            "Ustawienia zostaną zastosowane przy głównym przycisku „Zapisz”."
        ),
        foreground="#666",
        wraplength=690,
    ).pack(anchor="w", pady=(4, 14))

    body_host = ttk.Frame(outer)
    body_host.pack(fill="both", expand=True)
    canvas = tk.Canvas(body_host, highlightthickness=0, yscrollincrement=20)
    scrollbar = ttk.Scrollbar(body_host, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    body = ttk.Frame(canvas)
    body_window = canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind(
        "<Configure>",
        lambda _event=None: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(body_window, width=event.width),
    )

    vars_: dict[str, Any] = {}

    if stable_id == PORTAL_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        ttk.Checkbutton(
            body,
            text="Pokaż animowany tekst w portalu",
            variable=vars_["enabled"],
        ).pack(anchor="w", pady=(0, 12))
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 2)))
        _add_int_row(
            body,
            "Długość portalu",
            vars_["screens"],
            minimum=1,
            maximum=10,
            hint="1 ekran = 100vh. Wartość określa, ile przed końcem scrubbingu zaczyna się portal.",
        )
        ttk.Label(body, text="Tekst portalu:").pack(anchor="w")
        text_widget = tk.Text(body, wrap="word", height=9, font=("", 10))
        text_widget.insert("1.0", str(values.get("text") or ""))
        text_widget.pack(fill="both", expand=True, pady=(4, 0))
        vars_["text"] = text_widget
        ttk.Label(
            body,
            text="Każda niepusta linia jest animowana osobno; maksymalnie 5 linii.",
            foreground="#777",
        ).pack(anchor="w", pady=(4, 0))

    elif stable_id == HERO_RISE_ID:
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_int_row(
            body,
            "Długość wjazdu Hero",
            vars_["screens"],
            minimum=1,
            maximum=5,
            hint="Faza jest obowiązkowa dla obecnej architektury. 1 ekran = 100vh.",
        )

    elif stable_id == HERO_HOLD_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        ttk.Checkbutton(
            body,
            text="Włącz pusty scroll po wycentrowaniu Hero",
            variable=vars_["enabled"],
        ).pack(anchor="w", pady=(0, 12))
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_int_row(
            body,
            "Długość postoju Hero",
            vars_["screens"],
            minimum=0,
            maximum=5,
            hint="Po wyłączeniu generator zapisze 0vh i kurtyna zacznie się bez postoju.",
        )

    elif stable_id == SOUND_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        ttk.Checkbutton(
            body,
            text="Pokaż pytanie o uruchomienie dźwięku",
            variable=vars_["enabled"],
        ).pack(anchor="w", pady=(0, 12))
        vars_["question"] = tk.StringVar(value=str(values.get("question") or ""))
        _add_entry_row(body, "Pytanie", vars_["question"])
        vars_["toggle_label"] = tk.StringVar(value=str(values.get("toggle_label") or ""))
        _add_entry_row(body, "Etykieta przełącznika", vars_["toggle_label"])
        vars_["start_label"] = tk.StringVar(value=str(values.get("start_label") or ""))
        _add_entry_row(body, "Przycisk rozpoczęcia", vars_["start_label"])
        vars_["audio_url"] = tk.StringVar(value=str(values.get("audio_url") or ""))
        _add_entry_row(
            body,
            "URL ambientu CDN",
            vars_["audio_url"],
            hint="Wczytany z ustawień Hero. Po zgodzie użytkownika ten plik będzie odtwarzany w pętli.",
        )

        volume_frame = ttk.Frame(body)
        volume_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(volume_frame, text="Głośność ambientu:", width=31).pack(side="left")
        volume_col = ttk.Frame(volume_frame)
        volume_col.pack(side="left", fill="x", expand=True)
        vars_["volume"] = tk.IntVar(value=int(values.get("volume", 28)))
        volume_label = tk.StringVar(value=f"{vars_['volume'].get()}%")
        ttk.Scale(
            volume_col,
            from_=0,
            to=100,
            orient="horizontal",
            variable=vars_["volume"],
            command=lambda _value: volume_label.set(f"{int(vars_['volume'].get())}%"),
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(volume_col, textvariable=volume_label, width=6).pack(side="left", padx=(8, 0))

        vars_["auto_muted_fraction"] = tk.IntVar(
            value=int(values.get("auto_muted_fraction", 35))
        )
        _add_int_row(
            body,
            "Autostart bez dźwięku po",
            vars_["auto_muted_fraction"],
            minimum=0,
            maximum=100,
            hint="Procent postoju Hero. Gdy użytkownik nie odpowie, wideo zacznie się wyciszone.",
        )

    elif stable_id == CURTAIN_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        ttk.Checkbutton(
            body,
            text="Włącz poziomą kurtynę Hero → Giclée Art",
            variable=vars_["enabled"],
        ).pack(anchor="w", pady=(0, 12))
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_int_row(
            body,
            "Długość otwierania kurtyny",
            vars_["screens"],
            minimum=1,
            maximum=5,
            hint="1 ekran = 100vh przewijania.",
        )

    elif stable_id == INTRO_HOLD_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        ttk.Checkbutton(
            body,
            text="Włącz pusty scroll na odsłoniętej sekcji Giclée Art",
            variable=vars_["enabled"],
        ).pack(anchor="w", pady=(0, 12))
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_int_row(
            body,
            "Długość postoju sekcji",
            vars_["screens"],
            minimum=0,
            maximum=5,
            hint="Po wyłączeniu przejście natychmiast odda sekcję do normalnego układu strony.",
        )

    status_var = tk.StringVar(value="")
    ttk.Label(outer, textvariable=status_var, foreground="#666", wraplength=690).pack(
        anchor="w", pady=(10, 0)
    )

    def collect() -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, variable in vars_.items():
            if isinstance(variable, tk.Text):
                out[key] = variable.get("1.0", "end-1c")
            elif hasattr(variable, "get"):
                out[key] = variable.get()
        return out

    def save() -> None:
        try:
            set_phase_config(variant_id, stable_id, collect())
        except (ValueError, OSError) as exc:
            messagebox.showerror("GICLÉE HOME FLOW", str(exc), parent=win)
            return
        status_var.set("Ustawienia fazy zapisane. Kliknij główne „Zapisz”, aby przebudować podgląd motywu.")
        if on_saved is not None:
            on_saved()
        messagebox.showinfo(
            "GICLÉE HOME FLOW",
            "Ustawienia fazy zostały zapisane dla bieżącego wariantu.\n\n"
            "Teraz użyj głównego przycisku „Zapisz”, aby zastosować je do strony.",
            parent=win,
        )
        win.destroy()

    def restore() -> None:
        if not messagebox.askyesno(
            "GICLÉE HOME FLOW",
            "Usunąć własne ustawienia tej fazy i wrócić do wartości zapisanych w wariancie?",
            parent=win,
        ):
            return
        reset_phase_config(variant_id, stable_id)
        if on_saved is not None:
            on_saved()
        win.destroy()
        _open_phase_editor(host, stable_id, on_saved=on_saved)

    controls = ttk.Frame(outer)
    controls.pack(fill="x", pady=(14, 0))
    ttk.Button(controls, text="Przywróć z wariantu", command=restore).pack(side="left")
    ttk.Button(controls, text="Zapisz fazę", command=save).pack(side="right")
    ttk.Button(controls, text="Anuluj", command=win.destroy).pack(side="right", padx=(0, 8))

    def on_destroy(event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not win:
            return
        if getattr(host, "_giclee_home_phase_window", None) is win:
            host._giclee_home_phase_window = None  # type: ignore[attr-defined]

    win.bind("<Destroy>", on_destroy)


def _find_tree(host: tk.Misc, *, headings: bool) -> ttk.Treeview | None:
    for widget in _walk(host):
        if not isinstance(widget, ttk.Treeview):
            continue
        try:
            show = str(widget.cget("show"))
        except tk.TclError:
            show = ""
        if headings and "headings" in show:
            return widget
        if not headings and "headings" not in show:
            return widget
    return None


def _decorate_flow_window(host: tk.Misc) -> None:
    win = getattr(host, "_giclee_home_flow_window", None)
    if win is None or getattr(win, "_giclee_phase_controls", False):
        return
    try:
        if not win.winfo_exists():
            return
    except tk.TclError:
        return

    tree = _find_tree(win, headings=True)
    if tree is None:
        return
    controls = None
    for widget in _walk(win):
        if isinstance(widget, ttk.Button) and _widget_text(widget) == "Zmień nazwę…":
            controls = widget.master
            break
    if controls is None:
        return

    win._giclee_phase_controls = True  # type: ignore[attr-defined]
    edit_button = ttk.Button(
        controls,
        text="Edytuj fazę…",
        command=lambda: _open_phase_editor(
            host,
            _selected_phase(tree),
            on_saved=lambda: None,
        ),
    )
    edit_button.pack(side="left", padx=(8, 0))

    def sync_button(_event=None) -> None:
        edit_button.configure(state="normal" if _selected_phase(tree) else "disabled")

    tree.bind("<<TreeviewSelect>>", sync_button, add="+")
    sync_button()


def _decorate_main_tree(host: tk.Misc) -> None:
    tree = _find_tree(host, headings=False)
    if tree is None or getattr(tree, "_giclee_phase_bound", False):
        return
    tree._giclee_phase_bound = True  # type: ignore[attr-defined]

    def open_from_double_click(event) -> None:
        stable_id = str(tree.identify_row(event.y) or "")
        if stable_id in KNOWN_PHASE_IDS:
            tree.selection_set(stable_id)
            tree.focus(stable_id)
            _open_phase_editor(host, stable_id)

    tree.bind("<Double-1>", open_from_double_click, add="+")


def install_home_flow_phase_gui() -> None:
    current_open = base_gui._open_flow_editor
    if not getattr(current_open, "_giclee_phase_editor", False):

        def open_with_phase_controls(
            host: tk.Misc,
            refresh_navigation: Callable[[], None],
        ) -> None:
            current_open(host, refresh_navigation)
            host.after_idle(lambda: _decorate_flow_window(host))

        setattr(open_with_phase_controls, "_giclee_phase_editor", True)
        setattr(open_with_phase_controls, "__wrapped__", current_open)
        base_gui._open_flow_editor = open_with_phase_controls

    current_decorate = base_gui._decorate_home_editor
    if not getattr(current_decorate, "_giclee_phase_editor", False):

        def decorate_with_phase_editor(host: tk.Misc) -> None:
            current_decorate(host)
            host.after_idle(lambda: _decorate_main_tree(host))

        setattr(decorate_with_phase_editor, "_giclee_phase_editor", True)
        setattr(decorate_with_phase_editor, "__wrapped__", current_decorate)
        base_gui._decorate_home_editor = decorate_with_phase_editor
