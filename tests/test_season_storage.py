"""Small corruption/identity tests complement the one full career rehearsal."""
import json
import sqlite3

import pytest
from braga_era.db import file_sha256

from braga_era import season_objects as objects
from braga_era.multiseason.continental_entry import country_of,declare_country


def test_chunk_tree_deduplicates_and_detects_corruption(tmp_path):
    pool=tmp_path/'objects';source=tmp_path/'source'
    data=b''.join(bytes([i%251])*objects.CHUNK for i in range(70))+b'last page'
    source.write_bytes(data);first=objects.capture(pool,source)
    assert 'index' in first and 'pages' not in first
    count=len(list(pool.iterdir()))
    assert objects.capture(pool,source)==first and len(list(pool.iterdir()))==count
    objects.materialize(pool,first,tmp_path/'restored')
    assert (tmp_path/'restored').read_bytes()==data
    damaged=next(objects.pages(pool,first));(pool/(damaged+'.gz')).write_bytes(b'broken')
    with pytest.raises((ValueError,OSError,EOFError)):
        objects.materialize(pool,first,tmp_path/'damaged')
    assert not (tmp_path/'damaged').exists()
    # A verified existing cache is still checked byte for byte on every read.
    (tmp_path/'restored').write_bytes(b'changed')
    with pytest.raises(ValueError,match='cache changed'):
        objects.materialize(pool,first,tmp_path/'restored')


def test_country_declaration_preserves_native_identity_and_rejects_override():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE world_clubs(key TEXT,name TEXT,country TEXT,source_id INTEGER);
        CREATE TABLE league_participants(season INTEGER,club_id INTEGER);
        CREATE TABLE ms_seasons(season INTEGER,state TEXT);
        CREATE TABLE ms_pools(id TEXT PRIMARY KEY,season INTEGER,competition TEXT,clubs_json TEXT,reason TEXT);
        INSERT INTO world_clubs VALUES('unknown','Ambiguous historical club',NULL,NULL),('known','Known','BRA',1);
        INSERT INTO ms_seasons VALUES(2028,'preparing');''')
    a={'club':'unknown','country':'CHI','season':2028,'evidence':{'type':'development_administrative_scenario',
       'id':'forward-country-proposal-1','reason':'Explicit forward assumption, not a historical correction'}}
    assert country_of(c,'unknown') is None
    declare_country(c,a)
    assert country_of(c,'unknown')=='CHI'
    assert c.execute("SELECT country FROM world_clubs WHERE key='unknown'").fetchone()[0] is None
    assert json.loads(c.execute('SELECT clubs_json FROM ms_pools').fetchone()[0])==a
    for value in (a,{**a,'country':'ARG'},{**a,'club':'known'}):
        with pytest.raises(ValueError,match='cannot be replaced'):declare_country(c,value)
    with pytest.raises(ValueError):declare_country(c,{**a,'country':'invented'})
    c.close()


def test_final_review_is_read_only_and_requires_archive(tmp_path):
    from braga_era.season_gameplay import review
    path=tmp_path/'unit-fixture.sqlite';c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE ms_seasons(season INTEGER,state TEXT,archive_json TEXT);
        CREATE TABLE world_clubs(key TEXT,name TEXT);
        CREATE TABLE world_players(id INTEGER,attributes_json TEXT);
        CREATE TABLE ms_executions(fixture TEXT,result_json TEXT);
        CREATE TABLE ms_fixtures(key TEXT,edition TEXT);
        CREATE TABLE ms_editions(id TEXT,season INTEGER);
        INSERT INTO world_clubs VALUES('club:15','Vasco');
        INSERT INTO ms_editions VALUES('LEAGUE:2028',2028);
        INSERT INTO ms_fixtures VALUES('unit-match','LEAGUE:2028');''')
    snapshot={'standings':{'LEAGUE:2028':[{'club':'club:15','points':3}]},
              'editions':[{'competition':'LEAGUE','champion':'club:15'},{'competition':'LIB_PRE1','champion':None}],
              'finances':[{'club':'club:15','cash_cents':100,'provenance_json':'private diagnostic data'}]}
    c.execute('INSERT INTO ms_seasons VALUES(?,?,?)',(2028,'preparing',json.dumps(snapshot)))
    c.execute('INSERT INTO world_players VALUES(?,?)',(1,json.dumps({'name':'Fictional Unit Player'})))
    c.execute('INSERT INTO ms_executions VALUES(?,?)',('unit-match',json.dumps({'performances':[{'player_id':1,'seconds_played':5400,'goals':2,'assists':1}]})))
    c.commit();info={'season':2028,'checkpoint':'a'*64,'database':path}
    with pytest.raises(ValueError,match='Archived season'):review(info)
    c.execute("UPDATE ms_seasons SET state='archived'");c.commit();c.close()
    before=file_sha256(path);result=review(info)
    assert result['top_scorers'][0]['goals']==2 and result['tables']['LEAGUE:2028'][0]['name']=='Vasco'
    assert 'provenance_json' not in result['vasco_finances']
    assert len(result['trophies'])==1
    assert file_sha256(path)==before


def test_signed_candidate_cannot_expand_authorized_season_or_delegation():
    from braga_era import lineage,season_lineage as seasons
    from braga_era.multiseason.registered import policy
    from braga_era.history import digest
    key=b'PUBLIC TEST MANIFEST BINDING ONLY'*2
    t={'career':'unit-test','test_only':True,'seed':'fixed','commissioner':'SIMULATED'}
    a={'profile':seasons.PROFILE,'career':t['career'],'test_only':True,'policy':policy(True),
       'immediate_parent_sha256':'a'*64,'generation':2,'season':2028,'automatic_gameplay':False,
       'career_seed_sha256':digest(t['seed']),'seed_policy':lineage.SEED_POLICY}
    m={**a,'manifest_sha256':digest(a),'world_sha256':'b'*64}
    def node(meta):
        return {'metadata':meta,'manifest':a,'package_sha256':'c'*64,
                'authorization':lineage.signed(seasons.authorization(a),key),
                'validation':lineage.signed(seasons.validation(meta),key),
                'acceptance':lineage.signed(lineage.expected_acceptance(meta,'c'*64,t),key)}
    seasons.verify_node(node(m),t,key)
    for change in ({'automatic_gameplay':True},{'season':2029},{'generation':3},{'test_only':False}):
        # Even a signed validation/acceptance cannot expand the independently
        # signed execution authorization. This guards against signer mistakes.
        with pytest.raises(ValueError,match='exact authorized manifest'):
            seasons.verify_node(node({**m,**change}),t,key)


def test_registered_milestone_preserves_recorded_shootout(tmp_path):
    from braga_era.season_gameplay import state
    from braga_era.bridge.episode import Episode
    path=tmp_path/'milestone-unit.sqlite';db=sqlite3.connect(path)
    db.executescript('''CREATE TABLE world_clubs(key TEXT,name TEXT);
CREATE TABLE ms_editions(id TEXT,competition TEXT,season INTEGER,format TEXT,state TEXT,champion TEXT);
CREATE TABLE ms_fixtures(key TEXT,edition TEXT,stage TEXT,round INTEGER,tie_key TEXT,home TEXT,away TEXT,kickoff TEXT,status TEXT,home_goals INTEGER,away_goals INTEGER);
CREATE TABLE ms_executions(fixture TEXT,result_json TEXT);
CREATE TABLE ms_entries(edition TEXT,club TEXT);
CREATE TABLE ms_ties(key TEXT,edition TEXT,stage INTEGER,club_a TEXT,club_b TEXT,winner TEXT);
INSERT INTO world_clubs VALUES('club:2','Unit A'),('club:3','Unit B');
INSERT INTO ms_editions VALUES('SUPERCOPA:2029','SUPERCOPA',2029,'domestic_supercup','completed','club:2');
INSERT INTO ms_fixtures VALUES('ms:unit','SUPERCOPA:2029','TROPHY',1,'unit-tie','club:2','club:3','2029-01-06 16:00','final',1,1);
INSERT INTO ms_ties VALUES('unit-tie','SUPERCOPA:2029',1,'club:2','club:3','club:2');''')
    bundle={'events':[{'kind':'FINAL_WHISTLE'}],'resolution':{'penalty_score':[4,3],'extra_time_played':True}}
    db.execute('INSERT INTO ms_executions VALUES(?,?)',('ms:unit',json.dumps(bundle)));db.commit();db.close()
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript("CREATE TABLE cursors(fixture TEXT,sequence INTEGER);INSERT INTO cursors VALUES('ms:unit',1);")
    projected=state(c,{'database':path,'season':2029})
    report=Episode.milestone(None,projected,'SUPERCOPA:TROPHY')
    assert report['ties'][0]['legs'][0]['resolution']==bundle['resolution']
    assert report['ties'][0]['qualified']['id']=='club:2'
    c.close()


def test_independent_replay_byte_identity_and_portable_logical_fallback(tmp_path):
    import shutil
    from braga_era.season_lineage import replay_matches
    from braga_era.seasons import fingerprints
    from braga_era.history import digest
    original=tmp_path/'original.sqlite';c=sqlite3.connect(original)
    c.executescript('CREATE TABLE results(score INTEGER);INSERT INTO results VALUES(2);');c.commit()
    expected=digest(fingerprints(c));c.close();byte_hash=file_sha256(original)
    copied=tmp_path/'replay.sqlite';shutil.copyfile(original,copied)
    assert replay_matches(copied,expected,byte_hash)
    assert replay_matches(copied,expected,byte_hash,logical_only=True)
    with sqlite3.connect(copied) as c:c.execute('PRAGMA user_version=17')
    assert file_sha256(copied)!=byte_hash
    assert replay_matches(copied,expected,byte_hash)  # same tables, different header/layout.
    with sqlite3.connect(copied) as c:c.execute('UPDATE results SET score=3')
    assert not replay_matches(copied,expected,byte_hash)
