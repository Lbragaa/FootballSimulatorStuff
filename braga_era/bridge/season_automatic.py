"""Existing automatic journal/delegation, edition-aware signed successors."""
import json
import time
from . import automatic
from .. import lineage, season_lineage
from ..db import connect_read_only
from ..history import digest
from ..world.storage import process_lock


def play(auto,request):
    def measure(stage, function, *args, **kwargs):
        started = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            metric = getattr(auto.controls, 'metric', None)
            if metric:
                metric(stage, time.perf_counter() - started)

    auto.controls.trusted();path=auto._path(request)
    with process_lock(auto.directory,name='.automatic.lock'):
        if path.exists():
            op=auto._read(path)
            if op['request_sha256']!=digest(request):raise ValueError('Changed season gameplay request')
            if op['response'] is not None:return op['response']
        else:
            if auto.career.identity()['checkpoint']!=request['expected_checkpoint']:raise ValueError('Stale season gameplay parent')
            events=auto.career.play('next')['events']
            narration=[e for e in events if e['kind']=='narration']
            if narration:
                if request['command']!='continue_gameplay':return {'phase':'narration_ready','simulation_advanced':False,'next_events':events}
                page=auto.career.play('narrate',auto.choose(narration),page_id='automatic:'+request['request_id'])
                return {'phase':'narration','simulation_advanced':False,'pages':[page]}
            if not auto.mode()['enabled']:return {'phase':'manual_approval_required','simulation_advanced':False}
            if not events:
                with lineage.access(auto.career.registry,auto.career.key) as (c,t):
                    info,_=season_lineage.current(c,t,auto.career.key)
                    with connect_read_only(info['database']) as db:
                        state=db.execute('SELECT state FROM ms_seasons WHERE season=?',(info['season'],)).fetchone()[0]
                        comps=[r[0] for r in db.execute('SELECT competition FROM ms_editions WHERE season=? ORDER BY competition',(info['season'],))]
                if state=='archived':return {'phase':'season_boundary','simulation_advanced':False,'season_status':auto.career.season_boundary()}
                operations=[{'kind':'archive_season','args':{'season':info['season'],'required_competitions':comps}}]
            else:operations=[{'kind':'advance','args':{'max_groups':1}}]
            manifest=measure('season_prepare',season_lineage.prepare,auto.career.registry,auto.career.key,request['request_id'],operations,delegated=True)
            op={'request_sha256':digest(request),'head_before':request['expected_checkpoint'],'kind':'registered_season',
                'manifest':manifest,'approval':lineage.signed(season_lineage.authorization(manifest),auto.career.key),'response':None}
            auto._save(path,op)
        manifest=op['manifest'];key=auto.career.key;reg=auto.career.registry
        measure('season_authorize',season_lineage.authorize,reg,key,manifest,op['approval'])
        directory=auto.directory/'season-successors'/request['request_id']
        with lineage.access(reg,key) as (c,t):
            row=c.execute('SELECT * FROM batches WHERE id=?',('season3:'+request['request_id'],)).fetchone()
            if row['state']=='accepted' and row['checkpoint']!=t['head']:raise ValueError('A later accepted season already exists')
        if row['state']!='accepted':measure('season_execute_and_verify',season_lineage.execute,reg,key,request['request_id'],directory)
        decision=season_lineage.acceptance_template(reg,key,directory)
        accepted=measure('season_accept',season_lineage.accept,reg,key,directory,decision,lineage.sign(key,decision))
        events=auto.career.play('next')['events'];fixture=auto.choose(events)
        op['response']={'phase':'pregame_ready' if events else 'season_boundary','simulation_advanced':True,
                        'accepted_checkpoint':accepted['checkpoint_sha256'],'next_events':events,
                        'prematch':auto.career.preview(fixture) if fixture and events[0]['kind']=='narration' else None}
        auto._save(path,op)
        return op['response']
