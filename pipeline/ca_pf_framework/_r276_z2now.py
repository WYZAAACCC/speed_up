#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r276_z2now.py —— ★★ **P0 判决 Z-2 的提前读数**（两组都有到 step 120 的数据）。

## 两组（几何逐字相同、γ_F3 对比同为 1.815×，**只差 `--facet-proj`**）
* **投影组**：`p45L` vs `p45P`（`--facet-proj 10`）—— 已有到 step 340
* **无投影组**：`p45L0` vs `p45P0`（`--facet-proj 0`）—— 已有到 step 120

## 预登记判据（`_r253` 头部已写死）
* **Z-2** ★ 核心：关掉投影后，**分叉列数与幅度都应显著大于**投影组。
  ⇒ 在**共同步（≤120）**上比，公平。
* **Z-3** 记录 `f3_area`/`nf3`/`Vt`/`r_selfac` 的**末态符号方向**。

⚠ **记账**：两组目前**步数不同**（340 vs 120）⇒ **只在共同步上比**，不比末态。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}
KEY = ('f3_area_m2', 'nf3', 'Vt', 'n_lath', 'f1_area_m2', 'f2_area_m2',
       'r_selfac', 'f3_pos_dx', 'dG_near_max', 'blk_nprof')


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def study(A, B, upto=None):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    if upto is not None:
        common = [s for s in common if int(s) <= upto]
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    per_step = {}
    colmax = {c: 0.0 for c in cols}
    for s in common:
        nd = 0
        worst = 0.0
        for c in cols:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                if (sa[s].get(c) or '') != (sb[s].get(c) or ''):
                    nd += 1
                continue
            if fa != fa and fb != fb:
                continue
            if repr(fa) == repr(fb):
                continue
            d = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
            nd += 1
            worst = max(worst, d)
            colmax[c] = max(colmax[c], d)
        per_step[s] = (nd, worst)
    return common, cols, per_step, colmax, sa, sb


def main():
    print('=' * 108)
    print('_r276 —— **Z-2 提前读数**：投影 vs 无投影（同几何、同 γ 对比 1.815×）')
    print('=' * 108)
    L, P = rows('p45L'), rows('p45P')
    L0, P0 = rows('p45L0'), rows('p45P0')
    if not all((L, P, L0, P0)):
        print('  ⚠ 缺数据'); return 2
    print('  步数：投影组末步 %s；无投影组末步 %s'
          % (L[-1]['step'], L0[-1]['step']))
    U = min(int(L[-1]['step']), int(L0[-1]['step']))
    print('  ⇒ **只在共同步（≤ %d）上比**（公平；两组步数不同）' % U)
    print()
    c1, cols, ps1, cm1, sa1, sb1 = study(L, P, upto=U)
    c2, _, ps2, cm2, sa2, sb2 = study(L0, P0, upto=U)
    print('  ## 逐步：有差异的列数 / 最大相对差')
    print('     %-6s | %-24s | %s' % ('step', '投影组（p45L vs p45P）',
                                      '无投影组（p45L0 vs p45P0）'))
    for s in c1:
        a = ps1.get(s, (0, 0.0))
        b = ps2.get(s, (0, 0.0))
        print('     %-6s | %-24s | %s' % (s, '%3d 列  %.3e' % a,
                                          '%3d 列  %.3e' % b))
    print()
    n1 = max(v[0] for v in ps1.values())
    n2 = max(v[0] for v in ps2.values())
    w1 = max(v[1] for v in ps1.values())
    w2 = max(v[1] for v in ps2.values())
    print('  ## **Z-2 汇总**（共同步 ≤%d）' % U)
    print('     %-22s %-14s %-14s %s' % ('量', '投影组', '无投影组', '比值'))
    print('     %-22s %-14d %-14d %.2f×' % ('最多差异列数', n1, n2, n2 / max(n1, 1)))
    print('     %-22s %-14.3e %-14.3e %.2f×' % ('最大相对差', w1, w2, w2 / max(w1, 1e-30)))
    print()
    print('  ## **Z-3** 关键列的**最大**相对差（共同步内）')
    print('     %-16s %-14s %-14s %s' % ('列', '投影组', '无投影组', '比值'))
    for c in KEY:
        if c not in cm1:
            continue
        a, b = cm1[c], cm2.get(c, 0.0)
        r = (b / a) if a > 0 else float('inf')
        print('     %-16s %-14.3e %-14.3e %s'
              % (c, a, b, ('%.2f×' % r) if r != float('inf') else '∞（投影组为 0）'))
    print()
    print('=' * 108)
    if n2 > n1 and w2 > w1:
        print('  ⇒ ✅ **Z-2 方向成立**：关掉投影后，分叉**列数更多、幅度更大**')
        print('     ⇒ 支持 `§144`/`§147`："投影压制界面能对形态的影响"。')
    elif n2 == n1 and abs(w2 - w1) < 1e-30:
        print('  ⇒ ⚠ **两组完全相同** ⇒ 投影**不影响**该对照（需查为何 `_r248` 却测到差异）')
    else:
        print('  ⇒ ⚠ **方向不明确**（列数 %d vs %d；幅度 %.3e vs %.3e）⇒ 如实记录，不硬判'
              % (n1, n2, w1, w2))
    print()
    print('  ⚠ 记账：这是**中途读数**（≤step %d），**不是 400 步末态判决**。' % U)
    return 0


if __name__ == '__main__':
    sys.exit(main())
