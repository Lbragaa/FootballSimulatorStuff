"""Versioned DEV SULA groups -> LIB-third playoffs -> R16 with winner byes."""
from datetime import datetime,timedelta
import json
import random
from ..history import digest,canonical_json as encode
from .competitions import insert_fixture
from .groups import pools,table


def schedule(c,e,start,deadline):
    if e['state']=='planned':
        from .groups import schedule as groups
        groups(c,e,start,deadline)
        c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
        return {'edition':e['id'],'stage':'GROUP','scheduled':96}
    ties=[dict(r) for r in c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage,key',(e['id'],))]
    if not ties:
        own=[table(c,e['id'],g) for g in sorted(pools(c,e['id']))]
        lib=f"LIB:{e['season']}"
        other=c.execute('SELECT * FROM ms_editions WHERE id=?',(lib,)).fetchone()
        if not other or other['format']!='groups_knockout':raise ValueError('Completed Libertadores group source required')
        third_groups={table(c,lib,g)[2]['club']:g for g in sorted(pools(c,lib))}
        thirds=list(third_groups)
        runners=[t[1]['club'] for t in own]
        if len(thirds)!=8 or len(runners)!=8 or set(thirds)&{r['club'] for t in own for r in t}:raise ValueError('Invalid or overlapping continental playoff pools')
        seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
        random.Random(int(digest({'seed':seed,'edition':e['id'],'thirds':thirds,'runners':runners,'policy':'sula-cross-playoff-1'}),16)).shuffle(thirds)
        for club in thirds:
            evidence={'type':'group_position','edition':lib,'group':third_groups[club],'position':3}
            old=c.execute('SELECT source_json FROM ms_qualifications WHERE season=? AND competition=? AND club=?',(e['season'],'SULA',club)).fetchone()
            if old and json.loads(old[0])!=evidence:raise ValueError('Conflicting continental cross-entry provenance')
            if not old:c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(f"SULA:{e['season']}:{club}",e['season'],'SULA',club,encode(evidence)))
            c.execute('INSERT INTO ms_entries VALUES(?,?,?,?)',(e['id'],club,'LIB_GROUP_THIRD',encode(evidence)))
        pairings=list(zip(thirds,runners));stage=0
    else:
        last=max(t['stage'] for t in ties);previous=[t for t in ties if t['stage']==last]
        if any(not t['winner'] for t in previous):raise ValueError('Previous SULA stage unresolved')
        entrants=[t['winner'] for t in previous]
        if len(entrants)==1:raise ValueError('SULA final already completed')
        seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
        random.Random(int(digest({'seed':seed,'edition':e['id'],'stage':last+1,'entrants':sorted(entrants),'policy':'sula-cross-playoff-1'}),16)).shuffle(entrants)
        if last==0:
            winners=[table(c,e['id'],g)[0]['club'] for g in sorted(pools(c,e['id']))]
            if len(entrants)!=8 or len(winners)!=8 or set(entrants)&set(winners):raise ValueError('Invalid SULA R16 seed pots')
            pairings=list(zip(entrants,winners))  # Group winners host the return leg.
        else:pairings=list(zip(entrants[::2],entrants[1::2]))
        stage=last+1
    rules=json.loads(e['rules_json']);legs=rules['final_legs'] if len(pairings)==1 else rules['legs']
    for i,(home,away) in enumerate(pairings,1):
        key=f"{e['id']}:S{stage}:{i}"
        c.execute('INSERT INTO ms_ties VALUES(?,?,?,?,?,NULL)',(key,e['id'],stage,home,away))
        for leg in range(1,legs+1):
            when=(datetime.fromisoformat(start)+timedelta(days=4*(leg-1))).isoformat(sep=' ',timespec='minutes')
            insert_fixture(c,e['id'],'PO' if stage==0 else f'S{stage}',leg,key,home if leg==1 else away,away if leg==1 else home,when,deadline)
    return {'edition':e['id'],'stage':stage,'scheduled':c.execute('SELECT count(*) FROM ms_fixtures WHERE edition=?',(e['id'],)).fetchone()[0]}
