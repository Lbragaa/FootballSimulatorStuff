"""Actual constrained draw remains authoritative through execution and restore."""
from uuid import uuid4
import pytest
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason import store
from braga_era.multiseason.groups import pools,table,qualifiers
from braga_era.multiseason.agenda import advance


def test_constrained_draw_fixture_membership_survives_crash_and_restore(candidate,tmp_path):
    cmd(candidate,'prepare_season',season=2028)
    cmd(candidate,'open_recorded_account',club='club:15')
    clubs=[]
    for country in ('BRA','ARG','BOL','CHI'):
        for i in range(8):
            clubs.append(cmd(candidate,'register_fictional_club_country',country=country,
                name=f'Fictional Draw {country} {i}',strength=65+i,dated='2028-01-01')['club'])
    cmd(candidate,'propose_pool',id='country-draw-regression',season=2028,competition='LIB',clubs=clubs,
        reason='NONCANONICAL synthetic draw regression, not national qualification or historical entrants')
    for club in clubs:cmd(candidate,'qualify',season=2028,competition='LIB',club=club,source={'type':'proposed_pool','pool':'country-draw-regression'})
    cmd(candidate,'edition',competition='LIB',season=2028,format='groups_knockout',clubs=clubs,rules={'legs':2,'final_legs':1,'neutral_final':True})
    with connect_read_only(candidate/'database.sqlite') as c:
        with pytest.raises(ValueError,match='not been committed'):pools(c,'LIB:2028')
    args={'edition':'LIB:2028','start':'2028-01-06 16:00','deadline':'2028-12-21 23:59'}
    request=str(uuid4())
    with pytest.raises(RuntimeError,match='after commit'):
        store.run(candidate,KEY,request,'schedule_country_groups',args,crash='after_commit')
    draw=store.run(candidate,KEY,request,'schedule_country_groups',args)['groups']
    assert store.run(candidate,KEY,request,'schedule_country_groups',args)['groups']==draw
    with connect_read_only(candidate/'database.sqlite') as c:
        assert pools(c,'LIB:2028')==draw
        countries={r['key']:r['country'] for r in c.execute('SELECT * FROM world_clubs')}
        assert all(len({countries[k] for k in group})==4 for group in draw.values())
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=6)
    with connect_read_only(candidate/'database.sqlite') as c:
        expected=[r['club'] for name in sorted(draw) for r in table(c,'LIB:2028',name)[:2]]
        assert qualifiers(c,'LIB:2028')==expected
    package=tmp_path/'package';store.export(candidate,package,KEY)
    restored=tmp_path/'restored';store.restore(package,restored,KEY)
    with connect_read_only(restored/'database.sqlite') as c:
        assert pools(c,'LIB:2028')==draw
        assert qualifiers(c,'LIB:2028')==expected


def test_pool_reader_rejects_receipt_fixture_disagreement(candidate):
    import sqlite3,json
    # Corruption fixture only: no fabricated match results.
    with sqlite3.connect(candidate/'database.sqlite') as c:
        for h in range(1,5):
            for a in range(1,5):
                if h==a:continue
                c.execute('INSERT INTO ms_seasons VALUES(2028,?,NULL) ON CONFLICT DO NOTHING',('preparing',))
                c.execute("INSERT INTO ms_editions VALUES('LIB:2028','LIB',2028,'groups_knockout','{}','active',NULL) ON CONFLICT DO NOTHING")
                c.execute("INSERT INTO ms_fixtures VALUES(?,?,?,1,NULL,?,?,?,'scheduled',NULL,NULL,NULL)",
                    (f'test:{h}:{a}','LIB:2028','GROUP:1',f'club:{h}',f'club:{a}','2028-01-06 16:00'))
        c.execute("INSERT INTO ms_operations VALUES(1,'test','schedule_country_groups',?,?,?, ?,?)",
                  (json.dumps({'edition':'LIB:2028'}),json.dumps({'groups':{'GROUP:1':['club:1','club:2','club:3','club:5']}}),'0','corrupt','corrupt'))
    with connect_read_only(candidate/'database.sqlite') as c:
        with pytest.raises(ValueError,match='disagree'):pools(c,'LIB:2028')
        with pytest.raises(ValueError,match='disagree'):table(c,'LIB:2028','GROUP:1',require_complete=False)
        from braga_era.results import Projection
        with pytest.raises(ValueError,match='disagree'):Projection(c)


@pytest.mark.parametrize('defect',['self_pair','duplicate_pair','duplicate_member','duplicate_group'])
def test_invalid_committed_inventory_rejected(defect):
    import sqlite3,json
    with sqlite3.connect(':memory:') as c:
        c.row_factory=sqlite3.Row
        c.execute('CREATE TABLE ms_fixtures(edition,stage,home,away,key)')
        c.execute('CREATE TABLE ms_operations(sequence,kind,args_json,response_json)')
        clubs=['a','b','c','d'];pairs=[(h,a) for h in clubs for a in clubs if h!=a]
        if defect=='self_pair':pairs[0]=('a','a')
        if defect=='duplicate_pair':pairs[0]=pairs[1]
        for i,(h,a) in enumerate(pairs):c.execute('INSERT INTO ms_fixtures VALUES(?,?,?,?,?)',('LIB:2028','GROUP:1',h,a,i))
        if defect=='duplicate_group':
            c.execute("INSERT INTO ms_fixtures SELECT edition,'GROUP:2',home,away,key FROM ms_fixtures")
        draw={'GROUP:1':clubs+(['a'] if defect=='duplicate_member' else [])}
        c.execute('INSERT INTO ms_operations VALUES(1,?,?,?)',('schedule_country_groups',json.dumps({'edition':'LIB:2028'}),json.dumps({'groups':draw})))
        with pytest.raises(ValueError,match='inventory|disagree|multiple'):pools(c,'LIB:2028')
