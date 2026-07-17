# Tłumaczenia treści motywu (poza produktami)

Hub: [`README.md`](README.md)

Sklep ma **dwie warstwy językowe**:

1. **Produkty / kolekcje / blog** — Shopify Translations API (`cursor-api`, `translationsRegister`).
2. **Motyw** — pliki `locales/*.json` + klucze `giclee.*` opisane poniżej.

Polski jest językiem bazowym sklepu. Treść z edytora motywu (JSON szablonów) zostaje po polsku w `templates/*.json`. Klucze `giclee.ui.*` (splash, nawigacja galerii, mockup, JS) muszą być w `pl.json`, bo Liquid używa `| t` bez fallbacku. Bloki i sekcje po polsku biorą tekst z ustawień motywu. Dla EN, DE, FR, ES, NL, IT tłumaczenia są w locale pod kluczami `giclee.blocks.<block_id>.<pole>` i `giclee.sections.<section_id>.<pole>`.

## Jak to działa

| Warstwa | Pliki | Mechanizm |
|---------|--------|-----------|
| **Menu nawigacji** | `snippets/giclee-i18n-menu-title.liquid`, `blocks/_header-menu.liquid`, `snippets/header-drawer.liquid`, `snippets/mega-menu-list.liquid`, `blocks/menu.liquid` | klucze `giclee.menu.<handleize tytułu PL>`; nazwiska artystów bez tłumaczenia (fallback); `data-giclee-menu="catalog"` na pozycji Katalog (`link.handle == 'katalog'`); panel artystów w `layout/theme.liquid` używa `Shopify.routes.root` + regex `/collections/` (prefiks językowy `/de/` itd.) |
| Bloki tekstowe / przyciski / FAQ / jumbo | `snippets/text.liquid`, `snippets/button.liquid`, `snippets/jumbo-text.liquid`, `blocks/_accordion-row.liquid` | `giclee-i18n-block-text.liquid` — runtime `block.id` ma prefisz sekcji (`SekcjaId__text_abc` → klucz `text_abc`); brak tłumaczenia = `{{ block.settings.text }}` (richtext bez escapingu); tłumaczenie z locale = Liquid escapuje HTML → `assets/rte-formatter.js` dekoduje encje przy starcie |
| **Mockup fotografii** | `snippets/giclee-photo-mockup.liquid`, `assets/giclee-photo-mockup.js` | `giclee.ui.mockup_*` + `window.__gicleeI18n` |
| Sekcja galerii autora | `sections/giclee-artist-collection-showcase.liquid` | to samo dla `heading`, `lead`, `cta_label`, `eyebrow` |
| UI (splash, katalog, mockup, JS) | `snippets/giclee-i18n-js.liquid` → `window.__gicleeI18n` | klucze `giclee.ui.*` + standardowe `actions.*` / `products.product.*`; fallback PL: `snippets/giclee-i18n-defaults-json.liquid` + `snippets/giclee-ui-t.liquid` gdy brak klucza w locale |
| Analiza PPI mockupu | `assets/giclee-print-analysis.js` | czyta `window.__gicleeI18n` |

## Utrzymanie tłumaczeń

1. Edytuj kanoniczny master: `tools/i18n/giclee_i18n_all.json`.
2. Wygeneruj pliki: `node tools/i18n/merge_giclee_locales.cjs`.
3. Sprawdź zgodność: `node tools/i18n/merge_giclee_locales.cjs --check` oraz `python tools/i18n/validate_giclee_i18n.py`.

**Nowy blok lub sekcja:** dodaj klucze i tłumaczenia do kanonicznego mastera, a następnie uruchom generator i walidator.

**Długie wartości:** uruchom `node tools/i18n/split_long_giclee_texts.cjs`, a następnie ponownie generator i walidator.

## Deploy

Narzędzia i18n nie publikują motywu ani nie zmieniają sklepu. Publikacja jest osobnym etapem wymagającym przeglądu zmian, zakończonych testów i jawnej decyzji o wdrożeniu.

Powiązane: [`../../THEME_KNOWLEDGE.md`](../../THEME_KNOWLEDGE.md) §3 (języki motywu vs produktów).
