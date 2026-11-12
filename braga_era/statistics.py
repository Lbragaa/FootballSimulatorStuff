"""Allowlisted projections over an authenticated career database."""

from datetime import date
import json

from .multiseason import competitions, groups

COUNT_FIELDS = ('goals', 'assists', 'shots', 'on_target', 'saves', 'yellows')
METRICS = ('appearances', 'starts', 'seconds_played', *COUNT_FIELDS, 'reds', 'injuries',
           'xg', 'xg_per_90', 'mean_rating')
ATTRIBUTES = ('name', 'position', 'ovr', 'attack', 'defense', 'passing', 'physical', 'composure', 'goalkeeping')
RANKING = ['points', 'wins', 'goal_difference', 'goals_for', 'club_id']
FILTERS = {
    'editions': {'season'},
    'standings': {'season', 'competition', 'group'},
    'squad': {'club', 'player', 'sort'},
    'player_stats': {'season', 'competition', 'stage', 'club', 'player', 'date_from', 'date_to', 'sort', 'min_minutes'},
    'team_record': {'season', 'competition', 'stage', 'club', 'date_from', 'date_to'},
    'development': {'season', 'club', 'player', 'sort'},
    'transfers': {'season', 'club', 'player', 'date_from', 'date_to'},
    'transfer_market': {'season', 'club'},
}


class QueryError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate(args):
    dataset = args.get('dataset')
    if not isinstance(dataset, str) or dataset not in FILTERS:
        raise QueryError('UNKNOWN_DATASET', 'Choose editions, standings, squad, player_stats, team_record, development, transfers or transfer_market.')
    for field, value in args.items():
        if field == 'through_date' and dataset in ('player_stats', 'team_record', 'transfers'):
            raise QueryError('INVALID_FILTER', 'Use date_to for an inclusive YYYY-MM-DD cutoff.')
        if field not in FILTERS[dataset] | {'dataset', 'limit'}:
            raise QueryError('INVALID_FILTER', f'Unsupported filter for {dataset}.')
        if field in ('season', 'limit', 'group', 'min_minutes', 'player') and (field != 'player' or type(value) is not str):
            low, high = {'season': (2027, 2200), 'limit': (1, 30), 'group': (1, 99),
                         'min_minutes': (0, 1000000), 'player': (1, 2**63 - 1)}[field]
            if type(value) is not int or not low <= value <= high:
                raise QueryError('INVALID_FILTER', f'{field} requires an integer from {low} to {high}.')
        elif type(value) is not str or not value.strip() or len(value) > 100:
            raise QueryError('INVALID_FILTER', f'{field} requires a short nonempty string.')
        elif field in ('date_from', 'date_to'):
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                raise QueryError('INVALID_FILTER', 'Dates must use YYYY-MM-DD.') from None
    if args.get('date_from', '') > args.get('date_to', '9999'):
        raise QueryError('INVALID_FILTER', 'date_from must be on or before date_to.')
    if dataset in ('squad', 'team_record', 'transfer_market') and not (args.get('club') or args.get('player')):
        raise QueryError('INVALID_FILTER', 'Supply a club or player.')
    sort_fields = {'squad': {'name', 'ovr'}, 'development': {'ovr_delta'}, 'player_stats': set(METRICS)}
    if 'sort' in args and args['sort'] not in sort_fields[dataset]:
        raise QueryError('INVALID_FILTER', 'Unknown sort metric for this dataset.')


def one(rows, value, key, name, label):
    matches = [r for r in rows if r[key] == value or
               isinstance(value, str) and r[name].casefold() == value.strip().casefold()]
    if not matches:
        raise QueryError('UNKNOWN_IDENTITY', f'No recorded {label} matches the selection.')
    if len(matches) > 1:
        ids = ', '.join(str(r[key]) for r in matches[:8])
        raise QueryError('AMBIGUOUS_IDENTITY', f'Use a stable {label} ID. Matching IDs: {ids}.')
    return matches[0][key]


def require_revealed(fixtures, hidden):
    if any(f['key'] in hidden for f in fixtures):
        raise QueryError('NARRATION_PENDING', 'Finish the relevant accepted match narration before reading these statistics.')


def standings(db, args, hidden, season, names):
    competition = args.get('competition', 'LEAGUE')
    edition = db.execute('SELECT * FROM ms_editions WHERE season=? AND competition=?',
                         (args.get('season', season), competition)).fetchone()
    if not edition:
        raise QueryError('UNKNOWN_EDITION', 'Use editions to find a recorded competition and season.')
    key = edition['id']
    fixtures = list(db.execute('SELECT * FROM ms_fixtures WHERE edition=? ORDER BY kickoff,key', (key,)))
    if edition['format'] == 'groups_knockout':
        if 'group' not in args:
            raise QueryError('GROUP_REQUIRED', 'Supply a committed group number from editions.')
        group = f"GROUP:{args['group']}"
        if group not in (groups.recorded(db, key) or {}):
            raise QueryError('UNKNOWN_GROUP', 'This group is absent from the committed draw.')
        fixtures = [f for f in fixtures if f['stage'] == group]
        require_revealed(fixtures, hidden)
        table = groups.table(db, key, group, require_complete=False)
    elif edition['format'] == 'league' and 'group' not in args:
        group = None
        require_revealed(fixtures, hidden)
        table = competitions.standings(db, key)
    else:
        raise QueryError('NO_STANDINGS', 'Use a league or a committed continental group. Brackets are available via historical_results.')
    rows = []
    for rank, r in enumerate(table, 1):
        draws = r['points'] - 3 * r['wins']
        rows.append({**r, 'draws': draws, 'losses': r['played'] - r['wins'] - draws,
                     'goal_difference': r['gf'] - r['ga'], 'rank': rank, 'name': names[r['club']]})
    played = sum(f['status'] == 'final' for f in fixtures)
    remaining = [{'id': f['key'], 'kickoff': f['kickoff'], 'home': names[f['home']],
                  'away': names[f['away']]} for f in fixtures if f['status'] != 'final'] if group else None
    return rows, {'edition': key, 'season': edition['season'], 'group': group, 'ranking': RANKING,
                  'played_fixtures': played, 'scheduled_fixtures': len(fixtures),
                  'complete': bool(fixtures) and played == len(fixtures),
                  'remaining_group_fixtures': remaining,
                  'qualification_slots': (['Libertadores knockout', 'Libertadores knockout', 'Sul-Americana playoff']
                                          if group and competition == 'LIB' else
                                          ['Sul-Americana knockout', 'Sul-Americana playoff'] if group and competition == 'SULA' else None)}


def editions(db, args):
    rows = []
    for edition in db.execute('SELECT id,competition,season,format FROM ms_editions ORDER BY season,competition'):
        if 'season' in args and edition['season'] != args['season']:
            continue
        group_ids = [int(r[0].split(':')[1]) for r in db.execute(
            "SELECT DISTINCT stage FROM ms_fixtures WHERE edition=? AND stage LIKE 'GROUP:%'", (edition['id'],))]
        rows.append({**dict(edition), 'groups': sorted(group_ids)})
    return rows, {}


def squad(db, args, players, club, player, hidden):
    if hidden:
        raise QueryError('NARRATION_PENDING', 'Finish accepted match narration before reading the current player state.')
    lifecycle = db.execute("SELECT 1 FROM sqlite_master WHERE name='ms_lifecycle'").fetchone()
    rows = []
    for p in players:
        if (club and p['club_key'] != club) or (player is not None and p['id'] != player):
            continue
        status = db.execute('SELECT state_json FROM world_player_state WHERE player_id=?', (p['id'],)).fetchone()
        state = json.loads(status[0]) if status else {}
        contract = db.execute(
            "SELECT club,starts,ends,wage_cents FROM ms_contracts WHERE player=? AND status='active'", (p['id'],)
        ).fetchone()
        life = db.execute('SELECT age,observed_season,status FROM ms_lifecycle WHERE player=?',
                          (p['id'],)).fetchone() if lifecycle else None
        discipline = [dict(r) for r in db.execute(
            'SELECT competition,yellows,bans FROM world_discipline WHERE player_id=? ORDER BY competition', (p['id'],))]
        rows.append({'id': p['id'], 'club': p['club_key'], 'modeled': bool(p['modeled']),
                     **{k: p['attributes'].get(k) for k in ATTRIBUTES},
                     'state': {k: state.get(k) for k in ('fitness', 'morale', 'form', 'observed_at',
                                                        'injury_until', 'injury_unknown', 'registered')},
                     'active_contract': dict(contract) if contract else None,
                     'lifecycle': dict(life) if life else None, 'discipline': discipline})
    rows.sort(key=lambda p: (p['name'].casefold(), p['id']))
    if args.get('sort') == 'ovr':
        rows.sort(key=lambda p: (p['ovr'] is None, -(p['ovr'] or 0)))
    return rows, {'null_means': 'unknown_or_not_recorded', 'fitness_basis': 'last stored observation',
                  'contract_basis': 'active multi-season contract ledger only'}


def final_fixtures(db, args, club):
    # Filter before opening match bundles. All identifiers originate from the
    # authenticated world. Values from a request are compared as data.
    for source, sql in (
        ('multi_season', """SELECT f.key,f.home,f.away,f.kickoff,f.stage,f.home_goals,f.away_goals,
                             e.competition,e.season FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition
                             WHERE f.status='final' ORDER BY f.key"""),
        ('forward', """SELECT key,home,away,kickoff,stage,home_goals,away_goals,competition,season
                       FROM world_fixtures WHERE status='final' ORDER BY key"""),
    ):
        for f in db.execute(sql):
            if club and club not in (f['home'], f['away']):
                continue
            if any(k in args and args[k] != f[k] for k in ('competition', 'season', 'stage')):
                continue
            if not args.get('date_from', '') <= f['kickoff'][:10] <= args.get('date_to', '9999'):
                continue
            yield source, f


def player_stats(db, args, players, club, player, hidden):
    totals = {}
    fixtures = list(final_fixtures(db, args, club))
    require_revealed((f for _, f in fixtures), hidden)
    recorded = 0
    for source, fixture in fixtures:
        key = fixture['key']
        if source == 'multi_season':
            result = db.execute('SELECT result_json FROM ms_executions WHERE fixture=?', (key,)).fetchone()
            lines = json.loads(result[0]).get('performances', []) if result and result[0] else []
        else:
            lines = [json.loads(r[0]) for r in db.execute(
                'SELECT performance_json FROM world_performances WHERE fixture_key=? ORDER BY player_id', (key,))]
        recorded += bool(lines)
        for p in lines:
            ident = p['player_id']
            if ((player is not None and player != ident) or (club and p['club_key'] != club)
                    or not (p['seconds_played'] or p['starter'])):
                continue
            row = totals.setdefault(ident, {k: 0 for k in (*COUNT_FIELDS, 'appearances', 'starts',
                                      'seconds_played', 'reds', 'injuries', 'xg', 'rating_sum')})
            row['appearances'] += 1
            row['starts'] += int(p['starter'])
            row['seconds_played'] += p['seconds_played']
            for field in COUNT_FIELDS:
                row[field] += p[field]
            row['reds'] += int(p['red'])
            row['injuries'] += int(p['injured'])
            row['xg'] += p['xg']
            row['rating_sum'] += p['rating']
    names = {p['id']: p['name'] for p in players}
    rows = []
    for ident, row in totals.items():
        seconds = row['seconds_played']
        if seconds < 60 * args.get('min_minutes', 0):
            continue
        row.update(id=ident, name=names.get(ident), minutes=round(seconds / 60, 2),
                   xg_per_90=round(row['xg'] * 5400 / seconds, 3) if seconds else None,
                   mean_rating=round(row.pop('rating_sum') / row['appearances'], 2), xg=round(row['xg'], 3))
        rows.append(row)
    metric = args.get('sort', 'goals')
    rows.sort(key=lambda r: (r[metric] is None, -(r[metric] or 0), r['id']))
    return rows, {'final_fixtures_in_scope': len(fixtures), 'fixtures_with_performances': recorded,
                  'coverage': 'recorded_engine_performances_only',
                  'legacy_coverage': 'native history without engine performances excluded'}


def team_record(db, args, club, hidden):
    fixtures = list(final_fixtures(db, args, club))
    require_revealed((f for _, f in fixtures), hidden)
    rows = []
    for venue in ('home', 'away'):
        row = dict(club=club, venue=venue, played=0, wins=0, draws=0, losses=0, gf=0, ga=0, clean_sheets=0)
        for _, f in fixtures:
            if f[venue] != club:
                continue
            other = 'home' if venue == 'away' else 'away'
            gf, ga = f[f'{venue}_goals'], f[f'{other}_goals']
            row['played'] += 1
            row['gf'] += gf
            row['ga'] += ga
            row['wins'] += int(gf > ga)
            row['draws'] += int(gf == ga)
            row['losses'] += int(gf < ga)
            row['clean_sheets'] += int(ga == 0)
        if row['played']:
            rows.append(row)
    return rows, {'coverage': 'forward_and_multi_season_fixtures_only',
                  'outcome_basis': 'stored match score excluding shootout', 'venue_basis': 'fixture designation'}


def development(db, args, names, club, player):
    rows = []
    for entry in db.execute('SELECT * FROM ms_attributes ORDER BY season DESC,player'):
        if ('season' in args and args['season'] != entry['season']) or (player is not None and player != entry['player']):
            continue
        before, after = (json.loads(entry[k]) for k in ('before_json', 'after_json'))
        if club and after.get('club_key') != club:
            continue
        changes = {k: {'before': before[k], 'after': after[k]} for k in ATTRIBUTES[2:]
                   if k in before and k in after and before[k] != after[k]}
        ovr_delta = round(after['ovr'] - before['ovr'], 3) if 'ovr' in before and 'ovr' in after else None
        rows.append({'id': entry['player'], 'name': names.get(entry['player']),
                     'season': entry['season'], 'club_at_update': after.get('club_key'),
                     'ovr_delta': ovr_delta, 'changes': changes})
    if args.get('sort') == 'ovr_delta':
        rows.sort(key=lambda r: (r['ovr_delta'] is None, -(r['ovr_delta'] or 0)))
    return rows, {'coverage': 'recorded_annual_attribute_updates_only',
                  'club_basis': 'club at update when recorded'}


def transfers(db, args, names, club_names, club, player):
    rows = []
    for entry in db.execute('SELECT id,player,seller,buyer,dated,kind FROM ms_transfers ORDER BY dated DESC,id'):
        dated = entry['dated'][:10]
        if club and club not in (entry['seller'], entry['buyer']):
            continue
        if player is not None and entry['player'] != player:
            continue
        if 'season' in args and str(args['season']) != dated[:4]:
            continue
        if args.get('date_from', '') <= dated <= args.get('date_to', '9999'):
            rows.append({**dict(entry), 'name': names.get(entry['player']),
                         'seller_name': club_names.get(entry['seller']), 'buyer_name': club_names.get(entry['buyer'])})
    return rows, {'coverage': 'multi_season_transfer_records_only', 'season_basis': 'transaction calendar year'}


def select(db, args, hidden, season):
    dataset = args['dataset']
    if dataset == 'editions':
        return editions(db, args)
    clubs = list(db.execute('SELECT key,name FROM world_clubs ORDER BY key'))
    club_names = {r['key']: r['name'] for r in clubs}
    if dataset == 'standings':
        return standings(db, args, hidden, season, club_names)
    club = one(clubs, args['club'], 'key', 'name', 'club') if 'club' in args else None
    if 'competition' in args and not db.execute(
        'SELECT competition FROM ms_editions WHERE competition=? UNION SELECT competition FROM world_fixtures WHERE competition=?',
        (args['competition'], args['competition'])
    ).fetchone():
        raise QueryError('UNKNOWN_EDITION', 'Competition code is absent from the recorded fixtures and editions.')
    if dataset == 'team_record':
        return team_record(db, args, club, hidden)
    if dataset == 'transfer_market':
        if hidden:
            raise QueryError('NARRATION_PENDING', 'Finish accepted match narration before reading these records.')
        from .multiseason.offseason import installed
        if not installed(db):
            raise QueryError('NO_MARKET_RECORD', 'This checkpoint predates the recorded offseason market.')
        year = args.get('season', season)
        kinds = ('squad_plan', 'offer_submitted', 'offer_rejected', 'registration_offer_rejected', 'purchase', 'loan')
        rows = []
        for decision in db.execute("""SELECT d.player,d.kind,d.detail_json,p.attributes_json
                                      FROM ms_market_decisions d LEFT JOIN world_players p ON p.id=d.player
                                      WHERE d.club=? AND d.season=? ORDER BY d.kind,d.player,d.id""", (club, year)):
            if decision['kind'] not in kinds:
                continue
            detail = json.loads(decision['detail_json'])
            fields = {'need', 'depth', 'strategy', 'manager', 'fee_cents', 'wage_cents', 'kind',
                      'valuation', 'seller_ask_cents', 'reason', 'competing_offers'}
            rows.append({'kind': decision['kind'], 'player_id': decision['player'],
                         'name': json.loads(decision['attributes_json'])['name'] if decision['attributes_json'] else None,
                         **{k: v for k, v in detail.items() if k in fields and k != 'kind'},
                         **({'transaction': detail['kind']} if 'kind' in detail else {})})
        return rows, {'club': club, 'season': year, 'basis': 'recorded autonomous offseason decisions',
                      'currency': 'BRL cents', 'current_offer': False}
    players = []
    for p in db.execute('SELECT id,club_key,modeled,attributes_json FROM world_players ORDER BY id'):
        attrs = json.loads(p['attributes_json'])
        players.append({**dict(p), 'name': attrs['name'], 'attributes': attrs})
    player = one(players, args['player'], 'id', 'name', 'player') if 'player' in args else None
    if dataset == 'squad':
        return squad(db, args, players, club, player, hidden)
    if dataset in ('development', 'transfers'):
        if hidden:
            raise QueryError('NARRATION_PENDING', 'Finish accepted match narration before reading these records.')
        names = {p['id']: p['name'] for p in players}
        if dataset == 'development':
            return development(db, args, names, club, player)
        return transfers(db, args, names, club_names, club, player)
    return player_stats(db, args, players, club, player, hidden)
