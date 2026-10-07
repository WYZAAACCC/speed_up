#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r94_invplane_direct.py —— **直接量"不变平面"的定义性质**（不再碰特征值）。

## 判据（定义式，无特征值退化问题）

平面 `P_u = {x : u·x = 0}` 是**不变平面** ⟺ `F` 把它映到自身 ⟺ 对 `P_u` 内所有 `x`，`F x ∈ P_u`。

数值化：取 `P_u` 的一组正交基 `(b1,b2)`，令 `B = [b1 b2]`（3×2），
    @@\\mathrm{res}(u)=\\left\\|u^{\\mathsf T}F B\\right\\|_2@@
则 `res(u) = 0` ⟺ `P_u` 是不变平面。**取 `res` 最小的那个 `u` 就是惯习面法向。**

## 为什么不再用特征值（`_r89→_r93` 的教训）

对**精确** IPS，`Fᵀu = u` 的解空间是**二维**的（整个惯习面）⇒ `np.linalg.eig` 返回的
是退化空间里的**任选一支**，拿它当"真值"去比 `NPF` **在方法上就没有意义**
（`_r93` 的正对照已证实：`p` 与 `d×p` **都**在空间里）。
真实的 `FV` 不是精确 IPS ⇒ 空间退化成 1 维 ⇒ 更要小心。
**`res(u)` 没有这个问题**：它是定义式的、对每个 `u` 单独成立。

## 正对照（`AGENTS.md §3.3-19`）

合成 IPS `F = I + 0.2·d pᵀ`：`res(p)` 必须 ≈ 0，`res(d)` 必须 ≫ 0。
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


def res(F, u):
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    # 平面 ⟂ u 的正交基
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    B = np.stack([b1, b2], 1)                     # (3,2)
    M = u @ (np.asarray(F, float) @ B)            # (2,) ·  → 用行向量算
    return float(np.linalg.norm(np.asarray(F, float) @ B - B @ (B.T @ (np.asarray(F, float) @ B)), 2))


def res2(F, u):
    """更直接：`max_{x∈P_u,|x|=1} ‖(F−I)x‖` = `‖(F−I)B‖₂`（因为 `P_u` 上 `Fx∈P_u` ⟺ `uᵀFB=0`）。

    两个量都给：`rA = ‖uᵀFB‖₂`（映到自身），`rB = ‖(F−I)B‖₂`（不动）。
    """
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    B = np.stack([b1, b2], 1)
    F = np.asarray(F, float)
    rA = float(np.linalg.norm(u @ (F @ B)))
    rB = float(np.linalg.norm((F - np.eye(3)) @ B, 2))
    return rA, rB


def main():
    print('=' * 112)
    print('_r94_invplane_direct —— 直接量不变平面：`rA = ‖uᵀFB‖`、`rB = ‖(F−I)B‖₂`')
    print('=' * 112)
    # ---- 正对照 ----
    p = np.array([0.0, 0.0, 1.0]); d = np.array([1.0, 0.0, 0.0])
    Fi = np.eye(3) + 0.2 * np.outer(d, p)
    a1, a2 = res2(Fi, p)
    b1, b2 = res2(Fi, d)
    print('  **正对照**（合成 IPS，`p` 是法向、`d` 是滑移方向）：')
    print('     `u = p`： rA = %.3e（应 ≈0）  rB = %.3e（应 ≈0）' % (a1, a2))
    print('     `u = d`： rA = %.3e（应 ≫0）  rB = %.3e（应 ≫0）' % (b1, b2))
    pos = (a1 < 1e-12 and a2 < 1e-12 and b1 > 0.1 and b2 > 0.1)
    print('     ⇒ 判据正对照 %s' % ('PASS（工具可信）' if pos else '**FAIL ⇒ 下面作废**'))
    print()
    # ---- 实测 ----
    print('  %-4s %-11s %-11s %-11s %-11s %-11s %s'
          % ('变体', 'rA(n*)', 'rA(a)', 'rA(w)', 'rB(n*)', 'rB(w)', 'argmin rB'))
    cn = cw = ca = 0
    for v in range(1, NV + 1):
        F = np.asarray(FV[v - 1], float)
        e = np.asarray(EPS0[v - 1], float)
        n = npf(v)
        R = WS.LevelSetMulti._rank1_axes(e, n)
        aa = np.asarray(R[1], float); aa /= np.linalg.norm(aa)
        w = np.asarray(R[2], float); w /= np.linalg.norm(w)
        rn = res2(F, n); ra = res2(F, aa); rw = res2(F, w)
        k = min((rn[1], 'n*'), (ra[1], 'a'), (rw[1], 'w'))[1]
        cn += int(k == 'n*'); ca += int(k == 'a'); cw += int(k == 'w')
        print('  V%-3d %-11.3e %-11.3e %-11.3e %-11.3e %-11.3e %s'
              % (v, rn[0], ra[0], rw[0], rn[1], rw[1],
                 k + ('  ⚠ 与 NPF 不符' if k != 'n*' else '  ✅ = NPF')))
    print()
    print('  ⇒ `rB` 最小的轴：n* %d/12、a %d/12、w %d/12' % (cn, ca, cw))
    print()
    if cn == 12:
        print('  ⇒ ✅ **`n*`（= `NPF`）就是不变平面法向** ⇒ 模型正确，')
        print('     `_r89`/`_r90`/`_r92` 的"不一致"**全部作废**（都是退化特征空间里的任选一支）。')
    elif cw == 12:
        print('  ⇒ ⚠⚠ **不变平面法向是 `w`，而不是模型当板条厚向用的 `n*`** ——')
        print('     这与 `_rank1_axes` 的 docstring（"n = 惯习面法向、w = 宽度方向"）**矛盾**。')
        print('     **这是物理层的疑似 P0，必须先与用户/专家确认再动代码**；')
        print('     ⚠ 但在下结论前必须再排除一次"我读错了 `_rank1_axes` 的哪一支"。')
    else:
        print('  ⇒ ⚠ 三根轴都不是 ⇒ 需另找（**不要下结论**）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
