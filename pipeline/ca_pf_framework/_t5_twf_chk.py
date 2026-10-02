#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_twf_chk.py --- ★ 正对照 ②/④：`wide_face_thickness` 里的 `k` 到底起什么作用？

## 要回答的疑点（§33.2 疑点 1）
场 0（**母相**）与场 1（**变体**）给出**完全相同**的 559.6 nm ⇒ 可疑。

## 三类对照（**判据先写死**）
| # | 输入 | 若 `k` 只用来"选场" | 若 `k` 不起作用 |
|---|---|---|---|
| **A** | 场 1 的 φ，`k=1` | 正常 | — |
| **B** | **场 1 的 φ，`k=0`** | 应给出**不同**结果（选的是场 0）| **与 A 完全相同** |
| **C** | **场 0 的 φ（全 `1e3`，无界面）** | 应**报错或给 NaN** | 仍给 559.6 ⇒ **量具在母相上无意义** |

**★ 判据**：若 **B == A** ⇒ `k` 不参与厚度计算 ⇒ **必须查它到底用 `k` 干什么**；
   若 **C 也 == A** ⇒ **量具对"没有界面的场"也给数** ⇒ 判据② **只能对变体场取数**。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM                                     # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t5/dry_t5G3/snap_00000.npz'
with np.load(P, allow_pickle=False) as z:
    N = int(np.asarray(z['N']).item())
    dx = float(np.asarray(z['L']).item()) / N
    n_hab = np.asarray(z['n_hab'], float)
    idx = np.asarray(z['band_idx'])
    val = np.asarray(z['band_val'], np.float64)
    fld = np.asarray(z['band_fld'])


def rebuild(k):
    phi = np.full(N ** 3, 1e3, np.float64)
    m = (fld == k)
    phi[idx[m]] = val[m]
    return phi.reshape(N, N, N)


def pick(r):
    if isinstance(r, dict):
        for kk in ('t_wf', 't_wf_m', 't', 'thickness'):
            if kk in r:
                return float(np.asarray(r[kk]).ravel()[0])
        return '（dict 无厚度键：%s）' % sorted(r)[:6]
    try:
        return float(np.asarray(r).ravel()[0])
    except Exception:
        return str(r)[:40]


phi1 = rebuild(1)
phi0 = rebuild(0)          # 场 0 = 母相；它的"带内"也只是同一张界面
blank = np.full((N, N, N), 1e3, np.float64)   # **完全没有界面**

print('=' * 92)
print('正对照 ②/④：`k` 的作用（%s）' % P)
print('=' * 92)
CASES = [('A  场1 的 φ, k=1', phi1, 1),
         ('B  场1 的 φ, k=0', phi1, 0),
         ('C  场0 的 φ, k=0', phi0, 0),
         ('D  **全 1e3**（无界面）, k=1', blank, 1),
         ('E  **全 1e3**（无界面）, k=0', blank, 0)]
res = {}
for name, phi, k in CASES:
    try:
        r = BM.wide_face_thickness(phi, dx, n_hab, k)
        v = pick(r)
        res[name[0]] = v
        print('  %-30s ⇒ %s' % (name, ('%.1f nm' % (v * 1e9)) if isinstance(v, float) else v))
    except Exception as e:
        res[name[0]] = None
        print('  %-30s ⇒ ❌ %s: %s' % (name, type(e).__name__, str(e)[:44]))
print()
print('  ── 判读（判据先写死）──')
a, b, c, d = res.get('A'), res.get('B'), res.get('C'), res.get('D')
if isinstance(a, float) and isinstance(b, float):
    print('  A vs B（换 k，同一 φ）：%s'
          % ('**完全相同** ⇒ `k` **不参与**厚度计算 ⇒ 必须查它用 k 干什么'
             if abs(a - b) < 1e-12 else '不同（%.1f vs %.1f nm）⇒ k 确实选场 ✓' % (a*1e9, b*1e9)))
if isinstance(d, float):
    print('  D（**完全没有界面**）仍给出 %.1f nm ⇒ ❌ **量具对无界面的输入也给数**'
          % (d * 1e9))
    print('     ⇒ 判据② **绝不能对"没有界面的场"取数**（含母相、空场）')
elif d is None:
    print('  D（完全没有界面）⇒ 抛异常 ⇒ ✅ 量具能拒绝无意义的输入')
print('=' * 92)
