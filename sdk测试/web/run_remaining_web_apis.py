"""依次验收剩余 Web API；每个 API 单独进程，默认三轮，场景不满足时跳过。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

__test__ = False
ROOT=Path(__file__).resolve().parents[1]


def main():
    contracts=json.loads((ROOT/'web'/'remaining_web_contracts_20261004.json').read_text(encoding='utf-8'))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api',action='append',choices=list(contracts['apis']))
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'web'/'evidence'/'artifacts')
    args=parser.parse_args()
    if args.rounds<1:parser.error('--rounds 必须大于 0')
    summary=[]
    for api in (args.api or list(contracts['apis'])):
        reports=[]
        for round_no in range(1,args.rounds+1):
            output=args.output_dir/(api.replace('.','_')+f'_20261004_run{round_no}.txt')
            script=ROOT/contracts['apis'][api]['script']
            # A failed invocation must never reuse an earlier successful report.
            output.unlink(missing_ok=True)
            process=subprocess.run([sys.executable,str(script),'--json','--report-file',str(output)],capture_output=True,text=True)
            if not output.exists():
                print(json.dumps({'api':api,'round':round_no,'error':process.stderr[-2000:]},ensure_ascii=True),flush=True)
                reports.append({'lifecycle':'READY_FOR_LIVE','exit_code':process.returncode,'results':[]})
                break
            report=json.loads(output.read_text(encoding='utf-8'))
            if report['exit_code'] != process.returncode:
                raise RuntimeError(f'{api}: report exit code differs from child process')
            reports.append(report)
            counts={s:sum(r['status']==s for r in report['results']) for s in ['PASS','FAIL','KNOWN']}
            print(json.dumps({'api':api,'round':round_no,'status':report['lifecycle'],'counts':counts,'exit_code':report['exit_code']},ensure_ascii=True),flush=True)
            if report['lifecycle']=='SKIPPED':break
        last=reports[-1]
        stable=all(r['lifecycle']==last['lifecycle'] for r in reports)
        summary.append({'api':api,'lifecycle':last['lifecycle'],'rounds':len(reports),'stable':stable,
                        'results':last['results'],'exit_code':last['exit_code']})
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'remaining_web_20261004_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 1 if any(s['exit_code'] for s in summary) else 0


if __name__=='__main__':raise SystemExit(main())
