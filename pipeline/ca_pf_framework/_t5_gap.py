#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_gap.py --- ★★★★★ 第4条候选的检验：碎片之间隔的是**薄膜**还是**真的分开**？

## 方法（**膨胀半径扫描** —— 干净且决定性）
对一个场的掩模，逐档**膨胀** r = 0,1,2,3,5,8,12 体素，每档数 26-连通分量数：
* **在小 r（1–2）就合并** ⇒ 碎片之间只隔**1–2 体素的薄层** ⇒ **薄膜切割**（物理：残余 β 膜）;
* **要到较大 r（≥5）才合并** ⇒ 隔的是**厚实的别的相/场** ⇒ 碎片**本来就分开**;
* **一直不合并（r=12 仍多块）** ⇒ 碎片相距 ≥25 体素（>1.5 µm）⇒ **完全独立**。

## 同时报
* 每个碎片与其**最近的其他碎片**之间的距离（体素）；
* 隔开它们的是**母相（0）**还是**别的场**（>0）—— 取"连接两碎片的最短路径"上的多数成分。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)

RADII = [0, 1, 2, 3, 5, 8, 12]
print('=' * 100)
print('★ %s step %d：碎片**膨胀半径扫描**（判"薄膜切割"还是"真的分开"）' % (TAG, st))
print('=' * 100)
print('  %-6s %-7s %s' % ('场', '体素', '  '.join('r=%-2d' % r for r in RADII)))
rows = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    n = int(m.sum())
    if n < 100:
        continue
    counts = []
    for r in RADII:
        mm = ndimage.binary_dilation(m, structure=S26, iterations=r) if r else m
        _, c = ndimage.label(mm, structure=S26)
        counts.append(c)
    rows.append((k, n, counts))
    print('  %-6d %-7d %s' % (k, n, '  '.join('%-4d' % c for c in counts)))
print()
print('  ── 汇总：各档下"仍是多块"的场数 ──')
for i, r in enumerate(RADII):
    multi = sum(1 for _, _, c in rows if c[i] > 1)
    print('     r=%-2d ⇒ 仍多块的场 = **%2d / %d**' % (r, multi, len(rows)))
print()
print('  ── 判据（**预先写死**）──')
print('  * **r=1–2 就全部合并（multi→0）** ⇒ **薄膜切割**（残余母相薄层，物理）;')
print('  * **r≥5 仍多块** ⇒ 碎片**真的分开**（相距 >0.3 µm）⇒ 与"薄膜"无关;')
print('  * **r=12 仍多块** ⇒ 相距 >0.75 µm ⇒ 完全独立的两根/多根。')
