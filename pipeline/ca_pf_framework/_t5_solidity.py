#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_solidity.py --- ★★★★★ 那些后期场是**实心团块**还是**散碎片段**？（决定我量具是否失效）

## 为什么要查（**用户的质疑逼出来的**）
用户问："新的场不应该也是要形核的吗？这是代码的问题吗？"
**⇒ 逼我重新看数字，发现一个反常：**
```
场 10 首现：包围盒 4.247 × 4.289 × 4.181 µm（~76 µm³）
            但只有 **2657 体素 = 0.65 µm³**
种子盘参考：1044 体素 = 0.255 µm³
```
**⇒ 体积只比种子大 2.5 倍，却被摊在 4.2 µm 的范围里 ⇒ **不是实心块，而是稀疏/散碎的格点集**。**
**⇒ 而**对散碎集合，PCA 跨度与长宽比没有物理意义****（跨度 = 最远两点距离，不是形状）。

## 本脚本（**判定量具是否失效**）
对每个场算：
1. **实心度 solidity = 体素体积 / 包围盒体积**（实心板条应 ≈ 0.3-0.6；散碎云会 ≪ 0.1）；
2. **连通段数**（用 6-邻域 labeling；应与 `series.csv` 的 `runs` 一致 —— **交叉验证**）；
3. **按实心度分档**：早期场 vs 后期场。
**⇒ 判据（预先写死）**：
* 若后期场实心度 **≪ 0.1** 或连通段 **>3** ⇒ **它们是散碎片段 ⇒ 我的长宽比量具对它们**不适用****；
* 若后期场实心度 **>0.3** 且连通段 =1 ⇒ **确实是实心团块 ⇒ 量具有效，是物理现象**。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
VOX = DX ** 3 * 1e-9          # µm³ / 体素
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not snaps:
    print('  （无快照）'); sys.exit(0)
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)

print('=' * 100)
print('★ %s 快照 step %d：各场的**实心度**与**连通段数**' % (TAG, st))
print('=' * 100)
print('  %-5s %-8s %-12s %-12s %-10s %s'
      % ('场', '体素', '体积(µm³)', '包围盒(µm³)', '**实心度**', '**连通段数**'))
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    n = int(m.sum())
    if n < 8:
        continue
    idx = np.argwhere(m)
    bb = float(np.prod(idx.max(0) - idx.min(0) + 1)) * VOX
    v = n * VOX
    lab, ncomp = ndimage.label(m, structure=ndimage.generate_binary_structure(3, 1))
    print('  %-5d %-8d %-12.4f %-12.3f %-10.3f %d'
          % (k, n, v, bb, v / max(bb, 1e-12), ncomp))
print()
print('  ── 判据（**预先写死**）──')
print('  * 实心板条（1000×500×510 nm 椭球）: 实心度 ≈ **0.52**（π/6），连通段 = 1;')
print('  * 散碎云: 实心度 ≪ 0.1 或 连通段 > 3 ⇒ **我的长宽比量具对它们不适用**;')
print('  * ★ 交叉验证：这里的"连通段数"应与 `series.csv` 的 `runs` 列一致。')
