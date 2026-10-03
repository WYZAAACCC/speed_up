#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_mature.py --- ★★★★★ 填满 5 µm 盒需要多少**成熟**板条（用实测体积分布）

## 为什么不能用种子体积
种子 = `plate_L×W×T = 1000×500×510 nm³ = **0.255 µm³**`（**初始**尺寸）。
而板条**会长**：实测最大场 **3223 体素 = 0.787 µm³**（≈ 3× 种子）。
**⇒ "成熟"必须用**终态实测**的每根体积（体素数 × (62.5 nm)³）。**

## 本脚本给出
1. **`t5H3`（已跑完，step 1800）24 个场的**体积分布**（中位/均值/最大/总和）；
2. **由该分布反推**：填满 **5 µm 盒（125 µm³）** 需要多少根
   —— 分别按 **中位**、**均值**、**最大** 三种口径给（**并说明各自含义**）；
3. **同时给 10 µm 盒（1000 µm³）** 作对照。
"""
import glob
import numpy as np

DX = 62.5          # nm
VOX = DX ** 3 * 1e-9      # 每体素 µm³ = 0.2441e-3 µm³

for TAG in ('t5H3',):
    sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
    if not sn:
        print('  （%s 无快照）' % TAG); continue
    P = sn[-1]
    st = int(P.split('snap_')[1].replace('.npz', ''))
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    vols = []
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        n = int((reg == k).sum())
        if n >= 8:
            vols.append(n * VOX)
    v = np.array(vols)
    print('=' * 88)
    print('★ %s 终态（step %d）：%d 个场的**实测体积**（µm³）' % (TAG, st, len(v)))
    print('=' * 88)
    print('  中位 = **%.4f**   均值 = **%.4f**   最大 = **%.4f**   最小 = %.4f'
          % (np.median(v), v.mean(), v.max(), v.min()))
    print('  **全部场加总 = %.3f µm³**（= 该盒里已转变体积）' % v.sum())
    print('  种子体积（对照）= 0.2550 µm³  ⇒ 中位/种子 = **%.2f×**'
          % (np.median(v) / 0.2550))
    print()
    print('  ── 填满盒子需要多少根（三种口径）──')
    print('  %-14s %-12s %-16s %-16s' % ('口径', '单根体积', '填满 5 µm 盒', '填满 10 µm 盒'))
    print('  ' + '-' * 70)
    for name, val in (('中位（典型）', np.median(v)),
                      ('均值', v.mean()),
                      ('最大（最成熟）', v.max()),
                      ('种子（**已不适用**）', 0.2550)):
        print('  %-14s %-12.4f %-16.0f %-16.0f'
              % (name, val, 125.0 / val, 1000.0 / val))
    print()
    print('  ⚠ 口径说明：')
    print('   * 「中位」= 若所有板条都长到**中位大小**，填满所需的根数；')
    print('   * 「最大」= 若所有板条都长到**已观测到的最大**，填满所需的根数；')
    print('   * 真实答案在两者之间 —— 因为**填得越满，板条互相挤压、单根越小**。')
    print()
    print('  ── 与实际**场预算**对照 ──')
    print('  当前各臂 `nv = 72`（nvar 3 × m 24）⇒ **最多 69 根**（B·n = 3×23）')
    print('  ⇒ 69 根 × 中位 %.3f µm³ = **%.1f µm³** ⇒ 占 5 µm 盒的 **%.1f%%**；'
          % (np.median(v), 69 * np.median(v), 69 * np.median(v) / 125 * 100))
    print('     69 根 × 最大 %.3f µm³ = **%.1f µm³** ⇒ 占 **%.1f%%**'
          % (v.max(), 69 * v.max(), 69 * v.max() / 125 * 100))
