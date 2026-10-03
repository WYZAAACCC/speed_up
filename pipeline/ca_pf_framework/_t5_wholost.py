#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_wholost.py --- ★★★★★★ 三个问题：① 一场一根吗？ ② 碎裂/流失是真的吗？ ③ 流失的胞去哪了？

## 用**物理量具**（`band` 的 φ<0）
* 一个格点若**存在任何场 j 使 `band_val(j) < 0`** ⇒ **该格点是转变态（相）**;
* 若该格点**没有任何场的 φ<0** ⇒ **它是母相**。

## 三个判据
### ① 一个场对应一根板条吗？
数**该场 φ<0 掩模的 26-连通分量数**。**=1 ⇒ 一场一根；>1 ⇒ 一场多块。**
### ② 碎裂/流失是真的吗？
物理掩模的分量数与总体积随时间的演化。
### ③ ★★ 流失的胞去哪了？（**把问题一分为二**）
对 t0 属于场 k（φ_k<0）、t1 不再属于它的那些胞：
* 若 t1 时**仍有某个场 φ<0** ⇒ **归属转移**（相还在，换了主人）;
* 若 t1 时**所有场 φ≥0** ⇒ **真溶解**（变回母相）。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
KS = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else '2,3,4,5'.split(','))]
T0 = int(sys.argv[3]) if len(sys.argv) > 3 else 200
T1 = int(sys.argv[4]) if len(sys.argv) > 4 else 1720


def load_at(st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    return N, bi, bv, bf


def masks(N, bi, bv, bf):
    """返回 (每场的 φ<0 掩模 dict, 全盒"是否转变"掩模)"""
    flat = bi // (N * N) * (N * N) + (bi // N) % N * N + bi % N   # 归一化到整数胞号
    per = {}
    trans = np.zeros(N ** 3, bool)
    neg = bv < 0
    for k in np.unique(bf[neg]):
        k = int(k)
        if k == 0:
            continue
        sel = neg & (bf == k)
        g = np.zeros(N ** 3, bool)
        g[flat[sel]] = True
        per[k] = g
        trans |= g
    return per, trans


A = load_at(T0); B = load_at(T1)
if A is None or B is None:
    print('  ⚠ 快照缺失'); sys.exit(1)
N = A[0]
perA, transA = masks(*A)
perB, transB = masks(*B)
print('=' * 100)
print('★ %s：step %d → %d（物理量具：`band` 的 φ<0）' % (TAG, T0, T1))
print('=' * 100)
print('  全盒转变胞数：step %d = **%d** ｜ step %d = **%d**（Δ=%+d）'
      % (T0, int(transA.sum()), T1, int(transB.sum()), int(transB.sum() - transA.sum())))
print()
print('  ── ① 一个场对应一根板条吗？（数该场 φ<0 掩模的 26-连通分量）──')
print('  %-6s %-12s %-12s %-12s %s'
      % ('场', 'step %d 胞' % T0, '分量数', '最大占比', '判读'))
for k in KS:
    if k not in perA:
        print('  场 %-4d （step %d 无该场）' % (k, T0)); continue
    g = perA[k].reshape(N, N, N)
    lab, nc = ndimage.label(g, structure=S26)
    sz = np.bincount(lab.ravel())[1:]
    fr = sz.max() / max(sz.sum(), 1)
    print('  %-6d %-12d **%-12d** %-12.0f%% %s'
          % (k, int(g.sum()), nc, 100 * fr,
             '**✅ 一场一块**' if nc == 1 else '**❌ 一场 %d 块** ⇒ **不是一根板条**' % nc))
print()
print('  ── ② 碎裂是真的吗？（同一场在两个时刻的分量数）──')
for k in KS:
    row = []
    for (per, st) in ((perA, T0), (perB, T1)):
        if k not in per:
            row.append('—'); continue
        g = per[k].reshape(N, N, N)
        lab, nc = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        row.append('%d 块 / %d 胞 / 最大占比 %.0f%%' % (nc, int(g.sum()), 100 * sz.max() / max(sz.sum(), 1)))
    print('  场 %-4d：step %d → %s ｜ step %d → %s' % (k, T0, row[0], T1, row[1]))
print()
print('  ── ③ ★★ 流失的胞去哪了？（**一分为二**）──')
for k in KS:
    if k not in perA:
        continue
    lost = perA[k] & ~perB.get(k, np.zeros(N ** 3, bool))
    nl = int(lost.sum())
    if nl == 0:
        print('  场 %-4d：无流失' % k); continue
    still = int(transB[lost].sum())      # t1 时仍被**某场**占据
    gone = nl - still                    # t1 时**无任何场** φ<0 ⇒ 真溶解
    print('  场 %-4d：流失 %-6d 胞 ⇒ **转移给别的场 = %-6d（%.0f%%）** ｜ **真溶解 = %-6d（%.0f%%）**'
          % (k, nl, still, 100.0 * still / nl, gone, 100.0 * gone / nl))
print()
print('  ── 判据（**预先写死**）──')
print('  * ① 分量数 **>1** ⇒ **一个场**不是**一根板条**（与代码注释的设计意图冲突）;')
print('  * ③ **真溶解占比高** ⇒ **相在消失**（物理不守恒）⇒ 查物理/代码;')
print('  * ③ **转移占比高** ⇒ 相还在 ⇒ 问题在**归属动力学**（不是溶解）。')
