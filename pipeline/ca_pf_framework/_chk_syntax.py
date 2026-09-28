#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_syntax.py --- 语法自检（避免 PowerShell 引号地狱）。"""
import ast
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
files = ('windowB_surface.py', 'T24_verify_grouping.py', 'T21_beta_calib.py',
         'T26_verify_normsmooth.py', 'T27_verify_nucleation.py',
         '_probe_LT.py', '_proto_nucleate.py', '_chk_fixes.py',
         '_chk_geomAR.py', '_chk_sepconv.py',
         # ★ 2026-09-28 Round 137 追加：本轮新建/改动的脚本必须一并自检，
         #   否则"我改过的东西"恰好落在守卫之外（AGENTS §3.4：守卫必须覆盖被守卫的对象）。
         '_probe_shape.py', '_probe_d6_variants.py', '_probe_iface_types.py',
         '_chk_advgrad.py', 'T16_verify_rve.py', '_audit_faces2.py')
bad = []
for f in files:
    try:
        ast.parse(open(f, encoding='utf-8').read())
        print('OK   %s' % f)
    except SyntaxError as e:
        bad.append((f, e))
        print('FAIL %s : %s' % (f, e))
# ★★ Round 88：**必须打印"n/N"并通过计数**。
#   起因（Round 87 实测事故）：我往已有的 docstring 前插了一段说明文字，两个字符串字面量
#   贴在一起 ⇒ `SyntaxError: invalid character '。'` ⇒ 整个 `windowB_surface.py` 无法 import。
#   当时工具**确实报了 FAIL**，但我是用 `grep -c OK` 看输出的 ⇒ 只看到 "6"，
#   差点把 6/7 当成通过。⇒ 现在把计数行做成**唯一判决句**，并且**缺一即非零退出**。
print('=== 语法自检 %d/%d OK ===' % (len(files) - len(bad), len(files)))
if bad:
    print('⛔ 有文件语法错 ⇒ 这些文件**根本无法 import**，任何依赖它的运行都会失败：%s'
          % [f for f, _ in bad])
sys.exit(1 if bad else 0)
