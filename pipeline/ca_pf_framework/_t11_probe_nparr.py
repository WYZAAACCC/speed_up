#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_probe_nparr.py —— **直接测掉候选 (c)**：`np_arr[0]` 是否 NaN、界面上是否有 `karr==0`。

## 候选 (c)（`R638 §8.4`）
`windowB_surface.py:4684`：`np_arr = np.full((nreg,3), np.nan)`；
`:4686` 只在 `npref` 的**键**上循环（键 = 变体号 ≥ 1）⇒ **`np_arr[0]` 从未被赋值**。
若某个界面胞的 winner 是母相（`karr==0`）且 `larr==0`（另一侧也是母相），
则 `nd_ref = np_arr[0]` = **NaN** ⇒ `c2b_` = NaN ⇒ `np.exp(NaN)·...` = NaN
⇒ 而 `np.max`（非 nanmax）**会忽略 NaN** ⇒ **最大值可能来自完全没有界面的胞**。

## 怎么测（不改主代码）
用 `np.stack` 桩截获 `gd_` 的同时，**从 `self` 上取 `karr`/`larr`**？
—— 它们是局部变量，拿不到。改为**复算**：用与引擎同一套公式重算 `karr/larr`，
或**直接读引擎写在 `self` 上的可得量**。
⇒ 最省的做法：**只看"界面上是否存在 `(n·n*)²` 为 NaN 的胞"**，
   并统计**非界面胞**（远离界面）里是否也有 `(n·n*)²≈1`（那才是 `dG_max` 的来源）。
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402

CAP = {}
_orig = np.stack


def spy(arrays, *a, **k):
    try:
        lst = list(arrays)
        if len(lst) == 3 and all(getattr(x, 'ndim', 0) == 3 for x in lst):
            CAP['gd'] = [np.array(x, copy=True) for x in lst]
    except TypeError:
        pass
    return _orig(arrays, *a, **k)


N, dx, M, df = 32, 2e-9, 1e-9, 1e7
z_ = np.array([0., 0., 1.])

for tag, axis in (('∇φ∥x, n*∥z', 0), ('∇φ∥z, n*∥z', 2)):
    np.stack = _orig
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M, df=[0.0, -df],
                        reinit_every=0)
    r = (np.arange(N)[None, None, :] + 0.5) * dx
    a, L = (N // 2) * dx, N * dx
    prof = np.where(r <= a, -np.minimum(r, a - r), np.minimum(r - a, L - r))
    sh = [1, 1, 1]; sh[axis] = N
    g.phi[1] = prof.reshape(sh) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    g.npref = {1: z_}
    g.wtab = np.full((2, 3), np.nan); g.wtab[1] = np.array([0., 1., 0.])
    CAP.clear()
    np.stack = spy
    try:
        g.advance(0.1 * dx / (M * df), extend='edt', band_cells=20,
                  mob_beta=6.477, mob_iform='exp2', npref=g.npref, pin_min=True)
    finally:
        np.stack = _orig
    if 'gd' not in CAP:
        print("【%s】⚠ 未截获" % tag); continue
    gdn = np.sqrt(sum(x ** 2 for x in CAP['gd']))
    print("=" * 92)
    print("【%s】" % tag)
    print("  `|∇(φ0−φ1)|` 直方图（前 6 档）：")
    h, e = np.histogram(gdn, bins=6)
    for i in range(6):
        print("     [%.3g, %.3g) : %d 胞" % (e[i], e[i + 1], h[i]))
    # ⚠ 关键：**非零梯度**的胞有多少？梯度≈0 的胞（远离界面）也参与 `Mfac` 吗？
    nz = gdn > 1e-9
    print("  ⇒ 梯度非零的胞 = %d / %d（%.1f%%）" % (int(nz.sum()), gdn.size,
                                                    100.0 * nz.mean()))
    print("     **若只有 ~界面那么多** ⇒ 说明 `ndir_` 只在界面附近有定义；")
    print("     **若几乎全部** ⇒ 说明 `gd_` 不是空间梯度（而是别的场）。")
    # 复算 ndir 并看 (n·n*)² 在所有"梯度非零"胞上的分布
    nd = np.stack([x / (gdn + 1e-30) for x in CAP['gd']], -1)
    nd = nd / (np.linalg.norm(nd, axis=-1, keepdims=True) + 1e-300)
    c2 = np.clip(nd @ z_, -1, 1) ** 2
    v = c2[nz]
    if v.size:
        print("  梯度非零胞上 `(n·n*)²`：p50=%.3f  max=%.4f  >0.81 占 %.1f%%"
              % (np.median(v), v.max(), 100.0 * (v > 0.81).mean()))
