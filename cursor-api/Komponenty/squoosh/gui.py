"""GUI: kolejka plikow -> WebP (ustawienia Squoosh)."""

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

from .converter import (
    DEFAULT_METHOD,
    DEFAULT_QUALITY,
    OVERSIZED_JPEG_FULL,
    OVERSIZED_SCALE_WEBP,
    convert_to_webp,
    is_image_path,
    output_path_for,
)
from .squoosh_cli import squoosh_cli_available
from Komponenty._shared.tkdnd_safe import register_drop_target
from Komponenty._shared.window_geometry import position_toplevel_screen_center

APP_TITLE = "Squoosh WebP — batch"

DEFAULT_OUT_DIR = Path(
    r"E:\Firma\1. Obrazy\2. Reprodukcje\Reprodukcje Mistrzów\1. OK\2. Na stronę\KK\Full\Do dodania"
)


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
    """Plik obrazu lub folder — zwraca liste grafik (rekurencyjnie w folderze)."""
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


class SquooshApp:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 920, 720)
        self.root.minsize(780, 560)

        self.queue_paths: list[Path] = []
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._workers_var = tk.IntVar(value=2)

        self.out_dir_var = tk.StringVar(value=str(DEFAULT_OUT_DIR))
        self.name_suffix_var = tk.StringVar(value="")
        self.quality_var = tk.IntVar(value=DEFAULT_QUALITY)
        self.method_var = tk.IntVar(value=DEFAULT_METHOD)
        self.lossless_var = tk.BooleanVar(value=False)
        self.preserve_alpha_var = tk.BooleanVar(value=False)
        self.oversized_var = tk.StringVar(value=OVERSIZED_JPEG_FULL)
        self.engine_var = tk.StringVar(value="squoosh")
        self.engine_status_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Gotowy. Dodaj pliki do kolejki.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="")

        self._build_ui()
        self._poll_log()
        self._refresh_engine_status()

    def _refresh_engine_status(self) -> None:
        ok, msg = squoosh_cli_available()
        if ok:
            self.engine_status_var.set("Squoosh CLI: gotowy (oryginalny silnik WASM)")
            if self.engine_var.get() == "squoosh":
                return
        else:
            self.engine_status_var.set(f"Squoosh CLI: {msg}")
            self.engine_var.set("pillow")

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Wybierz pliki...", command=self._browse_files).pack(side="left")
        ttk.Button(top, text="Usun zaznaczone", command=self._remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Wyczysc", command=self._clear_queue).pack(side="left", padx=(6, 0))
        ttk.Label(top, textvariable=self.status_var, foreground="#666").pack(side="right")

        drop_note = "" if _HAS_DND else " (brak DnD: pip install tkinterdnd2)"
        drop = ttk.LabelFrame(main, text=f"Kolejka plikow{drop_note}")
        drop.pack(fill="both", expand=True, **pad)

        cols = ("file", "size", "status")
        self.tree = ttk.Treeview(drop, columns=cols, show="headings", height=10, selectmode="extended")
        self.tree.heading("file", text="Plik")
        self.tree.heading("size", text="Rozmiar")
        self.tree.heading("status", text="Status")
        self.tree.column("file", width=520, stretch=True)
        self.tree.column("size", width=90, stretch=False)
        self.tree.column("status", width=120, stretch=False)
        sb = ttk.Scrollbar(drop, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 6))

        for w in (drop, self.tree):
            register_drop_target(w, on_drop=self._on_drop)

        settings = ttk.LabelFrame(main, text="Ustawienia WebP (jak Squoosh)")
        settings.pack(fill="x", **pad)

        row_engine = ttk.Frame(settings)
        row_engine.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Label(row_engine, text="Silnik:").pack(side="left")
        ttk.Radiobutton(
            row_engine,
            text="Squoosh CLI (jak squoosh.app)",
            variable=self.engine_var,
            value="squoosh",
        ).pack(side="left", padx=(6, 12))
        ttk.Radiobutton(
            row_engine,
            text="Pillow (szybszy, przyblizony)",
            variable=self.engine_var,
            value="pillow",
        ).pack(side="left")
        ttk.Button(row_engine, text="Sprawdz CLI", command=self._refresh_engine_status).pack(
            side="right"
        )
        ttk.Label(
            settings,
            textvariable=self.engine_status_var,
            foreground="#666",
            wraplength=860,
        ).pack(anchor="w", padx=8, pady=(2, 4))

        row0 = ttk.Frame(settings)
        row0.pack(fill="x", padx=6, pady=6)
        ttk.Label(row0, text="Quality:").pack(side="left")
        ttk.Spinbox(row0, from_=1, to=100, textvariable=self.quality_var, width=5).pack(
            side="left", padx=(4, 16)
        )
        ttk.Label(row0, text="Effort:").pack(side="left")
        ttk.Spinbox(row0, from_=0, to=6, textvariable=self.method_var, width=5).pack(
            side="left", padx=(4, 16)
        )
        ttk.Checkbutton(row0, text="Lossless", variable=self.lossless_var).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(
            row0, text="Zachowaj przezroczystosc", variable=self.preserve_alpha_var
        ).pack(side="left")
        ttk.Label(row0, text="Workers:").pack(side="left", padx=(16, 4))
        ttk.Spinbox(row0, from_=1, to=8, textvariable=self._workers_var, width=4).pack(side="left")

        row_oversized = ttk.Frame(settings)
        row_oversized.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Label(row_oversized, text="Obraz wiekszy niz 16383 px:").pack(side="left")
        ttk.Radiobutton(
            row_oversized,
            text="Pelna rozdzielczosc → JPEG",
            variable=self.oversized_var,
            value=OVERSIZED_JPEG_FULL,
        ).pack(side="left", padx=(8, 12))
        ttk.Radiobutton(
            row_oversized,
            text="Zmniejsz do WebP",
            variable=self.oversized_var,
            value=OVERSIZED_SCALE_WEBP,
        ).pack(side="left")

        row1 = ttk.Frame(settings)
        row1.pack(fill="x", padx=6, pady=(0, 4))
        ttk.Label(row1, text="Folder wyjsciowy:").pack(side="left")
        ttk.Entry(row1, textvariable=self.out_dir_var, width=50).pack(side="left", padx=(6, 4), fill="x", expand=True)
        ttk.Button(row1, text="Wybierz...", command=self._pick_out_dir).pack(side="left")

        row_suffix = ttk.Frame(settings)
        row_suffix.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(row_suffix, text="Sufiks nazwy:").pack(side="left")
        ttk.Entry(row_suffix, textvariable=self.name_suffix_var, width=24).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(
            row_suffix,
            text='np. Full → «Tytul - Full.webp» (puste = bez zmiany nazwy)',
            foreground="#666",
        ).pack(side="left", padx=(8, 0))
        ttk.Label(
            settings,
            text=(
                "Pusty folder wyjsciowy = zapis obok pliku zrodlowego (.webp). "
                "Przeciagnij pliki lub folder. WebP max 16383 px na bok — wieksze: JPEG lub skalowanie. "
                "Domyslnie: Quality 80, Effort 4. "
                "Squoosh CLI wymaga Node.js + npm install --force w cursor-api."
            ),
            foreground="#666",
        ).pack(anchor="w", padx=8, pady=(0, 6))

        actions = ttk.Frame(main)
        actions.pack(fill="x", **pad)
        self.run_btn = ttk.Button(actions, text="Konwertuj wszystko", command=self._run_batch)
        self.run_btn.pack(side="left")

        prog = ttk.Frame(main)
        prog.pack(fill="x", **pad)
        prog.columnconfigure(1, weight=1)
        ttk.Label(prog, text="Postep:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Progressbar(prog, variable=self.progress_var, maximum=100).grid(row=0, column=1, sticky="ew")
        ttk.Label(prog, textvariable=self.progress_label_var, width=14).grid(row=0, column=2, padx=(8, 0))

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

    def _pick_out_dir(self) -> None:
        d = filedialog.askdirectory(title="Folder wyjsciowy WebP")
        if d:
            self.out_dir_var.set(d)

    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz obrazy",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.gif"),
                ("Wszystkie", "*.*"),
            ],
        )
        self._add_paths(Path(p) for p in paths)

    def _on_drop(self, event: tk.Event) -> None:
        dropped = _parse_dnd_files(event.data)
        images = _expand_paths_to_images(dropped)
        folders = sum(1 for p in dropped if Path(p).is_dir())
        self._add_paths(images)
        if folders and not images:
            self.status_var.set("Folder nie zawiera obslugiwanych obrazow (jpg, png, tiff, webp...).")

    def _add_paths(self, paths) -> None:
        added = 0
        for p in paths:
            p = Path(p)
            if not is_image_path(p):
                continue
            key = p.resolve()
            if any(existing.resolve() == key for existing in self.queue_paths):
                continue
            self.queue_paths.append(p)
            size_kb = p.stat().st_size // 1024
            self.tree.insert("", "end", iid=str(p), values=(p.name, f"{size_kb} KB", "oczekuje"))
            added += 1
        self.status_var.set(f"Kolejka: {len(self.queue_paths)} plik(ow). Dodano: {added}.")

    def _remove_selected(self) -> None:
        for iid in self.tree.selection():
            path = Path(iid)
            if path in self.queue_paths:
                self.queue_paths.remove(path)
            self.tree.delete(iid)
        self.status_var.set(f"Kolejka: {len(self.queue_paths)} plik(ow).")

    def _clear_queue(self) -> None:
        self.queue_paths.clear()
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("Kolejka pusta.")

    def _set_status(self, iid: str, status: str) -> None:
        vals = self.tree.item(iid, "values")
        if vals:
            self.tree.item(iid, values=(vals[0], vals[1], status))

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_log(self) -> None:
        try:
            while True:
                self._append_log(self._log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(120, self._poll_log)

    def _enqueue_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _set_progress(self, done: int, total: int, label: str) -> None:
        pct = (done / total * 100) if total else 0
        self.progress_var.set(pct)
        short = label if len(label) <= 28 else label[:25] + "..."
        self.progress_label_var.set(f"{done}/{total}" + (f" — {short}" if short else ""))

    def _run_batch(self) -> None:
        if not self.queue_paths:
            messagebox.showwarning(APP_TITLE, "Kolejka jest pusta.")
            return

        out_raw = self.out_dir_var.get().strip()
        out_dir = Path(out_raw) if out_raw else None
        if out_dir is not None:
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                messagebox.showerror(APP_TITLE, f"Nie mozna utworzyc folderu:\n{e}")
                return

        quality = int(self.quality_var.get())
        method = int(self.method_var.get())
        lossless = bool(self.lossless_var.get())
        preserve = bool(self.preserve_alpha_var.get())
        engine = (self.engine_var.get() or "pillow").strip().lower()
        if engine == "squoosh":
            ok, msg = squoosh_cli_available()
            if not ok:
                messagebox.showerror(
                    APP_TITLE,
                    f"Squoosh CLI niedostepny:\n{msg}\n\n"
                    "W cursor-api uruchom: npm install --force\n"
                    "Albo wybierz silnik Pillow.",
                )
                return
            workers = max(1, min(2, int(self._workers_var.get())))
        else:
            workers = max(1, min(8, int(self._workers_var.get())))
        paths = list(self.queue_paths)
        name_suffix = self.name_suffix_var.get().strip()

        self.run_btn.configure(state="disabled")
        self._set_progress(0, len(paths), "start")
        suffix_note = f" | sufiks: {name_suffix!r}" if name_suffix else ""
        self._enqueue_log(
            f"\n=== WEBP START: {len(paths)} plik(ow) | silnik: {engine}{suffix_note} ==="
        )

        def worker() -> None:
            ok, err = 0, 0
            done = 0

            def one(src: Path) -> tuple[Path, str | None]:
                dest = output_path_for(src, out_dir, name_suffix=name_suffix)
                convert_to_webp(
                    src,
                    dest,
                    quality=quality,
                    method=method,
                    lossless=lossless,
                    preserve_alpha=preserve,
                    engine=engine,
                    oversized_mode=self.oversized_var.get(),
                    logger=self._enqueue_log,
                )
                return src, None

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(one, p): p for p in paths}
                for fut in as_completed(futures):
                    src = futures[fut]
                    iid = str(src)
                    try:
                        fut.result()
                        ok += 1
                        self.root.after(0, lambda i=iid: self._set_status(i, "OK"))
                    except Exception as exc:
                        err += 1
                        self._enqueue_log(f"[BLAD] {src.name}: {exc}")
                        self.root.after(0, lambda i=iid, e=str(exc): self._set_status(i, f"BLAD: {e[:40]}"))
                    done += 1
                    self.root.after(
                        0,
                        lambda d=done, t=len(paths), n=src.name: self._set_progress(d, t, n),
                    )

            def _done() -> None:
                self.run_btn.configure(state="normal")
                self.status_var.set(f"Gotowe. OK: {ok}, bledy: {err}.")
                messagebox.showinfo(APP_TITLE, f"Konwersja zakonczona.\nOK: {ok}\nBledy: {err}")

            self.root.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    if _HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    SquooshApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
