"""Queries for the recorded Save 046 state; no inference from stale meta notes."""
LEAGUE = "Brasileirão 2027"
ACCOUNT = "2027 football restricted account"


def standings(connection) -> list[dict]:
    rows = connection.execute("""SELECT cl.* FROM clubs cl JOIN league_participants lp
        ON lp.club_id=cl.id WHERE lp.season=2027
        ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name""")
    return [dict(row, position=position) for position, row in enumerate(rows, 1)]


def summary(connection) -> dict:
    meta = dict(connection.execute("SELECT key,value FROM meta"))
    table = standings(connection)
    vasco = next(row for row in table if row["name"] == "Vasco")
    next_fixture = connection.execute("""SELECT f.*,h.name home,a.name away
        FROM fixtures f JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id
        WHERE f.competition=? AND f.status='scheduled' AND (f.home_id=? OR f.away_id=?)
        ORDER BY f.datetime_local,f.id LIMIT 1""", (LEAGUE, vasco["id"], vasco["id"])).fetchone()
    inventory = dict(connection.execute("""SELECT status,count(*) FROM fixtures
        WHERE competition=? GROUP BY status""", (LEAGUE,)))
    cash = connection.execute("SELECT sum(amount_brl) FROM finance_ledger WHERE account=?", (ACCOUNT,)).fetchone()[0]
    budgets = [dict(row, remaining_brl=row["amount_brl"] - row["spent_brl"])
               for row in connection.execute("SELECT * FROM finance_budget WHERE season=2027 ORDER BY id")]
    carioca = connection.execute("SELECT * FROM cup_summary WHERE season=2027 AND club_id=?",
                                 (vasco["id"],)).fetchone()
    sula = connection.execute("SELECT * FROM sudamericana_2027_group_outcomes WHERE club='Vasco'").fetchone()
    cdb = connection.execute("""SELECT * FROM cdb_2027_bracket
        WHERE stage='Oitavas' AND (club_a='Vasco' OR club_b='Vasco')""").fetchone()
    competitions = {
        "Carioca": {"vasco_stage": carioca["stage"], "vasco_status": "eliminated",
                    "champion": meta["carioca_2027_champion"]},
        "Sudamericana": {"vasco_status": sula["route"], "group": sula["group_id"],
                         "position": sula["position"], "points": sula["points"],
                         "group_matches": connection.execute("SELECT count(*) FROM sudamericana_2027_fixtures WHERE status='final'").fetchone()[0]},
        "Copa do Brasil": {"vasco_stage": cdb["stage"], "vasco_status": "eliminated" if cdb["winner"] != "Vasco" else "advanced",
                           "tie_status": cdb["status"], "winner": cdb["winner"],
                           "completed_legs": connection.execute("SELECT count(*) FROM cdb_2027_legs").fetchone()[0]},
        "Libertadores": {"group_matches": connection.execute("SELECT count(*) FROM libertadores_2027_fixtures WHERE status='final'").fetchone()[0]},
    }
    overdue = {}
    for label, name, date_column, predicate in [
        ("Libertadores R16", "libertadores_2027_round_of_16", "second_leg_date", ""),
        ("Sudamericana playoffs", "sudamericana_2027_playoffs", "second_leg_date", ""),
        ("Copa do Brasil QF", "cdb_2027_bracket", "leg2_date", "AND stage='Quartas'"),
    ]:
        overdue[label] = connection.execute(f"SELECT count(*) FROM {name} WHERE status='scheduled' AND {date_column} < ? {predicate}",
                                             (meta["current_date"][:10],)).fetchone()[0]
    return {"save_version": meta["saved_state_version"], "current_date": meta["current_date"],
            "board_confidence": int(meta["board_confidence"]), "manager_matches": int(meta["braga_matches"]),
            "vasco": vasco, "next_fixture": dict(next_fixture) if next_fixture else None,
            "league": {"clubs": len(table), **inventory}, "competitions": competitions,
            "overdue_ties": overdue, "finance": {"restricted_cash_brl": cash, "budgets": budgets,
            "payroll_months": [row[0] for row in connection.execute("""SELECT substr(dated,1,7) FROM finance_ledger
                WHERE account=? AND category='incremental wage payroll' ORDER BY dated""", (ACCOUNT,))]}}
