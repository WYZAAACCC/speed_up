#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r95_branch.py —— **收尾**：`V1/V3/V8` 的 `n*`/`a` 标签是否反了？以及后果是什么。

## 已知（`_r94`，正对照 PASS）

判据 `rB(u) = ‖(F−I)B_u‖₂`（`B_u` = 平面 `⟂u` 的正交基）
—— `rB = 0` ⟺ 该平面内向量**不动** ⟺ `u` 是**惯习面法向**。
正对照（合成 IPS）：`rB(p)=0`、`rB(d)=0.2·‖·‖` ⇒ 工具可信。

**实测**：`rB(n*) ≈ 8.4e-3`（9/12 变体，小）；但 **`V1`、`V3`、`V8`** 上
`rB(n*) ≈ 1.90e-1` 而 `rB(a) ≈ 8.4e-3` ⇒ **这三个变体的 `n*`/`a` 标签像是反的**。

## 为什么这**不一定**是 bug（先想清楚再判）

`_rank1_axes` 的两个候选解在数学上是
    `n⁺ = e1 + r·e3`、`a⁺ ∝ μ1 e1 − √(−μ1μ3) e3`，且 **`n⁻ ∝ a⁺`、`a⁻ ∝ n⁺`**
⇒ **两支给出的是同一对向量，只是 `n`/`a` 的**标签**互换**。
⇒ "哪个叫 n" 是一个**标号选择**；代码用 `nref = argmin_normal(C, eps)`（**弹性能**）选。
⇒ 若三个变体上弹性能选出的标号与"几何不变平面"相反，后果是：
   **那三个变体的板条厚度方向（=`n*`）落在剪切方向 `a` 上** —— 形态学会反 90°。

## 本脚本查什么

1. **配对自洽**：`V1&V2`（`_r88` 证明共享惯习面）⇒ 应有 `a₁ ≈ ±n*₂` 或 `n*₁ ≈ ±n*₂`。
   若 `a₁ ≈ ±n*₂` 而 `n*₁ ≉ ±n*₂`，说明"每对里恰好一个被反标"，**而这对仍共享平面**
   ⇒ 组织学结论（哪些变体共享惯习面）**不受影响**，受影响的只是**单变体的板条取向**。
2. **12 个变体逐个**：把"几何正确的标号"选出来，看它与代码标号差几个。
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
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


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


def axes(v):
    e = np.asarray(EPS0[v - 1], float)
    R = WS.LevelSetMulti._rank1_axes(e, npf(v))
    a = np.asarray(R[1], float); a /= np.linalg.norm(a)
    w = np.asarray(R[2], float); w /= np.linalg.norm(w)
    return npf(v), a, w


def rB(F, u):
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    B = np.stack([b1, b2], 1)
    return float(np.linalg.norm((np.asarray(F, float) - np.eye(3)) @ B, 2))


def main():
    print('=' * 108)
    print('_r95_branch —— `n*`/`a` 标号：逐变体 + 配对自洽')
    print('=' * 108)
    print('  %-4s %-12s %-12s %-11s %s'
          % ('变体', 'rB(NPF)', 'rB(a)', '几何正确的标号', '与代码标号一致？'))
    bad = []
    for v in range(1, NV + 1):
        F = np.asarray(FV[v - 1], float)
        n, a, _w = axes(v)
        rn, ra = rB(F, n), rB(F, a)
        k = 'n*' if rn <= ra else 'a'
        if k == 'a':
            bad.append(v)
        print('  V%-3d %-12.4e %-12.4e %-11s %s'
              % (v, rn, ra, k, '✅' if k == 'n*' else '⚠ **反了**'))
    print()
    print('  ⇒ 代码标号与几何不一致的变体：**%s**' % (bad if bad else '无'))
    print()
    print('  ---- 配对自洽（`_r88` 证明这 6 对共享惯习面）----')
    print('  %-10s %-13s %-13s %-13s %s'
          % ('对', '∠(n*₁,n*₂)', '∠(n*₁,a₂)', '∠(a₁,n*₂)', '结论'))
    for i, j in PAIRS:
        n1, a1, _ = axes(i)
        n2, a2, _ = axes(j)
        d_nn = ang(n1, n2)
        d_na = ang(n1, a2)
        d_an = ang(a1, n2)
        best = min(d_nn, d_na, d_an)
        which = {d_nn: 'n*₁~n*₂', d_na: 'n*₁~a₂', d_an: 'a₁~n*₂'}[best]
        print('  (%2d,%2d)    %-13.2f %-13.2f %-13.2f %s（%.2f°）'
              % (i, j, d_nn, d_na, d_an, which, best))
    print()
    # 全 66 对里有多少对共享平面（用"两变体的四根轴任意配对"最好的一档）
    cnt = 0
    for i in range(1, 13):
        for j in range(i + 1, 13):
            n1, a1, _ = axes(i)
            n2, a2, _ = axes(j)
            if min(ang(n1, n2), ang(n1, a2), ang(a1, n2)) < 1.0:
                cnt += 1
    print('  ⇒ 全 66 对里"某一对轴近平行（<1°）"的对数 = **%d**（`_r88` 说应为 6）' % cnt)
    return 0


if __name__ == '__main__':
    sys.exit(main())
