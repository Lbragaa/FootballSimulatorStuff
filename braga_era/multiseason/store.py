"""Authenticated TEST-only migrations, transactional commands and full independent replay."""
from contextlib import closing, contextmanager
import hmac
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from uuid import UUID

from ..checkpoints import staged_directory, write_json, read_json, manifest_for
from ..db import connect_read_only, file_sha256
from ..forward import sign
from ..history import canonical_json as encode, digest
from ..seasons import AcceptedSource, source_manifest, closure_report, fingerprints
from . import PROFILE, POLICY
from .schema import DDL, TABLES, MUTABLE_INHERITED, VERSION

MAX_PACKAGE_BYTES = 2 * 1024**3

def proposed_policy():
    return {"version": POLICY, "test_only": True, "minimum_rest_hours": 72,
            "blackout": ["12-22", "01-05"], "engine": "braga-headless-1.1.0",
            "knockout": "braga-knockout-2.1.0", "annual_attribute_change_bound": 1.5,
            "economics": "recorded-money-and-explicit-TEST-income-proposals-1"}


def statement(source, policy, seed):
    if policy != proposed_policy() or not isinstance(seed,str) or not seed:
        raise ValueError("Unsupported proposed policy or missing committed career seed")
    return {"action":"migrate_development_season", "profile":PROFILE, "test_only":True,
            "parent_checkpoint":source.checkpoint, "parent_sha256":source.database_sha256,
            "policy_sha256":digest(policy), "seed_sha256":digest(seed), "migration_sha256":digest(DDL)}


def create(source, destination, *, seed, policy, decision, signature, test_key):
    """No production flag exists. A migration decision binds all immutable inputs."""
    if not isinstance(source, AcceptedSource) or decision != statement(source,policy,seed) or not hmac.compare_digest(sign(test_key,decision), signature):
        raise ValueError("Exact signed TEST-only migration decision required")
    if file_sha256(source.database) != source.database_sha256:
        raise ValueError("Parent bytes changed")
    # First migrated season must actually be finished, not merely dated December.
    closure_policy = {"version":"season-lifecycle-proposal-1","season":2027,"next_season":2028,
        "competitions":[{"id":k,"minimum_completed":n,"cross_year":False,"requires_champion":True}
                        for k,n in (("LEAGUE",380),("CDB",61),("LIB",125),("SULA",141),("CARIOCA",5))]}
    closure = closure_report(source.database, closure_policy)
    if not closure["ready_to_finalize"]:
        raise ValueError("2027 closure not validated: " + ','.join(closure['blockers']))
    baseline = source_manifest(source.database)
    with staged_directory(Path(destination)) as stage:
        shutil.copyfile(source.database, stage/'parent.sqlite')
        shutil.copyfile(source.database, stage/'database.sqlite')
        if file_sha256(stage/'parent.sqlite') != source.database_sha256 or file_sha256(stage/'database.sqlite') != source.database_sha256:
            raise ValueError("Parent changed during copy")
        write_json(stage/'development.json', {"profile":PROFILE,"test_only":True,"acceptance_eligible":False,
            "parent":baseline,"decision":decision,"signature":signature,"seed":seed,"policy":policy})
        with closing(sqlite3.connect(stage/'database.sqlite')) as c:
            c.executescript('BEGIN IMMEDIATE;'+DDL)
            clock = c.execute('SELECT clock FROM world_info').fetchone()[0]
            c.execute('INSERT INTO ms_meta VALUES(1,?,?,?,?,?,?,1)',(PROFILE,source.checkpoint,source.database_sha256,encode(policy),seed,clock))
            c.execute('INSERT INTO ms_migrations VALUES(?,?,?)',(VERSION,digest(DDL),source.database_sha256))
            c.execute('INSERT INTO ms_seasons VALUES(2027,?,?)',('archived',encode({"parent":baseline,"closure":closure})))
            for row in c.execute('SELECT * FROM transfer_contracts').fetchall():
                player=c.execute('SELECT club_key FROM world_players WHERE id=?',(row[0],)).fetchone()
                if player:
                    from ..payroll import cents
                    c.execute('INSERT INTO ms_contracts VALUES(?,?,?,?,?,?,?,?)',(f'legacy:{row[0]}',row[0],player[0],row[1],row[2],cents(row[3]),'active',encode({'source':'transfer_contracts','historical_terms_unchanged':True})))
            c.commit()
    return validate(destination, test_key, replay=False)


def authenticated(directory, test_key):
    directory=Path(directory).resolve()
    marker=read_json(directory/'development.json')
    if (marker.get('profile')!=PROFILE or marker.get('test_only') is not True or marker.get('acceptance_eligible') is not False
        or marker['policy']!=proposed_policy() or not hmac.compare_digest(marker['signature'],sign(test_key,marker['decision']))):
        raise ValueError('Not an authenticated nonpromotable multi-season candidate')
    source=AcceptedSource(directory/'parent.sqlite',marker['decision']['parent_checkpoint'],marker['parent']['database_sha256'])
    if (marker['decision']!=statement(source,marker['policy'],marker['seed'])
        or any(Path(str(source.database)+suffix).exists() for suffix in ('-wal','-journal'))
        or file_sha256(source.database)!=source.database_sha256):
        raise ValueError('Parent, policy, seed or migration changed')
    return directory,marker


@contextmanager
def connection(directory, test_key):
    directory,marker=authenticated(directory,test_key)
    with closing(sqlite3.connect(directory/'database.sqlite',timeout=10,isolation_level=None)) as c:
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA synchronous=FULL')
        meta=c.execute('SELECT * FROM ms_meta').fetchone()
        if not meta or (meta['profile'],meta['parent_checkpoint'],meta['parent_sha256'],meta['policy_json'],meta['seed'],meta['test_only'])!=(
            PROFILE,marker['decision']['parent_checkpoint'],marker['parent']['database_sha256'],encode(marker['policy']),marker['seed'],1):
            raise ValueError('Multi-season committed identity changed')
        yield c,marker


def run(directory, test_key, request_id, kind, args, *, crash=None):
    from .operations import apply
    if str(UUID(request_id))!=request_id:
        raise ValueError('Canonical request UUID required')
    # Canonical copies prevent the caller changing an input while it is committed.
    args=json.loads(encode(args))
    with connection(directory,test_key) as (c,marker):
        c.execute('BEGIN IMMEDIATE')
        try:
            old=c.execute('SELECT * FROM ms_operations WHERE request_id=?',(request_id,)).fetchone()
            if old:
                if old['kind']!=kind or old['args_json']!=encode(args):raise ValueError('Request identity reused')
                original={'request_id':request_id,'kind':kind,'args':args,'response':json.loads(old['response_json']),'previous':old['previous_sha256']}
                if digest(original)!=old['sha256'] or not hmac.compare_digest(sign(test_key,original),old['signature']):raise ValueError('Committed operation response changed')
                return json.loads(old['response_json'])
            if kind not in {'play_group','begin_run'} and c.execute("SELECT 1 FROM ms_fixtures WHERE status='claimed' LIMIT 1").fetchone():
                raise ValueError('Resume the committed match group before changing the world')
            response=json.loads(encode(apply(c,kind,args)))
            previous=c.execute('SELECT sha256 FROM ms_operations ORDER BY sequence DESC LIMIT 1').fetchone()
            previous=previous[0] if previous else digest(marker['decision'])
            document={'request_id':request_id,'kind':kind,'args':args,'response':response,'previous':previous}
            c.execute('INSERT INTO ms_operations(request_id,kind,args_json,response_json,previous_sha256,sha256,signature) VALUES(?,?,?,?,?,?,?)',
                (request_id,kind,encode(args),encode(response),previous,digest(document),sign(test_key,document)))
            if crash=='before_commit':raise RuntimeError('Injected multi-season crash before commit')
            c.commit()
            if crash=='after_commit':raise RuntimeError('Injected multi-season crash after commit')
            return response
        except BaseException:
            c.rollback();raise


def validate(directory, test_key, *, replay=True):
    directory,marker=authenticated(directory,test_key)
    if source_manifest(directory/'parent.sqlite')!=marker['parent']:raise ValueError('Archived parent manifest changed')
    with connect_read_only(directory/'database.sqlite') as c, connect_read_only(directory/'parent.sqlite') as parent:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Multi-season SQLite integrity failure')
        if c.execute("SELECT 1 FROM ms_fixtures WHERE status='claimed' LIMIT 1").fetchone():
            raise ValueError('Incomplete claimed group cannot be a validated checkpoint')
        inherited=fingerprints(parent)
        expected=fingerprints(c)
        if set(expected)!=set(inherited)|TABLES:raise ValueError('Unexpected migration table inventory')
        for table in set(inherited)-MUTABLE_INHERITED:
            if expected[table]!=inherited[table]:raise ValueError('Protected historical table changed: '+table)
        for row in parent.execute('SELECT * FROM world_clubs'):
            child=c.execute('SELECT * FROM world_clubs WHERE key=?',(row['key'],)).fetchone()
            if child is None or tuple(child)!=tuple(row):raise ValueError('Inherited club identity or strength changed')
        # A schema fingerprint is needed too: adding a trigger/index is not harmless.
        with closing(sqlite3.connect(':memory:')) as schema:
            schema.executescript(DDL)
            objects=lambda db:{r[0]:tuple(r) for r in db.execute("SELECT name,type,sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")}
            if objects(c)!={**objects(parent),**objects(schema)}:raise ValueError('Unexpected multi-season schema change')
        migration=c.execute('SELECT * FROM ms_migrations').fetchall()
        if [tuple(r) for r in migration]!=[(VERSION,digest(DDL),marker['parent']['database_sha256'])]:raise ValueError('Migration commitment differs')
        operations=[dict(r) for r in c.execute('SELECT * FROM ms_operations ORDER BY sequence')]
        previous=digest(marker['decision'])
        for number,row in enumerate(operations,1):
            doc={'request_id':row['request_id'],'kind':row['kind'],'args':json.loads(row['args_json']),
                 'response':json.loads(row['response_json']),'previous':previous}
            if row['sequence']!=number or row['previous_sha256']!=previous or row['sha256']!=digest(doc) or not hmac.compare_digest(row['signature'],sign(test_key,doc)):raise ValueError('Operation chain changed')
            previous=row['sha256']
    if replay:
        with tempfile.TemporaryDirectory(dir=directory.parent,prefix='.ms-independent-') as temp:
            target=Path(temp)/'replay'
            source=AcceptedSource(directory/'parent.sqlite',marker['decision']['parent_checkpoint'],marker['parent']['database_sha256'])
            create(source,target,seed=marker['seed'],policy=marker['policy'],decision=marker['decision'],signature=marker['signature'],test_key=test_key)
            for row in operations:
                if run(target,test_key,row['request_id'],row['kind'],json.loads(row['args_json']))!=json.loads(row['response_json']):raise ValueError('Independent operation response differs')
            with connect_read_only(target/'database.sqlite') as c:
                if fingerprints(c)!=expected:raise ValueError('Independent multi-season replay differs')
    return {'profile':PROFILE,'ok':True,'test_only':True,'acceptance_eligible':False,
            'operations':len(operations),'world_sha256':digest(expected),'independent_replay':replay}


def export(directory, destination, test_key):
    """Portable directory package; no production publication/promotion API."""
    directory=Path(directory)
    if sum((directory/n).stat().st_size for n in ('parent.sqlite','database.sqlite','development.json'))>MAX_PACKAGE_BYTES:
        raise ValueError('Multi-season package exceeds the 2 GiB development bound; explicit archive compaction policy required')
    # Authenticate source/history/signatures and pin its complete fingerprint.
    # The copied staging package is then independently replayed before atomic
    # publication. Replaying the same source as well duplicates that proof.
    before=validate(directory,test_key,replay=False)
    with staged_directory(Path(destination)) as stage:
        for name in ('parent.sqlite','database.sqlite','development.json'):shutil.copyfile(directory/name,stage/name)
        report=validate(stage,test_key)
        if report!={**before,'independent_replay':True}:raise ValueError('Candidate changed during export')
        write_json(stage/'verification.json',report)
        write_json(stage/'manifest.json',manifest_for(stage))
    return report


def restore(package, destination, test_key):
    package=Path(package)
    if set(p.name for p in package.iterdir())!={'parent.sqlite','database.sqlite','development.json','verification.json','manifest.json'}:
        raise ValueError('Unexpected multi-season package inventory')
    if any(p.is_symlink() or not p.is_file() for p in package.iterdir()) or sum(p.stat().st_size for p in package.iterdir())>MAX_PACKAGE_BYTES:
        raise ValueError('Unsafe or oversized multi-season package')
    if any((package/n).stat().st_size>5*1024**2 for n in ('development.json','manifest.json','verification.json')):
        raise ValueError('Oversized multi-season metadata')
    if read_json(package/'manifest.json')!=manifest_for(package):raise ValueError('Portable manifest differs')
    with staged_directory(Path(destination)) as stage:
        for name in ('parent.sqlite','database.sqlite','development.json'):shutil.copyfile(package/name,stage/name)
        report=validate(stage,test_key)
        if report!=read_json(package/'verification.json'):raise ValueError('Independent restoration differs')
    return report
