# Moduły współdzielone (`Komponenty/_shared`)

Hub warstwy API: [`README.md`](README.md)

Folder: `cursor-api/Komponenty/_shared/`

---

## Pliki

| Moduł | Rola | Używany przez |
|-------|------|---------------|
| `auth.py` | Hasło startowe aplikacji | GicleeApp, komponenty wrażliwe |
| `activity_log.py` | Dziennik zdarzeń JSONL | Wszystkie komponenty (log akcji) |
| `activity_log_ui.py` | Okno podglądu + kopiowanie | GicleeApp toolbar |
| `task_notify.py` | Dźwięk po zakończeniu batcha | `dodajobraz`, inne kolejki |
| `fx_rates.py` | Kursy NBP (cache 24h) | Dialog rynków w `dodajobraz` |
| `window_geometry.py` | Centrowanie okien Tk | GicleeApp, dialogi |
| `tile_grid.py` | Siatka kafelków (inline views) | `blog`, `socialmedia`, `zadania` |
| `help_dialog.py` | Okno pomocy | Komponenty z HELP_TEXT |
| `tree_sort.py` | Sortowanie Treeview | `produkcja`, planery |
| `toast.py`, `notifications.py` | Powiadomienia UI | Różne GUI |
| `backup.py` | Kopie zapasowe danych | Opcjonalnie komponenty |

Dane: `Komponenty/_shared/data/` — `activity_log.jsonl`, `fx_cache.json`

---

## activity_log

Format: JSONL, jedna linia = jedno zdarzenie.

```python
from Komponenty._shared.activity_log import log_activity
log_activity("dodajobraz", "Utworzono produkt", detail="Hans Dahl - Babie lato")
```

Podgląd: GicleeApp → **Dziennik akcji**

---

## fx_rates (NBP)

- API: https://api.nbp.pl (bez klucza)
- Cache: `data/fx_cache.json` (24h)
- Używane przy liczeniu cen rynkowych EUR/PLN w komponencie **zmienceny** (widok Rynki…)

Szczegóły rynków: [`../SHOP_KNOWLEDGE.md`](../SHOP_KNOWLEDGE.md) §2
