#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prod_boxB.py --- 盒子 B 的**完整生产级轨迹**：L=20 µm @ Delta x=0.25 µm。

* 逐步记录：t / dt / step / f / 界面带胞 / S_v / 板片厚 / 12 个变体体积分数
* 停止：f >= F_STOP 或 t >= T_END 或 步数上限 或 **墙钟上限**（graceful）
* 产出：轨迹 CSV、末态 region 场 npz、以及**三个正交中面剖面图**（不同组织不同颜色）

性能：OMP_NUM_THREADS 由外面给； 给 FFT 线程数。物理设置（与 W-8c 同族）：
12 个晶核、R=4.4 µm、种子厚 0.5 µm（=2 胞）、df=+2e8（变体有利；三元闭合在 ~800 K 给 1.5e8 量级）。
"""
import csv
import json
import os
import time

import numpy as np

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

N, DX = 80, 0.25e-6
L = N * DX
DF = 2.0e8
R_M, T_SEED = 4.4e-6, 0.5e-6
NSEED = 12
CFL = 0.15
F_STOP = 0.90
T_END = 6.0e-5
MAX_STEPS = 1200
WALL_CAP = float(os.environ.get('PROD_WALL', '2400'))
WORKERS = int(os.environ.get('PROD_WORKERS', '8'))
TAG = 'boxB_N080_dx250nm'
print('=== prod_boxB: L=%.0f um  dx=%.3f um  N=%d  df=%.1e  wall_cap=%.0f s  workers=%d'
      % (L * 1e6, DX * 1e6, N, DF, WALL_CAP, WORKERS), flush=True)

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
rng = np.random.default_rng(4)
npf = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(200, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npf[v + 1] = bn

g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] * (nv + 1), workers=WORKERS, reinit_every=25)
seeds = []
for _ in range(NSEED):
    c = rng.random(3) * (L - 2 * R_M) + R_M
    k = int(rng.integers(1, nv + 1))
    g.seed_plate(k, c, npf[k], R_M, T_SEED)
    seeds.append((c.tolist(), k))
g.init_parent()
g.c[:] = 0.036
g.df[1:] = DF
f0 = 1.0 - float((g.region() == 0).mean())
print('   种子: %d 个, R=%.1f um, 厚=%.1f um -> 初始 f=%.4f' % (NSEED, R_M * 1e6, T_SEED * 1e6, f0), flush=True)

rows = []
t = 0.0
dt = CFL * DX / (1e-9 * DF)
t_start = time.time()
stop = 'max_steps'
for k in range(1, MAX_STEPS + 1):
    g.advance(dt, aniso=0.4, npref=npf, band_cells=20)
    g.update_Gamma(dt)
    t += dt
    reg = g.region()
    f = 1.0 - float((reg == 0).mean())
    nb, medg, okg = g.band_health()
    Sv = g.area_total_geom() / L ** 3
    vt = np.array([g.volume(j) for j in range(g.nreg)], float)
    mb, ms = g.totals()
    rows.append(dict(step=k, t=t, dt=dt, f=f, band=nb, band_ok=int(okg),
                     Sv=Sv, t_plate=2 * f / max(Sv, 1e-30),
                     unif=float(vt[1:].max() / max(vt[1:].min(), 1e-30)),
                     mol_bulk=mb, mol_face=ms,
                     **{'v%d' % (j + 1): float(vt[j + 1] / max(vt[1:].sum(), 1e-30))
                        for j in range(nv)}))
    nd = g.suggest_dt(cfl=CFL, dt_prev=dt)
    if nd:
        dt = nd
    if k % 50 == 0 or k == 1:
        print('   step %4d  t=%.3e s  f=%.4f  带=%6d %s  t_plate=%.3f um  用时 %.0f s'
              % (k, t, f, nb, 'OK' if okg else 'DEG', rows[-1]['t_plate'],
                 time.time() - t_start), flush=True)
    if f >= F_STOP:
        stop = 'f_stop'
        break
    if t >= T_END:
        stop = 't_end'
        break
    if time.time() - t_start > WALL_CAP:
        stop = 'wall_cap'
        break

wall = time.time() - t_start
print('=== 结束: %s ; steps=%d ; t=%.3e s ; f=%.4f ; 墙钟 %.1f s (%.2f s/步)'
      % (stop, len(rows), t, rows[-1]['f'], wall, wall / len(rows)), flush=True)

with open('results_%s_traj.csv' % TAG, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        w.writerow(r)
np.savez_compressed('results_%s_final.npz' % TAG, reg=g.region(), N=N, dx=DX,
                    f=rows[-1]['f'], Sv=rows[-1]['Sv'], t_plate=rows[-1]['t_plate'],
                    seeds=np.array([s[0] for s in seeds]), seed_v=np.array([s[1] for s in seeds]))
json.dump(dict(stop=stop, steps=len(rows), t=t, f=rows[-1]['f'], wall=wall,
               s_per_step=wall / len(rows), N=N, dx=DX, df=DF, NSEED=NSEED,
               R_M=R_M, T_SEED=T_SEED, wall_cap=WALL_CAP, workers=WORKERS),
          open('results_%s_summary.json' % TAG, 'w'), indent=1)
print('   已存 results_%s_traj.csv / _final.npz / _summary.json' % TAG, flush=True)
