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


def identity(name):return str(uuid5(NAMESPACE_URL,'registered-seasons-rehearsal-1:'+name))


def run(root_db,output,*,groups=20,full_year=True):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    work=output/'work';work.mkdir(exist_ok=True);reg=work/'authority/registry.sqlite'
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
            c.executemany('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',rows);lineage.seal_cursors(c,t,KEY)
    career=Career(reg,KEY,'season-boundary-test',True)
    clock_path=work/'human-clock.json'
    clock=[json.loads(clock_path.read_text()) if clock_path.exists() else 1700000000]
    gate=HumanGate(work/'human.sqlite',KEY,SECRET,{'profile':HUMAN,'career':career.career,'test_only':True,
        'repository_id':1436541980,'human_id':78325376,'human_login':'Lbragaa'},clock=lambda:clock[0])
    if not (work/'human.sqlite').exists():gate.initialize()
    with lineage.access(reg,KEY) as (c,t):
        policy={'profile':CONTROL,'action':'approve_remote_control_policies','career':career.career,'test_only':True,
                'authority_key_sha256':t['key_hash'],'policy_sha256':digest(json.loads(t['policy_json'])),
                'repository_id':1436541980,'human_id':78325376,'human_login':'Lbragaa','operations':OPERATIONS}
    receipt=work/'control-policy.json'
    if not receipt.exists():receipt.write_text(encode(lineage.signed(policy,KEY)))
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
        _,review=command('prepare_season_transition',f'prepare:{year}',policy='supported-ecosystem-proposal-1')
        pid=review['preparation_id'];sha=review['manifest_sha256']
        n,r=command('request_authorize_season',f'authorize:{year}',preparation_id=pid,manifest_sha256=sha);confirm(n,r)
        n,r=command('request_execute_season',f'execute:{year}',preparation_id=pid,manifest_sha256=sha);candidate=confirm(n,r)
        n,r=command('request_accept_season',f'accept:{year}',preparation_id=pid,checkpoint_sha256=candidate['checkpoint_sha256']);confirm(n,r)
        return {'season':year,'wall_seconds':time.perf_counter()-before,'cpu_seconds':time.process_time()-cpu,'accepted':True}
    transitions=[transition(2028)]
    episodes=[]
    for i in range(12):
        before=time.perf_counter();_,episode=command('play_next_episode',f'episode:2028:{i}')
        episodes.append({'episode_type':episode['episode_type'],'wall_seconds':time.perf_counter()-before})
        if episode['episode_type']=='vasco_match':break
    else:raise ValueError('No complete Vasco episode within rehearsal bound')
    counts={};checkpoints=[]
    if full_year:
        for i in range(80):
            with lineage.access(reg,KEY) as (c,t):info,_=seasons.current(c,t,KEY)
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
                counts=dict(db.execute('SELECT edition,count(*) FROM ms_fixtures GROUP BY edition'))
                if sum(counts.values())!=1341:raise ValueError('Incomplete integrated 2028 competition count')
                # Bulk simulation is complementary to the actual phone episode.
                # Its results are explicitly acknowledged for test season closure.
                cursors=[tuple(r) for r in db.execute("SELECT fixture,result_sha256,json_array_length(result_json,'$.events') FROM ms_executions WHERE result_json IS NOT NULL")]
            c.executemany('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',cursors);lineage.seal_cursors(c,t,KEY)
        _,closed=command('play_next_episode','close:2028')
        if closed['episode_type']!='season_boundary':raise ValueError('Season conclusion did not reach approval boundary')
        transitions.append(transition(2029))
        _,ep=command('play_next_episode','episode:2029:0');episodes.append({'episode_type':ep['episode_type'],'season':2029})
    with lineage.access(reg,KEY) as (c,t):info,path=seasons.current(c,t,KEY)
    archive=work/'TEST-season-checkpoint.zip';exported=seasons.export(reg,KEY,path,archive)
    restored=seasons.restore(reg,KEY,archive,work/'independent-restoration')
    if file_sha256(root_db)!=original or file_sha256(parent/'payload/database.sqlite')!=parent_sha:raise ValueError('Protected source changed')
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','production_modified':False,'source_unchanged':True,
            '2028_fixture_counts':counts,'transitions':transitions,'phone_episodes':episodes,'rolling_successors':checkpoints,
            'portable':exported,'restoration':restored,'elapsed_seconds':time.perf_counter()-started,
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
    a=p.parse_args();print(json.dumps(run(a.db,a.output,groups=a.groups,full_year=not a.representative_only),indent=2))
