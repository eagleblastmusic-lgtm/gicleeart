# Passe-partout — kalkulator Allegro

Komponent **inline** w GicleeApp (Tkinter, bez przeglądarki).

## Uruchomienie

```powershell
cd cursor-api
python -m giclee_app
```

Sekcja **Zamówienia** → kafelek **Passe-partout** — kalkulator otwiera się w oknie launchera.

**Wielopozycyjne zamówienie:** przycisk „Zapisz do zamówienia” dodaje bieżący format do listy; łączne jednostki, cena i wiadomość do sprzedawcy liczą się ze wszystkich zapisanych pozycji (dostawa raz na całość). Pozycje o **tym samym wymiarze zewnętrznym, cenie m² i trybie zaokrąglania** są łączone przed zaokrągleniem — np. w trybie „całość zamówienia razem” trzy szt. A4 + trzy szt. A4 dają tę samą cenę co sześć szt. naraz (wcześniej każda zapisana linia zaokrąglała się osobno). Karta podsumowania pokazuje **Całe zamówienie** (średnia cena/szt.), gdy lista zapisanych pozycji nie jest pusta. Przycisk **Zamów** w nagłówku otwiera ofertę Allegro (passe-partout biały 10×10 cm).

## Weryfikacja obliczeń

```powershell
cd cursor-api
python -m Komponenty.passepartout.verify_examples
```

## Kod

| Plik | Rola |
|------|------|
| `calculations.py` | Wzory, presety, formatowanie |
| `view.py` | UI Tkinter (`build_view`) |
