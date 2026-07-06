# Studio v2 Workflow Map

**Faza:** F6.1 — docs-only navigation map  
**Checkpoint:** `caabb27` · v1.35.0 · F6.0 audit accepted · Background Builder local v1 frozen  
**Hub:** [`studio-preview.md`](studio-preview.md) · [`background-builder.md`](background-builder.md) · [`admin-components-strategy.md`](admin-components-strategy.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

---

## 1. Purpose

Studio v2 ma być **workflow-based**, nie płaską listą 53 komponentów.

| Zasada | Opis |
|--------|------|
| Workflow-first | Użytkownik myśli obszarami pracy (Site Builder, Asset Lab…), nie folderami `Komponenty/*` |
| Legacy launcher | Klasyczny `python -m giclee_app` pozostaje fallback produkcyjny (polling, backup, pełne subprocess) |
| Brak usuwania | Istniejące komponenty **nie są usuwane** — Studio opakowuje, grupuje lub deleguje launch |
| Read-only first | Nowe powłoki Studio zaczynają od podglądu / launch delegate, bez zapisu i bez Shopify w warstwie `giclee_app/studio/` |
| Discovery bez zmian (F6.1) | `studio_categories.json`, `component.json` i loader komponentów **nie zmieniają się** w tej fazie |

**Stan obecny (F5.3):** Studio Preview ma dashboard, 8 kategorii sidebaru z [`studio_categories.json`](../data/studio_categories.json), inline embed, background panel (tylko `stronaglowna`, `tldobio`). To jest **v1 navigation** — ten dokument definiuje **v2 target map**.

**Przyszłość (opcjonalnie, poza F6.1):** read-only `giclee_app/data/studio_workflows.json` mapujący folder → workflow. **Nie tworzyć w F6.1** bez osobnej akceptacji.

**Administracja strony (post-freeze):** rebuild vs adapt — [`admin-components-strategy.md`](admin-components-strategy.md). **Katalog** = parent workflow (absorbs `tldobio`). 9 komponentów rebuild; reszta adapt-first; `stronaglowna` = frozen reference.

---

## 2. Primary workflows

| # | Workflow | Skrót |
|---|----------|-------|
| 1 | Dashboard | Punkt wejścia, recent/pinned, statusy |
| 2 | Site Builder | Strony motywu, warianty, tła sekcji |
| 3 | Asset Lab | Przetwarzanie plików graficznych |
| 4 | Product Pipeline | Cykl produktu Shopify |
| 5 | Collections | Kolekcje katalogowe i losowanie |
| 6 | Fulfillment | Zamówienia → produkcja |
| 7 | Content Hub | Blog, social, analytics, zadania |
| 8 | Finance Desk | Księgowość (izolowana) |
| 9 | System | Limity, planer, poczta, sklep, deploy |
| 10 | Legacy Tools | Utility subprocess, dev, GPT review |

---

## 3. Workflow details

Legenda **Studio treatment:**

| Treatment | Znaczenie |
|-----------|-----------|
| `native_shell` | Docelowo dedykowany ekran Studio (multi-step UX) |
| `read_only_shell` | Panel read-only + handoff (wzorzec F4/F5 Background Builder) |
| `launch` | Karta / przycisk → istniejący inline lub subprocess |
| `defer` | Dostępny przez legacy hub lub ukryty; brak priorytetu Studio v2 |
| `legacy_only` | Tylko klasyczny launcher lub Legacy Tools |

Legenda **ryzyka:** N niskie · M średnie · H wysokie · VH bardzo wysokie

---

### 3.1 Dashboard

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Szybki przegląd stanu studia, ostatnie akcje, skróty do workflowów |
| **Komponenty** | Brak (agreguje metadane ze wszystkich workflowów) |
| **Mode** | — |
| **Studio treatment** | `native_shell` (już istnieje F2) |
| **Ryzyko** | N |
| **Save** | Nie |
| **Shopify** | Nie |
| **Pierwsza faza** | Done (F2) — rozszerzenie o skróty workflow v2 w przyszłości |

---

### 3.2 Site Builder

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Edycja treści i grafiki stron sklepu — warianty, sekcje, tła |
| **Komponenty** | `stronaglowna`, `katalog`, `kontakt`, `faq`, `filozofiamarki`, `wspolpraca`, `stronablogu`, `karuzela`, `stronaproduktu`, `gicleeframe`, `wlasnafotografia`, `losujobraz`, `tldobio` |
| **Mode** | inline (12) · `tldobio` = Tier 1 background |
| **Studio treatment** | `read_only_shell` dla background paths · `launch` dla inline edytorów · `defer` dla utility subprocess w theme |
| **Ryzyko** | M (`stronaglowna`) · H (`tldobio` — Shopify Files + metafields) |
| **Save** | Tak (przez istniejące inline / controlled handoff F5.4+) |
| **Shopify** | Częściowo (deploy/upload w komponencie, nie w Studio layer) |
| **Pierwsza faza** | **F6.3** — Tier 3 read-only variant shells · **F5.4** — save tylko `stronaglowna` section_background |

**Wzorzec F5 Background Builder (proven):**

```text
Hub card → Background Panel (read-only) → draft (in-memory) → conceptual preview → handoff inline
```

Dotyczy dziś: `stronaglowna` (F5.0–F5.3 done).  
`tldobio` — osobna akceptacja po stabilizacji `stronaglowna` (Tier 1, upload Shopify).

**Utility poza core Site Builder (legacy):** `stronyzobrazami`, `stronydozycia` → Legacy Tools.

---

### 3.3 Asset Lab

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | „Mam plik → przetwórz → podejrzyj → wyślij dalej” — jeden spójny warsztat graficzny |
| **Komponenty** | `mockup`, `kolaz`, `squoosh`, `print_optimize`, `przedpo`, `nazwijobraz`, `infoplikow`, `pobierzobraz` |
| **Mode** | subprocess (wszystkie) |
| **Studio treatment** | **F6.2:** `read_only_shell` + `launch` (bez merge backend) · docelowo `native_shell` |
| **Ryzyko** | N–M (lokalne PIL) · H dla `mockup` (Shopify publish) |
| **Save** | Tak (pliki lokalne / export) |
| **Shopify** | Opcjonalnie (`mockup`, `kolaz` kolekcja, `pobierzobraz`) |
| **Pierwsza faza** | **F6.2** — shell read-only / launch-only |

**Merge concept (map only — bez implementacji F6.1):**

| Moduł Asset Lab | Istniejący folder | Rola w Lab |
|-----------------|-------------------|------------|
| Mock-up katalogowy | `mockup` | Ramka A4 → galeria produktu |
| Kreator kolaży | `kolaz` | Składanie wielu obrazów, presety BIO |
| Kompresja WebP | `squoosh` | Konwersja formatów |
| Optymalizacja druku | `print_optimize` | Pipeline druku |
| Przed/Po | `przedpo` | Porównanie wersji |
| Nazwij obraz | `nazwijobraz` | Konwencja nazw plików |
| Info plików | `infoplikow` | Metadane EXIF/rozmiar |
| Pobierz obraz | `pobierzobraz` | Pobranie z Shopify/CDN |

`mockup` może też występować jako **publish step** w Product Pipeline — w Asset Lab traktowany jako narzędzie graficzne.

---

### 3.4 Product Pipeline

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Od pliku źródłowego do produktu Shopify — opisy, ceny, szablony, tytuły |
| **Komponenty** | `dodajobraz`, `aktualizujopis`, `zmienceny`, `wyborszablonu`, `zmietytuly`, `tytulyai`, `wzorzecszablonu` |
| **Mode** | subprocess (6) · inline `wzorzecszablonu` |
| **Studio treatment** | `launch` (F6.x+) · docelowo `native_shell` wizard · **defer** masowy Shopify bez planu |
| **Ryzyko** | H (LLM, REST/GraphQL Shopify, markets) |
| **Save** | Tak |
| **Shopify** | **Tak** |
| **Pierwsza faza** | Defer implementacji shell — pozostaje launch z huba Produkty · `mockup` publish step później |

**Proponowany flow (docelowy, nie implementowany):**

```text
dodajobraz → wyborszablonu / wzorzecszablonu → tytulyai / zmietytuly → aktualizujopis → zmienceny → [mockup publish]
```

---

### 3.5 Collections

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Zarządzanie kolekcjami katalogowymi i losowaniem produktów |
| **Komponenty** | `katalog` (primary), `losujobraz` |
| **Mode** | inline |
| **Studio treatment** | `launch` · **F6.3** read-only variant summary (wzorzec F4.3b) |
| **Ryzyko** | N–M |
| **Save** | Tak |
| **Shopify** | Częściowo (sync kolekcji w komponencie) |
| **Pierwsza faza** | F6.3 (razem z Site Builder Tier 3) |

**Uwaga:** `katalog` i `losujobraz` są też w Site Builder (strony motywu). W nawigacji v2 **Collections** to workflow operacyjny (kolekcje produktów); edycja strony katalogu → Site Builder.

---

### 3.6 Fulfillment

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Od zamówienia do wydruku, ramy, etykiety, wysyłki |
| **Komponenty** | `obrazy`, `passepartout`, `produkcja`, `kalkulacja` |
| **Mode** | inline (wszystkie) |
| **Studio treatment** | `launch` · **defer** sync polling w Studio |
| **Ryzyko** | M (`obrazy`, `passepartout`) · **H** (`produkcja` — `orders_sync.py`) |
| **Save** | Tak |
| **Shopify** | Tak (`produkcja` polling) |
| **Pierwsza faza** | Launch-only · sync zostaje w klasycznym launcherze (F7) |

---

### 3.7 Content Hub

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Blog, social media, marketing, analytics, zadania redakcyjne |
| **Komponenty** | `blog`, `socialmedia`, `zadania`, `cenyMarketing`, `analytics` |
| **Mode** | inline (wszystkie) |
| **Studio treatment** | `launch` · **defer** tokeny/API w Studio layer |
| **Ryzyko** | M (`analytics` Shopify API · `socialmedia` Meta tokeny) |
| **Save** | Tak |
| **Shopify** | Częściowo |
| **Pierwsza faza** | Defer native shell — launch z obecnego huba Content/AI |

---

### 3.8 Finance Desk

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Księgowość, dokumenty sprzedaży, KPiR, DNR — **osobny kontekst pracy** |
| **Komponenty** | `finanse`, `dokumentysprzedazy`, `kpir`, `dnr`, `ksiegowosc` |
| **Mode** | inline · 4× `hidden: true` |
| **Studio treatment** | `launch` · **defer** · **nie** w primary creative flow |
| **Ryzyko** | **VH** |
| **Save** | Tak |
| **Shopify** | Nie (dane sprzedaży lokalne / sync orders) |
| **Pierwsza faza** | Izolacja w sidebarze (secondary) · brak redesignu F6.x |

**Zasada izolacji:** Finance Desk **nie miesza się** z Asset Lab, Site Builder ani Product Pipeline w primary navigation. Osobna sekcja, ewentualnie wymaga potwierdzenia wejścia w przyszłości.

---

### 3.9 System

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Limity, planer, notatnik, poczta, sklep (URL), theme deploy |
| **Komponenty** | `limity`, `planer`, `notatnik`, `poczta`, `sklep`, `pushe` |
| **Mode** | inline (4) · subprocess (`notatnik`, `pushe`) · **url** (`sklep`) |
| **Studio treatment** | `launch` · **defer** `pushe` (deploy) w Studio |
| **Ryzyko** | N–M · **H** (`pushe` theme deploy) |
| **Save** | Zależnie od modułu |
| **Shopify** | `pushe` tak · `sklep` external URL |
| **Pierwsza faza** | Launch-only · `pushe` → defer do F5.5/F7 |

---

### 3.10 Legacy Tools

| Pole | Wartość |
|------|---------|
| **Cel użytkownika** | Narzędzia dev, GPT review, utility batch — poza codziennym creative flow |
| **Komponenty** | `integracjagpt`, `bazapromptow`, `debugowanie`, `stronyzobrazami`, `stronydozycia` |
| **Mode** | subprocess (4) · inline N/A |
| **Studio treatment** | `legacy_only` · `launch` · status read-only GPT (F3) |
| **Ryzyko** | **VH** (`integracjagpt` — git push, mirror) · M (reszta) |
| **Save** | Tak |
| **Shopify** | Częściowo (`integracjagpt` theme push) |
| **Pierwsza faza** | Bez zmian — subprocess + obecny hub Review/GPT |

---

## 4. Component mapping table

**Current category** = [`studio_categories.json`](../data/studio_categories.json) (bez zmian w F6.1).

| Folder | Current category | Proposed workflow | Treatment | Priority | Notes |
|--------|------------------|-------------------|-----------|----------|-------|
| `stronaglowna` | theme | Site Builder | read_only_shell + launch | P0 | Frozen reference · Background Builder local v1 done |
| `tldobio` | theme | Site Builder (via Katalog) | absorbed · not standalone tile | P1 | Absorbed into `katalog` · see admin-components-strategy |
| `katalog` | theme | Site Builder / Collections | rebuild · parent workflow | P1 | Rebuild · absorbs tldobio · F6.3 next |
| `kontakt` | theme | Site Builder | rebuild · F6.3+ | P2 | Rebuild per admin-components-strategy |
| `faq` | theme | Site Builder | rebuild · F6.3+ | P2 | Rebuild per admin-components-strategy |
| `filozofiamarki` | theme | Site Builder | rebuild | P2 | Rebuild per admin-components-strategy |
| `wspolpraca` | theme | Site Builder | rebuild | P2 | Rebuild per admin-components-strategy |
| `stronablogu` | theme | Site Builder | rebuild | P2 | Rebuild per admin-components-strategy |
| `karuzela` | theme | Site Builder | launch · adapt-first | P2 | Adapt-first |
| `stronaproduktu` | theme | Site Builder | launch · adapt-first | P2 | Adapt-first |
| `gicleeframe` | theme | Site Builder | rebuild | P2 | Rebuild per admin-components-strategy |
| `wlasnafotografia` | theme | Site Builder | rebuild | P2 | Rebuild per admin-components-strategy |
| `losujobraz` | theme | Collections | rebuild | P3 | Rebuild per admin-components-strategy |
| `stronyzobrazami` | theme | Legacy Tools | legacy_only | P4 | subprocess utility |
| `stronydozycia` | theme | Legacy Tools | legacy_only | P4 | subprocess utility |
| `wzorzecszablonu` | theme | Product Pipeline | launch · adapt-first | P2 | Adapt-first · inline szablony |
| `mockup` | products | Asset Lab (+ Pipeline step) | launch · F6.2 shell | P1 | H risk Shopify publish |
| `kolaz` | products | Asset Lab | launch · F6.2 shell | P1 | |
| `squoosh` | products | Asset Lab | launch · F6.2 shell | P1 | |
| `print_optimize` | products | Asset Lab | launch · F6.2 shell | P2 | |
| `przedpo` | products | Asset Lab | launch · F6.2 shell | P2 | |
| `nazwijobraz` | products | Asset Lab | launch · F6.2 shell | P2 | |
| `infoplikow` | products | Asset Lab | launch · F6.2 shell | P3 | |
| `pobierzobraz` | products | Asset Lab | launch · F6.2 shell | P3 | |
| `dodajobraz` | products | Product Pipeline | launch · defer shell | P2 | H · Shopify |
| `aktualizujopis` | products | Product Pipeline | launch · defer | P3 | H |
| `zmienceny` | products | Product Pipeline | launch · defer | P3 | H |
| `wyborszablonu` | products | Product Pipeline | launch | P3 | |
| `zmietytuly` | products | Product Pipeline | launch | P3 | |
| `tytulyai` | products | Product Pipeline | launch | P3 | H · Gemini |
| `obrazy` | orders | Fulfillment | launch | P2 | |
| `passepartout` | orders | Fulfillment | launch | P2 | |
| `produkcja` | production | Fulfillment | launch · defer sync | P2 | H · polling |
| `kalkulacja` | production | Fulfillment | launch | P3 | |
| `finanse` | finance | Finance Desk | launch · defer | P4 | VH · not primary |
| `dokumentysprzedazy` | finance | Finance Desk | launch · hidden | P4 | VH · hidden |
| `kpir` | finance | Finance Desk | launch · hidden | P4 | VH · hidden |
| `dnr` | finance | Finance Desk | launch · hidden | P4 | VH · hidden |
| `ksiegowosc` | finance | Finance Desk | legacy_only · hidden | P5 | legacy duplicate |
| `blog` | content | Content Hub | launch · defer | P3 | |
| `socialmedia` | content | Content Hub | launch · defer | P3 | tokeny |
| `zadania` | content | Content Hub | launch | P3 | |
| `cenyMarketing` | content | Content Hub | launch | P4 | |
| `analytics` | content | Content Hub | launch · defer | P4 | Shopify API |
| `integracjagpt` | review | Legacy Tools | legacy_only | P4 | VH · subprocess |
| `bazapromptow` | review | Legacy Tools | launch | P4 | |
| `debugowanie` | review | Legacy Tools | legacy_only | P5 | dev |
| `limity` | system | System | launch | P3 | |
| `planer` | system | System | launch | P3 | |
| `notatnik` | system | System | launch | P4 | subprocess |
| `poczta` | system | System | launch | P4 | |
| `sklep` | system | System | launch (url) | P3 | external |
| `pushe` | system | System | defer | P4 | H · theme deploy |

**Priority:** P0 = proven path · P1 = next shells · P2 = wrap/launch · P3+ = defer

---

## 5. Primary vs secondary navigation

### Primary Studio sidebar (docelowy v2)

| Pozycja | Workflow | Uzasadnienie |
|---------|----------|------------|
| Dashboard | Dashboard | Punkt wejścia (już istnieje) |
| Site Builder | Site Builder | Najwyższa wartość creative · F5 pattern |
| Asset Lab | Asset Lab | Konsolidacja 8 narzędzi graficznych |
| Product Pipeline | Product Pipeline | Operacje Shopify produktów |
| Collections | Collections | Katalog + losowanie |
| Fulfillment | Fulfillment | Ops codzienny |
| Content Hub | Content Hub | Redakcja i marketing |
| System | System | Narzędzia systemowe |

### Secondary / collapsed / protected

| Pozycja | Workflow | Uzasadnienie |
|---------|----------|------------|
| Finance Desk | Finance Desk | VH risk · inny kontekst użytkownika · nie w creative flow |
| Legacy Tools | Legacy Tools | GPT push, debug, utility batch |
| Review/GPT | → Legacy Tools | `integracjagpt`, `bazapromptow` |

### Workflow detail screens (wewnątrz workflowu, nie flat 53 cards)

- **Site Builder:** grupy „Strona główna”, „Strony informacyjne”, „Sekcje specjalne”, „Tła BIO (Tier 1)”
- **Asset Lab:** 8 modułów jako kafelki z opisem + „Otwórz narzędzie”
- **Product Pipeline:** kroki wizarda (docelowo) lub lista launch (F6.2–F6.x)
- **Fulfillment:** Zamówienia → Produkcja → Kalkulacja

### Hidden / deferred (bez primary nav)

- `dokumentysprzedazy`, `kpir`, `dnr`, `ksiegowosc` — hidden w `component.json`; dostęp przez Finance Desk
- `pushe`, `produkcja` sync — defer F5.5/F7
- `integracjagpt` push/mirror — legacy only

### Mapowanie v1 → v2 (informacyjne, bez zmiany kodu)

| Obecna kategoria v1 | Docelowy workflow v2 |
|---------------------|----------------------|
| Strona / Motyw | Site Builder (+ część Legacy) |
| Produkty | Asset Lab + Product Pipeline |
| Zamówienia + Produkcja | Fulfillment |
| Finanse | Finance Desk (secondary) |
| Content / AI | Content Hub |
| Review / GPT | Legacy Tools |
| System | System |

---

## 6. Asset Lab proposal (map only)

**Cel:** Jeden warsztat graficzny zamiast 8 osobnych kart w hubie Produkty.

**F6.2 scope (planowany):**

- Nowy ekran Studio (read-only shell): opis workflowu, 8 kafelków modułów
- Każdy kafelek: krótki opis + przycisk **Otwórz** → `launcher_delegate` subprocess
- **Bez:** merge `gui.py`, wspólnego backendu PIL, Shopify publish w Studio layer

**Kolejność modułów w UI (propozycja):**

1. Nazwij obraz → Info plików → Squoosh → Print optimize  
2. Przed/Po → Kolaż → Mock-up → Pobierz obraz  

**Zależność od Product Pipeline:** `mockup` publish może linkować do Product Pipeline w przyszłości; w Asset Lab pozostaje narzędziem graficznym.

---

## 7. Site Builder proposal

**Core pages (inline launch):**

`stronaglowna`, `katalog`, `kontakt`, `faq`, `filozofiamarki`, `wspolpraca`, `stronablogu`, `karuzela`, `stronaproduktu`, `gicleeframe`, `wlasnafotografia`, `losujobraz`

**Background paths:**

| Komponent | Tier | Studio pattern | Status |
|-----------|------|----------------|--------|
| `stronaglowna` | Tier 2 section_background | F4 panel + F5 draft/preview | F5.3 done |
| `tldobio` | Tier 1 bio_workflow | Ten sam pattern read-only first | Not started · H risk |
| Tier 3 (`katalog`, `kontakt`, `faq`, `stronablogu`) | theme_image_bg | F6.3 read-only variant summary | Planned |

**F5.4 boundary:** Controlled save **tylko** `stronaglowna` · nie generalizować na Tier 1/3 bez osobnej spec.

---

## 8. Product Pipeline proposal

**Komponenty:**

| Krok | Folder | Mode |
|------|--------|------|
| Utworzenie produktu | `dodajobraz` | subprocess |
| Szablon | `wyborszablonu`, `wzorzecszablonu` | subprocess / inline |
| Tytuły | `zmietytuly`, `tytulyai` | subprocess |
| Opis | `aktualizujopis` | subprocess |
| Ceny | `zmienceny` | subprocess |
| Mockup (opcjonalnie) | `mockup` | subprocess · cross-link Asset Lab |

**Studio v2.0:** launch-only z grupowaną nawigacją — **bez** wizarda i **bez** Shopify w `giclee_app/studio/`.

---

## 9. Finance Desk isolation

| Zasada | Implementacja (docelowa) |
|--------|--------------------------|
| Osobna sekcja sidebar | Finance Desk — secondary, nie w primary creative list |
| Brak cross-links | Asset Lab / Site Builder nie linkują do finanse |
| Hidden components | `dokumentysprzedazy`, `kpir`, `dnr`, `ksiegowosc` — dostęp tylko przez Finance Desk |
| Brak redesignu F6.x | Launch istniejących inline · VH = defer native shell |
| Klasyczny launcher | Pełny dostęp do finanse bez zmian |

---

## 10. Roadmap recommendation

| Faza | Cel | Typ |
|------|-----|-----|
| **F6.0** | Component redesign audit | docs · **accepted** |
| **F6.1** | Studio v2 navigation map (ten dokument) | docs · **current** |
| **F6.2** | Asset Lab shell — read-only / launch-only | code · shell only |
| **F5.4-plan** | Mini-spec controlled save `stronaglowna` | docs |
| **F5.4-impl** | Controlled save implementation | code · after F5.4-plan acceptance |
| **F6.3** | Site Builder Tier 3 read-only shells | code |
| **F5.5 / F7** | Shopify / sync / deploy w Studio | defer · osobna decyzja |
| **F5.6** | `GICLEE_STUDIO_UI` default switch | config |
| **F8** | Packaging / PyInstaller (dawne „F6” w planie) | build |

**Rekomendowana kolejność po F6.1:**

```text
F6.1 (docs) → F6.2 Asset Lab shell → F5.4-plan → F5.4-impl → F6.3 → F5.5/F7 → F5.6 → F8
```

Uzasadnienie: Asset Lab shell (F6.2) przed F5.4-plan — zapis tła nie projektujemy w oderwaniu od większej mapy workflowów.

---

## 11. Out of scope (F6.1 i bezpośredni follow-up)

- Implementacja UI / kod komponentów
- Usuwanie komponentów lub legacy launcher
- Masowa migracja `component.json`
- Zmiana `studio_categories.json` (wymaga osobnej propozycji)
- Shopify / sync / deploy w Studio layer
- F5.4 save (implementacja)
- Merge backend Asset Lab (`gui.py`, PIL pipelines)
- Redesign Finance Desk
- PyInstaller / F8 packaging
- Utworzenie `studio_workflows.json` (wspomniane jako opcja przyszła)

---

## 12. Acceptance criteria (F6.1)

| Kryterium | Status |
|-----------|--------|
| Docs-only | Ten plik + aktualizacja `UI_REDESIGN_PLAN.md` |
| Brak zmian kodu | `giclee_app/ui/*`, `launcher_studio.py`, `Komponenty/*` nietknięte |
| Brak version bump | v1.29.3 bez zmian |
| Brak zmian discovery | `studio_categories.json`, `component.json` bez zmian |
| Brak unrelated dirty w stage | integracjagpt, backups, variants — poza commitem |
| Jasna rekomendacja next step | **F6.2 Asset Lab shell** |

**Next step po akceptacji F6.1:** F6.2 — read-only Asset Lab shell (launch delegate do 8 subprocess), potem F5.4-plan dla `stronaglowna`.

---

## 13. Administracja strony strategy

**Docs:** [`admin-components-strategy.md`](admin-components-strategy.md) (checkpoint `caabb27`)

| Reguła | Opis |
|--------|------|
| Rebuild | 9 komponentów: `katalog`, `wlasnafotografia`, `gicleeframe`, `wspolpraca`, `filozofiamarki`, `kontakt`, `stronablogu`, `faq`, `losujobraz` |
| Parent workflow | **Katalog** rebuild od zera — absorbs `tldobio` (Tło do Bio) |
| Adapt-first | `wzorzecszablonu`, `stronaproduktu`, `karuzela` + reguła: poza tabelą rebuild = adapt-first |
| Frozen | `stronaglowna` — Background Builder local v1 reference |

**Next:** F6.3 / Katalog rebuild plan. **F5.5** deferred.

---

## 14. Katalog rebuild plan

**Docs:** [`katalog-rebuild-plan.md`](katalog-rebuild-plan.md) (checkpoint `56b4c9c`)

| Punkt | Status |
|-------|--------|
| Katalog rebuild plan | **done (docs-only)** |
| Katalog F1 shell | **done @ 1.36.0** — read-only inventory |
| Katalog = parent workflow | absorbs `tldobio` |
| Next implementation | **Katalog F2** — bounded data map |
| Writer / Shopify | not started · F5.5 deferred |

---

## 15. Katalog F1 read-only shell

| Element | Status |
|---------|--------|
| `katalog_inventory.py` | Bounded read-only paths |
| `katalog_view.py` | Shell — no Save / no writer |
| Sidebar NAV `katalog` | Without `studio_categories.json` change |
| Hub `katalog` click | Routes to F1 shell |
| tldobio | Absorbed subflow info only |
