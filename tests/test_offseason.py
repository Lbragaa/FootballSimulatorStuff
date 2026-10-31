"""Forward labour/economic policies exercised only on disconnected test worlds."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
from uuid import uuid4
import pytest
from test_multiseason import parent,KEY,cmd
from braga_era.db import connect_read_only,file_sha256
from braga_era.forward import sign
from braga_era.multiseason import store,offseason
from braga_era.multiseason.agenda import advance
from braga_era.seasons import fingerprints


@pytest.fixture(scope='module')
def prepared(parent,tmp_path_factory):
    target=tmp_path_factory.mktemp('offseason-parent')/'world'
    policy=store.proposed_policy();decision=store.statement(parent,policy,'offseason-regression-fixed-1')
    store.create(parent,target,seed='offseason-regression-fixed-1',policy=policy,decision=decision,signature=sign(KEY,decision),test_key=KEY)
    cmd(target,'prepare_season',season=2028);cmd(target,'open_recorded_account',club='club:15')
    cmd(target,'install_offseason',policy=offseason.POLICY)
    with connect_read_only(target/'database.sqlite') as c:
        foreign=[r[0] for r in c.execute("SELECT key FROM world_clubs WHERE country IS NOT NULL AND country<>'BRA' AND (SELECT count(*) FROM world_players WHERE club_key=key)>=23 ORDER BY key LIMIT 2")]
        keys={'club:15','club:1',*foreign}
        economics=offseason.development_economics(c,2028,keys)
    assert len(economics)==4
    return target,economics


@pytest.fixture
def case(prepared,tmp_path):
    target=tmp_path/'world';shutil.copytree(prepared[0],target)
    economics=json.loads(json.dumps(prepared[1]))
    return target,economics


def configure(target,economics):
    cmd(target,'configure_offseason',season=2028,dated='2028-01-01',policy=offseason.POLICY,economics=economics)
    cmd(target,'settle_economics',dated='2028-01-01 00:00:00')


def test_autonomous_shared_world_exact_crash_retry_and_restore(case,tmp_path):
    target,economics=case;configure(target,economics)
    request=str(uuid4());args={'season':2028,'dated':'2028-01-01','policy':offseason.POLICY}
    with pytest.raises(RuntimeError,match='after commit'):store.run(target,KEY,request,'run_offseason',args,crash='after_commit')
    with ThreadPoolExecutor(2) as pool:replies=list(pool.map(lambda _:store.run(target,KEY,request,'run_offseason',args),range(2)))
    assert replies[0]==replies[1] and replies[0]['clubs_planned']==4 and replies[0]['youth']==8
    before=file_sha256(target/'database.sqlite')
    assert store.run(target,KEY,request,'run_offseason',args)==replies[0]
    assert before==file_sha256(target/'database.sqlite')
    with connect_read_only(target/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_lifecycle WHERE age>=17').fetchone()[0]>80
        assert c.execute("SELECT count(*) FROM ms_market_decisions WHERE kind='squad_plan'").fetchone()[0]==4
        plan=json.loads(c.execute("SELECT detail_json FROM ms_market_decisions WHERE kind='squad_plan' AND club='club:15'").fetchone()[0])
        assert plan['manager']=='Luan Braga'
        assert not c.execute('SELECT 1 FROM ms_registrations WHERE player=196 AND status=\'registered\'').fetchone()
        assert c.execute('SELECT count(*) FROM ms_migrations').fetchone()[0]==2
    package=tmp_path/'portable';report=store.export(target,package,KEY)
    assert store.restore(package,tmp_path/'restored',KEY)==report


@pytest.mark.parametrize('defect',['capital','insolvent','wrong_policy'])
def test_no_implicit_capital_or_unfunded_promises(case,defect):
    target,economics=case
    if defect=='capital':economics['club:15']['opening_liquidity_cents']=1
    if defect=='wrong_policy':
        with pytest.raises(ValueError,match='offseason'):cmd(target,'configure_offseason',season=2028,dated='2028-01-01',policy='unapproved-production',economics=economics)
        return
    if defect=='insolvent':
        key=next(k for k in economics if k!='club:15')
        economics[key].update(opening_liquidity_cents=0,monthly_income_cents=0,monthly_cost_cents=0)
        configure(target,economics)
        with connect_read_only(target/'database.sqlite') as c:before=fingerprints(c)
        with pytest.raises(ValueError,match='insolvent'):cmd(target,'run_offseason',season=2028,dated='2028-01-01',policy=offseason.POLICY)
        with connect_read_only(target/'database.sqlite') as c:assert fingerprints(c)==before
    else:
        with pytest.raises(ValueError,match='capital'):configure(target,economics)
        with connect_read_only(target/'database.sqlite') as c:assert c.execute('SELECT count(*) FROM ms_economics').fetchone()[0]==0


def test_year_obligations_payroll_and_foreign_squads_reconcile(case):
    target,economics=case;configure(target,economics)
    cmd(target,'run_offseason',season=2028,dated='2028-01-01',policy=offseason.POLICY)
    advance(target,KEY,request_id=str(uuid4()),max_groups=1)
    with connect_read_only(target/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_payroll').fetchone()[0]==12
        assert c.execute("SELECT count(*) FROM ms_obligations WHERE status='pending' AND substr(due,1,4)='2028'").fetchone()[0]==0
        accounts=[dict(r) for r in c.execute('SELECT * FROM ms_accounts')]
        assert all(r['cash_cents']>=r['reserve_cents'] for r in accounts)
        before=fingerprints(c)
    response=cmd(target,'pay_month',period='2028-12')
    assert response['paid']
    with connect_read_only(target/'database.sqlite') as c:
        # The new signed read-equivalent retry operation may extend the journal;
        # every economic/football table stays identical.
        after=fingerprints(c)
        assert all(after[t]==before[t] for t in before if t!='ms_operations')
    assert store.validate(target,KEY)['independent_replay']


def test_real_loan_option_accounting_and_guaranteed_wage_release_refusal(case):
    target,economics=case;configure(target,economics)
    cmd(target,'run_offseason',season=2028,dated='2028-01-01',policy=offseason.POLICY)
    # Exercise the low-level agreement machinery in a rollback-only unit
    # transaction. This deliberately does not manufacture a publishable journal.
    with store.connection(target,KEY) as (c,_):
        c.execute('BEGIN IMMEDIATE')
        try:
            buyer=next(k for k in economics if k not in {'club:15','club:1'})
            player=c.execute("SELECT p.id,t.wage_cents FROM world_players p JOIN ms_contracts t ON t.player=p.id WHERE p.club_key='club:1' AND t.status='active' AND NOT EXISTS(SELECT 1 FROM ms_loans l WHERE l.player=p.id AND l.status='active') ORDER BY t.wage_cents LIMIT 1").fetchone()
            assert player
            with pytest.raises(ValueError,match='guaranteed'):
                offseason.release(c,player['id'],'2028-01-02','release')
            with pytest.raises(ValueError,match='Unaffordable'):
                offseason.move(c,player['id'],buyer,'2028-01-02',10**15,player['wage_cents'])
            market=__import__('braga_era.multiseason.market',fromlist=['apply'])
            market.advance_time(c,'2028-01-02 00:00:00')
            loan=offseason.move(c,player['id'],buyer,'2028-01-02',10000,player['wage_cents'],'loan','2028-06-30')
            market.apply(c,'pay_month',{'period':'2028-01'})
            offseason.settle(c,{'dated':'2028-02-01 00:00:00'})
            reply=offseason.apply(c,'exercise_loan_option',{'loan':loan,'dated':'2028-02-01'})
            assert reply['committed_option_exercised']
            assert c.execute('SELECT club_key FROM world_players WHERE id=?',(player['id'],)).fetchone()[0]==buyer
            assert c.execute('SELECT status FROM ms_loans WHERE id=?',(loan,)).fetchone()[0]=='exercised'
            assert c.execute("SELECT count(*) FROM ms_transfers WHERE player=? AND kind IN ('loan','purchase')",(player['id'],)).fetchone()[0]>=2
            assert c.execute("SELECT sum(amount_cents) FROM ms_ledger WHERE category='transfer upfront'").fetchone()[0]==0
            # Expiring a retired player's terms must never resurrect them as
            # an available free agent.
            attrs=json.loads(c.execute('SELECT attributes_json FROM world_players WHERE id=?',(player['id'],)).fetchone()[0])
            attrs.update(eligible=False,exclusion_reasons=['forward retirement 2028-02-02'])
            c.execute('UPDATE world_players SET attributes_json=? WHERE id=?',(json.dumps(attrs),player['id']))
            c.execute("UPDATE ms_contracts SET ends='2028-02-01' WHERE player=? AND status='active'",(player['id'],))
            c.execute("UPDATE ms_lifecycle SET status='retired' WHERE player=?",(player['id'],))
            offseason.release(c,player['id'],'2028-02-02','expiry')
            assert c.execute('SELECT status FROM ms_lifecycle WHERE player=?',(player['id'],)).fetchone()[0]=='retired'
        finally:c.rollback()


def test_multiple_simultaneous_loan_returns_resume_without_uuid_collision(case):
    target,economics=case;configure(target,economics)
    cmd(target,'run_offseason',season=2028,dated='2028-01-01',policy=offseason.POLICY)
    buyer=next(k for k in economics if k not in {'club:15','club:1'})
    with connect_read_only(target/'database.sqlite') as c:
        players=[r[0] for r in c.execute("SELECT p.id FROM world_players p JOIN ms_contracts t ON t.player=p.id WHERE p.club_key='club:1' AND t.status='active' AND NOT EXISTS(SELECT 1 FROM ms_loans l WHERE l.player=p.id AND l.status='active') ORDER BY p.id LIMIT 2")]
    assert len(players)==2
    for pid in players:cmd(target,'loan',player=pid,buyer=buyer,dated='2028-01-02',fee_cents=0,ends='2028-01-31',wage_share_bps=0)
    request=str(uuid4());result=advance(target,KEY,request_id=request,max_groups=1)
    before=file_sha256(target/'database.sqlite')
    assert advance(target,KEY,request_id=request,max_groups=1)==result
    assert before==file_sha256(target/'database.sqlite')
    with connect_read_only(target/'database.sqlite') as c:
        for pid in players:
            assert c.execute('SELECT club_key FROM world_players WHERE id=?',(pid,)).fetchone()[0]=='club:1'
            assert c.execute('SELECT club FROM ms_registrations WHERE season=2028 AND player=?',(pid,)).fetchone()[0]=='club:1'
    assert store.validate(target,KEY)['independent_replay']
