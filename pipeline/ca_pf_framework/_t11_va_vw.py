#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_va_vw.py <tag> [...] —— 测**长/宽速度比** `v_a/v_w`（(1) 的核心判据）。

## 怎么测（不靠猜）
对每个场、每对相邻快照：
  · 用**基无关回转张量**取该场在三个主方向的等效半轴 `R1 ≥ R2 ≥ R3`
  · **长轴方向**的半轴变化率 `v_a = ΔR1/Δstep`
  · **宽轴方向**的半轴变化率 `v_w = ΔR2/Δstep`
  ⇒ `v_a/v_w` 即"伸长 vs 加宽"的速度比（长条在**面内**拉长，宽度是第二快方向）

⚠ 记账：`R1/R3` 是"长/厚"，`R1/R2` 是"长/宽"。
   `β_h` 压的是**沿 `n*`（厚）**，所以**真正对应 `β_h` 的是 `v_a/v_厚`**；
   但仓库里 `P1-31` 报的 **9.90** 是 **`v_a/v_w`（长/宽）**。
   ⇒ **本工具两个都报**，并以 `v_a/v_w` 对照 P1-31 的 9.90。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
for tag in (sys.argv[1:] or ["fW0"]):
    t = tag[4:] if tag.startswith('dry_') else tag
    sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % t, "snap_*.npz")))
    print("=" * 100)
    print("【%s】v_a/v_w（长/宽速度比）  快照 %d 个" % (t, len(sns)))
    print("=" * 100)
    if len(sns) < 2:
        print("   ⚠ 快照不足（需要 ≥2 个）⇒ 无法测速度")
        continue
    # 逐场收集 (step, R1, R2, R3)
    per = {}
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        for k in sorted(int(v) for v in np.unique(reg) if v > 0):
            m = (reg == k)
            if m.sum() < 20:
                continue
            nc, lab = ncomp(m)
            # 只用最大分量（`P22`；孤儿胞会污染矩）
            if lab is not None and nc > 1:
                szs = np.bincount(lab.ravel()); szs[0] = 0
                m = (lab == int(np.argmax(szs)))
            met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
            per.setdefault(k, []).append((st, met['R1'], met['R2'], met['R3']))
    print("  %-5s %-28s %-12s %-12s %s"
          % ('场', 'step 区间', 'v_a(nm/步)', 'v_w(nm/步)', 'v_a/v_w'))
    ratios = []
    for k, lst in sorted(per.items()):
        lst.sort()
        if len(lst) < 2:
            continue
        s0, s1 = lst[0], lst[-1]
        d = max(s1[0] - s0[0], 1)
        va, vw, vt = (s1[1] - s0[1]) / d, (s1[2] - s0[2]) / d, (s1[3] - s0[3]) / d
        if vw <= 0:
            print("  %-5d %-28s %-12.4f %-12.4f %s"
                  % (k, '%d→%d' % (s0[0], s1[0]), va * 1e9, vw * 1e9,
                     '⚠ v_w ≤ 0（未加宽）'))
            continue
        r = va / vw
        ratios.append(r)
        print("  %-5d %-28s %-12.4f %-12.4f **%.2f**"
              % (k, '%d→%d' % (s0[0], s1[0]), va * 1e9, vw * 1e9, r))
    if ratios:
        print("  ⇒ **v_a/v_w 中位 = %.2f**（%d 个场；解析靶 9.90）"
              % (float(np.median(ratios)), len(ratios)))
    else:
        print("  ⇒ 无可用比值")
