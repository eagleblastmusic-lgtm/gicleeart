# GicleeApp — Implemented Solutions Index

Hub warstwy API: [`README.md`](README.md) · Launcher: [`../giclee_app/docs/README.md`](../giclee_app/docs/README.md) · Logika per komponent: [`komponenty/README.md`](komponenty/README.md) · Moduły `_shared`: [`shared.md`](shared.md)

**Ostatnia aktualizacja indeksu:** 2026-07-16

---

## Cel pliku

Żywa mapa wdrożonych rozwiązań w GicleeApp dla Cursora i przyszłych prac. Odpowiada na pytania:

- co już istnieje,
- gdzie leży kod,
- kiedy użyć istniejącego wzorca,
- czego **nie** tworzyć drugi raz.

To **nie jest** kopia kodu ani zamiennik dokumentacji biznesowej komponentów (`komponenty/<nazwa>.md`).

---

## Zasady użycia

1. **Przed każdym nowym komponentem** — przeczytaj ten plik (sekcja [Przyszłe komponenty](#przyszłe-komponenty)).
2. **Przed dodaniem helpera** — sprawdź [`Komponenty/_shared/`](../Komponenty/_shared/) i sekcje [Wzorce GUI](#wzorce-gui) oraz [Operacje na plikach](#operacje-na-plikach).
3. **Po dodaniu komponentu lub wspólnego wzorca** — zaktualizuj ten plik (wiersz w tabeli + ewentualny wpis w TODO).
4. **Nie kopiuj pełnego kodu** — podawaj ścieżki, nazwy funkcji i zastosowanie.
5. Szczegóły biznesowe komponentu → [`komponenty/<folder>.md`](komponenty/). Szczegóły launchera → [`../giclee_app/docs/`](../giclee_app/docs/).

---

## Przyszłe komponenty

**Obowiązkowa kolejność pracy Cursora:**

1. Przeczytaj **ten plik**: `cursor-api/docs/GICLEEAPP_IMPLEMENTED_SOLUTIONS_INDEX.md`
2. Sprawdź, czy podobny komponent lub helper już istnieje (tabele poniżej + `_shared/`)
3. Przeczytaj [`component-loader.md`](../giclee_app/docs/component-loader.md) — minimalny zestaw plików
4. Dopiero potem projektuj nowy folder w `Komponenty/<nazwa>/`

Jeśli funkcja (toast, DnD, log JSONL, wybór folderu) jest już w `_shared/` — **użyj jej**, nie pisz lokalnej kopii.

---

## Komponenty

**Stan:** 56 zarejestrowanych komponentów (`component.json`) + 1 folder poza rejestracją (`stronaglownav2` — pusty placeholder).

**Ścieżka bazowa:** `cursor-api/Komponenty/<folder>/`

**Uruchomienie:**

| Tryb | Jak uruchomić |
|------|----------------|
| `subprocess` | `python -m Komponenty.<folder>` lub kafelek w GicleeApp |
| `inline` | Kafelek w launcherze / Studio → `view.py` → `build_view(parent, on_back)` |
| `url` | Kafelek otwiera przeglądarkę (`url` w `component.json`) |

**Legenda kolumn:** `hidden` = ukryty na siatce klasycznego launchera (`hidden: true` w JSON).

### Administracja produktu

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `dodajobraz` | Dodaj obraz | subprocess | `data/` | `gui.py`, `__main__.py` | `fx_rates`, `task_notify`, `price_change_dialog`; legacy lokalny toast — nowy kod → `show_toast` |
| `aktualizujopis` | Aktualizuj opis | subprocess | — | `gui.py`, `__main__.py` | Shopify + parser JSON LLM |
| `zmienceny` | Zmień ceny | subprocess | — | `gui.py`, `__main__.py` | Masowa aktualizacja cen wariantów |
| `wyborszablonu` | Wybór szablonu produktu | subprocess | — | `gui.py`, `__main__.py` | Szablon wariantów typu Obraz |
| `zmietytuly` | Zmień tytuły | subprocess | — | `gui.py`, `__main__.py` | Generator promptu (7 języków) |
| `tytulyai` | Tytuły AI (Gemini) | subprocess | `data/` | `gui.py`, `__main__.py`, `storage.py` | `gemini_client` |
| `nazwijobraz` | Nazwij obraz | subprocess | — | `gui.py`, `__main__.py` | Wzorzec atomic save: `disk_cache.py` |
| `pobierzobraz` | Pobierz obraz | subprocess | — | `gui.py`, `__main__.py` | IIIF z muzeów |
| `squoosh` | Squoosh WebP | subprocess | — | `gui.py`, `__main__.py` | Kolejka → WebP |
| `print_optimize` | Optymalizacja druku | subprocess | `data/` | `gui.py`, `__main__.py` | Gemini + korekcja pod druk |
| `mockup` | Mock-up | subprocess | `data/` | `gui.py`, `__main__.py` | **Mockup katalogowy** — ≠ mockup klienta (motyw + Worker) |
| `infoplikow` | Informacje o plikach | subprocess | — | `gui.py`, `__main__.py` | Podgląd galerii Shopify |
| `przedpo` | Przed/Po | subprocess | — | `gui.py`, `__main__.py`, `service.py` | Wgranie „przed”; „po” z Shopify |
| `kolaz` | Kreator kolaży | subprocess | `data/` | `gui.py`, `__main__.py`, `service.py` | DnD (`tkdnd_safe`); sekcja launchera „Inne” |

### Administracja strony (theme / inline)

Większość deleguje do [`theme_page_editor/bootstrap.py`](../Komponenty/_shared/theme_page_editor/bootstrap.py) (`build_page_ui`).

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `wzorzecszablonu` | Wzorzec szablonu | inline | — | `view.py`, `gui.py`, `__main__.py`, `service.py` | Szablon PDP hurtowo |
| `stronaproduktu` | Strona produktu | inline | — | `view.py`, `gui.py`, `__main__.py`, `service.py` | PDP v3 mini-strony |
| `karuzela` | Karuzela | inline | `data/` | `view.py`, `gui.py`, `service.py` | Sekcja „Wybrane dzieła” |
| `submenukatalog` | Submenu katalog | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Animowana lista artystów |
| `tldobio` | Tło do Bio | inline | `data/` | `view.py`, `gui.py`, `service.py` | Metafield tła BIO |
| `stronaglowna` | Strona główna | inline | `data/` | `view.py`, `gui.py`, `service.py` | `templates/index.json`; Studio save pattern |
| `gicleeframe` | Giclée Frame | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | `page.giclee-frame.json` |
| `wlasnafotografia` | Własna fotografia | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Szablon własnej fotografii |
| `katalog` | Katalog | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Strony kolekcji artystów |
| `wspolpraca` | Współpraca | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | `page.wspolpraca.json` |
| `filozofiamarki` | Filozofia marki | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | `page.filozofia-marki.json` |
| `kontakt` | Kontakt | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Hero + formularz |
| `stronablogu` | Strona blogu | inline | — | `view.py`, `gui.py`, `__main__.py` | `templates/blog.json` |
| `faq` | FAQ | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Accordion FAQ |
| `losujobraz` | Losuj Obraz | inline | `data/` | `view.py`, `gui.py`, `__main__.py` | Etykiety sekcji WebGL |

### Zamówienia i produkcja

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `obrazy` | Obrazy | inline | — | `view.py` | `tile_grid` — skróty do folderów |
| `produkcja` | Produkcja | inline | `dane/` | `view.py` | `tree_sort`; status zamówień |
| `passepartout` | Passe-partout | inline | — | `view.py` | Kalkulator Allegro |
| `kalkulacja` | Kalkulator kosztów | inline | `data/` | `view.py` | Koszty ramek, marże |

### Finanse

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `finanse` | Księgowość (hub) | inline | — | `view.py` | Hub → `finance_navigation` do modułów hidden |
| `kpir` | JDG — KPiR | inline **hidden** | `dane/` | `view.py`, `storage.py` | Pełny moduł KPiR |
| `dnr` | Działalność nierejestrowana | inline **hidden** | `dane/` | `view.py`, `storage.py` | Limit DNR |
| `dokumentysprzedazy` | Dokumenty sprzedaży | inline **hidden** | `dane/` | `view.py`, `storage.py` | Faktury PDF |
| `ksiegowosc` | Księgowość (legacy) | inline **hidden** | — | `view.py` | Stary hub — preferuj `finanse` |
| `cenyMarketing` | Ceny w marketingu | inline | — | `view.py` | P&L, LTV/CAC, promocje |

### Marketing i content

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `blog` | Blog | inline | `data/` | `view.py`, `storage.py` | Posty Shopify 7 jęz. |
| `socialmedia` | Social Media | inline | `data/` | `view.py`, `storage.py` | IG/FB + podmoduł `cykl/` |
| `zadania` | Zadania | inline | `data/` | `view.py`, `storage.py` | Planer marketingowy LLM |
| `analytics` | Analiza ruchu | inline | `dane/` | `view.py`, `storage.py` | Shopify analytics |

### Narzędzia, system, integracje

| Folder | Nazwa UI | Tryb | Config | Ważne pliki | Reuse / uwagi |
|--------|----------|------|--------|-------------|---------------|
| `limity` | Limity | inline | — | `view.py` | Zużycie R2, Resend, SerpAPI… |
| `planer` | Planer | inline | `dane/` | `view.py` | Zadania wewnętrzne |
| `notatnik` | Notatnik | subprocess | — | `gui.py`, `__main__.py` | Notatki Markdown |
| `segregatorplikow` | Segregator plików | subprocess | `data/` | `gui.py`, `storage.py`, `move_service.py` | DnD (`tkdnd_safe`); kafelki folderów; config lokalny `data/tiles.json` (gitignore, szablon `tiles.example.json`); `shutil.move` od razu bez konfliktu nazw, podgląd przy duplikacie |
| `bazapromptow` | Baza Promptów | subprocess | `data/` | `gui.py`, `storage.py` | Schowek promptów |
| `wybortrybu` | Wybór Trybu | subprocess | `data/` | `gui.py`, `data_loader.py`, `prompt_builder.py`, `knowledge_sources.py`, `__main__.py` | Katalog GPT **v38** (schema v2): 17 formalnych trybów, premium cards UI, wybieralne profile Veo, auto Shopify Snapshot, zwijany generator, read-only kontrola źródeł |
| `integracjagpt` | Integracja z GPT | subprocess | `data/` | `gui.py`, `__main__.py` | Mirror, ZIP knowledge, push |
| `stronyzobrazami` | Strony z obrazami | subprocess | `data/` | `gui.py`, `storage.py` | Muzea + wyszukiwarka |
| `stronydozycia` | Strony do użycia | subprocess | `data/` | `gui.py`, `storage.py` | Zapisane linki |
| `poczta` | Poczta firmowa | inline | `data/` | `view.py` | IMAP Gmail |
| `sklep` | Giclee Art Sklep | **url** | — | tylko `component.json` | Otwiera gicleeart.eu |
| `pushe` | Pushe | subprocess | — | `gui.py`, `service.py` | Push motywu + monorepo GitHub |
| `debugowanie` | Debugowanie | subprocess | — | `gui.py`, `__main__.py` | Sekcje debug → schowek |

### Poza rejestracją

| Folder | Status |
|--------|--------|
| `stronaglownav2` | Pusty placeholder — **brak** `component.json`, nie jest wykrywany |
| `_shared` | Biblioteka współdzielona — **nie** jest komponentem |

Dokumentacja biznesowa: [`komponenty/README.md`](komponenty/README.md)

---

## Rejestracja komponentów

**Źródło prawdy:** [`giclee_app/component_loader.py`](../giclee_app/component_loader.py) — `discover_components()`.

**Brak centralnego pliku rejestru** — discovery oparte na filesystem.

### Minimalny zestaw

| Tryb | Wymagane | Opcjonalne |
|------|----------|------------|
| `subprocess` (domyślny) | `__main__.py` | `component.json`, `gui.py`, `requirements.txt` |
| `inline` | `view.py` z `build_view(parent, on_back)` | `component.json` z `"mode": "inline"` |
| `url` | `component.json` z `"url"` | — |

### `component.json` — typowe pola

`name`, `description`, `icon`, `color`, `order`, `mode`, `url`, `hidden`, `inline_width`, `inline_height`, `inline_min_width`, `inline_min_height`, `availability`, `stability`

Checklist: [`component-loader.md`](../giclee_app/docs/component-loader.md)

### Profile i kanały komponentów

| Pole | Dozwolone wartości | Zachowanie bez pola |
|------|---------------------|---------------------|
| `availability` | `classic`, `studio_preview`, `studio` | Dostępny we wszystkich profilach |
| `stability` | `stable`, `preview`, `experimental`, `legacy` | `stable` |

Produkcyjne Studio wymaga jednocześnie `availability: studio` i `stability: stable`.
Preview może pokazywać wszystkie kanały. Szczegóły: [`component-channels.md`](../giclee_app/docs/component-channels.md) i [`studio-production-profile.md`](../giclee_app/docs/studio-production-profile.md).

### Gdzie dopisać poza folderem komponentu

| Cel | Plik |
|-----|------|
| Sekcja klasycznego launchera (domyślna) | [`giclee_app/launcher_layout.py`](../giclee_app/launcher_layout.py) → `DEFAULT_SECTIONS` |
| Personalizacja użytkownika | [`giclee_app/data/launcher_layout.json`](../giclee_app/data/launcher_layout.json) |
| Kategoria Studio sidebar | [`giclee_app/data/studio_categories.json`](../giclee_app/data/studio_categories.json) |

Launcher skanuje `Komponenty/` co **~3 s** — nowy folder pojawia się automatycznie po spełnieniu wymagań trybu.

### Czego nie ruszać

- `_shared/` — nie rejestruj jako komponent
- Logika discovery w `component_loader.py` — tylko przy zmianie kontraktu trybów
- `hidden: true` — ukrywa kafelek klasyczny; moduł nadal działa (np. z huba `finanse`)

---

## Wzorce GUI

### Okna i layout

| Potrzeba | Moduł | API |
|----------|-------|-----|
| Inline shell (nagłówek + wstecz) | [`inline_view_shell.py`](../Komponenty/_shared/inline_view_shell.py) | `mount_inline_view(parent, on_back, title=..., build_content=...)` |
| Mini-siatka kafelków w inline | [`tile_grid.py`](../Komponenty/_shared/tile_grid.py) | siatka + external-first `settings.json` w roaming AppData |
| Centrowanie modala | [`window_geometry.py`](../Komponenty/_shared/window_geometry.py) | `position_toplevel_screen_center(win, w, h)` |
| Scroll myszką | [`tk_scroll.py`](../Komponenty/_shared/tk_scroll.py) | binding kółka dla Canvas |
| Theme page editor | [`theme_page_editor/`](../Komponenty/_shared/theme_page_editor/) | `bootstrap.build_page_ui()` |
| Shopify theme dev | [`theme_dev_gui.py`](../Komponenty/_shared/theme_dev_gui.py) | dialog podglądu :9292 |

### Subprocess

| Potrzeba | Moduł | API |
|----------|-------|-----|
| Uruchomienie z launchera | [`launcher_delegate.py`](../giclee_app/launcher_delegate.py) | `launch_component()`, log → `logs/<folder>.log` |
| Bez okna konsoli (Win) | [`subprocess_win.py`](../Komponenty/_shared/subprocess_win.py) | `no_console_kwargs()` → spread do `Popen`/`run` |
| Dźwięk po długim batchu | [`task_notify.py`](../Komponenty/_shared/task_notify.py) | `notify_long_task_done(root)` |

### Dialogi

| Potrzeba | Moduł | API |
|----------|-------|-----|
| Okno pomocy | [`help_dialog.py`](../Komponenty/_shared/help_dialog.py) | `show_help(parent, title=..., text=...)` |
| Podgląd dziennika akcji | [`activity_log_ui.py`](../Komponenty/_shared/activity_log_ui.py) | `open_activity_log_dialog(master, title=...)` |
| Efekty sekcji (theme) | [`page_effects_dialog.py`](../Komponenty/_shared/theme_page_editor/page_effects_dialog.py) | `open_text_effects_dialog`, `open_image_effects_dialog` |

**Konwencja modala:** `Toplevel` → `transient(parent)` → `grab_set()` → `messagebox.*(..., parent=dlg)`.

Wzorce referencyjne: `theme_page_editor/gui_shell.py`, `dodajobraz/price_change_dialog.py`, `mockup/transparent_dialog.py`.

### Toasty i powiadomienia

| Potrzeba | Moduł | API | Kiedy |
|----------|-------|-----|-------|
| Toast w oknie aplikacji | [`toast.py`](../Komponenty/_shared/toast.py) | `show_toast(parent, text, duration_ms=...)` | **Domyślny wybór** dla GUI |
| Toast systemowy (OS) | [`notifications.py`](../Komponenty/_shared/notifications.py) | `notify(title, message)` | Tło, launcher, zadania bez okna |

**Nie duplikuj:** lokalny toast w `dodajobraz/gui.py` — legacy; nowy kod → `show_toast`.

### Komunikaty błędów

- `tkinter.messagebox.showerror/showwarning/askyesno` z `parent=` ustawionym na aktywne okno
- Status w GUI: callback `set_status(text)` w wątkach batchowych
- Audyt akcji: `append_activity` (patrz [Logi](#logi))

---

## Konfiguracja lokalna

### Gdzie trzymać dane

| Wzorzec | Lokalizacja | Przykłady komponentów |
|---------|-------------|----------------------|
| `AppPath` / `data_path` / `config_path` / `cache_path` / `log_path` / `backup_path` | [`giclee_app/app_paths.py`](../giclee_app/app_paths.py) → zewnętrzne AppData, legacy tylko do odczytu | Nowe i migrowane mutable stores |
| `data/*.json` | `Komponenty/<folder>/data/` | **legacy read path**: `stronaglowna`, `bazapromptow`, `integracjagpt`, `blog` |
| `dane/*.json` | `Komponenty/<folder>/dane/` | **legacy read path**: `dnr`, `kpir`, `dokumentysprzedazy`, `produkcja` |
| `storage.py` | w folderze komponentu | `load_*` / `save_*` — wzorzec per moduł |
| `settings.json` | `%APPDATA%/GicleeArt/GicleeApp/config/Komponenty/<component>/` | `tile_grid`: external-first, legacy source-tree read-only |

`tile_grid` wyznacza stabilny klucz od najbliższego katalogu `Komponenty`.
Aktualni konsumenci `InlineTileView` to `obrazy`, `cenyMarketing` i
`ksiegowosc`. Publiczne API `load_settings(component_dir)` oraz
`save_settings(component_dir, data)` pozostaje bez zmian.

### Wzorce zapisu

| Wzorzec | Gdzie | Kiedy używać |
|---------|-------|--------------|
| AppData + legacy read fallback | [`giclee_app/app_paths.py`](../giclee_app/app_paths.py) | Mutable runtime/config/log/backups; nowe zapisy poza source checkout |
| Prosty `json.dumps` → `write_text` | większość `storage.py` | Niskie ryzyko, małe pliki legacy — migrować przez `AppPath` |
| Atomic: `.tmp` → `replace()` | [`giclee_app/app_paths.py`](../giclee_app/app_paths.py), [`nazwijobraz/disk_cache.py`](../Komponenty/nazwijobraz/disk_cache.py), [`giclee_app/studio/state.py`](../giclee_app/studio/state.py) | Crash-safe |
| Backup przed zapisem szablonu | [`theme_page_editor/service_base.py`](../Komponenty/_shared/theme_page_editor/service_base.py) | `backup_before_save()` → `index-YYYYMMDD-HHMMSS.json` |
| Studio bounded writer | [`giclee_app/studio/background_save_writer.py`](../giclee_app/studio/background_save_writer.py) | Tylko flow Studio background — patrz [`studio-save-pattern.md`](../giclee_app/docs/studio-save-pattern.md) |
| Dzienny zip wszystkich `data/` | [`backup.py`](../Komponenty/_shared/backup.py) | `run_daily_backup_if_needed()` z launchera → `%LOCALAPPDATA%\GicleeArt\GicleeApp\backups\` |

Kopie `stronaglowna`: `Komponenty/stronaglowna/data/backups/`.

---

## Logi

| Typ | Ścieżka / moduł | API / zastosowanie |
|-----|-----------------|-------------------|
| **Dziennik akcji (JSONL)** | [`activity_log.py`](../Komponenty/_shared/activity_log.py) → `%LOCALAPPDATA%\GicleeArt\GicleeApp\logs\Komponenty\_shared\activity_log.jsonl` | `append_activity(component, message, level="info", detail="")`; copy-on-first-append z legacy |
| Podgląd UI dziennika | [`activity_log_ui.py`](../Komponenty/_shared/activity_log_ui.py) | GicleeApp toolbar → „Dziennik akcji” |
| Stdout subprocess | `cursor-api/logs/<folder>.log` | [`launcher_delegate.py`](../giclee_app/launcher_delegate.py) |
| Log w GUI (wątki) | callbacki w komponencie | `enqueue_log`, `append_log`, `set_status` |

**Czego unikać:** modułu `logging` / `getLogger` — w GicleeApp nie jest standardem; nie wprowadzaj bez uzgodnienia.

**Zasada:** akcje użytkownika widoczne w UI → `append_activity`; debug techniczny subprocess → plik w `logs/`.

---

## Operacje na plikach

### Co już istnieje — używaj zamiast pisać od zera

| Potrzeba | Istniejące rozwiązanie | Uwagi |
|----------|------------------------|-------|
| **Zewnętrzne mutable paths** | [`giclee_app/app_paths.py`](../giclee_app/app_paths.py) | `AppPath`, `data_path`, `config_path`, `cache_path`, `log_path`, `backup_path`, atomic writes |
| **Drag & drop plików** | [`_shared/tkdnd_safe.py`](../Komponenty/_shared/tkdnd_safe.py) | `register_drop_target(widget, on_drop=...)`, `parse_dnd_files(event.data)`, `dnd_files_available()` |
| **Log JSONL akcji** | [`_shared/activity_log.py`](../Komponenty/_shared/activity_log.py) | `append_activity(...)` — nie twórz własnego JSONL |
| **Toast po akcji** | [`_shared/toast.py`](../Komponenty/_shared/toast.py) | `show_toast(parent, text)` |
| **Wybór folderu** | `tkinter.filedialog.askdirectory` | Wzorzec referencyjny: [`tile_grid.py`](../Komponenty/_shared/tile_grid.py) (edytor kafelków) |
| **Wybór pliku** | `filedialog.askopenfilename` / `askopenfilenames` / `asksaveasfilename` | Powszechny wzorzec w `gui.py` komponentów |
| Backup przed zapisem | `theme_page_editor/service_base.backup_before_save` | Timestampowane kopie JSON |
| Kopia załączników promptów | `bazapromptow/storage.py` | `copy_context_image`, `copy_context_file` |

### Drag & drop — szczegóły

- **Kanoniczny moduł:** `_shared/tkdnd_safe.py` — graceful fallback gdy brak `tkinterdnd2` lub embed w Studio.
- Subprocess GUI z pełnym DnD: root `TkinterDnD.Tk()` (np. `dodajobraz`, `mockup`, `kolaz`, `squoosh`).
- W Studio embed DnD może się **degradować** — `register_drop_target` obsługuje to cicho.
- **Nie duplikuj** lokalnych `_parse_dnd_files` — są legacy w `mockup/gui.py`, `kolaz/gui.py`; nowy kod → `parse_dnd_files`.

### Rozproszone operacje (brak jednego modułu)

`shutil.copy2`, `shutil.rmtree`, `Path.replace` używane bezpośrednio w:

- `theme_page_editor/service_base.py`, `features.py`
- `integracjagpt/mirror.py`, `zip_knowledge.py`
- `bazapromptow/storage.py`
- `giclee_app/studio/background_save_writer.py`

Otwarcie w Explorerze / Finderze — powtarzany wzorzec `subprocess` (`explorer /select`, `open`, `xdg-open`) w `tile_grid.py`, `nazwijobraz/gui.py` i innych — **brak wspólnego helpera**.

### Centralny `file_utils` — TODO

**Nie istnieje.** Brakuje wspólnego modułu do: bezpiecznego kopiowania, rename z konfliktem nazw, `open_in_explorer(path)`.

**Nie tworzyć ad-hoc** w nowym komponencie bez planu — albo użyj istniejących wzorców powyżej, albo zaplanuj `_shared/file_utils.py` jako osobne zadanie.

---

## Integracje GPT / ZIP

| Temat | Gdzie |
|-------|-------|
| Pliki startowe Custom GPT | `Pliki startowe dla GPT/` (poza `cursor-api/`) |
| Komponent synchronizacji | [`Komponenty/integracjagpt/`](../Komponenty/integracjagpt/) — mirror, `zip_knowledge.py`, push |
| Konfiguracja GPT | `integracjagpt/data/gpt_config.json` |

**Co wolno aktualizować:** dane komponentu, docs w `cursor-api/docs/`, ten indeks — na polecenie użytkownika.

**Czego nie robić bez osobnego polecenia:**

- generowanie ZIP-a wiedzy GPT,
- aktualizacja `GICLEE_CURSOR_MASTER_INDEX` / COMPACT / `CURRENT_APP_STATE`,
- push lustra do repo GPT.

---

## Zakończona izolacja i refaktor

Zakres stabilizacji RC1, STUDIO-ISOLATION-1 — 3 i bezpiecznej konsolidacji repozytorium został zamknięty 2026-07-16. Kanoniczny raport: [`GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md`](GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md).

Wdrożone wzorce, których nie należy tworzyć drugi raz:

- niemutowalne profile `classic`, `studio_preview`, `studio` z osobnymi namespace stanu/logów;
- availability/stability komponentów;
- bezpośrednie service wiring Theme Page Editor bez bootstrap monkey-patcha;
- conditional CSS i runtime motywu jako testowane kompozycje Liquid;
- jedno źródło wersji desktop;
- security contract, tracked-large-file guard i runtime source-write inventory;
- kontrolowany retry CI tylko dla dokładnej przejściowej awarii Tcl/Tk.

---

## Guardrails

| Zasada | Szczegół |
|--------|----------|
| Nie ruszać motywu Shopify | Przy lokalnych komponentach GicleeApp — chyba że zadanie dotyczy theme editora |
| Nie ruszać PDP / homepage / Giclée Frame | Bez wyraźnego sygnału w zadaniu |
| Mockup katalogowy ≠ mockup klienta | `Komponenty/mockup/` vs motyw + Worker |
| Nie commitować bezpośrednio do `master` | Branch zadaniowy → PR → exact-head CI → squash merge |
| Nie generować ZIP | Bez polecenia użytkownika |
| Nie dublować helperów | Sprawdź `_shared/` i ten indeks przed nowym kodem |
| `_shared` nie jest komponentem | Importuj moduły, nie kopiuj plików |

---

## TODO / Braki

| Brak | Status | Uwaga |
|------|--------|-------|
| Centralny `_shared/file_utils.py` | **TODO** | copy/move/rename/open_in_explorer — nie implementować przy okazji innego zadania |
| Wspólny `open_in_explorer(path)` | TODO | Wzorzec powtarzany w 5+ miejscach |
| Ujednolicenie parserów DnD | TODO niski | Zastąpić lokalne kopie → `tkdnd_safe.parse_dnd_files` |
| Legacy toast w `dodajobraz/gui.py` | TODO kosmetyka | Migracja na `show_toast` |
| `stronaglownav2` | placeholder | Pusty folder — implementacja lub usunięcie |
| Moduł `logging` stdlib | świadoma decyzja | Używamy `activity_log` + pliki `logs/` |
| Ten indeks w plikach startowych GPT | poza scope | Do dopisania w MASTER_INDEX / COMPACT na osobne polecenie |

---

## Powiązana dokumentacja

| Plik | Rola |
|------|------|
| [`komponenty/README.md`](komponenty/README.md) | Indeks docs biznesowych per komponent |
| [`shared.md`](shared.md) | Szczegóły modułów `_shared` |
| [`../giclee_app/docs/component-loader.md`](../giclee_app/docs/component-loader.md) | Discovery, checklist nowego komponentu |
| [`../giclee_app/docs/launcher.md`](../giclee_app/docs/launcher.md) | Sekcje kafelków, toolbar |
| [`../giclee_app/docs/studio-save-pattern.md`](../giclee_app/docs/studio-save-pattern.md) | Wzorzec zapisu Studio |
| [`../giclee_app/docs/studio-preview.md`](../giclee_app/docs/studio-preview.md) | Shell Studio Preview (CTk) |
| [`../giclee_app/docs/component-channels.md`](../giclee_app/docs/component-channels.md) | Availability i stability komponentów |
| [`../giclee_app/docs/studio-production-profile.md`](../giclee_app/docs/studio-production-profile.md) | Produkcyjny profil Giclée Studio |
| [`GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md`](GICLEEAPP_REFACTOR_COMPLETION_2026-07-16.md) | Zamknięcie izolacji i refaktoru |
| [`versioning.md`](versioning.md) | Kanoniczne źródło wersji desktop |
| [`theme-liquid-runtime.md`](theme-liquid-runtime.md) | Kompozycja runtime motywu |
| [`tracked-large-files.md`](tracked-large-files.md) | Guard dużych plików w historii Git |
| [`../../SECURITY.md`](../../SECURITY.md) | Security i secret-handling policy |
