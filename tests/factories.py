"""Small builders so model tests share one boat and one operation."""

from __future__ import annotations

from agents.common.models import Boat, Operation, utcnow


def add_boat(session, boat_id: str = "sagar-4", name: str = "Sagar-4") -> Boat:
    boat = Boat(
        id=boat_id,
        name=name,
        owner="Prakash Jadhav",
        licence_no="RTN-FISH-2019-1142",
        district="Ratnagiri",
        home_port="Harnai",
        crew_json='[{"name": "Prakash Jadhav", "role": "skipper"}]',
        gear="gillnet",
    )
    session.add(boat)
    session.flush()
    return boat


def add_operation(session, boat_id: str = "sagar-4", opened_by: str = "ramesh") -> Operation:
    operation = Operation(
        boat_id=boat_id,
        status="open",
        opened_at=utcnow(),
        opened_by=opened_by,
    )
    session.add(operation)
    session.flush()
    return operation
