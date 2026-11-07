"""Registered season successors in the existing lineage authority.

The authority, seed, parent claims, acceptance table and narration ledger are
shared with profile 2. Immutable chunks deduplicate snapshots. Only new commands
are independently replayed against an authenticated accepted parent; full audit
also reconstructs the legacy anchor and replays the complete season journal.
"""
from contextlib import closing,nullcontext
from contextvars import ContextVar
import json
from pathlib import Path
import shutil
import tempfile
import time
from uuid import UUID, uuid5

from . import lineage, season_objects as objects
from .checkpoints import read_json, write_json
from .db import connect_read_only, file_sha256
from .history import canonical_json as encode, digest
from .multiseason import store
from .multiseason.registered import PROFILE, policy
from .seasons import AcceptedSource, fingerprints

FILES = {'database.sqlite', 'parent.sqlite', 'development.json'}
POOL_OVERRIDE=ContextVar('season_object_pool',default=None)


def pool(c):
    if POOL_OVERRIDE.get() is not None:return POOL_OVERRIDE.get()
    return Path(c.execute('PRAGMA database_list').fetchone()[2]).resolve().parent/'season-objects'


def blob(c, value):return objects.put(pool(c), encode(value).encode())
def document(c, identity):return json.loads(objects.get(pool(c), identity))


def is_registered(parent):
    path=Path(parent)/'payload/checkpoint.json'
    return path.is_file() and read_json(path).get('profile')==PROFILE


def authorization(manifest):
    return {'profile':PROFILE,'action':'authorize_season_successor','career':manifest['career'],
            'test_only':manifest['test_only'],'manifest_sha256':digest(manifest),
            'parent':manifest['immediate_parent_sha256'],'separate_acceptance_required':True}


def validation(meta):
    return {'profile':PROFILE,'action':'independent_season_validation','checkpoint_sha256':digest(meta),
            'world_sha256':meta['world_sha256'],'independent_delta_replay':True}


def bind_manifest(m,a,trusted):
    """Acceptance/validation signatures cannot substitute for execution consent."""
    if (m['profile']!=PROFILE or a['profile']!=PROFILE or m['career']!=trusted['career']
        or a['career']!=m['career'] or type(m['test_only']) is not bool
        or m['test_only']!=bool(trusted['test_only']) or a['test_only'] is not m['test_only']
        or a['policy']!=policy(bool(trusted['test_only']))
        or a['immediate_parent_sha256']!=m['immediate_parent_sha256']
        or a['generation']!=m['generation'] or a['season']!=m['season']
        or type(m['automatic_gameplay']) is not bool or a['automatic_gameplay'] is not m['automatic_gameplay']
        or a['career_seed_sha256']!=m['career_seed_sha256'] or m['career_seed_sha256']!=digest(trusted['seed'])
        or a['seed_policy']!=m['seed_policy'] or m['seed_policy']!=lineage.SEED_POLICY
        or digest(a)!=m['manifest_sha256']):
        raise ValueError('Season metadata differs from exact authorized manifest')


def verify_node(node, trusted, key):
    m=node['metadata'];a=node['manifest']
    bind_manifest(m,a,trusted)
    if (lineage.check_signed(node['authorization'],key)!=authorization(a)
        or lineage.check_signed(node['validation'],key)!=validation(m)
        or lineage.check_signed(node['acceptance'],key)!=lineage.expected_acceptance(m,node['package_sha256'],trusted)):
        raise ValueError('Untrusted season ancestor/authorization')


def chain(c, package, trusted, key, proof):
    meta=package['metadata'];anchor=document(c,meta['anchor_sha256'])
    nodes=[];previous=meta.get('parent_node_sha256');seen=set()
    while previous:
        if previous in seen or len(seen)>100000:raise ValueError('Invalid season ancestry')
        seen.add(previous);node=document(c,previous);nodes.append(node)
        previous=node['metadata'].get('parent_node_sha256')
    result=anchor['nodes']+list(reversed(nodes))+[proof]
    if lineage.verify_chain(result,trusted,key)!=digest(meta):raise ValueError('Season ancestry differs')
    return anchor,result


def read_package(directory):
    directory=Path(directory);payload=directory/'payload'
    if payload.is_symlink() or {p.name for p in payload.iterdir()}!={'checkpoint.json','package.json'}:
        raise ValueError('Invalid season checkpoint inventory')
    if any(p.is_symlink() or p.stat().st_size>objects.MAX_OBJECT for p in payload.iterdir()):
        raise ValueError('Unsafe season metadata')
    package=read_json(payload/'package.json')
    if read_json(payload/'checkpoint.json')!=package['metadata']:raise ValueError('Season metadata changed')
    if set(package['state'])!=FILES:raise ValueError('Invalid season state inventory')
    descriptor_binding(package)
    return package


def descriptor_binding(package):
    m=package['metadata']
    if (set(package['state'])!=FILES or digest(package['state'])!=m['state_sha256']
        or package['state']['database.sqlite']['sha256']!=m['database_sha256']):
        raise ValueError('Season state descriptors differ from signed metadata')


def replay_matches(database,world_sha256,database_sha256,*,logical_only=False):
    # Byte identity implies identity of every table, after actual independent
    # replay. Different SQLite layouts retain the original logical comparison.
    if not logical_only and file_sha256(database)==database_sha256:return True
    with connect_read_only(database) as db:return digest(fingerprints(db))==world_sha256


def materialize(c, package, target):
    if set(package['state'])!=FILES:raise ValueError('Invalid season state file inventory')
    target=Path(target)
    if target.is_symlink():raise ValueError('Redirected season materialization')
    target.mkdir(parents=True,exist_ok=True)
    for name,descriptor in package['state'].items():objects.materialize(pool(c),descriptor,target/name)
    return target


def parent_info(c, trusted, key, parent, *, require_head=True,cache_directory=None):
    package=read_package(parent);meta=package['metadata'];checkpoint=digest(meta)
    row=c.execute('SELECT * FROM accepted WHERE checkpoint=?',(checkpoint,)).fetchone()
    if not row or require_head and checkpoint!=trusted['head']:raise ValueError('Unaccepted or stale season parent')
    proof=json.loads(row['proof'])
    if proof['metadata']!=meta or proof['package_sha256']!=digest(package):raise ValueError('Season package was tampered')
    if proof['authorization']!=package['authorization'] or proof['validation']!=package['validation']:
        raise ValueError('Season validation proof differs')
    chain(c,package,trusted,key,proof)
    if meta['state_sha256']!=digest(package['state']):raise ValueError('Season state descriptor changed')
    world=materialize(c,package,cache_directory or pool(c).parent/'season-cache'/checkpoint)
    _,marker=store.authenticated(world,key)
    if marker['profile']!=PROFILE or marker['seed']!=trusted['seed'] or marker['test_only']!=bool(trusted['test_only']):
        raise ValueError('Season career/seed/mode changed')
    if file_sha256(world/'database.sqlite')!=meta['database_sha256']:raise ValueError('Season database changed')
    return {'checkpoint':checkpoint,'database':world/'database.sqlite','world':world,'payload':Path(parent)/'payload',
            'generation':meta['generation'],'clock':meta['clock'],'world_sha256':meta['world_sha256'],
            'season':meta['season'],'profile':PROFILE,'metadata':meta,'package':package}


def current(c,trusted,key):
    row=c.execute('SELECT path FROM accepted WHERE checkpoint=?',(trusted['head'],)).fetchone()
    if not row:raise ValueError('An accepted completed forward parent is required')
    return lineage.parent_info(c,trusted,key,row[0]),Path(row[0])


def prepare(registry,key,request_id,operations,*,transition=False,automatic_gameplay=False,delegated=False):
    if str(UUID(request_id))!=request_id or type(automatic_gameplay) is not bool:raise ValueError('Exact season request required')
    operations=json.loads(encode(operations))
    if (not isinstance(operations,list) or not 1<=len(operations)<=2000 or len(encode(operations).encode())>8*1024**2
        or any(not isinstance(x,dict) or set(x)!={'kind','args'} or not isinstance(x['kind'],str) or not isinstance(x['args'],dict) for x in operations)):
        raise ValueError('Bounded explicit season operations required')
    with lineage.access(registry,key) as (c,t):
        info,parent=current(c,t,key);registered=info.get('profile')==PROFILE
        if transition:
            if registered:
                with connect_read_only(info['database']) as db:
                    previous=db.execute('SELECT season,state FROM ms_seasons ORDER BY season DESC LIMIT 1').fetchone()
                    if previous['state']!='archived':raise ValueError('Archive the completed season before transition')
                    year=previous['season']+1
                from .season_gameplay import unrevealed
                if unrevealed(c,info['database']):raise ValueError('Reveal earlier season narration first')
            else:
                from .season_authority import _closure
                report=_closure(info,c,t,key)
                if not report['ready_to_finalize']:raise ValueError('Season closure/reveal is incomplete')
                year=2028
            operations=[{'kind':'prepare_season','args':{'season':year}}]+operations
        else:
            if not registered:raise ValueError('Explicit season transition required')
            year=info['season'];automatic_gameplay=info['metadata']['automatic_gameplay']
            if any(x['kind']=='prepare_season' for x in operations):raise ValueError('A new season needs separate transition approval')
        if delegated:
            if transition or not automatic_gameplay:
                raise ValueError('Season policy does not delegate this operation')
            if operations!=[{'kind':'advance','args':{'max_groups':1}}]:
                with connect_read_only(info['database']) as db:
                    comps=[r[0] for r in db.execute('SELECT competition FROM ms_editions WHERE season=? ORDER BY competition',(year,))]
                    if operations!=[{'kind':'archive_season','args':{'season':year,'required_competitions':comps}}]:
                        raise ValueError('Season delegation permits only chronology or exact season closure')
                    calendars=[json.loads(r[0]) for r in db.execute("SELECT args_json FROM ms_operations WHERE kind='commit_season_calendar'")]
                    declared=next((r for r in reversed(calendars) if r['season']==year),None)
                    actual={r[0] for r in db.execute('SELECT id FROM ms_editions WHERE season=?',(year,))}
                    if declared and set(declared['plans'])!=actual:raise ValueError('Declared competition calendar is incomplete')
            from .season_gameplay import unrevealed
            if unrevealed(c,info['database']):raise ValueError('Existing narration first')
        claim=c.execute('SELECT batch FROM parent_claims WHERE parent=?',(info['checkpoint'],)).fetchone()
        prior=None
        if claim and claim[0]!='season3:'+request_id:
            old=c.execute("SELECT manifest,state FROM batches WHERE id=?",(claim[0],)).fetchone()
            if not transition or not old or old['state']!='season_authorized':raise ValueError('Parent already committed to another execution')
            prior={'batch':claim[0],'manifest_sha256':digest(json.loads(old['manifest']))}
        return {'profile':PROFILE,'career':t['career'],'test_only':bool(t['test_only']),
                'request_id':request_id,'kind':'transition' if transition else 'operations','season':year,
                'immediate_parent_sha256':info['checkpoint'],'database_sha256':file_sha256(info['database']),
                'generation':info['generation']+1,'career_seed_sha256':digest(t['seed']),
                'seed_policy':lineage.SEED_POLICY,'policy':policy(bool(t['test_only'])),
                'automatic_gameplay':automatic_gameplay,'delegated':delegated,'lease_epoch':t['lease_epoch'],
                'prior_review':prior,'operations':operations}


def authorize(registry,key,manifest,approval):
    with lineage.access(registry,key,True) as (c,t):
        row=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+manifest['request_id'],)).fetchone()
        if row:
            if json.loads(row['manifest'])!=manifest or json.loads(row['decision'])!=lineage.check_signed(approval,key):
                raise ValueError('Changed registered season request')
            return
        expected=prepare(registry,key,manifest['request_id'],manifest['operations'][1:] if manifest['kind']=='transition' else manifest['operations'],
                         transition=manifest['kind']=='transition',automatic_gameplay=manifest['automatic_gameplay'],delegated=manifest['delegated'])
        if expected!=manifest or lineage.check_signed(approval,key)!=authorization(manifest):raise ValueError('Exact signed season authorization required')
        _,parent=current(c,t,key);identifier='season3:'+manifest['request_id']
        c.execute('BEGIN IMMEDIATE')
        try:
            if manifest['prior_review']:
                prior=manifest['prior_review']
                if c.execute('UPDATE parent_claims SET batch=? WHERE parent=? AND batch=?',(identifier,t['head'],prior['batch'])).rowcount!=1:
                    raise ValueError('Season review claim changed')
                c.execute("UPDATE batches SET state='season_review_superseded' WHERE id=?",(prior['batch'],))
            else:c.execute('INSERT INTO parent_claims VALUES(?,?)',(t['head'],identifier))
            c.execute("INSERT INTO batches VALUES(?,?,?,?,?,'season_authorized_v3',NULL,?,NULL,NULL)",
                      (identifier,t['head'],encode(manifest),encode(approval['document']),approval['signature'],str(parent)))
            c.execute('INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)',
                      (identifier,'season_execution',encode(approval['document']),approval['signature']))
            c.commit()
        except BaseException:c.rollback();raise


def apply(world,key,manifest):
    from .multiseason.agenda import advance
    for i,op in enumerate(manifest['operations']):
        request=str(uuid5(UUID(manifest['request_id']),f'operation:{i}'))
        if op['kind']=='lifecycle_setup':
            if op['args']!={'scenario':'full-2028-proposal-1'} or manifest['season']!=2028:
                raise ValueError('Unsupported explicit season setup policy')
            from .multiseason.lifecycle import setup_2028
            def command(kind,**args):
                return store.run(world,key,str(uuid5(UUID(request),'setup:'+kind+':'+digest(args))),kind,args)
            setup_2028(world,command,lambda n:advance(world,key,
                request_id=str(uuid5(UUID(request),'bootstrap:'+str(n))),max_groups=1))
        elif op['kind']=='lifecycle_following':
            if op['args']!={'scenario':'repeat-season-proposal-1'} or manifest['season']<2029:
                raise ValueError('Unsupported repeat season policy')
            from .multiseason.lifecycle import setup_following
            def command(kind,**args):
                return store.run(world,key,str(uuid5(UUID(request),'setup:'+kind+':'+digest(args))),kind,args)
            setup_following(world,command,manifest['season'])
        elif op['kind']=='advance':advance(world,key,request_id=request,**op['args'])
        else:store.run(world,key,request,op['kind'],op['args'])


def _clone(info,target):
    target.mkdir()
    for name in FILES:shutil.copyfile(info['world']/name,target/name)


def _start(info,target,key,manifest,seed):
    if info.get('profile')==PROFILE:_clone(info,target)
    else:
        source=AcceptedSource(info['database'],info['checkpoint'],manifest['database_sha256'])
        decision=store.statement(source,manifest['policy'],seed)
        store.create(source,target,seed=seed,policy=manifest['policy'],decision=decision,
                     signature=lineage.sign(key,decision),test_key=key)


def verify_candidate(c,t,key,directory,*,replay=True,logical_only=False):
    if replay not in (True,False,'full'):raise ValueError('Unsupported season verification mode')
    package=read_package(directory);m=package['metadata'];a=package['manifest']
    bind_manifest(m,a,t)
    if lineage.check_signed(package['authorization'],key)!=authorization(a) or a['immediate_parent_sha256']!=t['head']:
        raise ValueError('Untrusted/stale season candidate')
    if digest(a)!=m['manifest_sha256'] or digest(package['state'])!=m['state_sha256']:
        raise ValueError('Season candidate input changed')
    info,_=current(c,t,key)
    if info['checkpoint']!=m['immediate_parent_sha256'] or file_sha256(info['database'])!=a['database_sha256']:
        raise ValueError('Exact season parent differs')
    with tempfile.TemporaryDirectory(dir=Path(directory),prefix='.season-verify-') as temp:
        child=materialize(c,package,Path(temp)/'candidate')
        report=store.validate(child,key,replay=replay=='full')
        if report['profile']!=PROFILE or report['world_sha256']!=m['world_sha256'] or not report['acceptance_eligible']:
            raise ValueError('Season candidate state differs')
        if replay is True:
            target=Path(temp)/'replay';_start(info,target,key,a,t['seed']);apply(target,key,a)
            if not replay_matches(target/'database.sqlite',report['world_sha256'],m['database_sha256'],logical_only=logical_only):
                raise ValueError('Independent season suffix replay differs')
        with connect_read_only(child/'database.sqlite') as db:
            if db.execute('SELECT max(season) FROM ms_seasons').fetchone()[0]!=m['season']:
                raise ValueError('Unapproved season activation')
            if db.execute('SELECT clock FROM ms_meta').fetchone()[0]!=m['clock']:
                raise ValueError('Season metadata clock differs from recorded state')
    if lineage.check_signed(package['validation'],key)!=validation(m):raise ValueError('Invalid season verification statement')
    return package


def execute(registry,key,request_id,directory,*,crash=None):
    directory=Path(directory).resolve()
    started=time.perf_counter();cpu=time.process_time();timings={}
    resumed=directory.exists()
    with lineage.access(registry,key,True) as (c,t):
        row=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+request_id,)).fetchone()
        if not row or row['state'] not in {'season_authorized_v3','season_candidate'}:raise ValueError('Season batch not authorized')
        a=json.loads(row['manifest']);approval={'document':json.loads(row['decision']),'signature':row['signature']}
        if a['lease_epoch']!=t['lease_epoch']:raise ValueError('Season execution belongs to a different authority epoch')
        if lineage.check_signed(approval,key)!=authorization(a):raise ValueError('Season authorization changed')
        claim=c.execute('SELECT batch FROM parent_claims WHERE parent=?',(t['head'],)).fetchone()
        if row['parent']!=t['head'] or not claim or claim[0]!=row['id']:raise ValueError('Season parent is stale or unclaimed')
        if row['directory'] and Path(row['directory'])!=directory:raise ValueError('Resume original season execution directory')
        info,parent=current(c,t,key)
        owner={'profile':PROFILE,'manifest_sha256':digest(a),'directory':str(directory)}
        if directory.exists():
            if lineage.check_signed(read_json(directory/'owner.json'),key)!=owner:raise ValueError('Unowned season execution directory')
        else:
            directory.mkdir(parents=True);write_json(directory/'owner.json',lineage.signed(owner,key))
        c.execute('UPDATE batches SET directory=? WHERE id=?',(str(directory),row['id']))
        if not (directory/'payload').exists():
            world=directory/'world'
            if not world.exists():_start(info,world,key,a,t['seed'])
            before=time.perf_counter()
            apply(world,key,a)
            timings['simulation_and_operations']=time.perf_counter()-before
            if crash=='after_operations':raise RuntimeError('Injected season crash after operations')
            before=time.perf_counter();report=store.validate(world,key,replay=False)
            timings['structural_validation']=time.perf_counter()-before
            before=time.perf_counter()
            if info.get('profile')==PROFILE:
                anchor=info['metadata']['anchor_sha256']
                old=c.execute('SELECT proof FROM accepted WHERE checkpoint=?',(t['head'],)).fetchone()
                parent_node=blob(c,json.loads(old[0]))
            else:
                files={name:objects.capture(pool(c),parent/'payload'/name) for name in sorted(lineage.FILES|{'manifest.json'})}
                anchor=blob(c,{'nodes':info['nodes'],'legacy_files':files,
                               'legacy_archive':objects.capture(pool(c),parent/'checkpoint.zip')});parent_node=None
            state={name:objects.capture(pool(c),world/name) for name in sorted(FILES)}
            blob(c,state)
            with connect_read_only(world/'database.sqlite') as db:clock=db.execute('SELECT clock FROM ms_meta').fetchone()[0]
            meta={'profile':PROFILE,'career':t['career'],'test_only':bool(t['test_only']),
                  'root_sha256':lineage.ROOT,'seed_policy':lineage.SEED_POLICY,'career_seed_sha256':digest(t['seed']),
                  'immediate_parent_sha256':t['head'],'generation':a['generation'],'season':a['season'],
                  'automatic_gameplay':a['automatic_gameplay'],'clock':clock,'manifest_sha256':digest(a),
                  'world_sha256':report['world_sha256'],'database_sha256':state['database.sqlite']['sha256'],
                  'state_sha256':digest(state),'anchor_sha256':anchor,'parent_node_sha256':parent_node}
            package={'metadata':meta,'state':state,'manifest':a,'authorization':approval,
                     'validation':lineage.signed(validation(meta),key)}
            with lineage.staged_directory(directory/'payload') as stage:
                write_json(stage/'checkpoint.json',meta);write_json(stage/'package.json',package)
            timings['chunk_export_and_publication']=time.perf_counter()-before
            # The copied, reconstructed exported state is replayed independently.
        before=time.perf_counter();package=verify_candidate(c,t,key,directory)
        timings['independent_restoration_and_replay']=time.perf_counter()-before
        if crash=='after_verification':raise RuntimeError('Injected season crash after verification')
        c.execute("UPDATE batches SET state='season_candidate',checkpoint=?,package_sha=? WHERE id=?",
                  (digest(package['metadata']),digest(package),row['id']))
        # Diagnostics are outside the immutable payload and never trusted as proof.
        metrics=directory/'execution_metrics.json'
        if not metrics.exists():write_json(metrics,{'seconds':timings,'wall_seconds':time.perf_counter()-started,'cpu_seconds':time.process_time()-cpu,'resumed_working_copy':resumed})
        return {'checkpoint_sha256':digest(package['metadata']),'package_sha256':digest(package),
                'independent_delta_replay':True,'acceptance_required':True}


def acceptance_template(registry,key,directory):
    with lineage.access(registry,key) as (c,t):
        package=read_package(directory)
        return lineage.expected_acceptance(package['metadata'],digest(package),t)


def accept(registry,key,directory,decision,signature,*,crash=None):
    directory=Path(directory).resolve()
    with lineage.access(registry,key,True) as (c,t):
        package=read_package(directory);meta=package['metadata'];checkpoint=digest(meta)
        if lineage.check_signed({'document':decision,'signature':signature},key)!=lineage.expected_acceptance(meta,digest(package),t):
            raise ValueError('Separate exact successor acceptance required')
        old=c.execute('SELECT * FROM accepted WHERE checkpoint=?',(checkpoint,)).fetchone()
        if old:
            if Path(old['path'])!=directory:raise ValueError('Accepted season location differs')
            parent_info(c,t,key,directory,require_head=False)
            lineage.publish_json(directory/'acceptance.json',json.loads(old['proof'])['acceptance'])
            if t['head']==checkpoint:_compact(c,t,key,directory,package)
            return {'checkpoint_sha256':checkpoint,'accepted':True}
        row=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+package['manifest']['request_id'],)).fetchone()
        if not row or row['state']!='season_candidate' or row['package_sha']!=digest(package) or Path(row['directory'])!=directory:
            raise ValueError('Unregistered season candidate')
        verify_candidate(c,t,key,directory)
        proof={'metadata':meta,'manifest':package['manifest'],'authorization':package['authorization'],
               'validation':package['validation'],'package_sha256':digest(package),
               'acceptance':{'document':decision,'signature':signature}}
        # Check the complete signed chain before publishing a new authority head.
        chain(c,package,t,key,proof)
        c.execute('BEGIN IMMEDIATE')
        try:
            c.execute('INSERT INTO accepted VALUES(?,?,?,?,?)',(checkpoint,t['head'],meta['generation'],encode(proof),str(directory)))
            if c.execute('UPDATE authority SET head=? WHERE head=?',(checkpoint,t['head'])).rowcount!=1:raise ValueError('Concurrent season acceptance')
            c.execute("UPDATE batches SET state='accepted' WHERE id=?",(row['id'],))
            c.execute('INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)',(row['id'],'season_acceptance',encode(decision),signature))
            if crash=='before_commit':raise RuntimeError('Injected season acceptance crash before commit')
            c.commit()
        except BaseException:c.rollback();raise
        if crash=='after_commit':raise RuntimeError('Injected season acceptance crash after commit')
        lineage.publish_json(directory/'acceptance.json',proof['acceptance'])
        _compact(c,t,key,directory,package)
        return {'checkpoint_sha256':checkpoint,'accepted':True}


def _compact(c,t,key,directory,package):
    """Discard only owned materializations after immutable publication is durable."""
    checkpoint=digest(package['metadata'])
    materialize(c,package,pool(c).parent/'season-cache'/checkpoint)
    world=Path(directory)/'world'
    owner={'profile':PROFILE,'manifest_sha256':digest(package['manifest']),'directory':str(Path(directory).resolve())}
    if world.exists():
        if world.is_symlink() or lineage.check_signed(read_json(Path(directory)/'owner.json'),key)!=owner:
            raise ValueError('Unsafe season working-copy cleanup')
        objects.remove_owned(world,directory)
    cache=pool(c).parent/'season-cache'
    for child in cache.iterdir():
        if child.name!=checkpoint and objects.HASH.fullmatch(child.name) and child.is_dir() and not child.is_symlink():
            try:objects.remove_owned(child,cache)
            except PermissionError:pass  # retain a reader's locked cache until next acceptance.


def _reachable(c,package,proof):
    pending=[package['metadata']['anchor_sha256'],package['metadata']['state_sha256']]
    if package['metadata']['parent_node_sha256']:pending.append(package['metadata']['parent_node_sha256'])
    found=set()
    while pending:
        identity=pending.pop()
        if identity in found:continue
        found.add(identity);value=document(c,identity)
        if isinstance(value,dict) and 'metadata' in value:
            pending += [value['metadata']['state_sha256'],value['metadata']['anchor_sha256']]
            if value['metadata']['parent_node_sha256']:pending.append(value['metadata']['parent_node_sha256'])
        elif isinstance(value,dict) and 'legacy_files' in value:
            for descriptor in [*value['legacy_files'].values(),value['legacy_archive']]:
                if 'pages' in descriptor:found.update(descriptor['pages'])
                else:pending.append(descriptor['index'])
        elif isinstance(value,dict) and set(value)==FILES:
            for descriptor in value.values():
                if 'pages' in descriptor:found.update(descriptor['pages'])
                else:pending.append(descriptor['index'])
        elif isinstance(value,dict) and value.get('kind')=='season-page-index-1':
            if type(value.get('level')) is not int or not 0<=value['level']<=4 or len(value['children'])>64:
                raise ValueError('Invalid portable page index')
            if value['level']:pending.extend(value['children'])
            else:found.update(value['children'])
        if len(found)>250000:raise ValueError('Season archive object bound exceeded')
    return found


def export(registry,key,parent,archive,*,_session=None):
    import zipfile
    with (nullcontext(_session) if _session else lineage.access(registry,key,True)) as (c,t):
        info=parent_info(c,t,key,parent,require_head=False);package=info['package']
        proof=json.loads(c.execute('SELECT proof FROM accepted WHERE checkpoint=?',(info['checkpoint'],)).fetchone()[0])
        identities=_reachable(c,package,proof)
        if sum((pool(c)/(x+'.gz')).stat().st_size for x in identities)>8*1024**3:raise ValueError('Season portable archive exceeds 8 GiB')
        archive=Path(archive)
        if archive.exists():raise ValueError('Fresh season archive destination required')
        with tempfile.NamedTemporaryFile(dir=archive.parent,delete=False) as f:temporary=Path(f.name)
        try:
            with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as z:
                z.writestr('package.json',encode(package));z.writestr('proof.json',encode(proof))
                for identity in sorted(identities):
                    objects.get(pool(c),identity)
                    z.write(pool(c)/(identity+'.gz'),'objects/'+identity+'.gz')
            temporary.rename(archive)
        finally:temporary.unlink(missing_ok=True)
        return {'checkpoint':info['checkpoint'],'archive_bytes':archive.stat().st_size,'objects':len(identities)}


def restore(registry,key,archive,destination,*,full_audit=False):
    """Fresh independently reconstructed portable state; never changes accepted head."""
    import zipfile
    destination=Path(destination)
    with lineage.access(registry,key) as (c,t),lineage.staged_directory(destination) as stage:
        local_pool=stage/'objects';local_pool.mkdir()
        token=POOL_OVERRIDE.set(local_pool)
        try:
            with zipfile.ZipFile(archive) as z:
                entries=z.infolist();names=[i.filename for i in entries]
                if (len(entries)>250002 or len(set(names))!=len(names) or sum(i.file_size for i in entries)>8*1024**3
                    or not {'package.json','proof.json'}<=set(names)):
                    raise ValueError('Invalid or oversized season archive')
                for entry in entries:
                    name=entry.filename
                    if name in {'package.json','proof.json'}:
                        if entry.file_size>objects.MAX_OBJECT:raise ValueError('Oversized season metadata')
                        continue
                    identity=name.removeprefix('objects/').removesuffix('.gz')
                    if name!='objects/'+identity+'.gz' or not objects.HASH.fullmatch(identity) or entry.file_size>objects.MAX_OBJECT*2:
                        raise ValueError('Unsafe season archive entry')
                    (local_pool/(identity+'.gz')).write_bytes(z.read(entry))
                package=json.loads(z.read('package.json'));proof=json.loads(z.read('proof.json'))
            descriptor_binding(package)
            expected=_reachable(c,package,proof)
            if {p.stem for p in local_pool.iterdir()}!=expected:raise ValueError('Season archive inventory differs')
            if digest(package)!=proof['package_sha256'] or proof['metadata']!=package['metadata']:
                raise ValueError('Season portable package differs')
            anchor,nodes=chain(c,package,t,key,proof)
            world=materialize(c,package,stage/'world')
            report=store.validate(world,key,replay=full_audit)
            if report['world_sha256']!=package['metadata']['world_sha256']:raise ValueError('Restored season state differs')
            # Independently replay the last successor against its signed parent.
            m=package['metadata'];a=package['manifest']
            if m['parent_node_sha256']:
                parent=document(c,m['parent_node_sha256']);state=document(c,parent['metadata']['state_sha256'])
                parent_world=materialize(c,{'state':state},stage/'immediate-parent')
                info={'profile':PROFILE,'world':parent_world}
            else:
                info={'database':world/'parent.sqlite','checkpoint':a['immediate_parent_sha256']}
            target=stage/'independent';_start(info,target,key,a,t['seed']);apply(target,key,a)
            if not replay_matches(target/'database.sqlite',report['world_sha256'],m['database_sha256']):
                raise ValueError('Independent portable suffix replay differs')
            if full_audit:
                legacy=stage/'legacy';legacy.mkdir()
                for name,descriptor in anchor['legacy_files'].items():
                    if name not in lineage.FILES|{'manifest.json'}:raise ValueError('Invalid legacy anchor inventory')
                    objects.materialize(local_pool,descriptor,legacy/name)
                objects.materialize(local_pool,anchor['legacy_archive'],stage/'legacy.zip')
                if file_sha256(stage/'legacy.zip')!=anchor['nodes'][-1]['package_sha256']:raise ValueError('Legacy anchor archive differs')
                lineage.verify_payload(legacy,t,key)
            # Only one restored DB retained; replay/parent duplicates are disposable.
            objects.remove_owned(target,stage)
            if (stage/'immediate-parent').exists():objects.remove_owned(stage/'immediate-parent',stage)
            if (stage/'legacy').exists():objects.remove_owned(stage/'legacy',stage)
            (stage/'legacy.zip').unlink(missing_ok=True)
            write_json(stage/'restoration.json',{'checkpoint':digest(m),'independent_restore':True,'full_history_audit':full_audit})
        finally:POOL_OVERRIDE.reset(token)
    return {'checkpoint':digest(package['metadata']),'independent_restore':True,'full_history_audit':full_audit}


def backup(registry,key,destination,*,transfer=False):
    destination=Path(destination).resolve()
    with lineage.access(registry,key,True,allow_fenced=transfer) as (c,t):
        lineage.check_cursors(c,t,key)
        if not t['active']:
            if not transfer or t['transfer_target']!=str(destination):raise ValueError('Authority fenced for another destination')
            if destination.exists():
                saved=lineage.check_signed(read_json(destination/'handoff.json'),key)
                if saved['head']!=t['head'] or not saved['transfer']:raise ValueError('Transfer head changed')
                return {'ok':True,'head':t['head'],'source_fenced':True,'key_included':False}
        if c.execute("SELECT 1 FROM batches WHERE state NOT IN ('accepted','season_review_superseded')").fetchone():
            raise ValueError('Finish the pending execution before authority transfer')
        info,parent=current(c,t,key)
        if transfer and t['active']:
            c.execute('BEGIN IMMEDIATE')
            try:
                c.execute('UPDATE authority SET active=0,lease_epoch=lease_epoch+1,transfer_target=?',(str(destination),))
                lineage.seal_authority(c,key);c.commit()
            except BaseException:c.rollback();raise
            t=lineage.authority(c,key)
        with lineage.staged_directory(destination) as stage:
            import sqlite3
            with closing(sqlite3.connect(stage/'authority.sqlite')) as copy:
                c.backup(copy);copy.row_factory=sqlite3.Row
                if not transfer:
                    copy.execute('UPDATE authority SET active=0,transfer_target=NULL');lineage.seal_authority(copy,key);copy.commit()
            export(registry,key,parent,stage/'checkpoint.zip',_session=(c,t))
            proof=json.loads(c.execute('SELECT proof FROM accepted WHERE checkpoint=?',(t['head'],)).fetchone()[0])
            write_json(stage/'acceptance.json',proof['acceptance'])
            write_json(stage/'narration.json',lineage.signed(lineage.cursor_document(c,t),key))
            document={**lineage.identity(t),'action':'portable_accepted_career','storage_profile':PROFILE,
                'head':t['head'],'transfer':transfer,'lease_epoch':t['lease_epoch'],
                'files':{name:file_sha256(stage/name) for name in ('authority.sqlite','checkpoint.zip','acceptance.json','narration.json')}}
            write_json(stage/'handoff.json',lineage.signed(document,key))
        return {'ok':True,'head':t['head'],'source_fenced':transfer,'key_included':False}


def restore_backup(source,key,destination,*,expected_test_only,recover_lost_authority=False):
    source=Path(source);destination=Path(destination).resolve()
    doc=lineage.check_signed(read_json(source/'handoff.json'),key)
    names={'authority.sqlite','checkpoint.zip','acceptance.json','narration.json','handoff.json'}
    if (type(expected_test_only) is not bool or doc['test_only'] is not expected_test_only or doc['storage_profile']!=PROFILE
        or {p.name for p in source.iterdir()}!=names or any(p.is_symlink() for p in source.iterdir())
        or doc['files']!={name:file_sha256(source/name) for name in names-{'handoff.json'}}):
        raise ValueError('Corrupt or mixed-mode season authority backup')
    if not doc['transfer'] and not recover_lost_authority:raise ValueError('Explicit lost-authority acknowledgment required')
    with lineage.staged_directory(destination) as stage:
        registry=stage/'authority/career.sqlite';registry.parent.mkdir()
        shutil.copyfile(source/'authority.sqlite',registry)
        with lineage.access(registry,key) as (c,t):
            if t['head']!=doc['head'] or t['active'] or t['lease_epoch']!=doc['lease_epoch']:
                raise ValueError('Season authority was not fenced correctly')
        checkpoint=stage/'accepted-head'
        restore(registry,key,source/'checkpoint.zip',checkpoint)
        with lineage.access(registry,key) as (c,t):
            # Install authenticated immutable chunks, not a new signer or seed.
            for file in (checkpoint/'objects').iterdir():objects.put(pool(c),objects.get(checkpoint/'objects',file.stem))
            # Recover the exact package descriptor from the portable envelope.
            import zipfile
            with zipfile.ZipFile(source/'checkpoint.zip') as z:package=json.loads(z.read('package.json'))
            payload=checkpoint/'payload';payload.mkdir()
            write_json(payload/'checkpoint.json',package['metadata']);write_json(payload/'package.json',package)
            c.execute('UPDATE accepted SET path=? WHERE checkpoint=?',(str(checkpoint),t['head']))
            materialize(c,package,pool(c).parent/'season-cache'/t['head'])
            objects.remove_owned(checkpoint/'world',checkpoint);objects.remove_owned(checkpoint/'objects',checkpoint)
            write_json(checkpoint/'acceptance.json',read_json(source/'acceptance.json'))
            c.execute('UPDATE batches SET directory=? WHERE checkpoint=?',(str(checkpoint),t['head']))
            c.execute('UPDATE authority SET active=1,transfer_target=NULL,lease_epoch=lease_epoch+?',(int(recover_lost_authority),))
            lineage.seal_authority(c,key)
        lineage.import_cursor(registry,key,read_json(source/'narration.json'))
        with lineage.access(registry,key) as (c,t):
            c.execute('UPDATE accepted SET path=? WHERE checkpoint=?',(str(destination/'accepted-head'),t['head']))
            c.execute('UPDATE batches SET directory=? WHERE checkpoint=?',(str(destination/'accepted-head'),t['head']))
    return {'ok':True,'registry':str(destination/'authority/career.sqlite'),'accepted_parent':str(destination/'accepted-head'),
            'head':doc['head'],'test_only':expected_test_only}
