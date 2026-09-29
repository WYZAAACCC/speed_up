#!/usr/bin/env python3
"""_r31_syntax.py —— 只做语法检查（避免 PowerShell 内联 Python 的引号地狱）。"""
import ast
import sys
for f in sys.argv[1:]:
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print('AST OK   %s' % f)
    except SyntaxError as e:
        print('SYNTAX ERR %s: line %s: %s' % (f, e.lineno, e.msg))
        sys.exit(1)
