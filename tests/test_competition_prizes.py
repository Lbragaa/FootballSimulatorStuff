import json
import sqlite3

import pytest

from braga_era.multiseason import prizes, valuation
from braga_era.multiseason.offseason import DDL as OFFSEASON
from braga_era.multiseason.schema import DDL
from braga_era.world.schema import DDL as WORLD


@pytest.fixture
def world():
    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        db.executescript(WORLD + DDL + OFFSEASON)
        db.execute("INSERT INTO ms_meta VALUES(1,'test','head','sha','{}','seed','2029-01-01 00:00:00',1)")
        db.execute("INSERT INTO ms_seasons VALUES(2028,'archived','{}'),(2029,'preparing',NULL)")
        db.execute("INSERT INTO ms_offseasons VALUES(2029,'test','2029-01-01','open',NULL)")
        db.executemany("INSERT INTO world_clubs VALUES(?,?,?,NULL,'BRA',70,0,'{}')",
                       [(f'club:{n}', str(n), str(n)) for n in range(1, 21)])
        db.executemany("INSERT INTO ms_accounts VALUES(?,10000,2000,100,200,'{}')",
                       [(f'club:{n}',) for n in range(1, 21)])
        yield db


def edition(c, comp, stages, *, league=False, champion=True):
    key = f'{comp}:2028'
    c.execute("INSERT INTO ms_editions VALUES(?,?,2028,?,'{}','completed',?)",
              (key, comp, 'league' if league else 'knockout', 'club:1' if champion else None))
    pairs = [('club:1', 'club:2')]
    if league:
        clubs = [f'club:{n}' for n in range(1, 21)]
        c.executemany("INSERT INTO ms_entries VALUES(?,?,'test','{}')", [(key, club) for club in clubs])
        pairs = [(h, a) for h in clubs for a in clubs if h != a]
    for stage in stages:
        for n, (home, away) in enumerate(pairs, 1):
            c.execute("""INSERT INTO ms_fixtures VALUES(?,?,?,?,NULL,?,?,'2028-03-01 16:00',
                         'final',?,0,NULL)""", (f'{key}:{stage}:{n}', key, stage, n, home, away, int(home == 'club:1')))


def args():
    return dict(season=2029, policy=prizes.POLICY, schedule_sha256=prizes.CONFIG_SHA256)


def test_every_award_tier_and_final_exclusivity(world):
    for comp in prizes.LEAGUES:
        edition(world, comp, ['LEAGUE'], league=True)
    for comp in prizes.PRELIMINARY:
        edition(world, comp, ['S1'], champion=False)
    for comp, (final, _, _) in prizes.FINALS.items():
        tiers = prizes.STAGES.get(comp, {})
        stages = [('GROUP:1' if x == 'GROUP' else x) for x in tiers if x != 'GROUP_WIN']
        edition(world, comp, [*stages, final])
    records = list(prizes.awards(world, 2028))
    for comp, rates in prizes.LEAGUES.items():
        rows = [r for r in records if r['competition'] == comp]
        assert [r['amount_cents'] for r in rows] == [rate * 100 for rate in rates]
    for comp, rates in prizes.STAGES.items():
        assert {r['tier']: r['amount_cents'] for r in records
                if r['competition'] == comp and r['club'] == 'club:1'
                and r['tier'] in rates} == {tier: rate * 100 for tier, rate in rates.items()}
    for comp, (_, champion, runner) in prizes.FINALS.items():
        assert [(r['tier'], r['amount_cents']) for r in records
                if r['competition'] == comp and r['tier'] in {'champion', 'runner-up'}] == [
                    ('champion', champion * 100), ('runner-up', runner * 100)]
    for comp, rate in prizes.PRELIMINARY.items():
        assert [r['amount_cents'] for r in records if r['competition'] == comp] == [rate * 100] * 2


def test_opening_posts_once_and_preserves_archive_on_retry(world):
    edition(world, 'LIB_PRE2', ['S1'], champion=False)
    edition(world, 'LIB', ['GROUP:1', 'S1', 'S2', 'S4'])
    world.execute("INSERT INTO ms_economics VALUES('club:1',2029,?)", (json.dumps({'annual_wage_cap_cents': 1000}),))
    snapshot = '\n'.join(world.iterdump())
    world.execute('SAVEPOINT successor')
    first = prizes.settlement(world, args())
    world.execute('ROLLBACK TO successor')
    world.execute('RELEASE successor')
    assert '\n'.join(world.iterdump()) == snapshot
    assert prizes.settlement(world, args()) == first
    assert first['clubs'] == 2
    total = sum(r['amount_cents'] for r in prizes.awards(world, 2028) if r['club'] == 'club:1')
    fee, wage = prizes.allocation(total)
    assert tuple(world.execute("""SELECT cash_cents,reserve_cents,fee_authority_cents,wage_authority_cents
                                 FROM ms_accounts WHERE club='club:1'""").fetchone()) == (
                                     10000 + total, 2000, 100 + fee, 200 + wage)
    assert json.loads(world.execute("SELECT scenario_json FROM ms_economics WHERE club='club:1'").fetchone()[0]) == {
        'annual_wage_cap_cents': 1000 + wage}
    assert prizes.financial_position(world, 'club:1', 2029, '2029-01-01')['available_transfer_funds_cents'] == 100 + fee
    assert world.execute("SELECT archive_json FROM ms_seasons WHERE season=2028").fetchone()[0] == '{}'
    with pytest.raises(ValueError, match='already settled'):
        prizes.settlement(world, args())


def test_production_requires_exact_policy_record_and_known_receipts(world):
    from braga_era.multiseason.authentic import POLICY

    edition(world, 'LIB_PRE1', ['S1'], champion=False)
    world.execute('PRAGMA ignore_check_constraints=ON')
    world.execute('UPDATE ms_meta SET test_only=0')
    world.execute('PRAGMA ignore_check_constraints=OFF')
    with pytest.raises(ValueError, match='Missing signed'):
        prizes.settlement(world, args())
    world.execute('INSERT INTO ms_pools VALUES(?,2029,?,?,?)',
                  (f'authorized:{POLICY}:2029', 'TRANSITION_POLICY',
                   json.dumps(dict(season=2029, policy=POLICY, prize_policy=prizes.POLICY,
                                   prize_schedule_sha256=prizes.CONFIG_SHA256)), POLICY))
    world.execute("INSERT INTO ms_ledger VALUES('external','club:1','2028-04-01',100,'external prize','{}')")
    with pytest.raises(ValueError, match='reconciliation'):
        prizes.settlement(world, args())
    assert world.execute('SELECT count(*) FROM ms_ledger').fetchone()[0] == 1


def test_asking_price_accounts_for_squad_importance_age_and_terms():
    attrs = {'ovr': 76, 'position': 'FW'}
    prospect = valuation.quote(attrs, 21, 24, [{'minutes': 90, 'rating': 7.8}], 0, 2_000_000_000, 78, True, False)
    veteran = valuation.quote(attrs, 34, 3, [], 4, 0, 65, False, True)
    assert prospect[0] > veteran[0] > 0
    assert prospect[1] and not veteran[1]
    assert valuation.expectation(10, 20, False) == 21


def test_financial_position_survives_bridge_projection(world, tmp_path):
    from uuid import uuid4

    from braga_era.bridge.career import Career as LiveCareer
    from braga_era.bridge.protocol2 import PROTOCOL
    from braga_era.bridge.worker2 import Worker2
    from test_bridge import Career, REQUESTERS, Transport

    edition(world, 'LIB_PRE2', ['S1'], champion=False)
    prizes.settlement(world, args())
    position = prizes.financial_position(world, 'club:1', 2029, '2029-01-01')

    class RegisteredCareer(Career):
        finances = LiveCareer.finances

        def play(self, view, fixture=None, page_id=None):
            assert view == 'finances'
            return dict(restricted_cash_cents=position['cash_cents'], account_unknown=False,
                        accrued_unpaid_cents=None, annual_incremental_commitments_cents=0,
                        financial_position=position)

    career = RegisteredCareer()
    transport = Transport()
    worker = Worker2(transport, career, tmp_path / 'ledger.sqlite', REQUESTERS)
    issue = transport.add(dict(protocol=PROTOCOL, request_id=str(uuid4()), sequence=1,
                               career=career.career, expected_checkpoint=career.head,
                               command='current_finances', args={}))
    worker.poll()
    reply = transport.result(issue)
    assert worker.verify_response(reply)
    assert reply['response']['result']['financial_position'] == position


def test_market_query_projects_only_recorded_terms(world):
    from braga_era import statistics

    world.execute("""INSERT INTO ms_market_decisions VALUES('plan',2029,'club:15',NULL,'squad_plan',
                  '{"need":"FW","private_note":"omit"}')""")
    world.execute("""INSERT INTO ms_market_decisions VALUES('offer',2029,'club:15',NULL,'offer_submitted',
                  '{"fee_cents":100000,"wage_cents":20000,"kind":"loan"}')""")
    query = {'dataset': 'transfer_market', 'club': 'club:15', 'season': 2029}
    statistics.validate(query)
    rows, coverage = statistics.select(world, query, set(), 2029)
    assert rows[0]['transaction'] == 'loan' and rows[0]['wage_cents'] == 20000
    assert rows[1]['need'] == 'FW' and 'private_note' not in rows[1]
    assert coverage['current_offer'] is False
    with pytest.raises(statistics.QueryError, match='narration'):
        statistics.select(world, query, {'ms:unrevealed'}, 2029)
