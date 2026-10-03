#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_conn.py --- ★★★★★ "碎裂"是**真碎**还是**连通性判据太严**？

## 背景（**用户质疑 + 我的更正**）
* 用户看 3D 图："新场是**联通**的、长宽比正常"；
* 我算 6-连通 ⇒ 段数 20–59 ⇒ 判"碎裂"；
* ★ 而我刚核实：**`region` 是完整图**（`reg>0` 的体积 = 引擎 `Vt` 的 **84%**，
  差的 16% 可由"快照 step 800 vs Vt@820"与"界面带判给母相"解释）
  ⇒ **数据没问题 ⇒ 那"碎裂"就只能是**连通性判据**的问题。**

## 本脚本（**三档判据对照**）
对每个场算**三种**连通段数：
1. **6-连通**（最严，面相邻）—— 我先前用的；
2. **26-连通**（含角/棱相邻，最松）；
3. **形态学闭运算后 + 6-连通**（结构元 3³，把体素级缝隙抹掉再数）。
**⇒ 判据（预先写死）**：
* 若 **26-连通 = 1**（或闭运算后 = 1）⇒ **"碎裂"是判据假象 ⇒ 场其实是连通的 ⇒ 用户是对的**；
* 若 **三档都 ≫1** ⇒ **确实碎裂**（但那与图矛盾，需另查）。
**同时给出：最大连通分量占该场体素的百分比**（决定性指标 —— 若 >90% 就是"基本连通"）。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)

S6 = ndimage.generate_binary_structure(3, 1)     # 6-连通
S26 = ndimage.generate_binary_structure(3, 3)    # 26-连通

print('=' * 104)
print('★ %s step %d：三档连通判据对照（判"碎裂"是真是假）' % (TAG, st))
print('=' * 104)
print('  %-5s %-8s %-11s %-11s %-13s %-14s %s'
      % ('场', '体素', '6-连通', '26-连通', '闭运算+6连', '最大分量占比', '判读'))
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    m = (reg == k)
    n = int(m.sum())
    if n < 8:
        continue
    _, c6 = ndimage.label(m, structure=S6)
    _, c26 = ndimage.label(m, structure=S26)
    mc = ndimage.binary_closing(m, structure=np.ones((3, 3, 3), bool))
    _, cc = ndimage.label(mc, structure=S6)
    lab6, _ = ndimage.label(m, structure=S6)
    sizes = np.bincount(lab6.ravel())[1:] if lab6.max() > 0 else np.array([0])
    frac = (sizes.max() / n) if n else 0
    verdict = ('**基本连通**' if frac > 0.9 else
               ('部分连通' if frac > 0.5 else '**确实碎**'))
    print('  %-5d %-8d %-11d %-11d %-13d %-14.1f%% %s'
          % (k, n, c6, c26, cc, frac * 100, verdict))
print()
print('  ── 判据（**预先写死**）──')
print('  * **最大分量占比 > 90%** ⇒ 该场**基本连通**（"碎"是长尾小碎块造成的假象）;')
print('  * **26-连通 = 1** 或 **闭运算后 = 1** ⇒ 更彻底地说明"碎"只是判据太严;')
print('  * 结论要按**多数场**的判读来下，不能只看一两个场。')
