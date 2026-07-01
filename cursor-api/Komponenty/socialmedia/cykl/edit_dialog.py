"""Dialog edycji pojedynczej pozycji w kolejce cyklu.

Notebook z zakladkami:
- Podsumowanie - metadata + 3 akapity opisu + zoom hints z Opus.
- Zdjecia - 2 kolumny (FB / IG) po 3 sekcje (main, zoomy, mockup).
  Zdjecia FB sa wspolne dla FB PL i FB EN; to samo dla IG. Sekcja 'main'
  pozwala na 1 plik (nadpisuje), 'zoomy' na wiele (multi-select), 'mockup' na 1.
- FB PL / FB EN / IG PL / IG EN - tylko caption + hashtagi per kanal.

Caption sekcja:
- Text z licznikiem znakow (ostrzezenie gdy > limit platformy).
- Hashtagi jako Entry space/przecinek separowane + info o limicie.
- Checkbox 'Publikuj na tym kanale'.

Dol: harmonogram (data YYYY-MM-DD + combobox slot).
'Zastosuj' -> set manual_override=True i zapisuje.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import images, platforms_cykl as _cp, storage


def open_edit_dialog(
    parent: tk.Misc,
    item_id: str,
    on_saved: Callable[[], None] | None = None,
) -> tk.Toplevel | None:
    item = storage.get_item(item_id)
    if item is None:
        messagebox.showerror("Cykl", f"Pozycja {item_id} nie istnieje.")
        return None

    dlg = tk.Toplevel(parent)
    dlg.title(f"Edytuj: {item.artist} - {item.painting_title_pl}")
    position_toplevel_screen_center(dlg, 1100, 820)
    dlg.minsize(920, 680)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    outer = ttk.Frame(dlg, padding=(10, 8))
    outer.pack(fill="both", expand=True)

    # ---------- Header ----------
    hdr = ttk.Frame(outer)
    hdr.pack(fill="x")
    ttk.Label(
        hdr, text=f"{item.artist}: {item.painting_title_pl}",
        font=("Segoe UI", 14, "bold"),
    ).pack(side="left")
    flags = []
    if item.is_first_of_artist:
        flags.append("PIERWSZY u artysty")
    if item.is_last_of_artist:
        flags.append("OSTATNI u artysty")
    if item.is_new_artist:
        flags.append("NOWY artysta")
    if item.is_new_painting:
        flags.append("NOWY obraz")
    if flags:
        ttk.Label(hdr, text=" | ".join(flags), foreground="#e65100").pack(
            side="left", padx=(12, 0), pady=(6, 0)
        )

    # ---------- Harmonogram ----------
    sched_frame = ttk.LabelFrame(outer, text="Harmonogram", padding=8)
    sched_frame.pack(fill="x", pady=(8, 4))

    sched_row = ttk.Frame(sched_frame)
    sched_row.pack(fill="x")
    ttk.Label(sched_row, text="Data:").pack(side="left")
    date_var = tk.StringVar(value=_extract_date(item.scheduled_at))
    ttk.Entry(sched_row, textvariable=date_var, width=12).pack(side="left", padx=(6, 14))

    ttk.Label(sched_row, text="Slot:").pack(side="left")
    _slot_labels = [
        f"{_cp.SLOT_LABEL_PL[s]} ({_cp.DEFAULT_SLOT_TIMES[s]})" for s in _cp.SLOT_CODES
    ]
    slot_var = tk.StringVar(value=_slot_labels[_cp.SLOT_CODES.index(item.slot)]
                            if item.slot in _cp.SLOT_CODES else _slot_labels[0])
    ttk.Combobox(
        sched_row, textvariable=slot_var, width=16,
        values=_slot_labels, state="readonly",
    ).pack(side="left", padx=(6, 14))

    # ---------- Notebook ----------
    nb = ttk.Notebook(outer)
    nb.pack(fill="both", expand=True, pady=(6, 4))

    # Tab: Podsumowanie
    _build_summary_tab(nb, item)

    # Tab: Zdjecia (FB + IG)
    images_widgets = _build_images_tab(nb, item)

    # Tab per kanal (caption + hashtags + enable)
    channel_widgets: dict[str, dict] = {}
    for ch in _cp.all_channels():
        tab = ttk.Frame(nb, padding=(10, 8))
        nb.add(tab, text=ch.label)
        channel_widgets[ch.code] = _build_channel_caption_tab(tab, ch, item)

    # ---------- Przyciski ----------
    btns = ttk.Frame(outer)
    btns.pack(fill="x", pady=(8, 0))

    def _apply() -> None:
        # --- Harmonogram ---
        slot_idx = _slot_labels.index(slot_var.get()) if slot_var.get() in _slot_labels else 0
        slot_code = _cp.SLOT_CODES[slot_idx]
        new_date = date_var.get().strip()
        if new_date:
            try:
                date_part = datetime.strptime(new_date, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("Harmonogram", "Data w formacie YYYY-MM-DD.", parent=dlg)
                return
            time_str = _cp.DEFAULT_SLOT_TIMES[slot_code]
            hh, mm = time_str.split(":", 1)
            sched_dt = datetime(date_part.year, date_part.month, date_part.day, int(hh), int(mm))
            item.scheduled_at = sched_dt.isoformat(timespec="seconds")
            item.slot = slot_code

        # --- Zdjecia (tab Zdjecia) ---
        # FB
        item.image_fb_main = images_widgets["fb_main_var"].get()
        item.image_fb_zooms = list(images_widgets["fb_zooms_list"].get(0, "end"))
        item.image_fb_mockup = images_widgets["fb_mockup_var"].get()
        # IG
        item.image_ig_main = images_widgets["ig_main_var"].get()
        item.image_ig_zooms = list(images_widgets["ig_zooms_list"].get(0, "end"))
        item.image_ig_mockup = images_widgets["ig_mockup_var"].get()

        # Invalidate CDN cache gdy zmieniono pliki
        item.cdn_fb_main = ""
        item.cdn_fb_zooms = []
        item.cdn_fb_mockup = ""
        item.cdn_ig_main = ""
        item.cdn_ig_zooms = []
        item.cdn_ig_mockup = ""

        # --- Taby kanalow (caption + hashtagi + enabled) ---
        enabled: list[str] = []
        for ch in _cp.all_channels():
            w = channel_widgets[ch.code]
            caption = w["caption_text"].get("1.0", "end").strip()
            hashtags_raw = w["hashtags_var"].get().strip()
            hashtags = [
                ("#" + h.lstrip("#"))
                for h in hashtags_raw.replace(",", " ").split() if h.strip()
            ]
            platform = ch.platform
            lang = ch.language
            setattr(item, f"caption_{platform}_{lang}", caption)
            if hashtags:
                if lang == "pl":
                    item.hashtags_pl = hashtags
                else:
                    item.hashtags_en = hashtags
            if w["enabled_var"].get() and ch.code not in enabled:
                enabled.append(ch.code)

        item.channels_enabled = enabled or list(_cp.CHANNEL_ORDER)
        item.manual_override = True

        fields_to_save = (
            "scheduled_at", "slot",
            "image_fb_main", "image_fb_zooms", "image_fb_mockup",
            "image_ig_main", "image_ig_zooms", "image_ig_mockup",
            "cdn_fb_main", "cdn_fb_zooms", "cdn_fb_mockup",
            "cdn_ig_main", "cdn_ig_zooms", "cdn_ig_mockup",
            "caption_fb_pl", "caption_fb_en", "caption_ig_pl", "caption_ig_en",
            "hashtags_pl", "hashtags_en",
            "channels_enabled", "manual_override",
        )
        storage.update_item(item.id, **{f: getattr(item, f) for f in fields_to_save})

        if on_saved:
            try:
                on_saved()
            except Exception:  # noqa: BLE001
                pass
        dlg.destroy()

    ttk.Button(btns, text="Zastosuj", command=_apply).pack(side="right", padx=(6, 0))
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right")

    return dlg


def _extract_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).date().isoformat()
    except ValueError:
        return ""


# ---------------------------------------------------------------------------
# Tab: Podsumowanie
# ---------------------------------------------------------------------------

def _build_summary_tab(nb: ttk.Notebook, item: storage.CykleItem) -> None:
    tab = ttk.Frame(nb, padding=(10, 8))
    nb.add(tab, text="Podsumowanie")

    grid = ttk.Frame(tab)
    grid.pack(fill="x")
    grid.columnconfigure(1, weight=1)

    rows = [
        ("Artysta:", item.artist),
        ("Pozycja:", f"{item.artist_position}/{item.artist_total}"),
        ("Tytul PL:", item.painting_title_pl),
        ("Tytul EN:", item.painting_title_en),
        ("Product ID:", str(item.product_id)),
        ("CDN URL:", item.product_image_url or "(brak)"),
        ("Folder obrazow:", f"Obrazy/{item.artist_handle}/{item.painting_handle}/"),
        ("Status:", item.status),
    ]
    for r, (lbl, val) in enumerate(rows):
        ttk.Label(grid, text=lbl, font=("Segoe UI", 9, "bold")).grid(
            row=r, column=0, sticky="w", pady=2, padx=(0, 10)
        )
        ttk.Label(grid, text=val, wraplength=800, justify="left").grid(
            row=r, column=1, sticky="w", pady=2
        )

    ttk.Label(tab, text="Opis produktu (PL):", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", pady=(10, 2)
    )
    pl_text = tk.Text(tab, height=5, wrap="word", font=("Segoe UI", 9))
    pl_text.insert("1.0", item.description_pl or "(brak)")
    pl_text.configure(state="disabled")
    pl_text.pack(fill="x")

    ttk.Label(tab, text="Opis produktu (EN):", font=("Segoe UI", 10, "bold")).pack(
        anchor="w", pady=(10, 2)
    )
    en_text = tk.Text(tab, height=5, wrap="word", font=("Segoe UI", 9))
    en_text.insert("1.0", item.description_en or "(brak)")
    en_text.configure(state="disabled")
    en_text.pack(fill="x")

    if item.zoom_hints:
        ttk.Label(tab, text="Sugestie zoomow (od Opusa):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
        for h in item.zoom_hints:
            ttk.Label(tab, text=f"  - {h}", foreground="#555").pack(anchor="w")


# ---------------------------------------------------------------------------
# Tab: Zdjecia (FB | IG)
# ---------------------------------------------------------------------------

def _build_images_tab(nb: ttk.Notebook, item: storage.CykleItem) -> dict:
    tab = ttk.Frame(nb, padding=(10, 8))
    nb.add(tab, text="Zdjecia")

    ttk.Label(
        tab,
        text=(
            "Zdjecia sa WSPOLNE dla obu jezykow (FB PL + FB EN uzywaja tego samego setu FB,\n"
            "IG PL + IG EN tego samego setu IG). FB i IG moga miec rozne zestawy.\n"
            "Kolejnosc w publikacji: main -> zoomy alfabetycznie -> mockup (ostatni)."
        ),
        foreground="#555", justify="left",
    ).pack(anchor="w", pady=(0, 8))

    cols = ttk.Frame(tab)
    cols.pack(fill="both", expand=True)
    cols.columnconfigure(0, weight=1, uniform="img")
    cols.columnconfigure(1, weight=1, uniform="img")

    widgets: dict = {}
    fb_col = ttk.LabelFrame(cols, text="Facebook (PL + EN)", padding=8)
    fb_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    _build_platform_column(fb_col, item, "fb", widgets)

    ig_col = ttk.LabelFrame(cols, text="Instagram (PL + EN)", padding=8)
    ig_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    _build_platform_column(ig_col, item, "ig", widgets)

    return widgets


def _build_platform_column(
    parent: ttk.LabelFrame,
    item: storage.CykleItem,
    platform: str,   # "fb" | "ig"
    widgets: dict,
) -> None:
    """Buduje 3 sekcje (main, zoomy, mockup) dla danej platformy."""
    prefix = platform  # "fb" lub "ig"

    # --- Main ---
    main_frame = ttk.LabelFrame(parent, text="Main (glowne zdjecie)", padding=6)
    main_frame.pack(fill="x", pady=(0, 6))

    main_var = tk.StringVar(value=getattr(item, f"image_{prefix}_main", ""))
    main_entry = ttk.Entry(main_frame, textvariable=main_var, state="readonly")
    main_entry.pack(fill="x")
    main_btn_row = ttk.Frame(main_frame)
    main_btn_row.pack(fill="x", pady=(4, 0))

    def _pick_main() -> None:
        p = filedialog.askopenfilename(
            parent=parent.winfo_toplevel(),
            title=f"{platform.upper()} - wybierz glowne zdjecie",
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
        )
        if not p:
            return
        try:
            rel = images.copy_into(
                Path(p), item.artist_handle, item.painting_handle, role="main",
            )
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("Main", str(e), parent=parent.winfo_toplevel())
            return
        main_var.set(rel)

    def _clear_main() -> None:
        main_var.set("")

    ttk.Button(main_btn_row, text="Wybierz plik...", command=_pick_main).pack(side="left")
    ttk.Button(main_btn_row, text="Wyczysc", command=_clear_main).pack(side="left", padx=(6, 0))

    # --- Zoomy ---
    zooms_frame = ttk.LabelFrame(parent, text="Zoomy (zblizenia)", padding=6)
    zooms_frame.pack(fill="both", expand=True, pady=(0, 6))

    zooms_list_row = ttk.Frame(zooms_frame)
    zooms_list_row.pack(fill="both", expand=True)
    zooms_list = tk.Listbox(zooms_list_row, height=6, font=("Consolas", 9))
    zooms_list.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(zooms_list_row, orient="vertical", command=zooms_list.yview)
    sb.pack(side="left", fill="y")
    zooms_list.configure(yscrollcommand=sb.set)
    for z in getattr(item, f"image_{prefix}_zooms") or []:
        zooms_list.insert("end", z)

    zooms_btn_row = ttk.Frame(zooms_frame)
    zooms_btn_row.pack(fill="x", pady=(4, 0))

    def _add_zooms() -> None:
        paths = filedialog.askopenfilenames(
            parent=parent.winfo_toplevel(),
            title=f"{platform.upper()} - wybierz zdjecia zoomow (mozna wiele)",
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
        )
        for p in paths:
            try:
                rel = images.copy_into(
                    Path(p), item.artist_handle, item.painting_handle, role="zoom",
                )
            except (FileNotFoundError, ValueError) as e:
                messagebox.showerror("Zoomy", str(e), parent=parent.winfo_toplevel())
                continue
            zooms_list.insert("end", rel)

    def _remove_zoom() -> None:
        for i in reversed(zooms_list.curselection()):
            zooms_list.delete(i)

    def _move_zoom(direction: int) -> None:
        sel = zooms_list.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= zooms_list.size():
            return
        val = zooms_list.get(idx)
        zooms_list.delete(idx)
        zooms_list.insert(new_idx, val)
        zooms_list.selection_set(new_idx)

    ttk.Button(zooms_btn_row, text="Dodaj pliki...", command=_add_zooms).pack(side="left")
    ttk.Button(zooms_btn_row, text="Usun", command=_remove_zoom).pack(side="left", padx=(6, 0))
    ttk.Button(zooms_btn_row, text="^", width=3,
               command=lambda: _move_zoom(-1)).pack(side="left", padx=(6, 0))
    ttk.Button(zooms_btn_row, text="v", width=3,
               command=lambda: _move_zoom(1)).pack(side="left")

    # --- Mockup ---
    mockup_frame = ttk.LabelFrame(parent, text="Mockup (ramka w pokoju)", padding=6)
    mockup_frame.pack(fill="x")

    mockup_var = tk.StringVar(value=getattr(item, f"image_{prefix}_mockup", ""))
    ttk.Entry(mockup_frame, textvariable=mockup_var, state="readonly").pack(fill="x")
    mockup_btn_row = ttk.Frame(mockup_frame)
    mockup_btn_row.pack(fill="x", pady=(4, 0))

    def _pick_mockup() -> None:
        p = filedialog.askopenfilename(
            parent=parent.winfo_toplevel(),
            title=f"{platform.upper()} - wybierz mockup",
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp")],
        )
        if not p:
            return
        try:
            rel = images.copy_into(
                Path(p), item.artist_handle, item.painting_handle, role="mockup",
            )
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("Mockup", str(e), parent=parent.winfo_toplevel())
            return
        mockup_var.set(rel)

    def _clear_mockup() -> None:
        mockup_var.set("")

    ttk.Button(mockup_btn_row, text="Wybierz plik...", command=_pick_mockup).pack(side="left")
    ttk.Button(mockup_btn_row, text="Wyczysc", command=_clear_mockup).pack(side="left", padx=(6, 0))

    # Zapisz referencje dla callera
    widgets[f"{prefix}_main_var"] = main_var
    widgets[f"{prefix}_zooms_list"] = zooms_list
    widgets[f"{prefix}_mockup_var"] = mockup_var


# ---------------------------------------------------------------------------
# Tab kanalu: caption + hashtagi (bez zdjec)
# ---------------------------------------------------------------------------

def _build_channel_caption_tab(
    tab: ttk.Frame, channel: _cp.Channel, item: storage.CykleItem,
) -> dict:
    enabled_var = tk.BooleanVar(value=channel.code in item.channels_enabled)
    ttk.Checkbutton(
        tab, text=f"Publikuj na {channel.label}", variable=enabled_var,
    ).pack(anchor="w", pady=(0, 6))

    # Caption
    caption_frame = ttk.LabelFrame(tab, text="Caption", padding=6)
    caption_frame.pack(fill="both", expand=True, pady=(0, 6))

    lang = channel.language
    platform = channel.platform
    initial_caption = getattr(item, f"caption_{platform}_{lang}", "") or (
        item.caption_pl if lang == "pl" else item.caption_en
    )

    caption_text = tk.Text(caption_frame, height=14, wrap="word", font=("Segoe UI", 10))
    caption_text.insert("1.0", initial_caption)
    caption_text.pack(fill="both", expand=True)

    counter_var = tk.StringVar(value="")
    ttk.Label(caption_frame, textvariable=counter_var, foreground="#666").pack(
        anchor="e", pady=(2, 0)
    )

    limit = _cp.CAPTION_LIMITS.get(platform, 2200)

    def _update_counter(_evt: object = None) -> None:
        text = caption_text.get("1.0", "end").rstrip("\n")
        ln = len(text)
        status = "OK" if ln <= limit else "PRZEKROCZONO LIMIT!"
        counter_var.set(f"{ln} / {limit} znakow - {status}")

    caption_text.bind("<KeyRelease>", _update_counter)
    _update_counter()

    # Hashtagi
    hashtags_frame = ttk.LabelFrame(
        tab, text="Hashtagi (oddzielone spacja lub przecinkiem)", padding=6,
    )
    hashtags_frame.pack(fill="x", pady=(0, 6))
    initial_tags = " ".join(item.hashtags_pl if lang == "pl" else item.hashtags_en)
    hashtags_var = tk.StringVar(value=initial_tags)
    ttk.Entry(hashtags_frame, textvariable=hashtags_var).pack(fill="x")
    hashtag_limit = _cp.HASHTAG_LIMITS.get(platform, 30)
    ttk.Label(
        hashtags_frame,
        text=f"Limit platformy: {hashtag_limit} hashtagow",
        foreground="#666",
    ).pack(anchor="w", pady=(2, 0))

    ttk.Label(
        tab,
        text="Zdjecia dla tego kanalu edytujesz w zakladce 'Zdjecia' albo w panelu bocznym.",
        foreground="#1976d2",
    ).pack(anchor="w", pady=(4, 0))

    return {
        "enabled_var": enabled_var,
        "caption_text": caption_text,
        "counter_var": counter_var,
        "hashtags_var": hashtags_var,
    }
