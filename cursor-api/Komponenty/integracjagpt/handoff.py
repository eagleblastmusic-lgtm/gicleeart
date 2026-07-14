"""Szablony wiadomości do ChatGPT (schowek)."""

from __future__ import annotations

from datetime import UTC, datetime

from .config import GptConfig
from .zip_knowledge import read_start_message

_START_REPO_PLACEHOLDER = "[TU WPISZ: gicleeart-gpt albo gicleeapp]"
_START_SHA_PLACEHOLDER = "[TU WPISZ SHA]"
_START_SCOPE_PLACEHOLDER = (
    "[TU WPISZ, np. homepage / header / katalog / launcher UI / aplikacja / integracja]"
)


def _default_review_repo(review_goal: str) -> str:
    goal = review_goal.lower()
    app_keywords = (
        "launcher",
        "gicleeapp",
        "cursor-api",
        "python",
        "komponent",
        "integracja gpt",
        "aplikacja",
        "integracjagpt",
    )
    if any(k in goal for k in app_keywords):
        return "gicleeapp"
    return "gicleeart-gpt"


def build_review_request(cfg: GptConfig, *, commit_sha: str = "", notes: str = "") -> str:
    repo = (cfg.remote_url or "gicleeart-gpt").rstrip("/").replace(".git", "").split("/")[-1]
    sha = commit_sha or cfg.last_push_sha or "(brak — push z GicleeApp)"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    extra = f"\n\n**Uwagi od mnie:** {notes.strip()}" if notes.strip() else ""
    return f"""Push do repo GPT gotowy ({ts}).

**Repo:** `{repo}` (branch `{cfg.branch}`)
**Commit:** `{sha}`

Proszę:
1. Przejrzyj diff tego commita i `SYNC_NOTES.md`.
2. Oceń jakość kodu (motyw Shopify, JS/CSS/Liquid).
3. Jeśli dotyczy UI — zajrzyj w `docs/review-demos/latest-desktop.webm` i `latest-mobile.webm` (jeśli są) albo poproś mnie o screeny.
4. Daj werdykt: OK / lista poprawek z konkretnymi wartościami (opacity, ms, px) gotowymi do wklejenia w Cursor.{extra}
"""


def build_plan_evaluation_message() -> str:
    """Wiadomość startowa — prośba o ocenę planu integracji."""
    return """Cześć — wdrażam integrację mojego projektu Shopify (GicleeArt) z Tobą jako Custom GPT. Oceń proszę plan i daj uwagi.

## Kontekst
- **Główne repo:** `gicleeart` na GitHubie (~270 MB) — motyw Shopify + `cursor-api/` (Python, GicleeApp, dane robocze).
- **Osobne repo GPT:** `gicleeart-gpt` — tylko lustro motywu (sections, assets, docs/motyw, nagrania review). Bez cursor-api, backupów, `.env`.
- **Wykonawca kodu:** Cursor Agent na moim PC (pełny dostęp do dysku).
- **Ty:** architekt + reviewer — planujesz, ja wklejam prompt do Cursor, po sesji robię push lustra z GicleeApp.

## Workflow (pętla)
1. Ty analizujesz repo GPT + docs i dajesz **strukturalny prompt** do Cursor.
2. Ja wklejam → Cursor implementuje lokalnie (theme dev).
3. GicleeApp: **Nagraj podgląd** (Playwright, scroll strony głównej) → `docs/review-demos/latest-desktop.webm` + mobile.
4. GicleeApp: **Push → GPT GitHub** — sync allowlist + commit + push.
5. Ty: review diff + opcjonalnie nagrania; werdykt lub poprawki → wracam do kroku 2.

## Co jest w lustre GPT
- `sections/`, `blocks/`, `snippets/`, `layout/`, `templates/`, `assets/`, `config/`
- `docs/motyw/`, `docs/review-demos/`
- `SYNC_NOTES.md`, `GPT_README.md` (auto)

## Czego NIE ma w lustre
- cursor-api, zamówienia, backupy JSON, .env, duże cache CSV

## Pytania do Ciebie
1. Czy ten podział ról (Ty = plan + review, Cursor = implementacja) ma sens?
2. Czy osobne repo GPT to dobra idea vs branch w głównym repo?
3. Jak najlepiej formatować prompty pod Cursor (mam sekcje: Cel / Pliki / Nie ruszaj / Kryteria)?
4. Czy nagrania Playwright w `review-demos/` wystarczą do oceny animacji/scroll stacka, czy zawsze prosić o dodatkowe screeny?
5. Co dopisać do Twoich Instructions, żeby review było konkretne (opacity, ms, px)?

Po Twojej ocenie skonfiguruję Custom GPT z konektorem GitHub na repo lustra."""


def build_zip_read_github_followup_message() -> str:
    """Druga wiadomość w Oknie rozmowy — po Wiadomości początkowej (ZIP + GitHub)."""
    return (
        "1. przeczytaj wszystkie pliki które są w zip. Co do jednego i potwierdź jak przeczytasz.\n"
        "2. Połącz się z githubem i zapoznaj się z repozytoriami.\n"
        "3. Na gicie jest pewnie nowsza wersja niż wyszczególniona w zipie także się tym nie przejmuj "
        "i analizuj bierzące wersje z gita"
    )


def build_confirmation_checklist_message() -> str:
    """Trzecia (ostatnia) wiadomość w Oknie rozmowy — potwierdzenia po ZIP-ie i GitHubie."""
    return """1. Potwierdź, że przeczytałeś wszystkie pliki wiedzy i rozumiesz instrukcje.

2. Potwierdź, że jako główne Instructions traktujesz:
   GICLEE_CURSOR_ARCHITECT_INSTRUCTIONS_COMPACT_v40.md

3. Potwierdź, że widzisz aktualny CURRENT_APP_STATE.md,
   w szczególności sekcję „Current repository state” osobno dla każdego repozytorium.

4. Potwierdź, że widzisz i rozumiesz aktywną roadmapę:
   GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md

5. Potwierdź, że widzisz pliki trybów analitycznych GICLEE_ANALYST_*_v1.md,
   w tym sześć nowych modułów v3.9:
   - GICLEE_ANALYST_MODE_GITHUB_PR_CI_v1.md
   - GICLEE_ANALYST_MODE_RUNTIME_DATA_OWNERSHIP_v1.md
   - GICLEE_ANALYST_MODE_WRITER_EXPORT_SAFETY_v1.md
   - GICLEE_ANALYST_MODE_CROSS_REPO_COORDINATOR_v1.md
   - GICLEE_ANALYST_MODE_HANDOFF_CONTINUITY_v1.md
   - GICLEE_ANALYST_LESSONS_LEARNED_v1.md

6. Potwierdź, że widzisz pliki trybów Shopify:
   GICLEE_SHOPIFY_MODE_*_v1.md

7. Potwierdź status integracji ZIP v40:
   - 47 plików Knowledge,
   - integracjagpt v40,
   - ZIP jest wyłącznie snapshotem.

8. Potwierdź, że dla prywatnych repozytoriów będziesz używać GitHub connectora.

9. Potwierdź, że przed rozpoczęciem zadania sprawdzisz przez connector:
   - aktualne default branche,
   - bieżące SHA,
   - otwarte PR-y,
   - status CI,
   - różnice względem CURRENT_APP_STATE.md.

10. Potwierdź, że nie rozpoczniesz review, planu ani implementacji i poczekasz na moje konkretne zadanie."""


def build_conversation_start_prompt(
    *,
    commit_sha: str = "",
    review_goal: str = "",
    repo: str = "",
) -> str:
    """Wiadomość startowa po Pełnym cyklu — na bazie «Wiadomość początkowa.txt» z uzupełnionymi polami."""
    text = read_start_message()
    sha = (commit_sha or "").strip() or "(brak — uruchom Pełny cykl i push)"
    scope = (review_goal or "").strip() or (
        "review snapshotu homepage według załączonych instrukcji Giclee Cursor Architect"
    )
    repo_name = (repo or "").strip() or _default_review_repo(scope)

    return (
        text.replace(_START_REPO_PLACEHOLDER, repo_name)
        .replace(_START_SHA_PLACEHOLDER, sha)
        .replace(_START_SCOPE_PLACEHOLDER, scope)
    )
