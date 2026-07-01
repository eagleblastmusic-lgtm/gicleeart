"""Sub-view 'Obecne posty' - lista postow z Shopify z auto-fetch przy wejsciu.

Przy zaladowaniu ekranu uruchamia fetch w tle (nie blokuje GUI).
Dwuklik / Enter otwiera artykul w przegladarce (storefront URL).
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast

from . import shopify_blog, storage

_BG = "#f4f4f7"


def build_articles_screen(
    parent: tk.Widget,
    *,
    on_back: Callable[[], None],
) -> tk.Widget:
    outer = tk.Frame(parent, bg=_BG)

    toolbar = tk.Frame(outer, bg=_BG)
    toolbar.pack(fill="x", padx=14, pady=(12, 4))
    ttk.Button(toolbar, text="< Blog", command=on_back).pack(side="left")
    tk.Label(
        toolbar, text="Obecne posty na blogu", bg=_BG,
        font=("Segoe UI", 18, "bold"), fg="#222",
    ).pack(side="left", padx=(14, 0))
    tk.Label(
        toolbar, text="Dwuklik -> otworz w przegladarce. PPM -> wiecej akcji.",
        bg=_BG, fg="#666", font=("Segoe UI", 10),
    ).pack(side="left", padx=(10, 0), pady=(8, 0))

    status_var = tk.StringVar(value="Ladowanie z Shopify...")
    action_row = tk.Frame(outer, bg=_BG)
    action_row.pack(fill="x", padx=14, pady=(4, 6))
    refresh_btn = ttk.Button(action_row, text="🔄 Odswiez z Shopify")
    refresh_btn.pack(side="left")
    tk.Label(action_row, textvariable=status_var, bg=_BG, fg="#555").pack(side="left", padx=(12, 0))

    body = tk.Frame(outer, bg=_BG)
    body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    columns = ("status", "title", "blog", "author", "published", "tags")
    tree = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
    tree.heading("status", text="")
    tree.heading("title", text="Tytul")
    tree.heading("blog", text="Blog")
    tree.heading("author", text="Autor")
    tree.heading("published", text="Publikacja")
    tree.heading("tags", text="Tagi")
    tree.column("status", width=30, anchor="center", stretch=False)
    tree.column("title", width=380, anchor="w")
    tree.column("blog", width=100, anchor="w")
    tree.column("author", width=100, anchor="w")
    tree.column("published", width=110, anchor="w")
    tree.column("tags", width=250, anchor="w")

    vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.tag_configure("draft", foreground="#888")
    tree.tag_configure("published", foreground="#222")

    row_map: dict[str, dict[str, Any]] = {}
    primary_domain = {"host": ""}  # boxed, zeby zamykac

    # Context menu
    menu = tk.Menu(tree, tearoff=0)

    def _selected() -> dict[str, Any] | None:
        sel = tree.selection()
        if not sel:
            return None
        return row_map.get(sel[0])

    def _open_storefront() -> None:
        art = _selected()
        if not art:
            return
        handle = str(art.get("handle") or "")
        blog_handle = str(art.get("_blog_handle") or "")
        if not (handle and blog_handle):
            messagebox.showwarning("Brak handle", "Artykul nie ma jeszcze storefront URL-a.")
            return
        host = primary_domain.get("host") or ""
        url = shopify_blog.article_storefront_url(
            shop="", primary_domain=host, blog_handle=blog_handle, article_handle=handle,
        )
        webbrowser.open(url)

    def _open_admin() -> None:
        art = _selected()
        if not art:
            return
        try:
            shop, _ = shopify_blog.load_session()
        except shopify_blog.ShopifyError as e:
            messagebox.showerror("Sesja", str(e))
            return
        blog_id = int(art.get("_blog_id") or 0)
        article_id = int(art.get("id") or 0)
        if not article_id:
            return
        webbrowser.open(shopify_blog.article_admin_url(shop, blog_id, article_id))

    def _copy_title() -> None:
        art = _selected()
        if not art:
            return
        title = str(art.get("title") or "")
        try:
            tree.clipboard_clear()
            tree.clipboard_append(title)
            tree.update()
        except tk.TclError:
            return
        show_toast(tree, "Skopiowano tytul", duration_ms=1000)

    def _copy_body() -> None:
        art = _selected()
        if not art:
            return
        body_html = str(art.get("body_html") or "")
        if not body_html:
            messagebox.showinfo("Brak body", "Ten snapshot nie zawiera body_html. Kliknij 'Odswiez'.")
            return
        try:
            tree.clipboard_clear()
            tree.clipboard_append(body_html)
            tree.update()
        except tk.TclError:
            return
        show_toast(tree, "Skopiowano body_html", duration_ms=1000)

    menu.add_command(label="🌐 Otworz w przegladarce (storefront)", command=_open_storefront)
    menu.add_command(label="⚙ Otworz w Shopify Admin", command=_open_admin)
    menu.add_separator()
    menu.add_command(label="📋 Kopiuj tytul", command=_copy_title)
    menu.add_command(label="📋 Kopiuj body_html", command=_copy_body)

    def _on_right_click(evt: tk.Event) -> None:
        iid = tree.identify_row(evt.y)
        if iid:
            tree.selection_set(iid)
            tree.focus(iid)
        try:
            menu.tk_popup(evt.x_root, evt.y_root)
        finally:
            menu.grab_release()

    tree.bind("<Button-3>", _on_right_click)
    tree.bind("<Button-2>", _on_right_click)
    tree.bind("<Double-Button-1>", lambda _e: _open_storefront())
    tree.bind("<Return>", lambda _e: _open_storefront())

    def _render_rows(articles: list[dict[str, Any]]) -> None:
        tree.delete(*tree.get_children())
        row_map.clear()
        # Sort: najnowsze publikacje na gorze (po published_at / updated_at).
        def _sort_key(a: dict[str, Any]) -> str:
            return str(a.get("published_at") or a.get("updated_at") or a.get("created_at") or "")

        articles_sorted = sorted(articles, key=_sort_key, reverse=True)
        for a in articles_sorted:
            aid = str(a.get("id") or "")
            if not aid:
                continue
            row_map[aid] = a
            published_at = a.get("published_at") or ""
            published_str = _format_date(published_at) if published_at else "(draft)"
            tags_val = a.get("tags") or ""
            if isinstance(tags_val, list):
                tags_val = ", ".join(tags_val)
            status = "📄" if published_at else "✏️"
            tag = "published" if published_at else "draft"
            tree.insert(
                "", "end", iid=aid,
                values=(
                    status,
                    a.get("title") or "(bez tytulu)",
                    a.get("_blog_title") or "",
                    a.get("author") or "",
                    published_str,
                    str(tags_val)[:140],
                ),
                tags=(tag,),
            )
        status_var.set(f"Postow: {len(articles_sorted)}  |  opublikowane: {sum(1 for a in articles_sorted if a.get('published_at'))}")

    def _load_from_cache() -> None:
        cache = storage.load_articles_cache()
        articles = cache.get("articles") or []
        if articles:
            _render_rows(articles)
            fetched_at = cache.get("fetched_at") or 0
            if fetched_at:
                status_var.set(
                    status_var.get() + f"  |  cache: {datetime.fromtimestamp(fetched_at):%Y-%m-%d %H:%M}"
                )

    def _fetch() -> None:
        refresh_btn.configure(state="disabled", text="Ladowanie...")
        status_var.set("Pobieram z Shopify...")

        def _worker() -> None:
            try:
                shop, token = shopify_blog.load_session()
                articles = shopify_blog.list_all_articles(shop, token)
                storage.save_articles_cache(articles)
                host = shopify_blog.get_shop_primary_domain(shop, token)

                def _ok() -> None:
                    primary_domain["host"] = host
                    _render_rows(articles)

                tree.after(0, _ok)
            except Exception as e:  # noqa: BLE001
                err = str(e)

                def _err() -> None:
                    status_var.set(f"⚠ Blad: {err[:120]}")
                    # Fallback do cache
                    _load_from_cache()

                tree.after(0, _err)
            finally:
                tree.after(0, lambda: refresh_btn.configure(state="normal", text="🔄 Odswiez z Shopify"))

        threading.Thread(target=_worker, daemon=True).start()

    refresh_btn.configure(command=_fetch)

    # Najpierw pokaz cache (szybkie), potem w tle odswiezaj.
    _load_from_cache()
    _fetch()

    return outer


def _format_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        # Shopify zwraca np. "2025-04-20T12:34:56+02:00"
        clean = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso[:16]
