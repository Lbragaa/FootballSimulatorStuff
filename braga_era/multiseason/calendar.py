"""Committed season reservations and shared-club/venue calendar constraints.

Optional, explicit DEV policy. Old worlds without a calendar retain exact replay.
Reservations contain dates, never unknown winners or invented participants.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime,timedelta
import json
from ..history import digest
from .competitions import required,COMPETITIONS,club

POLICY='shared-season-calendar-development-1'
_operation=ContextVar('braga_calendar_operation',default=None)


def read(c):
    for row in c.execute("SELECT args_json FROM ms_operations WHERE kind='commit_season_calendar' ORDER BY sequence DESC"):
        value=json.loads(row[0])
        if c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(value['season'],)).fetchone():return value
    return None


@contextmanager
def scope(c):
    token=_operation.set((c,read(c)))
    try:yield
    finally:_operation.reset(token)


def current(c):
    value=_operation.get()
    return value[1] if value is not None and value[0] is c else read(c)


def moment(value):
    if not isinstance(value,str):raise ValueError('Calendar dates must be strings')
    when=datetime.fromisoformat(value)
    if when.tzinfo or when.strftime('%Y-%m-%d %H:%M')!=value:raise ValueError('Minute-precision naive fictional calendar required')
    return when


def commit(c,a):
    required(a,'season policy plans international_windows venues')
    if a['policy']!=POLICY or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Preparing season and explicit calendar policy required')
    if read(c):raise ValueError('Season calendar already committed; resume original dates')
    if c.execute('SELECT 1 FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE e.season=?',(a['season'],)).fetchone():raise ValueError('Commit the calendar before creating its fixtures')
    if not isinstance(a['plans'],dict) or not 1<=len(a['plans'])<=80:raise ValueError('Bounded edition calendar required')
    if not isinstance(a['venues'],dict) or not a['venues'] or len(a['venues'])>1000:raise ValueError('Explicit venue bindings required')
    for key,venue in a['venues'].items():
        if not key.startswith('neutral:'):club(c,key)
        if not isinstance(venue,str) or not 1<=len(venue)<=200:raise ValueError('Bounded named venue required')
    if not isinstance(a['international_windows'],list) or len(a['international_windows'])>12:raise ValueError('Bounded explicit international windows required')
    windows=[]
    for interval in a['international_windows']:
        if not isinstance(interval,list) or len(interval)!=2:raise ValueError('Closed international date intervals required')
        first,last=map(moment,interval)
        if first>last or first.year!=a['season'] or last.year!=a['season']:raise ValueError('Invalid international window')
        windows.append((first,last))
    count=0
    for edition,plans in a['plans'].items():
        comp,year=edition.rsplit(':',1)
        if comp not in COMPETITIONS or year!=str(a['season']) or not isinstance(plans,list) or not plans:raise ValueError('Unsupported calendar edition')
        seen=set();previous=None
        for plan in plans:
            required(plan,'stage command slots')
            if plan['stage'] in seen or plan['command'] not in {'schedule','schedule_country_groups','schedule_calendar_country_groups'}:raise ValueError('Duplicate stage or unsupported calendar action')
            seen.add(plan['stage'])
            if not isinstance(plan['slots'],dict) or not plan['slots']:raise ValueError('Stage leg/round slots required')
            all_dates=[]
            for round,dates in plan['slots'].items():
                if not str(round).isdigit() or int(round)<1 or not isinstance(dates,list) or not dates:raise ValueError('Bounded round slot lists required')
                parsed=[moment(d) for d in dates]
                if parsed!=sorted(set(parsed)):raise ValueError('Sorted unique calendar slots required')
                for when in parsed:
                    if when.year!=a['season'] or not '01-05'<when.strftime('%m-%d')<'12-22' or any(x<=when<=y for x,y in windows):raise ValueError('Calendar reservation violates blackout/international window')
                all_dates+=parsed
            first,last=min(all_dates),max(all_dates)
            if previous and first<=previous:raise ValueError('Stage reservations overlap their prerequisites')
            previous=last;count+=len(all_dates)
    return {'season':a['season'],'policy':POLICY,'calendar_sha256':digest(a),'reservations':count,'conditional_participants':True,'canonical_approval':False}


def stage_name(stage):return 'GROUP' if stage.startswith('GROUP:') else stage


def stage_matches(stage,name):return stage.startswith('GROUP:') if name=='GROUP' else stage==name


def venue(c,calendar,edition,stage,home):
    row=c.execute('SELECT * FROM ms_editions WHERE id=?',(edition,)).fetchone()
    neutral=False
    if row:
        rules=json.loads(row['rules_json'])
        from .domestic import FORMATS,match_policy
        if row['format'] in FORMATS:neutral=match_policy(row,{'stage':stage},True,True)['neutral']
        elif rules['neutral_final'] and rules['final_legs']==1 and stage.startswith('S'):
            n=c.execute('SELECT count(*) FROM ms_entries WHERE edition=?',(edition,)).fetchone()[0]
            n=16 if row['format']=='sula_cross_playoffs' else n//2 if row['format']=='groups_knockout' else n
            neutral=n==2**int(stage[1:])
    key='neutral:'+edition if neutral else home
    if key not in calendar['venues']:raise ValueError('Missing explicit venue binding: '+key)
    return calendar['venues'][key]


def slot(c,home,away,start,deadline,edition,stage,round):
    calendar=current(c)
    if calendar is None:return None
    plans=calendar['plans'].get(edition)
    if not plans:raise ValueError('Competition is absent from committed season calendar: '+str(edition))
    plan=next((p for p in plans if p['stage']==stage_name(stage)),None)
    if not plan or str(round) not in plan['slots']:raise ValueError('Fixture stage/leg has no committed reservation')
    occupied=[dict(r) for r in c.execute('SELECT edition,stage,kickoff,home,away FROM ms_fixtures')]
    selected_venue=venue(c,calendar,edition,stage,home)
    for value in plan['slots'][str(round)]:
        when=moment(value)
        if not start<=when<=deadline:continue
        valid=True
        for game in occupied:
            other=datetime.fromisoformat(game['kickoff']);gap=abs((when-other).total_seconds())
            if gap and gap<3*3600:valid=False;break
            if {home,away}&{game['home'],game['away']} and gap<72*3600:valid=False;break
            if gap<3*3600 and venue(c,calendar,game['edition'],game['stage'],game['home'])==selected_venue:valid=False;break
        if valid:return when.isoformat(sep=' ',timespec='minutes')
    raise ValueError(f'No feasible committed calendar slot for {edition} {stage} leg/round {round}: {home} v {away}; constraints not relaxed')


def event(c):
    calendar=read(c)
    if calendar is None:return None
    events=[];clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
    for edition,plans in sorted(calendar['plans'].items()):
        e=c.execute('SELECT * FROM ms_editions WHERE id=?',(edition,)).fetchone()
        if not e:
            first=min(d for p in plans for values in p['slots'].values() for d in values)
            comp,year=edition.rsplit(':',1)
            from .continental_entry import intake_version
            if comp in {'LIB_PRE1','LIB_PRE2','LIB_PRE3','SULA_PRE','LIB','SULA'} and intake_version(c,int(year)):
                events.append({'kind':'competition_stage','kickoff':first[:10]+' 00:00:00','edition':edition,'action':'activate_continental_edition','args':{'competition':comp,'season':int(year)}})
            else:events.append({'kind':'calendar_blocker','kickoff':first[:10]+' 00:00:00','edition':edition,'reason':'Committed calendar edition is not registered: '+edition})
            continue
        if e['state']=='completed':continue
        games=[dict(r) for r in c.execute('SELECT stage,status FROM ms_fixtures WHERE edition=?',(edition,))]
        for plan in plans:
            present=[g for g in games if stage_matches(g['stage'],plan['stage'])]
            if present:continue
            dates=[d for values in plan['slots'].values() for d in values]
            first,last=min(dates),max(dates)
            events.append({'kind':'competition_stage','kickoff':first[:10]+' 00:00:00','edition':edition,'action':plan['command'],
                'args':{'edition':edition,'start':first,'deadline':last}})
            break
        else:
            if games and all(g['status']=='final' for g in games):events.append({'kind':'competition_stage','kickoff':clock,'edition':edition,'action':'close_edition','args':{'edition':edition}})
    return min(events,key=lambda e:(e['kickoff'],e['edition'],e.get('action',''))) if events else None
