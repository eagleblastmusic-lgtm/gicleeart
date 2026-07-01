"""GUI 'nazwijobraz' - drag-and-drop, wyszukanie tytulu, zmiana nazwy plikow.

Krok 1: dodaj pliki -> autor odczytany ze sciezki, status "do wyszukania".
Krok 2: 'Wyszukaj nazwy' -> upload obrazu na 0x0.st + SerpAPI Google Lens.
Krok 3: 'Zmien nazwy' -> przepisuje pliki na "Artist - Title.ext".
Sufiks: przed 'Wyszukaj nazwy' zmienia biezaca nazwe pliku; po wyszukiwaniu tylko
docelowa nazwa (kolumna + rename). 'Dodaj sufiks' = zaznaczone, 'Zmień na wszystkich' = cala kolejka.
"""

from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from .artist_from_path import find_artist_in_path, normalize_artist
from .env_loader import get as env_get
from .extra_searches import (
    art_institute_titles,
    art_sites_titles,
    english_title_for_foreign,
    google_text_titles,
    met_museum_titles,
    wikiart_lookup,
    wikidata_creator_label,
    wikidata_inception_year,
    wikidata_painting_lookup,
    wikimedia_commons_lookup,
    wikipedia_lookup,
    wikipedia_painting_titles,
)
from .filename_hints import parse_filename_hints
from .image_host import UploadError, upload_image_all_urls
from .env_loader import set_env_value
from .serpapi_status import SerpApiLimitError
from .image_prepare import _HAS_PIL as _HAS_PIL_FOR_RESIZE  # type: ignore[attr-defined]
from .metadata_writer import ArtworkMetadata, write_artwork_metadata
from .metadata_writer import _HAS_PIEXIF as _HAS_PIEXIF
from .renamer import (
    append_suffix_to_original_filename,
    build_new_name,
    format_artwork_title,
    is_already_named,
    rename_file,
)
from .title_resolver import (
    clean_query_seed,
    clean_title_descriptor,
    is_generic_title,
    resolve_title,
)
from .visual_search import DEFAULT_ENGINES, search_all_engines

try:
    from PIL import Image as _PILImage, ImageTk as _PILImageTk  # type: ignore
    _HAS_PIL_FOR_PREVIEW = True
except ImportError:
    _HAS_PIL_FOR_PREVIEW = False

from Komponenty._shared.window_geometry import (
    position_toplevel_screen_center,
    position_toplevel_screen_center_from_reqsize,
)


APP_TITLE = "nazwijobraz"

_QUEUE_COL_PAD = 14
_MIN_QUEUE_COL_WIDTH = 48
_MAX_QUEUE_COL_WIDTH = 520
_QUEUE_STRETCH_COL = "new_name"

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

# Liczba rownoleglych watkow przy wyszukiwaniu (upload + SerpAPI per item).
# Zwieksza throughput dla wielu plikow; SerpAPI free plan toleruje 4-5 jednoczesnie.
_SEARCH_WORKERS = 6
# Liczba zrodel online ktore odpalamy ROWNOLEGLE w obrebie jednego pliku
# (Wiki, Wikidata, Met, ArtIC, Commons, WikiArt). Visual search jest zawsze
# pierwszy (jego wynik jest nasieniem dla pozostalych).
_PER_FILE_SOURCE_WORKERS = 6

# Liczba "fazy wyszukiwania" na pojedynczy plik. Kazda zakonczona faza
# pcha pasek "Wyszukiwanie" o 1/SEARCH_PHASES wartosci pliku, dzieki czemu
# pasek rosnie plynnie nawet gdy mamy tylko 1 plik w kolejce.
# Fazy: visual, wiki, wikidata, met, artic, commons, wikiart, art_sites/google, finalize.
_SEARCH_PHASES = 9

# Co ile ms odswiezamy animator postepu (im czesciej, tym bardziej "plynnie").
_PROGRESS_TICK_MS = 30


class App:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        position_toplevel_screen_center(self.root, 1100, 780)
        self.root.minsize(900, 560)

        self.queue_items: list[dict[str, Any]] = []
        self._log_queue: queue.Queue[str] = queue.Queue()
        # Flaga "SerpAPI limit wyczerpany" - ustawiana z dowolnego watku, sprawdzana
        # przed kazdym SerpAPI call w `_process_one`. Pozwala "wstrzymac" nowe
        # zapytania SerpAPI po pierwszym 401/429/limit-message, zeby nie palic
        # request-ow w pustke. Reset gdy user zaaktualizuje klucz.
        self._serpapi_limit_event = threading.Event()
        self._serpapi_limit_reason = ""
        self._serpapi_limit_dialog_open = False
        self._serpapi_limit_lock = threading.Lock()
        self._toast_after_ids: list[Any] = []
        self._toast_win: tk.Toplevel | None = None
        self._busy = False
        # Cache per-artist + zapytanie - reset na poczatku kazdego "Wyszukaj nazwy".
        # Klucz: (source, artist_lower, query_lower) -> lista kandydatow / dict.
        self._search_cache: dict[tuple[str, str, str], Any] = {}
        self._cache_lock = threading.Lock()
        # Trwaly cache na dysku - przezywa restart aplikacji. TTL 30 dni.
        # Lokalizacja: <katalog projektu>/.cache/nazwijobraz/<source>.json
        try:
            from .disk_cache import DiskCache
            # Lokalizacja: cursor-api/.cache/nazwijobraz/<source>.json
            # gui.py jest w: cursor-api/Komponenty/nazwijobraz/gui.py
            # parents[0]=nazwijobraz, [1]=Komponenty, [2]=cursor-api.
            project_root = Path(__file__).resolve().parents[2]
            cache_dir = project_root / ".cache" / "nazwijobraz"
            # schema_version - BUMP po kazdej zmianie logiki wyszukiwania,
            # zeby zinwalidowac stare wyniki na dysku (te byly zapisane przez
            # wczesniejsza wersje kodu i moga byc bledne).
            #   v1 - poczatkowa
            #   v2 - dodano _filename_variants (Mockup, -1, -1-2 strip dla Commons/Wiki)
            #   v3 - parser Commons: italic strip, podzial "German: X English: Y",
            #        odrzucanie obj_name == nazwa pliku, odrzucanie opisu (cm/Öl)
            #   v4 - Commons fallback do page_title (wyciaga "Am Strand von ..."
            #        z "Andreas_Achenbach_Am_Strand_von_Scheveningen_1893.jpg")
            #   v5 - Commons: separacja direct match od search hits (zeby tytul
            #        innego obrazu nie wycieklll), formatversion=2, wikitext
            #        slots.main.content fallback, year strip po spacji,
            #        CamelCase split scalonego ObjectName (bei FlutTowboat -> de+en)
            #   v6 - is_direct po stem (JPG vs PNG na Commons), inventory suffix
            #        strip "(SM 875)", Title Case dla english_title z Commons
            #   v7 - _looks_english z DE/NL/FR/IT/ES function words (von, der, am...)
            #        zeby "Am Strand von Scheveningen" nie bylo brane jako EN
            #   v8 - english_title_for_foreign: czarna lista 'sold at auction' itp.
            #        + wymog overlap >=1 znaczacego slowa z foreign_title
            #   v9 - visual search rozbity per-engine (lens/yandex/bing osobne wagi),
            #        polskie generyki (obraz/rysunek/zdjecie/foto) w REJECT_FIRST_TOKENS,
            #        hint_tokens po odjeciu generykow (filename "Obraz" nie daje juz
            #        bonusu +4 dla kandydatow zawierajacych "obraz")
            self._disk_cache: DiskCache | None = DiskCache(
                cache_dir, schema_version="v9"
            )
        except Exception:  # noqa: BLE001
            self._disk_cache = None
        self._disk_flush_after_id: Any = None

        # Pre-warm sesji HTTP (TLS handshake do popularnych hostow w tle, zeby
        # pierwszy upload/lookup nie placil 100-300ms za TLS handshake).
        # Robimy to w osobnym watku, zeby nie blokowac startu GUI.
        threading.Thread(
            target=self._prewarm_http_session,
            name="http-prewarm",
            daemon=True,
        ).start()
        # Pamiec ostatniej operacji rename - umozliwia "Cofnij" jednym przyciskiem.
        # Lista (item_ref, old_path, new_path, sidecar_old, sidecar_new).
        self._last_rename_batch: list[dict[str, Any]] = []
        # Stan sortowania kolejki (klikniecie naglowka kolumny przelacza kierunek).
        self._sort_state: dict[str, str] = {}
        # Liczniki postepu - uzywane przez paski "Wgrywanie" i "Wyszukiwanie".
        # Wszystko trzymamy jako float (jednostki), zeby pasek mogl rosnac
        # plynnie przez kazda faze procesu, a nie skokowo po skonczeniu pliku.
        self._progress_lock = threading.Lock()
        self._upload_units_done = 0.0
        self._upload_units_total = 0.0
        self._upload_total_count = 0
        self._upload_pct_target = 0.0
        self._upload_pct_shown = 0.0
        self._upload_toast_shown = False
        self._search_units_done = 0.0
        self._search_units_total = 0.0
        self._search_total_count = 0
        self._search_pct_target = 0.0
        self._search_pct_shown = 0.0
        self._search_toast_shown = False

        self._build_ui()
        self._poll_log_queue()
        # Zapisz cache na dysk przy zamykaniu okna (i pozwol oknu sie zamknac).
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:  # noqa: BLE001
            pass
        # Animator paskow - dziala caly czas, plynnie zbliza wartosci pokazywane
        # na ekranie do wartosci docelowych ustawianych przez bumpery.
        self.root.after(_PROGRESS_TICK_MS, self._tick_progress)
        if not env_get("SERPAPI_KEY"):
            self._append_log(
                "[uwaga] Brak SERPAPI_KEY w cursor-api/.env - Lens i Google text beda nieaktywne "
                "(Wikipedia / Wikidata / Met / Art Institute dzialaja bez klucza)."
            )
        if not _HAS_PIL_FOR_RESIZE:
            self._append_log(
                "[uwaga] Brak Pillow - obrazy beda uploadowane bez zmniejszania. "
                "Zainstaluj: pip install Pillow"
            )
        if not _HAS_PIEXIF:
            self._append_log(
                "[uwaga] Brak piexif - oryginalny tytul nie zostanie wpisany do EXIF JPEG. "
                "Sidecar JSON nadal bedzie zapisany. Zainstaluj: pip install piexif"
            )

    # ---------------------- UI ----------------------
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        drop_text = (
            "Przeciagnij i upusc PLIKI OBRAZOW tutaj\n"
            "(autor zostanie odczytany z dowolnego segmentu sciezki, np. .../Sisley, Alfred/...)\n\n"
            "albo kliknij, aby wybrac pliki"
        ) if _HAS_DND else (
            "Kliknij, aby wybrac pliki obrazow (Ctrl/Shift = wiele)\n"
            "(drag-and-drop wymaga: pip install tkinterdnd2)\n\n"
            "Autor odczytany z dowolnego segmentu sciezki pliku."
        )
        self.drop_label = tk.Label(
            main,
            text=drop_text,
            relief="groove",
            bd=2,
            bg="#f5f5f5",
            fg="#333",
            cursor="hand2",
            height=4,
            font=("Segoe UI", 10),
        )
        self.drop_label.pack(fill="x", **pad)
        self.drop_label.bind("<Button-1>", lambda _e: self._browse_files())
        if _HAS_DND:
            self.drop_label.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

        list_frame = ttk.LabelFrame(main, text="Kolejka plikow")
        self._list_frame = list_frame
        list_frame.pack(fill="both", expand=True, **pad)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        cols = ("file", "artist", "title", "new_name", "status")
        self._queue_col_ids = cols
        self._queue_heading_text = {
            "file": "Plik (oryginalny)",
            "artist": "Autor (ze sciezki)",
            "title": "Tytul (z internetu)",
            "new_name": "Nowa nazwa",
            "status": "Status",
        }
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(
                c, text=self._queue_heading_text[c],
                command=lambda col=c: self._sort_by_column(col),
            )
            self.tree.column(
                c,
                width=_MIN_QUEUE_COL_WIDTH,
                anchor="w",
                stretch=(c == _QUEUE_STRETCH_COL),
                minwidth=_MIN_QUEUE_COL_WIDTH,
            )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        self.tree.bind("<Configure>", self._on_tree_configure, add="+")
        self.tree.bind("<Double-1>", self._on_tree_double_click, add="+")
        # Klik wiersza -> aktualizuj panel podgladu (debounced w handlerze).
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select, add="+")
        # Menu kontekstowe pod prawym klikiem (Windows = Button-3).
        self._build_context_menu()
        self.tree.bind("<Button-3>", self._on_tree_context, add="+")

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self._tree_scroll = tree_scroll
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=6)

        queue_btns = ttk.Frame(list_frame)
        self._queue_btns_frame = queue_btns
        ttk.Button(queue_btns, text="Usun zaznaczone", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(queue_btns, text="Wyczysc liste", command=self._clear_queue).pack(fill="x", pady=2)
        ttk.Separator(queue_btns, orient="horizontal").pack(fill="x", pady=8)
        ttk.Button(queue_btns, text="Edytuj autora...", command=self._edit_artist_dialog).pack(fill="x", pady=2)
        ttk.Button(queue_btns, text="Edytuj tytul...", command=self._edit_title_dialog).pack(fill="x", pady=2)
        self.counts_var = tk.StringVar(value="0 plikow")
        ttk.Label(queue_btns, textvariable=self.counts_var, foreground="#0a6").pack(fill="x", pady=(10, 2))

        # Panel podgladu obrazu - thumbnail aktualnie zaznaczonego wiersza.
        # Wymaga Pillow (PIL); bez Pillow pokazujemy tylko nazwe pliku.
        ttk.Separator(queue_btns, orient="horizontal").pack(fill="x", pady=(8, 4))
        ttk.Label(queue_btns, text="Podglad:", foreground="#666").pack(anchor="w", pady=(0, 2))
        self._preview_size = (200, 160)
        self.preview_panel = tk.Label(
            queue_btns,
            text="(zaznacz wiersz aby zobaczyc podglad)",
            relief="groove",
            bd=1,
            bg="#fafafa",
            fg="#999",
            width=26,
            height=10,
            wraplength=180,
            justify="center",
            anchor="center",
            cursor="hand2",
        )
        self.preview_panel.pack(fill="x", pady=2)
        self.preview_panel.bind(
            "<Button-1>",
            lambda _e: self._open_preview_window(),
        )
        # Cache miniatur (item.path -> PhotoImage) zeby nie generowac przy kazdym kliku.
        self._preview_cache: dict[str, Any] = {}
        self._preview_current_path: Path | None = None
        # Trzymamy referencje na PhotoImage, inaczej Tk garbage-colectuje obraz i znika.
        self._preview_photo: Any = None
        queue_btns.grid(row=0, column=2, sticky="ns", padx=(4, 6), pady=6)

        actions = ttk.Frame(main)
        actions.pack(fill="x", **pad)
        self.search_btn = ttk.Button(actions, text="Wyszukaj nazwy", command=self._on_search_clicked)
        self.search_btn.pack(side="left")
        self.rename_btn = ttk.Button(actions, text="Zmien nazwy", command=self._on_rename_clicked, state="disabled")
        self.rename_btn.pack(side="left", padx=8)
        self.undo_btn = ttk.Button(
            actions, text="Cofnij ostatni rename",
            command=self._on_undo_rename, state="disabled",
        )
        self.undo_btn.pack(side="left")

        # Sufiks doklejany osobnym przyciskiem "Dodaj sufiks" (nie w "Zmien nazwy").
        # Format: "... - Tytul - Mockup.jpg" po kliknieciu, gdy w polu np. "Mockup".
        ttk.Separator(actions, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(actions, text="Sufiks:").pack(side="left", padx=(0, 4))
        self.suffix_var = tk.StringVar(value="")
        self.suffix_entry = ttk.Entry(actions, textvariable=self.suffix_var, width=18)
        self.suffix_entry.pack(side="left", padx=(0, 6))
        # Odswiez kolumne "Nowa nazwa" przy zmianie sufiksu (podglad przed/po wyszukiwaniu).
        self.suffix_var.trace_add("write", lambda *_: self._refresh_tree())
        self.suffix_rename_btn = ttk.Button(
            actions,
            text="Dodaj sufiks",
            command=self._on_add_suffix_clicked,
            state="disabled",
        )
        self.suffix_rename_btn.pack(side="left")
        self.suffix_all_btn = ttk.Button(
            actions,
            text="Zmień na wszystkich",
            command=self._on_suffix_all_clicked,
            state="disabled",
        )
        self.suffix_all_btn.pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Instrukcja", command=self._show_help).pack(side="right")
        ttk.Button(
            actions, text="Wyczysc cache",
            command=self._on_clear_cache_clicked,
        ).pack(side="right", padx=(0, 6))
        self.status_var = tk.StringVar(value="Gotowy. Dodaj pliki do kolejki.")
        ttk.Label(actions, textvariable=self.status_var, foreground="#666").pack(side="left", padx=12)

        # Paski postepu: Wgrywanie + Wyszukiwanie nazwy
        progress_frame = ttk.Frame(main)
        progress_frame.pack(fill="x", **pad)
        progress_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(3, weight=1)

        ttk.Label(progress_frame, text="Wgrywanie:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.upload_progress = ttk.Progressbar(
            progress_frame, mode="determinate", maximum=100.0, value=0.0
        )
        self.upload_progress.grid(row=0, column=1, sticky="ew")
        self.upload_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.upload_progress_var, width=6, foreground="#0a6").grid(
            row=0, column=2, sticky="w", padx=(8, 16)
        )

        ttk.Label(progress_frame, text="Wyszukiwanie:").grid(row=0, column=3, sticky="w", padx=(0, 6))
        self.search_progress = ttk.Progressbar(
            progress_frame, mode="determinate", maximum=100.0, value=0.0
        )
        self.search_progress.grid(row=0, column=4, sticky="ew")
        self.search_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.search_progress_var, width=6, foreground="#0a6").grid(
            row=0, column=5, sticky="w", padx=(8, 0)
        )
        progress_frame.columnconfigure(4, weight=1)

        log_frame = ttk.LabelFrame(main, text="Log")
        log_frame.pack(fill="both", expand=False, **pad)
        from tkinter import scrolledtext
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_text.configure(state="disabled")

    # ---------------------- Toasty + paski postepu ----------------------
    def _show_toast(self, msg: str, *, color: str = "#0a6", duration_ms: int = 1700) -> None:
        """Pokaz krotki komunikat fade-out na dole okna."""
        # Anuluj poprzedni toast.
        for aid in self._toast_after_ids:
            try:
                self.root.after_cancel(aid)
            except tk.TclError:
                pass
        self._toast_after_ids.clear()
        if self._toast_win is not None:
            try:
                self._toast_win.destroy()
            except tk.TclError:
                pass
            self._toast_win = None

        try:
            tw = tk.Toplevel(self.root)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            tw.configure(bg=color)
            lbl = tk.Label(
                tw, text=msg, fg="white", bg=color,
                font=("Segoe UI", 10, "bold"),
                padx=14, pady=8,
            )
            lbl.pack()
            self.root.update_idletasks()
            x = self.root.winfo_rootx() + self.root.winfo_width() // 2 - tw.winfo_reqwidth() // 2
            y = self.root.winfo_rooty() + self.root.winfo_height() - 80
            tw.geometry(f"+{x}+{y}")
            self._toast_win = tw
            self._toast_after_ids.append(self.root.after(duration_ms, self._cancel_toast))
        except tk.TclError:
            pass

    def _cancel_toast(self) -> None:
        if self._toast_win is not None:
            try:
                self._toast_win.destroy()
            except tk.TclError:
                pass
            self._toast_win = None
        self._toast_after_ids.clear()

    # ---------- Heurystyki tytul EN vs oryginalny ----------
    # Slowa funkcyjne charakterystyczne dla nieangielskich jezykow.
    # Obecnosc takiego slowa silnie sugeruje ze tekst NIE jest angielski,
    # nawet jesli wyglada jak ASCII (np. "Am Strand von Scheveningen").
    _NON_EN_FUNCTION_WORDS = frozenset(
        {
            # niemiecki
            "am", "auf", "bei", "vom", "von", "zum", "zur", "der", "die", "das",
            "ein", "eine", "einer", "einem", "und", "mit", "ohne", "uber",
            "im", "ins", "des", "den", "dem",
            # niderlandzki / flamandzki
            "een", "het", "naar", "aan",
            # francuski
            "le", "la", "les", "du", "des", "et", "au", "aux", "dans", "sur",
            "sous", "sans", "avec", "vers",
            # wloski
            "il", "lo", "gli", "del", "della", "di", "con", "tra", "fra",
            # hiszpanski
            "el", "los", "las", "y", "en", "con", "sin", "sobre",
            # polski
            "na", "po", "w", "we", "z", "ze", "do", "od",
        }
    )

    @classmethod
    def _looks_english(cls, text: str) -> bool:
        """Heurystyka: czy tytul wyglada na angielski.

        Reguly:
        1) Jesli ma znaki diakrytyczne (au, e, c, cyrylica, CJK) -> NIE EN.
        2) Jesli zawiera typowo nieangielskie slowo funkcyjne (von, der, am,
           bei, vom, zum, ohne, etc.) -> NIE EN.
        3) W przeciwnym razie zakladamy EN (ASCII + brak DE/NL/FR/IT/ES sygnalu).

        Apostrof typograficzny `'` traktujemy jak ASCII `'`.
        """
        if not text:
            return False
        cleaned = text.replace("\u2019", "'").replace("\u2018", "'")
        if not all(ord(c) < 128 for c in cleaned):
            return False
        import re as _re
        words = [w.lower() for w in _re.findall(r"\b[a-zA-Z]+\b", cleaned)]
        for w in words:
            if w in cls._NON_EN_FUNCTION_WORDS:
                return False
        return True

    @staticmethod
    def _is_artist_name(text: str, artist: str) -> bool:
        """Heurystyka: czy 'text' to po prostu nazwisko artysty (a nie tytul dziela)?

        Klasyczny przypadek: zrodlo (Wikipedia / Wikidata / Commons) trafilo
        w biografie artysty zamiast w opis konkretnego dziela i zwrocilo
        jego imie/nazwisko jako rzekomy 'english title'. Bez tej kontroli
        podmienialibysmy poprawny tytul obrazu na same imie autora.

        Zwraca True dla:
        - dokladnej zgodnosci (z tolerancja na diakrytyki/wielkosc),
        - odwroconej kolejnosci ("Achenbach, Andreas" vs "Andreas Achenbach"),
        - samego nazwiska / samego imienia artysty.
        """
        if not text or not artist:
            return False
        import re as _re
        import unicodedata as _ud

        def _norm(s: str) -> str:
            s = _ud.normalize("NFKD", s)
            s = "".join(c for c in s if not _ud.combining(c))
            s = _re.sub(r"[^\w\s]+", " ", s, flags=_re.UNICODE)
            s = _re.sub(r"\s+", " ", s).strip().lower()
            return s

        t = _norm(text)
        a = _norm(artist)
        if not t or not a:
            return False
        if t == a:
            return True
        a_parts = a.split()
        if t == " ".join(reversed(a_parts)):
            return True
        if len(a_parts) >= 2 and (t == a_parts[-1] or t == a_parts[0]):
            return True
        return False

    # Slowa typowo wystepujace w TYTULACH OBRAZOW (a nie w imionach osob).
    # Synchronizowane z `_PAINTING_TITLE_WORDS` w title_resolver.py - obecnosc
    # ktoregokolwiek dyskwalifikuje text jako "person name". Bez tej heurystyki
    # "Indian Summer", "Lake View", "Self Portrait" itp. byly false-positive
    # odrzucane jako rzekome nazwiska artystow.
    _PAINTING_TITLE_WORDS = frozenset(
        {
            "summer", "winter", "autumn", "spring", "fall",
            "morning", "evening", "night", "noon", "dawn", "dusk", "twilight",
            "lake", "river", "sea", "ocean", "bay", "shore", "beach", "coast",
            "bridge", "mountain", "mountains", "hill", "hills", "valley",
            "forest", "wood", "woods", "garden", "field", "fields", "meadow",
            "sun", "moon", "star", "stars", "sky", "cloud", "clouds",
            "rain", "snow", "storm", "wind", "waves",
            "rose", "roses", "flower", "flowers", "tree", "trees",
            "fruit", "wheat", "corn", "harvest",
            "lady", "ladies", "woman", "women", "girl", "girls",
            "man", "men", "boy", "boys", "child", "children",
            "lover", "lovers", "mother", "father", "sister", "brother",
            "saint", "madonna", "christ", "angel", "angels", "venus", "mars",
            "king", "queen", "prince", "princess",
            "horse", "horses", "dog", "dogs", "cat", "cats", "bird", "birds",
            "rabbit", "deer", "lion", "tiger", "bull", "cow", "sheep",
            "landscape", "portrait", "self-portrait", "scene", "view", "vista",
            "still", "life", "abstract", "composition", "study",
            "interior", "exterior",
            "battle", "war", "victory", "death", "birth", "wedding", "dance",
            "music", "feast", "hunt", "prayer",
            "indian", "japanese", "chinese", "egyptian", "greek", "roman",
            "italian", "french", "spanish", "german", "dutch", "polish",
            "ancient", "modern", "old", "young", "blue", "red", "white", "black",
            "golden", "silver", "great", "little", "small", "big",
        }
    )

    @classmethod
    def _looks_like_person_name(cls, text: str, *, hint_tokens: set[str] = frozenset()) -> bool:
        """Heurystyka: czy 'text' to imie i nazwisko OSOBY (a nie tytul dziela)?

        Wykrywa wzor "Imie Nazwisko" / "Imie Drugie Nazwisko" - 2-3 slowa
        kapitalizowane, brak slow funkcyjnych ('the', 'of', 'in'), brak
        liczb, brak slow tytulowych ('summer'/'lake'/'lady'/...). Klasyczny
        przypadek: Wikipedia/Wikidata/Lens trafilo w biograficzny artykul
        INNEGO artysty (np. "Ludolf Bakhuizen") i zwrocilo jego imie jako
        rzekomy "tytul obrazu".

        `hint_tokens` - tokeny z nazwy pliku. Jesli tytul nie ma zadnego
        wspolnego tokena z nazwa pliku, jest BARDZIEJ podejrzany. Tytul
        ktory CZEŚCIOWO matchuje filename (np. "Andreas Achenbach Am Strand")
        jest mniej podejrzany - prawdopodobnie to faktyczny tytul.
        """
        if not text:
            return False
        import re as _re
        s = _re.sub(r"\s+", " ", text).strip()
        if not s or any(c.isdigit() for c in s):
            return False
        words = s.split()
        if not (2 <= len(words) <= 3):
            return False
        for w in words:
            if len(w) < 2 or not w[0].isupper():
                return False
        title_function_words = {
            "the", "of", "in", "at", "on", "by", "with", "for", "to",
            "and", "or", "from", "into", "near", "over", "under",
            "der", "die", "das", "ein", "eine", "und", "von", "zu", "am", "im",
            "le", "la", "les", "du", "des", "et", "au", "aux",
            "il", "lo", "gli", "del", "della",
        }
        for w in words:
            wl = w.lower()
            if wl in title_function_words:
                return False
            # Slowo typowe dla tytulow obrazow ("summer", "lake", "lady"...) -
            # NIE person name. To rozwiazuje false positive dla "Indian Summer".
            if wl in cls._PAINTING_TITLE_WORDS:
                return False
        if hint_tokens:
            cand_lower_tokens = {w.lower() for w in words}
            if cand_lower_tokens & hint_tokens:
                return False
        return True

    def _resolve_titles_for_metadata(
        self,
        *,
        final_title: str,
        wd_english: str,
        wd_original: str,
        wd_original_lang: str,
        filename_hint: str,
    ) -> tuple[str, str, str]:
        """Zwraca (english_title, original_title, original_lang) do zapisu w metadanych.

        Reguly:
        - english_title: priorytet -> Wikidata EN, potem final (jesli wyglada na EN),
          potem hint (jesli wyglada na EN). Pusty gdy nic nie pasuje.
        - original_title: priorytet -> Wikidata original (jesli rozny od EN),
          potem final (jesli NIE wyglada na EN i rozny od EN),
          potem hint (jesli NIE wyglada na EN i rozny od EN).
        - original_lang: z Wikidata jesli mamy, w przeciwnym razie pusty.
        """
        english = ""
        if wd_english:
            english = wd_english
        elif self._looks_english(final_title):
            english = final_title
        elif self._looks_english(filename_hint):
            english = filename_hint.strip()

        def _diff(a: str, b: str) -> bool:
            return a.strip().lower() != (b or "").strip().lower()

        original = ""
        original_lang = ""
        if wd_original and _diff(wd_original, english):
            original = wd_original
            original_lang = wd_original_lang
        elif final_title and not self._looks_english(final_title) and _diff(final_title, english):
            original = final_title
            original_lang = wd_original_lang  # czesto pusty - nie zgadujemy jezyka
        elif filename_hint and not self._looks_english(filename_hint) and _diff(filename_hint, english):
            original = filename_hint.strip()
            original_lang = ""

        return english, original, original_lang

    # ---------- Cache per (source, artist, query) ----------
    def _cached_call(
        self,
        source: str,
        artist: str,
        query: str,
        fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Memoizacja wynikow - dla tej samej (zrodlo, autor, zapytanie) zwraca cache.

        Dwupoziomowy:
        1) RAM (`self._search_cache`) - reset na poczatku kazdej sesji wyszukiwania.
        2) Dysk (`self._disk_cache`) - przezywa restart aplikacji (TTL 30 dni).

        Zysk: 30 obrazow Sisleya = 1 zapytanie do Met/ArtIC zamiast 30 (RAM).
        Po restarcie: te same obrazy = 0 zapytan (disk).
        """
        a_norm = (artist or "").strip().lower()
        q_norm = (query or "").strip().lower()
        key = (source, a_norm, q_norm)
        # 1) RAM
        with self._cache_lock:
            if key in self._search_cache:
                return self._search_cache[key]
        # 2) Dysk
        if self._disk_cache is not None:
            try:
                cached = self._disk_cache.get(source, a_norm, q_norm)
            except Exception:  # noqa: BLE001
                cached = None
            if cached is not None:
                with self._cache_lock:
                    self._search_cache[key] = cached
                return cached
        # 3) Fetch
        result = fn(*args, **kwargs)
        # 4) Zapisz w obu warstwach
        with self._cache_lock:
            self._search_cache[key] = result
        if self._disk_cache is not None and result is not None:
            try:
                self._disk_cache.set(source, a_norm, q_norm, result)
            except Exception:  # noqa: BLE001
                pass
            self._schedule_disk_flush()
        return result

    def _schedule_disk_flush(self) -> None:
        """Debounce - flush max raz na 5 sekund, zeby nie przesilac dyskiem."""
        if self._disk_cache is None:
            return
        if self._disk_flush_after_id is not None:
            return
        try:
            self._disk_flush_after_id = self.root.after(5000, self._flush_disk_cache_now)
        except Exception:  # noqa: BLE001
            self._disk_flush_after_id = None

    def _flush_disk_cache_now(self) -> None:
        self._disk_flush_after_id = None
        if self._disk_cache is None:
            return
        try:
            self._disk_cache.flush()
        except Exception:  # noqa: BLE001
            pass

    def _on_close(self) -> None:
        """Handler zamkniecia okna - flush cache + zniszcz root."""
        try:
            self._flush_disk_cache_now()
        finally:
            try:
                self.root.destroy()
            except Exception:  # noqa: BLE001
                pass

    # ---------- Plynne paski postepu (animowane, procentowe) ----------
    def _reset_progress(self, total_items: int) -> None:
        """Wyzeruj paski przed nowa partia plikow."""
        with self._progress_lock:
            self._upload_units_done = 0.0
            self._upload_units_total = float(total_items)
            self._upload_total_count = total_items
            self._upload_pct_target = 0.0
            self._upload_pct_shown = 0.0
            self._upload_toast_shown = False
            self._search_units_done = 0.0
            self._search_units_total = float(total_items * _SEARCH_PHASES)
            self._search_total_count = total_items
            self._search_pct_target = 0.0
            self._search_pct_shown = 0.0
            self._search_toast_shown = False
        self.upload_progress.configure(value=0.0)
        self.upload_progress_var.set("0%")
        self.search_progress.configure(value=0.0)
        self.search_progress_var.set("0%")

    def _bump_upload(self, units: float = 1.0) -> None:
        """Zglos zakonczenie czesci pracy uploadu (1.0 = caly plik)."""
        finished_now = False
        total_count = 0
        with self._progress_lock:
            if self._upload_units_total <= 0:
                return
            self._upload_units_done = min(
                self._upload_units_done + units, self._upload_units_total
            )
            self._upload_pct_target = (
                self._upload_units_done / self._upload_units_total * 100.0
            )
            if (
                not self._upload_toast_shown
                and self._upload_units_done >= self._upload_units_total
            ):
                self._upload_toast_shown = True
                finished_now = True
                total_count = self._upload_total_count
        if finished_now:
            self.root.after(
                0,
                lambda t=total_count:
                    self._show_toast(f"Wgrywanie zakonczone ({t} plik(ow))."),
            )
            self.root.after(
                0, lambda t=total_count: self.status_var.set(f"Wgrywanie zakonczone ({t}).")
            )

    def _bump_search(self, units: float = 1.0) -> None:
        """Zglos zakonczenie 'units' faz wyszukiwania."""
        finished_now = False
        total_count = 0
        with self._progress_lock:
            if self._search_units_total <= 0:
                return
            self._search_units_done = min(
                self._search_units_done + units, self._search_units_total
            )
            self._search_pct_target = (
                self._search_units_done / self._search_units_total * 100.0
            )
            if (
                not self._search_toast_shown
                and self._search_units_done >= self._search_units_total
            ):
                self._search_toast_shown = True
                finished_now = True
                total_count = self._search_total_count
        if finished_now:
            self.root.after(
                0,
                lambda t=total_count: self._show_toast(
                    f"Wyszukiwanie zakonczone ({t} plik(ow)).", color="#06a"
                ),
            )
            self.root.after(
                0, lambda t=total_count: self.status_var.set(f"Wyszukiwanie zakonczone ({t}).")
            )

    def _tick_progress(self) -> None:
        """Animator - co kilkadziesiat ms zbliza wartosci pokazywane do docelowych."""
        try:
            for target_attr, shown_attr, bar, label_var in (
                ("_upload_pct_target", "_upload_pct_shown", self.upload_progress, self.upload_progress_var),
                ("_search_pct_target", "_search_pct_shown", self.search_progress, self.search_progress_var),
            ):
                target = float(getattr(self, target_attr))
                shown = float(getattr(self, shown_attr))
                if abs(target - shown) > 0.05:
                    # Krok = 18% pozostalej odleglosci + 0.4pp - delikatne wytlumienie.
                    step = (target - shown) * 0.18
                    if step > 0:
                        new = shown + step + 0.4
                        new = min(new, target)
                    else:
                        new = shown + step - 0.4
                        new = max(new, target)
                    setattr(self, shown_attr, new)
                    bar.configure(value=new)
                    label_var.set(f"{int(round(new))}%")
                elif shown != target:
                    setattr(self, shown_attr, target)
                    bar.configure(value=target)
                    label_var.set(f"{int(round(target))}%")
        finally:
            self.root.after(_PROGRESS_TICK_MS, self._tick_progress)

    # ---------------------- Drag & drop / browse ----------------------
    def _browse_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz obrazy",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tif *.tiff"),
                ("Wszystkie", "*.*"),
            ],
        )
        if paths:
            self._add_paths(list(paths))

    def _on_drop(self, event: Any) -> None:
        raw = event.data
        paths: list[str] = []
        # tkdnd zwraca string; pliki ze spacjami sa w klamrach
        cur = ""
        in_brace = False
        for ch in raw:
            if ch == "{":
                in_brace = True
                cur = ""
            elif ch == "}":
                in_brace = False
                if cur:
                    paths.append(cur)
                cur = ""
            elif ch == " " and not in_brace:
                if cur:
                    paths.append(cur)
                cur = ""
            else:
                cur += ch
        if cur:
            paths.append(cur)
        self._add_paths(paths)

    def _add_paths(self, paths: list[str]) -> None:
        added = 0
        existing = {str(it["path"]) for it in self.queue_items}
        for raw in paths:
            p = Path(raw).expanduser()
            if not p.exists():
                continue
            if p.is_dir():
                for child in p.rglob("*"):
                    if child.suffix.lower() in _IMG_EXTS and str(child) not in existing:
                        self._append_item(child)
                        existing.add(str(child))
                        added += 1
                continue
            if p.suffix.lower() not in _IMG_EXTS:
                continue
            if str(p) in existing:
                continue
            self._append_item(p)
            existing.add(str(p))
            added += 1
        if added:
            self._refresh_tree()
            self._refresh_counts_and_status()
            self._append_log(f"[add] dodano {added} plik(ow).")

    def _append_item(self, path: Path) -> None:
        artist_path = find_artist_in_path(path)
        hints = parse_filename_hints(path, artist_hint=artist_path)
        # Nazwa pliku ma priorytet nad nazwa folderu - folder czesto jest
        # kategoria typu "Reprodukcje Mistrzów" / "Old Masters" / "Sea Paintings"
        # i lapie sie na ogolny pattern "Word Word", a nie jest nazwiskiem.
        # Nazwa pliku natomiast jest specyficzna dla danego obrazu (np.
        # "Achenbach, Andreas - Strand bei Scheveningen.jpg").
        artist = hints.artist or artist_path
        if artist_path and hints.artist and artist_path.lower() != hints.artist.lower():
            status = (
                f"rozne autorzy: plik wygrywa ({hints.artist}), "
                f"folder pomijam ({artist_path})"
            )
        elif artist:
            status = "do wyszukania"
        else:
            status = "brak autora (w sciezce i nazwie pliku)"
        self.queue_items.append(
            {
                "path": path,
                "original_name": path.name,
                "artist": artist,
                "title": "",
                "title_hint": hints.title,
                "status": status,
                "error": "",
                "renamed_to": "",
                # wypelniane podczas wyszukiwania - wykorzystywane przez "Pokaz zrodla"
                "visual_results": {},      # dict{engine: {titles, error, used_image_url, source_url}}
                "source_breakdown": {},    # dict{source_key: list[str]}
                "query_seed_used": "",
            }
        )

    def _remove_selected(self) -> None:
        selected = set(self.tree.selection())
        if not selected:
            return
        keep = []
        for iid, item in zip(self._iids(), self.queue_items):
            if iid not in selected:
                keep.append(item)
        self.queue_items = keep
        self._refresh_tree()
        self._refresh_counts_and_status()

    def _clear_queue(self) -> None:
        if not self.queue_items:
            return
        if not messagebox.askyesno(APP_TITLE, "Wyczyscic kolejke plikow?"):
            return
        self.queue_items.clear()
        self._refresh_tree()
        self._refresh_counts_and_status()

    # ---------------------- Helpers ----------------------
    def _suffix(self) -> str:
        """Aktualny sufiks z pola UI (pusty string gdy brak / sam whitespace)."""
        try:
            return (self.suffix_var.get() or "").strip()
        except (AttributeError, tk.TclError):
            return ""

    def _build_new_name(self, item: dict[str, Any]) -> str:
        """Docelowa nazwa bez sufiksu: 'Autor - Tytul.ext'."""
        return build_new_name(
            item.get("artist", ""),
            item.get("title", ""),
            item["path"],
        )

    def _preview_new_name_column(self, item: dict[str, Any]) -> str:
        """Podglad kolumny 'Nowa nazwa': przed wyszukiwaniem = biezaca nazwa + sufiks;
        po wyszukaniu (jest tytul) = docelowa nazwa kanoniczna +/- sufiks z pola."""
        suf = self._suffix()
        if item.get("title"):
            if suf:
                return build_new_name(
                    item.get("artist", ""),
                    item.get("title", ""),
                    item["path"],
                    suffix=suf,
                )
            return self._build_new_name(item)
        if suf:
            return append_suffix_to_original_filename(item["path"].name, suf)
        return ""

    def _items_from_tree_selection(self) -> list[dict[str, Any]]:
        """Zaznaczone wiersze w kolejce (pusta lista gdy brak zaznaczenia)."""
        sel = self.tree.selection()
        if not sel:
            return []
        iids = self._iids()
        out: list[dict[str, Any]] = []
        for iid in sel:
            try:
                idx = iids.index(iid)
            except ValueError:
                continue
            out.append(self.queue_items[idx])
        return out

    # ---------------------- Tree helpers ----------------------
    def _row_values(self, item: dict[str, Any]) -> tuple[str, str, str, str, str]:
        artist = item.get("artist") or "(brak)"
        title = item.get("title") or "(?)"
        status = item.get("status") or ""
        if item.get("error"):
            status = f"BLAD: {item['error']}"[:120]
        new_name = self._preview_new_name_column(item)
        return (item["path"].name, artist, title, new_name, status)

    def _iids(self) -> list[str]:
        return list(self.tree.get_children())

    def _refresh_tree(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for item in self.queue_items:
            self.tree.insert("", "end", values=self._row_values(item))
        self._autosize_queue_columns()

    def _queue_tree_font(self) -> tkfont.Font:
        f = getattr(self, "_queue_tv_font", None)
        if f is None:
            spec = ttk.Style(self.root).lookup("Treeview", "font")
            try:
                if spec:
                    self._queue_tv_font = tkfont.Font(self.root, font=spec)
                else:
                    self._queue_tv_font = tkfont.nametofont("TkDefaultFont")
            except tk.TclError:
                self._queue_tv_font = tkfont.nametofont("TkDefaultFont")
            f = self._queue_tv_font
        return f

    def _queue_col_text_width(self, text: str) -> int:
        t = (text or " ").replace("\n", " ")
        return self._queue_tree_font().measure(t)

    def _autosize_queue_columns(self) -> None:
        if not self.queue_items:
            self._equalize_queue_columns()
            return
        for i, col in enumerate(self._queue_col_ids):
            header = self._queue_heading_text[col]
            parts: list[str] = [header]
            for item in self.queue_items:
                parts.append(self._row_values(item)[i])
            wpx = max(self._queue_col_text_width(p) for p in parts) + _QUEUE_COL_PAD
            wpx = max(_MIN_QUEUE_COL_WIDTH, min(wpx, _MAX_QUEUE_COL_WIDTH))
            self.tree.column(
                col,
                width=wpx,
                minwidth=_MIN_QUEUE_COL_WIDTH,
                stretch=(col == _QUEUE_STRETCH_COL),
            )
        self.root.after_idle(self._fit_window_to_content)

    def _on_tree_configure(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self.queue_items:
            self._equalize_queue_columns()

    def _equalize_queue_columns(self) -> None:
        self.root.update_idletasks()
        try:
            tree_w = self.tree.winfo_width()
        except tk.TclError:
            tree_w = 0
        n = len(self._queue_col_ids)
        if tree_w < 40 * n:
            try:
                tree_w = max(self._list_frame.winfo_width() - 180, 40 * n)
            except tk.TclError:
                tree_w = 40 * n
        share = max(_MIN_QUEUE_COL_WIDTH, tree_w // n)
        for col in self._queue_col_ids:
            self.tree.column(col, width=share, minwidth=_MIN_QUEUE_COL_WIDTH, stretch=True)

    def _needed_window_width(self) -> int:
        try:
            sum_cols = sum(int(self.tree.column(c, "width")) for c in self._queue_col_ids)
        except (tk.TclError, ValueError, AttributeError):
            sum_cols = _MIN_QUEUE_COL_WIDTH * len(self._queue_col_ids)
        scroll_w = 18
        try:
            if self._tree_scroll.winfo_exists() and self._tree_scroll.winfo_width() > 1:
                scroll_w = self._tree_scroll.winfo_width()
        except tk.TclError:
            pass
        try:
            btns_w = self._queue_btns_frame.winfo_reqwidth()
        except tk.TclError:
            btns_w = 160
        if btns_w <= 1:
            btns_w = 160
        inner = 6 + sum_cols + scroll_w + 4 + btns_w + 6
        return inner + 48

    def _fit_window_to_content(self) -> None:
        if not getattr(self, "_list_frame", None):
            return
        self.root.update_idletasks()
        need_w = self._needed_window_width()
        try:
            req_w = self.root.winfo_reqwidth()
        except tk.TclError:
            req_w = need_w
        need_w = max(need_w, req_w)
        screen_w = self.root.winfo_screenwidth()
        need_w = min(need_w, screen_w - 40)
        try:
            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
        except tk.TclError:
            return
        if cur_w < need_w:
            self.root.geometry(f"{need_w}x{cur_h}")

    def _refresh_counts_and_status(self) -> None:
        n_total = len(self.queue_items)
        n_ready = sum(1 for it in self.queue_items if it.get("title") and it.get("artist"))
        self.counts_var.set(f"{n_total} plik(ow), gotowych do zmiany: {n_ready}")
        if not self.queue_items:
            self.status_var.set("Gotowy. Dodaj pliki do kolejki.")
        else:
            self.status_var.set(f"W kolejce: {n_total} plik(ow), {n_ready} z propozycja nowej nazwy.")
        state = "normal" if n_ready and not self._busy else "disabled"
        self.rename_btn.configure(state=state)
        suffix_state = "normal" if n_total and not self._busy else "disabled"
        self.suffix_rename_btn.configure(state=suffix_state)
        self.suffix_all_btn.configure(state=suffix_state)

    # ---------------------- Edit dialogs ----------------------
    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return self._iids().index(sel[0])
        except ValueError:
            return None

    def _apply_artist_to_item(self, item: dict[str, Any], artist: str) -> None:
        item["artist"] = artist
        if artist:
            item["error"] = ""
            if item.get("title"):
                item["status"] = "gotowe"

    def _edit_artist_dialog(self) -> None:
        items = self._items_from_tree_selection()
        if not items:
            messagebox.showinfo(APP_TITLE, "Najpierw zaznacz wiersz.")
            return
        from tkinter import simpledialog

        if len(items) == 1:
            prompt = f"Autor dla pliku:\n{items[0]['path'].name}"
        else:
            preview = "\n".join(f"  • {it['path'].name}" for it in items[:8])
            if len(items) > 8:
                preview += f"\n  ... i {len(items) - 8} kolejnych"
            prompt = f"Autor dla {len(items)} plikow:\n{preview}"

        unique_artists = {(it.get("artist") or "").strip() for it in items}
        initial = next(iter(unique_artists)) if len(unique_artists) == 1 else ""

        new_val = simpledialog.askstring(APP_TITLE, prompt, initialvalue=initial)
        if new_val is None:
            return
        artist = normalize_artist(new_val)
        for item in items:
            self._apply_artist_to_item(item, artist)
        self._refresh_tree()
        self._refresh_counts_and_status()

    def _edit_title_dialog(self) -> None:
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo(APP_TITLE, "Najpierw zaznacz wiersz.")
            return
        item = self.queue_items[idx]
        from tkinter import simpledialog
        new_val = simpledialog.askstring(
            APP_TITLE, f"Tytul dla pliku:\n{item['path'].name}",
            initialvalue=item.get("title", ""),
        )
        if new_val is None:
            return
        item["title"] = format_artwork_title((new_val or "").strip())
        item["error"] = ""
        if item["title"] and item.get("artist"):
            item["status"] = "gotowe"
        self._refresh_tree()
        self._refresh_counts_and_status()

    def _on_tree_double_click(self, _event: Any) -> None:
        self._edit_title_dialog()

    # ---------------------- Sortowanie kolumn ----------------------
    def _sort_by_column(self, col: str) -> None:
        """Sortuj kolejke wg klikni\u0119tej kolumny - Status sortuje po pewnosci."""
        if not self.queue_items:
            return
        cur = self._sort_state.get(col, "")
        # Toggle: brak -> asc -> desc -> asc...
        new_dir = "desc" if cur == "asc" else "asc"
        self._sort_state.clear()
        self._sort_state[col] = new_dir
        reverse = (new_dir == "desc")

        def key_for(item: dict[str, Any]) -> Any:
            if col == "status":
                # Klik "Status" sortuje po pewnosci - od najnizszej (latwiej
                # zauwazyc co wymaga weryfikacji).
                return float(item.get("confidence", 0.0))
            if col == "file":
                return item["path"].name.lower()
            if col == "artist":
                return (item.get("artist") or "").lower()
            if col == "title":
                return (item.get("title") or "").lower()
            if col == "new_name":
                return self._preview_new_name_column(item).lower()
            return ""

        self.queue_items.sort(key=key_for, reverse=reverse)
        # Wskaznik sortowania w naglowku.
        arrow = " v" if reverse else " ^"
        for c in self._queue_col_ids:
            base = self._queue_heading_text[c]
            self.tree.heading(c, text=(base + arrow if c == col else base))
        self._refresh_tree()
        self._refresh_counts_and_status()

    # ---------------------- Menu kontekstowe (RMB) ----------------------
    def _build_context_menu(self) -> None:
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Kopiuj tytul", command=self._ctx_copy_title)
        m.add_command(label="Kopiuj nowa nazwe", command=self._ctx_copy_new_name)
        m.add_command(label="Kopiuj oryginaln\u0105 nazw\u0119", command=self._ctx_copy_original_name)
        m.add_separator()
        m.add_command(label="Poka\u017c \u017ar\u00f3d\u0142a...", command=self._ctx_show_sources)
        m.add_command(label="Poka\u017c podgl\u0105d obrazu...", command=self._open_preview_window)
        m.add_separator()
        m.add_command(label="Edytuj tytul...", command=self._edit_title_dialog)
        m.add_command(label="Edytuj autora...", command=self._edit_artist_dialog)
        m.add_separator()
        m.add_command(label="Otworz folder pliku", command=self._ctx_open_folder)
        m.add_separator()
        m.add_command(label="Pomin (wyczysc tytul)", command=self._ctx_skip)
        m.add_command(label="Usun z kolejki", command=self._remove_selected)
        self._ctx_menu = m

    def _on_tree_context(self, event: Any) -> None:
        # Zaznacz wiersz pod kursorem przed pokazaniem menu.
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _ctx_copy_title(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        title = self.queue_items[idx].get("title") or ""
        if not title:
            self._show_toast("Brak tytulu do skopiowania.", color="#a60")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(title)
        self._show_toast(f"Skopiowano tytul: {title[:48]}")

    def _ctx_copy_new_name(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        it = self.queue_items[idx]
        nn = self._preview_new_name_column(it)
        if not nn:
            self._show_toast(
                "Brak podgladu nowej nazwy (przed wyszukiwaniem wpisz sufiks w polu "
                "albo poczekaj na tytul).",
                color="#a60",
            )
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(nn)
        self._show_toast(f"Skopiowano nazwe: {nn[:48]}")

    def _ctx_copy_original_name(self) -> None:
        idx = self._selected_index()
        if idx is None:
            self._show_toast("Najpierw zaznacz wiersz.", color="#a60")
            return
        it = self.queue_items[idx]
        # Oryginal = pierwotna nazwa pliku przed renamem (jesli zostal przemianowany,
        # mamy pierwotny stem w `original_name`; inaczej biezaca nazwa w `path`).
        orig = it.get("original_name") or it["path"].name
        self.root.clipboard_clear()
        self.root.clipboard_append(orig)
        self._show_toast(f"Skopiowano oryginaln\u0105 nazw\u0119: {orig[:48]}")

    # ---------------------- Podglad obrazu ----------------------
    def _on_tree_select(self, _event: Any) -> None:
        """Zaznaczenie wiersza -> aktualizuj panel podgladu (asynchronicznie).

        Generowanie miniatury przez Pillow dla 50 MB JPG zajmuje 100-300 ms,
        wiec robimy to w watku i wynik wracamy do UI przez `after`.
        """
        idx = self._selected_index()
        if idx is None:
            return
        try:
            path = self.queue_items[idx]["path"]
        except (KeyError, IndexError):
            return
        if self._preview_current_path == path:
            return
        self._preview_current_path = path
        if not _HAS_PIL_FOR_PREVIEW:
            self.preview_panel.configure(
                image="", text=path.name + "\n(zainstaluj Pillow zeby zobaczyc podglad)"
            )
            return
        # Cache hit?
        cache_key = str(path)
        cached = self._preview_cache.get(cache_key)
        if cached is not None:
            self._set_preview_photo(cached, path)
            return
        # Generuj w tle.
        threading.Thread(
            target=self._build_preview_in_bg,
            args=(path, self._preview_size),
            name="preview-builder",
            daemon=True,
        ).start()

    def _build_preview_in_bg(self, path: Path, size: tuple[int, int]) -> None:
        """Watek tla: wczytaj obraz i przeskaluj do thumb. Wynik przenosimy do UI."""
        try:
            with _PILImage.open(path) as im:
                im = im.copy()
                im.thumbnail(size, _PILImage.LANCZOS)
                # Konwertuj do RGB jesli potrzebne (PNG z alpha + tk = czesto trefne).
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                self.root.after(0, lambda i=im, p=path: self._finalize_preview(i, p))
        except Exception as e:  # noqa: BLE001
            self.root.after(
                0,
                lambda p=path, err=str(e): self._on_preview_error(p, err),
            )

    def _finalize_preview(self, pil_image: Any, path: Path) -> None:
        try:
            photo = _PILImageTk.PhotoImage(pil_image)
        except Exception as e:  # noqa: BLE001
            self._on_preview_error(path, str(e))
            return
        self._preview_cache[str(path)] = photo
        if self._preview_current_path == path:
            self._set_preview_photo(photo, path)

    def _set_preview_photo(self, photo: Any, path: Path) -> None:
        self._preview_photo = photo  # zapobiega GC
        try:
            # WAZNE: width/height w tk.Label przy starcie sa w JEDNOSTKACH TEKSTU
            # (znaki/linie) i Tk respektuje je nawet po wstawieniu PhotoImage,
            # CLIPUJAC obrazek. width=0/height=0 = auto-fit do rozmiaru obrazka.
            self.preview_panel.configure(image=photo, text="", width=0, height=0)
        except tk.TclError:
            pass

    def _on_preview_error(self, path: Path, err: str) -> None:
        if self._preview_current_path != path:
            return
        self.preview_panel.configure(
            image="",
            text=f"{path.name}\n(blad podgladu: {err[:60]})",
        )

    def _open_preview_window(self) -> None:
        """Otworz wieksze okno podgladu (~ 800x600) dla biezacego wiersza."""
        idx = self._selected_index()
        if idx is None:
            self._show_toast("Najpierw zaznacz wiersz.", color="#a60")
            return
        path = self.queue_items[idx]["path"]
        if not _HAS_PIL_FOR_PREVIEW:
            messagebox.showinfo(
                APP_TITLE,
                "Brak Pillow - duzy podglad nie zadziala.\n"
                "Zainstaluj: pip install Pillow",
            )
            return
        win = tk.Toplevel(self.root)
        win.title(f"Podglad: {path.name}")
        try:
            position_toplevel_screen_center(win, 820, 640)
        except tk.TclError:
            pass
        lbl = tk.Label(win, text="Wczytuje...", bg="#222", fg="#bbb")
        lbl.pack(fill="both", expand=True)
        info = tk.Label(
            win, text=str(path), font=("Consolas", 9),
            fg="#666", anchor="w", justify="left", padx=8, pady=4,
        )
        info.pack(fill="x")

        def _build() -> None:
            try:
                with _PILImage.open(path) as im:
                    im = im.copy()
                    im.thumbnail((800, 600), _PILImage.LANCZOS)
                    if im.mode not in ("RGB", "L"):
                        im = im.convert("RGB")
                photo = _PILImageTk.PhotoImage(im)
                lbl.image = photo  # type: ignore[attr-defined]  - ref dla GC
                lbl.configure(image=photo, text="", bg="#111")
            except Exception as e:  # noqa: BLE001
                lbl.configure(text=f"Blad: {e}", bg="#400", fg="#fcc")
        win.after(50, _build)

    # ---------------------- Okno "Pokaz zrodla" ----------------------
    def _ctx_show_sources(self) -> None:
        idx = self._selected_index()
        if idx is None:
            self._show_toast("Najpierw zaznacz wiersz.", color="#a60")
            return
        it = self.queue_items[idx]
        self._open_sources_window(it)

    def _open_sources_window(self, item: dict[str, Any]) -> None:
        """Okno z kandydatami z kazdego zrodla, ktore wzielo udzial w wyniku."""
        win = tk.Toplevel(self.root)
        win.title(f"Zrodla: {item['path'].name}")
        try:
            position_toplevel_screen_center(win, 760, 560)
        except tk.TclError:
            pass

        # Naglowek - aktualny wybor
        head = ttk.Frame(win, padding=10)
        head.pack(fill="x")
        title_now = item.get("title") or "(brak)"
        artist_now = item.get("artist") or "(brak)"
        conf = float(item.get("confidence", 0.0))
        srcs = int(item.get("sources_used", 0))
        ttk.Label(
            head,
            text=f"Wynik: {title_now}",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            head,
            text=(
                f"Autor: {artist_now}    "
                f"Pewnosc: {int(round(conf * 100))}%    "
                f"Zrodel zgodnych: {srcs}    "
                f"Wybrane przez: {item.get('source_name') or '?'}"
            ),
            foreground="#666",
        ).pack(anchor="w", pady=(2, 0))
        if item.get("source_url"):
            url = item["source_url"]
            link = ttk.Label(
                head, text=f"Link: {url}",
                foreground="#06a", cursor="hand2",
            )
            link.pack(anchor="w", pady=(2, 0))

            def _open(_e: Any, u: str = url) -> None:
                import webbrowser
                webbrowser.open(u)
            link.bind("<Button-1>", _open)

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=10)

        body = ttk.Frame(win, padding=10)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        from tkinter import scrolledtext
        txt = scrolledtext.ScrolledText(
            body, wrap="word", font=("Consolas", 9),
        )
        txt.grid(row=0, column=0, sticky="nsew")

        def _section(title: str, items: list[str], note: str = "") -> None:
            txt.insert("end", f"=== {title} ===\n", "head")
            if note:
                txt.insert("end", f"   ({note})\n", "note")
            if not items:
                txt.insert("end", "   (brak)\n\n", "empty")
                return
            for i, t in enumerate(items, 1):
                txt.insert("end", f"   {i:2d}. {t}\n")
            txt.insert("end", "\n")

        txt.tag_configure("head", font=("Segoe UI", 10, "bold"), foreground="#06a")
        txt.tag_configure("note", foreground="#888")
        txt.tag_configure("empty", foreground="#aaa")

        # Sekcja: Visual search engines
        visuals = item.get("visual_results") or {}
        for engine_label, engine_key in (
            ("Google Lens", "google_lens"),
            ("Yandex Images (reverse)", "yandex_images"),
            ("Bing Visual Search (reverse)", "bing_reverse_image"),
        ):
            data = visuals.get(engine_key)
            note = ""
            cands: list[str] = []
            if isinstance(data, dict):
                cands = list(data.get("titles") or [])
                if data.get("error"):
                    note = f"blad: {data['error']}"
                elif data.get("used_image_url"):
                    note = f"URL: {data['used_image_url']}"
            _section(engine_label, cands, note=note)

        # Sekcja: text-based sources
        text_srcs = item.get("source_breakdown") or {}
        for src_label, src_key in (
            ("Wikipedia", "wiki"),
            ("Wikidata", "wikidata"),
            ("Met Museum", "met"),
            ("Art Institute of Chicago", "artic"),
            ("Wikimedia Commons", "commons"),
            ("WikiArt (z Google site:wikiart.org)", "wikiart"),
            ("Art-sites (invaluable/mutualart/...)", "art_sites"),
            ("Google text", "google"),
        ):
            cands = list(text_srcs.get(src_key) or [])
            _section(src_label, cands)

        # Sekcja: filename hint
        fh = (item.get("title_hint") or "").strip()
        _section(
            "Hint z nazwy pliku",
            [fh] if fh else [],
            note=f"oryginal: {item.get('original_name') or item['path'].name}",
        )

        # Sekcja: query_seed
        qs = item.get("query_seed_used") or ""
        _section(
            "query_seed (uzyty do tekstowych zapytan)",
            [qs] if qs else [],
            note="To slowo/fraza, ktora poszla do Wiki/Wikidata/Met/ArtIC/Commons.",
        )

        txt.configure(state="disabled")

        # Stopka
        foot = ttk.Frame(win, padding=8)
        foot.pack(fill="x")
        ttk.Button(foot, text="Zamknij", command=win.destroy).pack(side="right")

    def _ctx_open_folder(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        p = self.queue_items[idx]["path"]
        try:
            import os
            import subprocess
            import sys
            folder = str(p.parent)
            if sys.platform.startswith("win"):
                # Eksplorator Windows: zaznacz konkretny plik.
                subprocess.run(["explorer", "/select,", str(p)], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
            _ = os  # noqa: F841 - import dla pokrycia roznych OS
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Nie mozna otworzyc folderu:\n{e}")

    def _ctx_skip(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        it = self.queue_items[idx]
        it["title"] = ""
        it["confidence"] = 0.0
        it["sources_used"] = 0
        it["status"] = "pominieto"
        self._refresh_tree()
        self._refresh_counts_and_status()

    # ---------------------- Search (background) ----------------------
    def _on_search_clicked(self) -> None:
        if self._busy:
            return
        if not env_get("SERPAPI_KEY"):
            messagebox.showerror(
                APP_TITLE,
                "Brak SERPAPI_KEY w cursor-api/.env.\n\n"
                "Dodaj linijke np.:\nSERPAPI_KEY=twoj_klucz_serpapi",
            )
            return
        # Reset flagi limitu - user kliknal nowe wyszukiwanie z (mozliwe) nowym kluczem.
        self._serpapi_limit_event.clear()
        self._serpapi_limit_reason = ""
        todo = [it for it in self.queue_items if not it.get("title")]
        if not todo:
            messagebox.showinfo(APP_TITLE, "Wszystkie pozycje maja juz proponowany tytul.")
            return
        self._busy = True
        self.search_btn.configure(state="disabled")
        self.rename_btn.configure(state="disabled")
        self.suffix_rename_btn.configure(state="disabled")
        self.suffix_all_btn.configure(state="disabled")
        total = len(todo)
        self.status_var.set(f"Wgrywanie i wyszukiwanie: 0/{total}...")
        self._reset_progress(total)
        # Reset cache na poczatku KAZDEGO wyszukiwania - dane online moga
        # sie zmieniac, a powtorne uruchomienie ma byc swieze.
        with self._cache_lock:
            self._search_cache.clear()
        for it in todo:
            it["status"] = "w kolejce..."
            it["error"] = ""
        self._refresh_tree()
        threading.Thread(target=self._search_worker, args=(todo,), daemon=True).start()

    def _process_one(self, item: dict[str, Any]) -> None:
        """Pelen pipeline dla jednej pozycji.

        Krok 1 (upload): obraz na 0x0.st / catbox.moe -> bumpuje pasek "Wgrywanie".
        Krok 2 (search): Lens + Wikipedia + Wikidata + Met + Art Institute
        + Wikimedia Commons + (warunkowo) Google text + agregat art-sites
        -> kazda zakonczona faza pcha pasek "Wyszukiwanie" o 1/N.
        Liczba faz = _SEARCH_PHASES (zachowujemy ja stala, zeby pasek
        konczyl sie zawsze na 100%, niezaleznie od pominietych zrodel).
        """
        artist = item.get("artist", "") or ""
        filename_hint = item.get("title_hint", "") or ""
        phases_done = 0

        def phase(units: float = 1.0) -> None:
            nonlocal phases_done
            phases_done += units
            self._bump_search(units)

        # ====== UPLOAD ======
        self._mark_status(item, "upload obrazu...")
        image_urls: dict[str, str] = {}     # {host: url}
        sent_bytes = 0
        import time as _t
        _upload_t0 = _t.monotonic()
        try:
            image_urls, sent_bytes, upl_errors = upload_image_all_urls(item["path"])
            size_mb = sent_bytes / (1024 * 1024)
            elapsed = _t.monotonic() - _upload_t0
            if image_urls:
                hosts_str = ", ".join(f"{h}={u}" for h, u in image_urls.items())
                self._append_log(
                    f"[upload] {item['path'].name} -> {hosts_str} "
                    f"({size_mb:.2f} MB, {elapsed:.2f}s)"
                )
            else:
                err_str = " | ".join(upl_errors) if upl_errors else "?"
                self._append_log(
                    f"[upload] {item['path'].name}: oba hostingi padly: {err_str} "
                    f"(po {elapsed:.2f}s) - bez visual search, lecimy z innych zrodel"
                )
        except UploadError as e:
            elapsed = _t.monotonic() - _upload_t0
            self._append_log(
                f"[upload] {item['path'].name}: {e} (po {elapsed:.2f}s) "
                "- bez visual search, lecimy z innych zrodel"
            )
        finally:
            self._bump_upload()

        # ====== SEARCH ======
        try:
            # 1) Visual search (Google Lens + Yandex Images + Bing Reverse) -- faza 1/8
            #    Wszystkie silniki rownolegle, kazdy preferuje 0x0.st > catbox
            #    (Google traktuje catbox jako podejrzany - dla Lens zwlaszcza
            #    znacznie czesciej zwraca "no results" dla URL-i z catbox).
            #    Aggregat wynikow IDZIE jako query_seed do tekstowych zrodel,
            #    co rozwiazuje problem "filename = generyczne slowo" (np. "Obraz").
            lens_candidates: list[str] = []
            yandex_candidates: list[str] = []
            bing_candidates: list[str] = []
            visual_aggregate: list[str] = []
            visual_source_url = ""
            if (image_urls and env_get("SERPAPI_KEY")
                    and not self._serpapi_limit_event.is_set()):
                self._mark_status(item, "Visual search (Lens+Yandex+Bing)...")
                try:
                    mvr = search_all_engines(image_urls, engines=DEFAULT_ENGINES)
                except SerpApiLimitError as e:
                    self._handle_serpapi_limit(e.reason)
                    self._append_log(
                        f"[serpapi-limit] {item['path'].name}: {e.reason} "
                        "(pomijam visual i text-source SerpAPI dla tego pliku)"
                    )
                    mvr = None
                except Exception as e:  # noqa: BLE001
                    self._append_log(
                        f"[visual] {item['path'].name}: nieoczekiwany blad: {e}"
                    )
                    mvr = None
                if mvr is not None:
                    # Zapisz pelny breakdown do "Pokaz zrodla".
                    item["visual_results"] = {
                        eng: {
                            "titles": list(r.titles),
                            "error": r.error,
                            "used_image_url": r.used_image_url,
                            "source_url": r.source_url,
                            "elapsed": round(r.elapsed, 2),
                        }
                        for eng, r in mvr.per_engine.items()
                    }
                    visual_source_url = mvr.best_source_url()
                    # PER-ENGINE candidates - kazdy silnik liczy sie jako OSOBNE
                    # zrodlo w title_resolver (lens=8, yandex=8, bing=6), a nie
                    # jeden zlepiony "lens" z waga 4.
                    lens_candidates = list(
                        (mvr.per_engine.get("google_lens").titles
                         if mvr.per_engine.get("google_lens") else [])
                    )
                    yandex_candidates = list(
                        (mvr.per_engine.get("yandex_images").titles
                         if mvr.per_engine.get("yandex_images") else [])
                    )
                    bing_candidates = list(
                        (mvr.per_engine.get("bing_reverse_image").titles
                         if mvr.per_engine.get("bing_reverse_image") else [])
                    )
                    # query_seed dla tekstowych zrodel - aggregat ze wszystkich
                    # visual silnikow (kolejnosc po DEFAULT_ENGINES, dedup case-ins.).
                    visual_aggregate = list(mvr.all_titles)
                    # Log per silnik - widac od razu ktory zadzialal.
                    for eng, r in mvr.per_engine.items():
                        if r.titles:
                            self._append_log(
                                f"[{eng}] {item['path'].name} -> {r.titles[:3]}"
                                f" (host: {r.used_image_url.split('/')[2] if r.used_image_url else '?'})"
                            )
                        elif r.error:
                            self._append_log(
                                f"[{eng}] {item['path'].name}: {r.error[:120]}"
                            )
            phase()

            # 2-6) Pieciu zrodel online ROWNOLEGLE -- fazy 2-6/8
            # Wszystkie uzywaja tego samego "query_seed" (Lens albo nazwa pliku),
            # bo Met/ArtIC/Commons fuzzy-matchuja wystarczajaco dobrze. Dzieki
            # temu zamiast 5 sekwencyjnych HTTP roundtripow mamy max(5) - typowo
            # 3-5x szybciej na pojedynczym pliku.
            self._mark_status(item, "Wiki/Wikidata/Met/ArtIC/Commons rownolegle...")
            # Priorytet query_seed:
            # 1) NAJLEPSZY tytul z aggregatu visual search (Lens/Yandex/Bing),
            #    PO cleanup (pierwszy ktory cos sensownego zwraca po _clean_for_pick).
            #    Bez tego pierwszy element typu "Amazon.com: Ivan - Tempest" po
            #    cleanup zwracal "Amazon.com: Ivan" i zatruwal text-search.
            # 2) filename_hint - tylko gdy visual zawiodl. Dla generycznych nazw
            #    typu "Obraz.jpg" filename_hint daje smieci, ale to lepsze niz
            #    pusty seed (wtedy text-search byl by w ogole nie odpalany).
            raw_seed = ""
            query_seed = ""
            for cand in visual_aggregate:
                cleaned = clean_query_seed(cand)
                if cleaned and len(cleaned) >= 3:
                    raw_seed = cand
                    query_seed = cleaned
                    break
            if not query_seed and filename_hint:
                raw_seed = filename_hint
                query_seed = clean_query_seed(filename_hint) or filename_hint
            item["query_seed_used"] = query_seed
            if query_seed and query_seed != raw_seed:
                self._append_log(
                    f"[seed] {item['path'].name}: {raw_seed!r} -> {query_seed!r} "
                    "(wyczyszczony do query)"
                )
            elif query_seed:
                self._append_log(
                    f"[seed] {item['path'].name}: uzywam {query_seed!r}"
                )
            empty_wd = {
                "candidates": [], "english": "", "original_title": "",
                "original_lang": "", "source_url": "", "qid": "",
            }
            empty_commons = {
                "candidates": [], "english": "", "original_title": "",
                "original_lang": "", "source_url": "", "page_title": "",
                "wikidata_qid": "",
            }
            empty_wp = {
                "candidates": [], "english": "", "original_title": "",
                "original_lang": "", "source_url": "", "wikidata_qid": "",
            }
            empty_wikiart = {
                "candidates": [], "english": "", "year": "",
                "artist": "", "source_url": "",
            }
            wiki_candidates: list[str] = []
            wp_info: dict[str, Any] = empty_wp
            wd_info: dict[str, Any] = empty_wd
            commons_info: dict[str, Any] = empty_commons
            wikiart_info: dict[str, Any] = empty_wikiart
            met_candidates: list[str] = []
            artic_candidates: list[str] = []
            commons_candidates: list[str] = []
            wikiart_candidates: list[str] = []

            # Commons + Wikipedia potrafia rozpoznac plik po DOKLADNEJ nazwie -
            # przekazujemy filename oryginalny (np. "Mona_Lisa.jpg" albo
            # "Paul_Fischer_-_Aftenstemning_..._1909.png") zeby probowaly
            # bezposrednio "File:<nazwa>" / "<nazwa>" zanim zaczna szukac.
            #
            # ALE: gdy stem nazwy pliku to GENERYK ("Obraz", "Picture", "Image"),
            # filename match daje falszywy hit (np. wiki znajduje "Obraz" =
            # rosyjska ikona Q12797704 zamiast prawdziwego dziela). Wtedy pomijamy
            # commons_filename - wiki/commons szukaja tylko po query_seed.
            if filename_hint and is_generic_title(filename_hint):
                commons_filename = ""
                self._append_log(
                    f"[hint] {item['path'].name}: nazwa pliku to generyk "
                    f"({filename_hint!r}) - pomijam filename-lookup w wiki/commons"
                )
            else:
                commons_filename = item["path"].name

            if query_seed:
                # Cache key dla Commons/Wiki obejmuje filename - rozne pliki tego
                # samego autora z taka sama query daja rozne hity.
                commons_cache_query = f"{query_seed}|{commons_filename}"
                wiki_cache_query = f"{query_seed}|{commons_filename}"
                # Specyfikacja: (cache_source, cache_query, fn, args, kwargs)
                src_calls: dict[str, tuple[str, str, Any, tuple, dict]] = {
                    "wiki":     ("wiki",     wiki_cache_query,
                                 wikipedia_lookup,          (artist, query_seed),
                                 {"filename": commons_filename}),
                    "wikidata": ("wikidata", query_seed,
                                 wikidata_painting_lookup,  (artist, query_seed), {}),
                    "met":      ("met",      query_seed,
                                 met_museum_titles,         (artist, query_seed), {}),
                    "artic":    ("artic",    query_seed,
                                 art_institute_titles,      (artist, query_seed), {}),
                    "commons":  ("commons",  commons_cache_query,
                                 wikimedia_commons_lookup,  (artist, query_seed),
                                 {"filename": commons_filename}),
                    "wikiart":  ("wikiart",  query_seed,
                                 wikiart_lookup,            (artist, query_seed), {}),
                }
                with ThreadPoolExecutor(
                    max_workers=_PER_FILE_SOURCE_WORKERS,
                    thread_name_prefix="src",
                ) as sub_pool:
                    futures = {}
                    for src, (cache_src, cache_q, fn, args, kwargs) in src_calls.items():
                        futures[sub_pool.submit(
                            self._cached_call, cache_src, artist, cache_q,
                            fn, *args, **kwargs,
                        )] = src
                    for fut in as_completed(futures):
                        src = futures[fut]
                        try:
                            res = fut.result()
                        except SerpApiLimitError as e:
                            # Tylko WikiArt z text-sources uzywa SerpAPI - reszta
                            # (wiki/wikidata/met/artic/commons) jest niezalezna.
                            self._handle_serpapi_limit(e.reason)
                            self._append_log(
                                f"[serpapi-limit] [{src}] {item['path'].name}: {e.reason}"
                            )
                            res = None
                        except Exception as e:  # noqa: BLE001
                            self._append_log(f"[{src}] {item['path'].name}: blad: {e}")
                            res = None
                        if src == "wiki":
                            wp_info = res or empty_wp
                            wiki_candidates = list(
                                (wp_info or {}).get("candidates", [])
                            )
                            if wp_info.get("english") or wp_info.get("original_title"):
                                self._append_log(
                                    f"[wiki] {item['path'].name} -> "
                                    f"EN: {wp_info.get('english') or '?'!r} | "
                                    f"orig: {wp_info.get('original_title') or '?'!r} "
                                    f"[{wp_info.get('original_lang') or '-'}]"
                                    f"{(' qid='+wp_info['wikidata_qid']) if wp_info.get('wikidata_qid') else ''}"
                                )
                            elif wiki_candidates:
                                self._append_log(
                                    f"[wiki] {item['path'].name} -> {wiki_candidates[:3]}"
                                )
                        elif src == "wikidata":
                            wd_info = res or empty_wd
                            wd_cands = list((wd_info or {}).get("candidates", []))
                            if wd_cands:
                                self._append_log(
                                    f"[wikidata] {item['path'].name} -> "
                                    f"{(wd_info or {}).get('english') or '?'} "
                                    f"(qid={(wd_info or {}).get('qid') or '-'}, "
                                    f"oryginal: {(wd_info or {}).get('original_title') or '-'} "
                                    f"[{(wd_info or {}).get('original_lang') or '-'}])"
                                )
                        elif src == "met":
                            met_candidates = list(res or [])
                            if met_candidates:
                                self._append_log(
                                    f"[met] {item['path'].name} -> {met_candidates[:3]}"
                                )
                        elif src == "artic":
                            artic_candidates = list(res or [])
                            if artic_candidates:
                                self._append_log(
                                    f"[artic] {item['path'].name} -> {artic_candidates[:3]}"
                                )
                        elif src == "commons":
                            commons_info = res or empty_commons
                            commons_candidates = list(
                                (commons_info or {}).get("candidates", [])
                            )
                            if commons_info.get("english") or commons_info.get("original_title"):
                                self._append_log(
                                    f"[commons] {item['path'].name} -> "
                                    f"EN: {commons_info.get('english') or '?'!r} | "
                                    f"orig: {commons_info.get('original_title') or '?'!r} "
                                    f"[{commons_info.get('original_lang') or '-'}]"
                                )
                            elif commons_candidates:
                                self._append_log(
                                    f"[commons] {item['path'].name} -> {commons_candidates[:3]}"
                                )
                        elif src == "wikiart":
                            wikiart_info = res or empty_wikiart
                            wikiart_candidates = list(
                                (wikiart_info or {}).get("candidates", [])
                            )
                            if wikiart_info.get("english"):
                                self._append_log(
                                    f"[wikiart] {item['path'].name} -> "
                                    f"{wikiart_info['english']!r} "
                                    f"by {wikiart_info.get('artist') or '?'} "
                                    f"({wikiart_info.get('year') or '?'})"
                                )
                            elif wikiart_candidates:
                                self._append_log(
                                    f"[wikiart] {item['path'].name} -> {wikiart_candidates[:3]}"
                                )
                        phase()
            else:
                for _ in range(6):
                    phase()

            # 7) Wstepny resolve -> decyduje czy odpalac Google text + art-sites -- faza 7/8
            wd_candidates_for_resolver = list((wd_info or {}).get("candidates", []))
            prelim_title, prelim_conf, _, _ = resolve_title(
                lens_candidates=lens_candidates,
                yandex_candidates=yandex_candidates,
                bing_candidates=bing_candidates,
                wikiart_candidates=wikiart_candidates,
                wiki_candidates=wiki_candidates,
                wikidata_candidates=wd_candidates_for_resolver,
                met_candidates=met_candidates,
                artic_candidates=artic_candidates,
                commons_candidates=commons_candidates,
                google_candidates=[],
                filename_hint=filename_hint,
                artist=artist,
            )

            google_candidates: list[str] = []
            art_sites_candidates: list[str] = []
            if (env_get("SERPAPI_KEY") and prelim_conf < 0.6
                    and not self._serpapi_limit_event.is_set()):
                self._mark_status(item, "Google + serwisy aukcyjne...")
                queries: list[str] = []
                if prelim_title and artist:
                    queries.append(f'"{prelim_title}" "{artist}" painting')
                if filename_hint and artist:
                    queries.append(f'"{filename_hint}" "{artist}" painting')
                elif filename_hint:
                    queries.append(f'"{filename_hint}" painting')
                try:
                    for q in queries[:2]:
                        google_candidates.extend(google_text_titles(q, limit=8))
                    if google_candidates:
                        self._append_log(
                            f"[google] {item['path'].name} -> {google_candidates[:3]}"
                        )
                    ask_q = filename_hint or prelim_title
                    if ask_q:
                        art_sites_candidates = self._cached_call(
                            "art_sites", artist, ask_q,
                            art_sites_titles, artist, ask_q,
                        )
                        if art_sites_candidates:
                            self._append_log(
                                f"[art_sites] {item['path'].name} -> {art_sites_candidates[:3]}"
                            )
                except SerpApiLimitError as e:
                    self._handle_serpapi_limit(e.reason)
                    self._append_log(
                        f"[serpapi-limit] {item['path'].name}: {e.reason} "
                        "(pomijam google/art_sites)"
                    )
            phase()

            # 8) Final resolve ze wszystkimi sygnalami -- faza 8/8
            title, confidence, alternatives, sources_used = resolve_title(
                lens_candidates=lens_candidates,
                yandex_candidates=yandex_candidates,
                bing_candidates=bing_candidates,
                wikiart_candidates=wikiart_candidates,
                wiki_candidates=wiki_candidates,
                wikidata_candidates=wd_candidates_for_resolver,
                met_candidates=met_candidates,
                artic_candidates=artic_candidates,
                commons_candidates=commons_candidates,
                art_sites_candidates=art_sites_candidates,
                google_candidates=google_candidates,
                filename_hint=filename_hint,
                artist=artist,
            )

            # Zapisz per-source kandydatow do dialogu "Pokaz zrodla" (RMB).
            item["source_breakdown"] = {
                "wiki": list(wiki_candidates),
                "wikidata": list(wd_candidates_for_resolver),
                "met": list(met_candidates),
                "artic": list(artic_candidates),
                "commons": list(commons_candidates),
                "wikiart": list(wikiart_candidates),
                "art_sites": list(art_sites_candidates),
                "google": list(google_candidates),
            }

            if not title:
                self._apply_filename_hint_fallback(
                    item, reason="brak wyniku z zadnego zrodla online"
                )
                return

            # 8) Wybor "english_title" + "original_title" - laczymy sygnaly z
            #    Wikidata, Wikimedia Commons I Wikipedii. Wszystkie trzy potrafia
            #    dostarczyc EN + tytul w jezyku oryginalu (Commons z {{en|...}}
            #    {{da|...}}, Wikipedia z langlinks 130+ jezykow, Wikidata
            #    z labelow we wszystkich jezykach).
            #
            # Preferencja:
            #   1) Commons (najbardziej specyficzne dla pliku - direct File:)
            #   2) Wikipedia (artykul moze byc dokladnie o tym obrazie + langlinks)
            #   3) Wikidata (Q-id moze byc o szerszym pojeciu)
            # Cleanup descriptor-suffixow ("(1889), by Ivan Aïvazovski" itp.) z
            # english_title/original_title PRZED uzyciem w preferowaniu / [lang] swap.
            # Bez tego Commons EN 'The wave (1889), by Ivan Aïvazovski' wprost trafial
            # do nazwy pliku zamiast zostac pociety do 'The wave'.
            wd_en = clean_title_descriptor(wd_info.get("english") or "")
            wd_orig = clean_title_descriptor(wd_info.get("original_title") or "")
            wd_orig_lang = wd_info.get("original_lang") or ""
            wd_url = wd_info.get("source_url") or ""

            cm_en = clean_title_descriptor(commons_info.get("english") or "")
            cm_orig = clean_title_descriptor(commons_info.get("original_title") or "")
            cm_orig_lang = commons_info.get("original_lang") or ""
            cm_url = commons_info.get("source_url") or ""

            wp_en = clean_title_descriptor(wp_info.get("english") or "")
            wp_orig = clean_title_descriptor(wp_info.get("original_title") or "")
            wp_orig_lang = wp_info.get("original_lang") or ""
            wp_url = wp_info.get("source_url") or ""

            # FILTR ANTY-AUTOR: zrodlo czesto trafia w strone biograficzna
            # artysty (np. Wikipedia/Wikidata Q-id artysty) i zwraca jego
            # imie/nazwisko jako rzekomy "english title" obrazu. Wycinamy
            # takie kandydatury _zanim_ wejdzie logika preferencji,
            # zeby nie podmienialy poprawnego tytulu na imie autora.
            # Sprawdzamy DWA przypadki:
            #   1) text == aktualny artist (Andreas Achenbach -> Andreas Achenbach)
            #   2) text wyglada jak imie INNEGO artysty (Ludolf Bakhuizen) i nie
            #      ma zadnej zgodnosci tokenowej z nazwa pliku.
            import re as _re
            _hint_tokens = set(
                t.lower() for t in _re.findall(r"\w+", filename_hint or "")
                if len(t) >= 3
            )

            def _is_suspect_person(val: str) -> bool:
                if self._is_artist_name(val, artist):
                    return True
                # Person-name innego artysty: 2-3 capitalized slow + brak common
                # title function words + brak overlapu z filename. Te check sa
                # rygorystyczne, wiec rzadko dadza false positive na realnym tytule.
                return self._looks_like_person_name(val, hint_tokens=_hint_tokens)

            for src_name, _en_var, _orig_var in (
                ("wp", "wp_en", "wp_orig"),
                ("wd", "wd_en", "wd_orig"),
                ("cm", "cm_en", "cm_orig"),
            ):
                en_val = locals()[_en_var]
                orig_val = locals()[_orig_var]
                drop_en = _is_suspect_person(en_val)
                drop_orig = _is_suspect_person(orig_val)
                if drop_en or drop_orig:
                    self._append_log(
                        f"[anty-autor] {item['path'].name}: ignoruje z {src_name} "
                        f"{'EN=' + repr(en_val) if drop_en else ''}"
                        f"{' + ' if drop_en and drop_orig else ''}"
                        f"{'orig=' + repr(orig_val) if drop_orig else ''} "
                        "(to nazwisko artysty, nie tytul obrazu)"
                    )
                    if drop_en:
                        if _en_var == "wp_en":
                            wp_en = ""
                        elif _en_var == "wd_en":
                            wd_en = ""
                        else:
                            cm_en = ""
                    if drop_orig:
                        if _orig_var == "wp_orig":
                            wp_orig = ""
                            wp_orig_lang = ""
                        elif _orig_var == "wd_orig":
                            wd_orig = ""
                            wd_orig_lang = ""
                        else:
                            cm_orig = ""
                            cm_orig_lang = ""

            # FILTR ANTY-GENERIC: jesli wp_en/cm_en/wd_en (albo orig) to tylko
            # generyczne slowo ("Obraz", "Picture", "Image", "Образ"), wyzeruj.
            # Bez tego logika [lang] swap nizej brala "Obraz" jako english_title
            # i nadpisywala poprawny final title z visual search ("Babie Lato...").
            for src_name, _en_var, _orig_var in (
                ("wp", "wp_en", "wp_orig"),
                ("wd", "wd_en", "wd_orig"),
                ("cm", "cm_en", "cm_orig"),
            ):
                en_val = locals()[_en_var]
                orig_val = locals()[_orig_var]
                drop_en = bool(en_val) and is_generic_title(en_val)
                drop_orig = bool(orig_val) and is_generic_title(orig_val)
                if drop_en or drop_orig:
                    self._append_log(
                        f"[anty-generic] {item['path'].name}: ignoruje z {src_name} "
                        f"{'EN=' + repr(en_val) if drop_en else ''}"
                        f"{' + ' if drop_en and drop_orig else ''}"
                        f"{'orig=' + repr(orig_val) if drop_orig else ''} "
                        "(to generyk typu 'Obraz'/'Picture'/'Image' - nie tytul dziela)"
                    )
                    if drop_en:
                        if _en_var == "wp_en":
                            wp_en = ""
                        elif _en_var == "wd_en":
                            wd_en = ""
                        else:
                            cm_en = ""
                    if drop_orig:
                        if _orig_var == "wp_orig":
                            wp_orig = ""
                            wp_orig_lang = ""
                        elif _orig_var == "wd_orig":
                            wd_orig = ""
                            wd_orig_lang = ""
                        else:
                            cm_orig = ""
                            cm_orig_lang = ""

            # Reguly preferencji - najpierw zrodlo z OBYDWOMA tytulami:
            # Commons > Wikipedia > Wikidata.
            if cm_en and cm_orig:
                preferred_en = cm_en
                preferred_orig = cm_orig
                preferred_lang = cm_orig_lang
                preferred_url = cm_url
                preferred_src = "commons"
            elif wp_en and wp_orig:
                preferred_en = wp_en
                preferred_orig = wp_orig
                preferred_lang = wp_orig_lang
                preferred_url = wp_url
                preferred_src = "wikipedia"
            elif wd_en and wd_orig:
                preferred_en = wd_en
                preferred_orig = wd_orig
                preferred_lang = wd_orig_lang
                preferred_url = wd_url
                preferred_src = "wikidata"
            else:
                # Mieszanka: bierzemy najlepszy EN i najlepszy orig osobno,
                # zachowujac ten sam priorytet zrodel.
                preferred_en = cm_en or wp_en or wd_en
                preferred_orig = cm_orig or wp_orig or wd_orig
                preferred_lang = cm_orig_lang or wp_orig_lang or wd_orig_lang
                preferred_url = cm_url or wp_url or wd_url
                if cm_en or cm_orig:
                    preferred_src = "commons"
                elif wp_en or wp_orig:
                    preferred_src = "wikipedia"
                elif wd_en or wd_orig:
                    preferred_src = "wikidata"
                else:
                    preferred_src = ""

            # FALLBACK URL/EN z WikiArt - gdy Wiki/Commons/Wikidata nic nie zwrocily,
            # uzyj WikiArt jako zrodlo (URL do strony obrazu trafia do metadanych).
            wikiart_url = (wikiart_info or {}).get("source_url", "")
            wikiart_en = (wikiart_info or {}).get("english", "")
            if not preferred_url and wikiart_url:
                preferred_url = wikiart_url
                if not preferred_src:
                    preferred_src = "wikiart"
            if not preferred_en and wikiart_en:
                preferred_en = wikiart_en
                if not preferred_src:
                    preferred_src = "wikiart"

            english_title, original_title, original_lang = self._resolve_titles_for_metadata(
                final_title=title,
                wd_english=preferred_en,
                wd_original=preferred_orig,
                wd_original_lang=preferred_lang,
                filename_hint=filename_hint,
            )

            # FALLBACK SEARCH FOR ENGLISH TITLE: jesli mamy original (DE/FR/...)
            # ale brak english_title, sprobuj znalezc EN po katalogach aukcyjnych
            # (invaluable, mutualart, sothebys, christies, artnet) - tam tytuly
            # sa POWSZECHNIE po angielsku. Bardzo czesto plik na Commons ma
            # tylko {{de|...}} bez {{en|...}}, ale ten sam obraz na invaluable
            # jest opisany "Andreas Achenbach - The Beach at Scheveningen".
            if original_title and not english_title and artist:
                self._mark_status(item, "Szukam angielskiego tytulu...")
                try:
                    en_found = self._cached_call(
                        "english_lookup", artist,
                        f"{original_title}|{original_lang or 'xx'}",
                        english_title_for_foreign, artist, original_title,
                    )
                except Exception as e:  # noqa: BLE001
                    self._append_log(f"[en-lookup] {item['path'].name}: blad: {e}")
                    en_found = ""
                if en_found:
                    english_title = en_found
                    # Aktualizujemy preferred_en, zeby logika `[lang]` swap
                    # nizej zamienila finalny title na ten EN. Bez tego title
                    # zostawal w jezyku oryginalu mimo ze mamy EN.
                    preferred_en = en_found
                    if not preferred_src:
                        preferred_src = "en-lookup"
                    self._append_log(
                        f"[en-lookup] {item['path'].name}: znalazlem EN "
                        f"'{en_found}' dla {original_lang or '??'} "
                        f"'{original_title}' (po site:invaluable/mutualart/...)"
                    )

            # Title Case dla wynikow z Commons/Wikidata - czesto te zrodla
            # zwracaja tytul z mala litera ("The beach at Scheveningen"),
            # a my chcemy konsekwentnie "The Beach at Scheveningen".
            # format_artwork_title zachowuje tytuly obcojezyczne (umlauty).
            if english_title:
                english_title = format_artwork_title(english_title)
            # original_title NIE title-casujemy - zachowuje natywna kapitalizacje
            # (po niemiecku/dunsku/polsku przymiotniki sa z malej litery).

            # PREFERUJ ANGIELSKI W NAZWIE PLIKU - jesli mamy autorytatywny EN
            # z Wikidata/Commons, uzywamy go jako finalnego title (a oryginalny
            # tytul ladowny w jezyku ojczystym artysty trafia do metadanych).
            # Wymagamy zeby EN pochodzil z online (preferred_en), nie tylko
            # z heurystyki ASCII na nazwie pliku.
            #
            # WALIDACJA OVERLAP: english_title MUSI miec >=1 wspolny znaczacy
            # token z aktualnym title LUB z visual_aggregate. Bez tego Commons
            # zwracajacy 'End of the Black Sea Freedom' przebijal poprawne
            # 'Tempest' z resolvera, mimo ze to ZUPELNIE INNY OBRAZ.
            def _meaningful_tokens(s: str) -> set[str]:
                return {
                    t.lower()
                    for t in re.findall(r"[A-Za-z\u00C0-\u017F]+", s or "")
                    if len(t) >= 3
                }
            en_tokens = _meaningful_tokens(english_title)
            title_tokens = _meaningful_tokens(title)
            visual_tokens: set[str] = set()
            for v in visual_aggregate[:5]:
                visual_tokens |= _meaningful_tokens(v)
            overlap_with_title = en_tokens & title_tokens
            overlap_with_visual = en_tokens & visual_tokens

            if preferred_en and english_title and \
                    english_title.lower() != title.lower() and \
                    not self._is_artist_name(english_title, artist) and \
                    (overlap_with_title or overlap_with_visual):
                self._append_log(
                    f"[lang] {item['path'].name}: zamieniam final '{title}' "
                    f"-> EN '{english_title}' (oryginal pojdzie do metadanych)"
                )
                # Dodajemy stary final do alternatives, zeby user mogl latwo cofnac.
                alts_with_orig = list(alternatives)
                if title and title.lower() not in {a.lower() for a in alts_with_orig}:
                    alts_with_orig.insert(0, title)
                alternatives = alts_with_orig
                title = english_title
            elif preferred_en and english_title and \
                    english_title.lower() != title.lower() and \
                    not (overlap_with_title or overlap_with_visual):
                # Defensywa: english_title z innego zrodla nie ma nic wspolnego
                # z naszym wynikiem. Nie nadpisuj - to prawie na pewno HALLUCINATION
                # z text-search dla zatrutego query_seed.
                self._append_log(
                    f"[lang] {item['path'].name}: NIE swap-uje '{title}' "
                    f"-> '{english_title}' (zero overlap, prawdopodobnie inny obraz)"
                )
                # Wyzeruj english_title zeby NIE trafil do EXIF jako 'Title'.
                english_title = ""
            elif english_title and self._is_artist_name(english_title, artist):
                # Defensywa - nie zapisuj nazwiska artysty jako "english_title".
                self._append_log(
                    f"[anty-autor] {item['path'].name}: english_title='{english_title}' "
                    "to nazwisko artysty - czyszcze pole EN."
                )
                english_title = ""

            # Tytul finalny do nazwy pliku tez przepuszczamy przez format_artwork_title
            # - zapewnia spojny Title Case dla EN, zachowuje DE/PL bez zmian.
            title = format_artwork_title(title)

            # AUTO-WNIOSKOWANIE z Wikidata (gdy mamy Q-id obrazu):
            #   - P170 (creator) -> uzupelnia `artist` (gdy brak z folderu/filename)
            #   - P571 (inception) -> `creation_year` (tylko precision>=9 == rok
            #     znany dokladnie, nie dekada/wiek).
            painting_qid = (
                (wp_info or {}).get("wikidata_qid")
                or (commons_info or {}).get("wikidata_qid")
                or (wd_info or {}).get("qid")
            )

            if not artist and painting_qid:
                self._mark_status(item, "Wnioskowanie autora z Wikidata...")
                try:
                    inferred = self._cached_call(
                        "wd_creator", "", painting_qid,
                        wikidata_creator_label, painting_qid,
                    )
                except Exception as e:  # noqa: BLE001
                    self._append_log(
                        f"[autor] {item['path'].name}: blad wnioskowania: {e}"
                    )
                    inferred = ""
                if inferred:
                    artist = normalize_artist(inferred)
                    item["artist"] = artist
                    item["artist_inferred_from"] = painting_qid
                    self._append_log(
                        f"[autor] {item['path'].name}: P170 z {painting_qid} -> "
                        f"{inferred!r} (auto-wykryty)"
                    )

            # FALLBACK autora z WikiArt URL slug (gdy Wikidata nie ma qid):
            #   https://www.wikiart.org/en/ivan-aivazovsky/tempest-1855
            #   -> artist = "Ivan Aivazovsky"
            if not artist and (wikiart_info or {}).get("artist"):
                wikiart_artist = wikiart_info["artist"]
                artist = normalize_artist(wikiart_artist)
                item["artist"] = artist
                item["artist_inferred_from"] = "wikiart"
                self._append_log(
                    f"[autor] {item['path'].name}: WikiArt URL slug -> "
                    f"{wikiart_artist!r} (auto-wykryty)"
                )

            creation_year = ""
            if painting_qid:
                try:
                    creation_year = self._cached_call(
                        "wd_year", "", painting_qid,
                        wikidata_inception_year, painting_qid,
                    ) or ""
                except Exception as e:  # noqa: BLE001
                    self._append_log(
                        f"[rok] {item['path'].name}: blad wnioskowania: {e}"
                    )
                    creation_year = ""
                if creation_year:
                    item["creation_year"] = creation_year
                    self._append_log(
                        f"[rok] {item['path'].name}: P571 z {painting_qid} -> "
                        f"{creation_year} (precision>=rok)"
                    )

            # FALLBACK roku z WikiArt URL slug (gdy Wikidata nie ma):
            #   /tempest-1855 -> year="1855"
            if not creation_year and (wikiart_info or {}).get("year"):
                creation_year = str(wikiart_info["year"])
                item["creation_year"] = creation_year
                self._append_log(
                    f"[rok] {item['path'].name}: WikiArt URL slug -> "
                    f"{creation_year} (auto-wykryty)"
                )

            item["title"] = title
            item["english_title"] = english_title
            item["alternatives"] = alternatives
            item["original_title"] = original_title
            item["original_lang"] = original_lang
            item["source_url"] = preferred_url
            item["source_name"] = preferred_src
            item["confidence"] = float(confidence)
            item["sources_used"] = int(sources_used)
            item["error"] = ""

            pct = int(round(confidence * 100))
            srcs = sources_used
            srcs_word = "zrodlo" if srcs == 1 else ("zrodla" if 2 <= srcs <= 4 else "zrodel")
            extra = ""
            if original_title and english_title and english_title.lower() != original_title.lower():
                extra = f", EN: {english_title!r}, oryginal: {original_title!r} [{original_lang or '?'}]"
            elif original_title:
                extra = f", oryginal: {original_title!r} [{original_lang or '?'}]"
            elif english_title and english_title.lower() != title.lower():
                extra = f", EN: {english_title!r}"
            if not artist:
                item["status"] = f"tytul OK ({pct}%, {srcs} {srcs_word}), brak autora"
            else:
                item["status"] = f"gotowe ({pct}%, {srcs} {srcs_word})"
            try:
                proposed_name = build_new_name(artist, title, item["path"]) if title else ""
            except Exception:  # noqa: BLE001
                proposed_name = ""
            artist_str = artist if artist else "(brak autora)"
            name_str = f" => {proposed_name}" if proposed_name else ""
            self._append_log(
                f"[wynik] {item['path'].name} -> autor: {artist_str} | tytul: {title!r} "
                f"({pct}%, {srcs} {srcs_word}){extra}{name_str}"
            )
            self.root.after(0, self._refresh_tree)
            self.root.after(0, self._refresh_counts_and_status)
        finally:
            # "Finalize" - faza 8/8. Jesli wczesniej wyszlismy z funkcji
            # przed osiagnieciem fazy N, dociagamy reszte zeby pasek
            # na pewno doszedl do 100% dla tego pliku.
            remaining = max(0.0, _SEARCH_PHASES - phases_done)
            if remaining > 0:
                self._bump_search(remaining)

    def _apply_filename_hint_fallback(self, item: dict[str, Any], *, reason: str) -> None:
        """Gdy upload / Lens zawiodl, uzyj tytulu z nazwy pliku jako propozycji."""
        hint = format_artwork_title((item.get("title_hint") or "").strip())
        if hint:
            # Nawet w trybie fallback staramy sie rozdzielic EN vs original.
            if self._looks_english(hint):
                item["english_title"] = hint
                item["original_title"] = ""
                item["original_lang"] = ""
            else:
                item["english_title"] = ""
                item["original_title"] = hint
                item["original_lang"] = ""
            item["title"] = hint
            item["confidence"] = 0.2
            item["sources_used"] = 1
            item["error"] = reason
            item["status"] = "z nazwy pliku (20%, 1 zrodlo)"
            self._append_log(f"[fallback] {item['path'].name}: uzywam tytulu z nazwy pliku -> {hint!r}")
            self.root.after(0, self._refresh_tree)
            self.root.after(0, self._refresh_counts_and_status)
            return
        self._set_error(item, reason)

    def _search_worker(self, items: list[dict[str, Any]]) -> None:
        total = len(items)
        workers = max(1, min(_SEARCH_WORKERS, total))
        try:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="lens") as pool:
                futures = {pool.submit(self._process_one, it): it for it in items}
                # Konsumujemy futures dla synchronizacji bledow/wyjatkow,
                # ale NIE nadpisujemy status_var - status pokazuja paski
                # postepu i toasty z _bump_search/_bump_upload.
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception:  # noqa: BLE001 - wyjatki sa logowane wewnatrz
                        pass
        finally:
            self._busy = False
            self.root.after(0, lambda: self.search_btn.configure(state="normal"))
            self.root.after(0, self._refresh_counts_and_status)

    def _mark_status(self, item: dict[str, Any], text: str) -> None:
        item["status"] = text
        self.root.after(0, self._refresh_tree)

    def _set_error(self, item: dict[str, Any], text: str) -> None:
        item["error"] = text
        item["status"] = "BLAD"
        self._append_log(f"[error] {item['path'].name}: {text}")
        self.root.after(0, self._refresh_tree)

    # ---------------------- Rename ----------------------
    _LOW_CONF_THRESHOLD = 0.40

    def _apply_rename_plan(
        self,
        plan: list[tuple[dict[str, Any], str]],
        *,
        log_tag: str = "rename",
    ) -> tuple[int, int, int, list[dict[str, Any]]]:
        """Wykonuje rename + zapis metadanych; zwraca (ok, errors, meta_written, batch)."""
        ok, errors, meta_written = 0, 0, 0
        batch: list[dict[str, Any]] = []
        for it, new_name in plan:
            old_path = it["path"]
            try:
                new_path = rename_file(old_path, new_name)
                it["renamed_to"] = new_path.name
                it["path"] = new_path
                it["status"] = "ZMIENIONO"
                ok += 1
                self._append_log(f"[{log_tag}] {old_path.name} -> {new_path.name}")
            except (FileExistsError, OSError, ValueError) as e:
                it["error"] = str(e)
                it["status"] = "BLAD"
                errors += 1
                self._append_log(f"[error] {log_tag} {old_path.name}: {e}")
                continue

            sidecar_path: Path | None = None
            if not it.get("title"):
                batch.append({
                    "item": it,
                    "old_path": old_path,
                    "new_path": it["path"],
                    "sidecar": None,
                })
                continue

            try:
                eng = (it.get("english_title") or "").strip() or it.get("title", "")
                meta = ArtworkMetadata(
                    english_title=eng,
                    original_title=it.get("original_title", ""),
                    original_lang=it.get("original_lang", ""),
                    artist=it.get("artist", ""),
                    creation_year=it.get("creation_year", ""),
                    source_url=it.get("source_url", ""),
                    source_name=it.get("source_name", ""),
                )
                info = write_artwork_metadata(it["path"], meta)
                bits = []
                exif_kind = info.get("exif", "")
                if exif_kind in ("ok", "png-text", "webp-exif"):
                    bits.append({
                        "ok": "EXIF",
                        "png-text": "PNG-tEXt",
                        "webp-exif": "WebP-EXIF",
                    }[exif_kind])
                if info.get("sidecar"):
                    bits.append(info["sidecar"])
                    sidecar_path = it["path"].with_suffix(it["path"].suffix + ".metadata.json")
                if bits:
                    meta_written += 1
                    self._append_log(
                        f"[meta] {it['path'].name}: {', '.join(bits)}"
                    )
            except OSError as e:
                self._append_log(f"[meta] {it['path'].name}: blad zapisu metadanych: {e}")

            batch.append({
                "item": it,
                "old_path": old_path,
                "new_path": it["path"],
                "sidecar": sidecar_path,
            })

        self._last_rename_batch = batch
        self.undo_btn.configure(state=("normal" if batch else "disabled"))
        self._refresh_tree()
        self._refresh_counts_and_status()
        return ok, errors, meta_written, batch

    def _warn_low_confidence(self, plan: list[tuple[dict[str, Any], str]]) -> bool:
        """True = kontynuuj, False = anuluj. Dotyczy tylko pozycji juz po wyszukiwaniu (jest tytul)."""
        low_conf = [
            (it, nn) for (it, nn) in plan
            if it.get("title")
            and float(it.get("confidence", 0.0)) < self._LOW_CONF_THRESHOLD
        ]
        if not low_conf:
            return True
        sample = "\n".join(
            f"  - {it['path'].name}  ->  {nn}  "
            f"({int(round(float(it.get('confidence', 0.0)) * 100))}%)"
            for it, nn in low_conf[:8]
        )
        more = f"\n  ... i {len(low_conf) - 8} innych" if len(low_conf) > 8 else ""
        return bool(
            messagebox.askyesno(
                APP_TITLE,
                f"UWAGA: {len(low_conf)} pozycji ma pewnosc ponizej "
                f"{int(self._LOW_CONF_THRESHOLD * 100)}%:\n\n{sample}{more}\n\n"
                "Czy mimo to kontynuowac?",
                icon="warning",
            )
        )

    def _on_rename_clicked(self) -> None:
        ready = [
            it for it in self.queue_items
            if it.get("title") and it.get("artist")
        ]
        if not ready:
            messagebox.showinfo(APP_TITLE, "Brak pozycji gotowych do zmiany nazwy.")
            return
        plan: list[tuple[dict[str, Any], str]] = []
        for it in ready:
            new_name = self._build_new_name(it)
            if new_name == it["path"].name:
                continue
            if is_already_named(it["artist"], it["title"], it["path"].name):
                continue
            plan.append((it, new_name))
        if not plan:
            messagebox.showinfo(APP_TITLE, "Wszystkie pliki maja juz docelowa nazwe.")
            return

        if not self._warn_low_confidence(plan):
            return

        if not messagebox.askyesno(
            APP_TITLE,
            f"Zmienic nazwy {len(plan)} plik(ow)?\n\nPrzyklad:\n"
            f"{plan[0][0]['path'].name}  ->  {plan[0][1]}",
        ):
            return

        ok, errors, meta_written, _batch = self._apply_rename_plan(plan, log_tag="rename")
        self._show_toast(
            f"Zmiana nazw: {ok} OK, bledow: {errors} (metadane: {meta_written})",
            color="#06a", duration_ms=2200,
        )
        messagebox.showinfo(
            APP_TITLE,
            f"Zmieniono nazwy: {ok}\n"
            f"Bledow: {errors}\n"
            f"Zapisano metadane: {meta_written}\n\n"
            f"W razie potrzeby uzyj 'Cofnij ostatni rename'.",
        )

    def _plan_suffix_renames(
        self, items: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], str]]:
        """Przed wyszukiwaniem: biezaca nazwa + sufiks. Po wyszukaniu: nazwa kanoniczna + sufiks."""
        suf = self._suffix()
        if not suf:
            return []
        plan: list[tuple[dict[str, Any], str]] = []
        for it in items:
            if not it.get("title"):
                nn = append_suffix_to_original_filename(it["path"].name, suf)
            else:
                nn = build_new_name(
                    it.get("artist", ""),
                    it.get("title", ""),
                    it["path"],
                    suffix=suf,
                )
            if nn == it["path"].name:
                continue
            plan.append((it, nn))
        return plan

    def _run_suffix_batch(
        self, items: list[dict[str, Any]], *, scope_desc: str
    ) -> None:
        suf = self._suffix()
        if not suf:
            messagebox.showinfo(
                APP_TITLE,
                "Wpisz tekst sufiksu w polu obok (np. Mockup, Print, Hi-Res).",
            )
            return
        if not items:
            messagebox.showinfo(APP_TITLE, "Brak pozycji do przetworzenia.")
            return
        plan = self._plan_suffix_renames(items)
        if not plan:
            messagebox.showinfo(
                APP_TITLE,
                "Zadna nazwa sie nie zmieni — pliki maja juz ten sufiks w nazwie "
                f"lub nazwa jest identyczna ({suf!r}).",
            )
            return

        if not self._warn_low_confidence(plan):
            return

        if not messagebox.askyesno(
            APP_TITLE,
            f"Dodac sufiks {suf!r} ({scope_desc})?\n"
            f"Liczba plikow: {len(plan)}\n\n"
            f"Przyklad:\n{plan[0][0]['path'].name}  ->  {plan[0][1]}",
        ):
            return

        ok, errors, meta_written, _batch = self._apply_rename_plan(plan, log_tag="rename+suffix")
        self._show_toast(
            f"Sufiks: {ok} OK, bledow: {errors} (metadane: {meta_written})",
            color="#06a", duration_ms=2200,
        )
        messagebox.showinfo(
            APP_TITLE,
            f"Dodano sufiks do nazw: {ok}\n"
            f"Bledow: {errors}\n"
            f"Zapisano metadane: {meta_written}\n\n"
            f"W razie potrzeby uzyj 'Cofnij ostatni rename'.",
        )

    def _on_add_suffix_clicked(self) -> None:
        items = self._items_from_tree_selection()
        if not items:
            messagebox.showinfo(
                APP_TITLE,
                "Zaznacz w tabeli jeden lub wiecej wierszy, ktorym dodac sufiks.\n\n"
                "Albo uzyj przycisku 'Zmień na wszystkich' — obejmie cala kolejke.",
            )
            return
        self._run_suffix_batch(items, scope_desc="tylko zaznaczone wiersze")

    def _on_suffix_all_clicked(self) -> None:
        if not self.queue_items:
            messagebox.showinfo(APP_TITLE, "Kolejka jest pusta — dodaj najpierw pliki.")
            return
        self._run_suffix_batch(list(self.queue_items), scope_desc="wszystkie pozycje na liscie")

    def _on_undo_rename(self) -> None:
        """Cofnij ostatnia operacje rename - przywroc pliki do poprzednich nazw."""
        if not self._last_rename_batch:
            messagebox.showinfo(APP_TITLE, "Brak operacji do cofniecia.")
            return
        if not messagebox.askyesno(
            APP_TITLE,
            f"Cofnac zmiane nazw {len(self._last_rename_batch)} plik(ow)?",
        ):
            return
        ok, errors = 0, 0
        for entry in reversed(self._last_rename_batch):
            it = entry["item"]
            new_path: Path = entry["new_path"]
            old_path: Path = entry["old_path"]
            sidecar: Path | None = entry.get("sidecar")
            try:
                if not new_path.exists():
                    raise FileNotFoundError(f"plik docelowy zniknal: {new_path}")
                if old_path.exists() and old_path != new_path:
                    raise FileExistsError(f"plik {old_path.name} juz istnieje")
                new_path.rename(old_path)
                it["path"] = old_path
                it["renamed_to"] = ""
                it["status"] = "cofnieto"
                ok += 1
                self._append_log(f"[undo] {new_path.name} -> {old_path.name}")
                # Cofnij sidecar (przemianuj go zeby pasowal do starego rozszerzenia).
                if sidecar and sidecar.exists():
                    new_sidecar = old_path.with_suffix(old_path.suffix + ".metadata.json")
                    try:
                        sidecar.rename(new_sidecar)
                    except OSError:
                        pass
            except (FileExistsError, FileNotFoundError, OSError) as e:
                errors += 1
                self._append_log(f"[error] undo {new_path.name}: {e}")
        self._last_rename_batch = []
        self.undo_btn.configure(state="disabled")
        self._refresh_tree()
        self._refresh_counts_and_status()
        self._show_toast(
            f"Cofnieto: {ok} OK, bledow: {errors}",
            color="#a60", duration_ms=2000,
        )

    # ---------------------- Cache ----------------------
    def _on_clear_cache_clicked(self) -> None:
        """Wymus odswiezenie - kasuje RAM cache i pliki .cache/nazwijobraz/*.json.

        Uzyteczne gdy zmienila sie logika wyszukiwania albo Commons/Wiki
        zaktualizowaly metadane obrazu, a my wciaz dostajemy stary wynik.
        """
        if not messagebox.askyesno(
            APP_TITLE,
            "Wyczyscic cache wynikow wyszukiwania?\n\n"
            "Nastepne 'Wyszukaj nazwy' ponownie zapyta wszystkie zrodla "
            "(Wikipedia, Wikidata, Commons, Met, ArtIC). "
            "To moze potrwac dluzej niz zwykle.",
        ):
            return
        # 1) RAM
        with self._cache_lock:
            self._search_cache.clear()
        # 2) Disk
        removed = 0
        if self._disk_cache is not None:
            try:
                with self._disk_cache._lock:  # noqa: SLF001 - prywatne, ale OK
                    self._disk_cache._data.clear()  # noqa: SLF001
                    self._disk_cache._loaded.clear()  # noqa: SLF001
                    self._disk_cache._dirty.clear()  # noqa: SLF001
                cache_dir = self._disk_cache.base_dir
                if cache_dir.exists():
                    for f in cache_dir.glob("*.json"):
                        try:
                            f.unlink()
                            removed += 1
                        except OSError:
                            pass
            except Exception as e:  # noqa: BLE001
                self._append_log(f"[cache] blad czyszczenia: {e}")
        self._append_log(f"[cache] wyczyszczono ({removed} plikow z dysku + RAM)")
        self._show_toast(
            f"Cache wyczyszczony ({removed} plikow)",
            color="#0a6", duration_ms=2000,
        )

    # ---------------------- SerpAPI limit handling ----------------------
    def _handle_serpapi_limit(self, reason: str) -> None:
        """Wywolywane z dowolnego watku gdy SerpAPI zwroci limit/blad klucza.

        Ustawia globalna flage (kolejne pliki w batch pomijaja SerpAPI calls)
        i zleca otwarcie dialogu z linkiem do dashboard SerpAPI + polem na nowy
        klucz. Dialog pokazuje sie TYLKO RAZ dla calej sesji.
        """
        with self._serpapi_limit_lock:
            already = self._serpapi_limit_event.is_set()
            self._serpapi_limit_event.set()
            self._serpapi_limit_reason = reason or "limit wyczerpany"
            if already or self._serpapi_limit_dialog_open:
                return
            self._serpapi_limit_dialog_open = True
        # Pokaz dialog w UI (musi byc na main thread)
        self.root.after(0, self._show_serpapi_limit_dialog, reason)

    def _show_serpapi_limit_dialog(self, reason: str) -> None:
        """Modalne okno z linkiem do dashboard + polem do wpisania nowego klucza."""
        try:
            win = tk.Toplevel(self.root)
            win.title("SerpAPI - limit wyczerpany")
            win.transient(self.root)
            win.grab_set()
            win.resizable(False, False)
        except tk.TclError:
            self._serpapi_limit_dialog_open = False
            return

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        # Ikona warning + tytul
        head = ttk.Frame(frame)
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(
            head, text="\u26A0  SerpAPI nie odpowiedzial (limit / klucz)",
            font=("Segoe UI", 11, "bold"), foreground="#a60",
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=f"Powod: {reason or '(nieznany)'}",
            wraplength=440, foreground="#666",
        ).pack(fill="x", pady=(0, 10))

        info = ttk.Label(
            frame,
            text=(
                "Zaloguj sie na inne konto SerpAPI (lub kup wiecej zapytan), "
                "skopiuj nowy klucz API i wklej ponizej. "
                "Plik cursor-api/.env zostanie zaktualizowany automatycznie."
            ),
            wraplength=440, justify="left",
        )
        info.pack(fill="x", pady=(0, 6))

        # Klikalny link do dashboard
        link_frame = ttk.Frame(frame)
        link_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(link_frame, text="Dashboard SerpAPI: ").pack(side="left")
        link = tk.Label(
            link_frame, text="https://serpapi.com/manage-api-key",
            fg="#06a", cursor="hand2", font=("Segoe UI", 9, "underline"),
        )
        link.pack(side="left")

        def _open_link(_e: Any = None) -> None:
            import webbrowser
            webbrowser.open("https://serpapi.com/manage-api-key")
        link.bind("<Button-1>", _open_link)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=8)

        # Pole na nowy klucz
        ttk.Label(frame, text="Nowy SERPAPI_KEY:").pack(anchor="w")
        key_var = tk.StringVar(value="")
        entry = ttk.Entry(frame, textvariable=key_var, width=58, show="*")
        entry.pack(fill="x", pady=(2, 4))
        show_var = tk.IntVar(value=0)

        def _toggle_show() -> None:
            entry.configure(show="" if show_var.get() else "*")
        ttk.Checkbutton(
            frame, text="Pokaz znaki", variable=show_var, command=_toggle_show,
        ).pack(anchor="w")

        status_var = tk.StringVar(value="")
        ttk.Label(
            frame, textvariable=status_var, foreground="#a60",
            wraplength=440,
        ).pack(fill="x", pady=(4, 0))

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(10, 0))

        def _close(reset_flag: bool) -> None:
            with self._serpapi_limit_lock:
                self._serpapi_limit_dialog_open = False
                if reset_flag:
                    self._serpapi_limit_event.clear()
                    self._serpapi_limit_reason = ""
            try:
                win.grab_release()
            except tk.TclError:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass

        def _save_and_continue() -> None:
            new_key = key_var.get().strip()
            if not new_key or len(new_key) < 16:
                status_var.set("Klucz wyglada na za krotki (>=16 znakow). Sprawdz i ponow.")
                return
            try:
                env_path = set_env_value("SERPAPI_KEY", new_key)
            except OSError as e:
                status_var.set(f"Nie udalo sie zapisac .env: {e}")
                return
            self._append_log(
                f"[serpapi-key] zaktualizowany w {env_path} "
                f"(klucz: ...{new_key[-6:]})"
            )
            self._show_toast("Klucz SerpAPI zaktualizowany. Klik 'Wyszukaj nazwy' aby kontynuowac.",
                             color="#0a6", duration_ms=3000)
            _close(reset_flag=True)

        def _skip_serpapi() -> None:
            # Pozostawmy flage SET-owana - pozostale pliki w trwajacym batch ich nie wywolaja.
            self._append_log(
                "[serpapi-key] uzytkownik wybral 'Pomin SerpAPI' - pozostale pliki "
                "uzyja tylko Wiki/Wikidata/Met/ArtIC/Commons (bez Lens/Yandex/Bing/Google)."
            )
            _close(reset_flag=False)

        ttk.Button(btn_row, text="Zapisz klucz i kontynuuj",
                   command=_save_and_continue).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="Pomin SerpAPI dla pozostalych",
                   command=_skip_serpapi).pack(side="right")
        ttk.Button(btn_row, text="Anuluj",
                   command=lambda: _close(reset_flag=False)).pack(side="right", padx=(0, 6))

        try:
            position_toplevel_screen_center_from_reqsize(win)
        except tk.TclError:
            pass
        entry.focus_set()

    # ---------------------- Log ----------------------
    def _show_help(self) -> None:
        try:
            from Komponenty._shared.help_dialog import show_help
        except ImportError:
            messagebox.showinfo("Instrukcja", _NAZWIJ_HELP)
            return
        show_help(self.root, title="Instrukcja - Nazwij obraz", text=_NAZWIJ_HELP)

    def _prewarm_http_session(self) -> None:
        """Otwiera TLS handshake do hostow uploadu zeby pierwszy upload byl szybki.

        Bez tego pierwszy upload do 0x0.st/catbox.moe placi 100-300ms za TLS
        handshake. Z keep-alive sesji requests, kolejne requesty leca po juz
        otwartym tunelu - oszczedzamy ~200ms na kazdym uploadzie.
        """
        try:
            from .http_client import get_session
            sess = get_session()
            for url in (
                "https://0x0.st",
                "https://catbox.moe",
                "https://en.wikipedia.org",
                "https://www.wikidata.org",
            ):
                try:
                    sess.head(url, timeout=5.0, allow_redirects=False)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    def _append_log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self._poll_log_queue)


_NAZWIJ_HELP = """# Nazwij obraz - automatyczna zmiana nazw

Aplikacja **wyszukuje oryginalna nazwe obrazu** w wielu zrodlach naraz
(Google Lens, Wikipedia, Wikidata, Wikimedia Commons, Met Museum,
Art Institute of Chicago + 10 stron art-marketu) i zmienia nazwy plikow
na format **`Autor - Tytul`**.

## Krok po kroku
1. **Dodaj pliki do kolejki** - przycisk **Dodaj pliki...** lub **przeciagnij i upusc**
   pliki/foldery na okno aplikacji.
2. Aplikacja automatycznie wyciaga **autora ze sciezki pliku** (np. z folderu
   `Sisley, Alfred/...` -> autor = "Alfred Sisley").
3. Kliknij **Wyszukaj nazwy** - aplikacja w tle pyta wszystkie zrodla rownolegle.
4. Po zakonczeniu w kolumnie "Tytul" widzisz znalezione nazwy + procent pewnosci.
5. Kliknij **Zmien nazwy** - aplikacja przemianuje pliki na `Autor - Tytul.ext`.
   - Niska pewnosc (<40%) -> wyswietli ostrzezenie z lista przed zmiana.
   - Po renamie aktywuje sie **Cofnij ostatni rename** - jednym przyciskiem cofniesz batch.
6. (Opcjonalnie) Pole **Sufiks** + przyciski **Dodaj sufiks** / **Zmień na wszystkich**:
   - **Przed** kliknieciem **Wyszukaj nazwy**: zmienia **biezaca nazwe pliku** na dysku
     (`stare.jpg` -> `stare - Mockup.jpg`). Kolumna "Nowa nazwa" pokazuje podglad.
   - **Po** wyszukiwaniu: ten sam sufiks wplywa tylko na **docelowa nazwe**
     (`Autor - Tytul - Mockup.jpg`); sam plik na dysku zmienia sie dopiero po tym przycisku.
   - **Dodaj sufiks** — tylko **zaznaczone** wiersze. **Zmień na wszystkich** — cala kolejka.

## Co aplikacja robi pod spodem
- **Upload obrazu** - rownolegle do 0x0.st i catbox.moe (bierzemy szybszego),
  obraz wczesniej skalowany do max 1.5 MB.
- **Wyszukiwanie nazwy** - 8 zrodel w pelnej rownoleglosci:
  Google Lens (SerpAPI), Wikipedia, Wikidata, Wikimedia Commons (z parsowaniem
  multilingual titles), Met Collection API, Art Institute API, Google text
  search po "art-sites", agregat 10+ specjalistycznych stron.
- **Konsolidacja kandydatow** - kazde zrodlo dostaje wage; tytul wybierany jest
  jako najlepiej oceniony, z **cap'em na pewnosc** w zaleznosci od liczby
  zgodnych zrodel.
- **Title Case** - wlasciwy dla nazw obrazow (przyimki male: "of, in, the"; rzymskie I-X duze; mixed case zachowane).
- **Metadane** - po zmianie nazwy zapisywane sa:
  - tytul angielski + tytul oryginalny (np. dunski) w EXIF (JPEG/WebP) lub PNG tEXt.
  - sidecar JSON `<plik>.metadata.json` z pelnymi info (zrodlo, pewnosc, lista kandydatow).

## Konfiguracja
- **Klucz SerpAPI** - aby uzywac Google Lens, ustaw zmienna `SERPAPI_KEY`
  w pliku `cursor-api/.env`. Bez klucza Lens jest pomijany - aplikacja dziala
  z pozostalych 7 zrodel.
- **Cache** - aplikacja trzyma cache RAM przez sesje + cache dyskowy
  (`cursor-api/.cache/nazwijobraz/<source>.json`, TTL 30 dni).
  Te same zapytania przy nastepnym uruchomieniu sa instant.

## Skroty
- **Ctrl+A** w kolejce - zaznacz wszystkie.
- **Delete** - usun zaznaczone.
- **Prawy klik** w kolejce - menu kontekstowe (kopiuj sciezke, otworz w eksploratorze).
- Klik na **naglowek kolumny** - sortowanie (toggle asc/desc).

## Tipy
- Gdy automat sie pomyli, mozesz **edytowac wiersze recznie** podwojnym kliknieciem.
- Filename hint - jesli plik nazywa sie `Mona_Lisa.jpg` (znaki `_` traktowane jak spacje),
  aplikacja uzyje tej nazwy jako mocnego hintu (waga `filename` = 10, najwieksza).
- Jesli upload trwa dlugo (>5s), sprawdz log - czasy uploadu sa logowane.
"""


def main() -> None:
    if _HAS_DND:
        root: Any = TkinterDnD.Tk()  # type: ignore[attr-defined]
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
