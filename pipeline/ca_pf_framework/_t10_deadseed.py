#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_deadseed.py --- 分辨未发育的 10 个场是「死核」还是「小核」（去阈值）。

对 step 200 快照，列出**指定场号**的：
  * 带内胞数（`band_fld==k & band_val<0`，**不设下限**）
  * 该场 φ 的负区是否非空
  * 是否出现在 `region` 里
并与"正常发育"的场（如 111）对照。
判据：
  * 若这些场 **带内胞 = 0** ⇒ **死核**（核没长起来/被抹掉）；
  * 若 **>0 但很小** ⇒ **小核**（只是没长到我的 30 胞阈值）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10CL2"
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 200
WATCH = [68, 119, 120, 121, 122, 123, 124, 125, 126, 162, 111, 112, 1]

p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (TAG, ST))
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z["N"]))
    bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
    bv = np.asarray(z["band_val"]).ravel()
    bf = np.asarray(z["band_fld"]).ravel()
    reg = np.asarray(z["region"]).ravel().astype(np.int32)

tot = bv.size
print("══ %s step=%d  N=%d  带内条目=%d（%.1f%% of N³）══\n"
      % (TAG, ST, N, tot, 100.0 * tot / N ** 3))
print("  %-6s %-10s %-12s %-12s %s"
      % ("场", "带内胞", "φ<0 的胞", "region 里的胞", "判定"))

for k in WATCH:
    sel = (bf == k) & (bv < 0)
    nb = int(sel.sum())
    nreg = int((reg == k).sum())
    if nb == 0:
        v = "**死核（一个胞都没有）**"
    elif nb < 30:
        v = "小核（<30 胞，被我的阈值滤掉）"
    else:
        v = "正常发育"
    print("  %-6d %-10d %-12s %-12d %s" % (k, nb, "-", nreg, v))

print()
allk = np.unique(bf[bv < 0])
print("  快照里出现的全部场号（%d 个）= %s" % (len(allk), list(map(int, allk))))
sz = {}
for k in allk:
    if int(k) == 0:
        continue
    sz[int(k)] = int(((bf == k) & (bv < 0)).sum())
if sz:
    arr = np.array(sorted(sz.values()))
    print("  带内胞分布：min=%d  中位=%d  max=%d ；<30 胞的场 = %d 个"
          % (arr.min(), int(np.median(arr)), arr.max(), int((arr < 30).sum())))
