#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r376_selfac_def.py —— 把 `r_selfac` 这个量"标定"出来：0 / 1 / 实测值各意味着什么。

## `r_selfac` 的定义（`_bk_measure.py:492-504`，逐行照抄）

    E_v = ε⁰_v − (tr ε⁰_v / 3)·I          # **偏量**（去掉体积变化）—— "形状"部分
    scale = mean_v ‖E_v‖_F                # 归一化尺度
    acc = Σ_v f_v · E_v                   # 体积分数加权的形状应变之和
    r_selfac = ‖acc‖_F / scale

**物理含义**：所有变体的形状应变**按体积加权求和**。
* `r_selfac = 0`  ⇒ 各变体的剪切**互相抵消** ⇒ 宏观无形状变化 ⇒ **完全自协调**；
* `r_selfac = 1`  ⇒ 相当于"整个转变区只有**一个**变体"（没有任何抵消）。

## 本脚本给的锚点

| 情形 | `r_selfac` |
|---|---|
| 单变体（无抵消） | 应为 **1.0000**（≡ 定义） |
| 12 变体**等体积分数** | ? |
| 6 个**不同**张量等分数 | ? |
| **可动下界**（在单纯形上最小化 ‖Σ f_v E_v‖） | ? ⇒ "最好能做到多少" |
| 归档实测（`saSet2` @400） | 0.616659 |
| 投影 0 实测（`saSet2P0` @400） | 0.548566 |
"""
from __future__ import annotations

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


def r_of(E, f):
    scale = float(np.mean([np.sqrt(np.sum(e ** 2)) for e in E]))
    acc = np.tensordot(np.asarray(f, float), E, axes=(0, 0))
    return float(np.sqrt(np.sum(acc ** 2)) / (scale + 1e-300))


def hull_min(E, iters=4000):
    """Frank–Wolfe：min_{f>=0, Σf=1} ‖Σ f_v E_v‖²。"""
    n = E.shape[0]
    f = np.full(n, 1.0 / n)
    for t in range(1, iters + 1):
        acc = np.tensordot(f, E, axes=(0, 0))
        # 线性子问题：min_s <E_s, acc>
        dots = np.tensordot(E, acc, axes=((1, 2), (0, 1)))
        s = np.zeros(n)
        s[int(np.argmin(dots))] = 1.0
        gamma = 2.0 / (t + 2.0)
        f = (1 - gamma) * f + gamma * s
    return r_of(E, f), f


def main():
    print('=' * 92)
    print('_r376 —— `r_selfac` 的锚点（0 = 完全自协调；1 = 单变体无抵消）')
    print('=' * 92)
    E = ev_set()
    n = E.shape[0]
    nrm = [float(np.sqrt(np.sum(e ** 2))) for e in E]
    print('  变体数 = %d；`‖E_v‖_F`（偏量）范围 = %.6f … %.6f（应全同：对称等价）'
          % (n, min(nrm), max(nrm)))
    print('  `E_v` 与体积无关（已去迹）；`ε⁰` 的 `tr` = %.6f ⇒ 体积变化不进这个量'
          % float(np.trace(np.asarray(__import__('T16_verify_rve').EPS0[0], float))))

    print()
    print('  ## 锚点')
    for v in range(n):
        f = np.zeros(n)
        f[v] = 1.0
        if v < 2:
            print('     单变体 V%-2d                ⇒ `r_selfac` = **%.4f**' % (v + 1, r_of(E, f)))
    print('     12 变体等分数           ⇒ `r_selfac` = **%.4f**' % r_of(E, np.full(n, 1.0 / n)))
    # 6 个不同张量（1,2 / 3,4 / … 成对相同 ⇒ 每组取一个）
    reps = [0, 2, 4, 6, 8, 10]
    f6 = np.zeros(n)
    for r_ in reps:
        f6[r_] = 1.0 / len(reps)
    print('     6 个不同张量等分数      ⇒ `r_selfac` = **%.4f**' % r_of(E, f6))
    rmin, fmin = hull_min(E)
    print('     **可动下界**（单纯形最小化）⇒ `r_selfac` = **%.4f**' % rmin)
    top = np.argsort(-fmin)[:6]
    print('       取到它的体积分数（只列 >1e-3）= %s'
          % {int(v + 1): round(float(fmin[v]), 3) for v in top if fmin[v] > 1e-3})

    print()
    print('  ## 实测值落在这条尺的哪里')
    for lab, val in (('归档 `saSet2` @400（投影 10）', 0.616659),
                     ('`saSet2P0` @400（投影 0）', 0.548566)):
        span = 1.0 - rmin
        pos = (val - rmin) / span if span > 0 else float('nan')
        print('     %-30s `r_selfac` = **%.6f** ⇒ 距下界 %.1f%% 的行程'
              % (lab, val, 100 * pos))
    print()
    print('  ⚠ 记账：`r_selfac` 量的是**宏观形状抵消**，是自协调的**必要非充分**signature ——')
    print('     随机选变体+等分数也可能给出中等偏小的值 ⇒ 必须配合 `§173` 那种')
    print('     "**配对是否被选择**"的检验（控制几何）才能定案。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
