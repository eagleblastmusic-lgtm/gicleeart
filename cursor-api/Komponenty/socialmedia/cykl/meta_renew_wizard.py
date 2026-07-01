"""Kreator odnowy tokenow Meta — krok po kroku (Limity / Cykl)."""

from __future__ import annotations

import json
import ssl
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import meta_publisher, platforms_cykl as _cp, storage
from .meta_config import open_meta_config_dialog
from .meta_token_status import (
    analyze_meta_tokens,
    discover_app_id_from_credentials,
    meta_app_credentials,
    refresh_token_metadata_in_file,
    save_meta_app_credentials,
)


def open_meta_renew_wizard(parent: tk.Misc, *, on_done: Callable[[], None] | None = None) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Odnów tokeny Meta")
    position_toplevel_screen_center(dlg, 720, 620)
    dlg.minsize(640, 520)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    state: dict[str, object] = {
        "step": 0,
        "user_token": "",
        "new_creds": {},
    }

    outer = ttk.Frame(dlg, padding=(14, 12))
    outer.pack(fill="both", expand=True)

    title_var = tk.StringVar(value="Krok 1/5 — Stan tokenów")
    ttk.Label(outer, textvariable=title_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")

    body = ttk.Frame(outer)
    body.pack(fill="both", expand=True, pady=(10, 0))

    nav = ttk.Frame(outer)
    nav.pack(fill="x", pady=(12, 0))
    back_btn = ttk.Button(nav, text="← Wstecz")
    back_btn.pack(side="left")
    next_btn = ttk.Button(nav, text="Dalej →")
    next_btn.pack(side="right")
    ttk.Button(nav, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 8))

    def _clear_body() -> None:
        for w in body.winfo_children():
            w.destroy()

    def _show_step0() -> None:
        _clear_body()
        title_var.set("Krok 1/5 — Stan tokenów")
        report = analyze_meta_tokens(live_debug=True)
        ttk.Label(
            body,
            text="Wszystkie 4 kanały odświeżysz jednym przejściem — nie po kolei.\n"
            "Wystarczy jeden User Token → jeden long-lived → automatycznie 2 Page Tokeny\n"
            "(FB PL + FB EN; Instagram PL/EN dostaje te same tokeny co powiązane FB).",
            foreground="#333",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        tree = ttk.Treeview(body, columns=("status",), show="headings", height=5)
        tree.heading("status", text="Status")
        tree.column("status", width=420, stretch=True)
        for col in ("channel",):
            tree.configure(columns=("channel", "status"), displaycolumns=("channel", "status"))
            tree.heading("channel", text="Kanał")
            tree.column("channel", width=160, stretch=False)
        for ch in report.channels:
            tree.insert("", "end", values=(ch.label, ch.detail))
        tree.pack(fill="x", pady=(0, 4))

        ttk.Label(
            body,
            text="Kliknij «Dalej» — w krokach 2–4 wkleisz jeden token, reszta zrobi się automatycznie.",
            foreground="#666",
            justify="left",
        ).pack(anchor="w")

    def _show_step1() -> None:
        _clear_body()
        title_var.set("Krok 2/5 — User Access Token")
        ttk.Label(
            body,
            text="1. Otwórz Graph API Explorer i wygeneruj User Token ze scope:\n"
            "   pages_show_list, pages_manage_posts, pages_read_engagement,\n"
            "   instagram_basic, instagram_content_publish",
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        btn_row = ttk.Frame(body)
        btn_row.pack(anchor="w", pady=(0, 8))
        ttk.Button(
            btn_row,
            text="Otwórz Graph API Explorer",
            command=lambda: webbrowser.open("https://developers.facebook.com/tools/explorer/"),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            btn_row,
            text="Otwórz Meta Apps",
            command=lambda: webbrowser.open("https://developers.facebook.com/apps/"),
        ).pack(side="left")

        app_id, app_secret = meta_app_credentials()
        if app_id and app_secret:
            ttk.Label(
                body,
                text=f"META_APP_ID w .env: {app_id} — w kroku 3 wymienimy token na long-lived automatycznie.",
                foreground="#2e7d32",
                wraplength=640,
            ).pack(anchor="w", pady=(0, 6))
        else:
            cfg = ttk.LabelFrame(body, text="Dane aplikacji Meta (App → Settings → Basic)", padding=8)
            cfg.pack(fill="x", pady=(0, 8))
            ttk.Label(
                cfg,
                text="App Secret: w panelu Meta kliknij «Show» przy polu App Secret.",
                foreground="#666",
                wraplength=620,
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

            id_var = tk.StringVar(value=app_id or discover_app_id_from_credentials())
            sec_var = tk.StringVar(value=app_secret)
            env_status = tk.StringVar(value="")

            ttk.Label(cfg, text="App ID:").grid(row=1, column=0, sticky="w", padx=(0, 8))
            ttk.Entry(cfg, textvariable=id_var, width=44).grid(row=1, column=1, sticky="ew")
            ttk.Label(cfg, text="App Secret:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
            ttk.Entry(cfg, textvariable=sec_var, width=44, show="*").grid(
                row=2, column=1, sticky="ew", pady=(6, 0)
            )
            cfg.columnconfigure(1, weight=1)

            def _save_meta_env() -> None:
                try:
                    save_meta_app_credentials(id_var.get(), sec_var.get())
                    env_status.set("Zapisano do cursor-api/.env — w kroku 3 użyj «Wymień automatycznie».")
                except Exception as exc:
                    env_status.set(str(exc))

            btn_row2 = ttk.Frame(cfg)
            btn_row2.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
            ttk.Button(btn_row2, text="Zapisz do .env", command=_save_meta_env).pack(side="left")
            ttk.Label(cfg, textvariable=env_status, foreground="#2e7d32", wraplength=620).grid(
                row=4, column=0, columnspan=2, sticky="w", pady=(6, 0)
            )

        ttk.Label(body, text="Wklej User Access Token (krótki lub long-lived):").pack(anchor="w")
        tok = scrolledtext.ScrolledText(body, height=4, font=("Consolas", 9))
        tok.pack(fill="x", pady=(4, 0))
        existing = str(state.get("user_token") or "")
        if existing:
            tok.insert("1.0", existing)
        state["_tok_widget"] = tok

    def _exchange_long_lived(short_token: str) -> str:
        app_id, app_secret = meta_app_credentials()
        if not app_id or not app_secret:
            raise RuntimeError("Brak META_APP_ID / META_APP_SECRET w .env")
        qs = urllib.parse.urlencode(
            {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            }
        )
        url = f"{meta_publisher.GRAPH_BASE}/oauth/access_token?{qs}"
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "GicleeApp/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Brak access_token w odpowiedzi: {data}")
        return str(token)

    def _fetch_page_token(page_id: str, user_token: str) -> str:
        qs = urllib.parse.urlencode({"fields": "access_token", "access_token": user_token})
        url = f"{meta_publisher.GRAPH_BASE}/{page_id}?{qs}"
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "GicleeApp/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Brak page access_token dla {page_id}: {data}")
        return str(token)

    def _show_step2() -> None:
        _clear_body()
        title_var.set("Krok 3/5 — Long-lived user token")
        status = tk.StringVar(value="")
        ttk.Label(body, textvariable=status, wraplength=640).pack(anchor="w", pady=(0, 8))

        user_tok = str(state.get("user_token") or "")

        def _run_exchange() -> None:
            status.set("Wymieniam token…")
            next_btn.configure(state="disabled")

            def worker() -> None:
                try:
                    long_tok = _exchange_long_lived(user_tok)
                    state["user_token"] = long_tok

                    def ok() -> None:
                        status.set("Long-lived user token OK (wymiana zakończona).")
                        next_btn.configure(state="normal")

                    dlg.after(0, ok)
                except Exception as exc:
                    def err() -> None:
                        status.set(f"Błąd: {exc}")
                        next_btn.configure(state="normal")

                    dlg.after(0, err)

            threading.Thread(target=worker, daemon=True).start()

        app_id, app_secret = meta_app_credentials()
        if app_id and app_secret:
            ttk.Button(body, text="Wymień na long-lived (automatycznie)", command=_run_exchange).pack(
                anchor="w", pady=(0, 8)
            )
        else:
            ttk.Label(
                body,
                text="Ręczna wymiana (PowerShell, podstaw APP_ID, APP_SECRET, KROTKI_TOKEN):\n\n"
                "Invoke-RestMethod \"https://graph.facebook.com/v19.0/oauth/access_token?"
                "grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET"
                "&fb_exchange_token=KROTKI_TOKEN\"",
                font=("Consolas", 8),
                foreground="#444",
                justify="left",
            ).pack(anchor="w", pady=(0, 8))
            ttk.Label(body, text="Wklej otrzymany long-lived token poniżej:").pack(anchor="w")
            tok = scrolledtext.ScrolledText(body, height=3, font=("Consolas", 9))
            tok.pack(fill="x")
            tok.insert("1.0", user_tok)
            state["_long_widget"] = tok

    def _show_step3() -> None:
        _clear_body()
        title_var.set("Krok 4/5 — Page Access Tokeny")
        status = tk.StringVar(value="Kliknij «Pobierz tokeny stron».")
        ttk.Label(body, textvariable=status, wraplength=640).pack(anchor="w", pady=(0, 8))

        old = storage.load_meta_credentials()
        page_pl = (old.get("fb_pl") or {}).get("page_id") or "518592191330579"
        page_en = (old.get("fb_en") or {}).get("page_id") or "1120189217838817"
        ttk.Label(body, text=f"FB PL Page ID: {page_pl}  ·  FB EN Page ID: {page_en}", foreground="#555").pack(
            anchor="w", pady=(0, 8)
        )

        def _fetch_all() -> None:
            user_tok = str(state.get("user_token") or "").strip()
            if not user_tok:
                messagebox.showerror("Błąd", "Brak user tokena — wróć do kroku 2.", parent=dlg)
                return
            status.set("Pobieram Page Access Tokeny…")
            next_btn.configure(state="disabled")

            def worker() -> None:
                try:
                    tok_pl = _fetch_page_token(str(page_pl), user_tok)
                    tok_en = _fetch_page_token(str(page_en), user_tok)
                    ig_pl = (old.get("ig_pl") or {}).get("ig_user_id", "")
                    ig_en = (old.get("ig_en") or {}).get("ig_user_id", "")
                    new_creds = {
                        "fb_pl": {"page_id": str(page_pl), "access_token": tok_pl},
                        "fb_en": {"page_id": str(page_en), "access_token": tok_en},
                        "ig_pl": {"ig_user_id": str(ig_pl), "access_token": tok_pl},
                        "ig_en": {"ig_user_id": str(ig_en), "access_token": tok_en},
                    }
                    state["new_creds"] = new_creds

                    def ok() -> None:
                        status.set("Tokeny stron pobrane. Dalej — test i zapis.")
                        next_btn.configure(state="normal")

                    dlg.after(0, ok)
                except Exception as exc:
                    def err() -> None:
                        status.set(f"Błąd: {exc}")
                        next_btn.configure(state="normal")

                    dlg.after(0, err)

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(body, text="Pobierz tokeny stron", command=_fetch_all).pack(anchor="w")

    def _test_channel(code: str, creds: dict[str, dict[str, str]]) -> tuple[bool, str]:
        ch = _cp.get(code)
        if ch is None:
            return False, "?"
        entry = creds.get(code) or {}
        token = (entry.get("access_token") or "").strip()
        if not token:
            return False, "brak tokenu"
        if ch.platform == "fb":
            pid = (entry.get("page_id") or "").strip()
            url = f"{meta_publisher.GRAPH_BASE}/{pid}"
            params = {"fields": "id,name", "access_token": token}
        else:
            iid = (entry.get("ig_user_id") or "").strip()
            url = f"{meta_publisher.GRAPH_BASE}/{iid}"
            params = {"fields": "id,username", "access_token": token}
        qs = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": "GicleeApp/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        name = data.get("name") or data.get("username") or "OK"
        return True, str(name)

    def _show_step4() -> None:
        _clear_body()
        title_var.set("Krok 5/5 — Test i zapis")
        new_creds = state.get("new_creds")
        if not isinstance(new_creds, dict) or not new_creds:
            ttk.Label(body, text="Najpierw pobierz tokeny w poprzednim kroku.", foreground="#c62828").pack(
                anchor="w"
            )
            return

        results = ttk.Treeview(body, columns=("ok",), show="headings", height=5)
        results.configure(columns=("channel", "ok"), displaycolumns=("channel", "ok"))
        results.heading("channel", text="Kanał")
        results.heading("ok", text="Test")
        results.column("channel", width=160)
        results.column("ok", width=400)
        results.pack(fill="x", pady=(0, 8))

        test_var = tk.StringVar(value="")

        def _run_tests() -> None:
            for i in results.get_children():
                results.delete(i)
            test_var.set("Testuję…")
            ok_all = True
            for ch in _cp.all_channels():
                try:
                    ok, name = _test_channel(ch.code, new_creds)
                    results.insert("", "end", values=(ch.label, f"OK: {name}" if ok else name))
                except Exception as exc:
                    ok_all = False
                    results.insert("", "end", values=(ch.label, f"Błąd: {exc}"))
            test_var.set("Wszystkie OK — możesz zapisać." if ok_all else "Napraw błędy lub użyj «Pełna konfiguracja».")

        ttk.Button(body, text="Test wszystkich kanałów", command=_run_tests).pack(anchor="w", pady=(0, 4))
        ttk.Label(body, textvariable=test_var, foreground="#555").pack(anchor="w", pady=(0, 8))

        btn_row = ttk.Frame(body)
        btn_row.pack(anchor="w")

        def _save() -> None:
            storage.save_meta_credentials(new_creds)
            refresh_token_metadata_in_file(mark_renewed=True)
            messagebox.showinfo(
                "Zapisano",
                "Tokeny Meta zapisane w data/cykl/meta_credentials.json.",
                parent=dlg,
            )
            dlg.destroy()
            if on_done:
                on_done()

        ttk.Button(btn_row, text="Zapisz tokeny", command=_save).pack(side="left", padx=(0, 8))
        ttk.Button(
            btn_row,
            text="Pełna konfiguracja…",
            command=lambda: open_meta_config_dialog(dlg, on_saved=on_done),
        ).pack(side="left")

    steps = [_show_step0, _show_step1, _show_step2, _show_step3, _show_step4]

    def _go(step: int) -> None:
        state["step"] = step
        steps[step]()
        back_btn.configure(state="normal" if step > 0 else "disabled")
        next_btn.configure(text="Zamknij" if step == len(steps) - 1 else "Dalej →")

    def _on_next() -> None:
        step = int(state["step"])
        if step == 1:
            w = state.get("_tok_widget")
            if isinstance(w, scrolledtext.ScrolledText):
                state["user_token"] = w.get("1.0", "end").strip()
            if not state.get("user_token"):
                messagebox.showwarning("Token", "Wklej User Access Token.", parent=dlg)
                return
        if step == 2:
            w = state.get("_long_widget")
            if isinstance(w, scrolledtext.ScrolledText):
                long_t = w.get("1.0", "end").strip()
                if long_t:
                    state["user_token"] = long_t
            if not state.get("user_token"):
                messagebox.showwarning("Token", "Brak long-lived user tokena.", parent=dlg)
                return
        if step >= len(steps) - 1:
            dlg.destroy()
            return
        _go(step + 1)

    def _on_back() -> None:
        step = int(state["step"])
        if step > 0:
            _go(step - 1)

    next_btn.configure(command=_on_next)
    back_btn.configure(command=_on_back)
    _go(0)
    dlg.grab_set()
