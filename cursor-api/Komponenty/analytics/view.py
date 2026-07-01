"""Widok inline — uruchamia serwer analityki i otwiera dashboard w przeglądarce."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast

from .collect import make_test_event
from .env_config import collect_secret, server_port
from . import server, storage


def _scrollable(parent: tk.Misc) -> ttk.Frame:
    wrap = ttk.Frame(parent)
    wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(wrap, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _scrollregion(_evt: object = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner.bind("<Configure>", _scrollregion)

    def _fill_width(evt: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=evt.width)

    canvas.bind("<Configure>", _fill_width)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    bind_mousewheel_to_canvas(canvas, inner)
    return inner


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    storage.init_db()
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    header = ttk.Frame(root, padding=(12, 10))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(
        header,
        text="Analiza ruchu",
        font=("Segoe UI", 14, "bold"),
    ).pack(side="left", padx=(12, 0))

    scroll_host = ttk.Frame(root, padding=(12, 0, 12, 12))
    scroll_host.pack(fill="both", expand=True)
    body = _scrollable(scroll_host)

    status_var = tk.StringVar(value="Serwer nieuruchomiony")
    url_var = tk.StringVar(value="")

    intro = ttk.LabelFrame(body, text="  Ruch sklepu + lejek zakupowy  ", padding=(14, 10))
    intro.pack(fill="x", pady=(0, 12))
    ttk.Label(
        intro,
        text=(
            "Moduł zbiera eventy ze sklepu Shopify (Custom Pixel) i łączy je "
            "z zamówieniami z Admin API. Dashboard otwiera się w przeglądarce."
        ),
        wraplength=680,
        justify="left",
    ).pack(anchor="w")

    actions = ttk.Frame(intro)
    actions.pack(fill="x", pady=(10, 0))

    def _start_and_open() -> None:
        try:
            url = server.restart_server(port=server_port(), background=True)
            url_var.set(url)
            status_var.set(f"Serwer działa na porcie {server_port()} (świeży restart)")
            webbrowser.open(url)
        except OSError as exc:
            show_toast(parent, f"Nie można uruchomić serwera: {exc}", bg="#a23b2a", fg="white")

    ttk.Button(actions, text="Uruchom i otwórz dashboard", command=_start_and_open).pack(
        side="left", padx=(0, 8)
    )

    def _open_only() -> None:
        u = url_var.get()
        if u:
            webbrowser.open(u)
        else:
            show_toast(parent, "Najpierw uruchom serwer", duration_ms=2000)

    ttk.Button(actions, text="Otwórz dashboard", command=_open_only).pack(side="left")

    cfg = ttk.LabelFrame(body, text="  Status  ", padding=(14, 10))
    cfg.pack(fill="x", pady=(0, 12))
    ttk.Label(cfg, textvariable=status_var, foreground="#444").pack(anchor="w")
    ttk.Label(cfg, textvariable=url_var, foreground="#1565c0").pack(anchor="w", pady=(4, 0))

    secret_ok = bool(collect_secret())
    secret_txt = "✓ ANALYTICS_COLLECT_SECRET ustawiony" if secret_ok else "✗ Brak ANALYTICS_COLLECT_SECRET w .env"
    ttk.Label(
        cfg,
        text=secret_txt,
        foreground="#2e7d52" if secret_ok else "#c62828",
    ).pack(anchor="w", pady=(6, 0))

    stats = storage.stats_summary()
    ttk.Label(
        cfg,
        text=f"Eventów w bazie: {stats['total_events']} · sesji: {stats['total_sessions']}",
        foreground="#555",
    ).pack(anchor="w", pady=(4, 0))

    test_box = ttk.LabelFrame(body, text="  Test  ", padding=(14, 10))
    test_box.pack(fill="x")

    def _send_test() -> None:
        if not secret_ok:
            show_toast(parent, "Ustaw ANALYTICS_COLLECT_SECRET w .env", bg="#a23b2a", fg="white")
            return
        if not server.is_running():
            server.restart_server(port=server_port(), background=True)

        from .collect import ingest_event

        def _run() -> None:
            try:
                result = ingest_event(
                    make_test_event(),
                    headers={"X-Analytics-Secret": collect_secret()},
                )
                msg = f"Event testowy: {result.get('event_id', 'ok')}"
                parent.after(0, lambda: show_toast(parent, msg, duration_ms=2500))
            except Exception as exc:
                parent.after(
                    0,
                    lambda: show_toast(parent, str(exc), bg="#a23b2a", fg="white"),
                )

        threading.Thread(target=_run, daemon=True).start()

    ttk.Button(test_box, text="Wyślij event testowy", command=_send_test).pack(anchor="w")

    if secret_ok and not server.is_running():
        threading.Thread(
            target=lambda: parent.after(0, lambda: server.restart_server(port=server_port(), background=True)),
            daemon=True,
        ).start()
        status_var.set(f"Uruchamiam serwer na porcie {server_port()}…")
        url_var.set(f"http://127.0.0.1:{server_port()}/")

    return root
