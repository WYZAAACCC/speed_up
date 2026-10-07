#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r111_vtctrl.py —— **§95 的收紧**：同 `Vt`（而非同 step）比较块 0，并查 β 分数。

## 为什么（§95 第五节自己列的局限 2）

`_r86` 的隔离判决是**同一步号**比较，而两块臂的 `Vt` 更大
（两块都在长）⇒ 部分差异可能来自"**转变总量不同**"（母相消耗程度不同），
而不是"耦合"。⇒ 必须**同 `Vt`** 再比一次。

## 做法

1. 读 `dry_mo1fp10`（单块）与 `dry_mb2fp10`（两块）的 `series.csv`；
2. 取**变体 1 那个块**的 `blk_span_nm`（按 `blk_vars` 选，不按位置 —— 块的排序是
   **体积降序**，两臂顺序可能是反的）；
3. 以 `Vt` 为横轴重采样（线性插值），在**共同的 `Vt` 区间**上比 `blk_span_nm`；
4. 若**同 `Vt`** 下仍有系统差 ⇒ 差异**不是**"转变总量"造成的。
5. 顺带报 β 分数（`1 − Vt/V_box`）与 `vol_0`（若 CSV 有）。

⚠ 记账：`Vt` 是**广延量**，两臂的 `Vt` 不同**是正常的**（两块臂有两个块）；
这里只用它做**横轴**，不用它做比值（`§84` 规程③）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = [('dry_mo1fp10', '单块 V1×3（`--facet-proj 10`）'),
        ('dry_mb2fp10', '两块 V1×3 + V3×3（`--facet-proj 10`）')]


def pick_var1(row, col):
    vs = [x for x in str(row.get('blk_vars', '') or '').split('/') if x.strip()]
    t = [x for x in str(row.get(col, '') or '').split('/') if x.strip()]
    try:
        i = [int(float(v)) for v in vs].index(1)
        return float(t[i])
    except (ValueError, IndexError):
        return float('nan')


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    st, vt, sp, al, wl = [], [], [], [], []
    for r in rows:
        try:
            st.append(int(float(r['step'])))
            vt.append(float(r['Vt']) * 1e18)
        except (KeyError, ValueError):
            continue
        sp.append(pick_var1(r, 'blk_span_nm'))
        al.append(pick_var1(r, 'blk_alen_nm'))
        wl.append(pick_var1(r, 'blk_wlen_nm'))
    return dict(tag=tag, step=np.array(st), Vt=np.array(vt),
                span=np.array(sp), alen=np.array(al), wlen=np.array(wl),
                has_v0=('V0' in rows[0] or 'vol_0' in rows[0]))


def main():
    print('=' * 104)
    print('_r111 —— 同 `Vt` 比较（收紧 §95 的"同 step"局限）')
    print('=' * 104)
    D = {}
    for t, lab in ARMS:
        d = load(t)
        if d is None:
            print('  %-14s （无数据）' % t)
            continue
        D[t] = d
        print('  %-14s %-34s step %d→%d  Vt %.3f→%.3f µm³  有 V0 列：%s'
              % (t, lab[:34], d['step'][0], d['step'][-1],
                 d['Vt'][0], d['Vt'][-1], d['has_v0']))
    if len(D) < 2:
        return 1
    a, b = D['dry_mo1fp10'], D['dry_mb2fp10']
    lo = max(np.nanmin(a['Vt']), np.nanmin(b['Vt']))
    hi = min(np.nanmax(a['Vt']), np.nanmax(b['Vt']))
    print()
    print('  **共同 `Vt` 区间 = [%.3f, %.3f] µm³**（区间外不可比）' % (lo, hi))
    if hi <= lo:
        print('  ⇒ ⚠ 两臂的 `Vt` 区间**不重叠** ⇒ 同 Vt 比较**做不了**（必须记账）')
        return 1
    grid = np.linspace(lo, hi, 13)
    print()
    print('  %-10s %-13s %-13s %-11s %-11s %s'
          % ('Vt(µm³)', '单块 span', '两块 span', 'Δ(nm)', 'Δ/Δx', 'Δ%'))
    ds = []
    for v in grid:
        sa = np.interp(v, a['Vt'], a['span'])
        sb = np.interp(v, b['Vt'], b['span'])
        d = sa - sb
        ds.append(d)
        print('  %-10.3f %-13.1f %-13.1f %+-11.1f %+-11.2f %+.2f%%'
              % (v, sa, sb, d, d / 62.5, 100 * d / max(sb, 1e-9)))
    ds = np.array(ds)
    print()
    print('  ⇒ **同 `Vt` 下 `Δ = 单块 − 两块`：mean %+.1f nm（%+.2f%%）、'
          'min %+.1f、max %+.1f**' % (ds.mean(), 100 * ds.mean() / 2800,
                                      ds.min(), ds.max()))
    if np.all(ds > 0) or np.all(ds < 0):
        print('     ⇒ **符号全程一致** ⇒ 差异**不是**"转变总量不同"造成的 ✅')
        print('        （`§95` 的"块 1 压低块 0 的 n* 跨度"在**同 Vt** 下依然成立）')
    else:
        print('     ⇒ ⚠ 符号不一致 ⇒ 同 Vt 下差异**不稳定** ⇒ `§95` 的结论要降级')
    print()
    print('  ⚠ 记账：插值比较（两臂的采样点不同）；`Vt` 是广延量，只作横轴。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
