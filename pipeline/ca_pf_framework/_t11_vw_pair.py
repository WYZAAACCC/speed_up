#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vw_pair.py <tagA> <tagB> —— **按生长量（Vt）配对**测 `v_a/v_w`（修正 `P8` 类问题）。

## 为什么必须配对
实测两臂在**同一 step** 的生长量可差 **4 倍**（`fW0` 的 `Vt` = 5.2e-19 vs `fW1` = 2.2e-18）
⇒ 同 step 比速度 = **把"阶段差"当成"机制差"**（`P8`：先对齐口径再比机器）。
⇒ 改为：**在相近 `Vt` 上比 `v_a/v_w`**。

## 怎么做
1. 从两臂 `series.csv` 读 `(step, Vt)`；
2. 对 A 的每个 step，在 B 里找 **`Vt` 最接近**的 step（配对）；
3. 对每个场，用**两臂各自的配对 step 区间**算 `v_a = ΔR1/Δstep`、`v_w = ΔR2/Δstep`；
4. 报两臂的 `v_a/v_w` 中位，以及配对的 `Vt` 误差。
"""
import csv
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
A, B = sys.argv[1], sys.argv[2]


def vt_of(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = float(r['Vt'])
            except (TypeError, ValueError):
                pass
    return d


def axes_of(tag, step):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        return (np.asarray(z['region']).astype(np.int32),
                np.asarray(z['a_ax'], float), np.asarray(z['w_ax'], float),
                np.asarray(z['n_hab'], float))


def radii(tag, step):
    """返回 {场: (R1,R2,R3)}，只用最大连通分量（`P22`）。"""
    t = axes_of(tag, step)
    if t is None:
        return None
    reg, a, w, nh = t
    out = {}
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        if m.sum() < 20:
            continue
        nc, lab = ncomp(m)
        if lab is not None and nc > 1:
            szs = np.bincount(lab.ravel()); szs[0] = 0
            m = (lab == int(np.argmax(szs)))
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        out[k] = (met['R1'], met['R2'], met['R3'])
    return out


va_, vb_ = vt_of(A), vt_of(B)
if not va_ or not vb_:
    sys.exit("缺 series.csv ⇒ 无法配对")
sa, sb = sorted(va_), sorted(vb_)
pairs = []
for s in sa:
    j = min(sb, key=lambda x: abs(vb_[x] - va_[s]))
    err = abs(vb_[j] - va_[s]) / max(va_[s], 1e-300)
    pairs.append((s, j, va_[s], vb_[j], err))
good = [p for p in pairs if p[4] < 0.35]
print("=" * 100)
print("按 Vt 配对：A=%s（%d 步）  B=%s（%d 步）  配成 %d 对（|ΔVt|/Vt < 35%%）"
      % (A, len(sa), B, len(sb), len(good)))
print("=" * 100)
print("  %-9s %-9s %-13s %-13s %s" % ('A.step', 'B.step', 'A.Vt', 'B.Vt', 'Vt 相对差'))
for s, j, v1, v2, e in pairs[:14]:
    mark = '✅' if e < 0.35 else '⚠'
    print("  %-9d %-9d %-13.4g %-13.4g %.1f%% %s" % (s, j, v1, v2, 100 * e, mark))

if len(good) < 2:
    sys.exit("\n⚠ 配成对不足 2 个 ⇒ B 臂还太短，等它跑久一点再配对")
s0, j0, _, _, _ = good[0]
s1, j1, _, _, _ = good[-1]
ra0, rb0 = radii(A, s0), radii(B, j0)
ra1, rb1 = radii(A, s1), radii(B, j1)
print("\n  ⇒ 用配对区间：A step %d→%d ；B step %d→%d" % (s0, s1, j0, j1))
res = {}
for nm, r0, r1, d0, d1 in ((A, ra0, ra1, s0, s1), (B, rb0, rb1, j0, j1)):
    if not r0 or not r1:
        continue
    ds = max(d1 - d0, 1)
    rat = []
    for k in sorted(set(r0) & set(r1)):
        va = (r1[k][0] - r0[k][0]) / ds
        vw = (r1[k][1] - r0[k][1]) / ds
        vt = (r1[k][2] - r0[k][2]) / ds
        if vw > 0:
            rat.append((va / vw, va / vt, k, va, vw, vt))
    if rat:
        res[nm] = rat
        print("  【%s】%d 个场：v_a/v_w 中位 = **%.2f** ；v_a/v_厚 中位 = **%.2f**"
              % (nm, len(rat), float(np.median([x[0] for x in rat])),
                 float(np.median([x[1] for x in rat]))))
print()
if A in res and B in res:
    ma = float(np.median([x[0] for x in res[A]]))
    mb = float(np.median([x[0] for x in res[B]]))
    print("  ★ **判据 F2**：A(%s) = %.2f  →  B(%s) = %.2f  ⇒ %s"
          % (A, ma, B, mb,
             "✅ **PASS**（≥7，解析靶 9.90 的 70%%）" if mb >= 7 else
             "⚠ 未达 ≥7（解析靶 9.90）"))
    print("     相对基线提升 = **%.2f×**" % (mb / max(ma, 1e-9)))
