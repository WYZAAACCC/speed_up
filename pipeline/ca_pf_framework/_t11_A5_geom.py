#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_A5_geom.py <tag>@<step> —— **A5 定量判定**：设计口径 vs 实现口径，盒子差多少。

## 两个口径（各自文档/代码的原文）
* **设计**（`BLOCK_SELFAC.md §8.C` 步骤 1 + `_r68_facet_op.py` 模块 docstring 步骤 1–2）：
  界面点 = `|φ_k| ≤ 0.5·Δx`；**支撑半宽 `h_j = (max−min)/2`**（即 **min/max**）。
* **实现**（`_r68_facet_op.facet_project_one:33-72`）：
  点云 = **体内胞 `φ_k < 0`**；`lo_j = quantile(·, 0.005)`、`hi_j = quantile(·, 0.995)`
  （`R70` 为抗"长指棘轮"从 min/max 改成分位数）。

## 判据（可 FAIL）
对同一快照、同一场、同一目标体积 `V0 = #(φ<0)`：
* **D1**：两口径给出的**三轴半宽**相对差 —— 若 ≤5% ⇒ **出入不影响结论**；
* **D2**：两口径给出的**盒子体积**（含 `|det U|` 换算）相对差 —— 同上；
* **D3**：两口径的**长厚比** `a/w` 相对差。

⇒ 若三者都 ≤5% ⇒ 结论：**该出入不影响上游判断**（可只记账）；
   若任一 >5% ⇒ 需报上游（因为它改变了 `facet_proj` 实际造的几何）。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def load(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % (st,))
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
        P = np.stack([X, Y, Z], -1).reshape(-1, 3)
        return dict(N=N, dx=dx, P=P,
                    idx=np.asarray(z['band_idx']),
                    val=np.asarray(z['band_val'], float),
                    fld=np.asarray(z['band_fld']),
                    U=np.stack([np.asarray(z['n_hab'], float),
                                np.asarray(z['a_ax'], float),
                                np.asarray(z['w_ax'], float)], 0))


def box(c, k, use_interface):
    """返回 (lo, hi, v0, detU)。`use_interface=True` ⇒ 设计口径（min/max）。"""
    N, dx, P = c['N'], c['dx'], c['P']
    sel = (c['fld'] == k)
    if int(sel.sum()) < 30:
        return None
    g = np.full(N ** 3, 1e3)
    g[c['idx'][sel]] = c['val'][sel]
    if use_interface:
        pts = P[np.abs(g) <= 0.5 * dx]           # 设计：界面点云
        if len(pts) < 30:
            return None
        pr = pts @ c['U'].T
        lo, hi = pr.min(0), pr.max(0)
        v0 = None                                 # 设计口径的"体积"用体内胞数
        body = int((g < 0).sum())
    else:
        pts = P[g < 0]                            # 实现：体内胞
        if len(pts) < 50:
            return None
        pr = pts @ c['U'].T
        lo = np.quantile(pr, 0.005, axis=0)
        hi = np.quantile(pr, 0.995, axis=0)
        body = int((g < 0).sum())
    lo = lo - 0.5 * dx
    hi = hi + 0.5 * dx
    return lo, hi, body, abs(float(np.linalg.det(c['U'])))


print("=" * 100)
print("A5：设计口径（界面点云 min/max） vs 实现口径（体内胞 分位数 0.005/0.995）")
print("=" * 100)
print("  %-6s %-6s %-26s %-26s %s"
      % ('tag', 'step', '设计: 三轴半宽(nm)', '实现: 三轴半宽(nm)', '半宽相对差'))
for spec in (sys.argv[1:] or ["B40@200", "B40@500", "L0@200", "L0@500"]):
    tag, _, st = spec.partition('@')
    st = int(st)
    c = load(tag, st)
    if c is None:
        print("  【%s@%d】快照缺失" % (tag, st))
        continue
    for k in sorted(int(v) for v in np.unique(c['fld']) if v > 0):
        a = box(c, k, True)
        b = box(c, k, False)
        if not a or not b:
            continue
        ha = 0.5 * (a[1] - a[0])
        hb = 0.5 * (b[1] - b[0])
        rel = np.abs(hb - ha) / np.maximum(ha, 1e-30)
        print("  %-6s %-6d %-26s %-26s %s"
              % (tag, st, '[%.0f, %.0f, %.0f]' % tuple(ha * 1e9),
                 '[%.0f, %.0f, %.0f]' % tuple(hb * 1e9),
                 '[%+.1f%%, %+.1f%%, %+.1f%%]' % tuple(100 * rel)))
        # 长厚比（a/w）
        ra = ha[1] / max(ha[2], 1e-30)
        rb = hb[1] / max(hb[2], 1e-30)
        print("         ⇒ `a/w`：设计 %.2f  实现 %.2f  相对差 **%+.1f%%**"
              % (ra, rb, 100 * (rb - ra) / max(ra, 1e-30)))
