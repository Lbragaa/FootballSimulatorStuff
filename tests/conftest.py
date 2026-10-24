from pathlib import Path

import pytest

from braga_era.db import connect_read_only
from tools.bootstrap_handoff import extract

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def canonical_path():
    destination = ROOT / "data/handoff"
    extract(ROOT / "BRAGA_ERA_HANDOFF_AFTER_046.zip", destination)
    return destination / "canonical/braga_save.sqlite"


@pytest.fixture
def canonical(canonical_path):
    with connect_read_only(canonical_path) as connection:
        yield connection
