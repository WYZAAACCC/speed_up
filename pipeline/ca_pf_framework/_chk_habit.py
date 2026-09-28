#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_habit.py --- ★★★ 惯习面法向 `n*` 的**唯一性**检查（`n*` 到底有没有被定错？）

为什么要做（Round 141）
----------------------
`_chk_axes.py` 实测（`NPF`=调用方 / `wtab,atab`=引擎 `_rank1_axes`）：

    变体 1,4,5,7,9,10 : <NPF, n_eng> =  7.3–9.8°   （一致，差在随机抽样）
    变体 2,3,6,8,11,12: <NPF, n_eng> = 88.6–89.7°  （**差 ~90°**）
    且对这 6 个变体 `|NPF · a_eng| = 0.996–1.000` ⇒ **引擎的 `a` 就是调用方的 `n*`**

**根因（读代码）**：`_rank1_axes` 对形状应变 `eps` 做 rank-1 分解
`eps = 0.5(a n^T + n a^T)`。这个分解**有两个解**（`n₊ = e1 + r e3` / `n₋ = e1 − r e3`），
**两个解都精确重构同一个 `eps`** ⇒ 从"重构误差"分不出哪个是惯习面法向。
代码用 `nref`（= 400 个**随机**法向里弹性自能最小的那个）来选解。

⇒ **若能量泛函在两个解处近似简并，选解就取决于随机抽样** —— 而 `T16` 每个变体
   **重新抽**一次、引擎**所有变体共用同一次抽样** ⇒ 两边可能落到不同解。

本探针把 `n*` 的**唯一性**变成可判定的：在**稠密球面**（Fibonacci）上算
`E(n) = 0.5·eps : Lam(C,n) : eps`，找**全局最小**与"离它 >20° 的次小"。

判据（先定判据再看数）
--------------------
  H-4 **正对照·立方对称性**：`E(n)` 必须在立方群操作下不变 ⇒ 最大差应 ≈0。
      破坏则本探针自身有问题，后面结论全不可用。
  H-1 **全局最小唯一**：若"离全局最小 >20° 的次小/全局 < 1.01" ⇒ **简并** ⇒
      "400 随机抽样取 argmin"**不可复现** ⇒ 必须改成规范化选法。
  H-2 **`NPF` 与两个 rank-1 解各在哪个盆地**：报 `NPF` 与全局最小的夹角、
      以及 `NPF` 与引擎 `a_eng`/`n_eng` 的夹角 ⇒ 分清"抽样噪声"与"选解错"。

用法：python3 _chk_habit.py [--nsphere 40000]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import _lam_full                              # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--nsphere', type=int, default=40000)
a = ap.parse_args()


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


print('=' * 108)
print('_chk_habit —— `n*` 唯一性   E(n) = 0.5·eps:Lam(C,n):eps    Fibonacci 球面 %d 点'
      % a.nsphere)
print('=' * 108)

# ---- 球面与 Lam 表（**与变体无关**，只算一次）----
ns = a.nsphere
i = np.arange(ns, dtype=float)
ph = np.pi * (3.0 - np.sqrt(5.0)) * i
zz = 1.0 - 2.0 * (i + 0.5) / ns
rr = np.sqrt(np.maximum(0.0, 1.0 - zz * zz))
NS = np.stack([rr * np.cos(ph), rr * np.sin(ph), zz], axis=1)
NS /= np.linalg.norm(NS, axis=1)[:, None]
LAM = np.array([_lam_full(C, n) for n in NS])                   # (ns,3,3,3,3)

# ---- H-4 正对照：立方对称性 ----
E0 = np.asarray(EPS0[0], float)
v0 = 0.5 * np.einsum('ij,sijkl,kl->s', E0, LAM, E0)
worst = 0.0
for perm in [(0, 1, 2), (0, 2, 1), (2, 1, 0)]:
    for sgn in [(1, 1, 1), (-1, 1, 1), (1, -1, 1), (1, 1, -1), (-1, -1, 1)]:
        NSp = NS[:, list(perm)] * np.array(sgn)[None, :]
        Lp = np.array([_lam_full(C, n) for n in NSp])
        worst = max(worst, float(np.max(np.abs(
            0.5 * np.einsum('ij,sijkl,kl->s', E0, Lp, E0) - v0))))
print('\nH-4 正对照（立方对称性，15 个立方操作）：max|ΔE| = %.3e J/m³ ；相对 %.2e'
      % (worst, worst / max(abs(v0.max()), 1e-30)))
print('    （应 ≈0；不为 0 ⇒ `_lam_full`/`C_cubic` 有问题 ⇒ 本探针结论不可用）')

# ---- 引擎的 wtab/atab ----
g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)

print('\nH-1/H-2 逐变体     `E(n)` 全局最小 vs 离它 >20° 的次小')
print('  %-4s %8s %10s %9s | %8s %8s | %8s %8s | %8s' %
      ('变体', 'E(NPF)', 'E(n_glob)', 'E比', '<NPF,glob>', '<NPF,次小>',
       '<n_eng,glob>', '<a_eng,glob>', '<NPF,a_eng>'))
amb = 0
for k in range(1, NV + 1):
    E = np.asarray(EPS0[k - 1], float)
    v = 0.5 * np.einsum('ij,sijkl,kl->s', E, LAM, E)
    ig = int(np.argmin(v))
    ng, vg = NS[ig], float(v[ig])
    far = np.abs(NS @ ng) < np.cos(np.deg2rad(20.0))
    if far.any():
        js = np.flatnonzero(far)[int(np.argmin(v[far]))]
        nsx, vs = NS[js], float(v[js])
    else:
        nsx, vs = None, float('nan')
    npref = np.asarray(NPF[k], float)
    w_ = np.asarray(g.wtab[k], float)
    a_ = np.asarray(g.atab[k], float)
    w_ /= np.linalg.norm(w_)
    a_ /= np.linalg.norm(a_)
    neng = np.cross(w_, a_)
    neng /= np.linalg.norm(neng)
    # `E(NPF)`：NPF 不在球面网格上 ⇒ 直接算
    vN = 0.5 * float(np.einsum('ij,ijkl,kl->', E, _lam_full(C, npref), E))
    ratio = vs / vg
    if ratio < 1.01:
        amb += 1
    print('  %-4d %8.3e %10.3e %9.5f | %7.3f° %7.3f° | %7.3f° %7.3f° | %7.3f°'
          % (k, vN, vg, ratio, ang(npref, ng), 0.0 if nsx is None else ang(npref, nsx),
             ang(neng, ng), ang(a_, ng), ang(npref, a_)))

print('\n  ⇒ H-1：次小/全局 < 1.01 的变体数 = **%d/%d**' % (amb, NV))
if amb:
    print('     ⇒ `n*` 在能量上**接近简并**；"400 随机抽样取 argmin" 的选解'
          '**不可复现**（引擎与调用方已实测对 6/12 个变体落到不同解）。')
else:
    print('     ⇒ `n*` 全局最小唯一（次小 >1% 深）⇒ 两边差 ~90° 不是简并，')
    print('        而是 **`_rank1_axes` 选错了 rank-1 解**（`nref` 用 |n·nref| 选，')
    print('        但 `a` 方向也可能更接近 `nref`）⇒ 须改选法。')
print('=' * 108)
