#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_samecmp.py --- ★★★★★ **步对齐**对照：`t5N276`（修复前）vs `t5N276F`（修复版）

## 为什么必须步对齐（**本项目的纪律：跨步比较会把演化当成差异**）
我上一轮拿 `t5N276F step 600` 去比 `t5N276 step 2160` ⇒ **步数不同 ⇒ 不是对照**。
**⇒ 本脚本在同一批 step 上测两版**，口径完全一致：
* **活跃场数**（`region` 非零场号数）
* **最大连通分量占比**（中位 / 最小）—— **碎片化的正确口径**
* **长宽比 / 长厚比**（**只按每场的最大连通分量测**）
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
S26 = ndimage.generate_binary_structure(3, 3)
STEPS = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1
                          else '400,600,800,1000,1200,1500,1800,2160'.split(','))]
TAGS = (sys.argv[2] if len(sys.argv) > 2 else 't5N276,t5N276F').split(',')


def metrics(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    fr, ar, lt = [], [], []
    for k in ks:
        m = (reg == k)
        n = int(m.sum())
        if n < 30:
            continue
        lab, _ = ndimage.label(m, structure=S26)
        sizes = np.bincount(lab.ravel())[1:]
        if sizes.size == 0:
            continue
        fr.append(sizes.max() / n)
        big = (lab == (int(np.argmax(sizes)) + 1))
        idx = np.argwhere(big).astype(np.float64)
        if idx.shape[0] < 30:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
        T = (float((c @ nh).max() - (c @ nh).min() + 1) * DX / 1000.0) if nh is not None \
            else float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(L / max(W, 1e-9)); lt.append(L / max(T, 1e-9))
    return dict(nf=len(ks), fr=fr, ar=ar, lt=lt)


print('=' * 104)
print('★ 步对齐对照：活跃场数 · 最大分量占比 · 长宽比/长厚比（只按每场**最大分量**测）')
print('=' * 104)
print('  %-6s | %-30s | %s' % ('step', TAGS[0] + '（修复前）', TAGS[1] + '（修复版）'))
for st in STEPS:
    cells = []
    for t in TAGS:
        fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % t)
              if ('%05d' % st) in f]
        if not fs:
            cells.append('（无快照）')
            continue
        m = metrics(fs[0])
        fr = np.array(m['fr']); ar = np.array(m['ar']); lt = np.array(m['lt'])
        cells.append('场=%-2d 占比中位=%3.0f%% 宽比中位=%4.2f 厚比中位=%5.2f'
                     % (m['nf'],
                        (100 * np.median(fr) if fr.size else 0),
                        (np.median(ar) if ar.size else 0),
                        (np.median(lt) if lt.size else 0)))
    print('  %-6d | %-30s | %s' % (st, cells[0], cells[1]))
print()
print('  ── 判据（**预先写死**）──')
print('  * **同 step 下**：修复版的「活跃场数」应**更高**（多留住 stack 的核）;')
print('  * 修复版的「最大分量占比」应**更高**（一场一根，不被撑碎）;')
print('  * 修复版的「长宽比/长厚比」应**更高**（各核独立生长，不再挤在一个场里）。')
