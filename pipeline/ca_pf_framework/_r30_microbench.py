#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_microbench.py --- R30 审计 S1：`advance()` 里各**算子**的独立标度曲线。

对 N=96（884736 胞）的场，逐个算子测 wall（workers = 1/2/4），
用来回答"哪一块能吃到多核、哪一块撞 DRAM 带宽天花板"。

用法：python3 -u _r30_microbench.py [N] [reps] [w1,w2,w4]
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_par as WP                                        # noqa: E402
from scipy.ndimage import distance_transform_edt                # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
WLIST = ([int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3
         else [1, 2, 4])
DX = 125e-9
rng = np.random.default_rng(0)
phi = rng.standard_normal((N, N, N))
a3 = rng.standard_normal((N, N, N, 3))
b3 = rng.standard_normal((N, N, N, 3))
V = [rng.standard_normal((N, N, N)) for _ in range(3)]
fields = np.stack([phi + 1.7 * i for i in range(12)])
karr = np.argmin(fields, axis=0).astype(np.intp)
sgn = np.where(phi > 0, 1.0, -1.0)
mask = np.abs(phi) < 0.5
if not mask.any():
    mask[0, 0, 0] = True
if mask.all():
    mask[0, 0, 0] = False
cond = phi > 0


def timed(fn, reps=REPS):
    fn()
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    return (time.perf_counter() - t0) / reps


OPS = [
    ('np.where(cond,a,b)          N³',
     lambda: np.where(cond, phi, -phi)),
    ('np.clip(x,0,1)              N³',
     lambda: np.clip(phi, 0.0, 1.0)),
    ("np.einsum('...i,...i->...') 3N³",
     lambda: np.einsum('...i,...i->...', a3, b3)),
    ('np.linalg.norm(a,axis=-1)   3N³',
     lambda: np.linalg.norm(a3, axis=-1)),
    ('np.take_along_axis(12,N³)',
     lambda: np.take_along_axis(fields, karr[None], 0)),
    ('np.argmin(12fields,axis=0)',
     lambda: np.argmin(fields, axis=0)),
    ('np.gradient(phi,dx,eo=2)',
     lambda: np.gradient(phi, DX, edge_order=2)),
    ('np.roll(phi,-1,0)',
     lambda: np.roll(phi, -1, axis=0)),
    ('W.upwind_flux_vec(o2)  N³',
     lambda: W.upwind_flux_vec(phi, V, DX, order=2)),
    ('W.upwind_grad2        N³',
     lambda: W.upwind_grad2(phi, sgn, DX)),
    ('np.sqrt(3项平方和)    3N³',
     lambda: np.sqrt(a3[..., 0] ** 2 + a3[..., 1] ** 2 + a3[..., 2] ** 2)),
    ('EDT(~mask)',
     lambda: distance_transform_edt(~mask)),
    ('EDT(~mask,idx=True)',
     lambda: distance_transform_edt(~mask, return_distances=False,
                                    return_indices=True)),
    ('triad  a=b+c  (读2写1)  3N³',
     lambda: np.add(a3, b3)),
    ('_minmod(a,b)  N³×5 临时量',
     lambda: W._minmod(phi, -phi)),
]

# 流式 triad 的**实际** DRAM 流量 = 读 a + 读 b + 写 c = 3 份 (3N³×8 B)
TRIAD_BYTES = 3 * (3 * 8 * N ** 3)


def triad_threaded(nth, reps=5):
    """把 triad 按 axis=0 切成 nth 段、用线程跑 —— 测 DRAM 带宽天花板。"""
    from concurrent.futures import ThreadPoolExecutor
    ed = [int(round(i * N / nth)) for i in range(nth + 1)]

    def work(i):
        lo, hi = ed[i], ed[i + 1]
        np.add(a3[lo:hi], b3[lo:hi], out=c3[lo:hi])

    c3 = np.empty_like(a3)
    with ThreadPoolExecutor(max_workers=nth) as ex:
        for _ in range(2):
            list(ex.map(work, range(nth)))
        t0 = time.perf_counter()
        for _ in range(reps):
            list(ex.map(work, range(nth)))
        return (time.perf_counter() - t0) / reps
PAR_OPS = [
    ('par.argmin2(12 fields)', lambda p: p.argmin2(fields)),
    ('par.argmin(12 fields)', lambda p: p.argmin(fields)),
    ('par.gradient', lambda p: p.gradient(phi, DX, edge_order=2)),
    ('par.upwind_flux_vec(o2)', lambda p: p.upwind_flux_vec(phi, V, DX, order=2)),
    ('par.upwind_grad2', lambda p: p.upwind_grad2(phi, sgn, DX)),
    ('par.einsum_ii', lambda p: p.einsum_ii(a3, a3)),
    ('par.norm_last', lambda p: p.norm_last(a3)),
    ('par.where', lambda p: p.where(cond, phi, -phi)),
]

print('=' * 104)
print('_r30_microbench  N=%d（%.3g 胞）  每档 %d 次；workers=%s'
      % (N, N ** 3, REPS, WLIST))
print('=' * 104)

BW = 3 * 8 * N ** 3 / 1e9          # triad: 读2写1
res = {}
print('\n[1] 直接 numpy / scipy 算子（**不走 ParCtx**，即单线程）')
for name, fn in OPS:
    t = timed(fn)
    res[name] = t
    tag = ''
    if 'triad' in name:
        tag = '  ⇒ 实际 DRAM 带宽 %.2f GB/s' % (TRIAD_BYTES / t / 1e9)
    print('   %-32s %9.4f s%s' % (name, t, tag))

print('\n[1b] 流式 triad（读2写1）的**线程标度** —— DRAM 带宽天花板')
t1 = None
for w in WLIST:
    t = triad_threaded(w)
    if t1 is None:
        t1 = t
    print('   triad  w=%-2d %9.4f s   %.2f GB/s   ×%.2f'
          % (w, t, TRIAD_BYTES / t / 1e9, t1 / t))

print('\n[2] ParCtx 算子（提供 vs 生效）')
par_tab = {}
for name, fn in PAR_OPS:
    row = []
    for w in WLIST:
        p = WP.ParCtx(w)
        t = timed(lambda: fn(p))
        row.append(t)
        p.close()
    par_tab[name] = row
    base = row[0]
    print('   %-28s' % name
          + ''.join('  w%d=%8.4f(×%.2f)' % (w, t, base / t)
                    for w, t in zip(WLIST, row)))

print('\n[3] 结论量：单线程占比可直接用 [1] 的数 × `advance()` 里的调用次数')
print('=' * 104)
