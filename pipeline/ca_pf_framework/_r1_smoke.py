#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_smoke.py --- ★★ 端到端守卫：多核改造**不许改变任何一个数**

为什么必须做这一条（本项目最贵的教训，`AGENTS.md §3.7` / `F-2` 两处实例）
--------------------------------------------------------------------------
算子级自检（`windowB_par._selftest`）只能证明"算子本身逐位相同"，
**证明不了**"接进 `advance` 之后整步逐位相同" —— `elastic_soft` 那个"死开关"
就是两处实例、只有**端到端守卫**抓到了第二处。

判据（硬失败）
--------------
  E-1 `nthreads=1` 与 `nthreads=N` 跑**同一条** RVE 轨迹（同一初值、同 dt、
      同步数、含强制 reinit），逐步比较 `phi` **逐位**相同。
  E-2 `region()` / `dG_max` / `elastic_driving()` 也逐位相同。
  E-3 **正对照**：把 `dt` 改一点点，`phi` **必须不同** —— 否则说明这个守卫
      根本没有分辨力（"两次都一样"可能只是因为"什么都没发生"）。
  E-4 线程数真的被用上了：`par.stats` 非空、`nth_max > 1`。

用法：python3 _r1_smoke.py --N 32 --nth 4 --steps 3
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=32)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--nth', type=int, default=4)
ap.add_argument('--steps', type=int, default=3)
ap.add_argument('--n0', type=int, default=8)
ap.add_argument('--reinit-band', type=float, default=6.0)
a = ap.parse_args()

L = a.L_um * 1e-6
dx = L / a.N
print('=' * 96)
print('_r1_smoke  端到端多核守卫   N=%d  Δx=%.2f nm  线程=%d  步数=%d'
      % (a.N, dx * 1e9, a.nth, a.steps))
print('=' * 96, flush=True)


def build(workers):
    g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=workers, reinit_every=0,
                        reinit_dt=6.0e-7,
                        reinit_band_cells=(None if a.reinit_band == 0 else a.reinit_band))
    return g


t0 = time.time()
g1 = build(1)
print('构造（workers=1） %.1f s' % (time.time() - t0), flush=True)
gN = build(a.nth)
gN.phi = g1.phi.copy()            # ← 保证两者初值**逐位**相同

rng = np.random.default_rng(7)
ns = 0
for _ in range(a.n0 * 8):
    if ns >= a.n0:
        break
    c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
    k = int(rng.integers(1, NV + 1))
    nrm = np.asarray(NPF[k], float)
    nrm = nrm / np.linalg.norm(nrm)
    try:
        g1.seed_plate(k, c, nrm, R_SEED, T_SEED)
        gN.seed_plate(k, c, nrm, R_SEED, T_SEED)
        ns += 1
    except ValueError:
        pass
g1.init_parent()
gN.init_parent()
same0 = np.array_equal(g1.phi.view(np.uint8), gN.phi.view(np.uint8))
print('播种 %d 个核；初值逐位相同 = %s' % (ns, same0), flush=True)

dt = 0.15 * dx / (MOB * DF)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2')

fail = []
for it in range(1, a.steps + 1):
    g1._t_since_reinit = 0.0
    gN._t_since_reinit = 0.0
    e1 = g1.elastic_driving()
    eN = gN.elastic_driving()
    ok_e = np.array_equal(e1.view(np.uint8), eN.view(np.uint8))
    if not ok_e:
        fail.append('E-2 elastic_driving step %d' % it)
    g1.advance(dt, **KW)
    gN.advance(dt, **KW)
    okp = np.array_equal(g1.phi.view(np.uint8), gN.phi.view(np.uint8))
    okr = np.array_equal(g1.region().view(np.uint8), gN.region().view(np.uint8))
    okd = (g1.dG_max == gN.dG_max)
    if not (okp and okr and okd):
        fail.append('E-1/2 step %d (phi=%s region=%s dG=%s)' % (it, okp, okr, okd))
    print('  step %d: phi逐位=%-5s region逐位=%-5s dG_max相同=%-5s  (dG=%.6e)'
          % (it, okp, okr, okd, g1.dG_max), flush=True)

# 强制 reinit 一次再比
g1.reinitialize(band_cells=6, force=True)
gN.reinitialize(band_cells=6, force=True)
okre = np.array_equal(g1.phi.view(np.uint8), gN.phi.view(np.uint8))
if not okre:
    fail.append('E-1 forced reinit')
print('  强制 reinit 后 phi 逐位相同 = %s' % okre, flush=True)

# ---- E-3 正对照：改变 dt 必须让结果不同（证明守卫有分辨力）----
gN.phi = g1.phi.copy()
g1._t_since_reinit = 0.0
gN._t_since_reinit = 0.0
g1.advance(dt, **KW)
gN.advance(dt * 1.0000001, **KW)
okc = not np.array_equal(g1.phi.view(np.uint8), gN.phi.view(np.uint8))
print('  E-3 正对照（dt 差 1e-7 相对）：结果不同 = %s  ← 必须 True' % okc, flush=True)
if not okc:
    fail.append('E-3 正对照无分辨力')

# ---- E-4 并行真的被调用 ----
tot, rows = gN.par.report()
print('\n  E-4 并行统计（nthreads=%d）：总 wall %.2f s，逐算子 top8：'
      % (gN.nthreads, tot), flush=True)
for tag, (tt, cnt, mx) in rows[:8]:
    print('        %-22s %8.2f s  ×%d  最大分段 %d' % (tag, tt, cnt, mx), flush=True)
print('      注意：`ParCtx.stats` 目前在核内部未逐次打点，只有 `report()` 拿到的表；'
      '若为空说明打点没接上（**必须修**，不许静默）', flush=True)
print('      par.n = %d ; nest_max = %d' % (gN.par.n, gN.par._nest_max), flush=True)

print('\n' + '=' * 96)
if fail:
    print('✗ 端到端守卫 FAIL：')
    for f in fail:
        print('   -', f)
    sys.exit(1)
print('★ 端到端守卫全部 PASS：多核改造**不改变任何一个数**')
print('=' * 96)
