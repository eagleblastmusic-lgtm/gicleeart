# Komponent: losujobraz

**Cel:** edycja wyglądu i treści `templates/page.losuj-produkt.json` dla pozycji menu **Losuj Obraz**.

Tryb: `inline` w sekcji **Administracja strony**. Uruchomienie: `python -m Komponenty.losujobraz`. Podgląd: `/pages/losuj-produkt`.

## Warianty designu w Giclee App

Lista **Wersja** jest selektorem pełnych wariantów strony:

| Wariant | ID | Efekt |
|---|---|---|
| **V1 — podstawowa** | `lo1` / `v1` | Baza bez dodatkowej warstwy atmosfery. |
| **V2 — atmosfera muzealna** | `lo2` / `v2` | Edytowalny glow, mgiełka i pył V2. |
| **V3 — Living Museum Light** | `lo3` / `v3` | Reflektor galerii, zoptymalizowany pył i muzealna tabliczka artysta / tytuł / rok. |
| **V4 — finał muzealny** | `lo4` / `v4` | Zachowuje V3 i dodaje ceremonialny handoff zwycięzcy, większy eksponat, portal zmieniający się w halo, lżejszą oprawę oraz kuratorską hierarchię typografii i akcji. |

Aktywnym wariantem jest `lo4`. **Zapisz** utrwala bieżący wariant i aktywny szablon przez istniejący workflow kopii zapasowej i zapisu edytora stron.

## Edytuj atmosferę…

Przycisk na pasku narzędzi otwiera strefę ustawień atmosfery bieżącego wariantu.

V2 zachowuje szczegółowe parametry glow, mgiełki i pyłu. V3 i V4 współdzielą parametry Living Museum Light:

- `living_light_enabled` — włącz reflektor;
- `living_dust_enabled` — włącz pył ambientowy;
- `living_light_intensity` — intensywność światła;
- `living_dust_particles` — liczba drobinek;
- `living_dust_opacity` — widoczność;
- `living_dust_size` — rozmiar;
- `living_dust_speed` — szybkość;
- `living_dust_fps` — limit FPS;
- `living_dust_dpr_cap` — limit jakości canvasu.

V1 i V2 zachowują wartości Living Museum Light w JSON, ale ich nie uruchamiają. Dzięki temu przełączanie wariantów nie kasuje strojenia.

## Finał V4

V4 korzysta z osobnego modułu WebGL końcówki bez przebudowy wspólnego modelu losowania. Zwycięzca stabilizuje się i rośnie, pozostałe karty odchodzą w głąb, a portal traci pierścienie i przechodzi w owalne światło ekspozycyjne. Po handoffie wynik ujawnia kolejno oprawę, artystę i tytuł, a następnie akcje.

„Zobacz obraz” jest głównym ciemnym przyciskiem galeryjnym. „Wylosuj ponownie” pozostaje lekką akcją drugorzędną. Reset czyści etapy i timery przed kolejnym losowaniem.

## Własne tło

Strefa **Losuj obraz — interfejs** obsługuje obraz, film i `background_parallax`. W V1/V2 parallax pozostaje w głównym kontrolerze. W V3/V4 ten sam model pozycji wskaźnika steruje reflektorem, pyłem i parallaxem, dzięki czemu nie powstaje drugi globalny listener ani konkurująca pętla RAF.

## Pliki danych

- manifest: `Komponenty/losujobraz/data/variants/manifest.json`;
- warianty: `lo1`, `lo2`, `lo3`, `lo4`;
- aktywny szablon: `templates/page.losuj-produkt.json`;
- mapowanie pól: `Komponenty/losujobraz/registry.py`;
- skrót panelu: `Komponenty/losujobraz/gui.py`.

Kod motywu i pełny kontrakt V4 opisuje `docs/motyw/losuj-obraz.md`.
