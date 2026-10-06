#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_snapkeys.py <tag> —— 打印快照的全部键、形状、dtype（找 `φ` 场与轴）。"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
tag = sys.argv[1] if len(sys.argv) > 1 else "kW1"
tag = tag[4:] if tag.startswith('dry_') else tag
ps = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz")))
print("文件数 = %d，取最后一个" % len(ps))
p = ps[-1]
print("文件:", p, " 大小 %.1f MB" % (os.path.getsize(p) / 1e6))
with np.load(p, allow_pickle=False) as z:
    for k in z.files:
        a = z[k]
        print("  %-16s %-18s %-10s %s" % (k, str(a.shape), str(a.dtype),
                                          ('min=%.4g max=%.4g' % (np.nanmin(a), np.nanmax(a)))
                                          if a.dtype.kind == 'f' and a.size else ''))
