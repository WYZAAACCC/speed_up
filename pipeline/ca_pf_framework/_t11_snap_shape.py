#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_snap_shape.py —— 查清快照的真实口径（我连续错三次，必须先把格式打出来）。"""
import sys

import numpy as np

sp = sys.argv[1] if len(sys.argv) > 1 else \
    "/mnt/f/speed_up/_exp/_bk_t5/dry_ifaceON/snap_00400.npz"
z = np.load(sp, allow_pickle=True)
print(f"文件: {sp}")
print(f"键（{len(z.files)}）:")
for k in sorted(z.files):
    a = z[k]
    if hasattr(a, "shape"):
        print(f"  {k:16} shape={str(a.shape):18} dtype={a.dtype}")
    else:
        print(f"  {k:16} = {a!r}")

for k in ("band_idx", "band_val", "band_fld"):
    if k not in z.files:
        continue
    a = np.asarray(z[k]).ravel()
    print(f"\n{k}: len={a.size}  dtype={a.dtype}")
    print(f"   min={a.min()!r}  max={a.max()!r}")
    uniq = np.unique(a[:6000])
    print(f"   前 6000 个里不同取值数 = {uniq.size}；前 20 个 = {uniq[:20].tolist()}")

# region 是什么形状
if "region" in z.files:
    r = np.asarray(z["region"])
    print(f"\nregion: shape={r.shape} dtype={r.dtype}  "
          f"uniq={np.unique(r)[:12].tolist()}  n_nonzero={int((r != 0).sum())}")
for k in ("N", "L", "step", "arm"):
    if k in z.files:
        print(f"{k} = {np.asarray(z[k]).ravel()[:3]!r}")
