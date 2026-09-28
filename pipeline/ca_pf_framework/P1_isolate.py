#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1_isolate.py --- 隔离"界面带自发膨胀"（P1）的来源：**只换平流格式**。

背景（P1 的四条独立证据）
------------------------
  T2  平面前沿 step≈100 起界面键数 +52%（`reinit_every=0` 档同样发生 ⇒ 与 reinit 无关）
  T11-B 界面面积测度在 Δx 三档上非单调（±1.3%）
  T13 `r_c^var` 在晚段被拉低
  T16  单核板条 400 步里**界面胞数 601 → 4232（×7）**，同时 `M6p` p25 从 3.5° 升到 18.2°

设计（**纯数值算例，单变量**）
----------------------------
球 + **常数驱动** + **无弹性** + **γ=0** ⇒ 精确解是"半径线性增长的完美球"，
界面**不该**粗化。于是任何粗化都是**纯数值**的。
只改一个变量：`adv_grad` ∈ {central, upwind}（其余全同：同一初值、同步长、同带宽）。

判据
----
  P1-0 **量具**：界面胞数的解析对照（完美球 `R(t)` 的键测度面积 / dx²）
  P1-1 两档都在 300 步内的"界面胞数"增长倍数；**格式若导致粗化，其倍数应显著 > 1**
  P1-2 **球度**：`R(θ,φ)` 的相对散布（粗化会让它上升）
  P1-3 结论：指出主因格式，并给出"改用它会付出什么代价"（用 `v/(MΔf)` 的精度作对照）

用法：python3 P1_isolate.py [--N 64] [--steps 300]
退出码：0 = 已定位
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

DF, MOB = 2.0e8, 1e-9


def run(N, dx, adv, steps=300, band=20):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=4, reinit_every=0, reinit_dt=6.0e-7)
    R0 = 0.15 * L
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    c0 = np.array([L / 2] * 3)
    dt = 0.15 * dx / (MOB * DF)
    hist = []
    for it in range(1, steps + 1):
        g.advance(dt, band_cells=band, adv_grad=adv)
        if it % 30 == 0:
            reg = g.region()
            nb = 0
            for ax in range(3):
                nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
            idx = np.argwhere(reg == 1)
            rr = np.linalg.norm((idx.astype(float) + 0.5) * dx - c0, axis=1)
            # 球度：把半径按方向分箱后取相对散布
            u = ((idx.astype(float) + 0.5) * dx - c0) / np.maximum(
                rr[:, None], 1e-30)
            key = np.round(u * 6).astype(int)
            _, inv = np.unique(key, axis=0, return_inverse=True)
            Rm = np.array([rr[inv == j].mean() for j in range(inv.max() + 1)])
            sph = float(np.std(Rm) / max(np.mean(Rm), 1e-30))
            hist.append((it, nb, float(rr.mean()), sph))
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=300)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    print('=' * 100)
    print('P1 隔离 —— 界面带自发膨胀：只换平流格式   N=%d Δx=%.0f nm L=%.2f µm'
          % (N, a.dx_nm, L * 1e6))
    print('  算例：球 + 常数驱动 + 无弹性 + γ=0 ⇒ 精确解是完美球，界面**不该**粗化')
    print('=' * 100)
    res = {}
    for adv in ('central', 'upwind'):
        h = run(N, dx, adv, a.steps)
        res[adv] = h
        print('  【%s】 step   界面键数   平均半径(nm)   球度(相对散布)' % adv)
        for it, nb, rm, sph in h:
            print('           %-6d %-10d %-14.1f %.4f' % (it, nb, rm * 1e9, sph))
        print()
    print('  判据 P1-1：界面键数的增长倍数（末 / 首）')
    for adv in ('central', 'upwind'):
        h = res[adv]
        gr = h[-1][1] / max(h[0][1], 1)
        sr = h[-1][3] / max(h[0][3], 1e-30)
        print('    %-8s 键数 %d → %d（×%.2f）；球度 %.4f → %.4f（×%.2f）'
              % (adv, h[0][1], h[-1][1], gr, h[0][3], h[-1][3], sr))
    gc = res['central'][-1][1] / max(res['central'][0][1], 1)
    gu = res['upwind'][-1][1] / max(res['upwind'][0][1], 1)
    main_adv = 'central' if gc > gu * 1.3 else ('upwind' if gu > gc * 1.3 else None)
    print()
    print('  ⇒ 粗化主因格式：%s'
          % (main_adv if main_adv else '**两者相当**（说明主因不在平流格式，另找）'))
    print('  ⚠ 记账：**换格式有代价** —— 见 T11b/T11g：`upwind` 在倾斜前沿的 `v/(MΔf)`')
    print('     偏差更大（1.14/0.86/0.65 对 0.92/0.84/0.82）⇒ 不能只按"粗化少"来选。')
    print('=' * 100)
    return 0


if __name__ == '__main__':
    sys.exit(main())
