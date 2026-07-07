from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_prewarm_is_disabled_by_default_and_has_quiet_window() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_STUDIO_IDLE_PREWARM" in text
    assert "_studio_idle_prewarm_enabled" in text
    assert "default=False" in text
    assert "_PREWARM_MIN_QUIET_MS" in text
    assert "prewarm.skipped_recent_user_action" in text
    assert "prewarm.skipped_disabled" in text
    assert "prewarm.factory_allowed" in text
