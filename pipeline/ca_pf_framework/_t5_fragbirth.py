#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fragbirth.py --- ★★★★★ 第1步：一个场在**首次出现**时有几个碎片？

## 判别（**预先写死**）
* **首现即多碎片（>1）** ⇒ 形核时就撒了**多个种子** ⇒ **碎片化是设计使然**（非缺陷）；
* **首现 1 个、后来变多** ⇒ 它原本是一根，后来被切开 ⇒ **缺陷嫌疑**。

## 口径
26-连通（对实心形状更合理）；只统计 ≥30 体素的碎片（避免单胞噪声）。
**同时报**：首现 step、首现碎片数、首现体素、以及该场的"碎片数轨迹"。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
MINV = 30
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
steps = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]

data = {}
for P, st in zip(snaps, steps):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    rec = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        m = (reg == k)
        if m.sum() < 30:
            continue
        lab, nc = ndimage.label(m, structure=S26)
        sizes = np.bincount(lab.ravel())[1:]
        big = int((sizes >= MINV).sum())
        rec[k] = (int(m.sum()), big, int(sizes.max()) if sizes.size else 0)
    data[st] = rec

print('=' * 96)
print('★ %s：各场**首次出现**时的碎片数（判"撒多种子"还是"被切开"）' % TAG)
print('=' * 96)
print('  %-5s %-9s %-9s %-10s %-12s %s'
      % ('场', '首现step', '首现体素', '**首现碎片**', '首现最大块', '碎片数轨迹（首现→末）'))
first = {}
for st in steps:
    for k in data[st]:
        first.setdefault(k, st)
for k in sorted(first):
    s0 = first[k]
    n0, big0, mx0 = data[s0][k]
    traj = [data[s][k][1] for s in steps if k in data[s]]
    print('  %-5d %-9d %-9d **%-8d** %-12d %s'
          % (k, s0, n0, big0, mx0, '→'.join(str(x) for x in traj)))
print()
new_first = [k for k in sorted(first) if k >= 10]
mult = [k for k in new_first if data[first[k]][k][1] > 1]
print('  ── 判据汇总 ──')
print('     新场（≥10）共 %d 个；其中**首现即多碎片** = **%d 个**' % (len(new_first), len(mult)))
if new_first:
    fr = [data[first[k]][k][1] for k in new_first]
    print('     首现碎片数：中位 **%d**，范围 [%d, %d]' % (int(np.median(fr)), min(fr), max(fr)))
print()
print('     ⇒ %s' % ('**首现即多碎片 ⇒ 形核时撒了多个种子 ⇒ 碎片化是**设计使然****'
                     if len(mult) > len(new_first) * 0.5 else
                     '**多数场首现是 1 块 ⇒ 后来被切开 ⇒ **缺陷嫌疑****'))
