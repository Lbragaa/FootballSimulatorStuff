"""NONCANONICAL continuation + edition rehearsal. Never accepts or deploys.

The --career-config path is LOCAL trusted operator input, never bridge args.
Signing material is read only for authenticating the source and never copied.
The new profile uses the public simulated key below, never production authority.
"""
import argparse
from datetime import datetime,timedelta
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid5,NAMESPACE_URL
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from braga_era import lineage
from braga_era.bridge.career import Career
from braga_era.db import file_sha256,connect_read_only
from braga_era.history import digest
from braga_era.seasons import AcceptedSource
from braga_era.world.scope import calculation
from braga_era.world.runner import advance as finish_2027
from braga_era.world.packages import fingerprints
from braga_era.multiseason import store
from braga_era.multiseason.agenda import advance,next_event

TEST_KEY=b'SIMULATED MULTISEASON REHEARSAL ONLY - NEVER PRODUCTION'


def run(config,output,monthly_income_cents=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh development output required')
    spec=json.loads(Path(config).read_text(encoding='utf-8'))
    protected=[Path(config),Path(spec['registry']),Path(spec['key_file']),Path(spec['automatic_directory'])/'mode.json']
    before={str(p):file_sha256(p) for p in protected}
    career=Career(spec['registry'],Path(spec['key_file']).read_bytes(),spec['career'],spec['test_only'])
    career.root_parent=Path(spec['root_parent'])
    with lineage.access(career.registry,career.key) as (c,t):
        parent=career.root_parent if t['head']==lineage.ROOT else Path(c.execute('SELECT path FROM accepted WHERE checkpoint=?',(t['head'],)).fetchone()[0])
        info=lineage.parent_info(c,t,career.key,parent);seed=t['seed'];original_head=t['head']
    # These directories are disconnected worlds, not registered accepted careers.
    if Path(config).resolve().parent in output.parents:raise ValueError('Output cannot be inside the operational career')
    output.mkdir(parents=True)
    (output/'NONCANONICAL-NEVER-PROMOTE.txt').write_text('Disconnected development rehearsal. No production acceptance permitted.\n')
    snapshots=[]
    with calculation(career.test_only):
        for name in ('completed-2027','independent-2027'):
            target=output/name;lineage.clone_parent(info,target,seed)
            finish_2027(target,until='2027-12-31 23:59')
            lineage.prefix_check(info['database'],target/'database.sqlite')
            with connect_read_only(target/'database.sqlite') as c:snapshots.append(fingerprints(c))
    if snapshots[0]!=snapshots[1]:raise ValueError('Independent 2027 completion differs')
    source=AcceptedSource(output/'completed-2027/database.sqlite','NONCANONICAL-COMPLETION:'+digest(snapshots[0]),file_sha256(output/'completed-2027/database.sqlite'))
    policy=store.proposed_policy();decision=store.statement(source,policy,seed);target=output/'multi'
    store.create(source,target,seed=seed,policy=policy,decision=decision,signature=lineage.sign(TEST_KEY,decision),test_key=TEST_KEY)
    def command(kind,**args):
        identity=str(uuid5(NAMESPACE_URL,'multiseason-rehearsal-1:'+kind+':'+digest(args)))
        return store.run(target,TEST_KEY,identity,kind,args)
    command('prepare_season',season=2028);command('open_recorded_account',club='club:15')
    if monthly_income_cents is not None:
        command('propose_income',club='club:15',season=2028,monthly_cents=monthly_income_cents,
                reason='TEST scenario for incremental known-contract cashflow; hypothetical forward receipts, unknown base payroll/real sponsorship remain excluded; commissioner review required')
    command('evolve',season=2028);command('continue_modeled_registrations',season=2028)
    clubs=[command('register_fictional_club',name=f'Fictional Access Club {i}',strength=64+i,dated='2028-01-01')['club'] for i in range(1,9)]
    def pool(comp,participants,format='knockout'):
        command('propose_pool',id=comp+'-2028-proposal',season=2028,competition=comp,clubs=participants,reason='Explicit NONCANONICAL scoped format/entry prototype; not historical qualification or approved 2028 allocation')
        for k in participants:command('qualify',season=2028,competition=comp,club=k,source={'type':'proposed_pool','pool':comp+'-2028-proposal'})
        return command('edition',competition=comp,season=2028,format=format,clubs=participants,rules={'legs':2,'final_legs':1,'neutral_final':True})['edition']
    access=pool('ACCESS',clubs,'qualification')
    command('schedule',edition=access,start='2028-01-06 16:00',deadline='2028-02-28 23:59')
    advance(target,TEST_KEY,request_id=str(uuid5(NAMESPACE_URL,'rehearsal-access-2028')),max_groups=2)
    qualifiers=command('close_edition',edition=access)['qualifiers']
    from braga_era.world.adapters import recompute_standings
    with connect_read_only(source.database) as c:
        table=recompute_standings(c,write=False)
        ranked=sorted(table,key=lambda k:(-table[k]['points'],-table[k]['wins'],-(table[k]['gf']-table[k]['ga']),-table[k]['gf'],c.execute('SELECT name FROM clubs WHERE id=?',(k,)).fetchone()[0]))
    survivors=['club:'+str(k) for k in ranked[:16]]
    for pos,k in enumerate(survivors,1):command('qualify',season=2028,competition='LEAGUE',club=k,source={'type':'legacy_league_position','position':pos})
    for k in qualifiers:command('qualify',season=2028,competition='LEAGUE',club=k,source={'type':'edition_qualifier','edition':access})
    command('edition',competition='LEAGUE',season=2028,format='league',clubs=survivors+qualifiers,rules={'legs':2,'final_legs':1,'neutral_final':False})
    command('schedule',edition='LEAGUE:2028',start='2028-01-15 16:00',deadline='2028-12-21 23:59')
    # Real engine integration for domestic cup prototype; full early-entry rules,
    # continental groups/allocations and the remaining ecosystem are not claimed.
    cup=pool('CDB',survivors)
    command('schedule',edition=cup,start='2028-02-01 16:00',deadline='2028-12-21 23:59')
    batches=0;blocker=None
    try:
        while next_event(target,TEST_KEY):
            advance(target,TEST_KEY,request_id=str(uuid5(NAMESPACE_URL,f'rehearsal-2028:{batches}')),max_groups=1);batches+=1
            with connect_read_only(target/'database.sqlite') as c:
                editions=[dict(r) for r in c.execute("SELECT * FROM ms_editions WHERE state='active' ORDER BY id")]
                clock=c.execute('SELECT clock FROM ms_meta').fetchone()[0]
                states={e['id']:([dict(r) for r in c.execute('SELECT * FROM ms_ties WHERE edition=? ORDER BY stage,key',(e['id'],))],
                                c.execute("SELECT count(*) FROM ms_fixtures WHERE edition=? AND status!='final'",(e['id'],)).fetchone()[0]) for e in editions}
            for e in editions:
                ties,pending=states[e['id']]
                if pending:continue
                if e['format']=='knockout' and len(ties)<len(survivors)-1:
                    start=(datetime.fromisoformat(clock)+timedelta(days=4)).strftime('%Y-%m-%d 16:00')
                    command('schedule',edition=e['id'],start=start,deadline='2028-12-21 23:59')
                else:command('close_edition',edition=e['id'])
        command('archive_season',season=2028,required_competitions=['ACCESS','LEAGUE','CDB'])
        command('prepare_season',season=2029)
    except (ValueError,RuntimeError) as error:
        blocker=str(error)  # internal exceptions here contain rule/operation text, no result dumps.
    verified=store.validate(target,TEST_KEY)
    portable=output/'portable';store.export(target,portable,TEST_KEY);store.restore(portable,output/'restored',TEST_KEY)
    with connect_read_only(target/'database.sqlite') as c:
        report={'scope':'NONCANONICAL DEVELOPMENT TEST','source_current_accepted_parent':original_head,
            'prior_accepted_results_preserved':True,'independent_2027_completion':True,
            'editions':[{'competition':r['competition'],'season':r['season'],'state':r['state'],'champion_recorded':r['champion'] is not None} for r in c.execute('SELECT * FROM ms_editions ORDER BY id')],
            'season_states':[tuple(r) for r in c.execute('SELECT season,state FROM ms_seasons ORDER BY season')],
            'completed_new_fixtures':c.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0],
            'replay':verified,'portable_restored':True,'blocker':blocker,'modelled_monthly_income_cents':monthly_income_cents,
            'not_2028_ready':True,'unsupported_full_ecosystem':['continental groups/allocations and cross-entry','full CDB early entry','state federation ecosystem','Série B full season','full-club economics','youth/retirement and competing-offer market','production authority/bridge profile']}
    if any(file_sha256(Path(p))!=sha for p,sha in before.items()):raise ValueError('Operational source changed concurrently; do not claim preservation')
    report['production_files_unchanged']=True
    (output/'rehearsal.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--career-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--monthly-income-cents',type=int);a=p.parse_args();run(a.career_config,a.output,a.monthly_income_cents)
