#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_p0cmp2.py --- 第 8 条决定性一步（**v2：按 `step` 取帧，不按文件名**）

## v1 的错（§13.2 已登记）
我用 `sorted(glob(...))[-1]` 当"最新帧" ⇒ 取到 `ckpt_B.npz` 的 `step=20`，且 `P0=nan`
⇒ 对比无意义。**这正是本仓库教训 25（文件枚举顺序不可依赖）**。

## v2 的判据（**预先写死**）
1. 先按 **`step` 字段**取最大帧（**若两臂最大 step 不同，只比共同 step**）；
2. 读各自的 **`f3_pos_p0_m`**；
3. 读 `series.csv` 在**该 step** 的 `f3_pos_dx`；
4. **判读**：
   * `P0` **相同**（差 < 1e-15）⇒ `f3_pos_dx` 的差异来自 `pm` ⇒ **真实分叉**；
   * `P0` **不同** ⇒ 该列**不可比**（但**不等于**没分叉 —— 还要看别的物理量）；
   * 任一 `P0` 为 **nan** ⇒ **无法判读**（并说明为什么）。
"""
import csv
import glob
import os

import numpy as np


def frames(d):
    """返回 [(step, path)]，**按 `step` 字段**排序（不按文件名）。"""
    out = []
    for f in glob.glob(os.path.join(d, '*.npz')):
        try:
            with np.load(f, allow_pickle=False) as z:
                st = int(np.asarray(z['step']).ravel()[0])
                p0 = (float(np.asarray(z['f3_pos_p0_m']).ravel()[0])
                      if 'f3_pos_p0_m' in z.files else None)
                dx = None
                if 'L' in z.files and 'N' in z.files:
                    dx = float(np.asarray(z['L']).ravel()[0]) / int(np.asarray(z['N']).ravel()[0])
            out.append((st, os.path.basename(f), p0, dx))
        except Exception as e:
            out.append((-1, os.path.basename(f) + ' (%s)' % type(e).__name__, None, None))
    return sorted(out)


def dxcol(tag, step):
    p = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(p):
        return None
    for x in csv.DictReader(open(p, encoding='utf-8', errors='replace')):
        if x['step'] == str(step):
            return (x.get('f3_pos_dx') or '').strip()
    return None


A = frames('_exp/_bk_t5/dry_ck8A/ckpt')
B = frames('_exp/_bk_t5/dry_ck8B/ckpt')
print('=' * 96)
print('第 8 条 v2：**按 step 取帧**对比 `f3_pos_p0_m`')
print('=' * 96)
for nm, F in (('A（续跑）', A), ('B（一次跑完）', B)):
    print('  ── %s：%d 帧 ──' % (nm, len(F)))
    for st, fn, p0, dx in F:
        s = ('%.10g m（%.4f Δx）' % (p0, p0 / dx)) if (p0 is not None and dx) else 'nan/无'
        print('     step=%-4d %-16s P0 = %s' % (st, fn, s))
print()
sa = max([f[0] for f in A]) if A else None
sb = max([f[0] for f in B]) if B else None
common = sorted(set(f[0] for f in A) & set(f[0] for f in B))
print('  A 最大 step = %s；B 最大 step = %s；**共同 step = %s**' % (sa, sb, common))
if not common:
    print('  ❌ 没有共同 step ⇒ **无法对比**（本轮判据不成立）')
else:
    st = common[-1]
    pa = next((f[2] for f in A if f[0] == st), None)
    pb = next((f[2] for f in B if f[0] == st), None)
    dxa = next((f[3] for f in A if f[0] == st), None)
    print()
    print('  ── 共同 step = %d ──' % st)
    print('     A 的 P0 = %s' % (('%.10g m' % pa) if pa is not None else 'nan'))
    print('     B 的 P0 = %s' % (('%.10g m' % pb) if pb is not None else 'nan'))
    print('     series 的 f3_pos_dx：A = %s   B = %s' % (dxcol('ck8A', st), dxcol('ck8B', st)))
    print()
    print('  ── 判读（判据预先写死）──')
    if pa is None or pb is None or (isinstance(pa, float) and np.isnan(pa)) \
            or (isinstance(pb, float) and np.isnan(pb)):
        print('     ❌ **任一 P0 为 nan ⇒ 无法判读**')
        print('        （可能原因：该 step 尚无 F3 面；或 P0 在更晚才被设定）')
        print('        ⇒ 应改取**两臂都有非 nan P0 的最晚共同 step**（下一步）')
    elif abs(pa - pb) < 1e-15:
        print('     **P0 完全相同** ⇒ `f3_pos_dx` 的差异**不是**基准造成的')
        print('        ⇒ **是真实分叉** ❌（须查 `lpbf` 档下哪一步不可恢复）')
    else:
        print('     **P0 不同**（Δ = %.6e m = %.6f Δx）'
              % (pa - pb, (pa - pb) / dxa if dxa else float('nan')))
        print('        ⇒ `f3_pos_dx` 列**不可比**；')
        print('        ⇒ **但仍须**用**不含基准的物理量**判是否分叉（下一步）')
print('=' * 96)
