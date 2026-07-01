"""Okno wykresu struktury kosztów — produkty i kategorie."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from collections.abc import Callable

from .calculator import (
    SECTION_LABELS,
    all_variants_summary,
    fmt_money,
    resolved_sales_mix,
)
from .store import load_cost_lines, load_settings

_SECTION_ORDER = ("production", "print", "packaging", "shipping")
_SECTION_COLORS = {
    "production": "#4a6fa5",
    "print": "#6b5b8a",
    "packaging": "#4a7c59",
    "shipping": "#c2410c",
}

_LIVE_REFRESHERS: list[Callable[[], None]] = []


def register_cost_structure_live_refresh(refresh: Callable[[], None]) -> Callable[[], None]:
    """Rejestruje odświeżanie otwartego okna; zwraca funkcję wyrejestrowania."""
    _LIVE_REFRESHERS.append(refresh)

    def unregister() -> None:
        try:
            _LIVE_REFRESHERS.remove(refresh)
        except ValueError:
            pass

    return unregister


def notify_cost_structure_update() -> None:
    """Wywołaj po zmianie mixu sprzedaży — odświeża otwarte okna struktury kosztów."""
    for refresh in list(_LIVE_REFRESHERS):
        try:
            refresh()
        except tk.TclError:
            try:
                _LIVE_REFRESHERS.remove(refresh)
            except ValueError:
                pass


def _blend_hex(base: str, factor: float) -> str:
    """factor 1.0 = base, niższy = jaśniejszy odcień."""
    r = int(base[1:3], 16)
    g = int(base[3:5], 16)
    b = int(base[5:7], 16)
    factor = max(0.0, min(1.0, factor))

    def mix(channel: int) -> int:
        return int(channel * factor + 255 * (1 - factor))

    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


def _line_items_meta() -> tuple[list[str], dict[str, str]]:
    """Kolejność i kolory pozycji kosztowych (jak w kalkulatorze)."""
    cost_lines = load_cost_lines()
    section_counts: dict[str, int] = {}
    for row in cost_lines:
        sec = str(row.get("section") or "production")
        section_counts[sec] = section_counts.get(sec, 0) + 1

    names: list[str] = []
    colors: dict[str, str] = {}
    section_seen: dict[str, int] = {}
    for row in cost_lines:
        name = str(row.get("name") or "")
        sec = str(row.get("section") or "production")
        idx = section_seen.get(sec, 0)
        section_seen[sec] = idx + 1
        count = section_counts.get(sec, 1)
        factor = 1.0 - (idx * 0.45 / max(count - 1, 1))
        colors[name] = _blend_hex(_SECTION_COLORS.get(sec, "#888888"), max(0.38, factor))
        names.append(name)
    return names, colors


    return names, colors


def _variant_rows(settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    rows: list[dict[str, Any]] = []
    for result in all_variants_summary(settings=settings):
        sections = {
            "production": result.production_total,
            "print": result.print_total,
            "packaging": result.packaging_total,
            "shipping": result.shipping_total,
        }
        rows.append(
            {
                "label": f"{result.wood} · {result.format}",
                "wood": result.wood,
                "format": result.format,
                "sections": sections,
                "lines_by_name": {line.name: line.cost for line in result.lines},
                "total_cost": result.total_cost,
                "full_cost": result.full_cost,
            }
        )
    return rows


def _aggregated_mix_data(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Suma kosztów per pozycja i kategoria: koszt jednostkowy × sztuki z mixu."""
    settings = settings or load_settings()
    mix = resolved_sales_mix(settings=settings)
    units_by_variant = {
        (str(row.get("wood") or ""), str(row.get("format") or "")): int(row.get("units") or 0)
        for row in mix
    }
    line_names, line_colors = _line_items_meta()
    lines_agg = {name: 0.0 for name in line_names}
    sections_agg = {sec: 0.0 for sec in _SECTION_ORDER}
    total_full = 0.0
    total_units = 0

    for row in _variant_rows(settings):
        units = units_by_variant.get((row["wood"], row["format"]), 0)
        if units <= 0:
            continue
        total_units += units
        total_full += float(row["full_cost"] or 0) * units
        for sec in _SECTION_ORDER:
            sections_agg[sec] += float(row["sections"][sec] or 0) * units
        for name in line_names:
            lines_agg[name] += float((row.get("lines_by_name") or {}).get(name) or 0) * units

    return {
        "total_units": total_units,
        "full_cost": total_full,
        "lines_by_name": lines_agg,
        "sections": sections_agg,
        "line_names": line_names,
        "line_colors": line_colors,
    }


def _draw_stacked_bar(
    canvas: tk.Canvas,
    *,
    x: int,
    y: int,
    max_width: int,
    height: int,
    segments: list[tuple[float, str, str]],
    total: float,
) -> None:
    if total <= 0:
        canvas.create_text(x, y + height // 2, text="—", anchor="w", fill="#888")
        return
    cx = x
    for value, color, tip in segments:
        if value <= 0:
            continue
        w = max(1, int(max_width * (value / total)))
        rect = canvas.create_rectangle(cx, y, cx + w, y + height, fill=color, outline="#fff", width=1)
        canvas.tag_bind(rect, "<Enter>", lambda _e, t=tip: _show_tip(canvas, t))
        canvas.tag_bind(rect, "<Leave>", lambda _e: _hide_tip(canvas))
        cx += w


def _show_tip(canvas: tk.Canvas, text: str) -> None:
    tip_id = getattr(canvas, "_tip_id", None)
    if tip_id:
        canvas.delete(tip_id)
    canvas._tip_id = canvas.create_text(  # type: ignore[attr-defined]
        canvas.winfo_width() // 2,
        12,
        text=text,
        font=("Segoe UI", 9),
        fill="#333",
    )


def _hide_tip(canvas: tk.Canvas) -> None:
    tip_id = getattr(canvas, "_tip_id", None)
    if tip_id:
        canvas.delete(tip_id)
        canvas._tip_id = None  # type: ignore[attr-defined]


def _render_products_chart(canvas: tk.Canvas, rows: list[dict[str, Any]]) -> None:
    canvas.delete("all")
    margin_left = 130
    margin_top = 36
    bar_height = 28
    gap = 14
    max_total = max((r["full_cost"] for r in rows), default=1.0) or 1.0
    chart_width = max(420, canvas.winfo_width() - margin_left - 120)

    canvas.create_text(
        12,
        10,
        text="Udział kategorii w pełnym koszcie (z wysyłką) — 6 wariantów",
        anchor="w",
        font=("Segoe UI", 10, "bold"),
    )

    for i, row in enumerate(rows):
        y = margin_top + i * (bar_height + gap)
        canvas.create_text(
            12,
            y + bar_height // 2,
            text=row["label"],
            anchor="w",
            font=("Segoe UI", 9),
        )
        segments = [
            (row["sections"][sec], _SECTION_COLORS[sec], f"{SECTION_LABELS[sec]}: {fmt_money(row['sections'][sec])}")
            for sec in _SECTION_ORDER
        ]
        bar_width = int(chart_width * (row["full_cost"] / max_total))
        _draw_stacked_bar(
            canvas,
            x=margin_left,
            y=y,
            max_width=max(1, bar_width),
            height=bar_height,
            segments=segments,
            total=row["full_cost"],
        )
        canvas.create_text(
            margin_left + bar_width + 8,
            y + bar_height // 2,
            text=fmt_money(row["full_cost"]),
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )

    legend_y = margin_top + len(rows) * (bar_height + gap) + 8
    lx = 12
    for sec in _SECTION_ORDER:
        canvas.create_rectangle(lx, legend_y, lx + 14, legend_y + 14, fill=_SECTION_COLORS[sec], outline="")
        canvas.create_text(lx + 20, legend_y + 7, text=SECTION_LABELS[sec], anchor="w", font=("Segoe UI", 8))
        lx += 150

    canvas.configure(scrollregion=canvas.bbox("all"))


def _draw_wrapped_legend(
    canvas: tk.Canvas,
    items: list[tuple[str, str]],
    *,
    start_y: int,
    max_x: int,
    col_width: int = 210,
) -> None:
    lx = 12
    ly = start_y
    for label, color in items:
        if lx + col_width > max_x and lx > 12:
            lx = 12
            ly += 18
        canvas.create_rectangle(lx, ly, lx + 14, ly + 14, fill=color, outline="")
        canvas.create_text(lx + 20, ly + 7, text=label, anchor="w", font=("Segoe UI", 8))
        lx += col_width


def _draw_cost_list_legend(
    canvas: tk.Canvas,
    items: list[tuple[str, str, float]],
    *,
    start_y: int,
    row_height: int = 18,
) -> int:
    """Pionowa legenda: kolor, nazwa i kwota w zł."""
    y = start_y
    for name, color, amount in items:
        if amount <= 0:
            continue
        canvas.create_rectangle(12, y, 26, y + 14, fill=color, outline="")
        canvas.create_text(
            32,
            y + 7,
            text=f"{name} — {fmt_money(amount)}",
            anchor="w",
            font=("Segoe UI", 8),
        )
        y += row_height
    return y


def _render_categories_chart(canvas: tk.Canvas, rows: list[dict[str, Any]]) -> None:
    """Wiersze = rodzaje ramek; segmenty = pojedyncze pozycje kosztowe."""
    canvas.delete("all")
    margin_left = 130
    margin_top = 36
    bar_height = 28
    gap = 14
    chart_width = max(420, canvas.winfo_width() - margin_left - 120)
    line_names, line_colors = _line_items_meta()

    canvas.create_text(
        12,
        10,
        text="Skład kosztu każdej ramki — poszczególne pozycje",
        anchor="w",
        font=("Segoe UI", 10, "bold"),
    )

    for i, row in enumerate(rows):
        y = margin_top + i * (bar_height + gap)
        total = float(row["full_cost"] or 0)
        lines_by_name = row.get("lines_by_name") or {}
        canvas.create_text(
            12,
            y + bar_height // 2,
            text=row["label"],
            anchor="w",
            font=("Segoe UI", 9),
        )
        segments = [
            (
                float(lines_by_name.get(name) or 0),
                line_colors[name],
                f"{name}: {fmt_money(float(lines_by_name.get(name) or 0))}",
            )
            for name in line_names
        ]
        _draw_stacked_bar(
            canvas,
            x=margin_left,
            y=y,
            max_width=chart_width,
            height=bar_height,
            segments=segments,
            total=total,
        )
        canvas.create_text(
            margin_left + chart_width + 8,
            y + bar_height // 2,
            text=fmt_money(total),
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )

    legend_y = margin_top + len(rows) * (bar_height + gap) + 8
    legend_items = [(name, line_colors[name]) for name in line_names]
    _draw_wrapped_legend(canvas, legend_items, start_y=legend_y, max_x=canvas.winfo_width() or 900)

    canvas.configure(scrollregion=canvas.bbox("all"))


def _render_aggregated_chart(canvas: tk.Canvas, data: dict[str, Any]) -> None:
    """Jeden mix — kategorie i pozycje przemnożone przez symulację sprzedaży."""
    canvas.delete("all")
    margin_left = 130
    margin_top = 36
    bar_height = 28
    gap = 22
    chart_width = max(420, canvas.winfo_width() - margin_left - 120)
    total_units = int(data.get("total_units") or 0)
    total_full = float(data.get("full_cost") or 0)
    line_names: list[str] = list(data.get("line_names") or [])
    line_colors: dict[str, str] = dict(data.get("line_colors") or {})
    lines_by_name: dict[str, float] = dict(data.get("lines_by_name") or {})
    sections: dict[str, float] = dict(data.get("sections") or {})

    canvas.create_text(
        12,
        10,
        text="Koszty zagregowane wg symulacji mixu sprzedaży",
        anchor="w",
        font=("Segoe UI", 10, "bold"),
    )
    if total_units <= 0 or total_full <= 0:
        canvas.create_text(
            12,
            44,
            text="Brak sztuk w mixie — ustaw symulację sprzedaży w zakładce Mix sprzedaży.",
            anchor="w",
            fill="#888",
            font=("Segoe UI", 9),
        )
        canvas.configure(scrollregion=canvas.bbox("all"))
        return

    mix_label = f"Mix sprzedaży ({total_units} szt.)"

    def _row(y: int, label: str, segments: list[tuple[float, str, str]], total: float) -> None:
        canvas.create_text(
            12,
            y + bar_height // 2,
            text=label,
            anchor="w",
            font=("Segoe UI", 9),
        )
        _draw_stacked_bar(
            canvas,
            x=margin_left,
            y=y,
            max_width=chart_width,
            height=bar_height,
            segments=segments,
            total=total,
        )
        canvas.create_text(
            margin_left + chart_width + 8,
            y + bar_height // 2,
            text=fmt_money(total),
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )

    y = margin_top
    section_segments = [
        (float(sections.get(sec) or 0), _SECTION_COLORS[sec], f"{SECTION_LABELS[sec]}: {fmt_money(float(sections.get(sec) or 0))}")
        for sec in _SECTION_ORDER
    ]
    _row(y, mix_label, section_segments, total_full)

    y += bar_height + gap
    canvas.create_text(
        12,
        y,
        text="Pozycje kosztowe (suma ze wszystkich wariantów × sztuki)",
        anchor="w",
        font=("Segoe UI", 9),
        fill="#555",
    )
    y += 18

    line_segments = [
        (
            float(lines_by_name.get(name) or 0),
            line_colors[name],
            f"{name}: {fmt_money(float(lines_by_name.get(name) or 0))}",
        )
        for name in line_names
    ]
    _row(y, "Pozycje", line_segments, total_full)

    legend_y = y + bar_height + gap + 8
    canvas.create_text(
        12,
        legend_y,
        text="Kategorie",
        anchor="w",
        font=("Segoe UI", 8, "bold"),
        fill="#555",
    )
    legend_y += 16
    for sec in _SECTION_ORDER:
        amount = float(sections.get(sec) or 0)
        if amount <= 0:
            continue
        canvas.create_rectangle(12, legend_y, 26, legend_y + 14, fill=_SECTION_COLORS[sec], outline="")
        canvas.create_text(
            32,
            legend_y + 7,
            text=f"{SECTION_LABELS[sec]} — {fmt_money(amount)}",
            anchor="w",
            font=("Segoe UI", 8),
        )
        legend_y += 18

    legend_y += 6
    canvas.create_text(
        12,
        legend_y,
        text="Pozycje kosztowe",
        anchor="w",
        font=("Segoe UI", 8, "bold"),
        fill="#555",
    )
    legend_y += 16
    line_legend_items = [
        (name, line_colors[name], float(lines_by_name.get(name) or 0))
        for name in line_names
    ]
    _draw_cost_list_legend(canvas, line_legend_items, start_y=legend_y)

    canvas.configure(scrollregion=canvas.bbox("all"))


_open_win: tk.Misc | None = None


def open_cost_structure_window(parent: tk.Misc) -> None:
    global _open_win  # noqa: PLW0603
    if _open_win is not None:
        try:
            if _open_win.winfo_exists():
                _open_win.lift()
                _open_win.focus_force()
                notify_cost_structure_update()
                return
        except tk.TclError:
            _open_win = None

    win = tk.Toplevel(parent)
    _open_win = win
    win.title("Struktura kosztów")
    win.geometry("920x520")
    win.minsize(760, 420)

    top = ttk.Frame(win, padding=(12, 10, 12, 6))
    top.pack(fill="x")
    ttk.Label(top, text="Struktura kosztów produkcji", font=("Segoe UI", 12, "bold")).pack(side="left")
    mix_status_var = tk.StringVar(value="")
    ttk.Label(
        top,
        textvariable=mix_status_var,
        foreground="#666",
        font=("Segoe UI", 9),
    ).pack(side="left", padx=(12, 0))

    notebook = ttk.Notebook(win, padding=(8, 0, 8, 8))
    notebook.pack(fill="both", expand=True)

    tab_products = ttk.Frame(notebook)
    tab_categories = ttk.Frame(notebook)
    tab_aggregated = ttk.Frame(notebook)
    notebook.add(tab_products, text="Wszystkie produkty")
    notebook.add(tab_categories, text="Skład ramki")
    notebook.add(tab_aggregated, text="Koszty zagregowane")

    def _make_canvas_tab(tab: ttk.Frame) -> tk.Canvas:
        wrap = ttk.Frame(tab)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0, bg="#fafafa")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return canvas

    canvas_products = _make_canvas_tab(tab_products)
    canvas_categories = _make_canvas_tab(tab_categories)
    canvas_aggregated = _make_canvas_tab(tab_aggregated)

    def refresh() -> None:
        settings = load_settings()
        rows = _variant_rows(settings)
        agg = _aggregated_mix_data(settings)
        units = int(agg.get("total_units") or 0)
        total = float(agg.get("full_cost") or 0)
        if units > 0:
            mix_status_var.set(
                f"Mix: {units} szt. · koszt zagregowany {fmt_money(total)} · aktualizacja na żywo",
            )
        else:
            mix_status_var.set("Brak sztuk w mixie — ustaw sprzedaż w zakładce Mix sprzedaży")
        _render_products_chart(canvas_products, rows)
        _render_categories_chart(canvas_categories, rows)
        _render_aggregated_chart(canvas_aggregated, agg)

    unregister = register_cost_structure_live_refresh(refresh)

    def _on_close() -> None:
        global _open_win  # noqa: PLW0603
        unregister()
        _open_win = None
        win.destroy()

    btn_row = ttk.Frame(win, padding=(12, 0, 12, 10))
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="Zamknij", command=_on_close).pack(side="right")
    ttk.Button(btn_row, text="Odśwież", command=refresh).pack(side="right", padx=(0, 8))

    win.protocol("WM_DELETE_WINDOW", _on_close)
    win.after(120, refresh)
