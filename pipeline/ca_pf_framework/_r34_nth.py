#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r34_nth.py —— **P0-7 的定量核查**：`advance` 里每个并行算子**实际用了几个线程**。

背景：R30 审计 S1 用计数器实测 `ParCtx.upwind_flux_vec` 在**生产路径上 12/12 次
都是 `nth=1`**（它唯一的调用点在 `par.for_each` 的 worker 里 ⇒ 重入守卫强制串行）。
S1 把它称为"死代码级浪费"。

**但那个结论需要一个定量补充**：`for_each` 本身是**按场并行**的 —— 只要
`nreg ≥ nthreads`，把 `upwind_flux_vec` 提到外面改成"按空间并行、按场串行"
**不会更快**（13 个场 / 4 线程 = 4 波；13 次串行 × (t/4) 也是 3.25t）。

⇒ 本脚本用权威口径（`ParCtx.report()`）把**每个 tag 的 `nth`** 打出来，
   看"按场并行"有没有真的生效、以及瓶颈在哪。

跑法：  python3 _r34_nth.py [--N 64] [--nv 6] [--workers 4] [--steps 4]
"""
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, MOB                    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--nv', type=int, default=6)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--steps', type=int, default=4)
    a = ap.parse_args()
    dx = 125e-9
    L = a.N * dx
    om = WL.default_omega(a.nv, 5.0, axis=np.array([1.0, 0.0, 0.0]))
    lt = WL.LathTable([1] * a.nv, omegas=om, eps0_var=EPS0, npref_var=NPF,
                      gamma0=0.25)
    g = W.LevelSetMulti(a.N, L, C=C, eps0=lt.eps0, gamma=0.25, Mob=MOB,
                        df=[0.0] + [1.5e8] * a.nv, workers=a.workers,
                        reinit_every=0)
    g.lath = lt
    n_hab = np.asarray(NPF[1], float); n_hab /= np.linalg.norm(n_hab)
    a_ax = np.asarray(W.LevelSetMulti._rank1_axes(
        np.asarray(EPS0[0], float), n_hab)[1], float)
    a_ax /= np.linalg.norm(a_ax)
    c0 = np.array([L / 2] * 3)
    T = 250e-9
    for j in range(a.nv):
        g.seed_plate(j + 1, c0 + (j - (a.nv - 1) / 2.0) * T * n_hab, n_hab,
                     400e-9, T, elong=3.0, along=a_ax, flat_end=True)
    g.init_parent()
    dt = 0.15 * dx / (MOB * 1.5e8)
    kw = dict(aniso=0.4, npref={i + 1: np.asarray(NPF[1], float)
                                for i in range(a.nv)},
              band_cells=20, mob_beta=6.477, mob_beta_w=2.3,
              adv_grad='proj2', norm_smooth=0)
    t0 = time.perf_counter()
    for _ in range(a.steps):
        g.advance(dt, **kw)
    wall = time.perf_counter() - t0
    tot, rows = g.par.report()
    print('=' * 88)
    print('N=%d  nv=%d  workers=%d  nreg=%d  steps=%d  wall=%.2f s  (%.3f s/步)'
          % (a.N, a.nv, a.workers, g.nreg, a.steps, wall, wall / a.steps))
    print('★ `ParCtx.report()` 的权威口径（`nth` = 该算子**实际**用到的分段数）')
    print('  %-26s %-10s %-10s %s' % ('tag', '累计wall', '调用次数', 'nth(max)'))
    for tag, v in rows:
        print('  %-26s %-10.3f %-10d %d' % (tag, v[0], v[1], v[2]))
    print('  %-26s %-10.3f' % ('—— 并行区内累计', tot))
    print('  %-26s %-10.3f  （占整段 wall 的 %.1f%%；其余是**串行残差**）'
          % ('整段 wall', wall, 100.0 * tot / max(wall, 1e-9)))
    print('\n判读：只要 `advance.k_loop` / `advance.geom_k` 的 nth 达到 workers，')
    print('      "按场并行"就已生效 ⇒ `upwind_flux_vec` 的 slab 路径用不上**不是浪费**'
          '（nreg ≥ workers 时两者等价）。')


if __name__ == '__main__':
    main()
