#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_m8_mobpin.py --- 判据 D8：**界面迁移率各向异性（facet pinning）**正对照。

背景（P0.3 实测）：在真实驱动力 df = dG_chem(M_s) = 1e8 J/m^3 下，
  界面能各向异性 gamma(n) 的强度从 0 调到 0.9（凸界极限）对界面取向**零效果**
  （M6 中位恒为 55.4 deg）=> "界面能 vs 驱动力"的幅度竞争不成立。
  W1 的正对照之所以 PASS，是因为它用 df=0（无驱动力）—— 与本结论自洽。

本判据测的是**另一条通道**：M(n) = M0*[1 - a*(1-(n.mref)^2)]。
  * 它是**动力学**量，无热力学凸性约束 => 强度可任意大
  * 判据 D8：a >= 0.5 时，末态界面法向 vs mref 的夹角中位应显著低于随机
    （随机约 57 deg）；且 a 增大时单调下降、长径比增大
  * 同时给 a=0 的正对照（应 ≈ 随机）

用法：python3 _chk_m8_mobpin.py            （4 档并行由 _run_m8.py 驱动）
      python3 _chk_m8_mobpin.py --a 0.0 --tag a00
"""
import argparse, json, time
import numpy as np

import windowB_surface as W

ap = argparse.ArgumentParser()
ap.add_argument('--a', type=float, default=0.0)
ap.add_argument('--tag', default='')
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx', type=float, default=2e-9)
ap.add_argument('--R0', type=float, default=1.2e-8)
ap.add_argument('--df', type=float, default=1e8)
ap.add_argument('--nstep', type=int, default=300)
ap.add_argument('--mref', default='0,0,1')
ap.add_argument('--M', type=float, default=1e-9)
ap.add_argument('--gamma', type=float, default=0.15)
ap.add_argument('--reinit_every', type=int, default=20)
args = ap.parse_args()
tag = args.tag or ('a%03d' % int(args.a * 100))
mref = np.array([float(v) for v in args.mref.split(',')])
mref = mref / np.linalg.norm(mref)

N, dx, L = args.N, args.dx, args.N * args.dx
g = W.LevelSetSurface(N, L, gamma=args.gamma, Mob=args.M, R0=args.R0,
                      reinit_every=args.reinit_every)
V0 = g.volume()
v0 = abs(args.df) * args.M
dt = 0.05 * dx / max(v0, 1e-30)
print('=== D8 mob_aniso=%.2f  N=%d dx=%.2f nm R0=%.1f nm df=%.1e mref=%s dt=%.2e'
      % (args.a, N, dx * 1e9, args.R0 * 1e9, args.df, mref, dt), flush=True)
t0 = time.time()
for it in range(1, args.nstep + 1):
    g.advance(dt, df=args.df, mob_aniso=args.a, mref=mref)
    if it % 60 == 0:
        print('   step %4d  V/V0=%.4f  用时 %.0f s'
              % (it, g.volume() / V0, time.time() - t0), flush=True)

# ---------- 测末态：界面法向 vs mref ----------
#  ★ 记账：interface_points 返回 (P (M,3), N (M,3)) **两元组**，不是单个数组
#    （第一版把元组当数组 moveaxis，报 "m has more than 2 dimensions" ✗）。
#    它给的是**一阶投影到零等值面**的法向，比 normal()[mask] 的逐胞台阶更准。
pts, nrm_if = g.interface_points(1.5)
nrm_if = nrm_if / (np.linalg.norm(nrm_if, axis=1, keepdims=True) + 1e-300)
ang = np.degrees(np.arccos(np.clip(np.abs(nrm_if @ mref), 0, 1)))
rng = np.random.default_rng(0)
ns = rng.normal(size=(20000, 3)); ns /= np.linalg.norm(ns, axis=1)[:, None]
ang_rnd = np.degrees(np.arccos(np.clip(np.abs(ns @ mref), 0, 1)))

pts_c = pts - pts.mean(0)
Cv = np.cov(pts_c.T)
ev, evec = np.linalg.eigh(Cv)
o = np.argsort(ev)[::-1]
ev = ev[o]; evec = evec[:, o]
asp = float((ev[0] / max(ev[2], 1e-30)) ** 0.5)
ax_main = np.abs(evec[:, 0]) / (np.linalg.norm(evec[:, 0]) + 1e-300)
ang_ax = float(np.degrees(np.arccos(np.clip(abs(ax_main @ mref), 0, 1))))

np.savez_compressed('results_m8_%s_final.npz' % tag, phi=g.phi, dx=dx, N=N,
                    mref=mref, a=args.a, df=args.df)
out = dict(tag=tag, a=args.a, df=args.df, mref=list(mref), N=N, dx=dx, R0=args.R0,
           nstep=args.nstep, dV=float(g.volume() / V0),
           M8_ang_med=float(np.median(ang)), M8_ang_rnd=float(np.median(ang_rnd)),
           M8_ang_p25=float(np.percentile(ang, 25)),
           M8_n=int(ang.size), M8_asp=asp, M8_axis_ang=ang_ax,
           wall=time.time() - t0)
json.dump(out, open('results_m8_%s.json' % tag, 'w'), indent=1)
print('--- [%s] a=%.2f  V/V0=%.3f  界面法向 vs mref 中位 %.1f deg (随机 %.1f, n=%d)  '
      '长径比 %.2f  主轴 vs mref %.1f deg  墙钟 %.0f s'
      % (tag, args.a, out['dV'], out['M8_ang_med'], out['M8_ang_rnd'], out['M8_n'],
         asp, ang_ax, out['wall']), flush=True)
