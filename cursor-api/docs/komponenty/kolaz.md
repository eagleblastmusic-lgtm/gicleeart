# Kreator kolaży (`kolaz`)

Zaawansowany kreator kolaży w GicleeApp — składanie wielu obrazów w jedną grafikę (Pillow, bez AI).

## UI

Launcher → **Marketing** → **Kreator kolaży**

### Źródła

- **Kolekcja Shopify** — pobiera miniatury produktów (do 24 unikalnych zdjęć)
- **Pliki lokalne** — wybór z dysku lub drag-and-drop (gdy `tkinterdnd2`)
- Lista obrazów z podwójnym kliknięciem = włącz/wyłącz kafelek w kolażu

### Ustawienia

| Grupa | Opcje |
|-------|--------|
| Płótno | presety (BIO 2400×1200, Full HD, kwadrat IG, banner, 4K), wymiary własne |
| Układ | muzealny, redakcyjny, siatka, hero, panorama, losowy (seed) |
| Kafelki | liczba, skala, **rozstawienie** (suwak), obrót, ramka, cień |
| Tło | kolor, opcjonalny gradient |

### Eksport i BIO

- **Generuj podgląd** — render w wątku, podgląd w oknie
- **Zapisz…** — JPG / WebP / PNG
- **Folder eksportów** — `Komponenty/kolaz/data/exports/`
- **→ Tło BIO** — zapis tymczasowy + upload przez `tldobio.upload_bio_background()` (wymaga wcześniejszego załadowania kolekcji)

## Kod

| Plik | Rola |
|------|------|
| `layouts.py` | Szablony pozycji kafelków |
| `compositor.py` | Render (cover, ramki, cień, tło) |
| `service.py` | Shopify, eksport, integracja BIO |
| `gui.py` | Interfejs Tkinter |

## Powiązane

- [`tldobio.md`](tldobio.md) — przypisanie tła do sekcji biografii
- [`../../docs/motyw/kolekcja-autora-showcase.md`](../../docs/motyw/kolekcja-autora-showcase.md)
