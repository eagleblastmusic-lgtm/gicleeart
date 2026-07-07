"""UX questionnaire for manual Performance Agent sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

ENUM_QUESTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("skeletons_seen", "Czy widziałeś skeletony / puste placeholdery?", ("yes", "no", "somewhat", "unknown")),
    ("layout_shift", "Czy layout zmieniał kształt albo elementy przeskakiwały?", ("yes", "no", "somewhat", "unknown")),
    ("sequential_popin", "Czy elementy pojawiały się po kolei?", ("yes", "no", "somewhat", "unknown")),
    ("click_instant", "Czy klik miał natychmiastową reakcję?", ("yes", "no", "somewhat", "unknown")),
    ("freeze_seen", "Czy był freeze / zawieszenie UI?", ("yes", "no", "somewhat", "unknown")),
    ("overlay_too_long", "Czy overlay był za długi?", ("yes", "no", "somewhat", "unknown")),
    ("cache_felt", "Czy cache przy powrocie był odczuwalny?", ("yes", "no", "somewhat", "unknown")),
)

ENUM_QUESTIONS_BY_ID: dict[str, tuple[str, str, tuple[str, ...]]] = {
    question_id: (question_id, prompt, allowed)
    for question_id, prompt, allowed in ENUM_QUESTIONS
}

SCENARIO_QUESTION_IDS: dict[str, tuple[str, ...]] = {
    "dashboard_cold": ("skeletons_seen", "layout_shift", "sequential_popin", "freeze_seen"),
    "hub_theme": ("skeletons_seen", "layout_shift", "sequential_popin", "freeze_seen"),
    "hub_products": ("skeletons_seen", "layout_shift", "sequential_popin", "freeze_seen"),
    "gf_open": ("skeletons_seen", "layout_shift", "sequential_popin", "overlay_too_long", "freeze_seen"),
    "section_click_normal": ("click_instant", "freeze_seen", "layout_shift"),
    "section_click_fast": ("click_instant", "freeze_seen"),
    "aba_cache": ("click_instant", "cache_felt"),
    "media_section": ("click_instant", "skeletons_seen", "layout_shift"),
    "details_cta": ("click_instant", "overlay_too_long", "cache_felt"),
}

MAIN_COMPLAINT_CHOICES: tuple[str, ...] = (
    "freeze",
    "skeleton",
    "layout_shift",
    "long_overlay",
    "sequential_popin",
    "no_response",
    "details_slow",
    "nothing",
    "other",
)

_ENUM_ALIASES: dict[str, str] = {
    "y": "yes",
    "yes": "yes",
    "t": "yes",
    "true": "yes",
    "n": "no",
    "no": "no",
    "f": "no",
    "false": "no",
    "0": "no",
    "s": "somewhat",
    "somewhat": "somewhat",
    "partial": "somewhat",
    "u": "unknown",
    "unknown": "unknown",
    "?": "unknown",
    "skip": "unknown",
    "": "unknown",
}

_MAIN_COMPLAINT_YES_NO = frozenset({"y", "yes", "n", "no", "t", "f", "true", "false"})


class QuestionnaireIO(Protocol):
    def input(self, prompt: str) -> str: ...
    def print(self, text: str) -> None: ...


@dataclass
class SimpleIO:
    input_fn: Callable[[str], str]
    print_fn: Callable[[str], None]

    def input(self, prompt: str) -> str:
        return self.input_fn(prompt)

    def print(self, text: str) -> None:
        self.print_fn(text)


def questions_for_scenario(scenario_id: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    question_ids = SCENARIO_QUESTION_IDS.get(scenario_id)
    if not question_ids:
        return ENUM_QUESTIONS
    return tuple(ENUM_QUESTIONS_BY_ID[qid] for qid in question_ids if qid in ENUM_QUESTIONS_BY_ID)


def normalize_enum(value: str, allowed: tuple[str, ...]) -> str | None:
    key = value.strip().lower()
    if key in allowed:
        return key
    mapped = _ENUM_ALIASES.get(key)
    if mapped is not None and mapped in allowed:
        return mapped
    return None


def normalize_smoothness_score(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if text in _ENUM_ALIASES and _ENUM_ALIASES[text] == "unknown":
        return None
    try:
        score = int(text)
    except ValueError:
        return None
    if 1 <= score <= 5:
        return score
    return None


def normalize_main_complaint(value: str) -> str | None:
    text = value.strip()
    if not text:
        return "nothing"
    if text.isdigit():
        index = int(text)
        if 1 <= index <= len(MAIN_COMPLAINT_CHOICES):
            return MAIN_COMPLAINT_CHOICES[index - 1]
        return None
    key = text.lower().replace(" ", "_").replace("-", "_")
    if key in MAIN_COMPLAINT_CHOICES:
        return key
    aliases = {
        "overlay": "long_overlay",
        "longoverlay": "long_overlay",
        "details": "details_slow",
        "none": "nothing",
        "ok": "nothing",
    }
    return aliases.get(key)


def _prompt_enum(io: QuestionnaireIO, question_id: str, prompt: str, allowed: tuple[str, ...]) -> str:
    allowed_text = "/".join(allowed)
    for attempt in range(3):
        raw = io.input(f"  {prompt} [{allowed_text}]: ").strip()
        normalized = normalize_enum(raw, allowed)
        if normalized is not None:
            return normalized
        io.print(f"    Nieznana odpowiedź. Użyj: {allowed_text}")
    return "unknown"


def _prompt_smoothness(io: QuestionnaireIO) -> int | None:
    for attempt in range(3):
        raw = io.input("  Ocena płynności 1–5 (Enter=unknown): ").strip()
        if not raw:
            return None
        score = normalize_smoothness_score(raw)
        if score is not None:
            return score
        io.print("    Podaj liczbę 1–5 lub Enter dla unknown.")
    return None


def _prompt_main_complaint(io: QuestionnaireIO) -> str:
    io.print("  Co najbardziej przeszkadzało? (Enter=pomiń)")
    for index, choice in enumerate(MAIN_COMPLAINT_CHOICES, start=1):
        io.print(f"    {index}) {choice}")
    for attempt in range(3):
        raw = io.input("  Wybierz numer 1–9 lub Enter: ").strip()
        if not raw:
            return "nothing"
        if raw.lower() in _MAIN_COMPLAINT_YES_NO:
            io.print("    To nie jest pytanie tak/nie — wybierz numer 1–9 lub Enter.")
            continue
        normalized = normalize_main_complaint(raw)
        if normalized is not None:
            return normalized
        io.print("    Nieznana wartość. Podaj numer 1–9 lub Enter.")
    return "other"


def ask_scenario(
    scenario_id: str,
    scenario_name: str,
    io: QuestionnaireIO,
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    if skipped:
        return {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "skipped": True,
            "answers": {},
        }

    io.print(f"\n--- Ankieta UX: {scenario_name} ({scenario_id}) ---")
    answers: dict[str, Any] = {}

    for question_id, prompt, allowed in questions_for_scenario(scenario_id):
        answers[question_id] = _prompt_enum(io, question_id, prompt, allowed)

    answers["main_complaint"] = _prompt_main_complaint(io)
    answers["smoothness_score"] = _prompt_smoothness(io)
    answers["note"] = io.input("  Krótka notatka (Enter=puste): ").strip()

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "skipped": False,
        "answers": answers,
    }


def answers_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize pre-filled answers (for tests)."""
    answers = dict(data.get("answers", data))
    for question_id, _, allowed in ENUM_QUESTIONS:
        if question_id in answers:
            value = answers[question_id]
            if isinstance(value, str):
                answers[question_id] = normalize_enum(value, allowed) or "unknown"
    if "main_complaint" in answers and isinstance(answers["main_complaint"], str):
        answers["main_complaint"] = normalize_main_complaint(answers["main_complaint"]) or "other"
    if "smoothness_score" in answers and answers["smoothness_score"] is not None:
        if not isinstance(answers["smoothness_score"], int):
            answers["smoothness_score"] = normalize_smoothness_score(str(answers["smoothness_score"]))
    return answers
