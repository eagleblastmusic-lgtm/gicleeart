# Komponent: kalkulacja

**Cel:** Kalkulator kosztów produkcji ramek — materiały, narzut/marża, optymalizacja drewna, mix sprzedaży.

Tryb: `inline`. Folder: `Komponenty/kalkulacja/`

Launcher: sekcja **Finanse** (obok kafelka Księgowość).

## Zakres

- **Kalkulator** — 6 wariantów (Sosna/Dąb × A4/A3+/A2): rozbicie kosztów, cena, narzut, marża, zysk, czas produkcji, zarobek/h; **pochodzenie drewna** (`stolarz24` / `drewno dla majsterkowicza`); przycisk **Struktura kosztów** — *Wszystkie produkty*, *Skład ramki*, *Koszty zagregowane*; **aktualizacja na żywo** przy zmianie mixu (otwarte okno)
- **Cennik wariantu** — edytowalne pola: narzut (%), marża (%), cena sprzedaży (zsynchronizowane); zapis lokalny; przycisk **Zaktualizuj w szablonie** → `Komponenty/dodajobraz/data/variant_templates.json` (wszystkie szablony, mapowanie M/L/XL + Sosna/Dąb jak w sklepie)
- **Mix sprzedaży** — pasek nad tabelą: **Udział na 100 szt.**, **Cel finansowy**, symulacja ±, **Sprzedane ramki (razem)** + Ustaw; pod **Przychód brutto** małą czcionką **Rocznie** (miesięczny × 12)
- **Drewno** — optymalizacja partii zamówienia (H &lt; 0,2 jak w Excelu)
- **Materiały** — podgląd i edycja cennika materiałów
- **Koszty działalności** — suwak wł./wył., koszty JDG 2026 (ulga na start, preferencyjny/pełny ZUS, PIT, księgowość); wpływ na **Zysk netto** w mixie
- **Mix → porównanie podatków** — w tle skala / liniowy / ryczałt; gdy ryczałt daje wyższy zysk netto, komunikat pod „Zysk netto”
- **Import Excel** — koszty materiałów i wiersze CENNIK; **nie** nadpisuje zapisanych cen/narzutów

## Cennik (narzut / marża / cena)

Wzory (koszt = koszt produkcji bez wysyłki):

- **Narzut %** = `(cena − koszt) / koszt × 100`
- **Marża %** = `(cena − koszt) / cena × 100`

Edycja jednego pola przelicza pozostałe. Zapis w `data/settings.json`:

```json
{
  "default_markup_pct": 250,
  "variant_pricing": {
    "SOSNA_A4": {
      "sell_price": 229.8,
      "markup_pct": 250.0,
      "margin_pct": 71.4,
      "driver": "markup"
    }
  }
}
```

Nowe warianty bez zapisu używają `default_markup_pct` (domyślnie 250%).

**Szablon wariantów (dodajobraz):** `variant_template_sync.sync_variant_template_prices()` — ceny z `variant_pricing` (lub przeliczone z narzutu) trafiają do `variant_templates.json`; nowe produkty biorą stąd warianty przy tworzeniu w dodajobraz.

**Czas produkcji** (h) — edytowalny per wariant obok ceny; wewnętrznie zapis w minutach (`variant_production_minutes`); domyślnie 0,75 h (45 min).
**Ramek na dzień** — tryb **Ręcznie**: przyciski **±** (po 1, min. 1), tylko liczby całkowite; czas pracy w **dniach** (zaokrąglone w górę); **Z czasu produkcji (Kalkulator)**: wartość z godzin produkcji, czas w **godzinach**
**Zysk brutto** (mix) — suma zysku × sztuki (bez kosztów JDG); obok **/** zysk dzienny.
**Przychód brutto** (mix) — suma cen sprzedaży × sztuki (ceny sklepowe); obok **/** przychód dzienny.
**Koszt produkcji z wysyłką** (mix) — suma `full_cost` × sztuki; obok **/** koszt dzienny (÷ `work_days_per_month`).
**Koszty działalności** (`business_costs` w `settings.json`) — po włączeniu suwaka: ZUS, PIT, księgowość itd.; w mixie wiersz **Zysk netto (po kosztach JDG)** liczony od zysku **z wysyłką** (`profit_full`). **PIT** (skala): podstawa = przychód brutto − koszt produkcji z wysyłką (zysk brutto); pozostałe koszty miesięczne odejmowane **osobno** w podsumowaniu JDG (nie w podstawie PIT). Podatek 12% do 120 000 zł rocznie po **kwocie wolnej** (`tax_free_annual`, domyślnie 30 000 zł w 2026), 32% od nadwyżki; szacunek miesięczny = PIT roczny ÷ 12. **Liniowy**: 19% od zysku brutto miesięcznego (bez kwoty wolnej). **Ryczałt**: % od przychodu (bez odliczenia KUP).
**Zarobek na godzinę** = `zysk / czas_produkcji_w_godzinach`.

**Pochodzenie drewna** (`wood_origin` w `settings.json`): `stolarz24` (domyślnie) lub `drewno dla majsterkowicza`. Przy majsterkowiczu koszt pozycji „Drewno” dla **Dębu** to: A4 = 12 zł, A3+ = 24 zł, A2 = 24 zł (Sosna bez zmian).

## Dane

JSON w `Komponenty/kalkulacja/data/` — generowane przez `import_excel.py` z arkuszy:

`CENNIK MATERIAŁÓW`, `TABELA CEN WG MATERIAŁÓW`, `CENNIK` (koszty + wagi mixu), `KALKULATOR KOSZTU DREWNA`.

Import zachowuje `variant_pricing`, `default_markup_pct`, `variant_production_minutes`, `frames_per_day`, `frames_per_day_mode`, `work_hours_per_day`, `business_costs` z istniejącego `settings.json`.
Mix sprzedaży (`sales_mix.json`) **nie jest** nadpisywany przy imporcie.

## Import

```bash
python -m Komponenty.kalkulacja.import_excel "ścieżka/do/pliku.xlsm"
```

Wymaga: `pip install openpyxl` (patrz `requirements.txt`).

## Powiązane

- `finanse` — legacy (ukryty w launcherze; skrót do zewnętrznego arkusza Excel)
- `produkcja` — koszty per zamówienie (osobny model)
- `zmienceny` — dialog **Zmień ceny** pokazuje przy obecnej cenie sklepowej w nawiasie sugerowaną cenę z kalkulatora (`calc_sell_price_for_shop_labels`: M→A4, L→A3+, XL→A2; legacy S→A4)

→ [`../../SHOP_KNOWLEDGE.md`](../../SHOP_KNOWLEDGE.md) §9d2
