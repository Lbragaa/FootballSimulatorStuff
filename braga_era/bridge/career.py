"""Narrow adapter over lineage. No execute, authorize, accept or seed parameter."""

import json
from pathlib import Path
from .. import lineage
from ..db import connect_read_only, file_sha256
from ..history import digest
from ..payroll import cents, financial_statement


class Career:
    def __init__(self, registry, key, career, test_only):
        self.registry, self.key, self.career, self.test_only = (
            Path(registry),
            key,
            career,
            test_only,
        )
        self.identity()

    def identity(self):
        with lineage.access(self.registry, self.key) as (c, t):
            if (
                t["career"] != self.career
                or bool(t["test_only"]) != self.test_only
                or not t["active"]
            ):
                raise ValueError("Career/mode/fencing mismatch")
            return {
                "career": self.career,
                "checkpoint": t["head"],
                "test_only": self.test_only,
            }

    def play(self, view, fixture=None, page_id=None):
        if self.identity()["checkpoint"] == lineage.ROOT:
            return self.root_view(view, fixture)
        v = lineage.gameplay(self.registry, self.key, view, fixture, 1, page_id=page_id)
        if view == "narrate":
            return {
                k: v[k]
                for k in (
                    "fixture_key",
                    "events",
                    "postmatch_available",
                    "postmatch_summary",
                )
                if k in v
            }
        return v

    def root_view(self, view, fixture=None):
        parent = getattr(self, "root_parent", None)
        if parent is None or file_sha256(Path(parent)) != lineage.ROOT:
            raise ValueError("Exact root parent required")
        with connect_read_only(parent) as c:
            group = [
                {
                    "key": r["competition"].lower() + ":" + r["event_id"],
                    "kickoff": r["kickoff"],
                    "kind": "scheduled",
                    "home": r["home"],
                    "away": r["away"],
                }
                for r in c.execute(
                    "SELECT * FROM calendar_events WHERE kickoff=(SELECT min(kickoff) FROM calendar_events)"
                )
            ]
            if view == "next":
                return {"events": group, "official_execution_authorized": False}
            if view == "table":
                return {
                    "basis": "accepted 046C only",
                    "standings": [
                        dict(r)
                        for r in c.execute(
                            "SELECT c.id,c.name,c.points,c.played,c.wins,c.draws,c.losses,c.gf,c.ga FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027 ORDER BY points DESC,wins DESC,(gf-ga) DESC,gf DESC,name"
                        )
                    ],
                }
            if view == "finances":
                return financial_statement(c)
            if view == "preview":
                row = next((r for r in group if r["key"] == fixture), None)
                if not row:
                    raise ValueError("Earlier chronology first")
                return {
                    **row,
                    "fixture_key": fixture,
                    "as_of": "2027-09-26 23:30",
                    "lineups": [],
                    "eligibility_exclusions": [],
                    "lineups_available": False,
                    "unknown_team_news": True,
                    "reason": "No accepted forward snapshot yet; separate batch authorization required",
                    "postmatch_available": False,
                }
            raise ValueError("No accepted narration result")

    def inspect(self):
        v = lineage.inspect(self.registry, self.key)
        return {
            k: v[k]
            for k in (
                "career",
                "test_only",
                "accepted_checkpoint",
                "generation",
                "accepted_clock",
                "authority_active",
            )
        }

    def preview(self, fixture, news=False):
        v = self.play("preview", fixture)
        if "lineups_available" in v:
            return v
        # The original preview contains committed seeds: never transport those.
        keys = (
            "fixture_key",
            "home",
            "away",
            "kickoff",
            "as_of",
            "eligibility_exclusions",
        )
        result = {k: v[k] for k in keys}
        result["lineups"] = [
            {
                "club_key": p["club_key"],
                "formation": p["formation"],
                "coach": p["coach"],
                "defensive_shape": p["defensive_shape"],
                "risk": p["risk"],
                "roles": p["roles"],
                "rationale": p["rationale"],
                "starters": [
                    {"id": i, "name": name}
                    for i, name in zip(p["starters"], p["starting_names"], strict=True)
                ],
                "bench": [
                    {"id": i, "name": name}
                    for i, name in zip(p["bench"], p["bench_names"], strict=True)
                ],
            }
            for p in v["plans"]
        ]
        result["postmatch_available"] = False
        if not news:
            result["prematch"] = v["prematch"]
        return result

    def finances(self):
        v = self.play("finances")
        if "restricted_cash_cents" in v:
            return {
                k: v[k]
                for k in (
                    "restricted_cash_cents",
                    "accrued_unpaid_cents",
                    "annual_incremental_commitments_cents",
                )
            }
        cash = sum(cents(r["amount_brl"]) for r in v["accepted_ledger"])
        paid = [
            {"period": r["key"], **json.loads(r["detail_json"])}
            for r in v["revealed_forward_obligations"]
        ]
        # Expose only aggregate cash and revealed obligations, never the raw ledger.
        return {
            "basis": "accepted parent plus revealed month ends",
            "accepted_cash_cents": cash,
            "revealed_cash_cents": cash - sum(p["cash_cents"] for p in paid),
            "revealed_paid_periods": [p["period"] for p in paid],
            "budgets": [
                {k: r[k] for k in ("category", "amount_brl", "spent_brl")}
                for r in v["accepted_budgets"]
            ],
        }

    def boundary_seen(self, fixture, boundary):
        doc = lineage.export_cursor(self.registry, self.key)["document"]
        cursor = next((r for r in doc["cursors"] if r["fixture"] == fixture), None)
        if not cursor:
            return False
        with lineage.access(self.registry, self.key) as (c, t):
            row = c.execute(
                "SELECT path FROM accepted WHERE checkpoint=?", (t["head"],)
            ).fetchone()
        with connect_read_only(Path(row[0]) / "payload/database.sqlite") as db:
            result = json.loads(
                db.execute(
                    "SELECT result_json FROM world_executions WHERE fixture_key=?",
                    (fixture,),
                ).fetchone()[0]
            )
            return any(
                e["kind"] == boundary for e in result["events"][: cursor["sequence"]]
            )

    def prepare(self, until, request_id):
        with lineage.access(self.registry, self.key) as (c, t):
            if t["head"] == lineage.ROOT:
                # Explicit locally configured parent, never a remotely supplied path.
                parent = getattr(self, "root_parent", None)
                if parent is None:
                    raise ValueError("Root parent not configured")
            else:
                parent = c.execute(
                    "SELECT path FROM accepted WHERE checkpoint=?", (t["head"],)
                ).fetchone()[0]
        manifest = lineage.prepare(
            self.registry,
            self.key,
            parent,
            until=until,
            execution_id="bridge-" + request_id,
        )
        return manifest

    @staticmethod
    def manifest_summary(m):
        return {
            "manifest_sha256": digest(m),
            "execution_id": m["execution_id"],
            "immediate_parent_sha256": m["immediate_parent_sha256"],
            "until": m["until"],
            "fixtures": m["fixtures"],
            "obligations": m["obligations"],
            "world_policy": m["policy"]["version"],
            "engine": m["configurations"]["normal"]["version"],
            "execution_authorized": False,
            "acceptance_authorized": False,
        }

    def candidate(self, checkpoint):
        with lineage.access(self.registry, self.key) as (c, t):
            row = c.execute(
                "SELECT path FROM accepted WHERE checkpoint=?", (checkpoint,)
            ).fetchone()
            if row:
                directory = Path(row[0])
                accepted = True
            else:
                row = c.execute(
                    "SELECT directory FROM batches WHERE checkpoint=? AND state='candidate'",
                    (checkpoint,),
                ).fetchone()
                if not row:
                    raise ValueError("Unknown local candidate")
                directory = Path(row[0])
                accepted = False
            v = lineage.verify_payload(directory / "payload", t, self.key, replay=False)
        return {
            k: v[k]
            for k in (
                "checkpoint_sha256",
                "immediate_parent_sha256",
                "generation",
                "ok",
                "test_only",
            )
        } | {"accepted": accepted, "validation_only": True}
