"""Reczna publikacja pojedynczego posta (FB lub IG) z grafika lokalna.

Obrazy sa wgrywane do Shopify Files (publiczny CDN), potem wywolywane sa
publish_fb_photo / publish_fb_multi lub publish_ig_single / publish_ig_carousel
z meta_publisher.
"""

from __future__ import annotations

import math
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.socialmedia.cykl import meta_publisher, platforms_cykl as _cp, storage

# W osadzonym widoku (zakladki w Social Media) ograniczamy wysokosc kontrolek,
# zeby zmiescic formularz na typowym ekranie; calosc jest w przewijanym Canvas.
_EMB_LISTBOX_LINES = 4
_EMB_CAPTION_LINES = 6
_STANDALONE_LISTBOX_LINES = 6
_STANDALONE_CAPTION_LINES = 10


def _scrollable_inner(parent: tk.Misc) -> tuple[ttk.Frame, tk.Canvas]:
    """Ramka w pionowym scrollu (Canvas) — wypelnij zwracana ramke; scrollbar z prawej."""
    wrap = ttk.Frame(parent)
    wrap.pack(fill="both", expand=True)
    # Ten sam ton co tlo Social Media — mniej migotania przy szybkim przewijaniu.
    canvas = tk.Canvas(wrap, highlightthickness=0, bd=0, bg="#f4f4f7")
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    _sr_job: list[str | None] = [None]

    def _scrollregion(_evt: object | None = None) -> None:
        # Po jednym idle na serii Configure — taniej przy resize / pierwszym rysowaniu.
        if _sr_job[0] is not None:
            try:
                canvas.after_cancel(_sr_job[0])
            except (tk.TclError, ValueError):
                pass

        def _apply() -> None:
            _sr_job[0] = None
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except tk.TclError:
                pass

        _sr_job[0] = canvas.after_idle(_apply)

    inner.bind("<Configure>", _scrollregion)

    def _fill_width(evt: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=evt.width)

    canvas.bind("<Configure>", _fill_width)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    return inner, canvas


def _bind_wheel_to_scroll_children(canvas: tk.Canvas, root: tk.Misc) -> None:
    """Kolo nad etykietami / ramkami przewija Canvas (nie nadpisuje Listbox/Text).

    Laczy serie zdarzen kola (touchpad / szybkie krecenie) w jedna aktualizacje
    na idle — mniej „przycinania” obrazu niz dziesiatki yview_scroll pod rzad.
    """

    acc: list[int] = [0]
    job: list[str | None] = [None]

    def _flush() -> None:
        job[0] = None
        d = acc[0]
        acc[0] = 0
        if not d:
            return
        step = -d / 120.0
        if -1 < step < 1 and step != 0:
            step = math.copysign(1.0, float(-d))
        canvas.yview_scroll(int(step), "units")

    def _queue_wheel(delta: int) -> None:
        acc[0] += delta
        jid = job[0]
        if jid is not None:
            try:
                canvas.after_cancel(jid)
            except (tk.TclError, ValueError):
                pass
        job[0] = canvas.after_idle(_flush)

    def _wheel(evt: tk.Event) -> None:
        w = evt.widget
        if isinstance(w, (tk.Text, tk.Listbox)):
            return
        if evt.delta:
            _queue_wheel(int(evt.delta))

    def _bind_tree(w: tk.Misc) -> None:
        if isinstance(w, (tk.Text, tk.Listbox)):
            return
        w.bind("<MouseWheel>", _wheel)
        try:
            for c in w.winfo_children():
                _bind_tree(c)
        except tk.TclError:
            pass

    _bind_tree(root)


def attach_media_list_section(
    parent: tk.Misc,
    root_win: tk.Misc,
    paths_var: list[str],
    *,
    lb_lines: int,
    hint_wrap: int,
    title: str = "Grafiki (media)",
    shared_for_all_tabs: bool = False,
) -> tk.Listbox:
    """Buduje ramke listy sciezek plikow (jedna lub wiele grafik). Mutuje paths_var.

    shared_for_all_tabs=True: tekst pomocniczy dla ekranu hub (wspolna lista nad zakladkami).

    Zwraca Listbox (np. do podpiecia skrotow).
    """
    list_fr = ttk.LabelFrame(parent, text=title, padding=8)
    list_fr.pack(fill="both", expand=False, pady=(0, 8))

    hint_a = (
        "W oknie wyboru plikow zaznacz wiele naraz (Ctrl / Shift + klik albo przeciagnij prostokat)."
        if not shared_for_all_tabs else
        "Ta lista jest wspólna dla całego posta — dodaj wiele plików raz, zaznacz ptaszki przy "
        "kanałach (Facebook / Instagram), jeden podpis i „Publikuj na zaznaczone”. "
        "W eksploratorze: Ctrl lub Shift + klik (wiele plików naraz)."
    )
    hint_b = (
        "Na liście poniżej można zaznaczyć wiele pozycji (Ctrl/Shift) lub Ctrl+A, potem „Usuń zaznaczone”."
    )
    ttk.Label(
        list_fr,
        text=hint_a + " " + hint_b,
        foreground="#666",
        font=("Segoe UI", 9),
        wraplength=hint_wrap,
        justify="left",
    ).pack(anchor="w", pady=(0, 6))

    count_var = tk.StringVar(value="0 plików")

    list_row = ttk.Frame(list_fr)
    list_row.pack(fill="both", expand=True)
    lb = tk.Listbox(
        list_row, height=lb_lines, font=("Segoe UI", 10),
        selectmode=tk.EXTENDED,
        activestyle="dotbox",
    )
    sb = ttk.Scrollbar(list_row, orient="vertical", command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    lb.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def _lb_select_all(_evt: object | None = None) -> None:
        lb.selection_set(0, "end")
        return "break"

    lb.bind("<Control-a>", _lb_select_all)
    lb.bind("<Control-A>", _lb_select_all)

    btn_row = ttk.Frame(list_fr)
    btn_row.pack(fill="x", pady=(8, 0))

    def _refresh_lb() -> None:
        lb.delete(0, "end")
        for p in paths_var:
            lb.insert("end", p)
        n = len(paths_var)
        count_var.set(f"{n} {'plik' if n == 1 else ('pliki' if 2 <= n <= 4 else 'plików')}")

    def _add_files() -> None:
        files = filedialog.askopenfilenames(
            title="Wybierz obrazy — wiele naraz (Ctrl lub Shift + klik)",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.gif"),
                ("Wszystkie", "*.*"),
            ],
            parent=root_win,
        )
        if isinstance(files, str):
            files = (files,)
        for f in files:
            if f and f not in paths_var:
                paths_var.append(f)
        _refresh_lb()

    def _remove_sel() -> None:
        sel = list(lb.curselection())
        for i in reversed(sel):
            if 0 <= i < len(paths_var):
                paths_var.pop(i)
        _refresh_lb()

    def _clear() -> None:
        paths_var.clear()
        _refresh_lb()

    ttk.Label(btn_row, textvariable=count_var, foreground="#1565c0").pack(side="right", padx=(8, 0))
    ttk.Button(
        btn_row, text="Dodaj pliki (wielokrotny wybór)...", command=_add_files,
    ).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Usun zaznaczone", command=_remove_sel).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Wyczysc liste", command=_clear).pack(side="left")

    _refresh_lb()
    return lb


def build_manual_post_ui(
    parent: tk.Misc,
    channel_code: str,
    *,
    show_close_button: bool = False,
    on_close: Callable[[], None] | None = None,
    embedded: bool = False,
    shared_media_paths: list[str] | None = None,
) -> None:
    """Buduje formularz publikacji dla jednego kanalu (do zakladki lub okna Toplevel).

    embedded=True: zakladka w oknie Social Media — kompaktowe kontrolki + pionowy scroll.

    shared_media_paths: jesli podane, nie buduje sekcji mediów — uzywa tej samej listy
    (np. wspólna lista nad zakładkami w „Dodaj post”).
    """
    root_win = parent.winfo_toplevel()
    ch = _cp.get(channel_code)
    if ch is None:
        ttk.Label(
            parent,
            text=f"Nieznany kanal: {channel_code}",
            foreground="#c62828",
        ).pack(anchor="w", pady=8)
        return

    ok, err_msg = meta_publisher.check_credentials(channel_code)
    if not ok:
        ttk.Label(
            parent,
            text=err_msg,
            foreground="#c62828",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            parent,
            text="Uzupelnij tokeny w Cykl -> Ustawienia Meta API.",
            foreground="#666",
        ).pack(anchor="w", pady=(0, 8))

        def _open_meta_err() -> None:
            from Komponenty.socialmedia.cykl import meta_config

            meta_config.open_meta_config_dialog(root_win, on_saved=None)

        ttk.Button(parent, text="Ustawienia Meta API...", command=_open_meta_err).pack(anchor="w")
        return

    scroll_canvas: tk.Canvas | None = None
    if embedded:
        host, scroll_canvas = _scrollable_inner(parent)
    else:
        outer = ttk.Frame(parent)
        outer.pack(fill="both", expand=True)
        host = outer

    lb_lines = _EMB_LISTBOX_LINES if embedded else _STANDALONE_LISTBOX_LINES
    cap_lines = _EMB_CAPTION_LINES if embedded else _STANDALONE_CAPTION_LINES
    hint_wrap = 520 if embedded else 620

    creds_preview = storage.load_meta_credentials().get(channel_code) or {}
    profile_url = _cp.public_profile_url(channel_code, creds_preview)

    ttk.Label(
        host, text=f"{ch.icon} {ch.label}",
        font=("Segoe UI", 14, "bold"),
    ).pack(anchor="w")
    prof_lbl = tk.Label(
        host, text=f"Profil: {profile_url}",
        foreground="#1976d2", cursor="hand2",
    )
    prof_lbl.pack(anchor="w", pady=(2, 8))

    def _open_profile(_evt: object | None = None) -> None:
        if profile_url:
            webbrowser.open(profile_url)

    prof_lbl.bind("<Button-1>", lambda e: _open_profile())
    intro_txt = (
        "FB: post tekstowy lub grafika + podpis. IG: wymagany min. 1 obraz (bez samego tekstu). "
        "Wiele JPG/PNG; IG max 10 w karuzeli; podpis IG max 2200 znakow. "
        "Po publikacji pliki tymczasowe usuwane z Shopify Files."
    )
    ttk.Label(
        host,
        text=intro_txt,
        foreground="#555",
        wraplength=hint_wrap,
        justify="left",
    ).pack(anchor="w", pady=(0, 8))

    if shared_media_paths is not None:
        paths_var = shared_media_paths
        ttk.Label(
            host,
            text="📎 Publikacja używa grafik z listy nad zakładkami (jedna kolejka plików dla FB/IG).",
            foreground="#37474f",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 6))
    else:
        paths_var = []
        attach_media_list_section(
            host, root_win, paths_var,
            lb_lines=lb_lines,
            hint_wrap=hint_wrap,
            shared_for_all_tabs=False,
        )

    cap_fr = ttk.LabelFrame(host, text="Podpis (caption)", padding=8)
    # W trybie osadzonym nie rozciagaj ramki podpisu — scroll obejmuje cala zawartosc.
    cap_fr.pack(fill="both", expand=not embedded, pady=(0, 8))

    cap = tk.Text(cap_fr, height=cap_lines, wrap="word", font=("Segoe UI", 10))
    cap.pack(fill="both", expand=True)
    cnt_var = tk.StringVar(value="0 znakow")

    def _upd_cnt(_e: object | None = None) -> None:
        t = cap.get("1.0", "end-1c")
        n = len(t)
        lim = _cp.CAPTION_LIMITS.get(ch.platform, 63206)
        cnt_var.set(f"{n} / {lim} znakow")
        if ch.platform == "ig" and n > lim:
            cnt_lbl.configure(foreground="#c62828")
        else:
            cnt_lbl.configure(foreground="#666")

    cnt_lbl = ttk.Label(cap_fr, textvariable=cnt_var, foreground="#666")
    cnt_lbl.pack(anchor="e", pady=(4, 0))
    cap.bind("<<Modified>>", lambda e: (_upd_cnt(), cap.edit_modified(False)))
    cap.bind("<KeyRelease>", _upd_cnt)
    _upd_cnt()

    status_var = tk.StringVar(value="")
    ttk.Label(host, textvariable=status_var, foreground="#666").pack(anchor="w")

    def _publish() -> None:
        caption = cap.get("1.0", "end-1c").strip()
        has_files = bool(paths_var)

        if not has_files:
            if ch.platform == "ig":
                messagebox.showerror(
                    "Dodaj post",
                    "Instagram (Graph API): publikacja wymaga co najmniej jednego obrazu.\n"
                    "Sam tekst na IG nie jest obslugiwany przez to API.",
                    parent=root_win,
                )
                return
            if ch.platform == "fb" and not caption:
                messagebox.showwarning(
                    "Dodaj post",
                    "Post tekstowy na Facebooku: wpisz tresc w polu Podpis (albo dodaj zdjecie).",
                    parent=root_win,
                )
                return

        if has_files and ch.platform == "ig" and len(paths_var) > 10:
            messagebox.showerror(
                "Dodaj post",
                "Instagram: maksymalnie 10 zdjec w jednej karuzeli.",
                parent=root_win,
            )
            return
        if has_files and not caption:
            if not messagebox.askyesno(
                "Pusty podpis",
                "Publikowac bez tekstu w podpisie?",
                parent=root_win,
            ):
                return
        lim = _cp.CAPTION_LIMITS.get(ch.platform, 63206)
        if ch.platform == "ig" and len(caption) > lim:
            messagebox.showerror(
                "Za dlugi podpis",
                f"Instagram: maksymalnie {lim} znakow (masz {len(caption)}).",
                parent=root_win,
            )
            return

        creds = storage.load_meta_credentials().get(channel_code) or {}
        token = creds.get("access_token", "")

        def work() -> None:
            shopify_file_ids: list[str] = []
            try:
                if not has_files and ch.platform == "fb":
                    root_win.after(0, lambda: status_var.set("Publikacja tekstu na Facebooku..."))
                    page_id = creds.get("page_id", "")
                    pid = meta_publisher.publish_fb_feed_text(
                        page_id=page_id, access_token=token, message=caption,
                    )
                    result = f"Facebook: opublikowano post tekstowy (id: {pid})"

                    def _ok_text() -> None:
                        status_var.set(result)
                        messagebox.showinfo("Dodaj post", result, parent=root_win)

                    root_win.after(0, _ok_text)
                    return

                root_win.after(0, lambda: status_var.set("Upload na CDN (Shopify)..."))
                urls: list[str] = []
                for p in paths_var:
                    u, fid = meta_publisher.upload_to_shopify_files_with_id(Path(p))
                    urls.append(u)
                    shopify_file_ids.append(fid)

                root_win.after(0, lambda: status_var.set("Publikacja w Meta..."))
                if ch.platform == "fb":
                    page_id = creds.get("page_id", "")
                    if len(urls) == 1:
                        pid = meta_publisher.publish_fb_photo(
                            page_id=page_id, access_token=token,
                            image_url=urls[0], caption=caption,
                        )
                    else:
                        pid = meta_publisher.publish_fb_multi(
                            page_id=page_id, access_token=token,
                            image_urls=urls, caption=caption,
                        )
                    result = f"Facebook: opublikowano (post id: {pid})"
                else:
                    ig_id = creds.get("ig_user_id", "")
                    if len(urls) == 1:
                        mid = meta_publisher.publish_ig_single(
                            ig_user_id=ig_id, access_token=token,
                            image_url=urls[0], caption=caption,
                        )
                    else:
                        mid = meta_publisher.publish_ig_carousel(
                            ig_user_id=ig_id, access_token=token,
                            image_urls=urls, caption=caption,
                        )
                    result = f"Instagram: opublikowano (media id: {mid})"

                def _ok() -> None:
                    status_var.set(result)
                    messagebox.showinfo("Dodaj post", result, parent=root_win)

                root_win.after(0, _ok)
            except Exception as e:  # noqa: BLE001
                err = str(e)
                hint = ""
                if "stagedUploadsCreate" in err or (
                    "ACCESS_DENIED" in err and "stagedUploads" in err.lower()
                ):
                    hint = (
                        "\n\n---\n"
                        "Shopify: brak scope do uploadu plikow (Files API).\n"
                        "Dopisz do .env: read_files,write_files (i to samo w shopify.app.toml),\n"
                        "potem: cd cursor-api && npm run oauth\n"
                        "Dokumentacja: https://shopify.dev/api/usage/access-scopes"
                    )

                def _err() -> None:
                    status_var.set("Blad.")
                    messagebox.showerror("Publikacja", (err + hint)[:4000], parent=root_win)

                root_win.after(0, _err)
            finally:
                if shopify_file_ids:
                    meta_publisher.delete_shopify_file_ids(shopify_file_ids)

        status_var.set("Przygotowanie...")
        threading.Thread(target=work, daemon=True).start()

    bottom = ttk.Frame(host)
    bottom.pack(fill="x")

    def _open_meta() -> None:
        from Komponenty.socialmedia.cykl import meta_config

        meta_config.open_meta_config_dialog(root_win, on_saved=None)

    ttk.Button(bottom, text="Ustawienia Meta API...", command=_open_meta).pack(side="left")
    ttk.Button(bottom, text="Publikuj", command=_publish).pack(side="right", padx=(8, 0))
    if show_close_button:
        def _do_close() -> None:
            if on_close:
                on_close()
            else:
                root_win.destroy()

        ttk.Button(bottom, text="Zamknij", command=_do_close).pack(side="right")

    if scroll_canvas is not None:
        _bind_wheel_to_scroll_children(scroll_canvas, host)


# ---------------------------------------------------------------------------
# Hub „Dodaj post” — wiele kanalow naraz (checkboxy)
# ---------------------------------------------------------------------------

_HUB_CHANNEL_ORDER = list(_cp.CHANNEL_ORDER)


def _publish_media_to_channel(channel_code: str, caption: str, urls: list[str]) -> str:
    """Publikuje gotowe URL-e CDN na jeden kanal."""
    ch = _cp.get(channel_code)
    if ch is None:
        raise ValueError(f"Nieznany kanal: {channel_code}")
    creds = storage.load_meta_credentials().get(channel_code) or {}
    token = creds.get("access_token", "")
    if ch.platform == "fb":
        page_id = creds.get("page_id", "")
        if len(urls) == 1:
            pid = meta_publisher.publish_fb_photo(
                page_id=page_id, access_token=token,
                image_url=urls[0], caption=caption,
            )
        else:
            pid = meta_publisher.publish_fb_multi(
                page_id=page_id, access_token=token,
                image_urls=urls, caption=caption,
            )
        return f"{ch.label}: opublikowano (post id: {pid})"
    ig_id = creds.get("ig_user_id", "")
    if len(urls) == 1:
        mid = meta_publisher.publish_ig_single(
            ig_user_id=ig_id, access_token=token,
            image_url=urls[0], caption=caption,
        )
    else:
        mid = meta_publisher.publish_ig_carousel(
            ig_user_id=ig_id, access_token=token,
            image_urls=urls, caption=caption,
        )
    return f"{ch.label}: opublikowano (media id: {mid})"


def _publish_fb_text_channel(channel_code: str, message: str) -> str:
    creds = storage.load_meta_credentials().get(channel_code) or {}
    ch = _cp.get(channel_code)
    label = ch.label if ch else channel_code
    pid = meta_publisher.publish_fb_feed_text(
        page_id=creds.get("page_id", ""),
        access_token=creds.get("access_token", ""),
        message=message,
    )
    return f"{label}: opublikowano post tekstowy (id: {pid})"


def build_multi_channel_hub_ui(parent: tk.Misc, root_win: tk.Misc, paths_var: list[str]) -> None:
    """Jeden formularz: checkboxy kanalow + wspolny podpis + publikacja na zaznaczone."""
    host, scroll_canvas = _scrollable_inner(parent)
    cap_lines = 10
    hint_wrap = 680

    ttk.Label(
        host,
        text="Zaznacz jedno lub wiele kont (ptaszki). Ten sam podpis i ta sama lista plikow "
        "trafia na kazde z nich. Instagram wymaga co najmniej jednego obrazu; Facebook moze "
        "byc sam tekst lub grafika.\n"
        "Jednoczesnie mozesz wybrac tylko wersje polskie (PL) LUB tylko zagraniczne (EN) — druga "
        "grupa jest wtedy zablokowana az odznaczysz cala pierwsza.",
        foreground="#555",
        wraplength=hint_wrap,
        justify="left",
        font=("Segoe UI", 10),
    ).pack(anchor="w", pady=(0, 8))

    sel_fr = ttk.LabelFrame(host, text="Gdzie opublikować", padding=10)
    sel_fr.pack(fill="x", pady=(0, 8))

    ch_vars: dict[str, tk.BooleanVar] = {}
    ch_cb: dict[str, ttk.Checkbutton] = {}
    grid = ttk.Frame(sel_fr)
    grid.pack(fill="x")

    for i, code in enumerate(_HUB_CHANNEL_ORDER):
        ch = _cp.get(code)
        title = ch.label if ch else code
        icon = (ch.icon + " ") if ch else ""
        row, col = divmod(i, 2)
        cell = ttk.Frame(grid)
        cell.grid(row=row, column=col, sticky="nw", padx=(0, 24), pady=4)
        ok, _err = meta_publisher.check_credentials(code)
        v = tk.BooleanVar(value=False)
        ch_vars[code] = v
        cb = ttk.Checkbutton(cell, text=f"{icon}{title}", variable=v)
        cb.pack(anchor="w")
        if not ok:
            cb.configure(state="disabled")
            ttk.Label(
                cell,
                text="— brak tokenu / ID w Meta API",
                foreground="#c62828",
                font=("Segoe UI", 8),
            ).pack(anchor="w")
        else:
            ch_cb[code] = cb

    _lock_silent: list[bool] = [False]

    pl_codes = [c for c in _HUB_CHANNEL_ORDER if c.endswith("_pl") and c in ch_cb]
    en_codes = [c for c in _HUB_CHANNEL_ORDER if c.endswith("_en") and c in ch_cb]

    def _apply_language_lock(*_a: object) -> None:
        """PL i EN wzajemnie sie wykluczaja: aktywna grupa blokuje druga."""
        if _lock_silent[0]:
            return
        pl_sel = any(ch_vars[c].get() for c in pl_codes)
        en_sel = any(ch_vars[c].get() for c in en_codes)

        _lock_silent[0] = True
        try:
            if pl_sel and en_sel:
                for c in en_codes:
                    ch_vars[c].set(False)
                en_sel = False

            if pl_sel:
                for c in en_codes:
                    ch_vars[c].set(False)
                    ch_cb[c].configure(state="disabled")
                for c in pl_codes:
                    ch_cb[c].configure(state="normal")
            elif en_sel:
                for c in pl_codes:
                    ch_vars[c].set(False)
                    ch_cb[c].configure(state="disabled")
                for c in en_codes:
                    ch_cb[c].configure(state="normal")
            else:
                for c in pl_codes:
                    ch_cb[c].configure(state="normal")
                for c in en_codes:
                    ch_cb[c].configure(state="normal")
        finally:
            _lock_silent[0] = False

    for code in list(ch_cb.keys()):
        ch_vars[code].trace_add("write", lambda *_x: _apply_language_lock())

    _apply_language_lock()

    qb = ttk.Frame(sel_fr)
    qb.pack(fill="x", pady=(8, 0))

    def _clear_checks() -> None:
        for code in _HUB_CHANNEL_ORDER:
            ok, _x = meta_publisher.check_credentials(code)
            if ok:
                ch_vars[code].set(False)

    def _select_pl_only() -> None:
        """Zaznacza wylacznie kanaly jezyka polskiego (fb_pl, ig_pl); pozostale wylacza."""
        for code in _HUB_CHANNEL_ORDER:
            ok, _x = meta_publisher.check_credentials(code)
            if not ok:
                continue
            ch_vars[code].set(code.endswith("_pl"))

    def _select_en_only() -> None:
        """Zaznacza wylacznie kanaly jezyka angielskiego (fb_en, ig_en); polskie wylacza."""
        for code in _HUB_CHANNEL_ORDER:
            ok, _x = meta_publisher.check_credentials(code)
            if not ok:
                continue
            ch_vars[code].set(code.endswith("_en"))

    ttk.Button(qb, text="Odznacz wszystkie", command=_clear_checks).pack(side="left")

    qb2 = ttk.Frame(sel_fr)
    qb2.pack(fill="x", pady=(8, 0))
    ttk.Label(
        qb2,
        text="Szybki wybor jezyka:",
        foreground="#555",
        font=("Segoe UI", 9),
    ).pack(side="left", padx=(0, 8))
    ttk.Button(qb2, text="Tylko polskie (FB PL + IG PL)", command=_select_pl_only).pack(side="left")
    ttk.Button(
        qb2,
        text="Tylko zagraniczne (FB EN + IG EN)",
        command=_select_en_only,
    ).pack(side="left", padx=(10, 0))

    cap_fr = ttk.LabelFrame(host, text="Podpis (caption) — wspólny dla zaznaczonych kont", padding=8)
    cap_fr.pack(fill="both", expand=True, pady=(0, 8))

    cap = tk.Text(cap_fr, height=cap_lines, wrap="word", font=("Segoe UI", 10))
    cap.pack(fill="both", expand=True)
    cnt_var = tk.StringVar(value="0 znaków (Instagram max 2200 przy grafice)")

    def _upd_cnt(_e: object | None = None) -> None:
        t = cap.get("1.0", "end-1c")
        n = len(t)
        ig_lim = _cp.CAPTION_LIMITS.get("ig", 2200)
        cnt_var.set(f"{n} znaków — dla Instagram max {ig_lim}")
        cnt_lbl.configure(foreground="#c62828" if n > ig_lim else "#666")

    cnt_lbl = ttk.Label(cap_fr, textvariable=cnt_var, foreground="#666")
    cnt_lbl.pack(anchor="e", pady=(4, 0))
    cap.bind("<<Modified>>", lambda e: (_upd_cnt(), cap.edit_modified(False)))
    cap.bind("<KeyRelease>", _upd_cnt)
    _upd_cnt()

    status_var = tk.StringVar(value="")
    ttk.Label(host, textvariable=status_var, foreground="#666").pack(anchor="w")

    def _selected_codes() -> list[str]:
        out: list[str] = []
        for code in _HUB_CHANNEL_ORDER:
            ok, _x = meta_publisher.check_credentials(code)
            if not ok:
                continue
            if ch_vars[code].get():
                out.append(code)
        return out

    def _publish_multi() -> None:
        selected = _selected_codes()
        if not selected:
            messagebox.showwarning(
                "Dodaj post",
                "Zaznacz co najmniej jedno konto (ptaszek przy kanale z poprawnymi tokenami).",
                parent=root_win,
            )
            return

        caption = cap.get("1.0", "end-1c").strip()
        has_files = bool(paths_var)
        ig_picked = any(c.startswith("ig") for c in selected)
        fb_picked = any(c.startswith("fb") for c in selected)

        if ig_picked and not has_files:
            messagebox.showerror(
                "Dodaj post",
                "Instagram wymaga co najmniej jednego obrazu.\n"
                "Odznacz konta IG albo dodaj pliki do listy powyżej.",
                parent=root_win,
            )
            return

        if not has_files and not caption:
            messagebox.showwarning(
                "Dodaj post",
                "Dodaj treść podpisu (Facebook może być sam tekst) albo pliki graficzne.",
                parent=root_win,
            )
            return

        if has_files and ig_picked:
            ig_lim = _cp.CAPTION_LIMITS.get("ig", 2200)
            if len(caption) > ig_lim:
                messagebox.showerror(
                    "Za długi podpis",
                    f"Instagram: maksymalnie {ig_lim} znaków (masz {len(caption)}).\n"
                    "Skróć podpis albo odznacz Instagram.",
                    parent=root_win,
                )
                return
            if len(paths_var) > 10:
                messagebox.showerror(
                    "Dodaj post",
                    "Instagram: maksymalnie 10 zdjęć w jednej karuzeli.",
                    parent=root_win,
                )
                return

        if has_files and not caption:
            if not messagebox.askyesno(
                "Pusty podpis",
                "Publikować bez tekstu w podpisie na wszystkich zaznaczonych kontach?",
                parent=root_win,
            ):
                return

        def work() -> None:
            shopify_file_ids: list[str] = []
            lines: list[str] = []
            try:
                urls: list[str] = []
                if has_files:
                    root_win.after(0, lambda: status_var.set("Upload na CDN (Shopify)..."))
                    for p in paths_var:
                        u, fid = meta_publisher.upload_to_shopify_files_with_id(Path(p))
                        urls.append(u)
                        shopify_file_ids.append(fid)

                root_win.after(0, lambda: status_var.set("Publikacja w Meta..."))
                for code in selected:
                    ch = _cp.get(code)
                    if ch is None:
                        continue
                    try:
                        if not has_files:
                            if ch.platform == "fb":
                                lines.append(_publish_fb_text_channel(code, caption))
                            else:
                                lines.append(f"{ch.label}: pominięto (IG wymaga zdjęcia)")
                            continue
                        if ch.platform == "ig" and len(caption) > _cp.CAPTION_LIMITS.get("ig", 2200):
                            lines.append(f"{ch.label}: pominięto (podpis za długi dla IG)")
                            continue
                        lines.append(_publish_media_to_channel(code, caption, urls))
                    except Exception as e:  # noqa: BLE001
                        _ch = _cp.get(code)
                        _lbl = _ch.label if _ch else code
                        lines.append(f"{_lbl}: BŁĄD {e}")

                summary = "\n".join(lines)

                def _done() -> None:
                    status_var.set("Gotowe.")
                    messagebox.showinfo("Dodaj post — wynik", summary[:8000], parent=root_win)
                    show_toast(root_win, "Zakończono publikację", duration_ms=1800)

                root_win.after(0, _done)
            except Exception as e:  # noqa: BLE001
                err = str(e)
                hint = ""
                if "stagedUploadsCreate" in err or (
                    "ACCESS_DENIED" in err and "stagedUploads" in err.lower()
                ):
                    hint = (
                        "\n\nShopify: brak scope do uploadu plików.\n"
                        "Dopisz read_files, write_files i npm run oauth."
                    )

                def _err() -> None:
                    status_var.set("Błąd.")
                    messagebox.showerror("Publikacja", (err + hint)[:4000], parent=root_win)

                root_win.after(0, _err)
            finally:
                if shopify_file_ids:
                    meta_publisher.delete_shopify_file_ids(shopify_file_ids)

        status_var.set("Przygotowanie...")
        threading.Thread(target=work, daemon=True).start()

    bottom = ttk.Frame(host)
    bottom.pack(fill="x", pady=(8, 0))

    def _open_meta() -> None:
        from Komponenty.socialmedia.cykl import meta_config

        meta_config.open_meta_config_dialog(root_win, on_saved=None)

    ttk.Button(bottom, text="Ustawienia Meta API...", command=_open_meta).pack(side="left")
    ttk.Button(
        bottom,
        text="Publikuj na zaznaczone konta",
        command=_publish_multi,
    ).pack(side="right", padx=(8, 0))

    _bind_wheel_to_scroll_children(scroll_canvas, host)


def open_manual_post_wizard(parent: tk.Misc, channel_code: str) -> None:
    """Osobne okno z kreatorem (np. wywolanie z zewnatrz)."""
    ch = _cp.get(channel_code)
    if ch is None:
        messagebox.showerror("Dodaj post", f"Nieznany kanal: {channel_code}", parent=parent)
        return

    dlg = tk.Toplevel(parent)
    dlg.title(f"Dodaj post — {ch.label}")
    position_toplevel_screen_center(dlg, 720, 620)
    dlg.minsize(560, 480)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(14, 12))
    outer.pack(fill="both", expand=True)
    build_manual_post_ui(
        outer, channel_code, show_close_button=True, on_close=dlg.destroy,
    )


def open_social_ids_dialog(parent: tk.Misc) -> None:
    """Lista ID Meta (page / IG user) + klikalne linki do profili — ekran Dodaj post."""
    dlg = tk.Toplevel(parent)
    dlg.title("Id socjali")
    position_toplevel_screen_center(dlg, 680, 540)
    dlg.minsize(520, 400)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(14, 12))
    outer.pack(fill="both", expand=True)

    ttk.Label(
        outer,
        text="Facebook / Instagram — numeryczne ID z konfiguracji Meta oraz linki do profili.",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        outer,
        text="Zrodlo danych: Social Media -> Cykl -> Ustawienia Meta API (meta_credentials.json).",
        foreground="#666",
    ).pack(anchor="w", pady=(0, 10))

    box = ttk.Frame(outer)
    box.pack(fill="both", expand=True)

    creds_all = storage.load_meta_credentials()

    def _copyable_line(parent_fr: tk.Widget, caption: str, value: str) -> None:
        row = ttk.Frame(parent_fr)
        row.pack(fill="x", pady=(0, 6))
        ttk.Label(row, text=caption, width=20, anchor="w").pack(side="left", padx=(0, 8))
        ent = ttk.Entry(row, font=("Segoe UI", 10))
        ent.insert(0, value)
        ent.state(["readonly"])
        ent.pack(side="left", fill="x", expand=True)

    for code in _cp.CHANNEL_ORDER:
        ch = _cp.get(code)
        if ch is None:
            continue
        cr = creds_all.get(code) or {}
        sec = ttk.LabelFrame(box, text=f"{ch.icon} {ch.label}", padding=(10, 8))
        sec.pack(fill="x", pady=(0, 8))

        if ch.platform == "fb":
            pid = str(cr.get("page_id") or "").strip()
            _copyable_line(
                sec, "Page ID:",
                pid or "(brak — uzupelnij w Ustawienia Meta API)",
            )
        else:
            iid = str(cr.get("ig_user_id") or "").strip()
            _copyable_line(
                sec, "Instagram user ID:",
                iid or "(brak — uzupelnij w Ustawienia Meta API)",
            )

        url = _cp.public_profile_url(code, cr)
        url_row = ttk.Frame(sec)
        url_row.pack(fill="x", pady=(2, 0))
        ttk.Label(url_row, text="URL profilu:", width=20, anchor="w").pack(side="left", padx=(0, 8))
        url_ent = ttk.Entry(url_row, font=("Segoe UI", 10))
        url_ent.insert(0, url or "(brak URL)")
        url_ent.state(["readonly"])
        url_ent.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if url:

            def _open(_u: str = url) -> None:
                webbrowser.open(_u)

            ttk.Button(url_row, text="Otworz", width=10, command=_open).pack(side="left")

    ttk.Label(
        outer,
        text="Zaznacz tekst w polu i uzyj Ctrl+C, aby skopiowac.",
        foreground="#888",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(4, 0))

    ttk.Button(outer, text="Zamknij", command=dlg.destroy).pack(anchor="e", pady=(12, 0))
