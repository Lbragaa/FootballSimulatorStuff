"""Generic edition adapters, evidence-based entries and a shared rest calendar.

These are explicitly proposed fictional formats, not imported 2028 regulations.
"""
from datetime import datetime, timedelta
import json
import math
import random
from ..history import canonical_json as encode, digest
from ..seasons import double_round_robin

COMPETITIONS={'LEAGUE','SERIE_B','ACCESS','CDB','CARIOCA','STATE','LIB','SULA','SUPERCOPA','RECOPA'}


def required(args, fields):
    if not isinstance(args,dict) or set(args)!=set(fields.split()):raise ValueError('Unsupported command arguments')
    integers={'season','player','position','monthly_cents','wage_cents','fee_cents','wage_share_bps','max_fee_cents','max_wage_cents','max_groups'}
    strings={'id','competition','club','edition','start','deadline','kickoff','dated','starts','ends','period','reason','policy','name','buyer','loan','income','type','pool'}
    for key,value in args.items():
        if key in integers and type(value) is not int:raise ValueError(key+' must be an integer')
        if key in strings and (not isinstance(value,str) or not value.strip() or len(value)>1000):raise ValueError(key+' must be a bounded nonempty string')
        if key in {'source','rules'} and not isinstance(value,dict):raise ValueError(key+' must be an object')
        if key in {'clubs','required_competitions'} and (not isinstance(value,list) or not value or any(not isinstance(x,str) or not x or len(x)>200 for x in value)):
            raise ValueError(key+' must be a nonempty bounded identity list')


def club(c,key):
    if not isinstance(key,str) or not c.execute('SELECT 1 FROM world_clubs WHERE key=?',(key,)).fetchone():
        raise ValueError('Unknown persistent club identity')


def brazilian(c,key):
    row=c.execute('SELECT source_id,country FROM world_clubs WHERE key=?',(key,)).fetchone()
    return bool(row and (row['country']=='BRA' or row['source_id'] is not None and c.execute('SELECT 1 FROM league_participants WHERE season=2027 AND club_id=?',(row['source_id'],)).fetchone()))


def standings(c,edition):
    rows={r[0]:dict(club=r[0],points=0,played=0,wins=0,draws=0,losses=0,gf=0,ga=0)
          for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(edition,))}
    for f in c.execute("SELECT * FROM ms_fixtures WHERE edition=? AND status='final' ORDER BY key",(edition,)):
        for own,other,gf,ga in ((f['home'],f['away'],f['home_goals'],f['away_goals']),(f['away'],f['home'],f['away_goals'],f['home_goals'])):
            row=rows[own];row['played']+=1;row['wins']+=int(gf>ga);row['draws']+=int(gf==ga);row['losses']+=int(gf<ga)
            row['gf']+=gf;row['ga']+=ga;row['points']+=3 if gf>ga else int(gf==ga)
    return sorted(rows.values(),key=lambda r:(-r['points'],-r['wins'],-(r['gf']-r['ga']),-r['gf'],r['club']))


def qualification(c,a):
    required(a,'season competition club source');club(c,a['club'])
    if type(a['season']) is not int or not 2028<=a['season']<=2200 or a['competition'] not in COMPETITIONS:
        raise ValueError('Unsupported edition or competition')
    if a['competition'] in {'LEAGUE','SERIE_B','ACCESS','CDB','CARIOCA','STATE','SUPERCOPA'} and not brazilian(c,a['club']):
        raise ValueError('Domestic entry lacks recorded or explicit fictional Brazilian identity')
    source=a['source']
    if not isinstance(source,dict):raise ValueError('Qualification evidence required')
    kind=source.get('type')
    if kind=='proposed_pool':
        required(source,'type pool')
        pool=c.execute('SELECT * FROM ms_pools WHERE id=?',(source['pool'],)).fetchone()
        if not pool or (pool['season'],pool['competition'])!=(a['season'],a['competition']) or a['club'] not in json.loads(pool['clubs_json']):
            raise ValueError('Club not in declared proposed pool')
        if a['competition']=='LEAGUE':raise ValueError('Série A entry requires recorded survival or promotion, never a proposed pool')
    elif kind=='group_position':
        required(source,'type edition group position')
        from .groups import table
        e=c.execute('SELECT * FROM ms_editions WHERE id=?',(source['edition'],)).fetchone()
        if not e or e['format']!='groups_knockout' or e['season']!=a['season'] or type(source['position']) is not int or not 1<=source['position']<=4:
            raise ValueError('Invalid completed group qualification source')
        if a['competition']!='SULA' or e['competition']!='LIB' or source['position']!=3:
            raise ValueError('This proposed cross-entry route is only Libertadores third place to Sul-Americana')
        if table(c,e['id'],source['group'])[source['position']-1]['club']!=a['club']:raise ValueError('Group qualification identifies another club')
    elif kind=='legacy_champion':
        required(source,'type competition')
        allowed={'RECOPA':{'LIB','SULA'},'SUPERCOPA':{'LEAGUE','CDB'},'LIB':{'LIB','SULA'},'CDB':{'CDB'}}
        row=c.execute('SELECT club_key FROM world_champions WHERE competition=?',(source['competition'],)).fetchone()
        if a['season']!=2028 or source['competition'] not in allowed.get(a['competition'],set()) or not row or row[0]!=a['club']:
            raise ValueError('Recorded 2027 champion does not support this entry')
    elif kind=='legacy_league_position':
        required(source,'type position')
        from ..world.adapters import recompute_standings
        if type(source['position']) is not int or not 1<=source['position']<=20:raise ValueError('Invalid source position')
        if c.execute("SELECT count(*) FROM fixtures WHERE competition='Brasileirão 2027' AND status='final'").fetchone()[0]!=380:
            raise ValueError('2027 league is not complete')
        table=recompute_standings(c,write=False)
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],
                        c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
        if a['season']!=2028 or a['club']!='club:'+str(ranked[source['position']-1]):raise ValueError('Legacy qualification source mismatch')
        if a['competition']=='LEAGUE' and source['position']>16:raise ValueError('Relegated club cannot qualify by survival')
        if a['competition']=='SERIE_B' and source['position']<=16:raise ValueError('A surviving Série A club cannot be relegated by a reporting choice')
    elif kind in {'edition_position','edition_champion','edition_qualifier'}:
        required(source,'type edition position' if kind=='edition_position' else 'type edition')
        edition=c.execute('SELECT * FROM ms_editions WHERE id=?',(source['edition'],)).fetchone()
        if not edition or edition['state']!='completed' or edition['season']>a['season'] or edition['season']<a['season']-1:
            raise ValueError('Qualification source edition is not completed or adjacent')
        if kind=='edition_champion':winner=edition['champion']
        elif kind=='edition_qualifier':
            if edition['format']!='qualification' or a['club'] not in {r[0] for r in c.execute('SELECT winner FROM ms_ties WHERE edition=?',(edition['id'],))}:
                raise ValueError('Club did not win a recorded access qualification tie')
            winner=a['club']
        else:
            if edition['format']!='league' or type(source['position']) is not int or not 1<=source['position']<=len(standings(c,edition['id'])):raise ValueError('Invalid source standing')
            winner=standings(c,edition['id'])[source['position']-1]['club']
        if a['club']!=winner:raise ValueError('Qualification source does not identify this club')
        if a['competition']=='LEAGUE':
            survival=kind=='edition_position' and edition['competition']=='LEAGUE' and source['position']<=16 and edition['season']==a['season']-1
            promotion=(kind=='edition_position' and edition['competition']=='SERIE_B' and source['position']<=4 and edition['season']==a['season']-1
                       or kind=='edition_qualifier' and edition['competition']=='ACCESS' and edition['season']==a['season'])
            if not survival and not promotion:raise ValueError('No recorded survival or top-four/access promotion route')
    else:raise ValueError('Unavailable qualification source; no historical result invented')
    key=f"{a['competition']}:{a['season']}:{a['club']}"
    c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(key,a['season'],a['competition'],a['club'],encode(source)))
    return {'qualification':key,'source':source,'proposed':True}


def edition(c,a):
    required(a,'competition season format clubs rules')
    if a['competition'] not in COMPETITIONS or a['format'] not in {'league','knockout','qualification','groups_knockout','sula_cross_playoffs'}:raise ValueError('Unsupported competition format')
    if not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Season not prepared')
    clubs=a['clubs'];rules=a['rules']
    if (not isinstance(clubs,list) or len(clubs)<2 or len(set(clubs))!=len(clubs)
        or not isinstance(rules,dict) or set(rules)!={'legs','final_legs','neutral_final'}
        or type(rules['legs']) is not int or rules['legs'] not in (1,2) or type(rules['final_legs']) is not int or rules['final_legs'] not in (1,2)
        or type(rules['neutral_final']) is not bool):raise ValueError('Invalid proposed format or participants')
    if a['format']=='league' and (len(clubs)%2 or len(clubs)<4):raise ValueError('Invalid league size')
    if a['competition'] in {'LEAGUE','SERIE_B'} and (a['format']!='league' or len(clubs)!=20):raise ValueError('National league requires 20 clubs')
    if a['competition']=='ACCESS' and a['format']!='qualification':raise ValueError('Access promotion uses the declared four-tie qualification format')
    if a['format']=='knockout' and len(clubs)&(len(clubs)-1):raise ValueError('Knockout entry count must be a power of two')
    if a['format']=='qualification' and (a['competition']!='ACCESS' or len(clubs)!=8):raise ValueError('Prospective access requires eight clubs and four qualifying ties')
    if a['format']=='groups_knockout' and (a['competition'] not in {'LIB','SULA'} or len(clubs)<8 or len(clubs)>32 or len(clubs)&(len(clubs)-1)):
        raise ValueError('Group prototype requires 8/16/32 continental entrants')
    if a['format']=='sula_cross_playoffs' and (a['competition']!='SULA' or len(clubs)!=32 or rules['legs']!=2 or rules['final_legs']!=1):raise ValueError('SULA cross-playoff format requires 32 group entrants, two-legged ties and single final')
    key=f"{a['competition']}:{a['season']}"
    c.execute('INSERT INTO ms_editions VALUES(?,?,?,?,?,?,NULL)',(key,a['competition'],a['season'],a['format'],encode(rules),'planned'))
    routes=[]
    for k in sorted(clubs):
        q=c.execute('SELECT * FROM ms_qualifications WHERE season=? AND competition=? AND club=?',(a['season'],a['competition'],k)).fetchone()
        if not q:raise ValueError('Unqualified participant: '+k)
        c.execute('INSERT INTO ms_entries VALUES(?,?,?,?)',(key,k,json.loads(q['source_json'])['type'],q['source_json']))
        routes.append(json.loads(q['source_json']))
    if a['competition']=='LEAGUE':
        promotions=sum(r['type']=='edition_qualifier' or r['type']=='edition_position' and c.execute('SELECT competition FROM ms_editions WHERE id=?',(r['edition'],)).fetchone()[0]=='SERIE_B' for r in routes)
        if promotions!=4:raise ValueError('Série A requires exactly sixteen survivors and four recorded promoted clubs')
    return {'edition':key,'participants':len(clubs),'format':a['format'],'proposed':True}


def free_slot(c,home,away,start,deadline):
    start=datetime.fromisoformat(start);end=datetime.fromisoformat(deadline)
    if start.tzinfo or end.tzinfo:raise ValueError('Naive fictional calendar required')
    clock=datetime.fromisoformat(c.execute('SELECT clock FROM ms_meta').fetchone()[0])
    if start<=clock:raise ValueError('Cannot schedule behind the inherited clock')
    occupied=[datetime.fromisoformat(r[0]) for r in c.execute('SELECT kickoff FROM ms_fixtures WHERE home IN (?,?) OR away IN (?,?)',(home,away,home,away))]
    occupied += [datetime.fromisoformat(r[0]) for r in c.execute("SELECT kickoff FROM world_fixtures WHERE status='final' AND (home IN (?,?) OR away IN (?,?))",(home,away,home,away))]
    global_groups={datetime.fromisoformat(r[0]) for r in c.execute('SELECT DISTINCT kickoff FROM ms_fixtures')}
    while start<=end:
        md=start.strftime('%m-%d')
        if ('01-05'<md<'12-22' and all(abs((start-o).total_seconds())>=72*3600 for o in occupied)
            and all(start==o or abs((start-o).total_seconds())>=3*3600 for o in global_groups)):
            return start.isoformat(sep=' ',timespec='minutes')
        start+=timedelta(days=1)
    raise ValueError('No calendar slot under 72-hour/holiday policy; revise proposed calendar')


def insert_fixture(c,edition,stage,number,tie,home,away,start,deadline):
    kickoff=free_slot(c,home,away,start,deadline)
    key=f"ms:{edition}:{stage}:{number}:{home}:{away}"
    c.execute('INSERT INTO ms_fixtures VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
              (key,edition,stage,number,tie,home,away,kickoff,'scheduled',None,None,None))
    return key


def schedule(c,a):
    required(a,'edition start deadline')
    e=c.execute('SELECT * FROM ms_editions WHERE id=?',(a['edition'],)).fetchone()
    if not e or e['state'] not in {'planned','active'}:raise ValueError('Edition not schedulable')
    entries=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(e['id'],))]
    start=datetime.fromisoformat(a['start'])
    if e['format']=='sula_cross_playoffs':
        from .sudamericana import schedule as schedule_sula
        return schedule_sula(c,e,a['start'],a['deadline'])
    if e['format']=='groups_knockout' and e['state']=='planned':
        from .groups import schedule as schedule_groups
        schedule_groups(c,e,a['start'],a['deadline'])
        c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
        return {'edition':e['id'],'stage':'GROUP','scheduled':len(entries)*3}
    if e['format']=='league':
        if e['state']!='planned':raise ValueError('League already scheduled')
        for f in double_round_robin(entries,season=e['season'],competition=e['competition']):
            when=(start+timedelta(days=7*(f['round']-1))).isoformat(sep=' ',timespec='minutes')
            insert_fixture(c,e['id'],'LEAGUE',f['round'],None,f['home'],f['away'],when,a['deadline'])
        stage=0
    else:
        ties=[dict(r) for r in c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage,key',(e['id'],))]
        if ties:
            if e['format']=='qualification':raise ValueError('Access qualification has no invented later championship round')
            last=max(t['stage'] for t in ties);previous=[t for t in ties if t['stage']==last]
            if any(not t['winner'] for t in previous):raise ValueError('Previous knockout stage unresolved')
            entries=[t['winner'] for t in previous]
            if len(entries)==1:raise ValueError('Final already completed')
            stage=last+1
        else:
            stage=1
            if e['format']=='groups_knockout':
                from .groups import qualifiers
                entries=qualifiers(c,e['id'])
        commitment={'edition':e['id'],'stage':stage,'qualified_pool':sorted(entries),
                    'policy':'committed-open-draw-1','seed':c.execute('SELECT seed FROM ms_meta').fetchone()[0]}
        random.Random(int(digest(commitment),16)).shuffle(entries)
        rules=json.loads(e['rules_json']);legs=rules['final_legs'] if len(entries)==2 else rules['legs']
        for i in range(0,len(entries),2):
            home,away=entries[i:i+2];tie=f"{e['id']}:S{stage}:{i//2+1}"
            c.execute('INSERT INTO ms_ties VALUES(?,?,?,?,?,NULL)',(tie,e['id'],stage,home,away))
            for leg in range(1,legs+1):
                when=(start+timedelta(days=4*(leg-1))).isoformat(sep=' ',timespec='minutes')
                insert_fixture(c,e['id'],f'S{stage}',leg,tie,home if leg==1 else away,away if leg==1 else home,when,a['deadline'])
    c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
    return {'edition':e['id'],'stage':stage,'scheduled':c.execute('SELECT count(*) FROM ms_fixtures WHERE edition=?',(e['id'],)).fetchone()[0]}


def close_edition(c,a):
    required(a,'edition')
    e=c.execute('SELECT * FROM ms_editions WHERE id=?',(a['edition'],)).fetchone()
    if not e or e['state']!='active':raise ValueError('Edition not active')
    fixtures=c.execute('SELECT * FROM ms_fixtures WHERE edition=?',(e['id'],)).fetchall()
    if not fixtures or any(f['status']!='final' for f in fixtures):raise ValueError('Edition has incomplete fixtures')
    n=c.execute('SELECT count(*) FROM ms_entries WHERE edition=?',(e['id'],)).fetchone()[0]
    if e['format']=='league':
        if len(fixtures)!=n*(n-1):raise ValueError('Incomplete league inventory')
        table=standings(c,e['id']);winner=table[0]['club']
    elif e['format']=='qualification':
        ties=c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY key',(e['id'],)).fetchall()
        rules=json.loads(e['rules_json'])
        if len(ties)!=4 or len(fixtures)!=4*rules['legs'] or any(not t['winner'] for t in ties):raise ValueError('Incomplete access qualification process')
        winner=None;table=None
    elif e['format']=='sula_cross_playoffs':
        ties=c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage DESC,key',(e['id'],)).fetchall()
        if len(fixtures)!=141 or len(ties)!=23 or any(not t['winner'] for t in ties):raise ValueError('Incomplete SULA group/playoff/knockout path')
        winner=ties[0]['winner'];table=None
    else:
        ties=c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage DESC,key',(e['id'],)).fetchall()
        rules=json.loads(e['rules_json']);knockout_n=n//2 if e['format']=='groups_knockout' else n
        expected=(knockout_n-2)*rules['legs']+rules['final_legs']+(n*3 if e['format']=='groups_knockout' else 0)
        if len(ties)!=knockout_n-1 or len(fixtures)!=expected or any(not t['winner'] for t in ties):raise ValueError('Incomplete knockout path')
        winner=ties[0]['winner'];table=None
    c.execute("UPDATE ms_editions SET state='completed',champion=? WHERE id=?",(winner,e['id']))
    qualifiers=[r[0] for r in c.execute('SELECT winner FROM ms_ties WHERE edition=? ORDER BY key',(e['id'],))] if e['format']=='qualification' else None
    return {'edition':e['id'],'champion':winner,'standings':table,'qualifiers':qualifiers,'test_only':True}
