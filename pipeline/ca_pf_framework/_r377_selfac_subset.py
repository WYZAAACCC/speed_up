#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r377_selfac_subset.py —— ★★★ **先查一个可能推翻诊断的问题**：
我们**播种的那 6 个变体**，本身就够不够自协调？

## 为什么必须查

`_r376` 算出的可动下界 0.0003 是用**全部 12 个变体**、并且最优解落在
变体集 **{2,3,5,8,9,11}** 上。
而算例播种的是 `--laths 1,1,2,2,3,3,4,4,7,7,8,8` ⇒ 变体集是 **{1,2,3,4,7,8}**。

**这两个集合不一样。**
⇒ 如果"只用 {1,2,3,4,7,8} 能做到的最好 `r`"本来就很大（比如 0.5），
那么实测 0.6167 **几乎已经是这个变体集的上限** ——
**"没自协调"就不是动力学的问题，而是我们压根没给系统一个能自协调的变体组合。**
⇒ 那整个诊断要改写（属于**播种/盒子设计**问题，不是物理问题）。

## 判据（**先写死**）

* **S-0 自证**：全 12 变体等分的 `r` 必须 ≈ 0（`BLOCK_SELFAC.md` P-1 独立测到 3.3e-16）。
* **S-1 ★**：播种集 `{1,2,3,4,7,8}` 上单纯形最小化的 `r_min(seeded)`。
* **S-2**：全部 12 个变体里，**最好的 6 变体子集**是谁、它的 `r_min` 是多少。
* **S-3 判读**：
  * 若 `r_min(seeded)` 与实测 0.6167 同量级 ⇒ **"没自协调"首先是播种集选错了**；
  * 若 `r_min(seeded)` 明显更小（≲0.1）⇒ 播种集不是瓶颈，问题在动力学/时长/参数。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def ev_set():
    from T16_verify_rve import EPS0
    E = []
    for e in EPS0:
        A = np.asarray(e, float)
        E.append(A - np.trace(A) / 3.0 * np.eye(3))
    return np.asarray(E)


def r_of(E, f, scale):
    acc = np.tensordot(np.asarray(f, float), E, axes=(0, 0))
    return float(np.sqrt(np.sum(acc ** 2)) / (scale + 1e-300))


def subset_min(E, idx, iters=3000):
    """在**给定子集**的单纯形上最小化 `r`（Frank–Wolfe）。"""
    scale = float(np.mean([np.sqrt(np.sum(e ** 2)) for e in E]))
    Es = E[list(idx)]
    n = len(idx)
    f = np.full(n, 1.0 / n)
    for t in range(1, iters + 1):
        acc = np.tensordot(f, Es, axes=(0, 0))
        dots = np.tensordot(Es, acc, axes=((1, 2), (0, 1)))
        s = np.zeros(n)
        s[int(np.argmin(dots))] = 1.0
        g = 2.0 / (t + 2.0)
        f = (1 - g) * f + g * s
    return r_of(Es, f, scale), f


def main():
    print('=' * 96)
    print('_r377 —— 播种的那 6 个变体，本身够不够自协调？')
    print('=' * 96)
    E = ev_set()
    n = E.shape[0]
    scale = float(np.mean([np.sqrt(np.sum(e ** 2)) for e in E]))

    # S-0 自证
    f12 = np.full(n, 1.0 / n)
    print('  **S-0 自证**：全 %d 变体等分 ⇒ `r` = **%.3e** %s'
          % (n, r_of(E, f12, scale), '✅' if r_of(E, f12, scale) < 1e-12 else '❌'))
    allidx = tuple(range(n))
    rmin_all, fall = subset_min(E, allidx)
    print('  全 12 变体的可动下界 ⇒ `r` = **%.6f**；取到它的变体 = %s'
          % (rmin_all,
             {int(v + 1): round(float(fall[v]), 4) for v in np.argsort(-fall)[:6]
              if fall[v] > 1e-3}))

    # S-1 播种集
    seeded = (0, 1, 2, 3, 6, 7)          # 1-based {1,2,3,4,7,8} → 0-based
    rmin_s, fs = subset_min(E, seeded)
    print()
    print('  ## **S-1 播种集 `{1,2,3,4,7,8}`**（`--laths 1,1,2,2,3,3,4,4,7,7,8,8`）')
    print('     只用这 6 个变体，**能做到的最好** `r` = **%.6f**' % rmin_s)
    print('     取到它的体积分数 = %s'
          % {int(seeded[i] + 1): round(float(fs[i]), 4)
             for i in range(len(seeded)) if fs[i] > 1e-3})

    # S-2 全部 6 子集
    print()
    print('  ## **S-2 全部 C(12,6)=924 个 6 变体子集**的 `r_min` 分布')
    vals, best = [], []
    for idx in itertools.combinations(range(n), 6):
        r_, _ = subset_min(E, idx, iters=1200)
        vals.append(r_)
        best.append((r_, tuple(int(v + 1) for v in idx)))
    vals = np.asarray(vals)
    best.sort()
    print('     中位 %.6f；范围 %.6f … %.6f' %
          (float(np.median(vals)), float(vals.min()), float(vals.max())))
    print('     最好的 5 个 6 子集：%s'
          % ['%s:%.6f' % (b[1], b[0]) for b in best[:5]])
    print('     播种集在 924 个子集里的排名 = **%d / 924**（百分位 %.1f%%）'
          % (1 + int((vals < rmin_s).sum()), 100.0 * float((vals < rmin_s).mean())))

    # S-3 判读
    print()
    print('  ## **S-3 判读**（实测 `r_selfac` = **0.6167**）')
    print('     播种集能做到的最好 = **%.6f**' % rmin_s)
    if rmin_s > 0.3:
        print('     ⇒ ❌ **播种集本身就是瓶颈** ⇒ "没自协调"首先是**变体组合没选对**，')
        print('        不是动力学/时长/参数的问题。**诊断要改写。**')
    elif rmin_s > 0.1:
        print('     ⇒ ⚠ 播种集能做到 %.3f，而实测 %.3f ⇒ 有差距但不悬殊' % (rmin_s, 0.6167))
    else:
        print('     ⇒ ✅ **播种集不是瓶颈**（它能做到 %.4f）⇒ 问题在动力学/时长/参数侧。'
              % rmin_s)
    print()
    print('  ⚠ 记账：`r` 是**几何/运动学**判据（`BLOCK_SELFAC.md` L-2），不含弹性各向异性；')
    print('     `ε⁰` 也不含点阵不变剪切（L-1）⇒ 它是"点阵形变自协调"的必要条件，不是全部。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
