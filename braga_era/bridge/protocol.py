"""Closed request grammar; GitHub identity comes from API metadata, never JSON."""

import json
import re
from uuid import UUID
from . import PROTOCOL

COMMANDS = {
    "inspect_career": {},
    "next_event": {},
    "current_table": {},
    "current_finances": {},
    "inspect_accepted_checkpoint": {},
    "prematch_preview": {"fixture": "fixture"},
    "available_team_news": {"fixture": "fixture"},
    "narrate_next": {"fixture": "fixture"},
    "narrate_count": {"fixture": "fixture", "count": "count"},
    "narrate_until_halftime": {"fixture": "fixture"},
    "narrate_until_final": {"fixture": "fixture"},
    "repeat_previous_delivery": {"delivery_id": "uuid"},
    "prepare_batch": {"until": "boundary"},
    "inspect_batch_manifest": {"prepare_id": "uuid"},
    "inspect_candidate_validation": {"checkpoint": "hash"},
}
ADMIN = {"prepare_batch", "inspect_batch_manifest", "inspect_candidate_validation"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
FIXTURE = re.compile(r"(?:league:[0-9]{1,6}|(?:lib|sula|cdb):[A-Za-z0-9:_-]{1,64})\Z")


RESULT_KEYS = set(
    "accepted accepted_checkpoint career events official_execution_authorized profile scope test_only generation accepted_clock authority_active basis standings accepted_cash_cents revealed_cash_cents revealed_paid_periods budgets restricted_cash_cents accrued_unpaid_cents annual_incremental_commitments_cents fixture_key home away kickoff as_of eligibility_exclusions lineups postmatch_available prematch lineups_available unknown_team_news reason key kind manifest_sha256 execution_id immediate_parent_sha256 until fixtures obligations world_policy engine execution_authorized acceptance_authorized checkpoint_sha256 ok validation_only fixture pages boundary_reached delivery_id original_delivery error resume_existing_delivery".split()
)


def response_schema():
    properties = {
        k: {"type": "string"}
        for k in (
            "domain",
            "protocol",
            "request_id",
            "request_sha256",
            "career",
            "expected_checkpoint",
        )
    }
    properties.update(
        {
            k: {"type": "integer", "minimum": 1}
            for k in (
                "repository_id",
                "worker_id",
                "sequence",
                "source_issue",
                "next_sequence",
            )
        }
    )
    properties.update(
        {
            "domain": {"const": "bridge-delivery-1"},
            "protocol": {"const": PROTOCOL},
            "test_only": {"type": "boolean"},
            "execution_enabled": {"const": False},
            "acceptance_enabled": {"const": False},
            "status": {"enum": ["completed", "refused"]},
            "result": {
                "type": "object",
                "additionalProperties": False,
                "properties": {k: {} for k in sorted(RESULT_KEYS)},
            },
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["response", "authentication"],
        "properties": {
            "response": {
                "type": "object",
                "additionalProperties": False,
                "required": list(properties),
                "properties": properties,
            },
            "authentication": {
                "type": "object",
                "additionalProperties": False,
                "required": ["algorithm", "signature"],
                "properties": {
                    "algorithm": {"const": "HMAC-SHA256/local-audit"},
                    "signature": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            },
        },
    }


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("Duplicate JSON key")
        result[k] = v
    return result


def uuid(value):
    return isinstance(value, str) and str(UUID(value)) == value


def parse(body):
    if not isinstance(body, str) or len(body.encode("utf-8")) > 8192:
        raise ValueError("Request size")
    value = json.loads(
        body,
        object_pairs_hook=unique_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
    )
    if not isinstance(value, dict) or set(value) != {
        "protocol",
        "request_id",
        "sequence",
        "career",
        "expected_checkpoint",
        "command",
        "args",
    }:
        raise ValueError("Request fields")
    if value["protocol"] != PROTOCOL or not uuid(value["request_id"]):
        raise ValueError("Protocol or request ID")
    if type(value["sequence"]) is not int or not 1 <= value["sequence"] <= 2**31 - 1:
        raise ValueError("Sequence")
    if not isinstance(value["career"], str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,80}", value["career"]
    ):
        raise ValueError("Career")
    if not isinstance(value["expected_checkpoint"], str) or not HASH.fullmatch(
        value["expected_checkpoint"]
    ):
        raise ValueError("Checkpoint")
    spec = COMMANDS.get(value["command"]) if isinstance(value["command"], str) else None
    if (
        spec is None
        or not isinstance(value["args"], dict)
        or set(value["args"]) != set(spec)
    ):
        raise ValueError("Unsupported command/arguments")
    for k, kind in spec.items():
        x = value["args"][k]
        good = False
        if kind == "count":
            good = type(x) is int and 1 <= x <= 20
        elif isinstance(x, str):
            if kind == "uuid":
                good = uuid(x)
            elif kind == "fixture":
                good = bool(FIXTURE.fullmatch(x))
            elif kind == "hash":
                good = bool(HASH.fullmatch(x))
            elif kind == "boundary":
                good = bool(re.fullmatch(r"2027-\d{2}-\d{2} 23:59", x))
        if not good:
            raise ValueError("Invalid argument")
    return value


def role(command):
    return (
        "admin"
        if command in ADMIN
        else (
            "narration"
            if command.startswith("narrate_") or command == "repeat_previous_delivery"
            else "read"
        )
    )


def schema():
    types = {
        "fixture": {
            "type": "string",
            "pattern": "^" + FIXTURE.pattern.replace("\\Z", "$"),
        },
        "hash": {"type": "string", "pattern": "^" + HASH.pattern.replace("\\Z", "$")},
        "count": {"type": "integer", "minimum": 1, "maximum": 20},
        "boundary": {"type": "string", "pattern": r"^2027-\d{2}-\d{2} 23:59$"},
        "uuid": {"type": "string", "format": "uuid"},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "protocol",
                    "request_id",
                    "sequence",
                    "career",
                    "expected_checkpoint",
                    "command",
                    "args",
                ],
                "properties": {
                    "protocol": {"const": PROTOCOL},
                    "command": {"const": name},
                    "request_id": types["uuid"],
                    "sequence": {"type": "integer", "minimum": 1, "maximum": 2**31 - 1},
                    "career": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"},
                    "expected_checkpoint": types["hash"],
                    "args": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": list(spec),
                        "properties": {k: types[v] for k, v in spec.items()},
                    },
                },
            }
            for name, spec in COMMANDS.items()
        ],
    }
