#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r91_axisid.py —— **`n_inv` 到底是哪根轴？**（把 `_r90` 的 90° 偏移定案）

## 已知（`_r90`，可复现）

* `F = FV[v]`（`windowB_ti64_variants.variants()` 的**真形变梯度**）；
* `n_inv[v]` = `Fᵀ` 的、`λ` 最接近 1 的左特征向量；
* **12/12 变体上 `∠(NPF[v], n_inv[v]) = 90.00°`**（精确到两位小数）；
* `n_inv` 的**配对结构**（`|n_i·n_j| ≈ 1` 的 6 对）与 `EPS0` 的**唯一**配对
  `(1,2)(3,4)(5,6)(7,8)(9,10)(11,12)` **完全一致（6/6）**；
* 而 `NPF` 下这 6 对**一对都不共享**。

⇒ 90° 这个数太整齐，必须排除"`NPF` 其实是同一组三轴里的**另一根**"。

## 本脚本

引擎里变体 `v` 的三轴由 `_bk_exp.py:546-557` 给出：
    `(n, a, w) = (NPF[v], R[1], R[2])`，`R = LevelSetMulti._rank1_axes(eps0_v, NPF[v])`
（注意：实测 `n·a = −0.1271 ≠ 0` ⇒ **这三根并不正交**，所以"90°"不一定意味着"另一根轴"。）

逐变体报 5 个夹角 ⇒ 一次定案。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0, NPF                         # noqa: E402
from windowB_ti64_variants import variants                   # noqa: E402

_E, FV, _M = variants()
NV = len(FV)


def npf(v):
    try:
        a = np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        a = np.asarray(NPF[v - 1], float)
    return a / np.linalg.norm(a)


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(float(u @ v)), -1.0, 1.0))))


def ninv_of(v):
    F = np.asarray(FV[v - 1], float)
    ev, evec = np.linalg.eig(F.T)
    ev = np.real(ev)
    j = int(np.argmin(np.abs(ev - 1.0)))
    x = np.real(evec[:, j])
    return x / np.linalg.norm(x)


def main():
    print('=' * 112)
    print('_r91_axisid —— `n_inv` 与引擎三轴 (`NPF`, `a`, `w`) 的关系')
    print('=' * 112)
    print('  %-4s %-9s %-9s %-9s %-9s %-9s %-9s %s'
          % ('变体', '∠N,ninv', '∠a,ninv', '∠w,ninv', '∠(w×a),ninv',
             '∠N,a', '∠N,w', 'n·a'))
    best = {k: [] for k in ('a', 'w', 'wxa')}
    for v in range(1, NV + 1):
        n = npf(v)
        e0 = np.asarray(EPS0[v - 1], float)
        R = WS.LevelSetMulti._rank1_axes(e0, n)
        a = np.asarray(R[1], float); a /= np.linalg.norm(a)
        w = np.asarray(R[2], float); w /= np.linalg.norm(w)
        wxa = np.cross(w, a); wxa /= np.linalg.norm(wxa)
        ni = ninv_of(v)
        d_na = ang(n, ni)
        d_a = ang(a, ni)
        d_w = ang(w, ni)
        d_x = ang(wxa, ni)
        best['a'].append(d_a)
        best['w'].append(d_w)
        best['wxa'].append(d_x)
        print('  V%-3d %-9.2f %-9.2f %-9.2f %-9.2f %-9.2f %-9.2f %+.4f'
              % (v, d_na, d_a, d_w, d_x, ang(n, a), ang(n, w), float(n @ a)))
    print()
    for k, lab in (('a', '`a` 轴（长轴）'), ('w', '`w` 轴（宽度）'),
                   ('wxa', '`w × a`（引擎的另一种 n）')):
        arr = best[k]
        print('  `n_inv` vs %-24s  max %6.2f°  mean %6.2f°  （<2° 的变体 %d/12）'
              % (lab, max(arr), float(np.mean(arr)), sum(1 for x in arr if x < 2.0)))
    print()
    if min(max(best['a']), max(best['w']), max(best['wxa'])) < 2.0:
        print('  ⇒ ✅ **`n_inv` 就是引擎三轴中的另一根** ⇒ `NPF` 与 `n_inv` 不矛盾，')
        print('     只是"`npref` 到底指哪根轴"的口径问题（**不是 bug**）。')
    else:
        print('  ⇒ ⚠ `n_inv` **不是**引擎三轴中的任何一根（都 > 2°）⇒')
        print('     这两组轴是**不同的几何量**，需要判定哪一个才是"惯习面法向"。')
        print('     ⚠ 判定前**不得**下"哪张表错了"的结论（`_r89` 已经错过一次）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
