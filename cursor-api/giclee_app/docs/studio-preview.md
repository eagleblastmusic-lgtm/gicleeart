# GicleeApp Studio Preview (F2)

Hub: [`README.md`](README.md) · plan: [`../../docs/UI_REDESIGN_PLAN.md`](../../docs/UI_REDESIGN_PLAN.md)

**Studio Preview** to ciemny shell CustomTkinter obok klasycznego launchera. Nie zastępuje `launcher.py`.

---

## Uruchomienie

Z katalogu `cursor-api`:

```powershell
pip install -r requirements-dev.txt
python -m giclee_app.studio_preview
```

Klasyczny launcher (bez zmian, fallback produkcyjny):

```powershell
python -m giclee_app
```

Brak `customtkinter` → komunikat:

```
Zainstaluj zależności dev: pip install -r requirements-dev.txt
```

---

## F2 — panel pracy (scope)

| Element | Stan |
|---------|------|
| Lokalny state (`recent`, `pinned`) | `giclee_app/logs/studio_state.json` |
| Dashboard — statusy read-only | Shopify, Theme Dev, wersja Studio |
| Dashboard — pinned / recent chips | launch przez delegate |
| Dashboard — activity log | read-only tail |
| Safe quick actions | odśwież, docs, klasyczny launcher, folder Komponenty |
| Component Hub — sort | pinned → recent → domyślna kolejność |
| Component Hub — filtr trybu | all / subprocess / url / inline |
| Component Hub — PPM | uruchom, folder, log, kopiuj moduł, pin/unpin |
| Launch subprocess / url | działa; recent tylko po sukcesie |
| Launch inline | komunikat F3 — nie trafia do recent |
| Polling / sync / backup / deploy | **brak** |
| Inline embed w Studio | **F3** |
| Git dirty / real GitHub / GPT snapshot | **F3** |

State file **nie** jest commitowany (`.gitignore`).

---

## F1.2 — szybsze przełączanie zakładek

- **Cache widoków** — dashboard i huby kategorii są tworzone raz, potem `grid()` / `grid_remove()`.
- **Lazy render kart** — pierwsze wejście buduje karty partiami.
- **Card cache** — wyszukiwarka i filtry używają `grid()` / `grid_remove()`, bez destroy kart.

---

## F1.3 — skeleton first-paint

- **Skeleton grid** — 6 placeholderów przed budową kart.
- **Opóźnienie 16 ms** — first paint przed kosztowną budową.
- **Batche po 2 karty** — płynniejsze pierwsze wejście.
- **Cache bez skeletonu** — powrót do odwiedzonej kategorii natychmiastowy.

---

## Performance acceptance (F2)

- `discover_components()` — **1×** przy starcie shell.
- Second visit hub — bez regresji > ~10% vs F1.3.
- Dashboard `on_show()` — odświeża teksty/chips, bez pełnego rebuildu widoku.
- Pin / filter — nie niszczą card cache.

---

## Ograniczenia

- Stary launcher = produkcja (polling, backup, inline).
- Studio Preview = UI + read-only statusy + launch subprocess/url + lokalny state.
- PyInstaller (`.exe`) — Studio **nie** jest w bundlu do Fazy 6.
- `__main__.py` nadal wskazuje na stary launcher.

---

## Pliki

| Plik | Rola |
|------|------|
| `studio_preview.py` | entrypoint |
| `launcher_studio.py` | okno CTk, load/prune state |
| `launcher_delegate.py` | uruchamianie subprocess/url |
| `studio/state.py` | recent + pinned JSON |
| `ui/*` | layout |
| `studio/categories.py` | mapa kategorii |
| `studio/status_providers.py` | statusy read-only |
| `data/studio_categories.json` | folder → kategoria |
| `logs/studio_state.json` | runtime state (gitignored) |
