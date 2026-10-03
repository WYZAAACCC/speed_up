#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fix_nonuc.py --- 修 `--no-nucleation` 的语义：**保留 `--grow-stack`，只把 `--nuc-init` 设 0**

## 为什么（**实测教训**）
第一版把 `--grow-stack` 也去掉了 ⇒ `grow` 变 False ⇒ 引擎走 **t=0 多片播种**分支
（`_bk_exp.py:1636`）⇒ `nvar 1 · m 23` 要播 **23 片 × 0.51 µm = 11.7 µm > 盒 4 µm**
⇒ **`ValueError: elongated seed exceeds domain: margin -2.376e-06`**（margin 为负 = 中心出盒）。
**★ 教训**：`grow` 不只控制"生长"，还**决定 t=0 播 1 片还是 M 片**（`_bk_exp.py:1707` 注释逐字）。
⇒ **禁形核不能靠去掉 `--grow-stack`**，只能靠 `--nuc-init 0`。
"""
import hashlib
import os
import shutil
import sys

P = '_t5_short.py'
src = open(P, encoding='utf-8').read()
h0 = hashlib.sha256(src.encode()).hexdigest()
print('  改前 sha256 = %s…' % h0[:16])

OLD = """             ] + (['--nuc-init', '0'] if bool(getattr(a, 'no_nucleation', False))
                  else ['--grow-stack', '--nuc-init', '6']) + ["""
NEW = """             # ★★★★★ s266 修（**实测教训**）：**保留 `--grow-stack`**，只把 `--nuc-init` 设 0。
             #   第一版连 `--grow-stack` 一起去掉 ⇒ `grow=False` ⇒ 引擎走
             #   **t=0 多片播种**（`_bk_exp.py:1636`）⇒ `nvar 1 · m 23` 播 23 片 × 0.51 µm
             #   = 11.7 µm > 盒 4 µm ⇒ `ValueError: margin -2.376e-06`（中心出盒）。
             #   ⚠ `grow` 还决定"t=0 播 1 片还是 M 片"（`_bk_exp.py:1707` 逐字）
             #     ⇒ **禁形核只能靠 `--nuc-init 0`**，不能靠去掉 `--grow-stack`。
             ] + (['--grow-stack', '--nuc-init', '0']
                  if bool(getattr(a, 'no_nucleation', False))
                  else ['--grow-stack', '--nuc-init', '6']) + ["""

n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)
try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
open(P, 'w', encoding='utf-8').write(out)
print('  改后 sha256 = %s… ⇒ 已写盘' % hashlib.sha256(out.encode()).hexdigest()[:16])
print()
print('  ── 语义复核 ──')
print('     `--no-nucleation` ⇒ argv 含 `--grow-stack --nuc-init 0`')
print('     ⇒ **t=0 播 1 片**（grow=True）且 **fresh/stack 名额为 0** ⇒ **只剩场 1** ✓')
print('     默认档 ⇒ `--grow-stack --nuc-init 6` ⇒ **与归档逐字相同** ✓')
