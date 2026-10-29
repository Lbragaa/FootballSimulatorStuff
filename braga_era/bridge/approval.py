"""Versioned remote-human consent gate. Not enabled by the v1 polling worker.

GitHub identity authenticates transport, not separate human consent. A human
confirms an exact challenge in GitHub mobile using a separately enrolled TOTP
authenticator. Neither the TOTP secret nor the authority key enters GitHub.
"""

from contextlib import contextmanager, closing
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import struct
import time
from uuid import UUID

from ..history import canonical_json as encode, digest
from ..lineage import sign
from ..world.storage import process_lock

PROFILE = "bridge-human-confirmation-1"
ACTIONS = {"authorize_batch", "execute_batch", "accept_candidate"}
DDL = """
CREATE TABLE configuration(id INTEGER PRIMARY KEY CHECK(id=1),context TEXT NOT NULL,last_counter INTEGER NOT NULL,seal TEXT NOT NULL);
CREATE TABLE challenges(id TEXT PRIMARY KEY,issue INTEGER NOT NULL,statement TEXT NOT NULL,expires INTEGER NOT NULL,state TEXT NOT NULL,proof TEXT,result TEXT);
CREATE TABLE comments(id INTEGER PRIMARY KEY,challenge TEXT UNIQUE NOT NULL);
CREATE TABLE attempts(id INTEGER PRIMARY KEY CHECK(id=1),window INTEGER NOT NULL,count INTEGER NOT NULL);
"""


def otp(secret, counter):
    """RFC 4226/6238 SHA1, six digits, 30-second steps; no secret creation."""
    if not isinstance(secret, bytes) or len(secret) < 20 or counter < 0:
        raise ValueError("Invalid locally enrolled authenticator")
    raw = hmac.digest(secret, struct.pack(">Q", counter), "sha1")
    offset = raw[-1] & 15
    return f"{(int.from_bytes(raw[offset:offset+4], 'big') & 0x7fffffff) % 1000000:06}"


class HumanGate:
    """Sealed durable challenges; consume proof before any authority mutation.

    initialize() is deliberately separate from opening an existing gate. Loss of
    this database must never silently reset replay counters or approvals.
    """

    def __init__(self, path, key, secret, context, *, clock=time.time):
        self.path, self.key, self.secret = Path(path), key, secret
        self.context, self.clock = dict(context), clock
        if (
            set(context) != {"profile", "career", "test_only", "repository_id", "human_id", "human_login"}
            or context["profile"] != PROFILE
            or type(context["test_only"]) is not bool
            or any(type(context[k]) is not int or context[k] <= 0 for k in ("repository_id", "human_id"))
            or not context["career"]
            or not context["human_login"]
            or not isinstance(secret, bytes)
            or len(secret) < 20
        ):
            raise ValueError("Explicit enrolled human/mode/transport required")
        self.context["authenticator_sha256"] = hashlib.sha256(secret).hexdigest()
        sign(key, context)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with process_lock(self.path.parent, name=".human-gate.lock"):
            if self.path.exists():
                raise ValueError("Existing human gate must not be reset")
            with closing(sqlite3.connect(self.path)) as c, c:
                c.executescript(DDL)
                c.execute("INSERT INTO configuration VALUES(1,?,-1,'')", (encode(self.context),))
                c.execute("INSERT INTO attempts VALUES(1,-1,0)")
                self._seal(c)

    def _state(self, c):
        return {
            "context": list(c.execute("SELECT context,last_counter FROM configuration").fetchone()),
            "challenges": [list(r) for r in c.execute("SELECT * FROM challenges ORDER BY id")],
            "comments": [list(r) for r in c.execute("SELECT * FROM comments ORDER BY id")],
            "attempts": list(c.execute("SELECT window,count FROM attempts").fetchone()),
        }

    def _seal(self, c):
        c.execute("UPDATE configuration SET seal=?", (sign(self.key, self._state(c)),))
        c.commit()

    @contextmanager
    def access(self):
        if not self.path.is_file():
            raise ValueError("Missing human gate; restore its private backup")
        with process_lock(self.path.parent, name=".human-gate.lock"):
            c = sqlite3.connect(self.path)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA synchronous=FULL")
            try:
                row = c.execute("SELECT * FROM configuration").fetchone()
                if row["context"] != encode(self.context) or not hmac.compare_digest(
                    row["seal"], sign(self.key, self._state(c))
                ):
                    raise ValueError("Human gate context/integrity mismatch")
                yield c
            finally:
                c.close()

    def challenge(self, request_id, issue, statement):
        if str(UUID(request_id)) != request_id or type(issue) is not int or issue <= 0:
            raise ValueError("Challenge identity")
        if (
            statement.get("action") not in ACTIONS
            or statement.get("career") != self.context["career"]
            or statement.get("test_only") is not self.context["test_only"]
            or statement.get("repository_id") != self.context["repository_id"]
            or not re.fullmatch("[0-9a-f]{64}", statement.get("target_sha256", ""))
        ):
            raise ValueError("Exact action/career/mode/target required")
        with self.access() as c:
            previous = c.execute("SELECT * FROM challenges WHERE id=?", (request_id,)).fetchone()
            if previous:
                if previous["issue"] != issue or previous["statement"] != encode(statement):
                    raise ValueError("Challenge ID reused with changed contents")
                expires = previous["expires"]
            else:
                # A TOTP is not a transaction-signing code. Allow ONE active
                # challenge so a code visible in GitHub cannot be redirected to
                # another pending action before the original comment is read.
                c.execute("UPDATE challenges SET state='expired' WHERE state='awaiting_human' AND expires<?",
                          (int(self.clock()),))
                self._seal(c)
                if c.execute("SELECT 1 FROM challenges WHERE state IN ('awaiting_human','committed')").fetchone():
                    raise ValueError("Finish/resume the single active human action first")
                expires = int(self.clock()) + 600
                c.execute("INSERT INTO challenges VALUES(?,?,?,?,'awaiting_human',NULL,NULL)",
                          (request_id, issue, encode(statement), expires))
                self._seal(c)
        binding = digest({"profile": PROFILE, "challenge": request_id, "issue": issue,
                          "statement": statement, "expires": expires})
        return {"profile": PROFILE, "challenge_id": request_id, "action": statement["action"],
                "target_sha256": statement["target_sha256"], "binding_sha256": binding,
                "expires_at_unix": expires, "state": "awaiting_human",
                "confirmation_format": f"BRAGA_CONFIRM_V1 {request_id} {binding} <authenticator-code>"}

    def confirm(self, request_id, issue, comment, perform):
        """Transport must fetch comment metadata afresh from the pinned repo.

        perform(statement, proof) must be independently idempotent against the
        existing lineage receipts. A crash after the mutation resumes that same
        operation; it must never create a fresh seed, manifest or candidate.
        """
        with self.access() as c:
            row = c.execute("SELECT * FROM challenges WHERE id=?", (request_id,)).fetchone()
            if not row or row["issue"] != issue:
                raise ValueError("Unknown exact-issue challenge")
            if row["state"] == "cancelled":
                raise ValueError("Challenge explicitly cancelled; no approval exists")
            statement = json.loads(row["statement"])
            if row["result"] is not None:
                return json.loads(row["result"])
            proof = json.loads(row["proof"]) if row["proof"] else None
            if proof is None:
                actor = comment.get("user", {})
                if (
                    actor.get("id") != self.context["human_id"]
                    or actor.get("login") != self.context["human_login"]
                    or type(comment.get("id")) is not int or comment["id"] <= 0
                    or comment.get("performed_via_github_app")
                    or not comment.get("created_at")
                    or comment.get("updated_at") != comment["created_at"]
                ):
                    raise ValueError("Unedited pinned human confirmation required")
                binding = digest({"profile": PROFILE, "challenge": request_id, "issue": issue,
                                  "statement": statement, "expires": row["expires"]})
                match = re.fullmatch(r"BRAGA_CONFIRM_V1 " + re.escape(request_id) + " " + binding + r" ([0-9]{6})",
                                     comment.get("body", ""))
                now = int(self.clock())
                if not match or now > row["expires"]:
                    raise ValueError("Incorrect/expired exact action confirmation")
                window, used = c.execute("SELECT window,count FROM attempts").fetchone()
                used = used if window == now // 600 else 0
                if used >= 10:
                    raise ValueError("Human confirmation attempt limit; wait for next window")
                c.execute("UPDATE attempts SET window=?,count=?", (now // 600, used + 1))
                self._seal(c)
                last = c.execute("SELECT last_counter FROM configuration").fetchone()[0]
                counters = [i for i in range(max(0, now // 30 - 1), now // 30 + 2)
                            if i > last and hmac.compare_digest(otp(self.secret, i), match[1])]
                if len(counters) != 1:
                    raise ValueError("Invalid or replayed authenticator code")
                if c.execute("SELECT 1 FROM comments WHERE id=?", (comment["id"],)).fetchone():
                    raise ValueError("Confirmation comment already consumed")
                proof = {"profile": PROFILE, "challenge_id": request_id, "issue": issue,
                         "binding_sha256": binding, "human_id": actor["id"],
                         "comment_id": comment["id"], "confirmed_at_unix": now,
                         "statement_sha256": digest(statement), "otp_counter": counters[0]}
                proof = {"document": proof, "signature": sign(self.key, proof)}
                c.execute("INSERT INTO comments VALUES(?,?)", (comment["id"], request_id))
                c.execute("UPDATE configuration SET last_counter=?", (counters[0],))
                c.execute("UPDATE challenges SET state='committed',proof=? WHERE id=?", (encode(proof), request_id))
                self._seal(c)
            # Durable proof is committed BEFORE the external lineage transaction.
            result = perform(statement, proof)
            c.execute("UPDATE challenges SET state='completed',result=? WHERE id=?", (encode(result), request_id))
            self._seal(c)
            return result

    def cancel_unconfirmed(self, request_id, instruction_sha256):
        """Explicit operator cancellation; retain original statement and no proof."""
        if not re.fullmatch(r"[0-9a-f]{64}", instruction_sha256):
            raise ValueError("Cancellation instruction provenance required")
        with self.access() as c:
            row = c.execute("SELECT * FROM challenges WHERE id=?", (request_id,)).fetchone()
            if not row or row["proof"] or row["state"] not in ("awaiting_human", "expired", "cancelled"):
                raise ValueError("A committed approval cannot be cancelled or rewritten")
            result = {"cancelled": True, "approval_recorded": False,
                      "superseding_instruction_sha256": instruction_sha256}
            if row["state"] == "cancelled" and json.loads(row["result"]) != result:
                raise ValueError("Cancellation provenance differs")
            c.execute("UPDATE challenges SET state='cancelled',result=? WHERE id=?", (encode(result), request_id))
            self._seal(c)
            return result

    def resume(self, request_id, perform):
        with self.access() as c:
            row = c.execute("SELECT issue,proof FROM challenges WHERE id=?", (request_id,)).fetchone()
            if not row or not row["proof"]:
                raise ValueError("No human-confirmed operation to resume")
            issue = row["issue"]
        return self.confirm(request_id, issue, {}, perform)
