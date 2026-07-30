"""GICLÉE FRAME™ — menu PPM prowadzące do trwałego edytora Film-scroll."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Any


def _section_key_for_context(
    owner: Any,
    element_id: str | None,
) -> str | None:
    target_id = element_id or owner._top_level_row_id_for_selection()
    if not target_id:
        return None
    row = next(
        (
            candidate
            for candidate in owner._section_tree_rows_cache
            if candidate.element_id == target_id
        ),
        None,
    )
    return row.section_key if row is not None else None


def _open_persistent_scroll_film_editor(
    owner: Any,
    after_section_key: str | None,
) -> None:
    """Dodaj draft do właściwego wariantu i otwórz pełny edytor strony."""

    label = simpledialog.askstring(
        "Giclée Frame — wygląd strony",
        "Nazwa nowej sekcji Scroll Film:",
        initialvalue="Film-scroll",
        parent=owner,
    )
    if not label or not label.strip():
        return
    try:
        # Importy są celowo leniwe: widok Studio pozostaje szybki i RAM-only,
        # dopóki operator nie wybierze jawnej akcji zapisu modułu.
        from Komponenty._shared.theme_page_editor.bootstrap import (
            build_page_ui,
        )
        from Komponenty._shared.theme_page_editor.film_scroll import (
            add_film_scroll_section,
        )
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            ensure_variants_initialized,
            load_variant_into_editor,
            persist_editor_to_variant,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        ensure_variants_initialized(config)
        variant_id = active_variant_id(config)
        template = load_variant_into_editor(config, variant_id)
        section_key = add_film_scroll_section(
            template,
            label=label.strip(),
            after_section_key=after_section_key,
        )
        persist_editor_to_variant(config, variant_id, template)
    except Exception as exc:
        messagebox.showerror(
            "Giclée Frame — wygląd strony",
            str(exc),
            parent=owner,
        )
        return

    win = tk.Toplevel(owner)
    win.title("Giclée Frame — Scroll Film")
    win.geometry("1240x820")
    win.minsize(880, 560)
    build_page_ui(
        win,
        config,
        initial_section_key=section_key,
    )
    if owner._on_status:
        owner._on_status(
            f"Dodano «Scroll Film — {label.strip()}» do wariantu. "
            "Uzupełnij film i zapisz w otwartym edytorze."
        )


def _open_persistent_page_scroll_editor(owner: Any) -> None:
    """Dodaj globalny scroll do wariantu i otwórz jego trwały edytor."""

    try:
        from Komponenty._shared.theme_page_editor.bootstrap import (
            build_page_ui,
        )
        from Komponenty._shared.theme_page_editor.page_scroll import (
            add_page_scroll_section,
        )
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            ensure_variants_initialized,
            load_variant_into_editor,
            persist_editor_to_variant,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        ensure_variants_initialized(config)
        variant_id = active_variant_id(config)
        template = load_variant_into_editor(config, variant_id)
        section_key = add_page_scroll_section(template)
        persist_editor_to_variant(config, variant_id, template)
    except Exception as exc:
        messagebox.showerror(
            "Giclée Frame — wygląd strony",
            str(exc),
            parent=owner,
        )
        return

    win = tk.Toplevel(owner)
    win.title("Giclée Frame — Scroll strony")
    win.geometry("1240x820")
    win.minsize(880, 560)
    build_page_ui(
        win,
        config,
        initial_section_key=section_key,
    )
    if owner._on_status:
        owner._on_status(
            "Dodano lub otwarto «Scroll strony». Ustaw tryb i zapisz wariant."
        )


def _open_persistent_viewport_screen_editor(
    owner: Any,
    after_section_key: str | None,
) -> None:
    """Wstaw pusty ekran do wariantu i otwórz jego pole wysokości."""

    height_vh = simpledialog.askinteger(
        "Giclée Frame — wygląd strony",
        (
            "Wysokość pustego ekranu w vh:\n"
            "100 = jeden viewport, 200 = dwa viewporty."
        ),
        initialvalue=100,
        minvalue=1,
        maxvalue=10000,
        parent=owner,
    )
    if height_vh is None:
        return
    try:
        from Komponenty._shared.theme_page_editor.bootstrap import (
            build_page_ui,
        )
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            ensure_variants_initialized,
            load_variant_into_editor,
            persist_editor_to_variant,
        )
        from Komponenty._shared.theme_page_editor.viewport_screen import (
            add_viewport_screen_section,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        ensure_variants_initialized(config)
        variant_id = active_variant_id(config)
        template = load_variant_into_editor(config, variant_id)
        section_key = add_viewport_screen_section(
            template,
            height_vh=height_vh,
            after_section_key=after_section_key,
        )
        persist_editor_to_variant(config, variant_id, template)
    except Exception as exc:
        messagebox.showerror(
            "Giclée Frame — wygląd strony",
            str(exc),
            parent=owner,
        )
        return

    win = tk.Toplevel(owner)
    win.title("Giclée Frame — pusty ekran")
    win.geometry("1240x820")
    win.minsize(880, 560)
    build_page_ui(
        win,
        config,
        initial_section_key=section_key,
    )
    if owner._on_status:
        owner._on_status(
            f"Wstawiono pusty ekran {height_vh}vh do bieżącego wariantu."
        )


def _is_persistent_viewport_screen(
    owner: Any,
    section_key: str | None,
) -> bool:
    if not section_key:
        return False
    try:
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            load_variant_into_editor,
        )
        from Komponenty._shared.theme_page_editor.viewport_screen import (
            is_viewport_screen_section,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        variant_id = active_variant_id(config)
        template = load_variant_into_editor(config, variant_id)
        sections = template.get("sections")
        return (
            isinstance(sections, dict)
            and is_viewport_screen_section(sections.get(section_key))
        )
    except Exception:
        return False


def _delete_persistent_viewport_screen(
    owner: Any,
    section_key: str,
) -> None:
    """Usuń potwierdzony ekran z aktywnego wariantu GICLÉE FRAME™."""

    try:
        from Komponenty._shared.theme_page_editor.service_base import (
            backup_variant_bundle,
        )
        from Komponenty._shared.theme_page_editor.text_layers import (
            load_document,
            shared_variant_path,
        )
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            load_variant_into_editor,
            persist_editor_to_variant,
        )
        from Komponenty._shared.theme_page_editor.viewport_screen import (
            is_viewport_screen_section,
            remove_viewport_screen_section,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        variant_id = active_variant_id(config)
        template = load_variant_into_editor(config, variant_id)
        sections = template.get("sections")
        section = (
            sections.get(section_key)
            if isinstance(sections, dict)
            else None
        )
        if not is_viewport_screen_section(section):
            raise ValueError(
                "Wybrana sekcja nie jest ekranem utworzonym przez „Wstaw ekran”."
            )
        document = load_document(shared_variant_path(config, variant_id))
        layers = (document.get("sections") or {}).get(section_key)
        layer_count = len(layers) if isinstance(layers, list) else 0
        label = str(section.get("name") or "Pusty ekran")
        message = f"Usunąć ekran «{label}» z bieżącego wariantu?"
        if layer_count:
            message += (
                f"\n\nEkran ma {layer_count} warstw tekstowych. "
                "Pozostaną zachowane jako osierocone dane i nie zostaną "
                "skasowane po cichu."
            )
        if not messagebox.askyesno(
            "Giclée Frame — wygląd strony",
            message,
            parent=owner,
        ):
            return
        backup_variant_bundle(config, variant_id)
        remove_viewport_screen_section(template, section_key)
        persist_editor_to_variant(config, variant_id, template)
    except Exception as exc:
        messagebox.showerror(
            "Giclée Frame — wygląd strony",
            str(exc),
            parent=owner,
        )
        return

    refresh = getattr(owner, "_refresh_inventory", None)
    if callable(refresh):
        try:
            refresh(warn_if_draft=False)
        except Exception:
            pass
    if owner._on_status:
        owner._on_status(
            "Usunięto pusty ekran z aktywnego wariantu GICLÉE FRAME™."
        )


def open_persistent_text_layer_editor(
    owner: Any,
    section_key: str | None = None,
) -> None:
    """Dodaj warstwę tekstową do trwałego wariantu GICLÉE FRAME™."""

    target_key = section_key or _section_key_for_context(owner, None)
    if not target_key:
        messagebox.showinfo(
            "Giclée Frame — wygląd strony",
            "Najpierw wybierz sekcję.",
            parent=owner,
        )
        return
    try:
        from Komponenty._shared.theme_page_editor.text_layers import (
            load_document,
            save_document,
            shared_variant_path,
        )
        from Komponenty._shared.theme_page_editor.text_layers_dialog import (
            add_text_layer_for_section,
        )
        from Komponenty._shared.theme_page_editor.service_base import (
            backup_variant_bundle,
        )
        from Komponenty._shared.theme_page_editor.variants import (
            active_variant_id,
            ensure_variants_initialized,
        )
        from Komponenty.gicleeframe.gui import _config

        config = _config()
        ensure_variants_initialized(config)
        variant_id = active_variant_id(config)
        path = shared_variant_path(config, variant_id)
        document = load_document(path)
        updated = add_text_layer_for_section(
            owner,
            document=document,
            section_key=target_key,
            app_title="Giclée Frame — wygląd strony",
        )
        if updated is None:
            return
        backup_variant_bundle(config, variant_id)
        save_document(path, updated)
    except Exception as exc:
        messagebox.showerror(
            "Giclée Frame — wygląd strony",
            str(exc),
            parent=owner,
        )
        return

    refresh = getattr(owner, "_refresh_inventory", None)
    if callable(refresh):
        try:
            refresh(warn_if_draft=False)
        except Exception:
            pass
    if owner._on_status:
        owner._on_status(
            "Dodano warstwę tekstową do wariantu GICLÉE FRAME™."
        )


def _show_section_context_menu(
    owner: Any,
    event: object,
    element_id: str | None,
) -> str:
    after_section_key = _section_key_for_context(owner, element_id)
    is_viewport_screen = _is_persistent_viewport_screen(
        owner,
        after_section_key,
    )
    menu = tk.Menu(owner, tearoff=0)
    menu.add_command(
        label="Wstaw ekran…",
        command=lambda key=after_section_key: (
            _open_persistent_viewport_screen_editor(owner, key)
        ),
    )
    menu.add_separator()
    menu.add_command(
        label="Dodaj „Scroll Film”…",
        command=lambda key=after_section_key: (
            _open_persistent_scroll_film_editor(owner, key)
        ),
    )
    menu.add_command(
        label="Dodaj „Scroll strony”…",
        command=lambda: _open_persistent_page_scroll_editor(owner),
    )
    menu.add_separator()
    menu.add_command(
        label="Dodaj tekst…",
        command=lambda key=after_section_key: (
            open_persistent_text_layer_editor(owner, key)
        ),
    )
    if after_section_key and is_viewport_screen:
        menu.add_separator()
        menu.add_command(
            label="Usuń ekran…",
            command=lambda key=after_section_key: (
                _delete_persistent_viewport_screen(owner, key)
            ),
        )
    try:
        menu.tk_popup(
            int(getattr(event, "x_root", 0)),
            int(getattr(event, "y_root", 0)),
        )
    finally:
        menu.grab_release()
    return "break"


def bind_section_list_context_target(
    owner: Any,
    widget: Any,
    element_id: str | None = None,
) -> None:
    bind = getattr(widget, "bind", None)
    if not callable(bind):
        return
    for sequence in ("<Button-3>", "<Button-2>"):
        callback = (
            lambda event, eid=element_id: _show_section_context_menu(
                owner,
                event,
                eid,
            )
        )
        try:
            bind(sequence, callback, add="+")
        except TypeError:
            # Proste atrapy widgetów w testach nie implementują argumentu add.
            bind(sequence, callback)


__all__ = [
    "bind_section_list_context_target",
    "open_persistent_text_layer_editor",
]
