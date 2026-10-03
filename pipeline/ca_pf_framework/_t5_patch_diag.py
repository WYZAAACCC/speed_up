#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_diag.py --- 给 `_t5_short.py` 加 `--diag-terms` 透传（**默认不传 ⇒ 逐字不变**）

## 为什么
`--diag-terms`（`_bk_exp.py:1226` / `:2406`，实现在 `windowB_surface.py:4372` 起的
**R208 块**）会**逐胞直测速度律的三项量级**：
* `|df_k − df_l|`（化学）· `|ed_k − ed_l|`（弹性）· `|stk·κ|`（曲率）
并**把含母相的 F1 界面单列**（正是"孤立种子"的界面）。
**⇒ 这正是判"是弹性项还是曲率项把 dG 推负"的唯一直接量具。**

## 改法（**最小**）
在启动器的 argv 列表末尾追加：`(['--diag-terms'] if a.diag_terms else [])`
⇒ **默认（False）⇒ 一个参数都不传 ⇒ 与归档逐字相同** ✓
"""
import hashlib
import os
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_diag'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…' % hashlib.sha256(src.encode()).hexdigest()[:16])

# ① 在 `--nuc-overlap-nm` 之后（已有的 `] +` 链起点）插入一个透传项
OLD = """             '--nuc-overlap-nm', repr(float(a.overlap_nm))] +"""
NEW = """             '--nuc-overlap-nm', repr(float(a.overlap_nm))] + \\
            # ★★★★★ s267：**`--diag-terms` 透传**（R208 三项分离诊断，**默认不传**）。
            #   为什么要它：判"孤立种子为何溶解"必须**直接测**速度律三项
            #     `|df_k−df_l|`（化学）· `|ed_k−ed_l|`（弹性）· `|stk·κ|`（曲率）,
            #   且引擎把**含母相的 F1 界面单列**（正是孤立种子的界面）。
            #   ⚠ 纯记账：只读、只统计，**不参与任何分支/数值**
            #     ⇒ `--diag-terms` 关时（**默认**）逐位不变 ✓
            (['--diag-terms'] if bool(getattr(a, 'diag_terms', False)) else []) + \\"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# ② 加 argparse 选项（插在 `--no-nucleation` 之后）
ANCH = "ap.add_argument('--no-nucleation'"
if ANCH not in out:
    print('  ❌ 找不到 `--no-nucleation` 锚点 ⇒ 拒绝修改'); sys.exit(1)
i = out.index(ANCH)
depth = 0; j = i
while j < len(out):
    if out[j] == '(':
        depth += 1
    elif out[j] == ')':
        depth -= 1
        if depth == 0:
            break
    j += 1
ADD = ("\n    ap.add_argument('--diag-terms', action='store_true',\n"
       "                    help='★ s267：透传 `--diag-terms`（R208 三项分离诊断）；'\n"
       "                         '默认 False ⇒ 归档逐字不变')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
if '--diag-terms' not in out:
    print('  ❌ 选项没插进去'); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  改后 sha256 = %s… ⇒ 已写盘' % hashlib.sha256(out.encode()).hexdigest()[:16])
