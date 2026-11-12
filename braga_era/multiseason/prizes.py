"""Versioned BRL competition distributions settled at the next season opening."""

from collections import Counter
import json

from ..history import canonical_json as encode, digest
from .competitions import COMPETITIONS, required, standings

POLICY = 'competition-prizes-brl-1'
OPERATION = 'settle_competition_prizes'
CATEGORY = 'competition prize settlement'

# Integer BRL. Finals are exclusive; preceding stages are cumulative.
LEAGUES = {
    'LEAGUE': (8000000, 6500000, 5500000, 4800000, 4200000, 3700000, 3300000, 2950000,
               2650000, 2400000, 2200000, 2000000, 1850000, 1700000, 1550000, 1400000,
               1200000, 1100000, 1000000, 900000),
    'SERIE_B': (2200000, 1800000, 1500000, 1300000, 1150000, 1050000, 950000, 850000,
                775000, 700000, 650000, 600000, 560000, 520000, 480000, 450000,
                420000, 390000, 360000, 330000),
}
STAGES = {
    'CDB': dict(C1=150000, C2=200000, C3=300000, C4=450000, C5=650000, C6=950000, C7=1500000, C8=2400000),
    'CARIOCA': dict(POOL=120000, K1=180000, K2=300000),
    'LIB': dict(GROUP=2100000, GROUP_WIN=230000, S1=1400000, S2=2200000, S3=3200000),
    'SULA': dict(GROUP=850000, GROUP_WIN=90000, PO=450000, S1=700000, S2=1100000, S3=1600000),
}
FINALS = {
    'CDB': ('C9', 8500000, 4200000), 'CARIOCA': ('K3', 1250000, 650000),
    'LIB': ('S4', 14000000, 6400000), 'SULA': ('S4', 6800000, 3100000),
    'SUPERCOPA': ('TROPHY', 1800000, 950000), 'RECOPA': ('TROPHY', 2400000, 1150000),
}
PRELIMINARY = {'LIB_PRE1': 220000, 'LIB_PRE2': 320000, 'LIB_PRE3': 470000, 'SULA_PRE': 180000}
NO_AWARD = COMPETITIONS - LEAGUES.keys() - STAGES.keys() - FINALS.keys() - PRELIMINARY.keys()
FEE_PERCENT = 30
WAGE_PERCENT = 10
CONFIG_SHA256 = digest(dict(leagues=LEAGUES, stages=STAGES, finals=FINALS, preliminary=PRELIMINARY,
                            no_award=sorted(NO_AWARD), fee_percent=FEE_PERCENT, wage_percent=WAGE_PERCENT))


def awards(c, year, *, preview=False):
    editions = c.execute('SELECT * FROM ms_editions WHERE season=? ORDER BY id', (year,)).fetchall()
    if not editions:
        raise ValueError('No recorded season editions for competition settlement')
    for e in editions:
        comp, edition = e['competition'], e['id']
        if comp in NO_AWARD:
            continue
        if comp not in LEAGUES and comp not in FINALS and comp not in PRELIMINARY:
            raise ValueError('Unknown competition prize policy')
        games = c.execute('SELECT * FROM ms_fixtures WHERE edition=? ORDER BY key', (edition,)).fetchall()
        if (not games or any(g['status'] != 'final' for g in games)
                or (e['state'] != 'completed' and not (preview and comp in LEAGUES))):
            raise ValueError('Competition settlement requires completed sporting records')

        def award(club, tier, amount, count=1):
            return dict(edition=edition, competition=comp, club=club, tier=tier,
                        count=count, amount_cents=amount * count * 100)

        if comp in LEAGUES:
            table = standings(c, edition)
            rates = LEAGUES[comp]
            if (len(table) != len(rates) or len(games) != len(rates) * (len(rates) - 1)
                    or any(row['played'] != 2 * (len(rates) - 1) for row in table)
                    or e['champion'] and e['champion'] != table[0]['club']):
                raise ValueError('League prize inventory differs from recorded table')
            for place, (row, amount) in enumerate(zip(table, rates), 1):
                yield award(row['club'], f'place-{place}', amount)
            continue
        if comp in PRELIMINARY:
            for club in sorted({g[side] for g in games for side in ('home', 'away')}):
                yield award(club, 'participation', PRELIMINARY[comp])
            continue
        final_stage, winner_rate, runner_up_rate = FINALS[comp]
        participants = set()
        wins = Counter()
        finalists = set()
        for g in games:
            stage = 'GROUP' if g['stage'].startswith('GROUP:') else g['stage']
            if stage == final_stage:
                finalists.update((g['home'], g['away']))
                continue
            if stage not in STAGES.get(comp, {}) or stage == 'GROUP_WIN':
                raise ValueError('Unrecognized recorded prize stage')
            participants.update(((stage, g['home']), (stage, g['away'])))
            if stage == 'GROUP' and g['home_goals'] != g['away_goals']:
                wins[g['home'] if g['home_goals'] > g['away_goals'] else g['away']] += 1
        for stage, club in sorted(participants):
            yield award(club, stage, STAGES[comp][stage])
        for club, count in sorted(wins.items()):
            yield award(club, 'GROUP_WIN', STAGES[comp]['GROUP_WIN'], count)
        if len(finalists) != 2 or e['champion'] not in finalists:
            raise ValueError('Final award needs a recorded champion and runner-up')
        for club in sorted(finalists):
            winner = club == e['champion']
            yield award(club, 'champion' if winner else 'runner-up', winner_rate if winner else runner_up_rate)


def allocation(amount):
    return amount * FEE_PERCENT // 100, amount * WAGE_PERCENT // 100


def financial_position(c, club, year, dated):
    from . import offseason

    if not c.execute('SELECT 1 FROM ms_pools WHERE id=?', (f'{POLICY}:{year - 1}',)).fetchone():
        return None
    account = c.execute('SELECT * FROM ms_accounts WHERE club=?', (club,)).fetchone()
    if account is None:
        return None
    outstanding = c.execute("""SELECT coalesce(sum(amount_cents),0) FROM ms_obligations
                               WHERE club=? AND status='pending' AND direction=-1""", (club,)).fetchone()[0]
    wage = offseason.active_wages(c, club, dated)
    free = max(0, account['cash_cents'] - account['reserve_cents'] - outstanding - 2 * wage)
    return {
        'cash_cents': account['cash_cents'], 'protected_reserve_cents': account['reserve_cents'],
        'unpaid_obligations_cents': outstanding, 'two_month_wage_buffer_cents': 2 * wage,
        'monthly_committed_wages_cents': wage, 'operating_liquidity_before_transfers_cents': free,
        'fee_authority_cents': account['fee_authority_cents'],
        'available_transfer_funds_cents': min(free, account['fee_authority_cents']),
        'annual_additional_wage_authority_cents': account['wage_authority_cents'],
        'prize_settlement': [json.loads(r[0]) for r in c.execute(
            "SELECT evidence_json FROM ms_ledger WHERE club=? AND category=? AND dated=? ORDER BY id",
            (club, CATEGORY, f'{year}-01-01'))],
    }


def settlement(c, args):
    from . import market
    from .authentic import POLICY as AUTHENTIC

    required(args, 'season policy schedule_sha256')
    year = args['season']
    if (type(year) is not int or year < 2029 or args['policy'] != POLICY
            or args['schedule_sha256'] != CONFIG_SHA256):
        raise ValueError('Exact competition prize policy and schedule required')
    if not c.execute('SELECT test_only FROM ms_meta').fetchone()[0]:
        row = c.execute("SELECT clubs_json FROM ms_pools WHERE id=? AND competition='TRANSITION_POLICY'",
                        (f'authorized:{AUTHENTIC}:{year}',)).fetchone()
        if not row or json.loads(row[0]) != dict(season=year, policy=AUTHENTIC, prize_policy=POLICY,
                                               prize_schedule_sha256=CONFIG_SHA256):
            raise ValueError('Missing signed competition economy transition authorization')
    prior = c.execute('SELECT state,archive_json FROM ms_seasons WHERE season=?', (year - 1,)).fetchone()
    opening = c.execute('SELECT state,dated FROM ms_offseasons WHERE season=?', (year,)).fetchone()
    dated = f'{year}-01-01'
    if (not prior or prior['state'] != 'archived' or not prior['archive_json']
            or not opening or tuple(opening) != ('open', dated)
            or c.execute('SELECT clock FROM ms_meta').fetchone()[0] != dated + ' 00:00:00'):
        raise ValueError('Settle only at the opening of an exact archived successor')
    if c.execute('SELECT 1 FROM ms_pools WHERE id=?', (f'{POLICY}:{year - 1}',)).fetchone():
        raise ValueError('Competition season already settled')
    # The inherited system uses other named income categories. An unrecognized
    # existing prize receipt requires reconciliation before applying this policy.
    if c.execute("""SELECT 1 FROM ms_ledger WHERE substr(dated,1,4)=?
                 AND lower(category) LIKE '%prize%' AND category<>?""", (str(year - 1), CATEGORY)).fetchone():
        raise ValueError('Existing prize income requires reconciliation')
    totals = Counter()
    rows = list(awards(c, year - 1))
    for row in rows:
        club = row['club']
        if not c.execute('SELECT 1 FROM ms_accounts WHERE club=?', (club,)).fetchone():
            market.apply(c, 'open_recorded_account', {'club': club})
        identity = f"competition-prize:{row['edition']}:{row['tier']}:{club}"
        evidence = {**row, 'earned_season': year - 1, 'policy': POLICY, 'schedule_sha256': CONFIG_SHA256}
        c.execute('INSERT INTO ms_ledger VALUES(?,?,?,?,?,?)',
                  (identity, club, dated, row['amount_cents'], CATEGORY, encode(evidence)))
        totals[club] += row['amount_cents']
    for club, amount in sorted(totals.items()):
        fee, wage = allocation(amount)
        c.execute("""UPDATE ms_accounts SET cash_cents=cash_cents+?,fee_authority_cents=fee_authority_cents+?,
                     wage_authority_cents=wage_authority_cents+? WHERE club=?""", (amount, fee, wage, club))
        scenario = c.execute('SELECT scenario_json FROM ms_economics WHERE club=? AND season=?', (club, year)).fetchone()
        if scenario:
            value = json.loads(scenario[0])
            value['annual_wage_cap_cents'] += wage
            c.execute('UPDATE ms_economics SET scenario_json=? WHERE club=? AND season=?', (encode(value), club, year))
    summary = dict(earned_season=year - 1, paid_at=dated, policy=POLICY, schedule_sha256=CONFIG_SHA256,
                   clubs=len(totals), awards=len(rows), total_cents=sum(totals.values()), awards_sha256=digest(rows))
    c.execute('INSERT INTO ms_pools VALUES(?,?,?,?,?)',
              (f'{POLICY}:{year - 1}', year, 'PRIZE_SETTLEMENT', encode(summary), POLICY))
    return summary
