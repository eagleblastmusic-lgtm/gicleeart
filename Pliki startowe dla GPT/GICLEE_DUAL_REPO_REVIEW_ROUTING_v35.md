# GICLEE DUAL-REPO REVIEW ROUTING v3.5

Kanoniczne zasady routingu dla Custom GPT po utworzeniu drugiego repo review.

---

## Dwa repozytoria

### 1. `eagleblastmusic-lgtm/gicleeart-gpt`

**Zakres:** motyw Shopify, snapshot theme, Liquid, CSS, JS, assets, sections, snippets, layout, templates, homepage, header, menu, UX strony, animacje, `docs/review-demos/`, `docs/motyw/`.

**To repo NIE jest:** aplikacją Python, launcherem, `cursor-api`, backoffice, sekretami.

### 2. `eagleblastmusic-lgtm/gicleeapp`

**Zakres:** lokalna aplikacja `cursor-api` / GicleeApp, launcher GUI, Python, komponenty, workflow automation, sekrety, konfiguracja lokalna, integracja z Shopify workflow, przyszły redesign **GicleeApp Studio / Premium Fine Art Control Center**.

**To repo NIE jest:** motywem Shopify, live theme, produkcją storefrontu.

### GicleeApp push workflow

Workflow push GicleeApp: użytkownik zwykle wypycha lokalną aplikację przez przycisk w GicleeApp **„Push GicleeApp do GitHub”**, a nie ręcznie przez terminal. Traktuj to jako kanoniczny workflow push dla aplikacji: `cursor-api` → staging → `eagleblastmusic-lgtm/gicleeapp`; dry-run → audyt → potwierdzenie użytkownika → commit + push na `main`. Workflow dotyczy wyłącznie lokalnej GicleeApp/cursor-api. Nie dotyczy motywu Shopify, repo `gicleeart-gpt`, generowania ZIP-a wiedzy ani plików startowych GPT. Gdy dajesz instrukcje push/checkpoint, odnoś się do tego przycisku/workflow, chyba że użytkownik wyraźnie prosi o komendy terminalowe.

---

## Kiedy którego repo używać

| Typ zadania | Repo |
|-------------|------|
| Shopify theme, frontend, Liquid, CSS, JS, homepage, header, menu, animacje, UX strony | `gicleeart-gpt` |
| Local app, launcher, Python, cursor-api, komponenty, sekrety, UI aplikacji, workflow tools | `gicleeapp` |
| Zadanie cross-layer (app + theme) | logika aplikacji → `gicleeapp`; efekt w motywie → `gicleeart-gpt` |

---

## Zasady obowiązkowe

- **Nie proś o zmiany Pythona / launchera / cursor-api w repo `gicleeart-gpt`.**
- **Nie traktuj `gicleeapp` jako motywu Shopify.**
- **`gicleeart-gpt`** = snapshot working tree motywu (nie produkcja/live).
- **`changed_files`** w manifeście motywu ≠ pełny diff względem main/live.
- **Canonical commit SHA** = SHA z pusha / GitHub / podany przez użytkownika.

---

## GitHub connector

- Używaj **GitHub connectora** Custom GPT do prywatnych repo.
- **Nie sprawdzaj** prywatnych repo przez publiczne URL-e ani `raw.githubusercontent.com`.
- Jeśli connector **nie widzi** `gicleeart-gpt` lub `gicleeapp`, poproś użytkownika o dodanie dostępu do właściwego repo (może być potrzebny dostęp do **obu**).

---

## Cross-repo

Jeśli problem motywu zależy od zachowania aplikacji lokalnej:

1. Opisz punkt integracji (np. `integracjagpt`, `stronaglowna`, sibling layout motyw + `cursor-api/`).
2. Poproś o review logiki w **`gicleeapp`**.
3. Efekt storefrontu oceniaj w **`gicleeart-gpt`**.

---

## Powiązane pliki wiedzy

- `GICLEE_GITHUB_SNAPSHOT_REVIEW_WORKFLOW_v35.md` — workflow review snapshotów
- `GICLEE_CURSOR_MASTER_INDEX_v35.md` — hierarchia plików (POZIOM 0)
