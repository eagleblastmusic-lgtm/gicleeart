"""Edycja faz HOME FLOW bezpośrednio w prawym panelu głównego komponentu.

Pojedyncze kliknięcie sekcji nadal uruchamia istniejący edytor sekcji. Kliknięcie
fazy GH-Txx zastępuje jego zawartość formularzem fazy, bez dodatkowego okna.
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
from .home_flow_phase_summary import phase_summary
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


def _find_main_tree(host: tk.Misc) -> ttk.Treeview | None:
    for widget in _walk(host):
        if not isinstance(widget, ttk.Treeview):
            continue
        try:
            show = str(widget.cget("show"))
        except tk.TclError:
            continue
        if "headings" not in show:
            return widget
    return None


def _find_editor(host: tk.Misc) -> tuple[ttk.LabelFrame | None, ttk.Frame | None, tk.Canvas | None]:
    right: ttk.LabelFrame | None = None
    for widget in _walk(host):
        if isinstance(widget, ttk.LabelFrame) and _widget_text(widget).startswith("Edycja"):
            right = widget
            break
    if right is None:
        return None, None, None

    canvas = next((w for w in _walk(right) if isinstance(w, tk.Canvas)), None)
    if canvas is None:
        return right, None, None
    editor = next((w for w in canvas.winfo_children() if isinstance(w, ttk.Frame)), None)
    return right, editor, canvas


def _clear(parent: ttk.Frame) -> None:
    for child in parent.winfo_children():
        child.destroy()


def _add_check(parent: ttk.Frame, text: str, variable: tk.BooleanVar) -> None:
    ttk.Checkbutton(parent, text=text, variable=variable).pack(anchor="w", pady=(0, 12))


def _add_entry(
    parent: ttk.Frame,
    label: str,
    variable: tk.StringVar,
    *,
    hint: str = "",
) -> None:
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(0, 10))
    ttk.Label(row, text=label + ":", width=30).pack(side="left", anchor="n")
    col = ttk.Frame(row)
    col.pack(side="left", fill="x", expand=True)
    ttk.Entry(col, textvariable=variable).pack(fill="x", expand=True)
    if hint:
        ttk.Label(col, text=hint, foreground="#777", wraplength=560).pack(
            anchor="w", pady=(3, 0)
        )


def _add_screens(
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
    ttk.Label(row, text=label + ":", width=30).pack(side="left", anchor="n")
    col = ttk.Frame(row)
    col.pack(side="left", fill="x", expand=True)
    top = ttk.Frame(col)
    top.pack(anchor="w")
    ttk.Spinbox(
        top,
        from_=minimum,
        to=maximum,
        textvariable=variable,
        width=7,
    ).pack(side="left")
    vh = tk.StringVar()

    def refresh(*_args: object) -> None:
        try:
            value = max(minimum, min(maximum, int(variable.get())))
        except (tk.TclError, TypeError, ValueError):
            value = minimum
        vh.set(f"{value * 100}vh")

    variable.trace_add("write", refresh)
    refresh()
    ttk.Label(top, textvariable=vh, foreground="#666").pack(side="left", padx=(8, 0))
    if hint:
        ttk.Label(col, text=hint, foreground="#777", wraplength=560).pack(
            anchor="w", pady=(3, 0)
        )


def _update_tree_summary(tree: ttk.Treeview, stable_id: str) -> None:
    if not tree.exists(stable_id):
        return
    item = flow_item_by_id(active_variant_id(), stable_id)
    if item is None:
        return
    summary = phase_summary(stable_id)
    suffix = f"  ·  {summary}" if summary else ""
    tree.item(stable_id, text=f"↳ {item.code}  {item.display_name}{suffix}")


def _render_phase(
    host: tk.Misc,
    tree: ttk.Treeview,
    stable_id: str,
) -> None:
    if stable_id not in KNOWN_PHASE_IDS:
        return
    right, editor, canvas = _find_editor(host)
    if right is None or editor is None:
        return

    variant_id = active_variant_id()
    item = flow_item_by_id(variant_id, stable_id)
    title = item.display_name if item is not None else PHASE_LABELS.get(stable_id, stable_id)
    code = item.code if item is not None else ""
    values = effective_phase_config(variant_id, stable_id)

    _clear(editor)
    right.configure(text=f"Edycja fazy — {code} {title}".strip())
    if canvas is not None:
        canvas.yview_moveto(0)

    ttk.Label(editor, text=f"{code}  {title}", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(
        editor,
        text=(
            f"ID techniczne: {stable_id} · wariant: {variant_label(variant_id)}\n"
            "Ustawienia fazy zapisujesz poniżej. Główny „Zapisz” zastosuje je do motywu."
        ),
        foreground="#666",
        wraplength=680,
    ).pack(anchor="w", pady=(3, 14))

    form = ttk.Frame(editor)
    form.pack(fill="both", expand=True)
    vars_: dict[str, Any] = {}

    if stable_id == PORTAL_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        _add_check(form, "Pokaż animowany tekst w portalu", vars_["enabled"])
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 2)))
        _add_screens(
            form,
            "Długość portalu",
            vars_["screens"],
            minimum=1,
            maximum=10,
            hint="Określa, ile przed końcem scrubbingu rozpoczyna się portal.",
        )
        ttk.Label(form, text="Tekst portalu:").pack(anchor="w")
        text = tk.Text(form, wrap="word", height=9, font=("", 10))
        text.insert("1.0", str(values.get("text") or ""))
        text.pack(fill="both", expand=True, pady=(4, 0))
        vars_["text"] = text
        ttk.Label(
            form,
            text="Każda niepusta linia jest animowana osobno; maksymalnie 5 linii.",
            foreground="#777",
        ).pack(anchor="w", pady=(4, 0))

    elif stable_id == HERO_RISE_ID:
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_screens(
            form,
            "Długość wjazdu Hero",
            vars_["screens"],
            minimum=1,
            maximum=5,
            hint="Faza obowiązkowa dla obecnej architektury.",
        )

    elif stable_id == HERO_HOLD_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        _add_check(form, "Włącz pusty scroll po wycentrowaniu Hero", vars_["enabled"])
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_screens(
            form,
            "Długość postoju Hero",
            vars_["screens"],
            minimum=0,
            maximum=5,
            hint="Po wyłączeniu generator zapisze 0vh.",
        )

    elif stable_id == SOUND_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        _add_check(form, "Pokaż pytanie o uruchomienie dźwięku", vars_["enabled"])
        vars_["question"] = tk.StringVar(value=str(values.get("question") or ""))
        _add_entry(form, "Pytanie", vars_["question"])
        vars_["toggle_label"] = tk.StringVar(value=str(values.get("toggle_label") or ""))
        _add_entry(form, "Etykieta przełącznika", vars_["toggle_label"])
        vars_["start_label"] = tk.StringVar(value=str(values.get("start_label") or ""))
        _add_entry(form, "Przycisk rozpoczęcia", vars_["start_label"])
        vars_["audio_url"] = tk.StringVar(value=str(values.get("audio_url") or ""))
        _add_entry(
            form,
            "URL ambientu CDN",
            vars_["audio_url"],
            hint="Plik jest odtwarzany w pętli po świadomej zgodzie użytkownika.",
        )

        row = ttk.Frame(form)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Głośność ambientu:", width=30).pack(side="left")
        col = ttk.Frame(row)
        col.pack(side="left", fill="x", expand=True)
        vars_["volume"] = tk.IntVar(value=int(values.get("volume", 28)))
        volume_text = tk.StringVar(value=f"{vars_['volume'].get()}%")
        ttk.Scale(
            col,
            from_=0,
            to=100,
            orient="horizontal",
            variable=vars_["volume"],
            command=lambda _value: volume_text.set(f"{int(vars_['volume'].get())}%"),
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(col, textvariable=volume_text, width=6).pack(side="left", padx=(8, 0))

        vars_["auto_muted_fraction"] = tk.IntVar(
            value=int(values.get("auto_muted_fraction", 35))
        )
        _add_screens(
            form,
            "Autostart wyciszony po (%)",
            vars_["auto_muted_fraction"],
            minimum=0,
            maximum=100,
            hint="Procent wykorzystanego postoju Hero; wartość jest procentem, nie vh.",
        )

    elif stable_id == CURTAIN_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        _add_check(form, "Włącz poziomą kurtynę Hero → Giclée Art", vars_["enabled"])
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_screens(
            form,
            "Długość otwierania kurtyny",
            vars_["screens"],
            minimum=1,
            maximum=5,
        )

    elif stable_id == INTRO_HOLD_ID:
        vars_["enabled"] = tk.BooleanVar(value=bool(values.get("enabled", True)))
        _add_check(
            form,
            "Włącz pusty scroll na odsłoniętej sekcji Giclée Art",
            vars_["enabled"],
        )
        vars_["screens"] = tk.IntVar(value=int(values.get("screens", 1)))
        _add_screens(
            form,
            "Długość postoju sekcji",
            vars_["screens"],
            minimum=0,
            maximum=5,
        )

    status = tk.StringVar(value="")
    ttk.Label(editor, textvariable=status, foreground="#666", wraplength=680).pack(
        anchor="w", pady=(12, 0)
    )

    def collect() -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, variable in vars_.items():
            if isinstance(variable, tk.Text):
                result[key] = variable.get("1.0", "end-1c")
            else:
                result[key] = variable.get()
        return result

    def save() -> None:
        try:
            set_phase_config(variant_id, stable_id, collect())
        except (ValueError, OSError, tk.TclError) as exc:
            messagebox.showerror("GICLÉE HOME FLOW", str(exc), parent=host.winfo_toplevel())
            return
        _update_tree_summary(tree, stable_id)
        status.set("Zapisano fazę dla wariantu. Główny „Zapisz” zastosuje ją do podglądu motywu.")

    def restore() -> None:
        if not messagebox.askyesno(
            "GICLÉE HOME FLOW",
            "Przywrócić ustawienia tej fazy z bieżącego wariantu?",
            parent=host.winfo_toplevel(),
        ):
            return
        reset_phase_config(variant_id, stable_id)
        _update_tree_summary(tree, stable_id)
        _render_phase(host, tree, stable_id)

    controls = ttk.Frame(editor)
    controls.pack(fill="x", pady=(14, 0))
    ttk.Button(controls, text="Przywróć z wariantu", command=restore).pack(side="left")
    ttk.Button(controls, text="Zapisz fazę", command=save).pack(side="right")


def _decorate_inline_editor(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    if tree is None or getattr(tree, "_giclee_inline_phase_editor", False):
        return
    tree._giclee_inline_phase_editor = True  # type: ignore[attr-defined]

    # Dwuklik nie otwiera już osobnego okna w głównej nawigacji.
    tree.unbind("<Double-1>")

    def on_select(_event=None) -> None:
        selected = tree.selection()
        stable_id = str(selected[0]) if selected else ""
        if stable_id in KNOWN_PHASE_IDS:
            host.after_idle(
                lambda sid=stable_id: (
                    _render_phase(host, tree, sid)
                    if tree.selection() and str(tree.selection()[0]) == sid
                    else None
                )
            )
            return

        def restore_section_title() -> None:
            right, _editor, _canvas = _find_editor(host)
            item = flow_item_by_id(active_variant_id(), stable_id) if stable_id else None
            if right is not None:
                if item is not None:
                    right.configure(text=f"Edycja sekcji — {item.code} {item.display_name}")
                else:
                    right.configure(text="Edycja sekcji")

        host.after_idle(restore_section_title)

    tree.bind("<<TreeviewSelect>>", on_select, add="+")


def install_home_flow_phase_inline() -> None:
    current = base_gui._decorate_home_editor
    if getattr(current, "_giclee_inline_phase_editor", False):
        return

    def decorate_with_inline_phases(host: tk.Misc) -> None:
        current(host)
        host.after_idle(lambda: _decorate_inline_editor(host))

    setattr(decorate_with_inline_phases, "_giclee_inline_phase_editor", True)
    setattr(decorate_with_inline_phases, "__wrapped__", current)
    base_gui._decorate_home_editor = decorate_with_inline_phases
