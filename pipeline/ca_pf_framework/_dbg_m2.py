#!/usr/bin/env python3
"""诊断 M2 的初始区域归属（为什么 t=0 时母相体积就是 0）"""
import numpy as np
import windowB_surface as W

g = W.M2_twelve_variants(N=32, nstep=0)
vt = np.array([g.volume(k) for k in range(g.nreg)])
print('各区域体积分数 =', np.round(vt / vt.sum(), 4))
for k in range(min(g.nreg, 4)):
    print('  phi[%d]: min %.3e  max %.3e' % (k, g.phi[k].min(), g.phi[k].max()))
print('母相 phi[0] 的最小值 =', g.phi[0].min())
print('region() 各值计数 =', np.bincount(g.region().ravel()))
