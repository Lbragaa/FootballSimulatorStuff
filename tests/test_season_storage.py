"""Small corruption/identity tests complement the one full career rehearsal."""
import json
import sqlite3

import pytest

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
