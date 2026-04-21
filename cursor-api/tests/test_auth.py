"""Testy modulu autentykacji (hashowanie + weryfikacja hasla)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest  # type: ignore[import-not-found]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def temp_auth_dir(monkeypatch, tmp_path):
    """Izoluje testy do tymczasowego katalogu zamiast %APPDATA%."""
    from Komponenty._shared import auth

    monkeypatch.setattr(auth, "_app_data_dir", lambda: tmp_path)
    return tmp_path


class TestAuth:
    def test_not_configured_initially(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        assert not auth.is_configured()

    def test_set_and_verify_password(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        auth.set_password("test1234")
        assert auth.is_configured()
        assert auth.verify_password("test1234")
        assert not auth.verify_password("wrong")
        assert not auth.verify_password("")

    def test_empty_password_rejected(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        with pytest.raises(ValueError):
            auth.set_password("")

    def test_short_password_rejected(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        with pytest.raises(ValueError):
            auth.set_password("abc")

    def test_reset_removes_file(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        auth.set_password("test1234")
        assert auth.is_configured()
        assert auth.reset_password()
        assert not auth.is_configured()

    def test_hash_is_not_plaintext(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        auth.set_password("MySecret123")
        content = (temp_auth_dir / "auth.json").read_text(encoding="utf-8")
        assert "MySecret123" not in content

    def test_salt_is_different_each_time(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        import json
        auth.set_password("same-password")
        hash1 = json.loads((temp_auth_dir / "auth.json").read_text(encoding="utf-8"))["hash_hex"]
        salt1 = json.loads((temp_auth_dir / "auth.json").read_text(encoding="utf-8"))["salt_hex"]
        auth.set_password("same-password")
        hash2 = json.loads((temp_auth_dir / "auth.json").read_text(encoding="utf-8"))["hash_hex"]
        salt2 = json.loads((temp_auth_dir / "auth.json").read_text(encoding="utf-8"))["salt_hex"]
        assert salt1 != salt2  # losowy salt
        assert hash1 != hash2  # dlatego hash jest rozny mimo tego samego hasla

    def test_password_with_special_chars(self, temp_auth_dir) -> None:
        from Komponenty._shared import auth
        auth.set_password("123BBBbbb@!$")
        assert auth.verify_password("123BBBbbb@!$")
        assert not auth.verify_password("123BBBbbb@")
