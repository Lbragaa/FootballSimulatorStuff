"""One isolated career through real authority, phone protocol and rolling saves.

No production configuration or signing material is read. The public TEST signer
and fixed precommitted career seed are the same as the focused integration test.
Raw worlds are removed after success; only a safe count/timing report remains.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
import time
from uuid import uuid5,NAMESPACE_URL

from braga_era import lineage,season_lineage as seasons
from braga_era.bridge.approval import HumanGate,PROFILE as HUMAN,otp
from braga_era.bridge.automatic import Automatic
from braga_era.bridge.career import Career
from braga_era.bridge.control import Controls,PROFILE as CONTROL,OPERATIONS
from braga_era.bridge.worker2 import Worker2
from braga_era.db import connect_read_only,file_sha256
from braga_era.history import digest,canonical_json as encode
from braga_era.multiseason.agenda import next_event
from braga_era.multiseason import store

KEY=b'TEST SEASON BOUNDARY SIGNER ONLY!!'*2
SECRET=b'PUBLIC NONPRODUCTION REHEARSAL AUTHENTICATOR'


def retain_evidence(work,output):
    """One compact private TEST fixture; no key and no raw working DB retained."""
    import gzip
    import sqlite3
    import tempfile
    import zipfile
    from contextlib import closing
    work=Path(work);output=Path(output);target=output/'TEST-portable-evidence.zip'
    if target.exists():return target
    with lineage.access(work/'authority/registry.sqlite',KEY) as (c,t):
        if not t['test_only'] or t['career']!='season-boundary-test':raise ValueError('Public TEST fixture only')
        with tempfile.TemporaryDirectory(dir=output,prefix='.test-evidence-') as temp:
            registry=Path(temp)/'registry.sqlite'
            with closing(sqlite3.connect(registry)) as copied:c.backup(copied)
            note={'scope':'NONCANONICAL DEVELOPMENT TEST','key_included':False,'career':t['career'],'head':t['head'],
                  'checkpoint_archive_sha256':file_sha256(work/'TEST-season-checkpoint.zip'),
                  'registry_sha256':file_sha256(registry),
                  'restore':'Extract registry.sqlite.gz to a disposable registry, then season_lineage.restore with the public TEST KEY in this runner. No production use.'}
            temporary=Path(temp)/'evidence.zip'
            with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as z:
                z.write(work/'TEST-season-checkpoint.zip','checkpoint.zip')
                z.writestr('registry.sqlite.gz',gzip.compress(registry.read_bytes(),mtime=0))
                z.writestr('NONCANONICAL.json',encode(note))
            temporary.rename(target)
    return target


def identity(name):return str(uuid5(NAMESPACE_URL,'registered-seasons-rehearsal-1:'+name))


def acknowledge_test_bulk(c,t,cursors):
    if not t['test_only'] or t['career']!='season-boundary-test':raise ValueError('Disconnected TEST bulk delivery only')
    c.execute('BEGIN IMMEDIATE')
    try:
        c.executemany('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',cursors)
        lineage.seal_cursors(c,t,KEY);c.commit()
    except BaseException:c.rollback();raise


def run(root_db,output,*,groups=20,full_year=True, policy='supported-ecosystem-proposal-1'):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    work=output/'work';work.mkdir(exist_ok=True);reg=work/'authority/registry.sqlite'
    resumed_run=reg.exists()
    # The desktop Windows sandbox can deny deleting system TEMP directories.
    # Keep this runner's owned spill files inside its disposable work root.
    import tempfile
    scratch=work/'scratch';scratch.mkdir(exist_ok=True);tempfile.tempdir=str(scratch)
    original=file_sha256(root_db);started=time.perf_counter()
    if not reg.exists():lineage.provision(reg,KEY,test_only=True,commissioner='SIMULATED',career_id='season-boundary-test',seed='season-boundary-fixed-v1')
    with lineage.access(reg,KEY) as (c,t):
        if not t['test_only'] or t['career']!='season-boundary-test':raise ValueError('Isolated TEST authority required')
        old=c.execute("SELECT * FROM batches WHERE id='finish-2027'").fetchone()
    parent=work/'completed-2027'
    if not old:
        m=lineage.prepare(reg,KEY,root_db,until='2027-12-31 23:59',execution_id='finish-2027')
        with lineage.access(reg,KEY) as (c,t):d=lineage.expected_authorization(m,t)
        lineage.authorize(reg,KEY,root_db,m,d,lineage.sign(KEY,d))
    if not old or old['state']!='accepted':
        lineage.execute(reg,KEY,'finish-2027',parent)
        d=lineage.acceptance_template(reg,KEY,parent);lineage.accept(reg,KEY,parent,d,lineage.sign(KEY,d))
    parent_sha=file_sha256(parent/'payload/database.sqlite')
    # Start at the documented post-delivery fixture boundary. This is not a
    # claim to narrate all 217 legacy matches through a phone conversation.
    with lineage.access(reg,KEY,True) as (c,t):
        if t['head']==digest(json.loads((parent/'payload/checkpoint.json').read_text())):
            with connect_read_only(parent/'payload/database.sqlite') as db:
                rows=[(r[0],r[1],r[2]) for r in db.execute('SELECT r.fixture_key,r.result_sha256,max(e.sequence) FROM world_receipts r JOIN world_events e ON e.fixture_key=r.fixture_key GROUP BY r.fixture_key,r.result_sha256')]
            acknowledge_test_bulk(c,t,rows)
    career=Career(reg,KEY,'season-boundary-test',True)
    clock_path=work/'human-clock.json'
    clock=[json.loads(clock_path.read_text()) if clock_path.exists() else 1700000000]
    gate=HumanGate(work/'human.sqlite',KEY,SECRET,{'profile':HUMAN,'career':career.career,'test_only':True,
        'repository_id':1436541980,'human_id':78325376,'human_login':'Lbragaa'},clock=lambda:clock[0])
    if not (work/'human.sqlite').exists():gate.initialize()
    with lineage.access(reg,KEY) as (c,t):
        control_policy={'profile':CONTROL,'action':'approve_remote_control_policies','career':career.career,'test_only':True,
                'authority_key_sha256':t['key_hash'],'policy_sha256':digest(json.loads(t['policy_json'])),
                'repository_id':1436541980,'human_id':78325376,'human_login':'Lbragaa','operations':OPERATIONS}
    receipt=work/'control-policy.json'
    if not receipt.exists():receipt.write_text(encode(lineage.signed(control_policy,KEY)))
    controls=Controls(career,work/'controls.sqlite',work/'executions',receipt,gate,enabled=True)
    if not controls.store.exists():controls.initialize()
    auto=Automatic(controls,work/'automatic')
    if not (auto.directory/'mode.json').exists():auto.initialize()
    # The actual Worker2 protocol, using the existing disconnected test transport.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
    from test_bridge import Transport,REQUESTERS,USER
    transport=Transport();transport_file=work/'transport.json'
    if transport_file.exists():
        saved=json.loads(transport_file.read_text());transport.rows={int(k):v for k,v in saved['rows'].items()};transport.notes={int(k):v for k,v in saved['notes'].items()}
    requesters=json.loads(json.dumps(REQUESTERS));requesters[str(USER['id'])]['scopes'].append('control')
    worker=Worker2(transport,career,work/'bridge.sqlite',requesters,controls=controls,automatic=auto)
    def save_transport():
        transport_file.write_text(encode({'rows':transport.rows,'notes':transport.notes}));clock_path.write_text(str(clock[0]))
    def command(name,tag,**args):
        rid=identity(tag);old=next((r for r in transport.rows.values() if json.loads(r['body'])['request_id']==rid),None)
        if old:number=old['number']
        else:
            status=worker.poll()
            request={'protocol':'braga-bridge-2','request_id':rid,'sequence':status['next_sequence'],
                     'career':career.career,'expected_checkpoint':career.identity()['checkpoint'],'command':name,'args':args}
            number=transport.add(request);save_transport()
        worker.poll();save_transport()
        # Keep the original command delivery even after a control receipt follows.
        for note in transport.comments(number):
            if note['body'].startswith('BRAGA_BRIDGE_RESPONSE') or '"response":' in note['body']:
                envelope=json.loads(note['body'].split('```json\n')[1].split('\n```')[0])
                if not worker.verify_response(envelope) or envelope['response']['status']!='completed':raise ValueError('Phone rehearsal command refused')
                return number,envelope['response']['result']
        raise ValueError('Missing signed worker reply')
    def confirm(number,result):
        ch=result['confirmation'];rid=ch['challenge_id']
        with gate.access() as gc:row=gc.execute('SELECT state,result FROM challenges WHERE id=?',(rid,)).fetchone()
        if row['state']=='completed':return json.loads(row['result'])
        if row['state'] not in {'completed','committed'}:
            with gate.access() as gc:last=gc.execute('SELECT last_counter FROM configuration').fetchone()[0]
            clock[0]=max(clock[0],(last+1)*30)
            stamp=datetime.fromtimestamp(clock[0],timezone.utc).isoformat().replace('+00:00','Z')
            comment_id=1+max([100000,*[note['id'] for notes in transport.notes.values() for note in notes]])
            transport.notes[number].append({'id':comment_id,'user':USER,'created_at':stamp,'updated_at':stamp,
                'body':ch['confirmation_format'].replace('<authenticator-code>',otp(SECRET,clock[0]//30))})
            save_transport()
        worker.poll();save_transport();clock[0]+=31;clock_path.write_text(str(clock[0]))
        with gate.access() as gc:row=gc.execute('SELECT state,result FROM challenges WHERE id=?',(rid,)).fetchone()
        if row['state']!='completed':raise ValueError('Separate exact human confirmation did not complete')
        return json.loads(row['result'])
    command('enable_automatic_gameplay','enable',confirmation='ENABLE_AUTOMATIC_GAMEPLAY')
    def transition(year):
        before=time.perf_counter();cpu=time.process_time()
        tag = f'prepare:{year}' if policy == 'supported-ecosystem-proposal-1' else f'prepare:{year}:{policy}'
        _,review=command('prepare_season_transition',tag,policy=policy)
        pid=review['preparation_id'];sha=review['manifest_sha256']
        with lineage.access(reg,KEY) as (c,t):resumed=c.execute('SELECT 1 FROM batches WHERE id=?',('season3:'+pid,)).fetchone() is not None
        n,r=command('request_authorize_season',f'authorize:{year}',preparation_id=pid,manifest_sha256=sha);confirm(n,r)
        n,r=command('request_execute_season',f'execute:{year}',preparation_id=pid,manifest_sha256=sha);candidate=confirm(n,r)
        n,r=command('request_accept_season',f'accept:{year}',preparation_id=pid,checkpoint_sha256=candidate['checkpoint_sha256']);confirm(n,r)
        return {'season':year,'wall_seconds':time.perf_counter()-before,'cpu_seconds':time.process_time()-cpu,'accepted':True,
                'timing_scope':'remaining/resumed control workflow' if resumed else 'fresh control workflow'}
    transitions=[transition(2028)]
    episodes=[]
    for i in range(12):
        cached=any(json.loads(r['body'])['request_id']==identity(f'episode:2028:{i}') for r in transport.rows.values())
        before=time.perf_counter();_,episode=command('play_next_episode',f'episode:2028:{i}')
        episodes.append({'episode_type':episode['episode_type'],'wall_seconds':time.perf_counter()-before,
                         'timing_scope':'cached/resumed request delivery' if cached else 'new command processing'})
        if episode['episode_type']=='vasco_match':break
    else:raise ValueError('No complete Vasco episode within rehearsal bound')
    counts={};checkpoints=[]
    if full_year:
        for i in range(80):
            with lineage.access(reg,KEY) as (c,t):info,_=seasons.current(c,t,KEY)
            if info['season']>2028:break
            if next_event(info['world'],KEY) is None:break
            rid=identity(f'full-season:2028:{i}');before=time.perf_counter();cpu=time.process_time()
            with lineage.access(reg,KEY) as (c,t):prior=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+rid,)).fetchone()
            if prior and prior['state']=='accepted':continue
            if prior:m=json.loads(prior['manifest'])
            else:
                m=seasons.prepare(reg,KEY,rid,[{'kind':'advance','args':{'max_groups':groups}}])
                seasons.authorize(reg,KEY,m,lineage.signed(seasons.authorization(m),KEY))
            target=work/'successors'/rid;seasons.execute(reg,KEY,rid,target)
            d=seasons.acceptance_template(reg,KEY,target);seasons.accept(reg,KEY,target,d,lineage.sign(KEY,d))
            checkpoints.append({'wall_seconds':time.perf_counter()-before,'cpu_seconds':time.process_time()-cpu,
                'object_bytes':sum(p.stat().st_size for p in (work/'authority/season-objects').glob('*.gz'))})
            with lineage.access(reg,KEY) as (c,t):info,_=seasons.current(c,t,KEY)
            with connect_read_only(info['database']) as db:total=db.execute("SELECT count(*) FROM ms_fixtures WHERE status='final'").fetchone()[0]
            print('NONCANONICAL registered fixtures',total,flush=True)
        else:raise ValueError('Registered season exceeded explicit batch bound')
        with lineage.access(reg,KEY,True) as (c,t):
            info,_=seasons.current(c,t,KEY)
            with connect_read_only(info['database']) as db:
                counts=dict(db.execute('SELECT f.edition,count(*) FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE e.season=2028 GROUP BY f.edition'))
                if sum(counts.values())!=1341:raise ValueError('Incomplete integrated 2028 competition count')
                # Bulk simulation is complementary to the actual phone episode.
                # Its results are explicitly acknowledged for test season closure.
                cursors=[tuple(r) for r in db.execute("SELECT x.fixture,x.result_sha256,json_array_length(x.result_json,'$.events') FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture JOIN ms_editions e ON e.id=f.edition WHERE e.season=2028 AND x.result_json IS NOT NULL")]
            acknowledge_test_bulk(c,t,cursors)
        _,closed=command('play_next_episode','close:2028')
        if closed['episode_type']!='season_boundary':raise ValueError('Season conclusion did not reach approval boundary')
        transitions.append(transition(2029))
        for i in range(12):
            cached=any(json.loads(r['body'])['request_id']==identity(f'episode:2029:{i}') for r in transport.rows.values())
            before=time.perf_counter();_,ep=command('play_next_episode',f'episode:2029:{i}')
            episodes.append({'episode_type':ep['episode_type'],'season':2029,'wall_seconds':time.perf_counter()-before,
                             'timing_scope':'cached/resumed request delivery' if cached else 'new command processing'})
            if ep['episode_type']=='vasco_match':break
            if ep['episode_type']=='blocker':raise ValueError('2029 bridge episode has a real blocker; do not omit it')
        else:raise ValueError('No complete 2029 Vasco episode within bound')
        # Measure consecutive real accepted successors with the evolved 2029
        # world. These are complementary bounded bulk TEST advances, not a claim
        # that every simulated fixture was narrated through a phone.
        timing_file=output/'successor-timings.json'
        measured=json.loads(timing_file.read_text(encoding='utf-8')) if timing_file.exists() else []
        for i in range(3):
            rid=identity(f'timed-2029:{i}');target=work/'successors'/rid
            with lineage.access(reg,KEY) as (c,t):prior=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+rid,)).fetchone()
            if prior and prior['state']=='accepted':continue
            before=time.perf_counter();cpu=time.process_time();phase={}
            mark=time.perf_counter()
            if prior:m=json.loads(prior['manifest'])
            else:
                m=seasons.prepare(reg,KEY,rid,[{'kind':'advance','args':{'max_groups':2}}])
                seasons.authorize(reg,KEY,m,lineage.signed(seasons.authorization(m),KEY))
            phase['prepare_authorize']=time.perf_counter()-mark;mark=time.perf_counter()
            seasons.execute(reg,KEY,rid,target);phase['execute']=time.perf_counter()-mark;mark=time.perf_counter()
            d=seasons.acceptance_template(reg,KEY,target);seasons.accept(reg,KEY,target,d,lineage.sign(KEY,d))
            phase['acceptance']=time.perf_counter()-mark
            with lineage.access(reg,KEY) as (c,t):info,_=seasons.current(c,t,KEY)
            from tools.benchmark_registered_seasons import peak_memory
            measured.append({'request_id':rid,'resumed':prior is not None,'wall_seconds':time.perf_counter()-before,
                             'cpu_seconds':time.process_time()-cpu,'phases_seconds':phase,'process_peak_memory_bytes':peak_memory(),
                             'execution_metrics':json.loads((target/'execution_metrics.json').read_text(encoding='utf-8')),
                             'database_bytes':info['package']['state']['database.sqlite']['bytes'],
                             'object_pool_bytes':sum(p.stat().st_size for p in (work/'authority/season-objects').glob('*.gz'))})
            timing_file.write_text(json.dumps(measured,indent=2)+'\n',encoding='utf-8')
        checkpoints+=measured
    with lineage.access(reg,KEY) as (c,t):info,path=seasons.current(c,t,KEY)
    archive=work/'TEST-season-checkpoint.zip';mark=time.perf_counter()
    if archive.exists():
        import zipfile
        with zipfile.ZipFile(archive) as z:
            if json.loads(z.read('package.json'))!=info['package']:raise ValueError('Existing export belongs to another accepted successor')
            exported={'checkpoint':info['checkpoint'],'archive_bytes':archive.stat().st_size,'objects':len(z.infolist())-2,'resumed_original_export':True}
        export_seconds=None
    else:
        exported=seasons.export(reg,KEY,path,archive);export_seconds=time.perf_counter()-mark
    mark=time.perf_counter()
    restored=seasons.restore(reg,KEY,archive,work/'independent-restoration')
    restore_seconds=time.perf_counter()-mark
    retained=retain_evidence(work,output)
    if file_sha256(root_db)!=original or file_sha256(parent/'payload/database.sqlite')!=parent_sha:raise ValueError('Protected source changed')
    with connect_read_only(info['database']) as db:
        future=dict(db.execute("SELECT f.edition,count(*) FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE e.season=2029 AND f.status='final' GROUP BY f.edition"))
        offseason_reports=[json.loads(r[0]) for r in db.execute('SELECT summary_json FROM ms_offseasons ORDER BY season')]
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','production_modified':False,'source_unchanged':True,
            '2028_fixture_counts':counts,'transitions':transitions,'phone_episodes':episodes,'rolling_successors':checkpoints,
            '2029_completed_fixture_counts':future,'offseasons':offseason_reports,
            'portable':exported,'restoration':restored,'retained_test_evidence_bytes':retained.stat().st_size,'elapsed_seconds':time.perf_counter()-started,
            'export_wall_seconds':export_seconds,'restoration_wall_seconds':restore_seconds,
            'elapsed_scope':'final resumed invocation; earlier attempts excluded' if resumed_run else 'entire fresh run',
            'coverage':'Full supported 2028 ecosystem plus representative phone episodes; subsequent 2029 episode, not full 2029 season.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    # All mutable/test data is under this one explicitly owned subtree.
    if work.resolve().parent!=output or work.name!='work':raise ValueError('Unsafe rehearsal cleanup target')
    from braga_era.season_objects import remove_owned
    remove_owned(work,output)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--groups',type=int,default=20);p.add_argument('--representative-only',action='store_true')
    from braga_era.multiseason.lifecycle import SEASON_POLICIES
    p.add_argument('--policy', choices=SEASON_POLICIES, default='supported-ecosystem-proposal-1')
    a=p.parse_args();print(json.dumps(run(a.db,a.output,groups=a.groups,full_year=not a.representative_only,policy=a.policy),indent=2))
