#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r130b_floor.py —— `_r130` 的更正版：球面上搜 `min rB`，与体积地板比。

## `_r130` 错在哪

我手写的 9 个方向列表被 `np.linalg.norm(..., axis=1)[:, None]` 广播搞坏了，
12 个变体给出**同一个数** 8.742e-2 —— 那是**同一个方向**的读数，不是各变体的最小值。
⇒ 作废。

## 本脚本

用 **Fibonacci 球 20000 点 + 坐标下降精修**求 `min_u rB(u)`（`_r96` 已用过同法且过正对照），
再与**体积地板** `|tr ε|/3` 比。

* `min rB ≈ |tr ε|/3` ⇒ 存在**偏量意义下精确不变**的平面；
* 若该方向就是 `_rank1_axes` 的**另一个**分支（而代码没选它） ⇒ `§102` 成立。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402
from windowB_ti64_variants import variants                  # noqa: E402

_E, FV, _M = variants()


def rB(F, u):
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    return float(np.linalg.norm((np.asarray(F, float) - np.eye(3))
                                @ np.stack([b1, b2], 1), 2))


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    ga = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(ga) * np.sin(phi), np.sin(ga) * np.sin(phi),
                     np.cos(phi)], 1)


U = fib(20000)


def min_rB(F):
    A = np.asarray(F, float) - np.eye(3)
    t = np.where(np.abs(U[:, 0]) < 0.9, 1.0, 0.0)
    T = np.stack([t, 1 - t, np.zeros_like(t)], 1)
    B1 = np.cross(U, T); B1 /= np.linalg.norm(B1, axis=1, keepdims=True)
    B2 = np.cross(U, B1)
    g = ((B1 @ A.T) ** 2).sum(1) + ((B2 @ A.T) ** 2).sum(1)
    u = U[int(np.argmin(g))]
    best = rB(F, u)
    step = 0.05
    for _ in range(400):
        imp = False
        for k in range(3):
            for s in (+1.0, -1.0):
                v = u.copy(); v[k] += s * step; v /= np.linalg.norm(v)
                r = rB(F, v)
                if r < best - 1e-15:
                    best, u, imp = r, v, True
        if not imp:
            step *= 0.5
            if step < 1e-7:
                break
    return u, best


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(float(u @ v)), -1, 1))))


def main():
    print('=' * 104)
    print('_r130b —— `min_u rB(u)` vs 体积地板 `|tr ε|/3`')
    print('=' * 104)
    # 正对照
    p = np.array([0., 0, 1.]); d = np.array([1., 0, 0])
    Fips = np.eye(3) + 0.2 * np.outer(d, p)
    u0, r0 = min_rB(Fips)
    print('  **正对照**（精确 IPS，`tr=0`）：`min rB` = %.3e（应 0）、'
          '方向与 `p` 夹角 %.2f°（应 0）' % (r0, ang(u0, p)))
    Fvol = np.eye(3) - 0.01 * np.eye(3)
    u1, r1 = min_rB(Fvol)
    print('  **正对照**（纯体积）：`min rB` = %.6f（应 =|c|=0.010000）' % r1)
    print()
    print('  %-4s %-13s %-13s %-9s %-13s %-13s %s'
          % ('变体', 'min rB', '地板', '比值', '∠(argmin, n*)', '∠(argmin, a)',
             '判定'))
    for v in range(1, 13):
        F = np.asarray(FV[v - 1], float)
        e = np.asarray(EPS0[v - 1], float)
        fl = abs(float(np.trace(e))) / 3.0
        u, r = min_rB(F)
        n = np.asarray(NPF[v] if v in NPF else NPF[v - 1], float)
        R = WS.LevelSetMulti._rank1_axes(e, n)
        a = np.asarray(R[1], float)
        print('  V%-3d %-13.6e %-13.6e %-9.4f %-13.2f %-13.2f %s'
              % (v, r, fl, r / fl, ang(u, n), ang(u, a),
                 '✅ **= 地板**（偏量不变平面存在）' if abs(r / fl - 1) < 0.05
                 else '⚠ 高于地板 %.1f×' % (r / fl)))
    print()
    print('  ⇒ 若比值普遍 ≈1 ⇒ **每个变体都存在偏量意义下精确不变的面**，')
    print('     且 `argmin rB` 落在 `a` 上（`∠(·,a)` 小）而代码用的是 `n*`。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
