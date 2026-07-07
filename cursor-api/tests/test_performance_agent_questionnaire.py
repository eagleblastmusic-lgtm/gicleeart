from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.questionnaire import (
    MAIN_COMPLAINT_CHOICES,
    SCENARIO_QUESTION_IDS,
    answers_from_dict,
    normalize_enum,
    normalize_main_complaint,
    normalize_smoothness_score,
    questions_for_scenario,
)


def test_normalize_enum_yes_no_somewhat_unknown() -> None:
    allowed = ("yes", "no", "somewhat", "unknown")
    assert normalize_enum("y", allowed) == "yes"
    assert normalize_enum("N", allowed) == "no"
    assert normalize_enum("somewhat", allowed) == "somewhat"
    assert normalize_enum("?", allowed) == "unknown"
    assert normalize_enum("bogus", allowed) is None


def test_normalize_smoothness_score() -> None:
    assert normalize_smoothness_score("3") == 3
    assert normalize_smoothness_score("5") == 5
    assert normalize_smoothness_score("0") is None
    assert normalize_smoothness_score("6") is None
    assert normalize_smoothness_score("") is None


def test_normalize_main_complaint() -> None:
    assert normalize_main_complaint("freeze") == "freeze"
    assert normalize_main_complaint("long overlay") == "long_overlay"
    assert normalize_main_complaint("nothing") == "nothing"
    assert normalize_main_complaint("1") == MAIN_COMPLAINT_CHOICES[0]
    assert normalize_main_complaint("7") == "details_slow"
    assert normalize_main_complaint("") == "nothing"
    assert normalize_main_complaint("y") is None
    assert normalize_main_complaint("yes") is None


def test_questions_for_scenario_subset() -> None:
    gf_questions = questions_for_scenario("gf_open")
    gf_ids = {q[0] for q in gf_questions}
    assert "overlay_too_long" in gf_ids
    assert "cache_felt" not in gf_ids
    assert "click_instant" not in gf_ids

    aba_questions = questions_for_scenario("aba_cache")
    aba_ids = {q[0] for q in aba_questions}
    assert aba_ids == {"click_instant", "cache_felt"}

    assert "dashboard_cold" in SCENARIO_QUESTION_IDS


def test_answers_from_dict_json_shape() -> None:
    data = {
        "answers": {
            "skeletons_seen": "y",
            "layout_shift": "no",
            "sequential_popin": "somewhat",
            "click_instant": "yes",
            "freeze_seen": "no",
            "overlay_too_long": "unknown",
            "cache_felt": "yes",
            "main_complaint": "freeze",
            "smoothness_score": "2",
            "note": "lag on hub",
        }
    }
    answers = answers_from_dict(data)
    assert answers["skeletons_seen"] == "yes"
    assert answers["smoothness_score"] == 2
    assert answers["main_complaint"] == "freeze"

    payload = {
        "mode": "manual",
        "scenarios": [{"scenario_id": "gf_open", "answers": answers}],
    }
    text = json.dumps(payload, ensure_ascii=False)
    assert "gf_open" in text
