"""Additive development schema. Never installed into an accepted checkpoint."""

DDL = """
CREATE TABLE world_info(id INTEGER PRIMARY KEY CHECK(id=1),scope TEXT NOT NULL,
 version TEXT NOT NULL,parent_sha256 TEXT NOT NULL,policy_json TEXT NOT NULL,seed TEXT NOT NULL,clock TEXT NOT NULL);
CREATE TABLE world_clubs(key TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,alias TEXT UNIQUE NOT NULL,
 source_id INTEGER UNIQUE,country TEXT,strength REAL NOT NULL,form REAL NOT NULL,provenance_json TEXT NOT NULL);
CREATE TABLE world_players(id INTEGER PRIMARY KEY,club_key TEXT NOT NULL REFERENCES world_clubs(key),
 source_id INTEGER UNIQUE,modeled INTEGER NOT NULL,attributes_json TEXT NOT NULL,provenance_json TEXT NOT NULL);
CREATE TABLE world_player_state(player_id INTEGER PRIMARY KEY REFERENCES world_players(id),
 state_json TEXT NOT NULL);
CREATE TABLE world_discipline(player_id INTEGER NOT NULL REFERENCES world_players(id),competition TEXT NOT NULL,
 yellows INTEGER NOT NULL CHECK(yellows>=0),bans INTEGER NOT NULL CHECK(bans>=0),PRIMARY KEY(player_id,competition));
CREATE TABLE world_training(id TEXT PRIMARY KEY,club_key TEXT NOT NULL REFERENCES world_clubs(key),
 starts TEXT NOT NULL,expires TEXT NOT NULL,quality_delta REAL NOT NULL CHECK(abs(quality_delta)<=1),
 consumed_fixture TEXT);
CREATE TABLE world_fixtures(key TEXT PRIMARY KEY,competition TEXT NOT NULL,season INTEGER NOT NULL,
 stage TEXT NOT NULL,tie_key TEXT,leg INTEGER NOT NULL,home TEXT REFERENCES world_clubs(key),
 away TEXT REFERENCES world_clubs(key),kickoff TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('scheduled','conditional','final')),
 source_table TEXT NOT NULL,source_key TEXT NOT NULL,depends_json TEXT NOT NULL,
 home_goals INTEGER,away_goals INTEGER,resolution_json TEXT);
CREATE TABLE world_ties(key TEXT PRIMARY KEY,competition TEXT NOT NULL,stage TEXT NOT NULL,
 club_a TEXT REFERENCES world_clubs(key),club_b TEXT REFERENCES world_clubs(key),
 next_tie TEXT,aggregate_a INTEGER NOT NULL DEFAULT 0,aggregate_b INTEGER NOT NULL DEFAULT 0,
 legs_played INTEGER NOT NULL DEFAULT 0,winner TEXT,status TEXT NOT NULL DEFAULT 'scheduled');
CREATE TABLE world_batches(key TEXT PRIMARY KEY,kickoff TEXT NOT NULL,status TEXT NOT NULL,
 input_world_sha256 TEXT NOT NULL,finish_time TEXT);
CREATE TABLE world_executions(fixture_key TEXT PRIMARY KEY REFERENCES world_fixtures(key),
 batch_key TEXT NOT NULL REFERENCES world_batches(key),status TEXT NOT NULL,
 input_json TEXT NOT NULL,input_sha256 TEXT NOT NULL,config_json TEXT NOT NULL,seed_json TEXT NOT NULL,
 result_json TEXT,result_sha256 TEXT,validation_json TEXT,preview_json TEXT NOT NULL);
CREATE TABLE world_receipts(fixture_key TEXT PRIMARY KEY REFERENCES world_executions(fixture_key),
 result_sha256 TEXT NOT NULL,applied_at TEXT NOT NULL);
CREATE TABLE world_events(fixture_key TEXT NOT NULL REFERENCES world_receipts(fixture_key),
 sequence INTEGER NOT NULL,event_json TEXT NOT NULL,PRIMARY KEY(fixture_key,sequence));
CREATE TABLE world_performances(fixture_key TEXT NOT NULL REFERENCES world_receipts(fixture_key),
 player_id INTEGER NOT NULL REFERENCES world_players(id),performance_json TEXT NOT NULL,PRIMARY KEY(fixture_key,player_id));
CREATE TABLE world_obligations(key TEXT PRIMARY KEY,kickoff TEXT NOT NULL,status TEXT NOT NULL,detail_json TEXT NOT NULL);
CREATE TABLE world_operations(sequence INTEGER PRIMARY KEY,phase TEXT NOT NULL,table_name TEXT NOT NULL,
 row_key_json TEXT NOT NULL,before_json TEXT,after_json TEXT,previous_sha256 TEXT NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE world_cursors(fixture_key TEXT PRIMARY KEY REFERENCES world_receipts(fixture_key),
 result_sha256 TEXT NOT NULL,sequence INTEGER NOT NULL DEFAULT 0);
"""

# The handoff already has world_finals/world_final_events: a prefix is NOT a migration inventory.
TABLES = frozenset(
    (
        "world_info",
        "world_clubs",
        "world_players",
        "world_player_state",
        "world_discipline",
        "world_training",
        "world_fixtures",
        "world_ties",
        "world_batches",
        "world_executions",
        "world_receipts",
        "world_events",
        "world_performances",
        "world_obligations",
        "world_operations",
        "world_cursors",
    )
)
