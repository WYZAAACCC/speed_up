#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_snap_audit.py <tag> <step> —— 审计一个快照里**到底有什么**（查"量具漏了多少"）。

判据：`region` 里每个非零场号的胞数 + 总胞数，与 banner 的 `Vt` 交叉核对。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tag = sys.argv[1]
step = int(sys.argv[2])
p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
print("快照 = %s  (%.1f MB)" % (p, os.path.getsize(p) / 1e6))
with np.load(p, allow_pickle=False) as z:
    print("键 = %s" % sorted(z.files))
    reg = np.asarray(z['region']).astype(np.int32)
    print("region: shape=%s dtype=%s 非零胞数=%d  总胞数=%d"
          % (reg.shape, reg.dtype, int((reg > 0).sum()), reg.size))
    vmap_keys = np.asarray(z['vmap_keys']) if 'vmap_keys' in z.files else None
    vmap_vals = np.asarray(z['vmap_vals']) if 'vmap_vals' in z.files else None
    print("\n  %-6s %-8s %-12s %s" % ('场号', '变体', '胞数', '体积(µm³)'))
    tot = 0
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        n = int((reg == k).sum())
        tot += n
        var = -1
        if vmap_keys is not None:
            hit = np.where(vmap_keys == k)[0]
            if hit.size:
                var = int(vmap_vals[hit[0]])
        print("  %-6d %-8s %-12d %.4f" % (k, var, n, n * DX ** 3 * 1e18))
    print("  %-6s %-8s %-12d **%.4f**" % ('合计', '', tot, tot * DX ** 3 * 1e18))
