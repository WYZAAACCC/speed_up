#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pos_check.py —— ★ 用**新量具**（回转张量）量归档里**已知高长厚比的板条**。

## 为什么这是个便宜且必要的正对照（`P19`/`P24`）
`c2PosA`（核 R1/R3=9）要等 1 小时才轮到。而归档 `dry_t5AB_B` 的末快照里，
`_t11_arch_cmp.py` 用**旧口径**量出 8 个场的"长厚比"中位 = **8.34**。
⇒ 用新量具重量它：
  · 若新量具也给 ≈7–9 ⇒ **量具有分辨力**，`c2PosA` 可降为可选；
  · 若新量具给 ≈1–2 ⇒ **新量具把真实板条量没了** ⇒ `c2PosA` 成为**必需**，且我要重查量具。

判据（预登记）：
  · 新量具在 `t5AB_B` 上的 `R1/R3` 中位 **≥ 6** ⇒ PASS（有分辨力）；
  · 同时报 `t5AB_A`（旧口径 3.66）作对照，看两者是否被区分开。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
L = []


def run(tag, last_n=8):
    sns = sorted(glob.glob(os.path.join(ROOT, tag, "snap_*.npz")))
    if not sns:
        return None
    with np.load(sns[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
        step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
    L.append("\n【%s】末快照 step=%d  盒 %.2f µm  a·n=%.3f"
             % (tag, step, reg.shape[0] * DX * 1e6, float(abs(a @ nh))))
    L.append("  %-5s %-8s %-5s %-9s %-9s %-9s %-8s %-8s %-9s"
             % ('场', 'ncell', 'nc', 'R1(nm)', 'R2', 'R3', 'R1/R2', 'R1/R3', '厚_n̂'))
    flds = sorted(int(v) for v in np.unique(reg) if v != 0)
    res = []
    for k in flds[:last_n]:
        m = (reg == k)
        if m.sum() < 8:
            continue
        nc, lab = ncomp(m)
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        L.append("  %-5d %-8d %-5d %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %-9.0f"
                 % (k, int(m.sum()), nc, met['R1'] * 1e9, met['R2'] * 1e9,
                    met['R3'] * 1e9, met['elong_lw'], met['elong_lt'],
                    met['thick_nm']))
        res.append((met['elong_lt'], nc))
    if res:
        v = [x[0] for x in res]
        L.append("  ⇒ **R1/R3 中位 = %.2f**（范围 %.2f–%.2f，%d 个场）"
                 % (float(np.median(v)), min(v), max(v), len(v)))
    return [x[0] for x in res]


A = run("dry_t5AB_A")
B = run("dry_t5AB_B")
L.append("\n" + "=" * 100)
L.append("★ 判定（新量具是否有分辨力）")
L.append("=" * 100)
if B:
    mb = float(np.median(B))
    L.append("  `t5AB_B`（核 elong=3.75，旧口径 8.34）：新量具 **R1/R3 中位 = %.2f**" % mb)
    L.append("  ⇒ %s" % ("✅ **PASS：新量具有分辨力**（能测出高长厚比的真实板条）"
                         if mb >= 6 else
                         "❌ **FAIL：新量具把真实板条也量平了 ⇒ 必须重查量具**"))
if A:
    L.append("  `t5AB_A`（核 elong=0，旧口径 3.66）：新量具 **R1/R3 中位 = %.2f**"
             % float(np.median(A)))
if A and B:
    L.append("  ⇒ 两者是否被区分：%.2f vs %.2f（差 %.2f）"
             % (float(np.median(A)), float(np.median(B)),
                float(np.median(B)) - float(np.median(A))))
open("/mnt/f/speed_up/_w2_poscheck.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))
