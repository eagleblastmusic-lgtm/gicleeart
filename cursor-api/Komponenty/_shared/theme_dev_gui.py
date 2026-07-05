"""Dialog uruchamiania `shopify theme dev` — wspólny dla launchera i komponentów motywu."""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk

import Komponenty.stronaglowna.home_features as home_features_mod
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.stronaglowna.home_features import preview_url
from Komponenty.stronaglowna.service import (
    resolve_storefront_password,
    theme_dev_http_ready,
    theme_dev_port_open,
)

DEFAULT_APP_TITLE = "GicleeApp"


def open_theme_dev_preview(
    master: tk.Misc,
    *,
    status_var: tk.StringVar | None = None,
    app_title: str = DEFAULT_APP_TITLE,
) -> None:
    """Uruchom lub otwórz lokalny podgląd motywu (127.0.0.1:9292)."""
    preview = preview_url(local=True)
    if theme_dev_port_open() and theme_dev_http_ready(url=preview):
        webbrowser.open(preview)
        show_toast(master, "Otwieram lokalny podgląd theme dev.")
        return
    if theme_dev_port_open() and not theme_dev_http_ready(url=preview):
        hint = (
            "Port 9292 jest zajęty, ale serwer nie odpowiada (formularz hasła / timeout).\n\n"
            "Zatrzymać stary proces i uruchomić theme dev od nowa?"
        )
        if not resolve_storefront_password():
            hint += (
                "\n\nUwaga: sklep ma password page — wpisz hasło w "
                "«Integracja z GPT» → «Hasło sklepu» → Zapisz, albo utwórz plik "
                ".shopify-store-password.local w korzeniu motywu."
            )
        if messagebox.askyesno(
            app_title,
            hint,
            parent=master,
        ):
            home_features_mod.restart_theme_dev_port()
        else:
            return

    if status_var is not None:
        status_var.set("Uruchamiam shopify theme dev…")

    win = tk.Toplevel(master)
    win.title("Theme dev — shopify theme dev")
    position_toplevel_screen_center(win, 720, 420)
    win.transient(master)
    ttk.Label(
        win,
        text="shopify theme dev --environment development  →  http://127.0.0.1:9292",
        padding=(12, 10),
    ).pack(anchor="w")
    log = scrolledtext.ScrolledText(win, height=16, wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
    btn_row.pack(fill="x")
    open_btn = ttk.Button(
        btn_row,
        text="Otwórz podgląd",
        command=lambda: webbrowser.open(preview_url(local=True)),
        state="disabled",
    )
    open_btn.pack(side="left")
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")

    def append(line: str) -> None:
        log.insert("end", line + "\n")
        log.see("end")

    def poll_ready(attempt: int = 0) -> None:
        preview_local = preview_url(local=True)
        if theme_dev_http_ready(url=preview_local):
            append("—" * 40)
            append("Serwer gotowy — otwieram podgląd…")
            open_btn.configure(state="normal")
            if status_var is not None:
                status_var.set("Theme dev działa (127.0.0.1:9292).")
            webbrowser.open(preview_local)
            show_toast(master, "Theme dev gotowy.")
            return
        if theme_dev_port_open() and attempt >= 8:
            append("Port 9292 otwarty, ale brak odpowiedzi HTTP — możliwy zawieszony theme dev.")
        proc = home_features_mod._theme_dev_proc
        if proc is not None and proc.poll() is not None:
            code = proc.returncode
            if code != 0:
                log_text = log.get("1.0", "end")
                if "store password" in log_text.lower() or "failed to prompt" in log_text.lower():
                    msg = (
                        f"Theme dev wymaga hasła password page sklepu (kod {code}).\n\n"
                        "GicleeApp nie może wpisać hasła interaktywnie.\n"
                        "Integracja z GPT → pole «Hasło sklepu» → Zapisz ustawienia,\n"
                        "albo plik .shopify-store-password.local w korzeniu motywu.\n\n"
                        "Zmienna SHOPIFY_FLAG_STORE_PASSWORD w PowerShell działa tylko "
                        "jeśli GicleeApp uruchomiono z tego samego terminala."
                    )
                else:
                    msg = (
                        f"Theme dev zakończył się błędem (kod {code}).\n\n"
                        "Sprawdź log powyżej (theme ID, auth Shopify, hasło sklepu)."
                    )
                append("—" * 40)
                append(msg)
                if status_var is not None:
                    status_var.set("Theme dev — błąd.")
                messagebox.showerror(app_title, msg, parent=win)
            return
        if attempt >= 90:
            append("—" * 40)
            append(
                "Timeout — brak odpowiedzi HTTP na 127.0.0.1:9292.\n"
                "Zamknij okno, uruchom Theme dev… ponownie (zabije stary proces na porcie)."
            )
            if status_var is not None:
                status_var.set("Theme dev — timeout.")
            return
        win.after(1000, lambda: poll_ready(attempt + 1))

    def worker() -> None:
        try:
            home_features_mod.start_theme_dev(on_line=append, force_restart=True)
            master.after(500, poll_ready)
        except FileNotFoundError as exc:
            master.after(0, lambda: append(str(exc)))
            master.after(0, lambda: messagebox.showerror(app_title, str(exc), parent=win))
        except OSError as exc:
            master.after(0, lambda: append(f"BŁĄD: {exc}"))
            master.after(0, lambda: messagebox.showerror(app_title, str(exc), parent=win))

    threading.Thread(target=worker, daemon=True).start()
