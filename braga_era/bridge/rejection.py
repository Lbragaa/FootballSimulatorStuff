"""Visible transport rejections for issues that never became requests."""

import json
from hashlib import sha256

from ..history import canonical_json
from ..lineage import signed
from . import protocol, protocol2

MARKER = "BRAGA_BRIDGE_REJECTION_V1\n"


def message(body):
    if isinstance(body, str) and len(body) <= 8192:
        try:
            if len(body.encode("utf-8")) > 8192:
                raise ValueError("Request size")
            raw = json.loads(body, object_pairs_hook=protocol.unique_pairs)
            if isinstance(raw, dict):
                try:
                    valid = protocol.uuid(raw.get("request_id"))
                except ValueError:
                    valid = False
                if not valid:
                    return ("INVALID_REQUEST_ID",
                            "Use a complete lowercase UUID in request_id and the issue title.")
        except (ValueError, RecursionError):
            pass
    return ("INVALID_REQUEST",
            "Use the braga-bridge-2 request schema and an unedited issue. Recheck required fields and argument types.")


def reject(transport, career, issue, requesters):
    """Post one signed, issue-bound diagnostic and close the unclaimable issue."""
    actor = issue.get("user", {})
    allowed = requesters.get(str(actor.get("id")))
    if (not allowed or actor.get("login") != allowed["login"]
            or not issue.get("title", "").startswith("[BRAGA] ")
            or issue.get("pull_request") or issue.get("state") != "open"
            or issue.get("bridge_last_edited_at", "unverified") is not None):
        return
    try:
        protocol2.parse(issue.get("body"))
    except (ValueError, TypeError, KeyError, RecursionError):
        pass
    else:
        return
    code, detail = message(issue.get("body"))
    number = issue["number"]
    doc = {
        "domain": "bridge-rejection-1",
        "protocol": protocol2.PROTOCOL,
        "repository_id": transport.repository_id,
        "worker_id": transport.worker_id,
        "source_issue": number,
        "issue_sha256": sha256(canonical_json({k: issue.get(k) for k in ("title", "body")})
                               .encode("utf-8", errors="surrogatepass")).hexdigest(),
        "career": career.career,
        "test_only": career.test_only,
        "sequence_consumed": False,
        "error": {"code": code, "message": detail},
        "retry": "Read status issue #1 and create a new unedited issue with a fresh UUID and the advertised sequence.",
    }
    reply = MARKER + "```json\n" + canonical_json(signed(doc, career.key)) + "\n```"
    found = any(note.get("user", {}).get("id") == transport.worker_id and note.get("body") == reply
                for note in transport.comments(number))
    binding = ("title", "body", "user", "state", "bridge_last_edited_at")
    current = transport.issue(number)
    if any(current.get(k) != issue.get(k) for k in binding):
        return
    if not found:
        transport.reply(number, reply)
    current = transport.issue(number)
    if all(current.get(k) == issue.get(k) for k in binding):
        transport.close(number)
