# Save 046 schema inventory

Generated from read-only `sqlite_master`. 64 user tables; `sqlite_sequence` is internal.

Foreign keys are declared only in part of the legacy schema. `PRAGMA foreign_key_check` passes, but cannot validate undeclared relationships. No schema changes were made.

```sql
CREATE TABLE board_capital_decisions(id integer primary key, dated text not null, title text not null, approved_brl real not null, designated_budget text not null, rationale text not null, fictional integer not null default 1);
CREATE TABLE board_objectives (
 season INTEGER NOT NULL,competition TEXT NOT NULL,objective TEXT NOT NULL,
 importance TEXT NOT NULL,achieved TEXT NOT NULL DEFAULT 'pending',PRIMARY KEY(season,competition));
CREATE TABLE cdb_2027_bracket(tie_code TEXT PRIMARY KEY, stage TEXT NOT NULL, ordinal INTEGER NOT NULL, club_a TEXT, club_b TEXT, first_leg_home TEXT, second_leg_home TEXT, leg1_date TEXT, leg2_date TEXT, status TEXT NOT NULL DEFAULT 'scheduled', winner TEXT, next_tie TEXT);
CREATE TABLE cdb_2027_events(tie_code TEXT NOT NULL,leg INTEGER NOT NULL,minute INTEGER NOT NULL,team TEXT NOT NULL,player TEXT NOT NULL,type TEXT NOT NULL,detail TEXT);
CREATE TABLE cdb_2027_legs(tie_code TEXT NOT NULL,leg INTEGER NOT NULL,dated TEXT NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,hg INTEGER NOT NULL,ag INTEGER NOT NULL,hxg REAL NOT NULL,axg REAL NOT NULL,shots_home INTEGER NOT NULL,shots_away INTEGER NOT NULL,seed INTEGER NOT NULL,PRIMARY KEY(tie_code,leg));
CREATE TABLE cdb_2027_participants(club_name TEXT PRIMARY KEY, club_id INTEGER,entry_route TEXT NOT NULL, model_strength REAL NOT NULL, pot INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE cdb_2027_plan_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE cdb_2027_player_performance(tie_code TEXT NOT NULL,leg INTEGER NOT NULL,player_id INTEGER NOT NULL,club TEXT NOT NULL,minutes INTEGER NOT NULL,goals INTEGER NOT NULL,assists INTEGER NOT NULL,shots INTEGER NOT NULL,xg REAL NOT NULL,rating REAL NOT NULL,form_before REAL,form_after REAL,PRIMARY KEY(tie_code,leg,player_id));
CREATE TABLE cdb_2027_shots(tie_code TEXT NOT NULL,leg INTEGER NOT NULL,minute INTEGER NOT NULL,team TEXT NOT NULL,player TEXT NOT NULL,xg REAL NOT NULL,on_target INTEGER NOT NULL,goal INTEGER NOT NULL);
CREATE TABLE clubs(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,code TEXT,points INTEGER,played INTEGER,wins INTEGER,draws INTEGER,losses INTEGER,gf INTEGER,ga INTEGER,strength REAL,form REAL NOT NULL DEFAULT 0);
CREATE TABLE competition_history(
 season INTEGER NOT NULL,competition TEXT NOT NULL,winner TEXT NOT NULL,runner_up TEXT NOT NULL,
 final_id INTEGER NOT NULL, PRIMARY KEY(season,competition));
CREATE TABLE continental_calendar_actions(id INTEGER PRIMARY KEY AUTOINCREMENT, dated TEXT, action TEXT, notes TEXT);
CREATE TABLE continental_match_audit(fixture_id INTEGER PRIMARY KEY, seed INTEGER, strength_home REAL, strength_away REAL, planned_xg_home REAL, planned_xg_away REAL, tactical_plan TEXT);
CREATE TABLE continental_match_events(id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_id INTEGER, minute INTEGER, team TEXT, player TEXT, type TEXT, xg REAL, detail TEXT);
CREATE TABLE continental_match_shots(id INTEGER PRIMARY KEY AUTOINCREMENT, fixture_id INTEGER, minute INTEGER, team TEXT, player TEXT, xg REAL, on_target INTEGER, goal INTEGER);
CREATE TABLE continental_player_matches(fixture_id INTEGER, player_id INTEGER, club TEXT, started INTEGER, minutes INTEGER, goals INTEGER, assists INTEGER, shots INTEGER, xg REAL, rating REAL, PRIMARY KEY(fixture_id,player_id));
CREATE TABLE continental_qualifications (
 season INTEGER NOT NULL, competition TEXT NOT NULL, club TEXT NOT NULL,
 route TEXT NOT NULL, status TEXT NOT NULL, qualification_detail TEXT,
 PRIMARY KEY (season, competition, club));
CREATE TABLE cup_summary (season INTEGER,competition TEXT,club_id INTEGER,stage TEXT,scored INTEGER,conceded INTEGER,PRIMARY KEY(season,competition,club_id));
CREATE TABLE cup_ties (
 id INTEGER PRIMARY KEY,competition TEXT,season INTEGER,first_leg_id INTEGER,second_leg_id INTEGER,
 home_first_club_id INTEGER,away_first_club_id INTEGER,status TEXT,
 away_first_aggregate INTEGER,home_first_aggregate INTEGER,winner_club_id INTEGER);
CREATE TABLE decisions(id INTEGER PRIMARY KEY,dated TEXT,category TEXT,decision TEXT,impact TEXT);
CREATE TABLE development(id INTEGER PRIMARY KEY,dated TEXT,player_id INTEGER,old_ovr INTEGER,new_ovr INTEGER,reason TEXT);
CREATE TABLE events(id INTEGER PRIMARY KEY,fixture_id INTEGER REFERENCES fixtures(id),minute INTEGER,club_id INTEGER REFERENCES clubs(id),player_id INTEGER REFERENCES players(id),event_type TEXT,xg REAL,notes TEXT);
CREATE TABLE finance_assumptions (
 key TEXT PRIMARY KEY,amount_brl REAL,unit TEXT NOT NULL,basis TEXT NOT NULL,
 source_url TEXT,valid_for TEXT NOT NULL);
CREATE TABLE finance_budget (
 id INTEGER PRIMARY KEY,season INTEGER NOT NULL,category TEXT NOT NULL,amount_brl REAL NOT NULL,
 funding_source TEXT NOT NULL,restriction TEXT NOT NULL,approved_on TEXT NOT NULL,
 spent_brl REAL NOT NULL DEFAULT 0);
CREATE TABLE finance_ledger (
 id INTEGER PRIMARY KEY,dated TEXT NOT NULL,category TEXT NOT NULL,
 account TEXT NOT NULL,amount_brl REAL NOT NULL,restricted_for TEXT NOT NULL,
 description TEXT NOT NULL,fictional INTEGER NOT NULL DEFAULT 1);
CREATE TABLE fixtures(id INTEGER PRIMARY KEY,datetime_local TEXT,home_id INTEGER REFERENCES clubs(id),away_id INTEGER REFERENCES clubs(id),competition TEXT,round TEXT,status TEXT NOT NULL DEFAULT 'scheduled',home_goals INTEGER,away_goals INTEGER,home_xg REAL,away_xg REAL,home_shots INTEGER,away_shots INTEGER,home_possession INTEGER,away_possession INTEGER,home_sot INTEGER,away_sot INTEGER,attendance INTEGER,report TEXT);
CREATE TABLE league_club_audit(
 id INTEGER PRIMARY KEY,dated TEXT NOT NULL,club_id INTEGER NOT NULL,club_name TEXT NOT NULL,
 old_strength REAL,new_strength REAL,reviewed_players INTEGER,
 method TEXT,source_url TEXT,historical_results_unchanged INTEGER DEFAULT 1);
CREATE TABLE league_participants (season INTEGER NOT NULL,club_id INTEGER NOT NULL,origin TEXT NOT NULL,PRIMARY KEY(season,club_id));
CREATE TABLE league_registration_flags(
 id INTEGER PRIMARY KEY,dated TEXT NOT NULL,player_name TEXT,player_ids TEXT,club_names TEXT,
 reason TEXT,status TEXT);
CREATE TABLE league_scouting_audit(
 id INTEGER PRIMARY KEY,date TEXT NOT NULL, club_id INTEGER NOT NULL,player_id INTEGER NOT NULL,
 old_pos TEXT,new_pos TEXT,old_ovr INTEGER,new_ovr INTEGER,old_potential INTEGER,new_potential INTEGER,
 old_attack INTEGER,new_attack INTEGER,old_defense INTEGER,new_defense INTEGER,
 old_passing INTEGER,new_passing INTEGER,old_physical INTEGER,new_physical INTEGER,
 old_composure INTEGER,new_composure INTEGER,old_goalkeeping INTEGER,new_goalkeeping INTEGER,
 scouting_scope TEXT NOT NULL,reason TEXT,source_url TEXT,
 historical_results_unchanged INTEGER DEFAULT 1);
CREATE TABLE league_standings_archive (season INTEGER NOT NULL,team_id INTEGER NOT NULL,position INTEGER NOT NULL,points INTEGER,played INTEGER,wins INTEGER,draws INTEGER,losses INTEGER,gf INTEGER,ga INTEGER,PRIMARY KEY(season,team_id));
CREATE TABLE libertadores_2027_club_form (club TEXT PRIMARY KEY, power_base REAL NOT NULL, group_points INTEGER NOT NULL, group_gd INTEGER NOT NULL, group_finish INTEGER NOT NULL, source TEXT NOT NULL);
CREATE TABLE libertadores_2027_fixtures (id INTEGER PRIMARY KEY, group_id TEXT NOT NULL, matchday INTEGER NOT NULL, dated TEXT NOT NULL, home TEXT NOT NULL, away TEXT NOT NULL, power_home REAL NOT NULL, power_away REAL NOT NULL, home_xg REAL NOT NULL, away_xg REAL NOT NULL, home_goals INTEGER NOT NULL, away_goals INTEGER NOT NULL, home_shots INTEGER NOT NULL, away_shots INTEGER NOT NULL, home_sot INTEGER NOT NULL, away_sot INTEGER NOT NULL, seed INTEGER NOT NULL, status TEXT NOT NULL, UNIQUE(group_id,matchday,home,away));
CREATE TABLE libertadores_2027_group_outcomes (group_id TEXT NOT NULL, rank INTEGER NOT NULL, club TEXT NOT NULL UNIQUE, played INTEGER NOT NULL, won INTEGER NOT NULL, drawn INTEGER NOT NULL, lost INTEGER NOT NULL, points INTEGER NOT NULL, gd INTEGER NOT NULL, gf INTEGER NOT NULL, ga INTEGER NOT NULL, route TEXT NOT NULL, PRIMARY KEY(group_id,rank));
CREATE TABLE libertadores_2027_groups (group_id TEXT NOT NULL, club TEXT NOT NULL UNIQUE, pot INTEGER NOT NULL, played INTEGER NOT NULL, wins INTEGER NOT NULL, draws INTEGER NOT NULL, losses INTEGER NOT NULL, gf INTEGER NOT NULL, ga INTEGER NOT NULL, points INTEGER NOT NULL, PRIMARY KEY(group_id,club));
CREATE TABLE libertadores_2027_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE libertadores_2027_participants (club TEXT PRIMARY KEY, country TEXT NOT NULL, power REAL NOT NULL, pot INTEGER NOT NULL, qualification_route TEXT NOT NULL, canonical_brazil INTEGER NOT NULL DEFAULT 0);
CREATE TABLE libertadores_2027_round_of_16 (tie_id TEXT PRIMARY KEY, first_leg_home TEXT NOT NULL, second_leg_home TEXT NOT NULL, first_leg_date TEXT, second_leg_date TEXT, leg1_result TEXT, leg2_result TEXT, status TEXT NOT NULL, winner TEXT, first_seed_group TEXT NOT NULL, second_seed_group TEXT NOT NULL);
CREATE TABLE market_negotiations_2027(id integer primary key, dated text, player_name text, selling_club text, offered_brl real, outcome text, detail text, fictional integer default 1);
CREATE TABLE match_engine_audit (fixture_id INTEGER PRIMARY KEY,engine_version TEXT,form_mean_home REAL,form_mean_away REAL,home_prematch_xg REAL,away_prematch_xg REAL,tactical_note TEXT);
CREATE TABLE match_form_profile(player_id INTEGER PRIMARY KEY,form_rating REAL,last_updated TEXT,FOREIGN KEY(player_id) REFERENCES players(id));
CREATE TABLE match_shot_detail (fixture_id INTEGER,shot_id INTEGER,minute INTEGER,attacking_phase TEXT,delivery TEXT,shooter_form REAL,shooter_ovr INTEGER,keeper TEXT,keeper_goalkeeping INTEGER,goal_probability REAL,game_state TEXT,PRIMARY KEY(fixture_id,shot_id));
CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE news(id INTEGER PRIMARY KEY,dated TEXT,headline TEXT,body TEXT,type TEXT);
CREATE TABLE ownership_events (
 id INTEGER PRIMARY KEY,dated TEXT NOT NULL,actor TEXT NOT NULL,event_type TEXT NOT NULL,
 event_status TEXT NOT NULL,stake_pct REAL,details TEXT NOT NULL,fictional INTEGER NOT NULL DEFAULT 1,
 seed INTEGER,source_url TEXT);
CREATE TABLE player_form_snapshot (fixture_id INTEGER,player_id INTEGER,form_before REAL,form_after REAL,last_four_rating REAL,weighted_rating REAL,minutes INTEGER,PRIMARY KEY(fixture_id,player_id));
CREATE TABLE player_identity_resolution (archived_id INTEGER PRIMARY KEY, canonical_id INTEGER, resolved_at TEXT, rationale TEXT);
CREATE TABLE player_matches(id INTEGER PRIMARY KEY,fixture_id INTEGER REFERENCES fixtures(id),player_id INTEGER REFERENCES players(id),club_id INTEGER REFERENCES clubs(id),starter INTEGER,minutes INTEGER,goals INTEGER,assists INTEGER,shots INTEGER,xg REAL,rating REAL);
CREATE TABLE player_postmatch_impact (fixture_id INTEGER,player_id INTEGER,saves INTEGER,progressive_actions INTEGER,interceptions INTEGER,pressures INTEGER,expected_goals REAL,finishing_delta REAL,PRIMARY KEY(fixture_id,player_id));
CREATE TABLE player_season_totals(season INTEGER,competition TEXT,player_id INTEGER,club_id INTEGER,apps INTEGER,minutes INTEGER,goals INTEGER,assists INTEGER,shots INTEGER,xg REAL,rating_sum REAL,PRIMARY KEY(season,competition,player_id));
CREATE TABLE players(id INTEGER PRIMARY KEY,club_id INTEGER NOT NULL REFERENCES clubs(id),name TEXT NOT NULL,pos TEXT NOT NULL,ovr INTEGER NOT NULL,potential INTEGER NOT NULL,career_phase TEXT,attack INTEGER,defense INTEGER,passing INTEGER,physical INTEGER,composure INTEGER,goalkeeping INTEGER,fitness INTEGER NOT NULL,morale INTEGER NOT NULL,goals INTEGER DEFAULT 0,assists INTEGER DEFAULT 0,apps INTEGER DEFAULT 0,minutes INTEGER DEFAULT 0,rating_total REAL DEFAULT 0,shots INTEGER DEFAULT 0,xg REAL DEFAULT 0,injury TEXT DEFAULT '',source_url TEXT,source_status TEXT DEFAULT '2026 lineup-derived',UNIQUE(club_id,name));
CREATE TABLE scouting_recalibration(id INTEGER PRIMARY KEY, date TEXT NOT NULL, player_id INTEGER NOT NULL, old_ovr INTEGER, new_ovr INTEGER, old_potential INTEGER,new_potential INTEGER,reason TEXT, source_basis TEXT, historical_results_unchanged INTEGER DEFAULT 1);
CREATE TABLE season_rules (season INTEGER,competition TEXT,rule_key TEXT,detail TEXT,PRIMARY KEY(season,competition,rule_key));
CREATE TABLE shots (
 id INTEGER PRIMARY KEY, fixture_id INTEGER NOT NULL,minute INTEGER NOT NULL,
 club_id INTEGER NOT NULL, player_id INTEGER NOT NULL, xg REAL NOT NULL,
 on_target INTEGER NOT NULL, goal INTEGER NOT NULL, phase TEXT NOT NULL,
 FOREIGN KEY(fixture_id) REFERENCES fixtures(id), FOREIGN KEY(player_id) REFERENCES players(id));
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE sudamericana_2027_fixtures(id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT, matchday INTEGER, dated TEXT, home TEXT, away TEXT, status TEXT DEFAULT 'scheduled', hg INTEGER, ag INTEGER, home_xg REAL, away_xg REAL, UNIQUE(group_id,matchday,home,away));
CREATE TABLE sudamericana_2027_group_outcomes(group_id TEXT,position INTEGER,club TEXT,points INTEGER,gd INTEGER,gf INTEGER,route TEXT, PRIMARY KEY(group_id,position));
CREATE TABLE sudamericana_2027_groups(group_id TEXT NOT NULL, club TEXT NOT NULL, pot INTEGER NOT NULL, points INTEGER DEFAULT 0, played INTEGER DEFAULT 0, gf INTEGER DEFAULT 0, ga INTEGER DEFAULT 0, PRIMARY KEY(group_id,club));
CREATE TABLE sudamericana_2027_playoffs (tie_id TEXT PRIMARY KEY, sula_runner_up TEXT NOT NULL, sula_group TEXT NOT NULL, lib_third TEXT NOT NULL, lib_group TEXT NOT NULL, first_leg_home TEXT NOT NULL, second_leg_home TEXT NOT NULL, first_leg_date TEXT, second_leg_date TEXT, status TEXT NOT NULL, winner TEXT);
CREATE TABLE tactical_match_log (fixture_id INTEGER,minute INTEGER,club_id INTEGER,phase TEXT,description TEXT);
CREATE TABLE training_microcycles_2027(id INTEGER PRIMARY KEY AUTOINCREMENT, start_date TEXT, end_date TEXT, club TEXT, focus TEXT, workload TEXT, content TEXT, target_metric TEXT, effect_status TEXT, coach_note TEXT);
CREATE TABLE transfer_contracts (player_id INTEGER PRIMARY KEY REFERENCES players(id), contract_start TEXT,contract_end TEXT,wage_monthly_brl REAL,annual_wage_commitment_brl REAL,agent_fee_brl REAL,negotiation_seed INTEGER,notes TEXT);
CREATE TABLE transfers(id INTEGER PRIMARY KEY,dated TEXT,player_id INTEGER,from_club INTEGER,to_club INTEGER,fee_brl REAL,wage_brl REAL,status TEXT);
CREATE TABLE world_final_events(
 id INTEGER PRIMARY KEY,world_final_id INTEGER NOT NULL,minute INTEGER NOT NULL,team TEXT NOT NULL,
 player TEXT NOT NULL,event_type TEXT NOT NULL,xg REAL,shot_on_target INTEGER,
 FOREIGN KEY(world_final_id) REFERENCES world_finals(id));
CREATE TABLE world_finals(
 id INTEGER PRIMARY KEY, competition TEXT NOT NULL, season INTEGER NOT NULL,
 datetime_local TEXT NOT NULL, venue TEXT NOT NULL, home_team TEXT NOT NULL, away_team TEXT NOT NULL,
 home_goals INTEGER NOT NULL,away_goals INTEGER NOT NULL,home_xg REAL NOT NULL,away_xg REAL NOT NULL,
 home_shots INTEGER NOT NULL,away_shots INTEGER NOT NULL,home_sot INTEGER NOT NULL,away_sot INTEGER NOT NULL,
 home_possession INTEGER NOT NULL,away_possession INTEGER NOT NULL,penalties_home INTEGER,penalties_away INTEGER,
 champion TEXT NOT NULL, decided_by TEXT NOT NULL, seed INTEGER NOT NULL,fixture_id INTEGER, provenance TEXT NOT NULL,
 UNIQUE(competition,season));
```
