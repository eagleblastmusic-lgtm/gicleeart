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
| `ui/gicleeframe_view_models.py` | **GF-M1** — czyste kontrakty widoku (dataclass + helpery tekstowe, bez UI) |
| `ui/gicleeframe_view_primitives.py` | **GF-M2** — bezstanowe prymitywy UI i lokalne tokeny wizualne |
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

---

## 12. GF-M1 — Pure View Contracts Extraction

**Cel:** pierwszy, najmniejszy krok modularizacji `GicleeFrameView` — ekstrakcja czystych kontraktów widoku do osobnego modułu bez zmiany zachowania.

### Przeniesione symbole

| Symbol | Nowy moduł |
|--------|------------|
| `PageContextRowSpec` | `ui/gicleeframe_view_models.py` |
| `SectionVisualCacheEntry` | `ui/gicleeframe_view_models.py` |
| `_ellipsize` | `ui/gicleeframe_view_models.py` |
| `_section_kind_copy` | `ui/gicleeframe_view_models.py` |

### Gwarancje GF-M1

- **Zero** zmian behavior / layout / performance / timingów / schedulerów
- **Zero** zmian RAM draft, writera, zapisu do plików motywu, Shopify sync/deploy/mutation
- Re-eksport przez `gicleeframe_view.py` zachowany — `from giclee_app.ui.gicleeframe_view import SectionVisualCacheEntry` nadal działa
- Moduł models importuje wyłącznie `dataclass`, `PageSettingField`, `MergedPageElement` — bez tkinter/customtkinter/Komponenty/I/O/sieci

### Dalsze etapy

Kolejne kroki modularizacji (`GF-M2+`) — osobne PR-y. **GF-M1 nie uruchamia F3/F4 ani writera.**

---

## 13. GF-M2 — Stateless UI Primitives Extraction

**Cel:** drugi krok modularizacji `GicleeFrameView` — ekstrakcja bezstanowych prymitywów UI i lokalnych tokenów wizualnych do osobnego modułu bez zmiany zachowania ani wyglądu.

### Przeniesione tokeny (19)

`_BTN_HEIGHT`, `_CARD_PAD_X`, `_CARD_PAD_Y`, `_GF_BG`, `_GF_PANEL`, `_GF_CARD`, `_GF_CARD_SOFT`, `_GF_FIELD`, `_GF_FIELD_HOVER`, `_GF_BORDER`, `_GF_BORDER_WARM`, `_GF_GOLD_SOFT`, `_GF_GOLD`, `_GF_MUTED`, `_GF_PREVIEW_BG`, `_GF_PREVIEW_PAPER`, `_GF_PREVIEW_MAT`, `_GF_SUCCESS`, `_GF_DANGER`

### Przeniesione funkcje (15)

`_f2_entry_kwargs`, `_make_surface`, `_make_card`, `_make_gf_card`, `_make_section_caption`, `_make_card_title`, `_make_section_title`, `_make_status_pill`, `_make_pill`, `_make_empty_state`, `_build_safety_row`, `_make_secondary_button`, `_make_primary_button`, `_f2_menu_kwargs`, `_element_pill_colors`

### Gwarancje GF-M2

- **Zero** zmian UI, layoutu, tekstów, kolorów, wymiarów, timingów, schedulerów, performance lane i telemetry
- **Zero** zmian RAM draft, writera, zapisu do plików motywu, Shopify sync/deploy/mutation
- Re-eksport przez `gicleeframe_view.py` zachowany — `from giclee_app.ui.gicleeframe_view import _make_gf_card, _GF_PANEL` nadal działa i wskazuje ten sam obiekt co w `gicleeframe_view_primitives`
- Moduł primitives importuje wyłącznie `Callable`, `customtkinter`, `theme` — bez os/sys/time/tkinter/Komponenty/I/O/sieci/subprocess
- **GF-M2 nie uruchamia F3/F4 ani writera.**

---

## 14. GF-M3 — F1 Brand Panel Extraction

**Status:** zakończone.

**Cel:** wydzielenie panelu planowania marki **F1** (RAM-only) z `ui/gicleeframe_view.py` do osobnego modułu, bez zmiany UI/tekstu/layoutu oraz bez naruszania lifecycle, schedulerów, telemetry i selection/performance lane hosta.

### Wynik

- **Panel F1** przeniesiony do `ui/gicleeframe_view_brand.py` jako `GicleeFrameBrandPanelMixin`.
- **Mixin nie posiada lifecycle** ani `__init__` i **nie dziedziczy** po widżecie Tk.
- Host `GicleeFrameView` nadal posiada:
  - adapter expand/collapse `_toggle_f1_section` (w tym event `studio.gicleeframe.f1.build_on_expand`),
  - wspólny renderer readiness `_pack_readiness_row`.
- **Nota historyczna (GF-M7):** renderer pozostawał w hoście do GF-M7; ownership przeniesiono do `GicleeFrameReadinessRowMixin`.
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

---

## 15. GF-M4 — F2 Page Readiness Panel Extraction

**Status:** zakończone — MRO zintegrowany.

**Cel:** wydzielenie panelu readiness strony **F2** (RAM-only) z `ui/gicleeframe_view.py` do osobnego modułu, bez zmiany UI/tekstu/layoutu oraz bez naruszania lifecycle, schedulerów, telemetry i selection/performance lane hosta.

### Wynik

- **Panel readiness strony** przeniesiony do `ui/gicleeframe_view_page_readiness.py` jako `GicleeFramePageReadinessMixin`.
- **Mixin nie posiada lifecycle** ani `__init__` i **nie dziedziczy** po widżecie Tk.
- Host `GicleeFrameView` dziedziczy `GicleeFrameBrandPanelMixin` i `GicleeFramePageReadinessMixin` przed `ctk.CTkScrollableFrame`.
- Host nadal posiada:
  - kompozycję kolumny kontrolnej `_build_control_column`,
  - wspólny renderer readiness `_pack_readiness_row`.
- **Nota historyczna (GF-M7):** renderer pozostawał w hoście do GF-M7; ownership przeniesiono do `GicleeFrameReadinessRowMixin`.
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

---

## 16. GF-M5 — F2 Structure Dry-Run Panel Extraction

**Status:** zakończone — MRO zintegrowany.

**Cel:** wydzielenie panelu structure dry-run **F2** (RAM-only) z `ui/gicleeframe_view.py` do osobnego modułu, bez zmiany UI/tekstu/layoutu oraz bez naruszania lifecycle, schedulerów, telemetry i selection/performance lane hosta.

### Wynik

- **Panel structure dry-run** przeniesiony do `ui/gicleeframe_view_structure_dry_run.py` jako `GicleeFrameStructureDryRunMixin`.
- **Mixin nie posiada lifecycle** ani `__init__` i **nie dziedziczy** po widżecie Tk.
- Host `GicleeFrameView` dziedziczy `GicleeFrameBrandPanelMixin`, `GicleeFramePageReadinessMixin` i `GicleeFrameStructureDryRunMixin` przed `ctk.CTkScrollableFrame`.
- Przeniesiono dokładnie trzy metody: `_build_control_structure_card`, `_reset_structure_dry_run_display`, `_run_structure_dry_run`.
- Layout token `_STRUCTURE_DRY_RUN_WRAPLENGTH = 292` pozostaje w mixin module; `_CONTROL_COL_MINSIZE` pozostaje w hoście.
- Host nadal posiada:
  - kompozycję kolumny kontrolnej `_build_control_column` (structure → readiness → safety),
  - implementację inventory `_refresh_inventory`,
  - wspólny renderer readiness `_pack_readiness_row`,
  - etykietę command bar `CHECK_STRUCTURE_LABEL`.
- **Nota historyczna (GF-M7):** renderer pozostawał w hoście do GF-M7; ownership przeniesiono do `GicleeFrameReadinessRowMixin`.
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

### Dalsze etapy

Kolejne metody klasy `GicleeFrameView` pozostają zakresem **GF-M9+** — osobne PR-y.

---

## 17. GF-M6 — F2 Safety Card Extraction

**Status:** zakończone — MRO zintegrowany.

**Cel:** wydzielenie statycznej karty bezpieczeństwa **F2** (RAM-only) z `ui/gicleeframe_view.py` do osobnego modułu, bez zmiany UI/tekstu/layoutu oraz bez naruszania lifecycle, schedulerów, telemetry i selection/performance lane hosta.

### Wynik

- **Karta safety** przeniesiona do `ui/gicleeframe_view_safety.py` jako `GicleeFrameSafetyCardMixin`.
- **Mixin nie posiada lifecycle** ani `__init__` i **nie dziedziczy** po widżecie Tk.
- Przeniesiono dokładnie jedną metodę: `_build_safety_card`.
- Moduł safety jest właścicielem `_SAFETY_TITLE`, `_SAFETY_CHECKLIST` i `_SAFETY_ROW_WRAPLENGTH = 276`.
- Host `GicleeFrameView` dziedziczy `GicleeFrameBrandPanelMixin`, `GicleeFramePageReadinessMixin`, `GicleeFrameStructureDryRunMixin` i `GicleeFrameSafetyCardMixin` przed `ctk.CTkScrollableFrame`.
- Host nadal posiada:
  - kompozycję kolumny kontrolnej `_build_control_column` (structure → readiness → safety),
  - token layoutu `_CONTROL_COL_MINSIZE`,
  - implementację inventory `_refresh_inventory`,
  - wspólny renderer readiness `_pack_readiness_row`.
- **Nota historyczna (GF-M7):** renderer pozostawał w hoście do GF-M7; ownership przeniesiono do `GicleeFrameReadinessRowMixin`.
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

### Dalsze etapy

Kolejne metody klasy `GicleeFrameView` pozostają zakresem **GF-M9+** — osobne PR-y.

---

## 18. GF-M7 — Shared Readiness Row Renderer Extraction

**Status:** zakończone — MRO zintegrowany.

**Cel:** wydzielenie wspólnego renderera wiersza readiness używanego przez F1 Brand Panel i F2 Page Readiness Panel, bez zmiany UI/tekstu/layoutu oraz bez naruszania lifecycle, schedulerów, telemetry i selection/performance lane hosta.

### Wynik

- **Renderer readiness row** przeniesiony do `ui/gicleeframe_view_readiness_row.py` jako `GicleeFrameReadinessRowMixin`.
- **Mixin nie posiada lifecycle** ani `__init__` i **nie dziedziczy** po widżecie Tk.
- Przeniesiono dokładnie jedną metodę: `_pack_readiness_row`.
- Host `GicleeFrameView` dziedziczy pięć mixinów panelowych plus `GicleeFrameReadinessRowMixin` przed `ctk.CTkScrollableFrame`.
- F1 i F2 nadal wywołują `self._pack_readiness_row(...)` bez zmian; rozwiązanie przez MRO.
- Host nadal posiada:
  - kompozycję kolumny kontrolnej `_build_control_column`,
  - adapter expand/collapse `_toggle_f1_section`,
  - lifecycle, schedulery, telemetry, inventory i pozostałe lane'y wydajnościowe.
- Import `status_color` usunięty z hosta po ekstrakcji (jedyny konsument).
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

### Dalsze etapy

Kolejne metody klasy `GicleeFrameView` pozostają zakresem **GF-M9+** — osobne PR-y.

---

## 19. GF-M8 — Top Bar Subsystem Extraction

**Status:** zakończone — MRO zintegrowany.

**Cel:** pierwszy średni pakiet modularizacji po serii małych granic GF-M3–GF-M7 — ekstrakcja kompletnego subsystemu top bara (context bar, command bar, staggered late-build scheduling) bez zmiany UI, timingów, telemetry i integracji atomic reveal.

### Wynik

- **Top bar subsystem** przeniesiony do `ui/gicleeframe_view_top_bar.py` jako `GicleeFrameTopBarMixin`.
- Przeniesiono dokładnie **11 metod** oraz **6 stałych** subsystemowych (`_BACK_LABEL`, `_SHELL_STATUS_CHIP`, `_GF_TOP_BAR_*`).
- Mixin **nie posiada lifecycle** ani `__init__`, **nie dziedziczy** po widżecie Tk; **używa `after()`** jako część granicy schedulera.
- Host `GicleeFrameView` dziedziczy sześć mixinów panelowych plus `GicleeFrameTopBarMixin` przed `ctk.CTkScrollableFrame`.
- Host nadal posiada:
  - `__init__` i inicjalizację pól widgetów top bara,
  - `_build_shell` i wywołanie `_schedule_top_bar_actions_late_build()`,
  - `_ensure_top_bar_actions_for_atomic_reveal`, atomic-reveal orchestration,
  - suppression guards (`_should_suppress_visible_prewarm`, `_log_visible_prewarm_suppressed`),
  - **RAM workflow** (warianty, menu, nawigacja, inventory adaptery) — kandydat następnej większej paczki.
- Zachowano **RAM-only behavior**: brak writera, brak zapisu plików, brak operacji sieciowych i brak Shopify mutation.

### Dalsze etapy

Kolejne metody klasy `GicleeFrameView` pozostają zakresem **GF-M9+** — osobne PR-y. RAM workflow pozostaje host-owned.
