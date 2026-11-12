"""Read-only, checkpoint-bound analytics for registered careers."""

import base64
from contextlib import closing, contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile

from .. import lineage, season_lineage, season_objects, statistics
from ..db import connect_read_only
from ..history import canonical_json, digest
from .protocol import HASH

PROFILE = 'career-statistics-1'


@contextmanager
def accepted_snapshot(career, checkpoint):
    uri = Path(career.registry).resolve(strict=True).as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=1)) as c:
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA query_only=ON')
        c.execute('BEGIN')
        authority = lineage.authority(c, career.key)
        if (authority['career'] != career.career or bool(authority['test_only']) != career.test_only
                or not authority['active']):
            raise ValueError('Career identity differs')
        if checkpoint != authority['head']:
            raise statistics.QueryError('STALE_CHECKPOINT', 'Read bridge status and resubmit against the accepted head.')
        lineage.check_cursors(c, authority, career.key)
        cursors = {r['fixture']: (r['sequence'], r['result_sha']) for r in c.execute('SELECT * FROM cursors')}
        row = c.execute('SELECT path FROM accepted WHERE checkpoint=?', (checkpoint,)).fetchone()
        if row is None or not season_lineage.is_registered(row['path']):
            raise statistics.QueryError('UNSUPPORTED_CHECKPOINT', 'Use historical_results for older match history. Analytics requires a registered season.')
        package, _ = season_lineage.authenticated_package(c, authority, career.key, row['path'])
        pool = season_lineage.pool(c)
        metadata = package['metadata']
    # Neither query reads nor temporary cleanup can contend with production
    # materialization or pruning. Immutable chunks outlive the registry read.
    with tempfile.TemporaryDirectory(prefix='braga-statistics-') as tmp:
        database = Path(tmp) / 'database.sqlite'
        season_objects.materialize(pool, package['state']['database.sqlite'], database)
        with connect_read_only(database) as db:
            hidden = set()
            for row in db.execute("""SELECT fixture AS key,result_sha256 AS sha,
                         json_array_length(result_json,'$.events') AS n
                         FROM ms_executions WHERE result_json IS NOT NULL
                         UNION ALL
                         SELECT r.fixture_key,r.result_sha256,max(e.sequence)
                         FROM world_receipts r LEFT JOIN world_events e ON e.fixture_key=r.fixture_key
                         GROUP BY r.fixture_key,r.result_sha256"""):
                if not row['n'] or cursors.get(row['key']) != (row['n'], row['sha']):
                    hidden.add(row['key'])
            yield db, metadata, hidden


class Analytics:
    def __init__(self, career):
        self.career = career

    def cursor(self, binding, filters, offset):
        doc = {**binding, 'filters': filters, 'offset': offset}
        signed = lineage.signed(doc, self.career.key)
        return base64.urlsafe_b64encode(canonical_json(signed).encode()).decode()

    def decode(self, cursor):
        try:
            if type(cursor) is not str or not 1 <= len(cursor) <= 4096:
                raise ValueError()
            doc = lineage.check_signed(json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True)),
                                       self.career.key)
            if (set(doc) != {'profile', 'career', 'checkpoint', 'visibility', 'filters', 'offset'}
                    or doc['profile'] != PROFILE or doc['career'] != self.career.career
                    or not HASH.fullmatch(doc['checkpoint']) or not HASH.fullmatch(doc['visibility'])
                    or type(doc['offset']) is not int or doc['offset'] < 1 or not isinstance(doc['filters'], dict)):
                raise ValueError()
            return doc
        except (ValueError, TypeError, UnicodeError, KeyError, RecursionError):
            raise statistics.QueryError('INVALID_CURSOR', 'Use next_cursor from the preceding statistics page.') from None

    def query(self, args, checkpoint):
        try:
            if not isinstance(args, dict):
                raise statistics.QueryError('INVALID_FILTER', 'Supply a statistics filter object.')
            cursor = None
            if 'cursor' in args:
                if len(args) != 1:
                    raise statistics.QueryError('INVALID_FILTER', 'Send cursor alone to read the next page.')
                cursor = self.decode(args['cursor'])
                args = cursor['filters']
            statistics.validate(args)
            if cursor and cursor['checkpoint'] != checkpoint:
                raise statistics.QueryError('SNAPSHOT_MOVED', 'The career advanced. Restart the query with the original filters.')
            with accepted_snapshot(self.career, checkpoint) as (db, metadata, hidden):
                binding = {'profile': PROFILE, 'career': self.career.career,
                           'checkpoint': checkpoint, 'visibility': digest(sorted(hidden))}
                if cursor and cursor['visibility'] != binding['visibility']:
                    raise statistics.QueryError('SNAPSHOT_MOVED', 'Narration visibility changed. Restart the query.')
                rows, coverage = statistics.select(db, args, hidden, metadata['season'])
            offset = cursor['offset'] if cursor else 0
            page = []
            size = 0
            for row in rows[offset:offset + args.get('limit', 20)]:
                size += len(canonical_json(row).encode()) + 1
                if size > 30000:
                    break
                page.append(row)
            end = offset + len(page)
            if not page and end < len(rows):
                raise statistics.QueryError('RESULT_SIZE_LIMIT', 'The first row exceeds the reporting limit.')
            time_scope = ({'through_date': args['date_to']} if 'date_to' in args
                          else {'accepted_clock': metadata['clock']})
            return {'profile': PROFILE, 'read_only': True, 'accepted_checkpoint': checkpoint,
                    **time_scope, 'database_sha256': metadata['database_sha256'],
                    'filters': args, 'coverage': coverage, 'rows': page, 'offset': offset, 'total_rows': len(rows),
                    'next_cursor': self.cursor(binding, args, end) if end < len(rows) else None}
        except statistics.QueryError as error:
            return {'read_only': True, 'error': {'code': error.code, 'message': str(error)}}
        except (sqlite3.DatabaseError, OSError) as error:
            if (getattr(error, 'sqlite_errorcode', 0) & 255) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                return {'read_only': True, 'error': {'code': 'SNAPSHOT_BUSY', 'message': 'Read status before submitting a fresh query.'}}
            return {'read_only': True, 'error': {'code': 'SNAPSHOT_UNAVAILABLE',
                    'message': 'The accepted database could not be read. Report the issue to the worker operator.'}}
