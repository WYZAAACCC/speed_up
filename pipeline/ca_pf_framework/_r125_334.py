#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r125_334.py —— **`§93` 的文献锚定裁决**：`NPF` 是不是 `{334}β` 惯习面？

## 为什么是这条路（`§93` 的收尾）

`§93` 用"平面 ⟂u 内向量不动"（`rB`）判出 `V1`/`V3`/`V8` 的 `n*`/`a` 标签疑似互换，
但**我没有裁定哪一个是板条厚向** —— 因为两支给的是**同一对向量、只差标签**，
而代码用**弹性能**（`argmin_normal`）选标签，两个解的弹性能只差 8.6%（分辨力不足）。

⇒ **需要一个不依赖弹性能、也不依赖 `_rank1_axes` 的外部锚**：
**`{334}β` 惯习面**（Ti-64 β→α′ 的文献惯习面之一；`_chk_habit5.py:23-24` 的 H-10 就是这条）。

## 判据

`H334` = `{433}` 型的 12 个等价极（`(4,3,3)` 的位置置换 × 符号组合，去重后 12 个）。
对每个变体算 `near(NPF[v]) = min_h ∠(NPF[v], h)`：**< 2° ⇒ `NPF` 就是 `{334}` 惯习面法向**。

**正对照（`AGENTS.md §3.3-19`）**：把一个已知的 `H334` 元素喂进去必须给 **0.00°**；
再喂一个随机方向必须给非零。没有这两条，下面的 `<2°` 可能只是"`H334` 覆盖了整个球面"。

## 与 `§93` 的关系

* 若 `near(NPF[v]) < 2°` **全部 12 个** ⇒ **模型用的 `NPF` 就是文献惯习面**
  ⇒ `V1`/`V3`/`V8` 的 `rB` 不一致**不是**"标签反了"，而是**我的 `rB` 判据在这三个变体上不适用**
  （`rB` 找的是"平面内不动的方向"，而 `F` **不是精确 IPS** ⇒ 两者的最优方向可以不同）。
  ⇒ **`§93` 的疑似 P0 撤销。**
* 若只有 9/12 满足、而 `a` 在另外 3 个上满足 ⇒ **标签确实反了**（P0 成立，需修引擎）。
* 若都不满足 ⇒ `NPF` 与 `{334}` 无关 ⇒ 这条锚**不适用**，另找（如 `{110}β`、或与母相的取向关系）。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

# `{4 3 3}` 型极（= `{334}` 的等价族），与 `_chk_habit5.py:51-60` 同一构造
H334 = []
for pos in range(3):
    for s1, s2 in itertools.product((+1, -1), repeat=2):
        v = [0.0, 0.0, 0.0]
        oth = [i for i in range(3) if i != pos]
        v[pos], v[oth[0]], v[oth[1]] = 4.0, 3.0 * s1, 3.0 * s2
        u = np.array(v)
        if not any(abs(u @ w) > 1 - 1e-9 for w in H334):
            H334.append(u / np.linalg.norm(u))
H334 = np.array(H334)


def near(u):
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    return float(min(np.degrees(np.arccos(np.clip(abs(float(u @ h)), -1, 1)))
                     for h in H334))


def npf(v):
    try:
        return np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        return np.asarray(NPF[v - 1], float)


def axes(v):
    e = np.asarray(EPS0[v - 1], float)
    R = WS.LevelSetMulti._rank1_axes(e, npf(v))
    return (npf(v) / np.linalg.norm(npf(v)),
            np.asarray(R[1], float) / np.linalg.norm(R[1]),
            np.asarray(R[2], float) / np.linalg.norm(R[2]))


def main():
    print('=' * 104)
    print('_r125 —— `NPF` vs `{334}β` 惯习面极（文献锚定裁决 `§93`）')
    print('=' * 104)
    print('  `H334` 元素个数 = %d（应 12）' % len(H334))
    # ---- 正对照 ----
    c1 = near(H334[0])
    rng = np.random.default_rng(0)
    c2 = min(near(rng.normal(size=3)) for _ in range(200))
    print('  **正对照**：`near(H334[0])` = %.4f°（应 0）  ;  '
          '200 个随机方向的 `near` 最小 = %.2f°（应 ≫0）' % (c1, c2))
    pos = c1 < 1e-6 and c2 > 2.0
    print('     ⇒ 判据正对照 %s' % ('PASS（H334 覆盖球面不密，判据有分辨力）'
                                    if pos else '**FAIL ⇒ 下面作废**'))
    print()
    print('  %-4s %-13s %-13s %-13s %s'
          % ('变体', 'near(n*)', 'near(a)', 'near(w)', '`n*` 是 {334} 吗'))
    nn = na = nw = 0
    rows = []
    for v in range(1, 13):
        n, a, w = axes(v)
        d1, d2, d3 = near(n), near(a), near(w)
        nn += int(d1 < 2.0)
        na += int(d2 < 2.0)
        nw += int(d3 < 2.0)
        rows.append((v, d1, d2, d3))
        print('  V%-3d %-13.2f %-13.2f %-13.2f %s'
              % (v, d1, d2, d3, '✅' if d1 < 2.0 else '❌'))
    print()
    print('  ⇒ `near < 2°` 的个数：`n*` **%d/12**、`a` **%d/12**、`w` **%d/12**'
          % (nn, na, nw))
    print()
    print('  ---- 裁决 ----')
    if nn == 12:
        print('  ⇒ ✅ **`NPF` 全部 12 个都是 `{334}β` 极** ⇒ 模型用的惯习面法向**与文献一致**。')
        print('     ⇒ `§93` 的"标签疑似互换"**撤销**：`rB` 判据在 `V1/V3/V8` 上给出另一个方向，')
        print('       是因为 `F` **不是精确 IPS**（`|λ−1| = 4.17e-4`）⇒ "平面内不动"的最优方向')
        print('       与"弹性能最小"的最优方向**可以不同**，两者都不是"错"。')
    elif na == 12 and nn == 0:
        print('  ⇒ ⚠⚠ **`a` 才是 `{334}` 极、`n*` 不是** ⇒ **`§93` 的 P0 成立**（标签确实反了）。')
        print('     ⇒ 需修引擎（`_rank1_axes` 的选支规则），**先与用户确认**。')
    elif nn + na == 12:
        print('  ⇒ ⚠ **12 个变体里有一部分 `n*`、一部分 `a` 落在 `{334}` 上** ⇒')
        print('     与 `§93` 的"9 个 `n*` / 3 个 `a`"对照：**若正好是 9/3 且分组一致** ⇒ P0 成立。')
    else:
        print('  ⇒ ⚠ 两条都不成立（`n*` %d/12、`a` %d/12）⇒ **这条锚不适用**，')
        print('     需要另找外部锚（`{110}β` 极、或与母相的取向关系）。' % (nn, na))
    return 0


if __name__ == '__main__':
    sys.exit(main())
