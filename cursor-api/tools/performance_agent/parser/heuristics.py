"""UX suspect heuristics for performance logs."""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.performance_agent.parser.jsonl_loader import PerfEvent
from tools.performance_agent.profiles import Budgets


REVEAL_EVENTS = frozenset(
    {
        "studio.gicleeframe.atomic_reveal.revealed",
        "studio.gicleeframe.visual.visible_ready",
        "studio.gicleeframe.visual.perceived_ready",
    }
)

GF_REVEAL_MARKERS = frozenset(
    {
        "studio.gicleeframe.atomic_reveal.revealed",
        "studio.gicleeframe.visual.visible_ready",
    }
)

CLICK_EVENT = "studio.gicleeframe.selection.click"

VISIBLE_WORK_PATTERNS = (
    "scroll_upgrade",
    "incremental_batch",
    "identity_card_late",
    "actions_late",
    "control.structure",
    "placeholder_state",
)

SKELETON_LAYOUT_PATTERNS = (
    "skeleton",
    "placeholder",
    "loading_state",
    "scroll_upgrade",
    "identity_card_late",
    "actions_late",
    "incremental_batch",
    "prewarm",
    "deferred",
)

DETAILS_EVENT_MARKERS = (
    "details_on_demand.requested",
    "details_shell.applied",
    "details_on_demand.applied",
    "details_module.requested",
    "details_module.applied",
    "details_module.batch",
)

FULL_AUTO_STAGE_MARKERS = (
    "preview",
    "page_context",
    "layer_nav",
    "children",
)

CACHE_CONFLICT_MARKERS = (
    "populate",
    "preview",
    "layer_nav",
    "children",
    "page_context",
)


@dataclass
class Suspect:
    id: str
    priority: str
    message: str
    phase: str = "unknown"
    line_no: int | None = None
    event: str | None = None
    evidence: str = ""
    ms: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "priority": self.priority,
            "phase": self.phase,
            "message": self.message,
            "line_no": self.line_no,
            "event": self.event,
            "evidence": self.evidence,
            "ms": self.ms,
        }


@dataclass
class HeuristicsResult:
    suspects: list[Suspect] = field(default_factory=list)
    details_cta_events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "suspect_count": len(self.suspects),
            "suspects": [suspect.to_dict() for suspect in self.suspects],
            "details_cta_events": self.details_cta_events,
        }


def _contains_pattern(text: str, patterns: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        if pattern in lowered:
            return pattern
    return None


def _details_severity(ms: float, budgets: Budgets) -> str | None:
    if ms >= budgets.details_cta_major_ms:
        return "major"
    if ms >= budgets.details_cta_warning_ms:
        return "warning"
    return None


def _is_details_event(event_name: str) -> bool:
    return any(marker in event_name for marker in DETAILS_EVENT_MARKERS)


def _first_gf_reveal_index(events: list[PerfEvent]) -> int | None:
    for index, event in enumerate(events):
        if event.event in GF_REVEAL_MARKERS:
            return index
    return None


def _click_windows(events: list[PerfEvent]) -> list[tuple[int, int]]:
    indices = [i for i, event in enumerate(events) if event.event == CLICK_EVENT]
    windows: list[tuple[int, int]] = []
    for idx, start in enumerate(indices):
        end = indices[idx + 1] if idx + 1 < len(indices) else len(events)
        windows.append((start, end))
    return windows


def _phase_for_line(
    line_index: int,
    *,
    first_reveal_index: int | None,
    click_windows: list[tuple[int, int]],
    is_details: bool,
) -> str:
    if is_details:
        return "details"
    if first_reveal_index is not None and line_index < first_reveal_index:
        return "before_reveal"
    for start, end in click_windows:
        if start <= line_index < end:
            return "after_click"
    if first_reveal_index is not None and line_index >= first_reveal_index:
        return "after_reveal"
    return "unknown"


def _skeleton_priority(phase: str) -> str:
    if phase == "before_reveal":
        return "P2"
    if phase in {"after_reveal", "after_click"}:
        return "P1"
    return "P2"


def detect_heuristics(events: list[PerfEvent], budgets: Budgets) -> HeuristicsResult:
    suspects: list[Suspect] = []
    details_cta_events: list[dict] = []
    seen_skeleton: set[tuple[int, str]] = set()

    first_reveal_index = _first_gf_reveal_index(events)
    click_windows = _click_windows(events)

    for index, event in enumerate(events):
        event_name = event.event
        is_details = _is_details_event(event_name)
        phase = _phase_for_line(
            index,
            first_reveal_index=first_reveal_index,
            click_windows=click_windows,
            is_details=is_details,
        )

        pattern = _contains_pattern(event_name, SKELETON_LAYOUT_PATTERNS)
        if pattern is not None:
            key = (event.line_no, pattern)
            if key not in seen_skeleton:
                seen_skeleton.add(key)
                suspects.append(
                    Suspect(
                        id="SKELETON_LAYOUT_SUSPECT",
                        priority=_skeleton_priority(phase),
                        phase=phase,
                        message=f"Event name suggests skeleton/layout shift pattern ({pattern})",
                        line_no=event.line_no,
                        event=event_name,
                        evidence=f"matched pattern: {pattern}",
                        ms=event.primary_ms(),
                    )
                )

        if is_details:
            ms = event.since_request_ms
            severity = _details_severity(ms, budgets) if ms is not None else None
            details_cta_events.append(
                {
                    "line_no": event.line_no,
                    "event": event_name,
                    "since_request_ms": ms,
                    "elapsed_ms": event.elapsed_ms,
                    "module": event.module,
                    "stage": event.stage,
                    "severity": severity,
                }
            )
            if severity:
                suspects.append(
                    Suspect(
                        id="DETAILS_CTA_SLOW",
                        priority="P0" if severity == "major" else "P1",
                        phase="details",
                        message=f"Details CTA event exceeded {budgets.details_cta_warning_ms}ms threshold",
                        line_no=event.line_no,
                        event=event_name,
                        evidence=f"since_request_ms={ms}",
                        ms=ms,
                    )
                )

    for index, event in enumerate(events):
        if event.event not in REVEAL_EVENTS:
            continue
        for later_index, later in enumerate(events[index + 1 :], start=index + 1):
            if later.event in REVEAL_EVENTS:
                break
            pattern = _contains_pattern(later.event, VISIBLE_WORK_PATTERNS)
            if pattern is None:
                continue
            phase = _phase_for_line(
                later_index,
                first_reveal_index=first_reveal_index,
                click_windows=click_windows,
                is_details=False,
            )
            suspects.append(
                Suspect(
                    id="VISIBLE_WORK_AFTER_REVEAL",
                    priority="P0",
                    phase=phase if phase != "unknown" else "after_reveal",
                    message="Visible/deferred work detected after reveal milestone",
                    line_no=later.line_no,
                    event=later.event,
                    evidence=(
                        f"after reveal {event.event} (line {event.line_no}); "
                        f"matched pattern: {pattern}"
                    ),
                    ms=later.primary_ms(),
                )
            )
            break

    for index, event in enumerate(events):
        if "details_shell.applied" not in event.event:
            continue
        for later in events[index + 1 : index + 40]:
            if "details_module.requested" in later.event:
                break
            if "details_on_demand" in later.event or "details_module" in later.event:
                continue
            if not any(marker in later.event for marker in FULL_AUTO_STAGE_MARKERS):
                continue
            suspects.append(
                Suspect(
                    id="FULL_AUTO_DETAILS_REGRESSION",
                    priority="P0",
                    phase="details",
                    message="Auto stage events after details_shell.applied without details_module.requested",
                    line_no=later.line_no,
                    event=later.event,
                    evidence=(
                        f"after details_shell.applied line {event.line_no}; "
                        f"auto stage without module request"
                    ),
                    ms=later.primary_ms(),
                )
            )
            break

    for index, event in enumerate(events):
        has_cache = (
            event.cache_hit is True
            or event.raw.get("cache_hit") is True
            or event.raw.get("minimal_cache_hit") is True
            or "minimal_cache_hit" in event.event.lower()
        )
        if not has_cache:
            continue
        phase = _phase_for_line(
            index,
            first_reveal_index=first_reveal_index,
            click_windows=click_windows,
            is_details="details" in event.event,
        )
        for later_index, later in enumerate(events[index + 1 : index + 25], start=index + 1):
            conflict = _contains_pattern(later.event, CACHE_CONFLICT_MARKERS)
            if conflict is None:
                continue
            later_phase = _phase_for_line(
                later_index,
                first_reveal_index=first_reveal_index,
                click_windows=click_windows,
                is_details=False,
            )
            suspects.append(
                Suspect(
                    id="CACHE_UX_CONFLICT",
                    priority="P1",
                    phase=later_phase if later_phase != "unknown" else phase,
                    message="Cache hit followed by heavy populate/preview work",
                    line_no=later.line_no,
                    event=later.event,
                    evidence=(
                        f"after cache event {event.event} (line {event.line_no}); "
                        f"conflict pattern: {conflict}"
                    ),
                    ms=later.primary_ms(),
                )
            )
            break

    deduped: list[Suspect] = []
    seen: set[tuple[str, int | None, str | None]] = set()
    for suspect in suspects:
        key = (suspect.id, suspect.line_no, suspect.event)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suspect)

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    deduped.sort(key=lambda s: (priority_order.get(s.priority, 9), -(s.ms or 0)))

    return HeuristicsResult(suspects=deduped, details_cta_events=details_cta_events)
