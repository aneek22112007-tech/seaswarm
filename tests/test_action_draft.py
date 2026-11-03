"""The escalation card and scheme note use the computed Sagar-4 figures."""

from __future__ import annotations

from agents.action_agent.draft import (
    escalation_payload,
    family_profile,
    render_escalation,
    render_schemes,
    scenario_day,
)
from agents.common.room import load_room
from core.load import load_json
from core.schemes_matcher import match_schemes


def test_pending_card_names_the_coast_guard_and_the_signoff_line():
    room = load_room()
    boat = next(item for item in load_json("boats.json")["boats"] if item["id"] == "sagar-4")
    payload = escalation_payload(boat, room)
    text = render_escalation(boat, payload, approval=None)
    assert "NOT STORED" in text
    assert "Coast Guard / marine police, Harnai" in text
    assert "Sagar-4" in text
    assert "RTN-FISH-2019-1142" in text
    assert "Prakash Jadhav" in text
    assert "2.0 h" in text
    assert "17.8136" in text
    assert "73.0394" in text


def test_scheme_note_keeps_deadlines_and_the_inland_rejection():
    room = load_room()
    boat = next(item for item in load_json("boats.json")["boats"] if item["id"] == "sagar-4")
    matches = match_schemes(
        family_profile(boat, room),
        load_json("schemes.json")["schemes"],
        today=scenario_day(room),
    )
    text = render_schemes("Sagar-4", matches, approval=None)
    assert "INR 200000" in text
    assert "2026-02-14" in text
    assert "INR 500000" in text
    assert "not eligible" in text
    assert "outside the scheme area" in text
    assert "Approved — scheme-outreach" in text
