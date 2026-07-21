# Komponent: losujobraz

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.losuj-produkt.json` — pozycja menu **Losuj Obraz**.

| Plik | Rola |
|------|------|
| `Komponenty/losujobraz/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/losujobraz/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.losujobraz`.

**Szablon:** `templates/page.losuj-produkt.json` · **Podgląd:** `/pages/losuj-produkt`

## Warianty designu w Giclee App

Lista **Wersja** w edytorze Losuj Obraz pełni rolę bezpiecznego selektora wariantów designu:

| Wariant | ID | Efekt |
|---------|----|-------|
| **V1 — podstawowa** | `lo1` / `design_variant: v1` | Dotychczasowy wygląd bez dodatkowej warstwy światła, pyłu i mgiełki. |
| **V2 — atmosfera muzealna** | `lo2` / `design_variant: v2` | Subtelny ivory/champagne glow kursora, oszczędny pył i ambientowa głębia. |

Aktywnym wariantem jest `lo2`. Przełączenie pozycji na liście wczytuje pełny zapis danego wariantu, a **Zapisz** utrwala go w `templates/page.losuj-produkt.json` oraz w danych wariantu. Mechanizm korzysta z istniejącego systemu kopii zapasowych i nie dokłada drugiego, konkurencyjnego selektora.

W Shopify Theme Editor ta sama decyzja jest dostępna jako ustawienie sekcji **Wariant designu**. V1 nie ładuje plików atmosfery; V2 ładuje `giclee-random-artwork-atmosphere.css` i `giclee-random-artwork-atmosphere.js`.

## Własne tło (obraz / film / animacja)

Strefa **Losuj obraz — interfejs** ma dwa pola mediów (drag & drop + „Ostatnie ▾”):

| Pole | Ścieżka JSON | Uwagi |
|------|--------------|-------|
| Własne tło — obraz | `sections.random_artwork.settings.background_image` | ref `shopify://shop_images/…` |
| Kadrowanie tła (góra–dół) | `sections.random_artwork.settings.background_image_object_y` | 0–100 (domyślnie 50) |
| Własne tło — film / animacja | `sections.random_artwork.settings.background_video` | ref `shopify://files/videos/…`; **priorytet nad obrazem** |
| Parallax tła (mysz) | `sections.random_artwork.settings.background_parallax` | checkbox; subtelny ruch obrazu/filmu jak w konfiguratorze PDP (`MAX_X=22`, `MAX_Y=14`, `EASE=0.075`) |

Puste oba pola = domyślna scena (aurora + WebGL). Logika wyboru jest w motywie:
`sections/giclee-random-artwork.liquid` liczy `custom_bg` (`video` › `image` › `none`) i renderuje
warstwę `.giclee-random-artwork__custom-bg` przez snippet `snippets/background-media.liquid`
(styl: `assets/giclee-random-artwork.css`). Film odtwarza `video-background-component`
(`assets/video-background.js`, ładowany globalnie w `snippets/scripts.liquid`).

Pola mediów obsługuje wspólny edytor (`_shared/theme_page_editor/gui_shell.py`, gałąź
`shopify_image`/`shopify_video`); upload wideo przez `service_base.upload_video`.

Parallax: `background_parallax` włącza klasę `grw--custom-bg-parallax` i logikę w
`assets/giclee-random-artwork.js` (`initCustomBgParallax`) — te same parametry co
`initConfigBg` w `giclee-product-story.js`. Działa dla obrazu i filmu w tle.

→ [`README.md`](README.md) · wzorzec: [`stronaglowna.md`](stronaglowna.md)
