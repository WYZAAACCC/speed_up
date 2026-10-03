#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fraggeom.py --- ★★★★★ 碎片几何：碎片之间**相距多少**？是"跨盒面折返"还是"两个独立核"？

## 判据（**预先写死**）
对每个碎片算质心，然后看**两两之间的原始位移**：
* 若某对碎片的位移 **≈ 盒长 L**（或 L 的整数倍）⇒ **同一个种子跨盒面（最小镜像）折返** ⇒ 记账假象;
* 若位移 **≈ 种子长度（elong·R ≈ 2.2 µm）** ⇒ 种子被**拆成两段**（播种时就被分开）;
* 若位移 **很小（< 种子长）** 但**不连通** ⇒ 中间被**别的场/母相**隔开（薄层切割）。

## 同时报
* 每个碎片的**体素/尺寸/质心（µm）**；
* **原始位移** vs **最小镜像位移**（两者差别大 ⇒ 折返）。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5FIX'
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 3
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1] if len(sys.argv) <= 3 else [s for s in snaps if ('%05d' % int(sys.argv[3])) in s][0]
ST = int(P.split('snap_')[1].replace('.npz', ''))
DX = 62.5
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
N = reg.shape[0]
L = N * DX / 1000.0            # µm

print('=' * 100)
print('★ %s step %d：盒 %.2f µm（%d³）—— 碎片几何' % (TAG, ST, L, N))
print('=' * 100)

# 按碎片数排序，取前 TOPN 个"最碎"的场
info = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    if m.sum() < 100:
        continue
    lab, nc = ndimage.label(m, structure=S26)
    sizes = np.bincount(lab.ravel())[1:]
    keep = [i + 1 for i, s in enumerate(sizes) if s >= 30]
    if len(keep) >= 2:
        info.append((k, len(keep), int(m.sum()), lab, keep, sizes))
info.sort(key=lambda x: -x[1])
print('  碎片 ≥2 的场：%s' % [(k, n) for k, n, *_ in info[:8]])
print()

for k, nc, nvx, lab, keep, sizes in info[:TOPN]:
    print('  ── 场 %d：%d 个碎片（≥30 胞），总 %d 胞 ──' % (k, nc, nvx))
    cents, dims = [], []
    for ci in keep:
        idx = np.argwhere(lab == ci).astype(float)
        c = idx.mean(0) * DX / 1000.0
        cents.append(c)
        ext = (idx.max(0) - idx.min(0) + 1) * DX / 1000.0
        dims.append(ext)
        print('     碎片 %-2d：%5d 胞  质心 (%.2f, %.2f, %.2f) µm  尺寸 %.2f×%.2f×%.2f'
              % (ci, int((lab == ci).sum()), c[0], c[1], c[2], ext[0], ext[1], ext[2]))
    print('     ── 两两位移 ──')
    for i in range(len(cents)):
        for j in range(i + 1, len(cents)):
            d_raw = np.linalg.norm(cents[i] - cents[j])
            d = cents[i] - cents[j]
            d_mi = d - L * np.round(d / L)
            d_min = np.linalg.norm(d_mi)
            tag = ''
            if abs(d_raw - L) < 0.5:
                tag = '  ← ★ **≈ 盒长** ⇒ 跨盒面折返'
            elif d_min < 0.3:
                tag = '  ← ★ **最小镜像下相邻** ⇒ 本是一块'
            elif d_raw < 2.5:
                tag = '  ← 位移 < 种子长（2.2 µm）⇒ 可能是薄层切割'
            print('       碎片 %d–%d：原始 **%.2f µm** ｜ 最小镜像 %.2f µm%s'
                  % (keep[i], keep[j], d_raw, d_min, tag))
    print()

print('  ── 种子参考尺寸 ──')
print('     `--eng-r-nm 320` · `--eng-elong 7` ⇒ 种子长约 **%.2f µm**、宽约 **%.2f µm**'
      % (2 * 0.320 * 7 / 2, 2 * 0.320))   # 半宽 R=320nm ⇒ 长 ~2.24、宽 ~0.64
print('     盒长 L = %.2f µm ⇒ 种子长 / 半盒 = %.2f' % (L, 2.24 / (L / 2)))
print()
print('  ── 判据（**预先写死**）──')
print('  * 位移 **≈ L** ⇒ 跨盒面折返（假象）;')
print('  * 位移 **≈ 2.2 µm（种子长）** ⇒ 种子被拆成两段（播种就把一个核分成两块）;')
print('  * 位移 **< 1 µm 且最小镜像下不相邻** ⇒ 中间被薄层隔开。')
