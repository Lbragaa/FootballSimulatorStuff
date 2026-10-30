"""Precommitted simultaneous groups using the unchanged engine and ET validator."""
from dataclasses import asdict
from datetime import datetime,timedelta
import json
from ..engine.models import Snapshot,CompetitionRules,SeedCommitment
from ..engine.randomness import commit_seeds
from ..engine.coaches import prepare
from ..engine.match import simulate_match
from ..history import canonical_json as encode,digest
from ..world.players import team_at,apply_players
from ..world.policy import ReadinessPolicy,Rules
from ..world.forward_config import configuration,load
from ..world.codec import snapshot as decode_snapshot
from ..world.knockout_v2 import resolve,validate_bundle
from .competitions import required


def claim(c,a):
    required(a,'kickoff')
    first=c.execute("SELECT min(kickoff) FROM ms_fixtures WHERE status!='final'").fetchone()[0]
    if a['kickoff']!=first:raise ValueError('Only the earliest unresolved chronological group can be claimed')
    rows=c.execute("SELECT * FROM ms_fixtures WHERE kickoff=? AND status='scheduled' ORDER BY key",(first,)).fetchall()
    if not rows:raise ValueError('Group already claimed; resume the original execution')
    clubs=[f[k] for f in rows for k in ('home','away')]
    if len(set(clubs))!=len(clubs):raise ValueError('Simultaneous club collision')
    meta=c.execute('SELECT * FROM ms_meta').fetchone()
    from .market import next_obligation
    obligation=next_obligation(c)
    if obligation and obligation['kickoff']<=first:raise ValueError('Earlier payroll/loan obligation must be processed first')
    if first<=meta['clock']:raise ValueError('Kickoff predates committed completion state')
    if c.execute("SELECT 1 FROM ms_fixtures WHERE status='claimed' LIMIT 1").fetchone():raise ValueError('Resume the committed group first')
    policy=ReadinessPolicy()
    common=digest({'players':[tuple(r) for r in c.execute('SELECT * FROM world_player_state ORDER BY player_id')],
                   'discipline':[tuple(r) for r in c.execute('SELECT * FROM world_discipline ORDER BY player_id,competition')],
                   'clock':meta['clock'],'parent':meta['parent_sha256']})
    for f in rows:
        e=c.execute('SELECT * FROM ms_editions WHERE id=?',(f['edition'],)).fetchone()
        rules=json.loads(e['rules_json']);decisive=False;prior=[0,0];single=False
        if f['tie_key']:
            legs=c.execute('SELECT * FROM ms_fixtures WHERE tie_key=? ORDER BY round',(f['tie_key'],)).fetchall()
            decisive=f['round']==max(g['round'] for g in legs)
            if decisive:
                for g in legs:
                    if g['key']!=f['key']:
                        if g['status']!='final':raise ValueError('Earlier leg not completed')
                        prior[0]+=g['home_goals'] if g['home']==f['home'] else g['away_goals']
                        prior[1]+=g['away_goals'] if g['away']==f['away'] else g['home_goals']
            single=len(legs)==1
        config=configuration(policy,final=bool(single and rules['neutral_final']))
        snap=Snapshot(f['key'],f['kickoff'],meta['clock'],team_at(c,f['home'],e['id'],first,policy),
            team_at(c,f['away'],e['id'],first,policy),CompetitionRules(e['competition'],e['season'],
            aggregate_before=tuple(prior),progression='Regulation engine; separately validated edition ET/penalties'),
            common,notes=('NONCANONICAL proposed multi-season edition',))
        seeds=commit_seeds(snap,config,digest({'seed':meta['seed'],'fixture':f['key'],'policy':'career-stable-per-fixture-1'}))
        data={'snapshot':asdict(snap),'rules':asdict(Rules(e['competition'],extra_time=single and decisive and e['competition']!='SULA_PRE',penalties=decisive)),
              'prior':prior,'neutral':bool(single and rules['neutral_final'])}
        c.execute('INSERT INTO ms_executions VALUES(?,?,?,?,?,?,?)',(f['key'],encode(data),digest(data),encode(asdict(seeds)),encode(asdict(config)),None,None))
        c.execute("UPDATE ms_fixtures SET status='claimed' WHERE key=?",(f['key'],))
    return {'kickoff':first,'committed_fixtures':[f['key'] for f in rows],'common_pre_kickoff_sha256':common}


def play(c,a):
    required(a,'kickoff')
    rows=c.execute("SELECT * FROM ms_fixtures WHERE kickoff=? AND status='claimed' ORDER BY key",(a['kickoff'],)).fetchall()
    if not rows:raise ValueError('No committed group to resume')
    first=c.execute("SELECT min(kickoff) FROM ms_fixtures WHERE status!='final'").fetchone()[0]
    if first!=a['kickoff']:raise ValueError('Earlier chronological group unresolved')
    end=None;applied=[]
    for f in rows:
        execution=c.execute('SELECT * FROM ms_executions WHERE fixture=?',(f['key'],)).fetchone()
        data=json.loads(execution['input_json'])
        if digest(data)!=execution['input_sha256']:raise ValueError('Committed match input changed')
        policy=ReadinessPolicy();config=load(json.loads(execution['config_json']),policy,data['neutral'])
        snap=decode_snapshot(data['snapshot']);seeds=SeedCommitment(**json.loads(execution['seed_json']))
        plans=prepare(snap,config,seeds);regulation=simulate_match(snap,plans,config,seeds)
        rules=Rules(**data['rules']);bundle=resolve(snap,regulation,config,rules,tuple(data['prior']))
        validate_bundle(snap,regulation,config,rules,tuple(data['prior']),bundle)
        c.execute('UPDATE ms_executions SET result_json=?,result_sha256=? WHERE fixture=?',(encode(bundle),digest(bundle),f['key']))
        c.execute("UPDATE ms_fixtures SET status='final',home_goals=?,away_goals=?,winner=? WHERE key=?",(*bundle['score'],bundle['resolution']['winner'],f['key']))
        if f['tie_key'] and bundle['resolution']['winner']:
            c.execute('UPDATE ms_ties SET winner=? WHERE key=?',(bundle['resolution']['winner'],f['tie_key']))
        apply_players(c,{'key':f['key'],'competition':f['edition'],'home':f['home'],'away':f['away'],'kickoff':f['kickoff']},snap,bundle,policy)
        finish=(datetime.fromisoformat(f['kickoff'])+timedelta(seconds=bundle['duration_seconds'])).isoformat(sep=' ',timespec='seconds')
        end=max(end or finish,finish);applied.append({'fixture':f['key'],'result_sha256':digest(bundle)})
    c.execute('UPDATE ms_meta SET clock=?',(end,))
    return {'applied':applied,'clock':end,'test_only':True}
