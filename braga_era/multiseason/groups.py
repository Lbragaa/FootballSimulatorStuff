"""Proposed four-club group stage over stored edition fixtures, not another engine."""
from datetime import datetime,timedelta
import random
from ..history import digest
from ..seasons import double_round_robin
import json


def recorded(c,edition):
    rows=c.execute("SELECT stage,home,away FROM ms_fixtures WHERE edition=? AND stage LIKE 'GROUP:%' ORDER BY stage,key",(edition,)).fetchall()
    if not rows:return None
    groups={};seen={}
    for r in rows:
        groups.setdefault(r['stage'],set()).update((r['home'],r['away']))
    for name,clubs in groups.items():
        if len(clubs)!=4:raise ValueError('Committed group membership is not four distinct clubs')
        for club in clubs:
            if club in seen:raise ValueError('Club appears in multiple committed groups')
            seen[club]=name
        pairs=[(r['home'],r['away']) for r in rows if r['stage']==name]
        expected={(home,away) for home in clubs for away in clubs if home!=away}
        if len(pairs)!=12 or set(pairs)!=expected:raise ValueError('Committed group fixture inventory differs from draw')
    # Country draws already have immutable signed operation receipts. Use that
    # actual draw, and cross-check fixtures rather than rerunning any shuffle.
    for op in c.execute("SELECT args_json,response_json FROM ms_operations WHERE kind IN ('schedule_country_groups','schedule_calendar_country_groups') ORDER BY sequence"):
        if json.loads(op['args_json']).get('edition')!=edition:continue
        draw=json.loads(op['response_json'])['groups']
        if (not isinstance(draw,dict) or any(not isinstance(v,list) or len(v)!=4 or any(not isinstance(k,str) for k in v) or len(set(v))!=4 for v in draw.values())
            or {k:set(v) for k,v in draw.items()}!=groups):raise ValueError('Draw receipt and committed fixtures disagree')
        return draw
    return {name:sorted(clubs) for name,clubs in groups.items()}


def pools(c,edition):
    committed=recorded(c,edition)
    if committed is not None:return committed
    raise ValueError('Group draw has not been committed')


def _planned(c,edition):
    """Private generator input, never a published/inspectable group draw."""
    clubs=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(edition,))]
    seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
    random.Random(int(digest({'seed':seed,'edition':edition,'policy':'four-club-groups-1','entries':clubs}),16)).shuffle(clubs)
    return {f'GROUP:{i//4+1}':clubs[i:i+4] for i in range(0,len(clubs),4)}


def table(c,edition,group,*,require_complete=True):
    membership=recorded(c,edition)
    if membership is None or group not in membership:raise ValueError('Unknown committed group')
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
    for name,clubs in _planned(c,e['id']).items():
        for f in double_round_robin(clubs,season=e['season'],competition=e['competition']):
            when=(datetime.fromisoformat(start)+timedelta(days=7*(f['round']-1))).isoformat(sep=' ',timespec='minutes')
            insert_fixture(c,e['id'],name,f['round'],None,f['home'],f['away'],when,deadline)


def qualifiers(c,edition):
    result=[]
    for group in sorted(pools(c,edition)):
        result.extend(t['club'] for t in table(c,edition,group)[:2])
    return result
