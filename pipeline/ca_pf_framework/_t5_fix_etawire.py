#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fix_etawire.py --- 修 `_t5_patch_etawire.py` 的**校验串**（少写了 ` or 1.0)`）后重跑

## 上一版失败原因（已记账）
我把校验串写成 `"g.ed_eta = float(getattr(a, 'ed_eta', 1.0))"`，
而实际写入的是 `"g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)"`
⇒ **校验失败 ⇒ 拒绝写盘** ⇒ `_bk_exp.py` **未被改动** ✓（**自检起作用了**）
"""
import os
import re
import subprocess
import sys

P = '_t5_patch_etawire.py'
src = open(P, encoding='utf-8').read()
OLD = '''for need in ("g.ed_eta = float(getattr(a, 'ed_eta', 1.0))", "'--ed-eta', type=float"):'''
NEW = '''for need in ("g.ed_eta = float(getattr(a, 'ed_eta', 1.0) or 1.0)", "'--ed-eta', type=float"):'''
n = src.count(OLD)
print('  校验串锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
open(P, 'w', encoding='utf-8').write(src.replace(OLD, NEW, 1))
print('  ✅ 已修正校验串')
print()
print('  ── 重跑 patcher ──')
r = subprocess.run([sys.executable, P], capture_output=True, text=True)
print(r.stdout[-1200:] if r.stdout else '')
if r.stderr:
    print('  [stderr]', r.stderr[-400:])
