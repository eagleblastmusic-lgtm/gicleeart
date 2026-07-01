"""Zakladka pobierania obrazu — wklej link lub URL strony dziela."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.toast import show_toast

from .search.download import download_link, resolve_url
from .search.download.types import DownloadProgress


def build_download_tab(parent: tk.Misc, root: tk.Misc) -> None:
    from .settings import load_settings, save_settings

    app_settings = load_settings()
    hint = ttk.Label(
        parent,
        text=(
            "Wklej link do strony dziela, bezposredni URL obrazu lub adres IIIF. "
            "Silnik wybiera najlepsza jakosc: pelny plik JPEG/PNG albo skladanie kafelkow IIIF "
            "(Met, Artic, Rijks, Belvedere, Getty, Newfields, Cleveland, Mia, SMK…)."
        ),
        wraplength=920,
        foreground="#555",
        padding=(12, 8, 12, 8),
    )
    hint.pack(fill="x")

    form = ttk.LabelFrame(parent, text="Adres obrazu lub strony muzeum", padding=(10, 8))
    form.pack(fill="x", padx=12, pady=(0, 8))
    form.columnconfigure(0, weight=1)

    url_var = tk.StringVar()
    url_entry = ttk.Entry(form, textvariable=url_var, font=("Segoe UI", 10))
    url_entry.grid(row=0, column=0, sticky="ew", pady=(0, 6))

    def _paste_clipboard() -> None:
        try:
            clip = root.clipboard_get().strip()
            if clip:
                url_var.set(clip)
        except tk.TclError:
            pass

    paste_btn = ttk.Button(form, text="Wklej ze schowka", command=_paste_clipboard)
    paste_btn.grid(row=0, column=1, padx=(8, 0), pady=(0, 6))

    opts = ttk.Frame(form)
    opts.grid(row=1, column=0, columnspan=2, sticky="ew")
    ttk.Label(opts, text="Katalog docelowy:").pack(side="left")
    out_var = tk.StringVar(value=app_settings.download_dir or str(Path.home() / "Downloads"))
    out_entry = ttk.Entry(opts, textvariable=out_var, width=52)
    out_entry.pack(side="left", padx=(8, 4), fill="x", expand=True)

    def _pick_dir() -> None:
        path = filedialog.askdirectory(parent=root, title="Katalog na pobrane obrazy")
        if path:
            out_var.set(path)

    ttk.Button(opts, text="Przegladaj…", command=_pick_dir).pack(side="left")

    workers_var = tk.IntVar(value=app_settings.iiif_workers)
    force_png_var = tk.BooleanVar(value=app_settings.force_png)
    wrow = ttk.Frame(form)
    wrow.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
    ttk.Label(wrow, text="Watkow IIIF:").pack(side="left")
    ttk.Spinbox(wrow, from_=1, to=16, textvariable=workers_var, width=5).pack(side="left", padx=(6, 16))

    def _persist_download_settings() -> None:
        try:
            app_settings.iiif_workers = max(1, min(16, int(workers_var.get())))
        except tk.TclError:
            pass
        app_settings.force_png = bool(force_png_var.get())
        save_settings(app_settings)

    force_png_cb = ttk.Checkbutton(
        wrow,
        text="Wymuś PNG (tylko IIIF)",
        variable=force_png_var,
        command=_persist_download_settings,
        state="disabled",
    )
    force_png_cb.pack(side="left", padx=(0, 12))

    strategy_var = tk.StringVar(value="(analiza po wklejeniu linku)")
    ttk.Label(wrow, textvariable=strategy_var, foreground="#066").pack(side="left")

    btn_row = ttk.Frame(parent, padding=(12, 0, 12, 6))
    btn_row.pack(fill="x")
    download_btn = ttk.Button(btn_row, text="Pobierz w najlepszej jakosci")
    download_btn.pack(side="left")
    stop_btn = ttk.Button(btn_row, text="Stop", state="disabled")
    stop_btn.pack(side="left", padx=(8, 0))
    status_var = tk.StringVar(value="Gotowy.")
    ttk.Label(btn_row, textvariable=status_var, foreground="#444").pack(side="right")

    progress = ttk.Progressbar(parent, mode="determinate", maximum=100)
    progress.pack(fill="x", padx=12, pady=(0, 6))

    log_frame = ttk.LabelFrame(parent, text="Log", padding=(8, 6))
    log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    log_text = tk.Text(log_frame, height=12, wrap="word", font=("Consolas", 9), state="disabled")
    log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.pack(side="left", fill="both", expand=True)
    log_scroll.pack(side="right", fill="y")

    cancel_event = threading.Event()
    state: dict[str, object] = {"running": False}

    def _log(msg: str) -> None:
        log_text.configure(state="normal")
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        log_text.configure(state="disabled")

    def _analyze_url(*_args: object) -> None:
        url = url_var.get().strip()
        if not url:
            strategy_var.set("(analiza po wklejeniu linku)")
            force_png_cb.configure(state="disabled")
            return
        spec = resolve_url(url)
        if not spec:
            strategy_var.set("Nie rozpoznano")
            force_png_cb.configure(state="disabled")
            return
        if spec.strategy == "iiif":
            strategy_var.set(f"IIIF (kafelki) — {spec.service_id[:70]}…")
            force_png_cb.configure(state="normal")
        elif spec.strategy == "direct":
            strategy_var.set("Bezposredni plik (pelna rozdzielczosc CDN)")
            force_png_cb.configure(state="disabled")
        else:
            strategy_var.set("Analiza strony HTML → IIIF")
            force_png_cb.configure(state="normal")

    url_entry.bind("<KeyRelease>", _analyze_url)

    def _on_progress(prog: DownloadProgress) -> None:
        def ui() -> None:
            if prog.total > 0:
                progress["value"] = prog.fraction * 100
            if prog.message:
                status_var.set(prog.message)
            elif prog.phase == "tiles":
                status_var.set(f"Kafelki IIIF: {prog.done}/{prog.total}")

        root.after(0, ui)

    def _done() -> None:
        state["running"] = False
        download_btn.configure(state="normal")
        stop_btn.configure(state="disabled")

    def _start_download() -> None:
        url = url_var.get().strip()
        if not url:
            messagebox.showinfo("Pobierz obraz", "Wklej adres URL.", parent=root)
            return
        dest = Path(out_var.get().strip() or str(Path.home() / "Downloads"))
        if not dest.is_dir():
            messagebox.showerror("Pobierz obraz", "Wybierz istniejacy katalog.", parent=root)
            return
        try:
            workers = int(workers_var.get())
        except tk.TclError:
            workers = 8
        workers = max(1, min(16, workers))
        app_settings.download_dir = str(dest)
        app_settings.iiif_workers = workers
        app_settings.force_png = bool(force_png_var.get())
        save_settings(app_settings)

        cancel_event.clear()
        state["running"] = True
        download_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        progress["value"] = 0
        status_var.set("Pobieranie…")
        _log(f"--- {url}")

        def work() -> None:
            spec = resolve_url(url)
            want_png = bool(force_png_var.get()) and spec is not None and spec.strategy in ("iiif", "page_scrape")
            result = download_link(
                url,
                dest,
                workers=workers,
                force_png=want_png,
                on_progress=_on_progress,
                cancel_check=cancel_event.is_set,
            )

            def ui() -> None:
                progress["value"] = 100 if result.ok else 0
                if result.ok:
                    msg = f"Zapisano: {result.path}"
                    if result.width and result.height:
                        msg += f" ({result.width}×{result.height}px)"
                    status_var.set(msg)
                    _log(msg)
                    show_toast(root, "Obraz pobrany", duration_ms=2000)
                else:
                    status_var.set(f"Blad: {result.error}")
                    _log(f"BLAD: {result.error}")
                    messagebox.showerror("Pobierz obraz", result.error or "Nie udalo sie pobrac.", parent=root)

            root.after(0, ui)
            root.after(0, _done)

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-download").start()

    def _stop() -> None:
        cancel_event.set()
        status_var.set("Anulowanie…")

    download_btn.configure(command=_start_download)
    stop_btn.configure(command=_stop)
    url_entry.bind("<Return>", lambda _e: _start_download())
    url_entry.focus_set()


def run_download_for_hit(
    root: tk.Misc,
    hit,
    *,
    log: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    on_done: Callable[[], None] | None = None,
) -> None:
    """Pobierz obraz dla wyniku wyszukiwania (dialog katalogu)."""
    from .search.download import download_hit
    from .search.download.types import DownloadProgress
    from .settings import load_settings, save_settings

    app_settings = load_settings()
    dest = filedialog.askdirectory(
        parent=root,
        title="Katalog na pobrany obraz",
        initialdir=app_settings.download_dir or str(Path.home() / "Downloads"),
    )
    if not dest:
        if on_done:
            on_done()
        return
    dest_path = Path(dest)
    app_settings.download_dir = str(dest_path)
    save_settings(app_settings)
    cancel = cancel_event or threading.Event()

    def _on_progress(prog: DownloadProgress) -> None:
        if not log:
            return
        if prog.message:
            msg = prog.message
        elif prog.phase == "tiles" and prog.total:
            msg = f"Kafelki IIIF: {prog.done}/{prog.total}"
        elif prog.phase == "direct":
            msg = "Pobieranie pliku…"
        else:
            msg = "Pobieranie…"
        root.after(0, lambda m=msg: log(m))

    def work() -> None:
        from .search.download.resolvers import resolve_hit

        spec = resolve_hit(hit)
        use_png = app_settings.force_png and (
            spec is not None and spec.strategy in ("iiif", "page_scrape")
        )
        result = download_hit(
            hit,
            dest_path,
            workers=app_settings.iiif_workers,
            force_png=use_png,
            cancel_check=cancel.is_set,
            on_progress=_on_progress if log else None,
        )
        msg = (
            f"Zapisano: {result.path} ({result.width}×{result.height}px)"
            if result.ok
            else f"Blad pobierania: {result.error}"
        )
        if log:
            log(msg)

        def ui() -> None:
            if result.ok:
                show_toast(root, "Obraz pobrany", duration_ms=2200)
            else:
                messagebox.showerror("Pobierz obraz", result.error or "Blad.", parent=root)
            if on_done:
                on_done()

        root.after(0, ui)

    threading.Thread(target=work, daemon=True, name="stronyzobrazami-hit-dl").start()
