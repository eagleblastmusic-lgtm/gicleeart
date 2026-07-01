"""GUI: Kreator kolaży — zaawansowane składanie grafik."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from PIL import Image, ImageTk

from .compositor import CollageImage, CollageSettings
from .layouts import CANVAS_PRESETS, LAYOUT_CHOICES
from .service import (
    build_collage,
    export_collage,
    fetch_collection_product_images,
    fetch_collections,
    exports_dir,
    is_local_image,
    load_local_images,
    upload_collage_as_bio_background,
)

APP_TITLE = "Kreator kolaży"


def _parse_dnd_files(data: str) -> list[Path]:
    out: list[Path] = []
    buf = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        elif ch == " " and not in_brace:
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(Path(buf.strip()))
    return out


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1440, 900)
    root.minsize(1100, 720)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Tk) -> None:
    state: dict[str, Any] = {
        "collections": [],
        "images": [],
        "preview_pil": None,
        "preview_full": None,
        "last_export": None,
        "_preview_ref": None,
        "selected_collection": None,
    }

    intro = ttk.Frame(host, padding=(14, 10))
    intro.pack(fill="x")
    ttk.Label(intro, text=APP_TITLE, font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(
        intro,
        text=(
            "Składaj kolaże z produktów Shopify lub plików lokalnych. "
            "Szablony układu, ramki, cienie, eksport JPG/WebP/PNG. "
            "Opcjonalnie: wyślij gotowy kolaż jako tło sekcji BIO (Tło do Bio)."
        ),
        wraplength=1200,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 0))

    body = ttk.Panedwindow(host, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=8)

    src_panel = ttk.Frame(body, padding=4)
    settings_panel = ttk.Frame(body, padding=4)
    preview_panel = ttk.Frame(body, padding=4)
    body.add(src_panel, weight=2)
    body.add(settings_panel, weight=2)
    body.add(preview_panel, weight=3)

    progress_var = tk.StringVar(value="Gotowy.")
    status_var = tk.StringVar(value="")

    # --- Źródła ---
    src_lf = ttk.LabelFrame(src_panel, text="Źródła obrazów", padding=8)
    src_lf.pack(fill="both", expand=True)

    coll_row = ttk.Frame(src_lf)
    coll_row.pack(fill="x", pady=(0, 6))
    ttk.Label(coll_row, text="Kolekcja Shopify:").pack(side="left")
    coll_var = tk.StringVar(value="")
    coll_combo = ttk.Combobox(coll_row, textvariable=coll_var, width=42, state="readonly")
    coll_combo.pack(side="left", padx=(6, 4), fill="x", expand=True)

    def _load_collection_images() -> None:
        handle_title = coll_var.get()
        if not handle_title:
            messagebox.showinfo(APP_TITLE, "Wybierz kolekcję.")
            return
        col = next(
            (c for c in state["collections"] if c.get("_label") == handle_title),
            None,
        )
        if not col:
            return
        state["selected_collection"] = col
        progress_var.set("Pobieram obrazy kolekcji…")

        def worker() -> None:
            try:
                imgs = fetch_collection_product_images(int(col["id"]), limit=24)
                host.after(0, lambda: _set_images(imgs, f"kolekcja: {col.get('title')}"))
            except Exception as exc:
                host.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))
            finally:
                host.after(0, lambda: progress_var.set("Gotowy."))

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(coll_row, text="Załaduj", command=_load_collection_images).pack(side="left", padx=2)

    file_row = ttk.Frame(src_lf)
    file_row.pack(fill="x", pady=(0, 6))

    def _add_local_files() -> None:
        paths = filedialog.askopenfilenames(
            title="Dodaj obrazy",
            filetypes=[
                ("Obrazy", "*.jpg;*.jpeg;*.png;*.webp;*.tif;*.tiff;*.bmp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if not paths:
            return
        new_imgs = load_local_images([Path(p) for p in paths])
        merged = list(state["images"]) + new_imgs
        _set_images(merged, "pliki lokalne (dodano)")

    ttk.Button(file_row, text="Dodaj pliki…", command=_add_local_files).pack(side="left")
    ttk.Button(
        file_row,
        text="Wyczyść listę",
        command=lambda: _set_images([], "—"),
    ).pack(side="left", padx=6)

    img_tree_frame = ttk.Frame(src_lf)
    img_tree_frame.pack(fill="both", expand=True, pady=(4, 0))
    img_cols = ("use", "title", "source")
    img_tree = ttk.Treeview(img_tree_frame, columns=img_cols, show="headings", height=14)
    img_tree.heading("use", text="✓")
    img_tree.heading("title", text="Obraz")
    img_tree.heading("source", text="Źródło")
    img_tree.column("use", width=28, anchor="center")
    img_tree.column("title", width=220, anchor="w", stretch=True)
    img_tree.column("source", width=100, anchor="w")
    img_vsb = ttk.Scrollbar(img_tree_frame, orient="vertical", command=img_tree.yview)
    img_tree.configure(yscrollcommand=img_vsb.set)
    img_tree.grid(row=0, column=0, sticky="nsew")
    img_vsb.grid(row=0, column=1, sticky="ns")
    img_tree_frame.rowconfigure(0, weight=1)
    img_tree_frame.columnconfigure(0, weight=1)

    img_row_map: dict[str, CollageImage] = {}

    def _refresh_image_tree() -> None:
        img_tree.delete(*img_tree.get_children())
        img_row_map.clear()
        for i, img in enumerate(state["images"]):
            src = "URL" if img.url else "plik"
            iid = img_tree.insert(
                "",
                "end",
                values=("✓" if img.selected else " ", img.title[:60], src),
            )
            img_row_map[iid] = img
        sel_count = sum(1 for im in state["images"] if im.selected)
        status_var.set(f"Obrazów: {len(state['images'])} · zaznaczonych: {sel_count}")

    def _set_images(imgs: list[CollageImage], note: str) -> None:
        state["images"] = imgs
        _refresh_image_tree()
        if note:
            progress_var.set(note)

    def _toggle_image(_evt=None) -> None:
        sel = img_tree.selection()
        if not sel:
            return
        img = img_row_map.get(sel[0])
        if not img:
            return
        img.selected = not img.selected
        _refresh_image_tree()

    img_tree.bind("<Double-1>", _toggle_image)

    sel_btns = ttk.Frame(src_lf)
    sel_btns.pack(fill="x", pady=(6, 0))
    ttk.Button(
        sel_btns,
        text="Zaznacz wszystkie",
        command=lambda: [_set_sel(True)],
    ).pack(side="left")
    ttk.Button(
        sel_btns,
        text="Odznacz wszystkie",
        command=lambda: [_set_sel(False)],
    ).pack(side="left", padx=6)

    def _set_sel(val: bool) -> None:
        for im in state["images"]:
            im.selected = val
        _refresh_image_tree()

    if _HAS_DND:

        def _on_drop(event) -> None:
            paths = [p for p in _parse_dnd_files(event.data) if is_local_image(p)]
            if paths:
                _set_images(list(state["images"]) + load_local_images(paths), "upuszczono pliki")

        img_tree.drop_target_register(DND_FILES)
        img_tree.dnd_bind("<<Drop>>", _on_drop)

    # --- Ustawienia ---
    set_lf = ttk.LabelFrame(settings_panel, text="Płótno i układ", padding=8)
    set_lf.pack(fill="both", expand=True)

    preset_var = tk.StringVar(value=CANVAS_PRESETS[0][0])
    layout_var = tk.StringVar(value=LAYOUT_CHOICES[0][0])
    layout_label_var = tk.StringVar(value=LAYOUT_CHOICES[0][1])
    seed_var = tk.IntVar(value=42)
    count_var = tk.IntVar(value=6)
    custom_w_var = tk.IntVar(value=2400)
    custom_h_var = tk.IntVar(value=1200)
    frame_w_var = tk.IntVar(value=8)
    rot_scale_var = tk.DoubleVar(value=1.0)
    card_scale_var = tk.DoubleVar(value=1.0)
    spread_var = tk.DoubleVar(value=1.0)
    spread_label_var = tk.StringVar(value="1.00")
    shadow_var = tk.BooleanVar(value=True)
    shadow_blur_var = tk.IntVar(value=14)
    shadow_alpha_var = tk.IntVar(value=90)
    gradient_var = tk.BooleanVar(value=False)
    quality_var = tk.IntVar(value=88)
    export_fmt_var = tk.StringVar(value="jpeg")

    bg_color = {"rgb": (18, 16, 14)}
    frame_color = {"rgba": (245, 242, 235, 255)}
    grad_end = {"rgb": (8, 8, 10)}

    def _on_preset(_evt=None) -> None:
        label = preset_var.get()
        for name, w, h in CANVAS_PRESETS:
            if name == label:
                custom_w_var.set(w)
                custom_h_var.set(h)
                break

    ttk.Label(set_lf, text="Preset płótna:").grid(row=0, column=0, sticky="w", pady=2)
    preset_combo = ttk.Combobox(
        set_lf,
        textvariable=preset_var,
        values=[p[0] for p in CANVAS_PRESETS],
        state="readonly",
        width=36,
    )
    preset_combo.grid(row=0, column=1, sticky="ew", pady=2)
    preset_combo.bind("<<ComboboxSelected>>", _on_preset)

    size_row = ttk.Frame(set_lf)
    size_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
    ttk.Label(size_row, text="Szer.:").pack(side="left")
    ttk.Spinbox(size_row, from_=400, to=8000, textvariable=custom_w_var, width=7).pack(
        side="left", padx=(4, 10)
    )
    ttk.Label(size_row, text="Wys.:").pack(side="left")
    ttk.Spinbox(size_row, from_=400, to=8000, textvariable=custom_h_var, width=7).pack(
        side="left", padx=4
    )

    ttk.Label(set_lf, text="Szablon układu:").grid(row=2, column=0, sticky="w", pady=2)
    layout_combo = ttk.Combobox(
        set_lf,
        textvariable=layout_label_var,
        values=[label for _, label in LAYOUT_CHOICES],
        state="readonly",
        width=36,
    )
    layout_combo.grid(row=2, column=1, sticky="ew", pady=2)

    def _on_layout(_evt=None) -> None:
        label = layout_label_var.get()
        for lid, lname in LAYOUT_CHOICES:
            if lname == label:
                layout_var.set(lid)
                break

    layout_combo.bind("<<ComboboxSelected>>", _on_layout)

    ttk.Label(set_lf, text="Liczba kafelków:").grid(row=3, column=0, sticky="w", pady=2)
    ttk.Spinbox(set_lf, from_=1, to=24, textvariable=count_var, width=8).grid(
        row=3, column=1, sticky="w", pady=2
    )

    ttk.Label(set_lf, text="Seed (losowy układ):").grid(row=4, column=0, sticky="w", pady=2)
    ttk.Spinbox(set_lf, from_=0, to=999999, textvariable=seed_var, width=10).grid(
        row=4, column=1, sticky="w", pady=2
    )

    style_lf = ttk.LabelFrame(settings_panel, text="Styl kafelków", padding=8)
    style_lf.pack(fill="x", pady=(8, 0))

    ttk.Label(style_lf, text="Ramka (px):").grid(row=0, column=0, sticky="w")
    ttk.Spinbox(style_lf, from_=0, to=40, textvariable=frame_w_var, width=6).grid(
        row=0, column=1, sticky="w"
    )
    ttk.Label(style_lf, text="Skala obrotu:").grid(row=1, column=0, sticky="w", pady=2)
    ttk.Scale(
        style_lf,
        from_=0,
        to=2,
        variable=rot_scale_var,
        orient="horizontal",
        length=160,
    ).grid(row=1, column=1, sticky="ew")
    ttk.Label(style_lf, text="Skala kafelków:").grid(row=2, column=0, sticky="w", pady=2)
    ttk.Scale(
        style_lf,
        from_=0.6,
        to=1.4,
        variable=card_scale_var,
        orient="horizontal",
        length=160,
    ).grid(row=2, column=1, sticky="ew")

    spread_row = ttk.Frame(style_lf)
    spread_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 2))
    ttk.Label(spread_row, text="Rozstawienie:").pack(side="left")
    ttk.Label(spread_row, text="zbite", foreground="#666", font=("", 8)).pack(
        side="left", padx=(6, 2)
    )

    def _on_spread(_val=None) -> None:
        spread_label_var.set(f"{float(spread_var.get()):.2f}")

    spread_scale = ttk.Scale(
        spread_row,
        from_=0.45,
        to=1.75,
        variable=spread_var,
        orient="horizontal",
        length=160,
        command=_on_spread,
    )
    spread_scale.pack(side="left", padx=2)
    ttk.Label(spread_row, text="rozsunięte", foreground="#666", font=("", 8)).pack(
        side="left", padx=(2, 6)
    )
    ttk.Label(spread_row, textvariable=spread_label_var, width=5).pack(side="left")

    ttk.Checkbutton(style_lf, text="Cień pod kartami", variable=shadow_var).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=2
    )
    sh_row = ttk.Frame(style_lf)
    sh_row.grid(row=5, column=0, columnspan=2, sticky="ew")
    ttk.Label(sh_row, text="Rozmycie:").pack(side="left")
    ttk.Spinbox(sh_row, from_=0, to=40, textvariable=shadow_blur_var, width=5).pack(
        side="left", padx=(4, 10)
    )
    ttk.Label(sh_row, text="Krycie:").pack(side="left")
    ttk.Spinbox(sh_row, from_=0, to=255, textvariable=shadow_alpha_var, width=5).pack(
        side="left", padx=4
    )

    bg_lf = ttk.LabelFrame(settings_panel, text="Tło płótna", padding=8)
    bg_lf.pack(fill="x", pady=(8, 0))

    def _pick_bg() -> None:
        rgb, _ = colorchooser.askcolor(
            color=tuple(bg_color["rgb"]),
            title="Kolor tła",
            parent=host,
        )
        if rgb:
            bg_color["rgb"] = tuple(int(c) for c in rgb)

    def _pick_frame() -> None:
        rgb, _ = colorchooser.askcolor(
            color=tuple(frame_color["rgba"][:3]),
            title="Kolor ramki",
            parent=host,
        )
        if rgb:
            frame_color["rgba"] = (*tuple(int(c) for c in rgb), 255)

    ttk.Button(bg_lf, text="Kolor tła…", command=_pick_bg).pack(side="left")
    ttk.Button(bg_lf, text="Kolor ramki…", command=_pick_frame).pack(side="left", padx=6)
    ttk.Checkbutton(bg_lf, text="Gradient tła", variable=gradient_var).pack(side="left", padx=6)

    set_lf.columnconfigure(1, weight=1)
    style_lf.columnconfigure(1, weight=1)

    def _collect_settings() -> CollageSettings:
        return CollageSettings(
            width=int(custom_w_var.get()),
            height=int(custom_h_var.get()),
            layout=layout_var.get(),
            seed=int(seed_var.get()),
            image_count=int(count_var.get()),
            bg_color=bg_color["rgb"],
            bg_gradient=bool(gradient_var.get()),
            bg_gradient_end=grad_end["rgb"],
            frame_width=int(frame_w_var.get()),
            frame_color=frame_color["rgba"],
            rotation_scale=float(rot_scale_var.get()),
            shadow=bool(shadow_var.get()),
            shadow_blur=int(shadow_blur_var.get()),
            shadow_alpha=int(shadow_alpha_var.get()),
            card_scale=float(card_scale_var.get()),
            spread=float(spread_var.get()),
            jpeg_quality=int(quality_var.get()),
            webp_quality=int(quality_var.get()),
        )

    # --- Podgląd ---
    prev_lf = ttk.LabelFrame(preview_panel, text="Podgląd", padding=8)
    prev_lf.pack(fill="both", expand=True)

    preview_frame = tk.Frame(prev_lf, bg="#141414", height=420)
    preview_frame.pack(fill="both", expand=True)
    preview_label = tk.Label(
        preview_frame,
        text="Kliknij «Generuj podgląd»",
        bg="#141414",
        fg="#888",
    )
    preview_label.pack(fill="both", expand=True)

    def _show_preview(pil_img: Image.Image) -> None:
        state["preview_full"] = pil_img
        disp = pil_img.copy()
        max_w, max_h = 680, 480
        disp.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(disp)
        state["_preview_ref"] = photo
        preview_label.configure(image=photo, text="")

    def _generate_preview() -> None:
        if not any(im.selected for im in state["images"]):
            messagebox.showwarning(APP_TITLE, "Zaznacz co najmniej jeden obraz.")
            return
        progress_var.set("Generuję kolaż…")

        def worker() -> None:
            try:
                settings = _collect_settings()
                for im in state["images"]:
                    im.pil = None
                result = build_collage(list(state["images"]), settings)

                def done() -> None:
                    state["preview_pil"] = result
                    _show_preview(result)
                    progress_var.set(
                        f"Podgląd: {result.width}×{result.height}px · "
                        f"{sum(1 for i in state['images'] if i.selected)} kafelków"
                    )

                host.after(0, done)
            except Exception as exc:
                host.after(
                    0,
                    lambda: (
                        progress_var.set("Błąd generowania."),
                        messagebox.showerror(APP_TITLE, str(exc)),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    action_row = ttk.Frame(prev_lf)
    action_row.pack(fill="x", pady=(8, 0))
    ttk.Button(action_row, text="Generuj podgląd", command=_generate_preview).pack(
        side="left"
    )

    ttk.Label(action_row, text="Eksport:").pack(side="left", padx=(12, 4))
    ttk.Combobox(
        action_row,
        textvariable=export_fmt_var,
        values=["jpeg", "webp", "png"],
        width=8,
        state="readonly",
    ).pack(side="left")
    ttk.Label(action_row, text="Jakość:").pack(side="left", padx=(8, 4))
    ttk.Spinbox(action_row, from_=60, to=100, textvariable=quality_var, width=5).pack(
        side="left"
    )

    def _export() -> None:
        pil = state.get("preview_full") or state.get("preview_pil")
        if pil is None:
            messagebox.showinfo(APP_TITLE, "Najpierw wygeneruj podgląd.")
            return
        fmt = export_fmt_var.get()
        ext = {"jpeg": ".jpg", "webp": ".webp", "png": ".png"}[fmt]
        col = state.get("selected_collection") or {}
        default_name = col.get("handle") or "kolaz"
        path = filedialog.asksaveasfilename(
            title="Zapisz kolaż",
            initialdir=str(exports_dir()),
            initialfile=f"{default_name}{ext}",
            defaultextension=ext,
            filetypes=[("Obraz", f"*{ext}"), ("Wszystkie", "*.*")],
        )
        if not path:
            return
        try:
            saved = export_collage(
                pil,
                Path(path),
                fmt=fmt,  # type: ignore[arg-type]
                quality=int(quality_var.get()),
                basename=default_name,
            )
            state["last_export"] = saved
            progress_var.set(f"Zapisano: {saved}")
            show_toast(host, "Kolaż zapisany.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _open_exports() -> None:
        folder = str(exports_dir())
        os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)

    def _upload_bio() -> None:
        pil = state.get("preview_full") or state.get("preview_pil")
        col = state.get("selected_collection")
        if pil is None:
            messagebox.showinfo(APP_TITLE, "Najpierw wygeneruj podgląd.")
            return
        if not col:
            messagebox.showinfo(
                APP_TITLE,
                "Załaduj obrazy z kolekcji Shopify — upload BIO wymaga powiązanej kolekcji.",
            )
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Wysłać kolaż jako tło BIO dla «{col.get('title')}»?",
        ):
            return
        progress_var.set("Eksport tymczasowy + upload BIO…")

        def worker() -> None:
            try:
                tmp = export_collage(
                    pil,
                    None,
                    fmt="jpeg",
                    quality=int(quality_var.get()),
                    basename=str(col.get("handle") or "kolaz"),
                )
                res = upload_collage_as_bio_background(
                    tmp,
                    int(col["id"]),
                    str(col.get("handle") or ""),
                    str(col.get("title") or ""),
                )

                def done() -> None:
                    if not res.get("ok"):
                        messagebox.showerror(APP_TITLE, res.get("error") or "Błąd uploadu.")
                        progress_var.set("Błąd uploadu BIO.")
                        return
                    progress_var.set(f"Tło BIO zapisane dla {col.get('handle')}.")
                    show_toast(host, "Upload BIO zakończony.")

                host.after(0, done)
            except Exception as exc:
                host.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(action_row, text="Zapisz…", command=_export).pack(side="left", padx=(8, 0))
    ttk.Button(action_row, text="Folder eksportów", command=_open_exports).pack(
        side="left", padx=6
    )
    ttk.Button(action_row, text="→ Tło BIO", command=_upload_bio).pack(side="left", padx=6)

    # --- Stopka ---
    foot = ttk.Frame(host, padding=(12, 0, 12, 10))
    foot.pack(fill="x")
    ttk.Label(foot, textvariable=progress_var, foreground="#333").pack(side="left")
    ttk.Label(foot, textvariable=status_var, foreground="#0a6").pack(side="right")

    def _load_collections_async() -> None:
        progress_var.set("Ładuję listę kolekcji…")

        def worker() -> None:
            try:
                cols = fetch_collections()
                for c in cols:
                    c["_label"] = f"{c.get('title', '')} ({c.get('handle', '')})"

                def done() -> None:
                    state["collections"] = cols
                    labels = [c["_label"] for c in cols]
                    coll_combo["values"] = labels
                    if labels:
                        coll_var.set(labels[0])
                    progress_var.set(f"Załadowano {len(cols)} kolekcji.")

                host.after(0, done)
            except Exception as exc:
                host.after(
                    0,
                    lambda: (
                        progress_var.set("Błąd kolekcji."),
                        messagebox.showerror(APP_TITLE, str(exc)),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    _load_collections_async()
