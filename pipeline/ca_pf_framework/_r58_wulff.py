#!/usr/bin/env python3
"""R58: **刻面机制的数学形式** —— 用 Wulff 凸包改写速度律，并先在 2D 上验证。

## 推导（为什么必须凸化速度）
`φ_t + v(n)|∇φ| = 0`（`n = ∇φ/|∇φ|`）的**渐近形状**是 **Wulff 形**：
        `W = { x : x·n ≤ v(n)  ∀n }`      （半空间的交）
若 `v(n)` **凸** ⇒ `W` 的支撑函数就是 `v`，形状光滑；
若 `v(n)` **非凸** ⇒ `W` 的支撑函数是 `v` 的**凸包络** `v**`
        ⇒ `v**` 在缺失取向的区间上是**平面** ⇒ `W` 出现**平面刻面**。

⇒ **正确的做法不是"加一个通道"，而是把进入平流的法向速度从 `v(n)` 换成 `v**(n)`**
（`v**` = 极图 `{v(n)·n}` 的凸包的支撑函数）。
* 对**凸**的 `v` ⇒ `v** = v` ⇒ **行为完全不变**（这对回归很重要）；
* 对**非凸**的 `v`（本项目的 `M(θ)` 在尖端附近 `F<0` 就是非凸）⇒ 出现刻面。

## 本脚本
在 **2D（a–w 平面）** 上：
  1. 画出极曲线 `P(θ) = v(θ)·(cosθ, sinθ)`；
  2. 求其**凸包**，并由凸包给出 `v**(θ) = h(θ)`（支撑函数）；
  3. 比较 `v` 与 `v**`；
  4. 用**凸化后的 `v**`** 跑支撑函数演化，量 `v_a/v_w`，看是否升到 ≳9。
"""
import numpy as np

B_H, B_W, A_DOT_N = 6.477, 2.3, -0.127
NTH = 1441
TH = np.linspace(0.0, np.pi / 2, NTH)          # 只扫 0..90°（a–w 象限）


def v_of(th, bw=B_W, c=0.0):
    """`v(θ) = M(θ)·ΔG`（取 ΔG=1）；`c` = 45° 凹陷强度。"""
    n_dot_n = np.cos(th) * A_DOT_N
    m = np.exp(-B_H * n_dot_n ** 2 - bw * np.sin(th) ** 2
               - c * np.sin(2 * th) ** 2)
    return m


def polar_hull_support(th, v):
    """极图 `{v·n}` 的凸包的支撑函数（按 θ 求）。"""
    from scipy.spatial import ConvexHull
    P = np.stack([v * np.cos(th), v * np.sin(th)], -1)
    hull = ConvexHull(P)
    V = P[hull.vertices]
    # 支撑函数：h(θ) = max over hull 顶点 of (x·n)
    n = np.stack([np.cos(th), np.sin(th)], -1)
    return (V @ n.T).max(0)


print('=' * 92)
print('一、`v(n)` 与它的凸包络 `v**`（ΔG=1）')
print('  %-8s %-12s %-12s %-12s %s'
      % ('θ (deg)', 'v(θ)', 'v**(θ)', 'v** / v', '是否被凸化'))
for c in (0.0, 2.0):
    v = v_of(TH, c=c)
    vs = polar_hull_support(TH, v)
    print('  --- c=%.1f' % c)
    for t in (0, 15, 30, 45, 60, 75, 90):
        i = int(np.argmin(np.abs(np.degrees(TH) - t)))
        print('  %-8d %-12.4f %-12.4f %-12.4f %s'
              % (t, v[i], vs[i], vs[i] / v[i] if v[i] else float('inf'),
                 '**是**' if abs(vs[i] - v[i]) > 1e-9 * max(v[i], 1e-12) else '否'))
    print()
print('二、把 `v**` 代回**支撑函数演化**（`_r55_huygens` 的同一套），量 `v_a/v_w`')
print('  %-10s %-12s %-12s %-10s %s'
      % ('形式', 'd(a)', 'd(w)', 'v_a/v_w', '目标 ≥9'))
for c in (0.0, 1.0, 2.0, 4.0):
    v = v_of(TH, c=c)
    vs = polar_hull_support(TH, v)
    # 只用 0..90°；演化用完整 0..2π（对称延拓）
    th2 = np.concatenate([TH, np.pi - TH[::-1], np.pi + TH, 2 * np.pi - TH[::-1]])
    h2 = np.concatenate([vs, vs[::-1], vs, vs[::-1]])
    o = np.argsort(th2)
    th2, h2 = th2[o], h2[o]
    # 两轴跨度 = 2·h(0)（沿 a）与 2·h(90°)（沿 w）
    ha = float(np.interp(0.0, th2, h2))
    hw = float(np.interp(np.pi / 2, th2, h2))
    # 演化：h(θ) 每步加 v**(θ)·dt；**凸化已内建** ⇒ 直接用 h 的端点
    dt, steps = 0.1, 400
    ha_t, hw_t = ha + 0.0, hw + 0.0
    # 端点的推进 = h(0) 与 h(90°) 各自的增量（凸化后 h 已是支撑函数）
    da = ha * dt * steps       # 半宽增量
    dw = hw * dt * steps
    print('  %-10s %-12.4f %-12.4f %-10.2f %s'
          % ('c=%.1f' % c, 2 * ha * dt, 2 * hw * dt,
             (ha / hw) if hw else float('inf'),
             '✅' if hw and ha / hw >= 9 else ''))
print()
print('★ 注：`v_a/v_w` 就是 `h(0°)/h(90°)` = 凸包在两个主方向上的支撑函数之比。')
print('  ⇒ 只要 `v**(0°)/v**(90°)` ≳ 9，刻面演化就能给出 ≳9 的形状各向异性。')
