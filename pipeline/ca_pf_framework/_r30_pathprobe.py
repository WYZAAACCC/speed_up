#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_pathprobe.py --- R1 审计 S1：**哪些 ParCtx 算子真的走了并行分支？**

不靠读代码猜：把 `ParCtx` 的每个算子在**实例上**包一层计数器，记录
`_segments()` 给出的分段数（=1 ⇒ 走了单线程回退分支；>1 ⇒ 真并行）。
然后跑一次真实的 `advance()`，看每个算子的**并行命中率**。

判据（可证伪）：若 `upwind_flux_vec` 的分段数恒为 1，则它**从未**在 `advance`
里做过空间切片并行 —— `ParCtx.upwind_flux_vec` 的 slab 实现是**死代码**。

用法：python3 -u _r30_pathprobe.py [N] [workers]
"""
import os
import sys
import types
from collections import Counter

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_par as WP                                        # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 48
NW = int(sys.argv[2]) if len(sys.argv) > 2 else 4
DX = 125e-9
GAMMA0 = 0.25
NLATH = 11

CNT = {}
DEPTH = {}


def wrap(name):
    orig = getattr(WP.ParCtx, name)

    def patched(self, *a, **kw):
        c = CNT.setdefault(name, Counter())
        c['calls'] += 1
        c['depth%d' % self._depth()] += 1
        # 复刻 `_segments` 的判据（不改变行为）
        n0 = None
        if name in ('gradient', 'upwind_flux_vec', 'upwind_grad2', 'upwind_grad'):
            n0 = a[0].shape[0] if len(a) else kw['phi'].shape[0]
        elif name in ('argmin2', 'argmin'):
            n0 = a[0].shape[1]
        if n0 is not None:
            nth = self._segments(n0)
            c['nth%d' % min(nth, 8)] += 1
        return orig(self, *a, **kw)
    patched.__name__ = name
    setattr(WP.ParCtx, name, patched)


for _m in ('gradient', 'upwind_flux_vec', 'upwind_grad2', 'upwind_grad',
           'argmin2', 'argmin'):
    wrap(_m)

# ---------------- 装置（小盒，只为把并行分支走一遍） ----------------
L = N * DX
laths = [1] * NLATH
lt = WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                  eps0_var=EPS0, npref_var=NPF, gamma0=GAMMA0)
eps0 = [np.asarray(lt.eps0[i], float) for i in range(len(laths))]
npref = {i + 1: np.asarray(lt.npref[i + 1], float) for i in range(len(laths))}
nv = len(eps0)
g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=GAMMA0, Mob=MOB,
                    df=[0.0] + [DF] * nv, workers=NW, reinit_every=0,
                    reinit_dt=1.0e-7, reinit_band_cells=6.0, reinit_iters=20)
g.lath = lt
c0 = np.array([L / 2] * 3)
n_hab = np.asarray(NPF[1], float)
n_hab /= np.linalg.norm(n_hab)
a_ax = np.asarray(g.atab[1], float)
a_ax /= np.linalg.norm(a_ax)
T, Wd, Lp = 3 * DX, 8 * DX, 20 * DX
for i in range(nv):
    off = (i - (nv - 1) / 2.0) * T
    g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T, elong=Lp / Wd,
                 along=a_ax, flat_end=True)
g.init_parent()
print('=' * 96)
print('_r30_pathprobe  N=%d  workers=%d（生效值 g.par.n=%d）  活跃区域=%s'
      % (N, NW, g.par.n, np.unique(g.region()).tolist()))
print('=' * 96)
dt = 0.15 * g.dx / (MOB * DF)
kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05)
g.advance(dt, **kw)                        # 预热
for k in CNT:
    CNT[k].clear()
g.advance(dt, **kw)                        # 计数的那一步
g.reinitialize(force=True)                 # 覆盖 reinit 路径（sussman 热核）

print('算子                 调用次数  调用时深度分布        分段数分布（nth=1 ⇒ 单线程回退）')
for name in ('argmin2', 'argmin', 'gradient', 'upwind_flux_vec',
             'upwind_grad2', 'upwind_grad'):
    c = CNT.get(name, Counter())
    dep = {k: v for k, v in sorted(c.items()) if k.startswith('depth')}
    nth = {k: v for k, v in sorted(c.items()) if k.startswith('nth')}
    print('  %-18s %6d   %-22s %s' % (name, c.get('calls', 0), dep, nth))
print('-' * 96)
print('注：`depth1` = 该调用发生在 `par.for_each` 的 worker 里 ⇒ `_segments()`')
print('    按死锁守卫（windowB_par.py:124-127）**强制返回 1** ⇒ 走单线程回退。')
print('=' * 96)
