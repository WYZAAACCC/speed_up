#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_3face.py --- 判据：**分类测三类界面的实际推进速度** vs Mfac 预期。
   分类：大面(|n.n_hab|>0.9) / 侧面(|n.w|>0.9) / 端面(|n.a|>0.9)
   速度用逐胞反推 v_eff = -dphi/(dt*|grad phi0|)（_dbg_vnk.py 已验口径），只取 winner 侧。
"""
import numpy as np, sys, time
sys.path.insert(0,'.')
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants
C=C_cubic(134.0e9,110.0e9,36.0e9)
eps0,_F,_m=variants(); nv=12
rng=np.random.default_rng(0); npref={}
for v in range(nv):
    best,bn=None,None
    for n in rng.normal(size=(400,3)):
        n=n/np.linalg.norm(n)
        val=0.5*float(np.einsum('ij,ijkl,kl->',eps0[v],_lam_full(C,n),eps0[v]))
        if best is None or val<best: best,bn=val,n
    npref[v+1]=bn
N,dx=80,2e-8; L=N*dx
g=W.LevelSetMulti(N,L,C=C,eps0=eps0,gamma=0.0,Mob=1e-9,df=[0.0]+[2e8]*nv,
                  workers=8,reinit_every=0)
k=1
n_h=np.asarray(npref[k],float); n_h/=np.linalg.norm(n_h)
wv=np.asarray(g.wtab[k],float); wv/=np.linalg.norm(wv)
al=np.asarray(g.atab[k],float); al/=np.linalg.norm(al)     # 用真 a（EXPERT-#7）
g.seed_plate(k,[L/2]*3,n_h,1.2e-7,2.0e-7,elong=6.0,along=al)
g.init_parent(); g.c[:]=0.036; g.pf=None
M=1e-9; BH,BW=3.5,2.3
dt=0.15*dx/(M*2e8)
print('%-6s %-10s %-12s %-12s %-8s' % ('step','类','v实测(中位)','v理论(中位)','比值'))
t0=time.time()
for it in range(1,201):
    ph0=g.phi[k].copy()
    gd0=np.gradient(ph0,dx); gn=np.sqrt(sum(x**2 for x in gd0))+1e-30
    nd=np.stack([x/gn for x in gd0],-1); nd/=(np.linalg.norm(nd,axis=-1,keepdims=True)+1e-300)
    karr=np.argmin(g.phi,axis=0)   # (fix) 必须对**所有场**求 argmin；
                                   #   原来用 argsort(ph0)（单场）恒返回 0
    d=g.advance(dt,aniso=0.4,npref=npref,band_cells=20,mob_beta=BH,mob_beta_w=BW,
                adv_grad='central')
    if it % 40 == 0:
        dphi=g.phi[k]-ph0
        band=(np.abs(ph0)<=0.5*dx)&(karr==k)
        c2h=np.einsum('...i,i->...',nd,n_h)**2
        c2w=np.einsum('...i,i->...',nd,wv)**2
        c2a=np.einsum('...i,i->...',nd,al)**2
        veff=-dphi/(dt*gn)
        Mfac=np.exp(-BH*c2h-BW*c2w)
        vth=M*2e8*Mfac
        for nm,msk in (('大面',band&(c2h>0.81)),('侧面',band&(c2w>0.81)),('端面',band&(c2a>0.81))):
            if msk.sum()<20: continue
            a=np.median(veff[msk]); b=np.median(vth[msk])
            print('%-6d %-10s %-12.4e %-12.4e %-8.3f' % (it,nm,a,b,a/b if b else np.nan), flush=True)
    ndt=g.suggest_dt(cfl=0.15,dt_prev=dt)
    if ndt: dt=ndt
print('用时 %.0f s' % (time.time()-t0))
