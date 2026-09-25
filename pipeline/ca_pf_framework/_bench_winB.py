#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Window B 成本实测：给定 (dx, N, L) 下测 **单步耗时 + 峰值内存**，并外推 300 步。
   用法：_bench_winB.py [nstep]
   ★ 记账：本次只测**成本**，不做物理结论；几何数字（S_v/板厚）只用来确认"档位设置没搞错"。
"""
import sys
import time
import resource
import numpy as np
import windowB_surface as W
from windowB_pf3d import C_iso3, C_cubic, _lam_full
from windowB_ti64_variants import variants

nstep = int(sys.argv[1]) if len(sys.argv) > 1 else 5
GPA = 1e9
C = C_cubic(134.0 * GPA, 110.0 * GPA, 36.0 * GPA)        # bcc β（与 M2 现行一致）
eps0, Fs, meta = variants()
nv = len(eps0)


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 ** 2


def run(tag, N, dx, plate_dx=2.0, rfrac=0.08, aniso=False, elastic=True, workers=6):
    r0 = rss_gb()
    t0 = time.time()
    g = W.LevelSetMulti(N, N * dx, C=C if elastic else None,
                        eps0=eps0 if elastic else None, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [-1e8] * nv, workers=workers, reinit_every=25,
                        aniso_elastic=aniso, nv=nv)
    npref = {}
    rng = np.random.default_rng(0)
    for v in range(nv):
        best, bn = None, None
        for n in rng.normal(size=(200, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n),
                                        eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        npref[v + 1] = bn
    R = rfrac * N * dx
    for v in range(nv):
        g.seed_plate(v + 1, (rng.random(3) * max(N * dx - 2 * R, 1e-9) + R),
                     npref[v + 1], R, plate_dx * dx)
    g.init_parent()
    t_setup = time.time() - t0
    dt = 0.15 * dx / (1e-9 * 1e8)                 # 初值；之后自适应
    ts = []
    for _ in range(nstep):
        t1 = time.time()
        g.advance(dt, aniso=0.4, npref=npref, iface_band=2.0)
        dt = g.suggest_dt(cfl=0.15, dt_prev=dt) or dt
        ts.append(time.time() - t1)
    nb, medg, okg = g.band_health()
    per = float(np.median(ts))
    print('   %-26s N=%4d dx=%6.1f nm L=%5.2f um | 建场 %5.1fs | 单步 %6.2fs | '
          '300 步 %5.2f h | 峰值RSS %5.2f GB | 带胞 %6d 带内|grad| %.2f'
          % (tag, N, dx * 1e9, N * dx * 1e6, t_setup, per, per * 300 / 3600.0,
             rss_gb(), nb, medg))


print('==== Window B 成本实测（nstep=%d）====' % nstep)
print('   硬件：本机 WSL 限 22–23 GB；这里只报单进程峰值 RSS')
print('   现状档（我一直用的）:')
run('A 现状 dx=10nm', 32, 1e-8, rfrac=0.22)
print('   推荐档附近:')
run('B dx=60nm N=100 (6um)', 100, 6e-8)
run('C dx=60nm N=100 +各向异性弹性', 100, 6e-8, aniso=True)
print('   更大档:')
run('D dx=60nm N=160 (9.6um)', 160, 6e-8)
print('   更粗档:')
run('E dx=100nm N=60 (6um)', 60, 1e-7)
print('   （可选）不带动力的纯场更新成本:')
run('F dx=60nm N=100 无弹性', 100, 6e-8, elastic=False)
