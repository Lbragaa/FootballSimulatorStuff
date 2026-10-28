from copy import deepcopy
from uuid import uuid4
import pytest
from braga_era.bridge.automatic import Automatic
from braga_era.bridge import protocol2
from braga_era import lineage
from test_bridge_control import controls
from test_bridge_worker2 import req


@pytest.fixture
def auto(controls, tmp_path):
    a = Automatic(controls, tmp_path / "automatic")
    a.initialize()
    return a


def test_opt_in_is_explicit_scoped_and_revocable(auto):
    c = auto.career
    assert not auto.mode()["enabled"]
    r = req(c, "enable_automatic_gameplay", 1, confirmation="ENABLE_AUTOMATIC_GAMEPLAY")
    assert auto.set_mode(True, r, 1)["automatic_gameplay"]
    assert auto.set_mode(True, r, 1)["automatic_gameplay"]
    assert auto.mode()["revision"] == 1
    auto.set_mode(False, req(c,"disable_automatic_gameplay",2), 2)
    assert not auto.mode()["enabled"]
    # An old enable retry must not undo a later explicit stop.
    auto.set_mode(True, r, 1)
    assert not auto.mode()["enabled"]
    wrong = deepcopy(r); wrong["args"]["confirmation"] = "yes"
    with pytest.raises(ValueError):
        protocol2.parse(__import__('json').dumps(wrong))


def test_continue_consumes_stored_page_without_simulating(auto, monkeypatch):
    c = auto.career
    count = []
    def play(view, fixture=None, page_id=None):
        if view == "next": return {"events":[{"key":"league:332","kind":"narration","home":"club:1","away":"club:15"}]}
        count.append(page_id)
        return {"events":[{"kind":"KICK_OFF","sequence":1}],"postmatch_available":False}
    monkeypatch.setattr(c, "play", play)
    monkeypatch.setattr(auto.controls,"perform_delegated",lambda *_: pytest.fail("must never simulate while narration waits"))
    r=req(c,"continue_gameplay",1)
    a=auto.play(r)
    assert a["phase"]=="narration" and not a["simulation_advanced"]
    assert auto.play(r)==a and len(count)==1
    assert auto.play(req(c,"advance_next_batch",2))["phase"]=="narration_ready"


def test_disabled_mode_cannot_advance(auto):
    r=req(auto.career,"continue_gameplay",1)
    assert auto.play(r)["phase"]=="manual_approval_required"
    with lineage.access(auto.career.registry,auto.career.key) as (c,t):
        assert c.execute('SELECT count(*) FROM batches').fetchone()[0]==0


def test_pending_manual_challenge_is_cancelled_not_forged(auto):
    c=auto.controls
    pid=str(uuid4()); c.prepare(pid,"2027-09-30 23:59")
    challenge=c.request_confirmation("authorize_batch",pid,str(uuid4()),9)["confirmation"]
    r=req(auto.career,"enable_automatic_gameplay",1,confirmation="ENABLE_AUTOMATIC_GAMEPLAY")
    with pytest.raises(ValueError,match="manual challenge"):
        auto.set_mode(True,r,10)
    result=c.gate.cancel_unconfirmed(challenge['challenge_id'],'a'*64)
    assert result['cancelled'] and not result['approval_recorded']
    with c.gate.access() as db:
        row=db.execute('SELECT state,proof,statement FROM challenges').fetchone()
        assert row['state']=='cancelled' and row['proof'] is None
        assert row['statement']
    with pytest.raises(ValueError,match='cancelled'):
        c.gate.confirm(challenge['challenge_id'],9,{},lambda *_:pytest.fail())
    auto.set_mode(True,r,10)
    assert auto.mode()['enabled']


def test_delegated_proof_cannot_cross_career_or_mode(auto):
    c=auto.controls
    pid=str(uuid4()); c.prepare(pid,"2027-09-30 23:59")
    statement=c.statement('authorize_batch',pid)
    for invalid in [{"profile":"career-automatic-gameplay-1","enabled":True,"career":"different"},
                    {"profile":"bridge-human-confirmation-1","enabled":True}]:
        with pytest.raises(ValueError):
            c.perform_delegated(statement,lineage.signed(invalid,c.career.key),lineage.signed({},c.career.key))


def test_lost_automatic_mode_is_not_recreated(auto):
    (auto.directory/'mode.json').unlink()
    with pytest.raises(OSError): auto.mode()


def test_detailed_coverage_selection_persists(auto):
    events=[{'key':'lib:first'},{'key':'lib:chosen'},{'key':'league:332','away':'club:15'}]
    assert auto.choose(events)=='league:332'
    auto.focus('lib:chosen')
    assert auto.choose(events)=='lib:chosen'
    assert auto.choose([events[0]])=='lib:first'


def test_real_lineage_authorization_uses_delegation_not_fake_otp(auto):
    c=auto.controls
    auto.set_mode(True,req(auto.career,'enable_automatic_gameplay',1,confirmation='ENABLE_AUTOMATIC_GAMEPLAY'),10)
    pid=str(uuid4()); c.prepare(pid,'2027-09-30 23:59')
    statement=c.statement('authorize_batch',pid)
    grant=lineage.signed(auto.mode(),auto.career.key)
    from braga_era.history import digest
    proof=lineage.signed({'profile':'automatic-gameplay-operation-1','delegation_sha256':digest(grant),
                          'statement_sha256':digest(statement)},auto.career.key)
    assert c.perform_delegated(statement,grant,proof)['execution_authorized']
    with c.gate.access() as db:
        assert db.execute('SELECT count(*) FROM comments').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM challenges').fetchone()[0]==0


def test_accept_commit_crash_resumes_same_batch_and_head(auto,monkeypatch):
    c=auto.career; controls=auto.controls
    head=[lineage.ROOT]; calls=[]
    identity=c.identity
    monkeypatch.setattr(c,'identity',lambda:{**identity(),'checkpoint':head[0]})
    auto.set_mode(True,req(c,'enable_automatic_gameplay',1,confirmation='ENABLE_AUTOMATIC_GAMEPLAY'),10)
    monkeypatch.setattr(c,'play',lambda *_args,**_kw:{'events':[{'key':'lib:LIB-R16-01:L1','kickoff':'2027-09-30 16:00',
        'kind':'fixture' if head[0]==lineage.ROOT else 'narration'}]})
    monkeypatch.setattr(c,'preview',lambda f:{'fixture_key':f,'postmatch_available':False})
    monkeypatch.setattr(controls,'statement',lambda action,pid:{'action':action,'preparation_id':pid})
    monkeypatch.setattr(controls,'_batch',lambda m:{'state':'accepted','checkpoint':head[0]} if head[0]!=lineage.ROOT else None)
    def effect(statement,*_):
        action=statement['action']; calls.append(action)
        if action=='accept_candidate':
            head[0]='b'*64
            if calls.count(action)==1: raise RuntimeError('crash after acceptance commit')
            return {'checkpoint_sha256':head[0],'accepted':True}
        return {'stage':action}
    monkeypatch.setattr(controls,'perform_delegated',effect)
    r=req(c,'continue_gameplay',2)
    with pytest.raises(RuntimeError): auto.play(r)
    assert auto.resumable(r)
    result=auto.play(r)
    assert result['phase']=='pregame_ready' and result['simulation_advanced']
    assert auto.play(r)==result
    assert calls.count('authorize_batch')==calls.count('execute_batch')==1
    assert calls.count('accept_candidate')==2  # original effect plus receipt recovery.
