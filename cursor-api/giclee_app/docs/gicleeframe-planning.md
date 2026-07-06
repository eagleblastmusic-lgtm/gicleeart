# GICLÉE FRAME™ — planning shell (Studio F1 + F2)

Hub: [`admin-components-strategy.md`](admin-components-strategy.md) · [`studio-v2-workflows.md`](studio-v2-workflows.md) · [`studio-save-pattern.md`](studio-save-pattern.md) · legacy: [`../../docs/komponenty/gicleeframe.md`](../../docs/komponenty/gicleeframe.md)

**Stan:** app planning component **ready** @ Studio v1.40.0 · page structure inventory **ready (F2)** · Shopify implementation **not started** · writer/save **blocked**

---

## 1. Cel

Panel planistyczno-preview dla premium komponentu strony **GICLÉE FRAME™** — znak technologii ramy / podpis systemu / premium label / section label / hero label.

**F2:** uporządkowana mapa całej strony `/pages/giclee-frame` — sekcje, separatory, grafiki, teksty, kolejność, statusy — z edycją RAM (bez zapisu).

Nie zastępuje legacy writera (`Komponenty/gicleeframe` → `theme_page_editor`). W Studio karta `gicleeframe` otwiera **wyłącznie** ten planning shell.

---

## 2. Guardrails

| Reguła | Szczegół |
|--------|----------|
| Importy | **Zero** `Komponenty.*` w `giclee_app/studio/gicleeframe_*` i `ui/gicleeframe_view.py` |
| Zapis | **Zero** Save / Zapisz / Zastosuj / `write_text` |
| Shopify | **Zero** sync / deploy / upload |
| Runtime | **Nie** mutować `Komponenty/gicleeframe/data/*` |
| Inventory | Bounded read: `manifest.json` + `page.giclee-frame.json` + `registry.py` (regex etykiet) |
| Legacy | Klasyczny launcher → stary inline writer (bez zmian) |
| Studio | Brak przycisku „Legacy editor” |

Disclaimer F2: **„Zmiany są tylko lokalnym draftem w pamięci — nic nie zapisano.”**

---

## 3. Pliki

| Plik | Rola |
|------|------|
| `studio/gicleeframe_brief.py` | Statyczny brief: warianty, zasady wizualne/motion, placement |
| `studio/gicleeframe_draft_state.py` | Draft w RAM (wariant + strefa) — F1 marka |
| `studio/gicleeframe_dry_run.py` | Opis przyszłego outputu motywu (tekst) — F1 |
| `studio/gicleeframe_readiness.py` | Status gotowości marki + strony, `save_ready` zawsze False |
| `studio/gicleeframe_page_inventory.py` | **F2** — read-only inventory strony (rozwinięcie media → elementy) |
| `studio/gicleeframe_page_draft.py` | **F2** — RAM patchy elementów strony |
| `studio/gicleeframe_page_dry_run.py` | **F2** — dry-run struktury + guardrails |
| `ui/gicleeframe_view.py` | Widok CTk: **F2 struktura strony** + F1 komponent marki |
| `launcher_studio.py` | Routing: `gicleeframe` → `GicleeFrameView` |

---

## 4. Warianty koncepcyjne (F1 marka)

- `default_dark` — default / dark
- `light_inverted` — light / inverted
- `compact` — compact
- `section_label` — section-label
- `hero_label` — hero-label

---

## 5. Wejście użytkownika

### F2 — Struktura strony (priorytet)

1. Studio → **Strona / Motyw** → karta **Giclée Frame**
2. Sekcja **„Struktura strony GICLÉE FRAME™”** — inventory z wariantu `gf1` (aktywny w manifest)
3. **Odśwież inventory** — ponowny bounded read (draft RAM zachowany)
4. Klik elementu → panel edycji RAM (tytuł, tekst, alt, notatka, status, widoczność, kolejność)
5. **Uaktualnij RAM draft** — patch w pamięci
6. **Sprawdź strukturę (dry-run)** — liczniki, needs_review, shape writera F3 (informacyjnie)
7. **Wyczyść wybór** — reset draftu strony w RAM

Licznik `order[]` (np. 18 sekcji źródłowych) ≠ liczba elementów po rozwinięciu media (np. 42).

### F1 — Komponent marki (poniżej)

1. Wybór wariantu koncepcyjnego + opcjonalna strefa
2. **Sprawdź plan (dry-run)** + readiness marki
3. **Wyczyść wybór** — reset planu marki

---

## 6. Backlog (nie w tej fazie)

| Faza | Zakres |
|------|--------|
| **F2b** | Scale / motion / contrast / implementation spec — odłożone |
| **F3** | Bounded writer do `data/variants/{variant}/page.giclee-frame.json` |
| **F5.5** | Sync/deploy — osobna akceptacja produktowa |

**Gotowe do kolejnej fazy: po akceptacji F2.**
