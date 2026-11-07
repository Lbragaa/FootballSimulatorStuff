"""Real-engine domestic entry rounds and state progression on one DEV world."""
from collections import Counter
from datetime import datetime,timedelta
from uuid import uuid4
import json
import pytest
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance
from braga_era.multiseason.domestic import POLICY,CDB_MATCHES


def scenario(reason):return {'type':'development_administrative_scenario','id':'domestic-integration-2028-v1','reason':reason}


def serie_a_entries(candidate):
    clubs=[cmd(candidate,'register_fictional_club',name=f'Fictional Transitional Access {i}',strength=65+i,dated='2028-01-01')['club'] for i in range(8)]
    cmd(candidate,'propose_pool',id='transitional-access',season=2028,competition='ACCESS',clubs=clubs,reason='Explicit forward transition; missing 2027 Série B results are not invented')
    for k in clubs:cmd(candidate,'qualify',season=2028,competition='ACCESS',club=k,source={'type':'proposed_pool','pool':'transitional-access'})
    cmd(candidate,'edition',competition='ACCESS',season=2028,format='qualification',clubs=clubs,rules={'legs':2,'final_legs':1,'neutral_final':False})
    cmd(candidate,'schedule',edition='ACCESS:2028',start='2028-01-06 16:00',deadline='2028-01-31 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=2)
    winners=cmd(candidate,'close_edition',edition='ACCESS:2028')['qualifiers']
    from braga_era.world.adapters import recompute_standings
    with connect_read_only(candidate/'parent.sqlite') as c:
        table=recompute_standings(c,write=False)
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
    survivors=['club:'+str(k) for k in ranked[:16]]
    for pos,key in enumerate(survivors,1):cmd(candidate,'qualify',season=2028,competition='LEAGUE',club=key,source={'type':'legacy_league_position','position':pos})
    for key in winners:cmd(candidate,'qualify',season=2028,competition='LEAGUE',club=key,source={'type':'edition_qualifier','edition':'ACCESS:2028'})
    cmd(candidate,'edition',competition='LEAGUE',season=2028,format='league',clubs=survivors+winners,rules={'legs':2,'final_legs':1,'neutral_final':False})
    return survivors+winners


def test_full_cup_and_carioca_share_chronology_and_players(candidate,tmp_path):
    cmd(candidate,'prepare_season',season=2028);cmd(candidate,'open_recorded_account',club='club:15')
    cmd(candidate,'continue_modeled_registrations',season=2028)
    # Register entrants before the transitional access competition advances time.
    modeled=[cmd(candidate,'register_fictional_club',name=f'Fictional Domestic Entrant {i:03}',strength=60+i%15,dated='2028-01-01')['club'] for i in range(108)]
    top=serie_a_entries(candidate)
    entrants=[{'club':key,'phase':1 if i<36 else 2 if i<102 else 3,'source':scenario('Explicit unknown 2027 state/regional entry scenario, not historical results')} for i,key in enumerate(modeled)]
    entrants +=[{'club':key,'phase':5,'source':{'type':'current_serie_a','edition':'LEAGUE:2028'}} for key in top]
    created=cmd(candidate,'create_domestic_edition',season=2028,competition='CDB',policy=POLICY,entrants=entrants)
    assert created['participants']==128 and CDB_MATCHES==157
    with connect_read_only(candidate/'database.sqlite') as c:
        rio=['club:'+str(r[0]) for r in c.execute("SELECT id FROM clubs WHERE name IN ('Vasco','Flamengo','Fluminense','Botafogo') ORDER BY id")]
    assert len(rio)==4
    state=[{'club':key,'phase':1,'source':scenario('Proposed RJ registration plus explicitly fictional future reserve clubs')} for key in rio+modeled[:8]]
    cmd(candidate,'create_domestic_edition',season=2028,competition='CARIOCA',policy=POLICY,entrants=state)
    active={'CDB:2028','CARIOCA:2028'};deadline='2028-12-21 23:59'
    for edition in sorted(active):cmd(candidate,'schedule',edition=edition,start='2028-01-15 16:00',deadline=deadline)
    rounds=0
    while active:
        for edition in sorted(active.copy()):
            with connect_read_only(candidate/'database.sqlite') as c:
                unfinished=c.execute("SELECT 1 FROM ms_fixtures WHERE edition=? AND status!='final'",(edition,)).fetchone()
                stage=c.execute('SELECT max(stage) FROM ms_ties WHERE edition=?',(edition,)).fetchone()[0]
                clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
            if unfinished:continue
            if stage==(9 if edition.startswith('CDB:') else 3):
                cmd(candidate,'close_edition',edition=edition);active.remove(edition)
            else:
                start=(datetime.fromisoformat(clock)+timedelta(days=4)).strftime('%Y-%m-%d 16:00')
                cmd(candidate,'schedule',edition=edition,start=start,deadline=deadline)
        if active:advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
        rounds+=1
        assert rounds<200
    with connect_read_only(candidate/'database.sqlite') as c:
        assert dict(c.execute("SELECT edition,count(*) FROM ms_fixtures WHERE edition IN ('CDB:2028','CARIOCA:2028') GROUP BY edition"))=={'CDB:2028':157,'CARIOCA:2028':45}
        assert c.execute("SELECT count(*) FROM ms_editions WHERE competition IN ('CDB','CARIOCA') AND champion IS NOT NULL").fetchone()[0]==2
        assert Counter(r[0] for r in c.execute("SELECT stage FROM ms_fixtures WHERE edition='CDB:2028'"))=={'C1':18,'C2':42,'C3':24,'C4':12,'C5':32,'C6':16,'C7':8,'C8':4,'C9':1}
        games=[dict(r) for r in c.execute('SELECT * FROM ms_fixtures ORDER BY kickoff')]
        by_club={}
        for g in games:
            when=datetime.fromisoformat(g['kickoff'])
            for key in (g['home'],g['away']):
                if key in by_club:assert (when-by_club[key]).total_seconds()>=72*3600
                by_club[key]=when
        for row in c.execute("SELECT f.stage,x.input_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture WHERE f.edition='CDB:2028'"):
            data=json.loads(row['input_json']);assert not data['rules']['extra_time']
            assert data['neutral']==(row['stage']=='C9')
    package=tmp_path/'domestic-package';report=store.export(candidate,package,KEY)
    assert store.restore(package,tmp_path/'restored',KEY)['world_sha256']==report['world_sha256']


def test_incorrect_domestic_entry_fails_without_partial_edition(candidate):
    cmd(candidate,'prepare_season',season=2028)
    with pytest.raises(ValueError,match='participant inventory'):
        cmd(candidate,'create_domestic_edition',season=2028,competition='CDB',policy=POLICY,entrants=[])
    with connect_read_only(candidate/'database.sqlite') as c:assert c.execute('SELECT count(*) FROM ms_editions').fetchone()[0]==0


def test_bounded_state_qualifier_and_sporting_next_year_evidence(candidate,tmp_path):
    from braga_era.multiseason.domestic import evidence
    cmd(candidate,'prepare_season',season=2028);cmd(candidate,'open_recorded_account',club='club:15')
    clubs=[cmd(candidate,'register_fictional_club',name=f'Fictional State SP Club {i}',strength=65+i,dated='2028-01-01')['club'] for i in range(8)]
    cmd(candidate,'create_domestic_edition',season=2028,competition='STATE_SP',policy=POLICY,entrants=[{'club':key,'phase':1,'source':scenario('Proposed bounded SP qualifier, not a claim about historical Paulista participants')} for key in clubs])
    for day in ('2028-01-06 16:00','2028-01-13 16:00','2028-01-20 16:00'):
        cmd(candidate,'schedule',edition='STATE_SP:2028',start=day,deadline='2028-12-21 23:59')
        advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
    result=cmd(candidate,'close_edition',edition='STATE_SP:2028')
    assert result['fixtures']==7 and set(result['final_order'])==set(clubs)
    with connect_read_only(candidate/'database.sqlite') as c:
        evidence(c,2029,'CDB',result['champion'],{'type':'edition_finish','edition':'STATE_SP:2028','position':1})
        wrong=next(k for k in clubs if k!=result['champion'])
        with pytest.raises(ValueError,match='another club'):evidence(c,2029,'CDB',wrong,{'type':'edition_finish','edition':'STATE_SP:2028','position':1})
    package=tmp_path/'state-package';report=store.export(candidate,package,KEY)
    assert store.restore(package,tmp_path/'state-restored',KEY)['world_sha256']==report['world_sha256']


@pytest.mark.parametrize('competition',['SUPERCOPA','RECOPA'])
def test_supercup_requires_actual_prior_titles_and_exact_retry(candidate,competition):
    cmd(candidate,'prepare_season',season=2028)
    request=str(uuid4());args={'season':2028,'competition':competition,'policy':POLICY}
    response=store.run(candidate,KEY,request,'create_supercup',args)
    assert store.run(candidate,KEY,request,'create_supercup',args)==response
    assert len(set(response['participants']))==2
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_entries WHERE edition=?',(f'{competition}:2028',)).fetchone()[0]==2


def test_inconsistent_recopa_titles_do_not_invent_an_opponent(candidate):
    import sqlite3
    cmd(candidate,'prepare_season',season=2028)
    # Deliberate invalid unit source, never authenticated/exported as a save.
    with sqlite3.connect(candidate/'database.sqlite') as c:
        c.execute("UPDATE world_champions SET club_key=(SELECT club_key FROM world_champions WHERE competition='LIB') WHERE competition='SULA'")
    with pytest.raises(ValueError,match='exceptional policy'):cmd(candidate,'create_supercup',season=2028,competition='RECOPA',policy=POLICY)
    with connect_read_only(candidate/'database.sqlite') as c:assert not c.execute("SELECT 1 FROM ms_editions WHERE competition='RECOPA'").fetchone()


def test_club_cannot_join_two_state_federations(candidate):
    cmd(candidate,'prepare_season',season=2028)
    entrants=[{'club':f'club:{i}','phase':1,'source':scenario('Unit-only proposed registration; not historical geography')} for i in range(1,13)]
    cmd(candidate,'create_domestic_edition',season=2028,competition='CARIOCA',policy=POLICY,entrants=entrants)
    with pytest.raises(ValueError,match='multiple state'):
        cmd(candidate,'create_domestic_edition',season=2028,competition='STATE_SP',policy=POLICY,entrants=entrants[:8])
