"""GUI: Debugowanie — polecenie + kolejne sekcje debuga w schowku."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

APP_TITLE = "Debugowanie"


def _copy_to_clipboard(root: tk.Misc, text: str) -> None:
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()


def _format_sections(sections: list[str]) -> str:
    return "\n\n".join(sections)


class DebugowanieApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 520, 320)
        self.root.minsize(420, 260)

        self._command = ""
        self._sections: list[str] = []

        self._build_ui()
        self.root.after(120, self._start_session)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack(side="left")

        hint = ttk.Label(
            self.root,
            text=(
                "1. Wpisz polecenie — trafi do schowka.\n"
                "2. Wklej treść debuga w kolejnych oknach — każda sekcja zapisuje się w pamięci.\n"
                "3. Przy każdej nowej sekcji polecenie wraca do schowka.\n"
                "4. «Zakończ debug» kopiuje wszystkie zebrane sekcje."
            ),
            padding=(12, 6, 12, 8),
            foreground="#555",
            wraplength=480,
            justify="left",
        )
        hint.pack(fill="x")

        status_frame = ttk.LabelFrame(self.root, text="Sesja", padding=10)
        status_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self._status_var = tk.StringVar(value="Brak aktywnej sesji.")
        ttk.Label(
            status_frame,
            textvariable=self._status_var,
            wraplength=460,
            justify="left",
        ).pack(anchor="w")

        self._preview = scrolledtext.ScrolledText(
            status_frame,
            height=6,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
        )
        self._preview.pack(fill="both", expand=True, pady=(8, 0))

        btns = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        btns.pack(fill="x")
        ttk.Button(btns, text="Nowa sesja debug", command=self._start_session).pack(side="left")
        ttk.Button(btns, text="Zamknij", command=self.root.destroy).pack(side="right")

    def _update_preview(self) -> None:
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        if not self._sections:
            self._preview.insert("1.0", "(brak sekcji)")
        else:
            self._preview.insert("1.0", _format_sections(self._sections))
        self._preview.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _start_session(self) -> None:
        self._command = ""
        self._sections = []
        self._update_preview()
        self._set_status("Wpisz polecenie…")
        self._show_command_dialog()

    def _show_command_dialog(self) -> None:
        win = tk.Toplevel(self.root)
        win.title(f"{APP_TITLE} — Wpisz polecenie")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 640, 280)
        win.minsize(480, 220)

        ttk.Label(
            win,
            text="Wpisz polecenie do wykonania (np. dla Cursora). Po zatwierdzeniu trafi do schowka.",
            wraplength=580,
            padding=(12, 12, 12, 8),
        ).pack(fill="x")

        entry = scrolledtext.ScrolledText(win, height=5, wrap="word", font=("Segoe UI", 10))
        entry.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        entry.focus_set()

        btns = ttk.Frame(win, padding=(12, 0, 12, 12))
        btns.pack(fill="x")

        def _cancel() -> None:
            win.grab_release()
            win.destroy()
            if not self._sections:
                self._set_status("Anulowano. Kliknij «Nowa sesja debug», aby zacząć od nowa.")

        def _confirm() -> None:
            command = entry.get("1.0", "end").strip()
            if not command:
                messagebox.showwarning(APP_TITLE, "Wpisz polecenie.", parent=win)
                return
            self._command = command
            try:
                _copy_to_clipboard(self.root, command)
            except tk.TclError as exc:
                messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=win)
                return
            win.grab_release()
            win.destroy()
            self._set_status("Polecenie w schowku. Wklej treść debuga (Sekcja 1).")
            show_toast(self.root, "Skopiowano polecenie do schowka", duration_ms=1800)
            self._show_debug_dialog(section_num=1)

        ttk.Button(btns, text="Anuluj", command=_cancel).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Zatwierdź", command=_confirm).pack(side="right")
        win.bind("<Escape>", lambda _e: _cancel())
        win.protocol("WM_DELETE_WINDOW", _cancel)

    def _show_debug_dialog(self, *, section_num: int) -> None:
        win = tk.Toplevel(self.root)
        win.title(f"{APP_TITLE} — Sekcja {section_num}")
        win.transient(self.root)
        win.grab_set()
        position_toplevel_screen_center(win, 720, 420)
        win.minsize(560, 320)

        ttk.Label(
            win,
            text=(
                f"Wklej treść debuga (Sekcja {section_num}). "
                "Po «Dalej» polecenie wróci do schowka i otworzy się kolejna sekcja."
            ),
            wraplength=660,
            padding=(12, 12, 12, 8),
        ).pack(fill="x")

        entry = scrolledtext.ScrolledText(win, height=12, wrap="word", font=("Consolas", 9))
        entry.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        entry.focus_set()

        btns = ttk.Frame(win, padding=(12, 0, 12, 12))
        btns.pack(fill="x")

        def _current_text() -> str:
            return entry.get("1.0", "end").strip()

        def _append_section(text: str) -> None:
            if not text:
                return
            self._sections.append(f"Sekcja {section_num} - {text}")
            self._update_preview()

        def _copy_command_background() -> None:
            if not self._command:
                return
            try:
                _copy_to_clipboard(self.root, self._command)
            except tk.TclError:
                pass

        def _finish(*, include_current: bool) -> None:
            if include_current:
                text = _current_text()
                if text:
                    _append_section(text)
            if not self._sections:
                messagebox.showinfo(
                    APP_TITLE,
                    "Brak zebranych sekcji debuga.",
                    parent=win,
                )
                return
            payload = _format_sections(self._sections)
            try:
                _copy_to_clipboard(self.root, payload)
            except tk.TclError as exc:
                messagebox.showerror(APP_TITLE, f"Schowek: {exc}", parent=win)
                return
            win.grab_release()
            win.destroy()
            self._set_status(f"Skopiowano {len(self._sections)} sekcji do schowka.")
            show_toast(
                self.root,
                f"Skopiowano {len(self._sections)} sekcji debuga",
                duration_ms=2200,
            )

        def _next() -> None:
            text = _current_text()
            if not text:
                messagebox.showwarning(APP_TITLE, "Wklej treść debuga.", parent=win)
                return
            _append_section(text)
            win.grab_release()
            win.destroy()
            _copy_command_background()
            self._set_status(
                f"Zebrano {len(self._sections)} sekcji. Polecenie w schowku — Sekcja {section_num + 1}."
            )
            show_toast(self.root, "Polecenie skopiowane do schowka", duration_ms=1600)
            self._show_debug_dialog(section_num=section_num + 1)

        def _finish_clicked() -> None:
            _finish(include_current=True)

        ttk.Button(btns, text="Zakończ debug", command=_finish_clicked).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Dalej", command=_next).pack(side="right")
        win.bind("<Escape>", lambda _e: _finish(include_current=False))
        win.protocol("WM_DELETE_WINDOW", lambda: _finish(include_current=False))


def main() -> None:
    root = tk.Tk()
    DebugowanieApp(root)
    root.mainloop()
