#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_tune_reinit.py --- 压 EXPERT-#3 的残余跳变：扫 sussman 迭代数与 dtau。"""
import numpy as np, sys
sys.path.insert(0,'.')
import windowB_surface as W
N, dx = 48, 5e-8; L = N*dx
z = (np.arange(N)+0.5)*dx
X,Y,Z = np.meshgrid(z,z,z,indexing='ij')
a,b = 0.02*L, 0.03*L
def d0(g):
    col=(g.phi[1]-g.phi[2])[N//2,N//2,:]
    i=int(np.argmin(np.abs(col)))
    if i==0 or i>=len(col)-1: return float(z[i])
    v0,v1=col[i],col[i+1]
    return float(z[i]) if v0==v1 else float(z[i]+(0-v0)*dx/(v1-v0))
def mk():
    g=W.LevelSetMulti(N,L,nv=2,gamma=0.15,Mob=1e-9)
    g.phi[1]=Z+a; g.phi[2]=-Z+b
    g.phi[0]=-(np.minimum(g.phi[1],g.phi[2])); return g
print('%-10s %-10s %12s %12s' % ('iters','dtau','d=0(um)','跳变(um)'))
p0 = d0(mk())
print('%-10s %-10s %12.5f %12s' % ('(初始)','-',p0*1e6,'-'))
for it in (30, 100, 300, 1000):
    for dtau in (None, 0.25*dx, 0.1*dx):
        g = mk()
        # 直接调模块级 sussman 的"配对"路径：复现 reinitialize(mode='pair') 但换 iters
        d = g.phi[1]-g.phi[2]
        near = np.abs(d) <= 6*dx
        dn = W.sussman_reinit(d, dx, iters=it, dtau=dtau, grad='upwind2')
        corr = np.where(near, dn-d, 0.0)
        g.phi[1] += 0.5*corr; g.phi[2] -= 0.5*corr
        print('%-10d %-10s %12.5f %12.5f' % (it, str(dtau), d0(g)*1e6, abs(d0(g)-p0)*1e6))
