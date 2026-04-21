"""Reczna publikacja pojedynczego posta (FB lub IG) z grafika lokalna.

Obrazy sa wgrywane do Shopify Files (publiczny CDN), potem wywolywane sa
publish_fb_photo / publish_fb_multi lub publish_ig_single / publish_ig_carousel
z meta_publisher.
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty.socialmedia.cykl import meta_publisher, platforms_cykl as _cp, storage


def open_manual_post_wizard(parent: tk.Misc, channel_code: str) -> None:
    ch = _cp.get(channel_code)
    if ch is None:
        messagebox.showerror("Dodaj post", f"Nieznany kanal: {channel_code}", parent=parent)
        return

    ok, msg = meta_publisher.check_credentials(channel_code)
    if not ok:
        messagebox.showerror(
            "Brak konfiguracji Meta",
            f"{msg}\n\nOtworz Cykl -> Ustawienia Meta API i uzupelnij tokeny.",
            parent=parent,
        )
        return

    dlg = tk.Toplevel(parent)
    dlg.title(f"Dodaj post — {ch.label}")
    dlg.geometry("720x620")
    dlg.minsize(560, 480)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(14, 12))
    outer.pack(fill="both", expand=True)

    creds_preview = storage.load_meta_credentials().get(channel_code) or {}
    profile_url = _cp.public_profile_url(channel_code, creds_preview)

    ttk.Label(
        outer, text=f"{ch.icon} {ch.label}",
        font=("Segoe UI", 14, "bold"),
    ).pack(anchor="w")
    prof_lbl = tk.Label(
        outer, text=f"Profil: {profile_url}",
        foreground="#1976d2", cursor="hand2",
    )
    prof_lbl.pack(anchor="w", pady=(2, 8))

    def _open_profile(_evt: object | None = None) -> None:
        if profile_url:
            webbrowser.open(profile_url)

    prof_lbl.bind("<Button-1>", lambda e: _open_profile())
    ttk.Label(
        outer,
        text="Dodaj jedno lub wiecej zdjec (JPG/PNG). Instagram: maks. 10 w karuzeli.\n"
        "Podpis: dla IG limit 2200 znakow.\n"
        "Po publikacji w Meta pliki tymczasowe sa usuwane z biblioteki Shopify (oszczednosc miejsca).",
        foreground="#555",
    ).pack(anchor="w", pady=(0, 8))

    # Lista plikow
    list_fr = ttk.LabelFrame(outer, text="Grafiki", padding=8)
    list_fr.pack(fill="both", expand=False, pady=(0, 8))

    paths_var: list[str] = []

    list_row = ttk.Frame(list_fr)
    list_row.pack(fill="both", expand=True)
    lb = tk.Listbox(list_row, height=5, font=("Segoe UI", 10))
    sb = ttk.Scrollbar(list_row, orient="vertical", command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    lb.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    btn_row = ttk.Frame(list_fr)
    btn_row.pack(fill="x", pady=(8, 0))

    def _refresh_lb() -> None:
        lb.delete(0, "end")
        for p in paths_var:
            lb.insert("end", p)

    def _add_files() -> None:
        files = filedialog.askopenfilenames(
            title="Wybierz obrazy",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.gif"),
                ("Wszystkie", "*.*"),
            ],
            parent=dlg,
        )
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

    ttk.Button(btn_row, text="Dodaj obrazy...", command=_add_files).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Usun zaznaczone", command=_remove_sel).pack(side="left", padx=(0, 6))
    ttk.Button(btn_row, text="Wyczysc liste", command=_clear).pack(side="left")

    # Caption
    cap_fr = ttk.LabelFrame(outer, text="Podpis (caption)", padding=8)
    cap_fr.pack(fill="both", expand=True, pady=(0, 8))

    cap = tk.Text(cap_fr, height=10, wrap="word", font=("Segoe UI", 10))
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
    ttk.Label(outer, textvariable=status_var, foreground="#666").pack(anchor="w")

    def _publish() -> None:
        caption = cap.get("1.0", "end-1c").strip()
        if not paths_var:
            messagebox.showwarning("Dodaj post", "Wybierz co najmniej jeden plik graficzny.", parent=dlg)
            return
        if ch.platform == "ig" and len(paths_var) > 10:
            messagebox.showerror(
                "Dodaj post",
                "Instagram: maksymalnie 10 zdjec w jednej karuzeli.",
                parent=dlg,
            )
            return
        if not caption:
            if not messagebox.askyesno(
                "Pusty podpis",
                "Publikowac bez tekstu w podpisie?",
                parent=dlg,
            ):
                return
        lim = _cp.CAPTION_LIMITS.get(ch.platform, 63206)
        if ch.platform == "ig" and len(caption) > lim:
            messagebox.showerror(
                "Za dlugi podpis",
                f"Instagram: maksymalnie {lim} znakow (masz {len(caption)}).",
                parent=dlg,
            )
            return

        creds = storage.load_meta_credentials().get(channel_code) or {}
        token = creds.get("access_token", "")

        def work() -> None:
            shopify_file_ids: list[str] = []
            try:
                dlg.after(0, lambda: status_var.set("Upload na CDN (Shopify)..."))
                urls: list[str] = []
                for p in paths_var:
                    u, fid = meta_publisher.upload_to_shopify_files_with_id(Path(p))
                    urls.append(u)
                    shopify_file_ids.append(fid)

                dlg.after(0, lambda: status_var.set("Publikacja w Meta..."))
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
                    messagebox.showinfo("Dodaj post", result, parent=dlg)

                dlg.after(0, _ok)
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
                    messagebox.showerror("Publikacja", (err + hint)[:4000], parent=dlg)

                dlg.after(0, _err)
            finally:
                if shopify_file_ids:
                    meta_publisher.delete_shopify_file_ids(shopify_file_ids)

        status_var.set("Przygotowanie...")
        threading.Thread(target=work, daemon=True).start()

    bottom = ttk.Frame(outer)
    bottom.pack(fill="x")

    def _open_meta() -> None:
        from Komponenty.socialmedia.cykl import meta_config
        meta_config.open_meta_config_dialog(dlg, on_saved=None)

    ttk.Button(bottom, text="Ustawienia Meta API...", command=_open_meta).pack(side="left")
    ttk.Button(bottom, text="Publikuj", command=_publish).pack(side="right", padx=(8, 0))
    ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right")


def open_social_ids_dialog(parent: tk.Misc) -> None:
    """Lista ID Meta (page / IG user) + klikalne linki do profili — ekran Dodaj post."""
    dlg = tk.Toplevel(parent)
    dlg.title("Id socjali")
    dlg.geometry("680x540")
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

    for code in _cp.CHANNEL_ORDER:
        ch = _cp.get(code)
        if ch is None:
            continue
        cr = creds_all.get(code) or {}
        sec = ttk.LabelFrame(box, text=f"{ch.icon} {ch.label}", padding=(10, 8))
        sec.pack(fill="x", pady=(0, 8))

        if ch.platform == "fb":
            pid = str(cr.get("page_id") or "").strip()
            ttk.Label(sec, text=f"Page ID: {pid or '(brak — uzupelnij w Ustawienia Meta API)'}").pack(anchor="w")
        else:
            iid = str(cr.get("ig_user_id") or "").strip()
            ttk.Label(
                sec,
                text=f"Instagram user ID: {iid or '(brak — uzupelnij w Ustawienia Meta API)'}",
            ).pack(anchor="w")

        url = _cp.public_profile_url(code, cr)
        row = ttk.Frame(sec)
        row.pack(anchor="w", pady=(6, 0))
        ttk.Label(row, text="Otworz: ").pack(side="left")
        link = tk.Label(
            row, text=url or "(brak URL)", fg="#1976d2", cursor="hand2" if url else "",
            font=("Segoe UI", 10, "underline"),
        )
        link.pack(side="left")
        if url:
            link.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))

    ttk.Button(outer, text="Zamknij", command=dlg.destroy).pack(anchor="e", pady=(12, 0))
