#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_cost192.py --- ★★ P-4：**多核 RVE 在 R24 标准域上，一次 reinit 触发到底多贵**

为什么必须先做（`R1_HANDOFF.md` P-4，子代理的告警）
---------------------------------------------------
子代理实测（N=96、24 核、密微结构）：**12/12 配对都不被 `skip_tol` 跳过**，
单次触发合计 **230 s**；按 N³ 外推到 **N=192 是 20–90 min/次触发【推理，未实测】**。
而多核实验的触发间隔是 `reinit_dt/dt = 6e-7/5.357e-8 = 11.2 步`。
⇒ **若真是一次触发几十分钟，多核实验在 R24 上根本跑不动** ⇒ 必须先量。

判据（先写死）
--------------
  R-1 **实测**一次触发（把 `_t_since_reinit` 预置到刚好越界）的**步时增量**。
  R-2 报 `_reinit_wall_last`（只算 Sussman 本体）、`_reinit_pairs_last`（真做的配对数）、
      `_reinit_done` / `_reinit_skipped` / `_reinit_all_skipped_last`。
  R-3 **对照**：同样一步但**不触发** reinit ⇒ 给出干净的基线步时。
  R-4 换种子数（4 / 16 / 64）看**标度**：代价是随配对数还是随 N³ 走。
  R-5 **判定**：若一次触发 > 3× 基线步时 ⇒ 多核实验必须**先解决 reinit**，否则不可行。

用法：python3 _r1_reinit_cost192.py --N 192 --n0 64 --th 6
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--n0', type=int, default=64)
ap.add_argument('--th', type=int, default=6)
ap.add_argument('--steps', type=int, default=4)
ap.add_argument('--list', default='4,16,64', help='要扫的种子数')
a = ap.parse_args()

L = a.L_um * 1e-6
dx = L / a.N


def rss():
    with open('/proc/self/status') as f:
        for ln in f:
            if ln.startswith('VmRSS:'):
                return float(ln.split()[1]) / 1048576.0
    return float('nan')


print('=' * 104)
print('_r1_reinit_cost192  N=%d  L=%.1f µm  Δx=%.1f nm  线程=%d' % (a.N, a.L_um, dx * 1e9, a.th))
print('=' * 104, flush=True)

t0 = time.time()
g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=a.th, reinit_every=0,
                    reinit_dt=6.0e-7, reinit_band_cells=6.0)
print('构造 %.1f s ；RSS %.2f GB' % (time.time() - t0, rss()), flush=True)

dt = 0.15 * dx / (MOB * DF)
interval = 6.0e-7 / dt
print('dt = %.6e s ⇒ reinit 触发间隔 = %.2f 步' % (dt, interval), flush=True)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2')
shape = (a.N, a.N, a.N)
rows = []
for n0 in [int(x) for x in a.list.split(',')]:
    # 重置到"只有母相 + n0 个核"
    g.phi[:] = 1e3
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(n0 * 12):
        if ns >= n0:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    # 先跑几步把界面做出来（不触发 reinit）
    for _ in range(a.steps):
        g._t_since_reinit = 0.0
        g.advance(dt, **KW)
    # --- R-3 基线步（不触发）---
    g._t_since_reinit = 0.0
    t1 = time.time()
    g.advance(dt, **KW)
    t_base = time.time() - t1
    # --- R-1 触发步 ---
    g._reinit_done = 0
    g._reinit_skipped = 0
    g._reinit_wall_last = 0.0
    g._reinit_pairs_last = 0
    g._t_since_reinit = 6.0e-7        # 已越界 ⇒ 本步必触发
    t1 = time.time()
    g.advance(dt, **KW)
    t_trig = time.time() - t1
    done = int(getattr(g, '_reinit_done', 0))
    skip = int(getattr(g, '_reinit_skipped', 0))
    wall = float(getattr(g, '_reinit_wall_last', 0.0))
    pairs = int(getattr(g, '_reinit_pairs_last', 0))
    allsk = bool(getattr(g, '_reinit_all_skipped_last', False))
    rows.append((n0, t_base, t_trig, done, skip, pairs, wall, allsk))
    print('  n0=%-3d  基线步 %7.2f s   触发步 %8.2f s   **增量 %8.2f s（×%.2f）**'
          '   done=%d skip=%d **真做配对=%d**  Sussman本体 %.2f s  全跳过=%s'
          % (n0, t_base, t_trig, t_trig - t_base, t_trig / max(t_base, 1e-9),
             done, skip, pairs, wall, allsk), flush=True)

print('\n' + '=' * 104)
print('%-6s %10s %12s %10s %8s %8s %12s' %
      ('n0', '基线 s', '触发步 s', '增量 s', 'done', 'skip', 'Sussman s'))
for r in rows:
    print('%-6d %10.2f %12.2f %10.2f %8d %8d %12.2f' %
          (r[0], r[1], r[2], r[2] - r[1], r[3], r[4], r[6]))
mx = max((r[2] - r[1]) / max(r[1], 1e-9) for r in rows)
print('\nR-5 判定：最坏增量/基线 = **×%.2f** ⇒ %s'
      % (mx, '⛔ **多核实验必须先解决 reinit**（>3× 基线）' if mx > 3.0
         else '✅ 可以开跑（≤3× 基线）'))
print('=' * 104)
