"""Regresja: aktywny tor Integracja z GPT pozostaje na v40."""

from __future__ import annotations

from pathlib import Path


def test_active_v40_contract() -> None:
    from Komponenty.integracjagpt import config
    from Komponenty.integracjagpt import starter_checkpoint
    from Komponenty.integracjagpt import zip_knowledge

    assert config.GPT_KNOWLEDGE_PACK_VERSION == "v40"
    assert config.GPT_STARTER_ZIP_NAME == "giclee_cursor_architect_knowledge_v40.zip"
    assert config.GPT_COMPACT_INSTRUCTIONS_FILE.endswith("_v40.md")

    manifest = zip_knowledge.CLEAN_PACK_V40_ACTIVE_FILES
    assert len(manifest) == 47
    assert len(set(manifest)) == 47
    assert not any("_v38.md" in name or "_v39.md" in name for name in manifest)
    assert starter_checkpoint._STARTER_FILES_WITH_MARKERS == ("CURRENT_APP_STATE.md",)


def test_gui_has_no_obsolete_conversation_step() -> None:
    from Komponenty.integracjagpt import gui, handoff

    gui_source = Path(gui.__file__).read_text(encoding="utf-8")
    handoff_source = Path(handoff.__file__).read_text(encoding="utf-8")

    assert "CLEAN_PACK v38" not in gui_source
    assert "compact instructions (v35)" not in gui_source
    assert "Skopiuj wiadomość o roli" not in gui_source
    assert "build_cursor_delegate_followup_message" not in gui_source
    assert "build_cursor_delegate_followup_message" not in handoff_source
