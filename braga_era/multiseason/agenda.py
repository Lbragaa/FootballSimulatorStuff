"""Disconnected chronological orchestration; ordinary production bridge unchanged."""
import json
from uuid import uuid5,NAMESPACE_URL,UUID
from ..db import connect_read_only
from .store import authenticated,run
from .market import next_obligation


def next_event(directory,key):
    directory,_=authenticated(directory,key)
    with connect_read_only(directory/'database.sqlite') as c:
        return event_from_connection(c)


def event_from_connection(c):
    fixture=c.execute("SELECT kickoff,status FROM ms_fixtures WHERE status!='final' ORDER BY kickoff,key LIMIT 1").fetchone()
    obligation=next_obligation(c)
    ordinary=obligation if obligation and (not fixture or obligation['kickoff']<=fixture['kickoff']) else {'kind':'match_group','kickoff':fixture['kickoff'],'status':fixture['status']} if fixture else None
    from .calendar import event
    administrative=event(c)
    if administrative and (not ordinary or administrative['kickoff']<=ordinary['kickoff']):return administrative
    return ordinary


def completed_groups(c,request_id):
    return sum(row['request_id']==str(uuid5(NAMESPACE_URL,f'{request_id}:match_group:{json.loads(row["args_json"])["kickoff"]}:play_group'))
               for row in c.execute("SELECT request_id,args_json FROM ms_operations WHERE kind='play_group'"))


def advance(directory,key,*,request_id,max_groups=10):
    """Stable child UUIDs, same committed inputs after every interruption.

    New draws/stages are explicit operations; this coordinator stops at that real
    dependency instead of selecting an undisclosed bracket/calendar policy.
    """
    if str(UUID(request_id))!=request_id or type(max_groups) is not int or not 1<=max_groups<=100:raise ValueError('Bounded development groups required')
    directory,_=authenticated(directory,key)
    # Re-enter the signed begin receipt even on retries; the mutable run locator
    # is never authority to change the committed limit or forge a final reply.
    run(directory,key,str(uuid5(NAMESPACE_URL,request_id+':begin_run')),'begin_run',{'id':request_id,'max_groups':max_groups})
    with connect_read_only(directory/'database.sqlite') as c:
        row=c.execute('SELECT * FROM ms_runs WHERE id=?',(request_id,)).fetchone()
        if row and row['max_groups']!=max_groups:raise ValueError('Changed run parameters')
        if row and row['response_json'] is not None:
            return run(directory,key,str(uuid5(NAMESPACE_URL,request_id+':finish_run')),'finish_run',{'id':request_id})
    with connect_read_only(directory/'database.sqlite') as c:completed=completed_groups(c,request_id)
    while completed<max_groups:
        event=next_event(directory,key)
        if not event:break
        stem=f'{request_id}:{event["kind"]}:{event["kickoff"]}'
        if event['kind']=='loan_return':stem+=':'+event['loan']
        if event['kind']=='competition_stage':stem+=':'+event['edition']+':'+event['action']
        def execute(kind,args):return run(directory,key,str(uuid5(NAMESPACE_URL,stem+':'+kind)),kind,args)
        if event['kind']=='payroll':execute('pay_month',{'period':event['period']})
        elif event['kind']=='loan_return':execute('return_loan',{'loan':event['loan'],'dated':event['dated']})
        elif event['kind']=='proposed_income':execute('receive_income',{'income':event['income']})
        elif event['kind']=='economic_due':execute('settle_economics',{'dated':event['kickoff']})
        elif event['kind']=='competition_stage':execute(event['action'],event['args'])
        elif event['kind']=='calendar_blocker':raise ValueError(event['reason'])
        else:
            if event['status']=='scheduled':execute('claim_group',{'kickoff':event['kickoff']})
            execute('play_group',{'kickoff':event['kickoff']});completed+=1
    return run(directory,key,str(uuid5(NAMESPACE_URL,request_id+':finish_run')),'finish_run',{'id':request_id})
