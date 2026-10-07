#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r130_floor.py —— 确认 `rB(分支1)` 就是**体积项地板**（把 §102 钉死）。

`_r129` 实测 `rB(分支1) = 8.3686e-03`，而 `|tr ε|/3 = 2.5168e-02/3 = 8.3893e-03`。

**若两者相等** ⇒ 分支 1 的平面**在偏量意义下精确不变**（`(F−I)B` 只剩各向同性的体积项）
⇒ **`rB` 判据确实识别出了真正的不变平面**，而代码（弹性能选支）选的是**另一个**分支。

**正/负对照**：
* 纯体积应变 `ε = c·I` ⇒ `rB(u)` 应对**任意** `u` 都等于 `|c|`（地板是各向同性的）；
* 精确 IPS ⇒ `rB(p) = 0`（**没有**地板，因为 `tr = 0`）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from T16_verify_rve import EPS0                             # noqa: E402


def rB(F, u):
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    return float(np.linalg.norm((np.asarray(F, float) - np.eye(3))
                                @ np.stack([b1, b2], 1), 2))


def main():
    print('=' * 100)
    print('_r130 —— `rB` 的体积项地板')
    print('=' * 100)
    # 正对照 1：纯体积应变 ⇒ 地板各向同性
    c = -0.01
    Fi = np.eye(3) + c * np.eye(3)
    vals = [rB(Fi, u) for u in (np.array([1., 0, 0]), np.array([0, 1., 0]),
                                np.array([0, 0, 1.]),
                                np.array([1., 1, 1]) / np.sqrt(3))]
    print('  **正对照 1（纯体积）**：`rB` 对 4 个方向 = %s（应**全等于** |c|=%.4f）'
          % (['%.6f' % x for x in vals], abs(c)))
    print('     ⇒ %s' % ('PASS：地板是各向同性的' if max(vals) - min(vals) < 1e-12
                          and abs(max(vals) - abs(c)) < 1e-12 else 'FAIL'))
    # 正对照 2：精确 IPS ⇒ 法向上 rB = 0
    p = np.array([0., 0, 1.]); d = np.array([1., 0, 0])
    Fips = np.eye(3) + 0.2 * np.outer(d, p)
    print('  **正对照 2（精确 IPS，tr=0）**：`rB(p)` = %.3e（应 0 —— **没有**地板）'
          % rB(Fips, p))
    print()
    # 实测
    print('  %-4s %-14s %-14s %-12s %s'
          % ('变体', 'rB(分支1)', '|tr ε|/3', '比值', '判定'))
    for v in range(1, 13):
        e = np.asarray(EPS0[v - 1], float)
        F = np.eye(3) + e
        fl = abs(float(np.trace(e))) / 3.0
        # 分支 1 的 n 用 `_r129` 同法（取 rB 较小的那个候选）——这里直接搜球面确认地板
        best = min(rB(F, u) for u in
                   np.array([[1., 0, 0], [0, 1., 0], [0, 0, 1.],
                             [1., 1, 0], [1., 0, 1], [0, 1., 1],
                             [1., 1, 1], [1., -1, 0], [1., 0, -1]]) /
                   np.linalg.norm([[1., 0, 0], [0, 1., 0], [0, 0., 1],
                                   [1., 1, 0], [1., 0, 1], [0, 1., 1],
                                   [1., 1, 1], [1., -1, 0], [1., 0, -1]], axis=1)[:, None])
        print('  V%-3d %-14.6e %-14.6e %-12.4f %s'
              % (v, best, fl, best / fl,
                 '✅ **= 体积地板**（偏量部分≈0 ⇒ 真不变平面）'
                 if abs(best / fl - 1) < 0.05 else '⚠ 高于地板'))
    print()
    print('  ⇒ 若每个变体都能找到方向使 `rB = |tr ε|/3`（比值 ≈1）⇒')
    print('     **存在一个"偏量意义下精确不变"的平面**，而代码的选支（弹性能）**没选它**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
