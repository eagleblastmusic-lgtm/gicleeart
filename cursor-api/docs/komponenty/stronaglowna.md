# Komponent: stronaglowna



**Cel:** Zarządzanie treścią i grafiką **strony głównej** sklepu (`gicleeart.eu`) — bez ręcznej edycji `templates/index.json` w Theme Editor.



| Plik | Rola |

|------|------|

| `Komponenty/stronaglowna/gui.py` | Lista sekcji, miniaturki, edytor, podgląd, historia, deploy |

| `Komponenty/stronaglowna/service.py` | Odczyt/zapis JSON, backup, upload, `shopify theme push` |

| `Komponenty/stronaglowna/home_features.py` | Diff, walidacja, skan sekcji, theme dev, assets motywu |

| `Komponenty/stronaglowna/registry.py` | Mapowanie stref → ścieżki w szablonie / ustawieniach |

| `Komponenty/stronaglowna/homepage_variants.py` | Warianty strony głównej (home1 / home2) — osobne kopie JSON |



Tryb: `inline` (w launcherze GicleeApp, sekcja **Administracja strony** — przycisk «← Powrót» zamiast osobnego okna). Nadal można uruchomić osobno: `python -m Komponenty.stronaglowna`.



---



## Sekcje



| Strefa w GicleeApp | Źródło | Co edytujesz |

|--------------------|--------|--------------|

| Hero — slideshow | `index.json` | **Grafika**, **film** (z opcją boomerang) lub **kolaż wideo** (przycisk «Edytuj kolaż wideo…» → osobne okno); **Z listy…** — wybór z filmów w Shopify Files |

| Giclée Art — intro | `index.json` | Portret, **nagłówek + treść** (plain text → HTML) |

| Odrestaurowywanie / korekcja / potencjał / zobacz różnicę | `index.json` | Teksty, suwaki przed/po, CTA (w korekcji: wł./wył. przyciski) |

| **Powiadomienie modalne** | `config/settings_data.json` | Site notice: wł./wył., wersja, tytuł, treść, przycisk |



**Kolaż wideo — przejścia:** każdy klip ma osobno **Wejście** (`transition_in` + `transition_in_ms`) i **Wyjście** (`transition_out` + `transition_out_ms`). Czas wyjścia = długość efektu i moment startu przed końcem klipu. **Cross effect** (od klipu 2) odtwarza wyjście poprzedniego i wejście bieżącego równocześnie — każde ze swoim czasem ms.

**Filmy hero/kolaż** nie leżą w repozytorium — tylko referencje `shopify://files/videos/…` w JSON. Pliki są w **Shopify Files** (chmura). W oknie **Z listy…**: dwuklik = podgląd, **Zmień nazwę…** / **Usuń** (Shopify Admin API). Po zmianie nazwy pliku zaktualizuj odwołania w hero/kolażu; przy usunięciu — wybierz inny film lub wgraj ponownie.



---



## Przepływ



1. GicleeApp → **Strona główna** → w comboboxie wybierz **Strona Główna 1** lub **Strona Główna 2** (osobne kopie treści).

2. Wybierz sekcję z listy po lewej.

3. Grafiki: **Wgraj grafikę…** / **Pobierz…** (Hero) lub przeciągnij plik na miniaturę (`tkinterdnd2`).

4. Tekst: pola **Nagłówek** i **Treść** — komponent składa HTML (`<h2>`, `<p>`).

5. **Zapisz** — dialog diff + walidacja; kopia w `data/backups/index-YYYYMMDD-HHMMSS.json` (+ `settings-*.json`); zapis trafia też do aktywnego wariantu.

6. **Historia wersji…** — przywracanie kopii jednym kliknięciem.

7. **Podgląd live** / **Theme dev…** — URL z `?giclee_skip_splash=1&giclee_skip_notice=1` (pomija splash i modal). Lokalnie: `http://127.0.0.1:9292/` + te same parametry.

8. **Wdróż motyw…** — wybór celu: development / unpublished / live (`shopify.theme.toml`).

9. **Odśwież wariant** — ponowne wczytanie bieżącego wariantu z magazynu (bez dotykania drugiego wariantu).



Przy starcie: **skan index.json** — raport, gdy sekcja ma inne ID niż w `registry.py`.



---



## Warianty strony głównej



Combobox u góry okna: **Strona Główna 1** (`home1`) i **Strona Główna 2** (`home2`). Każdy wariant ma własną kopię `index.json`, `settings.json` i opcjonalnie `mobile_hero.webp`.



| Ścieżka | Zawartość |

|---------|-----------|

| `Komponenty/stronaglowna/data/variants/manifest.json` | Aktywny wariant + lista etykiet |

| `…/variants/home1/` | Dane wariantu 1 |

| `…/variants/home2/` | Kopia startowa wariantu 1 (niezależna po zapisie) |



Przy **pierwszym uruchomieniu** komponent kopiuje bieżące pliki motywu do `home1`, a następnie duplikuje je do `home2`. Przełączenie wariantu zapisuje stan bieżącego wariantu, podmienia pliki motywu (`templates/index.json`, `config/settings_data.json`, mobile hero) i wczytuje edytor. Edycja w wariancie 2 nie zmienia danych wariancu 1.

Przy starcie komponent **uzupełnia brakującą pętlę boomerang** w `home2`, jeśli ma ten sam film bazowy co `home1`, a pole `video_1_reversed` jest puste (naprawa po wcześniejszym błędzie edytora).

Przy starcie **nie nadpisuje** plików motywu aktywnym wariantem — tylko wczytuje wariant do edytora. Motyw (`index.json`) zmienia się przy **przełączeniu wariantu** lub **Zapisz**. Warianty **nie synchronizują** między sobą treści hero — każdy ma własny zapis w `data/variants/`.



---



## Walidacja przed zapisem / deployem



- Puste nagłówki/treść przy włączonej sekcji

- Brak obrazu w suwaku przed/po lub hero (boomerang: `video_1_reversed` = jeden plik `_boomerang.mp4`)

- Site notice włączony bez treści

- CTA z etykietą bez linku, nietypowy URL

- Brak pliku mobile hero w motywie



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

- `assets/giclee-home-sections-boot.js` — ustawia `data-giclee-home` na sekcjach



CSS: `assets/custom.css` używa `[data-giclee-home="intro"]` (z fallbackiem na stare ID).



---



## Deploy (`shopify.theme.toml`)



| Środowisko | Theme ID |

|------------|----------|

| `development` | 200713503068 («GicleeApp dev») |

| `unpublished` | 199521829212 |

| `live` | 197314249052 (wymaga `--allow-live`) |



Motyw: [`docs/motyw/strona-glowna.md`](../../../docs/motyw/strona-glowna.md).

