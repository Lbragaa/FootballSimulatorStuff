"""Identical-input read-only payroll benchmark; never a production episode claim."""
import argparse
import calendar
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
import json
from pathlib import Path
import time
from braga_era.db import connect_read_only,file_sha256
from braga_era.history import digest
from braga_era.multiseason.market import payroll_detail


def per_contract_scan(c,period):
    """Prior query strategy with the SAME declared annulled-term exclusion."""
    year,month=map(int,period.split('-'));days=calendar.monthrange(year,month)[1];amounts={}
    for row in c.execute('SELECT * FROM ms_contracts ORDER BY id'):
        if row['status']=='annulled':continue
        start,end=date.fromisoformat(row['starts']),date.fromisoformat(row['ends'])
        loans=[dict(r) for r in c.execute('SELECT * FROM ms_loans WHERE player=? ORDER BY starts',(row['player'],))]
        for d in range(1,days+1):
            day=date(year,month,d)
            if not start<=day<=end:continue
            matching=[r for r in loans if r['starts']<=day.isoformat()<=r['ends']]
            if len(matching)>1:raise ValueError('Overlapping loan obligations')
            loan=matching[0] if matching else None
            shares=[(row['club'],10000)] if not loan else [(loan['owner'],10000-loan['wage_share_bps']),(loan['borrower'],loan['wage_share_bps'])]
            for payer,bps in shares:amounts[payer]=amounts.get(payer,Decimal(0))+Decimal(row['wage_cents'])*bps/10000/days
    return {k:int(v.quantize(Decimal('1'),rounding=ROUND_HALF_UP)) for k,v in sorted(amounts.items()) if v}


def run(db,output):
    source=file_sha256(db);results={};answers={}
    for name,function in (('prior_per_contract_queries',per_contract_scan),('batched_loan_query',payroll_detail)):
        with connect_read_only(db) as c:
            if c.execute('SELECT test_only FROM ms_meta').fetchone()[0]!=1:raise ValueError('Development-only benchmark')
            selects=[0]
            def count(sql):
                if sql.lstrip().upper().startswith('SELECT'):selects[0]+=1
            c.set_trace_callback(count);wall=time.perf_counter();cpu=time.process_time()
            answers[name]={period:function(c,period) for period in ('2028-01','2028-06','2028-12')}
            results[name]={'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu,'select_queries':selects[0]}
    if answers['prior_per_contract_queries']!=answers['batched_loan_query']:raise ValueError('Payroll cents changed')
    if file_sha256(db)!=source:raise ValueError('Read-only payroll benchmark changed source')
    report={'scope':'NONCANONICAL DEVELOPMENT TEST','timings':results,'identical_payroll_sha256':digest(answers['batched_loan_query']),'source_unchanged':True,'production_modified':False,'limitations':'One paired read-only payroll workload, not full episode or successor-lifecycle timing; both use identical annulled-contract rules.'}
    Path(output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.db,a.output),indent=2))
