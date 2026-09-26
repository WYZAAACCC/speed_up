#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_ratio4.py --- **正确口径**重测 #1/#2：
   从 phi 的实际变化反推作用在界面上的速度 vnk_eff = -dphi/(dt*|grad phi|)，
   与**含曲率项**的理论 v = M*(df - gamma*kappa)*Mfac 比。取**中位数**（重尾）。"""
import numpy as np
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
N,dx=48,5e-8; L=N*dx
x=(np.arange(N)+0.5)*dx
X,Y,Z=np.meshgrid(x,x,x,indexing='ij')
M=1e-9; BH,BW=3.5,2.3
print('%-8s %-9s %12s %12s %8s %8s' % ('grad','DIR','vnk_eff(med)','v_theory(med)','比值','n'))
for advg in ('upwind','central'):
    for nm in ('n_hab','w','a'):
        g=W.LevelSetMulti(N,L,C=C,eps0=eps0,gamma=0.15,Mob=M,df=[0.0]+[2e8]*nv,
                          workers=2,reinit_every=0)
        k=1
        DIR={'n_hab':np.asarray(npref[k],float),
             'w':np.asarray(g.wtab[k],float),
             'a':np.asarray(g.atab[k],float)}[nm]      # AUDIT-#7: 用真 a
        DIR=DIR/np.linalg.norm(DIR)
        proj=X*DIR[0]+Y*DIR[1]+Z*DIR[2]
        g.phi[k]=proj-0.5*(proj.min()+proj.max())
        g.init_parent(); g.c[:]=0.036; g.pf=None
        dt=0.15*dx/(M*2e8)
        ph0=g.phi[k].copy()
        # 理论量（推进前）
        reg=g.region()
        karr,larr=np.argmin(g.phi,axis=0),np.argsort(g.phi,axis=0)[1]
        pha=np.take_along_axis(g.phi,karr[None],0)[0]
        phb=np.take_along_axis(g.phi,larr[None],0)[0]
        gd=np.gradient(pha-phb,dx); gdn=np.sqrt(sum(t**2 for t in gd))+1e-30
        ndir=np.stack([t/gdn for t in gd],-1)
        ndir/= (np.linalg.norm(ndir,axis=-1,keepdims=True)+1e-300)
        c2h=np.clip((ndir@np.asarray(npref[k],float)/np.linalg.norm(npref[k]))**2,0,1)
        c2w=np.clip((ndir@g.wtab[k]/np.linalg.norm(g.wtab[k]))**2,0,1)
        Mfac=np.exp(-BH*c2h-BW*c2w)
        kap=g.curvature_of(k)
        v_theory=M*(2e8*np.ones_like(kap)-g.gamma*kap)*Mfac*np.where(karr==k,1.0,-1.0)
        g.advance(dt,aniso=0.0,npref=npref,band_cells=6,mob_beta=BH,
                  mob_beta_w=BW,adv_grad=advg)
        dphi=g.phi[k]-ph0
        gn=np.sqrt(sum(t**2 for t in np.gradient(ph0,dx)))+1e-30
        band=np.abs(ph0)<=0.5*dx
        vnk_eff=-dphi[band]/(dt*gn[band])
        vt=v_theory[band]
        ok=np.isfinite(vt)&(np.abs(vt)>0)
        print('%-8s %-9s %12.4e %12.4e %8.3f %8d'
              % (advg,nm,np.median(vnk_eff),np.median(vt[ok]),
                 np.median(vnk_eff)/np.median(vt[ok]),band.sum()))
