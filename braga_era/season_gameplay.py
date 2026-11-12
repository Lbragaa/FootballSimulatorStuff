"""Edition-aware views over accepted profile-3 snapshots and existing cursors."""
from dataclasses import asdict
import json
from functools import lru_cache

from . import lineage
from .db import connect_read_only,file_sha256
from .history import digest, canonical_json as encode
from .multiseason.agenda import event_from_connection
from .multiseason.competitions import standings


@lru_cache(maxsize=2)
def _event_counts(database,authenticated_file_sha256):
    # Pure projection of immutable bytes, never a cached validation verdict or
    # cursor. Callers still authenticate the accepted head and file every time.
    with connect_read_only(database) as db:
        return tuple((r['fixture'],r['n']) for r in db.execute("SELECT fixture,json_array_length(result_json,'$.events') AS n FROM ms_executions WHERE result_json IS NOT NULL"))


def unrevealed(c, database, authenticated_sha256=None):
    cursors={r['fixture']:r['sequence'] for r in c.execute('SELECT * FROM cursors')}
    identity = authenticated_sha256 or file_sha256(database)
    return [fixture for fixture,n in _event_counts(str(database),identity) if cursors.get(fixture,0)<n]


def _unrevealed(c, info):
    return set(unrevealed(c, info['database'], info.get('metadata', {}).get('database_sha256')))


def next_events(c,info,*,pending=None):
    if pending is None:
        pending = _unrevealed(c, info)
    with connect_read_only(info['database']) as db:
        rows=[dict(r) for r in db.execute('SELECT f.*,e.competition,e.season FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition ORDER BY kickoff,key') if r['key'] in pending]
        if rows:
            first=rows[0]['kickoff']
            return [{'key':r['key'],'kind':'narration','kickoff':r['kickoff'],'home':r['home'],'away':r['away'],
                     'competition':r['competition'],'season':r['season']} for r in rows if r['kickoff']==first]
        event=event_from_connection(db)
        if not event:return []
        if event['kind']=='match_group':
            return [{'key':r['key'],'kind':'match','kickoff':r['kickoff'],'home':r['home'],'away':r['away'],
                     'competition':r['competition'],'season':r['season']} for r in db.execute(
                'SELECT f.*,e.competition,e.season FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE kickoff=? ORDER BY key',(event['kickoff'],))]
        return [{'key':event.get('edition',event['kind'])+':'+event['kickoff'],'kind':event['kind'],'kickoff':event['kickoff']}]


def table(c,info,edition=None):
    with connect_read_only(info['database']) as db:
        edition=edition or f'LEAGUE:{info["season"]}'
        e=db.execute('SELECT * FROM ms_editions WHERE id=?',(edition,)).fetchone()
        if not e:raise ValueError('Competition edition is not established')
        waiting=_unrevealed(c,info)
        if any(r[0] in waiting for r in db.execute('SELECT key FROM ms_fixtures WHERE edition=?',(edition,))):
            raise ValueError('Reveal this competition round before its standings')
        names=dict(db.execute('SELECT key,name FROM world_clubs'))
        return {'season':e['season'],'edition':edition,'standings':[
            {**r,'id':r['club'],'name':names[r['club']]} for r in standings(db,edition)]}


def review(info):
    """Called only after authenticated closure and fully revealed season results."""
    with connect_read_only(info['database']) as db:
        row=db.execute('SELECT state,archive_json FROM ms_seasons WHERE season=?',(info['season'],)).fetchone()
        if not row or row['state']!='archived':raise ValueError('Archived season required for final review')
        archive=json.loads(row['archive_json']);names=dict(db.execute('SELECT key,name FROM world_clubs'))
        players={r['id']:json.loads(r['attributes_json'])['name'] for r in db.execute('SELECT id,attributes_json FROM world_players')}
        totals={}
        for raw in db.execute('SELECT x.result_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture JOIN ms_editions e ON e.id=f.edition WHERE e.season=?',(info['season'],)):
            for p in json.loads(raw[0])['performances']:
                if not p['seconds_played']:continue
                item=totals.setdefault(p['player_id'],{'player':p['player_id'],'name':players[p['player_id']],'appearances':0,'goals':0,'assists':0,'seconds_played':0})
                for key in ('goals','assists','seconds_played'):item[key]+=p[key]
                item['appearances']+=1
        return {'season':info['season'],'complete':True,'source_checkpoint':info['checkpoint'],
                'tables':{edition:[{**r,'name':names[r['club']]} for r in rows] for edition,rows in archive['standings'].items()},
                'trophies':[{'competition':e['competition'],'club':e['champion'],'name':names[e['champion']]} for e in archive['editions'] if e['champion'] is not None],
                'top_scorers':sorted(totals.values(),key=lambda p:(-p['goals'],-p['assists'],p['seconds_played'],p['player']))[:10],
                'vasco_finances':next(({k:v for k,v in r.items() if k!='provenance_json'} for r in archive['finances'] if r['club']=='club:15'),None),
                'economics_note':'Recorded ledger under the authorized season policy; no unknown revenue inferred.'}


def preview(db,fixture):
    f=db.execute('SELECT * FROM ms_fixtures WHERE key=?',(fixture,)).fetchone()
    if not f:raise ValueError('Unknown edition fixture')
    names=dict(db.execute('SELECT key,name FROM world_clubs'))
    result={'fixture_key':fixture,'home':names[f['home']],'away':names[f['away']],
            'kickoff':f['kickoff'],'lineups_available':False,'lineups':[],'postmatch_available':False}
    row=db.execute('SELECT input_json,seed_json,config_json FROM ms_executions WHERE fixture=?',(fixture,)).fetchone()
    if row:
        from .world.codec import snapshot
        from .world.forward_config import load
        from .world.policy import ReadinessPolicy
        from .engine.models import SeedCommitment
        from .engine.coaches import prepare
        data=json.loads(row['input_json']);snap=snapshot(data['snapshot'])
        plans=prepare(snap,load(json.loads(row['config_json']),ReadinessPolicy(),data['neutral']),SeedCommitment(**json.loads(row['seed_json'])))
        for plan in plans:
            team=snap.home if plan.club_key==snap.home.key else snap.away
            people={p.id:p.name for p in team.players}
            result['lineups'].append({'club_key':plan.club_key,'coach':plan.coach,'formation':plan.formation,
                'defensive_shape':plan.defensive_shape,'risk':plan.risk,'rationale':list(plan.rationale),
                'starters':[{'id':i,'name':people[i]} for i in plan.starters],
                'bench':[{'id':i,'name':people[i]} for i in plan.bench]})
        result['lineups_available']=True
    return result


def gameplay(c,t,key,parent,command,fixture,count,page_id):
    from .season_lineage import parent_info
    info=parent_info(c,t,key,parent)
    if command=='next':return {'events':next_events(c,info)}
    if command=='table':return table(c,info)
    if command=='finances':
        with connect_read_only(info['database']) as db:
            row=db.execute("SELECT * FROM ms_accounts WHERE club='club:15'").fetchone()
            wages=db.execute("SELECT coalesce(sum(wage_cents),0)*12 FROM ms_contracts WHERE club='club:15' AND status='active'").fetchone()[0]
            return {'restricted_cash_cents':row['cash_cents'] if row else None,'accrued_unpaid_cents':None,
                    'annual_incremental_commitments_cents':wages,'account_unknown':row is None}
    request={'command':command,'fixture':fixture,'count':count}
    if page_id:
        old=c.execute('SELECT * FROM narration_pages WHERE id=?',(page_id,)).fetchone()
        if old:
            response=json.loads(old['response'])
            if old['request_sha']!=digest(request) or old['signature']!=lineage.sign(key,lineage.page_statement(page_id,old['checkpoint'],old['request_sha'],response,t)):
                raise ValueError('Narration page binding changed')
            return response
    eligible={r['key'] for r in next_events(c,info)}
    if fixture not in eligible:raise ValueError('Earlier chronology/narration first')
    with connect_read_only(info['database']) as db:
        if command=='preview':return preview(db,fixture)
        if command!='narrate' or not page_id or type(count) is not int or not 1<=count<=20:
            raise ValueError('Bounded narration with stable page ID required')
        row=db.execute('SELECT * FROM ms_executions WHERE fixture=?',(fixture,)).fetchone()
        if not row or row['result_json'] is None:raise ValueError('No accepted result to narrate')
        bundle=json.loads(row['result_json'])
        if digest(bundle)!=row['result_sha256']:raise ValueError('Accepted result differs')
        cursor=c.execute('SELECT * FROM cursors WHERE fixture=?',(fixture,)).fetchone()
        offset=cursor['sequence'] if cursor else 0
        if cursor and cursor['result_sha']!=row['result_sha256']:raise ValueError('Result-bound cursor differs')
        events=bundle['events'][offset:offset+count];end=offset+len(events)
        response={'fixture_key':fixture,'events':events,'postmatch_available':end==len(bundle['events']),
                  'accepted_checkpoint':info['checkpoint'],'test_only':bool(t['test_only'])}
        if response['postmatch_available']:response['postmatch_summary']={'score':bundle['score'],'resolution':bundle['resolution']}
    _commit_page(c, t, key, fixture, row['result_sha256'], end, page_id, digest(request), response)
    return response


def _commit_page(c, t, key, fixture, result_sha, end, page_id, request_sha, response):
    c.execute('BEGIN IMMEDIATE')
    try:
        c.execute('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',(fixture,result_sha,end))
        c.execute('UPDATE cursor_revision SET revision=revision+1');lineage.seal_cursors(c,t,key)
        checkpoint = response['accepted_checkpoint']
        c.execute('INSERT INTO narration_pages VALUES(?,?,?,?,?)',(page_id,checkpoint,request_sha,encode(response),
                  lineage.sign(key,lineage.page_statement(page_id,checkpoint,request_sha,response,t))))
        c.commit()
    except BaseException:c.rollback();raise


def state(c,info,*,hidden=None):
    with connect_read_only(info['database']) as db:
        names=dict(db.execute('SELECT key,name FROM world_clubs'))
        rows=[dict(r) for r in db.execute("""SELECT f.*,e.competition,e.season,e.format,
            json_extract(x.result_json,'$.resolution') AS resolution_json
            FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition
            LEFT JOIN ms_executions x ON x.fixture=f.key AND f.tie_key IS NOT NULL
            WHERE e.season=? ORDER BY kickoff,key""",(info['season'],))]
        fixtures=[{**r,'stage':'R'+str(r['round']) if r['competition']=='LEAGUE' else r['stage']} for r in rows]
        ties=[]
        for t in db.execute('SELECT t.*,e.competition FROM ms_ties t JOIN ms_editions e ON e.id=t.edition WHERE e.season=?',(info['season'],)):
            legs=[r for r in rows if r['tie_key']==t['key']];aggregates=[0,0]
            for leg in legs:
                if leg['status']=='final':
                    for i,club in enumerate((t['club_a'],t['club_b'])):aggregates[i]+=leg['home_goals'] if leg['home']==club else leg['away_goals']
            ties.append({**dict(t),'stage':legs[0]['stage'] if legs else str(t['stage']),
                         'status':'final' if t['winner'] else 'scheduled','aggregate_a':aggregates[0],'aggregate_b':aggregates[1]})
        league=[{**r,'id':r['club']} for r in standings(db,f'LEAGUE:{info["season"]}')]
        champions=[{'competition':r['competition'],'club_key':r['champion']} for r in db.execute(
            "SELECT * FROM ms_editions WHERE season=? AND state='completed' AND champion IS NOT NULL",(info['season'],))]
    if hidden is None:
        hidden = _unrevealed(c, info)
    return {'fixtures':fixtures,'ties':ties,'draws':[],'names':names,'league':league,'champions':champions,
            'revealed':[r['key'] for r in rows if r['status']=='final' and r['key'] not in hidden]}


def episode_view(registry, key):
    """Compute state and agenda under one authenticated, locked parent read."""
    from .season_lineage import current
    with lineage.access(registry, key, True) as (c, trusted):
        lineage.check_cursors(c, trusted, key)
        info, _ = current(c, trusted, key)
        hidden = _unrevealed(c, info)
        return state(c, info, hidden=hidden), next_events(c, info, pending=hidden)


def finish_background(registry, key, checkpoint, fixture, page_id):
    """Record one signed final cursor for an already accepted background match."""
    from .season_lineage import current

    request = {'command': 'finish_background', 'fixture': fixture, 'checkpoint': checkpoint}
    request_sha = digest(request)
    with lineage.access(registry, key, True) as (c, trusted):
        lineage.check_cursors(c, trusted, key)
        cached = c.execute('SELECT * FROM narration_pages WHERE id=?', (page_id,)).fetchone()
        if cached:
            response = json.loads(cached['response'])
            statement = lineage.page_statement(page_id, cached['checkpoint'], request_sha, response, trusted)
            if (cached['checkpoint'] != checkpoint or cached['request_sha'] != request_sha
                    or cached['signature'] != lineage.sign(key, statement)):
                raise ValueError('Background narration page binding changed')
            return response
        if trusted['head'] != checkpoint:
            raise ValueError('Background narration parent changed')
        info, _ = current(c, trusted, key)
        eligible = next((r for r in next_events(c, info)
                         if r['key'] == fixture and r['kind'] == 'narration'), None)
        if eligible is None or 'club:15' in (eligible['home'], eligible['away']):
            raise ValueError('Background narration requires an eligible non-Vasco result')
        with connect_read_only(info['database']) as db:
            row = db.execute('SELECT result_json,result_sha256 FROM ms_executions WHERE fixture=?', (fixture,)).fetchone()
        bundle = json.loads(row['result_json'])
        if digest(bundle) != row['result_sha256']:
            raise ValueError('Accepted result differs')
        end = len(bundle['events'])
        cursor = c.execute('SELECT * FROM cursors WHERE fixture=?', (fixture,)).fetchone()
        if cursor and (cursor['result_sha'] != row['result_sha256'] or not 0 <= cursor['sequence'] < end):
            raise ValueError('Result-bound cursor differs')
        if not end or bundle['events'][-1]['kind'] != 'FINAL_WHISTLE':
            raise ValueError('Background result lacks a final whistle')
        response = {'fixture_key': fixture, 'accepted_checkpoint': checkpoint, 'events': [],
                    'postmatch_available': True, 'test_only': bool(trusted['test_only']),
                    'consumed_from': cursor['sequence'] if cursor else 0, 'consumed_to': end,
                    'result_sha256': row['result_sha256']}
        _commit_page(c, trusted, key, fixture, row['result_sha256'], end, page_id, request_sha, response)
        return response


def offseason_news(career,request_id):
    from .season_lineage import current
    with lineage.access(career.registry,career.key,True) as (c,t):
        info,_=current(c,t,career.key);year=info['season'];page_id=f'season-news:{year}'
        request_sha=digest({'kind':'offseason_news','season':year,'episode':request_id})
        old=c.execute('SELECT * FROM narration_pages WHERE id=?',(page_id,)).fetchone()
        if old:
            response=json.loads(old['response'])
            if old['signature']!=lineage.sign(career.key,lineage.page_statement(page_id,old['checkpoint'],old['request_sha'],response,t)):
                raise ValueError('Offseason delivery signature differs')
            return response if old['request_sha']==request_sha else None
        with connect_read_only(info['database']) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='ms_offseasons'").fetchone():return None
            row=db.execute('SELECT * FROM ms_offseasons WHERE season=?',(year,)).fetchone()
            if not row or row['state']!='registered':return None
            summary=json.loads(row['summary_json'])
            names=dict(db.execute('SELECT key,name FROM world_clubs'))
            players={r['id']:json.loads(r['attributes_json'])['name'] for r in db.execute('SELECT id,attributes_json FROM world_players')}
            if year>=2029:
                from .multiseason.authentic import display_names
                players.update({int(pid): entry['name'] for pid,entry in display_names(db,year).items()})
            changes=[{'player':players[r['player']],'from':names.get(r['seller']),'to':names.get(r['buyer']),
                      'kind':r['kind'],'dated':r['dated'],'source_id':r['id']}
                     for r in db.execute("SELECT * FROM ms_transfers WHERE substr(dated,1,4)=? AND (seller='club:15' OR buyer='club:15') ORDER BY dated,id",(str(year),))]
        response={'section':'offseason','season':year,'dated':row['dated'],'vasco_changes':changes,
                  'world_summary':{k:v for k,v in summary.items() if type(v) is int},
                  'manager':'Luan Braga remains autonomous; all changes are recorded decisions.'}
        c.execute('BEGIN IMMEDIATE')
        try:
            c.execute('INSERT INTO narration_pages VALUES(?,?,?,?,?)',(page_id,info['checkpoint'],request_sha,encode(response),
                      lineage.sign(career.key,lineage.page_statement(page_id,info['checkpoint'],request_sha,response,t))))
            c.commit()
        except BaseException:c.rollback();raise
        return response
