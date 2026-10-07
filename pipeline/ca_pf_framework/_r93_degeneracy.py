#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r93_degeneracy.py —— **收尾定案**：`Fᵀ` 的 `λ≈1` 特征空间是**二维的**（就是惯习面本身）。

## 把 `_r89 → _r92` 这条错链一次说清

`_r89`/`_r90`/`_r92` 三次尝试都在问"哪根轴是不变平面法向"，三次都得到
「`NPF`（= `n*`）不对，另一根才对」的**表面结论**。**三次都是判据的错。**

**真因（本脚本验证）**：对不变平面应变 `F = I + m·d pᵀ`（`d·p = 0`），

    @@F^{\\mathsf T}=I+m\\,p\\,d^{\\mathsf T}@@

* `Fᵀ p = p`（`p` = 惯习面法向）
* 且对**任意** `x ⟂ d`：`Fᵀ x = x + m p (d·x) = x` ⇒ 也是特征值 1

⇒ **`λ = 1` 的特征空间是二维的**（张成整个**惯习面**：`p` 与 `d × p`）。
⇒ `np.linalg.eig` 在这个退化空间里返回的是**任意一组基** —— 它给我 `w`（也在面内、
也在 `NPF` 的 90° 处）**纯属偶然**。
⇒ `_chk_habit5.py` 的 H-11 拿这个"任选一支"去和 `NPF` 比，**在方法上就没有意义**
（它必然 ~90°，且**与 `NPF` 对不对无关**）。

## 本脚本的判据（先做**正对照**，见 `AGENTS.md §3.3-19`）

1. `Fᵀ` 在 `λ≈1` 处的**特征空间维数**（按 `|λ−1|<1e-6` 数）应为 **2**；
2. 该二维空间内应**同时**含 `n*`（`NPF`）与 `w`（二者都 ⟂ `a` 在面内）；
3. 该空间应**不含** `a`（`a` 是滑移/长轴方向，`Fᵀ a = a + m p ≠ a`）；
4. **正对照**：直接用 IPS 形式合成一个 `F = I + m d pᵀ`（已知答案），
   判据必须报"特征空间维数 = 2、含 `p`、不含 `d`"。
   —— 没有这条，第 1~3 条本身也可能是在看一个恒真的量（教训 #19）。
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


def eigspace_dim(F, tol=1e-6):
    """`Fᵀ` 在 `λ=1` 附近的**特征空间维数**（用 Schur/秩判断，不靠 eig 的基）。"""
    A = np.asarray(F, float).T - np.eye(3)
    return 3 - int(np.linalg.matrix_rank(A, tol=tol))


def in_space(F, u, tol=1e-6):
    """`u` 是否落在 `Fᵀ` 的 `λ=1` 特征空间里（⟺ `(Fᵀ−I)u ≈ 0`）。"""
    A = np.asarray(F, float).T - np.eye(3)
    return float(np.linalg.norm(A @ (np.asarray(u, float)
                                     / np.linalg.norm(u)))) < tol


def main():
    print('=' * 112)
    print('_r93_degeneracy —— `Fᵀ` 的 `λ≈1` 特征空间维数（正对照先行）')
    print('=' * 112)

    # ---------- 正对照：合成一个已知的 IPS ----------
    p = np.array([0.0, 0.0, 1.0])          # 惯习面法向
    d = np.array([1.0, 0.0, 0.0])          # 滑移方向
    F_ips = np.eye(3) + 0.2 * np.outer(d, p)
    dim = eigspace_dim(F_ips)
    ok_p = in_space(F_ips, p)
    ok_dp = in_space(F_ips, np.cross(d, p))     # 面内与 d 垂直的方向，也应在空间里
    ok_d = in_space(F_ips, d)                   # 滑移方向**不**应在空间里
    print('  **正对照**（合成 IPS `F = I + 0.2·d pᵀ`，已知答案）：')
    print('     特征空间维数 = %d（应为 2）  ⇒ %s' % (dim, 'PASS' if dim == 2 else '**FAIL**'))
    print('     `p`（法向）  在空间里？ %s（应为 True）' % ok_p)
    print('     `d×p`（面内）在空间里？ %s（应为 True）' % ok_dp)
    print('     `d`（滑移）  在空间里？ %s（应为 **False**）' % ok_d)
    pos = (dim == 2 and ok_p and ok_dp and not ok_d)
    print('     ⇒ 判据**正对照 %s**' % ('PASS（工具可信）' if pos else '**FAIL ⇒ 工具不可信，下面作废**'))
    print()

    # ---------- 实测 ----------
    print('  %-4s %-10s %-12s %-12s %-12s %s'
          % ('变体', '维数', 'n* 在空间?', 'w 在空间?', 'a 在空间?', '判定'))
    nd2 = n_n = 0
    for v in range(1, NV + 1):
        F = np.asarray(FV[v - 1], float)
        e = np.asarray(EPS0[v - 1], float)
        n = npf(v)
        R = WS.LevelSetMulti._rank1_axes(e, n)
        a = np.asarray(R[1], float); a /= np.linalg.norm(a)
        w = np.asarray(R[2], float); w /= np.linalg.norm(w)
        dim = eigspace_dim(F, tol=1e-3)      # `|λ−1| = 4.2e-4` ⇒ 容差取 1e-3
        inn, inw, ina = in_space(F, n, 1e-3), in_space(F, w, 1e-3), in_space(F, a, 1e-3)
        nd2 += int(dim == 2)
        n_n += int(inn)
        print('  V%-3d %-10d %-12s %-12s %-12s %s'
              % (v, dim, inn, inw, ina,
                 '✅ 与 IPS 一致' if (dim == 2 and inn and inw and not ina)
                 else '⚠ 见下'))
    print()
    print('  ⇒ 维数 = 2 的变体：**%d/12**；`n*` 落在该空间里的：**%d/12**' % (nd2, n_n))
    print()
    if pos and nd2 == 12 and n_n == 12:
        print('  ⇒ ✅✅ **`n*`（= `NPF`）确实在 `Fᵀ` 的 `λ=1` 特征空间（惯习面）里** ——')
        print('     它与 `w` 都能在里面（空间是**二维**的），`eig` 返回哪一个纯属偶然。')
        print('     ⇒ **`NPF` 没有被否证**；`_r89`/`_r90`/`_r92` 的"不一致"结论')
        print('       **全部作废**（都是拿退化空间里的任选一支当"真值"去比）。')
        print('     ⇒ `_chk_habit5.py` 的 H-11 **在方法上没有意义**（同因），')
        print('       它的 H-9/H-10 FAIL 也只能说明"这个 F 不是精确 IPS"，')
        print('       **不能**说明 `NPF` 错。')
    else:
        print('  ⇒ ⚠ 与预期不符 ⇒ **不要下结论**，先查正对照与容差。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
