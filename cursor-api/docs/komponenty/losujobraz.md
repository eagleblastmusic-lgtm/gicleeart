# Komponent: losujobraz

**Cel:** edycja wyglądu i treści `templates/page.losuj-produkt.json` dla pozycji menu **Losuj Obraz**.

Tryb: `inline` w sekcji **Administracja strony**. Uruchomienie: `python -m Komponenty.losujobraz`. Podgląd: `/pages/losuj-produkt`.

## Warianty designu w Giclee App

Lista **Wersja** jest selektorem pełnych wariantów strony:

| Wariant | ID | Efekt |
|---|---|---|
| **V1 — podstawowa** | `lo1` / `v1` | Baza bez Living Museum Light. |
| **V3 — Living Museum Light** | `lo3` / `v3` | Reflektor galerii, zoptymalizowany pył i muzealna tabliczka artysta / tytuł / rok. |
| **V4 — finał muzealny** | `lo4` / `v4` | Zachowuje V3 i dodaje ceremonialny handoff zwycięzcy, większy eksponat, portal → halo, lżejszą oprawę oraz kuratorską hierarchię typografii i akcji. |
| **V5 — V4 + dym kursora** | `lo5` / `v4` + smoke | Niezależna kopia V4 z Elegant Fluid (dym kursora). Theme nadal używa `design_variant: "v4"`. |
| **V6 — na bazie V5** | `lo6` / `v4` + smoke | Robocza kopia V5 (te same efekty i ustawienia startowe). |

Aktywnym wariantem jest **`lo6`**. **Zapisz** utrwala bieżący wariant i aktywny szablon przez istniejący workflow kopii zapasowej i zapisu edytora stron.

> Dawny wariant **V2 — atmosfera muzealna** (glow/mgła/pył V2) został usunięty z GicleeApp — nie jest używany przez aktywny stos V3–V6.

### Stan domyślny V6 (bieżący, jak V5)

| Efekt | Stan | Kiedy się pojawia |
|---|---|---|
| Parallax tła | **włączony** | od razu (tracking kursora) |
| Film→obraz: przenikanie | lead **1400 ms** / hold **1400 ms** | końcówka filmu tła (gdy film + obraz) |
| Living Light (reflektor) | **wyłączony** | — |
| Living Dust (pył) | **włączony** | po zakończeniu animacji złotego okręgu intro |
| Dym kursora (fluid) | **włączony** | po zakończeniu animacji złotego okręgu intro |
| Odkrycie maski (hover BG2) | wyłączone | — |

Sygnał runtime: `data-intro-circle-done="true"` (ustawiany po spinie okręgu, ~4,8 s od startu letter-fade nagłówka).

## Choreografia intro (timing)

1. **0 ms** — letter-fade nagłówka (+ scale 1.2 → 1, ~2,2 s).
2. **~1 s** — letter-fade podtytułu.
3. **~2 s** — start spinu złotego okręgu (`PORTAL_REVEAL_MS` = 2,8 s).
4. **~4,8 s** — koniec spinu → `data-intro-circle-done` → start **pyłu** i **dymu**; potem kreska eyebrow.
5. **~5,7 s** — fade-in przycisku «Losuj obraz».

Po kliknięciu Losuj:

1. Faza «Przeszukuję kolekcję…» — litery ~30% opacity, fala rozświetlenia do 100%; min. widoczność ~1,6 s.
2. Start wirowania obrazów — napis i pierścień intro robią **fade-out** w miejscu; ringi WebGL pojawiają się w scenie 3D.
3. Wynik V4 — ceremonialny handoff (frame → identity → actions).

## Edytuj atmosferę…

Living Museum Light (V3–V6):

- `living_light_enabled` — reflektor kursora (w V5/V6 domyślnie off);
- `living_dust_enabled` — pył ambientowy (start po okręgu);
- `living_light_intensity`, `living_dust_*` — strojenie.

Parallax w V3–V6 działa niezależnie od reflektora.

## Losuj obraz — tło i pula

Poza obrazem/filmem i parallaxem:

- `bg_video_crossfade_lead_ms` — start przenikania na żywym filmie (ms przed końcem);
- `bg_video_crossfade_hold_ms` — dalsze przenikanie na zawieszonej ostatniej klatce;
- suma = pełny czas fade (`--grw-bg-video-fade-ms`).

## V5 — dym kursora

Jedna sekcja **V5 — włącz/wyłącz dym** (toolbar: «Dym kursora V5…»):

- `cursor_smoke_enabled` — włącznik;
- preset, jakość, suwaki i auto-smugi — w tej samej strefie.

Montaż canvasa dymu jest opóźniony do `data-intro-circle-done`.

## Fine Art Oracle…

- teksty intro, faz losowania, wyniku i błędu;
- `galaxy_btn_variant` — glow przycisku (`v1` / `v2` — to wersja **przycisku**, nie designu strony);
- `enable_webgl`, `draw_loading_ms`, `draw_phase_hold_ms`.

## Pliki danych

- manifest: `Komponenty/losujobraz/data/variants/manifest.json` (`active: lo6`);
- warianty: `lo1`, `lo3`, `lo4`, `lo5`, `lo6`;
- aktywny szablon: `templates/page.losuj-produkt.json`;
- mapowanie pól: `Komponenty/losujobraz/registry.py`;
- skrót panelu: `Komponenty/losujobraz/gui.py`.

Kod motywu: `docs/motyw/losuj-obraz.md`.
