#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_m6_route.py --- P0.3 隔离扫描（LATH_FACET_PLAN 4-P0）：
   同一 RVE、同一随机种子，只改**一个**因素，测 M6（界面法向 vs 配对相容法向）
   与 M4（变体畴长径比）。

用法：
  python3 _chk_m6_route.py --tag A --aniso 0.0
  python3 _chk_m6_route.py --tag B --aniso 0.4
  python3 _chk_m6_route.py --tag C --aniso 0.4 --pair 1
  python3 _chk_m6_route.py --tag D --aniso 0.9 --pair 1
  python3 _chk_m6_route.py --tag E --df 2e7 --aniso 0.4 --pair 1

口径（与 _chk_morph.py 的 M4/M6 **逐字一致**）：
  M6 用平滑指示场 chi=gaussian_filter(reg==k0, 1.5) 的梯度当界面法向，
     与 ncomp(k,l)（= `g.ncmp`，同一张表）比夹角；随机对照 = 同一批采样方向。
  M4 用惯性张量的半轴比（长:短）。
"""
import argparse, json, os, time
import numpy as np
from scipy import ndimage as ndi

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

ap = argparse.ArgumentParser()
ap.add_argument('--tag', required=True)
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx', type=float, default=1e-8)
ap.add_argument('--df', type=float, default=1e8)
ap.add_argument('--aniso', type=float, default=0.0)
ap.add_argument('--pair', type=int, default=0)
ap.add_argument('--nstep', type=int, default=120)
ap.add_argument('--cfl', type=float, default=0.15)
ap.add_argument('--nseed', type=int, default=12)
ap.add_argument('--rfrac', type=float, default=0.22)
ap.add_argument('--plate_dx', type=float, default=2.0)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--workers', type=int, default=4)
ap.add_argument('--aniso_elastic', type=int, default=0)
ap.add_argument('--mob_aniso', type=float, default=0.0)
ap.add_argument('--pin_min', type=int, default=1)
ap.add_argument('--mob_beta', type=float, default=0.0)
ap.add_argument('--mob_beta_w', type=float, default=0.0)
ap.add_argument('--nplate', type=int, default=1)
ap.add_argument('--elong', type=float, default=1.0)   # 种子的面内长/宽比
ap.add_argument('--noelastic', type=int, default=0)  # 1 = 关弹性驱动（隔离用）
ap.add_argument('--gamma', type=float, default=0.15)  # 界面能（0 = 去掉曲率项）
ap.add_argument('--adv_grad', default='central')      # |grad phi| 格式：upwind / central
ap.add_argument('--reinit_every', type=int, default=25)
ap.add_argument('--only_measure', default='')
args = ap.parse_args()

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
N, dx, L = args.N, args.dx, args.N * args.dx

# ---------- 同一随机种子的初始化（保证各档只差被隔离的因素）----------
rng = np.random.default_rng(args.seed)
npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn

g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=args.gamma, Mob=1e-9,
                    df=[0.0] + [args.df] * nv, workers=args.workers,
                    reinit_every=args.reinit_every,
                    aniso_elastic=bool(args.aniso_elastic))
if args.noelastic:
    g.pf = None          # 隔离：关掉弹性驱动（ed == 0），wtab 已在 __init__ 建好
    print('   [隔离] 弹性驱动已关闭')
R = args.rfrac * L
t_seed = args.plate_dx * dx
for v in range(nv):
    _wv = None
    if getattr(g, 'wtab', None) is not None and np.isfinite(g.wtab[v + 1]).all():
        _wv = g.wtab[v + 1]
    _al = np.cross(npref[v + 1], _wv) if _wv is not None else None
    if _al is not None:
        _al = _al / (np.linalg.norm(_al) + 1e-300)
    for _ in range(args.nplate):
        c0 = rng.random(3) * (L - 2 * R) + R
        g.seed_plate(v + 1, c0, npref[v + 1], R, t_seed,
                     elong=args.elong, along=_al)
g.init_parent()
g.c[:] = 0.036

print('=== M6-route [%s]: N=%d dx=%.1f nm L=%.3f um df=%.1e aniso=%.2f pair=%d '
      'aniso_elastic=%d reinit=%d mob_aniso=%.2f pin_min=%d ==='
      % (args.tag, N, dx * 1e9, L * 1e6, args.df, args.aniso, args.pair,
         args.aniso_elastic, args.reinit_every, args.mob_aniso, args.pin_min), flush=True)
_v0 = np.array([g.volume(k) for k in range(g.nreg)])
print('   初始体积分数 %s' % np.round(_v0 / _v0.sum(), 4), flush=True)

M = 1e-9
# ★ 记账（smoke 抓到）：初始 dt 若只按 |df| 估，**第一步位移实测 0.994 dx**（超 CFL 3 倍以上）
#   —— 弹性项在界面带上中位是 df 的 ~5 倍（M2 已记账）。超 CFL 会让一阶迎风失真，
#   这正是 WINDOWB_SURFACE_AUDIT 里 M2 "塌缩"的真凶。改成用**实测弹性驱动**估上界。
_ed0 = g.elastic_driving()
_dg_est = abs(args.df) + 2.0 * float(np.max(np.abs(_ed0)))
dt = args.cfl * dx / (M * _dg_est)
print('   dt0 = %.3e s (按估 dG=%.2e 定；首步位移应 <=%.2f dx)'
      % (dt, _dg_est, args.cfl), flush=True)
t0 = time.time()
hist = []
stall = 0
for it in range(1, args.nstep + 1):
    ed_before = None
    g.advance(dt, aniso=args.aniso, npref=npref, band_cells=20,
              pair_aniso=bool(args.pair), mob_aniso=args.mob_aniso,
              pin_min=bool(args.pin_min), mob_beta=args.mob_beta,
              mob_beta_w=args.mob_beta_w, adv_grad=args.adv_grad)
    reg = g.region()
    f = 1.0 - float((reg == 0).mean())
    vt = np.array([g.volume(k) for k in range(g.nreg)], float)
    alive = int((vt[1:] > 0).sum())
    hist.append(dict(step=it, t=t0 and (it * dt), f=f, alive=alive,
                     dt=dt, dG=g.dG_max, vn=dt * g.dG_max * M / dx))
    if it % 20 == 0 or it == 1:
        print('   step %4d  f=%.4f  存活=%2d  位移=%.3f dx  用时 %.0f s'
              % (it, f, alive, hist[-1]['vn'], time.time() - t0), flush=True)
    nd = g.suggest_dt(cfl=args.cfl, dt_prev=dt)
    if nd:
        dt = nd
    if f > 0.999:
        break
wall = time.time() - t0

# ---------- 测量（与 _chk_morph.py 逐字同口径）----------
reg = g.region()
cnt = np.bincount(reg.ravel(), minlength=nv + 1).astype(float)
alive = [v + 1 for v in range(nv) if cnt[v + 1] > 0]
V = L ** 3

# M4 长径比
m4 = {}
X, Y, Z = np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij')
for v in alive:
    m = (reg == v)
    n = int(m.sum())
    if n < 50:
        continue
    p = np.stack([X[m], Y[m], Z[m]], 1).astype(float)
    p -= p.mean(0)
    ev = np.sort(np.clip(np.linalg.eigvalsh(np.cov(p.T)), 1e-30, None))[::-1]
    m4[v] = (ev[0] / ev[2]) ** .5
ar_all = (np.max((g.volume(j) for j in range(g.nreg))),)
# 面积加权长径比
wts = np.array([cnt[v] for v in m4]); ars = np.array([m4[v] for v in m4])
m4_med = float(np.median(ars)) if ars.size else float('nan')
m4_wavg = float((wts * ars).sum() / wts.sum()) if ars.size else float('nan')

# M5 界面配对（只取非母相）
pair = {}
for ax in range(3):
    a, b = reg, np.roll(reg, -1, axis=ax)
    sel = (a != b)
    ka, kb = a[sel], b[sel]
    for x, y in zip(ka.ravel(), kb.ravel()):
        if x == 0 or y == 0:
            continue
        kk = (min(x, y), max(x, y))
        pair[kk] = pair.get(kk, 0) + 1
tot = sum(pair.values()) or 1

# M6
rng2 = np.random.default_rng(0)
ns = rng2.normal(size=(600, 3))
ns /= np.linalg.norm(ns, axis=1)[:, None]
angs, angs_rnd = [], []
for kk, v in pair.items():
    if v < 30:
        continue
    chi = ndi.gaussian_filter((reg == kk[0]).astype(float), 1.5)
    gr = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8)
    nn = np.moveaxis(gr, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0] == 0:
        continue
    ncl = g.ncmp[kk[0], kk[1]]
    if not np.isfinite(ncl).all():
        continue
    c = np.abs(nn @ ncl)
    angs.append(np.degrees(np.arccos(np.clip(c, 0, 1))))
    angs_rnd.append(np.degrees(np.arccos(np.clip(np.abs(ns @ ncl), 0, 1))))
angs = np.concatenate(angs) if angs else np.array([np.nan])
angs_rnd = np.concatenate(angs_rnd) if angs_rnd else np.array([np.nan])

# M3 界面密度
bonds = 0
for ax in range(3):
    bonds += int((reg != np.roll(reg, -1, axis=ax)).sum())
Sv = bonds * dx ** 2 / V
f = 1.0 - cnt[0] / N ** 3

out = dict(tag=args.tag, N=N, dx=dx, df=args.df, aniso=args.aniso, pair=args.pair,
           aniso_elastic=args.aniso_elastic, reinit_every=args.reinit_every,
           mob_aniso=args.mob_aniso, pin_min=args.pin_min, mob_beta=args.mob_beta,
           mob_beta_w=args.mob_beta_w, elong=args.elong,
           nstep=len(hist), wall=wall, s_per_step=wall / max(len(hist), 1),
           f=f, alive=len(alive), alive_list=alive,
           frac=[float(cnt[v] / N ** 3) for v in range(1, nv + 1)],
           M3_Sv=Sv, M3_t_plate=2 * f / max(Sv, 1e-30),
           M4_ar_med=m4_med, M4_ar_wavg=m4_wavg, M4_per_variant=m4,
           M6_med=float(np.median(angs)), M6_n=int(angs.size),
           M6_rnd=float(np.median(angs_rnd)),
           M5_top={('%d-%d' % kk): float(v / tot)
                   for kk, v in sorted(pair.items(), key=lambda t: -t[1])[:6]},
           hist=hist)
json.dump(out, open('results_m6route_%s.json' % args.tag, 'w'), indent=1)
np.savez_compressed('results_m6route_%s_final.npz' % args.tag, reg=reg, N=N, dx=dx,
                    f=f, ncmp=g.ncmp)
print('--- [%s] f=%.4f 存活=%d/12  M6 中位 %.1f deg (随机 %.1f, n=%d)  '
      'M4 中位 %.2f  M3 t_plate=%.3f um  墙钟 %.0f s'
      % (args.tag, f, len(alive), np.median(angs), np.median(angs_rnd), angs.size,
         m4_med, out['M3_t_plate'] * 1e6, wall), flush=True)
