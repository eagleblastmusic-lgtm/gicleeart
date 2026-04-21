"""Planer postow - inline sub-view.

Pokazuje kolejke postow ze storage. Kolumny: status, data zaplanowana, platforma,
jezyk, temat, seria. Filtry: platforma, jezyk, status.

Akcje (przyciski + PPM):
- Edytuj (otwiera dialog z pelnymi polami posta)
- Kopiuj caption (caption + newlines + hashtagi)
- Kopiuj caption TYLKO tekst (bez hashtagow)
- Kopiuj hashtagi
- Otworz obraz (w folderze explorera)
- Oznacz jako: pending / in_progress / done / skipped
- Usun
- Eksport do CSV (cala lista lub tylko zaznaczone)
- 'Otworz generator' -> nowy post

PPM:
- Generuj serie z tego tematu (otwiera generator w trybie series z pre-wypelnionym tematem)
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.tree_sort import attach_sortable_headings

from . import platforms, storage
from .generator_tresci import open_content_generator

_STATUS_LABELS = {
    "pending": "⏳ Oczekuje",
    "in_progress": "▶ W toku",
    "done": "✅ Zrobione",
    "skipped": "⏭ Pominiete",
}

_STATUS_ORDER = ["pending", "in_progress", "done", "skipped"]


def build_planer_screen(
    parent: tk.Widget,
    on_back: Callable[[], None],
) -> tk.Frame:
    """Buduje widok planera w zadanym kontenerze. Zwraca frame (pakowany przez wolajacego)."""
    outer = tk.Frame(parent, bg="#f4f4f7")

    # Toolbar
    toolbar = tk.Frame(outer, bg="#f4f4f7")
    toolbar.pack(fill="x", padx=14, pady=(12, 4))
    ttk.Button(toolbar, text="< Social Media", command=on_back).pack(side="left")
    tk.Label(
        toolbar, text="Planer postow", bg="#f4f4f7",
        font=("Segoe UI", 18, "bold"), fg="#222",
    ).pack(side="left", padx=(14, 0))
    tk.Label(
        toolbar, text="Kolejka zaplanowanych postow - status, filtry, eksport CSV",
        bg="#f4f4f7", fg="#666", font=("Segoe UI", 10),
    ).pack(side="left", padx=(10, 0), pady=(8, 0))

    # Filtry
    filter_bar = tk.Frame(outer, bg="#f4f4f7")
    filter_bar.pack(fill="x", padx=14, pady=(4, 6))

    plat_var = tk.StringVar(value="(wszystkie)")
    lang_var = tk.StringVar(value="(wszystkie)")
    status_var = tk.StringVar(value="(wszystkie)")

    ttk.Label(filter_bar, text="Platforma:").pack(side="left", padx=(0, 4))
    plat_values = ["(wszystkie)"] + [f"{p.icon} {p.label}" for p in platforms.all_platforms()]
    ttk.Combobox(filter_bar, textvariable=plat_var, values=plat_values, state="readonly", width=22).pack(side="left")

    ttk.Label(filter_bar, text="Jezyk:").pack(side="left", padx=(10, 4))
    ttk.Combobox(
        filter_bar, textvariable=lang_var,
        values=["(wszystkie)"] + [c for c, _ in platforms.LANGUAGES],
        state="readonly", width=10,
    ).pack(side="left")

    ttk.Label(filter_bar, text="Status:").pack(side="left", padx=(10, 4))
    ttk.Combobox(
        filter_bar, textvariable=status_var,
        values=["(wszystkie)"] + _STATUS_ORDER,
        state="readonly", width=12,
    ).pack(side="left")

    ttk.Button(filter_bar, text="🔄 Odswiez", command=lambda: _refresh()).pack(side="left", padx=(14, 0))
    ttk.Button(
        filter_bar, text="＋ Nowy post (generator)",
        command=lambda: open_content_generator(outer.winfo_toplevel()),
    ).pack(side="right")
    ttk.Button(
        filter_bar, text="⬇ Eksport CSV",
        command=lambda: _export_csv(outer, _filtered()),
    ).pack(side="right", padx=(0, 6))

    # Treeview
    tv_frame = tk.Frame(outer, bg="#f4f4f7")
    tv_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    cols = ("status", "scheduled", "platform", "lang", "topic", "caption_preview", "series")
    tree = ttk.Treeview(tv_frame, columns=cols, show="headings", selectmode="extended")
    tree.column("status", width=110, anchor="w")
    tree.column("scheduled", width=140, anchor="w")
    tree.column("platform", width=130, anchor="w")
    tree.column("lang", width=60, anchor="center")
    tree.column("topic", width=200, anchor="w")
    tree.column("caption_preview", width=360, anchor="w")
    tree.column("series", width=50, anchor="center")

    vsb = ttk.Scrollbar(tv_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    # Sortowanie per kolumna (klik naglowka toggluje asc/desc)
    attach_sortable_headings(
        tree,
        columns={
            "status": ("Status", "text"),
            "scheduled": ("Data", "date"),
            "platform": ("Platforma", "text"),
            "lang": ("Jezyk", "text"),
            "topic": ("Temat", "text"),
            "caption_preview": ("Caption (skrot)", "text"),
            "series": ("Seria", "text"),
        },
    )

    # Kolory statusow
    tree.tag_configure("done", foreground="#2e7d32", font=("Segoe UI", 9, "overstrike"))
    tree.tag_configure("skipped", foreground="#888", font=("Segoe UI", 9, "overstrike"))
    tree.tag_configure("in_progress", foreground="#1976d2", font=("Segoe UI", 9, "bold"))
    tree.tag_configure("pending", foreground="#111")

    # PPM menu
    menu = tk.Menu(tree, tearoff=0)

    _iid_to_postid: dict[str, str] = {}

    def _selected_posts() -> list[storage.Post]:
        out: list[storage.Post] = []
        for iid in tree.selection():
            pid = _iid_to_postid.get(iid)
            if not pid:
                continue
            post = storage.get_post(pid)
            if post:
                out.append(post)
        return out

    def _fill(posts: list[storage.Post]) -> None:
        _iid_to_postid.clear()
        for iid in tree.get_children():
            tree.delete(iid)
        for post in posts:
            p = platforms.get(post.platform)
            plat_label = f"{p.icon} {p.label}" if p else post.platform
            status_label = _STATUS_LABELS.get(post.status, post.status)
            topic = post.topic or "(bez tematu)"
            caption_short = (post.caption or "").replace("\n", " ")
            if len(caption_short) > 90:
                caption_short = caption_short[:90] + "..."
            series_mark = "●" if post.series_id else ""
            iid = tree.insert(
                "", "end",
                values=(
                    status_label, post.scheduled_at or "", plat_label,
                    post.language, topic, caption_short, series_mark,
                ),
                tags=(post.status,),
            )
            _iid_to_postid[iid] = post.id

    def _filtered() -> list[storage.Post]:
        posts = storage.load_posts()
        pv = plat_var.get()
        if pv != "(wszystkie)":
            code = _label_to_code(pv)
            posts = [x for x in posts if x.platform == code]
        lv = lang_var.get()
        if lv != "(wszystkie)":
            posts = [x for x in posts if x.language == lv]
        sv = status_var.get()
        if sv != "(wszystkie)":
            posts = [x for x in posts if x.status == sv]
        posts.sort(key=_sort_key)
        return posts

    def _refresh() -> None:
        _fill(_filtered())

    plat_var.trace_add("write", lambda *_: _refresh())
    lang_var.trace_add("write", lambda *_: _refresh())
    status_var.trace_add("write", lambda *_: _refresh())

    # Menu callbacks
    def _menu_edit() -> None:
        sel = _selected_posts()
        if not sel:
            return
        _open_edit_dialog(outer.winfo_toplevel(), sel[0], on_saved=_refresh)

    def _menu_copy_full() -> None:
        sel = _selected_posts()
        if not sel:
            return
        post = sel[0]
        text_parts = []
        if post.title:
            text_parts.append(post.title)
        if post.caption:
            text_parts.append(post.caption)
        if post.hashtags:
            text_parts.append("\n" + " ".join(post.hashtags))
        _copy_text(outer, "\n\n".join(text_parts).strip())

    def _menu_copy_caption_only() -> None:
        sel = _selected_posts()
        if not sel:
            return
        _copy_text(outer, sel[0].caption.strip())

    def _menu_copy_hashtags() -> None:
        sel = _selected_posts()
        if not sel:
            return
        _copy_text(outer, " ".join(sel[0].hashtags))

    def _menu_open_image() -> None:
        sel = _selected_posts()
        if not sel:
            return
        ipath = sel[0].image_path
        if not ipath:
            messagebox.showinfo("Brak obrazka", "Post nie ma ustawionej sciezki obrazu.", parent=outer)
            return
        _open_path(outer, ipath)

    def _menu_set_status(status: str) -> None:
        sel = _selected_posts()
        if not sel:
            return
        for post in sel:
            storage.set_status(post.id, status)
        _refresh()
        show_toast(outer, f"Status: {_STATUS_LABELS.get(status, status)}", duration_ms=1200)

    def _menu_delete() -> None:
        sel = _selected_posts()
        if not sel:
            return
        if not messagebox.askyesno(
            "Usunac?",
            f"Usunac {len(sel)} post(ow)? Ta akcja jest nieodwracalna.",
            parent=outer,
        ):
            return
        for post in sel:
            storage.remove_post(post.id)
        _refresh()

    def _menu_generate_series_from() -> None:
        sel = _selected_posts()
        if not sel:
            return
        topic = sel[0].topic or sel[0].caption[:60]
        open_content_generator(
            outer.winfo_toplevel(),
            initial_topic=topic,
            initial_platform=sel[0].platform,
            initial_language=sel[0].language,
        )

    def _popup(event: tk.Event) -> None:
        row = tree.identify_row(event.y)
        if row and row not in tree.selection():
            tree.selection_set(row)
        if not tree.selection():
            return
        menu.delete(0, "end")
        menu.add_command(label="Edytuj...", command=_menu_edit)
        menu.add_separator()
        menu.add_command(label="Kopiuj caption + hashtagi", command=_menu_copy_full)
        menu.add_command(label="Kopiuj tylko caption", command=_menu_copy_caption_only)
        menu.add_command(label="Kopiuj hashtagi", command=_menu_copy_hashtags)
        menu.add_separator()
        menu.add_command(label="Otworz obraz/video", command=_menu_open_image)
        menu.add_command(label="Generuj seria z tego tematu...", command=_menu_generate_series_from)
        menu.add_separator()
        status_menu = tk.Menu(menu, tearoff=0)
        status_menu.add_command(label=_STATUS_LABELS["pending"], command=lambda: _menu_set_status("pending"))
        status_menu.add_command(label=_STATUS_LABELS["in_progress"], command=lambda: _menu_set_status("in_progress"))
        status_menu.add_command(label=_STATUS_LABELS["done"], command=lambda: _menu_set_status("done"))
        status_menu.add_command(label=_STATUS_LABELS["skipped"], command=lambda: _menu_set_status("skipped"))
        menu.add_cascade(label="Zmien status", menu=status_menu)
        menu.add_separator()
        menu.add_command(label="Usun...", command=_menu_delete)
        menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<Button-3>", _popup)
    tree.bind("<Double-1>", lambda _e: _menu_edit())

    _refresh()
    return outer


# ---------------------------------------------------------------------------
# Edit dialog
# ---------------------------------------------------------------------------

def _open_edit_dialog(parent: tk.Misc, post: storage.Post, *, on_saved: Callable[[], None]) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title(f"Edycja posta - {post.platform}/{post.language}")
    dlg.geometry("820x720")
    dlg.minsize(700, 600)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    root = ttk.Frame(dlg, padding=12)
    root.pack(fill="both", expand=True)

    p = platforms.get(post.platform)

    # Header
    header = ttk.Frame(root)
    header.pack(fill="x", pady=(0, 8))
    ttk.Label(
        header,
        text=f"{p.icon + ' ' if p else ''}{p.label if p else post.platform} · {platforms.lang_label(post.language)}",
        font=("Segoe UI", 13, "bold"),
    ).pack(side="left")
    if post.topic:
        ttk.Label(header, text=f"Temat: {post.topic}", foreground="#666").pack(side="left", padx=(14, 0))

    grid = ttk.Frame(root)
    grid.pack(fill="both", expand=True)
    grid.columnconfigure(1, weight=1)

    row = 0
    ttk.Label(grid, text="Tytul:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    title_var = tk.StringVar(value=post.title)
    ttk.Entry(grid, textvariable=title_var).grid(row=row, column=1, sticky="ew", pady=3)
    row += 1

    ttk.Label(grid, text="Caption:").grid(row=row, column=0, sticky="nw", padx=(0, 6), pady=3)
    cap_frame = ttk.Frame(grid)
    cap_frame.grid(row=row, column=1, sticky="ew", pady=3)
    cap_text = tk.Text(cap_frame, wrap="word", height=10, font=("Segoe UI", 10))
    csb = ttk.Scrollbar(cap_frame, orient="vertical", command=cap_text.yview)
    cap_text.configure(yscrollcommand=csb.set)
    cap_text.pack(side="left", fill="both", expand=True)
    csb.pack(side="right", fill="y")
    cap_text.insert("1.0", post.caption)
    cap_len_lbl = ttk.Label(grid, text="", foreground="#666", font=("Segoe UI", 8))
    cap_len_lbl.grid(row=row, column=1, sticky="e", padx=(0, 20), pady=(28, 0))

    def _update_len(*_a: object) -> None:
        text = cap_text.get("1.0", "end-1c")
        n = len(text)
        if p and n > p.caption_limit:
            cap_len_lbl.configure(text=f"{n}/{p.caption_limit} ⚠", foreground="#c62828")
        elif p:
            cap_len_lbl.configure(text=f"{n}/{p.caption_limit}", foreground="#666")
        else:
            cap_len_lbl.configure(text=str(n), foreground="#666")

    cap_text.bind("<KeyRelease>", _update_len)
    _update_len()
    row += 1

    if p and p.code in ("ig_reels", "tiktok"):
        ttk.Label(grid, text="Napisy on-screen (po 1 w linii):").grid(row=row, column=0, sticky="nw", padx=(0, 6), pady=3)
        ost_text = tk.Text(grid, height=3, wrap="word", font=("Segoe UI", 9))
        ost_text.grid(row=row, column=1, sticky="ew", pady=3)
        ost_text.insert("1.0", "\n".join(post.on_screen_text))
        row += 1
        ttk.Label(grid, text="Muzyka/dzwiek:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        music_var = tk.StringVar(value=post.music_hint)
        ttk.Entry(grid, textvariable=music_var).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
    else:
        ost_text = None
        music_var = None

    ttk.Label(grid, text="Hashtagi:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    ht_var = tk.StringVar(value=" ".join(post.hashtags))
    ttk.Entry(grid, textvariable=ht_var).grid(row=row, column=1, sticky="ew", pady=3)
    row += 1

    ttk.Label(grid, text="Sugestia obrazu:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    img_hint_var = tk.StringVar(value=post.image_hint)
    ttk.Entry(grid, textvariable=img_hint_var).grid(row=row, column=1, sticky="ew", pady=3)
    row += 1

    ttk.Label(grid, text="Sciezka obrazu/video:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    img_row = ttk.Frame(grid)
    img_row.grid(row=row, column=1, sticky="ew", pady=3)
    img_path_var = tk.StringVar(value=post.image_path)
    ttk.Entry(img_row, textvariable=img_path_var).pack(side="left", fill="x", expand=True)
    ttk.Button(
        img_row, text="...", width=4,
        command=lambda: _pick_image(img_path_var),
    ).pack(side="left", padx=(4, 0))
    row += 1

    ttk.Label(grid, text="Link docelowy:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    link_var = tk.StringVar(value=post.link)
    ttk.Entry(grid, textvariable=link_var).grid(row=row, column=1, sticky="ew", pady=3)
    row += 1

    ttk.Label(grid, text="Data (YYYY-MM-DD HH:MM):").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    scheduled_var = tk.StringVar(value=post.scheduled_at)
    ttk.Entry(grid, textvariable=scheduled_var).grid(row=row, column=1, sticky="ew", pady=3)
    row += 1

    ttk.Label(grid, text="Status:").grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
    status_var = tk.StringVar(value=post.status)
    ttk.Combobox(
        grid, textvariable=status_var,
        values=_STATUS_ORDER, state="readonly", width=14,
    ).grid(row=row, column=1, sticky="w", pady=3)
    row += 1

    ttk.Label(grid, text="Notatki:").grid(row=row, column=0, sticky="nw", padx=(0, 6), pady=3)
    notes_text = tk.Text(grid, height=3, wrap="word", font=("Segoe UI", 9))
    notes_text.grid(row=row, column=1, sticky="ew", pady=3)
    notes_text.insert("1.0", post.notes)
    row += 1

    # Bottom
    btns = ttk.Frame(root)
    btns.pack(fill="x", pady=(10, 0))

    def _save() -> None:
        tags = [t if t.startswith("#") else "#" + t for t in ht_var.get().split() if t.strip()]
        ost_list: list[str] = []
        if ost_text is not None:
            ost_list = [line.strip() for line in ost_text.get("1.0", "end-1c").splitlines() if line.strip()]
        music_hint_val = music_var.get().strip() if music_var is not None else post.music_hint
        storage.update_post(
            post.id,
            title=title_var.get().strip(),
            caption=cap_text.get("1.0", "end-1c").strip(),
            on_screen_text=ost_list,
            hashtags=tags,
            image_hint=img_hint_var.get().strip(),
            image_path=img_path_var.get().strip(),
            link=link_var.get().strip(),
            music_hint=music_hint_val,
            scheduled_at=scheduled_var.get().strip(),
            status=status_var.get().strip() or "pending",
            notes=notes_text.get("1.0", "end-1c").strip(),
        )
        show_toast(dlg, "Zapisano", duration_ms=1000)
        on_saved()
        dlg.destroy()

    ttk.Button(btns, text="💾 Zapisz", command=_save).pack(side="right")
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right", padx=(0, 6))
    dlg.bind("<Escape>", lambda _e: dlg.destroy())


def _pick_image(var: tk.StringVar) -> None:
    path = filedialog.askopenfilename(
        title="Wybierz obraz/video",
        filetypes=[
            ("Obraz i video", "*.jpg *.jpeg *.png *.webp *.gif *.mp4 *.mov"),
            ("Wszystkie", "*.*"),
        ],
    )
    if path:
        var.set(path)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _label_to_code(label: str) -> str:
    for p in platforms.all_platforms():
        if label == f"{p.icon} {p.label}":
            return p.code
    return ""


def _sort_key(post: storage.Post) -> tuple[int, str, str]:
    status_rank = {"in_progress": 0, "pending": 1, "done": 2, "skipped": 3}.get(post.status, 4)
    return (status_rank, post.scheduled_at or "9999", post.created_at)


def _copy_text(widget: tk.Widget, content: str) -> None:
    if not content.strip():
        return
    try:
        widget.clipboard_clear()
        widget.clipboard_append(content)
        widget.update()
    except tk.TclError:
        return
    show_toast(widget, "Skopiowano", duration_ms=1000)


def _open_path(widget: tk.Widget, path: str) -> None:
    p = Path(path).expanduser()
    if not p.exists():
        messagebox.showwarning("Brak pliku", f"Sciezka nie istnieje:\n{p}", parent=widget)
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])  # noqa: S607
        else:
            subprocess.Popen(["xdg-open", str(p)])  # noqa: S607
    except OSError as e:
        messagebox.showerror("Blad", f"Nie udalo sie otworzyc:\n{e}", parent=widget)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def _export_csv(widget: tk.Widget, posts: list[storage.Post]) -> None:
    if not posts:
        messagebox.showinfo("Pusto", "Brak postow do eksportu (filtry nie zwrocily wynikow).", parent=widget)
        return
    path = filedialog.asksaveasfilename(
        title="Zapisz CSV",
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
        initialfile="socialmedia_posts.csv",
    )
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "id", "status", "scheduled_at", "platform", "language", "topic",
                "title", "caption", "hashtags", "on_screen_text", "music_hint",
                "image_path", "link", "notes", "series_id", "created_at",
            ])
            for p in posts:
                writer.writerow([
                    p.id, p.status, p.scheduled_at,
                    p.platform, p.language, p.topic,
                    p.title, p.caption,
                    " ".join(p.hashtags),
                    " | ".join(p.on_screen_text),
                    p.music_hint, p.image_path, p.link,
                    p.notes, p.series_id, p.created_at,
                ])
    except OSError as e:
        messagebox.showerror("Blad zapisu", str(e), parent=widget)
        return
    show_toast(widget, f"Zapisano {len(posts)} postow do CSV", duration_ms=1600)
