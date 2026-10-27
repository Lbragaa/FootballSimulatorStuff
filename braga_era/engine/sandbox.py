"""Disposable demonstrations and complete reports, with no official write path."""

from dataclasses import asdict
import json
from pathlib import Path
import platform
import shutil

from ..checkpoints import staged_directory, write_json, read_json
from ..db import file_sha256
from ..history import digest
from .config import EngineConfig, PARAMETER_PROVENANCE
from .randomness import commit_seeds
from .coaches import prepare
from .match import simulate_match
from .validation import validate_match
from .world import World
from .narration import preview, summary
from .models import SCOPE


def run(db, output, seed, fixture=None, synthetic=False):
    db = Path(db).resolve()
    before = file_sha256(db)
    output = Path(output)
    config = EngineConfig()
    with staged_directory(output) as stage:
        scratch = stage / "scratch.sqlite"
        shutil.copyfile(db, scratch)
        world = World(scratch)
        snapshot = (
            world.synthetic()
            if synthetic
            else (
                world.load_pregame(fixture)
                if fixture
                else world.first_recorded_fixture()
            )
        )
        seeds = commit_seeds(snapshot, config, seed)
        # This file is written before lineup preparation or any match draws.
        write_json(stage / "seed_commitment.json", asdict(seeds))
        plans = prepare(snapshot, config, seeds)
        result = simulate_match(snapshot, plans, config, seeds)
        validation = validate_match(snapshot, result, config)
        if not validation.ok:
            raise ValueError(
                "Sandbox result failed independent validation: "
                + str(validation.errors)
            )
        if file_sha256(scratch) != before or file_sha256(db) != before:
            raise ValueError("STOP: source or disposable database changed")
        write_json(stage / "preview.json", preview(snapshot, result))
        postmatch = summary(snapshot, result)
        report = {
            "scope": SCOPE,
            "official": False,
            "synthetic": snapshot.synthetic,
            "snapshot": asdict(snapshot),
            "snapshot_sha256": snapshot.fingerprint,
            "config": asdict(config),
            "parameter_provenance": PARAMETER_PROVENANCE,
            "result": asdict(result),
            "result_sha256": result.fingerprint,
            "sealed_postmatch_summary": postmatch,
            "summary_sha256": digest(postmatch),
            "validation": validation.to_dict(),
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.system(),
            },
            "database_guard": {
                "before_sha256": before,
                "after_sha256": file_sha256(db),
                "unchanged": True,
            },
        }
        write_json(stage / "private_match_report.json", report)
        write_json(stage / "validation.json", validation.to_dict())
        write_json(
            stage / "narration_cursor.json",
            {"result_sha256": result.fingerprint, "consumed_sequence": 0},
        )
        with (stage / "private_events.jsonl").open("w", encoding="utf-8") as stream:
            for event in result.events:
                stream.write(
                    json.dumps(asdict(event), ensure_ascii=False, sort_keys=True) + "\n"
                )
        (stage / "README.md").write_text(
            f"""# {SCOPE}

This is a disposable-data demonstration, never an official result. `scratch.sqlite` is unchanged. No fixture, table, accepted checkpoint, save version or fictional date was updated.

Start with preview.json. Use `python -m braga_era narrate DIRECTORY --count 1` for the normal sequential delivery. It releases postmatch data only with the final whistle. The private report/event files contain future spoilers and are diagnostic artifacts, not normal pregame ChatGPT context.

Engine {config.version}; source {before}; result {result.fingerprint}. The seed commitment was stored before executing lineup/match draws. No outcome-based reroll was performed.
""",
            encoding="utf-8",
        )
    return {
        "scope": SCOPE,
        "output": str(output.resolve()),
        "fixture_key": snapshot.fixture_key,
        "synthetic": snapshot.synthetic,
        "validation_passed": True,
        "official_records_changed": False,
    }


def next_narration(directory, count=1):
    directory = Path(directory)
    if not 1 <= count <= 20:
        raise ValueError("Narration batch must contain 1–20 events")
    lock = directory / "narration.lock"
    with lock.open("x"):
        pass
    try:
        data = read_json(directory / "private_match_report.json")
        cursor = read_json(directory / "narration_cursor.json")
        if cursor["result_sha256"] != data["result_sha256"]:
            raise ValueError("Cursor belongs to another match")
        if digest(data["result"]) != data["result_sha256"]:
            raise ValueError(
                "Private result changed; narration must not improvise facts"
            )
        if digest(data["sealed_postmatch_summary"]) != data["summary_sha256"]:
            raise ValueError(
                "Sealed summary changed; narration must not improvise facts"
            )
        position = cursor["consumed_sequence"]
        events = data["result"]["events"]
        if not isinstance(position, int) or not 0 <= position <= len(events):
            raise ValueError("Invalid cursor position")
        batch = events[position : position + count]
        public = []
        for event in batch:
            value = dict(event)
            value["details"] = dict(event["details"])
            if event["kind"] == "SHOT":
                value["details"] = {
                    k: v
                    for k, v in value["details"].items()
                    if k not in ("goal", "on_target", "goal_probability")
                }
            public.append(value)
        position += len(batch)
        done = position == len(events)
        response = {"scope": SCOPE, "events": public, "postmatch_available": done}
        if done:
            response["postmatch_summary"] = data["sealed_postmatch_summary"]
        temporary = directory / "narration_cursor.next.json"
        write_json(
            temporary,
            {"result_sha256": cursor["result_sha256"], "consumed_sequence": position},
        )
        temporary.replace(directory / "narration_cursor.json")
        return response
    finally:
        lock.unlink(missing_ok=True)
