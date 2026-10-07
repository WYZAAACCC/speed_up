#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r379_lis_check.py —— `ε⁰` 的**谱结构**：它是不是"纯剪切 + 膨胀"？

## 为什么先算这个
"`ε⁰` 不含 LIS"这句话要讲准，必须先知道本项目的 `ε⁰` **本身长什么样**：
* `windowB_ti64_variants.py` 的 `ε⁰ = sym(F) − I`，`F` 是**点阵对应**（Burgers OR + 晶格常数）；
* docstring 记着：`d_(110)=0.23408 nm` 与 `c_a/2=0.23415 nm` 只差 **+0.03%**
  ⇒ 贝恩畸变的**法向分量几乎为零**。

**不变平面应变（IPS）的判据**：@@\\mathrm{sym}(F)-I@@ 的特征值应是 **(t, −t, 0)**
（一个纯剪切：一个方向拉、一个方向压、第三个方向不动）。
⚠ 注意：`sym(a\\otimes n)` 生成的集合正是"特征值为 (t,−t,0) 的对称张量"
⇒ `rank1_residual` 量的就是"离纯剪切有多远"（我此前叫它 "rank-1"，指的是
`F_i−F_j=a\\otimes n` 那个 **rank-1 矩阵**，命名不严谨但量是对的）。

## 判据
* **L-1**：`ε⁰` 的特征值应形如 (t+δ, −t+δ, δ)，其中 δ = tr/3 是膨胀部分。
  ⇒ 去迹后的 `dev(ε⁰)` 特征值应是 **(t, −t, 0)**（两个非零、一个零）。
* **L-2**：`dev(ε⁰)` 的最小特征值 / 最大特征值 应 ≈ 0（纯剪切的标志）。
* **L-3**：剪切量 t 与文献里 β→α′ 的形状应变比较。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    print('=' * 88)
    print('_r379 —— `ε⁰` 的谱结构（是不是"纯剪切 + 膨胀"）')
    print('=' * 88)
    from T16_verify_rve import EPS0
    E = [np.asarray(e, float) for e in EPS0]
    print('  变体数 = %d' % len(E))
    print()
    print('  ## **L-1 特征值**（前 3 个变体；其余逐位同构）')
    print('  %-4s %26s %26s %26s' % ('变体', 'ε⁰ 特征值', 'dev(ε⁰) 特征值', '|λ3|/|λ1|'))
    for v in range(min(3, len(E))):
        A = E[v]
        w = np.sort(np.linalg.eigvalsh(A))[::-1]
        D = A - np.trace(A) / 3.0 * np.eye(3)
        wd = np.sort(np.linalg.eigvalsh(D))[::-1]
        print('  %-4d %26s %26s %26.4f'
              % (v + 1,
                 '[%+.5f %+.5f %+.5f]' % tuple(w),
                 '[%+.5f %+.5f %+.5f]' % tuple(wd),
                 abs(wd[2]) / max(abs(wd[0]), 1e-30)))
    # 全部 12 个的汇总
    r3 = []
    for A in E:
        D = A - np.trace(A) / 3.0 * np.eye(3)
        wd = np.sort(np.linalg.eigvalsh(D))[::-1]
        r3.append(abs(wd[2]) / max(abs(wd[0]), 1e-30))
    print()
    print('  **L-2** 全部 12 个变体：`|λ3|/|λ1|` 范围 = %.6f … %.6f（**≈0 ⇒ 纯剪切** %s）'
          % (min(r3), max(r3), '✅' if max(r3) < 0.1 else '❌'))
    # 剪切量
    A = E[0]
    D = A - np.trace(A) / 3.0 * np.eye(3)
    wd = np.sort(np.linalg.eigvalsh(D))[::-1]
    t = float(wd[0])
    print('  **L-3** 剪切量 `t = λ1 = %.5f`；膨胀 `tr(ε⁰)/3 = %+.5f`；'
          '`tr(ε⁰) = %+.5f`' % (t, float(np.trace(A)) / 3.0, float(np.trace(A))))
    print('      ⇒ 即"纯剪切 %.4f（≈%.2f°）+ 静水膨胀 %+.2f%%"'
          % (t, np.degrees(np.arctan(2 * t)), 100 * float(np.trace(A))))
    print()
    print('  ## 对照：如果是**纯剪切**（无膨胀），`det(I+ε⁰)` 应 = 1')
    print('     实测 `det(I+ε⁰)` = **%.6f** ⇒ 差 %.2f%% 就是**膨胀**的贡献'
          % (float(np.linalg.det(np.eye(3) + A)),
             100 * abs(1 - float(np.linalg.det(np.eye(3) + A)))))
    print()
    print('  ⚠ 记账：`ε⁰ = sym(F) − I`，`F` 来自 `windowB_ti64_variants.py` 的**点阵对应**')
    print('     （Burgers OR + 晶格常数），**不含点阵不变剪切（LIS）**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
