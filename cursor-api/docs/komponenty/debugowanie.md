# Komponent: debugowanie

**Cel:** Sesja debugowania z poleceń — polecenie do schowka, kolejne sekcje z wklejonego debuga, zakończenie ze skopiowaniem wszystkich sekcji.

| Plik | Rola |
|------|------|
| `gui.py` | Okno główne + dialogi polecenia i sekcji debuga |

Tryb: `subprocess`. Sekcja launchera: **Narzędzia pomocnicze**.

## Workflow

1. **Wpisz polecenie** — po zatwierdzeniu tekst trafia do schowka.
2. **Sekcja N** — wklej treść debuga; «Dalej» zapisuje `Sekcja N - …` w pamięci, kopiuje polecenie do schowka i otwiera kolejną sekcję.
3. **Zakończ debug** (w każdym oknie sekcji) — bieżąca treść (jeśli jest) też trafia do pamięci; wszystkie sekcje kopiowane do schowka (oddzielone pustą linią).

Okno główne pokazuje podgląd zebranych sekcji i przycisk «Nowa sesja debug».

→ [`README.md`](README.md)
