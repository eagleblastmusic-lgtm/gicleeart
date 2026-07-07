# GICLÉE FRAME™ — planning shell (Studio F1 + F2)

Hub: [`admin-components-strategy.md`](admin-components-strategy.md) · [`studio-v2-workflows.md`](studio-v2-workflows.md) · [`studio-save-pattern.md`](studio-save-pattern.md) · legacy: [`../../docs/komponenty/gicleeframe.md`](../../docs/komponenty/gicleeframe.md)

**Stan:** app planning component **ready** @ Studio v1.40.8 · page editor workflow **ready (F2.1)** · **F2.2 layout polish** · **F2.2.1 visual hierarchy** · **F2.2.2 premium visual workbench** · **F2.2.3 first-screen composition** · **F2.2.4 premium visual language** · **F2.2.5 section workbench** · **F2.2.6 child layer navigation** · Shopify **not started** · writer/save **blocked**

---

## 1. Cel

Panel planistyczno-preview dla premium komponentu strony **GICLÉE FRAME™** — znak technologii ramy / podpis systemu / premium label / section label / hero label.

**F2:** uporządkowana mapa całej strony `/pages/giclee-frame` — sekcje, separatory, grafiki, teksty, kolejność, statusy — z edycją RAM (bez zapisu).

**F2.1:** workflow edytora strony — top bar (wariant/draft), trigger sekcji w edytorze, edytor typu-aware, jawny przycisk „Uaktualnij RAM draft”, dry-run i readiness pod spodem.

Nie zastępuje legacy writera (`Komponenty/gicleeframe` → `theme_page_editor`). W Studio karta `gicleeframe` otwiera **wyłącznie** ten planning shell.

---

## 2. Guardrails

| Reguła | Szczegół |
|--------|----------|
| Importy | **Zero** `Komponenty.*` w `giclee_app/studio/gicleeframe_*` i `ui/gicleeframe_view.py` |
| Zapis | **Zero** Save / Zapisz / Zastosuj / `write_text` |
| Shopify | **Zero** sync / deploy / upload |
| Runtime | **Nie** mutować `Komponenty/gicleeframe/data/*` |
| Inventory | Bounded read: `manifest.json` + `page.giclee-frame.json` + `registry.py` (regex etykiet) |
| Legacy | Klasyczny launcher → stary inline writer (bez zmian) |
| Studio | Brak przycisku „Legacy editor” |

Disclaimer F2: **„Zmiany są tylko lokalnym draftem w pamięci — nic nie zapisano.”**

---

## 3. Pliki

| Plik | Rola |
|------|------|
| `studio/gicleeframe_brief.py` | Statyczny brief: warianty, zasady wizualne/motion, placement |
| `studio/gicleeframe_draft_state.py` | Draft w RAM (wariant + strefa) — F1 marka |
| `studio/gicleeframe_dry_run.py` | Opis przyszłego outputu motywu (tekst) — F1 |
| `studio/gicleeframe_readiness.py` | Status gotowości marki + strony, `save_ready` zawsze False |
| `studio/gicleeframe_page_inventory.py` | **F2** — read-only inventory strony (rozwinięcie media → elementy) |
| `studio/gicleeframe_page_draft.py` | **F2** — RAM patchy elementów strony |
| `studio/gicleeframe_page_settings.py` | **F2.1** — specyfikacja pól `settings` sekcji (divider / media) |
| `studio/gicleeframe_page_dry_run.py` | **F2** — dry-run struktury + guardrails |
| `ui/gicleeframe_view.py` | Widok CTk: **F2.1 edytor strony** (top bar / trigger / edytor) + F1 komponent marki |
| `launcher_studio.py` | Routing: `gicleeframe` → `GicleeFrameView` |

---

## 4. Warianty koncepcyjne (F1 marka)

- `default_dark` — default / dark
- `light_inverted` — light / inverted
- `compact` — compact
- `section_label` — section-label
- `hero_label` — hero-label

---

## 5. Wejście użytkownika

### F2.1 — Edytor strony (priorytet)

1. Studio → **Strona / Motyw** → karta **Giclée Frame**
2. **Górny pasek:** wariant źródłowy (`gf1`), plik `page.giclee-frame.json`, **wariant roboczy RAM** (`Wariant 1`, `Wariant 2`, …), licznik zmian w aktywnym wariancie, status `RAM-only · nic nie zapisano`
3. **Wybór sekcji** — trigger w nagłówku edytora (`Separator 1 ▾`) + popup z rytmem strony; po rozwinięciu edycji dzieci sekcji media: Nagłówek, Tekst, Grafika
4. **Edytor sekcji** (prawa kolumna) — formularz zależny od typu; patch **tylko** po „Uaktualnij RAM draft”
5. Akcje RAM wariantów: **Dodaj wariant RAM**, **Duplikuj aktualny wariant**, **Zmień nazwę wariantu**, **Wyczyść wariant RAM**, **Odśwież inventory**
6. **Sprawdź strukturę (dry-run)** — wariant źródłowy + aktywny wariant roboczy, zmienione elementy, „nic nie zapisano”; porównanie wariantów = przełączanie i ocena podglądu (bez diffu w aplikacji)
7. Readiness strony pod edytorem

F2.1 **nie zapisuje** do plików. Warianty robocze i patche są wyłącznie w RAM. Domyślnie `Wariant 1`; można dodać/duplikować/przełączać warianty bez zapisu do `Komponenty/*`.

### F2 — Inventory (pod spodem logiki F2.1)

Bounded read z wariantu aktywnego w manifest. Licznik `order[]` ≠ liczba elementów po rozwinięciu media.

### F1 — Komponent marki (poniżej, zwinięty domyślnie)

1. Wybór wariantu koncepcyjnego + opcjonalna strefa
2. **Sprawdź plan (dry-run)** + readiness marki
3. **Wyczyść wybór** — reset planu marki

---

---

## 6. F2.2 — Studio cockpit layout polish (v1.40.2)

| Element | Szczegół |
|---------|----------|
| Układ | 3-kolumnowy desktop: **Sekcje strony** · **Edytor sekcji** · **Kontrola** (podgląd struktury, readiness, bezpieczeństwo) |
| Kontekst | Pasek u góry: tytuł, chip RAM-only, źródło `gf1 (dev) · page.giclee-frame.json`, wariant roboczy, licznik zmian, status „Nic nie zapisano” |
| Primary | Jedyna akcja accent: **Uaktualnij wariant RAM** + microcopy „Tylko pamięć · nic nie zapisuje” |
| RAM-only | Bez writera, bez zapisu do pliku, bez F3/F4/Shopify |
| Responsive | Desktop 3-kolumnowy; wąski fallback — osobny F2.2.1 jeśli potrzebny |

---

## 7. F2.2.1 — visual hierarchy pass (v1.40.3)

| Element | Szczegół |
|---------|----------|
| Workbench | Edytor środkowy: grupy ustawień w kartach (`Linia`, `Układ`, `Styl`, `Notatka`) w siatce 2-kolumnowej; max szerokość formularza ~680 px |
| Kontekst | Jeden kompaktowy pasek (chip RAM, źródło, wariant, zmiany, status) — bez powielania tytułu z breadcrumb |
| Command bar | Jedna powierzchnia operacji zamiast ramek w ramkach |
| Kontrola | Empty state dry-run, badge readiness, checklista bezpieczeństwa |
| RAM-only | Bez writera, F3/F4, Shopify — tylko polish UI |

---

## 7b. F2.2.2 — premium visual workbench pass (v1.40.4)

| Element | Szczegół |
|---------|----------|
| Identity card | Karta sekcji z mini podglądem separatora (`Podgląd ustawień`) |
| Karty ustawień | `CardBg`, bez ramek; pola w układzie pionowym |
| Action dock | `Uaktualnij wariant RAM` + microcopy w jednej powierzchni |
| Nawigacja | Lista sekcji z pill badges; mniej ramek w całym panelu |
| Status stack | Prawa kolumna: struktura + readiness pill + checklista bezpieczeństwa |
| RAM-only | Bez writera, F3/F4, Shopify — tylko polish UI |

---

## 7c. F2.2.3 — first-screen premium composition fix (v1.40.5)

| Element | Szczegół |
|---------|----------|
| First screen | Główna akcja RAM w identity card (above the fold) |
| Nawigacja | Szersza lista sekcji (320 px), ellipsize długich nazw |
| Hero preview | Podgląd separatora z pill „RAM preview”, feedback width/thickness |
| Formularz | Jaśniejsze menu (`CardBg`), większy oddech w gridzie ustawień |
| RAM-only | Bez writera, F3/F4, Shopify — tylko polish UI |

---

## 7d. F2.2.4 — premium visual language pass (v1.40.6)

| Element | Szczegół |
|---------|----------|
| Visual tokens | Lokalne tokeny `_GF_*` tylko dla GICLÉE FRAME |
| Preview | Mini artboard z papierem/matą i linią separatora |
| Nawigacja | Numerowane rowy sekcji + subtelny typ sekcji |
| Forms | Cieplejsze pola i setting cards |
| RAM-only | Bez writera, F3/F4, Shopify — tylko UI polish |

---

## 7e. F2.2.5 — section workbench / component tiles pass (v1.40.7)

| Element | Szczegół |
|---------|----------|
| Preview | Typ-zależny preview: divider / media section / legacy / child |
| Warstwy | Duże kafle dzieci sekcji zamiast małych przycisków |
| Workbench | Środkowy edytor bardziej jak narzędzie projektowe |
| Notes | Notatka mniej dominuje pierwszy ekran |
| RAM-only | Bez writera, F3/F4, Shopify — tylko UI polish |

---

## 7f. F2.2.6 — child editor / layer navigation + premium color polish (v1.40.8)

| Element | Szczegół |
|---------|----------|
| Layer nav | Stała nawigacja warstw sekcji także po wejściu w dziecko |
| Image child | Preview grafiki jako obiekt edytorski |
| Color | Cieplejsza lokalna paleta atelier `_GF_*` |
| Forms | `Źródło grafiki`, cieplejsze pola i mniej techniczny kontrast |
| RAM-only | Bez writera, F3/F4, Shopify — tylko UI polish |

---

## 8. F2.1 — editor workflow polish

| Element | Szczegół |
|---------|----------|
| Układ | Top bar / trigger sekcji w nagłówku edytora / edytor typu-aware |
| RAM draft | Jeden lub wiele wariantów roboczych w pamięci; patche per wariant; przełączanie bez diffu |
| Zablokowane | Zapis do plików, writer, synchronizacja/wdrożenie, mutacja `Komponenty/*` |
| F3 | Lokalny zapis draftu do pliku — po akceptacji |
| F4 | Bounded writer do `page.giclee-frame.json` — po akceptacji |

---

## 9. F2.1 jako wzorzec dla przyszłych edytorów strony

**Decyzja produktowa (Studio v1.40.1):** workflow F2.1 GICLÉE FRAME™ ustanawia docelowy wzorzec **`Studio Page Component Editor Pattern`** dla wszystkich komponentów GicleeApp Studio związanych z budowaniem i projektowaniem strony (Kontakt, FAQ, Filozofia marki, Blog, …).

**Nie migrujemy innych modułów w tej fazie** — Strona główna, Katalog, tło i pozostałe komponenty pozostają bez zmian do osobnej akceptacji.

Hub strategii: [`admin-components-strategy.md`](admin-components-strategy.md) · wzorzec zapisany tutaj jako referencja implementacyjna Giclée Frame.

### Studio Page Component Editor Pattern

| # | Element | Zasada |
|---|---------|--------|
| 1 | **Wariant źródłowy (read-only)** | Aktywny wariant JSON / inventory z manifestu — zero mutacji źródła na etapie planowania |
| 2 | **Warianty robocze RAM** | `Wariant 1`, `Wariant 2`, … — dodawanie (przycisk), duplikacja, zmiana nazwy; izolowane patche per wariant; porównanie = przełączanie wariantu + podgląd (bez diffu w UI) |
| 3 | **Wybór sekcji / struktury** | Trigger lub lista; rytm strony od góry do dołu; separatory jako elementy; sekcje nadrzędne; tekst / grafika / nagłówek / settings jako części sekcji |
| 4 | **Edytor typu-aware** | Osobne pola dla separatora, sekcji media, tekstu, grafiki, tła/settings — widoczność pól zależna od typu elementu |
| 5 | **Settings jako RAM patch** | Ustawienia z JSON jako inventory; zmiany tylko do RAM (`patch.settings`); brak zapisu do pliku |
| 6 | **Reorder jako RAM patch** | Drag/drop zmienia tylko `order` w RAM; brak zapisu do JSON |
| 7 | **Dry-run** | Aktywny wariant roboczy, liczba zmian, podgląd tego co zmieniłby writer; komunikat: nic nie zapisano |
| 8 | **Readiness** | RAM editor ready · local draft persistence `not_started` · writer blocked · sync/deploy blocked · runtime mutation blocked |
| 9 | **Guardrails** | Brak Save/Zapisz/Zastosuj na etapie RAM; brak Shopify/sync/deploy; brak mutacji `Komponenty/*`; legacy writery poza Studio lub ukryte do przebudowy |
| 10 | **Późniejsze fazy** | **F3** lokalny zapis draftu · **F4** bounded writer + backup/undo · **F5** preview/review jakości · **F5.5** Shopify/sync/deploy po osobnej akceptacji |

Implementacja referencyjna: ten moduł (`gicleeframe_page_*`, `gicleeframe_view.py`). Kolejne komponenty strony powinny **adaptować ten schemat**, nie kopiować ad hoc UI z legacy writerów.

---

## 10. Backlog (nie w tej fazie)

| Faza | Zakres |
|------|--------|
| **F2b** | Scale / motion / contrast / implementation spec — odłożone |
| **F3** | Lokalny zapis draftu RAM |
| **F4** | Bounded writer do `data/variants/{variant}/page.giclee-frame.json` |
| **F5.5** | Synchronizacja/wdrożenie — osobna akceptacja produktowa |

**Gotowe do kolejnej fazy: po akceptacji F2.1.**

---

## 11. Performance — responsive section selection (Studio v1.41.1)

Wybór sekcji w `gicleeframe_view.py` jest dwuetapowy:

| Etap | Opóźnienie | Zachowanie |
|------|------------|------------|
| **Immediate** | 0 ms | highlight wiersza, trigger, subtitle „Ładowanie: …”, anulowanie poprzednich jobów |
| **Deferred populate** | 16 ms (`_GF_SELECT_POPULATE_DEFER_MS`) | pełny `_populate_editor()` z guardem `_selection_generation` |
| **Stable page context** | 140 ms (`_GF_PAGE_CONTEXT_STABLE_DEFER_MS`) | `_populate_page_context_progressive` tylko gdy wybór się ustabilizował |

Lista sekcji **domyślnie nie zwija się** po kliknięciu wiersza (szybkie przechodzenie po strukturze). Legacy/debug: `$env:GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK="1"`.

Dropdown sekcji reużywa istniejących wierszy (`section_dropdown.rows_reused`) zamiast przebudowywać listę przy każdym otwarciu.

Logi perf (`GICLEE_STUDIO_PERF=1`): `select_element.immediate_ready`, `populate_editor.deferred`, `populate_editor.deferred_stale`, `page_context.stable_defer_stale`.
