"""Real-engine group completion and advancement, not synthetic score insertion."""
import pytest
from uuid import uuid4
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason.agenda import advance
from braga_era.multiseason import store
from braga_era.multiseason.groups import table


def test_continental_groups_to_final_and_cross_entry_evidence(candidate):
    clubs=[f'club:{i}' for i in range(1,9)]
    cmd(candidate,'prepare_season',season=2028)
    cmd(candidate,'open_recorded_account',club='club:15')
    cmd(candidate,'propose_pool',id='group-test',season=2028,competition='LIB',clubs=clubs,reason='TEST group-stage mechanism; not an official country allocation')
    for club in clubs:cmd(candidate,'qualify',season=2028,competition='LIB',club=club,source={'type':'proposed_pool','pool':'group-test'})
    cmd(candidate,'edition',competition='LIB',season=2028,format='groups_knockout',clubs=clubs,rules={'legs':2,'final_legs':1,'neutral_final':True})
    first=cmd(candidate,'schedule',edition='LIB:2028',start='2028-01-06 16:00',deadline='2028-12-21 23:59')
    assert first['scheduled']==24
    with pytest.raises(ValueError,match='incomplete'):
        cmd(candidate,'schedule',edition='LIB:2028',start='2028-02-20 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=6)
    with connect_read_only(candidate/'database.sqlite') as c:
        groups=[r[0] for r in c.execute("SELECT DISTINCT stage FROM ms_fixtures WHERE stage LIKE 'GROUP:%' ORDER BY stage")]
        thirds=[table(c,'LIB:2028',group)[2]['club'] for group in groups]
        assert all(r['played']==6 for group in groups for r in table(c,'LIB:2028',group))
    for group,club in zip(groups,thirds):
        cmd(candidate,'qualify',season=2028,competition='SULA',club=club,source={'type':'group_position','edition':'LIB:2028','group':group,'position':3})
    cmd(candidate,'schedule',edition='LIB:2028',start='2028-02-20 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=2)
    cmd(candidate,'schedule',edition='LIB:2028',start='2028-03-05 16:00',deadline='2028-12-21 23:59')
    advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
    assert cmd(candidate,'close_edition',edition='LIB:2028')['champion'] in clubs
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]==29
    assert store.validate(candidate,KEY)['independent_replay']
