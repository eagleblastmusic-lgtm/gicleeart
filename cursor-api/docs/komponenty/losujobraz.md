# Komponent: losujobraz

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.losuj-produkt.json` — pozycja menu **Losuj Obraz**.

| Plik | Rola |
|------|------|
| `Komponenty/losujobraz/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/losujobraz/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.losujobraz`.

**Szablon:** `templates/page.losuj-produkt.json` · **Podgląd:** `/pages/losuj-produkt`

**Warianty:** domyślnie jedna wersja (`lo1`); **Dodaj nową…** kopiuje bieżącą.

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
