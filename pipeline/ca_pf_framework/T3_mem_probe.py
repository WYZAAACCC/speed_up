#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3_mem_probe.py --- 内存账：**逐数组**列出 LevelSetMulti（含 PF3D）持有的内存，
                    并用 tracemalloc 量单步的**临时**峰值。

目的：把"1.55 kB/胞"拆成可操作的条目，决定 T3 该动哪儿（目标 ≤0.95 kB/胞）。
用法：python3 T3_mem_probe.py [N] [steps]
"""
import os
import sys
import gc
import tracemalloc

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 2
DX = float(os.environ.get('T3_DX', '2.5e-8'))
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
                    df=[0.0] * (nv + 1), workers=1, reinit_every=25)
g.df[1:] = 2.0e8
R = 0.09 * L
for _ in range(12):
    c = rng.random(3) * (L - 2 * R) + R
    try:
        g.seed_plate(int(rng.integers(1, nv + 1)), c, npf[1], R, 4 * DX)
    except ValueError:
        pass
g.init_parent()
nc = N ** 3
print('N=%d  dx=%.1f nm  cells=%.3e  nreg=%d' % (N, DX * 1e9, nc, g.nreg))


def dump(obj, label, seen=None):
    if seen is None:
        seen = set()
    rows = []
    for k, v in sorted(vars(obj).items()):
        if isinstance(v, np.ndarray) and v.nbytes > 1e5:
            rows.append(('%s.%s' % (label, k), str(v.shape), str(v.dtype), v.nbytes))
        elif isinstance(v, (list, tuple)) and len(v) and isinstance(v[0], np.ndarray) \
                and getattr(v[0], 'nbytes', 0) > 1e5:
            tot = sum(x.nbytes for x in v)
            rows.append(('%s.%s[%d]' % (label, k, len(v)), '-', str(v[0].dtype), tot))
    return rows


rows = dump(g, 'g')
if getattr(g, 'pf', None) is not None:
    rows += dump(g.pf, 'g.pf')
rows.sort(key=lambda r: -r[3])
tot = sum(r[3] for r in rows)
print('%-34s %-22s %-10s %12s %10s' % ('array', 'shape', 'dtype', 'MB', 'B/cell'))
for name, shape, dt, nb in rows:
    print('%-34s %-22s %-10s %12.2f %10.1f' % (name, shape, dt, nb / 1e6, nb / nc))
print('%-34s %-22s %-10s %12.2f %10.1f' % ('**合计（>0.1MB 的数组）**', '', '', tot / 1e6, tot / nc))

dt_ = 0.15 * DX / (1e-9 * 2e8)
g.advance(dt_, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
gc.collect()
tracemalloc.start()
for _ in range(NS):
    g.elastic_driving()
    g.advance(dt_, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
cur, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print()
print('单步 tracemalloc：当前 %.2f MB / **峰值 %.2f MB**  (= %.0f B/胞 峰值临时)'
      % (cur / 1e6, peak / 1e6, peak / nc))
snap = None
tracemalloc.start(10)
g.elastic_driving()
g.advance(dt_, aniso=0.4, npref=npf, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
snap = tracemalloc.take_snapshot()
tracemalloc.stop()
print('\n单步分配 top-12（按文件:行）:')
for st in snap.statistics('lineno')[:12]:
    print('   %10.2f MB  %s' % (st.size / 1e6, st.traceback[0]))
