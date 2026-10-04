#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_frame.py --- 逐帧统计「一场多块」，定位**掐断发生在第几步**。

用法：python _t10_frame.py <tag> [maxstep]
对每个存在的快照，统计：场数、分量数 ≥2 的场数及其占比、各场分量数列表。
"""
import glob
import os
import re
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10DGN"
MAXS = int(sys.argv[2]) if len(sys.argv) > 2 else 999

snaps = sorted(glob.glob(os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_*.npz" % TAG)))
if not snaps:
    print("⚠ 没有快照")
    sys.exit(0)
snaps = [f for f in snaps
         if int(re.search(r"snap_(\d+)\.npz", f).group(1)) <= MAXS]
print("══ %s：共 %d 帧 ══" % (TAG, len(snaps)))
print("  %-6s %-6s %-10s %-10s %s" % ("step", "场数", "有碎块的场", "占比", "各场分量数"))

first_multi = None
for f in snaps:
    st = int(re.search(r"snap_(\d+)\.npz", f).group(1))
    with np.load(f, allow_pickle=False) as z:
        N = int(np.asarray(z["N"]))
        bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
        bv = np.asarray(z["band_val"]).ravel()
        bf = np.asarray(z["band_fld"]).ravel()
    ncs = []
    for k in np.unique(bf[bv < 0]):
        if int(k) == 0:
            continue
        sel = (bf == k) & (bv < 0)
        if sel.sum() < 30:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, nc = ndimage.label(g, structure=S26)
        ncs.append(int(nc))
    if not ncs:
        print("  %-6d （无场）" % st)
        continue
    n_multi = sum(1 for x in ncs if x >= 2)
    pct = 100.0 * n_multi / len(ncs)
    if n_multi > 0 and first_multi is None:
        first_multi = st
    print("  %-6d %-6d %-10d %-10s %s"
          % (st, len(ncs), n_multi, "%.0f%%" % pct,
             "/".join(str(x) for x in sorted(ncs, reverse=True))))
print()
if first_multi is None:
    print("  ⇒ **所有帧都是单一连通体** ⇒ 本配置下没有掐断")
elif first_multi <= 1:
    print("  ⇒ ★ **第 %d 帧（step 1）就已多块** ⇒ **播种所致**（`seed_plate` 写出的 sdf 不连通？）"
          % first_multi)
else:
    print("  ⇒ ★ **掐断发生在 step %d**（step 1 时仍为单一）⇒ **动力学早期掐断**" % first_multi)
