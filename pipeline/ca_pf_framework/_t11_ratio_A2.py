#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ratio_A2.py —— **A2：尺度比 `γ·κ / Δf`**（goal 关键判据；修订版）。

## 判据（goal 预先登记）
若 `γκ/Δf ≪ 1e-2` ⇒ **瓶颈不在刻面表示** ⇒ **阶段 C（显式多面体）不应开工**
（依据 `LATH_FACET_PLAN` 主因②：界面能通道被驱动力压掉 ~4 个量级）。

## ⚠ 记账：口径与文档不完全相同（必须并列报）
* **文档**（`LATH_FACET_PLAN:53`）用的是 `γ·κ ≈ 0.15×(2/4µm) ≈ **7.5e4 Pa**`，
  其中 `γ=0.15` 是**文献类值**、`κ=2/4µm` 是**"形状半径"量级估计**（不是逐点曲率）；
* **本工具**用**引擎实际配置** `γ0 = 0.25`（`--gamma0`），
  `κ = ∇·n̂`（`n̂ = ∇φ/|∇φ|`，**φ 的等值面曲率**，逐点）。
⇒ **两者口径不同**：文档是"量级估计"，本工具是"逐点实测"。
**⇒ 对齐锚点**：本工具的 `γ·κ` 中位应与 **7.5e4** 同量级；差一个量级以上要记账。

## ⚠ 另一条口径限制（`R652` 已记账）
`Δf` 由 `ε⁰` 框架给出，而 `κ` 由 `φ` 给出 ⇒ **两者不同源**。
**但比值只需量级**，且 `Δf` 的三个口径（`dG_max`/`dG_p999`/`dG_wide`）都会并列报。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
GAMMA0 = 0.25          # `_t11_facet_arm.py:72` 的 `--gamma0 0.25`
DX = 62.5e-9
DOC_REF = 7.5e4        # 文档的口径参照（Pa）


def csv_rows(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = dict(
                    dmax=float(r.get('dG_max_Jm3') or 'nan'),
                    p999=float(r.get('dG_p999') or 'nan'),
                    wide=float(r.get('dG_wide') or 'nan'),
                    tip=float(r.get('dG_tip') or 'nan'),
                    f1=float(r.get('f1_area_m2') or 'nan'))
            except (KeyError, ValueError):
                pass
    return d


def curvature(tag, st):
    """对**最大场**的 φ 算 κ = ∇·n̂，返回界面上的 |κ| 分位。"""
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % (st,))
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        idx = np.asarray(z['band_idx'])
        val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
        reg = np.asarray(z['region']).astype(np.int32)
    fl = [int(v) for v in np.unique(fld) if v > 0]
    if not fl:
        return None
    # 取胞数最大的场
    ks = [k for k in fl if int((fld == k).sum()) > 200]
    if not ks:
        return None
    best = None
    for k in ks:
        n_k = int((reg == k).sum())
        if best is None or n_k > best[1]:
            best = (k, n_k)
    k = best[0]
    sel = (fld == k)
    g = np.full(N ** 3, 1e3)
    g[idx[sel]] = val[sel]
    G = g.reshape(N, N, N)
    ifc = np.abs(G) <= 1.5 * dx
    if int(ifc.sum()) < 100:
        return None
    gr = np.gradient(G, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
    n = np.stack([x / gn for x in gr], -1)
    kk = sum(np.gradient(n[..., i], dx, edge_order=2)[i] for i in range(3))
    a = np.abs(kk)[ifc]
    return dict(k=int(k), ncell=best[1], kappa=a, npts=int(ifc.sum()))


print("=" * 100)
print("A2：尺度比 `γ·κ / Δf`（判据：若 ≪1e-2 ⇒ 阶段 C 不应开工）")
print("  γ0 = %.3f（引擎实配）、κ = ∇·n̂（φ 等值面曲率）、文档口径参照 = %.1g Pa"
      % (GAMMA0, DOC_REF))
print("=" * 100)
print("  %-7s %-8s %-11s %-11s %-11s %-12s %-12s %s"
      % ('tag', 'step', 'γ·κ p50', 'γ·κ p90', 'κ p50', 'dG_max', 'dG_p999', '比值 p50/dG_p999'))
for tag in ("L0", "B40"):
    rows = csv_rows(tag)
    if not rows:
        print("  【%s】无 CSV" % tag)
        continue
    sts = sorted(rows)
    print("  --- %s ---" % tag)
    for st in sts:
        if st % 100 and st not in (0, 50):
            continue
        c = curvature(tag, st)
        if c is None:
            continue
        gk50 = GAMMA0 * float(np.median(c['kappa']))
        gk90 = GAMMA0 * float(np.percentile(c['kappa'], 90))
        r = rows.get(st, {})
        dp = r.get('p999', float('nan'))
        ratio = gk50 / dp if dp and dp == dp and dp > 0 else float('nan')
        print("  %-7s %-8d %-11.3g %-11.3g %-11.3g %-12.4g %-12.4g %.3e"
              % (tag, st, gk50, gk90, float(np.median(c['kappa'])),
                 r.get('dmax', float('nan')), dp, ratio))
print()
print("  ⇒ 判读：`比值 p50/dG_p999` 若 **≪1e-2** ⇒ **界面能通道被驱动力压掉** ⇒ 阶段 C 不应开工。")
