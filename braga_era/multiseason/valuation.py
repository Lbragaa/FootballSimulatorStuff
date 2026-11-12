"""Modeled transfer asking prices for the signed competition economy."""

from collections import defaultdict
import json

VERSION = 'transfer-valuation-1'


def inputs(c, year):
    from .prizes import POLICY

    if not c.execute('SELECT 1 FROM ms_pools WHERE id=?', (f'{POLICY}:{year - 1}',)).fetchone():
        return None
    states = {r[0]: json.loads(r[1]) for r in c.execute('SELECT * FROM world_player_state')}
    strength = dict(c.execute('SELECT key,strength FROM world_clubs'))
    accounts = dict(c.execute('SELECT club,cash_cents-reserve_cents FROM ms_accounts'))
    continental = {r[0] for r in c.execute(
        "SELECT club FROM ms_qualifications WHERE season=? AND competition IN ('LIB','SULA')", (year - 1,))}
    return states, strength, accounts, continental


def roster_depth(players, profiles, lives):
    positions = defaultdict(list)
    for player in players:
        pid = player['id']
        attrs = profiles[pid]
        if attrs['eligible'] and lives.get(pid, {}).get('status') == 'active':
            positions[player['club_key'], attrs['position']].append((-attrs['ovr'], pid))
    return {pid: index for group in positions.values() for index, (_, pid) in enumerate(sorted(group))}


def quote(attrs, age, months, recent, rank, seller_cash, strength, continental, injured):
    """Pure bounded valuation, in BRL cents. Potential is an age/ability proxy."""
    ovr = attrs['ovr']
    age_pct = 122 if age <= 22 else 108 if age <= 27 else 93 if age <= 30 else 72 if age <= 33 else 52
    contract_pct = 55 + 45 * min(max(months, 0), 24) // 24
    minutes = min(360, sum(p['minutes'] for p in recent[:4]))
    average = sum(p['rating'] * p['minutes'] for p in recent[:4]) / max(1, sum(p['minutes'] for p in recent[:4]))
    form_pct = 100 + round(max(-6, min(6, (average - 6.5) * 4)) * minutes / 360)
    starter = rank < (1 if attrs['position'] == 'GK' else 3)
    seller_pct = (130 if starter else 100) + (10 if seller_cash >= 1_500_000_000 else 0)
    exposure_pct = 100 + (6 if continental else 0) + max(0, min(8, round(strength - 70)))
    position_pct = {'GK': 94, 'DF': 100, 'MF': 105, 'FW': 110}.get(attrs['position'], 100)
    fee = max(100000, int((max(0, ovr - 45)) ** 2 * 100000))
    for factor in (age_pct, contract_pct, form_pct, seller_pct, exposure_pct, position_pct, 92 if injured else 100):
        fee = fee * factor // 100
    return max(100000, fee), starter


def expectation(base, current, free):
    return max(base, current * (100 if free else 105) // 100)
