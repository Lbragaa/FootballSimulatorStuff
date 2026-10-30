"""Read-only historical projection of heterogeneous accepted match records.

No result is inferred from standings, prose, events or a championship total.
Native rows and forward mirrors are joined by their recorded source identities.
"""

from collections import Counter
from datetime import date
import re
import unicodedata


def fold(value):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in unicodedata.normalize('NFKD', str(value)).lower()
                     if not unicodedata.combining(c))).split())


COMPETITIONS = {
    'LEAGUE': ('Brasileirão', ('brasileirao', 'brasileirao serie a', 'campeonato brasileiro', 'league')),
    'CDB': ('Copa do Brasil', ('copa do brasil', 'cdb')),
    'LIB': ('Copa Libertadores', ('libertadores', 'copa libertadores', 'lib')),
    'SULA': ('Copa Sul-Americana', ('sudamericana', 'sul americana', 'copa sul americana', 'sula')),
    'CARIOCA': ('Campeonato Carioca', ('carioca', 'campeonato carioca')),
    'SERIE_B': ('Brasileirão Série B', ('serie b','brasileirao serie b')),
    'SUPERCOPA': ('Supercopa do Brasil', ('supercopa','supercopa do brasil')),
    'RECOPA': ('Recopa Sul-Americana', ('recopa','recopa sul americana')),
    'ACCESS': ('Prospective access qualification', ('access','prospective access qualification')),
    'STATE': ('Proposed state championship', ('state','proposed state championship')),
}


def competition(value):
    name = fold(re.sub(r'\b(?:19|20)\d{2}\b', '', str(value)))
    for key, (label, aliases) in COMPETITIONS.items():
        if name in aliases or name == fold(key):
            return key, label
    return name, re.sub(r'\s+(?:19|20)\d{2}$', '', str(value))


def stage(value):
    normalized = fold(value)
    if normalized.startswith('cdb sf'):
        return 'SF'
    for name, aliases in {
        'QF': ('qf', 'quartas', 'quartas de final', 'quarterfinal', 'quarterfinals', 'quarter finals'),
        'SF': ('sf', 'semifinal', 'semifinais', 'semifinals', 'semi finals', 'sf 1st leg', 'sf 2nd leg'),
        'FINAL': ('final', 'final unica', 'finals'),
        'R16': ('r16', 'oitavas', 'oitavas de final', 'round of 16'),
        'R32': ('r32', 'fase 5 32 clubes', 'round of 32'),
        'PO': ('po', 'playoffs', 'playoff', 'play offs'),
        'GROUP': ('group', 'groups', 'group stage', 'fase de grupos'),
        'NATIONAL_PRE': ('national pre','national preliminary','national qualifying'),
    }.items():
        if normalized in aliases:
            return name
    return str(value)


def round_number(value):
    match = re.fullmatch(r'(?:r|round\s*|rodada\s*)?0*(\d+)(?:-postponed)?', str(value).lower())
    return int(match[1]) if match else None


class ResultsError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


FILTERS = {'competition', 'season', 'round', 'stage', 'leg', 'date', 'date_from', 'date_to',
           'club', 'recent', 'limit', 'include_pending', 'cursor'}


def validate_filters(args):
    if not isinstance(args, dict) or set(args) - FILTERS:
        raise ResultsError('UNSUPPORTED_FILTER', 'Use only the documented historical-results filters.')
    for key, value in args.items():
        if key in {'competition', 'stage', 'club'}:
            if not isinstance(value, str) or not value.strip() or len(value) > 100:
                raise ResultsError('INVALID_FILTER', f'{key} must be a nonempty name of at most 100 characters.')
        elif key in {'season', 'round', 'leg', 'recent', 'limit'}:
            bounds = {'season': (1900, 2200), 'round': (1, 99), 'leg': (1, 2), 'recent': (1, 500), 'limit': (1, 50)}
            low, high = bounds[key]
            if type(value) is not int or not low <= value <= high:
                raise ResultsError('INVALID_FILTER', f'{key} must be an integer from {low} through {high}.')
        elif key == 'include_pending':
            if type(value) is not bool:
                raise ResultsError('INVALID_FILTER', 'include_pending must be true or false.')
        elif key == 'cursor':
            if not isinstance(value, str) or not 1 <= len(value) <= 4096:
                raise ResultsError('INVALID_CURSOR', 'Use the unchanged next_cursor from the preceding response.')
        else:
            try:
                if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                raise ResultsError('INVALID_DATE', 'Dates must be real ISO dates: YYYY-MM-DD.') from None
    if 'date' in args and ({'date_from', 'date_to'} & set(args)):
        raise ResultsError('INVALID_DATE', 'Choose date or date_from/date_to.')
    if args.get('date_from', '') > args.get('date_to', '9999-12-31'):
        raise ResultsError('INVALID_DATE', 'date_from must not be later than date_to.')
    return args


class Projection:
    def __init__(self, db, *, revealed=()):
        self.db, self.revealed = db, set(revealed)
        self.tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.records, self.ties, self.identities, self.aliases = {}, {}, {}, {}
        self.labels = {}
        for r in self.rows('clubs'):
            self.identity(r['name'], f"club:{r['id']}")
        for r in self.rows('world_clubs'):
            self.identity(r['name'], r['key'])
            self.aliases[fold(r['alias'])] = r['key']
        if 'club:15' in self.identities:
            self.aliases['vasco da gama'] = 'club:15'
        self.load()

    def rows(self, table):
        # Only internal literal table names reach this helper, never request SQL.
        return [dict(r) for r in self.db.execute('SELECT * FROM "' + table + '"')] if table in self.tables else []

    def identity(self, name, key=None):
        key = key or self.aliases.get(fold(name)) or 'historical-name:' + fold(name)
        self.identities.setdefault(key, name)
        self.aliases[fold(name)] = key
        return key

    def team(self, key):
        return {'id': key, 'name': self.identities.get(key, key)} if key else None

    def add(self, key, comp, season, when, home, away, score, status, source, *, phase=None,
            number=None, leg=None, tie=None, resolution=None, replace=None):
        comp, label = competition(comp)
        self.labels[comp] = label
        completed = str(status).lower() in {'final', 'complete', 'completed', 'played'}
        old = self.records.pop(replace or key, None)
        if old and completed and old['status'] == 'completed' and old['score'] is not None and score is not None and all(type(v) is int for v in score) and old['score'] != score:
            raise ResultsError('SOURCE_SCORE_CONFLICT', 'Accepted source mirrors disagree on a recorded score; no result was chosen or changed.')
        if old and old['home'] and old['away'] and (old['home']['id'], old['away']['id']) != (home, away):
            raise ResultsError('SOURCE_IDENTITY_CONFLICT', 'Accepted source mirrors disagree on the participating clubs.')
        sources = (old['sources'] if old else []) + [source]
        value = {'id': key, 'competition_id': comp, 'competition': label, 'season': season,
                 'date': when or None, 'round': number, 'stage': stage(phase) if phase else None,
                 'leg': leg, 'home': self.team(home), 'away': self.team(away),
                 'status': 'completed' if completed else status, 'score': score if completed else None,
                 'tie_id': tie, 'resolution': resolution, 'sources': sources,
                 'record_type': 'conditional_reservation' if ':reserve:' in key else 'fixture'}
        if completed and (score is None or any(type(v) is not int or v < 0 for v in score)):
            value['score'] = None
            value['score_availability'] = 'not_recorded'
        if key in self.records:
            raise ResultsError('SOURCE_COLLISION', 'Two source records have the same match identity.')
        self.records[key] = value

    def load(self):
        native_ties = self.rows('cup_ties')
        fixture_ties = {}
        for t in native_ties:
            for leg, field in ((1, 'first_leg_id'), (2, 'second_leg_id')):
                if t[field] is not None:
                    fixture_ties[t[field]] = (t, leg)
        for f in self.rows('fixtures'):
            when = f['datetime_local']
            year = re.search(r'(?:19|20)\d{2}', f['competition'])
            season = int(year[0]) if year else int(when[:4]) if when else None
            t, leg = fixture_ties.get(f['id'], (None, None))
            if t:
                season = t['season']
            self.add(f"fixtures:{f['id']}", f['competition'], season, when,
                     f"club:{f['home_id']}", f"club:{f['away_id']}", [f['home_goals'], f['away_goals']], f['status'],
                     {'table': 'fixtures', 'id': f['id']}, phase=f['round'], number=round_number(f['round']), leg=leg,
                     tie=f"cup_ties:{t['id']}" if t else None)
        for t in native_ties:
            key = f"cup_ties:{t['id']}"
            a, b = f"club:{t['home_first_club_id']}", f"club:{t['away_first_club_id']}"
            self.ties[key] = self.tie(key, t['competition'], t['season'], None, a, b,
                [t['home_first_aggregate'], t['away_first_aggregate']],
                f"club:{t['winner_club_id']}" if t['winner_club_id'] else None, t['status'], 'cup_ties')
        brackets = {t['tie_code']: t for t in self.rows('cdb_2027_bracket')}
        for f in self.rows('cdb_2027_legs'):
            t = brackets[f['tie_code']]
            self.add(f"cdb:{f['tie_code']}:L{f['leg']}", 'CDB', 2027, f['dated'], self.identity(f['home']), self.identity(f['away']),
                     [f['hg'], f['ag']], 'completed', {'table': 'cdb_2027_legs', 'tie_code': f['tie_code'], 'leg': f['leg']},
                     phase=t['stage'], leg=f['leg'], tie='cdb:' + f['tie_code'])
        for code, t in brackets.items():
            key = 'cdb:' + code
            a, b = self.identity(t['club_a']) if t['club_a'] else None, self.identity(t['club_b']) if t['club_b'] else None
            self.ties[key] = self.tie(key, 'CDB', 2027, t['stage'], a, b, None,
                self.identity(t['winner']) if t['winner'] else None, t['status'], 'cdb_2027_bracket')
        for comp, table in (('LIB', 'libertadores_2027_fixtures'), ('SULA', 'sudamericana_2027_fixtures')):
            for f in self.rows(table):
                self.add(f'{table}:{f["id"]}', comp, 2027, f['dated'], self.identity(f['home']), self.identity(f['away']),
                    [f['home_goals'], f['away_goals']] if comp == 'LIB' else [f['hg'], f['ag']], f['status'],
                    {'table': table, 'id': f['id']}, phase='GROUP', number=f['matchday'])
        for comp, table, phase in (('LIB', 'libertadores_2027_round_of_16', 'R16'), ('SULA', 'sudamericana_2027_playoffs', 'PO')):
            for t in self.rows(table):
                a, b = self.identity(t['first_leg_home']), self.identity(t['second_leg_home'])
                key = comp.lower() + ':' + t['tie_id']
                for leg in (1, 2):
                    recorded = t.get(f'leg{leg}_result')
                    score = [int(v) for v in recorded.split('-')] if recorded and re.fullmatch(r'\d+-\d+', recorded) else None
                    self.add(key + f':L{leg}', comp, 2027, t['first_leg_date'] if leg == 1 else t['second_leg_date'],
                             a if leg == 1 else b, b if leg == 1 else a, score,
                             t['status'] if score is not None or t['status'] in {'completed', 'complete'} else 'scheduled',
                             {'table': table, 'id': t['tie_id'], 'leg': leg}, phase=phase, leg=leg, tie=key)
                self.ties[key] = self.tie(key, comp, 2027, phase, a, b, None,
                    self.identity(t['winner']) if t['winner'] else None, t['status'], table)
        for f in self.rows('world_finals'):
            native = f"fixtures:{f['fixture_id']}" if f['fixture_id'] is not None else None
            resolution = {'extra_time_played': None, 'penalty_score': [f['penalties_home'], f['penalties_away']]
                          if f['penalties_home'] is not None and f['penalties_away'] is not None else None,
                          'decided_by': f['decided_by'], 'champion': f['champion']}
            if native in self.records:
                self.records[native]['resolution'] = resolution
                self.records[native]['sources'].append({'table': 'world_finals', 'id': f['id'], 'provenance': f['provenance']})
            else:
                self.add(f"world_finals:{f['id']}", f['competition'], f['season'], f['datetime_local'],
                         self.identity(f['home_team']), self.identity(f['away_team']), [f['home_goals'], f['away_goals']],
                         'completed', {'table': 'world_finals', 'id': f['id'], 'provenance': f['provenance']}, phase='FINAL', resolution=resolution)
        receipts = {r['fixture_key']: r['result_sha256'] for r in self.rows('world_receipts')}
        drawn = {r['key'] for r in self.rows('world_draws') if r['status'] == 'activated'}
        for f in self.rows('world_fixtures'):
            if ':reserve:' in f['key'] and f"{f['competition']}:{f['stage']}" in drawn:
                continue  # activated reservations are not additional pending matches.
            # Native/forward mirrors are the same match, not a second result.
            native = f"fixtures:{f['source_key']}" if f['source_table'] == 'fixtures' else f['key']
            source = {'table': 'world_fixtures', 'id': f['key']}
            if f['key'] in receipts:
                source['result_sha256'] = receipts[f['key']]
            self.add(f['key'], f['competition'], f['season'], f['kickoff'], f['home'], f['away'],
                     [f['home_goals'], f['away_goals']], f['status'], source, phase=f['stage'], number=round_number(f['stage']),
                     leg=f['leg'] if f['competition'] != 'LEAGUE' else None, tie=f['tie_key'],
                     resolution=self.resolution(f['resolution_json']), replace=native)
        for t in self.rows('world_ties'):
            seasons = {r['season'] for r in self.records.values() if r['tie_id'] == t['key']}
            self.ties[t['key']] = self.tie(t['key'], t['competition'], next(iter(seasons)) if len(seasons) == 1 else None, t['stage'], t['club_a'], t['club_b'],
                [t['aggregate_a'], t['aggregate_b']], t['winner'], t['status'], 'world_ties')
        editions={e['id']:e for e in self.rows('ms_editions')}
        for e in editions.values():
            if e['format'] in {'groups_knockout','sula_cross_playoffs'}:
                from .multiseason.groups import recorded
                recorded(self.db,e['id'])
        executions={e['fixture']:e for e in self.rows('ms_executions')}
        entries=Counter(r['edition'] for r in self.rows('ms_entries'))
        for f in self.rows('ms_fixtures'):
            e=editions[f['edition']];execution=executions.get(f['key'])
            source={'table':'ms_fixtures','id':f['key'],'edition':e['id'],'profile':'DEV-MULTISEASON-2'}
            resolution=None
            if execution and execution['result_sha256']:
                import json
                receipts[f['key']]=execution['result_sha256'];source['result_sha256']=execution['result_sha256']
                resolution=json.loads(execution['result_json'])['resolution']
            knockout_entries=16 if e['format']=='sula_cross_playoffs' else entries[e['id']]//2 if e['format']=='groups_knockout' else entries[e['id']]
            numbered=re.fullmatch(r'S([1-9][0-9]*)',f['stage'])
            if f['stage'].startswith('GROUP:'):phase='GROUP'
            elif f['stage']=='PO':phase='PO'
            elif e['format']=='league':phase='LEAGUE'
            elif numbered and int(numbered[1])<=16:
                phase={2:'FINAL',4:'SF',8:'QF',16:'R16',32:'R32'}.get(knockout_entries//2**(int(numbered[1])-1),f['stage'])
            else:phase=f['stage']
            if e['competition'].startswith('LIB_PRE'):phase=e['competition'].replace('LIB_','')
            if e['competition']=='SULA_PRE':phase='NATIONAL_PRE'
            comp='LIB' if e['competition'].startswith('LIB_PRE') else 'SULA' if e['competition']=='SULA_PRE' else e['competition']
            self.add(f['key'],comp,e['season'],f['kickoff'],f['home'],f['away'],[f['home_goals'],f['away_goals']],f['status'],source,
                     phase=phase,number=f['round'] if e['format']=='league' or f['stage'].startswith('GROUP:') else None,leg=f['round'] if f['tie_key'] else None,tie=f['tie_key'],resolution=resolution)
        for t in self.rows('ms_ties'):
            e=editions[t['edition']]
            size=16 if e['format']=='sula_cross_playoffs' else entries[e['id']]//2 if e['format']=='groups_knockout' else entries[e['id']]
            phase='PO' if e['format']=='sula_cross_playoffs' and t['stage']==0 else {2:'FINAL',4:'SF',8:'QF',16:'R16',32:'R32'}.get(size//2**(t['stage']-1),str(t['stage']))
            if e['competition'].startswith('LIB_PRE'):phase=e['competition'].replace('LIB_','')
            if e['competition']=='SULA_PRE':phase='NATIONAL_PRE'
            comp='LIB' if e['competition'].startswith('LIB_PRE') else 'SULA' if e['competition']=='SULA_PRE' else e['competition']
            self.ties[t['key']]=self.tie(t['key'],comp,e['season'],phase,t['club_a'],t['club_b'],None,t['winner'],'final' if t['winner'] else 'scheduled','ms_ties')
        # Partial and final aggregates from recorded scores, never from standings.
        for key, t in self.ties.items():
            legs = [r for r in self.records.values() if r['tie_id'] == key]
            t['legs'] = [r['id'] for r in sorted(legs, key=lambda r: (r['leg'] or 0, r['id']))]
            if t['aggregate'] is None and legs:
                known = [r for r in legs if r['score'] is not None]
                t['aggregate'] = [sum(r['score'][0 if r['home']['id'] == t['clubs'][i]['id'] else 1] for r in known)
                                  for i in (0, 1)] if known and all(t['clubs']) else None
                t['aggregate_basis'] = 'recorded_leg_scores'
            t['aggregate_complete'] = t['status'] == 'completed' and bool(legs) and all(r['score'] is not None for r in legs)
            decided = [r for r in legs if r['resolution'] and (r['resolution'].get('penalty_score') is not None or r['resolution'].get('extra_time_played'))]
            t['deciding_resolution'] = {'fixture': decided[-1]['id'], 'home': decided[-1]['home'], 'away': decided[-1]['away'],
                                        **decided[-1]['resolution']} if decided else None
            if any(r['status'] == 'completed' and 'club:15' in (r['home']['id'] if r['home'] else None, r['away']['id'] if r['away'] else None)
                   and r['id'] in receipts and r['id'] not in self.revealed for r in legs):
                t.update(aggregate=None, qualified=None, deciding_resolution=None, aggregate_complete=False, score_availability='narration_required')
        for r in self.records.values():
            if r['id'] in receipts and r['id'] not in self.revealed and any(t and t['id'] == 'club:15' for t in (r['home'], r['away'])):
                r.update(score=None, resolution=None, score_availability='narration_required')

    @staticmethod
    def resolution(raw):
        if not raw:
            return None
        import json
        value = json.loads(raw)
        return {k: value[k] for k in ('extra_time_played', 'penalty_score', 'aggregate_home_away', 'winner') if k in value}

    def tie(self, key, comp, season, phase, a, b, aggregate, winner, status, source):
        return {'id': key, 'competition_id': competition(comp)[0], 'season': season, 'stage': stage(phase) if phase else None,
                'clubs': [self.team(a), self.team(b)], 'aggregate': aggregate, 'aggregate_basis': source,
                'qualified': self.team(winner) if winner and status in {'final', 'complete', 'completed'} else None,
                'status': 'completed' if status in {'final', 'complete', 'completed'} else status,
                'source_table': source}

    def coverage(self):
        counts = Counter((r['competition_id'], r['season']) for r in self.records.values())
        return [{'competition': self.labels[comp], 'competition_id': comp, 'season': season,
                 'recorded_matches': sum(r['record_type'] == 'fixture' for r in self.records.values() if (r['competition_id'], r['season']) == (comp, season)),
                 'conditional_reservations': sum(r['record_type'] == 'conditional_reservation' for r in self.records.values() if (r['competition_id'], r['season']) == (comp, season)),
                 'undated_matches': sum(r['date'] is None for r in self.records.values() if (r['competition_id'], r['season']) == (comp, season))}
                for (comp, season), n in sorted(counts.items(), key=lambda r: (r[0][0], r[0][1] or 0))]

    def select(self, args):
        validate_filters(args)
        comp = competition(args['competition'])[0] if 'competition' in args else None
        if comp is not None and comp not in self.labels:
            raise ResultsError('UNKNOWN_COMPETITION', 'Competition is not recorded; inspect coverage for available competitions.')
        club = self.aliases.get(fold(args['club'])) if 'club' in args else None
        if 'club' in args and club is None:
            raise ResultsError('UNKNOWN_CLUB', 'Club name is not recorded; use its recorded name or established alias.')
        rows = [r for r in self.records.values() if
                (comp is None or r['competition_id'] == comp) and
                ('season' not in args or r['season'] == args['season']) and
                ('round' not in args or r['round'] == args['round']) and
                ('stage' not in args or r['stage'] == stage(args['stage'])) and
                ('leg' not in args or r['leg'] == args['leg']) and
                (club is None or any(t and t['id'] == club for t in (r['home'], r['away'])))]
        if any(k in args for k in ('date', 'date_from', 'date_to')):
            low, high = args.get('date', args.get('date_from', '0000-00-00')), args.get('date', args.get('date_to', '9999-12-31'))
            rows = [r for r in rows if r['date'] is not None and low <= r['date'][:10] <= high]
        counts = Counter(r['status'] == 'completed' for r in rows)
        rows = [r for r in rows if args.get('include_pending', False) or r['status'] == 'completed']
        rows.sort(key=lambda r: (r['date'] is not None, r['date'] or '', r['id']), reverse='recent' in args)
        if 'recent' in args:
            rows = rows[:args['recent']]
        return rows, {'recorded_completed': counts[True], 'recorded_pending': counts[False],
                      'recorded_selection_complete': bool(counts) and counts[False] == 0,
                      'scores_unavailable': sum(r['status'] == 'completed' and r['score'] is None for r in rows),
                      'total_matching': len(rows)}
