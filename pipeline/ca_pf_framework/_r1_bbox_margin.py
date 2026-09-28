#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_bbox_margin.py --- ★ 子盒 reinit 的**最小充分余量**：实测扫描（不靠推理）

背景
----
`_r1_reinit_bbox.py` 第一版判 FAIL，但根因是**我自己的别名 bug**
（子盒路径原地改了调用者的 `d2` ⇒ `dn − d2 ≡ 0`）。修掉之后必须重新回答：
**余量取多少，子盒结果才与全域逐位相同？**

推理（只作假设，不作结论）：`upwind_grad2` 的数值依赖锥是**每迭代 ±2 胞**
（`Dm2[i]` 用 `phi[i−2..i+1]`、`Dp2` 用 `phi[i+2]`）⇒ `iters=100` 时半径 ≈ **200 胞**，
任何实用余量都不够。**但这只是上界**；实际有效依赖可能短得多
（特征线只向**界面内侧**传，而界面就在带里）。⇒ **必须实测。**

判据（先写死）
--------------
  M-1 逐位判据：对**真实引擎状态**上的**每一个活跃配对**，比较
      `sussman_reinit(d2, bbox=…, margin=m)` 与 `sussman_reinit(d2)` 在**带内**的差；
      要求 `max|Δ| == 0`（逐位）。
  M-2 报出"最小充分 margin" `m*`，以及 `m*` 下的**体积占比**（决定省不省）。
  M-3 ⛔ 若 `m*` 大到体积占比 > 0.6 ⇒ **子盒这条路不值得走**，如实写结论。

用法：python3 _r1_bbox_margin.py --N 48 --dx-nm 125 --iters 100
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
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=48)
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--nseed', type=int, default=6)
ap.add_argument('--steps', type=int, default=10)
ap.add_argument('--iters', type=int, default=100)
ap.add_argument('--band', type=float, default=6.0)
ap.add_argument('--nth', type=int, default=4)
ap.add_argument('--margins', default='0,2,4,8,16,32,64,128,203')
a = ap.parse_args()

dx = a.dx_nm * 1e-9
L = a.N * dx
print('=' * 104)
print('_r1_bbox_margin  最小充分余量实测   N=%d Δx=%.1f nm L=%.2f µm  iters=%d band=%.1f'
      % (a.N, a.dx_nm, L * 1e6, a.iters, a.band))
print('=' * 104, flush=True)

g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=a.nth, reinit_every=0,
                    reinit_dt=6.0e-7, reinit_band_cells=a.band,
                    reinit_iters=a.iters)
rng = np.random.default_rng(5)
ns = 0
for _ in range(a.nseed * 30):
    if ns >= a.nseed:
        break
    c = rng.random(3) * (L - 2e-6) + 1e-6
    k = int(rng.integers(1, NV + 1))
    nrm = np.asarray(NPF[k], float)
    nrm /= np.linalg.norm(nrm)
    try:
        g.seed_plate(k, c, nrm, 400e-9, 250e-9)
        ns += 1
    except ValueError:
        pass
g.init_parent()
dt = 0.15 * dx / (MOB * DF)
KW = dict(aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.2,
          adv_grad='proj2')
for _ in range(a.steps):
    g._t_since_reinit = 0.0
    g.advance(dt, **KW)
print('播种 %d，推进 %d 步，界面键 %d' % (ns, a.steps, g._band_bonds(g.region())), flush=True)

# ---- 抽出真实的活跃配对 ----
reg = g.region()
pairs = set()
for ax in range(3):
    aa = reg
    bb = np.roll(reg, -1, axis=ax)
    sel = aa != bb
    if sel.any():
        for x, y in zip(aa[sel].ravel(), bb[sel].ravel()):
            if x != y:
                pairs.add((int(min(x, y)), int(max(x, y))))
pairs = sorted(pairs)
print('活跃配对 %d 个：%s' % (len(pairs), pairs), flush=True)
if not pairs:
    print('✗ 没有活跃配对，无法定标'); sys.exit(1)

MS = [int(x) for x in a.margins.split(',')]
tot = float(g.phi[0].size)
rows = []
for (k, l) in pairs:
    d2 = 0.5 * (g.phi[k] - g.phi[l])
    near = np.abs(d2) <= a.band * dx
    if not near.any():
        continue
    t0 = time.time()
    full = W.sussman_reinit(d2.copy(), dx, iters=a.iters, band_cells=a.band,
                            par=g.par)
    t_full = time.time() - t0
    dfull = (full - d2)[near]
    for m in MS:
        bb = W._band_bbox(d2, a.band, dx, m)
        vol = 1
        for s in bb:
            vol *= (s.stop - s.start)
        frac = vol / tot
        sub = W.sussman_reinit(d2.copy(), dx, iters=a.iters, band_cells=a.band,
                               bbox=bb, par=g.par)
        d = (sub - d2)[near]
        same = np.array_equal(np.ascontiguousarray(dfull).view(np.uint8),
                              np.ascontiguousarray(d).view(np.uint8))
        rows.append((k, l, m, frac, same, float(np.max(np.abs(dfull - d)))))
    print('  配对 (%d,%d) 全域 %.2f s' % (k, l, t_full), flush=True)

print('\n' + '-' * 104)
print('%-16s %6s %10s %10s %14s' % ('配对', 'margin', '体积占比', '逐位相同', 'max|Δ|'))
for (k, l, m, frac, same, dm) in rows:
    if m in (0, 4, 16, 64, 203):
        print('%-16s %6d %10.4f %10s %14.3e'
              % ('(%d,%d)' % (k, l), m, frac, same, dm))

print('\n★ 汇总：每个 margin 上"全部配对都逐位相同"的比例')
for m in MS:
    sub = [r for r in rows if r[2] == m]
    nok = sum(1 for r in sub if r[4])
    fr = [r[3] for r in sub]
    print('  margin=%-4d  逐位相同 %d/%d   体积占比 中位 %.3f 最大 %.3f'
          % (m, nok, len(sub), float(np.median(fr)), float(np.max(fr))))
ok = [m for m in MS if all(r[4] for r in rows if r[2] == m)]
if ok:
    mstar = min(ok)
    fr = [r[3] for r in rows if r[2] == mstar]
    print('\n  ⇒ **最小充分 margin = %d**（体积占比 中位 %.3f 最大 %.3f）'
          % (mstar, float(np.median(fr)), float(np.max(fr))))
    print('  M-3 判定：%s'
          % ('**不值得走子盒**（占比 > 0.6）' if np.max(fr) > 0.6 else '**值得走**'))
else:
    print('\n  ⇒ 扫描范围内**没有**任何 margin 能让全部配对逐位相同 ⇒ '
          '**子盒路径不可用**（依赖锥确实远超实用余量）')
print('=' * 104)
