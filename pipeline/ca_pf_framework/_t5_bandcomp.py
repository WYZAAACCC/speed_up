#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bandcomp.py --- ⚠⚠⚠ 量具再验：**按连通分量**测物理相的形状（而不是整场跨度）

## 我上一轮的量具缺陷（**自查**）
`_t5_bandtrack.py` 用 **`band_fld==k 且 band_val<0` 的**全体**格点算 PCA 跨度。
**若该场的 φ<0 区**被打散成多块**，PCA 跨度 = **最远两点距离**（外接范围），
**不是"板条的宽度/厚度"** ⇒ **"W 暴涨 ×4、T 暴涨 ×10"很可能是这个假象。**

## 本脚本（**正确口径**）
1. 取该场的 φ<0 掩模（物理相）;
2. **26-连通分解**;
3. **只测最大的那个分量**的 L / W / T / 宽比 / 厚比;
4. **并报**：分量数、最大分量占比、以及**所有 ≥100 胞分量的 L/W/T 中位**
   （这样"一根板条"与"被打散"两种情形能分开看）。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
RK = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else '2,3,4,5'.split(','))]


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


def mask_of(N, bi, bv, bf, k):
    m = (bf == k) & (bv < 0)
    if not m.any():
        return None
    idx = bi[m].astype(np.int64)
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    return g


def shape_of(g, nh):
    idx = np.argwhere(g).astype(np.float64)
    if idx.shape[0] < 10:
        return None
    c = idx - idx.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    o = np.argsort(w)[::-1]
    L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX
    W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX
    T = (float((c @ nh).max() - (c @ nh).min() + 1) * DX) if nh is not None \
        else float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX
    return dict(n=idx.shape[0], L=L, W=W, T=T, ar=L / max(W, 1e-9), lt=L / max(T, 1e-9))


snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
steps = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]
print('=' * 104)
print('★ %s：**按连通分量**测物理相（φ<0）的形状 —— 修正"整场跨度"的口径错误' % TAG)
print('=' * 104)
print('  %-5s %-7s %-8s %-8s %-7s %-9s %-9s %-8s %-8s %s'
      % ('场', 'step', '总胞', '分量数', '最大占比', '最大L', '最大W', '最大T', '宽比', '分量L中位/宽比中位'))
for k in RK:
    print('  ── 场 %d ──' % k)
    for st in steps:
        N, bi, bv, bf, nh = load(_p := [P for P, s in zip(snaps, steps) if s == st][0])
        g = mask_of(N, bi, bv, bf, k)
        if g is None:
            continue
        tot = int(g.sum())
        if tot < 20:
            continue
        lab, nc = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        if sz.size == 0:
            continue
        big = (lab == (int(np.argmax(sz)) + 1))
        d = shape_of(big, nh)
        keep = [i + 1 for i, s in enumerate(sz) if s >= 100]
        ds = [shape_of(lab == ci, nh) for ci in keep]
        ds = [x for x in ds if x]
        if not ds or d is None:
            continue
        print('  %-5d %-7d %-8d %-8d %-7.0f%% %-9.0f %-9.0f %-8.0f **%-8.2f** %.0f / %.2f'
              % (k, st, tot, nc, 100.0 * sz.max() / tot, d['L'], d['W'], d['T'], d['ar'],
                 float(np.median([x['L'] for x in ds])),
                 float(np.median([x['ar'] for x in ds]))))
    print()
print('  ── 判据（**预先写死**）──')
print('  * **最大分量的 W/T 稳定（≈680/310 nm）** ⇒ 板条宽度/厚度**没失控** ⇒')
print('    先前的"W/T 暴涨"是**整场跨度的假象**;')
print('  * **最大分量的 W/T 也暴涨** ⇒ **真的失控** ⇒ 需查迁移率各向异性（代码）;')
print('  * **分量数随时间增多、最大占比下降** ⇒ **区域被打散**（另一回事）。')
