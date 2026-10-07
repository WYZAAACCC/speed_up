#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_region_vs_phi.py <tag>@<step> —— 判 `region` 是不是 `argmin_k φ_k`，并直接检验 `φ` 的等值面形状。

## 决策性检查（`R650`）
我的"填充率"一直 ≈0.2 ⇒ 要么场不是盒子，要么 **`region` 不是 `φ` 的 argmin**（而是分区/胜者）。
本工具：
  ① 从快照的 `band_idx`/`band_val`/`band_fld` **重建每个场的 `φ`**（窄带内）；
  ② 对窄带内每个胞，算 `argmin_k φ_k`，与 `region` 对账；
  ③ 对某个场，在 `(n*,a,w)` 坐标下画"`φ_k<0` 的占用"沿 `w` 的剖面
     ⇒ 若该场是盒子，每个 `(i,j)` 组合在 `w` 上都应是**连续一段**且占满该场 `w` 跨度。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
spec = sys.argv[1] if len(sys.argv) > 1 else "B40@700"
tag, _, st = spec.partition('@')
st = int(st)
p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
with np.load(p, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    N = int(np.asarray(z['N']).ravel()[0])
    L = float(np.asarray(z['L']).ravel()[0])
    dx = L / N
    bidx = np.asarray(z['band_idx'])
    bval = np.asarray(z['band_val'], float)
    bfld = np.asarray(z['band_fld'])
    U = np.stack([np.asarray(z['n_hab'], float),
                  np.asarray(z['a_ax'], float),
                  np.asarray(z['w_ax'], float)], 0)

print("=" * 90)
print("【%s】step %d" % (tag, st))
print("=" * 90)
flds = sorted(int(v) for v in np.unique(bfld))
print("  快照带里出现的场号 = %s" % flds)
print("  带内胞数 = %d（其中 `region<=0` 的 = %d）"
      % (len(bidx), int((reg.ravel()[bidx] <= 0).sum())))
# ---- ① 重建窄带内的 φ 场（每场一张 N³，带外 = +1e3）----
phi = {}
for k in flds:
    a = np.full(N ** 3, 1e3)
    sel = (bfld == k)
    a[bidx[sel]] = bval[sel]
    phi[k] = a
# ---- ② argmin 对账 ----
keys = sorted(phi)
M = np.stack([phi[k] for k in keys], 0)
am = np.array(keys)[np.argmin(M, 0)]
inband = np.zeros(N ** 3, bool)
inband[bidx] = True
same = int((am[inband] == reg.ravel()[inband]).sum())
tot = int(inband.sum())
print("\n  ② `region` vs `argmin_k φ_k`（只在带内比）：**%d / %d = %.1f%%** 一致"
      % (same, tot, 100.0 * same / max(tot, 1)))
print("     ⚠ 带外胞无 φ 数据 ⇒ 只能比带内；带内就是界面附近 ⇒ 这里最能暴露不一致。")
# ---- ③ 该场的 w 剖面 ----
for k in keys:
    if k <= 0:
        continue
    m = (reg == k)
    if int(m.sum()) < 500:
        continue
    idx = np.argwhere(m).astype(float)
    pr = idx @ U.T
    lo = np.floor(pr.min(0))
    ijk = np.round(pr - lo).astype(np.int64)
    wcol = {}
    for i, j, kk in ijk:
        wcol.setdefault((int(i), int(j)), []).append(int(kk))
    wmax = int(ijk[:, 2].max())
    full = sum(1 for v in wcol.values() if len(v) == (max(v) - min(v) + 1))
    spanfull = sum(1 for v in wcol.values()
                   if min(v) == 0 and max(v) == wmax)
    print("\n  ③ 场 %d：`(n*,a)` 格点组合 = %d 个；其中『`w` 上连续』的 = %d；"
          "且贯通整个 `w` 跨度的 = %d" % (k, len(wcol), full, spanfull))
    print("     ⇒ 若该场是盒子，应**几乎全部**贯通（%d / %d）" % (spanfull, len(wcol)))
