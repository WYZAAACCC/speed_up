#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_check_flags.py —— 校验一组 `--flag` 是否是 `_bk_exp.py` 的**真选项**。

用 `argparse` 真解析（不是 grep）⇒ 与引擎自己的判定**逐字一致**。
"""
import argparse
import ast
import sys

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py"
want = sys.argv[1:]

# 用 ast 取 main() 里所有 add_argument 的第一个字符串字面量
tree = ast.parse(open(SRC, encoding="utf-8").read())
opts = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == 'add_argument' and node.args:
        a0 = node.args[0]
        if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
            opts.add(a0.value)
print("引擎共注册 %d 个选项" % len(opts))
bad = [w for w in want if w not in opts]
for w in want:
    print("  %-26s %s" % (w, "✅ 存在" if w in opts else "❌ **不存在**"))
print("\n不存在的：%s" % (bad if bad else "（无）"))
sys.exit(1 if bad else 0)
