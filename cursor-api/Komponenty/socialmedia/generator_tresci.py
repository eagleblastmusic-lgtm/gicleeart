"""Okno 'Generator tresci social media' - toplevel dialog.

Flow:
1. Uzytkownik wybiera:
   - **Platformy (multi-select checkboxami)** - IG Feed, IG Stories, IG Reels, FB, TikTok, Pinterest.
   - Jezyk (PL/EN).
   - Wpisuje temat, opcjonalnie link i dodatkowy kontekst.
   - Tryb: pojedynczy post albo seria N postow.
     UWAGA: Tryb SERIES dziala tylko przy 1 platformie (inaczej eksplozja kombinacji).
2. Klik "Prompt dla Opus" / "Prompt dla GPT":
   - Dla 1 platformy: build_post_prompt_* (single) albo build_series_prompt_* (series).
   - Dla N>1 platform: build_multi_post_prompt_* - jeden prompt generuje N wersji postow.
   - Auto-kopiuje do schowka.
3. Uzytkownik wkleja prompt do Opus/GPT, kopiuje odpowiedz.
4. "Wklej odpowiedz ze schowka" -> auto-paste.
5. "Sprawdz i podglad" -> parsuje JSON, pokazuje PODGLAD (notebook z zakladka per platforma/post).
6. "Zapisz do planera" -> dodaje posty do `posts.json`.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast

from . import platforms, prompts, storage


def open_content_generator(
    parent: tk.Misc,
    *,
    initial_topic: str = "",
    initial_platforms: list[str] | None = None,
    initial_platform: str = "",    # backcompat - gdy ktos uzywa starej nazwy
    initial_language: str = "pl",
    initial_link: str = "",
    from_task_id: str = "",
    on_saved: Callable[[int], None] | None = None,
) -> tk.Toplevel:
    # Normalizacja initial platforms (nowe API) + backcompat (stare `initial_platform`)
    if initial_platforms:
        sel_platforms = [p for p in initial_platforms if platforms.get(p) is not None]
    elif initial_platform:
        sel_platforms = [initial_platform] if platforms.get(initial_platform) else []
    else:
        sel_platforms = []
    if not sel_platforms:
        sel_platforms = ["ig_feed"]  # domyslna

    dlg = tk.Toplevel(parent)
    dlg.title("Social Media - Generator tresci")
    dlg.geometry("1100x880")
    dlg.minsize(900, 720)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    state: dict[str, Any] = {"parsed": None, "from_task_id": from_task_id}

    root = ttk.Frame(dlg, padding=(10, 8))
    root.pack(fill="both", expand=True)

    # ---------- Sekcja 1: parametry ----------
    params = ttk.LabelFrame(root, text="1. Parametry", padding=8)
    params.pack(fill="x", pady=(0, 6))

    grid = ttk.Frame(params)
    grid.pack(fill="x")
    grid.columnconfigure(1, weight=1)
    grid.columnconfigure(3, weight=1)

    ttk.Label(grid, text="Temat:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
    topic_var = tk.StringVar(value=initial_topic)
    ttk.Entry(grid, textvariable=topic_var).grid(row=0, column=1, columnspan=3, sticky="ew", pady=3)

    # Platformy - multi-select checkboxami
    ttk.Label(grid, text="Platformy:").grid(row=1, column=0, sticky="nw", padx=(0, 6), pady=3)
    platforms_frame = ttk.Frame(grid)
    platforms_frame.grid(row=1, column=1, columnspan=3, sticky="ew", pady=3)
    plat_vars: dict[str, tk.BooleanVar] = {}
    for i, p in enumerate(platforms.all_platforms()):
        v = tk.BooleanVar(value=(p.code in sel_platforms))
        plat_vars[p.code] = v
        ttk.Checkbutton(
            platforms_frame, text=f"{p.icon} {p.label}", variable=v,
        ).grid(row=i // 3, column=i % 3, sticky="w", padx=6, pady=1)

    ttk.Label(grid, text="Jezyk:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=3)
    lang_var = tk.StringVar(value=initial_language)
    ttk.Combobox(
        grid, textvariable=lang_var,
        values=[code for code, _ in platforms.LANGUAGES],
        state="readonly", width=8,
    ).grid(row=2, column=1, sticky="w", pady=3)

    ttk.Label(grid, text="Link docelowy:").grid(row=2, column=2, sticky="w", padx=(18, 6), pady=3)
    link_var = tk.StringVar(value=initial_link)
    ttk.Entry(grid, textvariable=link_var).grid(row=2, column=3, sticky="ew", pady=3)

    ttk.Label(grid, text="Dodatkowy kontekst:").grid(row=3, column=0, sticky="nw", padx=(0, 6), pady=3)
    hint_text = tk.Text(grid, height=3, wrap="word", font=("Segoe UI", 9))
    hint_text.grid(row=3, column=1, columnspan=3, sticky="ew", pady=3)

    # Tryb + info
    mode_row = ttk.Frame(params)
    mode_row.pack(fill="x", pady=(6, 0))
    mode_var = tk.StringVar(value="single")
    ttk.Radiobutton(mode_row, text="Pojedynczy post", variable=mode_var, value="single").pack(side="left")
    ttk.Radiobutton(mode_row, text="Seria postow (tylko 1 platforma)", variable=mode_var, value="series").pack(
        side="left", padx=(10, 4)
    )
    series_count_var = tk.IntVar(value=5)
    ttk.Spinbox(mode_row, from_=2, to=7, width=4, textvariable=series_count_var).pack(side="left")
    ttk.Label(mode_row, text="postow w serii", foreground="#666").pack(side="left", padx=(4, 0))

    info_lbl = ttk.Label(params, text="", foreground="#1976d2", font=("Segoe UI", 9))
    info_lbl.pack(fill="x", pady=(6, 0))

    def _refresh_info(*_a: object) -> None:
        selected = [p for p, v in plat_vars.items() if v.get()]
        n = len(selected)
        if n == 0:
            info_lbl.configure(text="⚠ Zaznacz przynajmniej 1 platforme.", foreground="#c62828")
            return
        if n == 1:
            p = platforms.get(selected[0])
            info_lbl.configure(
                text=f"{p.icon} {p.label}: {p.caption_limit} znakow caption, ~{p.recommended_hashtags} hashtagow. {p.format_hint}",
                foreground="#1976d2",
            )
        else:
            codes = ", ".join(selected)
            info_lbl.configure(
                text=f"🎯 Multi-platform: {n} wersji ({codes}). Tryb 'Seria' niedostepny - automatycznie przejdzie na 'Pojedynczy'.",
                foreground="#6a1b9a",
            )

    for v in plat_vars.values():
        v.trace_add("write", _refresh_info)
    _refresh_info()

    # ---------- Sekcja 2: prompt ----------
    prompt_frame = ttk.LabelFrame(
        root, text="2. Prompt - klik kopiuje do schowka, wklej do Opus/GPT", padding=8,
    )
    prompt_frame.pack(fill="both", expand=True, pady=(0, 6))

    btn_row = ttk.Frame(prompt_frame)
    btn_row.pack(fill="x", pady=(0, 6))

    def _build_and_copy(variant: str) -> None:
        topic = topic_var.get().strip()
        if not topic:
            messagebox.showwarning("Brak tematu", "Wpisz temat posta.", parent=dlg)
            return
        selected = [p for p, v in plat_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Brak platformy", "Zaznacz przynajmniej 1 platforme.", parent=dlg)
            return
        language = lang_var.get().strip() or "pl"
        extra_hint = hint_text.get("1.0", "end-1c").strip()
        link = link_var.get().strip()
        mode = mode_var.get()
        if mode == "series" and len(selected) > 1:
            # Force single mode
            mode = "single"
            mode_var.set("single")
            messagebox.showinfo(
                "Seria + multi-platform",
                "Tryb 'Seria' dziala tylko dla 1 platformy. Przelaczono na 'Pojedynczy'.",
                parent=dlg,
            )

        try:
            if mode == "series":
                # 1 platforma
                code = selected[0]
                count = int(series_count_var.get())
                if variant == "opus":
                    text = prompts.build_series_prompt_opus(
                        topic=topic, platform_code=code, language=language,
                        count=count, extra_hint=extra_hint, link=link,
                    )
                else:
                    text = prompts.build_series_prompt_gpt(
                        topic=topic, platform_code=code, language=language,
                        count=count, extra_hint=extra_hint, link=link,
                    )
            elif len(selected) == 1:
                # single, 1 platforma - zachowaj format single
                code = selected[0]
                if variant == "opus":
                    text = prompts.build_post_prompt_opus(
                        topic=topic, platform_code=code, language=language,
                        extra_hint=extra_hint, link=link,
                    )
                else:
                    text = prompts.build_post_prompt_gpt(
                        topic=topic, platform_code=code, language=language,
                        extra_hint=extra_hint, link=link,
                    )
            else:
                # multi-platform single mode
                if variant == "opus":
                    text = prompts.build_multi_post_prompt_opus(
                        topic=topic, platform_codes=selected, language=language,
                        extra_hint=extra_hint, link=link,
                    )
                else:
                    text = prompts.build_multi_post_prompt_gpt(
                        topic=topic, platform_codes=selected, language=language,
                        extra_hint=extra_hint, link=link,
                    )
        except ValueError as e:
            messagebox.showerror("Blad", str(e), parent=dlg)
            return

        prompt_text.delete("1.0", "end")
        prompt_text.insert("1.0", text)
        _copy_to_clipboard(dlg, text)

    ttk.Button(btn_row, text="📋 Prompt dla Claude Opus", command=lambda: _build_and_copy("opus")).pack(side="left")
    ttk.Button(btn_row, text="📋 Prompt dla GPT", command=lambda: _build_and_copy("gpt")).pack(side="left", padx=(6, 0))
    ttk.Button(
        btn_row, text="Kopiuj ponownie",
        command=lambda: _copy_to_clipboard(dlg, prompt_text.get("1.0", "end-1c")),
    ).pack(side="left", padx=(16, 0))

    pc = ttk.Frame(prompt_frame)
    pc.pack(fill="both", expand=True)
    prompt_text = tk.Text(pc, wrap="word", height=8, font=("Consolas", 9))
    psb = ttk.Scrollbar(pc, orient="vertical", command=prompt_text.yview)
    prompt_text.configure(yscrollcommand=psb.set)
    prompt_text.pack(side="left", fill="both", expand=True)
    psb.pack(side="right", fill="y")

    # ---------- Sekcja 3: odpowiedz LLM ----------
    resp_frame = ttk.LabelFrame(root, text="3. Odpowiedz z LLM (JSON)", padding=8)
    resp_frame.pack(fill="both", expand=True, pady=(0, 6))

    resp_btn = ttk.Frame(resp_frame)
    resp_btn.pack(fill="x", pady=(0, 6))

    def _paste_clipboard() -> None:
        try:
            content = dlg.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Pusty schowek", "Schowek pusty lub niedostepny.", parent=dlg)
            return
        response_text.delete("1.0", "end")
        response_text.insert("1.0", content)
        show_toast(dlg, "Wklejono ze schowka", duration_ms=1000)

    ttk.Button(resp_btn, text="📥 Wklej odpowiedz ze schowka", command=_paste_clipboard).pack(side="left")
    ttk.Button(resp_btn, text="Wyczysc", command=lambda: response_text.delete("1.0", "end")).pack(
        side="left", padx=(6, 0)
    )
    ttk.Button(
        resp_btn, text="🔍 Sprawdz i podglad",
        command=lambda: _preview(dlg, state, response_text, mode_var.get(), plat_vars, on_saved),
    ).pack(side="right")

    rc = ttk.Frame(resp_frame)
    rc.pack(fill="both", expand=True)
    response_text = tk.Text(rc, wrap="word", height=7, font=("Consolas", 9))
    rsb = ttk.Scrollbar(rc, orient="vertical", command=response_text.yview)
    response_text.configure(yscrollcommand=rsb.set)
    response_text.pack(side="left", fill="both", expand=True)
    rsb.pack(side="right", fill="y")

    bottom = ttk.Frame(root)
    bottom.pack(fill="x", pady=(6, 0))
    ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right")
    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    return dlg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_to_clipboard(dlg: tk.Toplevel, content: str) -> None:
    if not content.strip():
        return
    try:
        dlg.clipboard_clear()
        dlg.clipboard_append(content)
        dlg.update()
    except tk.TclError:
        return
    show_toast(dlg, "Skopiowano do schowka", duration_ms=1200)


def _preview(
    dlg: tk.Toplevel,
    state: dict[str, Any],
    response_text: tk.Text,
    mode: str,
    plat_vars: dict[str, tk.BooleanVar],
    on_saved: Callable[[int], None] | None,
) -> None:
    raw = response_text.get("1.0", "end-1c").strip()
    if not raw:
        messagebox.showwarning("Brak odpowiedzi", "Wklej odpowiedz z LLM.", parent=dlg)
        return

    selected = [p for p, v in plat_vars.items() if v.get()]

    try:
        if mode == "series":
            parsed = prompts.parse_series_response(raw)
            variant = "series"
        elif len(selected) > 1:
            parsed = prompts.parse_multi_post_response(raw)
            variant = "multi"
        else:
            parsed = prompts.parse_post_response(raw)
            variant = "single"
    except ValueError as e:
        messagebox.showerror("Blad parsowania", str(e), parent=dlg)
        return

    state["parsed"] = parsed
    _open_preview_dialog(dlg, parsed, variant, state, on_saved)


# ---------------------------------------------------------------------------
# Preview dialog (single / series / multi)
# ---------------------------------------------------------------------------

def _open_preview_dialog(
    parent: tk.Toplevel,
    parsed: dict[str, Any],
    variant: str,       # 'single' | 'multi' | 'series'
    state: dict[str, Any],
    on_saved: Callable[[int], None] | None,
) -> None:
    pv = tk.Toplevel(parent)
    pv.title("Podglad postow")
    pv.geometry("1000x780")
    pv.minsize(820, 640)
    try:
        pv.transient(parent)
    except tk.TclError:
        pass

    language = parsed.get("language") or "pl"
    topic = parsed.get("topic") or ""

    header = ttk.Frame(pv, padding=(12, 10))
    header.pack(fill="x")
    ttk.Label(
        header,
        text=f"🎯 {variant.upper()} · jezyk: {platforms.lang_label(language)}",
        font=("Segoe UI", 13, "bold"),
    ).pack(side="left")
    if topic:
        ttk.Label(header, text=f"Temat: {topic}", foreground="#666").pack(side="left", padx=(14, 0))

    nb = ttk.Notebook(pv)
    nb.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # Struktura: lista (platform_code, post_dict)
    post_tabs: list[tuple[str, dict[str, Any]]] = []
    if variant == "multi":
        for code, entry in (parsed.get("platforms") or {}).items():
            post_tabs.append((code, entry.get("post") or {}))
    elif variant == "series":
        # Wszystkie te same platformy
        platform_code = parsed.get("platform") or ""
        for p in parsed.get("posts") or []:
            post_tabs.append((platform_code, p))
        # Header meta
        series_meta = parsed.get("series_meta") or {}
        if series_meta:
            ttk.Label(
                pv,
                text=f"Arc: {series_meta.get('arc', '')}  |  Cadence: {series_meta.get('cadence', '')}",
                foreground="#666", font=("Segoe UI", 9, "italic"),
            ).pack(anchor="w", padx=12)
    else:
        platform_code = parsed.get("platform") or ""
        post_tabs.append((platform_code, parsed.get("post") or {}))

    widgets_list: list[tuple[str, dict[str, Any]]] = []
    for i, (code, post) in enumerate(post_tabs, 1):
        p = platforms.get(code)
        frame = ttk.Frame(nb, padding=10)
        label = f"{p.icon + ' ' if p else ''}{p.label if p else code}"
        if variant == "series":
            label = f"{label} · post {i}"
        nb.add(frame, text=label)
        w = _build_post_preview_tab(frame, post, p)
        widgets_list.append((code, w))

    # Bottom bar
    bottom = ttk.Frame(pv, padding=(12, 6))
    bottom.pack(fill="x")

    def _save_all() -> None:
        saved = 0
        series_id = ""
        if variant == "series" and len(widgets_list) > 1:
            import uuid
            series_id = uuid.uuid4().hex[:12]
        for i, (code, w) in enumerate(widgets_list):
            try:
                data = _collect_post_data(w)
            except ValueError as e:
                messagebox.showerror("Post #" + str(i + 1), str(e), parent=pv)
                return
            post = storage.Post.new(
                platform=code,
                language=language,
                topic=topic,
                title=data["title"],
                caption=data["caption"],
                on_screen_text=data["on_screen_text"],
                hashtags=data["hashtags"],
                image_hint=data["image_hint"],
                image_path=data["image_path"],
                link=data["link"],
                music_hint=data["music_hint"],
                scheduled_at=data["scheduled_at"],
                notes=data["notes"],
                series_id=series_id,
                from_task_id=state.get("from_task_id", "") or "",
            )
            storage.add_post(post)
            saved += 1
        messagebox.showinfo(
            "Zapisano",
            f"Dodano {saved} post(y/ow) do planera ze statusem 'pending'.",
            parent=pv,
        )
        if on_saved:
            try:
                on_saved(saved)
            except Exception:  # noqa: BLE001
                pass
        pv.destroy()

    ttk.Button(bottom, text="💾 Zapisz do planera", command=_save_all).pack(side="right")
    ttk.Button(bottom, text="Anuluj", command=pv.destroy).pack(side="right", padx=(0, 6))
    pv.bind("<Escape>", lambda _e: pv.destroy())


def _build_post_preview_tab(frame: ttk.Frame, post: dict[str, Any], p: platforms.Platform | None) -> dict[str, Any]:
    widgets: dict[str, Any] = {}

    title_row = ttk.Frame(frame)
    title_row.pack(fill="x", pady=(0, 4))
    ttk.Label(title_row, text="Tytul:", width=12, anchor="w").pack(side="left")
    title_var = tk.StringVar(value=post.get("title", ""))
    ttk.Entry(title_row, textvariable=title_var).pack(side="left", fill="x", expand=True)
    widgets["title_var"] = title_var

    cap_lf = ttk.LabelFrame(frame, text="Caption", padding=6)
    cap_lf.pack(fill="both", expand=True, pady=(4, 4))

    cap_info = ttk.Frame(cap_lf)
    cap_info.pack(fill="x")
    cap_len_lbl = ttk.Label(cap_info, text="", foreground="#666")
    cap_len_lbl.pack(side="left")

    cap_text = tk.Text(cap_lf, wrap="word", height=8, font=("Segoe UI", 10))
    cap_text.pack(fill="both", expand=True, pady=(4, 0))
    cap_text.insert("1.0", post.get("caption", ""))

    def _update_caption_len(*_a: object) -> None:
        text = cap_text.get("1.0", "end-1c")
        n = len(text)
        w = len(text.split())
        if p:
            over = n > p.caption_limit
            lbl = f"{n}/{p.caption_limit} znakow | {w} slow"
            if over:
                lbl += "  ⚠ przekroczono limit!"
                cap_len_lbl.configure(text=lbl, foreground="#c62828")
            elif p.caption_limit - n < 40:
                cap_len_lbl.configure(text=lbl, foreground="#ef6c00")
            else:
                cap_len_lbl.configure(text=lbl, foreground="#666")
        else:
            cap_len_lbl.configure(text=f"{n} znakow | {w} slow", foreground="#666")

    cap_text.bind("<KeyRelease>", _update_caption_len)
    _update_caption_len()
    widgets["caption_text"] = cap_text

    if p and p.code in ("ig_reels", "tiktok"):
        ost_lf = ttk.LabelFrame(frame, text="Napisy on-screen (po 1 w linii)", padding=6)
        ost_lf.pack(fill="x", pady=(4, 4))
        ost_text = tk.Text(ost_lf, wrap="word", height=3, font=("Segoe UI", 9))
        ost_text.pack(fill="x")
        ost_text.insert("1.0", "\n".join(post.get("on_screen_text", []) or []))
        widgets["ost_text"] = ost_text

        music_row = ttk.Frame(frame)
        music_row.pack(fill="x", pady=(4, 4))
        ttk.Label(music_row, text="Muzyka/dzwiek:", width=16, anchor="w").pack(side="left")
        music_var = tk.StringVar(value=post.get("music_hint", ""))
        ttk.Entry(music_row, textvariable=music_var).pack(side="left", fill="x", expand=True)
        widgets["music_var"] = music_var
    else:
        widgets["ost_text"] = None
        widgets["music_var"] = None

    ht_lf = ttk.LabelFrame(frame, text="Hashtagi (oddzielone spacja)", padding=6)
    ht_lf.pack(fill="x", pady=(4, 4))
    ht_row = ttk.Frame(ht_lf)
    ht_row.pack(fill="x")
    ht_count_lbl = ttk.Label(ht_row, text="", foreground="#666")
    ht_count_lbl.pack(side="right")
    ht_entry = ttk.Entry(ht_row, font=("Segoe UI", 10))
    ht_entry.pack(side="left", fill="x", expand=True)
    ht_entry.insert(0, " ".join(post.get("hashtags", []) or []))

    def _update_ht_count(*_a: object) -> None:
        raw = ht_entry.get().strip()
        tags = [t for t in raw.split() if t]
        n = len(tags)
        if p:
            over = n > p.hashtag_limit
            lbl = f"{n}/{p.hashtag_limit}"
            if over:
                ht_count_lbl.configure(text=lbl + " ⚠", foreground="#c62828")
            else:
                ht_count_lbl.configure(text=lbl, foreground="#666")
        else:
            ht_count_lbl.configure(text=str(n), foreground="#666")

    ht_entry.bind("<KeyRelease>", _update_ht_count)
    _update_ht_count()
    widgets["ht_entry"] = ht_entry

    img_lf = ttk.LabelFrame(frame, text="Obraz / video (sugestia + sciezka)", padding=6)
    img_lf.pack(fill="x", pady=(4, 4))

    hint_row = ttk.Frame(img_lf)
    hint_row.pack(fill="x")
    ttk.Label(hint_row, text="Sugestia:", width=12, anchor="w").pack(side="left")
    img_hint_var = tk.StringVar(value=post.get("image_hint", ""))
    ttk.Entry(hint_row, textvariable=img_hint_var).pack(side="left", fill="x", expand=True)
    widgets["img_hint_var"] = img_hint_var

    path_row = ttk.Frame(img_lf)
    path_row.pack(fill="x", pady=(4, 0))
    ttk.Label(path_row, text="Sciezka/URL:", width=12, anchor="w").pack(side="left")
    img_path_var = tk.StringVar(value=post.get("image_path", "") or "")
    ttk.Entry(path_row, textvariable=img_path_var).pack(side="left", fill="x", expand=True)

    def _pick_image() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz obraz/video",
            filetypes=[
                ("Obraz i video", "*.jpg *.jpeg *.png *.webp *.gif *.mp4 *.mov"),
                ("Wszystkie", "*.*"),
            ],
        )
        if path:
            img_path_var.set(path)

    ttk.Button(path_row, text="...", width=4, command=_pick_image).pack(side="left", padx=(4, 0))
    widgets["img_path_var"] = img_path_var

    meta_row = ttk.Frame(frame)
    meta_row.pack(fill="x", pady=(4, 0))
    meta_row.columnconfigure(1, weight=1)

    ttk.Label(meta_row, text="Link docelowy:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    link_var = tk.StringVar(value=post.get("link", ""))
    ttk.Entry(meta_row, textvariable=link_var).grid(row=0, column=1, sticky="ew", pady=2)
    widgets["link_var"] = link_var

    ttk.Label(meta_row, text="Data (YYYY-MM-DD HH:MM):").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
    scheduled_var = tk.StringVar(value="")
    ttk.Entry(meta_row, textvariable=scheduled_var).grid(row=1, column=1, sticky="ew", pady=2)
    widgets["scheduled_var"] = scheduled_var

    ttk.Label(meta_row, text="Notatki:").grid(row=2, column=0, sticky="nw", padx=(0, 6), pady=2)
    notes_text = tk.Text(meta_row, height=2, wrap="word", font=("Segoe UI", 9))
    notes_text.grid(row=2, column=1, sticky="ew", pady=2)
    widgets["notes_text"] = notes_text

    return widgets


def _collect_post_data(w: dict[str, Any]) -> dict[str, Any]:
    caption = w["caption_text"].get("1.0", "end-1c").strip()
    if not caption:
        raise ValueError("Caption nie moze byc pusty.")
    ht_raw = w["ht_entry"].get().strip()
    tags = [t if t.startswith("#") else "#" + t for t in ht_raw.split() if t]
    on_screen: list[str] = []
    if w.get("ost_text") is not None:
        raw = w["ost_text"].get("1.0", "end-1c")
        on_screen = [line.strip() for line in raw.splitlines() if line.strip()]
    return {
        "title": w["title_var"].get().strip(),
        "caption": caption,
        "on_screen_text": on_screen,
        "hashtags": tags,
        "image_hint": w["img_hint_var"].get().strip(),
        "image_path": w["img_path_var"].get().strip(),
        "link": w["link_var"].get().strip(),
        "music_hint": w["music_var"].get().strip() if w.get("music_var") is not None else "",
        "scheduled_at": w["scheduled_var"].get().strip(),
        "notes": w["notes_text"].get("1.0", "end-1c").strip(),
    }
