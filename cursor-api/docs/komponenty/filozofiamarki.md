# Komponent: filozofiamarki

**Cel:** Zarządzanie faktycznie używaną animacją scrollowaną 60 FPS i jej treściami na stronie **Filozofia marki**.

| Plik | Rola |
|------|------|
| `Komponenty/filozofiamarki/registry.py` | Jakość, intro/outro, profil ruchu, ustawienia adapterów oraz alfa/tło |
| `Komponenty/filozofiamarki/gui.py` | Edytor strony oraz panel łatwej podmiany filmu |
| `Komponenty/filozofiamarki/motion_config.py` | Kanoniczne mapowanie katalogu presetów i walidacja |
| `Komponenty/filozofiamarki/video_sequence.py` | FFprobe/FFmpeg → WebP lub MP4, metadane 60 FPS/alfa, manifest i backup |
| `Komponenty/_shared/theme_page_editor/` | Wspólny edytor, pełne presety, wykrywanie ustawień własnych i przywracanie rekomendacji |

Tryb: `inline` (sekcja **Administracja strony**). Uruchomienie: `python -m Komponenty.filozofiamarki`.

**Szablon:** `templates/page.filozofia-marki.json` · **Podgląd:** `/pages/filozofia-marki`

**Warianty:** `fm1` (Wersja 1), `fm2` (Wersja 2); **Dodaj nową…** kopiuje bieżącą.

## Podmiana wideo

1. Kliknij **Wybierz i przygotuj wideo…** albo upuść film na panel.
2. Wskaż plik MP4, WebM, MOV lub MKV.
3. Wybierz `Film MP4` albo `Klatki WebP` oraz `720p` albo `1080p`.
4. Komponent generuje tylko wybrany wariant przy 60 FPS i aktualizuje jego manifest.
5. Poprzedni wariant trafia do rotacyjnej kopii ZIP (zachowywane są trzy ostatnie).
6. Użyj wdrożenia w edytorze, aby wysłać manifest, renderer i zasoby.

Film może mieć przezroczystość. WebM z VP9 jest dekodowany przez `libvpx-vp9`, aby zachować kanał alfa.

Aktywny wariant wybierasz polami **Sposób odtwarzania** i
**Jakość wyświetlania**. Klatki 720p i 1080p są zapisywane jako WebP RGBA;
1080p używa jakości 95, aby nie zmieniać kolorów jak JPEG. Filmy 720p i 1080p
mają klatkę kluczową na każdej klatce, dzięki czemu `<video>` może być
synchronizowane ze scrollem również podczas cofania.

## Charakter odtwarzania

Profil ruchu jest wspólny dla wybranego źródła 720p/1080p. Panel udostępnia:
preset, tempo, easing/Bézier, smoothing, lag, bezwładność, damping, limit
nadrabiania, zachowanie zatrzymania, kierunek, zakres materiału, interpolację,
końcowe płynne domknięcie hamowania, dead zone MP4/WebP, rounding, preload i
cache. Ręczna zmiana przełącza preset na **Własne ustawienia**, a
**Przywróć zalecane ustawienia** ustawia **Delikatny luksusowy**. Płynne
domknięcie odmierza oryginalne klatki według FPS źródła; nie miesza pikseli i
nie dodaje smug do kanału alfa.

Runtime ma jeden wspólny scheduler `requestAnimationFrame`. MP4 utrzymuje
wyłącznie najnowszy seek, a WebP używa kolejki target-first i ograniczonego LRU.
Szczegóły, diagnostyka oraz dokładne wartości presetów są w dokumentacji
kanonicznej.

→ [`README.md`](README.md) · wzorzec uniwersalny:
[`Film-scroll.md`](../../../docs/Film-scroll.md) · instrukcja dla AI:
[`Film-scroll-AI-Integration-Guide.md`](../../../docs/Film-scroll-AI-Integration-Guide.md)
