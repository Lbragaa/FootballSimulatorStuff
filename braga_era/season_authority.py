"""Exact-parent season review using the existing lineage registry and signer.

No new registry, key, seed, or accepted profile is introduced. The currently
available executor is DEV-MULTISEASON-2: only TEST authorities can authorize it.
Production successor registration deliberately remains unavailable.
"""

import json
from pathlib import Path
from uuid import UUID, uuid5

from . import lineage
from .db import connect_read_only, file_sha256
from .history import canonical_json as encode, digest
from .seasons import AcceptedSource, closure_report

PROFILE = "season-transition-review-1"


def policy():
    """Closed, proposed policy; approving ordinary 2027 gameplay does not approve it."""
    from .multiseason import store
    from .multiseason.offseason import POLICY
    return {"version": PROFILE, "season": 2027, "next_season": 2028,
            "closure": {"version": "season-lifecycle-proposal-1", "season": 2027,
                "next_season": 2028, "competitions": [
                    {"id": k, "minimum_completed": n, "cross_year": False,
                     "requires_champion": True}
                    for k, n in (("LEAGUE", 380), ("CDB", 61), ("LIB", 125),
                                 ("SULA", 141), ("CARIOCA", 5))]},
            "migration": store.proposed_policy(), "migration_schema_sha256": digest(store.DDL),
            "offseason": POLICY,
            "execution_profile": "DEV-MULTISEASON-2", "test_only": True,
            "production_acceptance_enabled": False}


def _parent(c, trusted, key, parent):
    info = lineage.parent_info(c, trusted, key, parent)
    if info['generation']:
        with connect_read_only(info['database']) as db:
            if db.execute('SELECT seed FROM world_info').fetchone()[0] != trusted['seed']:
                raise ValueError('Accepted parent career seed differs')
    return info


def _closure(info, c, trusted, key):
    report = closure_report(info['database'], policy()['closure'])
    lineage.check_cursors(c, trusted, key)
    cursors = {r['fixture']: r['sequence'] for r in c.execute('SELECT * FROM cursors')}
    with connect_read_only(info['database']) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        unrevealed = sum(cursors.get(r[0], 0) != r[1] for r in db.execute(
            'SELECT fixture_key,max(sequence) FROM world_events GROUP BY fixture_key')) if 'world_events' in tables else 0
    if unrevealed:
        report['blockers'].append('unrevealed_match_narration')
    report['unrevealed_matches'] = unrevealed
    report['ready_to_finalize'] = not report['blockers']
    return report


def inspect(career):
    """Read-only, spoiler-safe boundary, including with automatic mode disabled."""
    with lineage.access(career.registry, career.key) as (c, trusted):
        parent = career.root_parent if trusted['head'] == lineage.ROOT else Path(
            c.execute('SELECT path FROM accepted WHERE checkpoint=?', (trusted['head'],)).fetchone()[0])
        info = _parent(c, trusted, career.key, parent)
        report = _closure(info, c, trusted, career.key)
        claim = c.execute('SELECT batch FROM parent_claims WHERE parent=?', (info['checkpoint'],)).fetchone()
        transition = c.execute('SELECT manifest,decision,signature,state FROM batches WHERE id=?',
                               (claim[0],)).fetchone() if claim else None
        approved = False
        if transition and transition['state'] == 'season_authorized':
            manifest = json.loads(transition['manifest'])
            decision = lineage.check_signed({'document': json.loads(transition['decision']),
                                            'signature': transition['signature']}, career.key)
            if decision != authorization(manifest) or manifest != _manifest(c, trusted, career.key, parent, manifest['request_id']):
                raise ValueError('Season authorization differs from accepted parent')
            approved = True
        result = {'profile': PROFILE, 'season': 2027, 'next_season': 2028,
                'accepted_checkpoint': info['checkpoint'], 'closure': report,
                'phase': ('authorized_test_candidate_only' if approved else 'transition_approval_required')
                         if report['ready_to_finalize'] else 'season_not_closed',
                'policy_sha256': digest(policy()), 'test_policy_authorized': approved,
                'automatic_transition_allowed': False, 'production_transition_available': False,
                'blockers': ([] if report['ready_to_finalize'] else report['blockers']) +
                    ['production_season_profile_not_registered'],
                'next_action': 'Review a separate exact-parent season policy; existing automatic gameplay grants do not authorize a new season.'}
        if report['ready_to_finalize']:
            from .payroll import financial_statement
            with connect_read_only(info['database']) as db:
                result['season_review'] = {
                    'season': 2027, 'complete': True,
                    'standings': [dict(r) for r in db.execute(
                        'SELECT c.id,c.name,c.points,c.played,c.wins,c.draws,c.losses,c.gf,c.ga '
                        'FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027 '
                        'ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name')],
                    'trophies': [dict(r) for r in db.execute(
                        'SELECT h.competition,h.club_key,c.name FROM world_champions h '
                        'JOIN world_clubs c ON c.key=h.club_key ORDER BY h.competition')],
                    'finances': financial_statement(db),
                    'financial_scope': 'Recorded restricted account and incremental obligations; missing base accounts remain unknown.'}
        return result


def _manifest(c, trusted, key, parent, request_id):
    if str(UUID(request_id)) != request_id:
        raise ValueError('Canonical season request UUID required')
    info = _parent(c, trusted, key, parent)
    report = _closure(info, c, trusted, key)
    if not report['ready_to_finalize']:
        raise ValueError('Season closure blocked: ' + ','.join(report['blockers']))
    return {**lineage.identity(trusted), 'transition_profile': PROFILE,
            'request_id': request_id, 'immediate_parent_sha256': info['checkpoint'],
            'immediate_parent_database_sha256': file_sha256(info['database']),
            'career_seed_sha256': digest(trusted['seed']), 'seed_policy': lineage.SEED_POLICY,
            'generation': info['generation'] + 1, 'season_policy': policy(),
            'closure_sha256': digest(report), 'lease_epoch': trusted['lease_epoch'],
            'production_acceptance_enabled': False}


def prepare(registry, key, parent, request_id):
    with lineage.access(registry, key) as (c, trusted):
        return _manifest(c, trusted, key, parent, request_id)


def authorization(manifest):
    return {'action': 'authorize_exact_season_transition', 'profile': PROFILE,
            'career': manifest['career'], 'test_only': manifest['test_only'],
            'manifest_sha256': digest(manifest),
            'parent_checkpoint': manifest['immediate_parent_sha256'],
            'policy_sha256': digest(manifest['season_policy']),
            'career_seed_sha256': manifest['career_seed_sha256'],
            'automatic_transition_allowed': False,
            'successor_acceptance_required': True}


def authorize(registry, key, parent, manifest, approval, *, crash=None):
    """Atomic policy approval/parent fencing, never delegated by ordinary play.

    Existing parent_claims prevent both a second transition and a competing
    ordinary batch. Proof is persisted before migration. Exact retries reuse it.
    """
    with lineage.access(registry, key, True) as (c, trusted):
        if not trusted['test_only']:
            raise ValueError('Current season execution policy is TEST-only; production registration unavailable')
        expected = _manifest(c, trusted, key, parent, manifest['request_id'])
        if manifest != expected or lineage.check_signed(approval, key) != authorization(expected):
            raise ValueError('Exact signed season policy approval required')
        identifier = 'season:' + manifest['request_id']
        c.execute('BEGIN IMMEDIATE')
        try:
            old = c.execute('SELECT * FROM batches WHERE id=?', (identifier,)).fetchone()
            claim = c.execute('SELECT batch FROM parent_claims WHERE parent=?',
                              (manifest['immediate_parent_sha256'],)).fetchone()
            if old:
                if (old['manifest'] != encode(manifest) or old['decision'] != encode(approval['document'])
                    or old['signature'] != approval['signature'] or old['state'] != 'season_authorized'
                    or not claim or claim[0] != identifier):
                    raise ValueError('Season request/claim changed')
            else:
                if claim:
                    raise ValueError('Accepted parent already claimed by another execution')
                c.execute('INSERT INTO parent_claims VALUES(?,?)', (manifest['immediate_parent_sha256'], identifier))
                c.execute("INSERT INTO batches VALUES(?,?,?,?,?,'season_authorized',NULL,?,NULL,NULL)",
                          (identifier, manifest['immediate_parent_sha256'], encode(manifest),
                           encode(approval['document']), approval['signature'], str(Path(parent).resolve())))
                c.execute('INSERT INTO decisions(batch,kind,document,signature) VALUES(?,?,?,?)',
                          (identifier, 'season_policy', encode(approval['document']), approval['signature']))
            if crash == 'before_commit':
                raise RuntimeError('Injected season approval crash before commit')
            c.commit()
        except BaseException:
            c.rollback()
            raise
        if crash == 'after_commit':
            raise RuntimeError('Injected season approval crash after commit')
        return lineage.signed({'profile': PROFILE, 'manifest_sha256': digest(manifest),
                               'policy_authorized': True, 'executed': False,
                               'successor_accepted': False}, key)


def rehearse(registry, key, request_id, destination):
    """Execute only the reviewed migration on a disposable TEST candidate.

    Retains the actual lineage seed and current parent. Does not publish a new
    accepted head or claim the development executor is a registered successor.
    """
    from .multiseason import store
    with lineage.access(registry, key, True) as (c, trusted):
        if not trusted['test_only']:
            raise ValueError('TEST registry required')
        row = c.execute('SELECT * FROM batches WHERE id=?', ('season:' + request_id,)).fetchone()
        if not row or row['state'] != 'season_authorized':
            raise ValueError('Separate season policy authorization required')
        manifest = json.loads(row['manifest'])
        if manifest != _manifest(c, trusted, key, row['parent_path'], request_id):
            raise ValueError('Season parent or policy changed')
        approval = lineage.check_signed({'document': json.loads(row['decision']), 'signature': row['signature']}, key)
        if approval != authorization(manifest):
            raise ValueError('Season approval changed')
        claim = c.execute('SELECT batch FROM parent_claims WHERE parent=?', (trusted['head'],)).fetchone()
        if not claim or claim[0] != row['id']:
            raise ValueError('Season parent claim changed')
        destination = Path(destination).resolve()
        if row['directory'] and Path(row['directory']) != destination:
            raise ValueError('Resume the original season candidate directory')
        c.execute('UPDATE batches SET directory=? WHERE id=?', (str(destination), row['id']))
        info = _parent(c, trusted, key, row['parent_path'])
        source = AcceptedSource(info['database'], info['checkpoint'], manifest['immediate_parent_database_sha256'])
        migration = store.statement(source, manifest['season_policy']['migration'], trusted['seed'])
        if not destination.exists():
            store.create(source, destination, seed=trusted['seed'], policy=manifest['season_policy']['migration'],
                         decision=migration, signature=lineage.sign(key, migration), test_key=key)
        _, marker = store.authenticated(destination, key)
        if marker['decision'] != migration:
            raise ValueError('Resumed candidate differs from exact transition')
        with connect_read_only(destination/'database.sqlite') as db:
            permitted = [dict(r) for r in db.execute('SELECT * FROM ms_operations ORDER BY sequence')]
        args = {'season': 2028}
        child_id = str(uuid5(UUID(request_id), 'prepare_season:2028'))
        if permitted and (len(permitted) != 1 or permitted[0]['request_id'] != child_id
                          or permitted[0]['kind'] != 'prepare_season' or permitted[0]['args_json'] != encode(args)):
            raise ValueError('Unapproved operations in season candidate')
        store.run(destination, key, child_id, 'prepare_season', args)
        report = store.validate(destination, key)
        return lineage.signed({'profile': PROFILE, 'manifest_sha256': digest(manifest),
                               'candidate': report, 'successor_accepted': False,
                               'blocker': 'production_season_profile_not_registered'}, key)
