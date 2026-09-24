#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_seedfast.py --- 剪枝版与暴力参考逐位一致 + 大算例提速"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_SOL

# 暴力参考（不剪枝、不分块）
def brute(ca, cold):
    seeds = [(g, ca.seeds[g]) for g in range(1, len(ca.axes)) if ca.seeds[g] is not None]
    ti = np.argwhere((ca.gid == 0) & cold)
    if not len(ti):
        return ca.gid.copy()
    best = np.full(len(ti), np.inf); bg = np.full(len(ti), 1 << 30, np.int64)
    for g, sg in seeds:
        sup = ca.envelope_sup(g, ti[:, 0], ti[:, 1], ti[:, 2])
        upd = (sup < best) | ((sup == best) & (g < bg))
        best[upd] = sup[upd]; bg[upd] = g
    out = ca.gid.copy()
    out[ti[:, 0], ti[:, 1], ti[:, 2]] = bg
    return out

for (N, ns) in ((30, 4), (40, 6)):
    a = CA3D(N, N, N, 2e-6, irf=IRF(), seed=5); a.nucleate_substrate_grid(ns, ns)
    b = CA3D(N, N, N, 2e-6, irf=IRF(), seed=5); b.nucleate_substrate_grid(ns, ns)
    T = np.full(a.shape, 300.0)
    ref = brute(a, T < T_SOL)
    a.seed_solid_from_substrate(T, T_SOL)
    print("N=%d, %d 种子: 剪枝版 vs 暴力参考 -> 不同胞 %d" % (N, ns*ns, int((a.gid != ref).sum())))

# 大算例计时（wc_cet 里那种 64 种子）
t0 = time.time()
c = CA3D(150, 150, 150, 2e-6, irf=IRF(), seed=5); c.nucleate_substrate_grid(8, 8)
c.seed_solid_from_substrate(np.full(c.shape, 300.0), T_SOL)
print("150^3 (3375000 胞) + 64 种子: %.2f s" % (time.time() - t0))