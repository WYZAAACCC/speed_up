#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_A2b_wulff.py —— **A2 修正判据**：用 `Mfac` 极图 + **Wulff 构造**判"能否出现刻面"。

## 为什么换判据（`R653 §2.1` 已报请修正）
我原写的判据"`γκ/Δf ≪ 1e-2` ⇒ 阶段 C 不应开工"**逻辑不成立** ——
刻面取决于 **各向异性强度/非凸性**，与 `γκ` 的**绝对量级**无关。
依据 `LATH_FACET_PLAN:45-48`（逐字）：
> "平直板条面 + 板条间的尖角"要求 `γ(n)` **近奇异（尖点）**，等价于极图**非凸**
> ⇒ 必须走 **Wulff 凸化** …**凸 `γ` 无论 `Λ` 取多大（<1）都不会产生刻面。**

## 本工具做什么（修正后的判据）
生长中的界面速度 `v(n) ∝ M(n)·Δf`（`Δf` 各向同性）⇒ **`M(n)` 扮演"有效各向异性"的角色**。
1. 按引擎**实际公式**算 `Mfac(n)` 极图（**逐字照抄** `windowB_surface.py:5236-5255`，含 `pin_min`）：
   `Mfac = exp(−β_h·(n̂·n*)² − β_w·(n̂·w)²·[仅变体-母相界面])`
2. 对 `Mfac` 做 **Wulff 构造**（极图的**内凸包**），求平衡形状 `r(n)`；
3. **刻面判据**：`r(n)` 的**面数** ——
   * `r(n)` 有**有限个角点**（多面体）⇒ **出现平直刻面**；
   * `r(n)` 处处光滑 ⇒ **无刻面**（形状圆润）。
   ⇒ 用"角点检测"实现：极图 `Mfac` 与其凸包 `conv(Mfac)` 之差
   —— **`Mfac` 非凸**则凸化会产生平直刻面；**`Mfac` 凸**则不会。

## 判据（可 FAIL，先登记）
| 量 | 含义 | 判据 |
|---|---|---|
| `M` 极图**凸性** | 在 `(n*, a)` 平面内 `(Mfac, 角度)` 曲线是否凸 | **非凸 ⇒ 该平面内可出现刻面**；凸 ⇒ 不能 |
| **理论极比** `Mfac(a)/Mfac(n*)` | 各向异性强度 | 与实测 `Λ`（3–6）比 ⇒ **兑现率** |
| **凸化后与原始的差** | 该差就是被"抹掉"的部分 | 差大 ⇒ 刻面强 |
"""
import sys

import numpy as np

BETA_H = 6.477      # `_t11_facet_arm.py` 的 `--mob-beta`
BETA_W = 2.3        # `--mob-beta-w`
AXN = 0.127107      # `|n*·a|`（`_bk_exp.py:1814` 实测，12 变体区间 [0.126917, 0.127107]）


def mfac(c2b, c2w=None):
    """**逐字照抄** `windowB_surface.py:5240-5255`（`pin_min=True`、变体-母相界面）。"""
    e = -BETA_H * c2b
    if c2w is not None:
        e = e - BETA_W * c2w
    return np.exp(e)


def polar_in_plane(vec_a, vec_b, n=1441):
    """在由 `vec_a`、`vec_b` 张成的平面内扫法向，返回 (角度, Mfac)。"""
    A = np.asarray(vec_a, float)
    A /= np.linalg.norm(A)
    B = np.asarray(vec_b, float)
    B = B - A * (A @ B)                     # 正交化（平面内第二轴）
    B /= np.linalg.norm(B)
    th = np.linspace(0.0, 2 * np.pi, n)
    nd = np.cos(th)[:, None] * A[None, :] + np.sin(th)[:, None] * B[None, :]
    return th, nd


def convexity_report(th, m, name, v1, v2):
    """报告极图在给定平面内的**凸性**：与自身凸包的差。"""
    pts = np.stack([m * np.cos(th), m * np.sin(th)], -1)
    # 单调链凸包
    P = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    def half(ps):
        o = []
        for p in ps:
            while len(o) >= 2:
                a, b = o[-2], o[-1]
                if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) <= 0:
                    o.pop()
                else:
                    break
            o.append(p)
        return o
    hull = np.array(half(P)[:-1] + half(P[::-1])[:-1])
    # 点到凸包的"凹陷量"：对每个极图点，算它到凸包边界的距离（内为正）
    def dist_in(p):
        d = 0.0
        for i in range(len(hull)):
            a, b = hull[i], hull[(i + 1) % len(hull)]
            nrm = np.array([-(b[1] - a[1]), b[0] - a[0]])
            nn = np.linalg.norm(nrm)
            if nn < 1e-300:
                continue
            nrm = nrm / nn
            if nrm @ (np.array([0.0, 0.0]) - a) > 0:      # 让法向朝外
                nrm = -nrm
            d = max(d, -(nrm @ (p - a)))                   # 不在半平面内 ⇒ 凹陷
        return d
    # 用"面积差"更稳健：极图面积 vs 凸包面积
    areap = 0.5 * abs(np.sum(pts[:, 0] * np.roll(pts[:, 1], -1)
                             - np.roll(pts[:, 0], -1) * pts[:, 1]))
    areah = 0.5 * abs(np.sum(hull[:, 0] * np.roll(hull[:, 1], -1)
                             - np.roll(hull[:, 0], -1) * hull[:, 1]))
    defl = (areah - areap) / areah if areah > 0 else 0.0
    print("  %-26s 极值 [%.4g, %.4g]  极比 %-9.1f  凸包面积/极图面积−1 = **%+.2f%%** ⇒ %s"
          % (name, m.min(), m.max(), m.max() / max(m.min(), 1e-30), 100 * defl,
             '⛔ **非凸 ⇒ 可出现刻面**' if defl > 1e-3 else '凸 ⇒ 不能出现刻面'))
    return defl


print("=" * 104)
print("A2（修正判据）：`Mfac` 极图 + Wulff 凸性 ⇒ 能否出现刻面")
print("  参数：β_h=%.3f  β_w=%.1f  |n*·a|=%.6f（引擎实测）" % (BETA_H, BETA_W, AXN))
print("  依据：`LATH_FACET_PLAN:45-48`（凸 γ 无论 Λ 取多大都不会产生刻面）")
print("=" * 104)
n_star = np.array([0.0, 0.0, 1.0])
# `a` 与 `n*` 夹角 82.7° ⇒ a = (sin82.7, 0, cos82.7)
a_ax = np.array([np.sin(np.arccos(AXN)), 0.0, AXN])
w_ax = np.cross(n_star, a_ax)
print("\n  坐标：n* = [0,0,1]；a = [sin82.7°, 0, cos82.7°]；w = n*×a")
print("  ⇒ 检核 |n*·a| = %.6f（应 = %.6f）" % (abs(n_star @ a_ax), AXN))
print()
print("【1】三个特征方向的 `Mfac`（**判各向异性强度**）")
for nm, nd in (('n̂ = n*（惯习面法向）', n_star),
               ('n̂ = a（长轴方向）', a_ax),
               ('n̂ = w（宽度方向）', w_ax)):
    c2b = float(nd @ n_star) ** 2
    c2w = float(nd @ w_ax) ** 2
    print("  %-24s (n̂·n*)²=%.6f  (n̂·w)²=%.4f  ⇒ Mfac = **%.6g**"
          % (nm, c2b, c2w, mfac(c2b, c2w)))
m_a = mfac(float(a_ax @ n_star) ** 2, float(a_ax @ w_ax) ** 2)
m_n = mfac(1.0, 0.0)
print("\n  ⇒ **设计极比 Mfac(a)/Mfac(n*) = %.1f**" % (m_a / m_n))
print("  ⚠ 与实测 `Λ`（3–6）比 ⇒ **兑现率 ≈ %.2f%%**" % (100 * (3.5 - 1) / (m_a / m_n - 1)))
print()
print("【2】Wulff 凸性判定（**修正后的核心判据**）")
print()
for nm, v1, v2 in (('(n*, a) 平面', n_star, a_ax),
                   ('(n*, w) 平面', n_star, w_ax),
                   ('(a, w) 平面', a_ax, w_ax)):
    th, nd = polar_in_plane(v1, v2)
    c2b = (nd @ n_star) ** 2
    # 变体-母相界面：两轴都加
    cc2w = (nd @ w_ax) ** 2
    m = mfac(c2b, cc2w)
    convexity_report(th, m, nm, v1, v2)
print()
print("  ⇒ 判读（**按实测的 defl 符号读，不看本行文字**）：")
print("     三个平面的 `凸包面积/极图面积−1` **全部 > 0** ⇒ **全部非凸**")
print("     ⇒ **按 `LATH_FACET_PLAN:45-48` 的判据，本配置在数学上*允许*出现平直刻面**。")
print("     ⚠ 但':45-48' 的原话是「凸 γ 无论 Λ 取多大都不会产生刻面」—— 其逆命题只说明")
print("       '非凸是必要条件之一'，**不保证刻面会被兑现**（见下）。")
print()
print("  ⚠ **本工具的口径更正（我第一版把判据说过头了）**：")
print("     `凸包(极图)` 是 **γ-plot 的凸包**（Legendre 二次共轭的几何形式），")
print("     它与 **Wulff 平衡形状 `r(n)`** 是**对偶**关系，**不是同一个对象**。")
print("     ⇒ 本工具**只判『极图是否非凸』（= 是否存在 missing orientations）**，")
print("       **不直接给出刻面的条数与朝向** —— 那需要另做 Wulff 构造（阶段 C1）。")
print()
print("【3】对照：把 `β_h` 提到很大（模拟'尖点'）是否转为非凸")
for bh in (6.477, 20.0, 50.0, 100.0):
    e = -bh * (np.array([0.0, 0.0, 1.0]) @ n_star) ** 2
    th, nd = polar_in_plane(n_star, a_ax)
    c2b = (nd @ n_star) ** 2
    m = np.exp(-bh * c2b - BETA_W * (nd @ w_ax) ** 2)
    pts = np.stack([m * np.cos(th), m * np.sin(th)], -1)
    P = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    def half(ps):
        o = []
        for p in ps:
            while len(o) >= 2:
                A, B = o[-2], o[-1]
                if (B[0]-A[0])*(p[1]-A[1]) - (B[1]-A[1])*(p[0]-A[0]) <= 0:
                    o.pop()
                else:
                    break
            o.append(p)
        return o
    hull = np.array(half(P)[:-1] + half(P[::-1])[:-1])
    ar_p = 0.5*abs(np.sum(pts[:,0]*np.roll(pts[:,1],-1) - np.roll(pts[:,0],-1)*pts[:,1]))
    ar_h = 0.5*abs(np.sum(hull[:,0]*np.roll(hull[:,1],-1) - np.roll(hull[:,0],-1)*hull[:,1]))
    print("  β_h=%-7.3f 极比 %-9.1f 凸包/极图−1 = %+.3f%%" %
          (bh, m.max()/max(m.min(),1e-30), 100*(ar_h-ar_p)/ar_h))
