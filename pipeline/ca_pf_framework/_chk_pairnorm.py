#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_pairnorm.py --- `ncmp`（变体-变体界面的相容法向）是否也有 `n*` 那同一个缺陷？

背景（Round 141）
----------------
`_chk_habit2.py` 证明 `n*` 的选取「在 400 个**随机**法向里取能量最小」**从未收敛**
（`E(NPF)/E_min = 21–654`；40k 点 Fibonacci 仍高 3–9 倍；极小极窄）。
而 `windowB_surface.py:1031-1053` 的 `_pair_normals(C, eps0, nsamp=600, seed=0)`
用的是**同一个模式**：`argmin_n 0.5·dEps0:Lam(C,n):dEps0`，只是采样数 600。
它产出 `ncmp`/`ncl`，被 `advance()` 用作**变体-变体界面**的 `β_h` 参考轴
（`windowB_surface.py:2486-2487`）—— 也就是 **block / colony / packet（靶③）** 依赖的那个轴。

判据（**单边**，故意做成不可能误报的方向）
----------------------------------------
由于 20k 点也不是真最小 ⇒ `E(ncmp)/E(best-of-20k) ≤ E(ncmp)/E(true min)`
⇒ 这个比值是缺陷程度的**下界**。**若下界就已经 ≫1，缺陷坐实**（不需要更细的搜索）。

  P-1 **正对照**：把 `ncmp` 换成「20k 点里的最优点」跑同一套代码 ⇒ 比值必须 = 1.000。
  P-2 报 66 个变体对的 `E(ncmp)/E(best20k)` 的分布（min / 中位 / max）与
      `<ncmp, n_best20k>` 的夹角。

用法：python3 _chk_pairnorm.py [--nsphere 20000]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--nsphere', type=int, default=20000)
a = ap.parse_args()

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)


def fib(n):
    i = np.arange(n, dtype=float)
    p = np.pi * (3.0 - np.sqrt(5.0)) * i
    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    NS = np.stack([r * np.cos(p), r * np.sin(p), z], axis=1)
    return NS / np.linalg.norm(NS, axis=1)[:, None]


NS = fib(a.nsphere)
LAM = np.array([_lam_full(C, n) for n in NS])
print('=' * 104)
print('_chk_pairnorm —— `ncmp`（变体-变体相容法向）的收敛性   Fibonacci %d 点' % a.nsphere)
print('=' * 104)

g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
ncm = g.ncmp
assert ncm is not None, '引擎未生成 ncmp'


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


print('\n  %-10s %12s %12s %10s %10s' %
      ('配对 (k,l)', 'E(ncmp)', 'E(best20k)', '比值', '<ncmp,best>'))
rat, dang = [], []
for k in range(1, NV + 1):
    for l in range(k + 1, NV + 1):
        de = np.asarray(EPS0[k - 1], float) - np.asarray(EPS0[l - 1], float)
        v = 0.5 * np.einsum('ij,sijkl,kl->s', de, LAM, de)
        j = int(np.argmin(v))
        nb, vb = NS[j], float(v[j])
        nc = np.asarray(ncm[k, l], float)
        vc = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, nc), de))
        rat.append(vc / vb)
        dang.append(ang(nc, nb))
        if len(rat) <= 6:
            print('  (%2d,%2d)   %12.4e %12.4e %10.5f %9.2f°'
                  % (k, l, vc, vb, vc / vb, dang[-1]))

rat = np.array(rat)
dang = np.array(dang)
print('\n  P-1 正对照：把 `ncmp` 换成 20k 点最优点 ⇒ 比值必须 = 1.000：')
de = np.asarray(EPS0[0], float) - np.asarray(EPS0[1], float)
v = 0.5 * np.einsum('ij,sijkl,kl->s', de, LAM, de)
nb = NS[int(np.argmin(v))]
vb = float(v[int(np.argmin(v))])
vc = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, nb), de))
print('     用 `n_best20k` 自己当输入 ⇒ 比值 = %.6f  %s'
      % (vc / vb, 'PASS' if abs(vc / vb - 1) < 1e-9 else 'FAIL'))

print('\n  P-2 66 个变体对的 `E(ncmp)/E(best20k)`（**缺陷程度的下界**）：')
print('     min = %.3f  中位 = %.3f  max = %.3f   （>1.5 的配对数 %d/66）'
      % (rat.min(), np.median(rat), rat.max(), int((rat > 1.5).sum())))
print('     `<ncmp, n_best20k>`：min = %.2f°  中位 = %.2f°  max = %.2f°  （>20° 的配对数 %d/66）'
      % (dang.min(), np.median(dang), dang.max(), int((dang > 20).sum())))
print('\n  ⇒ 判定：若比值 >> 1 或夹角 >> 0 ⇒ `ncmp` 与 `NPF` 同病（抽样 argmin 未收敛），')
print('     而 `ncmp` 正是 **变体-变体界面（block/colony/packet，靶③）** 的参考轴。')
print('=' * 104)
