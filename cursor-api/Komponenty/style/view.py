"""Inline-view komponentu Style."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from Komponenty._shared.inline_view_shell import mount_inline_view

from .service import (
    THEME_APPLY_CONFIRMATION,
    apply_button_style_plan,
    build_button_style_plan,
    load_button_style,
)

_STYLE_DESCRIPTIONS = {
    "basic": (
        "Podstawowy",
        "Aktualny system motywu. Zachowuje kolory, promienie, typografię i stany "
        "przycisków dokładnie takie, jak ustawiono je dotychczas.",
    ),
    "nocturne": (
        "Nocturne",
        "Nocna galeria: grafitowe szkło, cienka chłodna ramka, tekst uppercase, "
        "precyzyjne odstępy i subtelny biały glow na hover oraz focus.",
    ),
    "frosted": (
        "Frosted",
        "Glassmorphism: półprzezroczyste chłodne szkło, miękki blur, zaokrąglony "
        "kontur i subtelny niebiesko-fioletowy glow.",
    ),
    "light-in-motion": (
        "Light in Motion",
        "Elegancka interakcja światła: głęboka czerń, cienki złoty kontur, świetlny "
        "punkt i kinetyczne linie reagujące na hover, active oraz focus.",
    ),
}

_CHANGED_BUTTONS = (
    ("Główne CTA", "przyciski sekcji, formularzy, „Dodaj do koszyka”, Quick add i koszyk"),
    ("Drugorzędne", "przyciski „Dowiedz się więcej”, „Zobacz szczegóły”, filtry i podobne akcje"),
    ("Płatności", "niebrandowany przycisk Shopify i przycisk BLIK; logotypy operatorów pozostają bez zmian"),
    ("CTA Giclée Art", "Losuj Obraz, showcase artysty, mockup własnej fotografii i komunikat strony"),
    ("Warianty produktu", "tekstowe opcje koloru, rozmiaru, rodzaju drewna i passe-partout"),
    ("Kontrolki ikonowe", "zoom galerii produktu oraz narzędzia mockupu; minimum 44×44 px"),
)


def _draw_button_preview(canvas: tk.Canvas, style: str) -> None:
    canvas.delete("all")
    width = max(canvas.winfo_width(), 280)
    canvas.configure(
        background={
            "basic": "#F3F3F1",
            "nocturne": "#0B0D10",
            "frosted": "#10202D",
            "light-in-motion": "#070A0C",
        }[style]
    )
    x1, y1, x2, y2 = 28, 28, width - 28, 82

    if style == "basic":
        canvas.create_rectangle(x1, y1, x2, y2, fill="#111111", outline="#111111", width=1)
        canvas.create_text(
            (x1 + x2) / 2,
            55,
            text="ODKRYJ KOLEKCJĘ",
            fill="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
        )
        canvas.create_text(
            28,
            108,
            text="Obecny wygląd motywu — bez dodatkowych nadpisań",
            anchor="w",
            fill="#555555",
            font=("Segoe UI", 9),
        )
        return

    if style == "light-in-motion":
        for offset, color in ((-12, "#5D4328"), (-5, "#9C7040"), (4, "#6E4E2D")):
            canvas.create_line(
                4,
                55 + offset,
                15,
                55 + offset,
                21,
                55 + (offset // 2),
                x1,
                55,
                fill=color,
                width=1,
                smooth=True,
            )
        for spread, color in ((8, "#241B12"), (4, "#51381F")):
            canvas.create_rectangle(
                x1 - spread,
                y1 - spread,
                x2 + spread,
                y2 + spread,
                outline=color,
                width=1,
            )
        canvas.create_rectangle(x1, y1, x2, y2, fill="#090C0E", outline="#D3A866", width=1)
        canvas.create_oval(x1 - 4, 51, x1 + 4, 59, fill="#F4D39A", outline="#E5B970")
        canvas.create_text(
            (x1 + x2) / 2 - 8,
            55,
            text="ODKRYJ KOLEKCJĘ",
            fill="#F1E5D2",
            font=("Montserrat", 9, "bold"),
        )
        canvas.create_text(x2 - 24, 55, text="→", fill="#E6BE7B", font=("Segoe UI", 17))
        palette = ("#F1E5D2", "#E6C38D", "#D3A866", "#9C7040", "#070A0C")
        for index, color in enumerate(palette):
            cx = 37 + index * 24
            canvas.create_oval(cx - 7, 103, cx + 7, 117, fill=color, outline="#8E693B")
        canvas.create_text(
            164,
            110,
            text="kinetic light lines • refined gold glow",
            anchor="w",
            fill="#BCA688",
            font=("Segoe UI", 8),
        )
        return

    if style == "frosted":
        for spread, color in ((8, "#152B3A"), (5, "#254052"), (2, "#4E687A")):
            canvas.create_rectangle(
                x1 - spread,
                y1 - spread,
                x2 + spread,
                y2 + spread,
                outline=color,
                width=1,
            )
        canvas.create_rectangle(x1, y1, x2, y2, fill="#344B5B", outline="#B9E8FA", width=1)
        canvas.create_line(x1 + 2, y1 + 2, x2 - 2, y1 + 2, fill="#E8F8FF", width=1)
        canvas.create_line(x1 + 2, y2 - 1, x1 + 58, y2 - 1, fill="#7FE4F2", width=1)
        canvas.create_line(x2 - 58, y2 - 1, x2 - 2, y2 - 1, fill="#E6A9F3", width=1)
        canvas.create_text(
            (x1 + x2) / 2 - 8,
            55,
            text="ODKRYJ KOLEKCJĘ",
            fill="#F2F8FC",
            font=("Montserrat", 9, "bold"),
        )
        canvas.create_text(x2 - 24, 55, text="→", fill="#F2F8FC", font=("Segoe UI", 17))
        palette = ("#EAF8FF", "#B9E8FA", "#7FCFE8", "#9BB8E8", "#D5A8EE")
        for index, color in enumerate(palette):
            cx = 37 + index * 24
            canvas.create_oval(cx - 7, 103, cx + 7, 117, fill=color, outline="#D9F5FF")
        canvas.create_text(
            164,
            110,
            text="frosted glass • blur • soft glow",
            anchor="w",
            fill="#BFD2DF",
            font=("Segoe UI", 8),
        )
        return

    for spread, color in ((8, "#252A30"), (4, "#363C43")):
        canvas.create_rectangle(
            x1 - spread,
            y1 - spread,
            x2 + spread,
            y2 + spread,
            outline=color,
            width=1,
        )
    canvas.create_rectangle(x1, y1, x2, y2, fill="#101318", outline="#B0B3B8", width=1)
    canvas.create_line(x1 + 1, y1 + 1, x2 - 1, y1 + 1, fill="#E6E6E6", width=1)
    canvas.create_text(
        (x1 + x2) / 2 - 8,
        55,
        text="ODKRYJ KOLEKCJĘ",
        fill="#E6E6E6",
        font=("Montserrat", 10, "bold"),
    )
    canvas.create_text(x2 - 30, 55, text="→", fill="#E6E6E6", font=("Segoe UI", 18))

    palette = ("#E6E6E6", "#B0B3B8", "#6B7077", "#2A2D33", "#0B0D10")
    for index, color in enumerate(palette):
        cx = 37 + index * 26
        canvas.create_oval(cx - 7, 103, cx + 7, 117, fill=color, outline="#8A8E93")
    canvas.create_text(
        182,
        110,
        text="chłodna paleta • cienka ramka • subtelny glow",
        anchor="w",
        fill="#B0B3B8",
        font=("Segoe UI", 9),
    )


def _build_style_card(
    parent: ttk.Frame,
    *,
    style_id: str,
    variable: tk.StringVar,
    on_select: Callable[[], None],
) -> ttk.LabelFrame:
    title, description = _STYLE_DESCRIPTIONS[style_id]
    card = ttk.LabelFrame(parent, text=title, padding=12)
    ttk.Radiobutton(
        card,
        text=f"Wybierz styl „{title}”",
        value=style_id,
        variable=variable,
        command=on_select,
    ).pack(anchor="w")
    ttk.Label(
        card,
        text=description,
        foreground="#5F6368",
        wraplength=270,
        justify="left",
    ).pack(anchor="w", pady=(7, 8))
    preview = tk.Canvas(card, height=130, highlightthickness=1, highlightbackground="#B8B8B8")
    preview.pack(fill="x", expand=True)
    preview.bind("<Configure>", lambda _event, c=preview, sid=style_id: _draw_button_preview(c, sid))
    return card


def _build_przyciski_tab(tab: ttk.Frame) -> None:
    try:
        active_style = load_button_style()
        load_error = ""
    except Exception as exc:
        active_style = "basic"
        load_error = str(exc)

    selected = tk.StringVar(value=active_style)
    active = tk.StringVar(value=active_style)
    detail = tk.StringVar()
    status = tk.StringVar(
        value=(
            f"Aktywny styl: {_STYLE_DESCRIPTIONS[active_style][0]}"
            if not load_error
            else f"Nie udało się odczytać motywu: {load_error}"
        )
    )

    ttk.Label(tab, text="System przycisków", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(
        tab,
        text=(
            "Wybór działa globalnie w witrynie. „Podstawowy” zachowuje obecny wygląd, "
            "„Nocturne” tworzy nocną galerię, a „Frosted” nakłada półprzezroczysty "
            "system glassmorphism z miękkim glow. „Light in Motion” dodaje złoty kontur, "
            "świetlny punkt i kinetyczną reakcję na interakcję."
        ),
        foreground="#5F6368",
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(4, 12))

    cards = ttk.Frame(tab)
    cards.pack(fill="x")
    cards.columnconfigure(0, weight=1)
    cards.columnconfigure(1, weight=1)

    def _refresh_selection() -> None:
        style_id = selected.get()
        title, description = _STYLE_DESCRIPTIONS[style_id]
        changed = style_id != active.get()
        detail.set(
            f"{title}: {description}"
            + ("\nZmiana nie jest jeszcze zapisana w motywie." if changed else "\nTen styl jest obecnie aktywny.")
        )
        apply_button.configure(
            state="normal" if changed and not load_error else "disabled",
            text=f"Zastosuj „{title}”",
        )

    basic_card = _build_style_card(
        cards,
        style_id="basic",
        variable=selected,
        on_select=_refresh_selection,
    )
    basic_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
    nocturne_card = _build_style_card(
        cards,
        style_id="nocturne",
        variable=selected,
        on_select=_refresh_selection,
    )
    nocturne_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 5))
    frosted_card = _build_style_card(
        cards,
        style_id="frosted",
        variable=selected,
        on_select=_refresh_selection,
    )
    frosted_card.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
    light_in_motion_card = _build_style_card(
        cards,
        style_id="light-in-motion",
        variable=selected,
        on_select=_refresh_selection,
    )
    light_in_motion_card.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(5, 0))

    selected_box = ttk.LabelFrame(tab, text="Wybrany styl", padding=10)
    selected_box.pack(fill="x", pady=(12, 8))
    ttk.Label(selected_box, textvariable=detail, wraplength=880, justify="left").pack(anchor="w")

    scope = ttk.LabelFrame(tab, text="Które przyciski zmienią wygląd?", padding=10)
    scope.pack(fill="x", pady=(0, 8))
    for title, description in _CHANGED_BUTTONS:
        row = ttk.Frame(scope)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=f"• {title}", font=("Segoe UI", 9, "bold"), width=20).pack(
            side="left", anchor="n"
        )
        ttk.Label(row, text=description, foreground="#5F6368", wraplength=680).pack(
            side="left", anchor="w", fill="x", expand=True
        )
    ttk.Label(
        scope,
        text=(
            "Nie zmienia: nawigacji nagłówka, ikon konta/koszyka, akordeonów, pól formularzy, "
            "okrągłych próbek kolorów (swatch) ani przycisków operatorów płatności wymagających własnych kolorów."
        ),
        foreground="#7A4E22",
        wraplength=880,
        justify="left",
    ).pack(anchor="w", pady=(7, 0))

    actions = ttk.Frame(tab)
    actions.pack(fill="x", pady=(4, 0))
    ttk.Label(actions, textvariable=status, foreground="#4B5563").pack(side="left")

    def _apply() -> None:
        style_id = selected.get()
        title = _STYLE_DESCRIPTIONS[style_id][0]
        confirmed = messagebox.askyesno(
            "Style — przyciski",
            (
                f"Zastosować globalnie styl „{title}”?\n\n"
                "Zmiana obejmie przyciski wymienione w sekcji zakresu i zapisze kopię "
                "poprzednich ustawień motywu."
            ),
            parent=tab,
        )
        if not confirmed:
            return
        try:
            plan = build_button_style_plan(style_id)
            result = apply_button_style_plan(plan, confirmation=THEME_APPLY_CONFIRMATION)
        except Exception as exc:
            messagebox.showerror("Style — przyciski", str(exc), parent=tab)
            return

        active.set(style_id)
        status.set(
            f"Aktywny styl: {title}"
            + (" — zapisano w motywie." if result.changed else " — bez zmian.")
        )
        _refresh_selection()
        messagebox.showinfo(
            "Style — przyciski",
            (
                f"Styl „{title}” jest aktywny.\n\n"
                "Lokalny podgląd Shopify odświeży zmianę automatycznie lub po przeładowaniu strony."
            ),
            parent=tab,
        )

    apply_button = ttk.Button(actions, command=_apply)
    apply_button.pack(side="right")
    _refresh_selection()


def _build_content(body: tk.Widget) -> None:
    notebook = ttk.Notebook(body, padding=(8, 0, 8, 8))
    notebook.pack(fill="both", expand=True)

    tab_przyciski = ttk.Frame(notebook, padding=12)
    notebook.add(tab_przyciski, text="Przyciski")
    _build_przyciski_tab(tab_przyciski)


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    return mount_inline_view(
        parent,
        on_back,
        title="Style",
        build_content=_build_content,
    )
