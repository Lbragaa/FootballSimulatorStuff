# Candidate 046C administrative DDL

Original 046 tables are unchanged structurally. Seven added tables:

```sql
CREATE TABLE admin_operations (sequence INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE,
        table_name TEXT NOT NULL, row_key_json TEXT NOT NULL, before_json TEXT, after_json TEXT,
        reason TEXT NOT NULL);
CREATE TABLE admin_policies (policy_id TEXT PRIMARY KEY, policy_json TEXT NOT NULL);
CREATE TABLE calendar_events (event_id TEXT PRIMARY KEY, competition TEXT NOT NULL,
        stage TEXT NOT NULL, leg INTEGER NOT NULL, clubs_json TEXT NOT NULL, depends_json TEXT NOT NULL,
        kickoff TEXT NOT NULL, international INTEGER NOT NULL, source_table TEXT, source_key TEXT,
        source_column TEXT, previous_date TEXT, home TEXT, away TEXT,
        status TEXT NOT NULL CHECK(status IN ('scheduled','reserved')));
CREATE TABLE checkpoint_info (version TEXT PRIMARY KEY, parent_version TEXT NOT NULL,
        parent_sha256 TEXT NOT NULL, schema_version INTEGER NOT NULL, status TEXT NOT NULL CHECK(status='candidate'),
        profile TEXT NOT NULL, plan_sha256 TEXT NOT NULL);
CREATE TABLE payroll_obligations (period TEXT NOT NULL REFERENCES payroll_periods(period),
        player_id INTEGER NOT NULL REFERENCES players(id), covered_from TEXT NOT NULL, covered_to TEXT NOT NULL,
        monthly_cents INTEGER NOT NULL, due_cents INTEGER NOT NULL, accrued_cents INTEGER NOT NULL,
        PRIMARY KEY(period,player_id));
CREATE TABLE payroll_periods (period TEXT PRIMARY KEY, account TEXT NOT NULL,
        policy_id TEXT NOT NULL REFERENCES admin_policies(policy_id), status TEXT NOT NULL,
        amount_due_cents INTEGER NOT NULL CHECK(amount_due_cents>=0), accrued_cents INTEGER NOT NULL CHECK(accrued_cents>=0),
        cash_cents INTEGER NOT NULL CHECK(cash_cents>=0), ledger_id INTEGER UNIQUE REFERENCES finance_ledger(id));
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, migration_id TEXT NOT NULL UNIQUE,
        ddl_sha256 TEXT NOT NULL);
```
