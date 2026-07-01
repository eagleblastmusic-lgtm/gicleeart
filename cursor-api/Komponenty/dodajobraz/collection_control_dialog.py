"""Okno «Kontrola kolekcji» — zestawienie produktow vs kolekcje Shopify."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .collection_control import (
    evaluate_collection_row_status,
    load_collection_control_rows,
    refresh_product_collection_titles,
    remove_product_from_custom_collection,
)
from .create import assign_products_to_collection_title
from . import shopify_client as sc

APP_TITLE = "Dodaj obraz"


def _unique_artist_count(rows: list[dict[str, Any]]) -> int:
    return len(
        {
            (r.get("artist") or "").strip()
            for r in rows
            if (r.get("artist") or "").strip()
        }
    )


def open_collection_control_dialog(
    parent: tk.Misc,
    *,
    enqueue_log: Callable[[str], None],
    set_status: Callable[[str], None],
) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Kontrola kolekcji")
    position_toplevel_screen_center(dlg, 1180, 700)
    dlg.minsize(900, 500)
    dlg.transient(parent)

    state: dict[str, Any] = {
        "rows": [],
        "collections": [],
        "row_by_iid": {},
        "cancel": False,
    }

    header = ttk.Frame(dlg, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    progress_var = tk.StringVar(value="Kliknij «Odswiez z Shopify», aby pobrac dane.")
    ttk.Label(header, textvariable=progress_var, foreground="#444", wraplength=1050).pack(
        anchor="w"
    )

    filter_bar = ttk.Frame(dlg, padding=(12, 0, 12, 6))
    filter_bar.pack(fill="x")
    only_issues_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        filter_bar,
        text="Tylko problemy (bez OK)",
        variable=only_issues_var,
        command=lambda: _refresh_tree(),
    ).pack(side="left")
    ttk.Label(filter_bar, text="Filtr:").pack(side="left", padx=(16, 4))
    filter_var = tk.StringVar(value="")
    filter_entry = ttk.Entry(filter_bar, textvariable=filter_var, width=36)
    filter_entry.pack(side="left")
    filter_var.trace_add("write", lambda *_: _refresh_tree())
    count_var = tk.StringVar(value="")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left", padx=(10, 0))

    table_frame = ttk.Frame(dlg, padding=(12, 0, 12, 6))
    table_frame.pack(fill="both", expand=True)

    cols = (
        "status",
        "artist",
        "painting_title",
        "expected",
        "collections",
        "handle",
    )
    headings = {
        "status": "Status",
        "artist": "Artysta",
        "painting_title": "Tytul",
        "expected": "Kolekcja artysty",
        "collections": "W kolekcjach (Shopify)",
        "handle": "Handle",
    }
    widths = {
        "status": 120,
        "artist": 180,
        "painting_title": 260,
        "expected": 200,
        "collections": 320,
        "handle": 140,
    }

    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18, selectmode="extended")
    for c in cols:
        tree.heading(c, text=headings[c])
        tree.column(c, width=widths[c], anchor="w", stretch=(c in ("painting_title", "collections")))
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    edit = ttk.LabelFrame(dlg, text="Edycja zaznaczonych (Ctrl+klik / Shift+klik)", padding=(12, 8))
    edit.pack(fill="x", padx=12, pady=(0, 6))

    sel_var = tk.StringVar(value="(brak zaznaczenia)")
    ttk.Label(edit, textvariable=sel_var, wraplength=1100).pack(anchor="w")

    row_assign = ttk.Frame(edit)
    row_assign.pack(fill="x", pady=(8, 0))
    ttk.Label(row_assign, text="Przypisz do kolekcji:").pack(side="left")
    coll_var = tk.StringVar(value="")
    coll_combo = ttk.Combobox(row_assign, textvariable=coll_var, width=48, state="normal")
    coll_combo.pack(side="left", padx=(6, 4))
    ttk.Button(row_assign, text="Przypisz zaznaczone", command=lambda: _assign(), width=18).pack(
        side="left", padx=2
    )
    ttk.Button(row_assign, text="Usun z custom", command=lambda: _remove_custom(), width=14).pack(
        side="left", padx=2
    )
    ttk.Button(row_assign, text="Otworz w Shopify", command=lambda: _open_admin(), width=14).pack(
        side="left", padx=(8, 0)
    )

    btn_row = ttk.Frame(dlg, padding=(12, 0, 12, 12))
    btn_row.pack(fill="x")
    refresh_btn = ttk.Button(btn_row, text="Odswiez z Shopify", width=18)
    refresh_btn.pack(side="left")
    ttk.Button(btn_row, text="Zamknij", command=dlg.destroy, width=12).pack(side="right")

    def _selected_rows() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for iid in tree.selection():
            row = state["row_by_iid"].get(iid)
            if row:
                out.append(row)
        return out

    def _selected_row() -> dict[str, Any] | None:
        rows = _selected_rows()
        return rows[0] if rows else None

    def _refresh_tree() -> None:
        tree.delete(*tree.get_children())
        state["row_by_iid"] = {}
        needle = filter_var.get().strip().lower()
        shown = 0
        visible_artists: set[str] = set()
        for row in state["rows"]:
            if only_issues_var.get() and row.get("status") == "OK":
                continue
            hay = " ".join(
                [
                    str(row.get("status") or ""),
                    str(row.get("artist") or ""),
                    str(row.get("painting_title") or ""),
                    str(row.get("expected_collection") or ""),
                    str(row.get("collections") or ""),
                    str(row.get("handle") or ""),
                ]
            ).lower()
            if needle and needle not in hay:
                continue
            iid = str(row["product_id"])
            coll_label = (row.get("shop_collection") or row.get("expected_collection") or "").strip()
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("status"),
                    row.get("artist"),
                    row.get("painting_title"),
                    coll_label,
                    row.get("collections"),
                    row.get("handle"),
                ),
            )
            state["row_by_iid"][iid] = row
            shown += 1
            artist = (row.get("artist") or "").strip()
            if artist:
                visible_artists.add(artist)
        total = len(state["rows"])
        problems = sum(1 for r in state["rows"] if r.get("status") != "OK")
        all_artists = _unique_artist_count(state["rows"])
        parts = [
            f"Widoczne: {shown} / {total}",
            f"problemow: {problems}",
            f"artystow: {all_artists}",
        ]
        if shown != total or only_issues_var.get() or needle:
            parts.append(f"w widoku: {len(visible_artists)}")
        count_var.set(" | ".join(parts))

    def _on_select(_event: tk.Event | None = None) -> None:
        rows = _selected_rows()
        if not rows:
            sel_var.set("(brak zaznaczenia)")
            return
        if len(rows) == 1:
            row = rows[0]
            sel_var.set(
                f"{row.get('product_title')}  |  status: {row.get('status')}  |  "
                f"oczekiwana kolekcja: {row.get('expected_collection') or '—'}"
            )
        else:
            problems = sum(1 for r in rows if r.get("status") != "OK")
            sel_var.set(
                f"Zaznaczono {len(rows)} produkt(ow) (problemow: {problems}). "
                f"«Przypisz zaznaczone» dodaje wszystkie do wybranej kolekcji."
            )
        shop_titles: list[str] = []
        for r in rows:
            st = (r.get("shop_collection") or "").strip()
            if st:
                shop_titles.append(st)
            exp = (r.get("expected_collection") or "").strip()
            if exp:
                shop_titles.append(exp)
        if shop_titles:
            coll_var.set(shop_titles[0])
        elif len(rows) == 1:
            exp = (rows[0].get("expected_collection") or "").strip()
            if exp:
                coll_var.set(exp)

    tree.bind("<<TreeviewSelect>>", _on_select)

    def _update_row_product(pid: int, *, refresh: bool = True) -> None:
        for row in state["rows"]:
            if int(row["product_id"]) != pid:
                continue
            shop, token = sc.load_session()
            catalog = sc.fetch_collection_catalog(shop, token)
            titles = refresh_product_collection_titles(
                shop,
                token,
                pid,
                artist=(row.get("artist") or ""),
                catalog=catalog,
            )
            row["collection_titles"] = sorted(titles, key=str.lower)
            row["collections"] = "; ".join(row["collection_titles"]) if titles else "—"
            ev = evaluate_collection_row_status(
                artist=(row.get("artist") or ""),
                titles=titles,
                catalog=catalog,
            )
            row["status"] = ev["status"]
            row["in_expected"] = ev["in_expected"]
            row["expected_collection_id"] = ev["expected_collection_id"]
            row["expected_kind"] = ev["expected_kind"]
            row["shop_collection"] = ev.get("shop_collection") or ""
            break
        if refresh:
            _refresh_tree()
            _on_select()

    def _assign() -> None:
        rows = _selected_rows()
        title = coll_var.get().strip()
        if not rows:
            messagebox.showwarning(APP_TITLE, "Zaznacz jeden lub wiecej produktow.", parent=dlg)
            return
        if not title:
            messagebox.showwarning(APP_TITLE, "Podaj nazwe kolekcji.", parent=dlg)
            return
        pids = [int(r["product_id"]) for r in rows]
        n = len(pids)
        if n > 1 and not messagebox.askyesno(
            APP_TITLE,
            f"Przypisac {n} produkt(ow) do kolekcji «{title}»?",
            parent=dlg,
        ):
            return

        def worker() -> None:
            try:
                res = assign_products_to_collection_title(
                    collection_title=title,
                    product_ids=pids,
                    logger=enqueue_log,
                )
                added = len(res.get("added") or [])
                already = len(res.get("already") or [])
                failed = res.get("failed") or []
                lines = [
                    f"Kolekcja: «{title}»",
                    f"Dodano: {added}",
                    f"Juz bylo w kolekcji: {already}",
                ]
                if failed:
                    lines.append(f"Bledy: {len(failed)} (szczegoly w logu)")
                    for fail in failed[:5]:
                        enqueue_log(
                            f"[kolekcje] id={fail.get('product_id')}: {fail.get('error')}"
                        )
                summary = "\n".join(lines)

                def _done() -> None:
                    if failed and not added:
                        messagebox.showwarning(APP_TITLE, summary, parent=dlg)
                    else:
                        messagebox.showinfo(APP_TITLE, summary, parent=dlg)
                    for pid in pids:
                        _update_row_product(pid, refresh=False)
                    _refresh_tree()
                    _on_select()

                dlg.after(0, _done)
            except Exception as e:
                dlg.after(
                    0,
                    lambda err=e: messagebox.showerror(APP_TITLE, str(err), parent=dlg),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _remove_custom() -> None:
        rows = _selected_rows()
        title = coll_var.get().strip()
        if not rows or not title:
            messagebox.showwarning(APP_TITLE, "Zaznacz produkt(y) i wpisz kolekcje.", parent=dlg)
            return
        n = len(rows)
        if not messagebox.askyesno(
            APP_TITLE,
            f"Usunac {n} produkt(ow) z custom collection «{title}»?",
            parent=dlg,
        ):
            return
        pids = [int(r["product_id"]) for r in rows]

        def worker() -> None:
            ok, err_n = 0, 0
            for pid in pids:
                try:
                    remove_product_from_custom_collection(
                        product_id=pid,
                        collection_title=title,
                        logger=enqueue_log,
                    )
                    ok += 1
                except Exception as e:
                    err_n += 1
                    enqueue_log(f"[kolekcje] Usuniecie id={pid}: {e}")

            def _done() -> None:
                messagebox.showinfo(
                    APP_TITLE,
                    f"Usunieto: {ok}\nBledy: {err_n}",
                    parent=dlg,
                )
                for pid in pids:
                    _update_row_product(pid, refresh=False)
                _refresh_tree()
                _on_select()

            dlg.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _open_admin() -> None:
        row = _selected_row()
        if row and row.get("admin_url"):
            webbrowser.open(row["admin_url"])

    def _load() -> None:
        state["cancel"] = False
        refresh_btn.configure(state="disabled")

        def worker() -> None:
            try:
                rows, choices = load_collection_control_rows(
                    logger=enqueue_log,
                    on_progress=lambda msg: dlg.after(0, lambda m=msg: progress_var.set(m)),
                    should_cancel=lambda: state["cancel"],
                )
            except sc.OperationCancelled:
                dlg.after(0, lambda: progress_var.set("Przerwano pobieranie."))
                dlg.after(0, lambda: refresh_btn.configure(state="normal"))
                return
            except Exception as e:
                enqueue_log(f"[kolekcje] BLAD: {e}")
                dlg.after(
                    0,
                    lambda err=e: messagebox.showerror(APP_TITLE, str(err), parent=dlg),
                )
                dlg.after(0, lambda: refresh_btn.configure(state="normal"))
                return

            titles = [c["title"] for c in choices]

            def done() -> None:
                state["rows"] = rows
                state["collections"] = choices
                coll_combo["values"] = titles
                problems = sum(1 for r in rows if r.get("status") != "OK")
                n_artists = _unique_artist_count(rows)
                progress_var.set(
                    f"Wczytano {len(rows)} produktow (Obraz), {n_artists} unikalnych artystow. "
                    f"Problemow: {problems}."
                )
                _refresh_tree()
                refresh_btn.configure(state="normal")
                set_status(f"Kontrola kolekcji: {len(rows)} produktow.")

            dlg.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    refresh_btn.configure(command=_load)
    dlg.protocol("WM_DELETE_WINDOW", lambda: (state.update(cancel=True), dlg.destroy()))
