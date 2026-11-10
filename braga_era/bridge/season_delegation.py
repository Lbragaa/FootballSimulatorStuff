"""Explicit standing authority for one closed-season transition at a time."""

import json
from uuid import UUID

from .. import lineage, season_lineage
from ..history import digest
from ..multiseason.lifecycle import RELEASE_PROPOSAL, SEASON_POLICIES
from ..world.storage import process_lock
from .protocol2 import SEASON_CONFIRMATIONS
from .season_control import SeasonControls

PROFILE = "standing-season-transition-1"
OPERATION = "standing-season-transition-operation-1"


class SeasonDelegation:
    def __init__(self, automatic):
        self.auto = automatic
        self.controls, self.career = automatic.controls, automatic.career
        self.seasons = SeasonControls(self.controls)
        self.mode_path = automatic.directory / "season-mode.json"

    def _path(self, request, prefix):
        request_id = request["request_id"]
        if str(UUID(request_id)) != request_id:
            raise ValueError("Canonical season request UUID required")
        return self.auto.directory / f"{prefix}-{request_id}.json"

    def _scope(self):
        who, receipt = self.controls.trusted()
        context = self.controls.gate.context
        with lineage.access(self.career.registry, self.career.key) as (_, trusted):
            epoch = trusted["lease_epoch"]
        return {
            "profile": PROFILE, "career": who["career"], "test_only": who["test_only"],
            "repository_id": context["repository_id"], "human_id": context["human_id"],
            "human_login": context["human_login"], "lease_epoch": epoch,
            "control_receipt_sha256": receipt, "policy": RELEASE_PROPOSAL,
            "policy_sha256": digest(season_lineage.policy(who["test_only"])),
            "scenarios": list(SEASON_POLICIES[RELEASE_PROPOSAL]),
        }

    def _mode(self):
        if self.mode_path.exists():
            return self.auto._read(self.mode_path)
        return {"enabled": False, "revision": 0, "scope": None}

    def status(self):
        mode = self._mode()
        enabled = mode["enabled"] and mode["scope"] == self._scope()
        return {"automatic_seasons": enabled, "season_policy": RELEASE_PROPOSAL}

    def _require_idle_gate(self, connection):
        self.controls.gate.expire_unconfirmed(connection)
        if connection.execute(
            "SELECT 1 FROM challenges WHERE state IN ('awaiting_human','committed')"
        ).fetchone():
            raise ValueError("Resolve the existing human challenge before using standing season authority")

    def set_mode(self, enabled, request, source):
        scope = self._scope()
        args = request["args"]
        if enabled and (set(args) != {"policy", "confirmation"} or args["policy"] != scope["policy"]
                        or args["confirmation"] not in SEASON_CONFIRMATIONS):
            raise ValueError("Explicit standing consent for the reviewed season policy required")
        with process_lock(self.auto.directory, name=".automatic.lock"):
            mode = self._mode()
            path = self._path(request, "season-grant")
            origin = {"issue": source, "request_id": request["request_id"], "request_sha256": digest(request)}
            if path.exists():
                grant = self.auto._read(path)
                if grant["source"] != origin or grant["enabled"] is not enabled:
                    raise ValueError("Standing season grant request reused")
            else:
                if enabled:
                    with self.controls.gate.access() as gate:
                        self._require_idle_gate(gate)
                grant = {"enabled": enabled, "revision": mode["revision"] + 1,
                         "scope": scope, "source": origin}
                self.auto._save(path, grant)
            if grant["revision"] > mode["revision"] and grant["scope"] == scope:
                self.auto._save(self.mode_path, grant)
            return self.status()

    def _operation(self, path, request):
        op = self.auto._read(path)
        if op["request_sha256"] != digest(request):
            raise ValueError("Standing season operation request reused")
        return op

    def resumable(self, request):
        path = self._path(request, "season-transition")
        if not path.exists():
            return False
        op = self._operation(path, request)
        manifest = op["manifest"]
        with lineage.access(self.career.registry, self.career.key) as (db, trusted):
            row = db.execute("SELECT state,checkpoint,manifest FROM batches WHERE id=?",
                             ("season3:" + manifest["request_id"],)).fetchone()
            return bool(row and row["state"] == "accepted" and row["checkpoint"] == trusted["head"]
                        and json.loads(row["manifest"]) == manifest)

    def _manifest(self, request, scope):
        args = request["args"]
        if request["command"] == "advance_prepared_season":
            manifest = self.seasons.manifest(args["preparation_id"])
            if digest(manifest) != args["manifest_sha256"]:
                raise ValueError("Wrong exact prepared season manifest")
        else:
            # Reuse a single compatible review of this head. Ambiguous reviews
            # require the caller to identify the intended preparation by hash.
            with self.controls.access() as db:
                prepared = [json.loads(row[0]) for row in db.execute("SELECT manifest FROM preparations")]
            reviews = [m for m in prepared if m.get("kind") == "transition"
                       and m.get("immediate_parent_sha256") == request["expected_checkpoint"]
                       and m.get("operations", [{}])[-1].get("args", {}).get("scenario") in scope["scenarios"]]
            if len(reviews) > 1:
                raise ValueError("Multiple reviewed preparations; specify the exact manifest")
            if reviews:
                manifest = reviews[0]
            else:
                self.seasons.prepare(request["request_id"], scope["policy"])
                manifest = self.seasons.manifest(request["request_id"])
        if (manifest["kind"] != "transition" or manifest["immediate_parent_sha256"] != request["expected_checkpoint"]
                or manifest["career"] != scope["career"] or manifest["test_only"] is not scope["test_only"]
                or manifest["lease_epoch"] != scope["lease_epoch"] or manifest["prior_review"]
                or digest(manifest["policy"]) != scope["policy_sha256"]
                or manifest["operations"][-1]["args"].get("scenario") not in scope["scenarios"]
                or not manifest["automatic_gameplay"] or manifest["delegated"]):
            raise ValueError("Preparation falls outside standing season authority")
        return manifest

    def _audit(self, op, phase, target):
        return lineage.signed({
            "profile": OPERATION, "phase": phase, "preparation_id": op["manifest"]["request_id"],
            "manifest_sha256": digest(op["manifest"]), "target_sha256": target,
            "request_id": op["request_id"], "request_sha256": op["request_sha256"],
            "source_issue": op["source_issue"], "grant": op["grant"],
        }, self.career.key)

    def advance(self, request, source, fault):
        scope = self._scope()
        path = self._path(request, "season-transition")
        registry, key = self.career.registry, self.career.key
        with process_lock(self.auto.directory, name=".automatic.lock"):
            if path.exists():
                op = self._operation(path, request)
                if op["source_issue"] != source or op["grant"]["scope"] != scope:
                    raise ValueError("Standing season operation belongs to a different issue or authority epoch")
                if op["response"] is not None:
                    return op["response"]
            else:
                grant = self._mode()
                if not grant["enabled"] or grant["scope"] != scope or not self.auto.mode()["enabled"]:
                    raise ValueError("Enable exact standing season authority and ordinary automatic gameplay first")
                with self.controls.gate.access() as gate:
                    self._require_idle_gate(gate)
                manifest = self._manifest(request, scope)
                op = {"request_id": request["request_id"], "request_sha256": digest(request), "source_issue": source,
                      "grant": grant, "manifest": manifest, "candidate": None, "response": None}
                self.auto._save(path, op)
            manifest = op["manifest"]
            pid, manifest_hash = manifest["request_id"], digest(manifest)
            approval = lineage.signed(season_lineage.authorization(manifest), key)
            try:
                with self.controls.gate.access() as gate:
                    self._require_idle_gate(gate)
                    if self._mode() != op["grant"] or not self.auto.mode()["enabled"]:
                        with lineage.access(registry, key) as (db, _):
                            started = db.execute(
                                "SELECT 1 FROM decisions WHERE batch=? AND kind='standing_season_execution'",
                                ("season3:" + pid,),
                            ).fetchone()
                        if not started:
                            raise ValueError("Standing grant revoked before execution was committed")
                    season_lineage.authorize(registry, key, manifest, approval,
                                             transition_audit=self._audit(op, "execution", manifest_hash))
                fault("after_standing_season_authorize")
                destination = self.controls._destination(pid)
                if op["candidate"] is None:
                    op["candidate"] = season_lineage.execute(registry, key, pid, destination)
                    self.auto._save(path, op)
                fault("after_standing_season_candidate")
                candidate = op["candidate"]
                decision = season_lineage.acceptance_template(registry, key, destination)
                if (decision["checkpoint_sha256"] != candidate["checkpoint_sha256"]
                        or decision["package_sha256"] != candidate["package_sha256"]):
                    raise ValueError("Standing acceptance differs from the verified candidate")
                accepted = season_lineage.accept(
                    registry, key, destination, decision, lineage.sign(key, decision),
                    transition_audit=self._audit(op, "acceptance", decision["checkpoint_sha256"]),
                )
                fault("after_standing_season_accept")
            except (OSError, ValueError) as error:
                with lineage.access(registry, key) as (db, _):
                    claimed = db.execute("SELECT 1 FROM decisions WHERE batch=? AND kind='standing_season_execution'",
                                         ("season3:" + pid,)).fetchone()
                if claimed or isinstance(error, OSError):
                    raise RuntimeError("Original standing season transition retained for recovery") from None
                raise
            accepted_candidate = {k: candidate[k] for k in
                                  ("checkpoint_sha256", "package_sha256", "independent_delta_replay")}
            op["response"] = {"automatic_seasons": True, "season_policy": scope["policy"],
                              "season": manifest["season"], "preparation_id": pid, "manifest_sha256": manifest_hash,
                              "accepted_checkpoint": accepted["checkpoint_sha256"], "candidate": accepted_candidate,
                              "phase": "season_transition_accepted"}
            self.auto._save(path, op)
            return op["response"]
