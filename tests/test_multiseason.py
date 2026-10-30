"""New profile uses complete NONCANONICAL 2027 fixtures, never production state."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import json
import shutil
import sqlite3
from uuid import uuid4
import pytest

from braga_era.db import connect_read_only,file_sha256
from braga_era.forward import sign
from braga_era.seasons import AcceptedSource
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance,next_event

KEY=b'TEST ONLY MULTISEASON AUTHORITY!!'*2


@pytest.fixture(scope='module')
def parent(accepted_path,tmp_path_factory):
    path=next((p for p in (Path('output/ci-season/database.sqlite'),Path('output/task03c-final-primary/database.sqlite')) if p.is_file()),None)
    if path is None:
        from tools.stress_season import run
        directory=tmp_path_factory.mktemp('completed-noncanonical-2027')/'world'
        run(accepted_path,directory,'task03c-final-a-fixed-v1',package=False)
        path=directory/'database.sqlite'
    return AcceptedSource(path.resolve(),'NONCANONICAL-completed-2027-fixture',file_sha256(path))


@pytest.fixture
def candidate(parent,tmp_path):
    policy=store.proposed_policy();decision=store.statement(parent,policy,'fixed-before-new-seasons')
    target=tmp_path/'candidate'
    store.create(parent,target,seed='fixed-before-new-seasons',policy=policy,decision=decision,signature=sign(KEY,decision),test_key=KEY)
    return target


def cmd(target,kind,**a):return store.run(target,KEY,str(uuid4()),kind,a)


def setup_edition(target,comp='STATE',clubs=None,format='league'):
    clubs=clubs or ['club:1','club:2','club:3','club:4']
    cmd(target,'prepare_season',season=2028)
    cmd(target,'propose_pool',id='TEST-entry-pool',season=2028,competition=comp,clubs=clubs,reason='Explicit proposed prospective qualification; not historical Série B')
    for club in clubs:cmd(target,'qualify',season=2028,competition=comp,club=club,source={'type':'proposed_pool','pool':'TEST-entry-pool'})
    cmd(target,'edition',competition=comp,season=2028,format=format,clubs=clubs,rules={'legs':2,'final_legs':1,'neutral_final':True})
    cmd(target,'open_recorded_account',club='club:15')
    return f'{comp}:2028'


def test_authenticated_migration_and_no_production_mode(parent,tmp_path):
    policy=store.proposed_policy();decision=store.statement(parent,policy,'fixed')
    with pytest.raises(ValueError,match='signed TEST'):
        store.create(parent,tmp_path/'bad',seed='fixed',policy=policy,decision=decision,signature='0'*64,test_key=KEY)
    policy['test_only']=False
    with pytest.raises(ValueError,match='Unsupported'):store.statement(parent,policy,'fixed')


def test_migration_independent_replay_and_preserved_history(candidate,parent):
    assert store.validate(candidate,KEY)['independent_replay']
    assert file_sha256(candidate/'parent.sqlite')==parent.database_sha256
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_contracts').fetchone()[0]==5
        assert c.execute('SELECT state FROM ms_seasons WHERE season=2027').fetchone()[0]=='archived'
    assert store.validate(candidate,KEY)['acceptance_eligible'] is False


def test_qualification_no_invented_promotions_or_duplicate_entries(candidate):
    cmd(candidate,'prepare_season',season=2028)
    with pytest.raises(ValueError,match='Unavailable'):
        cmd(candidate,'qualify',season=2028,competition='LEAGUE',club='club:1',source={'type':'invented_2027_serie_b_winner'})
    with pytest.raises(ValueError,match='Unqualified'):
        cmd(candidate,'edition',competition='CDB',season=2028,format='knockout',clubs=['club:1','club:2'],rules={'legs':2,'final_legs':1,'neutral_final':False})
    with connect_read_only(candidate/'database.sqlite') as c:assert c.execute('SELECT count(*) FROM ms_editions').fetchone()[0]==0


@pytest.mark.parametrize('stage',['before_commit','after_commit'])
def test_crash_and_exact_transition_retry(candidate,stage):
    request=str(uuid4());args={'season':2028}
    with pytest.raises(RuntimeError,match='Injected'):
        store.run(candidate,KEY,request,'prepare_season',args,crash=stage)
    result=store.run(candidate,KEY,request,'prepare_season',args)
    assert store.run(candidate,KEY,request,'prepare_season',args)==result
    with pytest.raises(ValueError,match='identity reused'):store.run(candidate,KEY,request,'prepare_season',{'season':2029})
    assert store.validate(candidate,KEY)['operations']==1


def test_simultaneous_commitment_and_engine_replay(candidate):
    edition=setup_edition(candidate)
    cmd(candidate,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    event=next_event(candidate,KEY)
    claim_id=str(uuid4());claim=store.run(candidate,KEY,claim_id,'claim_group',{'kickoff':event['kickoff']})
    assert len(claim['committed_fixtures'])==2
    with pytest.raises(ValueError,match='Resume the committed'):cmd(candidate,'evolve',season=2028)
    with pytest.raises(ValueError,match='Incomplete claimed'):store.validate(candidate,KEY)
    with connect_read_only(candidate/'database.sqlite') as c:
        inputs=[tuple(r) for r in c.execute('SELECT fixture,input_sha256,seed_json FROM ms_executions ORDER BY fixture')]
        assert len({json.loads(r[0])['snapshot']['source_sha256'] for r in c.execute('SELECT input_json FROM ms_executions')})==1
    request=str(uuid4())
    with pytest.raises(RuntimeError,match='after commit'):
        store.run(candidate,KEY,request,'play_group',{'kickoff':event['kickoff']},crash='after_commit')
    first=store.run(candidate,KEY,request,'play_group',{'kickoff':event['kickoff']})
    assert store.run(candidate,KEY,request,'play_group',{'kickoff':event['kickoff']})==first
    with connect_read_only(candidate/'database.sqlite') as c:
        assert [tuple(r) for r in c.execute('SELECT fixture,input_sha256,seed_json FROM ms_executions ORDER BY fixture')]==inputs
        assert c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]==2
    assert store.validate(candidate,KEY)['independent_replay']


def test_complete_small_state_league_and_payroll_closure_block(candidate):
    edition=setup_edition(candidate)
    cmd(candidate,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    request=str(uuid4());result=advance(candidate,KEY,request_id=request,max_groups=6)
    assert result==advance(candidate,KEY,request_id=request,max_groups=6)
    assert result['groups_completed']==6
    closed=cmd(candidate,'close_edition',edition=edition)
    assert all(r['played']==6 for r in closed['standings'])
    # Remaining real wages cannot be ignored to manufacture a closed season.
    with pytest.raises(ValueError,match='payroll'):
        cmd(candidate,'archive_season',season=2028,required_competitions=['STATE'])
    assert store.validate(candidate,KEY)['independent_replay']


def test_knockout_progression_and_final_on_same_engine(candidate):
    edition=setup_edition(candidate,'CDB',format='knockout')
    cmd(candidate,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    with pytest.raises(ValueError,match='unresolved'):
        cmd(candidate,'schedule',edition=edition,start='2028-01-20 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=2)
    cmd(candidate,'schedule',edition=edition,start='2028-01-20 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
    final=cmd(candidate,'close_edition',edition=edition)
    assert final['champion'] in {'club:1','club:2','club:3','club:4'}
    assert store.validate(candidate,KEY)['independent_replay']


def test_budget_reserve_and_accounting_fail_closed(candidate):
    cmd(candidate,'prepare_season',season=2028)
    cmd(candidate,'open_recorded_account',club='club:15')
    cmd(candidate,'open_recorded_account',club='club:1')
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute("SELECT cash_cents FROM ms_accounts WHERE club='club:1'").fetchone()[0]==0
        player=c.execute("SELECT id FROM world_players WHERE club_key='club:1' LIMIT 1").fetchone()[0]
    with pytest.raises(ValueError,match='authority|reserve'):
        cmd(candidate,'purchase',player=player,buyer='club:15',dated='2028-01-06',fee_cents=10**15,wage_cents=100,ends='2028-12-31')
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_transfers').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM ms_ledger').fetchone()[0]==0


def test_bounded_evolution_once_preserves_native_players(candidate):
    cmd(candidate,'prepare_season',season=2028)
    result=cmd(candidate,'evolve',season=2028)
    assert result['players_evolved']>1000
    with pytest.raises(ValueError,match='already consumed'):cmd(candidate,'evolve',season=2028)
    with connect_read_only(candidate/'database.sqlite') as c:
        assert all(abs(json.loads(r['after_json'])['ovr']-json.loads(r['before_json'])['ovr'])<=1.501 for r in c.execute('SELECT * FROM ms_attributes'))
    assert store.validate(candidate,KEY)['independent_replay']


def test_restore_and_corrupt_history(candidate,tmp_path,monkeypatch):
    cmd(candidate,'prepare_season',season=2028)
    package=tmp_path/'package';store.export(candidate,package,KEY)
    assert store.restore(package,tmp_path/'restored',KEY)['ok']
    with monkeypatch.context() as limits:
        limits.setattr(store,'MAX_PACKAGE_BYTES',1)
        with pytest.raises(ValueError,match='oversized'):store.restore(package,tmp_path/'oversized',KEY)
        with pytest.raises(ValueError,match='2 GiB'):store.export(candidate,tmp_path/'too-large',KEY)
    with sqlite3.connect(package/'database.sqlite') as c:c.execute("UPDATE fixtures SET home_goals=99 WHERE id=322")
    with pytest.raises(ValueError,match='manifest'):store.restore(package,tmp_path/'bad-restored',KEY)


def test_purchase_loan_return_and_actual_day_payroll(candidate):
    cmd(candidate,'prepare_season',season=2028)
    for k in ('club:15','club:1'):cmd(candidate,'open_recorded_account',club=k)
    with connect_read_only(candidate/'database.sqlite') as c:
        player=next(r['id'] for r in c.execute("SELECT * FROM world_players WHERE club_key='club:1' ORDER BY id") if json.loads(r['attributes_json'])['eligible'])
        cash=sum(r[0] for r in c.execute('SELECT cash_cents FROM ms_accounts'))
    cmd(candidate,'purchase',player=player,buyer='club:15',dated='2028-01-06',fee_cents=100000,wage_cents=10000,ends='2028-12-31')
    loan=cmd(candidate,'loan',player=player,buyer='club:1',dated='2028-01-07',fee_cents=0,ends='2028-01-31',wage_share_bps=0)
    with pytest.raises(ValueError,match='Earlier administrative'):
        cmd(candidate,'return_loan',loan=loan['transfer'],dated='2028-02-01')
    payroll=cmd(candidate,'pay_month',period='2028-01')
    assert cmd(candidate,'pay_month',period='2028-01')==payroll
    cmd(candidate,'return_loan',loan=loan['transfer'],dated='2028-02-01')
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT club_key FROM world_players WHERE id=?',(player,)).fetchone()[0]=='club:15'
        assert c.execute("SELECT sum(amount_cents) FROM ms_ledger WHERE category='transfer fee'").fetchone()[0]==0
        assert sum(r[0] for r in c.execute('SELECT cash_cents FROM ms_accounts'))==cash-sum(payroll['paid'].values())
    assert store.validate(candidate,KEY)['independent_replay']


def test_explicit_income_scenario_can_archive_test_scope_and_prepare_2029(candidate):
    edition=setup_edition(candidate)
    proposal=cmd(candidate,'propose_income',club='club:15',season=2028,monthly_cents=300000000,reason='TEST ONLY incremental operating-income scenario; not a real sponsorship')
    assert proposal['production_authorized'] is False
    cmd(candidate,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=10)
    cmd(candidate,'close_edition',edition=edition)
    cmd(candidate,'archive_season',season=2028,required_competitions=['STATE'])
    assert cmd(candidate,'prepare_season',season=2029)['season']==2029
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_payroll').fetchone()[0]==12
        assert c.execute("SELECT count(*) FROM ms_income WHERE status='applied'").fetchone()[0]==12
    assert store.validate(candidate,KEY)['independent_replay']


def test_signed_operation_response_tampering_and_concurrent_retries(candidate):
    identity=str(uuid4());args={'season':2028}
    with ThreadPoolExecutor(2) as pool:
        futures=[pool.submit(store.run,candidate,KEY,identity,'prepare_season',args) for _ in range(2)]
        assert futures[0].result()==futures[1].result()
    with sqlite3.connect(candidate/'database.sqlite') as c:c.execute("UPDATE ms_operations SET response_json='{}'")
    with pytest.raises(ValueError,match='changed'):store.run(candidate,KEY,identity,'prepare_season',args)
    with pytest.raises(ValueError,match='chain'):store.validate(candidate,KEY)


def test_proposed_pool_cannot_bypass_serie_a_promotion_evidence(candidate):
    cmd(candidate,'prepare_season',season=2028)
    cmd(candidate,'propose_pool',id='invalid-league-route',season=2028,competition='LEAGUE',clubs=['club:1'],reason='TEST negative bypass')
    with pytest.raises(ValueError,match='survival or promotion'):
        cmd(candidate,'qualify',season=2028,competition='LEAGUE',club='club:1',source={'type':'proposed_pool','pool':'invalid-league-route'})


def test_season_aware_history_from_new_edition_is_read_only(candidate):
    from braga_era.results import Projection
    from braga_era.multiseason.views import player_statistics,coach_records
    edition=setup_edition(candidate)
    cmd(candidate,'schedule',edition=edition,start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
    before=file_sha256(candidate/'database.sqlite')
    with connect_read_only(candidate/'database.sqlite') as c:
        rows,_=Projection(c).select({'competition':'STATE','season':2028})
        assert len(rows)==2 and all(r['score'] is not None for r in rows)
        assert all(r['sources'][0]['profile']=='DEV-MULTISEASON-2' for r in rows)
        assert sum(p['goals'] for p in player_statistics(c,2028))==sum(sum(r['score']) for r in rows)
        assert sum(coach['played'] for coach in coach_records(c,2028))==4
    assert file_sha256(candidate/'database.sqlite')==before


def test_explicit_cross_season_suspension_policy(candidate):
    cmd(candidate,'prepare_season',season=2028)
    with connect_read_only(candidate/'database.sqlite') as c:
        source=[tuple(r) for r in c.execute("SELECT player_id,competition,bans FROM world_discipline WHERE bans>0 AND competition IN ('LEAGUE','CDB','LIB','SULA') ORDER BY player_id,competition")]
    result=cmd(candidate,'carry_discipline',season=2028,policy='carry-unserved-bans-reset-yellows-1')
    assert result['unserved_bans_carried']==len(source)
    with connect_read_only(candidate/'database.sqlite') as c:
        for pid,competition,bans in source:
            assert tuple(c.execute('SELECT yellows,bans FROM world_discipline WHERE player_id=? AND competition=?',(pid,competition+':2028')).fetchone())==(0,bans)
    with pytest.raises(ValueError,match='already consumed'):cmd(candidate,'carry_discipline',season=2028,policy='carry-unserved-bans-reset-yellows-1')
    assert store.validate(candidate,KEY)['independent_replay']
