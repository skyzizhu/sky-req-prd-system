#!/usr/bin/env python3
"""Evaluate isolated skill-produced candidates against fixed product scenarios. Does not generate candidates."""
import argparse
import json
from pathlib import Path
import sys
from review_delivery import review, save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidates',type=Path,help='JSON: scenario ID -> {project, evidence?}')
    parser.add_argument('--suite',type=Path,default=Path(__file__).resolve().parents[1]/'tests/scenarios/delivery.json')
    parser.add_argument('--report-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        suite=json.loads(args.suite.read_text(encoding='utf-8'))
        candidates=json.loads(args.candidates.read_text(encoding='utf-8'))
        scenarios={s['id']:s for s in suite['scenarios']}
        if set(candidates)-scenarios.keys(): raise ValueError('未知评测场景')
        args.report_dir.mkdir(parents=True,exist_ok=True)
        summary=[]
        for key, scenario in scenarios.items():
            if key not in candidates:
                summary.append(dict(scenario=key,status='not_run'));continue
            candidate=candidates[key];root=Path(candidate['project']).resolve()
            if args.report_dir.resolve().is_relative_to(root): raise ValueError('评测报告应放在候选项目外，保持候选只读')
            evidence=json.loads(Path(candidate['evidence']).read_text(encoding='utf-8')) if candidate.get('evidence') else None
            report=review(root,inputs=[args.suite.resolve()],evidence=evidence,rubric=scenario)
            save(report,args.report_dir/key)
            summary.append(dict(scenario=key,status=report['status'],fingerprint=report['fingerprint']))
        (args.report_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        return 1 if any(r['status']=='issues_found' for r in summary) else 3 if any(r['status']!='review_recorded' for r in summary) else 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('评测失败：'+str(error),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
