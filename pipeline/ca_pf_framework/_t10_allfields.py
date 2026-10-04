#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_allfields.py --- 列**全部**场的带内胞数 + 连通分量数（诊断 ⑦ 只有 27% 的原因）。

口径（沿用已核实的）：`band_fld==k & band_val<0`、26-连通、**排除场 0**。
输出按带内胞数降序的全部场，便于看"少数大 + 多数小"的分布形态。
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10N160"
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 100
p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (TAG, ST))
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z["N"]))
    bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
    bv = np.asarray(z["band_val"]).ravel()
    bf = np.asarray(z["band_fld"]).ravel()

rows = []
for k in np.unique(bf[bv < 0]):
    if int(k) == 0:
        continue
    sel = (bf == k) & (bv < 0)
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    lab, nc = ndimage.label(g, structure=S26)
    sz = np.bincount(lab.ravel())[1:] if nc else np.array([0])
    rows.append((int(k), int(sel.sum()), int(nc), int(sz.max()) if nc else 0,
                 float(sz.max()) / max(sz.sum(), 1)))

rows.sort(key=lambda r: -r[1])
print("场数 = %d（排除场 0 = 母相）" % len(rows))
print("  %-6s %-9s %-6s %-9s %-8s" % ("场", "带内胞", "分量数", "最大分量", "主体%"))
for k, c, nc, big, m in rows[:12]:
    print("  %-6d %-9d %-6d %-9d %-8.0f" % (k, c, nc, big, 100 * m))
print("  ...（中间略）...")
for k, c, nc, big, m in rows[-12:]:
    print("  %-6d %-9d %-6d %-9d %-8.0f" % (k, c, nc, big, 100 * m))
print()
import statistics as st
cells = [r[1] for r in rows]
ncs = [r[2] for r in rows]
print("带内胞：中位 %d，均值 %.0f，最大 %d，最小 %d" %
      (st.median(cells), st.mean(cells), max(cells), min(cells)))
print("分量数：中位 %d，均值 %.2f，最大 %d" % (st.median(ncs), st.mean(ncs), max(ncs)))
print("单一连通体（nc==1）：%d/%d = %.0f%%" %
      (sum(1 for r in rows if r[2] == 1), len(rows),
       100.0 * sum(1 for r in rows if r[2] == 1) / len(rows)))
big_ok = [r for r in rows if r[1] >= 1000]
print("带内胞 >= 1000 的场：%d 个；其中单一连通体 %d 个" %
      (len(big_ok), sum(1 for r in big_ok if r[2] == 1)))
