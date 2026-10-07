#!/usr/bin/env python3
"""R51: cln11 的快照里到底存了什么？（决定能不能用金标准面间距口径事后重测）"""
import glob
import os

import numpy as np

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
snaps = sorted(glob.glob('_exp/_bk_closed/dry_cln11/snap_*.npz'))
print('快照 %d 个' % len(snaps))
for s in snaps[:4] + snaps[-1:]:
    z = np.load(s)
    ks = sorted(z.files)
    big = {k: (z[k].shape, str(z[k].dtype)) for k in ks
           if k in ('phi', 'region', 'psi')}
    print('  %-22s step=%-6s keys=%s' % (os.path.basename(s), z['step'], ks))
    if big:
        print('        sizes: %s' % big)
print()
z = np.load(snaps[-1])
print('=== 末快照细节')
for k in sorted(z.files):
    a = z[k]
    print('  %-14s shape=%-18s dtype=%-10s' % (k, a.shape, a.dtype))
print()
print('⇒ 若只有 `region`：**金标准面间距（要 φ）无法事后重测**，')
print('  只能用 `region` 上的几何量（跨度/分量/连通性）。')
print('  若还有 `band_*` 或 `phi`：可离线重算 `face_separations`。')
