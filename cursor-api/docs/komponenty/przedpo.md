# Komponent: przedpo

**Cel:** Zarządzanie porównaniem «przed / po obróbce» na PDP (szablon `szablon-produktu-v2`).

| Plik | Rola |
|------|------|
| `gui.py` | Lista produktów, podgląd, upload / usuwanie grafiki «przed» |
| `service.py` | Shopify Files + metafield, wykrywanie obrazu Full |

Tryb: `subprocess`. Sekcja launchera: **Administracja produktu** (po «Informacje o plikach»).

## Źródła grafik

| Warstwa | Skąd |
|---------|------|
| **Po obróbce** | Obraz **Full** w galerii produktu (już wgrany przez «Dodaj obraz») — nie uploadujesz ponownie |
| **Przed obróbką** | Wgrywasz w tym komponencie → Shopify Files → metafield `custom.before_retouch_url` |

Sekcja motywu `product-before-after-compare` pokazuje suwak tylko gdy są **oba**: metafield «przed» + Full w galerii. **Motyw live** musi zawierać pliki sekcji (deploy `shopify theme push`).

## Workflow

1. Uruchom kafelek **Przed/Po** w GicleeApp.
2. Wybierz produkt (filtr, sortowanie, checkbox «Tylko bez grafiki przed»).
3. Po wyborze: podgląd «po» (Full) i «przed» (jeśli jest).
4. **Wgraj grafikę «przed»…** — wybierz plik albo **przeciągnij go** na pole «Przed obróbką» (wymaga `tkinterdnd2`).
5. Na froncie (produkt ze szablonem v2) sekcja pojawi się nad «Proces produkcji».

→ [`README.md`](README.md)
