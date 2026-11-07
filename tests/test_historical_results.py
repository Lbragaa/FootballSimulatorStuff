"""Reporting fixtures only: no production registry, seed draws or world writes."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from braga_era import lineage
from braga_era.bridge.historical import HistoricalResults
from braga_era.bridge import protocol2
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest, canonical_json
from braga_era.results import Projection, ResultsError, validate_filters
from test_bridge_control import controls


@pytest.fixture
def records(tmp_path):
    path=tmp_path/'TEST-reporting.sqlite'
    with sqlite3.connect(path) as c:
        c.executescript('''
CREATE TABLE clubs(id INTEGER PRIMARY KEY,name TEXT);
CREATE TABLE fixtures(id INTEGER PRIMARY KEY,competition TEXT,datetime_local TEXT,"round" TEXT,home_id INTEGER,away_id INTEGER,home_goals INTEGER,away_goals INTEGER,status TEXT);
CREATE TABLE world_fixtures(key TEXT PRIMARY KEY,competition TEXT,season INTEGER,stage TEXT,tie_key TEXT,leg INTEGER,home TEXT,away TEXT,kickoff TEXT,status TEXT,source_table TEXT,source_key TEXT,home_goals INTEGER,away_goals INTEGER,resolution_json TEXT);
CREATE TABLE world_receipts(fixture_key TEXT PRIMARY KEY,result_sha256 TEXT);
CREATE TABLE world_ties(key TEXT PRIMARY KEY,competition TEXT,stage TEXT,club_a TEXT,club_b TEXT,aggregate_a INTEGER,aggregate_b INTEGER,winner TEXT,status TEXT);
CREATE TABLE world_draws(key TEXT PRIMARY KEY,status TEXT);
''')
        for i in range(1,21): c.execute('INSERT INTO clubs VALUES(?,?)',(i,'Vasco' if i==15 else 'Flamengo' if i==1 else 'Club '+str(i)))
        for round_,dated in ((28,'2027-10-18'),(29,'2027-10-24'),(30,'2027-11-01'),(31,'2027-11-08')):
            for i in range(10):
                fid=round_*10+i
                h,a=(15,1) if i==0 else (2+i,3+i)
                status='scheduled' if round_==30 else 'final'
                score=(None,None) if status=='scheduled' else (2,2) if i==0 else (i%3,(i+1)%3)
                when=dated+' 16:00'
                c.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(fid,'Brasileirão 2027',when,'R'+str(round_),h,a,*score,status))
                if round_>=29:
                    c.execute('INSERT INTO world_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                              (f'league:{fid}','LEAGUE',2027,'R'+str(round_),None,1,f'club:{h}',f'club:{a}',when,status,'fixtures',str(fid),*score,None))
                    if status=='final':c.execute('INSERT INTO world_receipts VALUES(?,?)',(f'league:{fid}',digest([fid,score])))
        for key,leg,h,a,score,status in (('lib:QF-01:L1',1,2,3,(1,0),'final'),('lib:QF-01:L2',2,3,2,(1,0),'final'),
                                       ('lib:QF-02:L1',1,4,5,(2,1),'final'),('lib:QF-02:L2',2,5,4,(None,None),'scheduled')):
            resolution=json.dumps({'extra_time_played':False,'penalty_score':[4,3] if leg==2 and key.startswith('lib:QF-01') else None})
            c.execute('INSERT INTO world_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (key,'LIB',2027,'QF',key.rsplit(':',1)[0],leg,f'club:{h}',f'club:{a}','2027-10-21 16:00' if leg==1 else '2027-10-28 16:00',status,'calendar_events',key,*score,resolution))
            if status=='final':c.execute('INSERT INTO world_receipts VALUES(?,?)',(key,digest([key,score])))
        c.execute("INSERT INTO world_ties VALUES('lib:QF-01','LIB','QF','club:2','club:3',1,1,'club:3','final')")
        c.execute("INSERT INTO world_ties VALUES('lib:QF-02','LIB','QF','club:4','club:5',2,1,NULL,'scheduled')")
    return path


def projection(path,revealed=('league:290','league:310')):
    with connect_read_only(path) as c:return Projection(c,revealed=revealed)


def test_entire_old_and_current_rodadas_no_mirror_duplicates(records):
    p=projection(records)
    for number in (28,29):
        rows,selection=p.select({'competition':'Brasileirão','season':2027,'round':number})
        assert len(rows)==10==len({r['id'] for r in rows}) and selection['recorded_selection_complete']
        vasco=next(r for r in rows if r['home']['name']=='Vasco')
        assert vasco['score']==[2,2]
    assert len(p.records)==44  # 40 league rows, four knockout legs; mirrors not doubled.
    mirrored=p.records['league:290']
    assert {r['table'] for r in mirrored['sources']}=={'fixtures','world_fixtures'}


def test_first_leg_before_stage_completion_aggregate_and_penalties(records):
    p=projection(records)
    rows,_=p.select({'competition':'Libertadores','stage':'quarterfinals','leg':1})
    assert len(rows)==2 and all(r['leg']==1 for r in rows)
    pending=p.ties['lib:QF-02']
    assert pending['aggregate']==[2,1] and pending['qualified'] is None and not pending['aggregate_complete']
    final=p.ties['lib:QF-01']
    assert final['aggregate']==[1,1] and final['qualified']['id']=='club:3'
    assert final['deciding_resolution']['penalty_score']==[4,3]
    assert final['aggregate_complete']


def test_club_date_recent_and_partial_selection(records):
    p=projection(records)
    rows,_=p.select({'club':'Vasco da Gama','date':'2027-10-24'})
    assert len(rows)==1 and rows[0]['score']==[2,2]
    rows,_=p.select({'club':'Flamengo','recent':2})
    assert [r['round'] for r in rows]==[31,29]
    rows,selection=p.select({'competition':'Brasileirão','round':30,'include_pending':True})
    assert len(rows)==10 and all(r['score'] is None for r in rows)
    assert not selection['recorded_selection_complete']
    assert p.select({'competition':'Brasileirão','season':1999})[0]==[]


@pytest.mark.parametrize('args',[{'seed':'bad'},{'limit':True},{'limit':51},{'leg':3},{'date':'2027-02-30'},
                                 {'date':'2027-01-01','date_to':'2027-02-01'},{'date_from':'2027-02-01','date_to':'2027-01-01'}])
def test_invalid_and_unsupported_filters(args):
    with pytest.raises(ResultsError):validate_filters(args)


def test_unknown_names_and_missing_dates_scores_stay_unknown(records):
    with sqlite3.connect(records) as c:
        c.execute('UPDATE fixtures SET datetime_local=NULL,home_goals=NULL WHERE id=281')
    p=projection(records)
    with pytest.raises(ResultsError,match='Competition'):p.select({'competition':'imaginary cup'})
    with pytest.raises(ResultsError,match='Club'):p.select({'club':'imaginary club'})
    rows,_=p.select({'competition':'Brasileirão','round':28})
    row=next(r for r in rows if r['id']=='fixtures:281')
    assert row['date'] is None and row['score'] is None and row['score_availability']=='not_recorded'
    rows,_=p.select({'competition':'Brasileirão','round':28,'date_from':'2027-01-01'})
    assert len(rows)==9


def test_unrevealed_vasco_not_exposed_and_no_writes(records):
    before=file_sha256(records)
    p=projection(records,revealed=())
    rows,_=p.select({'competition':'Brasileirão','round':29})
    vasco=next(r for r in rows if r['home']['name']=='Vasco')
    assert vasco['score'] is None and vasco['score_availability']=='narration_required'
    assert file_sha256(records)==before
    with connect_read_only(records) as c:
        with pytest.raises(sqlite3.DatabaseError):c.execute('UPDATE fixtures SET home_goals=9')


def test_all_legacy_competitions_seasons_and_final_dedup(accepted_path):
    before=file_sha256(accepted_path)
    p=projection(accepted_path)
    for comp,season,count in [('Brasileirão',2026,71),('Brasileirão',2027,250),('Carioca',2027,5),
                              ('Copa do Brasil',2026,5),('Libertadores',2026,1),('Sul-Americana',2026,1)]:
        rows,_=p.select({'competition':comp,'season':season})
        assert len(rows)==count
    for comp in ('Libertadores','Sudamericana'):
        assert len(p.select({'competition':comp,'season':2027,'stage':'GROUP'})[0])==96
    assert len(p.select({'competition':'Copa do Brasil','season':2027,'stage':'R16'})[0])==16
    f=p.records['fixtures:76']
    assert {s['table'] for s in f['sources']}=={'fixtures','world_finals'}
    assert file_sha256(accepted_path)==before


def test_authenticated_root_reads_preserve_registry_cursors_finances(controls):
    c=controls.career; api=HistoricalResults(c)
    before=(file_sha256(c.registry),file_sha256(c.root_parent),digest(lineage.export_cursor(c.registry,c.key)),c.finances())
    value=api.query({'competition':'Copa do Brasil','season':2027,'stage':'R16'})
    assert len(value['matches'])==16 and value['read_only']
    assert value['accepted_checkpoint']==lineage.ROOT
    assert before==(file_sha256(c.registry),file_sha256(c.root_parent),digest(lineage.export_cursor(c.registry,c.key)),c.finances())


def test_pagination_complete_stable_signed_and_tamper_resistant(records,controls,monkeypatch):
    api=HistoricalResults(controls.career)
    meta={'accepted_checkpoint':'a'*64,'read_only':True}
    visible=['league:290','league:310']
    seen_snapshots=[]
    def snapshot(checkpoint=None,visibility=None):
        seen_snapshots.append(checkpoint)
        return projection(records,visibility if visibility is not None else visible),meta,visible
    monkeypatch.setattr(api,'snapshot',snapshot)
    args={'competition':'Brasileirão','limit':7}
    all_rows=[]
    while True:
        page=api.query(args);assert 'error' not in page
        all_rows+=page['matches']
        if not page['has_more']:break
        args={'cursor':page['next_cursor']}
    assert len(all_rows)==30==len({r['id'] for r in all_rows})
    assert seen_snapshots[1:]==['a'*64]*(len(seen_snapshots)-1)
    assert api.query({'cursor':'tampered'})['error']['code']=='INVALID_CURSOR'
    first=api.query({'limit':1})
    assert api.query({'cursor':first['next_cursor'],'club':'Vasco'})['error']['code']=='CURSOR_FILTER_MISMATCH'
    assert len(canonical_json(first).encode())<55000


def test_bridge_read_only_without_controls_disabled_and_retry(controls,tmp_path):
    from braga_era.bridge.worker2 import Worker2
    from test_bridge import Transport,REQUESTERS
    from test_bridge_worker2 import req
    transport=Transport()
    career=controls.career
    worker=Worker2(transport,career,tmp_path/'bridge'/'ledger.sqlite',REQUESTERS)
    request=req(career,'historical_results',1,competition='Carioca',season=2027)
    assert protocol2.role('historical_results')=='read'
    issue=transport.add(request)
    before=(file_sha256(career.registry),digest(lineage.export_cursor(career.registry,career.key)))
    worker.poll()
    response=transport.result(issue)
    assert response['response']['status']=='completed'
    assert len(response['response']['result']['historical_results']['matches'])==5
    worker.poll()
    duplicate=transport.add(request);worker.poll()
    assert transport.result(duplicate)==response
    assert before==(file_sha256(career.registry),digest(lineage.export_cursor(career.registry,career.key)))


def test_episode_reports_all_ten_after_whistle_and_compact_continuation(records,controls,monkeypatch):
    api=HistoricalResults(controls.career)
    monkeypatch.setattr(api,'snapshot',lambda *_:(projection(records),{'accepted_checkpoint':'a'*64},['league:290','league:310']))
    op={'target':'league:290','target_done':True,'round':'R29','consumed':[f'league:{i}' for i in range(290,300)]+['lib:QF-02:L1']}
    sections,pending=api.episode(op,14000)
    result=sections[0]
    assert result['round_results']['complete'] and len(result['round_results']['matches'])==10
    assert result['other_results'][0]['score']==[2,1]
    assert not pending and result['exhaustive']
    op['target_done']=False
    deferred,pending=api.episode(op,14000)
    assert deferred[0]['section']=='results_deferred' and pending==op['consumed']
    assert '"score":' not in canonical_json(deferred)
    op['target_done']=True
    bounded,_=api.episode(op,1200)
    assert not bounded[0]['exhaustive'] and bounded[0]['retrieve_all']['command']=='historical_results'


def test_source_conflicts_fail_closed(records):
    with sqlite3.connect(records) as c:c.execute("UPDATE world_fixtures SET home_goals=99 WHERE key='league:290'")
    with pytest.raises(ResultsError,match='disagree'):projection(records)


def test_activated_reservations_not_duplicate_pending_fixtures(records):
    with sqlite3.connect(records) as c:
        c.execute("INSERT INTO world_draws VALUES('LIB:QF','activated')")
        c.execute("INSERT INTO world_fixtures VALUES('lib:reserve:QF:L1','LIB',2027,'QF',NULL,1,NULL,NULL,'2027-10-21 16:00','conditional','calendar_events','reservation',NULL,NULL,NULL)")
    p=projection(records)
    assert 'lib:reserve:QF:L1' not in p.records
    assert p.select({'competition':'Libertadores','stage':'QF','include_pending':True})[1]['recorded_pending']==1


def test_authenticated_unsupported_filter_returns_meaningful_read_only_reply(controls,tmp_path):
    from braga_era.bridge.worker2 import Worker2
    from test_bridge import Transport,REQUESTERS
    from test_bridge_worker2 import req
    transport=Transport();career=controls.career
    worker=Worker2(transport,career,tmp_path/'bridge'/'ledger.sqlite',REQUESTERS)
    before=file_sha256(career.registry)
    for sequence,args,code in ((1,{'arbitrary_sql':'DELETE FROM fixtures'},'UNSUPPORTED_FILTER'),
                               (2,{'competition':'not recorded'},'UNKNOWN_COMPETITION'),
                               (3,{'date':'2027-02-30'},'INVALID_DATE')):
        issue=transport.add(req(career,'historical_results',sequence,**args))
        worker.poll()
        result=transport.result(issue)['response']['result']['historical_results']
        assert result['read_only'] and result['error']['code']==code
    assert file_sha256(career.registry)==before
