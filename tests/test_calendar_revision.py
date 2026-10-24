from contextlib import closing
import copy
from datetime import datetime
import json
import shutil
import sqlite3
import subprocess
import sys

import pytest

from braga_era.calendar import CalendarError
from braga_era.calendar_v2 import Policy, explore, propose, validate, realism_score
from braga_era.checkpoints import (create_candidate,export_checkpoint,restore_checkpoint,verify_checkpoint,
    promote_candidate,read_json,manifest_for)
from braga_era.db import connect_read_only,file_sha256
from braga_era.history import completed_fixtures,digest,load_baseline,table_fingerprint
from braga_era.migrations import apply
from braga_era.profile_v2 import load_plan,APPROVALS
from braga_era.profiles import verify_database


@pytest.fixture(scope='session')
def revised(canonical_path,tmp_path_factory):
    path=tmp_path_factory.mktemp('task02b')/'046C_v2'
    create_candidate(canonical_path,path)
    return path


def test_all_strategies_and_deterministic_recommendation(canonical):
    result=explore(canonical)
    alternatives={a['strategy']:a for a in result['alternatives']}
    assert alternatives['A']['status']=='infeasible_model'
    assert alternatives['A']['realism_score'] is None
    assert result['recommendation']=='B'
    assert alternatives['B']['plan']==load_plan()
    assert alternatives['B']['feasibility']['feasible']
    assert alternatives['C']['feasibility']['feasible']
    assert alternatives['B']['realism_score']['total']>alternatives['C']['realism_score']['total']
    assert alternatives['B']['realism_score']['total']==77.53
    assert alternatives['C']['realism_score']['total']==66.37


def test_revised_constraints_and_date_inventory(canonical):
    plan=load_plan();report=validate(canonical,plan)
    assert report['feasible'],report['problems']
    assert report['holiday_conflicts']==0
    assert not report['new_rest_shortfalls']
    assert report['minimum_new_turnaround_hours']==72
    assert report['maximum_leg_interval_days']==7
    assert report['maximum_stage_wait_days']==28
    assert report['completion']=='2027-12-21 16:00'
    assert len(report['inherited_league_rest_exceptions'])==1
    assert len(plan['league_adjustments'])==70
    assert sum(m['before'][:10]!=m['after'][:10] for m in plan['league_adjustments'])==36
    assert all('2028' not in e['kickoff'] for e in plan['events'])
    finals={e['competition']:e['kickoff'] for e in plan['events'] if e['stage'] in ('FINAL','Final única')}
    assert finals=={'LIB':'2027-12-07 16:00','SULA':'2027-12-21 16:00','CDB':'2027-12-04 16:00'}


@pytest.mark.parametrize('stamp,expected',[
    ('2027-12-21 22:00',False),('2027-12-22 00:00',True),('2027-12-25 16:00',True),
    ('2028-01-01 12:00',True),('2028-01-05 23:59',True),('2028-01-06 00:00',False)])
def test_annual_holiday_blackout(stamp,expected):
    assert Policy().blacked_out(datetime.fromisoformat(stamp)) is expected


def test_72_hour_floor_cannot_be_relaxed():
    with pytest.raises(CalendarError,match='72-hour'):
        Policy(minimum_rest_hours=71).validate()


def test_calendar_cli_enforces_72_floor(canonical_path):
    result=subprocess.run([sys.executable,'-m','braga_era','calendar','--db',str(canonical_path),
                           '--strategy','A','--minimum-rest-hours','71'],capture_output=True,text=True)
    assert result.returncode==2
    assert '72-hour' in result.stderr


def test_extra_travel_buffer_does_not_silently_relax(canonical):
    with pytest.raises(CalendarError,match='infeasible'):
        propose(canonical,'B',Policy(deadline='2027-12-21 22:00',international_buffer_hours=6))


def test_blackout_and_long_return_leg_rejected(canonical):
    plan=copy.deepcopy(load_plan())
    plan['events'][0]['kickoff']='2027-12-25 16:00'
    assert any('holiday' in p for p in validate(canonical,plan)['problems'])
    plan=copy.deepcopy(load_plan())
    event=next(e for e in plan['events'] if e['event_id']=='LIB-R16-01:L2')
    event['kickoff']='2027-10-16 16:00'
    assert any('Return leg too late' in p for p in validate(canonical,plan)['problems'])


def test_mirassol_and_completed_fixtures_never_movable(canonical):
    plan=copy.deepcopy(load_plan())
    row=canonical.execute("""SELECT f.id,f.datetime_local FROM fixtures f JOIN clubs h ON h.id=f.home_id
        JOIN clubs a ON a.id=f.away_id WHERE competition='Brasileirão 2027' AND round='R26'
        AND h.name='Mirassol' AND a.name='Vasco'""").fetchone()
    plan['league_adjustments'].append({'fixture_id':row['id'],'before':row['datetime_local'],
                                    'after':'2027-10-04 16:00','reason':'invalid'})
    assert any('Unauthorized league move' in p for p in validate(canonical,plan)['problems'])
    plan=copy.deepcopy(load_plan())
    plan['league_adjustments'].append({'fixture_id':322,'before':'2027-09-26 16:00',
                                    'after':'2027-10-04 16:00','reason':'invalid'})
    assert not validate(canonical,plan)['feasible']


def test_revised_candidate_full_history_and_finance(revised,canonical_path):
    verified=verify_checkpoint(revised)
    assert verified['ok'] and verified['acceptance_eligible']
    assert verified['metadata']['proposal_revision']=='v2'
    assert verified['metadata']['status']=='candidate'
    assert verified['metadata']['operation_count']==189
    assert len(read_json(revised/'changes.json'))==378
    assert verified['metadata']['canonical_promoted'] is False
    with connect_read_only(revised/'database.sqlite') as c:
        assert digest(completed_fixtures(c))==load_baseline()['completed_fixtures_sha256']
        assert table_fingerprint(c,'players')==load_baseline()['tables']['players']
        assert table_fingerprint(c,'transfers')==load_baseline()['tables']['transfers']
        meta=dict(c.execute('SELECT key,value FROM meta'))
        assert meta['current_date']=='2027-09-26 23:30'
        sept=list(c.execute("SELECT * FROM payroll_obligations WHERE period='2027-09'"))
        assert sum(r['accrued_cents'] for r in sept)==155900001
        assert sum(r['due_cents'] for r in sept)==179966667
        assert len(sept)==5
    assert file_sha256(canonical_path)==load_baseline()['database_sha256']


def test_revised_candidate_deterministic_and_restorable(revised,canonical_path,tmp_path):
    other=tmp_path/'second'
    create_candidate(canonical_path,other)
    assert manifest_for(other)==manifest_for(revised)
    archive=tmp_path/'revised.zip'
    export_checkpoint(revised,archive)
    restored=tmp_path/'restored'
    assert restore_checkpoint(archive,restored)['ok']
    assert file_sha256(restored/'database.sqlite')==file_sha256(revised/'database.sqlite')
    assert verify_database(restored/'database.sqlite','046C',canonical_path).ok


@pytest.mark.parametrize('statement',[
    "UPDATE fixtures SET home_goals=4 WHERE id=322",
    "UPDATE fixtures SET datetime_local='2027-10-05 16:00' WHERE id=(SELECT f.id FROM fixtures f JOIN clubs h ON h.id=f.home_id JOIN clubs a ON a.id=f.away_id WHERE f.round='R26' AND h.name='Mirassol' AND a.name='Vasco')",
    "UPDATE fixtures SET datetime_local='2027-12-25 16:00' WHERE id=352",
    "UPDATE payroll_obligations SET accrued_cents=0 WHERE period='2027-09' AND player_id=227",
    "UPDATE board_objectives SET achieved='achieved' WHERE competition='Finance'",
])
def test_v2_rejects_unauthorized_changes(revised,canonical_path,tmp_path,statement):
    path=tmp_path/'mutated.sqlite'
    shutil.copyfile(revised/'database.sqlite',path)
    with closing(sqlite3.connect(path)) as c:
        c.execute(statement);c.commit()
    assert not verify_database(path,'046C',canonical_path).ok


def test_rollback_including_future_league_moves(canonical_path,tmp_path):
    path=tmp_path/'scratch.sqlite';shutil.copyfile(canonical_path,path)
    with closing(sqlite3.connect(path)) as c:
        c.row_factory=sqlite3.Row
        with pytest.raises(RuntimeError):
            apply(c,load_plan(),load_baseline()['database_sha256'],fail_after='calendar',revision='v2')
    assert file_sha256(path)==file_sha256(canonical_path)


def test_v2_promotion_api_only_on_temporary_registry(revised,tmp_path):
    metadata=read_json(revised/'checkpoint.json');registry=tmp_path/'canonical.json'
    args={'expected_parent_sha256':metadata['parent_sha256'],
          'approved_candidate_sha256':metadata['database_sha256'],'approvals':[]}
    with pytest.raises(ValueError,match='approvals'):
        promote_candidate(revised,registry,**args)
    assert not registry.exists()
    args['approvals']=APPROVALS
    assert promote_candidate(revised,registry,**args)['save_version']=='046C'
    with pytest.raises(ValueError,match='parent conflict'):
        promote_candidate(revised,registry,**args)
    assert read_json(revised/'checkpoint.json')['status']=='candidate'
