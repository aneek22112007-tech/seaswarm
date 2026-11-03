"""Persistence off duplicates sectors and drops the sign-off. On does neither."""

from __future__ import annotations

from scripts.killswitch_demo import render, run_mode


def test_same_scenario_diverges_when_persistence_is_off(tmp_path):
    kept = run_mode(tmp_path / "on.db", "on")
    lost = run_mode(tmp_path / "off.db", "off")
    assert kept.sector_count == 3
    assert kept.approval_count == 1
    assert kept.approver == "ramesh"
    assert "approved escalation" in kept.signoff
    assert lost.sector_count == 6
    assert kept.request_stored is True
    assert lost.approval_count == 0
    assert lost.request_stored is False
    assert lost.approver == ""
    assert "not applied" in lost.signoff
    assert kept.coverage == lost.coverage
    assert "Sector-1 x2" in render(lost)
    assert "sectors were duplicated" in render(lost)
    assert "sign-off was stored" in render(kept)
