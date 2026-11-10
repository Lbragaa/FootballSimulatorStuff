"""Disposable bridge and fixture-claim proof. Never plays the pending match."""
from pathlib import Path
import json
import sys
from uuid import uuid4

from braga_era import lineage, season_lineage as seasons, season_objects
from braga_era.db import connect_read_only
from braga_era.engine.substitutions import VERSION
from braga_era.multiseason import store
from braga_era.multiseason.agenda import event_from_connection


def check(root, registry, key, successor, worker, status):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from test_bridge import Transport
    transport = Transport()
    worker.transport = transport
    request = {"protocol": "braga-bridge-2", "request_id": str(uuid4()), "sequence": 1,
               "career": status["career"], "expected_checkpoint": status["checkpoint"], "command": "fork_status",
               "args": {}}
    wrong = transport.add({**request, "career": "the-braga-era", "request_id": str(uuid4()),
                           "command": "play_next_episode"})
    issue = transport.add(request)
    transport.lost_post = True
    try:
        worker.poll()
    except RuntimeError as error:
        assert str(error) == "Network lost after successful POST"
    else:
        raise AssertionError("Mock delivery interruption did not occur")
    worker.poll()
    reply = transport.result(issue)
    assert len(transport.comments(issue)) == 1 and not transport.comments(wrong)
    assert worker.verify_response(reply) and reply["response"]["result"]["fork_status"] == status
    archive = root / "TEST-portable.zip"
    seasons.export(registry,key,successor,archive)
    restored = root / "TEST-restore"
    result = seasons.restore(registry,key,archive,restored)
    assert result["independent_restore"] and result["checkpoint"] == status["checkpoint"]
    world = restored / "world"
    def op(kind, args):
        return store.run(world,key,str(uuid4()),kind,args)
    for _ in range(64):
        with connect_read_only(world / "database.sqlite") as c:
            event = event_from_connection(c)
        if event["kind"] == "match_group":
            assert event["status"] == "scheduled"
            claimed = op("claim_group",{"kickoff":event["kickoff"]})
            break
        if event["kind"] != "competition_stage":
            raise ValueError(f"Unexpected pre-match rehearsal obligation {event['kind']}")
        op(event["action"], event["args"])
    else:
        raise ValueError("Could not reach the next chronological match group")
    with connect_read_only(world / "database.sqlite") as c:
        for fixture in claimed["committed_fixtures"]:
            row=c.execute("SELECT config_json,result_json FROM ms_executions WHERE fixture=?",(fixture,)).fetchone()
            assert json.loads(row[0])["version"]==VERSION and row[1] is None
    # Close and advance the precise qualifying dependency in a separate scratch
    # copy so unrelated chronological events stay untouched in the actual head.
    qualification=root/"TEST-qualification"
    with lineage.access(registry,key) as (c,t):
        info,_=seasons.current(c,t,key)
        seasons._clone(info,qualification)
    with connect_read_only(qualification/"database.sqlite") as c:
        edition=c.execute("SELECT state FROM ms_editions WHERE id='LIB_PRE2:2028'").fetchone()[0]
        pre3=c.execute("SELECT 1 FROM ms_editions WHERE id='LIB_PRE3:2028'").fetchone()
    if edition != "completed":
        store.run(qualification,key,str(uuid4()),"close_edition",{"edition":"LIB_PRE2:2028"})
    if not pre3:
        store.run(qualification,key,str(uuid4()),"activate_continental_edition",{"competition":"LIB_PRE3","season":2028})
    with connect_read_only(qualification/"database.sqlite") as c:
        assert c.execute("SELECT 1 FROM ms_entries WHERE edition='LIB_PRE3:2028' AND club='club:15'").fetchone()
    season_objects.remove_owned(qualification,root)
    season_objects.remove_owned(restored,root)
    print(json.dumps({"isolated_bridge_retry_verified":True,"old_request_ignored":True,"portable_restored":True,
                      "qualification":"LIB_PRE3","next_commitments":len(claimed["committed_fixtures"]),
                      "next_engine":VERSION,"matches_played":0}),flush=True)
