"""Opt-in summary revelation using stored, signed narration pages only.

No simulation, seed selection, raw-result read or cursor overwrite is performed.
Only a caller-selected subset of the earliest simultaneous group is eligible.
Held matches remain available for detailed commentary before advancing time.
"""

from copy import deepcopy
import json
from pathlib import Path
from uuid import UUID

from .. import lineage
from ..history import canonical_json as encode, digest
from ..world.storage import process_lock

PROFILE = "bridge-roundup-1"
VASCO = "club:15"  # Immutable accepted clubs.id; club:5 is Fluminense.


def compact_events(events):
    """Lossless presentation projection; canonical event/page bytes stay intact."""
    states, projected = {}, []
    for original in events:
        event = deepcopy(original)
        if "on_field_home" in event and "on_field_away" in event:
            state = {"home": event.pop("on_field_home"), "away": event.pop("on_field_away")}
            reference = digest(state)
            states[reference] = state
            event["on_field_state_sha256"] = reference
        projected.append(event)
    return {"presentation": "bridge-events-2", "events": projected, "on_field_states": states}


def expand_events(presentation):
    if presentation["presentation"] != "bridge-events-2":
        raise ValueError("Unsupported presentation")
    events = []
    for original in presentation["events"]:
        event = deepcopy(original)
        reference = event.pop("on_field_state_sha256", None)
        if reference is not None:
            state = presentation["on_field_states"][reference]
            if digest(state) != reference:
                raise ValueError("Changed on-field identity mapping")
            event["on_field_home"], event["on_field_away"] = state["home"], state["away"]
        events.append(event)
    return events


class Roundups:
    def __init__(self, career, directory, *, read_page=None, crash=None):
        self.career, self.directory = career, Path(directory)
        self.read_page = read_page or self._read_page
        self.crash = crash
        if not self.directory.is_absolute():
            raise ValueError("Use a locally configured absolute roundup directory")

    def _read_page(self, fixture, page_id):
        return lineage.gameplay(self.career.registry, self.career.key, "narrate", fixture,
                                20, page_id=page_id)

    def _save(self, path, document):
        # Replace only our mutable private delivery journal, never accepted bytes.
        temporary = path.with_suffix(".pending")
        with temporary.open("w", encoding="utf-8") as f:
            f.write(encode(lineage.signed(document, self.career.key)))
            f.flush()
            import os
            os.fsync(f.fileno())
        temporary.replace(path)

    def run(self, request_id, checkpoint, fixtures, *, detailed=()):
        if str(UUID(request_id)) != request_id or not fixtures or len(fixtures) > 16:
            raise ValueError("Explicit bounded roundup selection required")
        if (len(set(fixtures)) != len(fixtures) or len(set(detailed)) != len(detailed)
            or set(fixtures) & set(detailed)):
            raise ValueError("Duplicate/conflicting detailed and roundup selection")
        request = {"profile": PROFILE, "id": request_id, "checkpoint": checkpoint,
                   "career": self.career.career, "test_only": self.career.test_only,
                   "fixtures": sorted(fixtures), "detailed": sorted(detailed)}
        self.directory.mkdir(parents=True, exist_ok=True)
        with process_lock(self.directory, name=".roundup.lock"):
            path = self.directory / (request_id + ".json")
            if path.exists():
                document = lineage.check_signed(json.loads(path.read_text(encoding="utf-8")), self.career.key)
                if document["request"] != request:
                    raise ValueError("Roundup UUID reused for another selection")
                if document["response"] is not None:
                    return document["response"]
            else:
                if self.career.identity()["checkpoint"] != checkpoint:
                    raise ValueError("Stale roundup checkpoint")
                group = self.career.play("next")["events"]
                keys = {f["key"] for f in group}
                if not (set(fixtures) | set(detailed)) <= keys:
                    raise ValueError("Only the earliest eligible group may be revealed")
                for event in group:
                    if event["key"] in fixtures and VASCO in (event.get("home"), event.get("away")):
                        raise ValueError("Vasco requires detailed narration; keep it held")
                document = {"request": request, "group": group, "pages": {}, "summaries": {}, "response": None}
                self._save(path, document)
            for fixture in sorted(fixtures):
                if fixture in document["summaries"]:
                    continue
                pages = document["pages"].setdefault(fixture, [])
                for index in range(len(pages), 256):
                    if self.career.identity()["checkpoint"] != checkpoint:
                        raise ValueError("Checkpoint changed during roundup; resume original journal")
                    page_id = f"{PROFILE}:{request_id}:{fixture}:{index}"
                    page = self.read_page(fixture, page_id)
                    if self.crash == "after_page_before_journal":
                        raise RuntimeError("Injected roundup crash")
                    if not page["events"] and not page["postmatch_available"]:
                        raise ValueError("Incomplete result; roundup cannot invent a final")
                    pages.append({"page_id": page_id, "page_sha256": digest(page)})
                    if page["postmatch_available"]:
                        summary = page["postmatch_summary"]
                        document["summaries"][fixture] = {"fixture": fixture, "score": summary["score"],
                                                           "resolution": summary["resolution"],
                                                           "final_page_sha256": digest(page)}
                    self._save(path, document)
                    if fixture in document["summaries"]:
                        break
                else:
                    raise ValueError("Roundup page bound reached; original cursor/journal retained")
            document["response"] = {"profile": PROFILE, "delivery_id": request_id,
                                    "checkpoint_sha256": checkpoint, "test_only": self.career.test_only,
                                    "summaries": [document["summaries"][f] for f in sorted(fixtures)],
                                    "held_for_detail": sorted(detailed),
                                    "next_events": self.career.play("next")["events"]}
            self._save(path, document)
            return document["response"]
