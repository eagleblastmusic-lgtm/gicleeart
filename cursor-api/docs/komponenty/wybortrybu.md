# Komponent: wybortrybu

**Cel:** Panel pomocniczy do przeglądania trybów pracy ChatGPT/Giclée Art, wybierania kombinacji i kopiowania krótkich promptów aktywacyjnych.

| Plik | Rola |
|------|------|
| `gui.py` | Okno Tkinter: lista trybów, szczegóły, generator, zakładka kombinacji |
| `data_loader.py` | Wczytanie `work_modes.json` + `combinations.json`, filtry |
| `prompt_builder.py` | Budowanie krótkiego i pełnego promptu aktywacyjnego |
| `import_from_xlsx.py` | Import XLSX → JSON (dev/maintenance, nie runtime) |
| `data/work_modes.json` | 10 trybów pracy |
| `data/combinations.json` | 6 rekomendowanych kombinacji |
| `data/source/tryby_pracy_chatgpt_giclee_art.xlsx` | Źródło do ponownego importu |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**. Kategoria Studio: **Review / GPT**.

## Workflow

1. Otwórz **Wybór Trybu** z launchera lub Studio (Review / GPT).
2. Przeglądaj tryby — filtruj po nazwie lub kategorii.
3. Zaznacz jeden lub więcej trybów (checkbox).
4. Kliknij tryb, aby zobaczyć szczegóły i skopiować przykładową komendę.
5. Na dole panelu — podgląd i kopiowanie pełnego promptu aktywacyjnego.
6. Zakładka **Kombinacje** — gotowe zestawy; klik **Wybierz tryby** zaznacza tryby i przechodzi do zakładki Tryby.

## Dane

Runtime korzysta **tylko z JSON** (bez openpyxl).

Ponowny import po zmianie XLSX:

```bash
cd cursor-api
python -m Komponenty.wybortrybu.import_from_xlsx
```

Opcjonalnie z inną ścieżką:

```bash
python -m Komponenty.wybortrybu.import_from_xlsx "sciezka/do/pliku.xlsx"
```

## Relacja do Bazy Promptów

Ten komponent generuje **krótkie komendy aktywacyjne**. Pełne, rozbudowane prompty (TRYB PERFORMANCE, SHOPIFY SNAPSHOT itd.) są w komponencie **Baza Promptów** — bez mapowania 1:1 na tym etapie.

→ [`README.md`](README.md)
