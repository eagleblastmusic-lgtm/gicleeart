"""Wykrywanie botów i spamu."""

from __future__ import annotations

import re

BOT_UA_PATTERNS = re.compile(
    r"(googlebot|bingbot|yandex|baiduspider|duckduckbot|slurp|facebot|"
    r"facebookexternalhit|twitterbot|linkedinbot|pinterest|semrush|ahrefs|"
    r"petalbot|bytespider|gptbot|claudebot|headlesschrome|lighthouse|"
    r"chrome-lighthouse|pagespeed|pingdom|uptimerobot|bot|crawler|spider|"
    r"preview|prerender|phantomjs|selenium)",
    re.I,
)

MAX_EVENTS_PER_SESSION_HOUR = 500


def is_bot_user_agent(user_agent: str) -> bool:
    ua = (user_agent or "").strip()
    if not ua:
        return True
    if len(ua) < 12:
        return True
    return bool(BOT_UA_PATTERNS.search(ua))


def is_suspicious_session_event_count(count: int) -> bool:
    return count > MAX_EVENTS_PER_SESSION_HOUR


def classify_bot(
    *,
    user_agent: str,
    event_name: str,
    session_id: str,
    session_event_count: int,
) -> bool:
    if is_bot_user_agent(user_agent):
        return True
    if not event_name:
        return True
    if not session_id and event_name not in {"checkout_completed"}:
        return False
    if is_suspicious_session_event_count(session_event_count):
        return True
    return False
