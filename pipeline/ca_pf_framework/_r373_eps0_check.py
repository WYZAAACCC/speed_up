#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r373_eps0_check.py —— ★★ 框架完备性检查：模型的 `ε⁰` 是不是**不变平面应变（IPS）**？

## 为什么这是"框架是否完善"的一条硬检查

马氏体相变的晶体学理论（WLR / Bowles–Mackenzie）要求：**单变体的转变应变是
不变平面应变**（invariant plane strain, IPS）——
即 @@\\varepsilon^0=\\tfrac12(a\\otimes n+n\\otimes a)@@（rank-1 对称），
等价于"存在一个**不畸变、不旋转**的惯习面 `n`"。

**若模型给的 `ε⁰` 不是 IPS**（例如只取了点阵畸变、漏掉点阵不变剪切 LIS），
那么 `ncmp`（`_pair_normals` 用弹性最小化找的"不变平面"）与
`npref`（惯习面法向）就只是**近似**，而"自协调"的晶体学判据也会跟着偏。

## 判据（**先写死**）

* **P-0 口径自证**：把 `ε⁰ = ½(a⊗n + n⊗a)` 的**解析**构造喂进同一个 `rank1_residual`
  ⇒ 必须给出 **≈ 0**（否则我的最小化写错了）。
* **P-1 每个变体 vs 母相**：@@R_v=\\min\\|\\varepsilon^0_v-\\mathrm{sym}(a\\otimes n)\\|@@
  * `R_v ≲ 1e-3` ⇒ **是 IPS** ✓；
  * `R_v` 与 @@\\|\\varepsilon^0_v\\|@@ 同量级 ⇒ **不是 IPS** ⇒ 记账。
* **P-2 体积**：`det(I+ε⁰)` 与 `tr(ε⁰)` —— IPS 的 `det=1`、一阶 `tr≈0`。
* **P-3 变体对**：`R(v,w)` 的分布（自协调对应当小）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def fib_sphere(m):
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def rank1_residual(D, dirs, refine=250):
    """@@\\min_{n,a}\\|D-\\mathrm{sym}(a\\otimes n)\\|_F@@。

    ⚠ **必须做局部细化**：只在 300–400 个球面方向上取最小，
    真解 `n*` 一般**落在网格点之间** ⇒ 残差被高估
    （实测：解析 IPS 在纯网格搜索下相对残差 **6.33e-2**，不是 0 —— 这是 P-0 抓出来的）。
    做法：网格定位后，用**自适应步长的随机模式搜索**细化到 ~1e-6。
    """
    d = D.ravel()

    def ev(n):
        A = np.zeros((9, 3))
        for k in range(3):
            e = np.zeros(3)
            e[k] = 1.0
            A[:, k] = (0.5 * (np.outer(e, n) + np.outer(n, e))).ravel()
        c, *_ = np.linalg.lstsq(A, d, rcond=None)
        r = d - A @ c
        return float(r @ r)

    bv, bn = np.inf, None
    for n in dirs:
        v = ev(n)
        if v < bv:
            bv, bn = v, n
    n = np.array(bn, float)
    rng = np.random.default_rng(3)
    step = 0.15
    for _ in range(refine):
        u = rng.standard_normal(3)
        u /= np.linalg.norm(u)
        cand = n + step * u
        cand /= np.linalg.norm(cand)
        v = ev(cand)
        if v < bv:
            bv, n = v, cand
        else:
            step *= 0.94
    return float(np.sqrt(max(bv, 0.0)))


def main():
    print('=' * 100)
    print('_r373 —— `ε⁰` 是不是不变平面应变（IPS）？')
    print('=' * 100)
    from T16_verify_rve import EPS0
    E = np.asarray([np.asarray(e, float) for e in EPS0])
    nv = E.shape[0]
    dirs = fib_sphere(400)

    # ---- P-0 口径自证 ----
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(6):
        a = rng.standard_normal(3)
        n = rng.standard_normal(3)
        n /= np.linalg.norm(n)
        D = 0.5 * (np.outer(a, n) + np.outer(n, a))
        worst = max(worst, rank1_residual(D, dirs) / max(np.linalg.norm(D), 1e-30))
    print('  **P-0 口径自证**：解析 IPS 的相对残差最大 = **%.3e** %s'
          % (worst, '✅' if worst < 1e-3 else '❌ 最小化写错了 ⇒ 作废'))
    if worst >= 1e-3:
        return 2

    # ---- P-1/P-2 逐变体 ----
    print()
    print('  ## **P-1/P-2 逐变体 vs 母相**（`R_v` 小 ⇒ 是 IPS）')
    print('  %-4s %14s %14s %12s %12s %10s' %
          ('变体', '‖ε⁰‖_F', 'R_v', 'R_v/‖ε⁰‖', 'tr(ε⁰)', 'det(I+ε⁰)'))
    Rs, Ns = [], []
    for v in range(nv):
        D = E[v]
        nrm = float(np.linalg.norm(D))
        R = rank1_residual(D, dirs)
        Rs.append(R)
        Ns.append(nrm)
        print('  %-4d %14.6f %14.6f %12.4f %12.6f %10.6f'
              % (v + 1, nrm, R, R / max(nrm, 1e-30),
                 float(np.trace(D)), float(np.linalg.det(np.eye(3) + D))))
    Rs = np.asarray(Rs)
    Ns = np.asarray(Ns)
    print()
    print('  ⇒ `‖ε⁰‖` 中位 %.6f；`R_v` 中位 **%.6f**；`R_v/‖ε⁰‖` 中位 **%.4f**'
          % (float(np.median(Ns)), float(np.median(Rs)),
             float(np.median(Rs / Ns))))
    frac = float(np.median(Rs / Ns))
    if frac < 0.05:
        print('     ⇒ ✅ **各变体的转变应变基本是 IPS**（相对残差 < 5%%）')
    elif frac < 0.25:
        print('     ⇒ ⚠ **近似 IPS**（相对残差 %.1f%%）—— 记账：`ncmp`/`npref` 只是近似' % (100 * frac))
    else:
        print('     ⇒ ❌ **明显不是 IPS**（相对残差 %.1f%%）⇒ '
              '**框架层记账**：`ncmp`/`npref` 的晶体学含义要重新审视' % (100 * frac))

    # ---- P-3 变体对 ----
    print()
    print('  ## **P-3 变体对** `R(v,w)`（自协调对应当小）')
    R2 = []
    for i in range(nv):
        for j in range(i + 1, nv):
            R2.append((rank1_residual(E[i] - E[j], dirs), i + 1, j + 1))
    R2.sort()
    print('     最小 5 对：%s' % ['(%d,%d):%.5f' % (a, b, c) for c, a, b in R2[:5]])
    print('     最大 5 对：%s' % ['(%d,%d):%.5f' % (a, b, c) for c, a, b in R2[-5:]])
    vals = np.array([c for c, _, _ in R2])
    print('     66 对：中位 %.6f，范围 %.6f … %.6f'
          % (float(np.median(vals)), float(vals.min()), float(vals.max())))
    print()
    print('  ⚠ 记账：`EPS0` 取自 `T16_verify_rve`（与 `_r195`/`§164`/`§173` 同源）。')
    print('     本检查只用 `ε⁰` 本身，**不涉及**求解器与算例。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
