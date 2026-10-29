"""Closed, opt-in v2 requests. Issues request review; human comments approve."""

from copy import deepcopy
import json
from . import protocol as v1

PROTOCOL = "braga-bridge-2"
COMMANDS = {
    "enable_automatic_gameplay": {"confirmation": "auto_consent"},
    "disable_automatic_gameplay": {},
    "automatic_status": {},
    "continue_gameplay": {},
    "play_next_episode": {},
    "historical_results": {},
    "advance_next_batch": {},
    "play_prepared_batch": {"preparation_id": "uuid", "manifest_sha256": "hash"},
    "prepare_control_batch": {"until": "boundary"},
    "inspect_control_batch": {"preparation_id": "uuid"},
    "request_authorize_batch": {"preparation_id": "uuid", "manifest_sha256": "hash"},
    "request_execute_batch": {"preparation_id": "uuid", "manifest_sha256": "hash"},
    "inspect_control_candidate": {"preparation_id": "uuid"},
    "request_accept_candidate": {"preparation_id": "uuid", "checkpoint_sha256": "hash"},
    "roundup": {"fixtures": "fixtures", "detailed": "fixtures"},
}
RESULT_KEYS = v1.RESULT_KEYS | set(
    "control_profile policy_sha256 configurations_sha256 career_seed_sha256 seed_policy preparation_id batch_state review candidate confirmation summaries held_for_detail next_events on_field_states presentation source_page_sha256s automatic_gameplay phase simulation_advanced episode_type presentation_rule world_progress recovery timings_seconds historical_results".split()
)


def parse(body):
    if not isinstance(body, str) or len(body.encode("utf-8")) > 8192:
        raise ValueError("Request size")
    request = json.loads(body, object_pairs_hook=v1.unique_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if not isinstance(request, dict):
        raise ValueError("Request object required")
    if request.get("protocol") == v1.PROTOCOL:
        return v1.parse(body)  # old deliveries retain their exact grammar/bytes.
    if request.get("protocol") != PROTOCOL:
        raise ValueError("Unsupported protocol")
    name = request.get("command")
    if name == 'historical_results':
        from ..results import validate_filters
        v1.parse(json.dumps({**request, "protocol": v1.PROTOCOL, "command": "inspect_career", "args": {}}))
        validate_filters(request['args'])
        return request
    if isinstance(name, str) and name in v1.COMMANDS:
        v1.parse(json.dumps({**request, "protocol": v1.PROTOCOL}))
        return request
    spec = COMMANDS.get(name) if isinstance(name, str) else None
    if spec is None or not isinstance(request.get("args"), dict) or set(request["args"]) != set(spec):
        raise ValueError("Unsupported control command/arguments")
    # Reuse the strict v1 header validator, including rejecting extra fields.
    v1.parse(json.dumps({**request, "protocol": v1.PROTOCOL, "command": "inspect_career", "args": {}}))
    for key, kind in spec.items():
        value = request["args"][key]
        if kind == "fixtures":
            if (not isinstance(value, list) or len(value) > 16
                or any(not isinstance(x, str) or not v1.FIXTURE.fullmatch(x) for x in value)
                or len(set(value)) != len(value)):
                raise ValueError("Bounded unique fixture selection required")
        elif kind == "uuid":
            if not v1.uuid(value):
                raise ValueError("Preparation UUID")
        elif kind == "hash":
            if not isinstance(value, str) or not v1.HASH.fullmatch(value):
                raise ValueError("Exact hash required")
        elif kind == "boundary":
            v1.parse(json.dumps({**request, "protocol": v1.PROTOCOL,
                                 "command": "prepare_batch", "args": {"until": value}}))
        elif kind == "auto_consent" and value != "ENABLE_AUTOMATIC_GAMEPLAY":
            raise ValueError("Explicit career-specific automatic mode opt-in required")
    if name == "roundup" and (not request["args"]["fixtures"]
                             or set(request["args"]["fixtures"]) & set(request["args"]["detailed"])):
        raise ValueError("Explicit non-overlapping summary/detail selection required")
    return request


def role(command):
    if command in {"automatic_status", "historical_results"}:
        return "read"
    return "narration" if command == "roundup" else "control" if command in COMMANDS else v1.role(command)


def schema():
    base = deepcopy(v1.schema())
    for branch in base["oneOf"]:
        branch["properties"]["protocol"] = {"const": PROTOCOL}
    example = deepcopy(base["oneOf"][0])
    types = {
        "auto_consent": {"const": "ENABLE_AUTOMATIC_GAMEPLAY"},
        "boundary": {"type": "string", "pattern": r"^2027-\d{2}-\d{2} 23:59$"},
        "uuid": {"type": "string", "format": "uuid"},
        "hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "fixtures": {"type": "array", "maxItems": 16, "uniqueItems": True,
                     "items": {"type": "string", "pattern": "^" + v1.FIXTURE.pattern.replace("\\Z", "$")}},
    }
    for name, spec in COMMANDS.items():
        branch = deepcopy(example)
        branch["properties"]["command"] = {"const": name}
        branch["properties"]["args"] = {"type": "object", "additionalProperties": False,
                                         "required": list(spec), "properties": {k: deepcopy(types[v]) for k, v in spec.items()}}
        if name == "roundup":
            branch["properties"]["args"]["properties"]["fixtures"]["minItems"] = 1
        if name == 'historical_results':
            branch['properties']['args'] = historical_schema()
        base["oneOf"].append(branch)
    return base


def historical_schema():
    properties = {k: {'type': 'string', 'minLength': 1, 'maxLength': 100} for k in ('competition', 'stage', 'club')}
    for name, (low, high) in {'season': (1900, 2200), 'round': (1, 99), 'leg': (1, 2), 'recent': (1, 500), 'limit': (1, 50)}.items():
        properties[name] = {'type': 'integer', 'minimum': low, 'maximum': high}
    for name in ('date', 'date_from', 'date_to'):
        properties[name] = {'type': 'string', 'format': 'date', 'pattern': '^\\d{4}-\\d{2}-\\d{2}$'}
    properties['include_pending'] = {'type': 'boolean'}
    properties['cursor'] = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
    return {'type': 'object', 'additionalProperties': False, 'properties': properties}


def response_schema():
    value = deepcopy(v1.response_schema())
    properties = value["properties"]["response"]["properties"]
    properties["protocol"] = {"const": PROTOCOL}
    properties["execution_enabled"] = {"type": "boolean"}
    properties["acceptance_enabled"] = {"type": "boolean"}
    properties["automatic_gameplay"] = {"type": "boolean"}
    properties["result"]["properties"] = {k: {} for k in sorted(RESULT_KEYS)}
    return value
