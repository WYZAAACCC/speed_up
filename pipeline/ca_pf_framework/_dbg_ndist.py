#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_ndist.py --- 判据：界面法向分布随时间的演化（定位"厚度增长最快"的机制）。
   记录界面带内 c2 = (ndir . n_hab)^2 的中位数与"大面占比" P(c2>0.8)。
   若大面占比随时间下降 => 界面变斜 => Mfac 的压制被自动稀释（自我放大）。"""
import numpy as np, sys, time
sys.path.insert(0,'.')
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0,_F,_m = variants(); nv=12
rng=np.random.default_rng(0); npref={}
for v in range(nv):
    best,bn=None,None
    for n in rng.normal(size=(400,3)):
        n=n/np.linalg.norm(n)
        val=0.5*float(np.einsum('ij,ijkl,kl->',eps0[v],_lam_full(C,n),eps0[v]))
        if best is None or val<best: best,bn=val,n
    npref[v+1]=bn

N,dx=80,2e-8; L=N*dx
g = W.LevelSetMulti(N,L,C=C,eps0=eps0,gamma=0.0,Mob=1e-9,
                    df=[0.0]+[2e8]*nv, workers=8, reinit_every=0)
k=1
n_h = np.asarray(npref[k],float); n_h/=np.linalg.norm(n_h)
wv = np.asarray(g.wtab[k],float)
al = np.cross(n_h, wv); al/=np.linalg.norm(al)
R, t = 1.2e-7, 2.0e-7
g.seed_plate(k,[L/2]*3, n_h, R, t, elong=6.0, along=al)
g.init_parent(); g.c[:]=0.036
g.pf=None
M=1e-9; dt=0.15*dx/(M*2e8)
print('界面法向分布（变体-母相界面带内）')
print('%-6s %-9s %-8s %-9s %-9s %-9s %-9s' %
      ('step','V(um^3)','带胞','med c2','P(c2>0.8)','P(c2<0.2)','med|n.w|'))
t0=time.time()
for it in range(1, 251):
    g.advance(dt, aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
              adv_grad='central')
    if it % 25 == 0:
        order=np.argsort(g.phi,axis=0); karr,larr=order[0],order[1]
        pha=np.take_along_axis(g.phi,karr[None],0)[0]
        phb=np.take_along_axis(g.phi,larr[None],0)[0]
        gd=np.gradient(pha-phb,dx)
        gn=np.sqrt(sum(x**2 for x in gd))+1e-30
        ndir=np.stack([x/gn for x in gd],-1)
        ndir/= (np.linalg.norm(ndir,axis=-1,keepdims=True)+1e-300)
        band=(np.abs(g.phi[k])<=1.5*dx) & ((karr==0)|(larr==0))   # 只要变体-母相界面
        if band.sum()<50: continue
        c2=np.einsum('...i,i->...', ndir[band], n_h)**2
        c2w=np.einsum('...i,i->...', ndir[band], wv/np.linalg.norm(wv))**2
        print('%-6d %-9.4f %-8d %-9.3f %-9.3f %-9.3f %-9.3f' %
              (it, g.volume(k), band.sum(), np.median(c2),
               float((c2>0.8).mean()), float((c2<0.2).mean()), np.median(np.abs(np.sqrt(c2w)))),
              flush=True)
    nd=g.suggest_dt(cfl=0.15, dt_prev=dt)
    if nd: dt=nd
print('用时 %.0f s' % (time.time()-t0))
