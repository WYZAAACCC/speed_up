#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_nm.py --- 判定 `argmin_normal` 报的极小点是否自洽（B-2/B-4 的矛盾点）

矛盾：`_chk_branch.py` 报「`n_micro` 离 rank-1 候选仅 0.05°，但能量低 13%」，
而一维切向扫描显示 E 在候选点**上升**（+3.6% @0.05°）。
⇒ 必须查清：是"极小点确实极窄"，还是 `argmin_normal` 的落点/能量不自洽。

判据（先定判据再看数）
--------------------
  N-1 **两条求值路径必须一致**：`E(n_micro)`（标量 `_lam_full`）必须等于
      `argmin_normal` 返回的 `vm`（批量 `_lam_full_batch`），相对差 < 1e-12。
      不等 ⇒ 批量核在**该点**失效（正对照只在 500 个 Fibonacci 点上做过）。
  N-2 **二维角邻域扫描**：在 rank-1 候选点周围做 θ∈[0,2°] × φ∈[0,360°) 的网格，
      报该邻域内的**最小能量**。
      * 若邻域最小 ≈ `vm` ⇒ 极小点确实在候选点附近且极窄 ⇒ B-2 自洽；
      * 若邻域最小 ≈ `E(候选)` ≫ `vm` ⇒ `vm` 不在该邻域 ⇒ `argmin_normal` 跑到别处了，
        必须重新审视「它到底在最小化什么」。
  N-3 **`n_micro` 的落点**：打印 `n_micro` 与候选的夹角，以及 `E(n_micro)`。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import (C_cubic, _lam_full, _lam_full_batch,   # noqa: E402
                          argmin_normal, E_normal)
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
eps = np.asarray(EPS0[0], float)          # 变体 1


def E1(n):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', eps, _lam_full(C, n), eps))


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


print('=' * 100)
print('_chk_nm —— `argmin_normal` 落点自洽性（变体 1）')
print('=' * 100)

nm, vm, cons = argmin_normal(C, eps, nsamp=20000)
print('\n  `argmin_normal` 返回： n_micro = (%+.6f,%+.6f,%+.6f)  vm = %.6e  cons = %.4f'
      % (nm[0], nm[1], nm[2], vm, cons))
print('  标量路径 E(n_micro) = %.6e' % E1(nm))
print('  批量路径 E_normal     = %.6e' % float(E_normal(C, eps, nm[None, :])[0]))
print('  N-1 两条路径相对差 = %.3e  => %s'
      % (abs(E1(nm) - vm) / max(abs(vm), 1e-30),
         'PASS（同一泛函）' if abs(E1(nm) - vm) / max(abs(vm), 1e-30) < 1e-12
         else 'FAIL（批量核在该点失效！）'))

# ---- N-2 二维角邻域 ----
w_, V = np.linalg.eigh(eps)
o = np.argsort(w_)[::-1]
w_, V = w_[o], V[:, o]
e1, e3 = V[:, 0], V[:, 2]
r = np.sqrt(-w_[2] / w_[0])
n_raw = e1 + r * e3
nref = n_raw / np.linalg.norm(n_raw)
Eref = E1(nref)
print('\n  rank-1 解1 的 n = (%+.6f,%+.6f,%+.6f)   E = %.6e'
      % (nref[0], nref[1], nref[2], Eref))
print('  <n_micro, n_rank1> = %.4f deg' % ang(nm, nref))

t1 = np.cross(nref, [0.0, 0.0, 1.0])
if np.linalg.norm(t1) < 1e-6:
    t1 = np.cross(nref, [0.0, 1.0, 0.0])
t1 /= np.linalg.norm(t1)
t2 = np.cross(nref, t1)

best, bth, bph = None, None, None
for th_d in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
    th = np.deg2rad(th_d)
    for ph_d in range(0, 360, 5):
        ph = np.deg2rad(ph_d)
        d = np.cos(ph) * t1 + np.sin(ph) * t2
        n = np.cos(th) * nref + np.sin(th) * d
        n /= np.linalg.norm(n)
        v = E1(n)
        if best is None or v < best:
            best, bth, bph = v, th_d, ph_d
print('\n  N-2 邻域扫描（θ ≤ 5°）：最小能量 = %.6e  在 θ=%.2f° φ=%d°' % (best, bth, bph))
print('       E(rank-1 候选) = %.6e ；E(n_micro) = %.6e' % (Eref, vm))
print('       邻域最小 / E(n_micro) = %.4f' % (best / max(vm, 1e-30)))
if abs(best - vm) / max(abs(vm), 1e-30) < 0.02:
    print('  => ✅ 邻域最小 ≈ `vm` ⇒ 极小点确实在 rank-1 候选附近且极窄，B-2 自洽。')
elif abs(best - Eref) / max(abs(Eref), 1e-30) < 0.02:
    print('  => ⛔ 邻域最小 ≈ 候选点能量，而 `vm` 低 13%% ⇒ **`vm` 不在此邻域**：')
    print('     `argmin_normal` 跑到了别处。必须查它在最小化什么（可能不是同一个泛函/同一个 eps）。')
else:
    print('  => ⚠ 邻域最小与两者都不等 ⇒ 需进一步查。')
print('=' * 100)
