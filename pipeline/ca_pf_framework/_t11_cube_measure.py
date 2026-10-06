#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cube_measure.py <arm> —— 量立方核臂的**逐场三轴跨度与长宽/长厚比**（含碎裂登记）。

⚠ 纪律：
  · 全用 `np.ptp()`（numpy≥2 去掉了 `ndarray.ptp()`）；
  · **必须同时报连通分量数 `nc`**（场碎了 ⇒ 跨度量的是碎片云包络，不是单根形状）；
  · **必须报绕盒**（跨度为盒尺度即自贯通 ⇒ 口径失去分辨力）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
ARM = sys.argv[1] if len(sys.argv) > 1 else "cubeEq0"
DX = 62.5e-9


def ncomp(mask):
    """26-连通分量数（能量出"场碎成几块"）。"""
    try:
        from scipy import ndimage
        _, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n)
    except Exception:                              # noqa: BLE001
        return -1


sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % ARM, "snap_*.npz")))
print("=" * 100)
print("【%s】立方核生长：逐场三轴跨度 + 长宽比/长厚比（%d 个快照）" % (ARM, len(sns)))
print("=" * 100)
for sp in sns:
    with np.load(sp, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a = np.asarray(z['a_ax'], float)
        w = np.asarray(z['w_ax'], float)
        nh = np.asarray(z['n_hab'], float)
        step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        N = reg.shape[0]
    L = N * DX
    print("\nstep=%d  盒 %.2f µm  场数=%d" % (step, L * 1e6,
                                            len([v for v in np.unique(reg) if v])))
    print("  %-5s %-7s %-6s %-9s %-9s %-9s %-8s %-8s %s"
          % ('场', '胞数', '碎裂', '沿a(nm)', '沿w(nm)', '沿n(nm)', '长/宽', '长/厚', '绕盒'))
    for k in sorted(int(v) for v in np.unique(reg) if v != 0)[:8]:
        m = (reg == k)
        idx = np.argwhere(m).astype(np.float64) * DX
        if idx.shape[0] < 8:
            continue
        sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                      float(np.ptp(idx @ nh)))
        nc = ncomp(m)
        wrap = '⚠自贯通' if max(sa, sw, sn) > 0.6 * L else ''
        print("  %-5d %-7d %-6s %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %s"
              % (k, idx.shape[0], nc if nc > 0 else '?',
                 sa * 1e9, sw * 1e9, sn * 1e9,
                 sa / max(sw, 1e-30), sa / max(sn, 1e-30), wrap))
