"""Proposed allocation/draw constraints and real-engine preliminary progression."""
from uuid import uuid4
import pytest
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance
from braga_era.multiseason.continental_policy import ALLOCATIONS,allocate,draw,calendar_draw


def test_country_allocations_overlap_and_shortage():
    rankings={k:[f'{k}:{i}' for i in range(n+2)] for k,n in ALLOCATIONS.items()}
    result=allocate(rankings,[{'club':'BRA:0','country':'BRA','title':'LIB'},{'club':'ARG:0','country':'ARG','title':'SULA'}])
    assert len(result)==len({r['club'] for r in result})==47
    assert sum(r['route']=='title_overlap_replacement' for r in result)==2
    rankings['PER']=[]
    with pytest.raises(ValueError,match='Insufficient'):allocate(rankings,[{'club':'BRA:0','country':'BRA','title':'LIB'},{'club':'ARG:0','country':'ARG','title':'SULA'}])


def test_country_draw_reproducible_and_never_relaxes_constraints():
    countries={f'{country}-{pot}':country for pot in range(4) for country in list(ALLOCATIONS)[:8]}
    pots=[[f'{country}-{pot}' for country in list(ALLOCATIONS)[:8]] for pot in range(4)]
    groups=draw(pots,countries,'fixed-before-draw')
    assert groups==draw(pots,countries,'fixed-before-draw')
    assert all(len({countries[k] for k in g})==4 for g in groups.values())
    with pytest.raises(ValueError,match='feasible|bound'):draw(pots,{k:'BRA' for k in countries},'fixed-before-draw')


def test_calendar_fallback_is_versioned_feasible_and_preserves_success(monkeypatch):
    import braga_era.multiseason.continental_policy as policy
    countries={f'{country}-{pot}':country for pot in range(4) for country in list(ALLOCATIONS)[:8]}
    pots=[[f'{country}-{pot}' for country in list(ALLOCATIONS)[:8]] for pot in range(4)]
    original=draw(pots,countries,'fixed-before-draw')
    assert calendar_draw(pots,countries,'fixed-before-draw')==(original,False)
    # Deterministic old-solver exhaustion is an algorithm failure, not permission
    # to choose new inputs, weaken country constraints or change any result.
    def exhausted(*args,**kwargs):raise ValueError('Country draw search bound reached; no constraints relaxed')
    monkeypatch.setattr(policy,'draw',exhausted)
    groups,fallback=calendar_draw(pots,countries,'fixed-before-draw')
    assert fallback and calendar_draw(pots,countries,'fixed-before-draw')==(groups,True)
    assert set(k for g in groups.values() for k in g)==set(countries)
    assert all(len(g)==4 and len({countries[k] for k in g})==4 for g in groups.values())
    assert all(len(set(g)&set(p))==1 for g in groups.values() for p in pots)
    with pytest.raises(ValueError,match='feasible|bound'):
        calendar_draw(pots,{k:'BRA' for k in countries},'fixed-before-draw')


def test_real_search_exhaustion_uses_same_committed_inputs():
    # This four-country pot cycle has a valid assignment, but V1 explores many
    # equivalent branches before finding the required country alignment.
    pots=[[f'{country}:{pot}:{i}' for country in pair for i in range(4)]
          for pot,pair in enumerate([('BRA','ARG'),('BOL','CHI'),('BRA','BOL'),('ARG','CHI')])]
    countries={club:club.split(':')[0] for p in pots for club in p}
    seed='adversarial-country-placement-0'
    with pytest.raises(ValueError,match='search bound'):draw(pots,countries,seed)
    groups,fallback=calendar_draw(pots,countries,seed)
    assert fallback and calendar_draw(pots,countries,seed)==(groups,True)
    assert all(len({countries[k] for k in g})==4 for g in groups.values())
    assert all(len(set(g)&set(p))==1 for g in groups.values() for p in pots)
    assert sorted(k for g in groups.values() for k in g)==sorted(countries)
    exception=pots[-1][-1];countries={**countries,exception:'BRA'}
    groups,fallback=calendar_draw(pots,countries,seed,preliminary_exceptions=[exception])
    assert fallback and all(len({countries[k] for k in g if k!=exception})==len([k for k in g if k!=exception]) for g in groups.values())


def test_three_preliminary_rounds_use_actual_winners(candidate,tmp_path):
    cmd(candidate,'prepare_season',season=2028);cmd(candidate,'open_recorded_account',club='club:15')
    cmd(candidate,'continue_modeled_registrations',season=2028)
    with connect_read_only(candidate/'database.sqlite') as c:
        clubs=[r[0] for r in c.execute('SELECT club_key FROM world_players GROUP BY club_key HAVING count(*)>=23 ORDER BY club_key')]
    winners=[]
    for comp,direct,start in [('LIB_PRE1',clubs[:6],'2028-01-06 16:00'),('LIB_PRE2',clubs[6:19],'2028-01-15 16:00'),('LIB_PRE3',[],'2028-01-24 16:00')]:
        if direct:
            cmd(candidate,'propose_pool',id=comp,season=2028,competition=comp,clubs=direct,reason='Explicit TEST preliminary entry evidence; country allocation integration not claimed')
            for k in direct:cmd(candidate,'qualify',season=2028,competition=comp,club=k,source={'type':'proposed_pool','pool':comp})
        previous={'LIB_PRE2':'LIB_PRE1:2028','LIB_PRE3':'LIB_PRE2:2028'}.get(comp)
        for k in winners:cmd(candidate,'qualify',season=2028,competition=comp,club=k,source={'type':'edition_qualifier','edition':previous})
        entrants=direct+winners
        cmd(candidate,'edition',competition=comp,season=2028,format='qualifier_ties',clubs=entrants,rules={'legs':2,'final_legs':1,'neutral_final':False})
        cmd(candidate,'schedule',edition=comp+':2028',start=start,deadline='2028-12-21 23:59')
        advance(candidate,KEY,request_id=str(uuid4()),max_groups=2)
        winners=cmd(candidate,'close_edition',edition=comp+':2028')['qualifiers']
        assert len(winners)==len(entrants)//2
    assert len(winners)==4
    for k in winners:cmd(candidate,'qualify',season=2028,competition='LIB',club=k,source={'type':'edition_qualifier','edition':'LIB_PRE3:2028'})
    with connect_read_only(candidate/'database.sqlite') as c:
        losers=[r['club_b'] if r['winner']==r['club_a'] else r['club_a'] for r in c.execute("SELECT * FROM ms_ties WHERE edition='LIB_PRE3:2028'")]
        assert c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]==30
    for k in losers:cmd(candidate,'qualify',season=2028,competition='SULA',club=k,source={'type':'preliminary_loser','edition':'LIB_PRE3:2028'})
    package=tmp_path/'preliminary-package';store.export(candidate,package,KEY)
    assert store.restore(package,tmp_path/'restored',KEY)['independent_replay']


def test_country_scheduler_fails_before_fixtures_for_unknown_nationality(candidate):
    cmd(candidate,'prepare_season',season=2028)
    with connect_read_only(candidate/'database.sqlite') as c:
        unknown=c.execute('SELECT key FROM world_clubs WHERE country IS NULL ORDER BY key LIMIT 1').fetchone()[0]
        clubs=[unknown]+[r[0] for r in c.execute('SELECT key FROM world_clubs WHERE key<>? ORDER BY key LIMIT 31',(unknown,))]
    cmd(candidate,'propose_pool',id='unknown-country-test',season=2028,competition='LIB',clubs=clubs,reason='Negative test only; not accepted continental eligibility')
    for k in clubs:cmd(candidate,'qualify',season=2028,competition='LIB',club=k,source={'type':'proposed_pool','pool':'unknown-country-test'})
    cmd(candidate,'edition',competition='LIB',season=2028,format='groups_knockout',clubs=clubs,rules={'legs':2,'final_legs':1,'neutral_final':True})
    with pytest.raises(ValueError,match='unknown nationality'):
        cmd(candidate,'schedule_country_groups',edition='LIB:2028',start='2028-02-01 16:00',deadline='2028-12-21 23:59')
    with connect_read_only(candidate/'database.sqlite') as c:assert c.execute('SELECT count(*) FROM ms_fixtures').fetchone()[0]==0
