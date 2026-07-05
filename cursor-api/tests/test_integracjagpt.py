"""Testy Integracja z GPT."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_gpt_config_roundtrip(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "gpt_config.json")

    original = cfg.GptConfig(remote_url="https://github.com/x/y.git", branch="dev")
    cfg.save_config(original)
    loaded = cfg.load_config()
    assert loaded.remote_url == "https://github.com/x/y.git"
    assert loaded.branch == "dev"


def test_sync_mirror_copies_allowlisted_files(tmp_path) -> None:
    from Komponenty.integracjagpt import mirror as mir

    theme = tmp_path / "theme"
    (theme / "sections").mkdir(parents=True)
    (theme / "sections" / "hero.liquid").write_text("{% comment %}hero{% endcomment %}", encoding="utf-8")
    (theme / "cursor-api").mkdir()
    (theme / "cursor-api" / "secret.json").write_text("{}", encoding="utf-8")

    mirror = tmp_path / "mirror"
    result = mir.sync_theme_to_mirror(mirror, theme_root=theme)

    assert (mirror / "sections" / "hero.liquid").is_file()
    assert not (mirror / "cursor-api").exists()
    assert "sections/hero.liquid" in result.copied
    assert (mirror / "SYNC_NOTES.md").is_file()
    assert (mirror / "GPT_README.md").is_file()


def test_sync_mirror_does_not_delete_git(tmp_path) -> None:
    from Komponenty.integracjagpt import mirror as mir

    theme = tmp_path / "theme"
    (theme / "sections").mkdir(parents=True)
    (theme / "sections" / "hero.liquid").write_text("x", encoding="utf-8")

    mirror = tmp_path / "mirror"
    mirror.mkdir()
    (mirror / ".git").mkdir()
    (mirror / ".git" / "config").write_text("[core]", encoding="utf-8")

    mir.sync_theme_to_mirror(mirror, theme_root=theme)
    assert (mirror / ".git" / "config").is_file()


def test_build_review_request_contains_sha() -> None:
    from Komponenty.integracjagpt.config import GptConfig
    from Komponenty.integracjagpt.handoff import build_review_request

    cfg = GptConfig(
        remote_url="https://github.com/org/gicleeart-gpt.git",
        branch="main",
        last_push_sha="abc123def456",
    )
    msg = build_review_request(cfg)
    assert "abc123def456" in msg
    assert "gicleeart-gpt" in msg


def test_plan_evaluation_message_not_empty() -> None:
    from Komponenty.integracjagpt.handoff import build_plan_evaluation_message

    msg = build_plan_evaluation_message()
    assert "gicleeart-gpt" in msg
    assert "Cursor" in msg


def test_review_session_commit_message() -> None:
    from Komponenty.integracjagpt.review_session import ReviewSession

    sess = ReviewSession.from_form("hero scroll UX", "menu overlap\nfooter gap")
    msg = sess.commit_message()
    assert msg.startswith("review: hero scroll UX")
    assert sess.known_issues == ["menu overlap", "footer gap"]

    empty = ReviewSession()
    assert empty.commit_message().startswith("review: theme snapshot")


def test_sync_writes_review_manifest(tmp_path) -> None:
    import json

    from Komponenty.integracjagpt import mirror as mir
    from Komponenty.integracjagpt.review_session import ReviewSession

    theme = tmp_path / "theme"
    (theme / "sections").mkdir(parents=True)
    (theme / "sections" / "hero.liquid").write_text("x", encoding="utf-8")

    mirror = tmp_path / "mirror"
    session = ReviewSession(review_goal="test goal", known_issues=["known bug"])
    mir.sync_theme_to_mirror(mirror, theme_root=theme, session=session, snapshot_commit="abc123")

    manifest_path = mirror / "REVIEW_MANIFEST.json"
    assert manifest_path.is_file()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["snapshot_type"] == "local_working_tree_theme_snapshot"
    assert data["snapshot_commit"] == "abc123"
    assert data["review_goal"] == "test goal"
    assert data["known_issues"] == ["known bug"]
    assert "sections/hero.liquid" in data["changed_files"]

    notes = (mirror / "SYNC_NOTES.md").read_text(encoding="utf-8")
    assert "test goal" in notes
    assert "changed_files" in notes or "paczce review" in notes

    readme = (mirror / "GPT_README.md").read_text(encoding="utf-8")
    assert "Jak interpretować snapshot" in readme
    assert "changed_files" in readme


def test_build_review_package_no_push(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import mirror as mir
    from Komponenty.integracjagpt.review_session import ReviewSession

    theme = tmp_path / "theme"
    for rel in (
        "sections",
        "blocks",
        "snippets",
        "layout",
        "templates",
        "assets",
        "config",
        "docs/motyw",
        "docs/review-demos",
    ):
        (theme / rel).mkdir(parents=True)
    (theme / "sections" / "a.liquid").write_text("a", encoding="utf-8")
    mirror = tmp_path / "mirror"

    monkeypatch.setattr(mir, "THEME_ROOT", theme)
    monkeypatch.setattr(mir, "MIRROR_DIR", mirror)

    pushed = {"called": False}

    def fake_push(*_a, **_k):
        pushed["called"] = True
        raise AssertionError("push should not run")

    monkeypatch.setattr(mir, "push_mirror_to_github", fake_push)

    session = ReviewSession(review_goal="local check")
    result = mir.build_review_package(session, include_recordings=False, log=[])
    assert result.ok
    assert (mirror / "REVIEW_MANIFEST.json").is_file()
    assert not pushed["called"]


def test_finalize_manifest_double_amend(tmp_path) -> None:
    import json
    import subprocess

    from Komponenty.integracjagpt import mirror as mir
    from Komponenty.integracjagpt.review_session import ReviewSession

    mirror = tmp_path / "mirror"
    mirror.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=mirror, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=mirror, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=mirror, check=True)
    (mirror / "foo.txt").write_text("a", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=mirror, check=True)
    subprocess.run(["git", "commit", "-m", "review: test"], cwd=mirror, check=True)

    sync = mir.SyncResult(copied=["foo.txt"])
    sess = ReviewSession(review_goal="goal")
    log: list[str] = []
    head = mir._finalize_manifest_snapshot_commit(mirror, sync, sess, log)

    data = json.loads((mirror / "REVIEW_MANIFEST.json").read_text(encoding="utf-8"))
    assert data["review_goal"] == "goal"
    assert data["snapshot_commit"]
    assert head == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=mirror).decode().strip()
    assert len(log) > 0


def test_make_video_session_dir(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import config as cfg
    from Komponenty.integracjagpt.record import make_video_session_dir

    monkeypatch.setattr(cfg, "VIDEOS_DIR", tmp_path / "nagrania")

    plain = make_video_session_dir()
    assert plain.parent.name == "nagrania"
    assert plain.is_dir()
    assert len(plain.name) == 15  # YYYYMMDD-HHMMSS

    labeled = make_video_session_dir(session_label="Hero scroll UX")
    assert labeled.name.endswith("-hero-scroll-ux")
    assert labeled.is_dir()


def test_import_manual_review_videos(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import record as rec_mod
    from Komponenty.integracjagpt.record import find_review_demo_recording, import_manual_review_videos

    demos = tmp_path / "review-demos"
    monkeypatch.setattr(rec_mod, "REVIEW_DEMOS_DIR", demos)

    src = tmp_path / "my-recording.mp4"
    src.write_bytes(b"fake-mp4")

    log: list[str] = []
    out = import_manual_review_videos(src, log=log)
    assert out["desktop"] == demos / "latest-desktop.webm"
    assert (demos / "latest-desktop.webm").read_bytes() == b"fake-mp4"
    assert find_review_demo_recording(demos, "desktop") == "docs/review-demos/latest-desktop.webm"


def test_import_knowledge_zip(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import zip_knowledge as zk
    from Komponenty.integracjagpt.zip_knowledge import import_knowledge_zip

    monkeypatch.setattr(zk, "DATA_DIR", tmp_path)
    monkeypatch.setattr(zk, "KNOWLEDGE_ZIP_FILE", tmp_path / "gpt_knowledge.zip")

    src = tmp_path / "architect.zip"
    src.write_bytes(b"PK fake")

    name, loaded_at = import_knowledge_zip(src)
    assert name == "architect.zip"
    assert loaded_at
    assert (tmp_path / "gpt_knowledge.zip").read_bytes() == b"PK fake"


def test_build_conversation_start_prompt(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import zip_knowledge as zk
    from Komponenty.integracjagpt.handoff import build_conversation_start_prompt

    repo_ph = "[TU WPISZ: gicleeart-gpt albo gicleeapp]"
    sha_ph = "[TU WPISZ SHA]"
    scope_ph = "[TU WPISZ, np. homepage / header / katalog / launcher UI / aplikacja / integracja]"

    starter = tmp_path / "Pliki startowe dla GPT"
    starter.mkdir()
    (starter / "Wiadomość początkowa.txt").write_text(
        f"ZIP wiedzy.\nRepo:\n{repo_ph}\nSHA:\n{sha_ph}\nZakres:\n{scope_ph}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(zk, "GPT_STARTER_DIR", starter)

    msg = build_conversation_start_prompt(
        commit_sha="abc123",
        review_goal="hero scroll UX",
    )
    assert "abc123" in msg
    assert "hero scroll UX" in msg
    assert "gicleeart-gpt" in msg
    assert repo_ph not in msg
    assert sha_ph not in msg
    assert scope_ph not in msg


def test_build_conversation_start_prompt_gicleeapp(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import zip_knowledge as zk
    from Komponenty.integracjagpt.handoff import build_conversation_start_prompt

    starter = tmp_path / "Pliki startowe dla GPT"
    starter.mkdir()
    (starter / "Wiadomość początkowa.txt").write_text(
        "Repo:\n[TU WPISZ: gicleeart-gpt albo gicleeapp]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(zk, "GPT_STARTER_DIR", starter)

    msg = build_conversation_start_prompt(review_goal="launcher UI aplikacji")
    assert "gicleeapp" in msg


def test_find_newest_obs_recording(tmp_path) -> None:
    from Komponenty.integracjagpt.obs_record import find_newest_recording
    import os
    import time

    old = tmp_path / "old.mkv"
    old.write_bytes(b"x")
    old_time = time.time() - 60
    os.utime(old, (old_time, old_time))

    new = tmp_path / "fresh.mp4"
    new.write_bytes(b"video")
    found = find_newest_recording(tmp_path, since=time.time() - 5)
    assert found == new


def test_stop_obs_recording_imports_review_demo(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import config as cfg_mod
    from Komponenty.integracjagpt import obs_record as obs_mod
    from Komponenty.integracjagpt import record as rec_mod
    from Komponenty.integracjagpt.config import GptConfig
    from Komponenty.integracjagpt.obs_record import stop_obs_recording

    demos = tmp_path / "review-demos"
    record_dir = tmp_path / "obs-out"
    record_dir.mkdir()
    source = record_dir / "2026.mp4"
    source.write_bytes(b"obs-rec")

    monkeypatch.setattr(rec_mod, "REVIEW_DEMOS_DIR", demos)
    obs_mod._active_session = obs_mod._ActiveObsSession(  # noqa: SLF001 — test stanu sesji
        record_directory=record_dir,
        started_at=0.0,
    )

    class FakeClient:
        def get_record_status(self):
            from types import SimpleNamespace

            return SimpleNamespace(output_active=False)

        def disconnect(self) -> None:
            pass

    monkeypatch.setattr(obs_mod, "_connect_client_for_cfg", lambda _cfg: (FakeClient(), None))

    cfg = GptConfig()
    res = stop_obs_recording(cfg, log=[])
    assert res.ok
    assert res.review_demo_path == demos / "latest-desktop.webm"
    assert (demos / "latest-desktop.webm").read_bytes() == b"obs-rec"
    assert obs_mod.obs_recording_active() is False


def test_load_obs_websocket_settings_from_file(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt.config import GptConfig
    from Komponenty.integracjagpt.obs_record import load_obs_websocket_settings

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "server_enabled": False,
                "auth_required": True,
                "server_password": "secret-from-obs",
                "server_port": 4456,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "Komponenty.integracjagpt.obs_record._obs_ws_config_path",
        lambda: cfg_path,
    )

    ws = load_obs_websocket_settings(GptConfig())
    assert ws.port == 4456
    assert ws.password == "secret-from-obs"
    assert ws.password_source == "obs_config"
    assert ws.server_enabled is False


def test_enable_obs_websocket_server(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt.obs_record import enable_obs_websocket_server

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"server_enabled": false, "server_port": 4455}\n', encoding="utf-8")
    monkeypatch.setattr(
        "Komponenty.integracjagpt.obs_record._obs_ws_config_path",
        lambda: cfg_path,
    )

    changed = enable_obs_websocket_server()
    assert changed is True
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data["server_enabled"] is True


def test_purge_review_demo_videos(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import record as rec_mod
    from Komponenty.integracjagpt.record import purge_review_demo_videos

    demos = tmp_path / "review-demos"
    demos.mkdir()
    (demos / "latest-desktop.webm").write_bytes(b"a")
    (demos / "latest-mobile.mp4").write_bytes(b"b")
    (demos / "latest-desktop.png").write_bytes(b"keep")

    monkeypatch.setattr(rec_mod, "REVIEW_DEMOS_DIR", demos)
    removed = purge_review_demo_videos()
    assert removed == 2
    assert not (demos / "latest-desktop.webm").exists()
    assert (demos / "latest-desktop.png").exists()


def test_build_starter_knowledge_zip_from_md_files(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import zip_knowledge as zk

    starter = tmp_path / "Pliki startowe dla GPT"
    starter.mkdir()
    manifest = ("A.md", "B.md")
    for name in manifest:
        (starter / name).write_text(f"# {name}", encoding="utf-8")
    (starter / "ARCHIVE_v34.md").write_text("# old", encoding="utf-8")
    (starter / "ignore.txt").write_text("x", encoding="utf-8")

    data_dir = tmp_path / "data"
    monkeypatch.setattr(zk, "GPT_STARTER_DIR", starter)
    monkeypatch.setattr(zk, "DATA_DIR", data_dir)
    monkeypatch.setattr(zk, "CLEAN_PACK_V35_ACTIVE_FILES", manifest)

    zip_path = zk.build_starter_knowledge_zip()
    assert zip_path.name == "giclee_cursor_architect_knowledge.zip"
    assert zip_path.is_file()
    assert data_dir.joinpath("gpt_knowledge.zip").is_file()

    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
    assert names == ["A.md", "B.md"]


def test_read_start_message(tmp_path, monkeypatch) -> None:
    from Komponenty.integracjagpt import zip_knowledge as zk

    starter = tmp_path / "Pliki startowe dla GPT"
    starter.mkdir()
    (starter / "Wiadomość początkowa.txt").write_text("Cześć GPT", encoding="utf-8")
    monkeypatch.setattr(zk, "GPT_STARTER_DIR", starter)

    assert zk.read_start_message() == "Cześć GPT"
