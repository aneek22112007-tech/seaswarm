"""Deterministic eligibility for family support schemes.

Rules live in the scheme records. This module only applies them. It does not
ask a model who qualifies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class SchemeMatch:
    scheme_id: str
    name: str
    eligible: bool
    reasons: tuple[str, ...]
    documents: tuple[str, ...]
    deadline: date
    amount_inr: int


def match_schemes(profile: dict, schemes: list[dict], *, today: date) -> list[SchemeMatch]:
    matches: list[SchemeMatch] = []
    for scheme in schemes:
        eligible, reasons = _evaluate(profile, scheme.get("rules") or {})
        if eligible:
            reasons = ("all eligibility rules matched",)
        deadline = today + timedelta(days=int(scheme["deadline_days"]))
        matches.append(
            SchemeMatch(
                scheme_id=scheme["id"],
                name=scheme["name"],
                eligible=eligible,
                reasons=tuple(reasons),
                documents=tuple(scheme.get("documents") or []),
                deadline=deadline,
                amount_inr=int(scheme.get("amount_inr") or 0),
            )
        )
    return matches


def _evaluate(profile: dict, rules: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    districts = rules.get("districts")
    if districts and profile.get("district") not in districts:
        reasons.append(f"district {profile.get('district')} is outside the scheme area")
    if rules.get("requires_licence") and not profile.get("licence_no"):
        reasons.append("boat licence is missing")
    minimum_overdue = rules.get("min_overdue_hours", 0)
    if float(profile.get("overdue_hours") or 0) < float(minimum_overdue):
        reasons.append("overdue time is below the scheme minimum")
    allowed_gear = rules.get("gear")
    if allowed_gear and profile.get("gear") not in allowed_gear:
        reasons.append("gear does not match")
    minimum_crew = rules.get("min_crew")
    if minimum_crew is not None and int(profile.get("crew_count") or 0) < int(minimum_crew):
        reasons.append("crew count is below the minimum")
    required_port = rules.get("home_port")
    if required_port and profile.get("home_port") != required_port:
        reasons.append(f"home port is not {required_port}")
    return (not reasons), reasons
