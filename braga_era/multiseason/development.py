"""Forward-only annual, ability-based development using existing audit rows."""

from collections import defaultdict
from datetime import date
import json
from math import isfinite
from random import Random

from ..history import canonical_json as encode, digest

POLICY = "ability-development-2"
ACTIVATION = "activate_realism"
WEIGHTS = {
    'GK': {'goalkeeping': .64, 'composure': .19, 'passing': .11, 'physical': .06},
    'DF': {'defense': .47, 'physical': .22, 'passing': .15, 'composure': .12, 'attack': .04},
    'MF': {'passing': .38, 'composure': .21, 'defense': .16, 'attack': .16, 'physical': .09},
    'FW': {'attack': .48, 'composure': .22, 'physical': .14, 'passing': .14, 'defense': .02},
}


def activation(c):
    row = c.execute("SELECT response_json FROM ms_operations WHERE kind=? ORDER BY sequence DESC LIMIT 1",
                    (ACTIVATION,)).fetchone()
    return json.loads(row[0]) if row else None


def evidence(c, year, started):
    """Read each covered bundle once. Older accepted fixtures contribute no evidence."""
    totals = defaultdict(lambda: [0, 0])
    since = max(started, f'{year-1:04d}-01-01 00:00:00')
    until = f'{year:04d}-01-01 00:00:00'
    for row in c.execute("""SELECT json_extract(x.result_json,'$.performances')
                            FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture
                            WHERE f.kickoff>? AND f.kickoff<? AND f.status='final'
                            AND x.result_json IS NOT NULL ORDER BY f.kickoff,f.key""", (since, until)):
        for line in json.loads(row[0]):
            item = totals[line['player_id']]
            item[0] += line['seconds_played']
            item[1] += int(line['injured'])
    return totals


def preseason(c, year, started):
    if started >= f'{year:04d}-01-01 00:00:00' or c.execute("""SELECT 1
        FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition
        WHERE e.season=? AND f.status IN ('claimed','final') LIMIT 1""", (year,)).fetchone():
        raise ValueError('Development starts at the first future preseason')
    return evidence(c, year, started)


def stream(seed, player, *purpose):
    return Random(int(digest([POLICY, seed, player, *purpose]), 16))


def rating(attrs):
    return sum(attrs[name] * weight for name, weight in WEIGHTS[attrs['position']].items())


def profile(attrs, rng, *, hint=None):
    current = attrs['ovr']
    headroom = max(1.0, min(14.0, rng.gauss(6, 3)))
    if isinstance(hint, (int, float)) and isfinite(hint) and hint > current:
        headroom = max(1.0, min(16.0, .6 * headroom + .4 * (hint-current)))
    return {'ceiling': round(max(current, min(96.0, current + headroom)), 3),
            'pace': round(rng.uniform(.2, 1.2), 4),
            'peak_shift': rng.randrange(-2, 3), 'ovr_offset': round(current-rating(attrs), 6)}


def project(attrs, age, career, seconds, injuries, rng):
    """A practice baseline, saturating match exposure, and position-specific aging."""
    peak = 26 + career['peak_shift'] + {'GK': 3, 'DF': 1, 'MF': 0, 'FW': -1}[attrs['position']]
    years_from_peak = age - peak
    decline = min(2.1, .22 * max(0, years_from_peak - 3))
    opportunity = min(1.0, seconds / (2100 * 60))
    health = max(.70, 1.0 - .06 * injuries)
    headroom = max(0.0, min(1.0, (career['ceiling'] - attrs['ovr']) / 6))
    learning = (max(.10, min(1.45, .20 - .145 * years_from_peak)) * career['pace']
                * (.58 + .42 * opportunity) * health * headroom)
    after = dict(attrs)
    for name, weight in WEIGHTS[attrs['position']].items():
        age_loss = decline * (1.50 if name == 'physical' else .65 if name == 'composure' else .90)
        delta = learning * (.65 + weight) - age_loss + rng.gauss(0, .28)
        delta = max(-2.7, min(2.0, delta))
        value = attrs[name]
        after[name] = round(max(min(15, value), min(max(99, value), value + delta)), 3)
    derived = rating(after) + career['ovr_offset']
    # Suppress positive ability drift once the role-weighted ceiling is reached.
    if derived > max(attrs['ovr'], career['ceiling']):
        limit = max(attrs['ovr'], career['ceiling']) - attrs['ovr']
        ratio = max(0, min(1, limit / (derived - attrs['ovr'])))
        for name in WEIGHTS[attrs['position']]:
            after[name] = round(attrs[name] + (after[name] - attrs[name]) * ratio, 3)
        derived = rating(after) + career['ovr_offset']
    after['ovr'] = round(max(min(15,attrs['ovr']), min(max(99,attrs['ovr']), derived)), 3)
    return after


def apply(c, player, attrs, year, started, exposure, *, age=None, age_basis=None):
    ident = player['id']
    seed = c.execute('SELECT seed FROM ms_meta').fetchone()[0]
    source = c.execute('SELECT career_phase,potential FROM players WHERE id=?',
                       (player['source_id'],)).fetchone() if player['source_id'] else None
    old = c.execute("""SELECT assumption_json FROM ms_attributes WHERE player=? AND season<?
                       ORDER BY season DESC LIMIT 1""", (ident, year)).fetchone()
    previous = json.loads(old[0]) if old else {}
    if previous.get('version') != POLICY:
        previous = {}
    if age is None:
        phase = str(source[0]).lower() if source else ''
        if previous:
            age = previous['age'] + year - previous['season']
            age_basis = previous['age_basis']
        else:
            rng = stream(seed, ident, 'age-prior')
            age = (rng.randint(18, 22) if 'young' in phase or 'prospect' in phase else
                   rng.randint(32, 36) if 'veteran' in phase else rng.randint(22, 33))
            age_basis = 'modeled from career phase' if phase else 'modeled age prior, age unknown'
    career = previous.get('trajectory') or profile(attrs, stream(seed, ident, 'trajectory'),
                                                    hint=source[1] if source else None)
    seconds, injuries = exposure.get(ident, (0, 0))
    # Prorate the first annual update to the actual forward exposure window.
    end = date(year, 1, 1)
    start = max(date(year-1, 1, 1), date.fromisoformat(started[:10]))
    fraction = max(0, min(1, (end-start).days / (end-date(year-1,1,1)).days))
    after = project(attrs, age, career, seconds, injuries, stream(seed, ident, 'season', year))
    for name in WEIGHTS[attrs['position']]:
        after[name] = round(attrs[name] + fraction * (after[name]-attrs[name]), 3)
    derived = attrs['ovr'] + (rating(after) - rating(attrs))
    after['ovr'] = round(max(min(15, attrs['ovr']), min(max(99, attrs['ovr']), derived)), 3)
    assumption = {'version': POLICY, 'season': year, 'age': age, 'age_basis': age_basis,
                  'trajectory': career, 'seconds': seconds, 'injuries': injuries, 'activation_clock': started,
                  'annual_fraction': round(fraction, 6)}
    c.execute('INSERT INTO ms_attributes VALUES(?,?,?,?,?)',
              (ident,year,encode(attrs),encode(after),encode(assumption)))
    c.execute('UPDATE world_players SET attributes_json=? WHERE id=?',(encode(after),ident))
