#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r383_habit_vs_exp.py —— 项目3：模型算出的**惯习面法向** `npref` 与实验/晶体学值比。

## 模型的 `npref` 是什么
`windowB_surface.py` 的注释：`npref` 是"**弹性最省能法向**（惯习面）"，
由 `_pair_normals` / `NPF` 给出：@@\\arg\\min_n \\tfrac12 \\Delta\\varepsilon:\\Lambda(C,n):\\Delta\\varepsilon@@。
⚠ `R1_PAIR_CRITERION.md` 已记：**经典几何判据 `λ₂=0` 与模型判据 `E_min` 的划分零重叠（2.5e5 倍）**
⇒ 本脚本要把这件事**量化到角度**。

## 判据
* **H-1**：打印 12 个 `npref`，并给出它们与**低指数面**（{110}、{111}、{100}、{334}、{344}、{225}）
  的最小夹角 —— 看它是不是一个"晶体学上说得通"的面。
* **H-2**：`npref` 与 `n*`（c 轴 / {110} 面法向）的关系 —— 同一变体的两个轴是否重合。
* **H-3**：12 个 `npref` 的**去重后**个数（`BLOCK_SELFAC` §3.2 记 `NPF` 按 `|cos|` 分组
  得到 **12 组各 1 个**，而物理上应是 6 组）—— 复核这一条。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def low_index():
    """候选低指数面（立方 β 坐标系，h,k,l ≤ 5，取代表元）。"""
    out = {}
    for h in range(0, 6):
        for k in range(0, 6):
            for l in range(0, 6):
                if h == k == l == 0:
                    continue
                g = np.gcd(np.gcd(h, k), l)
                hh, kk, ll = h // g, k // g, l // g
                key = tuple(sorted((hh, kk, ll)))
                v = np.array([h, k, l], float)
                v = v / np.linalg.norm(v)
                if key not in out:
                    out[key] = v
    return out


def main():
    print('=' * 100)
    print('_r383 —— 模型的 `npref`（弹性最省能法向）vs 低指数面')
    print('=' * 100)
    from T16_verify_rve import NPF
    # ⚠ `NPF` 是 **dict**（{变体号: n*}），不是数组（第一版按数组写 ⇒ TypeError）
    if isinstance(NPF, dict):
        keys = sorted(NPF)
        A = np.asarray([np.asarray(NPF[k_], float).ravel() for k_ in keys], float)
    else:
        keys = list(range(1, np.shape(NPF)[0] + 1))
        A = np.asarray(NPF, float)
    if A.ndim != 2 or A.shape[1] != 3:
        print('  ⚠ NPF 形状异常: %s' % (A.shape,))
        return 2
    n = A / np.linalg.norm(A, axis=1, keepdims=True)
    print('  变体数 = %d；键 = %s' % (n.shape[0], keys[:14]))
    print()
    print('  ## **H-1** 12 个 `npref` 与低指数面')
    print('  %-4s %-30s %-12s %s' % ('变体', 'npref', '最接近的面', '夹角(deg)'))
    LI = low_index()
    best_all = []
    for v in range(n.shape[0]):
        nv = n[v]
        best = None
        for key, u in LI.items():
            for s in itertools.product([1, -1], repeat=0):
                pass
            # 只比 |cos|（面法向无符号）⇒ 用绝对值
            c = abs(float(nv @ u))
            ang = np.degrees(np.arccos(min(1.0, c)))
            if best is None or ang < best[0]:
                best = (ang, key)
        best_all.append(best)
        print('  %-4d %-30s {%d%d%d}%s %12.3f'
              % (v + 1, '(%+.4f %+.4f %+.4f)' % tuple(nv),
                 best[1][0], best[1][1], best[1][2],
                 '' if best[1][0] or best[1][1] or best[1][2] else ' ',
                 best[0]))
    angs = np.array([b[0] for b in best_all])
    print()
    print('  ⇒ 与最近低指数面的夹角：中位 **%.3f°**，最大 %.3f°' %
          (float(np.median(angs)), float(angs.max())))
    cnt = {}
    for b in best_all:
        cnt[b[1]] = cnt.get(b[1], 0) + 1
    print('  ⇒ 最近面的分布：%s' % cnt)
    print()
    print('  ## **H-3** 去重（按 |cos| ≥ 1−1e-6 判同）')
    reps = []
    for v in range(n.shape[0]):
        if not any(abs(abs(float(n[v] @ u)) - 1.0) < 1e-6 for u in reps):
            reps.append(n[v])
    print('     `npref` 去重后 = **%d** 组（`BLOCK_SELFAC` §3.2 记的是 **12 组各 1 个**）'
          % len(reps))
    print('     ⇒ %s' % ('✅ 与文档一致' if len(reps) == n.shape[0] else
                        '⚠ 与文档不一致（文档记 12 组）'))
    print()
    print('  ⚠ 记账：本脚本只用 `NPF` 与立方低指数面，**不涉及**求解器与算例；')
    print('     实验值的比对需要一手文献（项目 `BLOCK_LIT_REQUEST.md` 已列出待查项）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
