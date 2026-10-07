#!/usr/bin/env python3
"""_r417_cmpcsv.py —— 核对 `nf3` 的**口径**：`dry_saSet2`(归档) vs `dry_gtA`(本轮真值)。

动机：`_r410` 从**快照 `region`** 数出的 `t=0` F3 面数 = **1169**，
      而 `dry_gtA` 的 `series.csv` 在 step 0 报 **3607**。
      两者相差 3.09× ⇒ **必须先搞清是不是同一个量**，否则一切比较都是错的。
"""
import csv
import os
import sys

import numpy as np

BASE = '_exp/_bk_mb'


def P(s):
    print(s, flush=True)


def rows(tag):
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p, newline='') as f:
        return list(csv.DictReader(f))


for tag in ('dry_saSet2', 'dry_gtA', 'dry_gtB', 'dry_gtC', 'dry_saSetP0'):
    r = rows(tag)
    P('=' * 78)
    if r is None:
        P('[%s] ✗ 无 series.csv' % tag)
        continue
    P('[%s] 行数=%d' % (tag, len(r)))
    head = [c for c in r[0].keys()]
    P('  列（%d）：%s' % (len(head), ', '.join(head)))
    sel = [c for c in ('step', 'nf1', 'nf2', 'nf3', 'nf3_col', 'nslab_n',
                       'blk_nprof', 'blk_lruns', 'blk_lath', 'nblk_sig',
                       'Vt', 'f3_area', 'f3_frac') if c in head]
    P('  %s' % ' | '.join('%-9s' % c for c in sel))
    for row in r[:4]:
        P('  %s' % ' | '.join('%-9s' % row.get(c) for c in sel))

# ---- 直接从快照 region 独立数一遍（与 `_r410` 同口径），做交叉核对
P('')
P('=' * 78)
P('[独立核对] 从 `dry_gtA/snap_00000.npz` 的 `region` 直接数 6-邻域异键')


def face_counts(reg, vmap):
    c1 = c2 = c3 = 0
    for d in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        nb = np.roll(reg, d, axis=(0, 1, 2))
        iface = (reg != nb)
        if not iface.any():
            continue
        a, b = reg[iface], nb[iface]
        lo = np.minimum(a, b)
        hi = np.maximum(a, b)
        z = (lo == 0)
        c1 += int(np.count_nonzero(z))
        nz = ~z
        if nz.any():
            va = np.array([vmap.get(int(x), -1) for x in hi[nz]])
            vb = np.array([vmap.get(int(x), -1) for x in lo[nz]])
            same = (va == vb)
            c3 += int(np.count_nonzero(same))
            c2 += int(np.count_nonzero(~same))
    return c1, c2, c3


for tag in ('dry_gtA', 'dry_gtB', 'dry_gtC', 'dry_saSet2'):
    for st in (0, 20):
        p = os.path.join(BASE, tag, 'snap_%05d.npz' % st)
        if not os.path.exists(p):
            continue
        d = np.load(p)
        sd = np.load(os.path.join(BASE, tag, 'seeds.npz'))
        reg = np.asarray(d['region'], np.int64)
        vk = d['vmap_keys'] if 'vmap_keys' in d.files else sd['vmap_keys']
        vv = d['vmap_vals'] if 'vmap_vals' in d.files else sd['vmap_vals']
        vmap = {int(k): int(v) for k, v in
                zip(np.asarray(vk).ravel(), np.asarray(vv).ravel())}
        f1, f2, f3 = face_counts(reg, vmap)
        P('  %-14s step=%-4d  独立数：F1=%-7d F2=%-6d **F3=%-7d**'
          % (tag, st, f1, f2, f3))
P('=' * 78)
