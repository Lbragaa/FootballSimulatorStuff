"""Authenticated, cursor-free historical reads and bounded reporting pages."""

import base64
import json
from pathlib import Path

from .. import lineage
from ..db import connect_read_only, file_sha256
from ..history import canonical_json as encode
from ..results import Projection, ResultsError, validate_filters, round_number

PROFILE = 'historical-results-1'


class HistoricalResults:
    def __init__(self, career):
        self.career = career

    def snapshot(self, checkpoint=None, visibility=None):
        self.career.identity()  # existing identity/mode/fencing checks; no control privilege needed.
        with lineage.access(self.career.registry, self.career.key) as (c, trusted):
            checkpoint = checkpoint or trusted['head']
            if checkpoint == lineage.ROOT:
                parent = getattr(self.career, 'root_parent', None)
                if parent is None:
                    raise ResultsError('MISSING_ACCEPTED_PARENT', 'The authenticated accepted database is not installed.')
            else:
                row = c.execute('SELECT path FROM accepted WHERE checkpoint=?', (checkpoint,)).fetchone()
                if row is None:
                    raise ResultsError('UNREGISTERED_CHECKPOINT', 'The results page is not from this accepted career.')
                parent = Path(row[0])
            info = lineage.parent_info(c, trusted, self.career.key, parent, require_head=False)
            cursors = {r['fixture']: r['sequence'] for r in c.execute('SELECT * FROM cursors')}
            lineage.check_cursors(c, trusted, self.career.key)
        with connect_read_only(info['database']) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if visibility is None:
                visibility = [r['fixture_key'] for r in db.execute(
                    "SELECT e.fixture_key,max(e.sequence) AS n FROM world_events e JOIN world_fixtures f ON f.key=e.fixture_key "
                    "WHERE f.home='club:15' OR f.away='club:15' GROUP BY e.fixture_key")
                    if cursors.get(r['fixture_key']) == r['n']] if 'world_events' in tables else []
            projection = Projection(db, revealed=visibility)
        metadata = {'profile': PROFILE, 'accepted_checkpoint': checkpoint, 'accepted_clock': info['clock'],
                    'database_sha256': file_sha256(info['database']), 'career': self.career.career,
                    'test_only': self.career.test_only, 'read_only': True}
        return projection, metadata, sorted(visibility)

    def token(self, metadata, args, offset, visibility):
        value = {'profile': PROFILE, 'career': self.career.career, 'test_only': self.career.test_only,
                 'checkpoint': metadata['accepted_checkpoint'], 'filters': args, 'offset': offset, 'visibility': visibility}
        return base64.urlsafe_b64encode(encode(lineage.signed(value, self.career.key)).encode()).decode()

    def decode(self, token):
        try:
            raw = base64.b64decode(token, altchars=b'-_', validate=True)
            value = lineage.check_signed(json.loads(raw), self.career.key)
            if (set(value) != {'profile', 'career', 'test_only', 'checkpoint', 'filters', 'offset', 'visibility'}
                or value['profile'] != PROFILE or value['career'] != self.career.career
                or value['test_only'] is not self.career.test_only or type(value['offset']) is not int or value['offset'] < 0
                or not isinstance(value['visibility'], list) or any(not isinstance(v, str) for v in value['visibility'])):
                raise ValueError()
            validate_filters(value['filters'])
            if 'cursor' in value['filters']:
                raise ValueError()
            return value
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise ResultsError('INVALID_CURSOR', 'Use the unchanged next_cursor from the preceding historical-results page.') from None

    def query(self, args):
        try:
            validate_filters(args)
            filters = {k: v for k, v in args.items() if k != 'cursor'}
            offset, checkpoint, visibility = 0, None, None
            if 'cursor' in args:
                value = self.decode(args['cursor'])
                if filters and filters != value['filters']:
                    raise ResultsError('CURSOR_FILTER_MISMATCH', 'Use cursor alone or repeat exactly the original filters.')
                filters, offset, checkpoint, visibility = value['filters'], value['offset'], value['checkpoint'], value['visibility']
            projection, meta, visibility = self.snapshot(checkpoint, visibility)
            rows, selection = projection.select(filters)
            limit = filters.get('limit', 20)
            page, ties = [], {}
            for row in rows[offset:offset+limit]:
                candidate = {**ties}
                if row['tie_id'] in projection.ties:
                    candidate[row['tie_id']] = projection.ties[row['tie_id']]
                if len(encode({'matches': page + [row], 'ties': list(candidate.values())}).encode()) > 36000:
                    break
                page.append(row)
                ties = candidate
            if rows[offset:] and not page:
                raise ResultsError('RESULT_SIZE_LIMIT', 'A recorded match exceeds the public reporting bound; inspect source metadata locally.')
            more = offset + len(page) < len(rows)
            warnings = [
                'Only recorded matches are available; season coverage is not a claim that a complete historical season was imported.',
                'Missing dates/scores stay unknown. Date filters exclude undated records; no scores are inferred from tables or prose.',
                'Unfinished Vasco narration withholds that match score and tie outcome; historical reads never consume a cursor.',
            ]
            return {**meta, 'filters': filters, 'selection': selection, 'matches': page, 'ties': list(ties.values()),
                    'coverage': projection.coverage(), 'offset': offset, 'returned': len(page), 'has_more': more,
                    'next_cursor': self.token(meta, filters, offset + len(page), visibility) if more else None,
                    'limitations': warnings, 'notice': None if rows else 'No recorded matches match this selection.'}
        except ResultsError as error:
            return {'error': {'code': error.code, 'message': error.message}, 'read_only': True}

    @staticmethod
    def compact(row):
        return {k: v for k, v in {
            'id': row['id'], 'date': row['date'], 'competition': row['competition'], 'season': row['season'],
            'stage': row['stage'], 'round': row['round'], 'leg': row['leg'],
            'home': row['home']['name'] if row['home'] else None,
            'away': row['away']['name'] if row['away'] else None,
            'status': row['status'], 'score': row['score'], 'resolution': row['resolution'],
            'score_availability': row.get('score_availability'), 'tie_id': row['tie_id']}.items() if v is not None}

    def episode(self, op, budget):
        """One compact section; omitted results always have a pinned retrieval page."""
        projection, meta, visibility = self.snapshot()
        keys = list(dict.fromkeys(op.get('report_pending', []) + op['consumed']))
        relevant = [projection.records[k] for k in keys if k in projection.records]
        if not relevant:
            return [], []
        dates = [r['date'][:10] for r in relevant if r['date']]
        filters = {'date_from': min(dates), 'date_to': max(dates), 'include_pending': True, 'limit': 50} if dates else {'limit': 50}
        retrieval = {'command': 'historical_results', 'args': {'cursor': self.token(meta, filters, 0, visibility)}}
        if op.get('target') and not op['target_done']:
            return [{'section': 'results_deferred', 'reason': 'Vasco narration must reach its final whistle before other scores.',
                     'retrieve_all': retrieval}], keys
        result = {'section': 'episode_results', 'accepted_checkpoint': meta['accepted_checkpoint'],
                  'round_results': None, 'other_results': [], 'ties': [], 'omitted': 0, 'omitted_ties': 0, 'retrieve_all': retrieval}
        round_ids = set()
        if op.get('round') and op['target_done']:
            target = projection.records.get(op['target'])
            season = target['season'] if target else None
            rows, selection = projection.select({'competition': 'Brasileirão', 'season': season,
                'round': round_number(op['round']), 'include_pending': True})
            round_filters = {'competition': 'Brasileirão', 'season': season, 'round': round_number(op['round']), 'include_pending': True, 'limit': 50}
            result['retrieve_round'] = {'command': 'historical_results', 'args': {'cursor': self.token(meta, round_filters, 0, visibility)}}
            result['round_results'] = {'competition': 'Brasileirão', 'season': season, 'round': round_number(op['round']),
                'complete': len(rows) == 10 and selection['recorded_selection_complete'] and all(r['score'] is not None for r in rows),
                'recorded_fixtures': len(rows),
                'matches': [self.compact(r) for r in rows]}
            round_ids = {r['id'] for r in rows}
        others = [r for r in relevant if r['id'] not in round_ids]
        others.sort(key=lambda r: (r['date'] or '', r['id']))
        for row in others:
            value = self.compact(row)
            if len(encode(result).encode()) + len(encode(value).encode()) + 1000 > budget:
                result['omitted'] += 1
            else:
                result['other_results'].append(value)
        tie_ids = {r['tie_id'] for r in relevant if r['tie_id']}
        for key in sorted(tie_ids):
            tie = projection.ties.get(key)
            if tie and len(encode(result).encode()) + len(encode(tie).encode()) + 500 <= budget:
                result['ties'].append(tie)
            elif tie:
                result['omitted_ties'] += 1
        result['exhaustive'] = result['omitted'] == 0 and result['omitted_ties'] == 0
        if len(encode(result).encode()) > budget:
            # Preserve narration and tables when an unusually large presentation
            # leaves too little space even for all ten compact round results.
            result = {'section': 'episode_results', 'exhaustive': False, 'omitted': len(relevant),
                      'reason': 'Transport size bound; retrieve all recorded results using this pinned page.', 'retrieve_all': retrieval,
                      **({'retrieve_round': result['retrieve_round']} if 'retrieve_round' in result else {})}
        return [result], []
