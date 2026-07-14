# GICLEE CURSOR MASTER INDEX v4.0

System Giclée Cursor Architect v4.0. **Bieżący stan repozytoriów:** `CURRENT_APP_STATE.md` § Current repository state — nie ten plik.

**Aktywny manifest:** `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v40.md` — **47 plików**.

---

## POZIOM 0 — ROUTING, ŹRÓDŁO PRAWDY, AUTONOMIA

**Ten poziom wygrywa** przy wyborze repo, zakresu write/push/merge i interpretacji checkpointu.

| Zasada | Plik |
|--------|------|
| Routing repo | `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md` |
| Cross-repo koordynacja | `GICLEE_ANALYST_MODE_CROSS_REPO_COORDINATOR_v1.md` |
| Stan per-repo (SHA, PR, next stage) | `CURRENT_APP_STATE.md` — **jedyny żywy checkpoint** |
| Konstytucja modelu | `GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md` |
| Pipeline autonomicznej inżynierii | `GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md` |
| PR / CI / merge | `GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md` |
| Runtime ownership | `GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md` |
| Writer / export | `GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md` |
| Integracja ZIP v40 | `GICLEE_ANALYST_MODE_GPT_ZIP_INTEGRATION_v1.md` |
| Roadmapa refaktoru (etapy, priorytety) | `GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md` |

| Zadanie | Repo |
|---------|------|
| Monorepo, CI Runtime Foundation | `eagleblastmusic-lgtm/gicleeart` |
| GicleeApp / cursor-api | `eagleblastmusic-lgtm/gicleeapp` |
| Snapshot motywu Shopify | `eagleblastmusic-lgtm/gicleeart-gpt` |
| Giclee Viewer | `eagleblastmusic-lgtm/giclee-viewer` |
| Studio 2.0 shell | `eagleblastmusic-lgtm/GicleeAppStudio_2` |

**Merge:** tylko po guardrailach **i** jawnej autoryzacji użytkownika. Zielone CI ≠ zgoda.

**ZIP:** snapshot rozmowy. Źródło edycji = lokalne pliki. Lokalne pliki startowe = v40 (47 plików Knowledge). `integracjagpt` generuje ZIP v40 zgodny z manifestem 47 plików.

**v39:** historyczne / superseded — nie używać jako aktywne Instructions ani manifest.

---

## POZIOM 1 — GŁÓWNE INSTRUKCJE

`GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md`

Archiwum Instructions: `*_v39.md`, `*_v38.md` i starsze — nie używać jako pole Instructions.

---

## POZIOM 2–9

Bez zmian względem v39 (motion, effects, playbook, examples) — patrz `GICLEE_CURSOR_ARCHITECT_CLEAN_PACK_v40.md`.

---

## Nowe moduły v4.0

| Plik | Rola |
|------|------|
| `GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md` | Makro-etapy IMPLEMENTATION / STABILIZATION / FINAL VALIDATION & SHIP; anomaly gates; anty-pętla full suite |

Moduły v3.9 (GITHUB_PR_CI, RUNTIME_DATA_OWNERSHIP, WRITER_EXPORT_SAFETY, CROSS_REPO_COORDINATOR, HANDOFF_CONTINUITY, LESSONS_LEARNED) — bez zmiany numeracji; zaktualizowane cross-linki do pipeline.

---

## Analyst modes (wszystkie 15)

Patrz CLEAN_PACK v40 § Analyst modes.

---

## Shopify modes (9)

Patrz CLEAN_PACK v40 § Shopify modes.

---

## Kiedy używać którego pliku

- **Duży autonomiczny etap:** `GICLEE_AUTONOMOUS_ENGINEERING_PIPELINE_v1.md` + COMPACT v40 § Autonomous Engineering Model
- **PR na gicleeart:** `GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md` + `CURRENT_APP_STATE.md` § gicleeart
- **Import branch GPT:** `GPT_GIT_BRANCH_WORKFLOW.md`
- **Review snapshot motywu:** `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md`
- **Maintenance plików startowych:** COMPACT v40 § KOMENDA + CLEAN_PACK v40
- **Handoff nowej sesji:** COMPACT v40 § Obowiązkowe zakończenie + `GICLEE_ANALYST_MODE_HANDOFF_CONTINUITY_v1.md`
- **Wieloetapowy refaktor / następny priorytet:** `GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md` + `CURRENT_APP_STATE.md` + `GICLEE_ANALYST_MODE_STAGE_ARCHITECT_v1.md`

---

## Rozstrzyganie konfliktów

1. POZIOM 0 (repo + autoryzacja + pipeline)
2. Bezpieczeństwo danych / runtime ownership
3. Granice Studio / writer / Shopify
4. Marka premium
5. Motion quality

---

## Finalna zasada

Piękne, premium, bezpieczne, wdrażalne przez Cursor lub kontrolowany PR na GitHubie — zawsze z dowodem i właściwym repo.

**Checkpointy:** tylko `CURRENT_APP_STATE.md` per repo. **Konstytucja:** COMPACT v40 bez SHA/PR/runów.
