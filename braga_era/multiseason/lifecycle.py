"""Shared lifecycle setup used by the rehearsal and registered lineage executor.

Explicit proposed inputs, never fabricated historical qualification or income.
The football, draw, market and calendar operations remain the existing ones.
"""
from datetime import datetime,timedelta
import json
from ..db import connect_read_only
from ..history import digest
from .domestic import POLICY as DOMESTIC
from .divisions import POLICY as DIVISIONS
from .calendar import POLICY as CALENDAR

SEASON_POLICIES = {
    "supported-ecosystem-proposal-1": ("full-2028-proposal-1", "repeat-season-proposal-1"),
    "supported-ecosystem-rio-venues-2": ("full-2028-rio-venues-2", "repeat-season-rio-venues-2"),
}
RELEASE_PROPOSAL = "supported-ecosystem-rio-venues-2"
RIO_GROUNDS = {"Flamengo": "Maracanã", "Fluminense": "Raulino de Oliveira",
               "Vasco": "São Januário", "Botafogo": "Nilton Santos"}


def venue_bindings(db, rio_alternative):
    rows = db.execute("SELECT key,name FROM world_clubs").fetchall()
    if rio_alternative and not RIO_GROUNDS.keys() <= {row['name'] for row in rows}:
        raise ValueError("Rio venue proposal requires the four recorded club identities")
    return {row['key']: RIO_GROUNDS.get(row['name'], 'Proposed individual ground: ' + row['key'])
            if rio_alternative else 'TEST assumed individual ground: ' + row['key'] for row in rows}

def scenario(reason):return {'type':'development_administrative_scenario','id':'domestic-year-transition-1','reason':reason}


def dates(first,last):
    day=datetime.fromisoformat(first);end=datetime.fromisoformat(last);result=[]
    while day<=end:result.append(day.strftime('%Y-%m-%d %H:%M'));day+=timedelta(days=1)
    return result


def plans(year,include_continental=False):
    def one(stage,*values):return {'stage':stage,'command':'schedule','slots':{str(i):[f'{year}-{value} 16:00'] for i,value in enumerate(values,1)}}
    international=[[f'{year}-{start} 00:00',f'{year}-{end} 23:59'] for start,end in [('03-20','03-28'),('06-05','06-13'),('09-04','09-12'),('10-09','10-17')]]
    day=datetime(year,3,1)
    while day.weekday()!=6:day+=timedelta(days=1)
    sundays=[]
    while len(sundays)<38:
        value=day.strftime('%Y-%m-%d %H:%M').replace('00:00','16:00')
        if not any(a<=value<=b for a,b in international):sundays.append(value)
        day+=timedelta(days=7)
    def league(n):return [{'stage':'LEAGUE','command':'schedule','slots':{str(i):[d] for i,d in enumerate(sundays[:n],1)}}]
    calendar={f'LEAGUE:{year}':league(38),f'SERIE_B:{year}':league(38),f'LOWER:{year}':league(14)}
    if year==2028:
        calendar[f'ACCESS:{year}']=[one('S1','01-06','01-10')]
        calendar[f'CARIOCA:{year}']=[{'stage':'POOL','command':'schedule','slots':{str(i+1):dates((datetime(year,1,7,16)+timedelta(days=4*i)).strftime('%Y-%m-%d %H:%M'),f'{year}-02-01 16:00') for i in range(6)}},one('K1','02-04'),one('K2','02-11','02-18'),one('K3','02-25')]
        calendar[f'CDB:{year}']=[one('C1','02-07'),one('C2','02-21'),one('C3','03-15'),one('C4','04-05'),one('C5','05-10','05-17'),one('C6','07-05','07-12'),one('C7','08-09','08-16'),one('C8','09-20','09-27'),one('C9','11-22')]
        calendar[f'SUPERCOPA:{year}']=[one('TROPHY','01-06')]
        calendar[f'RECOPA:{year}']=[one('TROPHY','01-10','01-17')]
        if include_continental:
            calendar[f'LIB_PRE1:{year}']=[one('S1','01-24','01-31')]
            calendar[f'LIB_PRE2:{year}']=[one('S1','02-07','02-14')]
            calendar[f'LIB_PRE3:{year}']=[one('S1','02-21','02-28')]
            calendar[f'SULA_PRE:{year}']=[one('NATIONAL_PRE','03-08')]
            groups={'stage':'GROUP','command':'schedule_calendar_country_groups','slots':{str(i):[f'{year}-{date} 16:00'] for i,date in enumerate(('04-12','04-26','05-03','05-24','06-14','06-28'),1)}}
            calendar[f'LIB:{year}']=[groups,one('S1','08-02','08-23'),one('S2','09-13','10-04'),one('S3','11-01','11-08'),one('S4','11-29')]
            calendar[f'SULA:{year}']=[groups,one('PO','07-19','07-26'),one('S1','08-02','08-23'),one('S2','09-13','10-04'),one('S3','11-01','11-08'),one('S4','11-15')]
    return calendar,international



def setup_2028(target, command, advance_group, *, include_continental=True, with_offseason=True, rio_alternative=False):
    command('open_recorded_account',club='club:15')
    if not with_offseason:
        command('propose_income',club='club:15',season=2028,monthly_cents=300000000,reason='Hypothetical TEST incremental operating-income scenario for known contracts; not real revenue, owner capital or approved finances')
        command('evolve',season=2028);command('continue_modeled_registrations',season=2028)
    command('carry_discipline',season=2028,policy='carry-unserved-bans-reset-yellows-1')
    def register(prefix,n):return [command('register_fictional_club',name=f'Fictional {prefix} {i:03}',strength=60+i%15,dated='2028-01-01')['club'] for i in range(n)]
    pool=register('Domestic State Entrant',108);access=register('Initial Access Entrant',8);b=register('Initial B Entrant',12);lower=register('Lower Path Entrant',8)
    if include_continental:
        from braga_era.multiseason.continental_policy import ALLOCATIONS
        from braga_era.multiseason.continental_entry import POLICY as ENTRY,SULA_SLOTS
        national={'BRA':{'type':'legacy_league_and_cup'}}
        for country,n in ALLOCATIONS.items():
            if country=='BRA':continue
            clubs=[command('register_fictional_club_country',country=country,name=f'Fictional Integrated {country} Entrant {i:02}',strength=80-i*.8,dated='2028-01-01')['club'] for i in range(n+SULA_SLOTS[country])]
            national[country]={**scenario('Explicit foreign entry-order scenario; missing historical national results remain unknown'),'clubs':clubs}
        with connect_read_only(target/'database.sqlite') as c:champions=[{'competition':comp,'club':c.execute('SELECT club_key FROM world_champions WHERE competition=?',(comp,)).fetchone()[0],'evidence':{'type':'legacy_champion'}} for comp in ('LIB','SULA')]
        # SULA-only inherited identities sometimes lack country observations.
        # This is proposed forward identity evidence, never a historical repair.
        from ..world.rosters import alias
        declared={alias(name):country for country,names in {
            'ARG':['Argentinos Juniors','Defensa y Justicia','Huracán','Independiente','Lanús','Racing Club','San Lorenzo','Talleres'],
            'CHI':['Audax Italiano','Colo-Colo','Palestino','Universidad Católica','Universidad de Chile'],
            'COL':['América de Cali','Millonarios'],
            'ECU':['Barcelona SC','Emelec','Independiente del Valle','LDU Quito'],
            'PAR':['Cerro Porteño','Guaraní','Libertad','Olimpia'],
            'URU':['Defensor Sporting','Nacional (URU)','Peñarol']}.items() for name in names}
        for holder in champions:
            with connect_read_only(target/'database.sqlite') as c:
                from .continental_entry import country_of
                # Inspect native evidence so exact retries repeat the same op.
                row=c.execute('SELECT name,country FROM world_clubs WHERE key=?',(holder['club'],)).fetchone()
                from .competitions import brazilian
                missing=not row['country'] and not brazilian(c,holder['club'])
            if missing:
                country=declared.get(alias(row['name']))
                if not country:raise ValueError('Defending champion requires explicit forward country evidence: '+row['name'])
                command('declare_club_country',club=holder['club'],country=country,season=2028,
                        evidence=scenario('Forward club-country mapping proposal; inherited unknown country remains unchanged. Universidad Católica, if selected, denotes the Chilean club; this is an unapproved identity assumption.'))
        command('commit_continental_entry',season=2028,policy=ENTRY,national_evidence=national,champions=champions)
    offseason=None
    if with_offseason:
        from braga_era.multiseason.offseason import POLICY as OFFSEASON,development_economics
        command('install_offseason',policy=OFFSEASON)
        with connect_read_only(target/'database.sqlite') as c:
            original=c.execute("SELECT args_json FROM ms_operations WHERE kind='configure_offseason' ORDER BY sequence LIMIT 1").fetchone()
            economics=json.loads(original[0])['economics'] if original else development_economics(c,2028)
        command('configure_offseason',season=2028,dated='2028-01-01',policy=OFFSEASON,economics=economics)
        command('settle_economics',dated='2028-01-01 00:00:00')
        offseason=command('run_offseason',season=2028,dated='2028-01-01',policy=OFFSEASON)
        print('NONCANONICAL autonomous offseason',offseason,flush=True)
    command('propose_pool',id='initial-access',season=2028,competition='ACCESS',clubs=access,reason='Explicit prospective 2028 transition, not fabricated 2027 SÃ©rie B results')
    for key in access:command('qualify',season=2028,competition='ACCESS',club=key,source={'type':'proposed_pool','pool':'initial-access'})
    command('edition',competition='ACCESS',season=2028,format='qualification',clubs=access,rules={'legs':2,'final_legs':1,'neutral_final':False})
    with connect_read_only(target/'database.sqlite') as c:
        rio=['club:'+str(r[0]) for r in c.execute("SELECT id FROM clubs WHERE name IN ('Vasco','Flamengo','Fluminense','Botafogo') ORDER BY id")]
        venues = venue_bindings(c, rio_alternative)
    command('create_domestic_edition',season=2028,competition='CARIOCA',policy=DOMESTIC,entrants=[{'club':key,'phase':1,'source':scenario('Proposed RJ membership and fictional forward entrants, not claimed historical registration')} for key in rio+pool[:8]])
    for comp in ('SUPERCOPA','RECOPA'):command('create_supercup',season=2028,competition=comp,policy=DOMESTIC)
    calendar,windows=plans(2028,include_continental)
    for edition in calendar:venues['neutral:'+edition]='TEST proposed neutral final: '+edition
    command('commit_season_calendar',season=2028,policy=CALENDAR,plans=calendar,international_windows=windows,venues=venues)
    # Prior champions are already known: reserve their complete one/two-leg duty
    # before drawing state fixtures. Unknown future winners are never assigned.
    command('schedule',edition='SUPERCOPA:2028',start='2028-01-06 16:00',deadline='2028-01-06 16:00')
    command('schedule',edition='RECOPA:2028',start='2028-01-10 16:00',deadline='2028-01-17 16:00')
    for i in range(40):
        with connect_read_only(target/'database.sqlite') as c:
            done=c.execute("SELECT count(*) FROM ms_fixtures WHERE edition='ACCESS:2028' AND status='final'").fetchone()[0]
        if done==8:break
        advance_group(i)
    else:raise ValueError('Access transition failed to finish within bound')
    with connect_read_only(target/'database.sqlite') as c:closed=c.execute("SELECT state FROM ms_editions WHERE id='ACCESS:2028'").fetchone()[0]=='completed'
    if not closed:command('close_edition',edition='ACCESS:2028')
    with connect_read_only(target/'database.sqlite') as c:
        winners=[r[0] for r in c.execute("SELECT winner FROM ms_ties WHERE edition='ACCESS:2028' ORDER BY key")]
        from braga_era.world.adapters import recompute_standings
        table=recompute_standings(c,write=False)
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
    survivors=['club:'+str(k) for k in ranked[:16]]
    for pos,key in enumerate(survivors,1):command('qualify',season=2028,competition='LEAGUE',club=key,source={'type':'legacy_league_position','position':pos})
    for key in winners:command('qualify',season=2028,competition='LEAGUE',club=key,source={'type':'edition_qualifier','edition':'ACCESS:2028'})
    command('edition',competition='LEAGUE',season=2028,format='league',clubs=survivors+winners,rules={'legs':2,'final_legs':1,'neutral_final':False})
    losers=[k for k in access if k not in winners]
    command('register_divisions',season=2028,policy=DIVISIONS,initial_b=[{'club':k,'source':{'type':'access_eliminated','edition':'ACCESS:2028'}} for k in losers]+[{'club':k,'source':scenario('Initial missing 2027 SÃ©rie B admission; no past sporting result asserted')} for k in b],initial_lower=[{'club':k,'source':scenario('Bounded forward lower-division access registration')} for k in lower])
    early=b+losers+pool[16:]
    command('create_domestic_edition',season=2028,competition='CDB',policy=DOMESTIC,entrants=[{'club':k,'phase':1 if i<36 else 2 if i<102 else 3,'source':scenario('Unapproved missing 2027 state/regional qualification scenario')} for i,k in enumerate(early)]+[{'club':k,'phase':5,'source':{'type':'current_serie_a','edition':'LEAGUE:2028'}} for k in survivors+winners])
    return {"calendar":calendar,"offseason":offseason}


def align_future_midweeks(calendar, year, windows):
    """Assign competing late-season reservations to distinct legal league midweeks."""
    anchors = {}
    for competition in ('CDB','LIB','SULA'):
        for stage in calendar[f'{competition}:{year}']:
            if competition=='CDB' and stage['stage'] in {'C1','C2'}:
                continue
            for leg, values in stage['slots'].items():
                for index, value in enumerate(values):
                    category = 'domestic' if competition=='CDB' else 'continental'
                    anchors.setdefault((value,category), []).append((stage['slots'],leg,index))

    # Continental editions can share a round date because entry is mutually
    # exclusive at these stages. Domestic rounds need their own midweek.
    ordered = sorted(anchors)
    paths = {datetime(year,1,1): (0, ())}
    for value, category in ordered:
        nominal = datetime.fromisoformat(value)
        weekday = 2 if category=='domestic' else 3
        next_paths = {}
        for delta in range(-21,22):
            kickoff = nominal + timedelta(days=delta)
            when = kickoff.isoformat(sep=' ',timespec='minutes')
            if (kickoff.weekday()!=weekday or kickoff.year!=year
                    or not '01-05'<kickoff.strftime('%m-%d')<'12-22'
                    or any(first<=when<=last for first,last in windows)):
                continue
            choices = [(cost+abs(delta), path+(when,)) for previous,(cost,path) in paths.items()
                       if kickoff-previous>=timedelta(days=6)]
            if choices:
                next_paths[kickoff] = min(choices)
        if not next_paths:
            raise ValueError('No legal midweek reservation for '+value)
        paths = next_paths
    _, choices = min(paths.values())
    for anchor, when in zip(ordered,choices,strict=True):
        for slots, leg, index in anchors[anchor]:
            slots[leg][index] = when


def setup_following(target,command,year,*,rio_alternative=False,authentic=False):
    """Repeat the supported ecosystem from recorded prior-season outcomes.

    Foreign national order and missing federation inputs remain explicit forward
    administrative proposals. No historical national match score is created.
    """
    from .offseason import POLICY as OFFSEASON,development_economics
    from .continental_policy import ALLOCATIONS
    from .continental_entry import POLICY as ENTRY,SULA_SLOTS,country_of
    from .domestic import CONTINUITY_POLICY,final_order
    from .authentic import POLICY as AUTHENTIC, SCHEDULE, catalogue, order
    if authentic:
        command('install_authentic_catalogue',season=year,policy=AUTHENTIC)
        command('commit_balanced_venues',season=year,policy=SCHEDULE)
    with connect_read_only(target/'database.sqlite') as c:
        originals=[json.loads(r[0]) for r in c.execute("SELECT args_json FROM ms_operations WHERE kind='configure_offseason'")]
        original=next((r for r in originals if r['season']==year),None)
        # Admission governs competition eligibility. Existing clubs still owe
        # contractual wages, including after they leave the competitive pools.
        economics=original['economics'] if original else development_economics(c,year)
    command('configure_offseason',season=year,dated=f'{year}-01-01',policy=OFFSEASON,economics=economics)
    command('settle_economics',dated=f'{year}-01-01 00:00:00')
    result=command('run_offseason',season=year,dated=f'{year}-01-01',policy=OFFSEASON)
    command('carry_discipline',season=year,policy='carry-unserved-bans-reset-yellows-1')
    command('register_divisions',season=year,policy=AUTHENTIC if authentic else DIVISIONS,initial_b=[],initial_lower=[])
    command('carry_division_bans',season=year,policy='follow-national-division-bans-1')
    with connect_read_only(target/'database.sqlite') as c:
        national={'BRA':{'type':'edition_league_and_cup','edition':f'LEAGUE:{year-1}','cup_edition':f'CDB:{year-1}'}}
        for country,n in ALLOCATIONS.items():
            if country=='BRA':continue
            clubs=[r[0] for r in c.execute('SELECT key FROM world_clubs ORDER BY strength DESC,key') if country_of(c,r[0])==country]
            # Keep replacement depth when a titleholder also occupies a national
            # route. Truncating to the slot count loses its legitimate replacement.
            national[country]={**scenario('Forward country-entry ranking proposal from persistent club priors; no invented national league results'),'clubs':clubs[:40]}
        champions=[{'competition':comp,'club':c.execute('SELECT champion FROM ms_editions WHERE id=?',(f'{comp}:{year-1}',)).fetchone()[0],
                    'evidence':{'type':'edition_champion','edition':f'{comp}:{year-1}'}} for comp in ('LIB','SULA')]
        rio_order=final_order(c,c.execute('SELECT * FROM ms_editions WHERE id=?',(f'CARIOCA:{year-1}',)).fetchone())
        rio=rio_order
        league=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=? ORDER BY club',(f'LEAGUE:{year}',))]
        from .domestic import final_order
        prior_cup=c.execute('SELECT * FROM ms_editions WHERE id=?',(f'CDB:{year-1}',)).fetchone()
        # Explicit proposed federation replacement: prior cup sporting order,
        # excluding the twenty new direct entrants. No invented state results.
        cup_order=final_order(c,prior_cup)
        early=[club for club in cup_order if club not in league][:108]
        if authentic:
            registered=catalogue(c,year)
            national={country:{'type':'authentic_national_model'} for country in ALLOCATIONS}
            ranking=order(c,'BRA',year)
            rio=[club for club in rio_order if club in registered and registered[club]['state']=='RJ']
            rio+=(list(key for key in ranking if registered[key]['state']=='RJ' and key not in rio))[:12-len(rio)]
            early=[key for key in cup_order if key in registered and key not in league][:108]
            represented={registered[key]['state'] for key in league+early}
            for key in ranking:
                state=registered[key]['state']
                if len(early)<108 and state not in represented:
                    early.append(key)
                    represented.add(state)
            early += [key for key in ranking if key not in league and key not in early][:108-len(early)]
            if len(rio)!=12:raise ValueError('Insufficient eligible Rio clubs')
        if len(early)!=108:raise ValueError('Repeat CDB entry inventory needs an explicit federation decision')
        venues = venue_bindings(c, rio_alternative)
    command('commit_continental_entry',season=year,policy=ENTRY,national_evidence=national,champions=champions)
    command('create_domestic_edition',season=year,competition='CARIOCA',policy=AUTHENTIC if authentic else DOMESTIC,
            entrants=[{'club':club,'phase':1,'source':{'type':'edition_finish','edition':f'CARIOCA:{year-1}','position':rio_order.index(club)+1}
                       if club in rio_order else {'type':'authentic_federation_admission'}} for club in rio])
    command('create_domestic_edition',season=year,competition='CDB',policy=AUTHENTIC if authentic else CONTINUITY_POLICY,
            entrants=[{'club':club,'phase':1 if i<36 else 2 if i<102 else 3,'source':{'type':'prior_cup_repeat_berth','edition':f'CDB:{year-1}','position':cup_order.index(club)+1}
                       if club in cup_order else {'type':'authentic_federation_admission'}} for i,club in enumerate(early)]+
                     [{'club':club,'phase':5,'source':{'type':'current_serie_a','edition':f'LEAGUE:{year}'}} for club in league])
    for comp in ('SUPERCOPA','RECOPA'):command('create_supercup',season=year,competition=comp,policy=DOMESTIC)
    template,windows=plans(2028,True);calendar={}
    def shift(value):
        if isinstance(value,str):return str(year)+value[4:] if value.startswith('2028-') else value
        if isinstance(value,list):return [shift(x) for x in value]
        if isinstance(value,dict):return {k:shift(v) for k,v in value.items()}
        return value
    for edition,entries in template.items():
        if not edition.startswith('ACCESS:'):calendar[edition.replace(':2028',':'+str(year))]=shift(entries)
    national_plans,windows=plans(year)
    calendar.update(national_plans)
    if authentic and year>=2030:
        align_future_midweeks(calendar,year,windows)
    for edition in calendar:venues['neutral:'+edition]='TEST proposed neutral final: '+edition
    command('commit_season_calendar',season=year,policy=CALENDAR,plans=calendar,international_windows=windows,venues=venues)
    return {'calendar':calendar,'offseason':result}
