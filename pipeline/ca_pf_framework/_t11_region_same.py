#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_region_same.py <tagA> <tagB> —— 比**数组内容**（不是文件哈希，后者含时间戳元数据）。

⚠ 记账（`R647` 修）：`_t11_dupcheck2.py` 用 `.npz` 的**文件 SHA256** 比 —— 那是错的量具：
`np.savez` 的 zip 条目含**时间戳** ⇒ 即使数组逐位相同，文件哈希也**必然不同**。
⇒ 必须比 `region` / `band_val` 的**数组内容**。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
A, B = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("B40", "B60")


def load(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in ('region', 'band_val', 'band_idx')}


def steps(tag):
    d = os.path.join(ROOT, "dry_%s" % tag)
    out = []
    for f in sorted(os.listdir(d)):
        if f.startswith("snap_"):
            with np.load(os.path.join(d, f), allow_pickle=False) as z:
                out.append(int(np.asarray(z['step']).ravel()[0]))
    return sorted(out)


SA, SB = steps(A), steps(B)
common = sorted(set(SA) & set(SB))
print("=" * 92)
print("比**数组内容**：%s vs %s（共有 step %d 个）" % (A, B, len(common)))
print("=" * 92)
print("  %-7s %-14s %-14s %s" % ('step', 'region 相同?', 'band_val 相同?', 'band_val 最大差'))
nsame = 0
for st in common:
    la, lb = load(A, st), load(B, st)
    if la is None or lb is None:
        continue
    r_eq = bool(np.array_equal(la['region'], lb['region']))
    v_eq = bool(np.array_equal(la['band_val'], lb['band_val']))
    d = float(np.max(np.abs(la['band_val'].astype(float)
                           - lb['band_val'].astype(float)))) if not v_eq else 0.0
    nsame += (r_eq and v_eq)
    print("  %-7d %-14s %-14s %.3e" % (st, '✅ 相同' if r_eq else '❌ 不同',
                                       '✅ 相同' if v_eq else '❌ 不同', d))
print()
print("  ⇒ **完全相同的 step：%d / %d**" % (nsame, len(common)))
print("  ⇒ 判读：全同 ⇒ (a) `band_cells >= 40` 后**真实饱和**；否则 (b) 读数有误。")
