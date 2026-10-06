#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_lath_traj.py <tag> [field ...] —— 逐场**伸化轨迹**（基无关回转张量口径）。

## 为什么跟踪"新生的板条"而不是只看场 1
场 1（`t=0` 的种子）在 `β_h = 0` 下会迅速分枝碎裂（实测 `nc` 到 17），
其"形状比值"失去意义。而**每根新核**（引擎的 attach 事件产物）从它出生的那一步起
可以**单独跟踪** ⇒ 给出"**一根板条随时间的伸化**"这个更干净的对象。

判据与纪律（`R628`）：
  · 用**回转张量**等效半轴 `R_i = √(5λ_i)`（**基无关**，避开 `a·n ≠ 0` 的投影污染）；
  · 报 `nc`（该场自己的连通分量数）、`ncell`、以及沿 `n̂` 的真实厚度；
  · `2·R1 > 0.6×盒` ⇒ 标 `WRAP` 并排除。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = sys.argv[1]
fields = [int(x) for x in sys.argv[2:]] or [1]
sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz")))
print("=" * 104)
print("【%s】逐场伸化轨迹（基无关 R_i = √(5λ_i)）  快照 %d 个" % (tag, len(sns)))
print("=" * 104)
for fd in fields:
    print("\n  ◆ 场 %d" % fd)
    print("    %-7s %-8s %-5s %-9s %-9s %-9s %-8s %-8s %-10s %s"
          % ('step', 'ncell', 'nc', 'R1(nm)', 'R2', 'R3', 'R1/R2', 'R1/R3',
             '厚_n̂(nm)', '备注'))
    traj = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        m = (reg == fd)
        if m.sum() < 8:
            continue
        nc, _ = ncomp(m)
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        wrap = 2.0 * met['R1'] > 0.6 * L
        print("    %-7d %-8d %-5d %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %-10.0f %s"
              % (st, int(m.sum()), nc, met['R1'] * 1e9, met['R2'] * 1e9,
                 met['R3'] * 1e9, met['elong_lw'], met['elong_lt'],
                 met['thick_nm'], 'WRAP(排除)' if wrap else ''))
        if not wrap:
            traj.append((st, met['elong_lt'], nc))
    # ★★ 主口径（对"碎裂"稳健）：**逐分量算 R1/R3，取分量中位**
    #   为什么必须这样：实测 `nc` 在快照之间从不是 1（1→4→17、1→25）⇒
    #   若只取"整场单连通"的读数，几乎每个场只有 1 个点 ⇒ **趋势判不了**（`P26`）。
    #   而"**每个碎块自己的**形状比值"是有意义的（每块都是母相中的一块析出物）
    #   ⇒ 取**分量中位**既稳健、又保留"是否有伸化"这个信息。
    comp = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        m = (reg == fd)
        if m.sum() < 8:
            continue
        nc, lab = ncomp(m)
        if lab is None:
            continue
        vals = []
        szs = np.bincount(lab.ravel())
        for cid in range(1, len(szs)):
            if szs[cid] < 20:                 # 太小的块（<20 胞）不算
                continue
            ib = np.argwhere(lab == cid).astype(np.float64) * DX
            mm = shape_metrics(ib, a, w, nh)
            if 2.0 * mm['R1'] > 0.6 * L:      # 自贯通 ⇒ 排除
                continue
            vals.append((mm['elong_lt'], mm['elong_lw'], mm['thick_nm']))
        if vals:
            lt = float(np.median([v[0] for v in vals]))
            lw = float(np.median([v[1] for v in vals]))
            tk = float(np.median([v[2] for v in vals]))
            comp.append((st, lt, lw, tk, len(vals)))
    if len(comp) >= 2:
        print("    ⇒ **分量中位口径**（≥20 胞的分量，%d 个快照）：" % len(comp))
        print("       %-7s %-10s %-10s %-11s %s"
              % ('step', 'R1/R3中位', 'R1/R2中位', '厚中位(nm)', '分量数'))
        for st, lt, lw, tk, n in comp:
            print("       %-7d %-10.2f %-10.2f %-11.0f %d" % (st, lt, lw, tk, n))
        d = comp[-1][1] - comp[0][1]
        print("    ⇒ R1/R3 中位：**%.2f → %.2f（%+.2f）** ⇒ 伸化**%s**"
              % (comp[0][1], comp[-1][1], d,
                 "在发生" if d > 0.2 else "**未发生/停滞**" if abs(d) <= 0.2 else "在减弱"))
    elif comp:
        print("    ⇒ 分量中位只有 1 个快照 ⇒ 无法判趋势")
    else:
        print("    ⇒ **无有效分量** ⇒ 无法判定")

    ok = [(s, v) for s, v, n in traj if n == 1]
    if len(ok) >= 2:
        print("    ⇒ （附）**整场单连通读数**：step %d → %d ，R1/R3 **%.2f → %.2f**"
              % (ok[0][0], ok[-1][0], ok[0][1], ok[-1][1]))
    else:
        print("    ⇒ （附）整场单连通读数不足 2 个 ⇒ 该口径无法判趋势")
