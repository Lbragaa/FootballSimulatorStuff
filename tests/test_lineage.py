"""Immediate-parent authority, three accepted successors and portable narration."""

import json
from pathlib import Path
import shutil
import sqlite3
import zipfile
import subprocess
import sys
import pytest

from braga_era import lineage
from braga_era.checkpoints import read_json, write_json, manifest_for
from braga_era.db import connect_read_only, file_sha256
from braga_era.history import digest
from braga_era.world.runner import InjectedCrash
from tools.rehearse_task03d import run, KEY


def authorize_first(root, accepted_path):
    root = Path(root)
    reg = root / "a" / "r.sqlite"
    lineage.provision(
        reg,
        KEY,
        test_only=True,
        commissioner="SIMULATED",
        career_id="lineage-unit-v1",
        seed="fixed-before-outcomes",
    )
    m = lineage.prepare(
        reg, KEY, accepted_path, until="2027-09-30 23:59", execution_id="first"
    )
    with lineage.access(reg, KEY) as (c, t):
        d = lineage.expected_authorization(m, t)
    lineage.authorize(reg, KEY, accepted_path, m, d, lineage.sign(KEY, d))
    return reg, m


@pytest.fixture(scope="module")
def candidate(tmp_path_factory, accepted_path):
    root = tmp_path_factory.mktemp("lc")
    reg, m = authorize_first(root, accepted_path)
    target = root / "cp"
    result = lineage.execute(reg, KEY, "first", target)
    return {
        "root": root,
        "registry": reg,
        "manifest": m,
        "checkpoint": target,
        "result": result,
    }


@pytest.fixture(scope="module")
def chain(tmp_path_factory, accepted_path):
    import os

    root = (
        Path(os.environ["BRAGA_LINEAGE_TEST_CHAIN"])
        if os.environ.get("BRAGA_LINEAGE_TEST_CHAIN")
        else tmp_path_factory.mktemp("chain") / "run"
    )
    report = (
        read_json(root / "rehearsal.json")
        if (root / "rehearsal.json").is_file()
        else run(accepted_path, root)
    )
    assert (
        report["single_world_sha256"]
        == "5e1ed0d03c3c5f3d9cce25b043ff8bd33cb296df903a09da1d113d2003dd3151"
    )
    return {"root": root, "registry": Path(report["registry"]), "report": report}


def clone_registry(source, tmp_path):
    reg = tmp_path / "a" / "r.sqlite"
    reg.parent.mkdir()
    shutil.copyfile(source, reg)
    return reg


def test_three_accepted_generations_equal_one_continuous_world(chain):
    r = chain["report"]
    assert [x["receipts"] for x in r["batches"]] == [16, 26, 42]
    assert [x["new_receipts"] for x in r["batches"]] == [16, 10, 16]
    assert r["narration_sequences_across_generations"] == [1, 2, 3]
    assert (
        not r["batch_boundaries_change_football"]
        and r["official_matches_executed"] == 0
    )
    with lineage.access(chain["registry"], KEY) as (c, t):
        assert t["head"] == r["accepted_test_head"]
        assert c.execute("SELECT count(*) FROM accepted").fetchone()[0] == 3
        assert c.execute("SELECT count(*) FROM fixture_claims").fetchone()[0] == 42
        assert c.execute("SELECT count(*) FROM obligation_claims").fetchone()[0] == 1


def test_unaccepted_development_and_stale_parents_fail(
    candidate, chain, accepted_path, tmp_path
):
    with pytest.raises(ValueError, match="unaccepted"):
        lineage.prepare(
            candidate["registry"],
            KEY,
            candidate["checkpoint"],
            until="2027-10-03 23:59",
            execution_id="bad",
        )
    with pytest.raises(ValueError, match="Stale"):
        lineage.prepare(
            chain["registry"],
            KEY,
            accepted_path,
            until="2027-10-09 23:59",
            execution_id="old-root",
        )
    fake = tmp_path / "arbitrary.sqlite"
    fake.write_bytes(b"not an accepted database")
    with pytest.raises(ValueError, match="Unrelated"):
        lineage.prepare(
            chain["registry"],
            KEY,
            fake,
            until="2027-10-09 23:59",
            execution_id="unrelated",
        )


def test_wrong_signature_model_or_execution_id_cannot_replace_claim(
    candidate, accepted_path, tmp_path
):
    reg = clone_registry(candidate["registry"], tmp_path)
    m = {**candidate["manifest"], "execution_id": "fresh-outcome-attempt"}
    with lineage.access(reg, KEY) as (c, t):
        d = lineage.expected_authorization(m, t)
    with pytest.raises(ValueError):
        lineage.authorize(reg, KEY, accepted_path, m, d, "wrong")
    with pytest.raises(sqlite3.IntegrityError):
        lineage.authorize(reg, KEY, accepted_path, m, d, lineage.sign(KEY, d))
    bad = {**m, "seed_policy": "fresh-per-save"}
    with lineage.access(reg, KEY) as (c, t):
        d = lineage.expected_authorization(bad, t)
    with pytest.raises(ValueError):
        lineage.authorize(reg, KEY, accepted_path, bad, d, lineage.sign(KEY, d))


@pytest.mark.parametrize(
    "stage",
    [
        "after_parent_copy",
        "after_claim",
        "after_result",
        "after_new_batch",
        "after_candidate_payload",
        "after_archive",
    ],
)
def test_crash_resumes_original_commitments_and_result(
    stage, tmp_path, accepted_path, candidate
):
    reg, m = authorize_first(tmp_path, accepted_path)
    target = tmp_path / "cp"
    with pytest.raises(InjectedCrash):
        lineage.execute(reg, KEY, "first", target, crash=stage)
    with connect_read_only(target / "world/database.sqlite") as db:
        before = {
            r["fixture_key"]: (r["input_sha256"], r["seed_json"], r["result_sha256"])
            for r in db.execute("SELECT * FROM world_executions")
        }
    result = lineage.execute(reg, KEY, "first", target)
    assert result["world_sha256"] == candidate["result"]["world_sha256"]
    with connect_read_only(target / "world/database.sqlite") as db:
        after = {
            r["fixture_key"]: (r["input_sha256"], r["seed_json"], r["result_sha256"])
            for r in db.execute("SELECT * FROM world_executions")
        }
    for key, (inputs, seeds, cached) in before.items():
        assert after[key][:2] == (inputs, seeds)
        if cached:
            assert after[key][2] == cached


def test_acceptance_needs_separate_signature_and_is_not_repeated(candidate, tmp_path):
    reg = clone_registry(candidate["registry"], tmp_path)
    target = candidate["checkpoint"]
    d = lineage.acceptance_template(reg, KEY, target)
    with pytest.raises(ValueError):
        lineage.accept(reg, KEY, target, d, "incorrect")
    result = lineage.accept(reg, KEY, target, d, lineage.sign(KEY, d))
    assert result["accepted"] and result["test_only"]
    with pytest.raises(ValueError, match="repeated|conflicting"):
        lineage.accept(reg, KEY, target, d, lineage.sign(KEY, d))


@pytest.mark.parametrize("stage", ["before_accept_commit", "after_accept_commit"])
def test_acceptance_crash_is_atomic_and_receipt_recovers(candidate, tmp_path, stage):
    reg = clone_registry(candidate["registry"], tmp_path)
    target = tmp_path / "cp"
    shutil.copytree(candidate["checkpoint"], target)
    (target / "acceptance.json").unlink(missing_ok=True)
    d = lineage.acceptance_template(reg, KEY, target)
    with pytest.raises(InjectedCrash):
        lineage.accept(reg, KEY, target, d, lineage.sign(KEY, d), crash=stage)
    with lineage.access(reg, KEY) as (c, t):
        head = t["head"]
    if stage == "before_accept_commit":
        assert head == lineage.ROOT
        lineage.accept(reg, KEY, target, d, lineage.sign(KEY, d))
    else:
        assert head == candidate["result"]["checkpoint_sha256"]
        assert lineage.recover_acceptance(reg, KEY, target)["acceptance_restored"]
    assert read_json(target / "acceptance.json")["document"] == d


def test_transferred_authority_is_fenced_and_test_cannot_be_production(chain, tmp_path):
    source = chain["root"] / "authority/rehearsal.sqlite"
    with lineage.access(source, KEY) as (c, t):
        assert not t["active"]
    with pytest.raises(ValueError, match="fenced"):
        lineage.gameplay(source, KEY, "next")
    with pytest.raises(ValueError, match="mixed-mode"):
        lineage.restore_backup(
            chain["root"] / "portable-after-batch-1",
            KEY,
            tmp_path / "wrong-mode",
            expected_test_only=False,
        )
    assert not (tmp_path / "wrong-mode").exists()


def test_cursor_delivery_retries_and_cross_checkpoint_spoilers(chain, tmp_path):
    reg = clone_registry(chain["registry"], tmp_path)
    first = "lib:LIB-R16-01:L1"
    page = lineage.gameplay(reg, KEY, "narrate", first, 1, page_id="next-test-page")
    assert page["events"][0]["sequence"] == 4
    assert (
        lineage.gameplay(reg, KEY, "narrate", first, 1, page_id="next-test-page")
        == page
    )
    with pytest.raises(ValueError, match="different request"):
        lineage.gameplay(reg, KEY, "narrate", first, 2, page_id="next-test-page")
    with pytest.raises(ValueError, match="earlier chronological"):
        lineage.gameplay(reg, KEY, "preview", "league:332")
    table = lineage.gameplay(reg, KEY, "table")
    assert all(r["played"] == 25 for r in table["standings"])


def test_signed_cursors_reject_in_range_tampering(chain, tmp_path):
    reg = clone_registry(chain["registry"], tmp_path)
    with sqlite3.connect(reg) as c:
        c.execute("UPDATE cursors SET sequence=sequence+1")
    with pytest.raises(ValueError, match="tampered"):
        lineage.export_cursor(reg, KEY)


def test_cursor_handoff_cannot_rewind_or_change_result(chain, tmp_path):
    reg = clone_registry(chain["registry"], tmp_path)
    envelope = lineage.export_cursor(reg, KEY)
    doc = dict(envelope["document"])
    doc["revision"] -= 1
    with pytest.raises(ValueError, match="Stale"):
        lineage.import_cursor(reg, KEY, lineage.signed(doc, KEY))
    wrong = json.loads(json.dumps(envelope))
    wrong["signature"] = "not-approved"
    with pytest.raises(ValueError, match="signature"):
        lineage.import_cursor(reg, KEY, wrong)


def test_registry_seed_and_head_tampering_fail(chain, tmp_path):
    reg = clone_registry(chain["registry"], tmp_path)
    with sqlite3.connect(reg) as c:
        c.execute("UPDATE authority SET seed='new-outcome-seed'")
    with pytest.raises(ValueError, match="tampered"):
        lineage.inspect(reg, KEY)


def test_parent_transfer_does_not_bootstrap_old_root_or_replay_parent_matches(
    chain, tmp_path, monkeypatch, accepted_path
):
    moved = tmp_path / "machine"
    restored = lineage.restore_backup(
        chain["root"] / "portable-after-batch-1", KEY, moved, expected_test_only=True
    )
    reg = Path(restored["registry"])
    parent = Path(restored["accepted_parent"])

    def forbidden(*args, **kwargs):
        raise AssertionError("Continuation must copy its immediate accepted parent")

    monkeypatch.setattr(lineage, "create", forbidden)
    original = lineage.file_sha256

    def guarded(path):
        if Path(path).resolve() == accepted_path.resolve():
            raise AssertionError("Unexpected external 046C dependency")
        return original(path)

    monkeypatch.setattr(lineage, "file_sha256", guarded)
    m = lineage.prepare(
        reg, KEY, parent, until="2027-10-03 23:59", execution_id="portable-second"
    )
    with lineage.access(reg, KEY) as (c, t):
        d = lineage.expected_authorization(m, t)
    lineage.authorize(reg, KEY, parent, m, d, lineage.sign(KEY, d))
    result = lineage.execute(reg, KEY, m["execution_id"], tmp_path / "next")
    assert result["new_receipts"] == 10 and result["receipts"] == 26


def test_bad_archive_and_payload_tampering_are_rejected(candidate, tmp_path):
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../escape", "invalid")
    with pytest.raises(ValueError):
        lineage.extract(bad, tmp_path / "escaped")
    payload = tmp_path / "payload"
    shutil.copytree(candidate["checkpoint"] / "payload", payload)
    meta = read_json(payload / "checkpoint.json")
    meta["test_only"] = False
    write_json(payload / "checkpoint.json", meta)
    write_json(payload / "manifest.json", manifest_for(payload))
    with lineage.access(candidate["registry"], KEY) as (c, t):
        with pytest.raises(ValueError, match="mixed-mode"):
            lineage.verify_payload(payload, t, KEY, replay=False)


def test_publication_retry_is_bounded_and_never_overwrites(tmp_path, monkeypatch):
    target = tmp_path / "new"
    original = Path.rename
    calls = []

    def transient(self, destination):
        if Path(destination) == target and not calls:
            calls.append(1)
            raise PermissionError("simulated transient filesystem lock")
        return original(self, destination)

    monkeypatch.setattr(Path, "rename", transient)
    with lineage.staged_directory(target) as stage:
        (stage / "data").write_text("verified")
    assert (target / "data").read_text() == "verified"
    with pytest.raises(FileExistsError):
        with lineage.staged_directory(target):
            pass


def test_publication_recovers_after_process_death(tmp_path):
    import subprocess
    import sys

    target = tmp_path / "interrupted"
    script = "from braga_era.lineage import staged_directory; from pathlib import Path; import os; "
    script += f"\nwith staged_directory(Path({str(target)!r})) as stage:\n (stage/'partial').write_text('unpublished')\n os._exit(17)\n"
    result = subprocess.run([sys.executable, "-c", script], check=False)
    assert result.returncode == 17
    assert not target.exists()
    with lineage.staged_directory(target) as stage:
        assert not (stage / "partial").exists()
        (stage / "complete").write_text("verified")
    assert (target / "complete").read_text() == "verified"
    assert not list(tmp_path.glob(".lp-*-*"))


def test_inherited_suspensions_remain_competition_specific(chain):
    first = chain["root"] / "TEST-ONLY-checkpoint-1/payload/database.sqlite"
    third = chain["root"] / "TEST-ONLY-checkpoint-3/payload/database.sqlite"
    with connect_read_only(first) as a, connect_read_only(third) as b:
        banned = a.execute(
            "SELECT * FROM world_discipline WHERE bans>0 ORDER BY player_id LIMIT 1"
        ).fetchone()
        assert banned is not None
        club = a.execute(
            "SELECT club_key FROM world_players WHERE id=?", (banned["player_id"],)
        ).fetchone()[0]
        f = b.execute(
            "SELECT f.*,e.input_json FROM world_fixtures f JOIN world_executions e ON e.fixture_key=f.key WHERE f.competition=? AND f.leg=2 AND (f.home=? OR f.away=?)",
            (banned["competition"], club, club),
        ).fetchone()
        snapshot = json.loads(f["input_json"])["snapshot"]
        player = next(
            p
            for t in ("home", "away")
            for p in snapshot[t]["players"]
            if p["id"] == banned["player_id"]
        )
        assert not player["eligible"] and any(
            "suspension" in reason for reason in player["exclusion_reasons"]
        )


def test_controlled_injury_fitness_morale_form_and_ban_survive_parent_copy(
    candidate, tmp_path
):
    from braga_era.world.scope import calculation
    from braga_era.world.players import projected
    from braga_era.world.policy import ReadinessPolicy

    modified = tmp_path / "controlled-parent.sqlite"
    shutil.copyfile(candidate["checkpoint"] / "payload/database.sqlite", modified)
    with sqlite3.connect(modified) as c:
        pid, state = c.execute(
            "SELECT player_id,state_json FROM world_player_state ORDER BY player_id LIMIT 1"
        ).fetchone()
        state = json.loads(state)
        state.update(
            fitness=61,
            morale=49,
            form=6.8,
            observed_at="2027-09-30 17:33",
            injury_until="2027-10-10 16:00",
        )
        c.execute(
            "UPDATE world_player_state SET state_json=? WHERE player_id=?",
            (json.dumps(state), pid),
        )
        c.execute("INSERT OR REPLACE INTO world_discipline VALUES(?,'LIB',2,1)", (pid,))
    info = {
        "generation": 1,
        "database": modified,
        "history_root": candidate["checkpoint"] / "payload/history_root.sqlite",
        "payload": candidate["checkpoint"] / "payload",
    }
    with calculation(True):
        lineage.clone_parent(
            info, tmp_path / "copied", "unused-for-accepted-parent-copy"
        )
    with connect_read_only(tmp_path / "copied/database.sqlite") as c:
        restored = json.loads(
            c.execute(
                "SELECT state_json FROM world_player_state WHERE player_id=?", (pid,)
            ).fetchone()[0]
        )
        assert restored == state
        assert tuple(
            c.execute(
                "SELECT yellows,bans FROM world_discipline WHERE player_id=? AND competition='LIB'",
                (pid,),
            ).fetchone()
        ) == (2, 1)
    before = projected(restored, "2027-10-03 17:33", ReadinessPolicy())
    assert before["fitness"] == 65.5 and before["injury_until"]
    assert (
        projected(restored, "2027-10-10 16:00", ReadinessPolicy())["injury_until"]
        is None
    )


def test_lineage_lock_rejects_concurrent_executor(candidate, tmp_path):
    reg = clone_registry(candidate["registry"], tmp_path)
    keyfile = tmp_path / "TEST-ONLY-key"
    keyfile.write_bytes(KEY)
    script = "from pathlib import Path; import sys; from braga_era.lineage import execute; execute(sys.argv[1],Path(sys.argv[2]).read_bytes(),'first',sys.argv[3])"
    with lineage.access(reg, KEY, True):
        done = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(reg),
                str(keyfile),
                str(candidate["checkpoint"]),
            ],
            capture_output=True,
            text=True,
        )
    assert done.returncode != 0 and "process lock" in done.stderr


def test_backup_requires_deliberate_recovery_and_contains_no_key(chain, tmp_path):
    reg = clone_registry(chain["registry"], tmp_path)
    bundle = tmp_path / "backup"
    lineage.backup(reg, KEY, bundle)
    assert all(KEY not in p.read_bytes() for p in bundle.iterdir())
    with zipfile.ZipFile(bundle / "checkpoint.zip") as z:
        assert all(KEY not in z.read(n) for n in z.namelist())
    with pytest.raises(ValueError, match="explicit lost-authority"):
        lineage.restore_backup(
            bundle, KEY, tmp_path / "accidental-second-writer", expected_test_only=True
        )
    assert lineage.inspect(reg, KEY)["authority_active"]


def test_incomplete_boundary_and_unregistered_configuration_fail_before_claim(
    candidate, accepted_path, tmp_path
):
    reg = clone_registry(candidate["registry"], tmp_path)
    with pytest.raises(ValueError, match="complete end-of-day"):
        lineage.prepare(
            reg, KEY, accepted_path, until="2027-09-30 16:00", execution_id="incomplete"
        )
    m = json.loads(json.dumps(candidate["manifest"]))
    m["configurations"]["normal"]["version"] = "unsupported"
    with lineage.access(reg, KEY) as (c, t):
        d = lineage.expected_authorization(m, t)
    with pytest.raises(ValueError):
        lineage.authorize(reg, KEY, accepted_path, m, d, lineage.sign(KEY, d))


def test_cli_prepares_and_authorizes_without_executing(accepted_path, tmp_path, capsys):
    from braga_era.continuous import main

    keyfile = tmp_path / "TEST-ONLY.key"
    keyfile.write_bytes(KEY)
    reg = tmp_path / "a/r.sqlite"
    prefix = ["--registry", str(reg), "--key-file", str(keyfile)]

    def invoke(args):
        assert main(prefix + args) == 0
        return json.loads(capsys.readouterr().out)

    assert invoke(["init-rehearsal", "--career", "cli-test-only", "--seed", "fixed"])[
        "test_only"
    ]
    manifest = tmp_path / "manifest.json"
    decision = tmp_path / "decision.json"
    approval = tmp_path / "approval.json"
    invoke(
        [
            "prepare",
            "--parent",
            str(accepted_path),
            "--until",
            "2027-09-30 23:59",
            "--execution-id",
            "cli-batch",
            "--output",
            str(manifest),
        ]
    )
    invoke(
        [
            "authorization-template",
            "--manifest",
            str(manifest),
            "--output",
            str(decision),
        ]
    )
    invoke(["sign-decision", "--decision", str(decision), "--output", str(approval)])
    result = invoke(
        [
            "authorize",
            "--parent",
            str(accepted_path),
            "--manifest",
            str(manifest),
            "--approval",
            str(approval),
        ]
    )
    assert result["authorized"] and not result["execution_started"]
    with lineage.access(reg, KEY) as (c, t):
        assert (
            t["head"] == lineage.ROOT
            and c.execute("SELECT state FROM batches").fetchone()[0] == "authorized"
        )
