"""Explicit additive migration; inherited tables are not renamed or deleted."""

VERSION = 1
DDL = """
CREATE TABLE ms_meta(id INTEGER PRIMARY KEY CHECK(id=1),profile TEXT NOT NULL,
 parent_checkpoint TEXT NOT NULL,parent_sha256 TEXT NOT NULL,policy_json TEXT NOT NULL,
 seed TEXT NOT NULL,clock TEXT NOT NULL,test_only INTEGER NOT NULL CHECK(test_only=1));
CREATE TABLE ms_migrations(version INTEGER PRIMARY KEY,ddl_sha256 TEXT NOT NULL,parent_sha256 TEXT NOT NULL);
CREATE TABLE ms_seasons(season INTEGER PRIMARY KEY,state TEXT NOT NULL,archive_json TEXT);
CREATE TABLE ms_editions(id TEXT PRIMARY KEY,competition TEXT NOT NULL,season INTEGER NOT NULL REFERENCES ms_seasons(season),
 format TEXT NOT NULL,rules_json TEXT NOT NULL,state TEXT NOT NULL,champion TEXT REFERENCES world_clubs(key),
 UNIQUE(competition,season));
CREATE TABLE ms_entries(edition TEXT REFERENCES ms_editions(id),club TEXT REFERENCES world_clubs(key),
 route TEXT NOT NULL,evidence_json TEXT NOT NULL,PRIMARY KEY(edition,club));
CREATE TABLE ms_pools(id TEXT PRIMARY KEY,season INTEGER NOT NULL,competition TEXT NOT NULL,
 clubs_json TEXT NOT NULL,reason TEXT NOT NULL);
CREATE TABLE ms_fixtures(key TEXT PRIMARY KEY,edition TEXT NOT NULL REFERENCES ms_editions(id),
 stage TEXT NOT NULL,round INTEGER NOT NULL,tie_key TEXT REFERENCES ms_ties(key),home TEXT NOT NULL REFERENCES world_clubs(key),
 away TEXT NOT NULL REFERENCES world_clubs(key),kickoff TEXT NOT NULL,status TEXT NOT NULL,
 home_goals INTEGER,away_goals INTEGER,winner TEXT REFERENCES world_clubs(key),CHECK(home<>away),
 UNIQUE(edition,stage,round,home,away));
CREATE TABLE ms_executions(fixture TEXT PRIMARY KEY REFERENCES ms_fixtures(key),input_json TEXT NOT NULL,
 input_sha256 TEXT NOT NULL,seed_json TEXT NOT NULL,config_json TEXT NOT NULL,result_json TEXT,result_sha256 TEXT);
CREATE TABLE ms_ties(key TEXT PRIMARY KEY,edition TEXT NOT NULL REFERENCES ms_editions(id),stage INTEGER NOT NULL,
 club_a TEXT NOT NULL REFERENCES world_clubs(key),club_b TEXT NOT NULL REFERENCES world_clubs(key),
 winner TEXT REFERENCES world_clubs(key),UNIQUE(edition,stage,club_a),UNIQUE(edition,stage,club_b));
CREATE TABLE ms_qualifications(id TEXT PRIMARY KEY,season INTEGER NOT NULL,competition TEXT NOT NULL,
 club TEXT NOT NULL REFERENCES world_clubs(key),source_json TEXT NOT NULL,UNIQUE(season,competition,club));
CREATE TABLE ms_contracts(id TEXT PRIMARY KEY,player INTEGER NOT NULL REFERENCES world_players(id),
 club TEXT NOT NULL REFERENCES world_clubs(key),starts TEXT NOT NULL,ends TEXT NOT NULL,wage_cents INTEGER NOT NULL CHECK(wage_cents>=0),
 status TEXT NOT NULL,provenance_json TEXT NOT NULL,CHECK(starts<=ends));
CREATE UNIQUE INDEX ms_active_contract ON ms_contracts(player) WHERE status='active';
CREATE TABLE ms_accounts(club TEXT PRIMARY KEY REFERENCES world_clubs(key),cash_cents INTEGER NOT NULL,
 reserve_cents INTEGER NOT NULL,fee_authority_cents INTEGER NOT NULL,wage_authority_cents INTEGER NOT NULL,
 provenance_json TEXT NOT NULL,CHECK(cash_cents>=reserve_cents),CHECK(reserve_cents>=0),
 CHECK(fee_authority_cents>=0),CHECK(wage_authority_cents>=0));
CREATE TABLE ms_ledger(id TEXT PRIMARY KEY,club TEXT NOT NULL REFERENCES ms_accounts(club),
 dated TEXT NOT NULL,amount_cents INTEGER NOT NULL,category TEXT NOT NULL,evidence_json TEXT NOT NULL);
CREATE TABLE ms_transfers(id TEXT PRIMARY KEY,player INTEGER NOT NULL REFERENCES world_players(id),
 seller TEXT REFERENCES world_clubs(key),buyer TEXT REFERENCES world_clubs(key),dated TEXT NOT NULL,
 kind TEXT NOT NULL,detail_json TEXT NOT NULL);
CREATE TABLE ms_attributes(player INTEGER NOT NULL REFERENCES world_players(id),season INTEGER NOT NULL,
 before_json TEXT NOT NULL,after_json TEXT NOT NULL,assumption_json TEXT NOT NULL,PRIMARY KEY(player,season));
CREATE TABLE ms_loans(id TEXT PRIMARY KEY,player INTEGER NOT NULL REFERENCES world_players(id),
 owner TEXT NOT NULL REFERENCES world_clubs(key),borrower TEXT NOT NULL REFERENCES world_clubs(key),
 starts TEXT NOT NULL,ends TEXT NOT NULL,wage_share_bps INTEGER NOT NULL,status TEXT NOT NULL,
 CHECK(starts<=ends),CHECK(wage_share_bps>=0 AND wage_share_bps<=10000));
CREATE UNIQUE INDEX ms_one_loan ON ms_loans(player) WHERE status='active';
CREATE TABLE ms_payroll(period TEXT PRIMARY KEY,detail_json TEXT NOT NULL);
CREATE TABLE ms_runs(id TEXT PRIMARY KEY,max_groups INTEGER NOT NULL,response_json TEXT);
CREATE TABLE ms_income(id TEXT PRIMARY KEY,club TEXT NOT NULL REFERENCES ms_accounts(club),
 due TEXT NOT NULL,amount_cents INTEGER NOT NULL CHECK(amount_cents>0),policy_json TEXT NOT NULL,status TEXT NOT NULL);
CREATE TABLE ms_operations(sequence INTEGER PRIMARY KEY,request_id TEXT NOT NULL UNIQUE,kind TEXT NOT NULL,
 args_json TEXT NOT NULL,response_json TEXT NOT NULL,previous_sha256 TEXT NOT NULL,sha256 TEXT NOT NULL,signature TEXT NOT NULL);
"""

# Explicit migration inventory; a prefix alone never establishes schema ownership.
TABLES = frozenset({"ms_meta", "ms_migrations", "ms_seasons", "ms_editions", "ms_entries",
    "ms_fixtures", "ms_executions", "ms_ties", "ms_qualifications", "ms_contracts", "ms_accounts",
    "ms_ledger", "ms_transfers", "ms_attributes", "ms_operations", "ms_pools", "ms_loans", "ms_payroll", "ms_runs", "ms_income"})
MUTABLE_INHERITED = frozenset({"world_player_state", "world_discipline", "world_players", "world_training", "world_clubs"})
