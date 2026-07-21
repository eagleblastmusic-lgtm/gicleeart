# TRYB CROSS-REPO COORDINATOR

Koordynacja zadań obejmujących więcej niż jedno repozytorium.

**Routing repozytoriów** — kanon w `GICLEE_DUAL_REPO_REVIEW_ROUTING_v35.md`. Ten plik **nie** zastępuje tabel routingu.

---

## Kiedy aktywować

- zmiana wymaga logiki aplikacji **i** efektu w motywie,
- import patcha z `gpt-work/*` lub `gicleeapp` do monorepo,
- review cross-layer (Studio + Shopify),
- synchronizacja checkpointów między `gicleeart`, `gicleeapp`, `gicleeart-gpt`.

---

## Zasady

1. **Jeden PR = jedna granica odpowiedzialności** na danym repo. Nie łącz niezależnych granic runtime w jednym PR.
2. Cross-layer: logika → `gicleeapp` lub `gicleeart` (`cursor-api/`); efekt motywu → `gicleeart-gpt` snapshot lub monorepo `gicleeart`.
3. Import patcha w PowerShell: `git diff --output`, **nie** `>`.
4. Przy cross-repo: **oba** `git apply --check` przed pierwszym apply.
5. Rollback = dokładna lista plików; bez szerokiego `restore -- cursor-api` i bez `git clean`.
6. `gicleeart` (monorepo, `origin`) ≠ `gicleeart-gpt` (snapshot motywu). CI Runtime Foundation → `gicleeart`.
7. `giclee-viewer` i `GicleeAppStudio_2` — osobne codebase'y; nie mieszać bez wyraźnego polecenia.

---

## Workflow PR per repo

| Repo | Typowa praca | Pipeline |
|------|--------------|----------|
| `gicleeart` | Runtime Foundation, CI, monorepo | `GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md` |
| `gicleeapp` | Aplikacja, push przez UI | `GPT_GIT_BRANCH_WORKFLOW.md` § GicleeApp |
| `gicleeart-gpt` | Snapshot motywu, review | `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` |
| `giclee-viewer` | WPF desktop | lokalny build/test; osobny tor |
| `GicleeAppStudio_2` | Przyszły shell C#/WPF | osobny tor |

---

## Checkpoint

Stan per repo → `CURRENT_APP_STATE.md` § Current repository state.

Nie zakładaj, że SHA z jednego repo obowiązuje w innym.
