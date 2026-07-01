"""Okno «Zmień ceny» — masowa aktualizacja cen wariantów + widok Rynki."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.task_notify import notify_long_task_done
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.kalkulacja.calculator import calc_sell_price_for_shop_labels

from .market_variant_prices import (
    get_market_variant_price,
    group_key,
    parse_group_key,
    set_market_variant_price,
)
from .create import get_reference_variant_rows, update_all_product_prices
from .markets import (
    compute_market_price,
    discover_shopify_market_ids,
    format_price,
    load_markets,
    market_price_in_eur,
    push_markup_to_shopify,
    update_market_markup,
)
from .shopify_client import OperationCancelled

APP_TITLE = "Zmien ceny"


class _PriceChangeCtx:
    def __init__(
        self,
        root: tk.Misc,
        *,
        enqueue_log: Callable[[str], None],
        set_status: Callable[[str], None],
        append_log: Callable[[str], None] | None = None,
    ) -> None:
        self.root = root
        self.enqueue_log = enqueue_log
        self.set_status = set_status
        self.append_log = append_log or enqueue_log

    def build_markets_panel(self,
        parent: tk.Misc,
        dialog_parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        get_variant_groups: Callable[[], tuple[list[tuple[str, str]], dict[tuple[str, str], dict]]] | None = None,
    ) -> None:
        """Buduje panel rynkow (markup %) wewnatrz istniejacego kontenera."""
        try:
            markets_initial = load_markets()
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE, f"Nie udalo sie wczytac markets_config.json:\n{exc}", parent=dialog_parent
            )
            on_back()
            return
        if not markets_initial:
            messagebox.showwarning(APP_TITLE, "Brak rynkow w konfiguracji.", parent=dialog_parent)
            on_back()
            return

        nav = ttk.Frame(parent)
        nav.pack(side="top", fill="x", padx=12, pady=(8, 4))
        ttk.Button(nav, text="Powrot", command=on_back, width=12).pack(side="left")

        ttk.Label(
            parent,
            text=(
                "Dla kazdego rynku ustaw % narzutu nad cena bazowa (PL). "
                "Rozwin rynek (strzalka) — pozycje jak w widoku Globalnym «Zmien ceny»: "
                "cena PL grupy, auto z markupu, reczna edycja (puste = auto). "
                "Double-click: kolumna Markup % (rynek) lub Cena edycji (grupa). "
                "Kolumna W EUR = podglad przykladu 100 PLN. Zapis: markets_config.json + market_variant_prices.json."
            ),
            justify="left",
            foreground="#444",
            wraplength=780,
        ).pack(side="top", fill="x", padx=12, pady=(10, 6))

        # ---------- Pasek: cena bazowa + filtr ----------
        toolbar = ttk.Frame(parent)
        toolbar.pack(side="top", fill="x", padx=12, pady=(0, 4))

        ttk.Label(toolbar, text="Cena bazowa (PL) do podgladu:").pack(side="left")
        sample_var = tk.StringVar(value="100.00")
        ttk.Entry(toolbar, textvariable=sample_var, width=10, justify="right").pack(
            side="left", padx=(8, 0)
        )
        ttk.Label(toolbar, text="PLN").pack(side="left", padx=(4, 14))

        ttk.Label(toolbar, text="Filtr:").pack(side="left")
        filter_var = tk.StringVar()
        filter_entry = ttk.Entry(toolbar, textvariable=filter_var, width=22)
        filter_entry.pack(side="left", padx=(6, 4))
        ttk.Button(
            toolbar, text="Wyczysc", width=10,
            command=lambda: filter_var.set(""),
        ).pack(side="left")

        # ---------- Panel: kursy walut (NBP) ----------
        fx_bar = ttk.Frame(parent)
        fx_bar.pack(side="top", fill="x", padx=12, pady=(2, 4))
        ttk.Label(fx_bar, text="Kurs walut:").pack(side="left")
        fx_status_var = tk.StringVar(value="(ladowanie...)")
        ttk.Label(fx_bar, textvariable=fx_status_var, foreground="#1565c0").pack(
            side="left", padx=(6, 10)
        )

        def _refresh_fx_button(*, force: bool = False) -> None:
            prev_rates: dict[str, float] = (
                {k: float(v) for k, v in state["fx_rates"].items()} if force else {}
            )
            _refresh_fx_cache(force=force)
            parts: list[str] = []
            for cur, rate in state["fx_rates"].items():
                info = state["fx_info"].get(cur, {})
                source = info.get("source", "?")
                stale = " [CACHE]" if info.get("stale") else ""
                parts.append(f"1 {cur} = {rate:.4f} PLN ({source}{stale})")
            if not parts:
                fx_status_var.set("(brak walut obcych - tylko PLN)")
            else:
                fx_status_var.set("  |  ".join(parts))
            _render()

            if force:
                infos = state.get("fx_info") or {}
                any_stale = any(
                    isinstance(infos.get(c), dict) and infos[c].get("stale")
                    for c in infos
                )
                any_err = any(
                    isinstance(infos.get(c), dict) and infos[c].get("error")
                    for c in infos
                )
                if not prev_rates and not state["fx_rates"]:
                    msg = "Brak walut obcych w rynkach — NBP nie jest potrzebne."
                    bg, duration = "#1565c0", 2200
                elif any_stale or any_err:
                    msg = "NBP: zwrocono stare kursy (siec/API). Zobacz znacznik [CACHE]."
                    bg, duration = "#e65100", 3200
                else:
                    changed = False
                    for cur, new_r in state["fx_rates"].items():
                        old = prev_rates.get(cur)
                        if old is None or abs(float(new_r) - float(old)) > 1e-5:
                            changed = True
                            break
                    if prev_rates and not changed:
                        msg = "Pobrano z NBP — kursy bez zmian (jak w tabeli)."
                    else:
                        msg = "Zaktualizowano kursy z NBP."
                    bg, duration = "#1b5e20", 2600
                show_toast(dialog_parent, msg, duration_ms=duration, fade_ms=240, bg=bg, fg="#fff")

        def _set_manual_rate() -> None:
            from tkinter import simpledialog as _sd
            cur = _sd.askstring(
                APP_TITLE, "Waluta (EUR/USD/...):",
                parent=dialog_parent, initialvalue="EUR",
            )
            if not cur:
                return
            val = _sd.askstring(
                APP_TITLE, f"Kurs recznie (ile PLN za 1 {cur.upper()}):",
                parent=dialog_parent, initialvalue="4.30",
            )
            if not val:
                return
            try:
                rate = float(val.replace(",", "."))
            except ValueError:
                messagebox.showerror(APP_TITLE, "Kurs musi byc liczba.", parent=dialog_parent)
                return
            try:
                from Komponenty._shared import fx_rates as fx
                fx.set_manual_rate(cur.upper(), rate)
            except (ValueError, OSError) as e:
                messagebox.showerror(APP_TITLE, f"Nie udalo sie zapisac kursu:\n{e}", parent=dialog_parent)
                return
            _refresh_fx_button(force=False)

        ttk.Button(
            fx_bar, text="Odswiez kursy (NBP)",
            command=lambda: _refresh_fx_button(force=True),
        ).pack(side="right")
        ttk.Button(
            fx_bar, text="Kurs recznie...",
            command=_set_manual_rate,
        ).pack(side="right", padx=(0, 6))
        # Przycisk "EUR w Shopify" doklejany po zdefiniowaniu `state` (patrz nizej).

        # Wstepna aktualizacja etykiety
        dialog_parent.after(50, lambda: _refresh_fx_button(force=False))

        ttk.Separator(parent, orient="horizontal").pack(side="top", fill="x", padx=12, pady=(6, 0))

        # ---------- Treeview ----------
        tree_wrap = ttk.Frame(parent)
        tree_wrap.pack(side="top", fill="both", expand=True, padx=12, pady=(6, 4))

        cols = ("markup", "pl_base", "auto_price", "manual", "preview_eur")
        headings_def: dict[str, tuple[str, int, str, bool]] = {
            "markup":      ("Markup %",       88, "e", False),
            "pl_base":     ("PL / baza",     110, "e", False),
            "auto_price":  ("Auto (rynek)",  120, "e", False),
            "manual":      ("Cena (edycja)", 110, "e", False),
            "preview_eur": ("W EUR (100 PLN)", 110, "e", False),
        }

        tree = ttk.Treeview(
            tree_wrap, columns=cols, show="tree headings",
            selectmode="browse", height=12,
        )
        tree.heading("#0", text="Rynek / grupa", command=lambda: _sort_by("name_pl"))
        tree.column("#0", width=220, anchor="w", stretch=True, minwidth=140)
        for c, (txt, w, anch, stretch) in headings_def.items():
            tree.heading(c, text=txt, command=lambda _c=c: _sort_by(_c))
            tree.column(c, width=w, anchor=anch, stretch=stretch, minwidth=max(50, w // 2))

        # tagi do podswietlania bazowego rynku + parzystych wierszy
        tree.tag_configure("base",   background="#f3f3f3", foreground="#777")
        tree.tag_configure("alt",    background="#fafafa")
        tree.tag_configure("normal", background="#ffffff")
        tree.tag_configure("child",  background="#f8fafc", foreground="#333")

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ---------- State ----------
        state: dict[str, Any] = {
            "markets": list(markets_initial),
            "sort_col": "name_pl",
            "sort_desc": False,
            "fx_rates": {},
            "fx_info": {},
            "expanded": set(),
        }

        def _child_iid(market_code: str, wood: str, size: str) -> str:
            return f"{market_code}::{group_key(wood, size)}"

        def _is_child_iid(iid: str) -> bool:
            return "::" in (iid or "")

        def _market_from_iid(iid: str) -> str | None:
            if not iid:
                return None
            if _is_child_iid(iid):
                return iid.split("::", 1)[0]
            return iid

        def _pl_base_for_group(ginfo: dict[str, Any]) -> float | None:
            uniq = sorted({str(p).strip() for p in (ginfo.get("prices") or []) if str(p).strip()})
            if len(uniq) == 1:
                try:
                    return float(uniq[0].replace(",", "."))
                except ValueError:
                    return None
            return None

        def _group_rows_for_market(market_code: str) -> list[tuple[str, str, dict[str, Any]]]:
            if not get_variant_groups:
                return []
            group_order, groups = get_variant_groups()
            out: list[tuple[str, str, dict[str, Any]]] = []
            for gkey in group_order:
                ginfo = groups.get(gkey)
                if not ginfo:
                    continue
                wood, size = gkey
                out.append((wood, size, ginfo))
            return out

        def _child_row_values(m: Any, wood: str, size: str, ginfo: dict[str, Any]) -> tuple[str, ...]:
            pl_val = _pl_base_for_group(ginfo)
            pct = 0.0 if m.is_base else float(m.markup_percent)
            cur = (m.currency or "PLN").upper()
            rate = state["fx_rates"].get(cur) if cur != "PLN" else None
            pl_txt = format_price(pl_val, "PLN") if pl_val is not None else "—"
            if pl_val is not None:
                auto_val = compute_market_price(pl_val, pct, currency=cur, fx_rate=rate)
                auto_txt = format_price(auto_val, m.currency)
            else:
                auto_txt = "—"
            manual = get_market_variant_price(m.code, wood, size) or ""
            return ("—", pl_txt, auto_txt, manual, "")

        def _ensure_market_children(market_code: str) -> None:
            if tree.get_children(market_code):
                return
            m = next((x for x in state["markets"] if x.code == market_code), None)
            if not m:
                return
            for wood, size, ginfo in _group_rows_for_market(market_code):
                color_count = len(ginfo.get("rows") or [])
                label = ginfo.get("label") or f"{wood} {size}".strip()
                child_label = f"{label}   ({color_count} kol.)"
                cid = _child_iid(market_code, wood, size)
                tree.insert(
                    market_code,
                    "end",
                    iid=cid,
                    text=f"  {child_label}",
                    values=_child_row_values(m, wood, size, ginfo),
                    tags=("child",),
                )

        def _refresh_fx_cache(*, force: bool = False) -> None:
            """Pobiera kursy z NBP (z cache 24h) dla niepolskich walut uzywanych przez rynki."""
            needed = sorted(
                {(m.currency or "").upper() for m in state["markets"]
                 if (m.currency or "").upper() not in ("", "PLN")}
            )
            try:
                from Komponenty._shared import fx_rates as fx
            except ImportError:
                return
            rates: dict[str, float] = {}
            info: dict[str, dict[str, Any]] = {}
            for cur in needed:
                try:
                    rate, _info = fx.get_rate(cur, force_refresh=force)
                    rates[cur] = rate
                    info[cur] = _info
                except fx.FxError as exc:
                    info[cur] = {"error": str(exc)}
            state["fx_rates"] = rates
            state["fx_info"] = info

        _refresh_fx_cache()

        def _show_shopify_eur_rate() -> None:
            """Kurs EUR wg ustawien walut w Shopify (GraphQL), obok NBP."""
            from . import shopify_client as sc

            try:
                shop, token = sc.load_session()
            except sc.ShopifyError as e:
                messagebox.showerror(APP_TITLE, str(e), parent=dialog_parent)
                return
            try:
                info = sc.get_presentment_currency_setting(shop, token, "EUR")
            except sc.ShopifyError as e:
                messagebox.showerror(APP_TITLE, f"Blad API Shopify:\n{e}", parent=dialog_parent)
                return
            if not info.get("found"):
                messagebox.showinfo(
                    APP_TITLE,
                    f"W sklepie nie ma waluty prezentacji {info.get('currency', 'EUR')} "
                    f"w Shop.currencySettings (waluta sklepu: {info.get('shop_currency') or '?'}).\n\n"
                    "Sprawdz, czy EUR jest wlaczone w Ustawieniach platnosci / walut w Shopify.",
                    parent=dialog_parent,
                )
                return
            lines = [
                f"Waluta sklepu (Shopify): {info['shop_currency']}",
                f"Waluta prezentacji: {info['currency']} ({info.get('currency_name') or 'EUR'})",
                f"Wlaczone w sklepie: {'tak' if info.get('enabled') else 'nie'}",
                "",
            ]
            mr = info.get("manual_rate")
            if mr is not None:
                lines.append(f"Reczny mnoznik Shopify (manualRate): {mr}")
                lines.append(
                    "(przy wlaczonych recznych kursach — konwersja ze waluty sklepu do EUR)"
                )
            else:
                lines.append(
                    "Reczny kurs (manualRate): brak — Shopify uzywa kursu automatycznego. "
                    "Liczbowej stawki nie zwraca Admin API (tylko data aktualizacji ponizej)."
                )
            ru = info.get("rate_updated_at")
            if ru:
                lines.append("")
                lines.append(
                    f"Ostatnia zmiana stawki (Shopify): {str(ru)[:19].replace('T', ' ')}"
                )
            eur_nbp = state["fx_rates"].get("EUR")
            if eur_nbp is not None:
                lines.append("")
                lines.append(
                    f"Do porownania — NBP (pasek powyzej): 1 EUR = {float(eur_nbp):.4f} PLN"
                )
            messagebox.showinfo(APP_TITLE, "\n".join(lines), parent=dialog_parent)

        ttk.Button(
            fx_bar, text="EUR w Shopify...",
            command=_show_shopify_eur_rate,
        ).pack(side="right", padx=(0, 6))

        def _current_base() -> float:
            try:
                return float((sample_var.get() or "0").replace(",", "."))
            except ValueError:
                return 0.0

        def _row_values(m: Any, base: float) -> tuple:
            pct = 0.0 if m.is_base else float(m.markup_percent)
            cur = (m.currency or "PLN").upper()
            rate = state["fx_rates"].get(cur) if cur != "PLN" else None
            price = compute_market_price(base, pct, currency=cur, fx_rate=rate)
            markup_txt = ("baza" if m.is_base else f"{pct:+.1f}%")
            eur_price = market_price_in_eur(
                base,
                pct,
                currency=cur,
                fx_rates=state["fx_rates"],
            )
            eur_txt = format_price(eur_price, "EUR") if eur_price is not None else "—"
            sample_txt = format_price(price, m.currency)
            return (
                markup_txt,
                format_price(base, "PLN"),
                sample_txt,
                "",
                eur_txt,
            )

        def _sort_key(m: Any, col: str) -> Any:
            if col == "name_pl":
                return (m.name_pl or "").lower()
            if col == "markup":
                return -1.0 if m.is_base else float(m.markup_percent)
            if col == "pl_base":
                return _current_base()
            if col == "auto_price":
                pct = 0.0 if m.is_base else float(m.markup_percent)
                cur = (m.currency or "PLN").upper()
                rate = state["fx_rates"].get(cur) if cur != "PLN" else None
                return compute_market_price(
                    _current_base(), pct, currency=cur, fx_rate=rate,
                )
            if col == "preview_eur":
                pct = 0.0 if m.is_base else float(m.markup_percent)
                cur = (m.currency or "PLN").upper()
                eur = market_price_in_eur(
                    _current_base(),
                    pct,
                    currency=cur,
                    fx_rates=state["fx_rates"],
                )
                return eur if eur is not None else -1.0
            return ""

        def _render() -> None:
            expanded = set(state.get("expanded") or set())
            tree.delete(*tree.get_children())
            ftxt = (filter_var.get() or "").strip().lower()
            items = list(state["markets"])
            if ftxt:
                items = [
                    m for m in items
                    if ftxt in (m.name_pl or "").lower()
                    or ftxt in (m.name_en or "").lower()
                    or ftxt in (m.code or "").lower()
                    or ftxt in (m.locale or "").lower()
                    or ftxt in (m.currency or "").lower()
                ]
            col = state["sort_col"]
            desc = state["sort_desc"]
            items.sort(key=lambda m: _sort_key(m, col), reverse=desc)
            base = _current_base()
            for idx, m in enumerate(items):
                if m.is_base:
                    tag = "base"
                else:
                    tag = "alt" if idx % 2 == 1 else "normal"
                tree.insert(
                    "",
                    "end",
                    iid=m.code,
                    text=m.name_pl,
                    values=_row_values(m, base),
                    tags=(tag,),
                )
                if m.code in expanded:
                    tree.item(m.code, open=True)
                    _ensure_market_children(m.code)
            for c, (txt, _w, _a, _s) in headings_def.items():
                arrow = ""
                if c == col:
                    arrow = "  v" if desc else "  ^"
                tree.heading(c, text=txt + arrow)
            arrow0 = ""
            if state["sort_col"] == "name_pl":
                arrow0 = "  v" if state["sort_desc"] else "  ^"
            tree.heading("#0", text="Rynek / grupa" + arrow0)

        def _sort_by(col: str) -> None:
            if state["sort_col"] == col:
                state["sort_desc"] = not state["sort_desc"]
            else:
                state["sort_col"] = col
                state["sort_desc"] = False
            _render()

        def _reload_from_disk() -> None:
            try:
                state["markets"] = load_markets()
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f"Blad ladowania konfiguracji: {exc}")
                return
            _render()

        def _refresh_child_row(rowid: str) -> None:
            if not _is_child_iid(rowid):
                return
            market_code, gk = rowid.split("::", 1)
            parsed = parse_group_key(gk)
            if not parsed:
                return
            wood, size = parsed
            m = next((x for x in state["markets"] if x.code == market_code), None)
            if not m or not get_variant_groups:
                return
            _group_order, groups = get_variant_groups()
            ginfo = groups.get((wood, size))
            if not ginfo:
                return
            tree.item(rowid, values=_child_row_values(m, wood, size, ginfo))

        def _refresh_market_children(market_code: str) -> None:
            for cid in tree.get_children(market_code):
                _refresh_child_row(cid)

        # ---------- Inline edit ----------
        def _begin_edit_markup(rowid: str) -> None:
            m = next((x for x in state["markets"] if x.code == rowid), None)
            if not m or m.is_base:
                return
            bbox = tree.bbox(rowid, column="markup")
            if not bbox:
                return
            x, y, w, h = bbox
            ed_var = tk.StringVar(value=f"{float(m.markup_percent):.1f}")
            ed = ttk.Spinbox(
                tree, from_=-50.0, to=200.0, increment=0.5,
                textvariable=ed_var, format="%.1f", justify="right",
            )
            ed.place(x=x, y=y, width=w, height=h)
            ed.focus_set()
            ed.selection_range(0, "end")

            def _commit(_evt=None) -> None:
                raw = (ed_var.get() or "").strip().replace(",", ".")
                try:
                    pct = float(raw)
                except ValueError:
                    ed.destroy()
                    return
                try:
                    update_market_markup(m.code, pct)
                    m.markup_percent = pct
                    self.enqueue_log(f"[rynki] {m.code}: markup zapisany ({pct:+.1f}%).")
                except Exception as exc:
                    self.enqueue_log(f"[rynki] BLAD zapisu {m.code}: {exc}")
                ed.destroy()
                _render()
                _refresh_market_children(m.code)

            def _cancel(_evt=None) -> None:
                ed.destroy()

            ed.bind("<Return>", _commit)
            ed.bind("<KP_Enter>", _commit)
            ed.bind("<FocusOut>", _commit)
            ed.bind("<Escape>", _cancel)

        def _begin_edit_manual(rowid: str) -> None:
            if not _is_child_iid(rowid):
                return
            market_code, gk = rowid.split("::", 1)
            parsed = parse_group_key(gk)
            if not parsed:
                return
            wood, size = parsed
            m = next((x for x in state["markets"] if x.code == market_code), None)
            if not m:
                return
            bbox = tree.bbox(rowid, column="manual")
            if not bbox:
                return
            x, y, w, h = bbox
            current = get_market_variant_price(market_code, wood, size) or ""
            ed_var = tk.StringVar(value=current)
            ed = ttk.Entry(tree, textvariable=ed_var, justify="right")
            ed.place(x=x, y=y, width=max(w, 72), height=h)
            ed.focus_set()
            ed.selection_range(0, "end")

            def _commit(_evt=None) -> None:
                raw = (ed_var.get() or "").strip().replace(",", ".")
                try:
                    if raw:
                        val = float(raw)
                        if val <= 0:
                            raise ValueError("cena <= 0")
                        set_market_variant_price(market_code, wood, size, f"{val:.2f}")
                        self.enqueue_log(
                            f"[rynki] {market_code} {wood} {size}: cena reczna {val:.2f}."
                        )
                    else:
                        set_market_variant_price(market_code, wood, size, None)
                        self.enqueue_log(
                            f"[rynki] {market_code} {wood} {size}: usunieto cene reczna (auto z markup)."
                        )
                except ValueError:
                    messagebox.showerror(
                        APP_TITLE, "Cena musi byc dodatnia liczba (puste = auto).", parent=dialog_parent,
                    )
                    ed.destroy()
                    return
                except Exception as exc:
                    self.enqueue_log(f"[rynki] BLAD zapisu ceny {market_code}: {exc}")
                ed.destroy()
                _refresh_child_row(rowid)

            def _cancel(_evt=None) -> None:
                ed.destroy()

            ed.bind("<Return>", _commit)
            ed.bind("<KP_Enter>", _commit)
            ed.bind("<FocusOut>", _commit)
            ed.bind("<Escape>", _cancel)

        def _on_tree_open(_event: Any) -> None:
            sel = tree.selection()
            rowid = sel[0] if sel else tree.focus()
            if not rowid or _is_child_iid(rowid):
                return
            state["expanded"].add(rowid)
            _ensure_market_children(rowid)

        def _on_tree_close(_event: Any) -> None:
            sel = tree.selection()
            rowid = sel[0] if sel else tree.focus()
            if not rowid or _is_child_iid(rowid):
                return
            state["expanded"].discard(rowid)

        def _on_double_click(event: Any) -> None:
            rowid = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if not rowid:
                return
            try:
                col_idx = int(col_id.lstrip("#")) - 1
            except (ValueError, AttributeError):
                return
            if _is_child_iid(rowid):
                if 0 <= col_idx < len(cols) and cols[col_idx] == "manual":
                    _begin_edit_manual(rowid)
                return
            if 0 <= col_idx < len(cols) and cols[col_idx] == "markup":
                _begin_edit_markup(rowid)

        tree.bind("<Double-1>", _on_double_click)
        tree.bind("<<TreeviewOpen>>", _on_tree_open)
        tree.bind("<<TreeviewClose>>", _on_tree_close)

        filter_var.trace_add("write", lambda *_a: _render())
        sample_var.trace_add("write", lambda *_a: _render())

        _render()

        # ---------- Bottom bar ----------
        ttk.Separator(parent, orient="horizontal").pack(side="bottom", fill="x", padx=12, pady=(0, 0))
        bottom = ttk.Frame(parent)
        bottom.pack(side="bottom", fill="x", padx=12, pady=8)

        # ---------- Buttons (refresh in-place) ----------
        def _do_discover() -> None:
            self.set_status("Pobieram dane rynkow z Shopify...")
            def _worker() -> None:
                try:
                    updated = discover_shopify_market_ids(logger=self.enqueue_log)
                    matched_codes = [m.code for m in updated if m.shopify_price_list_gid]
                    not_matched = [
                        m.code for m in updated
                        if not m.is_base and not m.shopify_price_list_gid
                    ]
                    self.root.after(0, _reload_from_disk)
                    self.root.after(
                        0, lambda: messagebox.showinfo(
                            APP_TITLE,
                            "Pobrano dane rynkow z Shopify.\n\n"
                            f"Dopasowane: {', '.join(matched_codes) or '(brak)'}\n"
                            f"Niedopasowane: {', '.join(not_matched) or '(brak)'}\n\n"
                            "Tabela zostala odswiezona.",
                            parent=dialog_parent,
                        )
                    )
                except Exception as exc:
                    self.enqueue_log(f"[markets] BLAD discover: {exc}")
                    self.root.after(
                        0, lambda e=exc: messagebox.showerror(
                            APP_TITLE,
                            "Nie udalo sie pobrac rynkow z Shopify.\n\n"
                            f"{e}\n\n"
                            "Mozliwa przyczyna: brak scope 'read_markets'/'write_markets' "
                            "w .env oraz shopify.app.toml. Po dodaniu uruchom: "
                            "cd cursor-api && npm run oauth",
                            parent=dialog_parent,
                        )
                    )
                finally:
                    self.root.after(0, lambda: self.set_status("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        def _do_push_all() -> None:
            if not messagebox.askyesno(
                APP_TITLE,
                "Wypchnac markupy WSZYSTKICH rynkow (oprocz PL) do Shopify?\n\n"
                "Wymaga: scope 'write_markets' + wczesniej uruchomionego 'Pobierz dane rynkow'.",
                parent=dialog_parent,
            ):
                return
            self.set_status("Pushuje markupy do Shopify...")
            def _worker() -> None:
                try:
                    pushed: list[str] = []
                    skipped: list[str] = []
                    failed: list[str] = []
                    for m in load_markets():
                        if m.is_base:
                            continue
                        try:
                            res = push_markup_to_shopify(m.code, logger=self.enqueue_log)
                            if res.get("ok"):
                                pushed.append(m.code)
                            else:
                                skipped.append(f"{m.code}: {res.get('reason','')}")
                        except Exception as e:
                            failed.append(f"{m.code}: {e}")
                            self.enqueue_log(f"[markets] BLAD push {m.code}: {e}")
                    self.root.after(0, _reload_from_disk)
                    self.root.after(0, lambda: messagebox.showinfo(
                        APP_TITLE,
                        f"Push zakonczony.\n\nWyslano: {', '.join(pushed) or '-'}\n"
                        f"Pominieto: {len(skipped)} (szczegoly w logu)\n"
                        f"Bledow: {len(failed)} (szczegoly w logu)\n\n"
                        "Tabela zostala odswiezona.",
                        parent=dialog_parent,
                    ))
                finally:
                    self.root.after(0, lambda: self.set_status("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        def _do_pull_markups() -> None:
            self.set_status("Pobieram markupy z Shopify...")
            def _worker() -> None:
                try:
                    updated = discover_shopify_market_ids(logger=self.enqueue_log)
                    lines = [
                        f"  {m.code}: {m.markup_percent:+.1f}%"
                        for m in updated if not m.is_base and m.shopify_price_list_gid
                    ]
                    skipped = [
                        m.code for m in updated
                        if not m.is_base and not m.shopify_price_list_gid
                    ]
                    msg = "Markupy zsynchronizowane z Shopify:\n\n" + (
                        "\n".join(lines) if lines else "(brak dopasowanych rynkow)"
                    )
                    if skipped:
                        msg += f"\n\nPominieto (brak GID): {', '.join(skipped)}"
                    msg += "\n\nTabela zostala odswiezona."
                    self.root.after(0, _reload_from_disk)
                    self.root.after(
                        0, lambda m=msg: messagebox.showinfo(APP_TITLE, m, parent=dialog_parent)
                    )
                except Exception as exc:
                    self.enqueue_log(f"[markets] BLAD pull markup: {exc}")
                    self.root.after(
                        0, lambda e=exc: messagebox.showerror(
                            APP_TITLE,
                            "Nie udalo sie pobrac markupow z Shopify.\n\n"
                            f"{e}\n\n"
                            "Sprawdz czy masz scope 'read_markets'.",
                            parent=dialog_parent,
                        )
                    )
                finally:
                    self.root.after(0, lambda: self.set_status("Gotowy."))
            threading.Thread(target=_worker, daemon=True).start()

        ttk.Button(bottom, text="Pobierz dane rynkow z Shopify", command=_do_discover).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bottom, text="Pobierz markupy z Shopify", command=_do_pull_markups).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(bottom, text="Wyslij markupy do Shopify", command=_do_push_all).pack(side="left")

    # ---------------------- Dziennik / dlugie operacje ----------------------

    def begin_long_operation_ui(self,
        title: str,
        initial_msg: str,
        *,
        transient_for: tk.Misc | None = None,
    ) -> tuple[threading.Event, Callable[[str], None], Callable[[], None]]:
        """Okno z paskiem (indeterminate) + Anuluj. Zwraca (event, set_msg, close)."""
        cancel_ev = threading.Event()
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        if transient_for is not None:
            dlg.transient(transient_for)
        else:
            dlg.transient(self.root)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=16)
        frm.pack(fill="both")
        lbl = ttk.Label(frm, text=initial_msg, wraplength=440)
        lbl.pack(anchor="w")
        pb = ttk.Progressbar(frm, mode="indeterminate", length=400)
        pb.pack(fill="x", pady=(10, 8))
        pb.start(12)
        ttk.Button(frm, text="Anuluj", command=cancel_ev.set).pack(anchor="e")
        position_toplevel_screen_center(dlg, 480, 170)
        dlg.update_idletasks()

        def set_msg(msg: str) -> None:
            def _apply() -> None:
                try:
                    lbl.configure(text=msg)
                except tk.TclError:
                    pass

            self.root.after(0, _apply)

        def close_ui() -> None:
            def _close() -> None:
                try:
                    pb.stop()
                    dlg.destroy()
                except tk.TclError:
                    pass

            self.root.after(0, _close)

        return cancel_ev, set_msg, close_ui

    # ---------------------- Change prices ----------------------
    def start_flow(self) -> None:
        self.set_status("Pobieram wzorcowe warianty...")
        cancel_ev, set_msg, close_ui = self.begin_long_operation_ui(
            "Pobieranie wariantow i cen",
            "Laczenie ze sklepem i skanowanie katalogu...",
        )

        def fetch_and_open() -> None:
            try:
                rows = get_reference_variant_rows(
                    logger=self.enqueue_log,
                    should_cancel=cancel_ev.is_set,
                    on_catalog_progress=set_msg,
                )
            except Exception as exc:
                close_ui()
                self.enqueue_log(f"[BLAD] {exc}")
                self.root.after(
                    0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Nie udalo sie pobrac wariantow:\n{e}")
                )
                self.root.after(0, lambda: self.set_status("Blad pobierania wariantow."))
                return
            close_ui()
            self.root.after(0, lambda: self.open_dialog(rows))
            self.root.after(0, lambda: self.set_status("Gotowy."))

        threading.Thread(target=fetch_and_open, daemon=True).start()

    def open_dialog(self, rows: list[dict]) -> None:
        if not rows:
            messagebox.showwarning(APP_TITLE, "Produkt referencyjny nie ma zadnych wariantow.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Zmien ceny (wszystkie produkty)")
        position_toplevel_screen_center(dlg, 760, 680)
        dlg.minsize(640, 480)
        dlg.transient(self.root)
        dlg.grab_set()

        price_title = "Zmien ceny (wszystkie produkty)"
        markets_title = "Rynki - markup % nad cena PL"

        price_frame = ttk.Frame(dlg)
        price_frame.pack(side="top", fill="both", expand=True)

        markets_frame = ttk.Frame(dlg)
        markets_built = False

        header = ttk.Label(
            price_frame,
            text=(
                "Wpisz NOWE ceny. Puste pola = brak zmiany.\n"
                "Ceny zostana ustawione w KAZDYM produkcie typu 'Obraz' na sklepie, ktory ma wariant\n"
                "pasujacy do wybranego klucza (Rodzaj drewna / Rozmiar / Kolor).\n"
                "W nawiasie przy obecnej cenie: sugerowana cena z kalkulatora kosztow (M=A4, L=A3+, XL=A2)."
            ),
            wraplength=720,
            justify="left",
            foreground="#444",
        )
        header.pack(side="top", fill="x", padx=12, pady=(10, 6))

        # ---------------- Przelacznik widoku (Globalny / Szczegolowy) ----------------
        view_bar = ttk.Frame(price_frame)
        view_bar.pack(side="top", fill="x", padx=12, pady=(0, 6))

        btn_refresh_prices = ttk.Button(view_bar, text="Pobierz aktualne ceny")
        btn_refresh_prices.pack(side="right", padx=(8, 0))
        btn_apply_calc = ttk.Button(view_bar, text="Zastosuj ceny z nawiasu")
        btn_apply_calc.pack(side="right", padx=(8, 0))
        btn_markets = ttk.Button(view_bar, text="Rynki...")
        btn_markets.pack(side="right", padx=(8, 0))

        ttk.Label(view_bar, text="Widok:", foreground="#444").pack(side="left", padx=(0, 8))

        view_mode = tk.StringVar(value="global")
        btn_global = ttk.Button(view_bar, text="Globalny", width=14)
        btn_detail = ttk.Button(view_bar, text="Szczegolowy", width=14)
        btn_global.pack(side="left", padx=(0, 4))
        btn_detail.pack(side="left")

        view_hint = ttk.Label(view_bar, text="", foreground="#777")
        view_hint.pack(side="left", padx=(12, 0))

        btns = ttk.Frame(dlg)
        btns.pack(side="bottom", fill="x", padx=12, pady=10)

        price_footer_sep = ttk.Separator(dlg, orient="horizontal")
        price_footer_sep.pack(side="bottom", fill="x")

        content = ttk.Frame(price_frame)
        content.pack(side="top", fill="both", expand=True, padx=(12, 0), pady=(0, 6))

        canvas = tk.Canvas(content, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y", padx=(0, 6))

        inner = ttk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(_event: tk.Event) -> None:  # type: ignore[type-arg]
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:  # type: ignore[type-arg]
            canvas.itemconfigure(inner_window, width=event.width)

        def _on_mousewheel(event: tk.Event) -> None:  # type: ignore[type-arg]
            delta = int(-1 * (event.delta / 120)) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _show_prices() -> None:
            markets_frame.pack_forget()
            price_frame.pack(side="top", fill="both", expand=True)
            price_footer_sep.pack(side="bottom", fill="x")
            btns.pack(side="bottom", fill="x", padx=12, pady=10)
            try:
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
            except tk.TclError:
                pass
            dlg.title(price_title)

        def _show_markets() -> None:
            nonlocal markets_built

            def _get_variant_groups() -> tuple[list[tuple[str, str]], dict[tuple[str, str], dict]]:
                return group_order, groups

            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            price_frame.pack_forget()
            price_footer_sep.pack_forget()
            btns.pack_forget()
            if not markets_built:
                self.build_markets_panel(
                    markets_frame,
                    dlg,
                    on_back=_show_prices,
                    get_variant_groups=_get_variant_groups,
                )
                markets_built = True
            markets_frame.pack(side="top", fill="both", expand=True)
            dlg.title(markets_title)

        btn_markets.configure(command=_show_markets)

        def _on_dialog_close() -> None:
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _on_dialog_close)

        _COL_CUR_W = 22
        _COL_NEW_W = 10
        _LABEL_MINSIZE = 260

        calc_price_cache: dict[tuple[str, str], float | None] = {}

        def _cached_calc_price(wood: str, size: str) -> float | None:
            key = (wood.strip(), size.strip())
            if key not in calc_price_cache:
                calc_price_cache[key] = calc_sell_price_for_shop_labels(wood, size)
            return calc_price_cache[key]

        def _fmt_shop_price_with_calc(shop_txt: str, calc_price: float | None) -> str:
            if calc_price is None:
                return shop_txt
            calc_txt = f"{calc_price:.2f}"
            if not shop_txt or shop_txt == "-":
                return f"({calc_txt})"
            return f"{shop_txt} ({calc_txt})"

        # ---------------- Przygotowanie danych dla obu widokow ----------------
        # Stan zachowywany przy przelaczaniu widoku - ostatnio wpisana wartosc.
        detail_values: dict[tuple[str, ...], str] = {row["key"]: "" for row in rows}

        # Grupowanie do widoku globalnego: klucz = (wood, size) z labela.
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        group_order: list[tuple[str, str]] = []

        def _rebuild_groups() -> None:
            nonlocal groups, group_order
            groups = {}
            group_order = []
            for row in rows:
                parts = [p.strip() for p in str(row["label"]).split(" / ")]
                wood = parts[0] if len(parts) >= 1 else ""
                size = parts[1] if len(parts) >= 2 else ""
                gkey = (wood, size)
                if gkey not in groups:
                    groups[gkey] = {
                        "label": f"{wood} {size}".strip() or "(bez nazwy)",
                        "rows": [],
                        "prices": [],
                    }
                    group_order.append(gkey)
                groups[gkey]["rows"].append(row)
                if row.get("price"):
                    groups[gkey]["prices"].append(str(row["price"]))

        _rebuild_groups()

        # Stan widoku globalnego.
        global_values: dict[tuple[str, str], str] = {gkey: "" for gkey in group_order}

        detail_entries: list[tuple[tuple[str, ...], tk.StringVar]] = []
        global_entries: list[tuple[tuple[str, str], tk.StringVar]] = []

        # ---------------- Renderowanie widokow ----------------
        def _clear_inner() -> None:
            for child in inner.winfo_children():
                child.destroy()
            detail_entries.clear()
            global_entries.clear()

        def _render_detail() -> None:
            _clear_inner()
            grid = ttk.Frame(inner)
            grid.pack(fill="x", padx=10, pady=(2, 6), anchor="w")
            grid.columnconfigure(0, minsize=_LABEL_MINSIZE)
            grid.columnconfigure(1, minsize=110)
            grid.columnconfigure(2, minsize=100)

            ttk.Label(
                grid,
                text="Wariant (Rodzaj drewna / Rozmiar / Kolor)",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
            ttk.Label(
                grid,
                text="Obecna cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_CUR_W,
            ).grid(row=0, column=1, sticky="e", padx=(0, 12))
            ttk.Label(
                grid,
                text="Nowa cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_NEW_W,
            ).grid(row=0, column=2, sticky="e")

            ttk.Separator(grid, orient="horizontal").grid(
                row=1, column=0, columnspan=3, sticky="ew", pady=(0, 2)
            )

            for i, row in enumerate(rows):
                r = 2 + 2 * i
                parts = [p.strip() for p in str(row["label"]).split(" / ")]
                wood = parts[0] if len(parts) >= 1 else ""
                size = parts[1] if len(parts) >= 2 else ""
                calc_price = _cached_calc_price(wood, size)
                ttk.Label(grid, text=row["label"]).grid(
                    row=r, column=0, sticky="w", padx=(0, 16), pady=4
                )
                ttk.Label(
                    grid,
                    text=_fmt_shop_price_with_calc(row["price"] or "-", calc_price),
                    foreground="#777",
                    anchor="e",
                    width=_COL_CUR_W,
                ).grid(row=r, column=1, sticky="e", padx=(0, 12))
                var = tk.StringVar(value=detail_values.get(row["key"], ""))

                def _sync(_a: str, _b: str, _c: str, _k=row["key"], _v=var) -> None:
                    detail_values[_k] = _v.get()

                var.trace_add("write", _sync)
                ttk.Entry(grid, textvariable=var, width=_COL_NEW_W, justify="right").grid(
                    row=r, column=2, sticky="e"
                )
                detail_entries.append((row["key"], var))
                if i < len(rows) - 1:
                    ttk.Separator(grid, orient="horizontal").grid(
                        row=r + 1, column=0, columnspan=3, sticky="ew"
                    )

        def _render_global() -> None:
            _clear_inner()
            grid = ttk.Frame(inner)
            grid.pack(fill="x", padx=10, pady=(2, 6), anchor="w")
            grid.columnconfigure(0, minsize=_LABEL_MINSIZE)
            grid.columnconfigure(1, minsize=180)
            grid.columnconfigure(2, minsize=100)

            ttk.Label(
                grid,
                text="Grupa (Rodzaj drewna + Rozmiar)",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)
            ttk.Label(
                grid,
                text="Obecna cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_CUR_W,
            ).grid(row=0, column=1, sticky="e", padx=(0, 12))
            ttk.Label(
                grid,
                text="Nowa cena",
                font=("Segoe UI", 9, "bold"),
                anchor="e",
                width=_COL_NEW_W,
            ).grid(row=0, column=2, sticky="e")

            ttk.Separator(grid, orient="horizontal").grid(
                row=1, column=0, columnspan=3, sticky="ew", pady=(0, 2)
            )

            for i, gkey in enumerate(group_order):
                r = 2 + 2 * i
                ginfo = groups[gkey]
                color_count = len(ginfo["rows"])
                label_txt = f"{ginfo['label']}   ({color_count} kolor.)"
                ttk.Label(grid, text=label_txt).grid(
                    row=r, column=0, sticky="w", padx=(0, 16), pady=4
                )

                uniq_prices = sorted(set(ginfo["prices"]))
                if not uniq_prices:
                    cur_txt = "-"
                elif len(uniq_prices) == 1:
                    cur_txt = uniq_prices[0]
                else:
                    cur_txt = f"rozne ({len(uniq_prices)})"
                wood, size = gkey
                calc_price = _cached_calc_price(wood, size)
                ttk.Label(
                    grid,
                    text=_fmt_shop_price_with_calc(cur_txt, calc_price),
                    foreground="#777",
                    anchor="e",
                    width=_COL_CUR_W,
                ).grid(row=r, column=1, sticky="e", padx=(0, 12))

                var = tk.StringVar(value=global_values.get(gkey, ""))

                def _sync(_a: str, _b: str, _c: str, _k=gkey, _v=var) -> None:
                    global_values[_k] = _v.get()

                var.trace_add("write", _sync)
                ttk.Entry(grid, textvariable=var, width=_COL_NEW_W, justify="right").grid(
                    row=r, column=2, sticky="e"
                )
                global_entries.append((gkey, var))
                if i < len(group_order) - 1:
                    ttk.Separator(grid, orient="horizontal").grid(
                        row=r + 1, column=0, columnspan=3, sticky="ew"
                    )

        def _set_view(mode: str) -> None:
            view_mode.set(mode)
            if mode == "global":
                btn_global.state(["disabled"])
                btn_detail.state(["!disabled"])
                view_hint.configure(
                    text="Jedna cena = wszystkie warianty kolorystyczne w grupie."
                )
                _render_global()
            else:
                btn_detail.state(["disabled"])
                btn_global.state(["!disabled"])
                view_hint.configure(text="Edycja kazdego wariantu osobno.")
                _render_detail()
            canvas.yview_moveto(0.0)

        btn_global.configure(command=lambda: _set_view("global"))
        btn_detail.configure(command=lambda: _set_view("detail"))

        def _apply_calc_prices_from_parentheses() -> None:
            """Wpisuje do 'Nowa cena' sugerowane ceny z kalkulatora (wartości w nawiasie)."""
            count = 0
            if view_mode.get() == "global":
                for gkey, var in global_entries:
                    calc = _cached_calc_price(gkey[0], gkey[1])
                    if calc is None or calc <= 0:
                        continue
                    txt = f"{calc:.2f}"
                    var.set(txt)
                    global_values[gkey] = txt
                    count += 1
            else:
                row_by_key = {row["key"]: row for row in rows}
                for key, var in detail_entries:
                    row = row_by_key.get(key)
                    if not row:
                        continue
                    parts = [p.strip() for p in str(row["label"]).split(" / ")]
                    calc = _cached_calc_price(
                        parts[0] if parts else "",
                        parts[1] if len(parts) > 1 else "",
                    )
                    if calc is None or calc <= 0:
                        continue
                    txt = f"{calc:.2f}"
                    var.set(txt)
                    detail_values[key] = txt
                    count += 1
            if count == 0:
                messagebox.showinfo(
                    APP_TITLE,
                    "Brak cen z kalkulatora do zastosowania.",
                    parent=dlg,
                )

        btn_apply_calc.configure(command=_apply_calc_prices_from_parentheses)

        def _sync_value_dicts_after_refresh() -> None:
            valid_detail = {row["key"] for row in rows}
            for k in list(detail_values.keys()):
                if k not in valid_detail:
                    del detail_values[k]
            for row in rows:
                if row["key"] not in detail_values:
                    detail_values[row["key"]] = ""
            valid_global = set(group_order)
            for k in list(global_values.keys()):
                if k not in valid_global:
                    del global_values[k]
            for gkey in group_order:
                if gkey not in global_values:
                    global_values[gkey] = ""

        def on_fetch_live_prices() -> None:
            try:
                btn_refresh_prices.state(["disabled"])
            except tk.TclError:
                pass
            self.set_status("Pobieram aktualne ceny ze sklepu...")
            cancel_ev, set_msg, close_prog = self.begin_long_operation_ui(
                "Aktualizacja cen w oknie",
                "Skanowanie katalogu produktow...",
                transient_for=dlg,
            )

            def worker() -> None:
                try:
                    new_rows = get_reference_variant_rows(
                        logger=self.enqueue_log,
                        should_cancel=cancel_ev.is_set,
                        on_catalog_progress=set_msg,
                    )
                except Exception as exc:
                    close_prog()
                    self.root.after(
                        0,
                        lambda: self.enqueue_log(f"[BLAD] {exc}"),
                    )
                    self.root.after(
                        0,
                        lambda e=exc: messagebox.showerror(
                            APP_TITLE,
                            f"Nie udalo sie pobrac cen:\n{e}",
                            parent=dlg,
                        ),
                    )
                    self.root.after(0, _fetch_done)
                    return

                close_prog()

                def apply() -> None:
                    rows.clear()
                    rows.extend(new_rows)
                    _rebuild_groups()
                    _sync_value_dicts_after_refresh()
                    _set_view(view_mode.get())
                    _fetch_done()

                self.root.after(0, apply)

            def _fetch_done() -> None:
                try:
                    btn_refresh_prices.state(["!disabled"])
                except tk.TclError:
                    pass
                self.set_status("Gotowy.")

            threading.Thread(target=worker, daemon=True).start()

        btn_refresh_prices.configure(command=on_fetch_live_prices)

        # Domyslnie startujemy w widoku Globalnym (zgodnie z prosba uzytkownika).
        _set_view("global")

        def on_cancel() -> None:
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            dlg.destroy()

        def on_apply() -> None:
            mapping: dict[tuple[str, ...], str] = {}
            mode = view_mode.get()

            if mode == "detail":
                for key, var in detail_entries:
                    val = var.get().strip().replace(",", ".")
                    if not val:
                        continue
                    try:
                        float(val)
                    except ValueError:
                        messagebox.showerror(
                            APP_TITLE,
                            f"Niepoprawna cena: '{val}' dla wariantu {' / '.join(key)}",
                        )
                        return
                    mapping[key] = val
            else:
                # Globalny: jedna cena -> wszystkie warianty kolorystyczne w grupie.
                touched_groups = 0
                for gkey, var in global_entries:
                    val = var.get().strip().replace(",", ".")
                    if not val:
                        continue
                    try:
                        float(val)
                    except ValueError:
                        messagebox.showerror(
                            APP_TITLE,
                            f"Niepoprawna cena: '{val}' dla grupy {groups[gkey]['label']}",
                        )
                        return
                    for row in groups[gkey]["rows"]:
                        mapping[row["key"]] = val
                    touched_groups += 1
                if touched_groups and not mapping:
                    messagebox.showwarning(
                        APP_TITLE, "Wybrane grupy nie maja zadnych wariantow do aktualizacji."
                    )
                    return

            if not mapping:
                messagebox.showwarning(APP_TITLE, "Nie podano zadnej nowej ceny.")
                return

            if mode == "global":
                groups_count = sum(
                    1 for _g, var in global_entries if var.get().strip()
                )
                msg = (
                    f"Tryb GLOBALNY: zaktualizowac {groups_count} grup(y) "
                    f"= {len(mapping)} wariant(y) we WSZYSTKICH produktach typu 'Obraz' na sklepie?\n\n"
                    "Operacji nie mozna cofnac automatycznie."
                )
            else:
                msg = (
                    f"Zaktualizowac {len(mapping)} wariant(y) we WSZYSTKICH produktach "
                    "typu 'Obraz' na sklepie?\n\n"
                    "Operacji nie mozna cofnac automatycznie."
                )
            confirm = messagebox.askyesno(APP_TITLE, msg)
            if not confirm:
                return
            try:
                canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            dlg.destroy()
            self.run_bulk_update(mapping)

        ttk.Button(btns, text="Anuluj", command=on_cancel, width=16).pack(side="right")
        ttk.Button(btns, text="Zatwierdz", command=on_apply, width=16).pack(side="right", padx=8)

    def run_bulk_update(self, mapping: dict[tuple[str, ...], str]) -> None:
        self.set_status("Aktualizuje ceny... (patrz log)")
        self.append_log("\n=== ZMIANA CEN ===")
        for key, price in mapping.items():
            self.append_log(f"  {' / '.join(key)} -> {price}")

        cancel_ev, set_msg, close_prog = self.begin_long_operation_ui(
            "Masowa zmiana cen",
            "Ladowanie katalogu i aktualizacja wariantow...",
        )

        def worker() -> None:
            try:
                summary = update_all_product_prices(
                    option_values_to_price=mapping,
                    logger=self.enqueue_log,
                    should_cancel=cancel_ev.is_set,
                    on_progress=set_msg,
                )
                close_prog()
                msg_lines = (
                    "Zmiana cen zakonczona.\n\n"
                    f"Produktow przetworzonych: {summary['products_total']}\n"
                    f"Zaktualizowanych wariantow: {summary['variants_updated']}\n"
                    f"Pominietych: {summary['variants_skipped']}\n"
                    f"Bledow: {len(summary['errors'])}"
                )

                def _done() -> None:
                    append_activity(
                        "zmienceny",
                        f"Ceny hurtowe: wariantow {summary['variants_updated']}, "
                        f"bledow {len(summary['errors'])}.",
                    )
                    notify_long_task_done(self.root)
                    self.set_status(
                        f"Ceny zaktualizowane: {summary['variants_updated']} "
                        f"(bledow: {len(summary['errors'])})"
                    )
                    messagebox.showinfo(APP_TITLE, msg_lines)

                self.root.after(0, _done)
            except OperationCancelled as exc:
                close_prog()
                self.enqueue_log(f"[ceny] Przerwano: {exc}")
                self.root.after(0, lambda: self.set_status("Zmiana cen przerwana."))
                self.root.after(
                    0,
                    lambda e=str(exc): messagebox.showinfo(
                        APP_TITLE, f"Przerwano operacje.\n\n{e}"
                    ),
                )
            except Exception as exc:
                close_prog()
                self.enqueue_log(f"[BLAD] {exc}")
                self.root.after(0, lambda: self.set_status("Blad - zobacz log."))
                self.root.after(0, lambda e=exc: messagebox.showerror(APP_TITLE, f"Blad:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------- Log plumbing ----------------------


def open_price_change_dialog(
    parent: tk.Misc,
    *,
    enqueue_log: Callable[[str], None],
    set_status: Callable[[str], None],
    append_log: Callable[[str], None] | None = None,
    standalone: bool = False,
    auto_start: bool = True,
) -> tk.Misc:
    """Otwiera flow zmiany cen. W standalone parent to glowne okno (tk.Tk)."""
    if standalone and isinstance(parent, tk.Tk):
        parent.title(APP_TITLE)
        position_toplevel_screen_center(parent, 760, 680)
        parent.minsize(640, 480)
    ctx = _PriceChangeCtx(
        parent,
        enqueue_log=enqueue_log,
        set_status=set_status,
        append_log=append_log,
    )
    if auto_start:
        parent.after(100, ctx.start_flow)
    return parent
