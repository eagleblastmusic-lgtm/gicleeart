"""Widok inline — dashboard limitów usług zewnętrznych."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from datetime import datetime
from tkinter import ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty.dodajobraz.r2_usage import _fmt_int, usage_percent, usage_status

from .collectors import (
    MeterRow,
    ServiceSection,
    clear_section_cache,
    collect_all_progressive,
    collect_static_services,
)

REFRESH_MS = 300_000  # 5 min


def _scrollable(parent: tk.Misc) -> tuple[ttk.Frame, tk.Canvas]:
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

    def _focus_canvas(_evt: object = None) -> None:
        try:
            canvas.focus_set()
        except tk.TclError:
            pass

    wrap.bind("<Enter>", _focus_canvas)
    canvas.bind("<Enter>", _focus_canvas)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    bind_mousewheel_to_canvas(canvas, inner)

    return inner, canvas


def _add_meter(parent: tk.Misc, row: int, meter: MeterRow) -> None:
    frame = ttk.Frame(parent)
    frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    frame.columnconfigure(0, weight=1)

    head = ttk.Frame(frame)
    head.pack(fill="x")
    ttk.Label(head, text=meter.title, font=("Segoe UI", 9, "bold")).pack(side="left")

    if meter.used is None:
        ttk.Label(head, text="brak danych", foreground="#888").pack(side="right")
        hint = meter.missing_hint or "Odśwież lub sprawdź konfigurację w .env"
        ttk.Label(frame, text=hint, foreground="#666", wraplength=640, justify="left").pack(
            anchor="w", pady=(3, 0)
        )
        return

    pct = usage_percent(meter.used, meter.quota)
    status, color = usage_status(pct)
    free = max(0, meter.quota - meter.used)
    ttk.Label(head, text=status, foreground=color).pack(side="right")

    bar = ttk.Progressbar(frame, maximum=100.0, value=pct, mode="determinate")
    bar.pack(fill="x", pady=(3, 2))

    unit = meter.unit_hint or ""
    detail = (
        f"{_fmt_int(meter.used)} / {_fmt_int(meter.quota)} {unit} "
        f"({pct:.1f}%) · wolne {_fmt_int(free)}"
    )
    ttk.Label(frame, text=detail, foreground="#444").pack(anchor="w")


def _render_section(
    parent: tk.Misc,
    row: int,
    sec: ServiceSection,
    *,
    on_meta_renew: Callable[[], None] | None = None,
) -> None:
    box = ttk.LabelFrame(parent, text=f"  {sec.title}  ", padding=(10, 8))
    box.grid(row=row, column=0, sticky="ew", pady=(0, 10))
    box.columnconfigure(0, weight=1)

    head = ttk.Frame(box)
    head.pack(fill="x", pady=(0, 4))
    if sec.subtitle:
        ttk.Label(head, text=sec.subtitle, foreground="#555").pack(side="left")
    ttk.Label(head, text=sec.status, foreground=sec.status_color).pack(side="right")

    if sec.error:
        ttk.Label(box, text=f"⚠ {sec.error}", foreground="#c62828", wraplength=660).pack(
            anchor="w", pady=(0, 6)
        )

    meters_frame = ttk.Frame(box)
    meters_frame.pack(fill="x")
    meters_frame.columnconfigure(0, weight=1)
    for i, meter in enumerate(sec.meters):
        _add_meter(meters_frame, i, meter)

    for line in sec.info_lines:
        ttk.Label(box, text=f"· {line}", foreground="#555", wraplength=660, justify="left").pack(
            anchor="w", pady=(1, 0)
        )

    if sec.panel_url:
        btn_row = ttk.Frame(box)
        btn_row.pack(fill="x", pady=(6, 0))
        if sec.key == "meta" and on_meta_renew:
            ttk.Button(
                btn_row,
                text="Odnów tokeny",
                command=on_meta_renew,
            ).pack(side="right", padx=(6, 0))
        ttk.Button(
            btn_row,
            text="Otwórz panel",
            command=lambda u=sec.panel_url: webbrowser.open(u),
        ).pack(side="right")


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    state: dict[str, object] = {"busy": False, "refresh_job": None}

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(header, text="Limity usług", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 0))

    status_var = tk.StringVar(value="Kliknij Odśwież, aby pobrać dane.")
    global_var = tk.StringVar(value="")

    toolbar = ttk.Frame(root, padding=(12, 0, 12, 6))
    toolbar.pack(fill="x")
    ttk.Label(toolbar, textvariable=global_var, foreground="#333", font=("Segoe UI", 9, "bold")).pack(
        anchor="w"
    )
    ttk.Label(toolbar, textvariable=status_var, foreground="#555", wraplength=760).pack(anchor="w")

    scroll_host = ttk.Frame(root, padding=(12, 0, 12, 12))
    scroll_host.pack(fill="both", expand=True)
    inner, scroll_canvas = _scrollable(scroll_host)

    btn_row = ttk.Frame(root, padding=(12, 0, 12, 10))
    btn_row.pack(fill="x")
    refresh_btn = ttk.Button(btn_row, text="Odśwież wszystko")
    refresh_btn.pack(side="right")

    def render(sections: list[ServiceSection], global_status: tuple[str, str], *, partial: bool = False) -> None:
        for w in inner.winfo_children():
            w.destroy()
        inner.columnconfigure(0, weight=1)

        def _renew_meta() -> None:
            from Komponenty.socialmedia.cykl.meta_renew_wizard import open_meta_renew_wizard

            open_meta_renew_wizard(root, on_done=lambda: refresh(force=True))

        for i, sec in enumerate(sections):
            _render_section(inner, i, sec, on_meta_renew=_renew_meta)
        bind_mousewheel_to_canvas(scroll_canvas, inner)
        label, _color = global_status
        global_var.set(f"Ogólny stan: {label}")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        suffix = " · pobieranie…" if partial else ""
        status_var.set(f"Odświeżono {ts} · źródło: USLUGI.md + API (.env){suffix}")

    def refresh(*, force: bool = False) -> None:
        if state["busy"]:
            return
        state["busy"] = True
        refresh_btn.configure(state="disabled")
        if force:
            clear_section_cache()
        status_var.set("Pobieram limity…")

        static = collect_static_services()
        sections_acc: dict[str, ServiceSection] = {}
        order = ("cloudflare", "resend", "serpapi", "meta", "shopify", "nbp", "vercel")

        def _ordered_sections() -> list[ServiceSection]:
            out: list[ServiceSection] = []
            for key in order:
                sec = sections_acc.get(key)
                if sec is not None:
                    out.append(sec)
            return out

        def _finish(sections: list[ServiceSection], global_status: tuple[str, str]) -> None:
            state["busy"] = False
            refresh_btn.configure(state="normal")
            render(sections, global_status, partial=False)

        def _on_section(sec: ServiceSection) -> None:
            sections_acc[sec.key] = sec

            def tick() -> None:
                current = _ordered_sections()
                for s in static:
                    if s.key not in {x.key for x in current}:
                        current.append(s)
                from .collectors import _worst_status

                render(current, _worst_status(current), partial=True)

            root.after(0, tick)

        def worker() -> None:
            try:
                sections, global_status = collect_all_progressive(
                    _on_section,
                    use_cache=not force,
                )

                def done() -> None:
                    _finish(sections, global_status)

                root.after(0, done)
            except Exception as exc:
                def err() -> None:
                    state["busy"] = False
                    refresh_btn.configure(state="normal")
                    status_var.set(f"Błąd: {exc}")

                root.after(0, err)

        threading.Thread(target=worker, daemon=True).start()

    refresh_btn.configure(command=lambda: refresh(force=True))

    def schedule_refresh() -> None:
        state["refresh_job"] = root.after(REFRESH_MS, auto_refresh)

    def auto_refresh() -> None:
        refresh(force=False)
        schedule_refresh()

    def on_destroy(_evt: object = None) -> None:
        job = state.get("refresh_job")
        if job:
            try:
                root.after_cancel(str(job))
            except tk.TclError:
                pass

    root.bind("<Destroy>", on_destroy, add="+")

    root.after(50, lambda: refresh(force=False))
    schedule_refresh()

    return root
