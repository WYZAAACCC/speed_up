#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bench_threads.py --- 线程扩展性实测：**一个作业到底能吃几个核、加速比多少**。

用法：python3 _bench_threads.py <N> <steps> [workers]
环境变量由外层设置（必须在 import numpy 之前生效）。
输出：wall / cpu / 并行度(cpu/wall) / s·步⁻¹
"""
import os, sys, time, resource
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
NW = int(sys.argv[3]) if len(sys.argv) > 3 else 4
DX = float(os.environ.get('BENCH_DX', '5e-8'))     # 50 nm

import numpy as np
print('  numpy %s | BLAS=%s' % (np.__version__,
      (np.show_config.__doc__ or '')[:0] or
      (getattr(np.__config__, 'CONFIG', {}) or {}).get('Build Dependencies', {})
      .get('blas', {}).get('name', '?')))
import windowB_surface as W
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

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
t0 = time.time()
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=1e-9,
                    df=[0.0] * (nv + 1), workers=NW, reinit_every=0)
g.df[1:] = 2.0e8
R = 0.09 * L
for _ in range(12):
    c = rng.random(3) * (L - 2 * R) + R
    try:
        g.seed_plate(int(rng.integers(1, nv + 1)), c, npf[1], R, 4 * DX)
    except ValueError:
        pass
g.init_parent()
t_build = time.time() - t0

dt = 0.15 * DX / (1e-9 * 2e8)
c0 = time.process_time(); w0 = time.time()
for _ in range(NS):
    g.advance(dt, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5)
wall = time.time() - w0
cpu = time.process_time() - c0
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
print('  N=%-4d steps=%-3d workers=%-2d | build %5.1fs | %6.3f s/step | '
      'cpu/wall=%.2f | RSS %.2f GB' % (N, NS, NW, t_build, wall / NS, cpu / max(wall, 1e-9), rss))
