# Background parity — audit map (F4.0)

Hub: [`studio-preview.md`](studio-preview.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

**F4** = *Background parity foundation*: audit + read-only awareness w Studio Preview. **Nie** dodaje sync/backup/deploy/polling, zapisu ustawień tła ani integracji Shopify w shellu Studio.

---

## Repo layout

| Kontekst | Prefiks ścieżek |
|----------|-----------------|
| Monorepo `pusty` | `cursor-api/giclee_app/`, `cursor-api/Komponenty/`, … |
| Standalone `gicleeapp` | `giclee_app/`, `Komponenty/`, … |

Poniżej ścieżki względem korzenia **cursor-api** (lub korzenia repo gicleeapp).

---

## Tier 1 — dedykowany workflow tła (`tldobio`)

| Aspekt | Szczegóły |
|--------|-----------|
| Komponent | `Komponenty/tldobio/` — inline, kategoria Studio `theme` |
| UI | Upload, kadr, gradient, maska radialna, podgląd z tekstem BIO |
| Persystencja | Shopify Files + metafieldy kolekcji (`custom.bio_background_*`) |
| Cache lokalny | `Komponenty/tldobio/data/collections.json` (read-only w F4.1) |
| Docs | [`docs/komponenty/tldobio.md`](../../docs/komponenty/tldobio.md) |
| Launcher | Sekcja „Administracja strony” — [`giclee_app/launcher_layout.py`](../launcher_layout.py) |

**F4.1 Studio:** badge „Tło” + status read-only na karcie huba.

---

## Tier 2 — `section_background` (`stronaglowna`)

| Aspekt | Szczegóły |
|--------|-----------|
| Komponent | `Komponenty/stronaglowna/` — edytor strony głównej (inline, ciężki) |
| Rejestr pól | [`Komponenty/stronaglowna/registry.py`](../../Komponenty/stronaglowna/registry.py) — helper `_section_bg`, kind `section_background` |
| Logika read/write | [`Komponenty/stronaglowna/service.py`](../../Komponenty/stronaglowna/service.py) — `_read/_write/_parse_section_background` |
| Strefy z tłem (5×) | `ga_background`, `rest_background`, `cc_background`, `pot_background`, `sd_background` |
| Wspólny typ | [`Komponenty/_shared/theme_page_editor/types.py`](../../Komponenty/_shared/theme_page_editor/types.py) — `FieldKind` zawiera `section_background` (używany głównie przez stronaglowna) |

**F4.1 Studio:** badge „Tło” + status read-only. Brak odczytu `index.json` / wariantów z poziomu shellu.

---

## Tier 3 — hero / `background_image` (theme page editor)

Pola `shopify_image` wskazujące na grafikę tła sekcji — **inny pipeline** niż `section_background`. Udokumentowane w F4.0; **bez badge w F4.1**.

| Komponent | Plik registry | Pole |
|-----------|---------------|------|
| `katalog` | `Komponenty/katalog/registry.py` | `bio_bg` → `background_image` |
| `kontakt` | `Komponenty/kontakt/registry.py` | `hero_image` → `image_1` |
| `faq` | `Komponenty/faq/registry.py` | `hero_image` → `image_1` |
| `stronablogu` | `Komponenty/stronablogu/registry.py` | `hero_image` → `image_1` |

Wzorzec wspólny: `Komponenty/_shared/theme_page_editor/` (bootstrap, gui_shell).

---

## Tier 4 — kolory / schematy motywu (JSON)

Klucze `"background": "#…"` w `Komponenty/stronaglowna/data/variants/*/settings.json` — schematy kolorów Shopify, nie edytor grafiki sekcji. **Poza zakresem F4.1 UI.**

---

## `giclee_app/` — brak logiki feature tła

Grep w warstwie Studio wykazał wyłącznie:

- `bg=` / `insertbackground` w [`launcher.py`](../launcher.py) — styl widgetów Tk, nie feature tła,
- routing kategorii: [`data/studio_categories.json`](../data/studio_categories.json), [`launcher_layout.py`](../launcher_layout.py),
- opis w help [`launcher.py`](../launcher.py) linia o `tldobio`.

Studio Preview **nie miał** warstwy rozpoznawania tła przed F4.1.

---

## Pliki do edycji (F4.0 / F4.1)

| Plik | F4.0 | F4.1 |
|------|------|------|
| `giclee_app/docs/background-parity.md` | tworzenie | — |
| `giclee_app/studio/background_capabilities.py` | — | tworzenie |
| `giclee_app/ui/widgets.py` | — | badge |
| `giclee_app/ui/component_hub.py` | — | status read-only |
| `giclee_app/docs/studio-preview.md` | — | sekcja F4 |
| `docs/UI_REDESIGN_PLAN.md` | — | korekta roadmapy F4 |
| `tests/test_studio_background_capabilities.py` | — | tworzenie |
| `tests/test_studio_imports.py` | — | rozszerzenie |

## Pliki read-only (referencja zachowania)

- `giclee_app/launcher.py`, `giclee_app/__main__.py`
- `Komponenty/*/view.py`, `Komponenty/*/component.json`
- `Komponenty/tldobio/*`, `Komponenty/stronaglowna/*`
- `inline_host.py`, back stack, lifecycle inline — **bez zmian w F4.1**

---

## Kontrakt F4.1 (minimalny)

Studio Preview **może:**

- rozpoznać `tldobio` i `stronaglowna` po statycznej mapie w `background_capabilities.py`,
- pokazać badge „Tło” na karcie huba,
- ustawić status: `Tło: <label> — <source_hint> (read-only)`.

Studio Preview **nie może** (F4.1):

- importować `Komponenty.*` z nowego modułu capabilities,
- czytać plików danych, metafieldów, sesji Shopify,
- zapisywać ustawień tła,
- dodawać panelu / route tła (F4.2 — zrealizowane osobno),
- włączać sync/backup/deploy/polling.

---

## F4.2 — Background Panel Shell (zrealizowane)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `giclee_app/ui/background_panel.py` |
| Routing | transient host w `launcher_studio.py` — bez nowego routera |
| Wejście | przycisk **Tło** na karcie huba (`tldobio`, `stronaglowna`) |
| Klik karty | inline bez zmian |
| Zawartość | label, tier, source_hint, **Aktualny stan** (F4.3b), inline_note, status read-only |
| Powrót | `_show_hub(return_category_id)` — ta sama kategoria co hub źródłowy |
| Poza zakresem | edycja w panelu, zapis, Shopify, sync/deploy/polling |

## F4.3a — Safe handoff (zrealizowane)

| Aspekt | Szczegóły |
|--------|-----------|
| Akcja | **Edytuj w komponencie** w panelu F4.2 |
| Handoff | `_handoff_background_to_inline` → `_show_inline_component(comp, category)` |
| Destroy | `_show_inline_component` woła `_destroy_background_host()` przed inline |
| Powrót | inline → hub (nie panel) |
| Poza zakresem | edytor w Studio (**F5**) |

## F4.3b — Read-only current state (zrealizowane)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduł | `giclee_app/studio/background_state.py` — pure read-only, **zero importów `Komponenty.*`** |
| UI | sekcja **Aktualny stan** w `background_panel.py` |
| `tldobio` | `data/collections.json` — liczba kolekcji + wpisy z tłem; bez URL-i |
| `stronaglowna` | `manifest.json` + `{active}/index.json` — 5 stref, status obraz/wideo/brak |
| Parser | defensywny — fallback zamiast crasha przy nieoczekiwanej strukturze |
| Zakazy | brak `load_manifest()`, `service.py`, backupów, zapisu, Shopify client |

## F5 — Premium Background Builder (plan)

Kontrakt UX: [`background-builder.md`](background-builder.md).

| Aspekt | Szczegóły |
|--------|-----------|
| Cel | Premium asset manager UX w panelu tła — po F4 |
| Start | tylko `stronaglowna` / `section_background` |
| F5.0 | [`background-builder.md`](background-builder.md) — docs-only, zero kodu |
| F5.1+ | osobne commity po akceptacji raportów |
| Poza zakresem F5.0 | UI, Python modules, bump wersji, `Komponenty/*`, Shopify, zapis |

## F5.1 — Read-only asset browser shell (zrealizowane)

| Aspekt | Szczegóły |
|--------|-----------|
| Moduły | `background_asset_types.py`, `background_asset_shell.py` |
| UI | sekcja **Biblioteka / Assety** — tylko `stronaglowna` |
| Typy | obraz / wideo / kolaż wideo — placeholdery, brak listowania plików |
| `tldobio` | brak sekcji biblioteki |
| Poza zakresem | F5.1b listowanie, F5.2+ draft/preview/save, Shopify |
