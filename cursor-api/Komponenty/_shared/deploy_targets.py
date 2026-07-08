"""Cele deploy motywu Shopify — wspólne dla stronaglowna i edytora stron menu."""

from __future__ import annotations

from typing import Any

DEPLOY_TARGETS: dict[str, dict[str, Any]] = {
    "development": {
        "label": "Development (shopify.theme.toml)",
        "environment": "development",
        "allow_live": False,
        "hint": "Motyw «GicleeApp dev» (200713503068) — dedykowana piaskownica.",
    },
    "unpublished": {
        "label": "Kopia nieopublikowana",
        "environment": "unpublished",
        "allow_live": False,
        "hint": "Theme ID 199521829212 — kopia robocza na Shopify.",
    },
    "live": {
        "label": "Live (opublikowany motyw)",
        "environment": "live",
        "allow_live": True,
        "hint": "Theme ID 197314249052 — wymaga --allow-live.",
    },
}
