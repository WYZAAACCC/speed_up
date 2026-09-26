#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_single_lath.py --- 判据 D11：**孤立单核**自由生长，测 M(n) 钉扎能否给出薄饼/板条。

为什么必须做这个（记账）：
  生产配置的三档都有核重叠（hi200 的 200 个核 R=2.5 um、间距仅 3.4 um => f0=0.33），
  "块"是**多核合并**的产物，测不出单根板条的形状。=> 用**一个核**做正对照：
    * beta=0   预期 各向同性 => 近球形（法向 extent ~ 面内 extent）
    * beta>0   预期 法向被钉住 => **薄饼**（面内 extent >> 法向 extent）
  判据 D11：aspect = 面内extent / 法向extent。
     beta=0  => aspect ~ 1.0（±0.2）
     beta=3.5 => aspect 应显著 > 1（理论量级 e^beta ~ 33 的上限，受生长时间限制）

  这是"钉扎机制到底对不对"的最直接判据，不掺任何邻居/重叠效应。
"""
import argparse, json, time
import numpy as np

import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

ap = argparse.ArgumentParser()
ap.add_argument('--beta', type=float, default=0.0)
ap.add_argument('--beta_w', type=float, default=0.0)
ap.add_argument('--facet', type=float, default=0.0)
ap.add_argument('--facet_eps', type=float, default=0.05)
ap.add_argument('--track', type=int, default=0)   # >0: 每 N 步记录主轴
ap.add_argument('--elong', type=float, default=1.0)  # 种子面内长/宽比（EXPERT-#1 起有越界检查）
ap.add_argument('--gamma', type=float, default=0.15)      # 0 = 关曲率项
ap.add_argument('--reinit_every', type=int, default=25)   # 0 = 关重初始化
ap.add_argument('--noelastic', type=int, default=0)       # 1 = 关弹性驱动
ap.add_argument('--tag', default='')
ap.add_argument('--N', type=int, default=64)
ap.add_argument('--dx', type=float, default=5e-8)
ap.add_argument('--R', type=float, default=3.0e-7)
ap.add_argument('--t', type=float, default=1.0e-7)
ap.add_argument('--df', type=float, default=2e8)
ap.add_argument('--nstep', type=int, default=300)
ap.add_argument('--cfl', type=float, default=0.15)
ap.add_argument('--variant', type=int, default=1)
ap.add_argument('--workers', type=int, default=4)
a = ap.parse_args()
tag = a.tag or ('b%03d' % int(a.beta * 10))

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
rng = np.random.default_rng(0)
npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn

N, dx, L = a.N, a.dx, a.N * a.dx
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=a.gamma, Mob=1e-9,
                    df=[0.0] + [a.df] * nv, workers=a.workers,
                    reinit_every=a.reinit_every)
if a.noelastic:
    g.pf = None      # 关弹性驱动（wtab 已在 __init__ 用 C 建好）
k = a.variant
_al = None
if a.elong > 1.0:
    _n = np.asarray(npref[k], float); _n /= np.linalg.norm(_n)
    _w = np.asarray(g.wtab[k], float) if getattr(g, 'wtab', None) is not None else None
    _al = np.cross(_n, _w) if _w is not None else np.array([1.0, 0.0, 0.0])
    _al /= (np.linalg.norm(_al) + 1e-300)
g.seed_plate(k, [L / 2, L / 2, L / 2], npref[k], a.R, a.t,
             elong=a.elong, along=_al)
g.init_parent()
g.c[:] = 0.036
V0 = g.volume(k)
_M = 1e-9
_ed = g.elastic_driving()
dt = a.cfl * dx / (_M * max(abs(a.df) + 2.0 * float(np.max(np.abs(_ed))), 1e-30))
print('=== D11 single-lath: beta=%.2f beta_w=%.2f facet=%.2f N=%d dx=%.1f nm L=%.2f um R=%.1f nm t=%.1f nm'
      % (a.beta, a.beta_w, a.facet, N, dx * 1e9, L * 1e6, a.R * 1e9, a.t * 1e9), flush=True)
t0 = time.time()
track = []
for it in range(1, a.nstep + 1):
    g.advance(dt, aniso=0.4, npref=npref, band_cells=20, mob_beta=a.beta,
              mob_beta_w=a.beta_w, facet_lam=a.facet, facet_eps=a.facet_eps)
    if it % 50 == 0:
        print('   step %4d  V/V0=%.2f  用时 %.0f s' % (it, g.volume(k) / V0, time.time() - t0),
              flush=True)
    nd = g.suggest_dt(cfl=a.cfl, dt_prev=dt)
    if nd:
        dt = nd
    if a.track and (it % a.track == 0):
        # ★ 逐时**主轴**跟踪（诊断"被压制方向增长最快"的反常）：
        #   用惯性张量特征向量当真主轴（不是任意正交基），并报告它与
        #   n_hab / w / a 三个物理方向的夹角 => 可判定"形状是否在转动"。
        _n1 = np.asarray(npref[k], float); _n1 /= np.linalg.norm(_n1)
        _w1 = np.asarray(g.wtab[k], float) if getattr(g, 'wtab', None) is not None else None
        _a1 = np.cross(_n1, _w1) if _w1 is not None else None
        _idx = np.argwhere(g.region() == k)
        if len(_idx) > 20:
            _p = _idx.astype(float) * dx
            _d = _p - _p.mean(0)
            _C = np.cov(_d.T)
            _ev, _evec = np.linalg.eigh(_C)
            _o = np.argsort(_ev)[::-1]
            _ev = _ev[_o]; _evec = _evec[:, _o]
            _ext = []
            for _j in range(3):
                _e = _d @ _evec[:, _j]
                _ext.append(float(_e.max() - _e.min()))
            def _ang(v, ref):
                if ref is None:
                    return float('nan')
                vv = np.abs(v / (np.linalg.norm(v) + 1e-300))
                rr = np.abs(np.asarray(ref, float) / (np.linalg.norm(ref) + 1e-300))
                return float(np.degrees(np.arccos(np.clip(vv @ rr, 0, 1))))
            track.append(dict(step=it, V=float(g.volume(k)),
                              ext=[e * 1e6 for e in _ext],
                              ang_n=[_ang(_evec[:, j], _n1) for j in range(3)],
                              ang_w=[_ang(_evec[:, j], _w1) for j in range(3)],
                              ang_a=[_ang(_evec[:, j], _a1) for j in range(3)]))
    if g.volume(k) / L ** 3 > 0.6:
        break

# ---------- 测形状（直接 extent，比惯性张量更贴合"薄饼"）----------
n1 = np.asarray(npref[k], float); n1 /= np.linalg.norm(n1)
# (fix) 面内两个方向必须用**物理轴 w / a**，不能用任意正交基
#       （任意基与 a/w 成角 => extent 只是投影，读不出长宽）。
w1_ = np.asarray(g.wtab[k], float) if getattr(g, 'wtab', None) is not None else None
if w1_ is not None and np.isfinite(w1_).all():
    t1 = w1_ / (np.linalg.norm(w1_) + 1e-300)      # 宽度方向 w
    t2 = np.cross(n1, t1)
    t2 /= (np.linalg.norm(t2) + 1e-300)            # 长轴方向 a = n x w
else:
    t1 = np.cross(n1, [0.0, 0.0, 1.0])
    t1 /= (np.linalg.norm(t1) + 1e-300)
    t2 = np.cross(n1, t1)
x = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
pts = np.stack([X, Y, Z], -1)
# 用 phi_k<0 作为该变体的体（LevelSetMulti 里 reg==k 更稳）
idx = np.argwhere(g.region() == k)
p = idx.astype(float) * dx
c0 = p.mean(0)
d = p - c0
ext_n = d @ n1
ext_1 = d @ t1
ext_2 = d @ t2
thick = ext_n.max() - ext_n.min()
side1 = ext_1.max() - ext_1.min()
side2 = ext_2.max() - ext_2.min()
side = 0.5 * (side1 + side2)
aspect = side / max(thick, 1e-30)
V = g.volume(k)
print('--- [%s] beta=%.2f beta_w=%.2f facet=%.2f  V/V0=%.2f  V=%.3f um^3' % (tag, a.beta, a.beta_w, a.facet, V / V0, V * 1e18))
print('    厚(沿 n_hab) = %.3f um ; 宽(沿 w) = %.3f um ; 长(沿 a) = %.3f um'
      % (thick * 1e6, side1 * 1e6, side2 * 1e6))
print('    **长/厚 = %.2f**  **宽/厚 = %.2f**  长/宽 = %.2f  (面内均值/厚 = %.2f)'
      % (side2 / max(thick, 1e-30), side1 / max(thick, 1e-30),
         side2 / max(side1, 1e-30), aspect))
print('    **aspect = 面内/法向 = %.2f**  (beta=0 应 ~1.0)' % aspect)
if a.track:
    with open('results_single_%s_track.csv' % tag, 'w') as fh:
        print('step,V_um3,e1_um,e2_um,e3_um,ang_n1,ang_n2,ang_n3,ang_w1,ang_w2,ang_w3,ang_a1,ang_a2,ang_a3',
              file=fh)
        for r in track:
            print('%d,%.5f,%.4f,%.4f,%.4f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f'
                  % (r['step'], r['V'] * 1e18, r['ext'][0], r['ext'][1], r['ext'][2],
                     r['ang_n'][0], r['ang_n'][1], r['ang_n'][2],
                     r['ang_w'][0], r['ang_w'][1], r['ang_w'][2],
                     r['ang_a'][0], r['ang_a'][1], r['ang_a'][2]), file=fh)
    print('   已存 results_single_%s_track.csv (%d 行)' % (tag, len(track)))
json.dump(dict(tag=tag, beta=a.beta, beta_w=a.beta_w, facet=a.facet, V=V, V0=V0, thick=thick, side1=side1, side2=side2,
               side=side, aspect=aspect, npref=list(n1), N=N, dx=dx, R=a.R, t=a.t,
               variant=k, wall=time.time() - t0),
          open('results_single_%s.json' % tag, 'w'), indent=1)
