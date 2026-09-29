#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_wire.py --- R30 审计 S1：`--nthreads` 到底接到了哪里？（"参数传了但没生效"专项）

三件事：
  W-1 复刻 `_bk_exp.py:266-272` 的**逐字**构造调用 ⇒ 打印 `g.par.n` / `g.nthreads`
      / `g.pf.workers`，证明 `workers=a.nthreads` 真的落到了并行上下文。
  W-2 **负对照**：复刻旧探针 `_probe_workers.py:90-91` 的写法（构造后再改
      `g.workers` / `g.pf.workers`）⇒ 证明这样改**对 `advance` 无效**
      （`g.par.n` 不变）⇒ 旧探针的"advance 恒为单线程"结论是**量错了旋钮**。
  W-3 静态消费者清单：`workers` 在 `windowB_surface.py` 里的全部去处。

用法：python3 -u _r30_wire.py
"""
import os
import re
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

F = []


def ck(tag, ok, det=''):
    print('  %-70s %s   %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def build(N, nthreads):
    """与 `_bk_exp.py:266-272` 同形（N 取小只为便宜；接口完全一致）。"""
    L = N * 25e-9
    eps0 = [np.asarray(EPS0[v], float) for v in range(2)]
    nv = len(eps0)
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=nthreads,
                        reinit_every=0, reinit_dt=6.0e-7,
                        reinit_band_cells=6.0,
                        dG_of_T=None, T_of_t=None, T=None)
    g.lath = WL.LathTable([1, 1], omegas=WL.default_omega(2, 5.0),
                          eps0_var=EPS0, npref_var=NPF, gamma0=0.15)
    return g


print('=' * 104)
print('_r30_wire —— `--nthreads` 接线核查')
print('=' * 104)

print('\n[W-1] 复刻 `_bk_exp.py:266-272` 的构造调用（workers=a.nthreads）')
for nt in (1, 2, 4):
    g = build(16, nt)
    ok = (g.par.n == nt) and (g.nthreads == nt) and (g.pf.workers == nt)
    print('  --nthreads %d ⇒  g.par.n=%d  g.nthreads=%d  g.pf.workers=%d'
          % (nt, g.par.n, g.nthreads, g.pf.workers))
    ck('W-1 --nthreads=%d 真的落到 ParCtx 与 PF3D' % nt, ok)
    g.par.close()

print('\n[W-2] 负对照：复刻旧探针 `_probe_workers.py:90-91` 的写法')
g = build(16, 1)
before = g.par.n
g.workers = 4
g.pf.workers = 4
after = g.par.n
print('  构造 workers=1 ⇒ g.par.n=%d；改 `g.workers=4` 与 `g.pf.workers=4` 之后'
      ' g.par.n=%d' % (before, after))
ck('W-2 改 `g.workers` / `g.pf.workers` **不改 ParCtx**（旧探针量错了旋钮）',
   after == 1, 'g.pf.workers=%d（只影响 FFT）' % g.pf.workers)
g.par.set_threads(4)
ck('W-2b 正确改法 `g.par.set_threads(4)` 生效', g.par.n == 4,
   'g.par.n=%d' % g.par.n)
g.par.close()

print('\n[W-3] 静态：`workers` 在 windowB_surface.py 里的全部去向')
src = open(os.path.join(_HERE, 'windowB_surface.py'), encoding='utf-8').read()
for i, ln in enumerate(src.splitlines(), 1):
    if re.search(r'\bworkers\b', ln) and not ln.strip().startswith('#'):
        print('  %5d  %s' % (i, ln.strip()[:100]))

print('-' * 104)
print('FAIL = %d %s' % (len(F), F if F else ''))
print('=' * 104)
sys.exit(1 if F else 0)
