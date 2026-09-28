#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_prof_step.py --- 单步 `advance` 的耗时分解（决定"并行/重写"值不值得）。"""
import os, sys, time, cProfile, pstats, io
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
DX = 5e-8
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
nv = len(eps0)
rng = np.random.default_rng(4)
npf = {}
for v in range(nv):
    best, bn = None, None
    for n in rng.normal(size=(200, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npf[v + 1] = bn
L = N * DX
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] * (nv + 1), workers=1, reinit_every=0)
g.df[1:] = 2.0e8
R = 0.09 * L
for _ in range(12):
    c = rng.random(3) * (L - 2 * R) + R
    try:
        g.seed_plate(int(rng.integers(1, nv + 1)), c, npf[1], R, 4 * DX)
    except ValueError:
        pass
g.init_parent()
dt = 0.15 * DX / (1e-9 * 2e8)
g.advance(dt, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5)   # 预热

pr = cProfile.Profile()
pr.enable()
for _ in range(NS):
    g.advance(dt, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5)
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(22)
txt = s.getvalue()
print('=== N=%d, %d 步, cProfile（tottime 前 22）===' % (N, NS))
for ln in txt.splitlines():
    if ln.strip():
        print(ln)
