# Komponent: stronaglowna



**Cel:** Zarządzanie treścią i grafiką **strony głównej** sklepu (`gicleeart.eu`) — bez ręcznej edycji `templates/index.json` w Theme Editor.



| Plik | Rola |

|------|------|

| `Komponenty/stronaglowna/gui.py` | Lista sekcji, miniaturki, edytor, podgląd, historia, deploy |

| `Komponenty/stronaglowna/service.py` | Odczyt/zapis JSON, backup, upload, `shopify theme push` |

| `Komponenty/stronaglowna/home_features.py` | Diff, walidacja, skan sekcji, theme dev, assets motywu |

| `Komponenty/stronaglowna/registry.py` | Mapowanie stref → ścieżki w szablonie / ustawieniach |

| `Komponenty/stronaglowna/text_html.py` | Konwersja nagłówek + treść ↔ HTML motywu |



Tryb: `subprocess`. Sekcja launchera: **Administracja strony** (kafelek «Strona główna»).



---



## Sekcje



| Strefa w GicleeApp | Źródło | Co edytujesz |

|--------------------|--------|--------------|

| Hero — slideshow | `index.json` | Slajd desktop, mobile (`assets/MALE_ORG.webp`), autoplay |

| Giclée Art — intro | `index.json` | Portret, **nagłówek + treść** (plain text → HTML) |

| Odrestaurowywanie / korekcja / potencjał / zobacz różnicę | `index.json` | Teksty, suwaki przed/po, CTA (w korekcji: wł./wył. przyciski) |

| **Powiadomienie modalne** | `config/settings_data.json` | Site notice: wł./wył., wersja, tytuł, treść, przycisk |



---



## Przepływ



1. GicleeApp → **Strona główna** → wybierz sekcję.

2. Grafiki: **Wgraj grafikę…** lub **przeciągnij plik na miniaturę** (`tkinterdnd2`).

3. Tekst: pola **Nagłówek** i **Treść** — komponent składa HTML (`<h2>`, `<p>`).

4. **Zapisz** — dialog diff + walidacja; kopia w `data/backups/index-YYYYMMDD-HHMMSS.json` (+ `settings-*.json`).

5. **Historia wersji…** — przywracanie kopii jednym kliknięciem.

6. **Podgląd…** — sklep live z `?giclee_skip_splash=1&giclee_skip_notice=1` albo lokalny `shopify theme dev` (127.0.0.1:9292).

7. **Wdróż motyw…** — wybór celu: development / unpublished / live (`shopify.theme.toml`).



Przy starcie: **skan index.json** — raport, gdy sekcja ma inne ID niż w `registry.py`.



---



## Walidacja przed zapisem / deployem



- Puste nagłówki/treść przy włączonej sekcji

- Brak obrazu w suwaku przed/po lub hero

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

