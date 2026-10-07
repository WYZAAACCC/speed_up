#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r96_habitmin.py —— **不依赖任何分支选择**：在整球上搜"最接近不变平面的法向"。

`rB(u) = ‖(F−I)B_u‖₂`（`B_u` = 平面 `⟂u` 的正交基）在单位球上取最小 ⇒ 几何法向。
用 Fibonacci 球 20000 点 + 局部精修（与 `argmin_normal` 同路线）。

## 为什么非要这么做

`_rank1_axes` 的两个候选解在数学上是**同一对向量、`n`/`a` 标签互换**
（`n⁻ ∝ a⁺`、`a⁻ ∝ n⁺`），而代码用**弹性能** `argmin_normal` 来选标号。
`_r95` 实测：`V1`、`V3`、`V8` 上代码标号与"平面内不动"判据相反。
⇒ 但"我的判据对不对"必须**独立于** `_rank1_axes` 再验一次。
**本脚本完全不碰 `_rank1_axes`**：只在球上搜 `argmin rB`，然后看它落在哪根轴上。

## 正对照（`AGENTS.md §3.3-19`）

合成 IPS：`argmin rB` 必须落在 `p` 上、且 `rB_min ≈ 0`；同时 `rB(d)` 必须 ≫ 0。
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


def fib_sphere(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    ga = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(ga) * np.sin(phi), np.sin(ga) * np.sin(phi),
                     np.cos(phi)], 1)


def basis_perp(u):
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    return np.stack([b1, b2], 1)


def rB(F, u):
    B = basis_perp(u)
    return float(np.linalg.norm((np.asarray(F, float) - np.eye(3)) @ B, 2))


def argmin_rB(F, npts=20000, seed=0):
    U = fib_sphere(npts)
    vals = np.empty(npts)
    A = np.asarray(F, float) - np.eye(3)
    # 向量化：对每个 u 造基并算 ‖A B‖₂ —— 直接用解析式避免逐点 SVD
    #   ‖A B‖₂² 的最大奇异值；这里用 Frobenius 作代理再精修（代理单调性足够选支）
    t = np.where(np.abs(U[:, 0]) < 0.9, 1.0, 0.0)
    T = np.stack([t, 1 - t, np.zeros_like(t)], 1)
    B1 = np.cross(U, T)
    B1 /= np.linalg.norm(B1, axis=1, keepdims=True)
    B2 = np.cross(U, B1)
    AB1 = B1 @ A.T
    AB2 = B2 @ A.T
    g = (AB1 * AB1).sum(1) + (AB2 * AB2).sum(1)          # ‖AB‖_F²
    i0 = int(np.argmin(g))
    u = U[i0]
    # 局部精修（坐标下降 + 归一化）
    step = 0.05
    best = rB(F, u)
    for _ in range(400):
        improved = False
        for k in range(3):
            for s in (+1.0, -1.0):
                v = u.copy()
                v[k] += s * step
                v /= np.linalg.norm(v)
                r = rB(F, v)
                if r < best - 1e-15:
                    best, u, improved = r, v, True
        if not improved:
            step *= 0.5
            if step < 1e-7:
                break
    return u, best


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(float(u @ v)), -1.0, 1.0))))


def main():
    print('=' * 108)
    print('_r96_habitmin —— 球上搜 `argmin rB`（**不依赖 `_rank1_axes`**）')
    print('=' * 108)
    # 正对照
    p = np.array([0.0, 0.0, 1.0]); d = np.array([1.0, 0.0, 0.0])
    Fi = np.eye(3) + 0.2 * np.outer(d, p)
    up, vp = argmin_rB(Fi)
    print('  **正对照**（合成 IPS）：argmin 与 `p` 夹角 = %.2f°（应 ≈0）  最小 rB = %.3e'
          % (ang(up, p), vp))
    print('     `rB(d)` = %.4f（应 ≫ 最小 rB）' % rB(Fi, d))
    pos = ang(up, p) < 0.5 and vp < 1e-10
    print('     ⇒ 正对照 %s' % ('PASS（工具可信）' if pos else '**FAIL ⇒ 下面作废**'))
    print()
    print('  %-4s %-12s %-11s %-11s %-11s %s'
          % ('变体', 'min rB', '∠(argmin,n*)', '∠(argmin,a)', '∠(argmin,w)', '落点'))
    near_n = near_a = 0
    for v in range(1, NV + 1):
        F = np.asarray(FV[v - 1], float)
        e = np.asarray(EPS0[v - 1], float)
        n = npf(v)
        R = WS.LevelSetMulti._rank1_axes(e, n)
        a = np.asarray(R[1], float); a /= np.linalg.norm(a)
        w = np.asarray(R[2], float); w /= np.linalg.norm(w)
        u, rmin = argmin_rB(F)
        an, aa, aw = ang(u, n), ang(u, a), ang(u, w)
        k = min((an, 'n*'), (aa, 'a'), (aw, 'w'))[1]
        near_n += int(k == 'n*')
        near_a += int(k == 'a')
        print('  V%-3d %-12.3e %-11.2f %-11.2f %-11.2f %s%s'
              % (v, rmin, an, aa, aw, k,
                 '  ✅ 与 NPF 一致' if k == 'n*' else '  ⚠ **与 NPF 不一致**'))
    print()
    print('  ⇒ `argmin rB` 落在 `n*` 上的变体：**%d/12**；落在 `a` 上的：**%d/12**'
          % (near_n, near_a))
    print()
    print('  ⚠ **无论如何都不在本脚本下结论**：`n*`/`a` 是同一对向量、只差标签，')
    print('     "哪个才是板条厚向"要看 `β_h` 压制的是哪一个，以及它与文献惯习面')
    print('     `{334}β`/`{110}β` 的对应 —— 这需要与用户/专家确认。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
