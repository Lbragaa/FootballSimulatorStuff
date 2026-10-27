"""Normal delivery exposes no future events or postmatch data before the whistle."""

from dataclasses import asdict

from .models import SCOPE


def preview(snapshot, result):
    names = {p.id: p.name for t in (snapshot.home, snapshot.away) for p in t.players}
    return {
        "scope": SCOPE,
        "fixture_key": snapshot.fixture_key,
        "synthetic": snapshot.synthetic,
        "home": snapshot.home.name,
        "away": snapshot.away.name,
        "kickoff": snapshot.kickoff,
        "as_of": snapshot.as_of,
        "source_sha256": snapshot.source_sha256,
        "prematch": asdict(result.prematch),
        "plans": [
            {
                **asdict(p),
                "starting_names": [names[i] for i in p.starters],
                "bench_names": [names[i] for i in p.bench],
            }
            for p in result.plans
        ],
        "eligibility_exclusions": [
            {"id": p.id, "name": p.name, "reasons": list(p.exclusion_reasons)}
            for t in (snapshot.home, snapshot.away)
            for p in t.players
            if not p.eligible or p.id in snapshot.archived_ids
        ],
        "notes": list(snapshot.notes),
        "postmatch_available": False,
    }


def summary(snapshot, result):
    teams = (snapshot.home, snapshot.away)
    return {
        "scope": SCOPE,
        "fixture_key": result.fixture_key,
        "home": teams[0].name,
        "away": teams[1].name,
        "score": list(result.score),
        "possession_home": result.possession_home,
        "team_stats": [
            {
                "club_key": team.key,
                "shots": sum(s.club_key == team.key for s in result.shots),
                "on_target": sum(
                    s.club_key == team.key and s.on_target for s in result.shots
                ),
                "xg": round(
                    sum(s.xg for s in result.shots if s.club_key == team.key), 4
                ),
                "yellow_cards": sum(
                    p.yellows for p in result.performances if p.club_key == team.key
                ),
                "red_cards": sum(
                    p.red for p in result.performances if p.club_key == team.key
                ),
                "substitutions": sum(
                    e.kind == "SUBSTITUTION" and e.club_key == team.key
                    for e in result.events
                ),
            }
            for team in teams
        ],
        "performances": [asdict(p) for p in result.performances],
    }


def public_event(event):
    value = asdict(event)
    if event.kind == "SHOT":
        value["details"] = {
            k: v
            for k, v in event.details.items()
            if k not in ("goal", "on_target", "goal_probability")
        }
    seconds = event.elapsed_seconds
    value["display_minute"] = (
        f"90+{(seconds-5400+59)//60}" if seconds > 5400 else str((seconds + 59) // 60)
    )
    return value


class NarrationCursor:
    """In-memory sequential cursor; the normal API has no seek-to-final method."""

    def __init__(self, snapshot, result):
        self._snapshot = snapshot
        self._result = result
        self._position = 0

    def preview(self):
        return preview(self._snapshot, self._result)

    def next(self, count=1):
        if not 1 <= count <= 20:
            raise ValueError("Narration batch must contain 1–20 events")
        batch = self._result.events[self._position : self._position + count]
        self._position += len(batch)
        done = self._position == len(self._result.events)
        value = {
            "scope": SCOPE,
            "events": [public_event(e) for e in batch],
            "postmatch_available": done,
        }
        if done:
            value["postmatch_summary"] = summary(self._snapshot, self._result)
        return value
