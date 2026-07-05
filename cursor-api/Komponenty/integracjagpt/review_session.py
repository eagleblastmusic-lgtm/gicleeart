"""Kontekst sesji review (Faza A) — cel, trasy, znane problemy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlparse


SOURCE_NOTE = (
    "Snapshot is copied from local working tree and may not match main repo or live theme."
)

WORKING_TREE_NOTE = (
    "Snapshot jest kopią lokalnego working tree motywu Shopify. "
    "Nie musi odpowiadać ostatniemu commitowi głównego repo ani stanowi live. "
    "GPT powinien traktować snapshot jako materiał review, a nie jako źródło prawdy o produkcji."
)

RELATED_GICLEEAPP_SECTION = """\
## Related repository: GicleeApp

Related repository: `eagleblastmusic-lgtm/gicleeapp`

**Routing:**

- `gicleeart-gpt` → Shopify theme snapshot, Liquid, CSS, JS, sections, snippets, assets, layout, templates, homepage, header, menu, UX strony, animations, `docs/review-demos`
- `gicleeapp` → local GicleeApp / cursor-api, Python, launcher, components, workflow automation, secrets/config, app UI

Do not request Python / launcher / cursor-api changes in `gicleeart-gpt`.
If a theme issue depends on local app behavior, mention the integration point and check `gicleeapp`.
Cross-repo review is normal in this project."""

GITHUB_CONNECTOR_NOTE = """\
## GitHub connector

- Use the GitHub connector for private repos — not public URLs or `raw.githubusercontent.com`.
- If the connector cannot access a repo, ask the user to grant access."""

CROSS_REPO_REVIEW_NOTE = """\
## Cross-repo review mode

Cross-repo is a normal workflow in this project, not an exception.

When a task crosses both layers:
- **gicleeapp** → app logic, workflow, generators, configuration,
- **gicleeart-gpt** → theme effect, Liquid, CSS, JS, UX, motion.

Review both repositories when needed without unnecessary repo-selection questions."""

DUAL_REPO_ROUTING_THEME = """\
## Dual-repo review routing

When reviewing:

1. If the task is about Shopify theme code, homepage, header, menu, Liquid, CSS, JS, animations, visual frontend:
   use `gicleeart-gpt`.

2. If the task is about the local app, launcher UI, Python components, workflow automation, secrets, local config:
   use `gicleeapp`.

3. If the task crosses both (cross-repo — normal mode):
   review app logic / workflow in `gicleeapp` and theme effect in `gicleeart-gpt`.

Important:
- This repository is for the Shopify theme snapshot only.
- Do not request Python, launcher, or cursor-api changes in this repository.
- If a theme issue depends on local app behavior, mention the integration point and check `gicleeapp`."""

DUAL_REPO_ROUTING_APP = """\
## Dual-repo review routing

When reviewing:

1. If the task is about Shopify theme code, homepage, header, menu, Liquid, CSS, JS, animations, visual frontend:
   use `gicleeart-gpt`.

2. If the task is about the local app, launcher UI, Python components, workflow automation, secrets, local config:
   use `gicleeapp`.

3. If the task crosses both (cross-repo — normal mode):
   review app logic / workflow in `gicleeapp` and theme effect in `gicleeart-gpt`.

Important:
- This repository is for the local GicleeApp / cursor-api application only.
- Do not treat this repository as the Shopify theme.
- Theme-side effects should be reviewed in `gicleeart-gpt`.
- App-side workflow, launcher UI, Python components, secrets and local config should be reviewed here.
- Cross-repo review is normal in this project."""


@dataclass
class ReviewSession:
    review_goal: str = ""
    known_issues: list[str] = field(default_factory=list)
    routes_recorded: list[str] = field(default_factory=lambda: ["/"])

    @classmethod
    def from_form(cls, review_goal: str, known_issues_text: str = "") -> ReviewSession:
        issues = [
            line.strip()
            for line in known_issues_text.replace(",", "\n").splitlines()
            if line.strip()
        ]
        return cls(review_goal=review_goal.strip(), known_issues=issues)

    def commit_message(self) -> str:
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        if self.review_goal:
            short = " ".join(self.review_goal.split())[:80]
            return f"review: {short} {now}"
        return f"review: theme snapshot {now}"


def route_from_url(url: str) -> str:
    try:
        path = urlparse(url).path or "/"
    except ValueError:
        return "/"
    return path if path.startswith("/") else f"/{path}"
