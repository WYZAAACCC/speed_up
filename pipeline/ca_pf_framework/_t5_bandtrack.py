#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bandtrack.py --- ★★★★★★ **用物理量具**（band 的 φ<0）逐场跟踪三维尺寸演化

## 为什么换量具（**用户的要求 + 量具错误**）
* 先前用 `region = argmin(φ)` ⇒ **归属标签**，会随邻居生长而重排 ⇒ **不能代表物理相**;
* **`band_val` 就是符号距离 φ**（实测有正有负、量级 = 界面宽）;
* **φ<0 的胞 = 真正的相** ⇒ **逐场物理体积 = #{band_fld==k 且 band_val<0}**;
* **自洽校验**：合计 = 18.003 µm³ vs `Vt` = 18.19 µm³ ⇒ **差 1%** ✓

## 报什么（**逐场**）
* **物理体积**（φ<0 胞数）
* **L / W / T**（PCA-1/PCA-2 跨度 + 沿 `n_hab` 跨度），**只在该场的 φ<0 集合上测**
* **长宽比 / 长厚比**
## 判据（**预先写死**）
* **物理体积单调不减 且 L 不缩** ⇒ **板条没退化** ⇒ 先前的"退化"是标签假象;
* **物理体积真的缩 / L 真的缩** ⇒ **退化真实** ⇒ 需查物理框架与代码。
"""
import glob
import sys
import numpy as np

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
RK = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else '2,3,4,5'.split(','))]
NMAX = int(sys.argv[3]) if len(sys.argv) > 3 else 12


def load(P):
    with np.load(P, allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel()
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    return N, bi, bv, bf, nh


def metrics(N, bi, bv, bf, nh, k):
    m = (bf == k) & (bv < 0)
    n = int(m.sum())
    if n < 10:
        return None
    idx = bi[m].astype(np.int64)
    i = idx // (N * N); j = (idx // N) % N; kk = idx % N
    P = np.stack([i, j, kk], 1).astype(np.float64)
    c = P - P.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    o = np.argsort(w)[::-1]
    L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX
    W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX
    T = (float((c @ nh).max() - (c @ nh).min() + 1) * DX) if nh is not None \
        else float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX
    return dict(n=n, L=L, W=W, T=T, ar=L / max(W, 1e-9), lt=L / max(T, 1e-9))


snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
steps = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]
print('=' * 104)
print('★ %s：**物理量具**（`band` 的 φ<0）逐场三维尺寸演化' % TAG)
print('=' * 104)
cache = {}
for P, st in zip(snaps, steps):
    cache[st] = load(P)

# 找出现最早、且活得最久的若干场（按首现 step 排序）
first = {}
for st in steps:
    N, bi, bv, bf, nh = cache[st]
    for k in np.unique(bf):
        k = int(k)
        if k == 0 or k in first:
            continue
        if int(((bf == k) & (bv < 0)).sum()) >= 10:
            first[k] = st
order = sorted(first, key=lambda k: first[k])[:NMAX]
print('  跟踪的场（按首现 step）：%s' % [(k, first[k]) for k in order])
print()
for k in (RK if RK else order):
    if k not in first:
        print('  场 %d 不存在' % k); continue
    seq = []
    for st in steps:
        if st < first[k]:
            continue
        N, bi, bv, bf, nh = cache[st]
        d = metrics(N, bi, bv, bf, nh, k)
        if d:
            seq.append((st, d))
    if len(seq) < 3:
        continue
    print('  ── 场 %-4d（首现 step %d）──' % (k, first[k]))
    print('     %-7s %-8s %-8s %-8s %-8s %-8s %s'
          % ('step', '体素', 'L(nm)', 'W(nm)', 'T(nm)', '宽比', '厚比'))
    for st, d in seq[:2] + seq[-3:]:
        print('     %-7d %-8d %-8.0f %-8.0f %-8.0f **%-8.2f** %.2f'
              % (st, d['n'], d['L'], d['W'], d['T'], d['ar'], d['lt']))
    d0, d1 = seq[0][1], seq[-1][1]
    print('     ⇒ **Δ体积 = %+d 胞（%+.0f%%）** ｜ **ΔL = %+.0f nm（%+.0f%%）** ｜ ΔW = %+.0f ｜ ΔT = %+.0f ｜ 宽比 %+.2f'
          % (d1['n'] - d0['n'], 100.0 * (d1['n'] / d0['n'] - 1),
             d1['L'] - d0['L'], 100.0 * (d1['L'] / d0['L'] - 1),
             d1['W'] - d0['W'], d1['T'] - d0['T'], d1['ar'] - d0['ar']))
    print()
print('  ── 判据（**预先写死**）──')
print('  * **物理体积单调不减 且 L 不缩** ⇒ **板条没退化** ⇒ 先前的"退化"是**标签假象**;')
print('  * **物理体积真的缩 / L 真的缩** ⇒ **退化真实** ⇒ 需查物理框架与代码。')
