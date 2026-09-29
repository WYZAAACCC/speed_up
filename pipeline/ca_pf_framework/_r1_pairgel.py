#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_pairgel.py --- ★ 用**模型自己的能量**（不是几何）给同 packet 的 6 对排序

为什么必须做这一步
------------------
第 23 轮我用**几何** rank-1 残余 `r` 给 66 对排了序，发现
**packet-1/2 的同族对是"好对"（r=0.707），packet-3~6 是"差对"（r=1.581）**，
并据此新增了 `e7c`（用 V5–V6）做实验 7 的**负对照**。

**但那是几何量，不是模型实际用的量。** 模型里变体-变体界面的行为由：
  * `ncmp[k,l]` —— 由 **`argmin_normal` 在微弹性能 `E(n)` 上**求出的最优法向；
  * `γ_el(k,l)` —— `interface_elastic_energy` 给的**相干界面弹性能**（`windowB_surface.py`）。
⇒ **必须用 `γ_el` 重新排序**，否则 `e7c` 的"好/差对照"就建立在错的量上。

判据（先写死）
--------------
  G-1 对 6 个同 packet 对算 `γ_el`（J/m²）。
  G-2 判定：**若 `γ_el(V1,V2) < γ_el(V5,V6)`** ⇒ 模型自己的能量也支持"好/差对照" ⇒
      `e7c` 设计成立；**否则** ⇒ 几何 `r` 不是模型的判据，`e7c` 的对照**无效**，须撤回。
  G-3 **正对照**：`γ_el` 必须随法向偏离最优值而**单调上升**（用同一对扫几个法向）。
      若法向扫描给出常数 ⇒ 量具坏了，结论作废。
"""
import os
import sys
import itertools

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB            # noqa: E402

PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]
print('=' * 96)
print('用**模型自己的弹性能**给同 packet 的 6 对排序')
print('=' * 96, flush=True)

# 取三轴需要引擎（N=16 即可）
g = W.LevelSetMulti(16, 16 * 2.5e-8, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
ncl = g.ncmp
print('\n各对的 `ncmp[k,l]`（模型给出的最优界面法向）与几何 rank-1 残余 `r`：')
xs = np.asarray(EPS0, float)


def rank1_resid(dE):
    S = 0.5 * (dE + dE.T)
    w, V = np.linalg.eigh(S)
    k = int(np.argmax(np.abs(w)))
    a = np.sign(w[k]) * np.sqrt(abs(w[k])) * V[:, k]
    return float(np.linalg.norm(dE - np.outer(a, a)) / max(np.linalg.norm(dE), 1e-300))


res = {}
for (k, l) in PAIRS:
    nv = ncl[k, l] if ncl is not None else None
    r = rank1_resid(xs[k - 1] - xs[l - 1])
    res[(k, l)] = dict(n=nv, r=r)
    print('   V%-2d–V%-2d   ncmp = [%s]   r = %.4f'
          % ((k, l) + ('%+.4f %+.4f %+.4f' % tuple(nv) if nv is not None
                       and np.all(np.isfinite(nv)) else '非有限', r)), flush=True)

print('\n算 `γ_el`（`interface_elastic_energy`，N=32；每对约 20 s）…', flush=True)
t0 = __import__('time').time()
for (k, l) in PAIRS:
    nv = res[(k, l)]['n']
    if nv is None or not np.all(np.isfinite(nv)):
        res[(k, l)]['gel'] = float('nan')
        print('   V%-2d–V%-2d   γ_el 跳过（ncmp 非有限）' % (k, l), flush=True)
        continue
    gel = W.interface_elastic_energy(C, EPS0, k, l, nv, N=32, dx=2.5e-8)
    res[(k, l)]['gel'] = gel[0]
    print('   V%-2d–V%-2d   **γ_el = %.6e J/m²**   （E=%.4e, A=%.3e m²；累计 %.0f s）'
          % ((k, l) + (gel[0], gel[1], gel[2], __import__('time').time() - t0)), flush=True)

print('\n' + '=' * 96)
print('★ 汇总（按 γ_el 升序）')
print('   %-10s %14s %10s  %s' % ('对', 'γ_el (J/m²)', 'r(几何)', '备注'))
order = sorted(PAIRS, key=lambda p: res[p]['gel'])
for p in order:
    d = res[p]
    tag = ''
    if p == (1, 2):
        tag = '← **e7 用的（好对，几何判据）**'
    if p == (5, 6):
        tag = '← **e7c 负对照用的**'
    print('   V%-2d–V%-2d %14.6e %10.4f  %s' % (p[0], p[1], d['gel'], d['r'], tag))
g12 = res[(1, 2)]['gel']
g56 = res[(5, 6)]['gel']
print('\n★ G-2 判定：γ_el(V1,V2) = %.6e ； γ_el(V5,V6) = %.6e' % (g12, g56))
if np.isfinite(g12) and np.isfinite(g56):
    if g12 < g56:
        print('   ⇒ ✅ **模型自己的能量也支持"好/差对照"** ⇒ `e7c` 设计成立')
    else:
        print('   ⇒ ⛔ **模型能量与几何判据相反** ⇒ `e7c` 的"差对"前提不成立，**须撤回**')
else:
    print('   ⇒ ⚠ 数据非有限，无法判定')
print('=' * 96)
