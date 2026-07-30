"""Wspólne GUI listy i edycji warstw tekstowych."""

from __future__ import annotations

import copy
import json
import tkinter as tk
import uuid
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from typing import Any, Callable

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .text_code_importer import adapt_code
from .text_layers import (
    ALIGNMENTS,
    ANCHORS,
    CONTENT_KINDS,
    EASINGS,
    ENTER_PRESETS,
    EXIT_PRESETS,
    layers_for_section,
    load_motion_preset_library,
    new_layer,
    normalize_layer,
    save_motion_preset_library,
    set_section_layers,
)

_KIND_LABELS = {
    "h1": "Nagłówek H1",
    "h2": "Nagłówek H2",
    "h3": "Nagłówek H3",
    "paragraph": "Akapit",
    "subtitle": "Podtytuł",
    "eyebrow": "Etykieta / eyebrow",
    "quote": "Cytat",
    "signature": "Podpis",
}
_MODE_LABELS = {"flow": "W normalnym układzie", "absolute": "Absolutnie wewnątrz sekcji"}
_ANCHOR_LABELS = {
    "top-left": "Lewy górny",
    "top-center": "Środkowy górny",
    "top-right": "Prawy górny",
    "center-left": "Lewy środkowy",
    "center": "Środek",
    "center-right": "Prawy środkowy",
    "bottom-left": "Lewy dolny",
    "bottom-center": "Środkowy dolny",
    "bottom-right": "Prawy dolny",
}
_ALIGN_LABELS = {"left": "Do lewej", "center": "Do środka", "right": "Do prawej"}
_ENTER_LABELS = {
    "none": "Brak",
    "fade": "Fade",
    "fade-up": "Fade Up",
    "fade-down": "Fade Down",
    "slide-left": "Slide Left",
    "slide-right": "Slide Right",
    "soft-blur-reveal": "Soft Blur Reveal",
    "gentle-scale-in": "Gentle Scale In",
    "mask-reveal": "Mask Reveal",
    "letter-spacing-reveal": "Letter Spacing Reveal",
}
_EXIT_LABELS = {
    "none": "Brak",
    "fade-out": "Fade Out",
    "fade-up-out": "Fade Up Out",
    "fade-down-out": "Fade Down Out",
    "slide-left-out": "Slide Left Out",
    "slide-right-out": "Slide Right Out",
    "blur-away": "Blur Away",
    "gentle-scale-out": "Gentle Scale Out",
    "mask-close": "Mask Close",
}
_EASING_LABELS = {
    "museum": "Muzealny",
    "soft": "Miękki",
    "crisp": "Dynamiczny",
    "linear": "Linear",
}


def _label_map_combo(
    parent: tk.Misc,
    *,
    variable: tk.StringVar,
    mapping: dict[str, str],
    width: int = 30,
) -> ttk.Combobox:
    label_to_value = {label: value for value, label in mapping.items()}
    value_to_label = dict(mapping)
    display = tk.StringVar(value=value_to_label.get(variable.get(), variable.get()))
    combo = ttk.Combobox(
        parent,
        textvariable=display,
        values=tuple(label_to_value),
        state="readonly",
        width=width,
    )

    def from_display(*_args: object) -> None:
        variable.set(label_to_value.get(display.get(), display.get()))

    def to_display(*_args: object) -> None:
        label = value_to_label.get(variable.get(), variable.get())
        if display.get() != label:
            display.set(label)

    display.trace_add("write", from_display)
    variable.trace_add("write", to_display)
    return combo


def _entry_row(
    parent: tk.Misc,
    row: int,
    label: str,
    variable: tk.Variable,
    *,
    width: int = 14,
    unit_values: tuple[str, ...] | None = None,
    unit_var: tk.StringVar | None = None,
) -> None:
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
    ttk.Entry(parent, textvariable=variable, width=width).grid(
        row=row, column=1, sticky="w", padx=(10, 4), pady=4
    )
    if unit_values and unit_var is not None:
        ttk.Combobox(
            parent,
            textvariable=unit_var,
            values=unit_values,
            state="readonly",
            width=5,
        ).grid(row=row, column=2, sticky="w", pady=4)


def _open_code_dialog(
    owner: tk.Misc,
    *,
    app_title: str,
    layer_id: str,
    on_apply: Callable[[dict[str, Any]], None],
) -> None:
    dialog = tk.Toplevel(owner)
    dialog.title("Wstaw kod — bezpieczna adaptacja")
    dialog.transient(owner)
    dialog.grab_set()
    position_toplevel_screen_center(dialog, 980, 720)

    ttk.Label(
        dialog,
        text=(
            "Wklej cały komponent HTML + CSS + JS. Zachowamy jego układ, "
            "dekoracje, SVG, obrazy/media, pseudo-elementy i reguły "
            "responsywne. JavaScript nie zostanie wykonany; rozpoznaną "
            "animację widoczności przejmie bezpieczny runtime GicleeApp. "
            "CSS zostanie ograniczony wyłącznie do tej warstwy."
        ),
        wraplength=920,
        padding=(12, 10),
    ).pack(anchor="w")
    source = scrolledtext.ScrolledText(dialog, wrap="none", font=("Consolas", 9))
    source.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    report = scrolledtext.ScrolledText(dialog, height=8, wrap="word", font=("", 9))
    report.pack(fill="x", padx=12, pady=(0, 8))
    report.insert("1.0", "Raport pojawi się po kliknięciu „Analizuj”.")
    report.configure(state="disabled")
    result: dict[str, Any] = {}

    def analyze() -> None:
        nonlocal result
        result = adapt_code(source.get("1.0", "end-1c"), layer_id=layer_id)
        report.configure(state="normal")
        report.delete("1.0", "end")
        report.insert(
            "1.0",
            "\n".join(f"• {line}" for line in result.get("report", []))
            + f"\n\nTreść po adaptacji: {result.get('plainText', '')[:500]}",
        )
        report.configure(state="disabled")

    def apply_result() -> None:
        if not result:
            analyze()
        if not result.get("html"):
            messagebox.showwarning(
                app_title,
                "Po oczyszczeniu kod nie zawiera treści HTML.",
                parent=dialog,
            )
            return
        on_apply(result)
        dialog.destroy()

    buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Analizuj", command=analyze).pack(side="left")
    ttk.Button(buttons, text="Anuluj", command=dialog.destroy).pack(side="right")
    ttk.Button(buttons, text="Zastosuj do warstwy", command=apply_result).pack(
        side="right", padx=(0, 8)
    )


def _device_layout_tab(
    notebook: ttk.Notebook,
    *,
    label: str,
    values: dict[str, Any],
    override_var: tk.BooleanVar | None,
) -> dict[str, Any]:
    tab = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(tab, text=label)
    tab.columnconfigure(1, weight=1)
    if override_var is None:
        ttk.Label(tab, text="Wartości bazowe", foreground="#666").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
    else:
        ttk.Checkbutton(
            tab,
            text="Nadpisz dla tego urządzenia",
            variable=override_var,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    anchor_var = tk.StringVar(value=str(values.get("anchor") or "top-left"))
    align_var = tk.StringVar(value=str(values.get("align") or "left"))
    z_var = tk.StringVar(value=str(values.get("zIndex", 20)))
    x_var = tk.StringVar(value=str((values.get("offsetX") or {}).get("value", 0)))
    x_unit = tk.StringVar(value=str((values.get("offsetX") or {}).get("unit", "px")))
    y_var = tk.StringVar(value=str((values.get("offsetY") or {}).get("value", 0)))
    y_unit = tk.StringVar(value=str((values.get("offsetY") or {}).get("unit", "px")))
    width_var = tk.StringVar(value=str((values.get("maxWidth") or {}).get("value", 720)))
    width_unit = tk.StringVar(value=str((values.get("maxWidth") or {}).get("unit", "px")))
    padding_var = tk.StringVar(value=str((values.get("padding") or {}).get("value", 0)))
    padding_unit = tk.StringVar(value=str((values.get("padding") or {}).get("unit", "px")))

    ttk.Label(tab, text="Kotwica 3 × 3").grid(row=1, column=0, sticky="w", pady=4)
    _label_map_combo(tab, variable=anchor_var, mapping=_ANCHOR_LABELS).grid(
        row=1, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=4
    )
    _entry_row(tab, 2, "Przesunięcie X", x_var, unit_values=("px", "%", "vw", "vh"), unit_var=x_unit)
    _entry_row(tab, 3, "Przesunięcie Y", y_var, unit_values=("px", "%", "vw", "vh"), unit_var=y_unit)
    _entry_row(tab, 4, "Maksymalna szerokość", width_var, unit_values=("px", "%", "vw"), unit_var=width_unit)
    ttk.Label(tab, text="Wyrównanie tekstu").grid(row=5, column=0, sticky="w", pady=4)
    _label_map_combo(tab, variable=align_var, mapping=_ALIGN_LABELS).grid(
        row=5, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=4
    )
    _entry_row(tab, 6, "Kolejność warstwy (z-index)", z_var)
    _entry_row(tab, 7, "Margines wewnętrzny", padding_var, unit_values=("px", "%", "vw", "vh"), unit_var=padding_unit)

    controls = [
        child
        for child in tab.winfo_children()
        if not isinstance(child, ttk.Checkbutton)
    ]

    def sync_state(*_args: object) -> None:
        enabled = override_var is None or bool(override_var.get())
        for child in controls:
            try:
                if isinstance(child, ttk.Combobox):
                    child.configure(state="readonly" if enabled else "disabled")
                else:
                    child.configure(state="normal" if enabled else "disabled")
            except tk.TclError:
                pass

    if override_var is not None:
        override_var.trace_add("write", sync_state)
    sync_state()
    return {
        "override": override_var,
        "anchor": anchor_var,
        "align": align_var,
        "zIndex": z_var,
        "offsetX": (x_var, x_unit),
        "offsetY": (y_var, y_unit),
        "maxWidth": (width_var, width_unit),
        "padding": (padding_var, padding_unit),
    }


def _collect_device_controls(controls: dict[str, Any]) -> dict[str, Any] | None:
    override = controls.get("override")
    if override is not None and not override.get():
        return None

    def number_unit(pair: tuple[tk.StringVar, tk.StringVar]) -> dict[str, Any]:
        value, unit = pair
        return {"value": value.get(), "unit": unit.get()}

    return {
        "anchor": controls["anchor"].get(),
        "align": controls["align"].get(),
        "zIndex": controls["zIndex"].get(),
        "offsetX": number_unit(controls["offsetX"]),
        "offsetY": number_unit(controls["offsetY"]),
        "maxWidth": number_unit(controls["maxWidth"]),
        "padding": number_unit(controls["padding"]),
    }


def _motion_editor(
    parent: tk.Misc,
    *,
    title: str,
    values: dict[str, Any],
    enter: bool,
) -> dict[str, Any]:
    frame = ttk.LabelFrame(parent, text=title, padding=(10, 8))
    frame.pack(fill="x", pady=(0, 10))
    frame.columnconfigure(1, weight=1)
    labels = _ENTER_LABELS if enter else _EXIT_LABELS
    preset_var = tk.StringVar(value=str(values.get("preset") or "none"))
    easing_var = tk.StringVar(value=str(values.get("easing") or "museum"))
    duration_var = tk.StringVar(value=str(values.get("duration", 0.8 if enter else 0.6)))
    distance_var = tk.StringVar(value=str(values.get("distance", 32)))
    blur_var = tk.StringVar(value=str(values.get("blur", 12)))
    intensity_var = tk.StringVar(value=str(values.get("intensity", 1)))

    ttk.Label(frame, text="Preset").grid(row=0, column=0, sticky="w", pady=3)
    _label_map_combo(frame, variable=preset_var, mapping=labels, width=28).grid(
        row=0, column=1, sticky="w", padx=(10, 0), pady=3
    )
    _entry_row(frame, 1, "Długość animacji (s)", duration_var)
    ttk.Label(frame, text="Easing").grid(row=2, column=0, sticky="w", pady=3)
    _label_map_combo(frame, variable=easing_var, mapping=_EASING_LABELS, width=20).grid(
        row=2, column=1, sticky="w", padx=(10, 0), pady=3
    )
    _entry_row(frame, 3, "Dystans (px)", distance_var)
    _entry_row(frame, 4, "Blur (px)", blur_var)
    _entry_row(frame, 5, "Intensywność (0–2)", intensity_var)

    extra: dict[str, Any] = {}
    row = 6
    if enter:
        delay_var = tk.StringVar(value=str(values.get("delay", 0)))
        stagger_var = tk.StringVar(value=str(values.get("stagger", 0.04)))
        stagger_mode_var = tk.StringVar(value=str(values.get("staggerMode") or "none"))
        _entry_row(frame, row, "Opóźnienie (s)", delay_var)
        row += 1
        _entry_row(frame, row, "Stagger (s)", stagger_var)
        row += 1
        ttk.Label(frame, text="Stagger dla").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Combobox(
            frame,
            textvariable=stagger_mode_var,
            values=("none", "words", "characters"),
            state="readonly",
            width=18,
        ).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=3)
        extra = {"delay": delay_var, "stagger": stagger_var, "staggerMode": stagger_mode_var}
    else:
        start_var = tk.StringVar(value=str(values.get("startPct", 80)))
        _entry_row(frame, row, "Początek wyjścia (%)", start_var)
        extra = {"startPct": start_var}

    library = load_motion_preset_library()
    kind = "enter" if enter else "exit"
    custom_rows = library.get(kind, [])
    custom_names = [str(row["name"]) for row in custom_rows]
    custom_var = tk.StringVar()
    preset_row = ttk.Frame(frame)
    preset_row.grid(row=row + 2, column=0, columnspan=3, sticky="ew", pady=(8, 0))
    custom_combo = ttk.Combobox(
        preset_row,
        textvariable=custom_var,
        values=custom_names,
        state="readonly" if custom_names else "disabled",
        width=28,
    )
    custom_combo.pack(side="left")

    controls = {
        "preset": preset_var,
        "duration": duration_var,
        "easing": easing_var,
        "distance": distance_var,
        "blur": blur_var,
        "intensity": intensity_var,
        **extra,
    }

    def snapshot() -> dict[str, Any]:
        return {
            key: variable.get()
            for key, variable in controls.items()
        }

    def apply_values(raw: dict[str, Any]) -> None:
        for key, variable in controls.items():
            if key in raw:
                variable.set(str(raw[key]))

    def apply_custom(_event: object = None) -> None:
        chosen = next(
            (row for row in load_motion_preset_library().get(kind, []) if row["name"] == custom_var.get()),
            None,
        )
        if chosen:
            apply_values(chosen["values"])

    custom_combo.bind("<<ComboboxSelected>>", apply_custom)

    def save_custom() -> None:
        name = simpledialog.askstring(
            "Preset animacji",
            "Nazwa własnego presetu:",
            parent=parent.winfo_toplevel(),
        )
        if not name or not name.strip():
            return
        store = load_motion_preset_library()
        rows = store.setdefault(kind, [])
        if any(str(row.get("name", "")).casefold() == name.strip().casefold() for row in rows):
            messagebox.showerror("Preset animacji", "Preset o tej nazwie już istnieje.", parent=parent)
            return
        rows.append({"id": uuid.uuid4().hex, "name": name.strip(), "values": snapshot()})
        save_motion_preset_library(store)
        custom_var.set(name.strip())
        custom_combo.configure(
            values=[row["name"] for row in store[kind]],
            state="readonly",
        )

    def delete_custom() -> None:
        name = custom_var.get()
        if not name:
            return
        store = load_motion_preset_library()
        store[kind] = [row for row in store.get(kind, []) if row.get("name") != name]
        save_motion_preset_library(store)
        custom_var.set("")
        names = [row["name"] for row in store[kind]]
        custom_combo.configure(values=names, state="readonly" if names else "disabled")

    ttk.Button(preset_row, text="Zapisz jako własny…", command=save_custom).pack(
        side="left", padx=(6, 0)
    )
    ttk.Button(preset_row, text="Usuń własny", command=delete_custom).pack(
        side="left", padx=(6, 0)
    )
    return controls


def _collect_motion(controls: dict[str, Any]) -> dict[str, Any]:
    return {key: variable.get() for key, variable in controls.items()}


def open_text_layer_dialog(
    owner: tk.Misc,
    *,
    layer: dict[str, Any],
    app_title: str,
) -> dict[str, Any] | None:
    working = copy.deepcopy(layer)
    dialog = tk.Toplevel(owner)
    dialog.title(f"Tekst — {working.get('name', 'warstwa')}")
    dialog.transient(owner)
    dialog.grab_set()
    position_toplevel_screen_center(dialog, 980, 790)

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=12, pady=(12, 8))

    # Treść
    content_tab = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(content_tab, text="Treść")
    content_tab.columnconfigure(1, weight=1)
    name_var = tk.StringVar(value=str(working.get("name") or "Tekst"))
    enabled_var = tk.BooleanVar(value=bool(working.get("enabled", True)))
    kind_var = tk.StringVar(value=str(working["content"].get("kind") or "paragraph"))
    ttk.Label(content_tab, text="Nazwa warstwy").grid(row=0, column=0, sticky="w", pady=4)
    ttk.Entry(content_tab, textvariable=name_var, width=54).grid(
        row=0, column=1, sticky="ew", padx=(10, 0), pady=4
    )
    ttk.Checkbutton(content_tab, text="Warstwa widoczna", variable=enabled_var).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=4
    )
    ttk.Label(content_tab, text="Rodzaj tekstu").grid(row=2, column=0, sticky="w", pady=4)
    _label_map_combo(content_tab, variable=kind_var, mapping=_KIND_LABELS).grid(
        row=2, column=1, sticky="w", padx=(10, 0), pady=4
    )
    ttk.Label(content_tab, text="Treść").grid(row=3, column=0, sticky="nw", pady=(8, 4))
    text_box = scrolledtext.ScrolledText(content_tab, height=14, wrap="word")
    text_box.grid(row=3, column=1, sticky="nsew", padx=(10, 0), pady=(8, 4))
    text_box.insert("1.0", str(working["content"].get("text") or ""))
    content_tab.rowconfigure(3, weight=1)
    code_status = tk.StringVar(
        value=(
            "Tryb: pełny komponent HTML/CSS"
            if (
                working["content"].get("mode") == "adapted-code"
                and working.get("importedStyle", {}).get("componentMode")
            )
            else "Tryb: zaadaptowany kod"
            if working["content"].get("mode") == "adapted-code"
            else "Tryb: zwykły tekst"
        )
    )
    code_row = ttk.Frame(content_tab)
    code_row.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=(6, 0))
    ttk.Label(code_row, textvariable=code_status, foreground="#666").pack(side="left")

    def apply_import(result: dict[str, Any]) -> None:
        working["content"]["mode"] = "adapted-code"
        working["content"]["html"] = str(result.get("html") or "")
        working["content"]["text"] = str(result.get("plainText") or "")
        working["importedStyle"]["scopedCss"] = str(result.get("scopedCss") or "")
        working["importedStyle"]["fontUrls"] = list(result.get("fontUrls") or [])
        working["importedStyle"]["componentMode"] = bool(
            result.get("componentMode", True)
        )
        working["importedStyle"]["ownsMotion"] = bool(
            result.get("ownsMotion", False)
        )
        working["importedStyle"]["behavior"] = dict(
            result.get("behavior") or {}
        )
        working["motion"]["enter"]["preset"] = str(
            result.get("suggestedEnterPreset") or "fade-up"
        )
        text_box.delete("1.0", "end")
        text_box.insert("1.0", working["content"]["text"])
        code_status.set("Tryb: pełny komponent HTML/CSS")

    ttk.Button(
        code_row,
        text="Wstaw kod…",
        command=lambda: _open_code_dialog(
            dialog,
            app_title=app_title,
            layer_id=str(working["id"]),
            on_apply=apply_import,
        ),
    ).pack(side="right")

    def clear_imported() -> None:
        working["content"]["mode"] = "plain"
        working["content"]["html"] = ""
        working["importedStyle"] = {
            "scopedCss": "",
            "fontUrls": [],
            "componentMode": False,
            "ownsMotion": False,
            "behavior": {
                "trigger": "section-progress",
                "threshold": 0.08,
                "rootMargin": "0px",
                "once": False,
            },
        }
        code_status.set("Tryb: zwykły tekst")

    ttk.Button(code_row, text="Usuń styl z kodu", command=clear_imported).pack(
        side="right", padx=(0, 6)
    )

    # Pozycjonowanie
    layout_tab = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(layout_tab, text="Pozycjonowanie")
    mode_var = tk.StringVar(value=str(working["layout"].get("mode") or "flow"))
    mode_row = ttk.Frame(layout_tab)
    mode_row.pack(fill="x", pady=(0, 8))
    ttk.Label(mode_row, text="Sposób pozycjonowania").pack(side="left")
    _label_map_combo(mode_row, variable=mode_var, mapping=_MODE_LABELS, width=34).pack(
        side="left", padx=(10, 0)
    )
    device_tabs = ttk.Notebook(layout_tab)
    device_tabs.pack(fill="both", expand=True)
    desktop_controls = _device_layout_tab(
        device_tabs,
        label="Desktop — bazowe",
        values=working["layout"]["desktop"],
        override_var=None,
    )
    tablet_override = tk.BooleanVar(value=isinstance(working["layout"].get("tablet"), dict))
    tablet_controls = _device_layout_tab(
        device_tabs,
        label="Tablet",
        values=working["layout"].get("tablet") or working["layout"]["desktop"],
        override_var=tablet_override,
    )
    mobile_override = tk.BooleanVar(value=isinstance(working["layout"].get("mobile"), dict))
    mobile_controls = _device_layout_tab(
        device_tabs,
        label="Mobile",
        values=(
            working["layout"].get("mobile")
            or working["layout"].get("tablet")
            or working["layout"]["desktop"]
        ),
        override_var=mobile_override,
    )

    # Ruch
    motion_tab = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(motion_tab, text="Animacje")
    motion_canvas = tk.Canvas(motion_tab, highlightthickness=0)
    motion_scroll = ttk.Scrollbar(motion_tab, orient="vertical", command=motion_canvas.yview)
    motion_canvas.configure(yscrollcommand=motion_scroll.set)
    motion_scroll.pack(side="right", fill="y")
    motion_canvas.pack(side="left", fill="both", expand=True)
    motion_inner = ttk.Frame(motion_canvas)
    motion_window = motion_canvas.create_window((0, 0), window=motion_inner, anchor="nw")
    motion_inner.bind(
        "<Configure>",
        lambda _event: motion_canvas.configure(scrollregion=motion_canvas.bbox("all")),
    )
    motion_canvas.bind(
        "<Configure>",
        lambda event: motion_canvas.itemconfigure(motion_window, width=event.width),
    )
    enter_controls = _motion_editor(
        motion_inner,
        title="Animacja wejścia",
        values=working["motion"]["enter"],
        enter=True,
    )
    exit_controls = _motion_editor(
        motion_inner,
        title="Animacja wyjścia",
        values=working["motion"]["exit"],
        enter=False,
    )

    # Pin
    pin_tab = ttk.Frame(notebook, padding=(12, 10))
    notebook.add(pin_tab, text="Przypięcie")
    desktop_pin = working["pin"]["desktop"]
    mobile_pin = working["pin"]["mobile"]
    pin_enabled = tk.BooleanVar(value=bool(desktop_pin.get("enabled")))
    duration_var = tk.StringVar(value=str(desktop_pin.get("durationVh", 100)))
    top_var = tk.StringVar(value=str((desktop_pin.get("top") or {}).get("value", 0)))
    top_unit = tk.StringVar(value=str((desktop_pin.get("top") or {}).get("unit", "px")))
    start_var = tk.StringVar(value=str(desktop_pin.get("startVh", 0)))
    end_var = tk.StringVar(
        value="" if desktop_pin.get("endVh") is None else str(desktop_pin.get("endVh"))
    )
    ttk.Checkbutton(
        pin_tab,
        text="Przypnij treść podczas przewijania",
        variable=pin_enabled,
    ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
    _entry_row(pin_tab, 1, "Długość przypięcia", duration_var, unit_values=("vh",), unit_var=tk.StringVar(value="vh"))
    _entry_row(pin_tab, 2, "Pozycja od góry", top_var, unit_values=("px", "vh"), unit_var=top_unit)
    _entry_row(pin_tab, 3, "Początek przypięcia", start_var, unit_values=("vh",), unit_var=tk.StringVar(value="vh"))
    _entry_row(pin_tab, 4, "Zakończenie (opcjonalne)", end_var, unit_values=("vh",), unit_var=tk.StringVar(value="vh"))
    ttk.Label(
        pin_tab,
        text=(
            "Długość oznacza dystans przewijania. Zakończenie pozostaw puste, "
            "aby było wyliczane jako początek + długość."
        ),
        foreground="#666",
        wraplength=650,
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 14))
    mobile_mode_var = tk.StringVar(value=str(mobile_pin.get("mode") or "inherit"))
    mobile_duration = tk.StringVar(value=str(mobile_pin.get("durationVh", 0)))
    mobile_top = tk.StringVar(value=str((mobile_pin.get("top") or {}).get("value", 0)))
    mobile_top_unit = tk.StringVar(value=str((mobile_pin.get("top") or {}).get("unit", "px")))
    ttk.Separator(pin_tab).grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 12))
    ttk.Label(pin_tab, text="Mobile").grid(row=7, column=0, sticky="w", pady=4)
    ttk.Combobox(
        pin_tab,
        textvariable=mobile_mode_var,
        values=("inherit", "on", "off", "custom"),
        state="readonly",
        width=18,
    ).grid(row=7, column=1, sticky="w", padx=(10, 0), pady=4)
    _entry_row(pin_tab, 8, "Własna długość mobile", mobile_duration, unit_values=("vh",), unit_var=tk.StringVar(value="vh"))
    _entry_row(pin_tab, 9, "Pozycja mobile od góry", mobile_top, unit_values=("px", "vh"), unit_var=mobile_top_unit)

    result: dict[str, Any] = {"layer": None}

    def save() -> None:
        working["name"] = name_var.get().strip()
        working["enabled"] = enabled_var.get()
        working["content"]["kind"] = kind_var.get()
        working["content"]["text"] = text_box.get("1.0", "end-1c")
        if working["content"].get("mode") != "adapted-code":
            working["content"]["html"] = ""
        working["layout"] = {
            "mode": mode_var.get(),
            "desktop": _collect_device_controls(desktop_controls),
            "tablet": _collect_device_controls(tablet_controls),
            "mobile": _collect_device_controls(mobile_controls),
        }
        working["motion"] = {
            "enter": _collect_motion(enter_controls),
            "exit": _collect_motion(exit_controls),
        }
        working["pin"] = {
            "desktop": {
                "enabled": pin_enabled.get(),
                "durationVh": duration_var.get(),
                "top": {"value": top_var.get(), "unit": top_unit.get()},
                "startVh": start_var.get(),
                "endVh": end_var.get().strip() or None,
            },
            "mobile": {
                "mode": mobile_mode_var.get(),
                "durationVh": mobile_duration.get(),
                "top": {"value": mobile_top.get(), "unit": mobile_top_unit.get()},
            },
        }
        normalized = normalize_layer(working)
        if normalized is None:
            messagebox.showerror(app_title, "Nie udało się znormalizować warstwy.", parent=dialog)
            return
        if not normalized["name"]:
            messagebox.showerror(app_title, "Nazwa warstwy nie może być pusta.", parent=dialog)
            return
        desktop = normalized["pin"]["desktop"]
        if desktop["endVh"] is not None and desktop["endVh"] < desktop["startVh"]:
            messagebox.showerror(
                app_title,
                "Zakończenie przypięcia nie może być przed początkiem.",
                parent=dialog,
            )
            return
        enter_cfg = normalized["motion"]["enter"]
        exit_cfg = normalized["motion"]["exit"]
        if (
            enter_cfg["preset"] != "none"
            and exit_cfg["preset"] != "none"
            and exit_cfg["startPct"] <= 20
            and not messagebox.askyesno(
                app_title,
                "Animacja wyjścia zaczyna się bardzo wcześnie i może przykryć wejście. Zapisać mimo to?",
                parent=dialog,
            )
        ):
            return
        result["layer"] = normalized
        dialog.destroy()

    buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    buttons.pack(fill="x")
    ttk.Button(buttons, text="Anuluj", command=dialog.destroy).pack(side="right")
    ttk.Button(buttons, text="Zapisz warstwę", command=save).pack(
        side="right", padx=(0, 8)
    )
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    owner.wait_window(dialog)
    return result["layer"]


def build_text_layers_panel(
    parent: tk.Misc,
    *,
    document_getter: Callable[[], dict[str, Any]],
    document_setter: Callable[[dict[str, Any]], None],
    section_key: str,
    app_title: str,
    can_render: bool = True,
) -> ttk.LabelFrame:
    panel = ttk.LabelFrame(parent, text="Teksty w sekcji", padding=(8, 8))
    if not can_render:
        ttk.Label(
            panel,
            text="Ta pozycja jest ustawieniem globalnym i nie ma elementu na stronie.",
            foreground="#777",
            wraplength=520,
        ).pack(anchor="w")
        return panel

    listbox = tk.Listbox(panel, height=5, exportselection=False)
    listbox.pack(fill="x")

    def rows() -> list[dict[str, Any]]:
        return layers_for_section(document_getter(), section_key)

    def refresh(select_index: int | None = None) -> None:
        current = rows()
        listbox.delete(0, "end")
        for item in current:
            suffix = "" if item.get("enabled", True) else " [wył.]"
            listbox.insert("end", f"{item['name']} — {_KIND_LABELS.get(item['content']['kind'], item['content']['kind'])}{suffix}")
        if current:
            index = min(
                select_index if select_index is not None else 0,
                len(current) - 1,
            )
            listbox.selection_set(index)
            listbox.see(index)

    def selected_index() -> int | None:
        selection = listbox.curselection()
        return int(selection[0]) if selection else None

    def commit(next_rows: list[dict[str, Any]], select: int | None = None) -> None:
        for index, item in enumerate(next_rows):
            item["order"] = index
        next_document = set_section_layers(document_getter(), section_key, next_rows)
        document_setter(next_document)
        refresh(select)

    def add_layer() -> None:
        current = rows()
        layer = new_layer(name=f"Tekst {len(current) + 1}")
        edited = open_text_layer_dialog(panel, layer=layer, app_title=app_title)
        if edited is None:
            return
        current.append(edited)
        commit(current, len(current) - 1)

    def edit_layer(_event: object = None) -> None:
        index = selected_index()
        current = rows()
        if index is None or index >= len(current):
            return
        edited = open_text_layer_dialog(
            panel,
            layer=current[index],
            app_title=app_title,
        )
        if edited is None:
            return
        current[index] = edited
        commit(current, index)

    def rename_layer() -> None:
        index = selected_index()
        current = rows()
        if index is None or index >= len(current):
            return
        name = simpledialog.askstring(
            app_title,
            "Nowa nazwa warstwy:",
            initialvalue=current[index]["name"],
            parent=panel.winfo_toplevel(),
        )
        if not name or not name.strip():
            return
        current[index]["name"] = name.strip()
        commit(current, index)

    def move(delta: int) -> None:
        index = selected_index()
        current = rows()
        if index is None:
            return
        target = index + delta
        if target < 0 or target >= len(current):
            return
        current[index], current[target] = current[target], current[index]
        commit(current, target)

    def delete_layer() -> None:
        index = selected_index()
        current = rows()
        if index is None or index >= len(current):
            return
        if not messagebox.askyesno(
            app_title,
            f"Usunąć warstwę «{current[index]['name']}»?",
            parent=panel,
        ):
            return
        del current[index]
        commit(current, max(0, index - 1) if current else None)

    buttons = ttk.Frame(panel)
    buttons.pack(fill="x", pady=(6, 0))
    ttk.Button(buttons, text="Dodaj tekst…", command=add_layer).pack(side="left")
    ttk.Button(buttons, text="Edytuj…", command=edit_layer).pack(side="left", padx=(4, 0))
    ttk.Button(buttons, text="Zmień nazwę…", command=rename_layer).pack(side="left", padx=(4, 0))
    ttk.Button(buttons, text="▲", width=3, command=lambda: move(-1)).pack(side="left", padx=(4, 0))
    ttk.Button(buttons, text="▼", width=3, command=lambda: move(1)).pack(side="left", padx=(2, 0))
    ttk.Button(buttons, text="Usuń", command=delete_layer).pack(side="right")
    listbox.bind("<Double-Button-1>", edit_layer)
    refresh()
    return panel


def add_text_layer_for_section(
    owner: tk.Misc,
    *,
    document: dict[str, Any],
    section_key: str,
    app_title: str,
) -> dict[str, Any] | None:
    current = layers_for_section(document, section_key)
    edited = open_text_layer_dialog(
        owner,
        layer=new_layer(name=f"Tekst {len(current) + 1}"),
        app_title=app_title,
    )
    if edited is None:
        return None
    current.append(edited)
    for index, item in enumerate(current):
        item["order"] = index
    return set_section_layers(document, section_key, current)


__all__ = [
    "add_text_layer_for_section",
    "build_text_layers_panel",
    "open_text_layer_dialog",
]
