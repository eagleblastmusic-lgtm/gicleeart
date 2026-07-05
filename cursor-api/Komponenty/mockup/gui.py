"""GUI: drag-and-drop obrazow -> mockup -> Shopify (mockup)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.tkdnd_safe import register_drop_target
from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.activity_log_ui import open_activity_log_dialog
from Komponenty._shared.help_dialog import show_help
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from PIL import Image, ImageTk

from .audit_dialog import open_missing_mockups_dialog
from .transparent_dialog import open_transparent_mockups_dialog
from .publish import (
    is_image_path,
    mockup_plan,
    preview_info_text,
    publish_mockup,
    render_mockup,
    save_mockup_to_disk,
)
from .templates import MockupSet, list_mockup_sets

APP_TITLE = "Mock-up"

_INSTRUKCJA = """# Mock-up — instrukcja

Komponent naklada obrazy na szablony ramek (pole A4) i wysyla wynik do **galerii produktu**
w Shopify z sufiksem **`(mockup)`**.

## Przygotowanie plikow zrodlowych

Nazwa pliku musi miec format **`Artysta - Tytul.ext`** (separator: spacja-myslnik-spacja).

Mozesz wrzucic plik **Full**, **(preview)** lub zwykly obraz bez sufiksu. Nie wrzucaj plikow `(mockup)`.

Produkt musi juz istniec w Shopify (utworzony przez **Dodaj obraz** z plikiem Full + JSON).

## Workflow

1. Wybierz **zestaw mockupu** (np. czarna ramka z bialym lub czarnym passe-partout).
2. Przeciagnij obrazy do pola **Kolejka** (lub uzyj «Wybierz pliki...»).
3. Zaznacz pozycje — po prawej zobaczysz **podglad mockupu** (pion/poziom dobierany automatycznie).
   **Kliknij w podglad**, dwuklik w kolejce lub «Pelny podglad» — wieksze okno.
   **Eksportuj na dysk** — zapisuje mockup z zaznaczonego obrazu (lub wielu) do wybranego
   folderu, bez wysylki do Shopify (`Artysta - Tytul - (mockup) - CZB.webp`).
4. **Braki na stronie** — skanuje Shopify i pokazuje produkty bez mockupow (CZB/CZCZ);
   mozesz dograc brakujace warianty jednym kliknieciem (z obrazu preview w galerii).
5. **Przezroczyste...** — lista produktow z mockupami; zaznacz oryginalny mockup,
   kliknij **Dodaj wersje przezroczysta...** i wybierz plik z dysku (ramka + grafika z alfa,
   bez bialego passe-partout). Ustaw wersje na stronie (`custom.mockup_display`).
   Mozesz usunac mockupy z galerii.
6. Kliknij **Generuj i wyslij** dopiero po sprawdzeniu podgladu:
   - pionowy obraz -> szablon pionowy, poziomy -> poziomy,
   - obraz wstawiany jest w pole A4 (cover, wycentrowany),
   - plik trafia do Shopify jako `Artysta - Tytul - (mockup) - CZB.webp` (bialy pp)
     lub `... - (mockup) - CZCZ.webp` (czarny pp) w galerii produktu.

## Szablony

Nowe mockupy dodajesz w `Komponenty/mockup/assets/` + wpis w `data/templates.json`.
Pole `slot` to `[x, y, szerokosc, wysokosc]` pola A4 w pikselach.
Jesli szablon ma przezroczyste srodek — wykrywane automatycznie.

## Wymagania

- Aktywna sesja Shopify OAuth (Token setup w GicleeApp).
- `pip install tkinterdnd2 Pillow` (patrz `requirements.txt`).
"""


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


def _expand_paths_to_images(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for fp in sorted(p.rglob("*")):
                if not is_image_path(fp):
                    continue
                key = fp.resolve()
                if key in seen:
                    continue
                seen.add(key)
                out.append(fp)
        elif is_image_path(p):
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


class MockupApp:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 920, 720)
        self.root.minsize(780, 560)

        self.sets = list_mockup_sets()
        self.queue_paths: list[Path] = []
        self._log_queue: queue.Queue[str] = queue.Queue()

        self.set_var = tk.StringVar(
            value=self.sets[0].name if self.sets else "(brak szablonow)"
        )
        self.status_var = tk.StringVar(value="Gotowy. Dodaj obrazy zrodlowe.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="")

        self._preview_cache: dict[str, Image.Image] = {}
        self._preview_job: str | None = None
        self._preview_token = 0

        self._build_ui()
        self._poll_log()

    def _selected_set(self) -> MockupSet | None:
        name = (self.set_var.get() or "").strip()
        for s in self.sets:
            if s.name == name:
                return s
        return self.sets[0] if self.sets else None

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", **pad)
        ttk.Button(toolbar, text="Instrukcja", command=self._on_help).pack(side="left")
        ttk.Button(toolbar, text="Dziennik akcji", command=self._on_activity_log).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(toolbar, text="Braki na stronie...", command=self._on_missing_mockups).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(toolbar, text="Przezroczyste...", command=self._on_transparent_mockups).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(toolbar, textvariable=self.status_var, foreground="#666").pack(side="right")

        cfg = ttk.LabelFrame(main, text="Szablon mockupu", padding=8)
        cfg.pack(fill="x", **pad)
        row = ttk.Frame(cfg)
        row.pack(fill="x")
        ttk.Label(row, text="Zestaw:").pack(side="left")
        set_names = [s.name for s in self.sets] or ["(brak)"]
        self.set_combo = ttk.Combobox(
            row, textvariable=self.set_var, values=set_names, state="readonly", width=40
        )
        self.set_combo.pack(side="left", padx=(8, 0))
        if self.sets:
            self.set_combo.current(0)
        self.set_combo.bind("<<ComboboxSelected>>", self._on_set_changed)

        self.variants_label = ttk.Label(cfg, text="", foreground="#555")
        self.variants_label.pack(anchor="w", pady=(6, 0))
        self._refresh_variants_label()

        top = ttk.Frame(main)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Wybierz pliki...", command=self._browse_files).pack(side="left")
        ttk.Button(top, text="Pelny podglad", command=self._open_full_preview).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Eksportuj na dysk...", command=self._export_to_disk).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(top, text="Usun zaznaczone", command=self._remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Wyczysc", command=self._clear_queue).pack(side="left", padx=(6, 0))

        drop_note = "" if _HAS_DND else " (brak DnD: pip install tkinterdnd2)"
        drop = ttk.LabelFrame(main, text=f"Kolejka obrazow zrodlowych{drop_note}")
        drop.pack(fill="both", expand=True, **pad)

        paned = ttk.Panedwindow(drop, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        queue_frame = ttk.Frame(paned)
        paned.add(queue_frame, weight=3)

        cols = ("file", "orient", "status")
        self.tree = ttk.Treeview(queue_frame, columns=cols, show="headings", height=10, selectmode="extended")
        self.tree.heading("file", text="Plik")
        self.tree.heading("orient", text="Orientacja")
        self.tree.heading("status", text="Status")
        self.tree.column("file", width=360, stretch=True)
        self.tree.column("orient", width=90, stretch=False)
        self.tree.column("status", width=140, stretch=False)
        sb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda _e: self._open_full_preview())

        preview_frame = ttk.LabelFrame(paned, text="Podglad mockupu", padding=6)
        paned.add(preview_frame, weight=2)

        self.preview_info_var = tk.StringVar(value="Zaznacz obraz w kolejce.")
        ttk.Label(preview_frame, textvariable=self.preview_info_var, wraplength=320, justify="left").pack(
            anchor="w", fill="x"
        )
        self.preview_canvas = tk.Canvas(
            preview_frame, bg="#eceff1", highlightthickness=1, highlightbackground="#cfd8dc"
        )
        self.preview_canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.preview_canvas.bind("<Button-1>", self._on_preview_click)
        self._preview_canvas_image_id: int | None = None
        self._preview_photo: tk.PhotoImage | None = None

        register_drop_target(self.tree, on_drop=self._on_drop)

        prog = ttk.Frame(main)
        prog.pack(fill="x", **pad)
        ttk.Progressbar(prog, variable=self.progress_var, maximum=100).pack(fill="x")
        ttk.Label(prog, textvariable=self.progress_label_var, foreground="#666").pack(anchor="w")

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=False, **pad)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        bottom = ttk.Frame(main)
        bottom.pack(fill="x", **pad)
        self.run_btn = ttk.Button(
            bottom, text="Generuj i wyslij do Shopify", command=self._run_batch
        )
        self.run_btn.pack(side="right")

    def _refresh_variants_label(self) -> None:
        variants = self._selected_set()
        if variants:
            vtxt = ", ".join(t.name for t in variants.templates)
            self.variants_label.configure(
                text=f"Warianty: {vtxt} — orientacja pion/poziom dobierana automatycznie"
            )
        else:
            self.variants_label.configure(text="Brak zdefiniowanych szablonow.")

    def _on_set_changed(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        self._preview_cache.clear()
        self._refresh_variants_label()
        self._refresh_preview()

    def _on_help(self) -> None:
        show_help(self.root, title="Instrukcja — Mock-up", text=_INSTRUKCJA)

    def _on_activity_log(self) -> None:
        open_activity_log_dialog(self.root, title="Dziennik akcji (mockup)")

    def _on_missing_mockups(self) -> None:
        open_missing_mockups_dialog(self.root, enqueue_log=self._enqueue_log)

    def _on_transparent_mockups(self) -> None:
        open_transparent_mockups_dialog(self.root, enqueue_log=self._enqueue_log)

    def _enqueue_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _poll_log(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_log)

    def _orient_label(self, path: Path) -> str:
        try:
            with Image.open(path) as im:
                w, h = im.size
            return "Poziom" if w >= h else "Pion"
        except OSError:
            return "?"

    def _preview_cache_key(self, path: Path) -> str:
        mockup_set = self._selected_set()
        set_id = mockup_set.id if mockup_set else ""
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            mtime = 0
        return f"{path.resolve()}|{set_id}|{mtime}"

    def _selected_queue_path(self) -> Path | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        for p in self.queue_paths:
            if str(p.resolve()) == iid:
                return p
        return None

    def _pil_to_photo(self, im: Image.Image, max_w: int, max_h: int) -> tk.PhotoImage:
        thumb = im.copy()
        thumb.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(thumb)

    def _show_preview_on_canvas(self, im: Image.Image | None, info: str) -> None:
        self.preview_info_var.set(info)
        self.preview_canvas.delete("all")
        self._preview_photo = None
        self._preview_canvas_image_id = None
        if im is None:
            self.preview_canvas.configure(cursor="arrow")
            self.preview_canvas.create_text(
                10, 10, anchor="nw", text="(brak podgladu)", fill="#78909c", font=("Segoe UI", 10)
            )
            return
        self.preview_canvas.configure(cursor="hand2")
        cw = max(self.preview_canvas.winfo_width(), 280)
        ch = max(self.preview_canvas.winfo_height(), 320)
        self._preview_photo = self._pil_to_photo(im, cw - 12, ch - 12)
        self._preview_canvas_image_id = self.preview_canvas.create_image(
            cw // 2, ch // 2, image=self._preview_photo, anchor="center"
        )

    def _on_preview_click(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        if self._preview_photo is None:
            return
        self._open_full_preview()

    def _on_tree_select(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        if self._preview_job:
            try:
                self.root.after_cancel(self._preview_job)
            except tk.TclError:
                pass
            self._preview_job = None
        self._preview_job = self.root.after(120, self._refresh_preview)

    def _refresh_preview(self) -> None:
        self._preview_job = None
        path = self._selected_queue_path()
        mockup_set = self._selected_set()
        if path is None:
            self._show_preview_on_canvas(None, "Zaznacz obraz w kolejce.")
            return
        if not mockup_set:
            self._show_preview_on_canvas(None, "Brak szablonu mockupu.")
            return

        cache_key = self._preview_cache_key(path)
        cached = self._preview_cache.get(cache_key)
        if cached is not None:
            try:
                template, artist, base_title = mockup_plan(path, mockup_set)
                info = preview_info_text(
                    path, template, artist, base_title, name_suffix=mockup_set.name_suffix
                )
            except Exception as exc:
                info = f"{path.name}\nBLAD: {exc}"
            self._apply_preview_result(path, cached, info)
            return

        self._preview_token += 1
        token = self._preview_token
        self._show_preview_on_canvas(None, f"Laduje podglad: {path.name}…")

        def worker() -> None:
            err: str | None = None
            img: Image.Image | None = None
            try:
                composed, template, artist, base_title = render_mockup(path, mockup_set)
                img = composed
                info_extra = preview_info_text(
                    path, template, artist, base_title, name_suffix=mockup_set.name_suffix
                )
            except Exception as exc:
                info_extra = f"{path.name}\nBLAD podgladu: {exc}"
                err = str(exc)

            def ui() -> None:
                if token != self._preview_token:
                    return
                if img is not None and err is None:
                    self._preview_cache[cache_key] = img
                self._apply_preview_result(path, img, info_extra)

            self.root.after(0, ui)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_preview_result(
        self, path: Path, im: Image.Image | None, info: str | None
    ) -> None:
        if im is None:
            self._show_preview_on_canvas(None, info or f"Nie udalo sie zbudowac podgladu: {path.name}")
            return
        if info is None:
            info = path.name
        self._show_preview_on_canvas(im, info)

    def _open_full_preview(self) -> None:
        path = self._selected_queue_path()
        if path is None:
            messagebox.showinfo(APP_TITLE, "Zaznacz obraz w kolejce, aby zobaczyc podglad.")
            return
        mockup_set = self._selected_set()
        if not mockup_set:
            messagebox.showerror(APP_TITLE, "Brak szablonow mockupu.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Podglad — {path.name}")
        position_toplevel_screen_center(win, 900, 820)
        win.minsize(640, 480)

        info_var = tk.StringVar(value="Laduje…")
        ttk.Label(win, textvariable=info_var, wraplength=860, justify="left").pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        canvas = tk.Canvas(win, bg="#eceff1", highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        photo_holder: dict[str, tk.PhotoImage | None] = {"photo": None}

        def draw(im: Image.Image) -> None:
            canvas.update_idletasks()
            cw = max(canvas.winfo_width(), 640)
            ch = max(canvas.winfo_height(), 480)
            photo_holder["photo"] = self._pil_to_photo(im, cw - 16, ch - 16)
            canvas.delete("all")
            canvas.create_image(cw // 2, ch // 2, image=photo_holder["photo"], anchor="center")

        cache_key = self._preview_cache_key(path)
        cached = self._preview_cache.get(cache_key)
        if cached is not None:
            try:
                template, artist, base_title = mockup_plan(path, mockup_set)
                info_var.set(
                    preview_info_text(
                        path, template, artist, base_title, name_suffix=mockup_set.name_suffix
                    )
                )
            except Exception as exc:
                info_var.set(f"{path.name}\nBLAD: {exc}")
            draw(cached)
        else:
            def worker() -> None:
                try:
                    composed, template, artist, base_title = render_mockup(path, mockup_set)
                    self._preview_cache[cache_key] = composed
                    txt = preview_info_text(
                        path, template, artist, base_title, name_suffix=mockup_set.name_suffix
                    )

                    def ui() -> None:
                        if not win.winfo_exists():
                            return
                        info_var.set(txt)
                        draw(composed)

                    self.root.after(0, ui)
                except Exception as exc:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror(APP_TITLE, f"Podglad: {exc}", parent=win),
                    )

            threading.Thread(target=worker, daemon=True).start()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=(0, 10))
        ttk.Button(btn_row, text="Eksportuj na dysk...", command=self._export_to_disk).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="left")

        def _on_resize(_event: tk.Event) -> None:  # type: ignore[type-arg]
            im2 = self._preview_cache.get(cache_key)
            if im2 is not None and win.winfo_exists():
                draw(im2)

        canvas.bind("<Configure>", _on_resize)

    def _add_paths(self, paths: list[Path]) -> None:
        mockup_set = self._selected_set()
        if not mockup_set:
            messagebox.showerror(APP_TITLE, "Brak zdefiniowanych szablonow mockupu.")
            return
        for p in _expand_paths_to_images(paths):
            key = p.resolve()
            if key in {x.resolve() for x in self.queue_paths}:
                continue
            self.queue_paths.append(p)
            iid = str(key)
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(p.name, self._orient_label(p), "Oczekuje"),
            )
        self.status_var.set(f"Kolejka: {len(self.queue_paths)} plik(ow).")

    def _on_drop(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        data = getattr(event, "data", "") or ""
        self._add_paths(_parse_dnd_files(data))

    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz obrazy zrodlowe",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp"),
                ("Wszystkie", "*.*"),
            ],
        )
        if paths:
            self._add_paths([Path(p) for p in paths])

    def _remove_selected(self) -> None:
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.queue_paths = [p for p in self.queue_paths if str(p.resolve()) != iid]
        self.status_var.set(f"Kolejka: {len(self.queue_paths)} plik(ow).")

    def _clear_queue(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.queue_paths.clear()
        self.status_var.set("Kolejka wyczyszczona.")

    def _set_status(self, iid: str, status: str) -> None:
        vals = self.tree.item(iid, "values")
        if vals:
            self.tree.item(iid, values=(vals[0], vals[1], status))

    def _set_progress(self, done: int, total: int, name: str) -> None:
        pct = (done / total * 100) if total else 0
        self.progress_var.set(pct)
        self.progress_label_var.set(f"{done}/{total}: {name}")

    def _selected_queue_paths(self) -> list[Path]:
        sel = self.tree.selection()
        if not sel:
            return []
        out: list[Path] = []
        for iid in sel:
            for p in self.queue_paths:
                if str(p.resolve()) == iid:
                    out.append(p)
                    break
        return out

    def _export_to_disk(self) -> None:
        mockup_set = self._selected_set()
        if not mockup_set:
            messagebox.showerror(APP_TITLE, "Brak szablonow mockupu.")
            return
        paths = self._selected_queue_paths()
        if not paths:
            messagebox.showinfo(
                APP_TITLE,
                "Zaznacz co najmniej jeden obraz w kolejce (Ctrl/Shift — wiele).",
            )
            return

        out_dir = filedialog.askdirectory(title="Folder docelowy — eksport mockupow")
        if not out_dir:
            return
        out_path = Path(out_dir)

        self.status_var.set("Eksportuje mockupy...")
        self.progress_var.set(0)

        def worker() -> None:
            ok = err = 0
            done = 0
            total = len(paths)
            saved: list[str] = []

            for src in paths:
                iid = str(src.resolve())
                try:
                    dest = save_mockup_to_disk(
                        src, mockup_set, out_path, logger=self._enqueue_log
                    )
                    ok += 1
                    saved.append(dest.name)
                    self.root.after(
                        0, lambda i=iid, n=dest.name: self._set_status(i, f"Eksport: {n[:28]}")
                    )
                except Exception as exc:
                    err += 1
                    self._enqueue_log(f"[eksport BLAD] {src.name}: {exc}")
                    self.root.after(
                        0, lambda i=iid, e=str(exc): self._set_status(i, f"BLAD: {e[:36]}")
                    )
                done += 1
                self.root.after(
                    0, lambda d=done, t=total, n=src.name: self._set_progress(d, t, n),
                )

            def _done() -> None:
                self.status_var.set(f"Eksport gotowy. OK: {ok}, bledy: {err}.")
                if ok:
                    append_activity(
                        "mockup",
                        f"Eksport mockupow: {ok} plik(ow) -> {out_path}",
                        detail=", ".join(saved[:5]) + ("…" if len(saved) > 5 else ""),
                    )
                messagebox.showinfo(
                    APP_TITLE,
                    f"Eksport zakonczony.\nFolder: {out_path}\nOK: {ok}\nBledy: {err}",
                )

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _run_batch(self) -> None:
        mockup_set = self._selected_set()
        if not mockup_set:
            messagebox.showerror(APP_TITLE, "Brak szablonow mockupu.")
            return
        paths = list(self.queue_paths)
        if not paths:
            messagebox.showinfo(APP_TITLE, "Dodaj obrazy do kolejki.")
            return

        if not messagebox.askyesno(
            APP_TITLE,
            f"Wyslac {len(paths)} mockup(ow) do Shopify?\n\n"
            "Sprawdz podglad po prawej (lub «Pelny podglad») przed wysylka.",
        ):
            return

        self.run_btn.configure(state="disabled")
        self.status_var.set("Przetwarzam...")
        self.progress_var.set(0)

        def worker() -> None:
            ok = err = 0
            done = 0
            total = len(paths)

            def one(src: Path) -> tuple[Path, dict | None, str | None]:
                try:
                    res = publish_mockup(src, mockup_set, logger=self._enqueue_log)
                    return src, res, None
                except Exception as exc:
                    return src, None, str(exc)

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(one, p): p for p in paths}
                for fut in as_completed(futures):
                    src = futures[fut]
                    iid = str(src.resolve())
                    try:
                        _, res, err_msg = fut.result()
                        if err_msg:
                            err += 1
                            self._enqueue_log(f"[BLAD] {src.name}: {err_msg}")
                            self.root.after(0, lambda i=iid, e=err_msg: self._set_status(i, f"BLAD: {e[:36]}"))
                        else:
                            ok += 1
                            pid = (res or {}).get("product_id", "?")
                            self.root.after(0, lambda i=iid, p=pid: self._set_status(i, f"OK (id={p})"))
                            append_activity(
                                "mockup",
                                f"Mockup: {src.name} -> produkt {pid}",
                                detail=(res or {}).get("admin_url", ""),
                            )
                    except Exception as exc:
                        err += 1
                        self._enqueue_log(f"[BLAD] {src.name}: {exc}")
                        self.root.after(0, lambda i=iid, e=str(exc): self._set_status(i, f"BLAD: {e[:36]}"))
                    done += 1
                    self.root.after(
                        0,
                        lambda d=done, t=total, n=src.name: self._set_progress(d, t, n),
                    )

            def _done() -> None:
                self.run_btn.configure(state="normal")
                self.status_var.set(f"Gotowe. OK: {ok}, bledy: {err}.")
                messagebox.showinfo(APP_TITLE, f"Koniec batcha.\nOK: {ok}\nBledy: {err}")

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    MockupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
