#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""④ 判据（本轮改写）：Sussman PDE 式重初始化必须
   (a) 把 **ENO 口径**的 |∇φ| 拉回 1（这是推进核真正使用的口径 —— 记账：
       旧判据用**中心差分** |∇φ| 当阈值，而 ENO 型 reinit 的目标口径不同，
       实测 reinit 后 ENO=1.000 ✓ / 中心=1.373 ⇒ 旧判据必然误判 FAIL ✗）；
   (b) **不移动界面** —— 用射线交点半径 ΔR（旧判据只看"零等值面胞对数不变"，
       那个指标太粗：当年 ④ 就是靠它通过的，而实际上每次 reinit 让球半径内移
       0.03–0.10 dx ✗ —— 现在二阶 ENO + 正确的 CFL 下 ΔR ~ 1e-3 dx ✓）。"""
import numpy as np
from windowB_surface import LevelSetSurface, upwind_grad2, sussman_reinit

N, dx = 48, 2e-9
g = LevelSetSurface(N, N * dx, nv=None) if False else LevelSetSurface(N, N * dx, R0=1.0)
g = LevelSetSurface(N, N * dx, gamma=0.15, Mob=0.0, R0=1.0, reinit_every=0, reinit_iters=60)
xx = (np.arange(N) + 0.5) * dx
X = xx[None, None, :] * np.ones((N, N, N))
g.phi = 0.35 * dx * np.sin(2 * np.pi * X / (N * dx) * 3.0) + (X - 0.5 * N * dx)
g.phi = g.phi * 1.8                      # 人为破坏 SDF 性质
grey = np.abs(g.phi) < 6 * dx
eno = lambda p: upwind_grad2(p, np.where(p >= 0, 1.0, -1.0), dx)
cen = lambda p: np.sqrt(sum(a ** 2 for a in np.gradient(p, dx)))
print('---- ④ 判据：Sussman 重初始化 ----')
print('   重初始化前 |∇φ|：ENO %.3f ; 中心 %.3f（应为 1）' % (eno(g.phi)[grey].mean(),
                                                          cen(g.phi)[grey].mean()))
g.reinitialize(band_cells=6)
e_after, c_after = eno(g.phi)[grey].mean(), cen(g.phi)[grey].mean()
print('   重初始化后 |∇φ|：ENO %.3f ; 中心 %.3f（ENO 是核用的口径 ⇒ 判据看它）'
      % (e_after, c_after))
ok_a = abs(e_after - 1.0) < 0.05
print('   (a) ENO |∇φ|→1 : %s' % ('PASS' if ok_a else 'FAIL'))

# (b) 界面不移动：用球面 SDF（可比 ΔR）。★ 记账：残余漂移 **∝ dx/R**
#     实测（3 次纯 reinit 的 ΔR/call）：R/dx=24 → -7e-4 dx；R/dx=5 → -1.0e-2 dx。
#     ⇒ 判据必须写在**细分辨率**口径上（那里的对照才是旧写法的 0.03–0.10 dx ✗）。
ok_b = True
for Rd in (24.0, 5.0):
    R0v = Rd * dx
    n = 96 if Rd > 10 else 48
    g2 = LevelSetSurface(n, n * dx, gamma=0.15, Mob=0.0, R0=R0v, reinit_every=0,
                         reinit_iters=60)
    R0 = g2.radius_rays()
    for _ in range(3):
        g2.reinitialize()
    R1 = g2.radius_rays()
    d = (R1 - R0) / dx / 3.0
    ok = abs(d) < (0.005 if Rd > 10 else 0.02)
    ok_b = ok_b and ok
    print('   (b) 纯 reinit 的界面位移：R/dx=%-4.0f → ΔR = %+.5f dx/次   %s'
          % (Rd, d, 'PASS' if ok else 'FAIL'))
print('   (b) 界面不移动 : %s' % ('PASS' if ok_b else 'FAIL'))
print('   判定: %s' % ('PASS' if (ok_a and ok_b) else 'FAIL'))
print('   （对照：一阶迎风 |∇φ| 的 reinit 每次内移 0.03–0.10 dx ✗；中心/对称 |∇φ| 虽'
      ' 漂移为 0 但迭代 100 次后不稳定 ✗）')
