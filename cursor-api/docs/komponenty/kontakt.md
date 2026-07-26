# Komponent: kontakt

**Cel:** Edycja wyglądu i treści szablonu motywu `templates/page.contact.json` — pozycja menu **Kontakt**.

| Plik | Rola |
|------|------|
| `Komponenty/kontakt/registry.py` | Mapowanie stref → ścieżki JSON |
| `Komponenty/kontakt/gui.py` | Cienka warstwa → `_shared/theme_page_editor` |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor (warianty, backup, deploy) |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.kontakt`.

**Szablon:** `templates/page.contact.json` · **Podgląd:** `/pages/contact`

**Warianty:** domyślnie jedna wersja (`ko1`); **Dodaj nową…** kopiuje bieżącą.

## Strefy

1. **Hero — Kontakt** — nagłówek + grafika hero
2. **Tło pod hero** — jak w FAQ: typ (grafika / gradient), wersja gradientu, plik tła, rozmycie, saturacja, jasność, nakładka przyciemniająca, powiększenie kadru → `giclee_contact_bg_*` + `background_*` w sekcji `form`
3. **Formularz kontaktowy** — etykieta przycisku

**Pole grafiki (`shopify_image`, wspólne dla wszystkich edytorów stron):**
- **Wgraj…** — wybór pliku (JPG/PNG/WebP) → upload do Shopify Files.
- **Drag & drop** — upuszczenie pliku na miniaturę/wiersz pola wgrywa grafikę (wymaga `tkinterdnd2`; bez niego degraduje bez błędu).
- **Ostatnie ▾** — lista ostatnio użytych grafik (historia w `Komponenty/_shared/data/recent_images.json`, moduł `_shared/recent_images.py`); klik ustawia ref.
- **Kadrowanie góra–dół** — suwak + skróty Góra / Środek / Dół (0–100%, domyślnie 50). Zapis w JSON jako `{klucz_obrazu}_object_y` obok refa (np. `image_1_object_y`). Motyw: `object-position: center Y%` (`snippets/giclee-image-object-position*.liquid`).

Implementacja: `_shared/theme_page_editor/image_object_y.py`, `gui_shell.py` (strony menu), `stronaglowna/gui.py` (strona główna + tło sekcji).

→ [`README.md`](README.md) · wzorzec: [`faq.md`](faq.md) (Tło pod hero) · [`stronaglowna.md`](stronaglowna.md)
