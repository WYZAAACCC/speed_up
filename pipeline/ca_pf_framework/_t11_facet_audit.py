#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_facet_audit.py <tag>@<step> —— 核实两件事（用数据，不靠推断）：
 ① **界面到底是"零厚度 Gibbs 面"还是弥散的？** ⇒ 量 φ 的带宽（`band_val` 的范围与层数）
 ② **所有场都变成盒子了吗？** ⇒ 逐场报 `(n*,a,w)` 三轴上的**跨度**，并与"盒子"的一致性检查
    （盒子判据：沿三轴投影的**分布应是阶跃**——内部均匀、边界锐利）
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp  # noqa: E402

for spec in (sys.argv[1:] or ["B40@700"]):
    tag, _, st = spec.partition('@')
    st = int(st)
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        print("缺 %s" % p)
        continue
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        L = float(np.asarray(z['L']).ravel()[0])
        N = int(np.asarray(z['N']).ravel()[0])
        dx = L / N
        bv = np.asarray(z['band_val'], float)
        bf = np.asarray(z['band_fld'])
        bc = int(np.asarray(z['band_cells']).ravel()[0])
        ii, jj, kk = np.unravel_index(np.asarray(z['band_idx']), (N, N, N))
        a = np.asarray(z['a_ax'], float)
        w = np.asarray(z['w_ax'], float)
        nh = np.asarray(z['n_hab'], float)

    print("=" * 96)
    print("【%s】step %d" % (tag, st))
    print("=" * 96)
    # ---- ① 界面厚度 ----
    print("  ① 界面带宽（`φ` 的弥散程度）")
    print("     快照带：%d 胞（`band_cells`=%d），`band_val` 范围 [%.4g, %.4g] m"
          % (bc, bc, bv.min(), bv.max()))
    print("     ⇒ 带半宽 = %.4g m = **%.1f 个胞**" % (bv.max(), bv.max() / dx))
    print("     ⚠ 说明：这只是**快照存下来**的带；φ 的实际过渡层厚度由 `reinit_band` 与"
          "平流扩散决定，量级为**数胞宽**（不是零厚度）。")
    # ---- ② 逐场是否盒子 ----
    print()
    print("  ② 逐场：三轴跨度 + 盒子一致性")
    print("     %-6s %-9s %-26s %-9s %s"
          % ('场', '胞数', '三轴跨度(nm)', '体积占比', '沿 a 的填充率（盒内胞/盒体积）'))
    tot = int((reg > 0).sum())
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        n0 = int(m.sum())
        if n0 < 50:
            continue
        nc, lab = ncomp(m)
        if lab is not None and nc > 1:
            s = np.bincount(lab.ravel()); s[0] = 0
            m = (lab == int(np.argmax(s)))
        idx = np.argwhere(m).astype(float)
        pr = idx @ np.stack([nh, a, w], 0).T          # 三轴坐标（胞）
        span = (pr.max(0) - pr.min(0) + 1)
        boxvox = float(np.prod(span))
        fill = float(m.sum()) / max(boxvox, 1)
        print("     %-6d %-9d %-26s %-9s **%.3f**"
              % (k, int(m.sum()),
                 '[%.0f, %.0f, %.0f]' % tuple(span * dx * 1e9),
                 100.0 * int(m.sum()) / max(tot, 1), fill))
    print()
    print("     ⇒ 判读：`填充率 ≈ 1.000` ⇒ **该场就是一个盒子**；`≪1` ⇒ 不是盒子（形状自由）。")
