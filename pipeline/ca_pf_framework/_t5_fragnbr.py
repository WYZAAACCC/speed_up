#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fragnbr.py --- ★★★★★ 按**碎片**统计邻居成分（区分"表示斑驳" vs "物理独立"）

## 为什么必须按碎片测（**我上一轮的错误**）
先前我把**整个场的外边界**当整体测，得出"多数接触母相" ⇒ 那是**场的整体外边界**，
**而碎片之间的**内边界**根本没被看到** ⇒ 结论对"碎片为何分开"**无判别力**。

## 判据（**预先写死**）
对每个**碎片**，统计它的**外边界**（该碎片独占的边界胞）上：
* `par` = 母相（`region==0`）；
* `sam` = **同变体的其他场**；
* `oth` = **异变体场**。
**⇒ 按碎片给出多数成分，再对"所有非最大碎片"汇总：**
| 结果 | 含义 |
|---|---|
| **`sam` 占多数** | **碎片被"同变体的其他场"隔开** ⇒ **物理上本是同一片，只是归属图斑驳**（表示层）|
| **`par` 占多数** | **碎片之间是真母相** ⇒ **物理独立的多根**（真碎片）|
| **`oth` 占多数** | 被异变体切开 ⇒ 竞争导致的碎裂 |
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
S26 = ndimage.generate_binary_structure(3, 3)
S6 = ndimage.generate_binary_structure(3, 1)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    vmap = {}
    for k, v in zip(np.asarray(z['vmap_keys']).ravel(),
                    np.asarray(z['vmap_vals']).ravel()):
        vmap[int(k)] = int(v)

var_img = np.full(reg.shape, -1, dtype=np.int32)
for f, v in vmap.items():
    var_img[reg == f] = v

print('=' * 104)
print('★ %s step %d：**按碎片**的邻居成分' % (TAG, st))
print('=' * 104)
print('  %-6s %-7s %-9s %-9s %-9s %-9s %s'
      % ('场', '碎片', '体素', 'par(母相)', 'sam(同变体)', 'oth(异变体)', '多数成分'))
agg = {'par': 0, 'sam': 0, 'oth': 0}
n_frag = 0
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    if m.sum() < 100:
        continue
    lab, nc = ndimage.label(m, structure=S26)
    if nc < 2:
        continue
    vk = vmap.get(k, -99)
    for ci in range(1, nc + 1):
        fm = (lab == ci)
        nb = fm.sum()
        if nb < 30:
            continue
        dil = ndimage.binary_dilation(fm, structure=S6) & ~fm
        nbr = reg[dil]
        nv_ = var_img[dil]
        par = int((nbr == 0).sum())
        sam = int(((nv_ == vk) & (nbr != 0) & (nbr != k)).sum())
        oth = int(((nv_ != vk) & (nbr != 0)).sum())
        tot = max(par + sam + oth, 1)
        # 多数成分（**用绝对数，不用占比，避免小碎片噪声主导**）
        maj = max((('par', par), ('sam', sam), ('oth', oth)), key=lambda t: t[1])[0]
        agg[maj] += 1
        n_frag += 1
        if nb >= 200:      # 只打印较大的碎片，避免刷屏
            print('  %-6s %-7d %-9d %-9d %-9d %-9d **%s**'
                  % ('%d(v%s)' % (k, vk), ci, nb, par, sam, oth, maj))
print()
print('  ── 汇总（**全部** %d 个非最大碎片）──' % n_frag)
for key, name in (('par', '母相（⇒ **物理独立**）'),
                  ('sam', '同变体的其他场（⇒ **表示层斑驳**）'),
                  ('oth', '异变体场（⇒ 竞争切开）')):
    print('     多数成分 = %-34s **%3d 个（%.0f%%）**'
          % (name, agg[key], 100.0 * agg[key] / max(n_frag, 1)))
print()
print('  ── 判据（**预先写死**）──')
print('  * **`sam` 占多数** ⇒ 碎片之间其实是**同变体的别的场** ⇒')
print('     **物理上它们本可以是一片，只是归属图（argmin）在同变体碰撞前沿斑驳** ⇒ **表示层现象**;')
print('  * **`par` 占多数** ⇒ 碎片之间是**真母相** ⇒ **物理上就是多根独立板条**（真碎片）。')
