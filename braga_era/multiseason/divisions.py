"""Reusable sporting A/B exchange and bounded lower-division pathway.

The eight-club LOWER league is a proposed access ecosystem, not fictional past
Série C/D history. No new clubs are allocated automatically in later seasons.
"""
from ..history import canonical_json as encode
from .competitions import required,brazilian,edition,standings,qualification

POLICY='divisions-development-1'


def previous(c,competition,season):
    row=c.execute("SELECT * FROM ms_editions WHERE competition=? AND season=? AND state='completed' AND format='league'",(competition,season)).fetchone()
    if not row:raise ValueError('Completed previous division required: '+competition)
    return row,[r['club'] for r in standings(c,row['id'])]


def register(c,a):
    required(a,'season policy initial_b initial_lower')
    if a['policy']!=POLICY or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Preparing season and versioned division policy required')
    year=a['season'];routes={comp:[] for comp in ('LEAGUE','SERIE_B','LOWER')}
    if any(c.execute('SELECT 1 FROM ms_editions WHERE id=?',(f'{comp}:{year}',)).fetchone() for comp in ('SERIE_B','LOWER')):raise ValueError('Divisions already registered')
    def add(comp,key,source):
        if not brazilian(c,key):raise ValueError('Brazilian division entry lacks identity evidence')
        routes[comp].append((key,source))
    if year==2028:
        if not c.execute('SELECT 1 FROM ms_editions WHERE id=?',(f'LEAGUE:{year}',)).fetchone():raise ValueError('Initial Série A requires its existing recorded survival/access process first')
        if not isinstance(a['initial_b'],list) or len(a['initial_b'])!=16 or not isinstance(a['initial_lower'],list) or len(a['initial_lower'])!=8:raise ValueError('Initial missing-data scenario requires sixteen B admissions and eight lower clubs')
        from ..world.adapters import recompute_standings
        table=recompute_standings(c,write=False)
        if c.execute("SELECT count(*) FROM fixtures WHERE competition='Brasileirão 2027' AND status='final'").fetchone()[0]!=380:raise ValueError('2027 league is incomplete')
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
        for position,key in enumerate(ranked[16:],17):add('SERIE_B','club:'+str(key),{'type':'legacy_league_position','position':position})
        from .domestic import evidence
        for comp,entries in (('SERIE_B',a['initial_b']),('LOWER',a['initial_lower'])):
            for entry in entries:
                required(entry,'club source')
                if entry['source'].get('type')=='access_eliminated':
                    required(entry['source'],'type edition')
                    prior=c.execute("SELECT * FROM ms_editions WHERE id=? AND competition='ACCESS' AND state='completed'",(entry['source']['edition'],)).fetchone()
                    tie=c.execute('SELECT * FROM ms_ties WHERE edition=? AND (club_a=? OR club_b=?)',(entry['source']['edition'],entry['club'],entry['club'])).fetchone()
                    if comp!='SERIE_B' or not prior or prior['season']!=year or not tie or not tie['winner'] or tie['winner']==entry['club']:raise ValueError('Only actual transitional access losers may use this B route')
                else:evidence(c,year,comp,entry['club'],entry['source'])
                native=c.execute('SELECT source_id FROM world_clubs WHERE key=?',(entry['club'],)).fetchone()[0]
                if native is not None and c.execute('SELECT 1 FROM league_participants WHERE season=2027 AND club_id=?',(native,)).fetchone():raise ValueError('Initial admissions cannot reclassify a recorded 2027 Série A club')
                add(comp,entry['club'],entry['source'])
        existing_a=[r[0] for r in c.execute('SELECT club FROM ms_entries WHERE edition=?',(f'LEAGUE:{year}',))]
        routes['LEAGUE']=[(key,{'type':'already_registered_2028'}) for key in existing_a]
    else:
        if a['initial_b']!=[] or a['initial_lower']!=[]:raise ValueError('Later promotions require recorded outcomes, never another initial pool')
        old={comp:previous(c,comp,year-1) for comp in routes}
        for comp,(e,clubs) in old.items():
            for pos,key in enumerate(clubs,1):
                target=('LEAGUE' if pos<=16 else 'SERIE_B') if comp=='LEAGUE' else ('LEAGUE' if pos<=4 else 'SERIE_B' if pos<=16 else 'LOWER') if comp=='SERIE_B' else ('SERIE_B' if pos<=4 else 'LOWER')
                add(target,key,{'type':'edition_position','edition':e['id'],'position':pos})
    all_keys=[key for entries in routes.values() for key,_ in entries]
    if {comp:len(v) for comp,v in routes.items()}!={'LEAGUE':20,'SERIE_B':20,'LOWER':8} or len(set(all_keys))!=48:raise ValueError('Division entry collision or incomplete 20/20/8 inventory')
    for comp,entries in routes.items():
        if year==2028 and comp=='LEAGUE':continue
        for key,source in entries:
            if comp=='LEAGUE':qualification(c,{'season':year,'competition':comp,'club':key,'source':source})
            else:
                provenance={'type':'division_entry','policy':POLICY,'sporting_source':source}
                c.execute('INSERT INTO ms_qualifications VALUES(?,?,?,?,?)',(f'{comp}:{year}:{key}',year,comp,key,encode(provenance)))
        edition(c,{'competition':comp,'season':year,'format':'league','clubs':[key for key,_ in entries],'rules':{'legs':2,'final_legs':1,'neutral_final':False}})
    return {'season':year,'policy':POLICY,'divisions':{comp:[key for key,_ in entries] for comp,entries in routes.items()},'initial_admissions_proposed':year==2028,'new_clubs_created':False,'test_only':True}


def carry_bans(c,a):
    """Explicit alternative: unserved national bans follow division movement."""
    import json
    required(a,'season policy')
    if a['policy']!='follow-national-division-bans-1' or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Explicit future national suspension policy required')
    if any(json.loads(r[0])['season']==a['season'] for r in c.execute("SELECT args_json FROM ms_operations WHERE kind='carry_division_bans'")):raise ValueError('Division disciplinary transition already consumed')
    if c.execute("SELECT 1 FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture JOIN ms_editions e ON e.id=f.edition WHERE e.season=? AND e.competition IN ('LEAGUE','SERIE_B','LOWER')",(a['season'],)).fetchone():raise ValueError('Carry division sanctions before the first national execution commitment')
    destinations={r['club']:r['competition'] for r in c.execute("SELECT x.club,e.competition FROM ms_entries x JOIN ms_editions e ON e.id=x.edition WHERE e.season=? AND e.competition IN ('LEAGUE','SERIE_B','LOWER')",(a['season'],))}
    if len(destinations)!=48:raise ValueError('Register all three future divisions before carrying bans')
    carried={}
    for row in c.execute('SELECT d.*,p.club_key FROM world_discipline d JOIN world_players p ON p.id=d.player_id WHERE d.bans>0 ORDER BY d.player_id,d.competition'):
        previous=row['competition']
        eligible=(a['season']==2028 and previous in {'LEAGUE','SERIE_B','LOWER'} or previous in {f'{comp}:{a["season"]-1}' for comp in ('LEAGUE','SERIE_B','LOWER')})
        if eligible and row['club_key'] in destinations:
            key=(row['player_id'],destinations[row['club_key']]);carried[key]=carried.get(key,0)+row['bans']
    for (pid,comp),bans in sorted(carried.items()):
        for old in ('LEAGUE','SERIE_B','LOWER'):c.execute('UPDATE world_discipline SET bans=0 WHERE player_id=? AND competition=?',(pid,f'{old}:{a["season"]}'))
        c.execute('INSERT OR REPLACE INTO world_discipline VALUES(?,?,0,?)',(pid,f'{comp}:{a["season"]}',bans))
    return {'season':a['season'],'policy':a['policy'],'players':len(carried),'unserved_bans':sum(carried.values()),'historical_counters_preserved':True,'canonical_approval':False}
