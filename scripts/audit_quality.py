#!/usr/bin/env python3
"""Read-only coverage and applicability audit for the selected delivery version."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))
from projectlib import read, safe
from qualitylib import evaluate, markdown


def audit(spec, version_dir=None):
    return evaluate(spec, Path(version_dir)/'content' if version_dir is not None else None)


def project_report(root, version=None):
    project=read(root/'project.json')
    vid=version or project['current_version']
    if vid not in [v['id'] for v in project['versions']]:raise ValueError('版本不存在')
    directory=safe(root,f'versions/{vid}')
    report=audit(read(directory/'content/spec.json'),directory)
    report.update(project=project['id'],version=vid)
    return report


def save_report(report, prefix):
    """Write both projections of one evaluated report."""
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(prefix)+'.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    Path(str(prefix)+'.md').write_text(markdown(report), encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--version')
    parser.add_argument('--strict',action='store_true',help='缺项或明确阻塞事项返回非零；非阻塞待决策单独列出')
    parser.add_argument('--report',type=Path,help='保存 JSON 与 Markdown 报告的文件前缀')
    args=parser.parse_args()
    try:
        report=project_report(args.project.resolve(),args.version)
        if args.report:
            save_report(report, args.report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return int(args.strict and report['counts']['errors']>0)
    except (ValueError,OSError,KeyError,TypeError) as error:
        print('检查失败：'+str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
