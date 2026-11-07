"""Bounded, durable episode orchestration over existing signed gameplay APIs.

Only presentation is new. Every internal advance retains the ordinary automatic
operation, exact manifest, independent replay, acceptance and page receipts.
"""

from datetime import datetime
import json
from pathlib import Path
import time
from uuid import UUID, uuid5

from .. import lineage
from ..db import connect_read_only
from ..history import canonical_json as encode, digest
from ..world.storage import process_lock
from .roundup import VASCO

PROFILE = "career-episode-1"
MAX_DAYS, MAX_BATCHES, MAX_FIXTURES = 35, 16, 120
MAX_BYTES, MAX_PAGES = 30000, 256  # leave room for final tables/milestone/transport envelope.
MAX_SECONDS = 900  # checked BETWEEN atomic operations, never cancels a committed match.


def projection(event):
    # No duplicate on-field arrays, RNG details, score snapshots or performance
    # dump. In particular a goal precedes any score that incorporates it.
    value = {k: event[k] for k in ("sequence", "elapsed_seconds", "kind", "club_key", "player_id") if k in event}
    value["details"] = {k: v for k, v in event.get("details", {}).items()
                        if k not in {"score", "home_goals", "away_goals", "goal_probability", "duration_seconds", "scope"}}
    return value


class Episode:
    def __init__(self, automatic, *, crash=None):
        self.auto, self.career = automatic, automatic.career
        self.directory = automatic.directory / "episodes"
        self.crash = crash

    def fault(self, stage):
        if self.crash == stage:
            raise RuntimeError("Injected episode crash: " + stage)

    def path(self, request):
        self.auto._path(request)  # canonical UUID validation, no remote paths.
        return self.directory / (request["request_id"] + ".json")

    def save(self, path, op):
        self.auto._save(path, op)

    def state(self):
        parent = self.auto.controls._parent()
        if parent.is_file():
            return {"fixtures": [], "ties": [], "draws": [], "names": {}, "revealed": [], "league": [], "champions": []}
        cursors = {r["fixture"]: r["sequence"] for r in lineage.export_cursor(self.career.registry, self.career.key)["document"]["cursors"]}
        with connect_read_only(parent / "payload/database.sqlite") as db:
            return {"fixtures": [dict(r) for r in db.execute("SELECT * FROM world_fixtures ORDER BY kickoff,key")],
                    "ties": [dict(r) for r in db.execute("SELECT * FROM world_ties ORDER BY key")],
                    "draws": [dict(r) for r in db.execute("SELECT * FROM world_draws ORDER BY key")],
                    "league": [dict(r) for r in db.execute("SELECT c.id,c.name,c.points,c.played,c.wins,c.gf,c.ga FROM clubs c JOIN league_participants p ON p.club_id=c.id AND p.season=2027")],
                    "champions": [dict(r) for r in db.execute("SELECT * FROM world_champions ORDER BY competition")],
                    "names": {r["key"]: r["name"] for r in db.execute("SELECT key,name FROM world_clubs")},
                    "revealed": [r["fixture_key"] for r in db.execute("SELECT fixture_key,max(sequence) AS n FROM world_events GROUP BY fixture_key")
                                 if cursors.get(r["fixture_key"]) == r["n"]]}

    def completed(self, state):
        groups = {}
        for tie in state["ties"]:
            groups.setdefault(tie["competition"] + ":" + tie["stage"], []).append(tie)
        return {k for k, ties in groups.items() if all(t["status"] == "final" and t["winner"] for t in ties)}

    def league_outcomes(self, state):
        rows = state.get("league", [])
        if len(rows) != 20:
            return set()
        outcomes = set()
        for club in rows:
            maximum = club["points"] + 3 * (38 - club["played"])
            others = [r for r in rows if r["id"] != club["id"]]
            if club["points"] > max(r["points"] + 3*(38-r["played"]) for r in others):
                outcomes.add("title:club:" + str(club["id"]))
            # Recorded season_rules: 17th-20th down, continental places remain
            # contingent. Strict inequality avoids inventing tiebreak decisions.
            if sum(r["points"] > maximum for r in others) >= 16:
                outcomes.add("relegation:club:" + str(club["id"]))
        for champion in state.get("champions", []):
            if champion["competition"] == "LEAGUE":
                outcomes.add("title:" + champion["club_key"])
        if all(r["played"] == 38 for r in rows):
            outcomes.add("league_season_complete")
        return outcomes

    def resumable(self, request):
        path = self.path(request)
        if not path.exists():
            return False
        op = self.auto._read(path)
        if op["request_sha256"] != digest(request):
            raise ValueError("Changed episode request")
        head = self.career.identity()["checkpoint"]
        if head == op["head"]:
            return True
        return bool(op["pending"] and op["pending"]["kind"] == "batch"
                    and self.auto.resumable(op["pending"]["request"]))

    def milestone(self, state, stage):
        comp, name = stage.split(":", 1)
        ties = [t for t in state["ties"] if t["competition"] == comp and t["stage"] == name]
        def club(k):
            return {"id": k, "name": state["names"].get(k, k)}
        report = {"competition": comp, "stage": name, "ties": [],
                  "surprises": "No inferred upset labels; use established strength evidence only."}
        for t in ties:
            legs = [f for f in state["fixtures"] if f["tie_key"] == t["key"]]
            report["ties"].append({"tie": t["key"], "clubs": [club(t["club_a"]), club(t["club_b"])],
                "aggregate": [t["aggregate_a"], t["aggregate_b"]], "qualified": club(t["winner"]),
                "eliminated": club(t["club_b"] if t["winner"] == t["club_a"] else t["club_a"]),
                "legs": [{"fixture": f["key"], "home": f["home"], "away": f["away"],
                          "score": [f["home_goals"], f["away_goals"]],
                          "resolution": json.loads(f["resolution_json"] or "null")} for f in legs]})
        report["established_draws"] = [{"stage": d["stage"], "pairings": json.loads(d["pairings_json"])}
            for d in state["draws"] if d["competition"] == comp and d["status"] == "activated"]
        report["next_stage"] = [{"stage": f["stage"], "kickoff": f["kickoff"],
                                 "home": f["home"], "away": f["away"], "status": f["status"]}
            for f in state["fixtures"] if f["competition"] == comp and f["status"] != "final"][:16]
        return report

    def _page(self, fixture, page_id):
        return lineage.gameplay(self.career.registry, self.career.key, "narrate", fixture, 20, page_id=page_id)

    def final_stats(self, fixture, summary):
        # Called only after the signed final page; never used in previews.
        parent = self.auto.controls._parent()
        with connect_read_only(parent / "payload/database.sqlite") as db:
            bundle = json.loads(db.execute("SELECT result_json FROM world_executions WHERE fixture_key=?", (fixture,)).fetchone()[0])
        stats = []
        for club in sorted({p["club_key"] for p in bundle["performances"]}):
            shots = [s for s in bundle["shots"] if s["club_key"] == club]
            stats.append({"club": club, "shots": len(shots), "on_target": sum(bool(s["on_target"]) for s in shots),
                          "xg": round(sum(s["xg"] for s in shots), 3)})
        return {"score": summary["score"], "resolution": summary["resolution"], "team_stats": stats,
                "assessment_basis": "Recorded manager choices and narrated events; Hikari may describe, never invent quotations."}

    def results_sections(self, op, budget):
        from .historical import HistoricalResults
        return HistoricalResults(self.career).episode(op, budget)

    def run(self, request):
        self.auto.controls.trusted()
        path = self.path(request)
        self.directory.mkdir(parents=True, exist_ok=True)
        with process_lock(self.directory, name=".episode.lock"):
            if path.exists():
                op = self.auto._read(path)
                if op["request_sha256"] != digest(request):
                    raise ValueError("Episode request/head mismatch")
                if op["response"] is not None:
                    return op["response"]
                if not self.resumable(request):
                    raise ValueError("Episode request/head mismatch")
            else:
                if self.career.identity()["checkpoint"] != request["expected_checkpoint"]:
                    raise ValueError("Stale episode parent")
                state = self.state()
                op = {"profile": PROFILE, "request": request, "request_sha256": digest(request), "head": request["expected_checkpoint"],
                      "start": self.career.inspect()["accepted_clock"], "baseline": sorted(self.completed(state)),
                      "league_baseline": sorted(self.league_outcomes(state)),
                      "pending": None, "steps": 0, "batches": 0, "consumed": [], "pages": 0,
                      "target": None, "round": None, "target_done": False, "presentation": [],
                      "timings": {}, "response": None}
                retained, prior_deliveries = [], []
                for prior_path in self.directory.glob("*.json"):
                    prior = self.auto._read(prior_path)
                    if prior.get("response"):
                        prior_deliveries.append((prior.get("request", {}).get("sequence", 0), prior_path, prior))
                    if prior.get("response") and prior.get("pending") and prior["pending"]["kind"] == "batch":
                        retained.append((prior_path, prior))
                if prior_deliveries:
                    _, prior_path, prior = max(prior_deliveries, key=lambda row: row[0])
                    if prior["response"]["episode_type"] in {"progress_bound", "blocker", "automatic_disabled"}:
                        for field in ("baseline", "league_baseline", "target", "round", "target_done", "report_pending"):
                            if field in prior:
                                op[field] = prior[field]
                        op["continuation_of"] = prior_path.stem
                if len(retained) > 1:
                    raise ValueError("Multiple unresolved episode commitments; local review required")
                if retained:
                    prior_path, prior = retained[0]
                    op["pending"] = prior["pending"]
                    op["adopted_episode"] = prior_path.stem
                self.save(path, op)
            started = time.perf_counter()
            previous_metric = getattr(self.auto.controls, "metric", None)
            def metric(name, seconds):
                op["timings"][name] = op["timings"].get(name, 0) + seconds
            self.auto.controls.metric = metric
            try:
                reason, report = self._loop(path, op, request, started + MAX_SECONDS)
                metric("episode_processing", time.perf_counter() - started)
                # Ordered sections survive canonical JSON sorting of object keys.
                sections = list(op["presentation"])
                if report:
                    sections.append({"section": "milestone_report", "data": report})
                if op["target_done"] and op["round"]:
                    state = self.state()
                    round_rows = [f for f in state["fixtures"] if f["competition"] == "LEAGUE" and f["stage"] == op["round"]]
                    complete = bool(round_rows) and all(f["status"] == "final" for f in round_rows)
                    complete = complete and {f["key"] for f in round_rows} <= set(state["revealed"])
                    if complete:
                        table = self.career.play("table")
                        rows = [{**r, "position": i, "gd": r["gf"] - r["ga"]} for i, r in enumerate(table["standings"], 1)]
                        sections.append({"section": "league_table", "round": op["round"], "complete": True, "data": rows})
                    else:
                        sections.append({"section": "round_pending", "round": op["round"], "complete": False})
                state = self.state()
                next_vasco = next(({k: f[k] for k in ("key", "home", "away", "kickoff", "competition", "stage", "status")}
                                   for f in state["fixtures"] if f["status"] != "final" and VASCO in (f["home"], f["away"])), None)
                sections.append({"section": "next_agenda", "data": self.career.play("next")["events"], "next_vasco": next_vasco})
                response = {"episode_type": reason, "presentation": sections,
                    "presentation_rule": "Render sections in array order. Narrate each goal before its score; scoreboard and statistics only after FINAL_WHISTLE. Luan Braga is autonomous, never the user avatar.",
                    "world_progress": {"from": op["start"], "to": self.career.inspect()["accepted_clock"],
                                       "batches": op["batches"], "fixtures_revealed": len(op["consumed"])},
                    "accepted_checkpoint": self.career.identity()["checkpoint"],
                    "recovery": {"episode_id": request["request_id"], "resumable": reason in {"progress_bound", "blocker", "automatic_disabled"},
                                 "retry": "Same issue/UUID returns this exact delivery; a new continue resumes durable world/cursors."},
                    "timings_seconds": {k: round(v, 3) for k, v in op["timings"].items()}}
                additions, op['report_pending'] = self.results_sections(op, max(1000, min(14000, 53000-len(encode(response).encode()))))
                index = next((i for i,s in enumerate(sections) if s['section'] in {'league_table','round_pending','next_agenda'}), len(sections))
                sections[index:index] = additions
                if len(encode(response).encode()) > 55000:
                    raise RuntimeError("Episode response bound: original journal retained")
                response = json.loads(encode(response))  # normalize integer mapping keys before first delivery/retry.
                op["response"] = response
                self.save(path, op)
                self.fault("before_response")
                return response
            finally:
                self.auto.controls.metric = previous_metric
                self.save(path, op)  # retain timing/progress evidence even on an injected/process-stage failure.

    def _loop(self, path, op, request, deadline):
        for _ in range(1024):
            if op["pending"]:
                pending = op["pending"]
                if pending["kind"] == "batch":
                    try:
                        self.auto.play(pending["request"])
                    except ValueError as error:
                        known = next((message for message in (
                            "Unresolved qualifier/draw at", "Unresolved competition dependency:",
                            "Fixture final or awaiting an unresolved qualifier/draw", "Draw dependency lacks a qualified club:",
                            "Invalid qualification inventory:", "Missing or phantom qualifiers",
                            "A club has overlapping simultaneous fixtures", "Club already has an unfinished overlapping fixture")
                            if str(error).startswith(message)), None)
                        committed = self.auto._path(pending["request"]).exists()
                        if committed and not known:
                            raise RuntimeError("Committed episode batch requires original recovery") from None
                        op["presentation"].append({"section": "blocker", "data": {
                            "code": known or "CHRONOLOGICAL_BATCH_VALIDATION_FAILED", "agenda": pending["agenda"],
                            "committed_request": pending["request"]["request_id"] if committed else None,
                            "explanation": "The next exact day failed existing eligibility/rule/dependency validation. No fixture skipped; inspect the retained local preparation."}})
                        if not committed:
                            op["pending"] = None
                        return "blocker", None
                    self.fault("after_acceptance")
                    op["batches"] += 1
                    op["head"] = self.career.identity()["checkpoint"]
                    if op.get("adopted_episode"):
                        prior_path = self.directory / (op["adopted_episode"] + ".json")
                        prior = self.auto._read(prior_path)
                        prior["pending"] = None
                        prior["recovered_by"] = request["request_id"]
                        self.save(prior_path, prior)
                    op["pending"] = None
                else:
                    page_started = time.perf_counter()
                    page = self._page(pending["fixture"], pending["page_id"])
                    op["timings"]["narration"] = op["timings"].get("narration", 0) + time.perf_counter() - page_started
                    self.fault("after_page")
                    if not page["events"] and not page["postmatch_available"]:
                        raise RuntimeError("Incomplete committed narration; no winner invented")
                    if pending["detailed"]:
                        events = [projection(e) for e in page["events"]]
                        if events:
                            op["presentation"].append({"section": "vasco_timeline" if pending["fixture"] == op["target"] else "selected_timeline",
                                                       "fixture": pending["fixture"], "events": events})
                        if page["postmatch_available"]:
                            op["presentation"].append({"section": "fulltime", "fixture": pending["fixture"],
                                "data": self.final_stats(pending["fixture"], page["postmatch_summary"])})
                    if page["postmatch_available"]:
                        op["consumed"].append(pending["fixture"])
                        if pending["fixture"] == op["target"]:
                            op["target_done"] = True
                    op["pages"] += 1
                    op["steps"] += 1
                    op["pending"] = None
                self.save(path, op)
                self.fault("after_step")
            state = self.state()
            events = self.career.play("next")["events"]
            newly_done = self.completed(state) - set(op["baseline"])
            # All of a stage's narration must have been consumed, not merely its
            # final batch accepted. Earlier completed stages are baseline only.
            for stage in sorted(newly_done):
                comp, name = stage.split(":", 1)
                keys = {f["key"] for f in state["fixtures"] if f["competition"] == comp and f["stage"] == name and ":reserve:" not in f["key"]}
                # No unseen event in the concluded stage may precede its report.
                remaining = {e["key"] for e in events if e.get("kind") == "narration"}
                if keys <= set(state["revealed"]) and not keys & remaining:
                    return "vasco_match" if op["target_done"] else "competition_milestone", self.milestone(state, stage)
            confirmed = self.league_outcomes(state) - set(op.get("league_baseline", []))
            league_finals = {f["key"] for f in state["fixtures"] if f["competition"] == "LEAGUE" and f["status"] == "final"}
            if confirmed and league_finals <= set(state["revealed"]):
                return "vasco_match" if op["target_done"] else "league_milestone", {
                    "confirmed": sorted(confirmed), "club_names": state["names"],
                    "basis": "Recorded 38 rounds and 17th-20th relegation; strict mathematical certainty or engine-recorded champion. No early continental berths."}
            if op["target_done"]:
                round_rows = [f for f in state["fixtures"] if f["competition"] == "LEAGUE" and f["stage"] == op["round"]]
                last = max((f["kickoff"] for f in round_rows), default="")
                if not op["round"] or not events or events[0]["kickoff"] > last:
                    return "vasco_match", None
                # Never cross a second Vasco fixture while completing a round.
                if any(VASCO in (e.get("home"), e.get("away")) and e["key"] != op["target"] for e in events):
                    return "vasco_match", None
            if not events:
                return "season_complete", None
            span = (datetime.fromisoformat(events[0]["kickoff"]).date() - datetime.fromisoformat(op["start"]).date()).days
            if (span > MAX_DAYS or op["batches"] >= MAX_BATCHES or len(op["consumed"]) >= MAX_FIXTURES
                or op["pages"] >= MAX_PAGES or len(encode(op["presentation"]).encode()) > MAX_BYTES
                or time.perf_counter() >= deadline):
                return "progress_bound", None
            narration = [e for e in events if e.get("kind") == "narration"]
            if narration:
                event = narration[0]
                # Existing focused non-Vasco selection remains detailed coverage.
                chosen = self.auto.choose(narration)
                event = next(e for e in narration if e["key"] == chosen)
                vasco = VASCO in (event.get("home"), event.get("away"))
                focused = self.auto.directory / "focus.json"
                selected = focused.exists() and self.auto._read(focused)["fixture"] == chosen
                detailed = vasco or selected
                if vasco and op["target"] is None:
                    op["target"] = chosen
                    fixture = next(f for f in state["fixtures"] if f["key"] == chosen)
                    op["round"] = fixture["stage"] if fixture["competition"] == "LEAGUE" else None
                marker = chosen + ":preview"
                if detailed and marker not in op.get("previews", []):
                    preview = self.career.preview(chosen)
                    # No standings, predictions, result-bound diagnostics or prematch model dumps.
                    preview = {k: preview[k] for k in ("fixture_key", "home", "away", "kickoff", "lineups", "eligibility_exclusions") if k in preview}
                    op["presentation"].append({"section": "prematch", "data": preview})
                    op.setdefault("previews", []).append(marker)
                op["pending"] = {"kind": "page", "fixture": chosen, "detailed": detailed,
                    "page_id": f"{PROFILE}:{request['request_id']}:{op['steps']}"}
            else:
                if not self.auto.mode()["enabled"]:
                    return "automatic_disabled", None
                child = {**request, "command": "advance_next_batch", "args": {},
                         "request_id": str(uuid5(UUID(request["request_id"]), f"batch:{op['batches']}")),
                         "expected_checkpoint": self.career.identity()["checkpoint"]}
                op["pending"] = {"kind": "batch", "request": child, "agenda": events}
            self.save(path, op)  # stable child UUID/page ID BEFORE every effect.
        return "progress_bound", None
