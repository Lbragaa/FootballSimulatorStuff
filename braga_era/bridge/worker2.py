"""Opt-in v2 worker: review issues, separate human consent, stored roundups."""

from copy import deepcopy
import json
import os
from pathlib import Path
import time

from .. import lineage
from ..history import canonical_json as encode, digest
from . import protocol2
from .roundup import Roundups, compact_events
from .worker import Worker, safe_output

CONTROL_ACTIONS = {"request_authorize_batch": "authorize_batch",
                   "request_execute_batch": "execute_batch",
                   "request_accept_candidate": "accept_candidate"}


def replace_signed(path, value, key):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".pending")
    with temporary.open("w", encoding="utf-8") as f:
        f.write(encode(lineage.signed(value, key)))
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(5):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


class Worker2(Worker):
    parse_request = staticmethod(protocol2.parse)
    command_role = staticmethod(protocol2.role)
    public_protocol = protocol2.PROTOCOL
    result_keys = protocol2.RESULT_KEYS

    def __init__(self, *args, controls=None, roundups=None, automatic=None, **kwargs):
        kwargs.setdefault("scopes", ("read", "narration", "admin", "control"))
        super().__init__(*args, **kwargs)
        self.controls = controls
        self.automatic = automatic
        from .episode import Episode
        self.episodes = Episode(automatic) if automatic else None
        self.roundups = roundups or Roundups(self.career, self.path.parent / "roundups")

    def capabilities(self):
        enabled = False
        if self.controls is not None:
            try:
                self.controls.trusted()
                human = self.requesters.get(str(self.controls.gate.context["human_id"]), {})
                enabled = (human.get("login") == self.controls.gate.context["human_login"]
                           and "control" in human.get("scopes", []) and "control" in self.scopes)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Missing control approval must not prevent ordinary reading.
        auto = False
        if enabled and self.automatic is not None:
            auto = self.automatic.mode()["enabled"]
        return {"execution_enabled": enabled, "acceptance_enabled": enabled, "automatic_gameplay": auto}

    def request_claimed(self, c, request):
        if request["command"] == "play_next_episode" and hasattr(self.transport, "status"):
            status = self.status_document(c)
            self.transport.status({"status": status, "signature": lineage.sign(self.career.key, status)})

    def deliver(self, c, number):
        started = time.perf_counter()
        before = dict(getattr(self.transport, "timings", {}))
        super().deliver(c, number)
        if before:
            row = c.execute("SELECT request,done FROM deliveries WHERE issue=?", (number,)).fetchone()
            path = self.path.parent / "performance" / (row["request"] + ".json")
            if row["done"] == 1 and not path.exists():
                replace_signed(path, {"issue": number, "request_id": row["request"],
                    "delivery_wall_seconds": round(time.perf_counter()-started, 3),
                    "github_seconds": {k: round(v-before.get(k,0),3) for k,v in self.transport.timings.items()}}, self.career.key)

    def valid_head(self, request):
        if super().valid_head(request):
            return True
        if self.episodes and request["command"] == "play_next_episode":
            return self.episodes.resumable(request)
        return bool(self.automatic and request["command"] in
                    {"continue_gameplay", "advance_next_batch", "play_prepared_batch"}
                    and self.automatic.resumable(request))

    def dispatch(self, c, row, request):
        name, args = request["command"], request["args"]
        if name == 'historical_results':
            from .historical import HistoricalResults
            return {'historical_results': HistoricalResults(self.career).query(args),
                    'accepted_checkpoint': self.career.identity()['checkpoint']}
        if name in {"enable_automatic_gameplay", "disable_automatic_gameplay", "automatic_status",
                    "continue_gameplay", "advance_next_batch", "play_prepared_batch", "play_next_episode"}:
            if self.automatic is None or not self.capabilities()["execution_enabled"]:
                raise ValueError("Automatic gameplay is not configured for this career")
            actor = self.transport.issue(row["source"])["user"]
            if actor.get("id") != self.controls.gate.context["human_id"]:
                raise ValueError("Pinned commissioner identity required")
            if name == "automatic_status":
                return {"automatic_gameplay": self.automatic.mode()["enabled"], "career": self.career.career}
            if name in {"enable_automatic_gameplay", "disable_automatic_gameplay"}:
                return self.automatic.set_mode(name == "enable_automatic_gameplay", request, row["source"])
            if name == "play_next_episode":
                try:
                    return self.episodes.run(request)
                except ValueError:
                    if self.episodes.path(request).exists():
                        raise RuntimeError("Original episode retained for recovery") from None
                    raise
            prepared = (args["preparation_id"], args["manifest_sha256"]) if name == "play_prepared_batch" else None
            try:
                return self.automatic.play(request, prepared=prepared)
            except ValueError:
                if self.automatic._path(request).exists():
                    raise RuntimeError("Original automatic gameplay commitment retained for recovery") from None
                raise
        if name == "roundup":
            try:
                result = self.roundups.run(request["request_id"], request["expected_checkpoint"],
                                          args["fixtures"], detailed=args["detailed"])
                if self.automatic and args["detailed"]:
                    self.automatic.focus(args["detailed"][0])
                return result
            except ValueError:
                path = self.roundups.directory / (request["request_id"] + ".json")
                if path.exists():
                    journal = lineage.check_signed(json.loads(path.read_text(encoding="utf-8")), self.career.key)
                    if any(journal["pages"].values()):
                        raise RuntimeError("Partial roundup retained; resume original request") from None
                raise
        if name in protocol2.COMMANDS:
            if not self.capabilities()["execution_enabled"]:
                raise ValueError("Separately approved control runtime required")
            if name in CONTROL_ACTIONS and self.automatic and self.automatic.mode()["enabled"]:
                raise ValueError("Disable automatic gameplay before starting a manual approval flow")
            controls = self.controls
            if name == "prepare_control_batch":
                return {**controls.prepare(request["request_id"], args["until"]),
                        "preparation_id": request["request_id"]}
            pid = args["preparation_id"]
            manifest = controls.manifest(pid)
            if name == "inspect_control_batch":
                batch = controls._batch(manifest)
                return {**controls.summary(manifest), "preparation_id": pid,
                        "batch_state": batch["state"] if batch else "prepared"}
            if name == "inspect_control_candidate":
                return {"candidate": controls.verify(pid)}
            action = CONTROL_ACTIONS[name]
            if action == "accept_candidate":
                if controls.verify(pid)["checkpoint_sha256"] != args["checkpoint_sha256"]:
                    raise ValueError("Wrong exact candidate hash")
            elif digest(manifest) != args["manifest_sha256"]:
                raise ValueError("Wrong exact manifest hash")
            return controls.request_confirmation(action, pid, request["request_id"], row["source"])
        result = super().dispatch(c, row, request)
        if self.automatic and name.startswith("narrate_"):
            self.automatic.focus(args["fixture"])
        if request["protocol"] == protocol2.PROTOCOL and name.startswith("narrate_"):
            pages = result["pages"]
            presentation = compact_events([e for page in pages for e in page["events"]])
            public_pages, offset = [], 0
            for page in pages:
                value = deepcopy(page)
                count = len(page["events"])
                value["events"] = presentation["events"][offset:offset+count]
                offset += count
                public_pages.append(value)
            return {**result, "pages": public_pages, "presentation": presentation["presentation"],
                    "on_field_states": presentation["on_field_states"],
                    "source_page_sha256s": [digest(p) for p in pages]}
        return result

    def _receipt(self, row):
        statement, result = json.loads(row["statement"]), json.loads(row["result"])
        doc = {"domain": "bridge-control-receipt-2", "protocol": protocol2.PROTOCOL,
               "repository_id": self.transport.repository_id, "worker_id": self.transport.worker_id,
               "career": self.career.career, "test_only": self.career.test_only,
               "challenge_id": row["id"], "source_issue": row["issue"],
               "action": statement["action"], "target_sha256": statement["target_sha256"],
               "manifest_sha256": statement["manifest_sha256"],
               "parent_sha256": statement["parent_sha256"],
               "human_proof_sha256": digest(json.loads(row["proof"])), "result": result,
               "status": "completed"}
        safe_output(doc)
        return "BRAGA_CONTROL_RECEIPT_V2\n```json\n" + encode(lineage.signed(doc, self.career.key)) + "\n```"

    def _deliver_control(self, row):
        body = self._receipt(row)
        directory = self.path.parent / "control-deliveries"
        path = directory / (row["id"] + ".json")
        marker = {"challenge": row["id"], "body_sha256": digest(body), "posted": False, "attempt": 0}
        if path.exists():
            saved = lineage.check_signed(json.loads(path.read_text(encoding="utf-8")), self.career.key)
            if saved["challenge"] != marker["challenge"] or saved["body_sha256"] != marker["body_sha256"]:
                raise ValueError("Control delivery binding changed")
            marker = saved
            if marker["posted"]:
                return
        found = any(x.get("user", {}).get("id") == self.transport.worker_id and x.get("body") == body
                    for x in self.transport.comments(row["issue"]))
        if not found:
            if marker["attempt"] and time.time() - marker["attempt"] < 30:
                return
            marker["attempt"] = int(time.time())
            replace_signed(path, marker, self.career.key)
            self.transport.reply(row["issue"], body)
            self.fault("after_control_post")
        marker["posted"] = True
        replace_signed(path, marker, self.career.key)

    def after_requests(self, c):
        if not self.capabilities()["execution_enabled"]:
            return
        gate = self.controls.gate
        with gate.access() as gc:
            rows = [dict(r) for r in gc.execute("SELECT * FROM challenges WHERE state IN ('awaiting_human','committed','completed') ORDER BY expires,id")]
        for row in rows:
            request = c.execute("SELECT body,source FROM requests WHERE id=?", (row["id"],)).fetchone()
            if not request or request["source"] != row["issue"]:
                raise ValueError("Human challenge has no authenticated issue request")
            original = json.loads(request["body"])
            statement = json.loads(row["statement"])
            if CONTROL_ACTIONS.get(original["command"]) != statement["action"]:
                raise ValueError("Human challenge/request action mismatch")
            if row["state"] == "committed":
                gate.resume(row["id"], self.controls.perform)
            elif row["state"] == "awaiting_human":
                for comment in self.transport.comments(row["issue"]):
                    actor = comment.get("user", {})
                    if (actor.get("id") != gate.context["human_id"]
                        or actor.get("login") != gate.context["human_login"]
                        or not comment.get("body", "").startswith("BRAGA_CONFIRM_V1 " + row["id"] + " ")):
                        continue
                    rejection = self.path.parent / "control-rejections" / (str(comment["id"]) + ".json")
                    if rejection.exists():
                        saved = lineage.check_signed(json.loads(rejection.read_text(encoding="utf-8")), self.career.key)
                        if saved["comment_sha256"] == digest(comment):
                            continue
                    try:
                        gate.confirm(row["id"], row["issue"], comment, self.controls.perform)
                    except ValueError:
                        with gate.access() as gc:
                            proof = gc.execute("SELECT proof FROM challenges WHERE id=?", (row["id"],)).fetchone()[0]
                        if proof:
                            raise RuntimeError("Human-approved operation retained; local validation review required") from None
                        replace_signed(rejection, {"challenge": row["id"], "comment_sha256": digest(comment)}, self.career.key)
                        self.transport.reply(row["issue"], "BRAGA_CONTROL_CONFIRMATION_REFUSED_V2 " + row["id"] +
                                             ": confirmation invalid or expired; no approval recorded. Review the exact challenge and retry with a new direct human comment.")
                        continue
                    self.fault("after_control_effect")
                    break
            with gate.access() as gc:
                current = dict(gc.execute("SELECT * FROM challenges WHERE id=?", (row["id"],)).fetchone())
            if current["state"] == "completed":
                self._deliver_control(current)
