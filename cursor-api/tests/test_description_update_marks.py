"""Testy oznaczen postepu w «Aktualizuj opis»."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.dodajobraz import description_update as du


@pytest.fixture()
def marks_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    update_path = tmp_path / "description_update_marks.json"
    pending_path = tmp_path / "description_pl_pending_marks.json"
    do_tlum_path = tmp_path / "description_do_tlumaczenia_marks.json"
    sent_path = tmp_path / "description_translations_sent_marks.json"
    monkeypatch.setattr(du, "_DESCRIPTION_UPDATE_MARKS_FILE", update_path)
    monkeypatch.setattr(du, "_DESCRIPTION_PL_PENDING_MARKS_FILE", pending_path)
    monkeypatch.setattr(du, "_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE", do_tlum_path)
    monkeypatch.setattr(du, "_DESCRIPTION_TRANSLATIONS_SENT_MARKS_FILE", sent_path)
    return update_path, pending_path, do_tlum_path, sent_path


def test_pl_only_save_marks_purple(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, pending_path, do_tlum_path, _sent_path = marks_files
    du.update_description_marks_after_save(101, saved_locales=["pl"])
    assert json.loads(update_path.read_text(encoding="utf-8")) == []
    assert json.loads(pending_path.read_text(encoding="utf-8")) == [101]


def test_full_translation_save_marks_green(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, pending_path, _do_tlum_path, _sent_path = marks_files
    du.set_description_pl_pending_mark(202, marked=True)
    du.update_description_marks_after_save(
        202,
        saved_locales=["pl", "en", "de", "fr", "es", "nl", "it"],
    )
    assert json.loads(update_path.read_text(encoding="utf-8")) == [202]
    assert json.loads(pending_path.read_text(encoding="utf-8")) == []


def test_translations_pushed_marks_green(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, pending_path, _do_tlum_path, _sent_path = marks_files
    du.set_description_pl_pending_mark(303, marked=True)
    du.update_description_marks_after_save(
        303,
        saved_locales=["pl"],
        translations_pushed=True,
    )
    assert json.loads(update_path.read_text(encoding="utf-8")) == [303]
    assert json.loads(pending_path.read_text(encoding="utf-8")) == []


def test_translations_pasted_marks_green(marks_files: tuple[Path, Path, Path, Path]) -> None:
    """Po «Wklej tlumaczenia do akapitu» — zielone nawet bez PL w saved_locales."""
    update_path, pending_path, _do_tlum_path, _sent_path = marks_files
    du.set_description_pl_pending_mark(404, marked=True)
    du.update_description_marks_after_save(
        404,
        saved_locales=["en", "de", "fr", "es", "nl", "it"],
        translations_pasted=True,
    )
    assert json.loads(update_path.read_text(encoding="utf-8")) == [404]
    assert json.loads(pending_path.read_text(encoding="utf-8")) == []


def test_normalize_paragraphs_keeps_positions() -> None:
    """Jeden zmieniony akapit + dwa stare — nadal 3 akapity do zapisu."""
    paras = du.normalize_paragraphs_for_save(
        ["Nowy akapit", "Stary drugi", "Stary trzeci"],
        locale="en",
    )
    assert paras == ["Nowy akapit", "Stary drugi", "Stary trzeci"]


def test_normalize_paragraphs_rejects_sparse() -> None:
    with pytest.raises(ValueError, match="niepuste"):
        du.normalize_paragraphs_for_save(["Tylko jeden", "", ""], locale="de")


def test_gpt_and_sonnet_translation_marks_batch(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, _pending_path, _do_tlum_path, _sent_path = marks_files
    gpt_path = update_path.parent / "description_gpt_translation_marks.json"
    sonn_path = update_path.parent / "description_sonnet_translation_marks.json"
    du._DESCRIPTION_GPT_TRANSLATION_MARKS_FILE = gpt_path
    du._DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE = sonn_path
    du.set_description_gpt_translation_marks_batch([11, 12], marked=True)
    du.set_description_sonnet_translation_marks_batch([12, 13], marked=True)
    assert json.loads(gpt_path.read_text(encoding="utf-8")) == [11, 12]
    assert json.loads(sonn_path.read_text(encoding="utf-8")) == [12, 13]
    du.set_description_gpt_translation_marks_batch([11], marked=False)
    assert json.loads(gpt_path.read_text(encoding="utf-8")) == [12]


def test_from_image_marks_batch(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, _pending_path, _do_tlum_path, _sent_path = marks_files
    from_image_path = update_path.parent / "description_from_image_marks.json"
    du._DESCRIPTION_FROM_IMAGE_MARKS_FILE = from_image_path
    du.set_description_from_image_marks_batch([21, 22], marked=True)
    assert json.loads(from_image_path.read_text(encoding="utf-8")) == [21, 22]
    assert du.toggle_description_from_image_mark(21) is False
    assert json.loads(from_image_path.read_text(encoding="utf-8")) == [22]
    assert du.toggle_description_from_image_mark(23) is True
    assert json.loads(from_image_path.read_text(encoding="utf-8")) == [22, 23]


def test_do_tlumaczenia_marks_batch(marks_files: tuple[Path, Path, Path, Path]) -> None:
    _update_path, _pending_path, do_tlum_path, _sent_path = marks_files
    du.set_description_do_tlumaczenia_marks_batch([101, 102], marked=True)
    assert json.loads(do_tlum_path.read_text(encoding="utf-8")) == [101, 102]
    assert du.toggle_description_do_tlumaczenia_mark(101) is False
    assert json.loads(do_tlum_path.read_text(encoding="utf-8")) == [102]


def test_bez_16_marks_batch(marks_files: tuple[Path, Path, Path, Path]) -> None:
    update_path, _pending_path, _do_tlum_path, _sent_path = marks_files
    bez_16_path = update_path.parent / "description_bez_16_marks.json"
    du._DESCRIPTION_BEZ_16_MARKS_FILE = bez_16_path
    du.set_description_bez_16_marks_batch([31, 32], marked=True)
    assert json.loads(bez_16_path.read_text(encoding="utf-8")) == [31, 32]
    assert du.toggle_description_bez_16_mark(31) is False
    assert json.loads(bez_16_path.read_text(encoding="utf-8")) == [32]
    assert du.toggle_description_bez_16_mark(33) is True
    assert json.loads(bez_16_path.read_text(encoding="utf-8")) == [32, 33]


def test_legacy_sent_marks_not_migrated(marks_files: tuple[Path, Path, Path, Path]) -> None:
    _update_path, _pending_path, do_tlum_path, sent_path = marks_files
    sent_path.write_text("[999]\n", encoding="utf-8")
    assert du.load_description_do_tlumaczenia_marks() == set()
    assert not do_tlum_path.is_file() or json.loads(do_tlum_path.read_text(encoding="utf-8")) == []


def test_pl_only_save_does_not_auto_mark_do_tlum(marks_files: tuple[Path, Path, Path, Path]) -> None:
    _update_path, _pending_path, do_tlum_path, _sent_path = marks_files
    du.update_description_marks_after_save(505, saved_locales=["pl"])
    assert not do_tlum_path.is_file() or json.loads(do_tlum_path.read_text(encoding="utf-8")) == []


def test_full_translation_does_not_clear_do_tlum_mark(marks_files: tuple[Path, Path, Path, Path]) -> None:
    _update_path, _pending_path, do_tlum_path, _sent_path = marks_files
    du.set_description_do_tlumaczenia_mark(606, marked=True)
    du.update_description_marks_after_save(
        606,
        saved_locales=["pl", "en", "de", "fr", "es", "nl", "it"],
    )
    assert json.loads(do_tlum_path.read_text(encoding="utf-8")) == [606]
