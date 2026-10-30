"""Versioned DEV intake: explicit evidence -> national slots -> real qualifiers.

Administrative scenarios are unapproved inputs, never invented historical scores.
The signed operation retains the complete input and output; no second archive.
"""
import json
from ..history import canonical_json as encode,digest
from .continental_policy import ALLOCATIONS
from .competitions import club,required,standings,brazilian

POLICY='continental-entry-development-1'
SULA_SLOTS={country:6 if country in {'BRA','ARG'} else 4 for country in ALLOCATIONS}


def country_of(c,key):
    club(c,key)
    row=c.execute('SELECT country FROM world_clubs WHERE key=?',(key,)).fetchone()
    return row[0] or ('BRA' if brazilian(c,key) else None)


def scenario(evidence):
    required(evidence,'type id reason')
    if evidence['type']!='development_administrative_scenario' or not all(isinstance(evidence[k],str) and 3<=len(evidence[k])<=1000 for k in ('id','reason')):
        raise ValueError('Explicit NONCANONICAL administrative scenario required')


def ranking(c,country,season,evidence):
    if not isinstance(evidence,dict):raise ValueError('Country entry evidence required')
    kind=evidence.get('type')
    if country=='BRA' and kind=='edition_table':raise ValueError('Brazilian intake requires the recorded cup route as well as its league')
    if kind=='development_administrative_scenario':
        required(evidence,'type id reason clubs')
        scenario({k:v for k,v in evidence.items() if k!='clubs'})
        clubs=evidence['clubs']
    elif kind in {'edition_table','edition_league_and_cup'}:
        required(evidence,'type edition' if kind=='edition_table' else 'type edition cup_edition')
        e=c.execute('SELECT * FROM ms_editions WHERE id=?',(evidence['edition'],)).fetchone()
        if not e or e['format']!='league' or e['state']!='completed' or e['season']!=season-1:
            raise ValueError('Recorded prior-season completed national table required')
        clubs=[r['club'] for r in standings(c,e['id'])]
        if kind=='edition_league_and_cup':
            cup=c.execute('SELECT * FROM ms_editions WHERE id=?',(evidence['cup_edition'],)).fetchone()
            if not cup or cup['competition']!=('CDB' if country=='BRA' else 'STATE') or cup['season']!=season-1 or cup['state']!='completed' or cup['format']!='knockout' or not cup['champion'] or country_of(c,cup['champion'])!=country:
                raise ValueError('Recorded adjacent domestic cup champion required')
            clubs=[cup['champion']]+[key for key in clubs if key!=cup['champion']]
    elif kind=='legacy_league_and_cup':
        required(evidence,'type')
        if country!='BRA' or season!=2028 or c.execute("SELECT count(*) FROM fixtures WHERE competition='Brasileirão 2027' AND status='final'").fetchone()[0]!=380:
            raise ValueError('Completed 2027 Brazilian league and cup required')
        from ..world.adapters import recompute_standings
        table=recompute_standings(c,write=False)
        ordered=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],
            c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
        cup=c.execute("SELECT club_key FROM world_champions WHERE competition='CDB'").fetchone()
        if not cup:raise ValueError('Recorded 2027 domestic cup champion required')
        clubs=[cup[0]]+['club:'+str(k) for k in ordered if 'club:'+str(k)!=cup[0]]
    else:raise ValueError('Unavailable national qualification evidence')
    if not isinstance(clubs,list) or len(clubs)>40 or len(set(clubs))!=len(clubs):raise ValueError('Bounded unique national entry order required')
    if any(country_of(c,key)!=country for key in clubs):raise ValueError('Qualification country disagrees with recorded club identity')
    return clubs


def titleholder(c,season,source):
    required(source,'competition club evidence')
    if source['competition'] not in {'LIB','SULA'}:raise ValueError('Continental title route required')
    club(c,source['club']);evidence=source['evidence']
    if not isinstance(evidence,dict):raise ValueError('Title evidence required')
    kind=evidence.get('type')
    if kind=='development_administrative_scenario':scenario(evidence)
    elif kind=='legacy_champion':
        required(evidence,'type')
        row=c.execute('SELECT club_key FROM world_champions WHERE competition=?',(source['competition'],)).fetchone()
        if season!=2028 or not row or row[0]!=source['club']:raise ValueError('Recorded 2027 title mismatch')
    elif kind=='edition_champion':
        required(evidence,'type edition')
        row=c.execute('SELECT * FROM ms_editions WHERE id=?',(evidence['edition'],)).fetchone()
        if not row or row['season']!=season-1 or row['state']!='completed' or row['competition']!=source['competition'] or row['champion']!=source['club']:
            raise ValueError('Recorded prior-season continental title mismatch')
    else:raise ValueError('Unavailable continental title evidence')
    if country_of(c,source['club']) not in ALLOCATIONS:raise ValueError('Titleholder nationality unavailable')
    return source['club']


def commit(c,a):
    required(a,'season policy national_evidence champions')
    if a['policy']!=POLICY or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():
        raise ValueError('Prepared season and explicit supported DEV intake policy required')
    if c.execute("SELECT 1 FROM ms_qualifications WHERE season=? AND competition IN ('LIB','SULA','LIB_PRE1','LIB_PRE2','LIB_PRE3','SULA_PRE') LIMIT 1",(a['season'],)).fetchone():
        raise ValueError('Continental intake already committed or competing qualifications exist; resume the original request')
    evidence=a['national_evidence'];titles=a['champions']
    if not isinstance(evidence,dict) or set(evidence)!=set(ALLOCATIONS) or not isinstance(titles,list) or len(titles)!=2:
        raise ValueError('Ten country sources and both continental champions required')
    holders={}
    for title in titles:
        key=titleholder(c,a['season'],title)
        if title['competition'] in holders:raise ValueError('Duplicate continental title route')
        holders[title['competition']]=key
    if set(holders)!={'LIB','SULA'} or len(set(holders.values()))!=2:raise ValueError('Two distinct recorded/scenario titleholders required')
    orders={country:ranking(c,country,a['season'],evidence[country]) for country in ALLOCATIONS}
    entries=[];used=set(holders.values())
    source_hash=digest(a)
    def add(comp,key,country,route,source):
        entries.append({'competition':comp,'club':key,'country':country,'route':route,'source':source})
    for comp,key in sorted(holders.items()):
        add('LIB',key,country_of(c,key),'defending_'+comp,next(t for t in titles if t['competition']==comp))
    for country,count in ALLOCATIONS.items():
        available=[k for k in orders[country] if k not in used]
        if len(available)<count+SULA_SLOTS[country]:raise ValueError('Insufficient replacement/entry evidence for '+country)
        for index,key in enumerate(available[:count]):
            # Proposed 28 direct + 6 PRE1 + 13 PRE2 national/title allocation.
            direct=5 if country in {'BRA','ARG'} else 2
            if index<direct:comp='LIB'
            elif country not in {'BRA','ARG','CHI','COL'} and index==count-1:comp='LIB_PRE1'
            else:comp='LIB_PRE2'
            add(comp,key,country,'national_entry_order',{'evidence':evidence[country],'position':orders[country].index(key)+1})
            used.add(key)
        for key in available[count:count+SULA_SLOTS[country]]:
            add('SULA' if country in {'BRA','ARG'} else 'SULA_PRE',key,country,'national_entry_order',{'evidence':evidence[country],'position':orders[country].index(key)+1})
            used.add(key)
    if len(entries)!=91 or len({r['club'] for r in entries})!=91:raise ValueError('Continental intake inventory collision')
    for row in entries:
        source={'type':'continental_entry','policy':POLICY,'evidence_sha256':source_hash,**row}
        c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(f"{row['competition']}:{a['season']}:{row['club']}",a['season'],row['competition'],row['club'],encode(source)))
    return {'policy':POLICY,'season':a['season'],'evidence_sha256':source_hash,'entries':entries,'test_only':True,'canonical_policy_approved':False}


def schedule_sula_pre(c,e,start,deadline):
    from .competitions import insert_fixture
    import random
    if e['state']!='planned':raise ValueError('National preliminary already scheduled')
    countries={}
    for row in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(e['id'],)):
        countries.setdefault(country_of(c,row[0]),[]).append(row[0])
    expected=set(ALLOCATIONS)-{'BRA','ARG'}
    if set(countries)!=expected or any(len(g)!=4 for g in countries.values()):raise ValueError('SULA preliminary requires four entries in each of eight countries')
    seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0];draw={}
    for country,clubs in sorted(countries.items()):
        random.Random(int(digest({'seed':seed,'edition':e['id'],'country':country,'clubs':clubs,'policy':POLICY}),16)).shuffle(clubs)
        draw[country]=clubs
        for i in (0,2):
            home,away=clubs[i:i+2];key=f"{e['id']}:{country}:{i//2+1}"
            c.execute('INSERT INTO ms_ties VALUES(?,?,?,?,?,NULL)',(key,e['id'],1,home,away))
            insert_fixture(c,e['id'],'NATIONAL_PRE',1,key,home,away,start,deadline)
    c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
    return {'edition':e['id'],'policy':POLICY,'country_draws':draw,'scheduled':16}


def preliminary_entries(c,e,entries):
    """New intake only: strength pots, committed seed, no same-country pairing."""
    if e['competition'] not in {'LIB_PRE1','LIB_PRE2','LIB_PRE3'} or not any(
        json.loads(r[0])['season']==e['season'] for r in c.execute("SELECT response_json FROM ms_operations WHERE kind='commit_continental_entry'")):
        return None
    import random
    ranked=sorted(entries,key=lambda k:(-c.execute('SELECT strength FROM world_clubs WHERE key=?',(k,)).fetchone()[0],k))
    half=len(ranked)//2;seeded=ranked[:half];unseeded=ranked[half:]
    seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
    random.Random(int(digest({'seed':seed,'edition':e['id'],'pots':[seeded,unseeded],'policy':POLICY}),16)).shuffle(unseeded)
    countries={k:country_of(c,k) for k in entries}
    if any(v not in ALLOCATIONS for v in countries.values()):raise ValueError('Preliminary draw nationality unavailable')
    nodes=0
    def match(index,remaining):
        nonlocal nodes
        nodes+=1
        if nodes>100000:raise ValueError('Preliminary draw search bound reached; constraints not relaxed')
        if index==half:return []
        for other in remaining:
            if countries[seeded[index]]==countries[other]:continue
            suffix=match(index+1,[k for k in remaining if k!=other])
            if suffix is not None:return [other,seeded[index]]+suffix
        return None
    result=match(0,unseeded)
    if result is None:raise ValueError('No feasible preliminary seeded country draw; constraints not relaxed')
    return result  # Seeded clubs host the return leg.
