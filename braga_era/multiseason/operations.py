"""Closed command dispatch. No shell, supplied Python or remote paths."""
import json
from ..history import canonical_json as encode,digest
from .competitions import required,club,qualification,edition,schedule,close_edition,standings,COMPETITIONS


def apply(c,kind,a):
    if kind=='begin_run':
        required(a,'id max_groups')
        from uuid import UUID
        if str(UUID(a['id']))!=a['id'] or type(a['max_groups']) is not int or not 1<=a['max_groups']<=100:raise ValueError('Invalid bounded run identity')
        if c.execute('SELECT 1 FROM ms_runs WHERE response_json IS NULL').fetchone():raise ValueError('Resume the active chronological run')
        c.execute('INSERT INTO ms_runs VALUES(?,?,NULL)',(a['id'],a['max_groups']))
        return {'run':a['id'],'max_groups':a['max_groups']}
    if kind=='finish_run':
        required(a,'id')
        from .agenda import event_from_connection,completed_groups
        row=c.execute('SELECT * FROM ms_runs WHERE id=?',(a['id'],)).fetchone()
        if not row or row['response_json'] is not None:raise ValueError('Missing active run')
        response={'test_only':True,'groups_completed':completed_groups(c,a['id']),'next_event':event_from_connection(c)}
        c.execute('UPDATE ms_runs SET response_json=? WHERE id=?',(encode(response),a['id']))
        return response
    if kind=='prepare_season':
        required(a,'season')
        previous=c.execute('SELECT * FROM ms_seasons ORDER BY season DESC LIMIT 1').fetchone()
        if type(a['season']) is not int or a['season']!=previous['season']+1 or previous['state']!='archived':
            raise ValueError('Exact next season requires archived predecessor')
        c.execute("INSERT INTO ms_seasons VALUES(?,'preparing',NULL)",(a['season'],))
        return {'season':a['season'],'state':'preparing','official_activation':False}
    if kind in {'register_fictional_club','register_fictional_club_country'}:
        required(a,'name strength dated' if kind=='register_fictional_club' else 'name strength dated country')
        country=a.get('country','BRA')
        from .continental_policy import ALLOCATIONS
        if not isinstance(country,str) or country not in ALLOCATIONS:raise ValueError('Explicit supported fictional club country required')
        from .market import advance_time
        from ..world.rosters import alias,modeled_squad
        from ..world.policy import WorldPolicy
        from dataclasses import asdict
        if not isinstance(a['name'],str) or not a['name'].startswith('Fictional ') or not 10<=len(a['name'])<=80 or type(a['strength']) not in (int,float) or not 50<=a['strength']<=80:
            raise ValueError('Explicit fictional identity and bounded strength prior required')
        advance_time(c,a['dated']+' 00:00:00')
        key='modeled-ms:'+digest({'name':alias(a['name']),'country':country})[:16]
        provenance={'source':'proposed forward fictional access-club registration','effective':a['dated'],'canonical':False,'wages':'unknown; not asserted as zero','roster_policy':'fictional-squads-1.0.0'}
        if country!='BRA':provenance={**provenance,'source':'proposed forward fictional international-club registration','country':country}
        c.execute('INSERT INTO world_clubs VALUES(?,?,?,?,?,?,?,?)',(key,a['name'],alias(a['name']),None,country,a['strength'],0,encode(provenance)))
        for p in modeled_squad(key,a['name'],a['strength'],WorldPolicy()):
            c.execute('INSERT INTO world_players VALUES(?,?,?,?,?,?)',(p.id,key,None,1,encode(asdict(p)),encode(provenance)))
            state={'fitness':p.fitness,'morale':p.morale,'form':p.form,'observed_at':a['dated']+' 00:00:00','last_played':None,
                   'injury_until':None,'injury_unknown':False,'registered':True,'contract_start':a['dated'],'contract_end':a['dated'][:4]+'-12-31','recent':[]}
            c.execute('INSERT INTO world_player_state VALUES(?,?)',(p.id,encode(state)))
        return {'club':key,'name':a['name'],'fictional':True,'provenance':provenance}
    if kind=='propose_pool':
        required(a,'id season competition clubs reason')
        if a['competition'] not in COMPETITIONS or not isinstance(a['reason'],str) or not a['reason'].strip():raise ValueError('Explicit proposed qualification policy required')
        if not isinstance(a['clubs'],list) or not a['clubs'] or len(set(a['clubs']))!=len(a['clubs']):raise ValueError('Duplicate or empty proposed club pool')
        for k in a['clubs']:
            club(c,k)
            if a['competition'] in {'ACCESS','SERIE_B'}:
                from .competitions import brazilian
                source=c.execute('SELECT source_id FROM world_clubs WHERE key=?',(k,)).fetchone()[0]
                if not brazilian(c,k) or source is not None and c.execute('SELECT 1 FROM league_participants WHERE season=2027 AND club_id=?',(source,)).fetchone():
                    raise ValueError('A proposed lower-division pool cannot invent nationality or reclassify known 2027 Série A clubs')
        c.execute('INSERT INTO ms_pools VALUES(?,?,?,?,?)',(a['id'],a['season'],a['competition'],encode(sorted(a['clubs'])),a['reason']))
        return {'pool':a['id'],'proposed':True,'historical_results_created':False}
    if kind=='qualify':return qualification(c,a)
    if kind=='commit_continental_entry':
        from .continental_entry import commit
        return commit(c,a)
    if kind=='edition':return edition(c,a)
    if kind=='schedule':return schedule(c,a)
    if kind=='schedule_country_groups':
        required(a,'edition start deadline')
        from .continental_policy import draw
        from .competitions import insert_fixture
        from ..seasons import double_round_robin
        from datetime import datetime,timedelta
        e=c.execute('SELECT * FROM ms_editions WHERE id=?',(a['edition'],)).fetchone()
        if not e or e['state']!='planned' or e['format'] not in {'groups_knockout','sula_cross_playoffs'}:raise ValueError('Unscheduled continental main stage required')
        entries=c.execute('SELECT x.*,w.country,w.strength FROM ms_entries x JOIN world_clubs w ON w.key=x.club WHERE x.edition=? ORDER BY w.strength DESC,x.club',(e['id'],)).fetchall()
        if len(entries)!=32 or any(not r['country'] for r in entries):raise ValueError('32 entries with recorded countries required; unknown nationality cannot be invented')
        pots=[[r['club'] for r in entries[i:i+8]] for i in range(0,32,8)]
        countries={r['club']:r['country'] for r in entries};exceptions=[]
        for r in entries:
            source=json.loads(r['evidence_json'])
            if source.get('type')=='edition_qualifier':
                parent=c.execute('SELECT competition FROM ms_editions WHERE id=?',(source['edition'],)).fetchone()
                if parent and parent[0]=='LIB_PRE3':exceptions.append(r['club'])
        seed=c.execute('SELECT seed FROM ms_meta').fetchone()[0]
        groups=draw(pots,countries,seed,preliminary_exceptions=exceptions)
        for name,clubs in groups.items():
            for f in double_round_robin(clubs,season=e['season'],competition=e['competition']):
                when=(datetime.fromisoformat(a['start'])+timedelta(days=7*(f['round']-1))).isoformat(sep=' ',timespec='minutes')
                insert_fixture(c,e['id'],name,f['round'],None,f['home'],f['away'],when,a['deadline'])
        c.execute("UPDATE ms_editions SET state='active' WHERE id=?",(e['id'],))
        return {'edition':e['id'],'policy':'country-pots-1','groups':groups,'preliminary_exceptions':exceptions,'scheduled':96}
    if kind=='claim_group':
        from .execution import claim
        return claim(c,a)
    if kind=='play_group':
        from .execution import play
        return play(c,a)
    if kind=='close_edition':return close_edition(c,a)
    if kind=='archive_season':
        required(a,'season required_competitions')
        if not isinstance(a['required_competitions'],list) or not a['required_competitions'] or len(set(a['required_competitions']))!=len(a['required_competitions']):raise ValueError('Complete required competition inventory needed')
        season=c.execute("SELECT * FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone()
        editions=[dict(r) for r in c.execute('SELECT * FROM ms_editions WHERE season=? ORDER BY id',(a['season'],))]
        if not season or {r['competition'] for r in editions}!=set(a['required_competitions']) or any(r['state']!='completed' for r in editions):
            raise ValueError('Required competition editions are missing or incomplete')
        # Known contract-backed wages must be booked through every due month.
        from .market import unpaid_periods
        missing=unpaid_periods(c,a['season'])
        if missing:raise ValueError('Contract-backed payroll periods not settled: '+','.join(missing))
        if c.execute("SELECT 1 FROM ms_income WHERE substr(due,1,4)=? AND status!='applied'",(str(a['season']),)).fetchone():raise ValueError('Proposed financial obligations remain pending')
        snapshot={'editions':editions,'standings':{r['id']:standings(c,r['id']) for r in editions if r['format']=='league'},
                  'contracts':[dict(r) for r in c.execute('SELECT * FROM ms_contracts ORDER BY id')],
                  'finances':[dict(r) for r in c.execute('SELECT * FROM ms_accounts ORDER BY club')],
                  'player_state_sha256':digest([tuple(r) for r in c.execute('SELECT * FROM world_player_state ORDER BY player_id')]),
                  'note':'All historical fixtures/events/contracts/transfers remain in the inherited database and append-only edition tables.'}
        c.execute("UPDATE ms_seasons SET state='archived',archive_json=? WHERE season=?",(encode(snapshot),a['season']))
        return {'season':a['season'],'state':'archived','archive_sha256':digest(snapshot)}
    if kind=='continue_modeled_registrations':
        required(a,'season')
        if not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('No preparing registration season')
        changed=0
        for p in c.execute('SELECT id FROM world_players WHERE modeled=1 ORDER BY id').fetchall():
            state=json.loads(c.execute('SELECT state_json FROM world_player_state WHERE player_id=?',(p['id'],)).fetchone()[0])
            if state['contract_end'] and state['contract_end']<f"{a['season']}-01-01":
                state['contract_end']=f"{a['season']}-12-31"
                c.execute('UPDATE world_player_state SET state_json=? WHERE player_id=?',(encode(state),p['id']));changed+=1
        return {'season':a['season'],'modelled_registrations_continued':changed,'assumption':'PROPOSED: artificial modeled registration prior continued; real wages and actual contract terms remain unknown','canonical_approval':False}
    if kind=='carry_discipline':
        required(a,'season policy')
        if a['policy']!='carry-unserved-bans-reset-yellows-1' or not c.execute("SELECT 1 FROM ms_seasons WHERE season=? AND state='preparing'",(a['season'],)).fetchone():raise ValueError('Explicit proposed discipline transition required')
        if c.execute("SELECT 1 FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE e.season=? AND f.status!='scheduled'",(a['season'],)).fetchone():raise ValueError('Carry sanctions before first execution commitment')
        if any(json.loads(r[0])['season']==a['season'] for r in c.execute("SELECT args_json FROM ms_operations WHERE kind='carry_discipline'")):
            raise ValueError('Disciplinary transition already consumed')
        carried=0
        for row in c.execute('SELECT * FROM world_discipline WHERE bans>0 ORDER BY player_id,competition').fetchall():
            if a['season']==2028 and row['competition'] in COMPETITIONS:comp=row['competition']
            elif row['competition'].endswith(':'+str(a['season']-1)):comp=row['competition'].rsplit(':',1)[0]
            else:continue
            c.execute('INSERT INTO world_discipline VALUES(?,?,0,?)',(row['player_id'],f"{comp}:{a['season']}",row['bans']));carried+=1
        return {'season':a['season'],'unserved_bans_carried':carried,'yellow_accumulation':'new edition starts at zero','policy':a['policy'],'canonical_approval':False}
    if kind in {'open_recorded_account','renew_contract','purchase','loan','return_loan','pay_month','evolve','autonomous_recruitment','propose_income','receive_income'}:
        from .market import apply as market
        return market(c,kind,a)
    raise ValueError('Unsupported multi-season operation')
