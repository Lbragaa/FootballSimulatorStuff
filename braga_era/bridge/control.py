"""Opt-in bridge-control-2 operations over continuous-forward-lineage-2.

This module is deliberately not routed by the Task 04B/v1 worker. It creates no
key, registry, policy receipt, career seed or production binding. Enrollment and
mobile acceptance must precede integration into a new reviewed worker version.
"""

from contextlib import contextmanager, closing
import hmac
import json
from pathlib import Path
import sqlite3
from uuid import UUID

from .. import lineage
from ..db import file_sha256
from ..history import canonical_json as encode, digest
from ..world.storage import process_lock
from .approval import PROFILE as HUMAN_PROFILE

PROFILE = "bridge-control-2"
OPERATIONS = ["authorize_batch", "execute_batch", "accept_candidate"]


class Controls:
    def __init__(self, career, store, directory, policy_receipt, gate, *, enabled=False,
                 production_binding_approved=False):
        self.career, self.gate = career, gate
        self.store, self.directory = Path(store), Path(directory)
        self.policy_receipt = Path(policy_receipt)
        self.enabled, self.production_binding_approved = enabled, production_binding_approved
        if not all(p.is_absolute() for p in (self.store, self.directory, self.policy_receipt)):
            raise ValueError("Only locally configured absolute control paths")

    def trusted(self):
        if self.enabled is not True:
            raise ValueError("Remote controls are not locally enabled")
        who = self.career.identity()
        if not who["test_only"] and self.production_binding_approved is not True:
            raise ValueError("Production control binding is not explicitly approved")
        with lineage.access(self.career.registry, self.career.key) as (c, t):
            if (t["profile"] != lineage.PROFILE or not t["active"]
                or bool(t["test_only"]) != who["test_only"] or t["career"] != who["career"]):
                raise ValueError("Untrusted/fenced/mixed-mode authority")
            expected = {
                "profile": PROFILE, "action": "approve_remote_control_policies",
                "career": t["career"], "test_only": bool(t["test_only"]),
                "authority_key_sha256": t["key_hash"],
                "policy_sha256": digest(json.loads(t["policy_json"])),
                "repository_id": self.gate.context["repository_id"],
                "human_id": self.gate.context["human_id"],
                "human_login": self.gate.context["human_login"],
                "operations": OPERATIONS,
            }
        if (self.gate.context["career"] != who["career"]
            or self.gate.context["test_only"] is not who["test_only"]
            or self.gate.key != self.career.key):
            raise ValueError("Human gate belongs to another authority")
        receipt = json.loads(self.policy_receipt.read_text(encoding="utf-8"))
        if lineage.check_signed(receipt, self.career.key) != expected:
            raise ValueError("Missing exact signed local policy/control approval")
        return who, digest(receipt)

    def _document(self, c):
        return {"profile": PROFILE, "career": self.career.career,
                "test_only": self.career.test_only,
                "batches": [list(r) for r in c.execute("SELECT * FROM preparations ORDER BY id")]}

    def _seal(self, c):
        c.execute("UPDATE integrity SET signature=?", (lineage.sign(self.career.key, self._document(c)),))
        c.commit()

    def initialize(self):
        self.trusted()
        self.store.parent.mkdir(parents=True, exist_ok=True)
        with process_lock(self.store.parent, name=".control-store.lock"):
            if self.store.exists():
                raise ValueError("Control journal already exists; never reset it")
            with closing(sqlite3.connect(self.store)) as c, c:
                c.executescript("CREATE TABLE preparations(id TEXT PRIMARY KEY,manifest TEXT NOT NULL);"
                                "CREATE TABLE integrity(signature TEXT NOT NULL); INSERT INTO integrity VALUES('');")
                self._seal(c)

    @contextmanager
    def access(self):
        self.trusted()
        if not self.store.is_file():
            raise ValueError("Missing control journal; restore its backup")
        with process_lock(self.store.parent, name=".control-store.lock"):
            c = sqlite3.connect(self.store)
            try:
                if not hmac.compare_digest(c.execute("SELECT signature FROM integrity").fetchone()[0],
                                           lineage.sign(self.career.key, self._document(c))):
                    raise ValueError("Control preparation journal integrity")
                yield c
            finally:
                c.close()

    def prepare(self, request_id, until):
        if str(UUID(request_id)) != request_id:
            raise ValueError("Stable preparation UUID required")
        with self.access() as c:
            row = c.execute("SELECT manifest FROM preparations WHERE id=?", (request_id,)).fetchone()
            if row:
                manifest = json.loads(row[0])
                if manifest["until"] != until:
                    raise ValueError("Preparation UUID reused with changed boundary")
            else:
                manifest = self.career.prepare(until, request_id)
                c.execute("INSERT INTO preparations VALUES(?,?)", (request_id, encode(manifest)))
                self._seal(c)
        return self.summary(manifest)

    def manifest(self, preparation_id):
        with self.access() as c:
            row = c.execute("SELECT manifest FROM preparations WHERE id=?", (preparation_id,)).fetchone()
            if not row:
                raise ValueError("Unknown local preparation")
            return json.loads(row[0])

    def summary(self, manifest):
        return {**self.career.manifest_summary(manifest), "control_profile": PROFILE,
                "policy_sha256": digest(manifest["policy"]),
                "configurations_sha256": digest(manifest["configurations"]),
                "career_seed_sha256": manifest["career_seed_sha256"],
                "seed_policy": manifest["seed_policy"],
                "test_only": self.career.test_only}

    def _parent(self):
        with lineage.access(self.career.registry, self.career.key) as (c, t):
            if t["head"] == lineage.ROOT:
                parent = getattr(self.career, "root_parent", None)
                if parent is None:
                    raise ValueError("Exact locally installed root parent required")
                return Path(parent)
            return Path(c.execute("SELECT path FROM accepted WHERE checkpoint=?", (t["head"],)).fetchone()[0])

    def _batch(self, manifest):
        with lineage.access(self.career.registry, self.career.key) as (c, t):
            row = c.execute("SELECT * FROM batches WHERE id=?", (manifest["execution_id"],)).fetchone()
            if row and (json.loads(row["manifest"]) != manifest
                        or json.loads(row["decision"]) != lineage.expected_authorization(manifest, t)
                        or not hmac.compare_digest(row["signature"], lineage.sign(self.career.key, json.loads(row["decision"])))):
                raise ValueError("Existing batch differs from the exact signed authorization")
            return dict(row) if row else None

    def _destination(self, preparation_id):
        if str(UUID(preparation_id)) != preparation_id:
            raise ValueError("Preparation UUID required")
        # Remote requests choose a known UUID, never a path or directory name.
        return self.directory / preparation_id

    def statement(self, action, preparation_id):
        if action not in OPERATIONS:
            raise ValueError("Unsupported control stage")
        who, receipt_hash = self.trusted()
        manifest = self.manifest(preparation_id)
        if who["checkpoint"] != manifest["immediate_parent_sha256"]:
            raise ValueError("Stale immediate accepted parent")
        row = self._batch(manifest)
        candidate = None
        if action == "authorize_batch":
            if row is not None:
                raise ValueError("Batch already authorized; inspect its receipt")
            with lineage.access(self.career.registry, self.career.key) as (c, t):
                if c.execute("SELECT 1 FROM parent_claims WHERE parent=?", (manifest["immediate_parent_sha256"],)).fetchone():
                    raise ValueError("Immediate parent is already claimed by another batch")
        elif action == "execute_batch":
            if not row or row["state"] not in ("authorized", "executing"):
                raise ValueError("Exact batch must be independently authorized first")
        else:
            if not row or row["state"] != "candidate":
                raise ValueError("A separately validated candidate is required")
            candidate = self.verify(preparation_id)
        return {"profile": PROFILE, "action": action, "preparation_id": preparation_id,
                "career": who["career"], "test_only": who["test_only"],
                "repository_id": self.gate.context["repository_id"],
                "parent_sha256": manifest["immediate_parent_sha256"],
                "manifest_sha256": digest(manifest), "policy_receipt_sha256": receipt_hash,
                "target_sha256": candidate["checkpoint_sha256"] if candidate else digest(manifest),
                "candidate": candidate, "review": self.summary(manifest)}

    def request_confirmation(self, action, preparation_id, request_id, issue):
        statement = self.statement(action, preparation_id)
        return {"review": statement["review"], "candidate": statement["candidate"],
                "confirmation": self.gate.challenge(request_id, issue, statement)}

    def perform(self, statement, proof):
        """Called only after HumanGate durably records separate human proof."""
        document = lineage.check_signed(proof, self.career.key)
        if (document.get("profile") != HUMAN_PROFILE
            or document.get("statement_sha256") != digest(statement)
            or document.get("human_id") != self.gate.context["human_id"]):
            raise ValueError("Independent exact-action human proof required")
        return self._perform_validated(statement)

    def perform_delegated(self, statement, grant, operation):
        """Separate user-opted-in delegation; never impersonates a human OTP."""
        g = lineage.check_signed(grant, self.career.key)
        p = lineage.check_signed(operation, self.career.key)
        if (g.get("profile") != "career-automatic-gameplay-1" or not g.get("enabled")
            or g.get("career") != self.career.career or g.get("test_only") is not self.career.test_only
            or g.get("repository_id") != self.gate.context["repository_id"]
            or g.get("human_id") != self.gate.context["human_id"]
            or g.get("scope") != "next_chronological_batches"
            or p.get("profile") != "automatic-gameplay-operation-1"
            or p.get("delegation_sha256") != digest(grant)
            or p.get("statement_sha256") != digest(statement)):
            raise ValueError("Exact logged automatic-gameplay delegation required")
        return self._perform_validated(statement)

    def _perform_validated(self, statement):
        who, policy_hash = self.trusted()
        pid, action = statement["preparation_id"], statement["action"]
        manifest = self.manifest(pid)
        if (statement["profile"] != PROFILE or action not in OPERATIONS
            or statement["manifest_sha256"] != digest(manifest)
            or statement["policy_receipt_sha256"] != policy_hash
            or statement["career"] != who["career"] or statement["test_only"] is not who["test_only"]
            or statement["repository_id"] != self.gate.context["repository_id"]
            or statement["parent_sha256"] != manifest["immediate_parent_sha256"]
            or statement["review"] != self.summary(manifest)):
            raise ValueError("Changed exact action or policy")
        row = self._batch(manifest)
        if action == "accept_candidate" and row and row["state"] == "accepted":
            if who["checkpoint"] != statement["target_sha256"] or row["checkpoint"] != who["checkpoint"]:
                raise ValueError("Conflicting accepted successor")
            lineage.recover_acceptance(self.career.registry, self.career.key, self._destination(pid))
            return {"accepted": True, "checkpoint_sha256": who["checkpoint"], "test_only": who["test_only"]}
        if who["checkpoint"] != manifest["immediate_parent_sha256"]:
            raise ValueError("Stale/competing immediate accepted parent")
        if action in ("authorize_batch", "execute_batch") and statement["target_sha256"] != digest(manifest):
            raise ValueError("Wrong exact manifest")
        if action == "authorize_batch":
            if not row:
                with lineage.access(self.career.registry, self.career.key) as (c, t):
                    decision = lineage.expected_authorization(manifest, t)
                lineage.authorize(self.career.registry, self.career.key, self._parent(), manifest,
                                  decision, lineage.sign(self.career.key, decision))
            return {"execution_id": manifest["execution_id"], "manifest_sha256": digest(manifest),
                    "execution_authorized": True, "executed": False}
        if action == "execute_batch":
            if not row or row["state"] not in ("authorized", "executing", "candidate"):
                raise ValueError("Missing exact execution authorization")
            lineage.execute(self.career.registry, self.career.key, manifest["execution_id"], self._destination(pid))
            return self.verify(pid)
        if not row or row["state"] != "candidate":
            raise ValueError("Missing candidate")
        candidate = self.verify(pid)
        if statement["candidate"] != candidate or statement["target_sha256"] != candidate["checkpoint_sha256"]:
            raise ValueError("Changed candidate or validation")
        decision = lineage.acceptance_template(self.career.registry, self.career.key, self._destination(pid))
        lineage.accept(self.career.registry, self.career.key, self._destination(pid),
                       decision, lineage.sign(self.career.key, decision))
        return {"accepted": True, "checkpoint_sha256": candidate["checkpoint_sha256"], "test_only": who["test_only"]}

    def verify(self, preparation_id):
        self.trusted()
        manifest = self.manifest(preparation_id)
        row = self._batch(manifest)
        destination = self._destination(preparation_id)
        if not row or row["state"] not in ("candidate", "accepted") or Path(row["directory"]) != destination:
            raise ValueError("No locally registered exact candidate")
        with lineage.access(self.career.registry, self.career.key) as (c, t):
            verified = lineage.verify_payload(destination / "payload", t, self.career.key)
            package_hash = file_sha256(destination / "checkpoint.zip")
            if verified["checkpoint_sha256"] != row["checkpoint"] or package_hash != row["package_sha"]:
                raise ValueError("Registered candidate/package differs")
        return {"checkpoint_sha256": verified["checkpoint_sha256"], "package_sha256": package_hash,
                "independently_verified": True, "test_only": self.career.test_only,
                "acceptance_required": row["state"] != "accepted"}
