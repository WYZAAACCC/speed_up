#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_shadow.py --- 判「卫星」是真板条还是**影子**（量具口径检验）。

## 两种口径（本会话早已确认）
* `band_fld == k AND band_val < 0` —— **该场自己的 φ**（我一直在用的形态量具）
* `region == k`，`region = argmin(φ)` —— **物理相归属**（谁离界面最近就是谁的）

## 本检验
把每个场的每个连通分量取出，统计这些胞里 `region == k` 的比例：
* **≈100%** ⇒ 该分量在物理相口径下**确实属于本场** ⇒ 真·独立一块；
* **≈0%** ⇒ 它被**邻场覆盖** ⇒ 只是"本场 φ 仍为负"的**影子**，**不是一块板条**。

⇒ 若多数卫星是影子，则「一个相场里有多个板条」这个**结论本身是量具口径造成的**，
   而不是物理/引擎的问题。这正是用户强调的"量具正确性"。
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
    reg = np.asarray(z["region"]).ravel().astype(np.int32)

# region 的长度可能是 N**3（全盒），而 band 是稀疏对 ⇒ 索引方式不同
print("N=%d  len(region)=%d  N**3=%d  len(band_idx)=%d"
      % (N, reg.size, N ** 3, bi.size))
if reg.size != N ** 3:
    print("⚠ region 不是全盒大小 ⇒ 本脚本的映射不适用")
    sys.exit(1)

rows = []
for k in np.unique(bf[bv < 0]):
    if int(k) == 0:
        continue
    sel = (bf == k) & (bv < 0)
    idx = bi[sel]
    g = np.zeros((N, N, N), bool)
    g[idx // (N * N), (idx // N) % N, idx % N] = True
    lab, nc = ndimage.label(g, structure=S26)
    if nc == 0:
        continue
    sz = np.bincount(lab.ravel())[1:]
    order = np.argsort(-sz)
    for rank, ci in enumerate(order[:3]):
        # ★ 直接从连通分量的 3D 坐标算平铺索引（不要用稀疏 idx 去 mask 3D 的 lab）
        xyz = np.argwhere(lab == (ci + 1))
        flat = xyz[:, 0] * (N * N) + xyz[:, 1] * N + xyz[:, 2]
        rr = reg[flat]
        frac = float((rr == k).mean())
        rows.append((int(k), rank, int(sz[ci]), frac))

rows.sort(key=lambda r: (r[1], -r[2]))
print()
print("  %-6s %-5s %-9s %-12s %s" % ("场", "序", "胞数", "region==本场", "判定"))
main_shadow = 0
sat_shadow = 0
sat_real = 0
for k, rank, n, frac in rows:
    tag = "**主体**" if rank == 0 else "卫星%d" % rank
    verdict = ("真·本场" if frac > 0.8 else
               "**影子（邻场覆盖）**" if frac < 0.2 else "混合")
    if rank == 0 and frac <= 0.2:
        main_shadow += 1
    if rank > 0:
        if frac < 0.2:
            sat_shadow += 1
        elif frac > 0.8:
            sat_real += 1
    if rank <= 1:
        print("  %-6d %-5s %-9d %-12.3f %s" % (k, tag, n, frac, verdict))

print()
print("★ 汇总：")
print("   主体被邻场覆盖的场数 = %d" % main_shadow)
print("   **卫星里**：影子 = %d 个 ；真·独立一块 = %d 个" % (sat_shadow, sat_real))
print("   ⇒ 若影子占多数，「一场多板条」是**量具口径产物**，不是引擎/物理问题。")
