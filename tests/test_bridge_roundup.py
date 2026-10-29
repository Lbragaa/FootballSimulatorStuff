from copy import deepcopy
from uuid import uuid4
import pytest
from braga_era.bridge.roundup import Roundups, compact_events, expand_events


class Career:
    key = b"task04c-public-test-key-32-bytes-ONLY"
    career = "test-roundup"
    test_only = True
    head = "a" * 64
    def __init__(self):
        self.remaining = [{"key": "lib:one", "home": "foreign:a", "away": "club:1"},
                          {"key": "lib:two", "home": "club:2", "away": "foreign:b"}]
        self.cache, self.effects = {}, 0
    def identity(self):
        return {"checkpoint": self.head}
    def play(self, view):
        assert view == "next"
        return {"events": deepcopy(self.remaining)}
    def read(self, fixture, page_id):
        if page_id not in self.cache:
            assert fixture in {r["key"] for r in self.remaining}
            self.effects += 1
            self.remaining = [r for r in self.remaining if r["key"] != fixture]
            self.cache[page_id] = {"events": [{"kind": "FINAL_WHISTLE"}], "postmatch_available": True,
                                   "postmatch_summary": {"score": [1, 0], "resolution": {"method": "regulation"}}}
        return deepcopy(self.cache[page_id])


def test_roundup_holds_detailed_and_replays_exact_delivery(tmp_path):
    career = Career()
    roundup = Roundups(career, tmp_path, read_page=career.read)
    rid = str(uuid4())
    response = roundup.run(rid, career.head, ["lib:one"], detailed=["lib:two"])
    assert response["summaries"][0]["score"] == [1, 0]
    assert response["held_for_detail"] == ["lib:two"]
    assert response["next_events"] == career.remaining
    assert len(career.remaining) == 1
    assert roundup.run(rid, career.head, ["lib:one"], detailed=["lib:two"]) == response
    assert career.effects == 1
    with pytest.raises(ValueError):
        roundup.run(rid, career.head, ["lib:two"])


def test_roundup_crash_after_final_page_preserves_receipt(tmp_path):
    career = Career()
    roundup = Roundups(career, tmp_path, read_page=career.read, crash="after_page_before_journal")
    rid = str(uuid4())
    with pytest.raises(RuntimeError):
        roundup.run(rid, career.head, ["lib:one"])
    roundup = Roundups(career, tmp_path, read_page=career.read)
    assert roundup.run(rid, career.head, ["lib:one"])["summaries"][0]["fixture"] == "lib:one"
    assert career.effects == 1


def test_roundup_denies_future_vasco_overlap_and_stale_head(tmp_path):
    career = Career()
    roundup = Roundups(career, tmp_path, read_page=career.read)
    for fixtures, detailed, head in [(["lib:future"], [], career.head),
                                     (["lib:one"], ["lib:one"], career.head),
                                     (["lib:one"], [], "b" * 64)]:
        with pytest.raises(ValueError):
            roundup.run(str(uuid4()), head, fixtures, detailed=detailed)
    career.remaining[0]["home"] = "club:15"
    with pytest.raises(ValueError, match="Vasco"):
        roundup.run(str(uuid4()), career.head, ["lib:one"])
    assert career.effects == 0


def test_vasco_protection_matches_accepted_club_identity(accepted_path):
    from braga_era.db import connect_read_only
    from braga_era.bridge.roundup import VASCO
    with connect_read_only(accepted_path) as c:
        club = c.execute("SELECT id FROM clubs WHERE name='Vasco'").fetchone()[0]
        assert VASCO == f"club:{club}"


def test_compact_presentation_is_lossless_and_tamper_evident():
    events = [{"sequence": i, "kind": "PASS", "on_field_home": list(range(1, 12)),
               "on_field_away": list(range(20, 31)), "details": {"player": 1}} for i in range(20)]
    presentation = compact_events(events)
    assert len(presentation["on_field_states"]) == 1
    assert expand_events(presentation) == events
    assert "on_field_home" in events[0]  # original engine events never rewritten.
    next(iter(presentation["on_field_states"].values()))["home"].pop()
    with pytest.raises(ValueError):
        expand_events(presentation)
