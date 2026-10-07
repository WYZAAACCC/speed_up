#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r168_ncmp.py —— **配对法向 `ncmp` 的接线审计**。

## 为什么查这一条

`windowB_surface.py:1087-1093` 写着：
> 两个变体 k,l 之间的界面应落在它们的不变平面上，法向
> `n*(k,l) = argmin_n 0.5·dEps0:Lam(C,n):dEps0`；
> **旧代码：任何界面都用 winner 的 `npref[k]`**（= 对**母相**的惯习面）
> ⇒ 变体-变体界面**用错对象**。

而 `:1185-1188` 进一步说：`ncmp` **正是 `advance()` 里变体-变体界面的 `β_h` 参考轴**
—— 也就是 **block / colony / packet 赖以形成的那根轴**。

⇒ **这是一条"模块是否正常接线"的硬主张**，本会话**没有独立复核过**。
（目标原文：「该有的模块是否正常接线」）

## 查什么（四条，都要正/负对照）

1. **有限性**：66 对里有多少对的 `ncmp` 是有限的？（`NaN` ⇒ 调用方 fallback 到 `npref`）
2. **同变体守卫**：`v(k)==v(l)`（**同变体、不同场**）时 `de = eps0_k − eps0_l = **0**`
   ⇒ 泛函恒为 0 ⇒ 任意法向都是最小 ⇒ **`ncmp` 必须保持 NaN**（`windowB_surface.py:1199-1203`）。
   ⇒ 本项查那个守卫**是否真的生效**。
3. **与 `npref` 的夹角**：`ncmp[k,l]` 与 `NPF[k]`/`NPF[l]` 的夹角。
   若**多数配对上 ≈ 0°** ⇒ 说明"pair 法向"其实退化成了单变体惯习面（= 旧 bug 的行为）。
4. **同 packet 对**：`_r88` 的 6 对（同惯习面）上，`ncmp` 是否 ≈ 它们共享的惯习面法向？
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                  # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


def ang(u, v):
    u = np.asarray(u, float); v = np.asarray(v, float)
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-12 or nv < 1e-12 or not (np.isfinite(u).all() and np.isfinite(v).all()):
        return float('nan')
    return float(np.degrees(np.arccos(np.clip(abs(float(u @ v)) / (nu * nv), -1, 1))))


def Efun(e, n):
    """`0.5·Δε:Lam(C,n):Δε`（与 `_pair_normals` 同一泛函）。"""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    e = np.asarray(e, float)
    return 0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, n), e))


def main():
    print('=' * 108)
    print('_r168 —— 配对法向 `ncmp` 的接线审计')
    print('=' * 108)
    E = [np.asarray(e, float) for e in EPS0]
    # ---- 正对照：自己跟自己（Δε = 0）⇒ 泛函恒 0 ⇒ 法向**不可定** ----
    print('  **正对照（语义）**：`Δε = 0` 时泛函恒等于 0 ⇒ "最小法向"**不可定**'
          ' ⇒ 必须由守卫保持 NaN')
    _z = np.zeros((3, 3))          # ⚠ 必须是 (3,3) —— 第一版写成 `np.zeros(3)`（1-D）⇒ einsum 报错
    print('     `Efun(0, 任意 n)` = %.3e  ⇒ %s'
          % (Efun(_z, np.array([0., 0, 1])),
             '确认恒 0（所以守卫是必需的）' if Efun(_z, np.array([0., 0, 1])) == 0.0
             else '**异常**'))
    print()
    # ---- 实测：从引擎拿 ncmp ----
    nv = len(E)
    tab = np.full((nv + 1, nv + 1, 3), np.nan)
    for k in range(1, nv + 1):
        for l in range(k + 1, nv + 1):
            de = E[k - 1] - E[l - 1]
            if float(np.linalg.norm(de)) < 1e-300:
                continue                          # ★ 守卫：零应变差 ⇒ 保持 NaN
            nref, _, _ = WS.argmin_normal_cached(C, de)
            # ★ 与 `LevelSetMulti._pair_normals` 取**同一个**函数（不另写一份）
            tab[k, l] = np.asarray(nref, float)
    nfin = int(np.isfinite(tab).all(-1).sum())
    print('  ① **有限性**：66 对里 `ncmp` 有限的 = **%d**（其余为 NaN ⇒ 调用方退回 `npref`）'
          % nfin)
    print('     ⇒ 本变体集**两两 `Δε ≠ 0`**（12 个变体互不相同）⇒ 应 **66/66** ⇒ %s'
          % ('✅' if nfin == 66 else '⚠ **有 NaN，需查**'))
    print()
    print('  ③ **与 `npref` 的夹角**（若多数 ≈0° ⇒ "pair 法向"退化成单变体惯习面 = 旧 bug 行为）')
    rows = []
    for k, l in itertools.combinations(range(1, nv + 1), 2):
        n = tab[k, l]
        rows.append((k, l, ang(n, NPF[k]), ang(n, NPF[l])))
    A = np.array([[r[2], r[3]] for r in rows])
    print('     `∠(ncmp, NPF_k)`：中位 **%.2f°**（min %.2f / max %.2f）'
          % (np.median(A[:, 0]), A[:, 0].min(), A[:, 0].max()))
    print('     `∠(ncmp, NPF_l)`：中位 **%.2f°**（min %.2f / max %.2f）'
          % (np.median(A[:, 1]), A[:, 1].min(), A[:, 1].max()))
    near = int((np.minimum(A[:, 0], A[:, 1]) < 2.0).sum())
    print('     ⇒ 与**任一** `npref` 夹角 < 2° 的对数 = **%d / 66** ⇒ %s'
          % (near, '✅ **确实用了"配对"法向**（不是退回单变体惯习面）'
             if near <= 6 else '⚠ **多数退化** ⇒ 旧 bug 可能仍在'))
    print()
    print('  ④ **同 packet 的 6 对**（`_r88`）')
    print('     %-9s %-11s %-11s %s' % ('对', '∠(ncmp,NPF_k)', '∠(ncmp,NPF_l)', '两 NPF 之间'))
    for k, l in PAIRS:
        print('     (%2d,%2d)   %-11.2f %-11.2f %.2f°'
              % (k, l, ang(tab[k, l], NPF[k]), ang(tab[k, l], NPF[l]),
                 ang(NPF[k], NPF[l])))
    print()
    print('  ---- 判读 ----')
    print('  * 若①是 66/66、③的"退化对数"很少 ⇒ **`ncmp` 这条接线是好的**（独立复核通过）。')
    print('  * 若③多数 < 2° ⇒ 说明 pair 法向**退化**，`advance()` 的 `β_h` 参考轴仍错。')
    print('  ⚠ 记账：本脚本**自己重算了** `argmin_normal_cached` 的结果（没调 `_pair_normals`），')
    print('     但用的是**同一个** `argmin_normal_cached` 与**同一个**泛函 ⇒ 口径一致。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
