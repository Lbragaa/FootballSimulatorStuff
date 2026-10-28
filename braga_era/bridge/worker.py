"""Persistent serial inbox/outbox with result-bound, replayable narration pages."""

import hmac
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from ..history import canonical_json as encode, digest
from ..lineage import sign
from ..world.storage import process_lock
from .protocol import parse, role, PROTOCOL, RESULT_KEYS

MARKER = "BRAGA_BRIDGE_RESPONSE_V1\n"
DDL = """
CREATE TABLE meta(id INTEGER PRIMARY KEY CHECK(id=1),next_sequence INTEGER NOT NULL,context TEXT NOT NULL,seal TEXT NOT NULL);
CREATE TABLE requests(id TEXT PRIMARY KEY,sha TEXT NOT NULL,body TEXT NOT NULL,sequence INTEGER UNIQUE NOT NULL,status TEXT NOT NULL,pages TEXT NOT NULL,response TEXT,manifest TEXT,source INTEGER NOT NULL);
CREATE TABLE deliveries(issue INTEGER PRIMARY KEY,request TEXT NOT NULL,sha TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0);
"""


def state(c):
    return {
        "next_sequence": c.execute("SELECT next_sequence FROM meta").fetchone()[0],
        "context": c.execute("SELECT context FROM meta").fetchone()[0],
        "requests": [list(r) for r in c.execute("SELECT * FROM requests ORDER BY id")],
        "deliveries": [
            list(r) for r in c.execute("SELECT * FROM deliveries ORDER BY issue")
        ],
    }


def seal(c, key):
    c.execute(
        "UPDATE meta SET seal=?",
        (sign(key, {"domain": "bridge-ledger-1", "state": state(c)}),),
    )


def check(c, key):
    if not hmac.compare_digest(
        c.execute("SELECT seal FROM meta").fetchone()[0],
        sign(key, {"domain": "bridge-ledger-1", "state": state(c)}),
    ):
        raise ValueError("Bridge ledger integrity")


def response_body(response):
    return MARKER + "```json\n" + encode(response) + "\n```"


def safe_output(value):
    forbidden = {
        "seed",
        "seed_commitment",
        "master_seed",
        "streams",
        "input_json",
        "result_json",
        "snapshot",
        "parent_path",
        "token",
        "key_bytes",
        "sql",
        "authorization",
        "seed_json",
        "config_json",
    }
    if isinstance(value, dict):
        if set(value) & forbidden:
            raise ValueError("Private output field")
        for item in value.values():
            safe_output(item)
    elif isinstance(value, list):
        for item in value:
            safe_output(item)


class Worker:
    def __init__(
        self,
        transport,
        career,
        database,
        requesters,
        *,
        scopes=("read", "narration", "admin"),
        crash=None,
    ):
        self.transport, self.career, self.path = transport, career, Path(database)
        self.requesters, self.scopes, self.crash = requesters, set(scopes), crash
        self.context = encode(
            {
                "protocol": PROTOCOL,
                "repository_id": transport.repository_id,
                "worker_id": transport.worker_id,
                "career": career.career,
                "test_only": career.test_only,
            }
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with sqlite3.connect(self.path) as c:
                c.executescript(DDL)
                c.execute("INSERT INTO meta VALUES(1,1,?,'')", (self.context,))
                seal(c, self.career.key)

    def fault(self, name):
        if self.crash == name:
            raise RuntimeError("Injected bridge crash: " + name)

    def envelope(self, request, source, status, result, next_sequence):
        doc = {
            "domain": "bridge-delivery-1",
            "protocol": PROTOCOL,
            "repository_id": self.transport.repository_id,
            "worker_id": self.transport.worker_id,
            "request_id": request["request_id"],
            "request_sha256": digest(request),
            "sequence": request["sequence"],
            "source_issue": source,
            "career": request["career"],
            "expected_checkpoint": request["expected_checkpoint"],
            "test_only": self.career.test_only,
            "status": status,
            "next_sequence": next_sequence,
            "result": result,
            "execution_enabled": False,
            "acceptance_enabled": False,
        }
        return {
            "response": doc,
            "authentication": {
                "algorithm": "HMAC-SHA256/local-audit",
                "signature": sign(self.career.key, doc),
            },
        }

    def verify_response(self, value):
        doc = value["response"]
        return (
            doc["domain"] == "bridge-delivery-1"
            and doc["repository_id"] == self.transport.repository_id
            and doc["worker_id"] == self.transport.worker_id
            and doc["career"] == self.career.career
            and doc["test_only"] == self.career.test_only
            and value["authentication"]["algorithm"] == "HMAC-SHA256/local-audit"
            and hmac.compare_digest(
                value["authentication"]["signature"], sign(self.career.key, doc)
            )
        )

    def save(self, c):
        seal(c, self.career.key)
        c.commit()

    def dispatch(self, c, row, request):
        name, args = request["command"], request["args"]
        if name in ("inspect_career", "inspect_accepted_checkpoint"):
            return self.career.inspect()
        if name == "next_event":
            return self.career.play("next")
        if name == "current_table":
            return self.career.play("table")
        if name == "current_finances":
            return self.career.finances()
        if name in ("prematch_preview", "available_team_news"):
            return self.career.preview(
                args["fixture"], news=name == "available_team_news"
            )
        if name == "inspect_candidate_validation":
            return self.career.candidate(args["checkpoint"])
        if name == "prepare_batch":
            manifest = self.career.prepare(args["until"], request["request_id"])
            c.execute(
                "UPDATE requests SET manifest=? WHERE id=?",
                (encode(manifest), row["id"]),
            )
            return self.career.manifest_summary(manifest)
        if name == "inspect_batch_manifest":
            m = c.execute(
                "SELECT manifest,body FROM requests WHERE id=?", (args["prepare_id"],)
            ).fetchone()
            if not m or not m[0] or json.loads(m[1])["command"] != "prepare_batch":
                raise ValueError("Unknown prepared manifest")
            return self.career.manifest_summary(json.loads(m[0]))
        if name == "repeat_previous_delivery":
            r = c.execute(
                "SELECT response FROM requests WHERE id=?", (args["delivery_id"],)
            ).fetchone()
            if not r or not r[0]:
                raise ValueError("Unknown delivery")
            previous = json.loads(r[0])
            if not self.verify_response(previous):
                raise ValueError("Delivery integrity")
            while "original_delivery" in previous["response"]["result"]:
                previous = previous["response"]["result"]["original_delivery"]
                if not self.verify_response(previous):
                    raise ValueError("Delivery integrity")
            return {"original_delivery": previous}
        if not name.startswith("narrate_"):
            raise ValueError("Disabled command")
        pages = json.loads(row["pages"])
        boundary = "HALF_TIME" if name == "narrate_until_halftime" else "FINAL_WHISTLE"
        until = name.startswith("narrate_until_")
        limit = 128 if until else args.get("count", 1)
        already = False
        if until:
            if row["manifest"] is None:
                initial = {
                    "bridge_boundary_already_seen": self.career.boundary_seen(
                        args["fixture"], boundary
                    )
                }
                c.execute(
                    "UPDATE requests SET manifest=? WHERE id=?",
                    (encode(initial), row["id"]),
                )
                self.save(c)
            else:
                initial = json.loads(row["manifest"])
            already = initial["bridge_boundary_already_seen"]
        while len(pages) < limit:
            if pages and (
                pages[-1]["postmatch_available"]
                or any(e["kind"] == boundary for e in pages[-1]["events"])
                and until
            ):
                break
            if not pages and already:
                break
            if len(encode(pages).encode()) > 28000:
                break
            if self.career.identity()["checkpoint"] != request["expected_checkpoint"]:
                raise ValueError("Checkpoint changed")
            page = self.career.play(
                "narrate",
                args["fixture"],
                page_id=f"bridge:{self.transport.repository_id}:{request['request_id']}:{len(pages)}",
            )
            self.fault("after_page_before_store")
            pages.append(page)
            c.execute(
                "UPDATE requests SET pages=? WHERE id=?", (encode(pages), row["id"])
            )
            self.save(c)
            if not page["events"]:
                break
        return {
            "fixture": args["fixture"],
            "pages": pages,
            "boundary_reached": (
                bool(
                    already
                    or pages
                    and (
                        pages[-1]["postmatch_available"]
                        or any(e["kind"] == boundary for e in pages[-1]["events"])
                    )
                )
                if until
                else False
            ),
            "delivery_id": request["request_id"],
        }

    def process(self, c, issue):
        if not issue.get("title", "").startswith("[BRAGA]"):
            return
        actor = issue.get("user", {})
        allowed = self.requesters.get(str(actor.get("id")))
        if not allowed or actor.get("login") != allowed["login"]:
            return
        # API metadata, exact body and current open state are fetched again before claim.
        issue = self.transport.issue(issue["number"])
        if (
            issue.get("pull_request")
            or issue.get("state") != "open"
            or issue.get("user", {}).get("id") != actor.get("id")
        ):
            return
        try:
            request = parse(issue["body"])
        except (ValueError, TypeError, KeyError, RecursionError):
            return
        if issue["title"] != "[BRAGA] " + request["request_id"]:
            return
        if (
            role(request["command"]) not in self.scopes
            or role(request["command"]) not in allowed["scopes"]
        ):
            return
        if request["career"] != self.career.career:
            return
        sha = digest(request)
        row = c.execute(
            "SELECT * FROM requests WHERE id=?", (request["request_id"],)
        ).fetchone()
        if not row and issue.get("bridge_last_edited_at", "unverified") is not None:
            return
        if row and row["sha"] != sha:
            return
        previous = c.execute(
            "SELECT * FROM deliveries WHERE issue=?", (issue["number"],)
        ).fetchone()
        if previous and previous["sha"] != sha:
            return
        if not row:
            seq = c.execute("SELECT next_sequence FROM meta").fetchone()[0]
            if request["sequence"] != seq:
                return
            if c.execute("SELECT 1 FROM requests WHERE sequence=?", (seq,)).fetchone():
                return
            c.execute(
                "INSERT INTO requests VALUES(?,?,?,?,'running','[]',NULL,NULL,?)",
                (
                    request["request_id"],
                    sha,
                    encode(request),
                    request["sequence"],
                    issue["number"],
                ),
            )
            self.save(c)
            row = c.execute(
                "SELECT * FROM requests WHERE id=?", (request["request_id"],)
            ).fetchone()
        c.execute(
            "INSERT OR IGNORE INTO deliveries(issue,request,sha) VALUES(?,?,?)",
            (issue["number"], row["id"], sha),
        )
        self.save(c)
        if not row["response"]:
            try:
                if (
                    self.career.identity()["checkpoint"]
                    != request["expected_checkpoint"]
                ):
                    raise ValueError("Stale checkpoint")
                result = self.dispatch(c, row, request)
                if set(result) - RESULT_KEYS:
                    raise ValueError("Unexpected public result shape")
                safe_output(result)
                status = "completed"
            except ValueError:
                retained = c.execute(
                    "SELECT pages FROM requests WHERE id=?", (row["id"],)
                ).fetchone()[0]
                if json.loads(retained):
                    raise RuntimeError(
                        "Retained partial delivery requires local review; original pages preserved"
                    ) from None
                # Do not publish exception text, paths, private diagnostics or future results.
                result = {"error": "COMMAND_REFUSED", "resume_existing_delivery": True}
                status = "refused"
            response = self.envelope(
                request, row["source"], status, result, request["sequence"] + 1
            )
            if len(response_body(response).encode()) > 60000:
                raise RuntimeError(
                    "Response bound; retained local delivery needs review"
                )
            c.execute(
                "UPDATE requests SET status=?,response=? WHERE id=?",
                (status, encode(response), row["id"]),
            )
            c.execute("UPDATE meta SET next_sequence=?", (request["sequence"] + 1,))
            self.save(c)
            self.fault("after_response_before_post")
        self.deliver(c, issue["number"])

    def deliver(self, c, number):
        delivery = c.execute(
            "SELECT * FROM deliveries WHERE issue=?", (number,)
        ).fetchone()
        row = c.execute(
            "SELECT * FROM requests WHERE id=?", (delivery["request"],)
        ).fetchone()
        if not row["response"]:
            return
        current = self.transport.issue(number)
        actor = current.get("user", {})
        allowed = self.requesters.get(str(actor.get("id")))
        if not allowed or actor.get("login") != allowed["login"]:
            return
        try:
            live = parse(current.get("body"))
        except (ValueError, TypeError, RecursionError):
            return
        if (
            digest(live) != delivery["sha"]
            or role(live["command"]) not in allowed["scopes"]
        ):
            return
        response = json.loads(row["response"])
        if not self.verify_response(response):
            raise ValueError("Response integrity")
        body = response_body(response)
        found = any(
            x.get("user", {}).get("id") == self.transport.worker_id
            and x.get("body") == body
            for x in self.transport.comments(number)
        )
        if not found:
            if delivery["done"] < 0 and time.time() + delivery["done"] < 30:
                return
            c.execute(
                "UPDATE deliveries SET done=? WHERE issue=?",
                (-int(time.time()), number),
            )
            self.save(c)
            self.fault("before_post")
            self.transport.reply(number, body)
            self.fault("after_post_before_ack")
        self.transport.close(number)
        c.execute("UPDATE deliveries SET done=1 WHERE issue=?", (number,))
        self.save(c)

    def poll(self):
        with process_lock(self.path.parent, name=".bridge-worker.lock"), closing(
            sqlite3.connect(self.path)
        ) as c:
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA synchronous=FULL")
            check(c, self.career.key)
            if c.execute("SELECT context FROM meta").fetchone()[0] != self.context:
                raise ValueError(
                    "Bridge ledger belongs to a different configured transport"
                )
            self.transport.privacy()
            for row in c.execute(
                "SELECT issue FROM deliveries WHERE done<>1 ORDER BY issue"
            ).fetchall():
                self.deliver(c, row[0])
            for issue in sorted(self.transport.issues(), key=lambda x: x["number"]):
                self.process(c, issue)
            result = {
                "next_sequence": c.execute("SELECT next_sequence FROM meta").fetchone()[
                    0
                ],
                "completed_requests": c.execute(
                    "SELECT count(*) FROM requests WHERE response IS NOT NULL"
                ).fetchone()[0],
            }
            if hasattr(self.transport, "status"):
                status = {
                    "domain": "bridge-status-1",
                    "protocol": PROTOCOL,
                    **self.career.identity(),
                    **result,
                    "worker_id": self.transport.worker_id,
                    "repository_id": self.transport.repository_id,
                    "execution_enabled": False,
                    "acceptance_enabled": False,
                    "recent_requests": [
                        {
                            "request_id": r[0],
                            "sequence": r[1],
                            "status": r[2],
                            "issue": r[3],
                        }
                        for r in c.execute(
                            "SELECT id,sequence,status,source FROM requests ORDER BY sequence DESC LIMIT 10"
                        )
                    ],
                }
                self.transport.status(
                    {"status": status, "signature": sign(self.career.key, status)}
                )
            return result
