"""Two boats never share a sector. The refusal string is what the room hears."""

from __future__ import annotations


def assignment_conflict(
    existing: dict[str, str | None],
    sector: str,
    boat: str,
) -> str | None:
    current = existing.get(sector)
    if current and current != boat:
        return (
            f"Conflict: {sector} is already assigned to {current}. "
            f"Refusing to assign {boat} as well."
        )
    return None
