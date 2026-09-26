#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可靠口径重测：界面位移用**射线交点**（iface_crossings 同一思想），不用中位数分箱。"""
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants(); nv = 12
rng = np.random.default_rng(0); npref = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5*float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best: best, bn = val, n
    npref[v+1] = bn

N, dx = 48, 5e-8
L = N*dx
x = (np.arange(N)+0.5)*dx
X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
BH, BW = 3.5, 2.3
M = 1e-9

def ray_pos(g, k, DIR):
    """从域中心沿 +DIR/−DIR 找 phi_k=0，返回两侧平均位置（沿 DIR 的投影值）"""
    c0 = np.array([L/2]*3)
    vals = []
    for sgn in (+1.0, -1.0):
        ts = np.arange(0.0, L/2, dx*0.1)
        pts = c0[None,:] + sgn*ts[:,None]*DIR[None,:]
        idx = np.floor(pts/dx).astype(int)
        ok = ((idx>=0).all(1)) & ((idx<N).all(1))
        idx = idx[ok]; tt = ts[ok]
        v = g.phi[k][idx[:,0], idx[:,1], idx[:,2]]
        neg = np.where(v < 0)[0]
        if len(neg)==0: continue
        i = neg[-1]
        if i >= len(tt)-1: continue
        r = tt[i] - v[i]*(tt[i+1]-tt[i])/(v[i+1]-v[i])
        vals.append(r)
    return float(np.mean(vals)) if vals else np.nan

print('%-8s %-10s %11s %11s %9s' % ('grad','DIR','位移(um)','预测(um)','比值'))
for advg in ('upwind','central'):
    for nm in ('n_hab','w','a','tilt'):
        g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=M,
                            df=[0.0]+[2e8]*nv, workers=2, reinit_every=0)
        k = 1
        DIR = {'n_hab': np.asarray(npref[k],float),
               'w': np.asarray(g.wtab[k],float),
               'a': np.cross(npref[k], g.wtab[k]),
               'tilt': np.array([1.,1.,1.])/np.sqrt(3)}[nm]
        DIR = DIR/np.linalg.norm(DIR)
        proj = X*DIR[0]+Y*DIR[1]+Z*DIR[2]
        g.phi[k] = proj - 0.5*(proj.min()+proj.max())
        g.init_parent(); g.c[:] = 0.036
        g.pf = None
        dt = 0.15*dx/(M*2e8)
        r0 = ray_pos(g,k,DIR)
        g.advance(dt, aniso=0.0, npref=npref, band_cells=6, mob_beta=BH, mob_beta_w=BW, adv_grad=advg)
        r1 = ray_pos(g,k,DIR)
        d = r1-r0
        n_ = np.asarray(npref[k],float); n_/=np.linalg.norm(n_)
        w_ = np.asarray(g.wtab[k],float); w_/=np.linalg.norm(w_)
        Mfac = float(np.exp(-BH*(DIR@n_)**2 - BW*(DIR@w_)**2))
        pred = M*2e8*Mfac*dt
        print('%-8s %-10s %11.4e %11.4e %9.3f' % (advg, nm, d, pred, d/pred if pred else np.nan))
