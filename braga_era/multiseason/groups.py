"""Proposed four-club group stage over stored edition fixtures, not another engine."""
from datetime import datetime,timedelta
import random
from ..history import digest
from ..seasons import double_round_robin


def pools(c,edition):
    clubs=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(edition,))]
    seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
    random.Random(int(digest({'seed':seed,'edition':edition,'policy':'four-club-groups-1','entries':clubs}),16)).shuffle(clubs)
    return {f'GROUP:{i//4+1}':clubs[i:i+4] for i in range(0,len(clubs),4)}


def table(c,edition,group,*,require_complete=True):
    fixtures=c.execute('SELECT * FROM ms_fixtures WHERE edition=? AND stage=? ORDER BY key',(edition,group)).fetchall()
    if len(fixtures)!=12 or require_complete and any(r['status']!='final' for r in fixtures):
        raise ValueError('Group inventory or results incomplete')
    clubs={r[k] for r in fixtures for k in ('home','away')}
    if len(clubs)!=4:raise ValueError('Group identities invalid')
    totals={k:dict(club=k,played=0,points=0,wins=0,gf=0,ga=0) for k in clubs}
    for f in fixtures:
        if f['status']!='final':continue
        for own,gf,ga in ((f['home'],f['home_goals'],f['away_goals']),(f['away'],f['away_goals'],f['home_goals'])):
            t=totals[own];t['played']+=1;t['points']+=3 if gf>ga else int(gf==ga);t['wins']+=int(gf>ga);t['gf']+=gf;t['ga']+=ga
    return sorted(totals.values(),key=lambda t:(-t['points'],-t['wins'],-(t['gf']-t['ga']),-t['gf'],t['club']))


def schedule(c,e,start,deadline):
    from .competitions import insert_fixture
    for name,clubs in pools(c,e['id']).items():
        for f in double_round_robin(clubs,season=e['season'],competition=e['competition']):
            when=(datetime.fromisoformat(start)+timedelta(days=7*(f['round']-1))).isoformat(sep=' ',timespec='minutes')
            insert_fixture(c,e['id'],name,f['round'],None,f['home'],f['away'],when,deadline)


def qualifiers(c,edition):
    result=[]
    for group in sorted(pools(c,edition)):
        result.extend(t['club'] for t in table(c,edition,group)[:2])
    return result
