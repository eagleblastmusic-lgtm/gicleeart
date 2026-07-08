# Komponent: stronaglowna



**Cel:** Zarządzanie treścią i grafiką **strony głównej** sklepu (`gicleeart.eu`) — bez ręcznej edycji `templates/index.json` w Theme Editor.



| Plik | Rola |

|------|------|

| `Komponenty/stronaglowna/gui.py` | Lista sekcji, miniaturki, edytor, podgląd, historia, deploy |

| `Komponenty/stronaglowna/service.py` | Odczyt/zapis JSON, backup, upload, `shopify theme push` |

| `Komponenty/stronaglowna/home_features.py` | Diff, walidacja, skan sekcji, theme dev, assets motywu |

| `Komponenty/_shared/deploy_targets.py` | Cele deploy motywu (development / unpublished / live) — wspólne z edytorem stron menu |

| `Komponenty/stronaglowna/registry.py` | Mapowanie stref → ścieżki w szablonie / ustawieniach |

| `Komponenty/stronaglowna/homepage_variants.py` | Warianty strony głównej (home1–home4) — osobne kopie JSON |



Tryb: `inline` (w launcherze GicleeApp, sekcja **Administracja strony** — przycisk «← Powrót» zamiast osobnego okna). Nadal można uruchomić osobno: `python -m Komponenty.stronaglowna`.



---



## Sekcje



| Strefa w GicleeApp | Źródło | Co edytujesz |

|--------------------|--------|--------------|

| Hero — slideshow | `index.json` | **Grafika**, **film** (z opcją boomerang) lub **kolaż wideo** (przycisk «Edytuj kolaż wideo…» → osobne okno); **Z listy…** — wybór z filmów w Shopify Files |

| Giclée Art — intro | `index.json` | Portret, **nagłówek + treść** (plain text → HTML); **Efekty…** (wszystkie typy) |

| Odrestaurowywanie / korekcja / potencjał / zobacz różnicę | `index.json` | Teksty, suwaki przed/po, CTA, **Tło…**; **Efekty…** (wszystkie typy) |

| **Powiadomienie modalne** | `config/settings_data.json` | Site notice: wł./wył., wersja, tytuł, treść, przycisk |



**Kolaż wideo — przejścia:** każdy klip ma osobno **Wejście** (`transition_in` + `transition_in_ms`) i **Wyjście** (`transition_out` + `transition_out_ms`). Czas wyjścia = długość efektu i moment startu przed końcem klipu. **Cross effect** (od klipu 2) odtwarza wyjście poprzedniego i wejście bieżącego równocześnie — każde ze swoim czasem ms.

**Filmy hero/kolaż** nie leżą w repozytorium — tylko referencje `shopify://files/videos/…` w JSON. Pliki są w **Shopify Files** (chmura). W oknie **Z listy…**: dwuklik = podgląd, **Zmień nazwę…** / **Usuń** (Shopify Admin API). Po zmianie nazwy pliku zaktualizuj odwołania w hero/kolażu; przy usunięciu — wybierz inny film lub wgraj ponownie.



---



## Przepływ



1. GicleeApp → **Strona główna** → w comboboxie wybierz **Strona Główna 1** lub **Strona Główna 2** (osobne kopie treści).

2. Wybierz sekcję z listy po lewej.

3. Grafiki: **Wgraj grafikę…** / **Usuń grafikę** (lub **Usuń film…**) przy każdym polu graficznym; **Pobierz…** (Hero) lub przeciągnij plik na miniaturę (`tkinterdnd2`). **Tło…** — osobne okno: wybór **Grafika** / **Film**, upload do Shopify Files (ustawia `background_media` + `background_image` lub `video` w `index.json`), suwak **Przyciemnienie (gradient)** 0–100% + **Wyłącz przyciemnienie** + **Usuń tło** (zapis → `background_overlay_pct` w ustawieniach sekcji; domyślnie 100% przy nowym tle, 0 gdy brak tła).

4. Tekst: pola **Nagłówek** i **Treść** — komponent składa HTML (`<h2>`, `<p>`).

5. **Zapisz** — dialog diff + walidacja; kopia w `data/backups/index-YYYYMMDD-HHMMSS.json` (+ `settings-*.json`); zapis trafia też do aktywnego wariantu.

6. **Historia wersji…** — przywracanie kopii jednym kliknięciem.

7. **Podgląd live** — URL z `?giclee_skip_splash=1&giclee_skip_notice=1` (pomija splash i modal). Lokalny podgląd motywu: **Theme dev…** w pasku narzędzi launchera (`http://127.0.0.1:9292/` + te same parametry).

8. **Wdróż motyw…** — wybór celu: development / unpublished / live (`shopify.theme.toml`).

9. **Odśwież wariant** — ponowne wczytanie bieżącego wariantu z magazynu (bez dotykania drugiego wariantu).



Przy starcie: **skan index.json** — raport, gdy sekcja ma inne ID niż w `registry.py`.



---



## Warianty strony głównej



Combobox u góry okna wybiera wersję (domyślnie `home1`–`home4`, kolejne jako `home5`, `home6`, …). Obok comboboxa:

- **Dodaj nową…** — kopiuje bieżącą wersję (w tym niezapisane zmiany w edytorze) pod nową nazwą; po utworzeniu przełącza edytor na kopię.
- **Zmień nazwę…** — zmienia etykietę aktywnej wersji w comboboxie (ID `homeN` pozostaje bez zmian).

Każdy wariant ma własną kopię `index.json`, `settings.json` i opcjonalnie `mobile_hero.webp`.



| Ścieżka | Zawartość |

|---------|-----------|

| `Komponenty/stronaglowna/data/variants/manifest.json` | Aktywny wariant, lista etykiet, opcjonalnie `home_stack` per wariant |

| `…/variants/home1/` | Dane wariantu 1 |

| `…/variants/home2/` | Wariant 2 (niezależna kopia po zapisie) |
| `…/variants/home3/` | Wariant 3 — scroll-over stack (niezależna kopia po zapisie) |
| `…/variants/home4/` | Wariant 4 — kopia startowa home3 (niezależna po zapisie) |
| `…/variants/homeN/` | Kolejne wersje utworzone przez «Dodaj nową…» |



Przy **pierwszym uruchomieniu** komponent kopiuje bieżące pliki motywu do `home1`, a następnie duplikuje je do `home2`. Przełączenie wariantu zapisuje stan bieżącego wariantu, podmienia pliki motywu (`templates/index.json`, `config/settings_data.json`, mobile hero) i wczytuje edytor. Edycja w wariancie 2 nie zmienia danych wariancu 1.

Przy starcie komponent **uzupełnia brakującą pętlę boomerang** w sklonowanych wariantach (np. `home2` z `home1`), jeśli mają ten sam film bazowy, a pole `video_1_reversed` jest puste.

Przy starcie komponent wczytuje aktywny wariant do edytora (bez automatycznego nadpisywania plików motywu). Motyw synchronizuje się przy **przełączeniu wariantu**, **Zapisz** lub **Historia → Przywróć**. Przy przełączeniu bez niezapisanych zmian poprzedni wariant nie jest zapisywany na dysk.

**Scroll-over stack:** warianty z `home_stack: true` w manifeście (domyślnie `home3`/`home4`; kopia takiego wariantu dziedziczy flagę) — przy zapisie / przełączeniu komponent ustawia `window.GICLEE_HOME_STACK = true` w `assets/giclee-home-sections.js`. Motyw ładuje `giclee-home-stack.css` + `giclee-home-stack.js`: warstwy **1→6** (hero → zobacz różnicę) jadą nad menu i nad poprzednią sekcją (`sticky` + rosnący `z-index`). Separatory między warstwami mają ten sam `z-index` co następna sekcja i przewijają się razem z nią (bez ukrywania). Na touch / reduced-motion efekt wyłączony.

**Efekty sekcji (universal):** przycisk **Efekty…** przy każdej sekcji z hookiem motywu (hero, intro, restoration, …). Jedno okno: combobox **Sekcja** + zakładki **typów efektów** (reveal, hover tekstu, gradient BIO, parallax). Wszystkie typy dostępne dla każdej sekcji — włączasz per zakładka. Rejestr: `home_effects_registry.py` (`HOME_EFFECT_TYPES` + `register_home_effect_type()` — nowy pakiet efektów = nowa zakładka). Panele UI: `home_effect_panels.py`. Storage: `section_effects_storage.py` (legacy: `studio-reveal.json` / `final-difference.json` dla intro / see-difference; pozostałe hooki → `section-effects.json`). Eksport: `GICLEE_HOME_STUDIO_REVEAL_CONFIG`, `GICLEE_HOME_FINAL_DIFFERENCE_CONFIG`, `GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG`, `GICLEE_HOME_SECTION_EFFECTS_CONFIG` w `assets/giclee-home-sections.js`.

**Przejścia (osobno):** przycisk **Przejścia…** na dolnym pasku — zakładki **Między sekcjami** (section-scroll, `scroll.json`) i **Warstwy (stack)** (`home_stack` w manifeście). Nie miesza się z efektami sekcji.

**Section-scroll (szczegóły):** combobox **Preset** (Galeria domyślny, Editorial kontemplacyjny, Kinowy, Dynamiczny premium, Miękki editorial, **GPT** — wypełnia formularz bez auto-zapisu), kill switch (`enabled`), desktop on/off, tryb mobile (`native`/`soft`/`disabled`), czasy animacji (min/max), suwak **Dynamika ruchu** (`motionDynamics` 0–100), progi gestów (wheel/touch), offsety headera i separatora, tryb reduced-motion (`instant`/`off`), debug, **Miękkie osadzenie nagłówka** (`headingSettle`). Przyciski: **Zapisz**, **Przywróć domyślne (scroll)**, **Wyłącz awaryjnie**, **Podgląd live**.

Front section-scroll: `assets/giclee-home-section-scroll.js/.css` — dock z viewportu, scroll w górę z dwuetapową logiką runway, okno ciszy kierunkowe (opis: [`docs/motyw/strona-glowna.md`](../../../docs/motyw/strona-glowna.md)). Testy: `tests/test_stronaglowna_scroll.py`.



---



## Walidacja przed zapisem / deployem



- Puste nagłówki/treść przy włączonej sekcji

- Brak obrazu w suwaku przed/po lub hero (boomerang: `video_1_reversed` = jeden plik `_boomerang.mp4`)

- Site notice włączony bez treści

- CTA z etykietą bez linku, nietypowy URL

- Brak pliku mobile hero w motywie

- Przed zapisem `index.json` / wariantu: `repair_color_correction_cta_blocks()` uzupełnia brakujące `type`/`name` w grupie przycisków CTA sekcji korekcji kolorystycznej (`group_PKPWxV`) — zapobiega błędowi Shopify „brak pola typu” przy deployu



---



## Site notice (modal)



Okno informacyjne na stronie głównej po pierwszym wejściu. Pola w sekcji «Powiadomienie modalne»:



- `site_notice_enabled`, `site_notice_version`, `site_notice_title`, `site_notice_message`, `site_notice_button`

- Zmiana **wersji** (np. 1 → 2) pokazuje modal ponownie (localStorage w przeglądarce).

- Podgląd dev: `?giclee_skip_notice=1` pomija modal.



Motyw: `snippets/giclee-site-notice.liquid`.



---



## Stabilne hooki motywu



Przy zapisie komponent aktualizuje:



- `assets/giclee-home-sections.js` — mapa hook → ID sekcji

- `assets/giclee-home-mobile.js` — lista plików mobile hero

- `assets/giclee-home-sections-boot.js` — `data-giclee-home`, intro/see-difference (legacy globals), **`GICLEE_HOME_SECTION_EFFECTS_CONFIG`** (scroll reveal + hover tekstu per hook), **`GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG`** (gradient + parallax; pomijane gdy sekcja ma już studio reveal)



CSS: `assets/custom.css` używa `[data-giclee-home="intro"]` (z fallbackiem na stare ID).



---



## Deploy (`shopify.theme.toml`)



| Środowisko | Theme ID |

|------------|----------|

| `development` | 200713503068 («GicleeApp dev») |

| `unpublished` | 199521829212 |

| `live` | 197314249052 (wymaga `--allow-live`) |



Motyw: [`docs/motyw/strona-glowna.md`](../../../docs/motyw/strona-glowna.md).

