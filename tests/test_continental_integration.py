"""One disconnected country-intake -> both continental finals, no injected scores."""
from collections import Counter
from datetime import datetime,timedelta
from uuid import uuid4
import json
import pytest
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import connect_read_only
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance
from braga_era.multiseason.continental_entry import POLICY,SULA_SLOTS
from braga_era.multiseason.continental_policy import ALLOCATIONS


def scenario():
    return {'type':'development_administrative_scenario','id':'synthetic-continental-entry-2028-v1',
            'reason':'NONCANONICAL administrative entry ordering for integration; not historical national results or approved participants'}


def test_country_intake_through_both_finals_in_one_world(candidate,tmp_path,monkeypatch):
    cmd(candidate,'prepare_season',season=2028);cmd(candidate,'open_recorded_account',club='club:15')
    evidence={}
    for country,n in ALLOCATIONS.items():
        clubs=[]
        for i in range(n+SULA_SLOTS[country]+(2 if country=='BRA' else 0)):
            clubs.append(cmd(candidate,'register_fictional_club_country',country=country,
                name=f'Fictional Continental {country} {i:02}',strength=76-i/2,dated='2028-01-01')['club'])
        evidence[country]={**scenario(),'clubs':clubs}
    titles=[{'competition':comp,'club':evidence['BRA']['clubs'][i],'evidence':scenario()} for i,comp in enumerate(('LIB','SULA'))]
    args={'season':2028,'policy':POLICY,'national_evidence':evidence,'champions':titles}
    request=str(uuid4())
    with pytest.raises(RuntimeError,match='after commit'):store.run(candidate,KEY,request,'commit_continental_entry',args,crash='after_commit')
    intake=store.run(candidate,KEY,request,'commit_continental_entry',args)
    assert store.run(candidate,KEY,request,'commit_continental_entry',args)==intake
    assert Counter(r['competition'] for r in intake['entries'])=={'LIB':28,'LIB_PRE1':6,'LIB_PRE2':13,'SULA':12,'SULA_PRE':32}
    assert all(r['source']['evidence']['type']=='development_administrative_scenario' for r in intake['entries'] if r['route'].startswith('defending'))
    def entries(comp):
        with connect_read_only(candidate/'database.sqlite') as c:
            return [r[0] for r in c.execute('SELECT club FROM ms_qualifications WHERE season=2028 AND competition=? ORDER BY club',(comp,))]
    def edition(comp,format,legs=2):
        cmd(candidate,'edition',competition=comp,season=2028,format=format,clubs=entries(comp),
            rules={'legs':legs,'final_legs':1,'neutral_final':format in {'groups_knockout','sula_cross_playoffs'}})
    deadline='2028-12-21 23:59'
    edition('SULA_PRE','qualifier_ties',1)
    cmd(candidate,'schedule',edition='SULA_PRE:2028',start='2028-01-06 16:00',deadline=deadline)
    for comp,start,target in [('LIB_PRE1','2028-01-06 16:00','LIB_PRE2'),('LIB_PRE2','2028-01-15 16:00','LIB_PRE3'),('LIB_PRE3','2028-01-24 16:00','LIB')]:
        edition(comp,'qualifier_ties')
        cmd(candidate,'schedule',edition=comp+':2028',start=start,deadline=deadline)
        advance(candidate,KEY,request_id=str(uuid4()),max_groups=2)
        winners=cmd(candidate,'close_edition',edition=comp+':2028')['qualifiers']
        for club in winners:cmd(candidate,'qualify',season=2028,competition=target,club=club,source={'type':'edition_qualifier','edition':comp+':2028'})
    sula_pre=cmd(candidate,'close_edition',edition='SULA_PRE:2028')['qualifiers']
    for club in sula_pre:cmd(candidate,'qualify',season=2028,competition='SULA',club=club,source={'type':'edition_qualifier','edition':'SULA_PRE:2028'})
    with connect_read_only(candidate/'database.sqlite') as c:
        losers=[r['club_b'] if r['winner']==r['club_a'] else r['club_a'] for r in c.execute("SELECT * FROM ms_ties WHERE edition='LIB_PRE3:2028'")]
        countries={r['key']:r['country'] for r in c.execute('SELECT key,country FROM world_clubs')}
        for row in c.execute("SELECT * FROM ms_ties WHERE edition LIKE 'LIB_PRE%'"):
            assert countries[row['club_a']]!=countries[row['club_b']]
        for row in c.execute("SELECT * FROM ms_ties WHERE edition='SULA_PRE:2028'"):
            assert countries[row['club_a']]==countries[row['club_b']]
        preliminary_inputs=c.execute("SELECT x.input_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture WHERE f.edition='SULA_PRE:2028'").fetchall()
        assert len(preliminary_inputs)==16
        assert all(json.loads(r[0])['rules']['extra_time'] is False for r in preliminary_inputs)
    for club in losers:cmd(candidate,'qualify',season=2028,competition='SULA',club=club,source={'type':'preliminary_loser','edition':'LIB_PRE3:2028'})
    assert len(entries('LIB'))==len(entries('SULA'))==32
    for comp,format in [('LIB','groups_knockout'),('SULA','sula_cross_playoffs')]:
        edition(comp,format)
        cmd(candidate,'schedule_country_groups',edition=comp+':2028',start='2028-02-03 16:00',deadline=deadline)
    # Interrupt after the first simultaneous main-stage group is durably final.
    # Resume the original run/child IDs rather than creating a replacement run.
    import braga_era.multiseason.agenda as agenda
    original=agenda.run;interrupted=False;run_id=str(uuid4())
    def interrupt_after_play(*pos,**kw):
        nonlocal interrupted
        if pos[3]=='play_group' and not interrupted:
            interrupted=True;kw['crash']='after_commit'
        return original(*pos,**kw)
    with monkeypatch.context() as patch:
        patch.setattr(agenda,'run',interrupt_after_play)
        with pytest.raises(RuntimeError,match='after commit'):advance(candidate,KEY,request_id=run_id,max_groups=6)
    with connect_read_only(candidate/'database.sqlite') as c:
        completed={r[0]:r[1] for r in c.execute('SELECT fixture,result_sha256 FROM ms_executions WHERE result_sha256 IS NOT NULL')}
        finances=[tuple(r) for r in c.execute('SELECT * FROM ms_payroll ORDER BY period')]
    resumed=advance(candidate,KEY,request_id=run_id,max_groups=6)
    assert advance(candidate,KEY,request_id=run_id,max_groups=6)==resumed
    with connect_read_only(candidate/'database.sqlite') as c:
        assert all(c.execute('SELECT result_sha256 FROM ms_executions WHERE fixture=?',(fixture,)).fetchone()[0]==sha for fixture,sha in completed.items())
        assert [tuple(r) for r in c.execute('SELECT * FROM ms_payroll WHERE period<=? ORDER BY period',(finances[-1][0],))]==finances
    for step in range(5):
        with connect_read_only(candidate/'database.sqlite') as c:clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
        start=(datetime.fromisoformat(clock)+timedelta(days=4)).strftime('%Y-%m-%d 16:00')
        if step<4:cmd(candidate,'schedule',edition='LIB:2028',start=start,deadline=deadline)
        cmd(candidate,'schedule',edition='SULA:2028',start=start,deadline=deadline)
        advance(candidate,KEY,request_id=str(uuid4()),max_groups=1 if step==4 else 2)
    for comp in ('LIB','SULA'):assert cmd(candidate,'close_edition',edition=comp+':2028')['champion']
    with connect_read_only(candidate/'database.sqlite') as c:
        counts={r[0]:r[1] for r in c.execute("SELECT edition,count(*) FROM ms_fixtures WHERE status='final' GROUP BY edition")}
        assert counts=={'LIB_PRE1:2028':6,'LIB_PRE2:2028':16,'LIB_PRE3:2028':8,'SULA_PRE:2028':16,'LIB:2028':125,'SULA:2028':141}
        assert c.execute("SELECT count(*) FROM ms_entries WHERE edition='SULA:2028' AND route='LIB_GROUP_THIRD'").fetchone()[0]==8
        assert c.execute('SELECT count(*) FROM ms_executions WHERE result_sha256 IS NOT NULL').fetchone()[0]==312
        assert not c.execute("SELECT 1 FROM ms_fixtures WHERE status!='final'").fetchone()
    verified=store.validate(candidate,KEY)
    package=tmp_path/'continental-entry-to-finals';store.export(candidate,package,KEY)
    restored=store.restore(package,tmp_path/'restored',KEY)
    assert verified['world_sha256']==restored['world_sha256'] and restored['independent_replay']


def test_country_intake_fails_closed_without_evidence(candidate):
    cmd(candidate,'prepare_season',season=2028)
    with pytest.raises(ValueError,match='Ten country'):
        cmd(candidate,'commit_continental_entry',season=2028,policy=POLICY,national_evidence={},champions=[])
    with connect_read_only(candidate/'database.sqlite') as c:
        assert c.execute('SELECT count(*) FROM ms_qualifications').fetchone()[0]==0


def test_recorded_brazilian_league_and_cup_evidence_is_read_only(candidate):
    from braga_era.multiseason.continental_entry import ranking
    from braga_era.db import file_sha256
    before=file_sha256(candidate/'database.sqlite')
    with connect_read_only(candidate/'database.sqlite') as c:
        ordered=ranking(c,'BRA',2028,{'type':'legacy_league_and_cup'})
        assert len(ordered)==len(set(ordered))==20
        assert ordered[0]==c.execute("SELECT club_key FROM world_champions WHERE competition='CDB'").fetchone()[0]
        with pytest.raises(ValueError,match='cup route'):ranking(c,'BRA',2028,{'type':'edition_table','edition':'LEAGUE:2027'})
    assert before==file_sha256(candidate/'database.sqlite')


@pytest.mark.parametrize('defect',[None,'missing_country','duplicate_title','wrong_country','short_depth','duplicate_club','unsupported_policy','false_title','future_table'])
def test_entry_evidence_validation_and_title_overlap(defect):
    import sqlite3
    from braga_era.multiseason.continental_entry import commit
    with sqlite3.connect(':memory:') as c:
        c.row_factory=sqlite3.Row
        c.executescript('''CREATE TABLE world_clubs(key PRIMARY KEY,country,source_id);
            CREATE TABLE world_champions(competition,club_key);
            CREATE TABLE ms_seasons(season,state);
            CREATE TABLE ms_editions(id,season,format,state);
            CREATE TABLE ms_qualifications(id,season,competition,club,source_json);
            INSERT INTO ms_seasons VALUES(2028,'preparing');''')
        evidence={}
        for country,n in ALLOCATIONS.items():
            clubs=[f'{country}:{i}' for i in range(n+SULA_SLOTS[country]+(2 if country=='BRA' else 0))]
            c.executemany('INSERT INTO world_clubs VALUES(?,?,NULL)',[(key,country) for key in clubs])
            evidence[country]={**scenario(),'clubs':clubs}
        titles=[{'competition':comp,'club':f'BRA:{i}','evidence':scenario()} for i,comp in enumerate(('LIB','SULA'))]
        args={'season':2028,'policy':POLICY,'national_evidence':evidence,'champions':titles}
        if defect=='missing_country':del evidence['VEN']
        if defect=='duplicate_title':titles[1]['club']=titles[0]['club']
        if defect=='wrong_country':c.execute("UPDATE world_clubs SET country='ARG' WHERE key='BRA:3'")
        if defect=='short_depth':evidence['PER']['clubs']=evidence['PER']['clubs'][:4]
        if defect=='duplicate_club':evidence['PER']['clubs'][0]=evidence['PER']['clubs'][1]
        if defect=='unsupported_policy':args['policy']='unapproved-other-version'
        if defect=='false_title':titles[0]['evidence']={'type':'legacy_champion'}
        if defect=='future_table':evidence['PER']={'type':'edition_table','edition':'future:2029'}
        if defect:
            with pytest.raises(ValueError):commit(c,args)
            assert c.execute('SELECT count(*) FROM ms_qualifications').fetchone()[0]==0
        else:
            receipt=commit(c,args)
            assert len(receipt['entries'])==91
            assert Counter(r['competition'] for r in receipt['entries'])=={'LIB':28,'LIB_PRE1':6,'LIB_PRE2':13,'SULA':12,'SULA_PRE':32}
            assert {r['club'] for r in receipt['entries'] if r['route'].startswith('defending')}=={'BRA:0','BRA:1'}
            assert not any(r['club'] in {'BRA:0','BRA:1'} and r['route']=='national_entry_order' for r in receipt['entries'])
            with pytest.raises(ValueError,match='already committed'):commit(c,args)
            assert c.execute('SELECT count(*) FROM ms_qualifications').fetchone()[0]==91
