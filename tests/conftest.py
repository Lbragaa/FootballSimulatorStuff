from pathlib import Path
import gc
import os
import shutil
import warnings

import pytest

from braga_era.db import connect_read_only
from tools.bootstrap_handoff import extract

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch, tmp_path):
    # A developer's real accepted pointer must never affect isolated tests.
    monkeypatch.setenv(
        "BRAGA_ERA_REGISTRY", str(tmp_path / "no-canonical-registry.json")
    )
    monkeypatch.delenv("BRAGA_ERA_DB", raising=False)


@pytest.fixture(autouse=True)
def discard_ci_disposable_copies(tmp_path,tmp_path_factory):
    yield
    if os.environ.get('BRAGA_DISCARD_TEST_COPIES')!='1' or not tmp_path.exists():return
    target=tmp_path.resolve();base=tmp_path_factory.getbasetemp().resolve()
    if target.parent!=base or not target.name.startswith('test_'):raise ValueError('Unsafe pytest cleanup target')
    gc.collect()
    try:shutil.rmtree(target)
    except PermissionError as error:
        # A Windows diagnostic handle may outlive test teardown. Preserve it;
        # never kill processes or broaden the deletion target to recover space.
        warnings.warn('Retained a locked disposable test copy: '+str(error),ResourceWarning)


@pytest.fixture(scope="session")
def accepted_path():
    import os
    from braga_era.acceptance import catalog
    from braga_era.db import file_sha256

    paths = (
        [Path(os.environ["BRAGA_ERA_ACCEPTED_TEST_DB"])]
        if os.environ.get("BRAGA_ERA_ACCEPTED_TEST_DB")
        else [
            ROOT / "output/ci-accepted/database.sqlite",
            ROOT / "output/Save046C_v2/database.sqlite",
            ROOT / "output/accepted-046c/database.sqlite",
        ]
    )
    path = next((p for p in paths if p.is_file()), None)
    assert (
        path is not None
    ), "Install exact accepted bytes: python tools/bootstrap_accepted.py --download"
    assert file_sha256(path) == catalog()["database_sha256"]
    return path


@pytest.fixture(scope="session")
def canonical_path():
    destination = ROOT / "data/handoff"
    extract(ROOT / "BRAGA_ERA_HANDOFF_AFTER_046.zip", destination)
    return destination / "canonical/braga_save.sqlite"


@pytest.fixture
def canonical(canonical_path):
    with connect_read_only(canonical_path) as connection:
        yield connection
