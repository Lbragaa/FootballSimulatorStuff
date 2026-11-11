"""Replay the group-stage horizon in an isolated and nonpromotable timeline."""
import argparse
import json
from pathlib import Path
import secrets
from uuid import UUID, uuid5

from braga_era import lineage
from braga_era.bridge.__main__ import config
from braga_era.db import connect_read_only
from braga_era.multiseason import groups, store, timeline
from braga_era.multiseason.agenda import advance

SOURCE = 'c090fe185089a5fc5a1cf0a748a532ac499dba5abe204fa5282988a54ab68136'
SCOPE = UUID('81a9439e-698e-441a-9de9-74f308d6c21c')


def status(world):
    with connect_read_only(world/'database.sqlite') as db:
        edition = 'LIB:2028'
        row = db.execute("""SELECT stage FROM ms_fixtures WHERE edition=?
            AND stage LIKE 'GROUP:%' AND 'club:15' IN (home,away) LIMIT 1""", (edition,)).fetchone()
        pending = db.execute("""SELECT count(*) FROM ms_fixtures WHERE edition=?
            AND stage LIKE 'GROUP:%' AND status!='final'""", (edition,)).fetchone()[0]
        if not row or pending:
            return {'group_matches_remaining': pending, 'group_stage_complete': False}
        table = groups.table(db, edition, row[0])
        rank = next(i for i, club in enumerate(table, 1) if club['club']=='club:15')
        return {'group': row[0], 'rank': rank, 'group_matches_remaining': 0, 'group_stage_complete': True,
                'route': {1:'Libertadores knockout', 2:'Libertadores knockout',
                          3:'Sul-Americana playoff berth', 4:'eliminated'}[rank]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--private-directory', type=Path, required=True)
    parser.add_argument('--seed-mode', choices=('same', 'alternate'), default='alternate')
    parser.add_argument('--max-groups', type=int, default=150)
    args = parser.parse_args()
    root = args.private_directory.resolve(strict=True)
    key_path = root/'test-rehearsal.key'
    v = config(args.config)
    target = root/'candidate'
    if not target.exists():
        if not key_path.exists():
            with key_path.open('xb') as out:
                out.write(secrets.token_bytes(32))
        key = key_path.read_bytes()
        decision = timeline.rehearse(v['registry'], Path(v['key_file']).read_bytes(), SOURCE, target, key,
                                     seed_mode=args.seed_mode)
        print(json.dumps({'source_checkpoint': SOURCE, 'seed_sha256': decision['seed_sha256'],
                          'seed_mode': decision['seed_mode'], 'test_only': True}), flush=True)
    key = key_path.read_bytes()
    world = target/'world'
    _, marker = store.authenticated(world, key)
    if marker['decision']['seed_mode'] != args.seed_mode:
        raise ValueError('Resume with the seed mode recorded before kickoff')
    for index in range(args.max_groups + 1):
        report = status(world)
        if report['group_stage_complete'] or index == args.max_groups:
            validation = store.validate(world, key)
            result = {**report, 'test_only': True, 'verified': validation['independent_replay'],
                      'operation_count': validation['operations'], 'world_sha256': validation['world_sha256']}
            lineage.publish_json(root/f'verification-{validation["operations"]}.json', lineage.signed(result, key))
            print(json.dumps(result), flush=True)
            return
        advance(world, key, request_id=str(uuid5(SCOPE, f'{SOURCE}:{index}')), max_groups=1)
        if (index + 1) % 10 == 0:
            print(json.dumps({'test_groups_processed': index + 1, **status(world)}), flush=True)


if __name__ == '__main__':
    main()
