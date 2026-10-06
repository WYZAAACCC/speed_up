#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_radial.py <tag> —— ★★★ **径向界面位移 vs 取向**（不依赖任何"面分类"）。

## 为什么这是决定性的
前两个量具都依赖"把界面胞分成 tip/side/wide"⇒ 结论受**阈值**影响。
本工具**完全不分档**，只按**取向区间**统计"界面到质心的径向距离"的**增长率**：
  `v(θ) = Δr(θ)/Δstep`，`θ` = 界面法向与 `n*` 的夹角
⇒ 若速度律各向异性被兑现，`v(θ)` 应**随 θ 强烈变化**；
⇒ 若界面粗糙/球化，`v(θ)` 应**几乎是常数**。

## 判据（可 FAIL，先登记）
  · **R1**：把 `cos²θ = (n·n*)²` 分成 5 档，`v(θ)` 应**单调变化**且
    **`v(⊥n*) / v(∥n*) ≥ 3`**（对应 `β_h=6.477` 的压制）；
    `≈1` ⇒ 各向异性未兑现 ⇒ FAIL。
  · **R2（形状核对）**：同时报"界面到质心的平均半径"，确认形状确实长得慢。
"""
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_vface2 import load  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
BINS = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, 1.0)]


def radial(C):
    phi = np.nan_to_num(C['phi'], nan=1e9)
    dx = C['dx']
    g = np.gradient(phi, dx, edge_order=1)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    iface = np.abs(phi) <= 1.5 * dx
    nd = np.stack([x / gn for x in g], axis=-1)
    pos = np.argwhere(iface).astype(float) * dx
    if pos.shape[0] < 50:
        return None
    ctr = pos.mean(0)
    rel = pos - ctr
    r = np.linalg.norm(rel, axis=1)
    c2n = np.clip(nd[iface] @ C['nh'], -1, 1) ** 2
    out = []
    for lo, hi in BINS:
        sel = (c2n >= lo) & (c2n < hi)
        out.append((lo, hi, int(sel.sum()), float(r[sel].mean()) * 1e9
                    if sel.sum() > 20 else np.nan))
    return out, float(r.mean()) * 1e9, pos.shape[0]


for tag in (sys.argv[1:] or ["kW1"]):
    t = tag[4:] if tag.startswith('dry_') else tag
    d = os.path.join(ROOT, "dry_%s" % t)
    if not os.path.isdir(d):
        continue
    steps = []
    for sp in sorted(os.listdir(d)):
        if sp.startswith("snap_"):
            with np.load(os.path.join(d, sp), allow_pickle=False) as z:
                steps.append(int(np.asarray(z['step']).ravel()[0]))
    steps.sort()
    if len(steps) < 3:
        continue
    s0, s1 = steps[1], steps[-1]
    C0, C1 = load(t, s0), load(t, s1)
    if C0 is None or C1 is None:
        continue
    R0, rav0, n0 = radial(C0)
    R1, rav1, n1 = radial(C1)
    print("=" * 96)
    print("【%s】径向界面位移 vs 取向（step %d→%d；界面胞 %d→%d）" % (t, s0, s1, n0, n1))
    print("=" * 96)
    print("  %-16s %-10s %-12s %-12s %-12s"
          % ('(n·n*)² 区间', '胞数', 'r(step%d)' % s0, 'r(step%d)' % s1, 'v(nm/步)'))
    vs = []
    for (lo, hi, n, r0), (_, _, _, r1) in zip(R0, R1):
        ds = max(s1 - s0, 1)
        v = (r1 - r0) / ds if np.isfinite(r0) and np.isfinite(r1) else np.nan
        vs.append(v)
        print("  %-16s %-10d %-12.1f %-12.1f **%+.4f**"
              % ('[%.1f, %.1f)' % (lo, hi), n, r0, r1, v))
    print()
    if np.isfinite(vs[0]) and np.isfinite(vs[-1]) and abs(vs[-1]) > 1e-9:
        print("  ⇒ `v(⊥n*)`=%.4f（区间 [0,0.1)）  /  `v(∥n*)`=%.4f（区间 [0.8,1.0]）"
              % (vs[0], vs[-1]))
        print("  ⇒ **比值 `v(⊥n*)/v(∥n*)` = %+.2f**（判据 R1 靶 ≥3）" % (vs[0] / vs[-1]))
    else:
        print("  ⇒ ⚠ 端点区间不可用 ⇒ 无法判定（`P26`）")
    print("  · 平均半径 %.1f → %.1f nm（×%.2f）" % (rav0, rav1, rav1 / max(rav0, 1e-9)))
