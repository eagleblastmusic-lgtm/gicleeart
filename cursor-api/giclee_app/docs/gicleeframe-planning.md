# GICLÉE FRAME™ — planning shell (Studio F1)

Hub: [`admin-components-strategy.md`](admin-components-strategy.md) · [`studio-v2-workflows.md`](studio-v2-workflows.md) · [`studio-save-pattern.md`](studio-save-pattern.md) · legacy: [`../../docs/komponenty/gicleeframe.md`](../../docs/komponenty/gicleeframe.md)

**Stan:** app planning component **ready** @ Studio v1.39.0 · Shopify implementation **not started** · writer/save **blocked**

---

## 1. Cel

Panel planistyczno-preview dla premium komponentu strony **GICLÉE FRAME™** — znak technologii ramy / podpis systemu / premium label / section label / hero label.

Nie zastępuje legacy writera (`Komponenty/gicleeframe` → `theme_page_editor`). W Studio karta `gicleeframe` otwiera **wyłącznie** ten planning shell.

---

## 2. Guardrails

| Reguła | Szczegół |
|--------|----------|
| Importy | **Zero** `Komponenty.*` w `giclee_app/studio/gicleeframe_*` i `ui/gicleeframe_view.py` |
| Zapis | **Zero** Save / Zapisz / Zastosuj / `write_text` |
| Shopify | **Zero** sync / deploy / upload |
| Runtime | **Nie** mutować `Komponenty/gicleeframe/data/*` |
| Legacy | Klasyczny launcher → stary inline writer (bez zmian) |
| Studio | Brak przycisku „Legacy editor” |

---

## 3. Pliki

| Plik | Rola |
|------|------|
| `studio/gicleeframe_brief.py` | Statyczny brief: warianty, zasady wizualne/motion, placement |
| `studio/gicleeframe_draft_state.py` | Draft w RAM (wariant + strefa) |
| `studio/gicleeframe_dry_run.py` | Opis przyszłego outputu motywu (tekst) |
| `studio/gicleeframe_readiness.py` | Status gotowości, `save_ready` zawsze False |
| `ui/gicleeframe_view.py` | Widok CTk w Studio |
| `launcher_studio.py` | Routing: `gicleeframe` → `GicleeFrameView` |

---

## 4. Warianty koncepcyjne

- `default_dark` — default / dark
- `light_inverted` — light / inverted
- `compact` — compact
- `section_label` — section-label
- `hero_label` — hero-label

---

## 5. Wejście użytkownika

1. Studio → **Strona / Motyw** → karta **Giclée Frame** → planning shell
2. Wybór wariantu + opcjonalna strefa docelowa
3. **Sprawdź plan (dry-run)** — podgląd przyszłego snippetu motywu + readiness
4. **Wyczyść wybór** — reset draftu w pamięci

---

## 6. Następna faza (po akceptacji)

- Bounded data map + writer do motywu Shopify
- Sync/deploy (F5.5) — osobna akceptacja produktowa

**Gotowe do kolejnej fazy: po akceptacji.**
