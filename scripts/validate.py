#!/usr/bin/env python3
"""Check project structure, build freshness and current-version delivery coverage."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))
from projectlib import validate, check_build
from audit_quality import project_report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--structure-only',action='store_true',help='草稿阶段仅检查结构与编译一致性，不代表交付完整')
    args=parser.parse_args()
    try:
        root=args.project.resolve();errors,warnings=validate(root)
        errors+=check_build(root)
        for message in warnings:print('警告：',message)
        if not args.structure_only and not errors:
            report=project_report(root)
            for item in report['issues']:
                message=item['path']+'：'+item['message']
                if item['severity']=='error':errors.append(message)
                else:print('待决策：' if item['severity']=='decision' else '警告：',message)
            print('交付检查：',report['status'])
        for message in errors:print('错误：',message)
        sys.exit(1 if errors else 0)
    except (ValueError,KeyError,OSError,TypeError) as error:
        print('验证失败：',error,file=sys.stderr);sys.exit(1)
