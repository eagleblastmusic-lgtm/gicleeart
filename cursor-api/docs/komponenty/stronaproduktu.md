# Komponent: stronaproduktu

**Cel:** Konfiguracja stronicowanego opisu («mini strony») na PDP `szablon-produktu-v3` — podział akapitów na strony + grafika per strona. Dodatkowo globalne **Ustawienia efektów PDP v3** (immersive zoom, blur R2, tła sekcji).

| Plik | Rola |
|------|------|
| `gui.py` | Lista produktów, edytor stron (liczba akapitów, podgląd tekstu, upload grafik), okno «Ustawienia efektów (PDP v3)…» |
| `service.py` | Metafieldy `custom.story_pages` (produkt) i `custom.pdp_v3_effects` (sklep), Shopify Files, parsowanie akapitów z `body_html` |

Tryb: `inline` (w launcherze — «← Powrót»). Sekcja: **Administracja strony** (kafelek «Strona produktu»).

## Metafield `custom.story_pages` (JSON)

```json
{
  "pages": [
    { "paragraphs": 2, "image": "https://cdn.shopify.com/..." },
    { "paragraphs": 1, "image": "https://cdn.shopify.com/..." }
  ],
  "details_image": "https://cdn.shopify.com/..."
}
```

- `pages[].paragraphs` — ile kolejnych akapitów opisu (z lewej kolumny `body_html`) wchodzi na stronę.
- `pages[].image` / `details_image` — grafika strony (Shopify Files); puste = zdjęcie główne produktu.
- Ostatnia strona (panel **SZCZEGÓŁY**) jest dokładana automatycznie przez motyw — nie liczy się w `pages`.
- **Bez metafielda** motyw dzieli akapity automatycznie (~850 znaków/strona) i używa featured image.

## Workflow

1. Uruchom kafelek **Strona produktu** w GicleeApp.
2. Wybierz produkt (filtr, checkbox «Tylko bez konfiguracji stron»).
3. Ustaw strony: «Dodaj/Usuń stronę», «+/− akapit» (podgląd tekstu strony po prawej).
4. «Wgraj grafikę strony…» dla wybranej strony (także dla wiersza SZCZEGÓŁY).
5. **Zapisz do Shopify** → metafield. «Usuń konfigurację» przywraca auto-podział.

## Metafield `custom.pdp_v3_effects` (JSON, owner: SHOP)

Globalne ustawienia efektów PDP v3 — okno **Ustawienia efektów (PDP v3)…** (przycisk na pasku filtra).

```json
{
  "zoom_immersive": true,
  "r2_blur": true,
  "config_bg": { "enabled": true, "image": "", "parallax": true, "blur": true, "brightness": 100 },
  "pt_bg": { "enabled": true, "image": "", "blur": false, "brightness": 100 }
}
```

- `zoom_immersive` — przybliżenie R2 chowa górne menu i powiększa viewer do 100vh.
- `r2_blur` — rozmycie R2 wraz z wjazdem sekcji opisu (0→10px).
- `config_bg` — tło sekcji konfiguratora (jak w karuzeli): `image` puste = zdjęcie główne produktu; `parallax` = subtelny ruch od myszy; `blur` = rozmycie 11px; `brightness` 30–170 (%).
- `pt_bg` — wspólne tło «Jak powstaje Twój obraz» + «Na czym budujemy Twoje zaufanie» (jeden obraz na obie sekcje): wymaga wgranej grafiki (`image`); `blur` = 14px; `brightness` jw.
- Brak metafielda / brak pola = wartości domyślne jak wyżej (motyw: `!== false`).
- Zapis: GraphQL `metafieldsSet` na `shop.id`; upload teł: Shopify Files.

## Warstwa motywu

`snippets/giclee-product-story.liquid` + `assets/giclee-product-story.css/.js` — tylko `szablon-produktu-v3`.
Szczegóły: [`../../../docs/motyw/szablony-i-strony.md`](../../../docs/motyw/szablony-i-strony.md).

→ [`README.md`](README.md)
