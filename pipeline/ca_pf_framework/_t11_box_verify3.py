#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_box_verify3.py <tag>@<step> —— **正确判"是否实心盒子"**：
数**被占据的三轴格点组合数** `unique((i,j,k))`，与"跨度之积"比。

## 我前两版量具的错（`R650` 记账）
* 第一版：体积算成"三轴跨度之积"（`n*·a=−0.127` 不正交）⇒ 只加了 `|det U|`，几乎无变化；
* 第二版：只查"每轴占用的**层数**" ⇒ 但**一叠斜放薄片也能铺满每个轴**
  ⇒ 必须数**三轴的联合组合**。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for spec in (sys.argv[1:] or ["B40@700", "L0@700"]):
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
        U = np.stack([np.asarray(z['n_hab'], float),
                      np.asarray(z['a_ax'], float),
                      np.asarray(z['w_ax'], float)], 0)
    print("=" * 92)
    print("【%s】step %d —— 三轴**联合**格点占用" % (tag, st))
    print("=" * 92)
    print("  %-6s %-9s %-13s %-13s %-13s %s"
          % ('场', '胞数', '跨度之积', '联合格点数', '联合/跨度', '自由形状的预期'))
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        n0 = int(m.sum())
        if n0 < 50:
            continue
        pr = np.argwhere(m).astype(float) @ U.T
        lo = np.floor(pr.min(0)); hi = np.ceil(pr.max(0))
        span = hi - lo + 1.0
        ijk = np.round(pr - lo).astype(np.int64)
        uniq = len(np.unique(ijk, axis=0))
        print("  %-6d %-9d %-13.0f %-13d %-13.3f %.3f"
              % (k, n0, float(np.prod(span)), uniq,
                 uniq / max(float(np.prod(span)), 1.0),
                 n0 / max(float(np.prod(span)), 1.0)))
    print()
    print("  ⇒ 判读：`联合/跨度 ≈ 1` ⇒ **实心盒子**（几乎每个格点组合都被占）；")
    print("           `联合/跨度 ≪ 1` ⇒ **不是实心**（形状是薄片/骨架/多片堆叠）。")
