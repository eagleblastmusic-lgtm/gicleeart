"""GUI nakladka na `iiif_downloader.py`.

Pozwala:
- pobierac POJEDYNCZY obraz albo CALA LISTE (URL-e jeden na linie),
- wczytac liste URL-i z pliku .txt,
- ustawic parametry (workers, timeout, quality, format),
- wybrac quality "oryginalna" (= IIIF native) i format "oryginalny" (= tif).

Sledzi postep przez parsowanie linii "Postep: X/Y (Z%)" z podprocesu i pokazuje
dwa paski: "Bieżący plik" oraz "Cały batch (plik X/Y)".
"""

from __future__ import annotations

import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

APP_TITLE = "Pobierz obraz - IIIF Full Downloader"

# Regex do parsowania postepu z podprocesu.
_PROGRESS_RE = re.compile(r"Postep:\s+(\d+)/(\d+)\s+\(([\d.]+)%\)")

# Mapowanie etykiet GUI -> wartosci IIIF do CLI.
_QUALITY_LABEL_TO_IIIF = {
    "oryginalna": "native",   # IIIF v2 'native' = oryginalna jakosc serwera
    "default": "default",
    "color": "color",
    "gray": "gray",
    "bitonal": "bitonal",
}
_FORMAT_LABEL_TO_IIIF = {
    "oryginalny": "tif",      # dla wiekszosci muzeow (np. National Gallery) tif = oryginal
    "jpg": "jpg",
    "png": "png",
    "webp": "webp",
    "tif": "tif",
}

_QUALITY_LABELS = list(_QUALITY_LABEL_TO_IIIF.keys())
_FORMAT_LABELS = list(_FORMAT_LABEL_TO_IIIF.keys())


class PobierzObrazApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 960, 780)
        self.root.minsize(800, 620)

        self._proc: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._batch_thread: threading.Thread | None = None
        self._stop_requested = False
        self._log_queue: queue.Queue[str] = queue.Queue()

        self.out_dir_var = tk.StringVar()
        self.workers_var = tk.IntVar(value=8)
        self.timeout_var = tk.IntVar(value=30)
        self.quality_var = tk.StringVar(value="oryginalna")
        self.format_var = tk.StringVar(value="oryginalny")
        self.status_var = tk.StringVar(value="Gotowy.")
        self.file_progress_var = tk.DoubleVar(value=0.0)
        self.batch_progress_var = tk.DoubleVar(value=0.0)
        self.batch_label_var = tk.StringVar(value="")

        self._build_ui()
        self._poll_log()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # Krok 1: URL-e (pojedynczy lub batch z .txt)
        top = ttk.LabelFrame(self.root, text="Krok 1: URL-e obrazow (jeden na linie)")
        top.pack(fill="x", **pad)
        top.columnconfigure(0, weight=1)

        urls_frame = ttk.Frame(top)
        urls_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        urls_frame.columnconfigure(0, weight=1)

        self.urls_text = tk.Text(urls_frame, height=5, wrap="none", undo=True)
        self.urls_text.grid(row=0, column=0, sticky="ew")
        sb_y = ttk.Scrollbar(urls_frame, orient="vertical", command=self.urls_text.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.urls_text.configure(yscrollcommand=sb_y.set)

        # Przyciski po prawej stronie pola URL
        btns = ttk.Frame(top)
        btns.grid(row=0, column=1, sticky="n", padx=(0, 6), pady=6)
        ttk.Button(btns, text="Wczytaj .txt...", command=self._load_urls_from_file, width=16).pack(fill="x")
        ttk.Button(btns, text="Wyczysc", command=self._clear_urls, width=16).pack(fill="x", pady=(4, 0))

        ttk.Label(
            top,
            text=(
                "Akceptuje URL-e stron obrazow (np. nationalgallery.org.uk/paintings/...) "
                "ORAZ URL-e info.json. Linie zaczynajace sie od # sa pomijane (komentarze)."
            ),
            foreground="#666",
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        # Krok 2: parametry
        params = ttk.LabelFrame(self.root, text="Krok 2: parametry pobierania")
        params.pack(fill="x", **pad)
        params.columnconfigure(1, weight=1)

        ttk.Label(params, text="Folder docelowy:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        out_row = ttk.Frame(params)
        out_row.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self.out_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_row, text="Wybierz...", command=self._pick_output_dir).grid(row=0, column=1, padx=(6, 0))
        ttk.Label(
            params,
            text=(
                "Puste = biezacy katalog. Pliki dostaja nazwy automatycznie z URL-a "
                "(np. 'Canaletto, Antonio - Eton College.png')."
            ),
            foreground="#666",
        ).grid(row=1, column=1, sticky="w", padx=6)

        grid2 = ttk.Frame(params)
        grid2.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=8)
        for i in range(8):
            grid2.columnconfigure(i, weight=1)
        ttk.Label(grid2, text="Workers:").grid(row=0, column=0, sticky="e", padx=4)
        ttk.Spinbox(grid2, from_=1, to=64, textvariable=self.workers_var, width=6).grid(
            row=0, column=1, sticky="w", padx=4
        )
        ttk.Label(grid2, text="Timeout (s):").grid(row=0, column=2, sticky="e", padx=4)
        ttk.Spinbox(grid2, from_=5, to=600, textvariable=self.timeout_var, width=6).grid(
            row=0, column=3, sticky="w", padx=4
        )
        ttk.Label(grid2, text="Jakosc:").grid(row=0, column=4, sticky="e", padx=4)
        ttk.Combobox(
            grid2, textvariable=self.quality_var, values=_QUALITY_LABELS,
            width=12, state="readonly",
        ).grid(row=0, column=5, sticky="w", padx=4)
        ttk.Label(grid2, text="Format:").grid(row=0, column=6, sticky="e", padx=4)
        ttk.Combobox(
            grid2, textvariable=self.format_var, values=_FORMAT_LABELS,
            width=12, state="readonly",
        ).grid(row=0, column=7, sticky="w", padx=4)

        # Krok 3: akcje
        actions = ttk.Frame(self.root)
        actions.pack(fill="x", **pad)
        self.start_btn = ttk.Button(actions, text="Pobierz obraz(y)", command=self._on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions, text="Przerwij", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Instrukcja", command=self._show_help).pack(side="right")
        ttk.Label(actions, textvariable=self.status_var, foreground="#555").pack(side="left", padx=12)

        # Paski postepu
        prog = ttk.LabelFrame(self.root, text="Postep")
        prog.pack(fill="x", **pad)

        ttk.Label(prog, text="Biezacy plik:").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 0))
        ttk.Progressbar(
            prog, variable=self.file_progress_var, maximum=100.0,
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 6))

        batch_header = ttk.Frame(prog)
        batch_header.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 0))
        ttk.Label(batch_header, text="Caly batch:").pack(side="left")
        ttk.Label(batch_header, textvariable=self.batch_label_var, foreground="#555").pack(
            side="right"
        )
        ttk.Progressbar(
            prog, variable=self.batch_progress_var, maximum=100.0,
        ).grid(row=3, column=0, sticky="ew", padx=8, pady=(2, 8))
        prog.columnconfigure(0, weight=1)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        log_inner = ttk.Frame(log_frame)
        log_inner.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text = tk.Text(log_inner, height=14, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(log_inner, command=self.log_text.yview)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)

    # ---------- URL list helpers ----------
    def _load_urls_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Wczytaj liste URL-i",
            filetypes=[("Plik tekstowy", "*.txt"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie wczytac pliku:\n{e}")
            return

        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        if not lines:
            messagebox.showinfo("Pusty plik", "Plik nie zawiera zadnych linii.")
            return

        # Doklej do tego co juz jest (zeby nie kasowac istniejacych URL-i)
        cur = self.urls_text.get("1.0", "end").rstrip()
        suffix = "\n".join(lines)
        new_content = (cur + "\n" + suffix) if cur else suffix
        self.urls_text.delete("1.0", "end")
        self.urls_text.insert("1.0", new_content + "\n")
        self._append_log(f"Wczytano {len(lines)} linii z: {path}")

    def _clear_urls(self) -> None:
        self.urls_text.delete("1.0", "end")

    def _get_urls(self) -> list[str]:
        raw = self.urls_text.get("1.0", "end")
        out: list[str] = []
        for ln in raw.splitlines():
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            out.append(s)
        return out

    def _pick_output_dir(self) -> None:
        cur = self.out_dir_var.get().strip()
        path = filedialog.askdirectory(
            title="Wybierz folder docelowy",
            initialdir=cur or str(Path.cwd()),
            mustexist=False,
        )
        if path:
            self.out_dir_var.set(path)

    # ---------- Logika - pojedynczy + batch ----------
    @staticmethod
    def _detect_url_kind(url: str) -> str:
        """Zwraca '--info-url' albo '--page-url' - auto-detekcja typu URL-a."""
        u = url.strip().lower()
        if u.endswith("info.json") or "/info.json" in u:
            return "--info-url"
        return "--page-url"

    def _resolve_iiif_quality(self) -> str:
        return _QUALITY_LABEL_TO_IIIF.get(self.quality_var.get().strip().lower(), "default")

    def _resolve_iiif_format(self) -> str:
        return _FORMAT_LABEL_TO_IIIF.get(self.format_var.get().strip().lower(), "jpg")

    def _on_start(self) -> None:
        if self._batch_thread is not None and self._batch_thread.is_alive():
            messagebox.showinfo("Info", "Pobieranie juz trwa.")
            return

        urls = self._get_urls()
        if not urls:
            messagebox.showwarning(
                "Brak URL-i",
                "Wpisz przynajmniej jeden URL w polu 'URL-e obrazow'\n"
                "lub wczytaj liste z pliku .txt.",
            )
            return

        out_dir_str = self.out_dir_var.get().strip()
        out_dir = Path(out_dir_str).expanduser().resolve() if out_dir_str else Path.cwd()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Blad", f"Nie udalo sie utworzyc folderu:\n{out_dir}\n\n{e}")
            return

        self._stop_requested = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.file_progress_var.set(0.0)
        self.batch_progress_var.set(0.0)
        self.batch_label_var.set(f"0/{len(urls)}")
        self.status_var.set(f"Pobieranie {len(urls)} obraz(ow)...")
        self._append_log(f"=== START batcha: {len(urls)} URL-i, folder: {out_dir} ===")

        self._batch_thread = threading.Thread(
            target=self._run_batch,
            args=(urls, out_dir),
            daemon=True,
            name="iiif-batch",
        )
        self._batch_thread.start()

    def _on_stop(self) -> None:
        self._stop_requested = True
        if self._proc is not None and self._proc.poll() is None:
            self._append_log("[stop] Przerywam aktualne pobieranie...")
            try:
                self._proc.terminate()
            except OSError:
                try:
                    self._proc.kill()
                except OSError:
                    pass
        self.status_var.set("Przerywam...")

    def _run_batch(self, urls: list[str], out_dir: Path) -> None:
        total = len(urls)
        ok_count = 0
        fail_count = 0
        for idx, url in enumerate(urls, start=1):
            if self._stop_requested:
                break
            self.root.after(
                0, lambda n=idx, t=total: self.batch_label_var.set(f"{n - 1}/{t}")
            )
            self.root.after(
                0,
                lambda n=idx, t=total: self.batch_progress_var.set(((n - 1) / t) * 100.0),
            )
            self.root.after(0, lambda u=url, n=idx, t=total: self.status_var.set(
                f"[{n}/{t}] Pobieranie: {u[:80]}{'...' if len(u) > 80 else ''}"
            ))
            self.root.after(0, lambda: self.file_progress_var.set(0.0))
            self._log_queue.put(f"--- [{idx}/{total}] {url}")
            rc = self._download_one(url, out_dir)
            if rc == 0:
                ok_count += 1
                # Pasek pliku do 100% na koniec
                self.root.after(0, lambda: self.file_progress_var.set(100.0))
            else:
                fail_count += 1
                self._log_queue.put(f"[err] [{idx}/{total}] zakonczone z kodem {rc}")
            self.root.after(
                0, lambda n=idx, t=total: self.batch_progress_var.set((n / t) * 100.0)
            )
            self.root.after(
                0, lambda n=idx, t=total: self.batch_label_var.set(f"{n}/{t}")
            )

        self.root.after(0, lambda: self._on_batch_finished(ok_count, fail_count, total))

    def _download_one(self, url: str, out_dir: Path) -> int:
        kind_flag = self._detect_url_kind(url)
        cmd = [
            sys.executable,
            "-u",  # unbuffered stdout
            "-m",
            "Komponenty.pobierzobraz.iiif_downloader",
            kind_flag, url,
            "--workers", str(int(self.workers_var.get())),
            "--timeout", str(int(self.timeout_var.get())),
            "--quality", self._resolve_iiif_quality(),
            "--format", self._resolve_iiif_format(),
            "--progress-every", "1",
        ]
        # cursor-api/ jest parents[2] (Komponenty/pobierzobraz/gui.py).
        cwd_for_module = Path(__file__).resolve().parents[2]
        # Realny CWD = folder docelowy uzytkownika (downloader zapisuje
        # pliki relatywnie do CWD, gdy nie podano --out).
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(out_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env={**__import__("os").environ, "PYTHONPATH": str(cwd_for_module)},
            )
        except OSError as e:
            self._log_queue.put(f"[blad] Nie udalo sie uruchomic: {e}")
            return -1

        try:
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                line = line.rstrip("\r\n")
                if not line:
                    continue
                self._log_queue.put(line)
                m = _PROGRESS_RE.search(line)
                if m:
                    pct = float(m.group(3))
                    self.root.after(0, lambda p=pct: self.file_progress_var.set(p))
        except Exception as e:  # noqa: BLE001
            self._log_queue.put(f"[reader] blad: {e}")

        rc = self._proc.wait()
        self._proc = None
        return rc

    def _on_batch_finished(self, ok: int, fail: int, total: int) -> None:
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self._stop_requested:
            self.status_var.set(
                f"Przerwano. Pobrano {ok}/{total}, bledy: {fail}."
            )
            self._append_log(f"=== STOP - pobrano {ok}/{total}, bledy {fail} ===")
        else:
            self.status_var.set(
                f"Gotowe! Pobrano {ok}/{total}, bledy: {fail}."
            )
            self._append_log(f"=== KONIEC - pobrano {ok}/{total}, bledy {fail} ===")
            self.batch_progress_var.set(100.0)
        self._stop_requested = False

    # ---------- Log ----------
    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_log(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            from tkinter import messagebox
            messagebox.showinfo("Instrukcja", _POBIERZ_HELP)
            return
        show_help(self.root, title="Instrukcja - Pobierz obraz", text=_POBIERZ_HELP)


_POBIERZ_HELP = """# Pobierz obraz - IIIF Full Downloader

Aplikacja pobiera obrazy w pelnej rozdzielczosci z muzeow udostepniajacych
**IIIF Image API** (np. National Gallery, Library of Congress, MET).
Sklada obraz z setek malych kafelkow (~800x800 px) i zapisuje jako pojedynczy PNG.

## Krok 1: URL-e obrazow
- Wklej **URL strony obrazu** (np. `https://www.nationalgallery.org.uk/paintings/...`)
  ALBO **URL do info.json** (zaawansowane).
- **Jeden URL na linie** - mozesz pobierac wiele obrazow w batchu.
- **Wczytaj .txt...** - przycisk wczytuje liste URL-i z pliku tekstowego (jeden na linie).
  Pliki .txt mozesz tworzyc w notatniku, np:
  ```
  https://www.nationalgallery.org.uk/paintings/leonardo-da-vinci-the-virgin-of-the-rocks
  https://www.nationalgallery.org.uk/paintings/vincent-van-gogh-sunflowers
  # linie zaczynajace sie od # sa pomijane (komentarze)
  ```
- **Wyczysc** - kasuje wszystkie URL-e z pola.

## Krok 2: parametry pobierania
- **Folder docelowy** - gdzie zapisac pliki. Aplikacja sama tworzy podfoldery
  z autorem (np. `da Vinci, Leonardo/`). Puste = biezacy katalog.
- **Workers** (1-64) - liczba rownoleglych pobran kafelkow. Wieksza wartosc =
  szybciej, ale wieksze obciazenie serwera. Domyslnie 8.
- **Timeout** - czas (s) na pojedyncze zapytanie do serwera.
- **Jakosc**:
  - `oryginalna` (domyslnie) = `native` w IIIF, automatycznie fallback do `default` jesli serwer nie wspiera.
  - `default` / `color` / `gray` / `bitonal` = standardowe IIIF qualities.
- **Format**:
  - `oryginalny` (domyslnie) = `tif`, automatycznie fallback do `jpg` jesli serwer nie wspiera.
  - `jpg` / `png` / `webp` / `tif` = explicite.
- **Plik wynikowy zawsze jest PNG** - format powyzej dotyczy tylko sposobu w jakim
  serwer wysyla pojedyncze kafelki, ostateczny obraz jest zapisywany lossless.

## Nazewnictwo plikow
Aplikacja parsuje strone HTML i z tagu `<title>` wyciaga prawdziwego autora i tytul:
- `Leonardo da Vinci | The Virgin of the Rocks` -> folder `da Vinci, Leonardo/`,
  plik `da Vinci, Leonardo - The Virgin of the Rocks.png`
- `Follower of Leonardo da Vinci | The Virgin and Child` -> ten sam folder,
  plik `da Vinci, Leonardo - The Virgin and Child (Follower of).png`
- Wszystkie prace tego samego artysty trafiaja do **jednego folderu**, atrybucja
  ("Follower of", "Attributed to", "Circle of"...) ladnie oznacza nazwe pliku.

## Postep
- **Biezacy plik** - postep pobierania kafelkow jednego obrazu (0-100%).
- **Caly batch** - postep przez cala kolejke URL-i z licznikiem `2/7`.

## Wznowienie po przerwaniu
- W trakcie pobierania mozesz kliknac **Przerwij**. Aplikacja zatrzymuje wszystkie
  watki i nastepnym razem startuje od nowa (checkpoints sa wylaczone domyslnie).
- Jesli chcesz checkpointing, uruchom CLI bezposrednio:
  `python -m Komponenty.pobierzobraz.iiif_downloader --page-url ... --checkpoint-every 50`

## Tipy
- Dla dluuugich batchow uzyj `Workers=4-8` zeby nie banowal cie serwer NG.
- Jesli widzisz duzo `Retry .../HTTP 400`, sprawdz w logu czy nie ma podpowiedzi
  "Serwer nie wspiera quality/format" - aplikacja sama sobie poradzi za pierwszym razem.
"""


def main() -> None:
    root = tk.Tk()
    PobierzObrazApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
