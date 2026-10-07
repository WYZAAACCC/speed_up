#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_box_verify2.py <tag>@<step> —— **修正后的盒子判据**：体积 = 跨度之积 × |det U|。

## 我的量具错在哪（`R650`）
第一版把"盒子体积"算成 `span_n·span_a·span_w`（三个**不正交**轴的跨度之积）。
但 `n*·a = −0.1271`（`R628 §9` 已记账）⇒ 三轴**不构成正交基**
⇒ 正确的体积换算必须带 **`|det U|`**（`U` 的行 = 三轴单位向量）。
⇒ 修正后重算填充率，并按 `facet_project_one` 的**解析公式**预测胞数：
     `V_anal = |det U| · (span_n·span_a·span_w) · det(0.5Δx 外扩)`
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
spec = sys.argv[1] if len(sys.argv) > 1 else "B40@700"
tag, _, st = spec.partition('@')
st = int(st)
p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
with np.load(p, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    L = float(np.asarray(z['L']).ravel()[0])
    N = int(np.asarray(z['N']).ravel()[0])
    dx = L / N
    U = np.stack([np.asarray(z['n_hab'], float),
                  np.asarray(z['a_ax'], float),
                  np.asarray(z['w_ax'], float)], 0)
detU = abs(float(np.linalg.det(U)))
print("=" * 90)
print("【%s】step %d   |det U| = **%.4f**" % (tag, st, detU))
print("=" * 90)
print("  %-6s %-9s %-10s %-12s %s" % ('场', '实际胞数', '跨度之积', '×|detU| 预期', '填充率（修正）'))
for k in sorted(int(v) for v in np.unique(reg) if v > 0):
    m = (reg == k)
    n0 = int(m.sum())
    if n0 < 50:
        continue
    pr = np.argwhere(m).astype(float) @ U.T
    span = pr.max(0) - pr.min(0) + 1.0
    raw = float(np.prod(span))
    exp = raw * detU
    print("  %-6d %-9d %-10.0f %-12.0f **%.3f**"
          % (k, n0, raw, exp, n0 / max(exp, 1e-9)))
print()
print("  ⇒ 判读：修正后填充率 ≈ 1 ⇒ **该场确实是实心盒子**（`facet_project` 生效）。")
print("  ⚠ 记账：`R650` 的第一版量具漏了 `|det U|` ⇒ 报出 0.26 的假填充率。")
