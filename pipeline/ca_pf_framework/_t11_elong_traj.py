#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_elong_traj.py <tag> —— 抽**等轴核算例的伸长时间演化**（用户问题的直接答案）。

判据与纪律（`R628`）：
  · **只量场 1**（t=0 播下的那一片）⇒ 追踪它自己从 step 0 到末步的形貌；
  · **报连通分量数 `nc`**（碎了 ⇒ 跨度量的是碎片云包络）；
  · **跨度 > 0.6×盒 ⇒ 标 WRAP 并排除**。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = sys.argv[1] if len(sys.argv) > 1 else "dry_t5AB_A"
fld = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def ncomp(mask):
    try:
        from scipy import ndimage
        _, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n)
    except Exception:                                  # noqa: BLE001
        return -1


sns = sorted(glob.glob(os.path.join(ROOT, tag, "snap_*.npz")))
print("=" * 104)
print("【%s】场 %d 的伸长时间演化（等轴核 ⇒ ?）  共 %d 个快照" % (tag, fld, len(sns)))
print("=" * 104)
print("  %-7s %-7s %-8s %-6s %-9s %-9s %-9s %-8s %-8s %s"
      % ('step', 'nfield', 'ncell', 'nc', '沿a(nm)', '沿w(nm)', '沿n(nm)',
         'L/W', 'L/T', '备注'))
rows = []
for sp in sns:
    with np.load(sp, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
        step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        N = reg.shape[0]
    L = N * DX
    nf = len([v for v in np.unique(reg) if v])
    m = (reg == fld)
    if m.sum() < 8:
        print("  %-7d %-7d （场 %d 不在/太小）" % (step, nf, fld))
        continue
    idx = np.argwhere(m).astype(np.float64) * DX
    sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                  float(np.ptp(idx @ nh)))
    trio = sorted([sa, sw, sn], reverse=True)      # 长轴取三轴最大（无先验）
    lw, lt = trio[0] / max(trio[1], 1e-30), trio[0] / max(trio[2], 1e-30)
    wrap = trio[0] > 0.6 * L
    print("  %-7d %-7d %-8d %-6s %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %s"
          % (step, nf, int(m.sum()), ncomp(m), sa * 1e9, sw * 1e9, sn * 1e9,
             lw, lt, 'WRAP(排除)' if wrap else ''))
    rows.append((step, lw, lt, wrap))
ok = [(s, lw, lt) for s, lw, lt, wp in rows if not wp]
if len(ok) >= 2:
    print("\n  ⇒ **未绕盒读数的趋势**：")
    print("     step %d → %d ：L/W %.2f → %.2f ；**L/T %.2f → %.2f**"
          % (ok[0][0], ok[-1][0], ok[0][1], ok[-1][1], ok[0][2], ok[-1][2]))
    print("     ⇒ 伸长**%s**（L/T 变化 %+.2f）"
          % ("在发生" if ok[-1][2] > ok[0][2] + 0.15 else
             "**未发生/停滞**", ok[-1][2] - ok[0][2]))
elif ok:
    print("\n  ⇒ 只有 1 个未绕盒读数 ⇒ **无法判定趋势**（`P26` 的分辨力闸）")
else:
    print("\n  ⇒ **全部读数自贯通 ⇒ 无法判定**")
