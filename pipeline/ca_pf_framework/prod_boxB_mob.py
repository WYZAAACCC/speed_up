#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prod_boxB_mob.py --- 生产配置（L=20 um @ dx=0.25 um）的**带 M(n) 物理各向异性**版本。

★ 本文件是 prod_boxB.py 的**副本**（不改原文件）：只加 mob_beta 与逐步全量记录 + phi 定期存档。

物理（LATH_FACET_PLAN §9）：
  M(n) = M0 * exp[-beta (n.n_hab)^2],  beta = dG_misfit/(k_B T) = 3.5（带 [3,6]）
  n_hab：变体 k 对母相 = npref[k]；变体 k 与 l 之间 = ncmp[k,l]（rank-1 不变平面）

记录（用户要求"每一步产生的所有数据"）：
  * **每一步**：step/t/dt/f/带胞/band_ok/S_v/t_plate/12 个变体体积/体+面摩尔守恒/dG_max/位移(dx)
  * **每 SNAP 步**：phi 场（float32）存档 + M6p/M4/连通性/界面配对
  ★ 记账：phi 场全步存 = 13*80^3*8B*871 = 46 GB（不可行）=> 折中为每 SNAP=10 步存 float32
    （26 MB/次，~90 次 ~2.3 GB）。**标量数据仍是每一步**。
"""
import csv, json, os, time
import numpy as np
from scipy import ndimage as ndi

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

N, DX = 80, 0.25e-6
L = N * DX
DF = 2.0e8
BETA = float(os.environ.get('PROD_BETA', '3.5'))
R_M = float(os.environ.get('PROD_RM', '4.4e-6'))
T_SEED = float(os.environ.get('PROD_TSEED', '0.5e-6'))
NSEED = int(os.environ.get('PROD_NSEED', '12'))
CFL = 0.15
F_STOP = float(os.environ.get('PROD_FSTOP', '0.90'))
T_END = 6.0e-5
MAX_STEPS = int(os.environ.get('PROD_MAXSTEP', '1200'))
WALL_CAP = float(os.environ.get('PROD_WALL', '5400'))
WORKERS = int(os.environ.get('PROD_WORKERS', '8'))
SNAP = int(os.environ.get('PROD_SNAP', '10'))
TAG = os.environ.get('PROD_TAG', 'boxB_mob_beta350')

print('=== prod_boxB_mob: L=%.0f um dx=%.3f um N=%d df=%.1e beta=%.2f wall=%.0f s snap=%d'
      % (L * 1e6, DX * 1e6, N, DF, BETA, WALL_CAP, SNAP), flush=True)

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
print('   种子 %d 个 R=%.1f um 厚=%.1f um -> f0=%.4f' % (NSEED, R_M * 1e6, T_SEED * 1e6, f0), flush=True)

# ---------- 测量工具（与 _chk_m6p.py 同口径）----------
rng2 = np.random.default_rng(0)
nsr = rng2.normal(size=(600, 3)); nsr /= np.linalg.norm(nsr, axis=1)[:, None]


def measure(reg, dx):
    nreg = nv + 1
    cnt = np.bincount(reg.ravel(), minlength=nreg).astype(float)
    V = (N * dx) ** 3
    bonds = 0
    pair = {}
    for ax in range(3):
        a, b = reg, np.roll(reg, -1, axis=ax)
        sel = (a != b)
        bonds += int(sel.sum())
        ka, kb = a[sel], b[sel]
        for x, y in zip(ka.ravel(), kb.ravel()):
            if x == 0 or y == 0:
                continue
            kk = (min(x, y), max(x, y))
            pair[kk] = pair.get(kk, 0) + 1
    Sv = bonds * dx ** 2 / V
    f = 1.0 - cnt[0] / N ** 3
    # M4 长径比
    X, Y, Z = np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij')
    m4 = {}
    for v in range(1, nreg):
        m = (reg == v)
        n = int(m.sum())
        if n < 50:
            continue
        p = np.stack([X[m], Y[m], Z[m]], 1).astype(float)
        p -= p.mean(0)
        ev = np.sort(np.clip(np.linalg.eigvalsh(np.cov(p.T)), 1e-30, None))[::-1]
        m4[v] = (ev[0] / ev[2]) ** .5
    # M6p：变体-母相界面法向 vs npref
    par = ndi.binary_dilation(reg == 0, iterations=2)
    angs = []
    for k in range(1, nreg):
        if cnt[k] < 200:
            continue
        chi = ndi.gaussian_filter((reg == k).astype(float), 1.5)
        gr = np.array(np.gradient(chi, dx))
        bnd = (chi > 0.2) & (chi < 0.8) & par
        nn = np.moveaxis(gr, 0, -1)[bnd]
        nrm = np.linalg.norm(nn, axis=1)
        nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
        if nn.shape[0] == 0:
            continue
        nd = npf[k]
        angs.append(np.degrees(np.arccos(np.clip(np.abs(nn @ nd), 0, 1))))
    m6p = float(np.median(np.concatenate(angs))) if angs else float('nan')
    # 连通性
    nblk = {}
    for v in range(1, nreg):
        if cnt[v] < 50:
            continue
        lab, nb = ndi.label(reg == v, structure=np.ones((3, 3, 3)))
        sz = np.bincount(lab.ravel())[1:]
        nblk[v] = (int(nb), int(sz.max()), int(sz.sum()))
    return dict(f=f, Sv=Sv, t_plate=2 * f / max(Sv, 1e-30), M4=m4, M6p=m6p,
                nblk=nblk, pair={'%d-%d' % k: v for k, v in pair.items()})


rows, snaps = [], []
t = 0.0
dt = CFL * DX / (1e-9 * DF)
t_start = time.time()
stop = 'max_steps'
SNAPDIR = 'prod_mob_snap_' + TAG
os.makedirs(SNAPDIR, exist_ok=True)
for k in range(1, MAX_STEPS + 1):
    g.advance(dt, aniso=0.4, npref=npf, band_cells=20, mob_beta=BETA)
    g.update_Gamma(dt)
    t += dt
    reg = g.region()
    f = 1.0 - float((reg == 0).mean())
    nb, medg, okg = g.band_health()
    vt = np.array([g.volume(j) for j in range(g.nreg)], float)
    mb, ms = g.totals()
    rows.append(dict(step=k, t=t, dt=dt, f=f, band=nb, band_ok=int(okg), dG=g.dG_max,
                     disp=dt * g.dG_max * 1e-9 / DX,
                     mol_bulk=mb, mol_face=ms,
                     **{'v%d' % (j + 1): float(vt[j + 1] / max(vt[1:].sum(), 1e-30))
                        for j in range(nv)}))
    if k % SNAP == 0 or k == 1:
        mm = measure(reg, DX)
        mm.update(step=k, t=t)
        snaps.append(mm)
        np.savez_compressed(os.path.join(SNAPDIR, 'phi_%04d.npz' % k),
                            phi=g.phi.astype(np.float32), reg=reg.astype(np.int8),
                            t=t, f=f)
    if k % 20 == 0 or k == 1:
        print('   step %4d  t=%.3e  f=%.4f  M6p=%.1f  M4=%.2f  带=%6d %s  %.0f s'
              % (k, t, f, snaps[-1]['M6p'], np.median(list(snaps[-1]['M4'].values()))
                 if snaps[-1]['M4'] else float('nan'), nb, 'OK' if okg else 'DEG',
                 time.time() - t_start), flush=True)
    nd = g.suggest_dt(cfl=CFL, dt_prev=dt)
    if nd:
        dt = nd
    if f >= F_STOP:
        stop = 'f_stop'; break
    if t >= T_END:
        stop = 't_end'; break
    if time.time() - t_start > WALL_CAP:
        stop = 'wall_cap'; break

wall = time.time() - t_start
print('=== 结束: %s steps=%d t=%.3e f=%.4f 墙钟 %.0f s (%.2f s/步)'
      % (stop, len(rows), t, rows[-1]['f'], wall, wall / len(rows)), flush=True)
with open('results_%s_traj.csv' % TAG, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows:
        w.writerow(r)
json.dump(dict(stop=stop, steps=len(rows), t=t, f=rows[-1]['f'], wall=wall, N=N, dx=DX,
               df=DF, beta=BETA, NSEED=NSEED, R_M=R_M, T_SEED=T_SEED, snap=SNAP,
               seeds=[(s[0], s[1]) for s in seeds], snaps=snaps),
          open('results_%s_summary.json' % TAG, 'w'), indent=1)
np.savez_compressed('results_%s_final.npz' % TAG, reg=g.region(), phi=g.phi.astype(np.float32),
                    N=N, dx=DX, f=rows[-1]['f'], t=t, ncmp=g.ncmp,
                    npref=np.array([npf[j] for j in range(1, nv + 1)]))
print('   已存 results_%s_traj.csv / _summary.json / _final.npz + prod_mob_snap/' % TAG, flush=True)
