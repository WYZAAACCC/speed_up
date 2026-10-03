#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_vardist.py --- ★★★★★ 两臂的**场→变体分布**（检验"同变体场太多 ⇒ argmin 斑块化"）
"""
import glob
import sys
import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)
for TAG in ('t5N276', 't5NR'):
    snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
    if not snaps:
        print('★ %s：（无快照）' % TAG); continue
    P = snaps[-1]
    st = int(P.split('snap_')[1].replace('.npz', ''))
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        vmap = {}
        for k, v in zip(np.asarray(z['vmap_keys']).ravel(),
                        np.asarray(z['vmap_vals']).ravel()):
            vmap[int(k)] = int(v)
    print('=' * 92)
    print('★ %s step %d：场 → 变体 分布' % (TAG, st))
    print('=' * 92)
    live = sorted(int(x) for x in np.unique(reg) if x != 0)
    from collections import defaultdict
    byv = defaultdict(list)
    for k in live:
        byv[vmap.get(k, -1)].append(k)
    print('  活跃场数 = **%d**' % len(live))
    print('  变体分布：')
    for v in sorted(byv):
        ks = byv[v]
        print('     变体 %-3d ： **%2d 个场**  %s' % (v, len(ks), ks[:24]))
    # 每个场的碎片数
    frag = {}
    for k in live:
        m = (reg == k)
        if m.sum() < 100:
            continue
        _, c = ndimage.label(m, structure=S26)
        frag[k] = c
    tot = sum(frag.values())
    print()
    print('  ── 关键对照 ──')
    print('     活跃场 %d 个 ⇒ 它们分布在 **%d 个变体**上' % (len(live), len(byv)))
    print('     碎片总数 = **%d**（平均每场 %.1f 块）' % (tot, tot / max(len(frag), 1)))
    # 最大变体组的场数 vs 该组的碎片
    vmax = max(byv, key=lambda v: len(byv[v]))
    ks = byv[vmax]
    fmax = sum(frag.get(k, 0) for k in ks)
    print('     **最大变体组 = 变体 %d（%d 个场）** ⇒ 占活跃场的 **%.0f%%**，'
          '贡献碎片 **%d/%d = %.0f%%**'
          % (vmax, len(ks), 100.0 * len(ks) / len(live), fmax, tot,
             100.0 * fmax / max(tot, 1)))
    print()
    print('  ── 判据（**预先写死**）──')
    print('  * 若**两臂都**是"一个变体占绝大多数场" ⇒ **同变体场过多**成立'
          ' ⇒ 支持"argmin 斑块化"（且解释了 random 为何没修好）;')
    print('  * 若 `t5NR` 的变体分布**明显更分散** ⇒ 该假设不成立。')
    print()
