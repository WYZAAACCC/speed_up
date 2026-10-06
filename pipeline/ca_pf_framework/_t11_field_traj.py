#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_field_traj.py <tag> <field> [...] —— 抽**指定场**逐快照的三轴跨度（伸长轨迹）。

用途：回答"伸长是持续发生还是停滞"。判据纪律（`R628`）：
  · 报连通分量数 `nc`（碎了 ⇒ 跨度量的是碎片云包络）；
  · 跨度 > 0.6×盒 ⇒ 标 WRAP 并**排除该读数**；
  · 长轴 = 三轴最大（无先验）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
if len(sys.argv) < 3:
    sys.exit("用法: _t11_field_traj.py <tag> <field> [field2 ...]")


def ncomp(mask):
    try:
        from scipy import ndimage
        _, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n)
    except Exception:                                  # noqa: BLE001
        return -1


tag = sys.argv[1]
flds = [int(x) for x in sys.argv[2:]]
sns = sorted(glob.glob(os.path.join(ROOT, tag, "snap_*.npz")))
print("=" * 106)
print("【%s】场 %s 的伸长轨迹（%d 个快照）" % (tag, flds, len(sns)))
print("=" * 106)
for fd in flds:
    print("\n  ◆ 场 %d" % fd)
    print("    %-7s %-8s %-6s %-9s %-9s %-9s %-8s %-8s %s"
          % ('step', 'ncell', 'nc', '沿a(nm)', '沿w(nm)', '沿n(nm)', 'L/W', 'L/T', '备注'))
    tab = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            N = reg.shape[0]
        L = N * DX
        m = (reg == fd)
        if m.sum() < 8:
            continue
        idx = np.argwhere(m).astype(np.float64) * DX
        sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                      float(np.ptp(idx @ nh)))
        trio = sorted([sa, sw, sn], reverse=True)
        lw, lt = trio[0] / max(trio[1], 1e-30), trio[0] / max(trio[2], 1e-30)
        wrap = trio[0] > 0.6 * L
        print("    %-7d %-8d %-6s %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %s"
              % (st, int(m.sum()), ncomp(m), sa * 1e9, sw * 1e9, sn * 1e9,
                 lw, lt, 'WRAP(排除)' if wrap else ''))
        if not wrap:
            tab.append((st, lt, sn * 1e9))
    if len(tab) >= 2:
        print("    ⇒ 未绕盒：step %d→%d，**L/T %.2f → %.2f**（%+.2f）；"
              "厚度 %.0f → %.0f nm"
              % (tab[0][0], tab[-1][0], tab[0][1], tab[-1][1],
                 tab[-1][1] - tab[0][1], tab[0][2], tab[-1][2]))
    elif tab:
        print("    ⇒ 只有 1 个未绕盒读数 ⇒ 无法判趋势（`P26` 分辨力闸）")
    else:
        print("    ⇒ 全部自贯通 ⇒ 无法判定")
