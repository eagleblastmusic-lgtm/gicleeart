#!/usr/bin/env python3
"""Validate the canonical Giclee translation source and generated outputs."""

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
LOCALES_ROOT = REPO_ROOT / "locales"
MASTER_PATH = ROOT / "giclee_i18n_all.json"
FALLBACK_SNIPPET_PATH = (
    REPO_ROOT / "snippets" / "giclee-i18n-defaults-json.liquid"
)

LOCALE_FILES = {
    "en": "en.default.json",
    "de": "de.json",
    "fr": "fr.json",
    "es": "es.json",
    "nl": "nl.json",
    "it": "it.json",
    "pl": "pl.json",
}


def parse_json(raw: str, path: Path) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def load_shopify_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8-sig")

    raw = re.sub(r"^\s*/\*[\s\S]*?\*/\s*", "", raw, count=1)
    raw = re.sub(r"(?m)^\s*//.*$", "", raw)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    return parse_json(raw, path)


def load_fallback_snippet(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8-sig")

    raw = re.sub(
        r"^\s*\{%-?\s*comment\s*-?%\}[\s\S]*?"
        r"\{%-?\s*endcomment\s*-?%\}\s*",
        "",
        raw,
        count=1,
    )

    return parse_json(raw, path)


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}

    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            result.update(flatten(child, path))
    else:
        result[prefix] = value

    return result


def describe_mismatch(
    label: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    errors: list[str],
) -> None:
    expected_flat = flatten(expected)
    actual_flat = flatten(actual)

    missing = sorted(set(expected_flat) - set(actual_flat))
    extra = sorted(set(actual_flat) - set(expected_flat))
    changed = sorted(
        key
        for key in set(expected_flat) & set(actual_flat)
        if expected_flat[key] != actual_flat[key]
    )

    errors.append(
        f"{label}: mismatch "
        f"(missing={len(missing)}, extra={len(extra)}, changed={len(changed)})"
    )

    for key in missing[:10]:
        errors.append(f"  missing: {key}")

    for key in extra[:10]:
        errors.append(f"  extra: {key}")

    for key in changed[:10]:
        errors.append(f"  changed value: {key}")


def main() -> int:
    master = load_shopify_json(MASTER_PATH)

    if not isinstance(master, dict):
        print("VALIDATION FAILED: master must be an object", file=sys.stderr)
        return 1

    expected_languages = set(LOCALE_FILES)
    actual_languages = set(master)
    errors: list[str] = []

    missing_languages = sorted(expected_languages - actual_languages)
    unexpected_languages = sorted(actual_languages - expected_languages)

    if missing_languages:
        errors.append(
            "master missing languages: " + ", ".join(missing_languages)
        )

    if unexpected_languages:
        errors.append(
            "master has unexpected languages: "
            + ", ".join(unexpected_languages)
        )

    for language, filename in LOCALE_FILES.items():
        locale = load_shopify_json(LOCALES_ROOT / filename)

        master_giclee = master.get(language, {}).get("giclee")
        locale_giclee = locale.get("giclee")

        if not isinstance(master_giclee, dict):
            errors.append(f"{language}: master has no giclee object")
            continue

        if not isinstance(locale_giclee, dict):
            errors.append(f"{language}: {filename} has no giclee object")
            continue

        if master_giclee != locale_giclee:
            describe_mismatch(
                f"{language} locale",
                master_giclee,
                locale_giclee,
                errors,
            )
        else:
            key_count = len(flatten(master_giclee, "giclee"))
            print(f"{language}: MATCH ({key_count} keys)")

    master_pl_ui = master.get("pl", {}).get("giclee", {}).get("ui")

    if not isinstance(master_pl_ui, dict):
        errors.append("master pl.giclee.ui must be an object")
    else:
        fallback = load_fallback_snippet(FALLBACK_SNIPPET_PATH)

        if not isinstance(fallback, dict):
            errors.append("fallback snippet must contain a JSON object")
        elif fallback != master_pl_ui:
            describe_mismatch(
                "PL fallback snippet",
                master_pl_ui,
                fallback,
                errors,
            )
        else:
            print(
                "PL fallback snippet: "
                f"MATCH ({len(flatten(master_pl_ui))} keys)"
            )

    if errors:
        print("\nVALIDATION FAILED", file=sys.stderr)

        for error in errors:
            print(error, file=sys.stderr)

        return 1

    print("\nRESULT: canonical source matches all generated outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
