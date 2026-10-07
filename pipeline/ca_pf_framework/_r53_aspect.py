#!/usr/bin/env python3
"""R53: 由 v2 口径的速率算**长径比的演化** —— 判"板条会不会保持板条性"。

关键点（容易被绝对速率误导）：
  **`d(a) > d(w)` 并不意味着长径比变大。**
  `L/W = (L0 + v_a·t)/(W0 + v_w·t)` ⇒ `t→∞` 时趋于 **`v_a/v_w`**。
  若初始 `L0/W0` 已经**大于** `v_a/v_w`，则 `L/W` **单调下降**
  —— 哪怕"长度长得比宽度快"。
"""
import numpy as np

L0, W0, T0 = 1600.0, 700.0, 635.0        # 种子（nm）
arms = {
    'mb1s   (Δx=125, 盒 12 µm)': dict(a=2.706, w=1.833, n=1.209),
    'mb1s62 (Δx=62.5, 盒 6 µm)': dict(a=1.463, w=1.182, n=0.408),
}
print('种子: L=%.0f  W=%.0f  T=%.0f nm  ⇒ L/W=%.2f  W/T=%.2f'
      % (L0, W0, T0, L0 / W0, W0 / T0))
print()
print('  %-28s %-9s %-9s %-9s %-9s %-9s %s'
      % ('臂', 'v_a/v_w', 'v_a/v_n', 'L/W(1500)', 'W/T(1500)', 'L/W(∞)', 'L/W 趋势'))
for name, v in arms.items():
    t = 1500.0
    L = L0 + v['a'] * t
    W = W0 + v['w'] * t
    T = T0 + v['n'] * t
    lw_inf = v['a'] / v['w']
    trend = '**降**' if lw_inf < L0 / W0 else '升'
    print('  %-28s %-9.2f %-9.2f %-9.2f %-9.2f %-9.2f %s'
          % (name, v['a'] / v['w'], v['a'] / v['n'], L / W, W / T, lw_inf, trend))
    print('        L: %.0f → %.0f nm   W: %.0f → %.0f   T: %.0f → %.0f'
          % (L0, L, W0, W, T0, T))
print()
print('★ 判读：')
print('  · 若 `L/W(∞) = v_a/v_w` **小于**初始 `L/W` ⇒ **长径比必然下降**，')
print('    即"绝对速率上长度最快"与"形状更像板条"**是两件事**；')
print('  · 真正的判据是 **`v_a/v_w` 是否足够大**（要维持/放大长径比需 `v_a/v_w > L/W`）。')
print()
print('=== 需要的 `v_a/v_w`（在 1500 步内把 L/W 从 2.29 提到 3.0 / 5.0 / 9.0）')
for target in (3.0, 5.0, 9.0):
    # 解 (L0 + va*t)/(W0 + vw*t) = target，取 vw = 1.0 归一
    for vw in (1.0,):
        va = (target * (W0 + vw * 1500.0) - L0) / 1500.0
        print('  目标 L/W=%.1f ⇒ 需 `v_a/v_w` ≥ **%.2f**（取 v_w=%.1f nm/步）'
              % (target, va / vw, vw))
print()
print('  实测 `v_a/v_w` = %.2f（Δx=125） / %.2f（Δx=62.5）'
      % (arms['mb1s   (Δx=125, 盒 12 µm)']['a'] / arms['mb1s   (Δx=125, 盒 12 µm)']['w'],
         arms['mb1s62 (Δx=62.5, 盒 6 µm)']['a'] / arms['mb1s62 (Δx=62.5, 盒 6 µm)']['w']))
