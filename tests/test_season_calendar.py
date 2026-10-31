"""Strict reservations, venues, retries and transaction-local calendar reads."""
from uuid import uuid4
import json
import sqlite3
import pytest
from test_multiseason import candidate,parent,cmd,KEY,setup_edition
from braga_era.db import connect_read_only,file_sha256
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance,next_event
from braga_era.multiseason.calendar import POLICY,current,scope


def calendar(venues,slots):
    return {'season':2028,'policy':POLICY,'plans':{'STATE:2028':[{'stage':'LEAGUE','command':'schedule','slots':slots}]},'international_windows':[],'venues':venues}


@pytest.mark.parametrize('alternative',[False,True])
def test_shared_stadium_requires_an_available_distinct_slot(candidate,alternative):
    setup_edition(candidate)
    slots={str(i):[f'2028-02-{1+7*(i-1):02} 16:00'] for i in range(1,4)}
    # Six matchdays, explicit dates instead of formatting impossible February.
    days=('02-01','02-08','02-15','02-22','03-01','03-08')
    slots={str(i):[f'2028-{d} 16:00']+([f'2028-{d} 20:00'] if alternative else []) for i,d in enumerate(days,1)}
    args=calendar({f'club:{i}':'shared stadium' for i in range(1,5)},slots)
    request=str(uuid4());receipt=store.run(candidate,KEY,request,'commit_season_calendar',args)
    assert store.run(candidate,KEY,request,'commit_season_calendar',args)==receipt
    with pytest.raises(ValueError,match='already committed'):cmd(candidate,'commit_season_calendar',**args)
    if not alternative:
        with pytest.raises(ValueError,match='No feasible committed'):cmd(candidate,'schedule',edition='STATE:2028',start='2028-02-01 16:00',deadline='2028-03-08 20:00')
        with connect_read_only(candidate/'database.sqlite') as c:assert c.execute('SELECT count(*) FROM ms_fixtures').fetchone()[0]==0
    else:
        cmd(candidate,'schedule',edition='STATE:2028',start='2028-02-01 16:00',deadline='2028-03-08 20:00')
        with connect_read_only(candidate/'database.sqlite') as c:
            assert c.execute('SELECT count(DISTINCT kickoff) FROM ms_fixtures').fetchone()[0]==12
        assert store.validate(candidate,KEY)['independent_replay']


@pytest.mark.parametrize('defect',['holiday','international','unregistered','unsupported_action'])
def test_calendar_constraints_fail_closed(candidate,defect):
    setup_edition(candidate)
    args=calendar({f'club:{i}':f'ground-{i}' for i in range(1,5)},{'1':['2028-02-01 16:00']})
    if defect=='holiday':args['plans']['STATE:2028'][0]['slots']['1']=['2028-12-24 16:00']
    if defect=='international':args['international_windows']=[['2028-01-31 00:00','2028-02-02 23:59']]
    if defect=='unsupported_action':args['plans']['STATE:2028'][0]['command']='execute_shell'
    if defect=='unregistered':args['plans']['CDB:2028']=[{'stage':'C1','command':'schedule','slots':{'1':['2028-01-10 16:00']}}]
    if defect=='unregistered':
        cmd(candidate,'commit_season_calendar',**args)
        before=file_sha256(candidate/'database.sqlite')
        assert next_event(candidate,KEY)['kind']=='calendar_blocker'
        assert before==file_sha256(candidate/'database.sqlite')
        with pytest.raises(ValueError,match='not registered'):advance(candidate,KEY,request_id=str(uuid4()),max_groups=1)
    else:
        before=file_sha256(candidate/'database.sqlite')
        with pytest.raises(ValueError):cmd(candidate,'commit_season_calendar',**args)
        assert before==file_sha256(candidate/'database.sqlite')


def test_calendar_read_cache_cannot_cross_connections_or_operations():
    def connection(identity):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        c.executescript("CREATE TABLE ms_operations(kind,args_json,sequence);CREATE TABLE ms_seasons(season,state);INSERT INTO ms_seasons VALUES(2028,'preparing');")
        c.execute("INSERT INTO ms_operations VALUES('commit_season_calendar',?,1)",(json.dumps({'season':2028,'identity':identity}),))
        return c
    with connection('first') as a,connection('second') as b:
        with scope(a):
            assert current(a)['identity']=='first'
            assert current(b)['identity']=='second'
        b.execute('DELETE FROM ms_operations')
        assert current(b) is None
