#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_gap.py --- §149.4 待查 2：1–7 号场的**两两最小距离**（判"相遇"解释）

## 判据（**预先写死**）
板条宽度实测 **~0.5 µm ≈ 8 胞**（§84/§144：宽 442–619 nm）。
* 若 1–7 号场之间的**最小距离 ≲ 8 胞** ⇒ **"它们已相遇/贴近"** ⇒ §150.3 的【推理】成立；
* 若**明显大于 8 胞** ⇒ **"相遇"不成立** ⇒ 充填率断崖式下降**另有原因**（须重查）。

## 方法
`scipy.spatial.cKDTree`（生产宿主有 scipy）；逐对算最近胞心距离（胞）。
⚠ 同时报**对照组**：1–7 号场 与 8–24 号场 之间的最小距离（**若前者显著更小 ⇒ 是"早期那批特别近"**）。
"""
import numpy as np
from scipy.spatial import cKDTree

DX = 62.5
P = '_exp/_bk_t5/dry_t5H3/snap_01000.npz'
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region'])
    fld = np.asarray(z['band_fld']).ravel()
    bidx = np.asarray(z['band_idx']).ravel()

coords = np.unravel_index(bidx.astype(np.int64), reg.shape)
reg_at = reg[coords]
print('=' * 88)
print('★ 1–7 号场的两两最小距离（step 1000，单位=胞；板条宽度 ≈ 8 胞）')
print('=' * 88)

def cells_of(f):
    sel = (fld == f) & (reg_at > 0)
    if not sel.any():
        return None
    return np.stack([c[sel] for c in coords], axis=1).astype(np.float64)

# ⚠ 用**完整 region**（不只 band）更能代表形状；这里用 band∩region 做快速估计
#   （两者对"最近距离"的差别很小，因为带外体素仍在场内部）
C = {f: cells_of(f) for f in range(1, 25) if cells_of(f) is not None}
print('  可用场 = %s' % sorted(C))
print()

EARLY = [1, 2, 3, 4, 5, 6, 7]
print('  ── 早期批（1–7）之间的两两最小距离 ──')
ds = []
for i, a in enumerate(EARLY):
    for b in EARLY[i + 1:]:
        if a not in C or b not in C:
            continue
        d, _ = cKDTree(C[b]).query(C[a], k=1)
        ds.append(float(d.min()))
        print('    %2d – %2d : %7.2f 胞 = %7.1f nm' % (a, b, float(d.min()), float(d.min()) * DX))
ds = np.array(ds)
print('    ⇒ 最小 = %.2f 胞 = %.1f nm   中位 = %.2f 胞' %
      (ds.min(), ds.min() * DX, float(np.median(ds))))

print()
print('  ── 对照：早期批 与 8–24 号场 之间的最小距离 ──')
dl = []
for a in EARLY:
    if a not in C:
        continue
    for b in [x for x in C if x not in EARLY]:
        d, _ = cKDTree(C[b]).query(C[a], k=1)
        dl.append(float(d.min()))
dl = np.array(dl)
print('    ⇒ 最小 = %.2f 胞 = %.1f nm   中位 = %.2f 胞' % (dl.min(), dl.min() * DX, float(np.median(dl))))

print()
print('  ── 判读（预先写死）──')
print('  早期批内部最小距离 = %.2f 胞；板条宽度 ≈ 8 胞' % ds.min())
if ds.min() <= 8.0:
    print('  ✅ **≲ 8 胞 ⇒ "它们已相遇/贴近"** ⇒ §150.3 的【推理】成立。')
else:
    print('  ❌ **> 8 胞 ⇒ "相遇"不成立** ⇒ 充填率断崖式下降**另有原因**（须重查）。')
print('  对照比值（早期内部 / 早期-晚期）= %.3f ⇒ %s'
      % (ds.min() / max(dl.min(), 1e-9),
         '早期那批确实更近' if ds.min() < dl.min() else '⚠ 无差别（"相遇"解释减弱）'))
