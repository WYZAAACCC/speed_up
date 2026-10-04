#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_frag.py --- ★★★★★ 碎片化的**三种可能**判别（数值噪声 / 多址形核 / 被邻居吃掉）

## 背景
* 老场（2-9）：最大分量占 **92-100%** ⇒ 连通；
* 新场（10-17）：最大分量只占 **28-70%** ⇒ **确实被切成几块**（每块厚度 0.33-0.50 µm，与老场相同）。
**⇒ 但"碎"有三种成因，结论完全不同：**
| # | 机制 | 性质 | 判别特征 |
|---|---|---|---|
| (a) | `argmin` 体素级抖动（相邻场 φ 接近） | **数值假象** | 碎片**互相咬合**、缝隙 1 体素、**隔的是别的场** |
| (b) | **多址形核**（`attach`/`stack` 多处起同一场） | **物理** | 碎片之间隔**母相**（region=0） |
| (c) | **被邻居吃掉**（别的场长进来切开它） | **物理** | 碎片之间隔**别的场**，且缝隙较宽 |

## 本脚本怎么做
对每个场的**每个碎片**，统计它的 **6-邻域边界**接触到的：
* **母相**（region==0）的胞数；
* **同变体的其他场**的胞数（用快照里的 `vmap_keys`/`vmap_vals` 把场号映射到变体）；
* **异变体场**的胞数。
**⇒ 再汇总到"场"级别，判 (a)/(b)/(c)。**
（⚠ 注意：`region==0` 在 `argmin` 口径下是"母相赢" ⇒ 可近似当母相。见 AGENTS P30 的单位/口径纪律。）
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
    # 场号 → 变体号
    vmap = {}
    if 'vmap_keys' in z.files and 'vmap_vals' in z.files:
        for k, v in zip(np.asarray(z['vmap_keys']).ravel(), np.asarray(z['vmap_vals']).ravel()):
            vmap[int(k)] = int(v)

# 每个胞的"变体号"图（母相 = -1）
var_img = np.full(reg.shape, -1, dtype=np.int32)
for f, v in vmap.items():
    var_img[reg == f] = v

k6 = np.ones((3, 3, 3), bool); k6[1, 1, 1] = False

print('=' * 100)
print('★ %s step %d：碎片化的成因判别' % (TAG, st))
print('=' * 100)
print('  %-5s %-8s %-9s %-10s %-11s %-11s %s'
      % ('场', '碎片数', '最大占比', '接触母相', '同变体他场', '异变体', '判读'))
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    n = int(m.sum())
    if n < 200:
        continue
    lab, nc = ndimage.label(m, structure=S26)
    sizes = np.bincount(lab.ravel())[1:]
    frac = sizes.max() / n
    # 边界邻居成分（只看 ≥100 体素的碎片的外边界）
    nb_par = nb_same = nb_other = 0
    dil = ndimage.binary_dilation(m, structure=k6) & ~m
    nbr = reg[dil]
    vk = var_img[dil]
    nb_par = int((nbr == 0).sum())
    nb_same = int(((vk == vmap.get(k, -99)) & (nbr != 0) & (nbr != k)).sum())
    nb_other = int(((vk != vmap.get(k, -99)) & (nbr != 0)).sum())
    tot = max(nb_par + nb_same + nb_other, 1)
    own = vmap.get(k, '?')
    if frac > 0.9:
        verdict = '连通（无需判）'
    elif nb_par / tot > 0.5:
        verdict = '**(b) 多址形核**（隔母相）'
    elif nb_other / tot > 0.5:
        verdict = '**(c) 被邻居切**（隔异变体）'
    elif nb_same / tot > 0.5:
        verdict = '**(a) 同变体互挤**（可能是标签抖动）'
    else:
        verdict = '混合'
    print('  %-5s %-8d %-9.2f %-10d %-11d %-11d %s'
          % ('%d(v%s)' % (k, own), nc, frac, nb_par, nb_same, nb_other, verdict))
print()
print('  ── 判据（**预先写死**）──')
print('  * 碎片外边界**多数接触母相** ⇒ **(b) 多址形核**（物理，一个新场在多处长大）;')
print('  * 碎片外边界**多数接触异变体场** ⇒ **(c) 被邻居切开**（物理，竞争）;')
print('  * 碎片外边界**多数接触同变体的其他场** ⇒ **(a) 同变体互挤/标签抖动**（数值嫌疑最大）。')
