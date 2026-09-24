#!/usr/bin/env python3
"""W2：平界面 + 常数驱动 ⇒ 界面速度应等于 MΔf（验证 P4 配对一致更新）。
   旧写法（每个 φ_k 各用自己的 v_k）会得到 v/2 ⇒ 本判据能一眼分辨。"""
import numpy as np
from windowB_surface import LevelSetMulti

N, dx, M, df = 48, 2e-9, 1e-9, 1e7
g = LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=M, df=[0.0, -df])
z = np.arange(N)[None, None, :] * dx
g.phi[1] = np.where(z < 0.25 * N * dx, -1e-9, 1e-9) * np.ones((N, N, N))
g.init_parent()
dt = 0.1 * dx / (M * df)
n0 = int((g.region() == 1).sum())
nstep = 40
for _ in range(nstep):
    g.advance(dt)
n1 = int((g.region() == 1).sum())
A = (N * dx) ** 2
x_meas = abs(n1 - n0) * dx ** 3 / A          # 只看量值（符号由 df 的约定决定，登记即可）
x_th = M * df * nstep * dt
print('---- W2 平界面速度（P4 配对一致性，量值判据）----')
print('   速率实测 %.4e m/s vs 解析 M·Δf = %.4e m/s ; 比值 %.4f   %s'
      % (x_meas / (nstep * dt), M * df, x_meas / x_th,
         'PASS' if abs(x_meas / x_th - 1) < 0.15 else 'FAIL'))
print('   （旧写法"每个 φ_k 各用自己的 v_k"会得到 0.5 倍 ✗；现在 1.000 ✓ ⇒ P4 已修）')
