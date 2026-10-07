#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_f3test.py --- ★★★★★★ 验证：**内层片（两侧 F3，Δf≡0）会碎，外层片（有 F1 自由面）不碎**

## 假说（来自 `_bk_exp.py:1554-1560` 的注释逐字）
> 「**内层片两张宽面都是 F3、`Δf = Δe_el ≡ 0`，没有任何体驱动力** 去补回来（§5.1）
>   ⇒ **被削薄就只会继续缩、碎裂**」

## 判据（**预先写死**）
按各场沿 `n_hab`（惯习面法向）的**平均投影**排序（用**早期**快照定序，避免被后期形变影响）：
* **最外两片**（投影极小/极大）⇒ **各有一张自由面（F1，α′/β）** ⇒ 预期**瓣数保持 1**;
* **中间的片**（内层）⇒ **两侧都是 F3** ⇒ 预期**瓣数增长（碎裂）**。
**⇒ 若"外层瓣数≈1 且内层瓣数≫1" ⇒ **机制确认**;**
**⇒ 若"两者都碎" ⇒ **否证**，需另找原因。**

## 量具（**物理相**）
`band` 的 φ<0 ⇒ 逐场物理掩模 ⇒ 26-连通分量数（每场取 ≥20 胞的分量）。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
S26 = ndimage.generate_binary_structure(3, 3)
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
steps = [int(P.split('snap_')[1].replace('.npz', '')) for P in snaps]


def load(P):
    with np.load(P, allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    return N, bi, bv, bf, nh


def per_field(st):
    fs = [f for f in snaps if ('%05d' % st) in f]
    if not fs:
        return None
    N, bi, bv, bf, nh = load(fs[0])
    neg = bv < 0
    out = {}
    for k in np.unique(bf[neg]):
        k = int(k)
        if k == 0:
            continue
        sel = neg & (bf == k)
        idx = bi[sel]
        i = idx // (N * N); j = (idx // N) % N; kk = idx % N
        g = np.zeros((N, N, N), bool)
        g[i, j, kk] = True
        lab, nc = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        nbig = int((sz >= 20).sum())
        proj = float(((np.stack([i, j, kk], 1) + 0.5) * 62.5 @ nh).mean()) if nh is not None else 0.0
        out[k] = dict(n=int(g.sum()), nc=nc, nbig=nbig, proj=proj)
    return out


print('=' * 100)
print('★ %s：**外层片 vs 内层片** 的碎裂对比（判据：外层不碎、内层碎）' % TAG)
print('=' * 100)
t0 = 400
A = per_field(t0)
if not A:
    print('  ⚠ step %d 无快照' % t0); sys.exit(1)
# 取**最大的一个块**（按场数最多的那组变体？此处简化：取投影连续的一段场）
ks = sorted(A, key=lambda k: A[k]['proj'])
print('  以 step %d 的**沿 n_hab 投影**排序（nm）：' % t0)
for rank, k in enumerate(ks):
    print('     rank %-2d 场 %-5d proj=%8.1f  胞=%-6d 瓣=%d' %
          (rank, k, A[k]['proj'], A[k]['n'], A[k]['nbig']))
print()
print('  ── 瓣数随时间的演化（外层 rank 0/末位 vs 内层中间）──')
sel = [ks[0], ks[-1], ks[len(ks)//2]]
if len(ks) > 4:
    sel += [ks[1], ks[-2], ks[len(ks)//2 + 1]]
sel = sorted(set(sel), key=lambda k: ks.index(k))
print('  %-6s %-10s %s' % ('场', 'rank', '  '.join('step %d' % s for s in steps[::4])))
for k in sel:
    row = []
    for st in steps[::4]:
        P = per_field(st)
        if P and k in P:
            row.append('%-7d' % P[k]['nbig'])
        else:
            row.append('%-7s' % '—')
    print('  %-6d %-10d %s' % (k, ks.index(k), '  '.join(row)))
print()
print('  ── 判据（**预先写死**）──')
print('  * **rank 最小/最大（外层）的瓣数保持 1**，而**中间（内层）的瓣数增长** ⇒ **✅ 机制确认**;')
print('  * **两者都增长** ⇒ **❌ 否证** ⇒ 需另找原因。')
