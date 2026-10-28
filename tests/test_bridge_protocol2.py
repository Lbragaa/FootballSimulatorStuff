import copy
import json
from pathlib import Path
from uuid import uuid4
import pytest
from braga_era.bridge import protocol2
from braga_era.bridge.__main__ import config
from test_bridge import request
from test_bridge_configuration import sample


def v2(command="inspect_career", **args):
    return {**request(command, **args), "protocol": protocol2.PROTOCOL}


def test_closed_v2_and_legacy_compatibility():
    assert protocol2.parse(json.dumps(request()))["protocol"] == "braga-bridge-1"
    for command, spec in protocol2.COMMANDS.items():
        args = {k: "2027-09-30 23:59" if t == "boundary" else str(uuid4()) if t == "uuid"
                else "a" * 64 if t == "hash" else ["lib:LIB-R16-01:L1"] for k, t in spec.items()}
        if command == "roundup":
            args["detailed"] = []
        assert protocol2.parse(json.dumps(v2(command, **args)))["command"] == command
    assert len(protocol2.schema()["oneOf"]) == 22
    assert not {"execute", "accept", "provision", "confirm", "sign"} & protocol2.COMMANDS.keys()


@pytest.mark.parametrize("args", [
    {"fixtures": [], "detailed": []},
    {"fixtures": ["league:1", "league:1"], "detailed": []},
    {"fixtures": ["league:1"], "detailed": ["league:1"]},
    {"fixtures": ["../../private"], "detailed": []},
    {"fixtures": [f"league:{i}" for i in range(17)], "detailed": []},
    {"fixtures": ["league:1"], "detailed": [], "approval_code": "123456"},
])
def test_roundup_and_secret_or_code_arguments_fail_closed(args):
    with pytest.raises(ValueError):
        protocol2.parse(json.dumps(v2("roundup", **args)))


def test_v2_control_requires_exact_hashes_not_generic_chat():
    for r in [v2("request_execute_batch", preparation_id=str(uuid4()), manifest_sha256="yes"),
              v2("request_accept_candidate", preparation_id=str(uuid4()), checkpoint_sha256="../x"),
              v2("execute", approved=True), v2("inspect_career", path="C:/x")]:
        with pytest.raises(ValueError):
            protocol2.parse(json.dumps(r))
    r = v2("request_authorize_batch", preparation_id=str(uuid4()), manifest_sha256="a"*64)
    r["protocol"] = "braga-bridge-1"
    with pytest.raises(ValueError):
        protocol2.parse(json.dumps(r))


def test_v2_configuration_scope_is_separate(tmp_path):
    value = sample(tmp_path)
    value["requesters"]["78325376"]["scopes"].append("control")
    path = tmp_path / "config.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        config(path)
    value["protocol"] = protocol2.PROTOCOL
    path.write_text(json.dumps(value))
    assert config(path)["protocol"] == protocol2.PROTOCOL


def test_generated_v2_schemas_match_reference():
    assert json.loads(Path("docs/bridge_request_v2.schema.json").read_text()) == protocol2.schema()
    assert json.loads(Path("docs/bridge_response_v2.schema.json").read_text()) == protocol2.response_schema()
