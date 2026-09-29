#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_speedup.py --- R30 审计 S1：`advance()` 单步 wall 的 workers 标度。

★ 关键（本仓库"参数传了但没生效"的老毛病）：R1（2026-09-29）之后真正决定
  并行度的是 **`g.par.n`（`windowB_par.ParCtx`）**，不是 `g.workers`。
  旧探针 `_probe_workers.py` 改的是 `g.pf.workers` / `g.workers` ⇒ 对 `advance`
  **无效**（这就是它当年测出"advance 恒为单线程"的原因之一）。
  本脚本用 `g.par.set_threads()` 改，并**每次都打印生效值**做自证。

用法：python3 -u _r30_speedup.py <N> <nsample> [w1,w2,...]
      默认 N=96 nsample=3 workers=1,2,4
"""
import json
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96
NS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
WLIST = ([int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3
         else [1, 2, 4])
DX = 125e-9
GAMMA0 = 0.25
BETA_H = 3.5
BETA_W = 2.3
NLATH = 11


def build(N, NW):
    L = N * DX
    laths = [1] * NLATH
    lt = WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                      eps0_var=EPS0, npref_var=NPF, gamma0=GAMMA0)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(len(laths))]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float)
             for i in range(len(laths))}
    nv = len(eps0)
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=GAMMA0, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=NW, reinit_every=0,
                        reinit_dt=1.0e-4, reinit_band_cells=6.0)
    g.lath = lt
    c0 = np.array([L / 2] * 3)
    n_hab = np.asarray(NPF[1], float)
    n_hab /= np.linalg.norm(n_hab)
    a_ax = np.asarray(g.atab[1], float)
    a_ax /= np.linalg.norm(a_ax)
    T, gap, Wd, Lp = 635e-9, 0.0, 1224e-9, 4590e-9
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * (T + gap)
        g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T,
                     elong=Lp / Wd, along=a_ax, flat_end=True)
    g.init_parent()
    return g, npref


def main():
    print('=' * 104)
    print('_r30_speedup   N=%d  Δx=%.1f nm  L=%.3f µm  nreg=%d  workers=%s  '
          '每档 %d 步' % (N, DX * 1e9, N * DX * 1e6, NLATH + 1, WLIST, NS))
    print('=' * 104, flush=True)
    t0 = time.time()
    g, npref = build(N, 1)
    print('构造耗时 %.1f s' % (time.time() - t0), flush=True)
    dx = g.dx
    dt = 0.15 * dx / (MOB * DF)
    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=BETA_H,
              mob_beta_w=BETA_W, adv_grad='proj2', norm_smooth=0,
              facet_lam=0.0, facet_eps=0.05)
    print('构造时 g.par.n = %d ；g.nthreads = %d ；g.pf.workers = %d'
          % (g.par.n, g.nthreads, g.pf.workers))
    g.advance(dt, **kw)                                   # 预热

    rows = []
    for Wk in WLIST:
        g.par.set_threads(Wk)
        g.pf.workers = Wk
        g.par.stats = {}
        print('\n--- workers=%d ---  生效值自证：g.par.n=%d  g.pf.workers=%d'
              % (Wk, g.par.n, g.pf.workers), flush=True)
        w0, c0 = time.perf_counter(), time.process_time()
        for _ in range(NS):
            g.advance(dt, **kw)
        wall = (time.perf_counter() - w0) / NS
        cpu = (time.process_time() - c0) / NS
        tot, stats = g.par.report()
        rows.append(dict(w=Wk, wall=wall, cpu=cpu, cpu_wall=cpu / wall,
                         par_total=tot,
                         stats={k: v for k, v in stats}))
        print('    advance = %.3f s/步  CPU = %.3f s/步  CPU/wall = %.2f'
              % (wall, cpu, cpu / wall))
        print('    并行算子累计 wall = %.3f s/步；分段自证（tag: 次数→最大分段）:'
              % tot)
        for tag, s in stats:
            print('      %-28s n=%-5d nth_max=%d  累计 %.3f s'
                  % (tag, s[1], s[2], s[0]))

    print('\n' + '=' * 104)
    print('加速比（相对 workers=%d）' % rows[0]['w'])
    print('  %-8s %12s %12s %10s %10s' % ('workers', 'wall(s/步)', 'CPU(s/步)',
                                          '加速比', 'CPU/wall'))
    for r in rows:
        print('  %-8d %12.3f %12.3f %10.2f %10.2f'
              % (r['w'], r['wall'], r['cpu'], rows[0]['wall'] / r['wall'],
                 r['cpu_wall']))
    print('=' * 104)

    dump = dict(N=N, dx=DX, nreg=NLATH + 1, nsample=NS, dt=dt,
                kwargs=dict(aniso=0.4, band_cells=20, mob_beta=BETA_H,
                            mob_beta_w=BETA_W, adv_grad='proj2',
                            norm_smooth=0, facet_lam=0.0, facet_eps=0.05),
                rows=rows)
    path = os.path.join(_HERE, '_r30_speedup_N%d.json' % N)
    with open(path, 'w') as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print('→ 原始数据写入 %s' % os.path.basename(path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
