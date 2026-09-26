#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_plane_vel.py --- 判据 D13：**平界面推进速度** vs Mfac 预测（无几何干扰）。

为什么（记账）：D11/D12 用的是"薄饼"，其端面曲率 kappa 与面对的几何一起变化，
  无法把"迁移率各向异性"与"曲率/Gibbs-Thomson"分开。平界面 kappa=0 =>
  v = M(n)*M0*DeltaG **纯粹**由 Mfac 决定 => 可干净地量出 v_n : v_w : v_a。

做法：初始 phi_k = (x . n) - c0（理想平面 SDF），沿 n 方向推进 200 步，测位移。
"""
import argparse, json, time
import numpy as np

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

ap = argparse.ArgumentParser()
ap.add_argument('--axis', default='n', choices=['n', 'w', 'a'])
ap.add_argument('--beta', type=float, default=3.5)
ap.add_argument('--beta_w', type=float, default=2.3)
ap.add_argument('--N', type=int, default=48)
ap.add_argument('--dx', type=float, default=5e-8)
ap.add_argument('--df', type=float, default=2e8)
ap.add_argument('--nstep', type=int, default=200)
ap.add_argument('--cfl', type=float, default=0.15)
a = ap.parse_args()

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants(); nv = 12
rng = np.random.default_rng(0); npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best: best, bn = val, n
    npref[v + 1] = bn

N, dx = a.N, a.dx
L = N * dx
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [a.df] * nv, workers=4, reinit_every=25)
k = 1
n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
w1 = np.asarray(g.wtab[k], float)
a1 = np.cross(n1, w1); a1 /= np.linalg.norm(a1)
DIR = {'n': n1, 'w': w1, 'a': a1}[a.axis]

x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
proj = X * DIR[0] + Y * DIR[1] + Z * DIR[2]
# (fix) w1 的两个分量都是负的 => proj=x.w1 全域为负 => 旧写法让变体填满整个域
#       （V=域体积、无界面、v 恒 0）。正确做法：界面放在 proj 的**中点**。
c0 = 0.5 * (proj.min() + proj.max())
g.phi[k] = proj - c0
g.init_parent(); g.c[:] = 0.036
_M = 1e-9
_ed = g.elastic_driving()
dt = a.cfl * dx / (_M * (abs(a.df) + 2.0 * float(np.max(np.abs(_ed)))))
print('=== D13 平界面 axis=%s beta=%.1f beta_w=%.1f N=%d dx=%.1f nm' %
      (a.axis, a.beta, a.beta_w, N, dx * 1e9), flush=True)
t0 = time.time()
# ★ 记账（修测量口径）：平面法向 DIR 一般**不与 z 轴平行**（w1 的 n_z=0 => 沿 z 扫描
#   根本没有交点 => 旧口径对 w 档**失效**）。改用**体积法**：平面推进 d => dV = A*d，
#   A 为常数 => dV 之比**就是**速度之比，与 DIR 无关、无几何干扰。
V0 = float(g.volume(k))
A_eff = L * L
hist = []
tacc = 0.0
for it in range(1, a.nstep + 1):
    g.advance(dt, aniso=0.0, npref=npref, band_cells=8, mob_beta=a.beta,
              mob_beta_w=a.beta_w)
    tacc += dt
    if it % 25 == 0:
        V = float(g.volume(k))
        dproj = (V - V0) / A_eff
        hist.append((it, V, dproj, tacc))
        print('   step %4d  t=%.3e s  V=%.5f um^3  dproj=%.4f um  用时 %.0f s'
              % (it, tacc, V * 1e18, dproj * 1e6, time.time() - t0), flush=True)
    nd = g.suggest_dt(cfl=a.cfl, dt_prev=dt)
    if nd:
        dt = nd
# (fix) 稳态速度用后 1/4 段斜率：前段是初始 phi 非精确 SDF 的瞬态
#       （实测 n 档前 75 步 dproj 甚至为负）。
_m = max(2, len(hist) // 4)
n1_, d1, t1 = hist[-_m][0], hist[-_m][2], hist[-_m][3]
n2_, d2, t2 = hist[-1][0], hist[-1][2], hist[-1][3]
vss = (d2 - d1) / max(t2 - t1, 1e-30)          # **物理时间**速度 (m/s)
vstep = (d2 - d1) / max(n2_ - n1_, 1)
print('[D13 axis=%s] steady v = %.6e m/s (= %.4e um/step over %d..%d steps)'
      % (a.axis, vss, vstep * 1e6, n1_, n2_), flush=True)
d1 = vss
json.dump(dict(axis=a.axis, beta=a.beta, beta_w=a.beta_w, N=N, dx=dx,
               v_per_step=d1 / max(n2_ - n1_, 1)), 
          open('results_plane_%s.json' % a.axis, 'w'), indent=1)
