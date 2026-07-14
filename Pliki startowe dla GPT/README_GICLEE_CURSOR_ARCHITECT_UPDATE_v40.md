# Giclee Cursor Architect — v40 update

## v40 update (2026-07-14)

**v4.0** = v3.9 + model autonomicznej inżynierii + pipeline + finalny audit GICLÉE FRAME GF-M1–GF-M18 + manifest 47 plików.

### Co nowego

1. **`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md`** — konstytucja bez SHA/PR/runów CI; sekcja Autonomous Engineering Model; v39 → archiwum.

2. **`GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md`** — makro-etapy, 19 kroków pipeline, anomaly gates, antyprzykład procesu stabilization.

3. **`GICLEE_CURSOR_MASTER_INDEX_v40.md`**, **`GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v40.md`** — manifest **47 plików** (v39 + pipeline).

4. **Zaktualizowane moduły analyst** — GITHUB_PR_CI, DEBUG_REGRESSION, CURSOR_REVIEW, STAGE_ARCHITECT, HANDOFF_CONTINUITY, LESSONS_LEARNED, `GPT_GIT_BRANCH_WORKFLOW.md`.

5. **`CURRENT_APP_STATE.md`** — GF-M1–GF-M18 complete, final audit PASS, CI #302, next: Bartosz OS discovery.

6. **`GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md`** — GF modularization COMPLETED; Start Files v40; brak GF-M19.

### Integracja ZIP v40

Po walidacji lokalnej:

- lokalne pliki startowe: v40;
- `integracjagpt`: v40;
- ZIP: `giclee_cursor_architect_knowledge_v40.zip`;
- liczba aktywnych plików: **47**;
- v39 pozostaje na dysku jako archiwum — **nie** dodawać do Knowledge.

ZIP generuj wyłącznie na osobne polecenie użytkownika.

---

## Jak użyć (Custom GPT)

### Pole Instructions

Wklej zawartość:

**`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md`**

### Pliki wiedzy (Knowledge)

Dodaj **47 aktywnych plików** z `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v40.md`.

**Procedura wymiany v39 → v40:**

1. Usuń z Knowledge aktywne pliki v39: `*_COMPACT_v39.md`, `*_MASTER_INDEX_v39.md`, `*_CLEAN_PACK_v39.md`, `README_*_v39.md`.
2. Dodaj odpowiadające pliki v40 oraz **`GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md`**.
3. Nie usuwaj plików v39 z dysku lokalnego — tylko z Knowledge GPT.
4. Zweryfikuj manifest: 47 unikalnych wpisów, suma kategorii 11+12+15+9=47.

### GitHub connector

Podłącz prywatne repo wg zakresu zadania.

Nie używaj publicznych URL ani `raw.githubusercontent.com`.

**Lokalny katalog** `C:\Strona\pusty\Pliki startowe dla GPT` = source of truth. **ZIP** = snapshot.

---

## Komenda: Aktualizuj pliki startowe

GPT → prompt do Cursora → edycja źródeł w `Pliki startowe dla GPT` → raport. **Bez ZIP z Cursora.**

---

## Archiwum

Pliki v39 pozostają na dysku jako archiwum — nie dodawać do Knowledge po przejściu na v40.

---

## Walidacja manifestu i ZIP-a

1. Wszystkie 47 ścieżek istnieją lokalnie.
2. Unikalność manifestu — brak duplikatów.
3. ZIP zawiera dokładnie 47 plików `.md` (bez `Wiadomość początkowa.txt`).
4. Brak aktywnych v39 w ZIP.
5. `integracjagpt` manifest = CLEAN_PACK v40.
