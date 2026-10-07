#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r163_g3matrix.py —— **66 对的"共格性"矩阵**（为 F2 面能的"配对依赖"提供物理输入）。

## 背景：框架的**具体缺口**（`§112/§121` 定位）

`windowB_lath.py:23-25` 写得很清楚：

| 类别 | 定义 | γ | 状态 |
|---|---|---|---|
| F1 | 恰一侧是母相 | `γ₁(n)` | **不动**（退回 `gamma0` 标量） |
| **F2** | `v(k) ≠ v(l)`（**异变体**） | `γ₂(n)` | **不动**（退回 **`gamma0` 标量**） |
| F3 | `v(k) = v(l) ≠ 0`（同变体） | `γ_RS(θ_kl)` | 本模块新增 ✅ |

⇒ **F2 完全没有"配对依赖"** —— V1/V3 界面的能量与 V1/V5 **一模一样**。
⇒ 这就是 `§112` 测到的"**生长竞争通道没有自协调机制**"的直接原因：
**界面能对"哪两个变体贴在一起"不敏感**，动力学**无从选择**。

## 本脚本给什么

对全部 **66 对**算两个**互相独立**的配对量：

1. **`g3(v,w)`（共格性 / 存在不变平面）** —— 仓库**已有**的正确判据
   （`_r1_pairgeo2.py:10-27` 的推导）：
   @@\Delta\boldsymbol\varepsilon=\mathrm{sym}(a\otimes n)\iff\Delta\varepsilon
   的特征值里有两个等大反号@@
   ⇒ @@g_3=\min_{i<j}|\lambda_i+\lambda_j|/\|\Delta\varepsilon\|_F@@，
   **`g3 = 0` ⟺ 存在不变平面 ⟺ 界面共格**（低能）。
2. **`r_pair(v,w)`（抵消 / 自协调）** —— `_r78` 用的
   @@\|E_v+E_w\|/(\|E_v\|+\|E_w\|)@@，`0` = 完全抵消。

**为什么要两个**：它们**不是同一个量** ——
`g3` 说的是"**能不能接上**"（共格），`r_pair` 说的是"**剪切抵不抵消**"（自协调）。
⇒ **必须先量它们的相关性与分歧**，才能决定 F2 面能该挂在哪一个上。

## 预登记判据

* 若 `g3 = 0` 的恰好是 `_r88` 那 **6 对**（同惯习面/packet）⇒ **与 `§94` 的结构自洽**；
* 若两量**强相关** ⇒ 一个参数化就够；
* 若**弱相关** ⇒ **这是一个物理选择**（要问用户/专家），本脚本不裁定。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from T16_verify_rve import EPS0, NPF                        # noqa: E402

E = [np.asarray(e, float) for e in EPS0]
DEV = [e - np.trace(e) / 3.0 * np.eye(3) for e in E]
SCALE = float(np.mean([np.linalg.norm(d) for d in DEV]))
# `_r88` 用**纯组合**定出的唯一配对（64 个自协调六元组 ↔ 每对一个）
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


def g3(v, w):
    """`min_{i<j}|λi+λj| / ‖Δε‖_F`；`0` ⟺ 存在不变平面（共格）。"""
    d = E[v - 1] - E[w - 1]
    n = float(np.linalg.norm(d))
    if n < 1e-300:
        return 0.0
    lam = np.linalg.eigvalsh(d)
    m = min(abs(lam[i] + lam[j]) for i, j in itertools.combinations(range(3), 2))
    return float(m / n)


def rpair(v, w):
    a, b = DEV[v - 1], DEV[w - 1]
    return float(np.linalg.norm(a + b) / (np.linalg.norm(a) + np.linalg.norm(b)))


def main():
    print('=' * 112)
    print('_r163 —— 66 对的共格性 `g3` 与抵消性 `r_pair`')
    print('=' * 112)
    # ---- 正对照：同变体 ⇒ Δε = 0 ⇒ g3 = 0（"自己跟自己"当然共格）----
    print('  **正对照**：`g3(V1,V1)` = %.3e（应 0）;  `r_pair(V1,V1)` = %.4f（应 1）'
          % (g3(1, 1), rpair(1, 1)))
    # ---- 负对照：一个已知不共格的（`_r1_pairrank` 说"真实 Burgers 变体对都不是精确 rank-1"）----
    print()
    print('  %-9s %-12s %-12s %s' % ('对', 'g3', 'r_pair', '备注'))
    rows = []
    for v, w in itertools.combinations(range(1, 13), 2):
        a, b = g3(v, w), rpair(v, w)
        rows.append((v, w, a, b))
        note = ''
        if (v, w) in PAIRS:
            note = '★ **`_r88` 的 6 对之一（同惯习面）**'
        print('  (%2d,%2d)   %-12.4f %-12.4f %s' % (v, w, a, b, note))
    print()
    # ---- 统计 ----
    G = np.array([x[2] for x in rows])
    R = np.array([x[3] for x in rows])
    print('  ---- 统计 ----')
    print('     `g3`：min %.4f  max %.4f  **= 0（<1e-9）的对数 %d/66**'
          % (G.min(), G.max(), int((G < 1e-9).sum())))
    print('     `r_pair`：min %.4f  max %.4f' % (R.min(), R.max()))
    c = float(np.corrcoef(G, R)[0, 1])
    print('     **两者相关系数 = %+.4f**' % c)
    print()
    # ---- `_r88` 的 6 对在 g3 上的表现 ----
    print('  ---- `_r88` 的 6 对（同惯习面）在 `g3` 上的位置 ----')
    gp = [g3(v, w) for v, w in PAIRS]
    rp = [rpair(v, w) for v, w in PAIRS]
    print('     `g3`     = %s' % ['%.4f' % x for x in gp])
    print('     `r_pair` = %s' % ['%.4f' % x for x in rp])
    print('     ⇒ 这 6 对的 `g3` 排名（越小越共格）：%s'
          % sorted(range(6), key=lambda i: gp[i]))
    print('     ⇒ 全库 `g3` 最小的 6 对是：%s'
          % ['(%d,%d)' % (x[0], x[1]) for x in sorted(rows, key=lambda t: t[2])[:6]])
    print()
    # ---- 第三个候选量：失配 ‖Δε‖_F（"共格但剪切大"仍要付能量）----
    print('  ---- 第三个候选：**失配大小** `‖Δε‖_F / scale`（共格也可能"剪切大"）----')
    M = []
    for v, w in itertools.combinations(range(1, 13), 2):
        d = E[v - 1] - E[w - 1]
        M.append(float(np.linalg.norm(d)) / SCALE)
    M = np.array(M)
    print('     min %.4f  max %.4f  中位 %.4f' % (M.min(), M.max(), np.median(M)))
    mp = [float(np.linalg.norm(E[v - 1] - E[w - 1])) / SCALE for v, w in PAIRS]
    print('     **`_r88` 的 6 对**：%s' % ['%.4f' % x for x in mp])
    print('     ⇒ 这 6 对在 66 对里的排位（升序）：%s'
          % sorted(range(66), key=lambda i: M[i]).index(0))
    print('     与 `g3` 的相关 = %+.4f；与 `r_pair` 的相关 = %+.4f'
          % (float(np.corrcoef(G, M)[0, 1]), float(np.corrcoef(R, M)[0, 1])))
    print()
    print('  ---- 判读 ----')
    if (G < 1e-9).sum() == 6 and set(
            (v, w) for v, w in itertools.combinations(range(1, 13), 2)
            if g3(v, w) < 1e-9) == set(PAIRS):
        print('  ⇒ ✅ **`g3 = 0` 的恰好就是 `_r88` 那 6 对** ⇒ 与 `§94` 的组合结构**自洽**')
        print('     ⇒ **F2 面能可以挂在 `g3` 上**，物理上就是"同 packet 的界面共格 ⇒ 低能"。')
    else:
        print('  ⇒ ⚠ `g3 = 0` 的集合与 `_r88` 的 6 对**不一致** ⇒ 需先弄清差异再动 F2。')
    print()
    print('  ⇒ 相关性 %+.4f ⇒ %s' % (c,
          '两量强相关（β 由 `g3` 或 `r_pair` 参数化差别不大）' if abs(c) > 0.8
          else '**两量弱相关** ⇒ "F2 面能挂哪个"是一个**物理选择**，需用户/专家裁定'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
