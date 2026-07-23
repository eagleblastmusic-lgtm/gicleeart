# Komponent: stronaproduktu

**Cel:** Konfiguracja stronicowanego opisu («mini strony») na PDP `szablon-produktu-v3` — podział akapitów na strony + grafika per strona. Moduł potrafi również zaproponować semantycznie dopasowane wycinki głównego obrazu przez Gemini API. Dodatkowo obsługuje globalne **Ustawienia efektów PDP v3** (immersive zoom, blur R2, tła sekcji).

| Plik | Rola |
|------|------|
| `gui.py` | Bazowy edytor stron (lista produktów, liczba akapitów, ręczny upload grafik, ustawienia efektów) |
| `gui_ai.py` | Nakładka GUI z akcją «AI — dobierz kadry…», podglądem wariantów i zatwierdzaniem |
| `ai_crops.py` | Gemini: interpretacja obrazu i tekstu; lokalne kadrowanie przez Pillow; walidacja, upload i zapis |
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

## Workflow ręczny

1. Uruchom kafelek **Strona produktu** w GicleeApp.
2. Wybierz produkt (filtr, checkbox «Tylko bez konfiguracji stron»).
3. Ustaw strony: «Dodaj/Usuń stronę», «+/− akapit» (podgląd tekstu strony po prawej).
4. «Wgraj grafikę strony…» dla wybranej strony (także dla wiersza SZCZEGÓŁY).
5. **Zapisz do Shopify** → metafield. «Usuń konfigurację» przywraca auto-podział.

## Inteligentne kadry Gemini

Przycisk **AI — dobierz kadry…** analizuje jednocześnie główny obraz produktu i tekst wszystkich zapisanych mini-stron.

### Zasady

- Najpierw zapisz podział stron przyciskiem **Zapisz do Shopify**. Funkcja AI nie pracuje na niezapisanym stanie, aby nie utracić istniejących adresów grafik.
- Strona 1 używa pełnego głównego obrazu. Aplikacja nie wysyła jego duplikatu do Shopify Files — pozostawia `pages[0].image` puste.
- Dla kolejnych stron Gemini wskazuje 2–3 obszary obrazu pasujące do tekstu: postać, gest, detal architektury, niebo, światło, tkaninę, przedmiot lub szerszy kadr atmosferyczny.
- Gemini zwraca wyłącznie plan kadrowania. Reprodukcja nie jest generowana ani retuszowana.
- GicleeApp wycina oryginalne piksele lokalnie przez Pillow, dopasowuje kadr do proporcji pola PDP v3 (`4 / 3.4`) i pilnuje minimalnej rozdzielczości.
- Kandydaci są oceniani pod kątem pewności i różnorodności; niemal identyczne kadry są obniżane w rankingu.
- Przy braku pewnego detalu stosowany jest bezpieczny szerszy kadr.
- Istniejące własne grafiki są w oknie podglądu domyślnie **wyłączone z nadpisania**.
- Panel **SZCZEGÓŁY** oraz `details_image` nie są zmieniane przez tę funkcję.

### Podgląd i zapis

1. Kliknij **AI — dobierz kadry…**.
2. Poczekaj na analizę Gemini i lokalne przygotowanie cropów.
3. Zaznacz strony, dla których mają zostać zapisane grafiki.
4. Użyj **Następny wariant**, aby przełączać propozycje; ostatnim wariantem jest zawsze pełny obraz.
5. Kliknij **Zatwierdź i zapisz do Shopify**.
6. Dopiero wtedy wybrane cropy są wysyłane do Shopify Files, a `custom.story_pages` zostaje zaktualizowany.

### Konfiguracja

W `cursor-api/.env`:

```env
GEMINI_API_KEY=...
```

Klient i retry są współdzielone z komponentem `tytulyai` (`Komponenty/_shared/gemini_client.py`). Klucz nie może trafić do repozytorium ani logów.

Funkcja wymaga Pillow:

```powershell
pip install Pillow
```

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

Proporcje grafiki w motywie: `.giclee-story__frame { aspect-ratio: 4 / 3.4; object-fit: cover; }`.

→ [`README.md`](README.md)
