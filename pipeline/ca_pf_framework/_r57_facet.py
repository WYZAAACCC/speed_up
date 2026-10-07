#!/usr/bin/env python3
"""R57: **刻面机制的数学条件** —— 能不能**只靠 `M(n)` 的角函数形式**让棱角自发刻面？

## 原理（法向速度演化的标准结果）
凸体按 `v(n)` 演化时，取向 `θ` 会**被跳过**（⇒ 形成**平面刻面**）当且仅当
        **`F(θ) ≡ v(θ) + v''(θ) < 0`**
（这是 Wulff 型"缺失取向"判据在**动力学**系数上的版本；
`M(n)` 是**动力学**量、**没有凸性约束** ⇒ 允许非凸，这正是本项目的有利条件。）

## 为什么这可能是解
`_r55_huygens.py` 已实测：**只要做凸包（= 允许刻面），`v_a/v_w` 就是 9.90**
（= `M(a)/M(w)`）；而引擎给 1.4–1.7（= 没刻面、棱角被磨圆）。
⇒ **不必新写代码，只要让 `M(θ)` 满足 `F < 0` 就能让刻面自发出现。**

## 现有形式为什么不行
`M = exp(−β_h(n·n*)² − β_w(n·w)²)` 在 θ 上**单调** ⇒ `v''` 为正的地方多
⇒ `F > 0` ⇒ 无缺失取向 ⇒ 不刻面。
"""
import numpy as np

B_H, A_DOT_N = 6.477, -0.127
TH = np.linspace(1e-4, np.pi / 2 - 1e-4, 4001)     # 0..90°，避开端点


def m_cur(bw):
    t = TH
    return np.exp(-B_H * (np.cos(t) * A_DOT_N) ** 2 - bw * np.sin(t) ** 2)


def m_dip(bw, c):
    """加一个在 45° 处取极小的因子：exp(−c·sin²(2θ))。"""
    t = TH
    return (np.exp(-B_H * (np.cos(t) * A_DOT_N) ** 2 - bw * np.sin(t) ** 2)
            * np.exp(-c * np.sin(2 * t) ** 2))


def F_of(m):
    """`F(θ) = v + v''`（v ∝ M，取 ΔG=1）。用二阶中心差分。"""
    d = TH[1] - TH[0]
    mpp = np.gradient(np.gradient(m, d), d)
    return m + mpp


print('=' * 92)
print('判据 `F(θ) = v + v″ < 0` ⇒ 该取向被跳过 ⇒ **自发刻面**')
print()
for bw in (2.3, 4.0):
    m = m_cur(bw)
    F = F_of(m)
    neg = TH[F < 0]
    print('  现形式 β_w=%.1f : min F = %+.4f   负区间 = %s'
          % (bw, F.min(),
             ('无' if neg.size == 0 else '%.1f°–%.1f°' % (np.degrees(neg[0]),
                                                          np.degrees(neg[-1])))))
print()
print('  加凹陷因子 exp(−c·sin²(2θ))（β_w=2.3）:')
for c in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0):
    m = m_dip(2.3, c)
    F = F_of(m)
    neg = TH[F < 0]
    r = float(np.degrees(TH[np.argmin(m)]))
    print('    c=%-6.1f  min F = %+-9.4f  负区间 = %-16s  min M 在 %.1f°   M(45°)/M0=%.4f'
          % (c, F.min(),
             ('无' if neg.size == 0 else '%.1f°–%.1f°'
              % (np.degrees(neg[0]), np.degrees(neg[-1]))), r,
             float(m_dip(2.3, c)[np.argmin(np.abs(TH - np.pi / 4))])))
print()
print('★ 目标：找到 `c` 使**负区间覆盖 30°–60° 一带**（棱角所在），')
print('  且 `M` 不塌到数值噪声以下（`min M ≳ 1e-3`）。')
