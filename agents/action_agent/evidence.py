"""Read a photo, GPS, or note line posted by a person in the room."""

from __future__ import annotations

import re
from dataclasses import dataclass

PHOTO_RE = re.compile(r"^photo:\s*(\S+)\s*$", re.IGNORECASE)
GPS_RE = re.compile(r"^gps:\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", re.IGNORECASE)
NOTE_RE = re.compile(r"^note:\s*(.+?)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class EvidenceLine:
    kind: str
    uri: str


def parse_evidence(text: str) -> EvidenceLine | None:
    stripped = text.strip()
    photo = PHOTO_RE.match(stripped)
    if photo:
        return EvidenceLine("photo", photo.group(1))
    gps = GPS_RE.match(stripped)
    if gps:
        lat = float(gps.group(1))
        lon = float(gps.group(2))
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return EvidenceLine("gps", "")
        return EvidenceLine("gps", f"{gps.group(1)},{gps.group(2)}")
    note = NOTE_RE.match(stripped)
    if note and note.group(1):
        return EvidenceLine("note", note.group(1))
    return None
