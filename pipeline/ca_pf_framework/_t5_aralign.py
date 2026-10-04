#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_aralign.py --- ★★★★★★ **步对齐的长宽比比较**（补 ③ 项，避免跨 step 误判）

## 为什么需要
`t5FIX`（修复版）与 `t5N276F`（对照）的**行宽比**此前是**跨 step** 比的
（修复在 step 320–400，对照显示的是 step 2160–2240）⇒ **不可比**（本会话已犯 3 次）。
本脚本在**同一 step** 上并排给出三指标：**长宽比 / 长厚比 / 瓣中位 / 单块场**。

## 量具（**物理量具，非标签**）
* `band_val < 0` 的胞 ⇒ 该场的**物理相**（`band_fld` 给场号）;
* **26-连通分量** 取**最大分量**;
* 长宽比 = `L/W`（PCA 三主轴的最大/次大跨度，单位 dx）;
* 长厚比 = `L/T`，`T` = 沿该场**惯习面法向**的跨度（`n_hab`）。
"""
import glob
import os
import sys

import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)


def measure(tag, st, dx_nm=62.5):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    neg = bv < 0
    ar, tt, nc, fr = [], [], [], []
    for k in sorted(int(x) for x in np.unique(bf[neg]) if x != 0):
        sel = neg & (bf == k)
        if int(sel.sum()) < 30:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, c = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        nc.append(c)
        fr.append(100.0 * sz.max() / max(sz.sum(), 1))
        big = (lab == (int(np.argmax(sz)) + 1))
        P = np.argwhere(big).astype(float)
        if P.shape[0] < 30:
            continue
        cc = P - P.mean(0)
        w, v = np.linalg.eigh(cc.T @ cc)
        o = np.argsort(w)[::-1]
        span = [float((cc @ v[:, o[i]]).max() - (cc @ v[:, o[i]]).min() + 1.0) for i in range(3)]
        ar.append(span[0] / max(span[1], 1e-9))
        if nh is not None:
            tp = cc @ nh
            tt.append(span[0] / max(float(tp.max() - tp.min() + 1.0), 1e-9))
    if not nc:
        return None
    return dict(nf=len(nc), ar=float(np.median(ar)) if ar else 0.0,
                tt=float(np.median(tt)) if tt else 0.0,
                nc=float(np.median(nc)), ncmax=int(max(nc)),
                fr=float(np.median(fr)), n1=int(sum(1 for x in nc if x == 1)))


STEPS = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '200,320,400,480'.split(','))]
A, B = 't5N276F', 't5FIX'
print('=' * 112)
print('★ **步对齐**三指标：%s（对照，η=1.0 线性律） vs %s（修复，η=0.375 + KM 律）' % (A, B))
print('=' * 112)
hdr = ('  %-6s | %-48s | %s' % ('step', A + '（对照）', B + '（修复）'))
print(hdr)
for st in STEPS:
    a = measure(A, st)
    b = measure(B, st)

    def fmt(d):
        if not d:
            return '（无快照）'
        return ('场=%-3d **宽比=%-5.2f** 长厚=%-5.2f 瓣中位=%-5.1f 单块=%d/%d'
                % (d['nf'], d['ar'], d['tt'], d['nc'], d['n1'], d['nf']))
    print('  %-6d | %-48s | %s' % (st, fmt(a), fmt(b)))
print()
print('  ── 判据（**预先写死**）──')
print('   ★ **同一 step 上**：`长宽比` 修复 ≥ 对照（真实 α′ 板条 5–20）')
print('   ★ `长厚比` 修复 ≥ 对照（板条应 ≥10）')
print('   ★ `瓣中位` 修复 ≤ 对照、`单块场` 修复 ≥ 对照 ⇒ 碎裂减轻')
print('   ⚠ 任一 step 上若"宽比好但碎裂差"，说明**修法 A 改善了形状但加剧了拥挤** ⇒ 需记账')
