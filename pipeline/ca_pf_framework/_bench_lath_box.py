#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bench_lath_box.py --- 板条盒子的**成本实测**（内存 + 步时），用来定 L / dx / N。

不猜、不外推：直接建 LevelSetMulti（12 变体 + 谱法弹性）跑 5 步，读
  * 峰值 RSS（resource.getrusage，单位 KB）
  * 每步墙钟
  * elapsed 里的 elastic_driving 占比
用法：python3 _bench_lath_box.py 96 128 160
"""
import os, sys, time, resource
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

DX = float(os.environ.get('BENCH_DX', '2.5e-8'))      # m
NS = int(os.environ.get('BENCH_STEPS', '5'))
NW = int(os.environ.get('BENCH_WORKERS', '6'))

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


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0


print('%-6s %-8s %-8s %-10s %-12s %-12s %-14s' %
      ('N', 'L(um)', 'cells', 't_build(s)', 's/step', 'peakRSS(GB)', 'elastic占比'))
for N in [int(a) for a in (sys.argv[1:] or ['96', '128', '160'])]:
    L = N * DX
    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                        df=[0.0] * (nv + 1), workers=NW, reinit_every=25)
    g.df[1:] = 2.0e8
    R = 0.09 * L
    t_seed = 4 * DX
    ns = 0
    while ns < 24:
        c = rng.random(3) * (L - 2 * R) + R
        k = int(rng.integers(1, nv + 1))
        try:
            g.seed_plate(k, c, npf[k], R, t_seed)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    t_build = time.time() - t0
    dt = 0.15 * DX / (1e-9 * 2e8)
    t_el = 0.0
    t1 = time.time()
    for _ in range(NS):
        _ta = time.time()
        g.elastic_driving()
        t_el += time.time() - _ta
        g.advance(dt, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5)
    wall = time.time() - t1
    print('%-6d %-8.2f %-8.2e %-10.1f %-12.3f %-12.2f %-14.1f' %
          (N, L * 1e6, N ** 3, t_build, wall / NS, rss_gb(), 100 * t_el / max(wall, 1e-9)),
          flush=True)
    del g
print('DX=%.1f nm  workers=%d  steps=%d' % (DX * 1e9, NW, NS))
