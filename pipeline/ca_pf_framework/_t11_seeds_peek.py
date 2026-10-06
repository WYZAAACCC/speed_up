#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_seeds_peek.py <tag> —— 读 seeds.npz，看驱动层预置位点的**实际几何**。"""
import os
import sys

import numpy as np

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD2"
p = next((os.path.join(b, TAG, "seeds.npz") for b in BASES
          if os.path.exists(os.path.join(b, TAG, "seeds.npz"))), None)
if p is None:
    sys.exit("**找不到 seeds.npz**")
print("文件 = %s（%.1f MB）" % (p, os.path.getsize(p) / 1e6))
with np.load(p, allow_pickle=False) as z:
    print("键：")
    for k in z.files:
        a = z[k]
        print("  %-16s shape=%-22s dtype=%s" % (k, a.shape, a.dtype))
    print()
    for k in z.files:
        a = np.asarray(z[k])
        if a.size <= 24:
            print("  %s = %s" % (k, a.ravel()[:24]))
        else:
            f = a.ravel().astype(float)
            print("  %-16s n=%-9d min=%.4g max=%.4g mean=%.4g"
                  % (k, f.size, np.nanmin(f), np.nanmax(f), np.nanmean(f)))
    # 若是 Nx3 的坐标 ⇒ 打印前几个 + 包围盒
    for k in z.files:
        a = np.asarray(z[k])
        if a.ndim == 2 and a.shape[1] == 3 and a.shape[0] <= 64:
            print("\n  `%s` 逐行（可能是位点坐标）：" % k)
            for i, row in enumerate(a):
                print("    %2d  (%.4f, %.4f, %.4f)" % (i, row[0], row[1], row[2]))
        elif a.ndim == 2 and a.shape[1] == 3:
            print("\n  `%s` 是 Nx3（N=%d）；包围盒 = %s"
                  % (k, a.shape[0],
                     np.array2string(a.min(0), precision=4) + ' … ' +
                     np.array2string(a.max(0), precision=4)))
