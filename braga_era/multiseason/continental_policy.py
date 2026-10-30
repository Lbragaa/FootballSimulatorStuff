"""Explicit DEV allocations and deterministic country-constrained pot draw.

Input rankings must be supplied as recorded evidence, never fabricated past
league results. Missing country facts/pools fail rather than receive aliases.
"""
import random
from ..history import digest

ALLOCATIONS={'BRA':7,'ARG':6,'BOL':4,'CHI':4,'COL':4,'ECU':4,'PAR':4,'PER':4,'URU':4,'VEN':4}


def allocate(rankings,champions):
    if set(rankings)!=set(ALLOCATIONS) or len(champions)!=2:raise ValueError('Ten country rankings and two recorded title routes required')
    if any(not isinstance(t,dict) for t in champions) or {t.get('title') for t in champions}!={'LIB','SULA'}:raise ValueError('Both distinct continental title routes required')
    result=[];seen=set()
    for country,count in ALLOCATIONS.items():
        rows=rankings[country]
        if not isinstance(rows,list) or any(not isinstance(k,str) or not k for k in rows):raise ValueError('Recorded club identity lists required')
        if len(set(rows))!=len(rows) or len(rows)<count:raise ValueError('Insufficient or duplicate recorded country pool: '+country)
        for position,club in enumerate(rows[:count],1):
            if club in seen:raise ValueError('Club assigned to multiple countries')
            seen.add(club);result.append({'club':club,'country':country,'route':'domestic_position','position':position})
    for title in champions:
        if set(title)!={'club','country','title'} or title['country'] not in ALLOCATIONS:raise ValueError('Invalid titleholder source')
        club=title['club']
        if club in seen:
            club=next((k for k in rankings[title['country']] if k not in seen),None)
            if club is None:raise ValueError('Title overlap needs recorded replacement depth')
            route='title_overlap_replacement'
        else:route='defending_title'
        seen.add(club);result.append({'club':club,'country':title['country'],'route':route,'title':title['title']})
    if len(seen)!=47:raise ValueError('Invalid 47-club allocation')
    return result


def draw(pots,countries,seed,*,preliminary_exceptions=()):
    if len(pots)!=4 or any(len(p)!=8 for p in pots):raise ValueError('Four eight-club pots required')
    clubs=[k for p in pots for k in p]
    if len(set(clubs))!=32 or set(countries)!=set(clubs) or any(v not in ALLOCATIONS for v in countries.values()):raise ValueError('Unique identities and known countries required')
    exceptions=set(preliminary_exceptions)
    if not exceptions<=set(clubs):raise ValueError('Unknown preliminary exception')
    rng=random.Random(int(digest({'seed':seed,'pots':pots,'countries':countries,'exceptions':sorted(exceptions),'policy':'country-pots-1'}),16))
    groups=[[] for _ in range(8)];nodes=0
    def place(pot,remaining):
        nonlocal nodes
        nodes+=1
        if nodes>100000:raise ValueError('Country draw search bound reached; no constraints relaxed')
        if pot==4:return True
        if not remaining:return place(pot+1,list(pots[pot+1]) if pot<3 else [])
        club=remaining[0];targets=list(range(8));rng.shuffle(targets)
        for i in targets:
            if len(groups[i])!=pot:continue
            same=[k for k in groups[i] if countries[k]==countries[club]]
            if same and not (club in exceptions or all(k in exceptions for k in same)):continue
            groups[i].append(club)
            if place(pot,remaining[1:]):return True
            groups[i].pop()
        return False
    if not place(0,list(pots[0])):raise ValueError('Country restrictions have no feasible draw')
    return {f'GROUP:{i+1}':g for i,g in enumerate(groups)}
