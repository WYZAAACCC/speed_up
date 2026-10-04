#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_erode.py --- ★ 检验「后播籽晶擦断先播板条」假说。

## 假说
`seed_plate` 会对**其它场**执行 `phi[j] = max(phi[j], −sdf)`（`windowB_surface.py:2891-2893`）。
45 个籽晶随机撒 ⇒ 后播的若**横穿**先播的板条，就把其中段擦成正值 ⇒ **一分为二**。
* 与 η 无关 ⇒ 解释「两跑 ⑦ 都是 12/45、同一批场」
* 卫星仍归本场（`region`）⇒ 与观测一致
* 卫星尺度 ≈ 一个籽晶 ⇒ 与观测一致

## 判据（**可 FAIL**）
取每个"有卫星的场"的**主体质心 → 卫星质心**连线，沿线上采样；
统计采样点落在**别的场的板条内部**（`region` 属于他场且他场 φ<0）的比例。
* 若**多数**卫星场的连线上有他场板条横亘 ⇒ **假说成立**（被擦断）；
* 若**几乎没有** ⇒ **假说否证**（不是擦断，得另找机制）。
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10E253"
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 100
p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (TAG, ST))
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z["N"]))
    bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
    bv = np.asarray(z["band_val"]).ravel()
    bf = np.asarray(z["band_fld"]).ravel()
    reg = np.asarray(z["region"]).ravel().astype(np.int32)
print("══ %s step=%d  N=%d ══" % (TAG, ST, N))

# 每个场的 φ<0 掩码 + 分量
fields = {}
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
    if nc == 0:
        continue
    sz = np.bincount(lab.ravel())[1:]
    fields[int(k)] = (g, lab, nc, sz)

results = []
for k, (g, lab, nc, sz) in fields.items():
    if nc < 2:
        continue
    order = np.argsort(-sz)
    if sz[order[1]] < 40:          # 卫星太小就不算（噪声）
        continue
    c_main = np.argwhere(lab == (order[0] + 1)).mean(0)
    c_sat = np.argwhere(lab == (order[1] + 1)).mean(0)
    ts = np.linspace(0.02, 0.98, 60)
    pts = c_main[None, :] * (1 - ts)[:, None] + c_sat[None, :] * ts[:, None]
    pts = np.clip(np.round(pts).astype(int), 0, N - 1)
    flat = pts[:, 0] * (N * N) + pts[:, 1] * N + pts[:, 2]
    own = reg[flat]
    other = (own != k) & (own != 0)          # 落在**别的变体场**里
    in_own = (own == k)
    results.append((k, int(sz[order[0]]), int(sz[order[1]]),
                    float(other.mean()), float(in_own.mean()),
                    int(len(np.unique(own[other]))) if other.any() else 0))

results.sort(key=lambda r: -r[3])
print("\n  有卫星（第二分量 ≥40 胞）的场数 = %d" % len(results))
print("  %-6s %-9s %-8s %-14s %-12s %s"
      % ("场", "主体胞", "卫星胞", "连线上他场占比", "连线上本场占比", "他场个数"))
for k, cm, cs, fr, fo, nk in results:
    print("  %-6d %-9d %-8d %-14.3f %-12.3f %d" % (k, cm, cs, fr, fo, nk))

if results:
    fr = np.array([r[3] for r in results])
    print("\n  ★ 连线被他场占据的比例：中位 %.3f，均值 %.3f" % (np.median(fr), fr.mean()))
    n_hi = int((fr > 0.3).sum())
    print("  ★ 占比 > 0.3 的场数 = %d / %d = **%.0f%%**"
          % (n_hi, len(fr), 100.0 * n_hi / len(fr)))
    print()
    if 100.0 * n_hi / len(fr) >= 50:
        print("  ⇒ ✅ **假说成立**：多数卫星与主体之间确实横着**别的场的板条**")
        print("     ⇒ 机制 = 后播籽晶的 `phi[j]=max(phi[j],−sdf)` **擦断**先播板条")
    else:
        print("  ⇒ ❌ **假说否证**：连线上没有他场板条横亘 ⇒ 不是擦断，需另找机制")
