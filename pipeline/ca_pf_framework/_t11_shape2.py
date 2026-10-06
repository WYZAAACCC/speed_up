#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_shape2.py —— **基无关**的形状量具（修掉 `a·n ≠ 0` 造成的系统性伪影）。

## 为什么必须换量具（实测根因）
`windowB_surface.py:1435 _rank1_axes` 的 docstring 明写：
  > ★ 记账：**`a·n` 不要求为 0**（rank-1 分解中 `a·n` 正比于 `trace(eps)`）
⇒ 我原先把胞坐标投影到 `a_ax` / `w_ax` / `n_hab` 三条**非正交**轴上取 `ptp`，
   **投影跨度会被非正交性污染**：
     沿 `n̂` 的真实跨度为 `c` 胞、而 `â·n̂ = cosθ` ⇒ 投影跨度可达 `c/|sinθ|`
     （θ=45° 时虚高 **41%**）
   ⇒ 立方核被量成 229/177/244 nm（−29%/+0%）正是这个伪影，**不是物理**。

## 换成什么
**回转张量**（gyration tensor）`G = ⟨(r−r̄)(r−r̄)ᵀ⟩` 的本征值 `λ1 ≥ λ2 ≥ λ3`：
  · **基无关**（本征值不依赖坐标系）；
  · 等效半轴 `R_i = √(5·λ_i)`（均匀椭球口径）；
  · 判据用 `√(λ1/λ3)` = **伸长比**（与"长/厚比"同义，但无基依赖）。

## 同时保留的量（用于与归档对照）
  · 沿 `n̂` 的**真实**厚度：把胞坐标投到 `n̂` 后，取**中心 60% 面内区域**的 `ptp`
    （避开斜轴边缘的拉长）；并报 `a·n` 内积以显式登记基的不正交程度。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def ncomp(mask):
    try:
        from scipy import ndimage
        lab, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n), lab
    except Exception:                                  # noqa: BLE001
        return -1, None


def shape_metrics(idx, a, w, nh):
    """基无关（回转张量）+ 沿 n̂ 的真实厚度。idx 为米单位的胞坐标。"""
    c = idx.mean(0)
    d = idx - c
    G = (d.T @ d) / max(d.shape[0], 1)
    lam = np.sort(np.linalg.eigvalsh(G))[::-1]
    R = np.sqrt(np.maximum(5.0 * lam, 0.0))           # 等效半轴
    # 沿 n̂ 的真实厚度：只取"沿 n̂ 的中间 60%"那层，避免斜边拉长
    pn = d @ nh
    lim = 0.3 * (pn.max() - pn.min()) if pn.size else 0.0
    core = np.abs(pn) <= lim if lim > 0 else np.ones_like(pn, bool)
    thick = float(np.ptp(pn[core])) if core.sum() > 4 else float(np.ptp(pn))
    return dict(
        R1=R[0], R2=R[1], R3=R[2],
        elong_lw=R[0] / max(R[1], 1e-30),      # 长/宽（基无关）
        elong_lt=R[0] / max(R[2], 1e-30),      # 长/厚（基无关）
        thick_nm=thick * 1e9,
        lw_ratio_of_R=R[0] / max(R[1], 1e-30),
        an=float(abs(a @ nh)),                 # 基不正交程度（登记用）
        aw=float(abs(a @ w)), nw=float(abs(nh @ w)),
    )


def series(tag, field=1):
    out = []
    for sp in sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz"))):
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        if field not in set(int(v) for v in np.unique(reg) if v):
            out.append((step, None, None))
            continue
        m = (reg == field)
        nc, lab = ncomp(m)
        idx_all = np.argwhere(m).astype(np.float64) * DX
        met_all = shape_metrics(idx_all, a, w, nh)
        met_big = None
        if lab is not None and nc > 1:
            szs = np.bincount(lab.ravel())
            szs[0] = 0
            ib = np.argwhere(lab == int(np.argmax(szs))).astype(np.float64) * DX
            met_big = shape_metrics(ib, a, w, nh)
        out.append((step, dict(ncell=int(m.sum()), nc=nc, L=L,
                               all=met_all, big=met_big), None))
    return out


if __name__ == "__main__":
    tags = sys.argv[1:] or ["c2Eq0"]
    for tag in tags:
        rows = series(tag)
        print("=" * 108)
        print("【%s】基无关形状量具（回转张量等效半轴 R_i = √(5λ_i)；elong = R1/R3）" % tag)
        print("=" * 108)
        print("  %-6s %-7s %-5s %-9s %-9s %-9s %-8s %-8s %-9s %s"
              % ('step', 'ncell', 'nc', 'R1(nm)', 'R2(nm)', 'R3(nm)',
                 'R1/R2', 'R1/R3', '厚_n̂(nm)', 'a·n'))
        for step, d, _ in rows:
            if d is None:
                print("  %-6d （场不在）" % step)
                continue
            t = d['big'] if d['big'] else d['all']
            src = '大分量' if d['big'] else '整场'
            print("  %-6d %-7d %-5d %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %-9.0f %.3f  %s"
                  % (step, d['ncell'], d['nc'], t['R1'] * 1e9, t['R2'] * 1e9,
                     t['R3'] * 1e9, t['elong_lw'], t['elong_lt'],
                     t['thick_nm'], t['an'], src))
