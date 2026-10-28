"""Use an existing NONCANONICAL rehearsal fixture; never run a new match here."""

import json
import os
from pathlib import Path
import shutil
import pytest
from braga_era.bridge.career import Career
from braga_era.bridge.worker import safe_output
from braga_era.db import file_sha256
from tools.rehearse_task03d import KEY


@pytest.fixture(scope="module")
def actual(tmp_path_factory):
    root = Path(os.environ.get("BRAGA_LINEAGE_TEST_CHAIN", "output/task03d-final"))
    bundle = root / "portable-after-batch-1"
    if not bundle.is_dir():
        pytest.skip(
            "Run the existing Task 03D rehearsal fixture before bridge integration tests"
        )
    # Independent TEST-ONLY fixture copy, not an operational authority transfer.
    target = tmp_path_factory.mktemp("bridge-career")
    shutil.copyfile(bundle / "authority.sqlite", target / "authority.sqlite")
    from braga_era import lineage

    with lineage.access(target / "authority.sqlite", KEY) as (c, t):
        assert t["test_only"]
        row = c.execute(
            "SELECT proof FROM accepted WHERE checkpoint=?", (t["head"],)
        ).fetchone()
        proof = json.loads(row[0])
    # Use the existing generation-one payload, relocating only registry locator.
    source = root / "TEST-ONLY-checkpoint-1"
    shutil.copytree(source, target / "checkpoint")
    import sqlite3

    with sqlite3.connect(target / "authority.sqlite") as c:
        c.execute(
            "UPDATE accepted SET path=?", (str((target / "checkpoint").resolve()),)
        )
        c.execute("UPDATE authority SET active=1,transfer_target=NULL")
        lineage.seal_authority(c, KEY)
    career = Career(target / "authority.sqlite", KEY, "task03d-rehearsal-v1", True)
    return career, target


def test_preview_filters_seeds_and_does_not_touch_accepted_bytes(actual):
    career, target = actual
    db = target / "checkpoint/payload/database.sqlite"
    before = file_sha256(db)
    preview = career.preview("lib:LIB-R16-01:L1")
    assert preview["home"] and preview["away"] and not preview["postmatch_available"]
    safe_output(preview)
    assert "seed_commitment" not in preview
    with pytest.raises(ValueError):
        career.preview("league:332")
    assert file_sha256(db) == before


def test_real_signed_page_retries_and_finances(actual):
    career, target = actual
    a = career.play("narrate", "lib:LIB-R16-01:L1", page_id="bridge-real-test-page-1")
    assert (
        career.play("narrate", "lib:LIB-R16-01:L1", page_id="bridge-real-test-page-1")
        == a
    )
    safe_output(a)
    assert not a["postmatch_available"]
    assert career.finances()["revealed_paid_periods"] == []
    assert career.finances()["revealed_cash_cents"] == 3055000000


@pytest.mark.parametrize(
    "field", ["seed_commitment", "master_seed", "result_json", "token", "sql"]
)
def test_private_fields_cannot_be_posted(field):
    with pytest.raises(ValueError):
        safe_output({"pages": [{field: "private"}]})


def test_initial_accepted_root_is_inspectable_without_forward_execution(accepted_path):
    from braga_era import lineage

    career = Career.__new__(Career)
    career.root_parent = accepted_path
    career.identity = lambda: {"checkpoint": lineage.ROOT}
    before = file_sha256(accepted_path)
    assert len(career.play("next")["events"]) == 16
    assert all(r["played"] == 25 for r in career.play("table")["standings"])
    assert career.finances()["restricted_cash_cents"] == 3055000000
    preview = career.preview("lib:LIB-R16-01:L1")
    assert not preview["lineups_available"] and preview["unknown_team_news"]
    with pytest.raises(ValueError):
        career.play("narrate", "lib:LIB-R16-01:L1", page_id="not-authorized")
    assert file_sha256(accepted_path) == before
