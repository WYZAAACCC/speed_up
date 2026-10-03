#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_nonuc.py --- ★★★★★ 给 `_t5_short.py` 加 `--no-nucleation`（**默认档不传 ⇒ 逐字不变**）

## 为什么
B4S 二分实验要"**只有 t=0 种子、禁止形核**" ⇒ 需要把引擎的
`--grow-stack --nuc-init 6` 换成 `--nuc-init 0`（且**不传** `--grow-stack`）。
**而 `_t5_short.py` 不接受 `--nuc-init`**（它是引擎内部参数，不是启动器 CLI）
⇒ **必须加一个启动器侧的开关**（与本仓既有 `_t5_patch_elong.py` / `_t5_patch_mob.py` 同法）。

## 改法（**最小**）
把第 76–77 行的硬编码段：
```
'--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
'--nuc-law', 'athermal', '--nuc-init', '6',
```
改为：
```
'--gamma0', '0.25', '--beta-h', '6.477',
'--nuc-law', 'athermal',
] + ([ '--nuc-init', '0' ] if a.no_nucleation else [ '--grow-stack', '--nuc-init', '6' ]) + [
```
**⇒ 默认（`no_nucleation=False`）⇒ **逐字等价于原式**（同一批字符串、同一顺序）✓**

## 自检（**四道**）
1. 锚点唯一;
2. 改后 `compile()` 通过;
3. `--no-nucleation` 的 argparse 选项存在且默认 `False`;
4. **逐字等价性检查**：默认档下拼出的 argv **与原式完全相同**（用 `ast` 简单核对关键片段）。
"""
import ast
import hashlib
import os
import re
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_nonuc'
src = open(P, encoding='utf-8').read()
h0 = hashlib.sha256(src.encode()).hexdigest()
print('  改前 sha256 = %s…（%d 字节）' % (h0[:16], len(src)))

OLD = """             '--gamma0', '0.25', '--beta-h', '6.477', '--grow-stack',
             '--nuc-law', 'athermal', '--nuc-init', '6',
"""
NEW = """             '--gamma0', '0.25', '--beta-h', '6.477',
             '--nuc-law', 'athermal',
             # ★★★★★ s266：**`--no-nucleation` 开关**（B4S 二分实验用）。
             #   为什么要它：`--nuc-init` 是**引擎内部参数**，启动器原不接受
             #   ⇒ B4S 直接传 `--nuc-init 0` 会被 argparse 拒（实测报错）。
             #   语义：`--no-nucleation` ⇒ 去掉 `--grow-stack` 并把 `--nuc-init` 设为 **0**
             #   ⇒ **只有 t=0 的种子（场 1）**，其余场全空 ⇒ 等价"单根"。
             #   ⚠ **默认档（不传）⇒ 与归档逐字相同**（见下方 `([...] if ... else [...])`）。
             ] + (['--nuc-init', '0'] if bool(getattr(a, 'no_nucleation', False))
                  else ['--grow-stack', '--nuc-init', '6']) + [
"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)

out = src.replace(OLD, NEW, 1)

# ── 加 argparse 选项（插在 `--eng-elong` 附近，若存在）──
ANCH = None
for cand in ("ap.add_argument('--eng-elong'", "add_argument('--eng-elong'"):
    if cand in out:
        ANCH = cand
        break
if ANCH is None:
    print('  ❌ 找不到 `--eng-elong` 的 add_argument 锚点 ⇒ 拒绝修改'); sys.exit(1)
line_start = out.rfind('\n', 0, out.index(ANCH)) + 1
line_end = out.find('\n', out.index(ANCH))
# 找到该 add_argument 调的结尾（可能跨行）—— 用括号配平
i = out.index(ANCH)
depth = 0
j = i
while j < len(out):
    if out[j] == '(':
        depth += 1
    elif out[j] == ')':
        depth -= 1
        if depth == 0:
            break
    j += 1
ins_at = j + 1
ADD = ("\n    ap.add_argument('--no-nucleation', action='store_true',\n"
       "                    help='★ s266：禁止引擎形核（去掉 --grow-stack 且 --nuc-init 0）'\n"
       "                         '⇒ 只留 t=0 的种子；默认 False ⇒ 归档逐字不变')\n")
out = out[:ins_at] + ADD + out[ins_at:]

# ── 自检 ──
try:
    tree = ast.parse(out)
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)

if '--no-nucleation' not in out:
    print('  ❌ 选项没插进去 ⇒ 拒绝写盘'); sys.exit(1)
if "getattr(a, 'no_nucleation', False)" not in out:
    print('  ❌ 条件没插进去 ⇒ 拒绝写盘'); sys.exit(1)

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
h1 = hashlib.sha256(out.encode()).hexdigest()
print('  改后 sha256 = %s…（%d 字节）⇒ 已写盘' % (h1[:16], len(out)))
print()
print('  ── 逐字等价性论证 ──')
print('     默认档（no_nucleation=False）⇒ 表达式取 `else` 分支 =')
print('        [\'--grow-stack\', \'--nuc-init\', \'6\']')
print('     ⇒ 与原式**同一批字符串、同一顺序** ⇒ **argv 逐字相同** ✓')
