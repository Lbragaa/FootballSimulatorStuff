"""Career-scoped, explicitly enabled gameplay delegation. No new match engine."""

import json
from pathlib import Path
from .. import lineage
from ..history import digest
from ..world.storage import process_lock

PROFILE = "career-automatic-gameplay-1"


class Automatic:
    def __init__(self, controls, directory):
        self.controls, self.career = controls, controls.career
        self.directory = Path(directory)
        if not self.directory.is_absolute():
            raise ValueError("Locally configured automatic journal required")

    def _read(self, path):
        return lineage.check_signed(json.loads(path.read_text(encoding="utf-8")), self.career.key)

    def _save(self, path, value):
        from .worker2 import replace_signed
        replace_signed(path, value, self.career.key)

    def initialize(self):
        self.controls.trusted()
        self.directory.mkdir(parents=True, exist_ok=True)
        with process_lock(self.directory, name=".automatic.lock"):
            if (self.directory / "mode.json").exists():
                raise ValueError("Automatic mode already initialized; never reset")
            self._save(self.directory / "mode.json", {"profile": PROFILE, "career": self.career.career,
                "test_only": self.career.test_only, "repository_id": self.controls.gate.context["repository_id"],
                "human_id": self.controls.gate.context["human_id"], "scope": "next_chronological_batches",
                "enabled": False, "revision": 0, "source": None})

    def mode(self):
        value = self._read(self.directory / "mode.json")
        if (value["profile"] != PROFILE or value["career"] != self.career.career
            or value["test_only"] is not self.career.test_only
            or value["repository_id"] != self.controls.gate.context["repository_id"]
            or value["human_id"] != self.controls.gate.context["human_id"]):
            raise ValueError("Automatic mode belongs to a different career/authority")
        return value

    def set_mode(self, enabled, request, source):
        self.controls.trusted()
        with process_lock(self.directory, name=".automatic.lock"):
            value = self.mode()
            receipt = self.directory / ("mode-" + request["request_id"] + ".json")
            if receipt.exists():
                old = self._read(receipt)
                if old["source"]["request_sha256"] != digest(request) or old["enabled"] != enabled:
                    raise ValueError("Mode request identity collision")
                if old["revision"] > value["revision"]:
                    self._save(self.directory / "mode.json", old)
                return {"automatic_gameplay": old["enabled"], "career": self.career.career}
            if enabled:
                with self.controls.gate.access() as gc:
                    if gc.execute("SELECT 1 FROM challenges WHERE state IN ('awaiting_human','committed')").fetchone():
                        raise ValueError("Resolve the existing manual challenge before enabling automatic mode")
            value.update(enabled=enabled, revision=value["revision"] + 1,
                         source={"issue": source, "request_id": request["request_id"], "request_sha256": digest(request)})
            self._save(receipt, value)
            self._save(self.directory / "mode.json", value)
            return {"automatic_gameplay": enabled, "career": self.career.career}

    def _path(self, request):
        from .protocol import uuid
        if not uuid(request["request_id"]):
            raise ValueError("Canonical request UUID required")
        return self.directory / ("play-" + request["request_id"] + ".json")

    def focus(self, fixture):
        self._save(self.directory / "focus.json", {"career": self.career.career, "fixture": fixture})

    def choose(self, events):
        path = self.directory / "focus.json"
        focused = self._read(path)["fixture"] if path.exists() else None
        return next((e["key"] for e in events if e["key"] == focused),
                    next((e["key"] for e in events if "club:15" in (e.get("home"), e.get("away"))),
                         events[0]["key"] if events else None))

    def resumable(self, request):
        path = self._path(request)
        if not path.exists():
            return False
        op = self._read(path)
        if op["request_sha256"] != digest(request) or op["head_before"] != request["expected_checkpoint"]:
            raise ValueError("Changed automatic execution request")
        head = self.career.identity()["checkpoint"]
        if head == op["head_before"]:
            return True
        if op["kind"] != "advance":
            return False
        m = self.controls.manifest(op["preparation_id"])
        row = self.controls._batch(m)
        return bool(row and row["state"] == "accepted" and row["checkpoint"] == head
                    and m["immediate_parent_sha256"] == op["head_before"])

    def _stage(self, path, op, action):
        if action in op["results"]:
            return op["results"][action]
        if action not in op["statements"]:
            op["statements"][action] = self.controls.statement(action, op["preparation_id"])
            self._save(path, op)
        statement = op["statements"][action]
        proof = lineage.signed({"profile": "automatic-gameplay-operation-1", "request_id": op["request_id"],
            "request_sha256": op["request_sha256"], "delegation_sha256": digest(op["grant"]),
            "statement_sha256": digest(statement)}, self.career.key)
        result = self.controls.perform_delegated(statement, op["grant"], proof)
        op["results"][action] = result
        self._save(path, op)
        return result

    def play(self, request, *, prepared=None):
        self.controls.trusted()
        path = self._path(request)
        with process_lock(self.directory, name=".automatic.lock"):
            if path.exists():
                op = self._read(path)
                if op["request_sha256"] != digest(request):
                    raise ValueError("Automatic request ID reused")
                if op["response"] is not None:
                    return op["response"]
            else:
                if self.career.identity()["checkpoint"] != request["expected_checkpoint"]:
                    raise ValueError("Stale gameplay parent")
                events = self.career.play("next")["events"]
                narration = [e for e in events if e.get("kind") == "narration"]
                op = {"request_id": request["request_id"], "request_sha256": digest(request),
                      "head_before": request["expected_checkpoint"], "response": None,
                      "statements": {}, "results": {}}
                if narration:
                    if request["command"] != "continue_gameplay":
                        return {"phase": "narration_ready", "simulation_advanced": False, "next_events": events}
                    op.update(kind="narration", fixture=self.choose(narration))
                else:
                    mode = self.mode()
                    if not mode["enabled"]:
                        return {"phase": "manual_approval_required", "simulation_advanced": False, "next_events": events}
                    if prepared:
                        pid, expected = prepared
                        manifest = self.controls.manifest(pid)
                        if digest(manifest) != expected:
                            raise ValueError("Wrong prepared manifest")
                        boundary = min(e["kickoff"] for e in events)[:10] + " 23:59"
                        if manifest["until"] != boundary:
                            raise ValueError("Automatic delegation permits only the next chronological day")
                    else:
                        if not events:
                            return {"phase": "season_complete", "simulation_advanced": False, "next_events": []}
                        until = min(e["kickoff"] for e in events)[:10] + " 23:59"
                        pid = request["request_id"]
                        self.controls.prepare(pid, until)
                    op.update(kind="advance", preparation_id=pid, grant=lineage.signed(mode, self.career.key))
                self._save(path, op)  # commitment before page consumption or any draws.
            if op["kind"] == "narration":
                self.focus(op["fixture"])
                page = self.career.play("narrate", op["fixture"], page_id="automatic:" + request["request_id"])
                response = {"phase": "narration", "simulation_advanced": False, "fixture": op["fixture"], "pages": [page]}
            else:
                self._stage(path, op, "authorize_batch")
                self._stage(path, op, "execute_batch")
                accepted = self._stage(path, op, "accept_candidate")
                events = self.career.play("next")["events"]
                fixture = self.choose(events)
                response = {"phase": "pregame_ready", "simulation_advanced": True,
                            "accepted_checkpoint": accepted["checkpoint_sha256"], "next_events": events,
                            "prematch": self.career.preview(fixture) if fixture else None}
            op["response"] = response
            self._save(path, op)
            return response
