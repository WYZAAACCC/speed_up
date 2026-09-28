#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_faces2.py --- 上接 _audit_faces.py：加**主轴跟踪 + 带健康度 + 逐面速度**，
   用来定位"各向异性随时间退化（等轴化）"的机制。
   全部关掉弹性/曲率/重初始化 ⇒ 剩下的只有「推进格式 + 速度延拓」。
"""
import os, sys, time
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants
import windowB_surface as W

BH, BW = 3.5, 2.3
N, dx, k = 96, 2e-8, 1
L = N * dx
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
rng = np.random.default_rng(0)
npref = {}
for v in range(len(eps0)):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn

import argparse
_ap = argparse.ArgumentParser(); _ap.add_argument('--reinit', type=int, default=0)
_ap.add_argument('--adv', default='proj2'); _ap.add_argument('--nstep', type=int, default=160)
# ★ 2026-09-28（Round 137，`_chk_advgrad.py` 抓到）：默认值原为 `'central'`
#   ⇒ 它会**静默覆盖**引擎经 D17 改成 `'proj2'` 的默认。要复现 D17 之前的读数请**显式**传 `central`。
_args = _ap.parse_args()

g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.0, Mob=1e-9,
                    df=[0.0] + [2e8] * len(eps0), workers=4,
                    reinit_every=_args.reinit)
g.pf = None
print('### reinit_every=%d  adv_grad=%s  nstep=%d' % (_args.reinit, _args.adv, _args.nstep))
n_h = np.asarray(npref[k], float); n_h /= np.linalg.norm(n_h)
wv = np.asarray(g.wtab[k], float); wv = wv - (wv @ n_h) * n_h; wv /= np.linalg.norm(wv)
av = np.cross(n_h, wv); av /= np.linalg.norm(av)
cen = np.array([L / 2] * 3)
rel = g.XYZ - cen
d_n = rel @ n_h; d_w = rel @ wv; d_a = rel @ av
sdf = np.maximum(np.maximum(np.abs(d_n) - 1.0e-7, np.abs(d_w) - 1.0e-7), np.abs(d_a) - 2.5e-7)
g.phi[k] = np.minimum(g.phi[k], sdf)
for j in range(g.nreg):
    if j != k:
        g.phi[j] = np.maximum(g.phi[j], -sdf)
g.init_parent()


def ray(u):
    s = np.arange(0, int(N * 0.49)) * dx
    pts = cen[None, :] + s[:, None] * u[None, :]
    idx = pts / dx - 0.5
    i0 = np.clip(np.floor(idx).astype(int), 0, N - 2)
    ok = np.all((idx >= 0) & (idx <= N - 2), axis=1)
    fr = idx - i0
    f = g.phi[k]
    vv = np.zeros(len(s))
    for c in range(8):
        o = np.array([(c >> 0) & 1, (c >> 1) & 1, (c >> 2) & 1])
        wgt = np.prod(np.where(o == 1, fr, 1 - fr), axis=1)
        vv += wgt * f[i0[:, 0] + o[0], i0[:, 1] + o[1], i0[:, 2] + o[2]]
    vv = np.where(ok, vv, np.nan)
    sg = np.zeros(len(s) - 1, bool)
    fin = ~np.isnan(vv[:-1]) & ~np.isnan(vv[1:])
    sg[fin] = vv[:-1][fin] * vv[1:][fin] < 0
    if not sg.any():
        return np.nan
    i = int(np.argmax(sg))
    t = vv[i] / (vv[i] - vv[i + 1])
    return s[i] + t * dx


dt = 0.15 * dx / (1e-9 * 2e8)
print('step  dt(ns)   r_n     r_w     r_a   | e1/e2/e3 (um) & 长轴与a夹角 | band  | med|grad| | iface   主轴角(a/w/n)')
t0 = time.time()
prev = None
for it in range(1, _args.nstep + 1):
    g.advance(dt, aniso=0.4, npref=npref, band_cells=20, mob_beta=BH, mob_beta_w=BW,
              adv_grad=_args.adv)
    nd = g.suggest_dt(cfl=0.15, dt_prev=dt)
    if nd:
        dt = nd
    if it % 20 == 0:
        rn, rw, ra = ray(n_h), ray(wv), ray(av)
        idx = np.argwhere(g.region() == k)
        p = idx.astype(float) * dx - cen
        Cv = np.cov(p.T)
        ev, evec = np.linalg.eigh(Cv)
        o = np.argsort(ev)[::-1]; ev = ev[o]; evec = evec[:, o]
        ext = [(p @ evec[:, j]).max() - (p @ evec[:, j]).min() for j in range(3)]
        ang = [np.degrees(np.arccos(np.clip(abs(evec[:, j] @ av), 0, 1))) for j in range(3)]
        # 带健康度
        phiw = np.take_along_axis(g.phi, np.argmin(g.phi, axis=0)[None], 0)[0]
        gr = np.gradient(phiw, dx)
        gn = np.sqrt(sum(t ** 2 for t in gr))
        bnd = np.abs(phiw) <= 2 * dx
        # iface 胞数（|phi_winner| <= 2dx 且 |v_cell|>0）
        print('%-5d %-8.3f %-7.4f %-7.4f %-7.4f | %.4f %.4f %.4f | a1=%4.1f a2=%4.1f a3=%4.1f | %6d | %6.3f | %6d'
              % (it, dt * 1e9, rn * 1e6, rw * 1e6, ra * 1e6,
                 ext[0] * 1e6, ext[1] * 1e6, ext[2] * 1e6,
                 ang[0], ang[1], ang[2],
                 int(bnd.sum()), float(np.median(gn[bnd])), int((np.abs(phiw) <= 2 * dx).sum())),
              flush=True)
print('用时 %.0f s' % (time.time() - t0))
