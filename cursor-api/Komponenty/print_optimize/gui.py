"""GUI GicleeApp: optymalizacja, zbieranie par Whitewall, kalibracja."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from Komponenty._shared.gemini_client import gemini_api_key_hint
from Komponenty._shared.help_dialog import show_help
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .calibrate import batch_calibrate_directory
from .compare import compare_images
from .optimize import optimize_to_file
from .paths import TEST_PHOTOS_DIR, WW_PAIRS_DIR, ensure_data_dirs
from .whitewall_collect import collect_pairs_for_directory

APP_TITLE = "Optymalizacja druku"

_INSTRUKCJA = """# Optymalizacja druku

Warstwa jak Whitewall «Image optimisation»: Gemini rozpoznaje scene, potem
korekcja kontrastu / saturacji / balansu / cieni. Suwak **strength** (0–100)
dziala jak `pcStrength` u Whitewall (domyslnie 70).

## Zakladka «Optymalizuj»

Pojedynczy plik → zapis z wybranym strength. Wymaga `GEMINI_API_KEY` w
`cursor-api/.env` (chyba ze wylaczysz Gemini).

## Zakladka «Zestaw testowy»

1. Wrzuc **wlasne** zdjecia do folderu `data/test_photos/` (patrz README.txt).
2. Kliknij **Zbierz pary z Whitewall** — Playwright uploaduje kazdy plik do
   konfiguratora Whitewall i pobiera pary: `original.jpg` (WW enhancement=0,
   ten sam kadr co ww70), `ww70.jpg`, `ww100.jpg`.
3. Wymaga: `pip install playwright` oraz `python -m playwright install chromium`.

## Zakladka «Kalibracja»

Dla kazdej pary generuje `ours70.jpg` (nasz pipeline) i zapisuje
`calibration_report.json` z metrykami **dE** i **SSIM** vs Whitewall.

Nizsze dE = blizej Whitewall. SSIM > 0.85 to dobry trend.

## Zakladka «Porownaj»

Reczne porownanie dwoch plikow (np. ww70 vs ours70).

## CLI (opcjonalnie)

`python -m Komponenty.print_optimize.cli optimize ...`
"""


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


class PrintOptimizeApp:
    def __init__(self, root: tk.Misc) -> None:
        ensure_data_dirs()
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 980, 760)
        self.root.minsize(820, 620)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._busy = False

        self.input_file_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.strength_var = tk.IntVar(value=70)
        self.use_gemini_var = tk.BooleanVar(value=True)

        self.test_in_var = tk.StringVar(value=str(TEST_PHOTOS_DIR))
        self.pairs_out_var = tk.StringVar(value=str(WW_PAIRS_DIR))
        self.visible_browser_var = tk.BooleanVar(value=False)

        self.pairs_dir_var = tk.StringVar(value=str(WW_PAIRS_DIR))
        self.cal_strength_var = tk.IntVar(value=70)
        self.cal_ref_var = tk.IntVar(value=70)
        self.cal_gemini_var = tk.BooleanVar(value=True)

        self.ref_file_var = tk.StringVar()
        self.cand_file_var = tk.StringVar()
        self.compare_result_var = tk.StringVar(value="")

        self.status_var = tk.StringVar(value="Gotowy.")
        self.gemini_var = tk.StringVar(value=f"Gemini: {gemini_api_key_hint() or 'brak klucza w .env'}")

        self._build_ui()
        self._poll_log()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, textvariable=self.gemini_var, foreground="#555").pack(side="left")
        ttk.Button(top, text="Pomoc", command=self._show_help).pack(side="right")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        tab_opt = ttk.Frame(nb)
        nb.add(tab_opt, text="Optymalizuj")
        self._build_tab_optimize(tab_opt)

        tab_collect = ttk.Frame(nb)
        nb.add(tab_collect, text="Zestaw testowy")
        self._build_tab_collect(tab_collect)

        tab_cal = ttk.Frame(nb)
        nb.add(tab_cal, text="Kalibracja")
        self._build_tab_calibrate(tab_cal)

        tab_cmp = ttk.Frame(nb)
        nb.add(tab_cmp, text="Porownaj")
        self._build_tab_compare(tab_cmp)

        foot = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        foot.pack(fill="both", expand=False)
        ttk.Label(foot, textvariable=self.status_var).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(foot, height=10, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, pady=(4, 0))

    def _build_tab_optimize(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="Plik wejsciowy:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.input_file_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_input_file).grid(row=0, column=2, padx=8)

        ttk.Label(tab, text="Plik wyjsciowy:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.output_file_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_output_file).grid(row=1, column=2, padx=8)

        ttk.Label(tab, text="Strength (0–100):").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        sf = ttk.Frame(tab)
        sf.grid(row=2, column=1, sticky="ew", padx=4)
        ttk.Scale(sf, from_=0, to=100, variable=self.strength_var, orient="horizontal").pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(sf, textvariable=self.strength_var, width=4).pack(side="left", padx=6)

        ttk.Checkbutton(tab, text="Analiza sceny Gemini", variable=self.use_gemini_var).grid(
            row=3, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Button(tab, text="Optymalizuj i zapisz", command=self._run_optimize).grid(
            row=4, column=1, sticky="w", padx=4, pady=12
        )

    def _build_tab_collect(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        intro = (
            "Wrzuc wlasne zdjecia testowe do folderu wejsciowego (patrz README.txt), "
            "potem zbierz pary original / ww70 / ww100 z Whitewall."
        )
        ttk.Label(tab, text=intro, wraplength=820, justify="left").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4)
        )

        ttk.Label(tab, text="Folder zdjec testowych:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.test_in_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_test_in).grid(row=1, column=2, padx=4)
        ttk.Button(tab, text="Otworz", command=lambda: _open_folder(Path(self.test_in_var.get()))).grid(
            row=1, column=3, padx=4
        )

        ttk.Label(tab, text="Folder par (wyjscie):").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.pairs_out_var).grid(row=2, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_pairs_out).grid(row=2, column=2, padx=4)
        ttk.Button(tab, text="Otworz", command=lambda: _open_folder(Path(self.pairs_out_var.get()))).grid(
            row=2, column=3, padx=4
        )

        ttk.Checkbutton(
            tab,
            text="Pokaz przegladarke (debug Playwright)",
            variable=self.visible_browser_var,
        ).grid(row=3, column=1, sticky="w", padx=4, pady=4)

        bf = ttk.Frame(tab)
        bf.grid(row=4, column=1, sticky="w", padx=4, pady=12)
        ttk.Button(bf, text="Zbierz pary z Whitewall", command=self._run_collect).pack(side="left")
        ttk.Button(
            bf,
            text="Otworz README testow",
            command=lambda: _open_folder(TEST_PHOTOS_DIR),
        ).pack(side="left", padx=8)

    def _build_tab_calibrate(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        ttk.Label(
            tab,
            text="Generuje ours70.jpg dla kazdej pary i raport calibration_report.json.",
            wraplength=820,
            justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))

        ttk.Label(tab, text="Folder par (ww_pairs):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.pairs_dir_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_pairs_dir).grid(row=1, column=2, padx=4)

        ttk.Label(tab, text="Strength ours:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Spinbox(tab, from_=0, to=100, textvariable=self.cal_strength_var, width=6).grid(
            row=2, column=1, sticky="w", padx=4
        )

        ttk.Label(tab, text="Referencja Whitewall:").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Spinbox(tab, from_=0, to=100, textvariable=self.cal_ref_var, width=6).grid(
            row=3, column=1, sticky="w", padx=4
        )

        ttk.Checkbutton(tab, text="Gemini przy kalibracji", variable=self.cal_gemini_var).grid(
            row=4, column=1, sticky="w", padx=4, pady=4
        )

        bf = ttk.Frame(tab)
        bf.grid(row=5, column=1, sticky="w", padx=4, pady=12)
        ttk.Button(bf, text="Uruchom kalibracje", command=self._run_calibrate).pack(side="left")
        ttk.Button(
            bf,
            text="Otworz raport",
            command=self._open_calibration_report,
        ).pack(side="left", padx=8)

    def _build_tab_compare(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="Referencja (np. ww70):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.ref_file_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_ref).grid(row=0, column=2, padx=8)

        ttk.Label(tab, text="Kandydat (np. ours70):").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(tab, textvariable=self.cand_file_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(tab, text="...", width=3, command=self._pick_cand).grid(row=1, column=2, padx=8)

        ttk.Button(tab, text="Porownaj", command=self._run_compare).grid(
            row=2, column=1, sticky="w", padx=4, pady=12
        )
        ttk.Label(tab, textvariable=self.compare_result_var, wraplength=820).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=8, pady=8
        )

    def _show_help(self) -> None:
        show_help(self.root, title=f"Instrukcja — {APP_TITLE}", text=_INSTRUKCJA)

    def _log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _poll_log(self) -> None:
        try:
            while True:
                line = self._log_queue.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", line + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self._poll_log)

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self._busy = busy
        if status:
            self.status_var.set(status)

    def _run_bg(self, status: str, fn) -> None:
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Operacja juz trwa.")
            return

        def worker() -> None:
            try:
                fn()
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))
                self._log(f"BLAD: {exc}")
            finally:
                self.root.after(0, lambda: self._set_busy(False, "Gotowy."))

        self._set_busy(True, status)
        threading.Thread(target=worker, daemon=True).start()

    def _pick_input_file(self) -> None:
        p = filedialog.askopenfilename(
            filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp"), ("Wszystkie", "*.*")]
        )
        if p:
            self.input_file_var.set(p)
            inp = Path(p)
            self.output_file_var.set(str(inp.with_name(f"{inp.stem}_opt{inp.suffix}")))

    def _pick_output_file(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")])
        if p:
            self.output_file_var.set(p)

    def _pick_test_in(self) -> None:
        p = filedialog.askdirectory(initialdir=self.test_in_var.get())
        if p:
            self.test_in_var.set(p)

    def _pick_pairs_out(self) -> None:
        p = filedialog.askdirectory(initialdir=self.pairs_out_var.get())
        if p:
            self.pairs_out_var.set(p)

    def _pick_pairs_dir(self) -> None:
        p = filedialog.askdirectory(initialdir=self.pairs_dir_var.get())
        if p:
            self.pairs_dir_var.set(p)

    def _pick_ref(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Obrazy", "*.jpg *.jpeg *.png")])
        if p:
            self.ref_file_var.set(p)

    def _pick_cand(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Obrazy", "*.jpg *.jpeg *.png")])
        if p:
            self.cand_file_var.set(p)

    def _run_optimize(self) -> None:
        inp = Path(self.input_file_var.get().strip())
        out = Path(self.output_file_var.get().strip())
        if not inp.is_file():
            messagebox.showwarning(APP_TITLE, "Wybierz plik wejsciowy.")
            return
        if not out.name:
            messagebox.showwarning(APP_TITLE, "Wybierz plik wyjsciowy.")
            return

        strength = float(self.strength_var.get())
        use_gemini = bool(self.use_gemini_var.get())

        def job() -> None:
            self._log(f"Optymalizacja: {inp.name}  strength={strength:.0f}%  gemini={use_gemini}")
            params_path = out.with_suffix(out.suffix + ".params.json")
            result = optimize_to_file(
                inp,
                out,
                strength=strength,
                use_gemini=use_gemini,
                save_params_path=params_path,
                on_status=self._log,
            )
            self._log(result.params_json())
            self._log(f"Zapisano: {out}")
            self._log(f"Parametry: {params_path}")

        self._run_bg("Optymalizacja...", job)

    def _run_collect(self) -> None:
        inp = Path(self.test_in_var.get().strip())
        out = Path(self.pairs_out_var.get().strip())
        if not inp.is_dir():
            messagebox.showwarning(APP_TITLE, f"Brak folderu: {inp}")
            return
        images = [
            p
            for p in inp.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif", ".tif", ".tiff"}
        ]
        if not images:
            messagebox.showwarning(
                APP_TITLE,
                f"Brak obrazow w {inp}\n\nDodaj pliki testowe (patrz README.txt).",
            )
            return

        headless = not bool(self.visible_browser_var.get())

        def job() -> None:
            self._log(f"Zbieranie {len(images)} plikow -> {out}")
            self._log("Playwright + Whitewall (moze potrwac kilka minut)...")
            manifests = collect_pairs_for_directory(
                inp,
                out,
                headless=headless,
                on_log=self._log,
            )
            self._log(f"Gotowe: {len(manifests)} par. Index: {out / 'index.json'}")
            self._log("Nastepny krok: zakladka Kalibracja -> Uruchom kalibracje.")

        self._run_bg("Zbieranie par Whitewall...", job)

    def _run_calibrate(self) -> None:
        pairs = Path(self.pairs_dir_var.get().strip())
        if not pairs.is_dir():
            messagebox.showwarning(APP_TITLE, f"Brak folderu: {pairs}")
            return

        strength = float(self.cal_strength_var.get())
        ref = str(int(self.cal_ref_var.get()))
        use_gemini = bool(self.cal_gemini_var.get())

        def job() -> None:
            self._log(f"Kalibracja: {pairs}  ours={strength:.0f}  ref=ww{ref}")
            rows = batch_calibrate_directory(
                pairs,
                strength=strength,
                reference_strength=ref,
                use_gemini=use_gemini,
                on_log=self._log,
            )
            if not rows:
                self._log("Brak par z manifest.json — najpierw zbierz pary.")
                return
            avg_de = sum(r["metrics"]["delta_e_mean"] for r in rows) / len(rows)
            avg_ssim = sum(r["metrics"]["ssim"] for r in rows) / len(rows)
            self._log(f"Srednia: dE={avg_de:.2f}  SSIM={avg_ssim:.4f}  ({len(rows)} par)")
            self._log(f"Raport: {pairs / 'calibration_report.json'}")

        self._run_bg("Kalibracja...", job)

    def _open_calibration_report(self) -> None:
        report = Path(self.pairs_dir_var.get().strip()) / "calibration_report.json"
        if not report.is_file():
            messagebox.showinfo(APP_TITLE, f"Brak raportu:\n{report}")
            return
        if sys.platform == "win32":
            os.startfile(str(report))  # noqa: S606
        else:
            _open_folder(report.parent)

    def _run_compare(self) -> None:
        ref = Path(self.ref_file_var.get().strip())
        cand = Path(self.cand_file_var.get().strip())
        if not ref.is_file() or not cand.is_file():
            messagebox.showwarning(APP_TITLE, "Wybierz oba pliki.")
            return
        try:
            m = compare_images(ref, cand)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        text = m.summary()
        self.compare_result_var.set(text)
        self._log(f"Porownanie: {text}")


def main() -> None:
    root = tk.Tk()
    PrintOptimizeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
