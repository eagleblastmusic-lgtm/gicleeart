# GicleeApp — dokumentacja launchera

Warstwa **giclee_app**. Hub: [`../../../docs/README.md`](../../../docs/README.md) · polityka docs tam samo.

Główna aplikacja-launcher uruchamiająca komponenty z `cursor-api/Komponenty/`. **Zmiany launcher →** pliki w tym folderze (`launcher.md` itd.), nie `SHOP_KNOWLEDGE.md`.

---

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
python -m giclee_app
```

Bez konsoli (tylko GUI):

```powershell
pythonw -m giclee_app
```

Szczegóły exe: [`build-exe.md`](build-exe.md)

**Studio Preview (F1):** [`studio-preview.md`](studio-preview.md) — `python -m giclee_app.studio_preview` (CustomTkinter, obok klasycznego launchera).

---

## Dokumenty w tym folderze

| Plik | Temat |
|------|--------|
| [`launcher.md`](launcher.md) | GUI, sekcje kafelków, toolbar |
| [`studio-preview.md`](studio-preview.md) | **Studio Preview (F1)** — ciemny shell CTk |
| [`component-loader.md`](component-loader.md) | Discovery, `component.json`, tryby |
| [`build-exe.md`](build-exe.md) | PyInstaller, `GICLEE_PYTHON` |
| [`session-status.md`](session-status.md) | Raport OAuth, NBP, git |
| [`troubleshooting.md`](troubleshooting.md) | Problemy launchera |

Logika komponentów (biznes): [`../docs/komponenty/README.md`](../docs/komponenty/README.md)

---

## Wszystkie komponenty (20)

| Folder | Nazwa | Order | Tryb | Opis |
|--------|-------|-------|------|------|
| `dodajobraz` | Dodaj obraz | 10 | subprocess | Tworzenie produktów malarskich w Shopify |
| `zmietytuly` | Zmień tytuły | 15 | subprocess | Prompt do zmiany tytułów produktu (PL/EN/oryg. + DE–IT) |
| `tytulyai` | Tytuły AI (Gemini) | 16 | subprocess | Batch tytułów z obrazów przez Gemini API → prompty Cursor |
| `nazwijobraz` | Nazwij obraz | 20 | subprocess | Rename plików → `Autor - Tytuł` |
| `pobierzobraz` | Pobierz obraz | 30 | subprocess | IIIF z muzeów |
| `squoosh` | Squoosh WebP | 35 | subprocess | Konwersja → WebP |
| `print_optimize` | Optymalizacja druku | 37 | subprocess | Gemini + korekcja pod druk; pary Whitewall + kalibracja |
| `mockup` | Mock-up | 36 | subprocess | Ramka katalogowa → Shopify **(≠ mockup klienta)** |
| `notatnik` | Notatnik | 40 | subprocess | Notatki Markdown |
| `obrazy` | Obrazy | 50 | inline | Skróty do folderów obrazów |
| `kalkulacja` | Kalkulator kosztów | 55 | inline | Koszty ramek, marże, drewno |
| `dnr` | Działalność nierejestrowana | 55 | inline | Ewidencja DNR, limit kwartalny, guardrail, Allegro/MoR |
| `kpir` | JDG — KPiR | 56 | inline | Księga Przychodów i Rozchodów |
| `ksiegowosc` | Księgowość | 58 | inline | ukryty (`hidden`) |
| `dokumentysprzedazy` | Dokumenty sprzedaży | 57 | inline | Faktury bez VAT, Shopify, PDF |
| `blog` | Blog | 60 | inline | Posty Shopify 7 jęz. |
| `socialmedia` | Social Media | 61 | inline | IG/FB + cykl |
| `zadania` | Zadania | 62 | inline | Planer marketingowy LLM |
| `cenyMarketing` | Ceny w marketingu | 65 | inline | P&L, promocje |
| `sklep` | Giclee Art Sklep | 70 | url | Otwiera gicleeart.eu |
| `limity` | Limity | 68 | inline | Zużycie Cloudflare, Resend, SerpAPI |
| `poczta` | Poczta firmowa | 72 | inline | Podgląd Gmail gicleeartpl@gmail.com |
| `planer` | Planer | 80 | inline | Zadania wewnętrzne |
| `passepartout` | Passe-partout | 45 | inline | Kalkulator jednostek Allegro (Tkinter) |
| `produkcja` | Produkcja | 90 | inline | Zamówienia, etykiety |

Sekcje w launcherze (kolejność UI, nie `order` JSON): patrz [`launcher.md`](launcher.md)

---

## Architektura (skrót)

```
cursor-api/
├── giclee_app/          ← launcher (ten folder)
│   ├── launcher.py
│   ├── component_loader.py
│   └── runtime.py
└── Komponenty/          ← izolowane procesy / inline views
```

Komponenty **izolowane** — crash jednego nie ubija launchera.

---

## Dodawanie nowego komponentu

Patrz [`component-loader.md`](component-loader.md) — folder + `__main__.py` + opcjonalnie `component.json`.  
GicleeApp wykrywa nowe co **3 sekundy** (przycisk Odśwież).
