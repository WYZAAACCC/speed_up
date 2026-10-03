#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_perconn.py --- ★★★★★ 决定性检验：碎片化是不是**跨盒面（周期）**造成的？

## 假设（来自代码）
`seed_plate` 里有 2026-10-04 的 `N13` 修复：**最小镜像**
```
⇒ 跨盒面的种子自动"接上"另一侧，几何完整，
  与周期动力学自洽（同一块板条在盒两侧各露一半）
```
**⇒ 若一个种子跨过盒面，它在**有界盒**里就表现为**两块（或多块）互不相连的区域** ⇒
**在**非周期**连通判据下算作"碎片"，而在**周期**判据下它们**本是同一块**。**

## 判据（**预先写死**）
对每个场算**两种**连通分量数：
* **非周期**（`ndimage.label`，我先前用的）；
* **周期**（把 `reg` 在三个方向各 `np.tile` 3×3×3，取中心块的场掩模，label 后**只看中心块**的标签数）。
**⇒ 若 `非周期 > 1` 而 `周期 == 1` ⇒ 碎片化 = **跨盒面的记账假象**（不是物理碎片）**；
**⇒ 若两者都 > 1 ⇒ **真的碎**。**
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

N = reg.shape[0]
print('=' * 96)
print('★ %s step %d（盒 %d³）：**非周期 vs 周期**连通分量数' % (TAG, st, N))
print('=' * 96)
print('  %-6s %-8s %-8s %-11s %-11s %s'
      % ('场', '体素', '非周期', '**周期**', '周期后最大块', '判读'))
tot_np = tot_p = 0
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    n = int(m.sum())
    if n < 100:
        continue
    _, c_np = ndimage.label(m, structure=S26)
    # 周期：tile 3×3×3，取中心块对应位置的标签，统计中心块内出现的不同标签数
    big = np.tile(m, (3, 3, 3))
    lab, _ = ndimage.label(big, structure=S26)
    ctr = lab[N:2 * N, N:2 * N, N:2 * N]
    labs = np.unique(ctr[ctr > 0])
    c_p = len(labs)
    # 周期意义下最大块的占比
    if c_p:
        sizes = [int((ctr == L).sum()) for L in labs]
        frac = max(sizes) / n
    else:
        frac = 0.0
    tot_np += c_np; tot_p += c_p
    verdict = ('✅ **周期下连通** ⇒ 碎片是跨盒面假象'
               if (c_np > 1 and c_p == 1) else
               ('**真的碎**（周期下仍 %d 块）' % c_p if c_p > 1 else '连通'))
    print('  %-6d %-8d %-8d **%-8d** %-11.1f%% %s'
          % (k, n, c_np, c_p, frac * 100, verdict))
print()
print('  ── 汇总 ──')
print('     非周期分量总数 = **%d** ｜ 周期分量总数 = **%d**' % (tot_np, tot_p))
print()
print('  ── 判据（**预先写死**）──')
print('  * 若**周期分量总数**远小于非周期 ⇒ **碎片化主要是"跨盒面"的记账假象**;')
print('  * 若两者接近 ⇒ **碎片是物理的**，需另找原因（与盒面无关）。')
