"""Repository-level secret handling and security policy contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"
SECURITY = ROOT / "SECURITY.md"


def test_local_shopify_session_is_ignored() -> None:
    lines = {
        line.strip()
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert ".shopify_session.json" in lines
    assert ".env" in lines
    assert ".env.*" in lines
    assert ".shopify-store-password.local" in lines


def test_security_policy_documents_private_reporting_and_rotation() -> None:
    text = SECURITY.read_text(encoding="utf-8")
    required = (
        "Do not open a public issue",
        "private GitHub Security Advisory",
        ".shopify_session.json",
        "revoke or rotate",
        "CI artifacts and logs must not contain secrets",
        "Shopify deploys",
        "separate explicit decision",
    )
    for phrase in required:
        assert phrase in text


def test_security_policy_does_not_publish_a_credential_value() -> None:
    text = SECURITY.read_text(encoding="utf-8").lower()
    forbidden_examples = (
        "shpat_",
        "shpca_",
        "shopify_access_token=",
        "client_secret=",
        "store_password=",
    )
    for marker in forbidden_examples:
        assert marker not in text
