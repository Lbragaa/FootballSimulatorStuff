"""Reproducible noncanonical match and career cohort calibration."""

from argparse import ArgumentParser
from collections import Counter
from dataclasses import asdict, replace
import json
from math import sqrt
from random import Random
from statistics import mean, median
from time import perf_counter

from braga_era.engine import commit_seeds, prepare, simulate_match, validate_match
from braga_era.engine.config import REALISM_VERSION
from braga_era.engine.models import Coach, CompetitionRules, Player, Snapshot, Team
from braga_era.engine.substitutions import VERSION
from braga_era.multiseason import development
from braga_era.history import digest
from braga_era.world.forward_config import configuration
from braga_era.world.knockout_v2 import resolve, validate_bundle
from braga_era.world.policy import ReadinessPolicy, Rules


def team(name, start, quality, formation, *, tired=False, shallow=False):
    positions = 'GK DF DF DF DF DF MF MF MF MF FW FW FW GK DF MF FW'.split()
    if shallow:
        positions = positions[:14]
    players = tuple(Player(start+i,name,f'{name}-{i}',role,quality+(i%5)-2,
                           quality,quality,quality,quality,quality,quality if role=='GK' else 22,
                           76 if tired else 98,60)
                    for i,role in enumerate(positions))
    return Team(name,name,quality,0,players,Coach(formation=formation))


def interval(successes,n):
    p=successes/n
    z=1.96
    center=(p+z*z/(2*n))/(1+z*z/n)
    radius=z*sqrt((p*(1-p)+z*z/(4*n))/n)/(1+z*z/n)
    return [round(center-radius,4),round(center+radius,4)]


def cell(snapshot, config, count, *, cup=False):
    totals=Counter()
    durations=[]
    people={p.id:p for side in (snapshot.home,snapshot.away) for p in side.players}
    reds=Counter()
    minutes=Counter()
    for i in range(count):
        start=perf_counter()
        commitment=commit_seeds(snapshot,config,f'realism-registered:{snapshot.fixture_key}:{i}')
        result=simulate_match(snapshot,prepare(snapshot,config,commitment),config,commitment)
        durations.append((perf_counter()-start)*1000)
        validate_match(snapshot,result,config)
        if cup:
            rules=Rules('STATE',extra_time=True,penalties=True)
            b=resolve(snapshot,result,config,rules)
            validate_bundle(snapshot,result,config,rules,(0,0),b)
            totals['et']+=int(b['duration_seconds']>result.duration_seconds)
            totals['shootouts']+=int(any(e['kind']=='PENALTY_SHOOTOUT_START' for e in b['events']))
        else:
            b=asdict(result)
        h,a=b['score']
        totals['home' if h>a else 'away' if h<a else 'draw']+=1
        totals['goals']+=h+a
        totals['five_plus']+=int(h+a>=5)
        totals['shots']+=len(b['shots'])
        totals['target']+=sum(s['on_target'] for s in b['shots'])
        totals['xg']+=sum(s['xg'] for s in b['shots'])
        events=b['events']
        totals['yellow']+=sum(e['kind']=='YELLOW_CARD' for e in events)
        dismissals=[e for e in events if e['kind']=='RED_CARD']
        totals['dismissal_matches']+=bool(dismissals)
        for e in dismissals:
            totals['second' if e['details']['reason']=='second yellow' else 'direct']+=1
            reds[people[e['player_id']].position]+=1
        totals['injuries']+=sum(p['injured'] for p in b['performances'])
        totals['substitutions']+=sum(e['kind']=='SUBSTITUTION' for e in events)
        for p in b['performances']:
            minutes[people[p['player_id']].position]+=p['seconds_played']/60
            if p['seconds_played']:
                totals['rating_sum']+=p['rating']
                totals['ratings']+=1
    return {**dict(totals), 'matches':count,'dismissal_match_ci95':interval(totals['dismissal_matches'],count),
            'red_by_position':dict(reds),'minutes_by_position':{k:round(v) for k,v in minutes.items()},
            'engine_median_ms':round(median(durations),3), 'engine_p95_ms':round(sorted(durations)[int(.95*(count-1))],3)}


def trajectories():
    report={}
    for pos,age in [('DF',18),('FW',18),('MF',25),('DF',32),('GK',32)]:
        samples=[]
        legacy=[]
        for i in range(240):
            attrs={'position':pos, 'ovr':70, **dict.fromkeys(('attack','defense','physical','passing','composure','goalkeeping'),70)}
            prior=development.profile(attrs,development.stream('cohort-v1',i,pos,age))
            history=[70]
            old=[70]
            for year in range(10):
                attrs=development.project(attrs,age+year,prior,60*(300 if i%3==0 else 2000),i%4,
                                          development.stream('cohort-v1',i,pos,age,year))
                history.append(attrs['ovr'])
                # Previous offseason with an active contract and no known potential hint.
                rng=Random(int(digest({'seed':'cohort-v1','stream':('development',year,i),
                                       'policy':'autonomous-offseason-development-1'}),16))
                mean_delta=.7 if age+year<23 else -.7 if age+year>=31 else .1
                delta=round(max(-2,min(2,rng.gauss(mean_delta,.35))),3)
                old.append(round(max(15,min(95,old[-1]+delta)),3))
            samples.append(history)
            legacy.append(old)
        report[f'{pos}:{age}']={'mean_ovr': [round(mean(row[y] for row in samples),2) for y in range(11)],
                                'legacy_mean_ovr':[round(mean(row[y] for row in legacy),2) for y in range(11)],
                                'first_year_non_gain':sum(row[1]<=row[0] for row in samples),
                                'illustrations':[samples[i] for i in (0,9,22)]}
    return report


def main():
    p=ArgumentParser(description=__doc__)
    p.add_argument('--count',type=int,default=300)
    args=p.parse_args()
    if args.count<100: p.error('At least 100 matches per cell')
    output={}
    for version in (VERSION,REALISM_VERSION):
        cells={}
        for name,h,a,tired,cup in [
            ('even',72,72,False,False),('strong-home',82,65,False,False),
            ('strong-away',65,82,False,False),('neutral-cup-congested',72,72,True,True),
        ]:
            snap=Snapshot(f'calibration:{name}','2028-11-02 16:00','2028-10-30 16:00',
                          team('home',100,h,'4-3-3',tired=tired,shallow=tired),
                          team('away',200,a,'4-2-3-1'),CompetitionRules('STATE',2028),'0'*64)
            cells[name]=cell(snap,configuration(ReadinessPolicy(),final=cup,engine_version=version),args.count,cup=cup)
        output[version]=cells
    print(json.dumps({'noncanonical':True,'matches':output,'development':trajectories()},indent=2))


if __name__=='__main__':
    main()
