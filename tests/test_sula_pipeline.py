"""Full-sized main-stage continental pipeline; no injected results."""
from datetime import datetime,timedelta
from uuid import uuid4
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason.agenda import advance
from braga_era.multiseason import store


def test_full_sized_continental_main_stages(candidate,tmp_path):
    cmd(candidate,'prepare_season',season=2028)
    cmd(candidate,'open_recorded_account',club='club:15')
    cmd(candidate,'propose_income',club='club:15',season=2028,monthly_cents=300000000,reason='Explicit TEST-only cashflow, not canonical revenue')
    cmd(candidate,'continue_modeled_registrations',season=2028)
    with connect_read_only(candidate/'database.sqlite') as c:
        clubs=[r[0] for r in c.execute('SELECT club_key FROM world_players GROUP BY club_key HAVING count(*)>=23 ORDER BY club_key')][:64]
    assert len(clubs)==64
    for competition,entries,format in [('LIB',clubs[:32],'groups_knockout'),('SULA',clubs[32:],'sula_cross_playoffs')]:
        cmd(candidate,'propose_pool',id=competition,season=2028,competition=competition,clubs=entries,reason='TEST roster-backed pool; country allocations/preliminaries are not claimed')
        for club in entries:cmd(candidate,'qualify',season=2028,competition=competition,club=club,source={'type':'proposed_pool','pool':competition})
        cmd(candidate,'edition',competition=competition,season=2028,format=format,clubs=entries,rules={'legs':2,'final_legs':1,'neutral_final':True})
        cmd(candidate,'schedule',edition=competition+':2028',start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=6)
    for stage in range(5):
        with connect_read_only(candidate/'database.sqlite') as c:clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
        start=(datetime.fromisoformat(clock)+timedelta(days=4)).strftime('%Y-%m-%d 16:00')
        if stage<4:cmd(candidate,'schedule',edition='LIB:2028',start=start,deadline='2028-12-21 23:59')
        cmd(candidate,'schedule',edition='SULA:2028',start=start,deadline='2028-12-21 23:59')
        advance(candidate,KEY,request_id=str(uuid4()),max_groups=1 if stage==4 else 2)
    cmd(candidate,'close_edition',edition='LIB:2028');cmd(candidate,'close_edition',edition='SULA:2028')
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute("SELECT count(*) FROM ms_fixtures WHERE edition='LIB:2028' AND status='final'").fetchone()[0]==125
        assert c.execute("SELECT count(*) FROM ms_fixtures WHERE edition='SULA:2028' AND status='final'").fetchone()[0]==141
        assert c.execute("SELECT count(*) FROM ms_entries WHERE edition='SULA:2028' AND route='LIB_GROUP_THIRD'").fetchone()[0]==8
        assert c.execute("SELECT count(*) FROM ms_qualifications WHERE competition='SULA' AND season=2028").fetchone()[0]==40
        from braga_era.multiseason.groups import pools,table
        winners={table(c,'SULA:2028',g)[0]['club'] for g in pools(c,'SULA:2028')}
        playoff_clubs={r[k] for r in c.execute("SELECT * FROM ms_ties WHERE edition='SULA:2028' AND stage=0") for k in ('club_a','club_b')}
        assert not winners&playoff_clubs
        assert {r[0] for r in c.execute("SELECT club_b FROM ms_ties WHERE edition='SULA:2028' AND stage=1") }==winners
    verified=store.validate(candidate,KEY)
    assert verified['independent_replay']
    package=tmp_path/'continental-package'
    assert store.export(candidate,package,KEY)['world_sha256']==verified['world_sha256']
    assert store.restore(package,tmp_path/'continental-restored',KEY)['world_sha256']==verified['world_sha256']
