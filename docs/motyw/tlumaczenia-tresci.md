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
| UI (splash, katalog, mockup, JS) | `snippets/giclee-i18n-js.liquid` → `window.__gicleeI18n` | klucze `giclee.ui.*` + standardowe `actions.*` / `products.product.*` |
| Analiza PPI mockupu | `assets/giclee-print-analysis.js` | czyta `window.__gicleeI18n` |

## Utrzymanie tłumaczeń

1. Ekstrakcja polskich stringów z szablonów: `node _extract_pl_template_text.cjs` → `_extract_pl_template_text.json`.
2. Master tłumaczeń (6 języków + PL UI): `locales/_giclee_i18n_all.json`.
3. Merge do plików Shopify: `node locales/_merge_giclee_locales.cjs` (aktualizuje `en.default.json`, `de.json`, `fr.json`, `es.json`, `nl.json`, `it.json` oraz **`pl.json`** — tylko sekcję `giclee.ui`).

**Nowy blok tekstowy po polsku:** po dodaniu bloku w Theme Editorze uruchom ekstrakcję, dopisz tłumaczenia do `_giclee_i18n_all.json`, merge, deploy `locales/*.json` + ewentualnie zmienione snippety/sekcje.

**Limit Shopify:** pojedyncza wartość w locale ≤ ~1000 znaków. Dłuższe HTML (np. strona Giclée Frame) dziel na `text_part1`, `text_part2`, … — skrypt `locales/_split_long_giclee_texts.cjs`; `snippets/text.liquid` skleja part-y automatycznie.

## Deploy

```powershell
shopify theme push --store giclee-art-3.myshopify.com --theme 197314249052 --allow-live `
  --only "locales/en.default.json" "locales/de.json" "locales/fr.json" "locales/es.json" "locales/nl.json" "locales/it.json" "locales/pl.json" `
  "snippets/giclee-i18n-text.liquid" "snippets/giclee-i18n-js.liquid" "snippets/text.liquid" "snippets/button.liquid" "snippets/jumbo-text.liquid" `
  "blocks/_accordion-row.liquid" "sections/giclee-artist-collection-showcase.liquid" "layout/theme.liquid" `
  "assets/giclee-artist-collection-showcase.js" "assets/giclee-pdp-artwork-preview.js" "assets/giclee-print-analysis.js"
```

Powiązane: [`../../THEME_KNOWLEDGE.md`](../../THEME_KNOWLEDGE.md) §3 (języki motywu vs produktów).
