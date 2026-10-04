#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fragalign.py --- ★★★★★★ 修正判据的同步对齐比较：**瓣数中位 / 最大分量占比**（不用 `Vt`）

## 判据修正（本会话第十一次口径提醒）
`Vt` 的短期涨落被**形核爆发**主导（step 100→120 因进入第二温度档而 +117%）
⇒ **`Vt` 不是"溶解"的判据**。
★ 正确的判据是 **逐场瓣数**与**最大分量占比**（物理量具 φ<0 的 26-连通分量）。

## 判据（**预先写死**）
在**同一 step** 上：
* `--B 6` 的**瓣数中位更低** 且 **最大分量占比中位更高**
  ⇒ **变体数↑ ⇒ 溶解/碎裂减轻** ⇒ **自协调假说确认** ✓
* 两者相近或 `--B 6` 更差 ⇒ **自协调假说否证** ⇒ 转 **线索 B**（`df(Ms)/|ed| = 0.379`）
"""
import glob
import sys
import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)
STEPS = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1
                          else '160,240,400,600,800'.split(','))]


def frag(tag, st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        N = int(np.asarray(z['N']))
        bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
        bv = np.asarray(z['band_val']).ravel()
        bf = np.asarray(z['band_fld']).ravel()
    neg = bv < 0
    rows = []
    for k in sorted(int(x) for x in np.unique(bf[neg]) if x != 0):
        sel = neg & (bf == k)
        n = int(sel.sum())
        if n < 30:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, c = ndimage.label(g, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        rows.append((k, n, c, 100.0 * sz.max() / max(sz.sum(), 1)))
    if not rows:
        return None
    return dict(nf=len(rows),
                nc=float(np.median([r[2] for r in rows])),
                ncmax=int(max(r[2] for r in rows)),
                frac=float(np.median([r[3] for r in rows])),
                n1=int(sum(1 for r in rows if r[2] == 1)))


print('=' * 104)
print('★ 同步对齐：**瓣数 / 最大分量占比**（物理量具 φ<0；不用 `Vt`）')
print('=' * 104)
print('  %-6s | %-42s | %s' % ('step', '--B 6 (修复)', '--B 3 (对照)'))
for st in STEPS:
    a = frag('t5B6np', st)
    b = frag('t5N276F', st)
    def fmt(d):
        if not d:
            return '（无快照/无场）'
        return ('场=%-3d **瓣中位=%-5.1f** 最大=%-3d **占比=%.0f%%** 单块场=%d/%d'
                % (d['nf'], d['nc'], d['ncmax'], d['frac'], d['n1'], d['nf']))
    print('  %-6d | %-42s | %s' % (st, fmt(a), fmt(b)))
print()
print('  ── 判据（**预先写死**）──')
print('  * **同一 step** 上 `--B 6` 的**瓣数中位更低** 且 **占比中位更高**')
print('    ⇒ **变体数↑ ⇒ 碎裂/溶解减轻** ⇒ **自协调假说确认** ✓')
print('  * 两者相近，或 `--B 6` 更差 ⇒ **自协调假说否证** ⇒ 转 **线索 B**')
print('    （`df(Ms)/|ed| = 0.379` 的量级不匹配）')
