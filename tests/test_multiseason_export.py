"""Removing duplicate export replay must still reject signed-state divergence."""
import sqlite3
import pytest
from test_multiseason import candidate,parent,cmd,KEY
from braga_era.db import file_sha256
from braga_era.multiseason import store


def test_export_replays_stage_before_publication(candidate,tmp_path):
    cmd(candidate,'prepare_season',season=2028)
    # Receipts remain authentic, but an allowed additive table no longer matches
    # their effects. Structural/signature validation alone cannot detect this.
    with sqlite3.connect(candidate/'database.sqlite') as c:
        c.execute("UPDATE ms_seasons SET state='archived' WHERE season=2028")
    assert store.validate(candidate,KEY,replay=False)['independent_replay'] is False
    before=file_sha256(candidate/'database.sqlite');target=tmp_path/'must-not-publish'
    with pytest.raises(ValueError,match='Independent multi-season replay differs'):
        store.export(candidate,target,KEY)
    assert not target.exists()
    assert before==file_sha256(candidate/'database.sqlite')
