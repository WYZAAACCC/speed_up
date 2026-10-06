#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_probe_ndir.py —— **截获真实的** `dfield` / `ndir_` / `nd_ref_`（不改主代码）。

## 动机（`R638 §6.3` 的未解线索）
平界面（`∇φ∥x`）+ `n*∥z` 的场，`dG_max` 里出现了 `e^{−β_h}` ⇒
**说明有胞满足 `(n̂·n*)² ≈ 1`**。必须查清"哪些胞、为什么"。

## 手段：`np.stack` 桩
`windowB_surface.py:4682` 是 `ndir_ = np.stack([g_/gdn_ for g_ in gd_], -1)`
—— 它是该模块里**唯一**的 `np.stack` 调用 ⇒ 用猴子补丁截获 `gd_` 三元组**不会误伤**。
（调用前先自检：`advance` 之前计数应为 0。）
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

CAP = {}
_orig_stack = np.stack


def spy(arrays, *a, **k):
    try:
        lst = list(arrays)
        if len(lst) == 3 and all(getattr(x, 'ndim', 0) == 3 for x in lst):
            CAP['gd'] = [np.array(x, copy=True) for x in lst]
    except TypeError:
        pass
    return _orig_stack(arrays, *a, **k)


N, dx, M, df = 32, 2e-9, 1e-9, 1e7
z_, x_ = np.array([0., 0., 1.]), np.array([1., 0., 0.])

for tag, axis, gh in (('平界面∇φ∥x, n*∥z', 0, z_), ('平界面∇φ∥z, n*∥z', 2, z_)):
    np.stack = _orig_stack
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M, df=[0.0, -df],
                        reinit_every=0)
    r = (np.arange(N)[None, None, :] + 0.5) * dx
    a, L = (N // 2) * dx, N * dx
    prof = np.where(r <= a, -np.minimum(r, a - r), np.minimum(r - a, L - r))
    sh = [1, 1, 1]; sh[axis] = N
    g.phi[1] = prof.reshape(sh) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.npref = {1: np.asarray(gh, float)}
    g.wtab = np.full((2, 3), np.nan); g.wtab[1] = np.array([0., 1., 0.])
    CAP.clear()
    print("  [%s] advance 前 np.stack 命中数 = %d（自检应为 0）"
          % (tag, len(CAP)))
    np.stack = spy
    try:
        g.advance(0.1 * dx / (M * df), extend='edt', band_cells=20,
                  mob_beta=6.477, mob_iform='exp2', npref=g.npref, pin_min=True)
    finally:
        np.stack = _orig_stack
    if 'gd' not in CAP:
        print("     ⚠ 未截获 `gd_` ⇒ 该路径没走 `np.stack`（探针无效，不猜）")
        continue
    gd = CAP['gd']
    dfi = gd[0] - gd[1]
    gdn = np.sqrt(sum(x ** 2 for x in gd)) + 1e-30
    nd = np.stack([x / gdn for x in gd], -1)
    nd = nd / (np.linalg.norm(nd, axis=-1, keepdims=True) + 1e-300)
    c2 = np.clip(nd @ gh, -1, 1) ** 2
    iface = np.abs(dfi) <= 2.0 * dx * gdn
    print("     截获成功：`dfield` 范围 [%.3g, %.3g]；界面胞 %d"
          % (dfi.min(), dfi.max(), int(iface.sum())))
    if iface.any():
        v = c2[iface]
        print("     界面上 `(n·n*)²` 分位：p10=%.3f p50=%.3f p90=%.3f max=%.4f"
              % tuple(list(np.percentile(v, [10, 50, 90])) + [v.max()]))
        print("     ⇒ 满足 >0.81 的界面胞 = **%d / %d（%.1f%%）**"
              % (int((v > 0.81).sum()), v.size, 100.0 * (v > 0.81).mean()))
        m = float(np.exp(-6.477 * v).max())
        print("     ⇒ 界面上 `exp(−β_h·c2)` 的最小值 = **%.4g**（= 能给出的最大压制）" % m)
