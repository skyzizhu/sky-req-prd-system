#!/usr/bin/env python3
"""Compile a V2 project for local file or HTTP reading."""
import pathlib
import sys
from projectlib import compile_project

if __name__ == '__main__':
    try:
        for warning in compile_project(pathlib.Path(__file__).resolve().parent):
            print('警告：', warning)
        print('已构建项目固定入口 site/index.html')
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
