"""Scheme eligibility is a rules engine, including an inland scheme that does not apply."""

from __future__ import annotations

from datetime import date

from core.load import load_json
from core.schemes_matcher import match_schemes

TODAY = date(2026, 1, 15)
SAGAR = {
    "district": "Ratnagiri",
    "licence_no": "RTN-FISH-2019-1142",
    "overdue_hours": 2,
    "gear": "gillnet",
    "crew_count": 3,
    "home_port": "Harnai",
}


def test_sagar_4_matches_the_coastal_schemes_only():
    matches = match_schemes(SAGAR, load_json("schemes.json")["schemes"], today=TODAY)
    by_id = {match.scheme_id: match for match in matches}
    assert by_id["mh-distress-relief"].eligible is True
    assert by_id["mh-distress-relief"].amount_inr == 200000
    assert by_id["mh-distress-relief"].deadline.isoformat() == "2026-02-14"
    assert "boat licence" in by_id["mh-distress-relief"].documents
    assert by_id["pmmsy-insurance"].eligible is True
    assert by_id["rtn-group-accident"].eligible is True
    assert by_id["inland-pond-grant"].eligible is False
    assert "outside the scheme area" in by_id["inland-pond-grant"].reasons[0]


def test_missing_licence_and_short_overdue_are_rejected():
    profile = {**SAGAR, "licence_no": "", "overdue_hours": 0.5, "crew_count": 0}
    matches = match_schemes(profile, load_json("schemes.json")["schemes"], today=TODAY)
    relief = next(match for match in matches if match.scheme_id == "mh-distress-relief")
    assert relief.eligible is False
    assert "boat licence is missing" in relief.reasons
    assert "overdue time is below the scheme minimum" in relief.reasons
