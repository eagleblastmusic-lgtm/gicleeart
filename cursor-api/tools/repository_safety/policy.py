"""Central repository data-classification policy for GicleeApp.

Only explicit source/example paths may be synchronized or tracked. Mutable,
private, secret, cache, backup and generated artifacts are classified before
any copy or Git operation.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Iterable


class DataClass(str, Enum):
    SOURCE = "SOURCE"
    EXAMPLE = "EXAMPLE"
    RUNTIME = "RUNTIME"
    CACHE = "CACHE"
    BACKUP = "BACKUP"
    PRIVATE = "PRIVATE"
    SECRET = "SECRET"
    GENERATED = "GENERATED"


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    classification: DataClass
    patterns: tuple[str, ...]
    tracked_allowed: bool
    sync_allowed: bool
    migration_bucket: str | None
    reason: str


@dataclass(frozen=True)
class PolicyDecision:
    path: str
    rule_id: str
    classification: DataClass | None
    tracked_allowed: bool
    sync_allowed: bool
    migration_bucket: str | None
    reason: str

    @property
    def requires_migration(self) -> bool:
        return self.migration_bucket is not None


_EXAMPLE_PATTERNS = (
    ".env.example",
    ".env.sample",
    "env.example",
    "env.sample",
    "**/*.example.json",
    "**/*.sample.json",
    "**/*.example.yaml",
    "**/*.example.yml",
)

_SECRET_PATTERNS = (
    ".env",
    ".env.*",
    "env",
    ".shopify_session.json",
    "shopify_session.json",
    ".npmrc",
    "npmrc",
    "**/*credentials*.json",
    "**/*credential*.json",
    "**/*access_token*.json",
    "**/*refresh_token*.json",
    "Komponenty/socialmedia/data/cykl/meta_credentials.json",
)

_PRIVATE_PATTERNS = (
    "Komponenty/notatnik/notatki/**",
    "Komponenty/bazapromptow/data/prompts.json",
    "Komponenty/bazapromptow/data/context_images/**",
    "Komponenty/bazapromptow/data/context_videos/**",
    "Komponenty/blog/data/topics.json",
    "Komponenty/dokumentysprzedazy/documents/**",
    "Komponenty/dokumentysprzedazy/dane/exports/**",
    "Komponenty/dokumentysprzedazy/dane/invoice_events.jsonl",
    "Komponenty/dnr/dane/dnr.json",
    "Komponenty/kalkulacja/data/materials.json",
    "Komponenty/kalkulacja/data/helpers.json",
    "Komponenty/kalkulacja/data/price_table.json",
    "Komponenty/kalkulacja/data/cost_lines.json",
    "Komponenty/kalkulacja/data/sales_mix.json",
    "Komponenty/kpir/dane/kpir.json",
    "Komponenty/kpir/documents/**",
    "Komponenty/planer/dane/*.json",
    "Komponenty/poczta/data/processed_client_orders.json",
    "Komponenty/produkcja/dane/zamowienia.json",
    "Komponenty/segregatorplikow/data/tiles.json",
    "Komponenty/socialmedia/data/cykl/Obrazy/**",
    "Komponenty/tytulyai/data/*_drafts.json",
    "Komponenty/zadania/data/tasks.json",
    "Komponenty/zadania/data/reminders.json",
    "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json",
    "**/invoices/**",
    "**/sales_exports/**",
    "**/*invoice*.json",
    "**/*invoice*.csv",
    "**/*sales_export*.csv",
)

_CONFIG_RUNTIME_PATTERNS = (
    "Komponenty/dnr/dane/dnr_settings.json",
    "Komponenty/dodajobraz/data/variant_templates.json",
    "Komponenty/integracjagpt/data/gpt_config.json",
    "Komponenty/kalkulacja/data/settings.json",
    "Komponenty/kalkulacja/data/wood_defaults.json",
    "Komponenty/karuzela/settings.json",
    "Komponenty/kpir/dane/kpir_settings.json",
    "Komponenty/produkcja/dane/package_templates.json",
    "Komponenty/socialmedia/data/cykl/config.json",
    "Komponenty/stronyzobrazami/data/settings.json",
    "giclee_app/data/launcher_shortcuts.json",
    "giclee_app/data/studio_categories.json",
    "giclee_app/logs/studio_state.json",
    "giclee_app/launcher_layout.json",
    "giclee_app/studio_state.json",
    "**/launcher_layout.json",
    "**/studio_state.json",
)

_LOG_RUNTIME_PATTERNS = (
    "_push_live.log",
    "logs/**",
    "giclee_app/logs/**",
    "reports/performance/**",
    "Komponenty/_shared/data/activity_log.jsonl",
    "**/*.log",
)

_RUNTIME_PATTERNS = (
    "Komponenty/_shared/data/recent_images.json",
    "Komponenty/dodajobraz/data/compare_versions.json",
    "Komponenty/dodajobraz/data/description_compare_llm.json",
    "Komponenty/dodajobraz/data/*marks*.json",
    "Komponenty/dodajobraz/data/*history*.json",
    "Komponenty/dodajobraz/data/*prefs*.json",
    "Komponenty/dodajobraz/data/*flag*.json",
    "Komponenty/socialmedia/data/cykl/generation_state.json",
    "Komponenty/socialmedia/data/cykl/queue.json",
    "Komponenty/stronaglowna/data/variants/*/index.json",
    "Komponenty/stronaglowna/data/variants/*/settings.json",
    "Komponenty/stronydozycia/data/pages.json",
    "Komponenty/stronyzobrazami/data/sites.json",
    "Komponenty/wspolpraca/data/variants/manifest.json",
    "Komponenty/wspolpraca/data/variants/*/page.wspolpraca.json",
    "Komponenty/produkcja/dane/sync_state.json",
    "Komponenty/produkcja/dane/notified.json",
    "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json",
    "Komponenty/socialmedia/data/cykl/meta_state.json",
    "**/sync_state.json",
)

_CACHE_PATTERNS = (
    ".cache/**",
    "**/.cache/**",
    "**/cache/**",
    "Komponenty/tldobio/data/collections.json",
    "Komponenty/tldobio/data/*.jpg",
    "Komponenty/tldobio/data/*.jpeg",
    "Komponenty/tldobio/data/*.png",
    "Komponenty/tldobio/data/*.webp",
    "Komponenty/_shared/data/fx_cache.json",
    "Komponenty/blog/data/articles_cache.json",
    "Komponenty/blog/data/preview.html",
    "Komponenty/karuzela/data/collection_quotes.json",
    "Komponenty/zadania/data/signals_cache.json",
    "Komponenty/analytics/dane/analytics.db",
    "**/*_cache.json",
)

_BACKUP_PATTERNS = (
    "backups/**",
    "**/backups/**",
    "**/*.bak",
    "**/*.backup",
    "**/*.orig",
)

_GENERATED_PATTERNS = (
    ".shopify/**",
    "build/**",
    "dist/**",
    "node_modules/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/backups/.gitkeep",
    ".gpt_mirror/**",
    "Komponenty/integracjagpt/data/nagrania/**",
    "Komponenty/integracjagpt/data/gpt_knowledge.zip",
    "Komponenty/print_optimize/data/ww_pairs/**",
    "Komponenty/stronaglowna/data/tmp/**",
    "gpt_knowledge.zip",
    "giclee_cursor_architect_knowledge*.zip",
    "_tmp_*/**",
    "_test_out/**",
    "_czesc7_parts/**",
    "_tmp_*",
    "_test_*",
    "_dup_result.txt",
    "czesc5*.json",
    "czesc6*.json",
    "czesc7*.json",
    "tmp_getty*.txt",
    "tmp_getty*.json",
    "10.0.0",
)

_SOURCE_PREFIXES = (
    "giclee_app/",
    "Komponenty/",
    "tools/",
    "tests/",
    "docs/",
    "extensions/",
    "lightroom-giclee-crop/",
    "mockup-order-worker/",
    "scripts/",
    "workers/",
    ".github/",
)

_SOURCE_EXACT_PATHS = frozenset(
    {
        ".graphqlrc.js",
        ".vscode/extensions.json",
        ".vscode/mcp.json",
        "Produkcja - serwer web.cmd",
        "SHOP_KNOWLEDGE.md",
    }
)

_SOURCE_ROOT_PATTERNS = (
    ".gitignore",
    ".gitattributes",
    "README.md",
    "GPT_README.md",
    "SYNC_NOTES.md",
    "REVIEW_MANIFEST.json",
    "CHECKLIST_SETUP.md",
    "SECURITY.md",
    "LICENSE*",
    "Makefile",
    "requirements*.txt",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "pytest.ini",
    "tox.ini",
    "giclee_app.spec",
    "*.py",
    "*.pyw",
    "*.mjs",
    "*.toml",
    "*.yaml",
    "*.yml",
)


POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(
        "EXAMPLE_SAFE",
        DataClass.EXAMPLE,
        _EXAMPLE_PATTERNS,
        True,
        True,
        None,
        "Sanitized bootstrap/example file.",
    ),
    PolicyRule(
        "SECRET_LOCAL_ONLY",
        DataClass.SECRET,
        _SECRET_PATTERNS,
        False,
        False,
        "config",
        "Credential, token or environment file must remain local.",
    ),
    PolicyRule(
        "PRIVATE_USER_DATA",
        DataClass.PRIVATE,
        _PRIVATE_PATTERNS,
        False,
        False,
        "data",
        "User, customer, invoice, accounting or authored personal data must remain outside Git.",
    ),
    PolicyRule(
        "LOCAL_CONFIG_RUNTIME",
        DataClass.RUNTIME,
        _CONFIG_RUNTIME_PATTERNS,
        False,
        False,
        "config",
        "Mutable local application configuration.",
    ),
    PolicyRule(
        "LOCAL_LOG_RUNTIME",
        DataClass.RUNTIME,
        _LOG_RUNTIME_PATTERNS,
        False,
        False,
        "logs",
        "Mutable application, performance or activity log.",
    ),
    PolicyRule(
        "LOCAL_RUNTIME_STATE",
        DataClass.RUNTIME,
        _RUNTIME_PATTERNS,
        False,
        False,
        "data",
        "Mutable runtime state is not source code.",
    ),
    PolicyRule(
        "GENERATED_ARTIFACT",
        DataClass.GENERATED,
        _GENERATED_PATTERNS,
        False,
        False,
        None,
        "Generated, temporary or build artifact.",
    ),
    PolicyRule(
        "LOCAL_CACHE",
        DataClass.CACHE,
        _CACHE_PATTERNS,
        False,
        False,
        "data",
        "Regenerable cache or local database.",
    ),
    PolicyRule(
        "LOCAL_BACKUP",
        DataClass.BACKUP,
        _BACKUP_PATTERNS,
        False,
        False,
        "backups",
        "Backup artifacts must not be tracked or synchronized.",
    ),
)


def normalize_repo_path(path: str | PurePosixPath) -> str:
    """Return a safe repository-relative POSIX path without resolving on disk."""

    raw = str(path).replace("\\", "/").strip()
    while raw.startswith("./"):
        raw = raw[2:]
    raw = raw.lstrip("/")
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError(f"Repository path escapes root: {path!r}")
    return "/".join(parts)


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _is_source_path(path: str) -> bool:
    if path in _SOURCE_EXACT_PATHS:
        return True
    if any(path.startswith(prefix) for prefix in _SOURCE_PREFIXES):
        return True
    if "/" not in path and _matches(path, _SOURCE_ROOT_PATTERNS):
        return True
    return False


def classify_path(path: str | PurePosixPath) -> PolicyDecision:
    normalized = normalize_repo_path(path)
    if not normalized:
        return PolicyDecision(
            path="",
            rule_id="EMPTY_PATH",
            classification=None,
            tracked_allowed=False,
            sync_allowed=False,
            migration_bucket=None,
            reason="Empty repository path.",
        )

    for rule in POLICY_RULES:
        if _matches(normalized, rule.patterns):
            return PolicyDecision(
                path=normalized,
                rule_id=rule.rule_id,
                classification=rule.classification,
                tracked_allowed=rule.tracked_allowed,
                sync_allowed=rule.sync_allowed,
                migration_bucket=rule.migration_bucket,
                reason=rule.reason,
            )

    if _is_source_path(normalized):
        return PolicyDecision(
            path=normalized,
            rule_id="SOURCE_ALLOWLIST",
            classification=DataClass.SOURCE,
            tracked_allowed=True,
            sync_allowed=True,
            migration_bucket=None,
            reason="Explicit source-tree allowlist.",
        )

    return PolicyDecision(
        path=normalized,
        rule_id="UNCLASSIFIED_BLOCKED",
        classification=None,
        tracked_allowed=False,
        sync_allowed=False,
        migration_bucket=None,
        reason="Path is outside the explicit source/example allowlist.",
    )


def is_sync_allowed(path: str | PurePosixPath) -> bool:
    return classify_path(path).sync_allowed


def is_tracked_allowed(path: str | PurePosixPath) -> bool:
    return classify_path(path).tracked_allowed
