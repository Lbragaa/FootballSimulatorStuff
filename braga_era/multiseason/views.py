"""Season-aware read projections. Never simulate, narrate or mutate a cursor."""
import json


def player_statistics(c,season):
    totals={}
    for row in c.execute("SELECT x.result_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture JOIN ms_editions e ON e.id=f.edition WHERE e.season=? AND f.status='final' ORDER BY f.key",(season,)):
        for p in json.loads(row[0])['performances']:
            if p['seconds_played']<=0:continue
            total=totals.setdefault(p['player_id'],dict(player_id=p['player_id'],appearances=0,starts=0,seconds=0,goals=0,assists=0,shots=0,xg=0.,rating_total=0.))
            total['appearances']+=1;total['starts']+=int(p['starter']);total['seconds']+=p['seconds_played']
            for field in ('goals','assists','shots','xg'):total[field]+=p[field]
            total['rating_total']+=p['rating']
    return [totals[k] for k in sorted(totals)]


def coach_records(c,season):
    totals={}
    for row in c.execute("SELECT f.home,f.away,f.home_goals,f.away_goals,x.input_json FROM ms_executions x JOIN ms_fixtures f ON f.key=x.fixture JOIN ms_editions e ON e.id=f.edition WHERE e.season=? AND f.status='final' ORDER BY f.key",(season,)):
        data=json.loads(row['input_json'])['snapshot']
        for side,other in (('home','away'),('away','home')):
            coach=data[side]['coach']['name'];club=row[side];gf=row[side+'_goals'];ga=row[other+'_goals']
            total=totals.setdefault((club,coach),dict(club=club,coach=coach,played=0,wins=0,draws=0,losses=0,gf=0,ga=0))
            total['played']+=1;total['wins']+=int(gf>ga);total['draws']+=int(gf==ga);total['losses']+=int(gf<ga);total['gf']+=gf;total['ga']+=ga
    return [totals[k] for k in sorted(totals)]
