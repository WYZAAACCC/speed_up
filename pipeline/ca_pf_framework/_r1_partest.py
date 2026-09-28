#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_partest.py --- windowB_par 的自检 + 重入守卫 + 真实步进加速比"""
import os
import sys
import time
import argparse
import threading

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_par as P

ap = argparse.ArgumentParser()
ap.add_argument('--mode', default='selftest')
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--th', type=int, default=4)
ap.add_argument('--reps', type=int, default=3)
a = ap.parse_args()

if a.mode == 'selftest':
    ok = P._selftest(64, a.th)
    print('selftest ok =', ok)

    # ---- 重入守卫：嵌套并行不得死锁、且结果不变 ----
    p = P.ParCtx(4)
    x = np.random.default_rng(3).standard_normal((64, 64, 64))

    def outer(lo, hi):
        g = p.gradient(x[lo:hi], 1e-7)[0]      # 嵌套调用（应自动串行）
        return g
    t0 = time.time()
    r = p.map0(outer, 64)
    print('嵌套 map0 未死锁；耗时 %.3f s；nest_max = %d' % (time.time() - t0, p._nest_max))
    ref = np.gradient(x, 1e-7, edge_order=2)[0]
    print('嵌套结果仍逐位相同 =', np.array_equal(r.view(np.uint8), ref.view(np.uint8)))
    p.close()

elif a.mode == 'scale':
    # ---- 真机标度：在**真实 RVE 构型**上逐步测 advance（含 elastic_driving）----
    import windowB_surface as W
    from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED
    L = 24.0e-6
    N = a.N
    dx = L / N

    def rss():
        with open('/proc/self/status') as f:
            for ln in f:
                if ln.startswith('VmRSS:'):
                    return float(ln.split()[1]) / 1048576.0
        return float('nan')

    print('=' * 96)
    print('_r1_partest scale   N=%d  Δx=%.1f nm   线程 = %d' % (N, dx * 1e9, a.th))
    print('=' * 96, flush=True)
    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7, reinit_band_cells=6.0)
    print('构造 %.1f s  RSS %.2f GB' % (time.time() - t0, rss()), flush=True)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(64 * 8):
        if ns >= 64:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        try:
            g.seed_plate(k, c, nrm / np.linalg.norm(nrm), R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
              adv_grad='proj2')

    # 先跑一步（不并行）把构造期的懒加载/分配都触发掉
    g.par.set_threads(1)
    g._t_since_reinit = 0.0
    g.elastic_driving(); g.advance(dt, **KW)

    # 保存参照态，用于逐位比较
    phi_ref = g.phi.copy()
    for th in [1] + [t for t in (2, 4, 8, 12, 16, 20) if t <= a.th]:
        g.phi = phi_ref.copy()
        g.par.set_threads(th)
        g._t_since_reinit = 0.0
        ts = []
        for r in range(a.reps):
            t1 = time.time()
            g.elastic_driving()
            t2 = time.time()
            g.advance(dt, **KW)
            t3 = time.time()
            ts.append((t2 - t1, t3 - t2))
        g.stats = dict(g.par.stats)
        ed = min(x[0] for x in ts)
        ad = min(x[1] for x in ts)
        print('  th=%-3d  elastic %.2f s + advance %.2f s = %.2f s/步   (best of %d)'
              % (th, ed, ad, ed + ad, a.reps), flush=True)
        if th == 1:
            phi_1 = g.phi.copy()
        else:
            same = np.array_equal(g.phi.view(np.uint8), phi_1.view(np.uint8))
            print('        与 th=1 逐位相同 = %s' % same, flush=True)
    p = phi_1 - phi_ref
    print('\n  ◆ 参考态与 th=1 结果的最大变化 = %.3e（确认这一步真的在演化）'
          % float(np.max(np.abs(p))))
