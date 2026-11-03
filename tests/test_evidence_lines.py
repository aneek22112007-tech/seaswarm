"""Photo, GPS, and note lines become evidence. A bad fix does not."""

from __future__ import annotations

from agents.action_agent.commands import is_mention, wants_close
from agents.action_agent.evidence import parse_evidence


def test_photo_gps_and_note_lines():
    photo = parse_evidence("photo: https://example.test/reef.jpg")
    gps = parse_evidence("GPS: 17.8136, 73.0394")
    note = parse_evidence("note: saw a net west of the reef")
    assert photo is not None and photo.kind == "photo"
    assert photo.uri == "https://example.test/reef.jpg"
    assert gps is not None and gps.uri == "17.8136,73.0394"
    assert note is not None and note.kind == "note"
    assert note.uri == "saw a net west of the reef"


def test_gps_out_of_range_is_empty_and_prose_is_ignored():
    bad = parse_evidence("gps: 120, 10")
    assert bad is not None and bad.uri == ""
    assert parse_evidence("the boat is overdue") is None


def test_close_and_mention_commands():
    assert wants_close("please close the search") is True
    assert wants_close("close search") is True
    assert wants_close("Approved — close-operation") is False
    assert is_mention("Three options\n@action") is True
    assert is_mention("hello") is False
