#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r243_p45sign.py —— P1-45 对照的**带符号**对比（含 O-2 的方向判据）。

## 预登记（`§140.3`，**原文**）
> **O-2** ★ 核心：因 `§138` 证明 F3 上 `Δed ≡ 0`（纯界面能驱动），
> **把 F3 变便宜应产生可测差别** ⇒ 预期 **P 臂 `f3_area` 更大**。
> **若无差别 ⇒ `§138` 的推论不成立**（重要的反证）。

**本脚本判**：
* **S-1** 处理确有影响（**已经由 `_r242` 证：41/95 列不同**）—— 这里复述效应量级。
* **S-2** ★ **方向**：末态（或当前末步）`f3_area(perstep) − f3_area(ladder)` 的**符号**。
* **S-3** 关键伴随量 `nf3` / `f3_pos_dx` / `blk_nprof` / `r_selfac` 的方向。
* ⚠ **必须打印读的是第几步**；未跑满 400 步时**不给终判**（硬规则③）。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
COLS = ('f3_area_m2', 'nf3', 'f3_pos_dx', 'f3_std_m', 'blk_nprof', 'r_selfac',
        'f1_area_m2', 'f2_area_m2', 'n_lath', 'Vt', 'dG_near_max')


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    A, B = rows('p45L'), rows('p45P')
    if A is None or B is None:
        print('⚠ 缺数据')
        return 2
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    last = common[-1]
    done = (int(A[-1]['step']) >= 400 and int(B[-1]['step']) >= 400)
    print('=' * 104)
    print('_r243 —— P1-45 对照的带符号对比')
    print('=' * 104)
    print('  末步 = **%s**；跑满 400 步？ **%s**' % (last, '是' if done else '否（中途）'))
    if not done:
        print('  ⚠ **未跑满 ⇒ 以下只是中途读数，不作终判**（硬规则③）。')
    print()
    print('  ## S-1/S-2 逐列带符号对比（共同步 %d 个）' % len(common))
    print('     %-16s %-14s %-14s %-13s %-11s %s'
          % ('列', 'ladder(末步)', 'perstep(末步)', '绝对差', '相对差', '方向'))
    for c in COLS:
        try:
            va = float(sa[last][c]); vb = float(sb[last][c])
        except (KeyError, TypeError, ValueError):
            print('     %-16s （列缺失或非数值）' % c)
            continue
        d = vb - va
        rel = d / va if va else float('nan')
        # 方向：perstep 更大/更小
        dirn = ('**perstep 更大**' if d > 0 else
                '**perstep 更小**' if d < 0 else '相同')
        print('     %-16s %-14.6g %-14.6g %-13.4e %-11s %s'
              % (c, va, vb, d, '%+.3e' % rel, dirn))
    print()
    print('  ## 逐 step 的 `f3_area` 对比（看方向是否一致，不是只看末步）')
    print('     %-6s %-13s %-13s %s' % ('step', 'ladder', 'perstep', 'Δ(perstep−ladder)'))
    for s in common:
        try:
            va = float(sa[s]['f3_area_m2']); vb = float(sb[s]['f3_area_m2'])
        except (KeyError, TypeError, ValueError):
            continue
        print('     %-6s %-13.6f %-13.6f %+.4e  %s'
              % (s, va * 1e12, vb * 1e12, (vb - va) * 1e12,
                 'perstep 大' if vb > va else ('perstep 小' if vb < va else '相同')))
    print()
    print('=' * 104)
    print('  ## 判定')
    print('=' * 104)
    try:
        va = float(sa[last]['f3_area_m2']); vb = float(sb[last]['f3_area_m2'])
        print('     **O-2 方向**：末步 `f3_area` ladder=%.6f µm² vs perstep=%.6f µm²'
              % (va * 1e12, vb * 1e12))
        if vb > va:
            print('     ⇒ ✅ **与预登记一致**（perstep/更便宜的 F3 ⇒ `f3_area` 更大）')
        elif vb < va:
            print('     ⇒ ⚠ **与预登记相反**（perstep 的 `f3_area` 更小）—— 如实记录')
        else:
            print('     ⇒ ⚠ 末步恰好相同 ⇒ 看上面的逐 step 方向')
    except (KeyError, TypeError, ValueError):
        pass
    if not done:
        print('     ⚠ **仍不作终判** —— 等两臂都到 400 步。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
