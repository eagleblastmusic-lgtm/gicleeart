"""GUI: Karuzela — wybór Karuzela1/2 i wyglądu sekcji V1/V2/V3."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .quotes_gui import APP_TITLE as QUOTES_TITLE
from .quotes_gui import build_quotes_panel
from .service import (
    SHOWCASE_LOOK_STORAGE_KEY,
    STORAGE_KEY,
    build_preview_url,
    get_carousel_version,
    get_hover_blur,
    get_preview_url,
    get_showcase_look,
    save_karuzela_settings,
)

APP_TITLE = "Karuzela — sekcja «Wybrane dzieła»"
_SETTINGS_SIZE = (700, 720)
_SETTINGS_MINSIZE = (540, 560)
_QUOTES_SIZE = (1120, 740)
_QUOTES_MINSIZE = (900, 580)


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, *_SETTINGS_SIZE)
    root.minsize(*_SETTINGS_MINSIZE)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    settings_view = ttk.Frame(host)
    settings_view.pack(fill="both", expand=True)
    quotes_view = ttk.Frame(host)

    def _show_settings() -> None:
        quotes_view.pack_forget()
        settings_view.pack(fill="both", expand=True)
        host.title(APP_TITLE)
        host.minsize(*_SETTINGS_MINSIZE)
        position_toplevel_screen_center(host, *_SETTINGS_SIZE)

    def _show_quotes() -> None:
        nonlocal quotes_initialized
        settings_view.pack_forget()
        quotes_view.pack(fill="both", expand=True)
        if not quotes_initialized:
            build_quotes_panel(quotes_view, on_back=_show_settings)
            quotes_initialized = True
        host.title(QUOTES_TITLE)
        host.minsize(*_QUOTES_MINSIZE)
        position_toplevel_screen_center(host, *_QUOTES_SIZE)

    quotes_initialized = False
    _build_settings_panel(settings_view, host=host, on_open_quotes=_show_quotes)
    host.protocol("WM_DELETE_WINDOW", host.destroy)


def _build_settings_panel(
    parent: tk.Misc,
    *,
    host: tk.Misc,
    on_open_quotes: Callable[[], None],
) -> None:
    version_var = tk.StringVar(value=get_carousel_version())
    look_var = tk.StringVar(value=get_showcase_look())
    preview_var = tk.StringVar(value=get_preview_url())
    hover_blur_var = tk.BooleanVar(value=get_hover_blur())

    intro = ttk.Frame(parent, padding=(16, 14))
    intro.pack(fill="x")
    ttk.Label(
        intro,
        text="Ustawienia sekcji «Wybrane dzieła» na stronie kolekcji autora.",
        wraplength=640,
    ).pack(anchor="w")
    ttk.Label(
        intro,
        text=(
            "Karuzela1/2 = zachowanie karuzeli (czy tło z obrazu aktywnego slajdu). "
            "V1/V2/V3 = wyłącznie wygląd tła sekcji (ciemność, tekstura, kontrast względem karuzeli)."
        ),
        wraplength=640,
        foreground="#555",
    ).pack(anchor="w", pady=(6, 0))

    choice = ttk.LabelFrame(parent, text="Zachowanie karuzeli", padding=12)
    choice.pack(fill="x", padx=16, pady=(4, 8))

    ttk.Radiobutton(
        choice,
        text="Karuzela1 — oryginalna (bez dynamicznego tła produktu)",
        value="Karuzela1",
        variable=version_var,
    ).pack(anchor="w", pady=2)
    ttk.Radiobutton(
        choice,
        text="Karuzela2 — cinematic hero (tło = obraz aktywnego slajdu)",
        value="Karuzela2",
        variable=version_var,
    ).pack(anchor="w", pady=2)

    look_frame = ttk.LabelFrame(parent, text="Wygląd sekcji karuzeli", padding=12)
    look_frame.pack(fill="x", padx=16, pady=(0, 8))

    ttk.Radiobutton(
        look_frame,
        text="V1 — ciemniejsze tło sekcji (jak przed korektą balansu światła)",
        value="V1",
        variable=look_var,
    ).pack(anchor="w", pady=2)
    ttk.Radiobutton(
        look_frame,
        text="V2 — jaśniejsze tło z większą teksturą",
        value="V2",
        variable=look_var,
    ).pack(anchor="w", pady=2)
    ttk.Radiobutton(
        look_frame,
        text="V3 — spokojniejsze tło (mniej kontrastu, karuzela na pierwszym planie)",
        value="V3",
        variable=look_var,
    ).pack(anchor="w", pady=2)

    effects_frame = ttk.LabelFrame(parent, text="Efekty tła (Karuzela2)", padding=12)
    effects_frame.pack(fill="x", padx=16, pady=(0, 8))

    ttk.Checkbutton(
        effects_frame,
        text="Rozmycie tła sekcji po najechaniu myszą na obraz w karuzeli",
        variable=hover_blur_var,
    ).pack(anchor="w", pady=2)
    ttk.Label(
        effects_frame,
        text=(
            "Delikatne rozmycie tła (blur) uruchamiane hoverem nad obrazem. "
            "Działa tylko z Karuzela2; wyłączone na urządzeniach dotykowych "
            "i przy „ogranicz ruch”."
        ),
        wraplength=640,
        foreground="#555",
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    url_frame = ttk.LabelFrame(parent, text="Podgląd w przeglądarce", padding=12)
    url_frame.pack(fill="x", padx=16, pady=8)
    ttk.Label(url_frame, text="URL strony kolekcji:").pack(anchor="w")
    ttk.Entry(url_frame, textvariable=preview_var, width=72).pack(fill="x", pady=(4, 8))
    ttk.Label(
        url_frame,
        text=(
            "Po Zapisz aktualizowany jest assets/giclee-carousel-config.js "
            "(domyślne ustawienia po wdrożeniu motywu).\n"
            f"Podgląd w przeglądarce ustawia localStorage: {STORAGE_KEY}, "
            f"{SHOWCASE_LOOK_STORAGE_KEY}."
        ),
        wraplength=640,
        foreground="#555",
        justify="left",
    ).pack(anchor="w")

    btns = ttk.Frame(parent, padding=(16, 8))
    btns.pack(fill="x")

    def _read_form() -> tuple[str, str] | None:
        version = version_var.get().strip()
        look = look_var.get().strip()
        if version not in ("Karuzela1", "Karuzela2"):
            messagebox.showerror("Karuzela", "Wybierz Karuzela1 lub Karuzela2.", parent=host)
            return None
        if look not in ("V1", "V2", "V3"):
            messagebox.showerror("Karuzela", "Wybierz wygląd V1, V2 lub V3.", parent=host)
            return None
        return version, look

    def _persist(version: str, look: str) -> None:
        save_karuzela_settings(
            version,  # type: ignore[arg-type]
            look,  # type: ignore[arg-type]
            preview_var.get(),
            hover_blur_var.get(),
        )

    def _save() -> None:
        form = _read_form()
        if not form:
            return
        version, look = form
        _persist(version, look)
        hover = "wł." if hover_blur_var.get() else "wył."
        show_toast(host, f"Zapisano: {version}, wygląd {look}, hover-blur {hover}")
        if messagebox.askyesno(
            "Karuzela — zapisano",
            f"Zapisano {version} + wygląd {look} (hover-blur {hover}).\n\n"
            "Otworzyć podgląd w przeglądarce?\n"
            "(Wymaga wdrożenia motywu: giclee-carousel-config.js, "
            "giclee-karuzela.js, CSS sekcji.)",
            parent=host,
        ):
            webbrowser.open(
                build_preview_url(version, look, hover_blur_var.get())  # type: ignore[arg-type]
            )

    def _open_preview() -> None:
        form = _read_form()
        if not form:
            return
        version, look = form
        _persist(version, look)
        webbrowser.open(
            build_preview_url(version, look, hover_blur_var.get())  # type: ignore[arg-type]
        )
        show_toast(host, f"Otwieram podgląd ({version}, {look})")

    ttk.Button(btns, text="Cytaty…", command=on_open_quotes).pack(side="left", padx=(0, 8))
    ttk.Button(btns, text="Zapisz", command=_save).pack(side="left", padx=(0, 8))

    right_btns = ttk.Frame(btns)
    right_btns.pack(side="right")
    ttk.Button(right_btns, text="Otwórz podgląd w przeglądarce", command=_open_preview).pack(
        side="left", padx=(0, 6)
    )
    ttk.Button(right_btns, text="Zamknij", command=host.winfo_toplevel().destroy).pack(side="left")
