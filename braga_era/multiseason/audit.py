"""Read-only season reconciliation, separate from cryptographic/replay validation."""
from collections import Counter,defaultdict
from datetime import datetime
import json
from .competitions import standings
from .calendar import venue


def season(c,year):
    state=c.execute('SELECT state,archive_json FROM ms_seasons WHERE season=?',(year,)).fetchone()
    if not state or state[0]!='archived':raise ValueError('Full-season audit requires an archived development season')
    fixtures=[dict(r) for r in c.execute('SELECT f.* FROM ms_fixtures f JOIN ms_editions e ON e.id=f.edition WHERE e.season=? ORDER BY kickoff,key',(year,))]
    if not fixtures or any(f['status']!='final' for f in fixtures):raise ValueError('Archived season has missing/pending football')
    clocks=defaultdict(list);groups=Counter()
    for f in fixtures:
        when=datetime.fromisoformat(f['kickoff']);groups[f['kickoff']]+=1
        for key in (f['home'],f['away']):clocks[key].append(when)
    for club,kickoffs in clocks.items():
        if any((b-a).total_seconds()<72*3600 for a,b in zip(kickoffs,kickoffs[1:])):raise ValueError('Club overlap/rest violation: '+club)
    actual=[]
    for row in c.execute("SELECT args_json FROM ms_operations WHERE kind='commit_season_calendar'"):
        calendar=json.loads(row[0])
        if calendar['season']!=year:continue
        occupied=defaultdict(list)
        for f in fixtures:
            when=datetime.fromisoformat(f['kickoff'])
            if not '01-05'<when.strftime('%m-%d')<'12-22' or any(datetime.fromisoformat(a)<=when<=datetime.fromisoformat(b) for a,b in calendar['international_windows']):raise ValueError('Season crossed a committed football blackout')
            occupied[venue(c,calendar,f['edition'],f['stage'],f['home'])].append(when)
        if any((b-a).total_seconds()<3*3600 for starts in occupied.values() for a,b in zip(sorted(starts),sorted(starts)[1:])):raise ValueError('Shared venue overlap')
        actual.append(calendar['policy'])
    tables={}
    for e in c.execute("SELECT * FROM ms_editions WHERE season=? AND format='league'",(year,)):
        table=standings(c,e['id']);n=len(table)
        if any(r['played']!=2*(n-1) or r['wins']+r['draws']+r['losses']!=r['played'] for r in table):raise ValueError('League appearances/standings differ')
        if sum(r['gf'] for r in table)!=sum(r['ga'] for r in table):raise ValueError('League goal reconciliation differs')
        games=[f for f in fixtures if f['edition']==e['id']]
        expected_points=sum(2 if f['home_goals']==f['away_goals'] else 3 for f in games)
        if sum(r['points'] for r in table)!=expected_points:raise ValueError('League points differ from actual recorded scores')
        tables[e['id']]={'clubs':n,'fixtures':len(games),'standings_reconcile':True}
    accounts={}
    archived_accounts={r['club']:r for r in json.loads(state['archive_json'])['finances']}
    for account in c.execute('SELECT * FROM ms_accounts'):
        opening=None
        for op in c.execute("SELECT args_json,response_json FROM ms_operations WHERE kind='open_recorded_account'"):
            if json.loads(op[0])['club']==account['club']:opening=json.loads(op[1])['recognized_cash_cents'];break
        if opening is None:raise ValueError('Account has no authenticated opening operation')
        movement=c.execute('SELECT coalesce(sum(amount_cents),0) FROM ms_ledger WHERE club=?',(account['club'],)).fetchone()[0]
        if opening+movement!=account['cash_cents'] or account['cash_cents']<account['reserve_cents']:raise ValueError('Cash/ledger/reserve reconciliation differs')
        if account['club'] in archived_accounts:
            old=archived_accounts[account['club']]
            through_year=c.execute('SELECT coalesce(sum(amount_cents),0) FROM ms_ledger WHERE club=? AND dated<?',(account['club'],f'{year+1}-01-01')).fetchone()[0]
            if opening+through_year!=old['cash_cents']:raise ValueError('Archived year-end financial snapshot differs from recorded ledger')
            accounts[account['club']]={'opening_cents':opening,'ledger_movement_through_year_cents':through_year,'year_end_cash_cents':old['cash_cents'],'reserve_cents':old['reserve_cents']}
    payroll=[r[0] for r in c.execute('SELECT period FROM ms_payroll WHERE period LIKE ? ORDER BY period',(str(year)+'-%',))]
    from .market import unpaid_periods
    if unpaid_periods(c,year):raise ValueError('Required contract-backed payroll is missing')
    return {'season':year,'scope':'NONCANONICAL DEVELOPMENT TEST','fixture_counts':dict(Counter(f['edition'] for f in fixtures)),
            'all_fixtures_final':True,'club_rest_and_venue_checks':True,'calendar_policies':actual,'league_tables':tables,
            'recorded_accounts':accounts,'paid_periods':payroll,'unknown_club_finances':'not asserted as zero or reconciled by this report',
            'production_modified':False}
