"""Okno konfiguracji skrótów klawiszowych launchera."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .component_loader import Component
from .launcher_shortcuts import (
    DEFAULT_LAUNCHER_SHORTCUTS,
    assign_component_shortcut,
    remove_component_shortcut,
    save_launcher_shortcuts,
    shortcut_display_label,
    shortcut_for_component,
    shortcut_key_from_event,
)


def show_shortcut_options(
    parent: tk.Misc,
    *,
    sections: list[tuple[str, list[Component]]],
    shortcuts: dict[str, str],
    on_saved: Callable[[dict[str, str]], None],
) -> None:
    """Pokazuje modalne okno przypisywania bezpośrednich skrótów komponentów."""

    win = tk.Toplevel(parent)
    win.title("Skróty komponentów")
    win.geometry("760x560")
    win.minsize(680, 460)
    try:
        win.transient(parent)
        win.grab_set()
    except tk.TclError:
        pass

    local_shortcuts = dict(shortcuts)
    rows: list[tuple[str, str, str]] = []
    component_names: dict[str, str] = {}
    for category, components in sections:
        for component in components:
            rows.append((component.folder_name, component.name, category))
            component_names[component.folder_name] = component.name
    known_folders = set(component_names)

    header = ttk.Frame(win, padding=(16, 14, 16, 8))
    header.pack(fill="x")
    ttk.Label(
        header,
        text="Skróty",
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        header,
        text=(
            "Przypisz literę, cyfrę albo klawisz F1–F12. Skrót działa od razu "
            "na ekranie kategorii i komponentów, o ile nie edytujesz pola tekstowego."
        ),
        foreground="#666",
        wraplength=700,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    table_frame = ttk.Frame(win, padding=(16, 6))
    table_frame.pack(fill="both", expand=True)
    table_frame.columnconfigure(0, weight=1)
    table_frame.rowconfigure(0, weight=1)

    tree = ttk.Treeview(
        table_frame,
        columns=("shortcut", "component", "category"),
        show="headings",
        selectmode="browse",
    )
    tree.heading("shortcut", text="Skrót")
    tree.heading("component", text="Komponent")
    tree.heading("category", text="Kategoria")
    tree.column("shortcut", width=90, anchor="center", stretch=False)
    tree.column("component", width=290, anchor="w")
    tree.column("category", width=250, anchor="w")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    def restore_parent_focus() -> None:
        try:
            parent.winfo_toplevel().lift()
            parent.focus_force()
        except tk.TclError:
            pass

    def close_dialog() -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        try:
            win.destroy()
        except tk.TclError:
            pass
        try:
            parent.after_idle(restore_parent_focus)
        except tk.TclError:
            pass

    win.protocol("WM_DELETE_WINDOW", close_dialog)

    def refresh_tree(selected_folder: str | None = None) -> None:
        current_selection = selected_folder
        if current_selection is None:
            selection = tree.selection()
            current_selection = selection[0] if selection else None
        for item in tree.get_children(""):
            tree.delete(item)
        for folder, name, category in rows:
            key = shortcut_for_component(local_shortcuts, folder)
            tree.insert(
                "",
                "end",
                iid=folder,
                values=(shortcut_display_label(key or ""), name, category),
            )
        if current_selection in known_folders:
            tree.selection_set(current_selection)
            tree.focus(current_selection)
            tree.see(current_selection)

    refresh_tree()

    def selected_folder() -> str | None:
        selection = tree.selection()
        return selection[0] if selection else None

    def capture_shortcut() -> None:
        folder = selected_folder()
        if folder is None:
            messagebox.showinfo("Skróty", "Najpierw wybierz komponent z listy.", parent=win)
            return

        capture = tk.Toplevel(win)
        capture.title("Przypisz skrót")
        capture.geometry("430x170")
        capture.resizable(False, False)
        try:
            capture.transient(win)
            capture.grab_set()
        except tk.TclError:
            pass

        frame = ttk.Frame(capture, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"Skrót dla: {component_names.get(folder, folder)}",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        prompt = ttk.Label(
            frame,
            text="Naciśnij literę, cyfrę albo F1–F12. Esc anuluje.",
            foreground="#555",
        )
        prompt.pack(anchor="w", pady=(12, 0))
        error_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=error_var, foreground="#a33").pack(anchor="w", pady=(8, 0))

        def close_capture() -> None:
            try:
                capture.grab_release()
            except tk.TclError:
                pass
            try:
                capture.destroy()
            except tk.TclError:
                pass
            try:
                win.grab_set()
                tree.focus_set()
            except tk.TclError:
                pass

        capture.protocol("WM_DELETE_WINDOW", close_capture)

        def on_key(event: tk.Event) -> str:
            nonlocal local_shortcuts
            if (event.keysym or "").lower() == "escape":
                close_capture()
                return "break"
            key = shortcut_key_from_event(event)
            if key is None:
                error_var.set("Ten klawisz nie może być użyty jako skrót.")
                return "break"

            occupied_folder = local_shortcuts.get(key)
            if occupied_folder and occupied_folder != folder:
                occupied_name = component_names.get(occupied_folder, occupied_folder)
                should_replace = messagebox.askyesno(
                    "Skrót jest zajęty",
                    f"Klawisz {shortcut_display_label(key)} otwiera już:\n{occupied_name}\n\n"
                    "Czy zastąpić to przypisanie?",
                    parent=capture,
                )
                if not should_replace:
                    error_var.set("Wybierz inny klawisz.")
                    return "break"

            local_shortcuts = assign_component_shortcut(local_shortcuts, key, folder)
            refresh_tree(folder)
            close_capture()
            return "break"

        capture.bind("<KeyPress>", on_key)
        capture.after_idle(capture.focus_force)

    def remove_shortcut() -> None:
        nonlocal local_shortcuts
        folder = selected_folder()
        if folder is None:
            messagebox.showinfo("Skróty", "Najpierw wybierz komponent z listy.", parent=win)
            return
        local_shortcuts = remove_component_shortcut(local_shortcuts, folder)
        refresh_tree(folder)

    def restore_defaults() -> None:
        nonlocal local_shortcuts
        if not messagebox.askyesno(
            "Przywróć skróty",
            "Przywrócić domyślne przypisania skrótów?",
            parent=win,
        ):
            return
        local_shortcuts = dict(DEFAULT_LAUNCHER_SHORTCUTS)
        refresh_tree()

    def save_and_close() -> None:
        filtered = {
            key: folder
            for key, folder in local_shortcuts.items()
            if folder in known_folders
        }
        try:
            save_launcher_shortcuts(filtered)
        except OSError as exc:
            messagebox.showerror(
                "Skróty",
                f"Nie udało się zapisać skrótów:\n{exc}",
                parent=win,
            )
            return
        on_saved(filtered)
        close_dialog()

    tree.bind("<Double-1>", lambda _event: capture_shortcut())

    actions = ttk.Frame(win, padding=(16, 8, 16, 14))
    actions.pack(fill="x")
    ttk.Button(actions, text="Przypisz skrót", command=capture_shortcut).pack(side="left")
    ttk.Button(actions, text="Usuń skrót", command=remove_shortcut).pack(side="left", padx=(8, 0))
    ttk.Button(actions, text="Przywróć domyślne", command=restore_defaults).pack(side="left", padx=(8, 0))
    ttk.Button(actions, text="Anuluj", command=close_dialog).pack(side="right")
    ttk.Button(actions, text="Zapisz", command=save_and_close).pack(side="right", padx=(0, 8))
