# GPT Review — GicleeApp (cursor-api)

To repo zawiera **lokalną aplikację GicleeApp / cursor-api**, nie motyw Shopify.

## Dual-repo review routing

| Repo | Zakres review |
|------|----------------|
| **gicleeapp** (to repo) | Python, launcher, UI aplikacji, komponenty, bezpieczeństwo sekretów, workflow, integracja z motywem |
| **gicleeart-gpt** | Motyw Shopify, UX strony, Liquid, CSS, JS, animacje, snapshoty, `docs/review-demos/` |

When reviewing:

1. Shopify theme / homepage / header / Liquid / CSS / JS / animations → **`gicleeart-gpt`**.
2. Local app / launcher / Python / components / secrets / config → **`gicleeapp`**.
3. Cross-repo (normal mode) → app logic / workflow in **`gicleeapp`**, theme effect in **`gicleeart-gpt`**.

**Cross-repo review is normal in this project** (homepage from app, catalog, mockups, integracjagpt, etc.).

## Related repository

Related repository: `eagleblastmusic-lgtm/gicleeart-gpt`

Do not request Shopify theme / Liquid / CSS / JS changes in this repository.
If an app change affects the storefront, describe the integration point and compare with **gicleeart-gpt**.

## GitHub connector

- Use the GitHub connector for private repos — not public URLs or `raw.githubusercontent.com`.
- If the connector cannot access a repo, ask the user to grant access.

## Zasady

- **`gicleeapp` is not the Shopify theme.** **`gicleeart-gpt` is not the local application.**
- **`integracjagpt`** pushes the Shopify theme snapshot to **`eagleblastmusic-lgtm/gicleeart-gpt`**, not to `gicleeapp`.
- Nie traktuj **gicleeapp** jako produkcyjnego motywu Shopify.
- Nie commituj API keys, tokenów, cookies, sesji, zamówień klientów, faktur, notatek osobistych ani prywatnych logów.

## Paczka wiedzy GPT (v3.5)

Pliki startowe ChatGPT (ZIP, compact v35, wiadomość startowa) są utrzymywane lokalnie w `{THEME_ROOT}/Pliki startowe dla GPT/` — patrz [`docs/GPT_KNOWLEDGE_PACK.md`](docs/GPT_KNOWLEDGE_PACK.md).

Komponent **`integracjagpt`** czyta ten folder i buduje ZIP wg manifestu CLEAN_PACK v35. **Nie commituj** runtime ZIP-ów ani `gpt_knowledge.zip`.

## Podczas review oceniaj

- architekturę aplikacji i organizację komponentów,
- UI/UX launchera (bez redesignu na tym etapie — patrz plan poniżej),
- bezpieczeństwo sekretów,
- integrację z lokalnym workflow Shopify (sibling layout: motyw obok `cursor-api/`).

## Planowany kierunek UI

Docelowo GicleeApp ma zostać przebudowana w stronę **Premium Fine Art Control Center / GicleeApp Studio**.

**Future UI redesign of the launcher happens in `eagleblastmusic-lgtm/gicleeapp`** (this repository), not in `gicleeart-gpt`.

Szczegóły: [`docs/UI_REDESIGN_PLAN.md`](docs/UI_REDESIGN_PLAN.md)

## Performance Agent path note

Performance Agent is part of this repository. **Checkpoint PA/GF (2026-07-08):** PA-1I…PA-3B done locally; GF-P0.1 done in code; fresh `--run` validation pending. Tests: 162 passed. Full state: `Pliki startowe dla GPT/CURRENT_APP_STATE.md`.

Local workspace path:

`C:\Strona\pusty\cursor-api\tools\performance_agent`

GitHub repository path:

`tools/performance_agent`

The GitHub repository `eagleblastmusic-lgtm/gicleeapp` is rooted at the local `cursor-api` folder, so GitHub paths should not be prefixed with `cursor-api/`.

Entrypoint (run from `cursor-api/`):

```powershell
python -m tools.performance_agent --doctor
python -m tools.performance_agent --analyze-latest
python -m tools.performance_agent --coverage-latest
python -m tools.performance_agent --hotspots-latest
python -m tools.performance_agent --baseline-candidate
python -m tools.performance_agent --parse-only
python -m tools.performance_agent --manual
python -m tools.performance_agent --run
```

Default output:

`reports/performance`

When diagnosing Studio performance issues, inspect a Performance Agent bundle before proposing code changes. Prefer read-only operator commands (`--analyze-latest`, `--coverage-latest`) over guessing from UI symptoms.

Details: [`tools/performance_agent/README.md`](tools/performance_agent/README.md)

## Powiązane pliki

- [`REVIEW_MANIFEST.json`](REVIEW_MANIFEST.json)
- [`SYNC_NOTES.md`](SYNC_NOTES.md)
- [`docs/SHOPIFY_THEME_INTEGRATION.md`](docs/SHOPIFY_THEME_INTEGRATION.md)
- [`docs/GPT_KNOWLEDGE_PACK.md`](docs/GPT_KNOWLEDGE_PACK.md)
- [`tools/performance_agent/README.md`](tools/performance_agent/README.md)
